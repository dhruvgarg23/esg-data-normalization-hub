"""
Seed the database with a demo tenant, users, emission factors,
and plant lookups. Run this after migrations.

Usage: python manage.py seed_data
"""
from datetime import date
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from core.models import Tenant, UserProfile, EmissionFactor, PlantLookup


class Command(BaseCommand):
    help = 'Seed database with demo tenant, users, and emission factors'

    def handle(self, *args, **options):
        self.stdout.write('Seeding database...')

        # --- Tenant ---
        tenant, created = Tenant.objects.get_or_create(
            slug='acme-corp',
            defaults={'name': 'ACME Corporation'},
        )
        self.stdout.write(f'  Tenant: {tenant.name} ({"created" if created else "exists"})')

        # --- Users ---
        for username, role, email in [
            ('admin', 'ADMIN', 'admin@acme.com'),
            ('analyst', 'ANALYST', 'analyst@acme.com'),
        ]:
            user, user_created = User.objects.get_or_create(
                username=username,
                defaults={'email': email},
            )
            if user_created:
                user.set_password('password123')
                user.save()

            profile, _ = UserProfile.objects.get_or_create(
                user=user,
                defaults={'tenant': tenant, 'role': role},
            )
            self.stdout.write(f'  User: {username}/{role} ({"created" if user_created else "exists"})')

        # --- Plant Lookups ---
        # These map SAP plant codes to real facilities.
        # In production, the client provides this mapping.
        plants = [
            ('PL01', 'Munich Manufacturing Plant', 'Germany', 'Bavaria'),
            ('PL02', 'Frankfurt Distribution Center', 'Germany', 'Hesse'),
            ('PL03', 'Hamburg Port Facility', 'Germany', 'Hamburg'),
        ]
        for code, name, country, region in plants:
            PlantLookup.objects.get_or_create(
                tenant=tenant,
                plant_code=code,
                defaults={
                    'plant_name': name,
                    'country': country,
                    'region': region,
                },
            )
        self.stdout.write(f'  Plant lookups: {len(plants)} plants')

        # --- Emission Factors (UK DESNZ 2024) ---
        # These are system-wide defaults (tenant=NULL).
        # Source: UK Government GHG Conversion Factors 2024
        factors = [
            # Fuel - Scope 1
            ('FUEL_DIESEL', 'L', Decimal('2.70480'), 'UK DESNZ 2024 - Fuels: Diesel (average biofuel blend)'),
            ('FUEL_PETROL', 'L', Decimal('2.31440'), 'UK DESNZ 2024 - Fuels: Petrol (average biofuel blend)'),
            ('FUEL_NATURAL_GAS', 'kWh', Decimal('0.18254'), 'UK DESNZ 2024 - Fuels: Natural Gas'),
            ('FUEL_LPG', 'L', Decimal('1.55370'), 'UK DESNZ 2024 - Fuels: LPG'),

            # Electricity - Scope 2
            ('ELECTRICITY_GRID', 'kWh', Decimal('0.22535'), 'UK DESNZ 2024 - UK Electricity (generation + T&D)'),

            # Travel - Scope 3
            ('FLIGHT_DOMESTIC', 'passenger-km', Decimal('0.24587'), 'UK DESNZ 2024 - Flights: Domestic, average'),
            ('FLIGHT_SHORT_HAUL', 'passenger-km', Decimal('0.15102'), 'UK DESNZ 2024 - Flights: Short-haul, average'),
            ('FLIGHT_LONG_HAUL', 'passenger-km', Decimal('0.10312'), 'UK DESNZ 2024 - Flights: Long-haul, average'),
            ('HOTEL', 'room-night', Decimal('20.60000'), 'UK DESNZ 2024 - Hotel stay, average'),

            # Ground transport - spend-based (kg CO2e per £)
            ('CAR_RENTAL', 'GBP', Decimal('0.12000'), 'UK DESNZ 2024 - Car rental, spend-based estimate'),
            ('TAXI', 'GBP', Decimal('0.14930'), 'UK DESNZ 2024 - Taxi, spend-based estimate'),
            ('RAIL', 'passenger-km', Decimal('0.03549'), 'UK DESNZ 2024 - National rail, average'),
        ]

        for category, unit_input, factor_value, source_ref in factors:
            EmissionFactor.objects.get_or_create(
                tenant=None,
                category=category,
                defaults={
                    'unit_input': unit_input,
                    'unit_output': 'kg_co2e',
                    'factor_value': factor_value,
                    'source_reference': source_ref,
                    'valid_from': date(2024, 1, 1),
                    'valid_to': date(2024, 12, 31),
                },
            )
        self.stdout.write(f'  Emission factors: {len(factors)} factors')

        self.stdout.write(self.style.SUCCESS('Seeding complete!'))
        self.stdout.write('')
        self.stdout.write('  Login credentials:')
        self.stdout.write('    admin / password123 (Admin role)')
        self.stdout.write('    analyst / password123 (Analyst role)')
