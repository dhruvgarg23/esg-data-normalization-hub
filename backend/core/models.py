import uuid
from django.db import models
from django.contrib.auth.models import User


class Tenant(models.Model):
    """
    Represents a client organization. All data is scoped to a tenant
    for row-level multi-tenancy isolation.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True, max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class UserProfile(models.Model):
    """
    Extends Django User with tenant association and role.
    """
    class Role(models.TextChoices):
        ADMIN = 'ADMIN', 'Admin'
        ANALYST = 'ANALYST', 'Analyst'

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='users')
    role = models.CharField(max_length=10, choices=Role.choices, default=Role.ANALYST)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} ({self.role}) @ {self.tenant.name}"


class PlantLookup(models.Model):
    """
    Maps opaque SAP plant codes to meaningful facility information.
    Each tenant maintains their own plant registry since codes are
    client-specific.
    """
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='plants')
    plant_code = models.CharField(max_length=10)
    plant_name = models.CharField(max_length=255)
    country = models.CharField(max_length=100, blank=True)
    region = models.CharField(max_length=100, blank=True)

    class Meta:
        unique_together = ('tenant', 'plant_code')

    def __str__(self):
        return f"{self.plant_code} - {self.plant_name}"


class EmissionFactor(models.Model):
    """
    Stores emission conversion factors. System-level defaults have
    tenant=NULL; tenant-specific overrides take precedence.

    Based on UK DESNZ 2024 Government GHG Conversion Factors.
    """
    class Category(models.TextChoices):
        FUEL_DIESEL = 'FUEL_DIESEL', 'Diesel'
        FUEL_PETROL = 'FUEL_PETROL', 'Petrol/Gasoline'
        FUEL_NATURAL_GAS = 'FUEL_NATURAL_GAS', 'Natural Gas'
        FUEL_LPG = 'FUEL_LPG', 'LPG'
        ELECTRICITY_GRID = 'ELECTRICITY_GRID', 'Grid Electricity'
        FLIGHT_DOMESTIC = 'FLIGHT_DOMESTIC', 'Domestic Flight'
        FLIGHT_SHORT_HAUL = 'FLIGHT_SHORT_HAUL', 'Short-Haul Flight'
        FLIGHT_LONG_HAUL = 'FLIGHT_LONG_HAUL', 'Long-Haul Flight'
        HOTEL = 'HOTEL', 'Hotel Stay'
        CAR_RENTAL = 'CAR_RENTAL', 'Car Rental'
        RAIL = 'RAIL', 'Rail Travel'
        TAXI = 'TAXI', 'Taxi'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        Tenant, on_delete=models.CASCADE, related_name='emission_factors',
        null=True, blank=True,
        help_text="NULL = system default; set tenant for client-specific overrides"
    )
    category = models.CharField(max_length=30, choices=Category.choices)
    unit_input = models.CharField(
        max_length=20,
        help_text="Input unit, e.g. 'L', 'kWh', 'passenger-km', 'room-night'"
    )
    unit_output = models.CharField(max_length=20, default='kg_co2e')
    factor_value = models.DecimalField(
        max_digits=12, decimal_places=6,
        help_text="kg CO2e per unit of input"
    )
    source_reference = models.CharField(
        max_length=255,
        help_text="e.g. 'UK DESNZ 2024 - Table: Fuels'"
    )
    valid_from = models.DateField()
    valid_to = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ['category', '-valid_from']

    def __str__(self):
        scope = "System" if self.tenant is None else self.tenant.name
        return f"[{scope}] {self.get_category_display()}: {self.factor_value} {self.unit_output}/{self.unit_input}"
