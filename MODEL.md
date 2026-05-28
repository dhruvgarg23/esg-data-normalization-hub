# Data Model

## Design Philosophy

The data model follows a **single canonical table** approach: every row from every source (SAP fuel, utility electricity, corporate travel) is normalized into a single `EmissionRecord` table. This is a deliberate choice over separate tables per source, and the reasoning is critical:

1. **Cross-source queries are the common case.** An analyst reviewing emissions doesn't filter by "SAP rows" vs "utility rows" — they filter by scope, time period, facility, or review status. A single table makes these queries trivial.

2. **The review workflow is source-agnostic.** Approving a record follows the same state machine regardless of whether it came from SAP or Concur. Separate tables would mean duplicating the review logic three times.

3. **Audit trail is unified.** The `AuditLog` table references one FK (`emission_record`), not three. Auditors see a single chronological trail.

Source-specific raw data is preserved in the `RawRecord` table as a JSON blob. This gives us both: clean normalized data for analysis + full original data for audit.

---

## Entity Relationship Diagram

```
┌──────────────┐
│    Tenant    │
│──────────────│
│ id (UUID PK) │
│ name         │
│ slug (unique)│
│ created_at   │
└──────┬───────┘
       │ 1:N
       ├──────────────────────────────────────────────────────┐
       │                    │                    │            │
┌──────▼────────┐  ┌────────▼────────┐  ┌──────▼──────┐  ┌────▼─────────┐
│  UserProfile  │  │DataIngestionJob │  │PlantLookup  │  │EmissionFactor│
│────────────── │  │─────────────────│  │─────────────│  │──────────────│
│ user (FK→User)│  │ id (UUID PK)    │  │ plant_code  │  │ category     │
│ tenant (FK)   │  │ tenant (FK)     │  │ plant_name  │  │ factor_value │
│ role (ENUM)   │  │ uploaded_by     │  │ country     │  │ unit_input   │
│ created_at    │  │ source_type     │  │ region      │  │ source_ref   │
└───────────────┘  │ file_name       │  └─────────────┘  │ valid_from/to│
                   │ file_hash       │                   └──────────────┘
                   │ status          │                   (tenant nullable=
                   │ total/success/  │                    system defaults)
                   │   error_rows    │
                   │ error_log (JSON)│
                   └────────┬────────┘
                            │ 1:N
                   ┌────────▼────────┐
                   │   RawRecord     │
                   │──────────────── │
                   │ id (UUID PK)    │
                   │ ingestion_job   │
                   │ row_number      │
                   │ raw_data (JSON) │◄── Original data preserved verbatim
                   │ parse_errors    │
                   │ status          │
                   └────────┬────────┘
                            │ 1:1
                   ┌────────▼──────────────────────────────────┐
                   │            EmissionRecord                 │
                   │───────────────────────────────────────────│
                   │ id (UUID PK)                              │
                   │ tenant (FK) ◄── Multi-tenancy             │
                   │                                           │
                   │ ── Source Tracking ──                     │
                   │ ingestion_job (FK)                        │
                   │ raw_record (FK, nullable)                 │
                   │ source_type (SAP_FUEL|UTILITY|TRAVEL)     │
                   │ source_identifier (PO#, Meter ID, Report#)│
                   │                                           │
                   │ ── GHG Classification ──                  │
                   │ ghg_scope (1, 2, or 3)                    │
                   │ ghg_category (text)                       │
                   │                                           │
                   │ ── Normalized Activity Data ──            │
                   │ activity_description                      │
                   │ activity_quantity (Decimal)               │
                   │ activity_unit (L, kWh, passenger-km, etc.)│
                   │                                           │
                   │ ── Original Data (as received) ──         │
                   │ original_quantity (Decimal)               │
                   │ original_unit                             │
                   │                                           │
                   │ ── Emissions ──                           │
                   │ emission_factor (FK)                      │
                   │ co2e_kg (Decimal) ◄── The result          │
                   │                                           │
                   │ ── Temporal ──                            │
                   │ activity_date                             │
                   │ reporting_period_start / end              │
                   │                                           │
                   │ ── Location ──                            │
                   │ facility_name, facility_code              │
                   │ country, region                           │
                   │                                           │
                   │ ── Review Workflow ──                     │
                   │ review_status (PENDING→APPROVED/FLAGGED/  │
                   │                REJECTED)                  │
                   │ reviewed_by, reviewed_at, review_notes    │
                   │ is_locked (bool) ◄── Immutable after approve│
                   │                                           │
                   │ ── Data Quality ──                        │
                   │ confidence (HIGH/MEDIUM/LOW)              │
                   │ quality_flags (JSON array)                │
                   │                                           │
                   │ ── Audit ──                               │
                   │ created_at, updated_at, created_by        │
                   └────────┬──────────────────────────────────┘
                            │ 1:N
                   ┌────────▼───────┐
                   │    AuditLog    │
                   │────────────────│
                   │ id (UUID PK)   │
                   │ tenant (FK)    │
                   │ emission_record│
                   │ action (ENUM)  │
                   │ field_changed  │
                   │ old_value      │
                   │ new_value      │
                   │ notes          │
                   │ performed_by   │
                   │ performed_at   │◄── Append-only, never updated
                   └────────────────┘
```

---

## Key Design Decisions

### Multi-Tenancy
Row-level isolation via `tenant_id` FK on all data tables. Every query in the API layer filters by the current user's tenant. This is the simplest approach for a prototype. A production system would likely use PostgreSQL Row Level Security policies or schema-per-tenant.

### Dual Quantity Tracking
Every `EmissionRecord` stores both:
- `activity_quantity` / `activity_unit` — the normalized value (always in standard units: L, kWh, passenger-km)
- `original_quantity` / `original_unit` — exactly what was in the source file

This is critical for audit. An auditor needs to verify that 200 GAL was correctly converted to 757.08 L.

### Scope Classification
Scope is determined at ingestion time based on source type:
- SAP Fuel → **Scope 1** (direct combustion)
- Utility Electricity → **Scope 2** (purchased energy)
- Corporate Travel → **Scope 3**, Category 6 (business travel)

This is correct per the GHG Protocol. The `ghg_category` field provides sub-classification (e.g., "Stationary Combustion", "Purchased Electricity", "Business Travel").

### Audit Trail
Two-layer approach:
1. **`is_locked` flag** on `EmissionRecord`: Once approved, the record cannot be modified. Enforced both in the model's `save()` method and at the API layer.
2. **`AuditLog` table**: Immutable append-only log. Records every creation, update, approval, rejection, flagging, and lock event. Includes old/new values for changed fields, who did it, and when.

### Unit Normalization
A conversion registry maps 20+ unit variants (GAL→L, MWh→kWh, miles→km, etc.). Conversions are tracked via `quality_flags` so analysts can see when a value was converted.

### Emission Factors
`EmissionFactor` table supports:
- **System defaults** (`tenant=NULL`): UK DESNZ 2024 factors
- **Tenant overrides** (`tenant=<id>`): Client-specific factors take precedence

Factors have `valid_from` / `valid_to` dates for temporal accuracy. The normalizer looks up the appropriate factor based on activity date.

### Data Quality Scoring
Each record gets a `confidence` rating:
- **HIGH**: All data present, actual (not estimated) readings, no conversions needed
- **MEDIUM**: Minor derivations (unit converted, distance calculated from airport codes)
- **LOW**: Estimated readings, missing data, unknown classifications

The `quality_flags` JSON array provides specifics (e.g., `["estimated_reading", "unit_converted"]`).
