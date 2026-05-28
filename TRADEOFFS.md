# Tradeoffs

Three things I deliberately did not build and why.

---

## 1. PDF Utility Bill Parsing

**What it would be:** An ingestion path that accepts scanned or digital PDF utility bills, extracts meter readings and consumption data using OCR/table extraction (e.g., tabula, AWS Textract, or Google Document AI), and feeds them into the same normalization pipeline.

**Why I didn't build it:**

PDF parsing for utility bills is genuinely hard, and doing it badly would be worse than not doing it at all. Here's why:

- **Every utility formats their bills differently.** There is no PDF standard for electricity bills. Duke Energy, E.ON, EDF, and ConEd all have completely different layouts, table structures, and terminology. A parser that works for one doesn't work for the next.

- **Table extraction is brittle.** Libraries like tabula-py work well on clean, well-structured tables. Utility bills often have nested tables, merged cells, multi-column layouts, and logos overlapping data regions. Accuracy drops quickly.

- **OCR compounds errors.** Scanned bills require OCR first, which introduces character-level errors (e.g., "kWh" → "kwh" or "kWN"). These propagate into the quantity field and produce wrong emission calculations with no obvious signal.

- **The cost is disproportionate to the value for a prototype.** Portal CSV export covers the same data (meter readings, consumption, billing periods) with 100% parsing accuracy. In a production system, PDF support would be worth the investment — but it's a separate workstream requiring training data, validation loops, and human-in-the-loop correction.

**What I'd build in production:** A template-based PDF parser where each utility provider gets a defined extraction template (bounding boxes, field locations). Combined with a confidence threshold — if extraction confidence is below X%, flag for manual entry. This is essentially what commercial utility data platforms (UtilityAPI, Urjanet) do.

---

## 2. Live Concur/Navan API Integration

**What it would be:** An OAuth2-authenticated API connector that pulls expense report data directly from SAP Concur's Expense API v4 or Navan's API, eliminating the need for manual CSV exports. The system would authenticate, paginate through expense entries, extract travel-related items, and feed them into the travel parser.

**Why I didn't build it:**

- **OAuth2 setup requires a registered application.** Concur's API requires registering an app in their developer portal, getting client credentials, and configuring scopes (e.g., `expense.report.read`). For a prototype, this is blocked — we don't have the client's Concur instance credentials.

- **Sandbox vs. production gap.** Concur's sandbox has limited data and doesn't accurately reflect real expense report structures. Building against the sandbox would give false confidence.

- **The CSV export is the same data.** Concur's "Send to Excel" function produces a CSV with the same fields available via the API (Report ID, Employee, Expense Type, Amount, Date, Vendor). The API adds incremental value for automation (polling for new reports) but not for data richness.

- **Client IT security review.** Granting API access to a third-party system (us) from their Concur instance requires IT security review, API key management, and access governance. This is a week-long process at enterprise clients, not a 4-day prototype feature.

**What I'd build in production:** An API connector with configurable OAuth2 credentials, automatic polling for new expense reports (webhook or scheduled), and incremental sync (only fetch reports modified since last sync). Plus a fallback to CSV upload for clients who won't grant API access.

---

## 3. Emission Factor Version Management with Automatic Re-Calculation

**What it would be:** A full emission factor database with:
- Country-specific factors (UK, US, EU, India, etc.)
- Year-specific vintages (2022, 2023, 2024 factors)
- Automatic factor selection based on the emission record's country + date
- When factors are updated, automatic re-calculation of all affected emission records
- Audit trail of which factor version was used for each calculation

**Why I didn't build it:**

- **Factor selection is a policy decision, not just a lookup.** Using UK vs. US factors isn't a technical choice — it depends on the client's reporting framework (GHG Protocol, CDP, TCFD), their auditor's requirements, and regulatory jurisdiction. Building automatic selection would encode assumptions that might be wrong.

- **Re-calculation has cascading implications.** If you update a factor and re-calculate 10,000 records, you've changed approved numbers. This conflicts with the audit lock mechanism. The right approach is versioned factors where old records keep their original calculation (with the factor version recorded) and new records use the updated factor.

- **Scope is enormous.** The UK DESNZ factors alone have 100+ line items (specific fuel types, vehicle classes, flight cabin classes, etc.). Add US EPA, IEA, and country-specific grid factors, and you're looking at thousands of entries with complex applicability rules.

- **12 hardcoded factors cover the prototype use case.** Diesel, petrol, natural gas, LPG, grid electricity, three flight haul types, hotel, car rental, taxi, and rail. This covers the three sources in the assignment with real, defensible numbers from a recognized source (UK DESNZ 2024).

**What I'd build in production:** An `EmissionFactorSet` model with versioning. Each set has an effective date range. Records reference the specific factor version used. New factor versions don't retroactively change existing records — they apply to new calculations going forward. An admin UI for importing factor sets from official spreadsheets (DESNZ publishes theirs as Excel).
