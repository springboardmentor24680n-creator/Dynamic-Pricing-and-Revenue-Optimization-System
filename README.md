# PricePilot AI – Dynamic Pricing Optimization & Revenue Intelligence System

**PricePilot AI** is an enterprise AI SaaS platform for dynamic pricing optimization, demand forecasting, dataset-driven analytics, and revenue intelligence. It is a full-stack application (React + Vite + Tailwind on the frontend, FastAPI + SQLAlchemy on the backend) designed for Pricing Analysts, Business Analysts, and Revenue Managers — with an enterprise-grade UI in the spirit of Salesforce, HubSpot, and Power BI.

---

## ✨ What's Inside

| Module | Status | Highlights |
|--------|--------|------------|
| **Authentication** | ✅ Complete | Register, Login, Logout, JWT access + **refresh tokens**, Forgot/Reset password, **Google Sign-In**, bcrypt hashing |
| **Role-Based Access Control** | ✅ Complete | `admin`, `pricing_manager`, `data_analyst` — route & UI guards |
| **Dashboard** | ✅ Complete | KPI cards, revenue trend, category distribution, price distribution, recent imports, latest activity — all from real APIs |
| **Product Management** | ✅ Complete | Full CRUD, search, category filter, sort, pagination, CSV export, bulk delete / bulk status, status toggle |
| **Pricing Management** | ✅ Complete | Manual price updates, price history, margin, AI recommendations with **approve / reject** workflow |
| **AI Price Prediction** | ✅ Complete | Linear Regression, Random Forest — selects the best model, real training on your data |
| **Demand Forecasting** | ✅ Complete | **Prophet** daily revenue forecasts per product with 80% confidence intervals, 6h cache, portfolio outlook |
| **Dataset Management** | ✅ Complete | Upload CSV/Excel → validate → clean → dedupe → stats → preview → **import into catalog** |
| **Reports** | ✅ Complete | Revenue, pricing, product, user, dataset reports with **CSV / Excel / PDF** export |
| **Sales Analytics** | ✅ Complete | Revenue trends, channel/region/category breakdown over configurable windows |
| **User Management** | ✅ Admin only | Create, update, delete, activate/deactivate, reset passwords, assign roles |
| **Settings** | ✅ Complete | Profile, password change, dark/light theme, notification preferences |

---

## 🚀 Quick Start

### 1. Backend

```bash
cd backend
python -m venv venv

# Windows
source venv/Scripts/activate
# macOS / Linux
# source venv/bin/activate

pip install -r requirements.txt

# Configure environment (see .env.example)
cp .env.example .env

# Start the API (auto-runs schema migration + seeds on first boot)
python -m uvicorn app.main:app --host 0.0.0.0 --port 8001
```

- API: `http://localhost:8001`
- Swagger docs: `http://localhost:8001/docs`

### 2. Frontend

```bash
cd frontend
npm install
npm run dev
```

- App: `http://localhost:5173`
- Vite proxies `/api` and `/loaders` to the backend on port 8001 — no CORS issues in development.

### 3. Demo Admin

The database is seeded with a demo admin on first startup:

| Field | Value |
|-------|-------|
| Username | `admin` |
| Password | `admin123` |

Public self-registration always creates a `data_analyst` account — role assignment is **admin-only** (via the Users page / `POST /api/v1/users/`).

---

## 🧰 Tech Stack

### Backend

| Technology | Version | Purpose |
|-----------|---------|---------|
| Python | 3.12+ | Core language |
| FastAPI | 0.115.6 | Web framework & REST API |
| SQLAlchemy | 2.0.36 | ORM |
| PostgreSQL | 15+ | Primary database (production-ready) |
| SQLite | — | Zero-config fallback (set `DATABASE_URL=sqlite:///...`) |
| MongoDB / Motor | 4.9 / 3.6 | Audit/document store (connects on startup) |
| Pydantic + pydantic-settings | 2.13 | Validation & configuration |
| Passlib + bcrypt | 1.7.4 | Password hashing |
| python-jose | 3.3.0 | JWT (access + refresh) |
| Pandas / NumPy | 2.2.3 / 1.26 | Dataset processing |
| openpyxl | 3.1.5 | Excel parsing/export |
| scikit-learn | 1.6.0 | ML price optimization |
| scikit-learn | 1.6.0 | ML price optimization (Linear Regression, Random Forest) |
| Prophet | 1.1.6 | Demand forecasting |
| fpdf2 | 2.8.7 | PDF report export |
| google-auth | 2.56.2 | Server-side Google ID token verification |

