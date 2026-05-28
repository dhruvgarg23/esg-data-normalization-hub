"""
SAP Fuel & Procurement CSV Parser

Handles ALV flat-file CSV exports from SAP transactions like ME2M/ME2N.
Supports both English and German column headers (common in SAP configurations
where the system language is German but exports go to international teams).

Expected columns (with German aliases):
  - PO_Number / Bestellnummer
  - Item / Position
  - Material / Materialnummer
  - Description / Bezeichnung / Kurztext
  - Plant / Werk
  - Quantity / Menge
  - Unit / Mengeneinheit / ME
  - Net_Price / Nettopreis
  - Currency / Währung
  - Document_Date / Belegdatum
  - Vendor / Lieferant
"""
import csv
import io
from datetime import datetime
from decimal import Decimal, InvalidOperation


# Maps German SAP column headers to our normalized English names.
# Real SAP exports use these exact German terms when the system language is DE.
HEADER_ALIASES = {
    # English -> canonical
    'po_number': 'po_number',
    'purchase_order': 'po_number',
    'ebeln': 'po_number',
    # German
    'bestellnummer': 'po_number',
    'einkaufsbelegnummer': 'po_number',

    'item': 'item',
    'position': 'item',
    'ebelp': 'item',
    'pos.': 'item',

    'material': 'material',
    'materialnummer': 'material',
    'matnr': 'material',

    'description': 'description',
    'bezeichnung': 'description',
    'kurztext': 'description',
    'material_description': 'description',
    'maktx': 'description',

    'plant': 'plant',
    'werk': 'plant',
    'werks': 'plant',

    'quantity': 'quantity',
    'menge': 'quantity',
    'order_quantity': 'quantity',
    'bestellmenge': 'quantity',

    'unit': 'unit',
    'mengeneinheit': 'unit',
    'me': 'unit',
    'meins': 'unit',
    'uom': 'unit',

    'net_price': 'net_price',
    'nettopreis': 'net_price',
    'price': 'net_price',

    'currency': 'currency',
    'währung': 'currency',
    'waehrung': 'currency',
    'waers': 'currency',

    'document_date': 'document_date',
    'belegdatum': 'document_date',
    'doc_date': 'document_date',
    'date': 'document_date',

    'vendor': 'vendor',
    'lieferant': 'vendor',
    'supplier': 'vendor',
    'vendor_name': 'vendor',
    'lifnr': 'vendor',
}

# Material code to fuel type classification.
# In production, this would come from a configurable mapping table.
MATERIAL_FUEL_MAP = {
    'fuel-dsl': 'FUEL_DIESEL',
    'diesel': 'FUEL_DIESEL',
    'dsl': 'FUEL_DIESEL',
    'fuel-gas': 'FUEL_PETROL',
    'petrol': 'FUEL_PETROL',
    'gasoline': 'FUEL_PETROL',
    'benzin': 'FUEL_PETROL',
    'fuel-ng': 'FUEL_NATURAL_GAS',
    'natural gas': 'FUEL_NATURAL_GAS',
    'erdgas': 'FUEL_NATURAL_GAS',
    'fuel-lpg': 'FUEL_LPG',
    'lpg': 'FUEL_LPG',
    'flüssiggas': 'FUEL_LPG',
}


def _normalize_header(header):
    """Lowercase, strip whitespace and special chars from header name."""
    h = header.strip().lower().replace(' ', '_').replace('.', '')
    return HEADER_ALIASES.get(h, h)


def _parse_sap_date(date_str):
    """
    Parse SAP date formats. SAP commonly uses:
    - DD.MM.YYYY (German locale)
    - YYYY-MM-DD (ISO, some configs)
    - MM/DD/YYYY (US locale)
    """
    date_str = date_str.strip()
    for fmt in ('%d.%m.%Y', '%Y-%m-%d', '%m/%d/%Y', '%d/%m/%Y'):
        try:
            return datetime.strptime(date_str, fmt).date()
        except ValueError:
            continue
    return None


