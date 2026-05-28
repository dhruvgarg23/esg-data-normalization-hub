from django.contrib import admin
from .models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('action', 'emission_record', 'performed_by', 'performed_at')
    list_filter = ('action',)
    readonly_fields = (
        'id', 'tenant', 'emission_record', 'action',
        'field_changed', 'old_value', 'new_value', 'notes',
        'performed_by', 'performed_at',
    )
