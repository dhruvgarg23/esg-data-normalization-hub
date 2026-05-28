# Sources

For each of the three data sources: what real-world format I researched, what I learned, what the sample data looks like and why, and what would break in a real deployment.

---

## 1. SAP Fuel & Procurement

### What I Researched

I researched how SAP procurement data is typically exported, looking at:
- **IDoc format** (ORDERS05, E1EDK01/E1EDP01 segments) — SAP's native EDI format
- **ALV grid exports** from standard transactions (ME2M, ME2N, ME2K)
- **OData services** in S/4HANA
- **SAP table structures**: EKKO (PO headers), EKPO (PO line items), MAKT (material descriptions), MARA (material master)

### What I Learned

1. **IDocs are for system integration, not human export.** They're hierarchically structured with control records, data segments, and status records. A sustainability team won't send you an IDoc — they'll send a spreadsheet.

2. **ALV exports are the real-world delivery format.** SAP users run ME2M (PO list by material), customize the column layout, and export as CSV/Excel. The columns depend on the layout they saved.

3. **German localization is pervasive.** In German SAP instances, column headers are German (`Bestellnummer`, `Menge`, `Mengeneinheit`). The decimal separator is comma, the column delimiter is often semicolon, and dates are DD.MM.YYYY.

4. **Material codes are opaque.** `FUEL-DSL-001` is human-friendly; real SAP material numbers look like `000000000050012345`. You need a material master lookup or naming convention to classify fuel types.

5. **Plant codes need context.** `PL01` tells you nothing without a lookup table mapping it to "Munich Manufacturing Plant, Germany."

### What the Sample Data Looks Like

`sap_fuel_export.csv` — 25 rows of fuel purchase orders across 3 plants (Munich PL01, Frankfurt PL02, Hamburg PL03), spanning January–June 2024.

Key design choices:
- **German headers and semicolon delimiter**: Realistic for a German enterprise's SAP export
- **German decimal separators**: `5000,000` not `5000.000` — this is what SAP produces in German locale
- **Mixed fuel types**: Diesel (FUEL-DSL-001) and petrol (FUEL-GAS-002) with German descriptions (`Diesel Kraftstoff`, `Benzin Bleifrei`)
- **One non-fuel row**: `LUB-OIL-100` (Hydrauliköl AW46) — lubricant, not a fuel. Tests that the parser correctly rejects unclassifiable materials
- **Real vendor names**: Shell Deutschland GmbH, Aral AG, TotalEnergies DE — actual fuel suppliers in Germany

### What Would Break in a Real Deployment

1. **Material classification**: Real SAP material numbers are 18-digit codes, not human-readable. We'd need a configurable material-to-fuel-type mapping table, maintained per client.
2. **Unit diversity**: SAP supports hundreds of units of measure. We handle L, GAL, KG, but real exports might have BBL (barrels), CF (cubic feet), or client-custom units.
3. **Multiple document types**: We only handle purchase orders. Real procurement data includes goods receipts (MIGO), invoices (MIRO), and contracts. Each has different date semantics.
4. **Multi-line POs**: A single PO can have 100+ line items mixing fuel, parts, and services. Our classifier would need to ignore non-fuel items gracefully (which it does — but scaling this to handle the full variety of procurement categories is non-trivial).

---

## 2. Utility Electricity

### What I Researched

- **Green Button / ESPI standard** (US-centric XML format for energy data)
- **EnergyCAP and Measurabl** CSV import formats
- **Real utility portal exports** from providers like E.ON, EDF, AGL
- **Meter reading data structures**: actual vs. estimated readings, demand vs. consumption, time-of-use tariffs

### What I Learned

1. **There is no standard CSV format.** Every utility has its own column names, date formats, and structure. Some use `Usage_Quantity`, others `Consumption`, others `kWh_Used`. A flexible column mapper is essential.

2. **Billing periods are irregular.** Utilities read meters on their schedule, not calendar months. A bill might cover Jan 15 – Feb 14, or Feb 20 – Mar 19. You cannot assume monthly alignment.

3. **Estimated readings are common.** When a meter can't be read (access issues, smart meter failure), the utility estimates usage. These are typically flagged with `E` (Estimated) vs `A` (Actual). Estimated readings should have lower confidence.

4. **Multiple meters per facility.** A manufacturing plant might have separate meters for production, office space, and HVAC. Each generates its own billing line.

5. **Units vary.** Residential bills are always kWh. Commercial/industrial meters may report in MWh or even kVA (demand). The prototype handles kWh and MWh.

### What the Sample Data Looks Like

`utility_electricity.csv` — 21 rows across 4 meters at 3 facilities, covering 6 months of readings.