def _classify_fuel(material_code, description):
    """
    Determine fuel type from material code and/or description.
    Returns the EmissionFactor category or None if unclassifiable.
    """
    search_str = f"{material_code} {description}".lower()
    for key, fuel_type in MATERIAL_FUEL_MAP.items():
        if key in search_str:
            return fuel_type
    return None


def parse_sap_csv(file_content):
    """
    Parse an SAP fuel/procurement CSV export.

    Args:
        file_content: String content of the CSV file.

    Returns:
        list of dicts, each with:
            - raw_data: the original row as dict
            - parsed: normalized parsed fields
            - errors: list of parsing issues
    """
    results = []

    # Detect delimiter (SAP exports use ; in some locales)
    sample = file_content[:2000]
    delimiter = ';' if sample.count(';') > sample.count(',') else ','

    reader = csv.DictReader(io.StringIO(file_content), delimiter=delimiter)

    # Normalize headers
    if reader.fieldnames is None:
        return results

    header_map = {}
    for original_header in reader.fieldnames:
        canonical = _normalize_header(original_header)
        header_map[original_header] = canonical

    for row_num, row in enumerate(reader, start=2):  # 2 because row 1 is header
        errors = []
        raw_data = dict(row)

        # Re-key the row with canonical names
        normalized_row = {}
        for orig_key, value in row.items():
            canonical_key = header_map.get(orig_key, orig_key)
            normalized_row[canonical_key] = value.strip() if value else ''

        parsed = {
            'row_number': row_num,
            'po_number': normalized_row.get('po_number', ''),
            'item': normalized_row.get('item', ''),
            'material': normalized_row.get('material', ''),
            'description': normalized_row.get('description', ''),
            'plant': normalized_row.get('plant', ''),
            'vendor': normalized_row.get('vendor', ''),
            'currency': normalized_row.get('currency', ''),
        }

        # Parse quantity
        qty_str = normalized_row.get('quantity', '')
        # SAP sometimes uses comma as decimal separator (German locale)
        qty_str = qty_str.replace('.', '').replace(',', '.') if ',' in qty_str else qty_str
        try:
            parsed['quantity'] = Decimal(qty_str)
        except (InvalidOperation, ValueError):
            errors.append(f"Invalid quantity: '{normalized_row.get('quantity', '')}'")
            parsed['quantity'] = None

        # Parse unit
        parsed['unit'] = normalized_row.get('unit', '').upper()
        if not parsed['unit']:
            errors.append("Missing unit of measure")

        # Parse date
        date_str = normalized_row.get('document_date', '')
        parsed['document_date'] = _parse_sap_date(date_str) if date_str else None
        if not parsed['document_date'] and date_str:
            errors.append(f"Unparseable date: '{date_str}'")

        # Parse price
        price_str = normalized_row.get('net_price', '')
        price_str = price_str.replace('.', '').replace(',', '.') if ',' in price_str else price_str
        try:
            parsed['net_price'] = Decimal(price_str) if price_str else None
        except (InvalidOperation, ValueError):
            parsed['net_price'] = None

        # Classify fuel type
        fuel_type = _classify_fuel(
            parsed.get('material', ''),
            parsed.get('description', ''),
        )
        parsed['fuel_type'] = fuel_type
        if fuel_type is None:
            errors.append(
                f"Could not classify fuel type from material "
                f"'{parsed['material']}' / description '{parsed['description']}'"
            )

        # Validation
        if not parsed['po_number']:
            errors.append("Missing PO number")
        if parsed['quantity'] is not None and parsed['quantity'] <= 0:
            errors.append(f"Non-positive quantity: {parsed['quantity']}")

        results.append({
            'raw_data': raw_data,
            'parsed': parsed,
            'errors': errors,
        })

    return results
