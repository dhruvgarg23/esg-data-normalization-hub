import hashlib
from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import DataIngestionJob, RawRecord
from .serializers import DataIngestionJobSerializer, RawRecordSerializer
from .parsers.sap_parser import parse_sap_csv
from .parsers.utility_parser import parse_utility_csv
from .parsers.travel_parser import parse_travel_csv
from .normalizer import (
    normalize_sap_record, normalize_utility_record, normalize_travel_record,
    compute_confidence,
)
from emissions.models import EmissionRecord
from review.models import AuditLog
from core.models import PlantLookup


PARSER_MAP = {
    'SAP_FUEL': parse_sap_csv,
    'UTILITY_ELECTRICITY': parse_utility_csv,
    'TRAVEL': parse_travel_csv,
}

NORMALIZER_MAP = {
    'SAP_FUEL': normalize_sap_record,
    'UTILITY_ELECTRICITY': normalize_utility_record,
    'TRAVEL': normalize_travel_record,
}


class DataIngestionJobViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = DataIngestionJobSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        tenant = getattr(getattr(self.request.user, 'profile', None), 'tenant', None)
        if tenant:
            return DataIngestionJob.objects.filter(tenant=tenant)
        return DataIngestionJob.objects.none()

    @action(detail=True, methods=['get'])
    def errors(self, request, pk=None):
        """Get raw records with errors for a specific job."""
        job = self.get_object()
        failed = RawRecord.objects.filter(
            ingestion_job=job, status='FAILED'
        )
        serializer = RawRecordSerializer(failed, many=True)
        return Response(serializer.data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def upload_file(request):
    """
    Upload a CSV file for ingestion.

    Expected form data:
      - file: The CSV file
      - source_type: SAP_FUEL | UTILITY_ELECTRICITY | TRAVEL
    """
    file = request.FILES.get('file')
    source_type = request.data.get('source_type')

    if not file:
        return Response({'error': 'No file provided'}, status=status.HTTP_400_BAD_REQUEST)

    if source_type not in PARSER_MAP:
        return Response(
            {'error': f'Invalid source_type. Must be one of: {list(PARSER_MAP.keys())}'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        profile = request.user.profile
        tenant = profile.tenant
    except Exception:
        return Response({'error': 'User has no tenant profile'}, status=status.HTTP_403_FORBIDDEN)

    # Read and hash the file for duplicate detection
    file_content = file.read().decode('utf-8-sig')  # utf-8-sig handles BOM
    file_hash = hashlib.sha256(file_content.encode()).hexdigest()

    # Check for duplicate upload
    if DataIngestionJob.objects.filter(tenant=tenant, file_hash=file_hash).exists():
        return Response(
            {'error': 'This file has already been uploaded (duplicate detected via hash).'},
            status=status.HTTP_409_CONFLICT,
        )

    # Create the ingestion job
    job = DataIngestionJob.objects.create(
        tenant=tenant,
        uploaded_by=request.user,
        source_type=source_type,
        file_name=file.name,
        file_hash=file_hash,
        status='PROCESSING',
    )

    # Parse the file
    parser = PARSER_MAP[source_type]
    normalizer = NORMALIZER_MAP[source_type]

    try:
        parsed_rows = parser(file_content)
    except Exception as e:
        job.status = 'FAILED'
        job.error_log = [{'error': f'Parser crashed: {str(e)}'}]
        job.completed_at = timezone.now()
        job.save()
        return Response(
            {'error': f'Failed to parse file: {str(e)}', 'job_id': str(job.id)},
            status=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )

    # Load plant lookups for facility resolution
    plant_map = {}
    if source_type == 'SAP_FUEL':
        for plant in PlantLookup.objects.filter(tenant=tenant):
            plant_map[plant.plant_code] = plant

    total = len(parsed_rows)
    success = 0
    errors = 0
    error_log = []

    for row_data in parsed_rows:
        raw = row_data['raw_data']
        parsed = row_data['parsed']
        row_errors = row_data['errors']

        # Create raw record
        raw_status = 'FAILED' if row_errors else 'PARSED'
        raw_record = RawRecord.objects.create(
            ingestion_job=job,
            row_number=parsed.get('row_number', 0),
            raw_data=raw,
            parse_errors=row_errors,
            status=raw_status,
        )

        if row_errors:
            # Still attempt normalization if we have enough data
            pass

        # Normalize
        try:
            normalized = normalizer(parsed, tenant)
        except Exception as e:
            normalized = None
            row_errors.append(f'Normalization error: {str(e)}')

        if normalized is None:
            errors += 1
            raw_record.status = 'FAILED'
            raw_record.parse_errors = row_errors
            raw_record.save()
            error_log.append({
                'row': parsed.get('row_number', 0),
                'errors': row_errors,
            })
            continue

        # Resolve facility from plant code
        if source_type == 'SAP_FUEL' and parsed.get('plant'):
            plant = plant_map.get(parsed['plant'])
            if plant:
                normalized['facility_name'] = plant.plant_name
                normalized['country'] = plant.country
                normalized['region'] = plant.region

        # Compute confidence
        confidence = compute_confidence(
            row_errors,
            normalized.get('quality_flags', []),
            has_all_fields=(normalized.get('activity_quantity') is not None),
        )

        # Create emission record
        try:
            emission = EmissionRecord.objects.create(
                tenant=tenant,
                ingestion_job=job,
                raw_record=raw_record,
                source_type=normalized['source_type'],
                source_identifier=normalized.get('source_identifier', ''),
                ghg_scope=normalized['ghg_scope'],
                ghg_category=normalized['ghg_category'],
                activity_description=normalized['activity_description'],
                activity_quantity=normalized['activity_quantity'],
                activity_unit=normalized['activity_unit'],
                original_quantity=normalized['original_quantity'],
                original_unit=normalized['original_unit'],
                emission_factor=normalized.get('emission_factor'),
                co2e_kg=normalized['co2e_kg'],
                activity_date=normalized.get('activity_date'),
                reporting_period_start=normalized.get('reporting_period_start'),
                reporting_period_end=normalized.get('reporting_period_end'),
                facility_name=normalized.get('facility_name', ''),
                facility_code=normalized.get('facility_code', ''),
                country=normalized.get('country', ''),
                region=normalized.get('region', ''),
                confidence=confidence,
                quality_flags=normalized.get('quality_flags', []),
                created_by=request.user,
            )

            # Audit log: record created
            AuditLog.objects.create(
                tenant=tenant,
                emission_record=emission,
                action='CREATED',
                notes=f'Ingested from {source_type}: {file.name}',
                performed_by=request.user,
            )

            raw_record.status = 'NORMALIZED'
            raw_record.save()
            success += 1

        except Exception as e:
            errors += 1
            error_log.append({
                'row': parsed.get('row_number', 0),
                'errors': [f'Failed to create record: {str(e)}'],
            })

    # Update job status
    job.total_rows = total
    job.success_rows = success
    job.error_rows = errors
    job.error_log = error_log
    job.status = 'COMPLETED' if errors == 0 else ('COMPLETED' if success > 0 else 'FAILED')
    job.completed_at = timezone.now()
    job.save()

    return Response(
        DataIngestionJobSerializer(job).data,
        status=status.HTTP_201_CREATED,
    )
