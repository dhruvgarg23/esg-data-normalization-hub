from django.contrib import admin
from .models import Tenant, UserProfile, PlantLookup, EmissionFactor


@admin.register(Tenant)
class TenantAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'created_at')
    prepopulated_fields = {'slug': ('name',)}


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'tenant', 'role', 'created_at')
    list_filter = ('role', 'tenant')


@admin.register(PlantLookup)
class PlantLookupAdmin(admin.ModelAdmin):
    list_display = ('plant_code', 'plant_name', 'tenant', 'country')
    list_filter = ('tenant',)


@admin.register(EmissionFactor)
class EmissionFactorAdmin(admin.ModelAdmin):
    list_display = ('category', 'factor_value', 'unit_input', 'tenant', 'valid_from')
    list_filter = ('category', 'tenant')
