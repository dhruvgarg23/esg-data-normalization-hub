from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Tenant, UserProfile, EmissionFactor, PlantLookup


class TenantSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tenant
        fields = ['id', 'name', 'slug', 'created_at']


class UserProfileSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)
    email = serializers.CharField(source='user.email', read_only=True)

    class Meta:
        model = UserProfile
        fields = ['username', 'email', 'tenant', 'role', 'created_at']


class RegisterSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150)
    password = serializers.CharField(write_only=True, min_length=8)
    email = serializers.EmailField()
    tenant_id = serializers.UUIDField()
    role = serializers.ChoiceField(choices=UserProfile.Role.choices, default='ANALYST')

    def validate_username(self, value):
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("Username already exists.")
        return value

    def create(self, validated_data):
        tenant = Tenant.objects.get(id=validated_data['tenant_id'])
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=validated_data['password'],
        )
        UserProfile.objects.create(
            user=user,
            tenant=tenant,
            role=validated_data['role'],
        )
        return user


class EmissionFactorSerializer(serializers.ModelSerializer):
    category_display = serializers.CharField(source='get_category_display', read_only=True)

    class Meta:
        model = EmissionFactor
        fields = [
            'id', 'tenant', 'category', 'category_display',
            'unit_input', 'unit_output', 'factor_value',
            'source_reference', 'valid_from', 'valid_to',
        ]


class PlantLookupSerializer(serializers.ModelSerializer):
    class Meta:
        model = PlantLookup
        fields = ['id', 'tenant', 'plant_code', 'plant_name', 'country', 'region']
