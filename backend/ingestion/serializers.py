from rest_framework import serializers
from .models import DataIngestionJob, RawRecord


class DataIngestionJobSerializer(serializers.ModelSerializer):
    source_type_display = serializers.CharField(
        source='get_source_type_display', read_only=True
    )
    status_display = serializers.CharField(
        source='get_status_display', read_only=True
    )

    class Meta:
        model = DataIngestionJob
        fields = [
            'id', 'tenant', 'uploaded_by', 'source_type', 'source_type_display',
            'file_name', 'file_hash', 'status', 'status_display',
            'total_rows', 'success_rows', 'error_rows', 'error_log',
            'created_at', 'completed_at',
        ]
        read_only_fields = [
            'id', 'tenant', 'uploaded_by', 'file_hash', 'status',
            'total_rows', 'success_rows', 'error_rows', 'error_log',
            'created_at', 'completed_at',
        ]


class RawRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = RawRecord
        fields = ['id', 'ingestion_job', 'row_number', 'raw_data', 'parse_errors', 'status']
