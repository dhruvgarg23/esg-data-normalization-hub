# Decisions

Every ambiguity I encountered, what I chose, why, and what I'd ask the PM.

---

## 1. SAP Export Format: ALV Flat File CSV (not IDoc)

**Ambiguity:** SAP data can come in many formats — IDoc, OData, BAPI, RFC, or flat file exports. The assignment says to pick one and justify it.

**Decision:** ALV flat-file CSV export (e.g., from ME2M transaction).

**Why:** In practice, when a sustainability team asks their SAP team for fuel procurement data, they get a spreadsheet. Not an IDoc. IDocs are for system-to-system middleware integration (SAP PI/PO, CPI). They're hierarchical, segment-based structures — the right choice if we were building an automated pipeline between SAP and our system. But "onboarding a new enterprise client" implies we're receiving data, not building a live integration. The facilities or procurement team runs ME2M, customizes the ALV layout, hits Export → Local File → Spreadsheet. That's the realistic flow.

**What I'd ask the PM:**
- "Is this a one-time historical load, or will we receive ongoing SAP exports? If ongoing, IDoc/OData integration would be worth the investment."
- "Does the client have SAP S/4HANA (which has native OData) or ECC (which mostly has BAPIs and flat files)?"

---

## 2. SAP Column Headers: Support Both English and German

**Ambiguity:** SAP column headers depend on the system language. German companies often have SAP configured in German.

**Decision:** Built a header alias map that accepts both English (`Quantity`, `Unit`, `PO_Number`) and German (`Menge`, `Mengeneinheit`, `Bestellnummer`) column names.

**Why:** This is a real pain point. I've seen SAP exports with `Bestellnummer` next to `Material_Description` (mixed language) because someone changed their login language. The alias map handles this gracefully. The sample data uses German headers and semicollon delimiters (`;`) because that's what German-locale SAP exports produce.

---

## 3. SAP Date Format: DD.MM.YYYY

**Ambiguity:** SAP date format depends on user settings. Could be DD.MM.YYYY, YYYY-MM-DD, MM/DD/YYYY.

**Decision:** Try multiple formats in order: DD.MM.YYYY first (most common in European SAP), then ISO, then US format.

**Why:** The parser shouldn't fail on a valid date just because the format is unexpected. Trying DD.MM.YYYY first reduces false-positive ambiguity (e.g., `01.02.2024` — is that Jan 2 or Feb 1? In SAP Germany, it's Feb 1).

**What I'd ask the PM:** "Can we specify the date format when the client sets up their export template? That eliminates ambiguity."

---

## 4. Utility Data: Portal CSV (not PDF)

**Ambiguity:** The assignment says "portal CSV export, a PDF bill, an API." Pick one.

**Decision:** Portal CSV export.

**Why:** PDF parsing is a can of worms — every utility formats their bills differently, tabula/camelot extraction is brittle, and OCR adds error. APIs exist (Green Button / ESPI standard) but are only offered by large US utilities. In Europe, portal CSV export is by far the most common way facilities teams get consumption data. They log into the provider's portal, download monthly usage as CSV.

**What I'd ask the PM:** "Does the client have a mix of utility providers? If so, we need to handle multiple CSV formats. The flexible column mapping I built handles this, but we'd need the client to tell us which columns map to what."

---

## 5. Utility Billing Periods: Non-Calendar-Month

**Ambiguity:** Billing periods rarely align with calendar months.

**Decision:** Store `reporting_period_start` and `reporting_period_end` as separate dates. Do not try to pro-rate to calendar months.

**Why:** Pro-rating introduces inaccuracy and complexity. If a bill covers Jan 15 – Feb 14, storing it as-is is honest. An analyst can see exactly what period the reading covers. Pro-rating to January and February would require assumptions about linear consumption (which is wrong — energy use varies by temperature, production schedules, etc.).

**What I'd ask the PM:** "For reporting, do auditors need emissions aligned to calendar months or fiscal quarters? If so, we need a pro-rating step, but it should be a separate calculation layer, not baked into the raw data."

---

## 6. Travel Data: Concur Expense Report CSV (not API)

**Ambiguity:** Concur offers APIs (Itinerary v4, Expense v4) and CSV exports.

**Decision:** CSV expense report export.

**Why:** Concur API integration requires OAuth2 setup, sandbox access, and proper scoping. For a 4-day prototype, CSV export is the realistic choice. More importantly, many clients don't grant third-party API access to their Concur instance — they export expense reports and send the CSV. The CSV format I handle matches what Concur's "Send to Excel" function produces.

