"""
Normalization Engine

Converts parsed data from each source into normalized EmissionRecord entries.
Handles:
  - Unit conversion (GAL→L, MWh→kWh, miles→km, etc.)
  - Emission factor lookup and CO2e calculation
  - Confidence scoring based on data quality
"""
from decimal import Decimal
from core.models import EmissionFactor


# --- Unit Conversion Registry ---
# (from_unit, to_unit) -> conversion factor
# Multiply the value by the factor to convert.
UNIT_CONVERSIONS = {
    # Volume
    ('GAL', 'L'): Decimal('3.78541'),
    ('GALLON', 'L'): Decimal('3.78541'),
    ('GALLONS', 'L'): Decimal('3.78541'),
    ('M3', 'L'): Decimal('1000'),
    ('M³', 'L'): Decimal('1000'),

    # Energy
    ('MWH', 'kWh'): Decimal('1000'),
    ('GJ', 'kWh'): Decimal('277.778'),

    # Distance
    ('MI', 'km'): Decimal('1.60934'),
    ('MILES', 'km'): Decimal('1.60934'),
    ('MILE', 'km'): Decimal('1.60934'),
    ('NM', 'km'): Decimal('1.852'),     # Nautical miles

    # Mass (for fuels sometimes reported in kg/tonnes)
    ('KG', 'L'): Decimal('1.19'),       # Approximate for diesel (density ~0.84 kg/L → 1 kg = 1.19 L)
    ('T', 'L'): Decimal('1190'),
    ('TONNE', 'L'): Decimal('1190'),
    ('TONNES', 'L'): Decimal('1190'),

    # Identity conversions
    ('L', 'L'): Decimal('1'),
    ('LITER', 'L'): Decimal('1'),
    ('LITERS', 'L'): Decimal('1'),
    ('LITRE', 'L'): Decimal('1'),
    ('LITRES', 'L'): Decimal('1'),
    ('KWH', 'kWh'): Decimal('1'),
    ('KM', 'km'): Decimal('1'),
}


def convert_unit(value, from_unit, to_unit):
    """
    Convert a value from one unit to another.

    Returns:
        (converted_value, was_converted) tuple.
        was_converted is True if a conversion was applied.
    """
    from_upper = from_unit.upper().strip()
    to_upper = to_unit.upper().strip()

    if from_upper == to_upper:
        return value, False

    key = (from_upper, to_unit)
    if key in UNIT_CONVERSIONS:
        return value * UNIT_CONVERSIONS[key], True

    # Try uppercase target too
    key = (from_upper, to_upper)
    if key in UNIT_CONVERSIONS:
        return value * UNIT_CONVERSIONS[key], True

    return value, False


def get_emission_factor(tenant, category, date=None):
    """
    Look up the appropriate emission factor.
    Tenant-specific overrides take precedence over system defaults.
    If date is provided, filter by validity period.
    """
    from django.db.models import Q

    qs = EmissionFactor.objects.filter(category=category)

    if date:
        qs = qs.filter(
            Q(valid_from__lte=date) &
            (Q(valid_to__gte=date) | Q(valid_to__isnull=True))
        )

    # Prefer tenant-specific, fall back to system default
    tenant_factor = qs.filter(tenant=tenant).first()
    if tenant_factor:
        return tenant_factor

    return qs.filter(tenant__isnull=True).first()


def compute_confidence(errors, quality_flags, has_all_fields=True):
    """
    Score data quality confidence.
    - HIGH: No errors, no flags, all fields present, actual readings
    - MEDIUM: Minor flags (unit conversion, derived values)
    - LOW: Errors present, estimated readings, missing critical data
    """
    if errors:
        return 'LOW'
    if not has_all_fields:
        return 'LOW'

    problematic_flags = {'estimated_reading', 'room_nights_assumed', 'distance_unknown'}
    if problematic_flags.intersection(set(quality_flags)):
        return 'LOW'

    minor_flags = {'unit_converted', 'distance_derived'}
    if minor_flags.intersection(set(quality_flags)):
        return 'MEDIUM'

    return 'HIGH'