### Frontend

| Technology | Version | Purpose |
|-----------|---------|---------|
| React | 19.2 | UI framework |
| Vite | 6.4 | Build tool & dev server |
| Tailwind CSS | 3.4 | Utility-first styling (enterprise blue theme) |
| React Router DOM | 7.18 | Client-side routing |
| Axios | 1.18 | HTTP client with JWT interceptor + auto token refresh |
| React Hook Form | 7.83 | Form validation |
| Recharts | 2.15 | Charts & graphs |
| Lucide React | 0.469 | Icons |
| @react-oauth/google | 0.13 | Official Google Sign-In button |

---

## 🔐 Authentication & Security

### Flow

```
Register ──► Hash password (bcrypt) ──► Store in PostgreSQL
Login ──► Verify credentials ──► Generate JWT (access + refresh) ──► Client stores tokens
Protected Routes ──► Axios attaches Bearer token ──► Role validation (401 / 403)
Token expiry ──► Axios interceptor silently refreshes via /auth/refresh ──► Retry request
```

### Key behaviors

- **JWT access tokens** expire in 30 minutes; **refresh tokens** in 7 days. The Axios response interceptor automatically refreshes on `401` and replays the queued request (single-flight refresh with subscriber queue).
- **Google Sign-In** (`/api/v1/auth/google`) verifies the ID token **server-side** with Google's official `google-auth` library — signature, audience, issuer, expiry, and verified email. Claims come from the verified token, never from the frontend. Users are auto-created (`is_google_user=True`, `hashed_password=NULL`) or logged in if the email already exists.
- A code-based OAuth flow (`/google/authorize` + `/google/callback`) is also implemented for server-to-server redirect flows.
- **Passwords are hashed with bcrypt** via Passlib — never stored in plain text.
- **Roles**: `admin` / `pricing_manager` / `data_analyst`. Missing Authorization headers return **401** (with `WWW-Authenticate`); authenticated-but-unauthorized users get **403**.
- **Security hardening**: public registration cannot self-assign `admin` (always downgraded to `data_analyst`), self-deactivation/deletion is blocked, and the ML price engine is restricted to admin/pricing roles.

### Environment variables

**Backend** (`.env`):

```env
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/dynamic_pricing
SECRET_KEY=change-me-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7
CORS_ORIGINS=["http://localhost:5173","http://localhost:3000"]

# Google OAuth (optional — Google button shows only when set)
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
GOOGLE_REDIRECT_URI=http://localhost:8001/api/v1/auth/google/callback

# MongoDB (optional — connector skips gracefully if unavailable)
MONGODB_URL=mongodb://localhost:27017
MONGODB_DB_NAME=pricepilot_ai
```

**Frontend** (`frontend/.env`):

```env
VITE_GOOGLE_CLIENT_ID=your-google-client-id.apps.googleusercontent.com
```

---

## 🏗 Architecture

```
┌───────────────────────────────────────────────────────────────┐
│                   FRONTEND (React + Vite + Tailwind)           │
│  Pages: Login · Register · Dashboard · Products · Pricing ·    │
│         AI Prediction · Datasets · Reports · Users · Settings  │
│         ┌──────────────────────────────────────────────────┐  │
│         │  AuthContext / ThemeContext / ToastContext        │  │
│         │  Axios client: JWT interceptor + auto refresh     │  │
│         └───────────────────────┬──────────────────────────┘  │
└─────────────────────────────────┼─────────────────────────────┘
                                  │ HTTP (Vite proxy /api, /loaders)
┌─────────────────────────────────┼─────────────────────────────┐
│                    BACKEND (FastAPI)                           │
│  Routers: auth · users · products · pricing · datasets · ai ·  │
│           dashboard · reports · sales · activity · loaders     │
│         ┌──────────────────────────────────────────────────┐  │
│         │  Service layer (business logic)                   │  │
│         │  Auth · Product · Pricing · DatasetProcessing ·    │  │
│         │  ML (RF/XGB/LR) · Forecast (Prophet) · Report ·   │  │
│         │  Dashboard · Sales · Activity · Google OAuth       │  │
│         └───────────────────────┬──────────────────────────┘  │
│                                 │                              │
│  PostgreSQL ── Users, Products, Sales, PricingHistory,        │
│                Recommendations, Datasets, ImportLogs,          │
│                ActivityLogs, ForecastRuns                      │
│  MongoDB ── audit/document store (optional)                    │
└───────────────────────────────────────────────────────────────┘
```

