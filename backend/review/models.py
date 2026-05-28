import uuid
from django.db import models
from django.contrib.auth.models import User
from core.models import Tenant
from emissions.models import EmissionRecord


class AuditLog(models.Model):
    """
    Immutable, append-only log of every action on emission records.
    This table is never updated or deleted — only inserted into.
    Provides the full audit trail for auditors.
    """
    class Action(models.TextChoices):
        CREATED = 'CREATED', 'Record Created'
        UPDATED = 'UPDATED', 'Record Updated'
        APPROVED = 'APPROVED', 'Approved'
        REJECTED = 'REJECTED', 'Rejected'
        FLAGGED = 'FLAGGED', 'Flagged'
        LOCKED = 'LOCKED', 'Locked for Audit'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='audit_logs')
    emission_record = models.ForeignKey(
        EmissionRecord, on_delete=models.CASCADE, related_name='audit_logs'
    )
    action = models.CharField(max_length=10, choices=Action.choices)
    field_changed = models.CharField(max_length=100, blank=True)
    old_value = models.TextField(blank=True)
    new_value = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    performed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    performed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-performed_at']
        indexes = [
            models.Index(fields=['tenant', 'emission_record']),
        ]

    def __str__(self):
        return f"{self.action} on {self.emission_record_id} by {self.performed_by}"
