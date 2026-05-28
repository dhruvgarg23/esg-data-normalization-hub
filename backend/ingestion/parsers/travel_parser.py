"""
Corporate Travel Expense CSV Parser

Handles CSV exports from corporate travel platforms like SAP Concur or Navan.
These are expense report line-item exports, not raw booking data.

Expected columns (with common aliases):
  - Report_ID / Report_Name / Report_Number
  - Employee / Employee_Name / Traveler
  - Expense_Type / Category / Type
  - Transaction_Date / Date / Expense_Date
  - Vendor / Merchant / Supplier
  - Amount / Total / Cost
  - Currency
  - Origin / Departure / From_City / From_Airport
  - Destination / Arrival / To_City / To_Airport
  - Hotel_Checkin / Check_In / Checkin_Date
  - Hotel_Checkout / Check_Out / Checkout_Date
  - Comment / Business_Purpose / Description / Notes
  - Payment_Type / Payment_Method
"""
import csv
import io
import math
from datetime import datetime
from decimal import Decimal, InvalidOperation


HEADER_ALIASES = {
    'report_id': 'report_id',
    'report_name': 'report_id',
    'report_number': 'report_id',
    'report': 'report_id',

    'employee': 'employee',
    'employee_name': 'employee',
    'traveler': 'employee',
    'traveller': 'employee',

    'expense_type': 'expense_type',
    'category': 'expense_type',
    'type': 'expense_type',
    'expense_category': 'expense_type',

    'transaction_date': 'date',
    'date': 'date',
    'expense_date': 'date',
    'travel_date': 'date',

    'vendor': 'vendor',
    'merchant': 'vendor',
    'supplier': 'vendor',

    'amount': 'amount',
    'total': 'amount',
    'cost': 'amount',
    'expense_amount': 'amount',

    'currency': 'currency',

    'origin': 'origin',
    'departure': 'origin',
    'from_city': 'origin',
    'from_airport': 'origin',
    'from': 'origin',
    'departure_airport': 'origin',

    'destination': 'destination',
    'arrival': 'destination',
    'to_city': 'destination',
    'to_airport': 'destination',
    'to': 'destination',
    'arrival_airport': 'destination',

    'hotel_checkin': 'checkin',
    'check_in': 'checkin',
    'checkin_date': 'checkin',
    'checkin': 'checkin',

    'hotel_checkout': 'checkout',
    'check_out': 'checkout',
    'checkout_date': 'checkout',
    'checkout': 'checkout',

    'comment': 'comment',
    'business_purpose': 'comment',
    'description': 'comment',
    'notes': 'comment',

    'payment_type': 'payment_type',
    'payment_method': 'payment_type',
}

# IATA airport code -> (latitude, longitude)
# A subset for prototype purposes. In production, use a full IATA database.
AIRPORT_COORDS = {
    'LHR': (51.4700, -0.4543),   # London Heathrow
    'JFK': (40.6413, -73.7781),   # New York JFK
    'FRA': (50.0379, 8.5622),     # Frankfurt
    'MUC': (48.3538, 11.7861),    # Munich
    'CDG': (49.0097, 2.5479),     # Paris CDG
    'AMS': (52.3105, 4.7683),     # Amsterdam
    'SIN': (1.3644, 103.9915),    # Singapore
    'DXB': (25.2532, 55.3657),    # Dubai
    'DEL': (28.5562, 77.1000),    # Delhi
    'BOM': (19.0896, 72.8656),    # Mumbai
    'BLR': (13.1986, 77.7066),    # Bangalore
    'HKG': (22.3080, 113.9185),   # Hong Kong
    'NRT': (35.7720, 140.3929),   # Tokyo Narita
    'SFO': (37.6213, -122.3790),  # San Francisco
    'LAX': (33.9416, -118.4085),  # Los Angeles
    'ORD': (41.9742, -87.9073),   # Chicago O'Hare
    'BER': (52.3667, 13.5033),    # Berlin
    'ZRH': (47.4647, 8.5492),     # Zurich
    'DUS': (51.2895, 6.7668),     # Dusseldorf
    'HAM': (53.6304, 9.9882),     # Hamburg
    'MAD': (40.4983, -3.5676),    # Madrid
    'BCN': (41.2974, 2.0833),     # Barcelona
    'FCO': (41.8003, 12.2389),    # Rome Fiumicino
    'IST': (41.2753, 28.7519),    # Istanbul
    'DOH': (25.2731, 51.6081),    # Doha
    'SYD': (33.9461, 151.1772),   # Sydney (using positive for calc)
    'MEL': (37.6690, 144.8410),   # Melbourne
    'YYZ': (43.6777, -79.6248),   # Toronto
    'CPT': (-33.9715, 18.6021),   # Cape Town
}

# Expense type classification
EXPENSE_TYPE_MAP = {
    'airfare': 'FLIGHT',
    'air fare': 'FLIGHT',
    'flight': 'FLIGHT',
    'airline': 'FLIGHT',
    'air ticket': 'FLIGHT',
    'air travel': 'FLIGHT',

    'hotel': 'HOTEL',
    'hotel/lodging': 'HOTEL',
    'lodging': 'HOTEL',
    'accommodation': 'HOTEL',
    'hotel room': 'HOTEL',

    'ground transportation': 'GROUND',
    'ground transport': 'GROUND',
    'taxi': 'TAXI',
    'cab': 'TAXI',
    'uber': 'TAXI',
    'lyft': 'TAXI',
    'ride share': 'TAXI',
    'car rental': 'CAR_RENTAL',
    'rental car': 'CAR_RENTAL',
    'car hire': 'CAR_RENTAL',
    'rail': 'RAIL',
    'train': 'RAIL',
    'railway': 'RAIL',
}