def normalize_sap_record(parsed, tenant):
    """
    Normalize a parsed SAP fuel record into EmissionRecord fields.

    Args:
        parsed: dict from sap_parser with keys like quantity, unit, fuel_type, etc.
        tenant: Tenant instance

    Returns:
        dict of EmissionRecord field values, or None if normalization failed.
    """
    if parsed.get('quantity') is None or parsed.get('fuel_type') is None:
        return None

    quantity = parsed['quantity']
    original_unit = parsed['unit']
    fuel_type = parsed['fuel_type']

    # Determine target unit based on fuel type
    if fuel_type == 'FUEL_NATURAL_GAS':
        target_unit = 'M3' if original_unit.upper() in ('M3', 'M³') else 'L'
    else:
        target_unit = 'L'

    # Convert to normalized unit
    quality_flags = []
    converted_qty, was_converted = convert_unit(quantity, original_unit, target_unit)
    if was_converted:
        quality_flags.append('unit_converted')

    # Look up emission factor
    ef = get_emission_factor(tenant, fuel_type, parsed.get('document_date'))
    if ef is None:
        return None

    co2e_kg = converted_qty * ef.factor_value

    return {
        'source_type': 'SAP_FUEL',
        'source_identifier': parsed.get('po_number', ''),
        'ghg_scope': 1,  # Direct combustion = Scope 1
        'ghg_category': 'Stationary Combustion',
        'activity_description': f"{parsed.get('description', 'Fuel')} - PO {parsed.get('po_number', '')}",
        'activity_quantity': converted_qty,
        'activity_unit': target_unit if target_unit != 'L' else 'L',
        'original_quantity': quantity,
        'original_unit': original_unit,
        'emission_factor': ef,
        'co2e_kg': co2e_kg,
        'activity_date': parsed.get('document_date'),
        'reporting_period_start': parsed.get('document_date'),
        'reporting_period_end': parsed.get('document_date'),
        'facility_code': parsed.get('plant', ''),
        'quality_flags': quality_flags,
    }


def normalize_utility_record(parsed, tenant):
    """
    Normalize a parsed utility electricity record.
    """
    if parsed.get('usage') is None:
        return None

    quantity = parsed['usage']
    original_unit = parsed['units']
    target_unit = 'kWh'

    quality_flags = []
    converted_qty, was_converted = convert_unit(quantity, original_unit, target_unit)
    if was_converted:
        quality_flags.append('unit_converted')

    if parsed.get('quality') == 'ESTIMATED':
        quality_flags.append('estimated_reading')

    ef = get_emission_factor(tenant, 'ELECTRICITY_GRID', parsed.get('start_date'))
    if ef is None:
        return None

    co2e_kg = converted_qty * ef.factor_value

    return {
        'source_type': 'UTILITY_ELECTRICITY',
        'source_identifier': parsed.get('meter_id', ''),
        'ghg_scope': 2,  # Purchased electricity = Scope 2
        'ghg_category': 'Purchased Electricity',
        'activity_description': f"Electricity - Meter {parsed.get('meter_id', '')}",
        'activity_quantity': converted_qty,
        'activity_unit': target_unit,
        'original_quantity': quantity,
        'original_unit': original_unit,
        'emission_factor': ef,
        'co2e_kg': co2e_kg,
        'activity_date': parsed.get('end_date'),
        'reporting_period_start': parsed.get('start_date'),
        'reporting_period_end': parsed.get('end_date'),
        'facility_name': parsed.get('facility', ''),
        'quality_flags': quality_flags,
    }