### Key design decisions

1. **Non-destructive startup migration** (`migrate_schema` in `app/database.py`) — reconciles existing PostgreSQL/SQLite schemas against the current SQLAlchemy models by *adding* missing columns (never dropping data), makes `hashed_password` nullable for Google-only accounts, creates the `google_id` index, and backfills legacy renamed columns. Idempotent — safe to run on every boot.
2. **Service layer** isolates business logic from routers; the ML, forecasting, and dataset-pipeline services are self-contained so future modules plug in without touching existing code.
3. **Real ML, not mockups** — price optimization trains Random Forest / Linear Regression on your products and picks the best model; Prophet trains per product with confidence intervals. With insufficient data the API returns a clear message instead of fabricating numbers.
4. **Vite dev proxy** avoids CORS during development; `VITE_API_URL` points the frontend at a deployed backend in production.
5. **Feature-flag friendly** — hidden future modules (`frontend/src/modules/future/`) are preserved in the codebase and gated in `src/config/features.js`.

---

## 🔌 Backend API (`/api/v1`)

Interactive docs at **`http://localhost:8001/docs`** (Swagger UI). Auth-protected endpoints require `Authorization: Bearer <access_token>`.

### Authentication (`/auth`)
| Method | Endpoint | Access | Description |
|--------|----------|--------|-------------|
| `POST` | `/auth/register` | Public | Register (always creates `data_analyst`) |
| `POST` | `/auth/login` | Public | Login → access + refresh tokens |
| `POST` | `/auth/refresh` | Public | Exchange refresh token for a new pair |
| `GET` | `/auth/me` | JWT | Current profile |
| `PUT` | `/auth/me` | JWT | Update profile (name, email, notifications) |
| `POST` | `/auth/change-password` | JWT | Change own password |
| `GET` | `/auth/google/authorize` | Public | OAuth consent URL |
| `GET` | `/auth/google/callback` | Public | OAuth code callback → JWT |
| `POST` | `/auth/google` | Public | Verify Google ID token → login/register → JWT |
| `POST` | `/auth/forgot-password` | Public | Request reset token |
| `POST` | `/auth/reset-password` | Public | Set new password with token |

### Dashboard
| Method | Endpoint | Access | Description |
|--------|----------|--------|-------------|
| `GET` | `/dashboard/` | JWT | KPIs, revenue trend, categories, price distribution, recent activity |

### Products (`/products`)
| Method | Endpoint | Access | Description |
|--------|----------|--------|-------------|
| `GET` | `/products/` | JWT | List (pagination, search, category, status, sort) |
| `GET` | `/products/{id}` | JWT | Single product |
| `POST` | `/products/` | admin / pricing_manager | Create |
| `PUT` | `/products/{id}` | admin / pricing_manager | Update |
| `PATCH` | `/products/{id}/status` | admin / pricing_manager | Toggle active/inactive |
| `DELETE` | `/products/{id}` | admin | Delete |
| `POST` | `/products/bulk-delete` | admin | Bulk delete |
| `POST` | `/products/bulk-status` | admin / pricing_manager | Bulk status update |
| `GET` | `/products/categories/all` | JWT | Category list |
| `GET` | `/products/export/csv` | JWT | Export filtered products as CSV |

### Pricing (`/pricing`)
| Method | Endpoint | Access | Description |
|--------|----------|--------|-------------|
| `PUT` | `/pricing/products/{id}/price` | admin / pricing_manager | Manual price update + history entry |
| `GET` | `/pricing/products/{id}/history` | JWT | Price change history |
| `GET` | `/pricing/recommendations` | JWT | AI recommendations (filter by status) |
| `POST` | `/pricing/recommendations/{id}/approve` | admin / pricing_manager | Apply recommended price |
| `POST` | `/pricing/recommendations/{id}/reject` | admin / pricing_manager | Reject recommendation |

