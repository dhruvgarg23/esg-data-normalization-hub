from rest_framework import serializers
from .models import AuditLog


class AuditLogSerializer(serializers.ModelSerializer):
    action_display = serializers.CharField(source='get_action_display', read_only=True)
    performed_by_name = serializers.CharField(
        source='performed_by.username', read_only=True, default=None
    )

    class Meta:
        model = AuditLog
        fields = [
            'id', 'tenant', 'emission_record', 'action', 'action_display',
            'field_changed', 'old_value', 'new_value', 'notes',
            'performed_by', 'performed_by_name', 'performed_at',
        ]