def normalize_travel_record(parsed, tenant):
    """
    Normalize a parsed corporate travel record.
    Different travel types use different emission factors and activity units.
    """
    travel_category = parsed.get('travel_category')
    if travel_category is None:
        return None

    quality_flags = list(parsed.get('quality_flags', []))

    if travel_category == 'FLIGHT':
        distance = parsed.get('distance_km')
        if distance is None:
            # Fallback: use a default average flight distance
            distance = Decimal('1500')
            quality_flags.append('distance_unknown')

        haul_type = parsed.get('haul_type', 'FLIGHT_SHORT_HAUL')
        ef = get_emission_factor(tenant, haul_type, parsed.get('date'))
        if ef is None:
            return None

        activity_qty = Decimal(str(distance))
        co2e_kg = activity_qty * ef.factor_value

        return {
            'source_type': 'TRAVEL',
            'source_identifier': parsed.get('report_id', ''),
            'ghg_scope': 3,
            'ghg_category': 'Business Travel',
            'activity_description': (
                f"Flight {parsed.get('origin', '?')} → {parsed.get('destination', '?')} "
                f"({parsed.get('employee', '')})"
            ),
            'activity_quantity': activity_qty,
            'activity_unit': 'passenger-km',
            'original_quantity': activity_qty,
            'original_unit': 'km (derived)' if 'distance_derived' in quality_flags else 'km',
            'emission_factor': ef,
            'co2e_kg': co2e_kg,
            'activity_date': parsed.get('date'),
            'reporting_period_start': parsed.get('date'),
            'reporting_period_end': parsed.get('date'),
            'quality_flags': quality_flags,
        }

    elif travel_category == 'HOTEL':
        room_nights = Decimal(str(parsed.get('room_nights', 1)))
        ef = get_emission_factor(tenant, 'HOTEL', parsed.get('date'))
        if ef is None:
            return None

        co2e_kg = room_nights * ef.factor_value

        return {
            'source_type': 'TRAVEL',
            'source_identifier': parsed.get('report_id', ''),
            'ghg_scope': 3,
            'ghg_category': 'Business Travel',
            'activity_description': (
                f"Hotel stay at {parsed.get('vendor', 'Unknown')} "
                f"({parsed.get('employee', '')})"
            ),
            'activity_quantity': room_nights,
            'activity_unit': 'room-night',
            'original_quantity': room_nights,
            'original_unit': 'room-night',
            'emission_factor': ef,
            'co2e_kg': co2e_kg,
            'activity_date': parsed.get('checkin') or parsed.get('date'),
            'reporting_period_start': parsed.get('checkin') or parsed.get('date'),
            'reporting_period_end': parsed.get('checkout') or parsed.get('date'),
            'quality_flags': quality_flags,
        }

    elif travel_category in ('TAXI', 'CAR_RENTAL', 'RAIL'):
        # For ground transport without distance, we use spend-based estimation
        # This is a recognized GHG Protocol method
        amount = parsed.get('amount')
        if amount is None:
            return None

        ef_category = travel_category
        ef = get_emission_factor(tenant, ef_category, parsed.get('date'))
        if ef is None:
            return None

        # For taxis/car rentals, use a spend-based factor (kg CO2e per currency unit)
        co2e_kg = amount * ef.factor_value
        quality_flags.append('spend_based_estimate')

        return {
            'source_type': 'TRAVEL',
            'source_identifier': parsed.get('report_id', ''),
            'ghg_scope': 3,
            'ghg_category': 'Business Travel',
            'activity_description': (
                f"{travel_category.replace('_', ' ').title()} - "
                f"{parsed.get('vendor', 'Unknown')} ({parsed.get('employee', '')})"
            ),
            'activity_quantity': amount,
            'activity_unit': parsed.get('currency', 'USD'),
            'original_quantity': amount,
            'original_unit': parsed.get('currency', 'USD'),
            'emission_factor': ef,
            'co2e_kg': co2e_kg,
            'activity_date': parsed.get('date'),
            'reporting_period_start': parsed.get('date'),
            'reporting_period_end': parsed.get('date'),
            'quality_flags': quality_flags,
        }

    return None