Key design choices:
- **Non-calendar billing periods**: Munich meters bill 15th-to-14th, Hamburg bills 20th-to-19th, Frankfurt uses calendar months. This directly tests whether the system handles irregular periods.
- **Estimated readings**: Two rows flagged with `Quality: E` — these get `confidence: LOW` and `quality_flags: ["estimated_reading"]`
- **MWh for Hamburg**: Hamburg Port reports in MWh instead of kWh. Tests the unit conversion pipeline.
- **Realistic consumption**: Munich plant uses 33–45 MWh/month (typical for a medium manufacturing facility), Frankfurt uses 21–28 MWh (distribution center, lower consumption), Hamburg uses 15–18 MWh (port facility, seasonal variation).

### What Would Break in a Real Deployment

1. **Date format ambiguity**: `01/02/2024` — is that January 2 or February 1? Without knowing the utility's locale, this is genuinely ambiguous. A production system needs configurable date format per data source.
2. **Demand charges**: Commercial bills have both consumption (kWh) and demand (kW/kVA) charges. Demand isn't directly convertible to emissions. We ignore it.
3. **Time-of-use rates**: Some utilities report consumption by rate period (peak, off-peak, shoulder). We aggregate to total consumption, which is correct for emissions but loses rate information.
4. **Solar/on-site generation offsets**: If a facility has rooftop solar, the utility bill shows net consumption. The actual grid consumption is higher. We'd need separate renewable generation data to handle this correctly.

---

## 3. Corporate Travel (Flights, Hotels, Ground Transport)

### What I Researched

- **SAP Concur**: Expense Report API v4, Itinerary API v4, standard export formats
- **Navan** (formerly TripActions): API documentation, expense report structure
- **GHG Protocol Scope 3 Category 6** guidance on business travel emissions calculation
- **IATA airport codes** and great-circle distance calculation

### What I Learned

1. **Expense reports are the data source, not bookings.** Travel bookings contain itinerary details (flight numbers, times), but expense reports are what gets approved and audited. They contain the financial record + basic travel details.

2. **Concur exports are configurable.** The CSV columns depend on the company's Concur configuration. There's no single standard format. Common fields: Report ID, Employee, Expense Type, Amount, Currency, Date, Vendor.

3. **Distance is almost never in the export.** Flight expenses include origin/destination airport codes (sometimes), but not distance. Distance must be derived from airport codes using great-circle calculation. This is the GHG Protocol's recommended approach.

4. **Multiple currencies per report.** A European company's travel expense report might include EUR, GBP, USD, SGD, and INR expenses. Currency conversion is needed for financial reporting but not for emissions (we use activity-based factors, not spend-based for flights).

5. **Hotel emissions use room-nights, not spend.** The GHG Protocol recommends room-nights as the activity unit for hotel emissions, with an average factor per night. Spend-based is a fallback.

### What the Sample Data Looks Like

`travel_expenses.csv` — 27 line items across 9 expense reports, 4 employees, spanning January–May 2024.

Key design choices:
- **Realistic travel patterns**: A German company with employees traveling to London, Dubai, Delhi, Paris, Singapore, Zurich, San Francisco. These represent actual business travel routes for a European enterprise.
- **Mixed expense types**: Airfare, Hotel, Taxi, Car Rental, Train. Each maps to a different emission factor category.
- **Airport codes for flights**: MUC→LHR, FRA→DXB, FRA→DEL, FRA→SIN, FRA→SFO, FRA→CDG, FRA→ZRH. Enables great-circle distance calculation.
- **Short-haul vs long-haul**: MUC→LHR (~930 km, short-haul factor) vs FRA→SIN (~10,300 km, long-haul factor). Different emission factors apply.
- **Hotels without amounts**: Some hotel entries deliberately omit the Amount field. Tests that the system handles incomplete data gracefully (uses room-nights for emissions, not spend).
- **Multiple currencies**: EUR, GBP, USD, SGD, INR, CHF, AED. Realistic for international travel.
- **Ground transport variety**: Uber, Careem (Middle East ride-hailing), Grab (Southeast Asia), Ola (India), Deutsche Bahn (German rail), SBB (Swiss rail), Hertz, Enterprise.

### What Would Break in a Real Deployment

1. **Incomplete airport codes**: Many Concur exports have city names instead of IATA codes (e.g., "London" not "LHR"). We'd need a city-to-airport resolver (which introduces ambiguity: London → LHR, LGW, LCY, STN?).
2. **Connecting flights**: A flight MUC→LHR→JFK has two segments. The expense report might show it as one line item to London and one to New York, or as a single ticket. Handling multi-segment flights correctly requires itinerary data, not just expense data.
3. **Class of service**: Business class has ~2-3x the emission factor of economy class (more space per passenger = more emissions per passenger-km). Concur exports sometimes include `airlineServiceClassName`, but not always.
4. **Personal vs. business**: Some expense reports include personal trips mixed with business. Filtering is a policy decision, not a technical one.
5. **Radiative Forcing Index (RFI)**: The GHG Protocol recommends multiplying flight emissions by an RFI of 1.9 to account for non-CO₂ effects at altitude (contrails, NOx). We don't apply this multiplier. A production system should make it configurable.
