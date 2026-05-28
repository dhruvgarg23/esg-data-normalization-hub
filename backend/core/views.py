from rest_framework import viewsets, status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from .models import Tenant, UserProfile, EmissionFactor, PlantLookup
from .serializers import (
    TenantSerializer, UserProfileSerializer, RegisterSerializer,
    EmissionFactorSerializer, PlantLookupSerializer,
)


class TenantViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Tenant.objects.all()
    serializer_class = TenantSerializer


@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def register_user(request):
    """Register a new user. In production this would be admin-only."""
    serializer = RegisterSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    user = serializer.save()
    return Response(
        {'message': f'User {user.username} created successfully.'},
        status=status.HTTP_201_CREATED,
    )


@api_view(['GET'])
def current_user(request):
    """Return the current user's profile info."""
    try:
        profile = request.user.profile
    except UserProfile.DoesNotExist:
        return Response({'error': 'No profile found'}, status=404)
    return Response(UserProfileSerializer(profile).data)


class EmissionFactorViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = EmissionFactorSerializer

    def get_queryset(self):
        """Return system defaults + tenant-specific factors."""
        tenant = getattr(getattr(self.request.user, 'profile', None), 'tenant', None)
        if tenant:
            return EmissionFactor.objects.filter(
                models.Q(tenant=tenant) | models.Q(tenant__isnull=True)
            )
        return EmissionFactor.objects.filter(tenant__isnull=True)


class PlantLookupViewSet(viewsets.ModelViewSet):
    serializer_class = PlantLookupSerializer

    def get_queryset(self):
        tenant = getattr(getattr(self.request.user, 'profile', None), 'tenant', None)
        if tenant:
            return PlantLookup.objects.filter(tenant=tenant)
        return PlantLookup.objects.none()


# Need to import models for Q
from django.db import models
