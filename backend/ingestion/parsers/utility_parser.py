"""
Utility Electricity CSV Parser

Handles portal CSV exports from electricity utility providers.
There is no single standard format — every utility exports differently.
This parser supports a flexible column mapping approach to handle common
variations.

Expected columns (with common aliases):
  - Account_ID / Account / Customer_ID
  - Meter_ID / Meter / Meter_Name / Service_Point_ID
  - Building_Name / Facility / Site
  - Start_Date / Period_Start / Billing_Start / From_Date
  - End_Date / Period_End / Billing_End / To_Date
  - Reading_Date / Read_Date
  - Usage_Quantity / Consumption / kWh_Used / Usage / Total_kWh
  - Usage_Units / Units / UOM
  - Cost / Total_Cost / Amount / Charge
  - Currency
  - Quality / Reading_Type / Status (A=Actual, E=Estimated)
"""
import csv
import io
from datetime import datetime
from decimal import Decimal, InvalidOperation


HEADER_ALIASES = {
    'account_id': 'account_id',
    'account': 'account_id',
    'customer_id': 'account_id',
    'account_number': 'account_id',

    'meter_id': 'meter_id',
    'meter': 'meter_id',
    'meter_name': 'meter_id',
    'service_point_id': 'meter_id',
    'meter_number': 'meter_id',

    'building_name': 'facility',
    'facility': 'facility',
    'site': 'facility',
    'site_name': 'facility',
    'location': 'facility',

    'start_date': 'start_date',
    'period_start': 'start_date',
    'billing_start': 'start_date',
    'from_date': 'start_date',
    'bill_start': 'start_date',

    'end_date': 'end_date',
    'period_end': 'end_date',
    'billing_end': 'end_date',
    'to_date': 'end_date',
    'bill_end': 'end_date',

    'reading_date': 'reading_date',
    'read_date': 'reading_date',

    'usage_quantity': 'usage',
    'consumption': 'usage',
    'kwh_used': 'usage',
    'usage': 'usage',
    'total_kwh': 'usage',
    'usage_kwh': 'usage',
    'energy_kwh': 'usage',

    'usage_units': 'units',
    'units': 'units',
    'uom': 'units',
    'unit': 'units',

    'cost': 'cost',
    'total_cost': 'cost',
    'amount': 'cost',
    'charge': 'cost',
    'total_charge': 'cost',

    'currency': 'currency',

    'quality': 'quality',
    'reading_type': 'quality',
    'status': 'quality',
    'read_type': 'quality',
}


def _normalize_header(header):
    h = header.strip().lower().replace(' ', '_').replace('-', '_')
    return HEADER_ALIASES.get(h, h)


def _parse_date(date_str):
    """Parse common date formats from utility exports."""
    date_str = date_str.strip()
    for fmt in (
        '%Y-%m-%d', '%m/%d/%Y', '%d/%m/%Y',
        '%d-%m-%Y', '%m-%d-%Y',
        '%d.%m.%Y', '%Y/%m/%d',
        '%b %d, %Y', '%d %b %Y',
    ):
        try:
            return datetime.strptime(date_str, fmt).date()
        except ValueError:
            continue
    return None


def parse_utility_csv(file_content):
    """
    Parse a utility electricity CSV export.

    Returns:
        list of dicts with raw_data, parsed fields, and errors.
    """
    results = []
    reader = csv.DictReader(io.StringIO(file_content))

    if reader.fieldnames is None:
        return results

    header_map = {}
    for original_header in reader.fieldnames:
        canonical = _normalize_header(original_header)
        header_map[original_header] = canonical

    for row_num, row in enumerate(reader, start=2):
        errors = []
        raw_data = dict(row)

        normalized = {}
        for orig_key, value in row.items():
            canonical = header_map.get(orig_key, orig_key)
            normalized[canonical] = value.strip() if value else ''

        parsed = {
            'row_number': row_num,
            'account_id': normalized.get('account_id', ''),
            'meter_id': normalized.get('meter_id', ''),
            'facility': normalized.get('facility', ''),
            'currency': normalized.get('currency', ''),
        }

        # Parse dates
        start_str = normalized.get('start_date', '')
        end_str = normalized.get('end_date', '')

        parsed['start_date'] = _parse_date(start_str) if start_str else None
        parsed['end_date'] = _parse_date(end_str) if end_str else None

        if start_str and not parsed['start_date']:
            errors.append(f"Unparseable start date: '{start_str}'")
        if end_str and not parsed['end_date']:
            errors.append(f"Unparseable end date: '{end_str}'")
        if not start_str and not end_str:
            errors.append("No billing period dates found")

        # Validate date range
        if parsed['start_date'] and parsed['end_date']:
            if parsed['start_date'] > parsed['end_date']:
                errors.append("Start date is after end date")

        # Parse usage quantity
        usage_str = normalized.get('usage', '')
        # Handle comma-formatted numbers (e.g., "1,234.56")
        usage_str = usage_str.replace(',', '')
        try:
            parsed['usage'] = Decimal(usage_str)
        except (InvalidOperation, ValueError):
            errors.append(f"Invalid usage quantity: '{normalized.get('usage', '')}'")
            parsed['usage'] = None

        # Parse units — default to kWh if not specified
        raw_unit = normalized.get('units', '').upper().strip()
        if not raw_unit or raw_unit in ('KWH', 'KILOWATT-HOUR', 'KILOWATT HOUR'):
            parsed['units'] = 'kWh'
        elif raw_unit in ('MWH', 'MEGAWATT-HOUR', 'MEGAWATT HOUR'):
            parsed['units'] = 'MWh'
        elif raw_unit in ('GJ', 'GIGAJOULE'):
            parsed['units'] = 'GJ'
        else:
            parsed['units'] = raw_unit
            errors.append(f"Unrecognized unit: '{raw_unit}'")

        # Parse cost
        cost_str = normalized.get('cost', '')
        cost_str = cost_str.replace(',', '').replace('$', '').replace('£', '').replace('€', '')
        try:
            parsed['cost'] = Decimal(cost_str) if cost_str else None
        except (InvalidOperation, ValueError):
            parsed['cost'] = None

        # Quality flag: A=Actual, E=Estimated
        quality = normalized.get('quality', '').upper().strip()
        if quality in ('A', 'ACTUAL'):
            parsed['quality'] = 'ACTUAL'
        elif quality in ('E', 'ESTIMATED', 'EST'):
            parsed['quality'] = 'ESTIMATED'
            errors.append("Reading is estimated, not actual")
        else:
            parsed['quality'] = 'UNKNOWN'

        # Validations
        if not parsed['meter_id']:
            errors.append("Missing meter ID")
        if parsed['usage'] is not None and parsed['usage'] < 0:
            errors.append(f"Negative usage: {parsed['usage']}")

        results.append({
            'raw_data': raw_data,
            'parsed': parsed,
            'errors': errors,
        })

    return results
