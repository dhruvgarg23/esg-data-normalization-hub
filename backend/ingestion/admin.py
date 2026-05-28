from django.contrib import admin
from .models import DataIngestionJob, RawRecord


@admin.register(DataIngestionJob)
class DataIngestionJobAdmin(admin.ModelAdmin):
    list_display = ('file_name', 'source_type', 'status', 'total_rows', 'success_rows', 'error_rows', 'created_at')
    list_filter = ('source_type', 'status')


@admin.register(RawRecord)
class RawRecordAdmin(admin.ModelAdmin):
    list_display = ('row_number', 'ingestion_job', 'status')
    list_filter = ('status',)