### AI Engine (`/ai`)
| Method | Endpoint | Access | Description |
|--------|----------|--------|-------------|
| `GET` | `/ai/status` | JWT | Engine status, model availability, data coverage |
| `GET` | `/ai/forecast` | JWT | Portfolio demand outlook (fast trend analysis) |
| `GET` | `/ai/forecast/{id}` | JWT | Prophet forecast (horizon 7–180 days, 80% CI, cached 6h, `force=true` retrains) |
| `GET` | `/ai/optimize/{id}` | admin / pricing_manager | Price optimization; `include_forecast=true` folds demand signal in |
| `POST` | `/ai/optimize/{id}/save` | admin / pricing_manager | Persist recommendation to approval workflow |
| `GET` | `/ai/batch-optimize` | admin / pricing_manager | Optimize whole catalog (optional category filter) |
| `POST` | `/ai/predict-revenue/{id}` | admin / pricing_manager | Revenue impact of a proposed price |

### Datasets (`/datasets`)
| Method | Endpoint | Access | Description |
|--------|----------|--------|-------------|
| `GET` | `/datasets/` | JWT | List processed datasets + stats |
| `POST` | `/datasets/upload` | admin / pricing_manager | Upload CSV/Excel → validate → clean → dedupe → stats → store |
| `POST` | `/datasets/{id}/import` | admin / pricing_manager | Import processed dataset into the product catalog |
| `GET` | `/datasets/{id}/preview` | JWT | Preview rows, pipeline steps, statistics |
| `GET` | `/datasets/stats` | JWT | Summary stats + import logs |
| `GET` | `/datasets/types` | JWT | Supported dataset type templates |

### Users (`/users`) — admin only
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/users/` | List all users |
| `POST` | `/users/` | Create user (any role) |
| `PUT` | `/users/{id}` | Update role / name / email / status |
| `POST` | `/users/{id}/reset-password` | Admin resets a password |
| `PUT` | `/users/{id}/status` | Activate / deactivate |
| `DELETE` | `/users/{id}` | Delete user |

### Reports (`/reports`)
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/reports/revenue` | Revenue analysis |
| `GET` | `/reports/pricing-performance` | Pricing performance (over/under-priced) |
| `GET` | `/reports/product-performance` | Product performance |
| `GET` | `/reports/users` | Users report |
| `GET` | `/reports/datasets` | Datasets report |
| `GET` | `/reports/export?report_type=…&format=csv\|xlsx\|pdf` | Download report |

### Sales & Activity
| Method | Endpoint | Access | Description |
|--------|----------|--------|-------------|
| `GET` | `/sales/analytics?days=…` | JWT | Revenue analytics over a window (1–365 days) |
| `GET` | `/activity/logs` | JWT | Recent activity log |

> **Note:** The legacy loaders and the health endpoint below are mounted at the **root** (`/loaders/…`, `/health`), not under `/api/v1`.