**What I'd ask the PM:** "Does the client want us to pull from Concur API directly, or will they send us exports? If API, we need their OAuth credentials and approval from their IT security team."

---

## 7. Flight Distance: Derived from Airport Codes via Haversine

**Ambiguity:** Concur exports rarely include distance. They include origin/destination airport codes.

**Decision:** Calculate great-circle distance using the haversine formula with a built-in IATA airport coordinate lookup table (~30 airports for prototype).

**Why:** This is the GHG Protocol's recommended approach for Scope 3 Category 6 when distance data isn't directly available. The haversine formula gives great-circle distance, which is a standard approximation for flight emissions. Derived distances are flagged with `quality_flags: ["distance_derived"]` so analysts know the value was calculated, not reported.

**Limitation:** The prototype has ~30 airports. A production system would use a full IATA database (10,000+ airports).

---

## 8. Ground Transport: Spend-Based Estimation

**Ambiguity:** Taxi and car rental expenses don't include distance.

**Decision:** Use spend-based emission factors (kg CO₂e per currency unit) as per GHG Protocol guidance.

**Why:** When activity data (distance, fuel consumed) is unavailable, the GHG Protocol explicitly recommends spend-based estimation as a fallback. The emission factors are less precise but better than nothing. Records using spend-based estimation are flagged with `quality_flags: ["spend_based_estimate"]` and confidence `LOW`.

**What I'd ask the PM:** "Is spend-based estimation acceptable for the client's auditors? Some prefer activity-based only and would rather have the data gap flagged as 'no data' than see an estimate."

---

## 9. Single EmissionRecord Table (not per-source tables)

**Ambiguity:** Should SAP records, utility records, and travel records live in separate tables?

**Decision:** Single `EmissionRecord` table with `source_type` discriminator.

**Why:** See MODEL.md for full rationale. TL;DR: the review workflow, filtering, aggregation, and audit trail all operate across sources. Separate tables would mean 3x the code for the same logic, JOIN complexity for dashboard queries, and a fragmented audit trail. Source-specific raw data is preserved in `RawRecord.raw_data` (JSON).

---

## 10. Row-Level Multi-Tenancy (not schema-per-tenant)

**Ambiguity:** How to isolate client data.

**Decision:** `tenant_id` FK on all tables, filtered in every API queryset.

**Why:** For a prototype, this is the right trade-off. Schema-per-tenant requires Django middleware to dynamically switch schemas, complicates migrations, and is overkill when we have one demo tenant. In production, I'd recommend PostgreSQL Row Level Security (RLS) policies — they enforce isolation at the database level, which is more secure than relying on application-layer filtering.

---

## 11. Immutability After Approval

**Ambiguity:** What happens after a record is approved?

**Decision:** `is_locked = True`. The record cannot be modified — enforced in the model's `save()` method AND the API. All changes before locking are tracked in `AuditLog`.

**Why:** Audit integrity. If approved records could be edited, the auditor's verification becomes meaningless. If a correction is needed after approval, the correct process is to reject/un-approve (which a production system would support with proper authorization), not silently edit.

---

## 12. Emission Factors: Hardcoded UK DESNZ 2024

**Ambiguity:** Which emission factor database to use.

**Decision:** Hardcoded 12 factors from UK DESNZ 2024 GHG Conversion Factors as system defaults.

**Why:** This is the UK government's official factor set, widely used in corporate carbon accounting. For a prototype, hardcoding is honest. A production system would need a full factor database with country-specific factors (e.g., US EPA for US grid, IEA for international grids), fuel-specific sub-categories, and vintage-year handling.

**What I'd ask the PM:** "Which emission factor database does the client use? DEFRA/DESNZ, US EPA, IEA? Do they have their own factors? The system supports tenant-specific overrides."

---

## 13. File Deduplication via SHA-256 Hash

**Decision:** Hash each uploaded file and reject duplicates.

**Why:** If someone accidentally uploads the same file twice, we don't want duplicate emission records. The hash comparison catches exact duplicates before processing. It does NOT catch near-duplicates (same data, different formatting) — that's a much harder problem.

---

## 14. Confidence Scoring

**Decision:** Three-tier confidence system (HIGH/MEDIUM/LOW) with explicit quality flags.

**Why:** Analysts need to quickly identify which records need extra scrutiny. A record with `confidence: LOW, quality_flags: ["estimated_reading"]` clearly needs manual verification. This is better than a binary "good/bad" because some records are usable but imperfect (MEDIUM: unit was converted, distance was derived).
