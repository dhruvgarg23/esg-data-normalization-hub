from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from .models import AuditLog
from .serializers import AuditLogSerializer


class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = AuditLogSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        tenant = getattr(getattr(self.request.user, 'profile', None), 'tenant', None)
        if not tenant:
            return AuditLog.objects.none()

        qs = AuditLog.objects.filter(tenant=tenant)

        # Filter by emission record
        record_id = self.request.query_params.get('record_id')
        if record_id:
            qs = qs.filter(emission_record_id=record_id)

        return qs
