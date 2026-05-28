# 🌿 Breathe ESG — Carbon Ingestion & Normalization Platform

An enterprise-grade ESG (Environmental, Social, Governance) emissions data ingestion and normalization platform designed for [Breathe ESG](https://breatheesg.com). Automates the ingestion of diverse activity data — fuels, electricity consumption, and corporate travel — matches them with UK DESNZ 2024 emission factors, and calculates high-precision **Scope 1, 2, and 3** greenhouse gas (GHG) emissions in kg CO₂e.

> **Live Demo**: [https://esg-data-normalization-hub-1.onrender.com](https://esg-data-normalization-hub-1.onrender.com)
> _(Free tier — first load takes ~30s while the backend wakes up)_

---

## 📑 Table of Contents

- [Architecture & Design Highlights](#-architecture--design-highlights)
- [Tech Stack](#-tech-stack)
- [Project Structure](#-project-structure)
- [Local Development Setup](#-local-development-setup)
- [Sample Test Data](#-sample-test-data)
- [API Reference](#-api-reference)
- [Production Deployment (Render)](#-production-deployment-render)
- [Design Decisions](#-design-decisions)
- [Additional Documentation](#-additional-documentation)

---

## 🚀 Architecture & Design Highlights

### Ingestion & Normalization Pipeline

```
 ┌────────────────────┐     ┌────────────────────┐     ┌──────────────────┐
 │   CSV File Upload  │────▶│  Source-Specific    │────▶│  Normalization   │
 │  (SAP / Utility /  │     │  Parser            │     │  Engine          │
 │   Travel)          │     │  (Column mapping,  │     │  (Unit convert,  │
 │                    │     │   date parsing,    │     │   EF lookup,     │
 │                    │     │   validation)      │     │   CO₂e calc)     │
 └────────────────────┘     └────────────────────┘     └──────┬───────────┘
                                                              │
 ┌────────────────────┐     ┌────────────────────┐            │
 │  Review & Approval │◀────│  EmissionRecord    │◀───────────┘
 │  Workflow          │     │  + RawRecord       │
 │  (Approve/Reject/  │     │  + AuditLog        │
 │   Bulk actions)    │     │  (Immutable after  │
 └────────────────────┘     │   approval)        │
                            └────────────────────┘
```

- **Multi-Source Support**: Three distinct parsers for real-world enterprise exports:
  - **SAP Fuel & Procurement** (SAP ALV layout, semicolon-delimited, German/English headers) → **Scope 1**
  - **Utility Electricity Portal** (meter-reading CSV with MWh/kWh support) → **Scope 2**
  - **Corporate Travel Expenses** (Concur-style CSV with flight distance derivation) → **Scope 3**

- **Intelligent Normalization**: Automatic unit conversions (GAL→L, MWh→kWh, miles→km) to kg CO₂e using **UK DESNZ 2024** emission factors

- **Confidence Scoring**: Three-tier system (HIGH / MEDIUM / LOW) with granular quality flags (`unit_converted`, `estimated_reading`, `distance_derived`, `spend_based_estimate`)

- **Audit Trail**: Every state transition is logged in `AuditLog`. Records become immutable after approval

- **File Deduplication**: SHA-256 hash check prevents duplicate uploads

### Modern UI/UX

- **Interactive Dashboard**: Scope 1/2/3 breakdowns, top facility emitters, monthly trends, data quality metrics
- **Review & Approval Workflow**: Expandable detail rows showing raw vs. normalized data, bulk approve, per-record audit log
- **Responsive Sidebar**: Collapsible navigation with state persisted in `localStorage`
- **Design System**: Custom CSS variables, smooth micro-animations, pastel-toned brand colors, dark surface palette

---

## 🛠 Tech Stack

| Layer | Technology |
|---|---|
| **Backend** | Django 4.2, Django REST Framework, SimpleJWT |
| **Frontend** | React 19, Vite 8, Vanilla CSS design system |
| **Charts** | Recharts 3 |
| **Icons** | Lucide React |
| **Database** | SQLite (local dev), PostgreSQL (production) |
| **Auth** | JWT (access + refresh tokens) |
| **Static Files** | WhiteNoise (compressed, manifest-based) |
| **Deployment** | Render (free tier) |

---

## 📁 Project Structure

```
esg_assignment/
├── backend/
│   ├── config/                    # Django project settings
│   │   ├── settings.py            # Database, CORS, REST, JWT config
│   │   ├── urls.py                # Root URL routing
│   │   └── wsgi.py                # WSGI entry point (Gunicorn)
│   │
│   ├── core/                      # Core models & auth
│   │   ├── models.py              # Tenant, UserProfile, EmissionFactor, PlantLookup
│   │   ├── views.py               # Registration, current user, reference data APIs
│   │   └── serializers.py
│   │
│   ├── ingestion/                 # Data ingestion pipeline
│   │   ├── parsers/
│   │   │   ├── sap_parser.py      # SAP ALV fuel export parser
│   │   │   ├── utility_parser.py  # Utility electricity CSV parser
│   │   │   └── travel_parser.py   # Corporate travel expense parser
│   │   ├── normalizer.py          # Unit conversion, EF lookup, CO₂e calculation
│   │   ├── models.py              # IngestionJob, RawRecord
│   │   └── views.py               # Upload endpoint, job listing
│   │
│   ├── emissions/                 # Emission records & analytics
│   │   ├── models.py              # EmissionRecord (normalized output)
│   │   ├── views.py               # CRUD, review actions, stats, bulk approve
│   │   └── serializers.py
│   │
│   ├── review/                    # Audit logging
│   │   ├── models.py              # AuditLog
│   │   └── views.py               # Audit trail API
│   │
│   ├── sample_data/               # Test CSVs (H1 2024)
│   ├── sample_data2/              # Test CSVs (H2 2024)
│   ├── build.sh                   # Render build script
│   ├── manage.py
│   └── requirements.txt
│
├── frontend/
│   ├── src/
│   │   ├── api/client.js          # API client with JWT refresh logic
│   │   ├── components/
│   │   │   └── Layout.jsx         # App shell with collapsible sidebar
│   │   ├── pages/
│   │   │   ├── Login.jsx          # Authentication page
│   │   │   ├── Dashboard.jsx      # Analytics dashboard
│   │   │   ├── Upload.jsx         # File upload interface
│   │   │   └── Review.jsx         # Data review & approval table
│   │   ├── App.jsx                # Router & auth state
│   │   ├── index.css              # Complete design system
│   │   └── main.jsx               # Entry point
│   ├── package.json
│   └── vite.config.js
│
├── render.yaml                    # Render Blueprint (infra-as-code)
├── DECISIONS.md                   # 14 architectural decisions with rationale
├── MODEL.md                       # Data model design document
├── SOURCES.md                     # Emission factor sources & references
├── TRADEOFFS.md                   # Engineering tradeoffs analysis
└── README.md                      # ← You are here
```

---

## 💻 Local Development Setup

### Prerequisites

- Python 3.9+
- Node.js 16+

### 1. Backend

```bash
# From the project root
cd backend

# Create and activate virtual environment
python3 -m venv ../venv
source ../venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run database migrations
python manage.py migrate

# Seed emission factors, plant lookups, and demo accounts
python manage.py seed_data

# Start the Django dev server
python manage.py runserver 8000
```

The backend will be available at:
- **API**: http://localhost:8000/api/
- **Admin**: http://localhost:8000/admin/

### 2. Frontend

Open a new terminal:

```bash
cd frontend

# Install dependencies
npm install

# Start Vite dev server
npm run dev
```

The frontend will be available at: **http://localhost:5173/**

> The Vite dev server proxies `/api` requests to `localhost:8000` automatically — no CORS issues in local dev.

---

## 🔑 Demo Accounts

| Role | Username | Password | Capabilities |
|---|---|---|---|
| **Admin** | `admin` | `Admin@1234` | Upload, review, approve/reject, bulk actions, admin panel |
| **Analyst** | `analyst` | `password123` | Upload, view dashboard, view records _(local dev only)_ |

> On the deployed Render instance, only the `admin` account is available.

---

## 🧪 Sample Test Data

Two complete datasets are provided for testing:

### `backend/sample_data/` — H1 2024 (Jan–Jun)

| File | Source Type (in upload UI) | Records | Description |
|---|---|---|---|
| `sap_fuel_export.csv` | SAP Fuel & Procurement | 26 | Diesel & petrol purchases across 3 plants (PL01–PL03) |
| `utility_electricity.csv` | Utility Electricity | 22 | Monthly meter readings from 4 facilities, incl. MWh data |
| `travel_expenses.csv` | Corporate Travel | 28 | Flights, hotels, taxis, trains, car rentals across 9 reports |

### `backend/sample_data2/` — H2 2024 (Jul–Dec)

| File | Source Type (in upload UI) | Records | Description |
|---|---|---|---|
| `sap_fuel_export.csv` | SAP Fuel & Procurement | 30 | Adds plant PL04, LPG fuel type, GAL unit edge case |
| `utility_electricity.csv` | Utility Electricity | 31 | Adds Stuttgart R&D Lab (MTR-4001), more MWh readings |
| `travel_expenses.csv` | Corporate Travel | 35 | New employees, 5 continents, 8 currencies |

### Upload Instructions

1. Login → navigate to **Upload** page
2. Select source type from dropdown (must match the file type)
3. Upload the CSV file
4. Navigate to **Dashboard** to see the processed emissions data
5. Navigate to **Review** to approve/reject individual or bulk records

---

## 📡 API Reference

All endpoints are prefixed with `/api/`. Authentication is via JWT Bearer token.

### Authentication

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/auth/token/` | Obtain JWT access + refresh tokens |
| `POST` | `/api/auth/token/refresh/` | Refresh an expired access token |

### Core

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/core/me/` | Current user profile |
| `POST` | `/api/core/register/` | Register new user |
| `GET` | `/api/core/tenants/` | List tenants |
| `GET` | `/api/core/emission-factors/` | List emission factors |
| `GET` | `/api/core/plants/` | Plant lookup table |

### Ingestion

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/ingestion/upload/` | Upload CSV file (multipart form) |
| `GET` | `/api/ingestion/jobs/` | List ingestion jobs |
| `GET` | `/api/ingestion/jobs/{id}/errors/` | Get errors for a job |

### Emissions

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/emissions/records/` | List emission records (filterable) |
| `GET` | `/api/emissions/records/{id}/` | Record detail |
| `PATCH` | `/api/emissions/records/{id}/review/` | Approve or reject a record |
| `POST` | `/api/emissions/bulk-approve/` | Bulk approve multiple records |
| `GET` | `/api/emissions/stats/` | Aggregated dashboard statistics |

### Review

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/review/audit-log/` | Audit trail (filterable by record) |

---

## ☁️ Production Deployment (Render)

This project is deployed on Render's free tier with three services.

### Architecture on Render

```
┌─────────────────────┐     ┌────────────────────┐     ┌───────────────┐
│  Static Site        │────▶│  Web Service       │────▶│  PostgreSQL   │
│  (React/Vite)       │     │  (Django/Gunicorn)  │     │  (Free 256MB) │
│  esg-frontend       │     │  esg-backend        │     │  esg-db       │
└─────────────────────┘     └────────────────────┘     └───────────────┘
```

### Manual Setup (No Credit Card Required)

**Step 1 — PostgreSQL Database**
1. Render Dashboard → **New** → **PostgreSQL** → Name: `esg-db`, Plan: Free
2. Copy the **Internal Database URL** once available

**Step 2 — Backend Web Service**
1. **New** → **Web Service** → Connect GitHub repo
2. Root Directory: `backend` | Environment: Python 3 | Plan: Free
3. Build Command: `./build.sh`
4. Start Command: `gunicorn config.wsgi:application --bind 0.0.0.0:$PORT`
5. Environment variables:

| Key | Value |
|---|---|
| `DATABASE_URL` | _(paste Internal DB URL)_ |
| `DJANGO_SECRET_KEY` | _(click Generate)_ |
| `DJANGO_DEBUG` | `False` |
| `ALLOWED_HOSTS` | `*` |

**Step 3 — Frontend Static Site**
1. **New** → **Static Site** → Connect same repo
2. Root Directory: `frontend`
3. Build Command: `npm install && npm run build`
4. Publish Directory: `dist`
5. Environment variable:

| Key | Value |
|---|---|
| `VITE_API_URL` | `https://<your-backend>.onrender.com/api` |

> ⚠️ `VITE_API_URL` is baked into the JS bundle at build time. Changing it requires a **redeploy** (Manual Deploy → Deploy latest commit).

### Free Tier Limitations

| Resource | Constraint |
|---|---|
| Web Service | Sleeps after 15 min idle; ~30s cold start |
| PostgreSQL | 256 MB storage; deleted after 90 days of inactivity |
| Static Site | Unlimited bandwidth, always on |
| Build minutes | 500 min/month |

---

## 🧠 Design Decisions

Key architectural decisions are documented in detail in [`DECISIONS.md`](DECISIONS.md). Highlights:

1. **SAP ALV flat-file CSV** over IDoc/OData — realistic for initial client onboarding
2. **German + English header support** — SAP exports vary by system locale
3. **Haversine flight distance derivation** — GHG Protocol recommended approach when distance data is unavailable
4. **Spend-based estimation** for ground transport — flagged as `LOW` confidence
5. **Single `EmissionRecord` table** with `source_type` discriminator — avoids 3x code duplication
6. **Row-level multi-tenancy** via `tenant_id` FK — upgrade path to PostgreSQL RLS
7. **Immutability after approval** — enforced at model + API layer for audit integrity
8. **Three-tier confidence scoring** with granular quality flags

---

## 📚 Additional Documentation

| Document | Description |
|---|---|
| [`DECISIONS.md`](DECISIONS.md) | 14 architectural decisions with full rationale and PM questions |
| [`MODEL.md`](MODEL.md) | Data model design — entity relationships, field justifications |
| [`SOURCES.md`](SOURCES.md) | Emission factor sources, references, and methodology |
| [`TRADEOFFS.md`](TRADEOFFS.md) | Engineering tradeoffs — what was prioritized and what was deferred |

---

## 📄 License

This project was built as an assignment for Breathe ESG. All rights reserved.