### Data loaders (legacy, server-side CSVs)
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/loaders/retail-pricing` · `/loaders/retail-pricing/upload` | Load/upload retail pricing CSV |
| `POST` | `/loaders/ecommerce-sales` · `/loaders/ecommerce-sales/upload` | Load/upload e-commerce sales CSV |

### System
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | Health check (status, version) |

---

## 🖥 Frontend Pages & Routes

| Page | Route | Access | Description |
|------|-------|--------|-------------|
| Login | `/login` | Public | Username/password + official Google button |
| Register | `/register` | Public | Self-registration (data_analyst) |
| Forgot Password | `/forgot-password` | Public | Request reset |
| Reset Password | `/reset-password` | Public | Set new password |
| Dashboard | `/dashboard` | JWT | KPI cards, revenue trend, category & price distribution, activity |
| Products | `/products` | JWT | Enterprise data table — search, filters, sort, pagination, CRUD modals, bulk actions, CSV export, small thumbnails |
| Pricing | `/pricing` | JWT | Manual price updates, margin, price history, AI recommendation review (approve/reject) |
| AI Prediction | `/ai` | JWT | Model status, price optimization with factors/confidence/revenue impact, **Forecasting tab** with confidence bands |
| Datasets | `/datasets` | JWT | Upload, pipeline status, statistics, health score, preview table, import to catalog, import logs |
| Reports | `/reports` | JWT | Revenue/pricing/product/user/dataset reports + CSV/Excel/PDF download |
| Users | `/users` | Admin | User CRUD, roles, activate/deactivate, reset password |
| Settings | `/settings` | JWT | Profile, password, dark/light theme, notifications |

### UI features
- Enterprise design system — professional spacing, Inter typography, blue primary palette, rounded cards, soft shadows.
- Full **dark / light mode** (persisted, respects system preference).
- Loading spinners, **skeleton loaders**, success/error **toasts**, and **confirmation dialogs** — no ugly default alerts.
- Responsive layout, animated transitions, and a protected-route guard that redirects unauthenticated users to `/login`.

---

## 🗄 Database Schema (PostgreSQL)

| Table | Purpose |
|-------|---------|
| `users` | Accounts — `username`, `email`, `hashed_password` (nullable), `role`, `is_active`, `google_id`, `profile_picture`, `is_google_user`, `notifications_enabled` |
| `products` | Catalog — name, sku, category, base/current/cost price, stock, revenue, status, image_url |
| `sales` | Transactions — product, quantity, unit price, total, `sale_date`, channel, region, `customer_segment` |
| `pricing_history` | Old/new price, AI suggested price, reason, changed_by |
| `recommendations` | AI suggestions — recommended price, confidence, `factors_considered`, `expected_revenue_impact`, status (pending/applied/rejected) |
| `datasets` | Processed uploads — rows, columns, missing values, duplicates, health score, column names, preview rows, pipeline steps |
| `import_logs` | Import/upload audit trail |
| `activity_logs` | User actions across the app |
| `forecast_runs` | Prophet forecast cache (per product/horizon) |

All relationships use proper foreign keys, unique constraints (username, email, sku), and indexes (including `ix_users_google_id`).

---

## 🧠 AI Engine — How It Works

### Price optimization
1. `GET /api/v1/ai/status` — reports data coverage, available models, and existing recommendations.
2. `GET /api/v1/ai/optimize/{product_id}` — builds features from price, cost, stock, demand, category, and historical sales; trains Random Forest and Linear Regression (with train/test split where data allows) and picks the **best-performing model**.
3. Returns **current vs suggested price, confidence, expected revenue impact, price difference, reason, and key factors**. With insufficient data, it returns a clear explanation instead of a guess.
4. `include_forecast=true` folds the Prophet demand signal into the suggestion (conservative in declining demand, room to test higher in rising demand).
5. Recommendations can be saved (`/ai/optimize/{id}/save`) into the approval workflow and then **approved** (price applied + history entry) or **rejected** on the Pricing page.

### Demand forecasting (Prophet)
- `GET /api/v1/ai/forecast/{product_id}?horizon=30` trains a Prophet model on the product's daily revenue history and returns `yhat` / `yhat_lower` / `yhat_upper` **80% confidence intervals**, the historical series, and growth metrics.
- Cached for **6 hours** per horizon; `force=true` retrains.
- `GET /api/v1/ai/forecast` returns a fast portfolio outlook across the whole catalog.

---

## 📊 Dataset Pipeline

Uploads (CSV or Excel) run through a real processing pipeline and the results are stored:

```
Upload ──► Validate columns & types ──► Clean missing values
   ──► Remove duplicate rows ──► Convert data types ──► Generate statistics
   ──► Build preview table ──► Store processed dataset ──► Import into catalog
```

Reported per dataset: **rows, columns, missing values, duplicate count, category count, average price, total revenue, top products, and a health score**. Preview rows and the pipeline steps are stored and visible in the UI.

**Supported CSV column aliases** (case-insensitive): `name|product_name`, `sku|product_sku`, `category|product_category`, `current_price|price|selling_price`, `base_price|original_price`, `cost_price|cost`, `stock_quantity|stock|quantity`, `revenue`, `description`, `image_url|image|product_image`. Duplicate SKUs are skipped on import.

---

## 📦 Sample Data & Seed Scripts

The backend auto-seeds on first startup (`seed_data.py`): **16 realistic products** with matching Unsplash images, pricing history, 30 days of sales transactions, a demo admin (`admin` / `admin123`), and activity logs. Seeding is idempotent — it skips if products already exist.

For richer AI training, two generator scripts produce deterministic (seed 42) datasets:

| Script | Output |
|--------|--------|
| `backend/scripts/generate_retail_dataset.py` | **520-product retail catalog** (`backend/data_uploaded/retail_catalog_520.csv`) across 14 categories — prices, costs, stock, 6-month revenue estimates |
| `backend/scripts/seed_sales_history.py` | **180 days of daily sales** for every product (non-destructive, skips days that already have sales) |

```bash
cd backend
source venv/Scripts/activate

