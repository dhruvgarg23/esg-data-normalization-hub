from django.contrib import admin
from .models import EmissionRecord


@admin.register(EmissionRecord)
class EmissionRecordAdmin(admin.ModelAdmin):
    list_display = (
        'activity_description', 'ghg_scope', 'source_type',
        'co2e_kg', 'review_status', 'confidence', 'is_locked',
        'created_at',
    )
    list_filter = ('ghg_scope', 'source_type', 'review_status', 'confidence', 'is_locked')
    search_fields = ('activity_description', 'source_identifier')
    readonly_fields = ('id', 'created_at', 'updated_at')
