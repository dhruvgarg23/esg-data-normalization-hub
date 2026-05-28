from django.utils import timezone
from django.db.models import Sum, Count, Q, Avg, F
from django.db.models.functions import TruncMonth
from rest_framework import viewsets, status
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import EmissionRecord
from .serializers import EmissionRecordListSerializer, EmissionRecordDetailSerializer
from review.models import AuditLog


class EmissionRecordViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        tenant = getattr(getattr(self.request.user, 'profile', None), 'tenant', None)
        if not tenant:
            return EmissionRecord.objects.none()

        qs = EmissionRecord.objects.filter(tenant=tenant)

        # Filtering
        source_type = self.request.query_params.get('source_type')
        if source_type:
            qs = qs.filter(source_type=source_type)

        ghg_scope = self.request.query_params.get('ghg_scope')
        if ghg_scope:
            qs = qs.filter(ghg_scope=ghg_scope)

        review_status = self.request.query_params.get('review_status')
        if review_status:
            qs = qs.filter(review_status=review_status)

        confidence = self.request.query_params.get('confidence')
        if confidence:
            qs = qs.filter(confidence=confidence)

        job_id = self.request.query_params.get('job_id')
        if job_id:
            qs = qs.filter(ingestion_job_id=job_id)

        return qs

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return EmissionRecordDetailSerializer
        return EmissionRecordListSerializer

    @action(detail=True, methods=['patch'])
    def review(self, request, pk=None):
        """
        Update review status of a record.
        Body: { "action": "APPROVE|REJECT|FLAG", "notes": "..." }
        """
        record = self.get_object()

        if record.is_locked:
            return Response(
                {'error': 'Record is locked and cannot be modified.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        review_action = request.data.get('action', '').upper()
        notes = request.data.get('notes', '')

        valid_actions = {'APPROVE': 'APPROVED', 'REJECT': 'REJECTED', 'FLAG': 'FLAGGED'}
        if review_action not in valid_actions:
            return Response(
                {'error': f'Invalid action. Must be one of: {list(valid_actions.keys())}'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if review_action in ('REJECT', 'FLAG') and not notes:
            return Response(
                {'error': 'Notes are required when rejecting or flagging a record.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        old_status = record.review_status
        new_status = valid_actions[review_action]

        record.review_status = new_status
        record.reviewed_by = request.user
        record.reviewed_at = timezone.now()
        record.review_notes = notes

        if review_action == 'APPROVE':
            record.is_locked = True

        record.save()

        # Audit log
        AuditLog.objects.create(
            tenant=record.tenant,
            emission_record=record,
            action=review_action + ('D' if review_action != 'FLAG' else 'GED'),
            field_changed='review_status',
            old_value=old_status,
            new_value=new_status,
            notes=notes,
            performed_by=request.user,
        )

        if review_action == 'APPROVE':
            AuditLog.objects.create(
                tenant=record.tenant,
                emission_record=record,
                action='LOCKED',
                notes='Record locked after approval',
                performed_by=request.user,
            )

        return Response(EmissionRecordDetailSerializer(record).data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def bulk_approve(request):
    """
    Bulk approve multiple records.
    Body: { "record_ids": ["uuid1", "uuid2", ...] }
    """
    record_ids = request.data.get('record_ids', [])
    if not record_ids:
        return Response(
            {'error': 'No record IDs provided'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        tenant = request.user.profile.tenant
    except Exception:
        return Response({'error': 'No tenant'}, status=status.HTTP_403_FORBIDDEN)

    records = EmissionRecord.objects.filter(
        id__in=record_ids,
        tenant=tenant,
        is_locked=False,
        review_status__in=['PENDING', 'FLAGGED'],
    )

    approved_count = 0
    for record in records:
        old_status = record.review_status
        record.review_status = 'APPROVED'
        record.reviewed_by = request.user
        record.reviewed_at = timezone.now()
        record.is_locked = True
        record.save()

        AuditLog.objects.create(
            tenant=tenant,
            emission_record=record,
            action='APPROVED',
            field_changed='review_status',
            old_value=old_status,
            new_value='APPROVED',
            notes='Bulk approved',
            performed_by=request.user,
        )
        AuditLog.objects.create(
            tenant=tenant,
            emission_record=record,
            action='LOCKED',
            notes='Record locked after bulk approval',
            performed_by=request.user,
        )
        approved_count += 1

    return Response({
        'approved': approved_count,
        'requested': len(record_ids),
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def emission_stats(request):
    """
    Dashboard aggregate statistics — comprehensive breakdown.
    """
    try:
        tenant = request.user.profile.tenant
    except Exception:
        return Response({'error': 'No tenant'}, status=status.HTTP_403_FORBIDDEN)

    qs = EmissionRecord.objects.filter(tenant=tenant)

    # --- Core KPIs ---
    total = qs.count()
    pending = qs.filter(review_status='PENDING').count()
    approved = qs.filter(review_status='APPROVED').count()
    flagged = qs.filter(review_status='FLAGGED').count()
    rejected = qs.filter(review_status='REJECTED').count()
    total_co2e = qs.aggregate(total=Sum('co2e_kg'))['total'] or 0

    # --- By Scope ---
    scope_breakdown = list(
        qs.values('ghg_scope').annotate(
            count=Count('id'),
            total_co2e=Sum('co2e_kg'),
        ).order_by('ghg_scope')
    )

    # --- By Source ---
    source_breakdown = list(
        qs.values('source_type').annotate(
            count=Count('id'),
            total_co2e=Sum('co2e_kg'),
        ).order_by('source_type')
    )

    # --- By Confidence ---
    confidence_breakdown = list(
        qs.values('confidence').annotate(
            count=Count('id'),
        ).order_by('confidence')
    )

    # --- Monthly Emissions Trend (by reporting_period_start) ---
    monthly_trend = list(
        qs.annotate(month=TruncMonth('reporting_period_start'))
        .values('month')
        .annotate(
            total_co2e=Sum('co2e_kg'),
            count=Count('id'),
        )
        .order_by('month')
    )
    # Serialize dates to ISO strings
    for entry in monthly_trend:
        entry['month'] = entry['month'].isoformat() if entry['month'] else None
        entry['total_co2e'] = float(entry['total_co2e'] or 0)

    # --- Monthly Trend by Scope (for stacked area chart) ---
    monthly_by_scope = list(
        qs.annotate(month=TruncMonth('reporting_period_start'))
        .values('month', 'ghg_scope')
        .annotate(total_co2e=Sum('co2e_kg'))
        .order_by('month', 'ghg_scope')
    )
    for entry in monthly_by_scope:
        entry['month'] = entry['month'].isoformat() if entry['month'] else None
        entry['total_co2e'] = float(entry['total_co2e'] or 0)

    # --- By Facility ---
    facility_breakdown = list(
        qs.exclude(facility_name='')
        .values('facility_name', 'country')
        .annotate(
            count=Count('id'),
            total_co2e=Sum('co2e_kg'),
        )
        .order_by('-total_co2e')[:10]
    )
    for entry in facility_breakdown:
        entry['total_co2e'] = float(entry['total_co2e'] or 0)

    # --- By GHG Category (fuel type / travel type) ---
    category_breakdown = list(
        qs.values('ghg_category', 'ghg_scope')
        .annotate(
            count=Count('id'),
            total_co2e=Sum('co2e_kg'),
        )
        .order_by('-total_co2e')
    )
    for entry in category_breakdown:
        entry['total_co2e'] = float(entry['total_co2e'] or 0)

    # --- Top 5 Emitting Records ---
    top_records = list(
        qs.order_by('-co2e_kg')[:5]
        .values(
            'id', 'activity_description', 'co2e_kg',
            'ghg_scope', 'source_type', 'facility_name',
            'activity_quantity', 'activity_unit',
        )
    )
    for entry in top_records:
        entry['co2e_kg'] = float(entry['co2e_kg'] or 0)
        entry['activity_quantity'] = float(entry['activity_quantity'] or 0)
        entry['id'] = str(entry['id'])

    return Response({
        'total_records': total,
        'pending': pending,
        'approved': approved,
        'flagged': flagged,
        'rejected': rejected,
        'total_co2e_kg': float(total_co2e),
        'scope_breakdown': scope_breakdown,
        'source_breakdown': source_breakdown,
        'confidence_breakdown': confidence_breakdown,
        'monthly_trend': monthly_trend,
        'monthly_by_scope': monthly_by_scope,
        'facility_breakdown': facility_breakdown,
        'category_breakdown': category_breakdown,
        'top_records': top_records,
    })