python scripts/generate_retail_dataset.py   # writes retail_catalog_520.csv
python scripts/seed_sales_history.py        # backfills 6 months of sales
```

Load the generated catalog through the **Datasets page** (upload → import) or the API so the ML models and charts train on 500+ products.

---

## 📁 Project Structure

```
backend/
├── app/
│   ├── main.py               # FastAPI entry (lifespan: migrate → create_all → seed → Mongo)
│   ├── config.py             # Pydantic settings (.env)
│   ├── database.py           # Engine, session, non-destructive schema migration
│   ├── mongodb.py            # MongoDB connector (optional)
│   ├── dependencies.py       # Auth guards (get_current_user, require_role)
│   ├── utils.py              # Hashing, JWT helpers
│   ├── seed_data.py          # 16 products + demo admin + sales + activity
│   ├── models/               # user, product, sales, pricing_history,
│   │                         #   recommendation, dataset, activity_log, forecast
│   ├── schemas/              # Pydantic models per module
│   ├── services/             # auth, product, pricing_service, dataset_service,
│   │                         #   ml_service, forecast_service, report_service,
│   │                         #   sales_service, activity_service, google_oauth, dashboard
│   ├── routers/              # auth, users, products, pricing, datasets, ai,
│   │                         #   dashboard, reports, sales, activity
│   └── loaders/              # base/retail/ecommerce CSV loaders
├── scripts/
│   ├── generate_retail_dataset.py   # 520-product CSV generator
│   └── seed_sales_history.py        # 180-day sales backfill
├── data_uploaded/            # Sample CSVs
├── requirements.txt
└── .env.example

frontend/
├── src/
│   ├── main.jsx / App.jsx    # Entry + routes (protected/admin/public guards)
│   ├── index.css             # Tailwind design system
│   ├── api/client.js         # Axios + JWT interceptor + auto-refresh + typed APIs
│   ├── config/features.js    # Feature flags
│   ├── context/              # AuthContext, ThemeContext, ToastContext
│   ├── components/           # Layout, Sidebar, Header, shared UI
│   ├── pages/                # Login, Register, Forgot/ResetPassword, Dashboard,
│   │                         #   Products, Pricing, AIPrediction, Datasets,
│   │                         #   Reports, Users, Settings
│   └── modules/future/       # Gated future modules (preserved)
├── vite.config.ts            # Dev proxy /api + /loaders → :8001
└── package.json
```

---

## 🧪 Verification

```bash
# Health check
curl http://localhost:8001/health

# Login → token
TOKEN=$(curl -s -X POST http://localhost:8001/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}' \
  | python -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

# Dashboard with real data
curl -s http://localhost:8001/api/v1/dashboard/ \
  -H "Authorization: Bearer $TOKEN" | python -m json.tool

# AI engine status
curl -s http://localhost:8001/api/v1/ai/status \
  -H "Authorization: Bearer $TOKEN" | python -m json.tool

# Optimize a product's price
curl -s "http://localhost:8001/api/v1/ai/optimize/1?include_forecast=true" \
  -H "Authorization: Bearer $TOKEN" | python -m json.tool

# Prophet demand forecast
curl -s "http://localhost:8001/api/v1/ai/forecast/1?horizon=30" \
  -H "Authorization: Bearer $TOKEN" | python -m json.tool

# Download a PDF report
curl -s -o report.pdf "http://localhost:8001/api/v1/reports/export?report_type=revenue&format=pdf" \
  -H "Authorization: Bearer $TOKEN"
```

**Frontend**: `cd frontend && npm run build` (production build) — then serve `dist/` behind any static host.

---

## 📝 License

MIT License — see [LICENSE](LICENSE) for details.

---

<div align="center">
  <sub>PricePilot AI — Dynamic Pricing Optimization & Revenue Intelligence System</sub>
</div>
