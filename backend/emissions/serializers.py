from rest_framework import serializers
from .models import EmissionRecord


class EmissionRecordListSerializer(serializers.ModelSerializer):
    """Compact serializer for list views."""
    source_type_display = serializers.CharField(
        source='get_source_type_display', read_only=True
    )
    review_status_display = serializers.CharField(
        source='get_review_status_display', read_only=True
    )
    scope_display = serializers.CharField(
        source='get_ghg_scope_display', read_only=True
    )
    reviewed_by_name = serializers.CharField(
        source='reviewed_by.username', read_only=True, default=None
    )

    class Meta:
        model = EmissionRecord
        fields = [
            'id', 'source_type', 'source_type_display',
            'source_identifier', 'ghg_scope', 'scope_display',
            'ghg_category', 'activity_description',
            'activity_quantity', 'activity_unit',
            'co2e_kg', 'activity_date',
            'reporting_period_start', 'reporting_period_end',
            'facility_name', 'country',
            'review_status', 'review_status_display',
            'is_locked', 'confidence',
            'quality_flags', 'created_at',
            'reviewed_by_name', 'reviewed_at',
        ]


class EmissionRecordDetailSerializer(serializers.ModelSerializer):
    """Full serializer with raw data for detail views."""
    source_type_display = serializers.CharField(
        source='get_source_type_display', read_only=True
    )
    review_status_display = serializers.CharField(
        source='get_review_status_display', read_only=True
    )
    scope_display = serializers.CharField(
        source='get_ghg_scope_display', read_only=True
    )
    raw_data = serializers.SerializerMethodField()
    emission_factor_display = serializers.SerializerMethodField()
    reviewed_by_name = serializers.CharField(
        source='reviewed_by.username', read_only=True, default=None
    )
    created_by_name = serializers.CharField(
        source='created_by.username', read_only=True, default=None
    )

    class Meta:
        model = EmissionRecord
        fields = '__all__'

    def get_raw_data(self, obj):
        if obj.raw_record:
            return obj.raw_record.raw_data
        return None

    def get_emission_factor_display(self, obj):
        if obj.emission_factor:
            return {
                'category': obj.emission_factor.get_category_display(),
                'value': str(obj.emission_factor.factor_value),
                'unit': f"{obj.emission_factor.unit_output}/{obj.emission_factor.unit_input}",
                'source': obj.emission_factor.source_reference,
            }
        return None