def _normalize_header(header):
    h = header.strip().lower().replace(' ', '_').replace('-', '_')
    return HEADER_ALIASES.get(h, h)


def _parse_date(date_str):
    date_str = date_str.strip()
    for fmt in ('%Y-%m-%d', '%m/%d/%Y', '%d/%m/%Y', '%d.%m.%Y', '%b %d, %Y', '%d %b %Y'):
        try:
            return datetime.strptime(date_str, fmt).date()
        except ValueError:
            continue
    return None


def _classify_expense(expense_type_str):
    """Map expense type string to travel category."""
    search = expense_type_str.lower().strip()
    return EXPENSE_TYPE_MAP.get(search, None)


def _haversine_km(lat1, lon1, lat2, lon2):
    """
    Calculate great-circle distance between two points using the
    Haversine formula. Returns distance in kilometers.

    This is how we derive flight distance when only airport codes are given
    (which is common — Concur exports rarely include distance).
    """
    R = 6371  # Earth's radius in km
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a))
    return R * c


def _compute_flight_distance(origin_code, dest_code):
    """
    Compute flight distance from airport IATA codes.
    Returns (distance_km, is_derived) or (None, False).
    """
    origin = origin_code.upper().strip() if origin_code else ''
    dest = dest_code.upper().strip() if dest_code else ''

    if origin in AIRPORT_COORDS and dest in AIRPORT_COORDS:
        lat1, lon1 = AIRPORT_COORDS[origin]
        lat2, lon2 = AIRPORT_COORDS[dest]
        distance = _haversine_km(lat1, lon1, lat2, lon2)
        return round(distance, 1), True
    return None, False


def _classify_flight_haul(distance_km):
    """Classify flight as domestic/short-haul/long-haul based on distance."""
    if distance_km is None:
        return 'FLIGHT_SHORT_HAUL'  # default assumption
    if distance_km < 500:
        return 'FLIGHT_DOMESTIC'
    elif distance_km < 3700:
        return 'FLIGHT_SHORT_HAUL'
    else:
        return 'FLIGHT_LONG_HAUL'


def parse_travel_csv(file_content):
    """
    Parse a corporate travel expense CSV export (Concur-style).

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
        quality_flags = []
        raw_data = dict(row)

        normalized = {}
        for orig_key, value in row.items():
            canonical = header_map.get(orig_key, orig_key)
            normalized[canonical] = value.strip() if value else ''

        parsed = {
            'row_number': row_num,
            'report_id': normalized.get('report_id', ''),
            'employee': normalized.get('employee', ''),
            'vendor': normalized.get('vendor', ''),
            'currency': normalized.get('currency', ''),
            'comment': normalized.get('comment', ''),
            'payment_type': normalized.get('payment_type', ''),
        }

        # Parse expense type
        expense_type_str = normalized.get('expense_type', '')
        travel_category = _classify_expense(expense_type_str)
        parsed['expense_type_raw'] = expense_type_str
        parsed['travel_category'] = travel_category
        if travel_category is None:
            errors.append(f"Unrecognized expense type: '{expense_type_str}'")

        # Parse date
        date_str = normalized.get('date', '')
        parsed['date'] = _parse_date(date_str) if date_str else None
        if date_str and not parsed['date']:
            errors.append(f"Unparseable date: '{date_str}'")

        # Parse amount
        amount_str = normalized.get('amount', '')
        amount_str = amount_str.replace(',', '').replace('$', '').replace('£', '').replace('€', '')
        try:
            parsed['amount'] = Decimal(amount_str) if amount_str else None
        except (InvalidOperation, ValueError):
            errors.append(f"Invalid amount: '{normalized.get('amount', '')}'")
            parsed['amount'] = None

        # --- Flight-specific ---
        if travel_category == 'FLIGHT':
            origin = normalized.get('origin', '')
            destination = normalized.get('destination', '')
            parsed['origin'] = origin
            parsed['destination'] = destination

            distance, derived = _compute_flight_distance(origin, destination)
            parsed['distance_km'] = distance
            parsed['haul_type'] = _classify_flight_haul(distance)

            if derived:
                quality_flags.append('distance_derived')
            if not origin or not destination:
                errors.append("Missing origin or destination airport codes")
            elif distance is None:
                errors.append(
                    f"Unknown airport code(s): origin='{origin}', dest='{destination}'"
                )

        # --- Hotel-specific ---
        elif travel_category == 'HOTEL':
            checkin_str = normalized.get('checkin', '')
            checkout_str = normalized.get('checkout', '')
            parsed['checkin'] = _parse_date(checkin_str) if checkin_str else None
            parsed['checkout'] = _parse_date(checkout_str) if checkout_str else None

            if parsed['checkin'] and parsed['checkout']:
                nights = (parsed['checkout'] - parsed['checkin']).days
                parsed['room_nights'] = max(nights, 1)
            else:
                parsed['room_nights'] = 1
                quality_flags.append('room_nights_assumed')
                if not checkin_str or not checkout_str:
                    errors.append("Missing check-in/check-out dates; assuming 1 night")

        # --- Ground transport ---
        elif travel_category in ('TAXI', 'CAR_RENTAL', 'RAIL'):
            parsed['ground_type'] = travel_category

        parsed['quality_flags'] = quality_flags

        results.append({
            'raw_data': raw_data,
            'parsed': parsed,
            'errors': errors,
        })

    return results
