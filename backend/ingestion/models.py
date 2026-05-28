import uuid
from django.db import models
from django.contrib.auth.models import User
from core.models import Tenant


class DataIngestionJob(models.Model):
    """
    Tracks each file upload / data ingestion attempt.
    One job = one file from one source type.
    """
    class SourceType(models.TextChoices):
        SAP_FUEL = 'SAP_FUEL', 'SAP Fuel & Procurement'
        UTILITY_ELECTRICITY = 'UTILITY_ELECTRICITY', 'Utility Electricity'
        TRAVEL = 'TRAVEL', 'Corporate Travel'

    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        PROCESSING = 'PROCESSING', 'Processing'
        COMPLETED = 'COMPLETED', 'Completed'
        FAILED = 'FAILED', 'Failed'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='ingestion_jobs')
    uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    source_type = models.CharField(max_length=25, choices=SourceType.choices)
    file_name = models.CharField(max_length=255)
    file_hash = models.CharField(
        max_length=64, blank=True,
        help_text="SHA-256 hash for duplicate detection"
    )
    status = models.CharField(max_length=15, choices=Status.choices, default=Status.PENDING)
    total_rows = models.IntegerField(default=0)
    success_rows = models.IntegerField(default=0)
    error_rows = models.IntegerField(default=0)
    error_log = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"[{self.get_source_type_display()}] {self.file_name} ({self.status})"


class RawRecord(models.Model):
    """
    Stores the original parsed data from a source file before normalization.
    Preserves the exact input for audit trail and re-processing.
    """
    class Status(models.TextChoices):
        PARSED = 'PARSED', 'Parsed'
        FAILED = 'FAILED', 'Failed'
        NORMALIZED = 'NORMALIZED', 'Normalized'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ingestion_job = models.ForeignKey(
        DataIngestionJob, on_delete=models.CASCADE, related_name='raw_records'
    )
    row_number = models.IntegerField()
    raw_data = models.JSONField(
        help_text="The original row data as key-value pairs"
    )
    parse_errors = models.JSONField(
        default=list, blank=True,
        help_text="List of parsing issues for this row"
    )
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.PARSED)

    class Meta:
        ordering = ['row_number']

    def __str__(self):
        return f"Row {self.row_number} of {self.ingestion_job.file_name}"
