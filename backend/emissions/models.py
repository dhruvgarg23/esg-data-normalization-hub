import uuid
from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from core.models import Tenant, EmissionFactor
from ingestion.models import DataIngestionJob, RawRecord


class EmissionRecord(models.Model):
    """
    The canonical, normalized emission record. Every row from every source
    (SAP fuel, utility electricity, corporate travel) ends up here after
    parsing and normalization.

    This is the single source of truth for the review dashboard.
    """
    class GHGScope(models.IntegerChoices):
        SCOPE_1 = 1, 'Scope 1 - Direct'
        SCOPE_2 = 2, 'Scope 2 - Indirect Energy'
        SCOPE_3 = 3, 'Scope 3 - Other Indirect'

    class ReviewStatus(models.TextChoices):
        PENDING = 'PENDING', 'Pending Review'
        FLAGGED = 'FLAGGED', 'Flagged for Review'
        APPROVED = 'APPROVED', 'Approved'
        REJECTED = 'REJECTED', 'Rejected'

    class Confidence(models.TextChoices):
        HIGH = 'HIGH', 'High'
        MEDIUM = 'MEDIUM', 'Medium'
        LOW = 'LOW', 'Low'

    # --- Identity ---
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # --- Tenancy ---
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='emission_records')

    # --- Source Tracking ---
    ingestion_job = models.ForeignKey(
        DataIngestionJob, on_delete=models.CASCADE, related_name='emission_records'
    )
    raw_record = models.ForeignKey(
        RawRecord, on_delete=models.SET_NULL, null=True, blank=True, related_name='emission_record'
    )
    source_type = models.CharField(
        max_length=25,
        choices=DataIngestionJob.SourceType.choices,
        help_text="Which source produced this record"
    )
    source_identifier = models.CharField(
        max_length=255, blank=True,
        help_text="Original ID from source: PO number, meter ID, report ID"
    )

    # --- GHG Classification ---
    ghg_scope = models.IntegerField(choices=GHGScope.choices)
    ghg_category = models.CharField(
        max_length=100,
        help_text="e.g. 'Stationary Combustion', 'Purchased Electricity', 'Business Travel'"
    )

    # --- Activity Data (normalized) ---
    activity_description = models.CharField(max_length=500)
    activity_quantity = models.DecimalField(
        max_digits=14, decimal_places=4,
        help_text="Quantity in normalized units"
    )
    activity_unit = models.CharField(
        max_length=30,
        help_text="Normalized unit: L, kWh, passenger-km, room-night"
    )

    # --- Original Data (as received) ---
    original_quantity = models.DecimalField(
        max_digits=14, decimal_places=4,
        help_text="Quantity as originally reported in source"
    )
    original_unit = models.CharField(
        max_length=30,
        help_text="Unit as it appeared in source data"
    )

    # --- Emissions Calculation ---
    emission_factor = models.ForeignKey(
        EmissionFactor, on_delete=models.PROTECT,
        null=True, blank=True,
        help_text="The factor used to compute CO2e"
    )
    co2e_kg = models.DecimalField(
        max_digits=14, decimal_places=4,
        help_text="Computed CO2 equivalent in kilograms"
    )

    # --- Temporal ---
    activity_date = models.DateField(
        null=True, blank=True,
        help_text="Specific date of activity, if known"
    )
    reporting_period_start = models.DateField(
        help_text="Start of the reporting/billing period"
    )
    reporting_period_end = models.DateField(
        help_text="End of the reporting/billing period"
    )

    # --- Location ---
    facility_name = models.CharField(max_length=255, blank=True)
    facility_code = models.CharField(max_length=20, blank=True)
    country = models.CharField(max_length=100, blank=True)
    region = models.CharField(max_length=100, blank=True)

    # --- Review Workflow ---
    review_status = models.CharField(
        max_length=10,
        choices=ReviewStatus.choices,
        default=ReviewStatus.PENDING,
    )
    reviewed_by = models.ForeignKey(
        User, on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='reviewed_records',
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    review_notes = models.TextField(blank=True)

    # --- Audit ---
    is_locked = models.BooleanField(
        default=False,
        help_text="True after approval — record becomes immutable"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        User, on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='created_records',
    )

    # --- Data Quality ---
    confidence = models.CharField(
        max_length=10,
        choices=Confidence.choices,
        default=Confidence.MEDIUM,
    )
    quality_flags = models.JSONField(
        default=list, blank=True,
        help_text='e.g. ["estimated_reading", "unit_converted", "distance_derived"]'
    )

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['tenant', 'review_status']),
            models.Index(fields=['tenant', 'ghg_scope']),
            models.Index(fields=['tenant', 'source_type']),
        ]

    def save(self, *args, **kwargs):
        """Enforce immutability on locked records."""
        if self.pk:
            try:
                existing = EmissionRecord.objects.get(pk=self.pk)
                if existing.is_locked:
                    raise ValidationError(
                        "This record has been approved and locked. "
                        "It cannot be modified."
                    )
            except EmissionRecord.DoesNotExist:
                pass
        super().save(*args, **kwargs)

    def __str__(self):
        return (
            f"[Scope {self.ghg_scope}] {self.activity_description[:50]} "
            f"({self.co2e_kg} kg CO2e) - {self.review_status}"
        )
