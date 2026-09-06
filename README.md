<div align="center">

# 💰 PricePilot AI

### Dynamic Pricing & Revenue Intelligence Platform for Retail

*Historical sales data → ML demand forecasting → elasticity & profit optimization → competitor & news intelligence → generative AI explanations — all in one dashboard.*

![Next.js](https://img.shields.io/badge/Next.js-14-black?logo=next.js)
![React](https://img.shields.io/badge/React-18-61DAFB?logo=react&logoColor=white)
![TypeScript](https://img.shields.io/badge/TypeScript-3178C6?logo=typescript&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white)
![LightGBM](https://img.shields.io/badge/LightGBM-%E2%9C%94-brightgreen)
![XGBoost](https://img.shields.io/badge/XGBoost-%E2%9C%94-brightgreen)

</div>

---

## 📌 The Core Question

> **What price should we set for this product now, and why?**

PricePilot AI answers this by combining machine learning demand forecasting, price elasticity modeling, profit optimization, and real-time market intelligence into a single explainable recommendation.

---

## 📑 Table of Contents

- [What the System Does](#-what-the-system-does)
- [High-Level Architecture](#-high-level-architecture)
- [Technology Stack](#-technology-stack)
- [Project Structure](#-project-structure)
- [Dataset Description](#-dataset-description)
- [Feature Engineering](#-feature-engineering)
- [Machine-Learning Workflow](#-machine-learning-workflow)
- [Price Elasticity & Optimization](#-price-elasticity--optimization)
- [Multi-Agent AI System](#-multi-agent-ai-system)
- [Backend API](#-backend-api)
- [Frontend Modules](#-frontend-modules)
- [Request Flow](#-complete-single-product-request-flow)
- [Installation](#-installation)
- [Environment Variables](#-environment-variables)
- [Running the Project](#-running-the-project)
- [Fallback Behavior](#-fallback-behavior)
- [Implementation Notes](#-important-implementation-notes)
- [Future Improvements](#-future-improvements)
- [Security Recommendations](#-security-recommendations-before-production)
- [Summary](#-summary)

---

## 🚀 What the System Does

For a selected product, PricePilot AI:

| Step | Action |
|:---:|---|
| 1 | Loads product and historical sales data |
| 2 | Creates pricing, promotion, calendar, and market features |
| 3 | Trains LightGBM, XGBoost, and a time-series Ridge model |
| 4 | Combines model predictions using a weighted ensemble |
| 5 | Applies price elasticity to estimate demand at different prices |
| 6 | Calculates projected revenue and profit for 16 candidate prices |
| 7 | Selects the candidate price with the highest projected profit |
| 8 | Calculates forecast horizons, inventory burn rate, stockout risk, and reorder quantity |
| 9 | Uses Tavily and News API to add current market context |
| 10 | Uses OpenRouter as a master AI agent to generate an executive explanation |
| 11 | Displays the results through a Next.js dashboard |

---

## 🏗️ High-Level Architecture

```text
products_catalog.csv
retail_pricing_dataset.csv
          │
          ▼
    Data Loading
          │
          ▼
  Feature Engineering
          │
          ▼
 LightGBM + XGBoost +
 Time-Series Ridge Model
          │
          ▼
  Weighted Demand Ensemble
          │
          ▼
 Price Elasticity + Profit Optimization
          │
          ├──────────────────┬──────────────────┐
          ▼                  ▼                  
 Tavily Market Search   News API Agent
 Tavily Seasonal Search        │
          │                    │
          └────────┬───────────┘
                    ▼
           OpenRouter AI Brain
                    │
                    ▼
          Explainable Recommendation
                    │
                    ▼
              Next.js Dashboard
```

---

## 🧰 Technology Stack

### Frontend
| Technology | Purpose |
|---|---|
| Next.js 14 | Application framework |
| React 18 | UI library |
| TypeScript | Type safety |
| Tailwind CSS | Styling |
| Recharts | Data visualization |
| Lucide React | Icons |
| Clerk | Authentication |

### Backend
| Technology | Purpose |
|---|---|
| Python | Core language |
| FastAPI | API framework |
| Uvicorn | ASGI server |
| Pandas / NumPy | Data processing |
| Scikit-learn | ML utilities |
| LightGBM / XGBoost | Gradient-boosted models |
| Requests | HTTP client |
| python-dotenv | Environment config |

### External Services
| Service | Role |
|---|---|
| **OpenRouter API** | Master AI explanation agent |
| **Tavily AI Search API** | Competitor and market research |
| **News API** | Current retail and category news |
| **Clerk** | Authentication and user identity |

---

## 📁 Project Structure

```text
Price pilot AI/
│
├── backend/
│   ├── main.py
│   ├── ml_engine.py
│   ├── agent_orchestrator.py
│   ├── catalog_datasets.py
│   ├── generate_and_save_dataset.py
│   └── requirements.txt
│
├── src/
│   ├── app/
│   │   ├── page.tsx
│   │   ├── layout.tsx
│   │   └── globals.css
│   │
│   └── components/
│       ├── Header.tsx
│       ├── OverviewDashboard.tsx
│       ├── ProductCatalog.tsx
│       ├── SingleProductPredictionModal.tsx
│       ├── PredictAllModal.tsx
│       ├── CompetitorAnalysis.tsx
│       ├── RevenueSimulator.tsx
│       ├── SeasonalReports.tsx
│       ├── AdminUserManagement.tsx
│       ├── PendingApprovalView.tsx
│       └── ClerkAuthWrapper.tsx
│
├── products_catalog.csv
├── retail_pricing_dataset.csv
├── package.json
├── package-lock.json
├── next.config.js
├── tailwind.config.js
├── tsconfig.json
├── .env.example
└── README.md
```

---

## 🗂️ Dataset Description

### `products_catalog.csv`
Current state of the product catalog — **10 products** with fields including:

- Product ID and SKU
- Product name and category
- Current price · Cost price
- Competitor price and competitor name
- Inventory
- Historical 30-day sales
- Rating
- Demand trend
- Elasticity score
- Discount percentage
- Seasonality factor
- Last updated date

### `retail_pricing_dataset.csv`
**~3,650 historical daily records** across all products, including:

- Date
- Product and category information
- Product price and cost price
- Competitor price
- Discount percentage
- Promotion flag
- Day of week · Month · Weekend flag · Holiday flag
- Units sold · Revenue · Profit
- Elasticity score

> 💡 **Note:** the catalog represents the current business state; the historical dataset represents past demand behavior.

---

## ⚙️ Feature Engineering

Derived features created in `backend/ml_engine.py`:

```text
price_diff      = competitor_price - price
price_ratio     = price / competitor_price
discount_factor = 1 - discount_percent / 100
effective_price = price * discount_factor
day_index       = chronological record index
```

**Final model features:**

```text
price               competitor_price     discount_percent
promotion_flag      day_of_week          month
is_weekend          is_holiday           price_diff
price_ratio         effective_price      day_index
```

---

## 🤖 Machine-Learning Workflow

| Model | Role | Ensemble Weight |
|---|---|:---:|
| **LightGBM** | Fast gradient-boosted tree regression for tabular pricing/demand features | **40%** |
| **XGBoost** | Regularized non-linear regression for price-response and demand prediction | **35%** |
| **Time-Series (Ridge)** | Labeled "Prophet/time-series" in the UI; uses day index, month, day-of-week, weekend & holiday flags | **25%** |

### Training and Evaluation
Historical data is split **chronologically**:

```text
80% training data   │   20% validation data
```

Evaluation metrics: **MAE** (Mean Absolute Error) · **RMSE** (Root Mean Squared Error) · **R²** (coefficient of determination)

### Ensemble Prediction

```text
Ensemble Demand =
    0.40 × LightGBM Demand
  + 0.35 × XGBoost Demand
  + 0.25 × Time-Series Demand
```

---

## 📈 Price Elasticity & Optimization

Price elasticity estimates how demand changes when price changes.

For every candidate price:

```text
Estimated Demand = Ensemble Demand × (Current Price / Candidate Price) ^ Elasticity

Projected Revenue = Estimated Demand × Candidate Price

Projected Profit  = Estimated Demand × (Candidate Price − Cost Price)
```

The engine evaluates **16 evenly spaced candidate prices** between:

```text
Minimum price = max(Cost Price × 1.05, Current Price × 0.75)
Maximum price = Current Price × 1.35
```

✅ The price with the **highest projected profit** is returned as the optimal price.

---

## 🧠 Multi-Agent AI System

Implemented in `backend/agent_orchestrator.py`.

### 1️⃣ Tavily Market Search Agent
Searches the web for product and category pricing trends. Provides:
- Market trend · Market signal
- Competitor pricing context
- Estimated price impact
- Strategic pricing action
- Source URL

### 2️⃣ Tavily Seasonal Search Agent
Searches for seasonal demand periods and shopping events:
- Q4 holiday demand
- Black Friday & Cyber Week
- Back-to-school demand
- Weekend shopping spikes
- Post-holiday clearance

Provides suggested timing and reason for price adjustment.

### 3️⃣ News API Agent
Fetches recent retail, e-commerce, and category news. Classifies text via keyword-based rules into:

`High Promo Season` · `Bullish` · `Stable`

Returns headline, source, date, trend factor, price impact, and business takeaway.

### 4️⃣ OpenRouter Brain Agent
Master AI explanation layer. Default model:

```text
openai/gpt-oss-20b:free
```

**Prompt includes:** product name, category, current price, cost price, competitor price, optimal price, recommended price change, market trend, news trend.

> Returns a concise executive pricing summary — it *explains* the recommendation but does **not** replace the numerical ML and optimization calculations.

---

## 🔌 Backend API

Implemented in `backend/main.py`.

| Method & Endpoint | Description |
|---|---|
| `GET /api/health` | Backend status, product count, training row count, model names, agent names |
| `GET /api/products` | Products loaded from `products_catalog.csv` |
| `GET /api/predict/single/{product_id}` | Full prediction + multi-agent pipeline for one product |
| `POST /api/predict/all` | Batch prediction for every catalog product |
| `GET /api/seasonal-reports` | Weekly demand patterns, seasonal factors, inventory turnover alerts |
| `GET /api/competitor-analysis` | Classifies products as *Underpriced*, *Premium*, or *Competitive* |
| `GET /api/admin/pending-users` | List pending user approvals |
| `POST /api/admin/approve-user` | Approve a pending user |
| `POST /api/admin/reject-user` | Reject a pending user |

### 📦 Single-Product Prediction Response Includes
- Optimal price · Price change percentage
- Margin before and after
- Model predictions and metrics
- Forecast horizons
- Seasonal report
- Inventory intelligence
- Revenue optimization curve
- Tavily results · News API results
- OpenRouter summary

### 📦 Batch Prediction Response Includes
Product-level results + total projected revenue before and after optimization.

---

## 🖥️ Frontend Modules

| Module | Description |
|---|---|
| **Overview Dashboard** | Revenue trends, demand index, model info, ensemble info, agent status |
| **Product Catalog** | Products, categories, current prices, inventory, competitor prices, demand trends, elasticity scores |
| **Single-Product Prediction Modal** | Optimal price, price change, model comparison, revenue curve, short/medium/long-term forecasts, seasonal analysis, inventory risk, competitor & news insights, OpenRouter explanation |
| **Competitor Analysis** | Price comparisons and market position |
| **Revenue Simulator** | Test price changes & promotional discounts → estimated revenue/margin outcomes |
| **Seasonal Reports** | Weekly demand patterns, seasonal demand factors, inventory alerts |
| **Admin User Management** | Approve or reject pending users |

---

## 🔄 Complete Single-Product Request Flow

```text
 1. User selects a product in the Next.js interface.
 2. Frontend calls /api/predict/single/{product_id}.
 3. FastAPI verifies the product.
 4. Historical records for the product are loaded.
 5. Features are engineered.
 6. Data is split chronologically.
 7. LightGBM, XGBoost, and Ridge time-series models are trained.
 8. Each model predicts daily demand.
 9. Predictions are combined using the ensemble weights.
10. Sixteen candidate prices are evaluated.
11. The highest-profit candidate becomes the optimal price.
12. Forecast horizons are generated.
13. Inventory burn rate and stockout risk are calculated.
14. Tavily market search is executed.
15. Tavily seasonal search is executed.
16. News API is queried.
17. The results are combined into an OpenRouter prompt.
18. OpenRouter creates the executive summary.
19. FastAPI returns the complete response.
20. Next.js displays the recommendation and supporting evidence.
```

---

## 🛠️ Installation

### Prerequisites
- Node.js 18 or newer
- npm
- Python 3.10 or newer

### 1. Install Frontend Dependencies
```bash
npm install
```

### 2. Install Backend Dependencies

```bash
python -m venv .venv
```

Activate the environment:

**Windows PowerShell**
```powershell
.\.venv\Scripts\Activate.ps1
```

**macOS/Linux**
```bash
source .venv/bin/activate
```

Install requirements:
```bash
pip install -r backend/requirements.txt
```

---

## 🔑 Environment Variables

Create a `.env` file in the project root (use `.env.example` as a template):

```env
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=your_clerk_publishable_key
CLERK_SECRET_KEY=your_clerk_secret_key

OPENROUTER_API_KEY=your_openrouter_key
OPENROUTER_MODEL=openai/gpt-oss-20b:free

TAVILY_API_KEY=your_tavily_key
NEWS_API_KEY=your_news_api_key

NEXT_PUBLIC_API_URL=http://127.0.0.1:8000
```

> ⚠️ **Never commit or upload `.env`.** It may contain private API keys. Use `.env.example` when sharing the project.

---

## ▶️ Running the Project

### Start the Backend
From the project root:
```bash
python backend/main.py
```
Runs at: `http://127.0.0.1:8000`
Health check: `http://127.0.0.1:8000/api/health`

### Start the Frontend
In a second terminal:
```bash
npm run dev
```
Available at: `http://localhost:3000`

### Production Build
```bash
npm run build
npm start
```

---

## 🛡️ Fallback Behavior

The application includes development fallbacks so the UI keeps working without all external API keys:

| Service | If Unavailable |
|---|---|
| Product API | Frontend uses fallback catalog data |
| Tavily | Predefined market insights are returned |
| News API | Predefined news insights are returned |
| OpenRouter | A predefined executive summary is returned |

---

## 📝 Important Implementation Notes

- The backend **retrains models during prediction requests** — production should add model caching or scheduled training.
- User approval data is **stored in memory** and is lost when the backend restarts.
- Product and training data are **CSV-based** rather than stored in a database.
- The frontend batch prediction modal currently performs a **simplified local simulation**, although the backend contains a complete `/api/predict/all` endpoint.
- The time-series component is implemented using **Ridge regression** with seasonal features, although the interface labels it as "Prophet/time-series."
- The backend currently **allows all CORS origins** for development.
- API calls depend on valid keys and network access.
- The system **recommends** prices but does **not yet automatically publish** them to a real commerce platform.

---

## 🔮 Future Improvements

- [ ] Add PostgreSQL or another persistent database
- [ ] Add scheduled model retraining and model caching
- [ ] Store recommendations and actual sales outcomes
- [ ] Add A/B testing for pricing strategies
- [ ] Add model drift monitoring
- [ ] Add SHAP-based model explanations
- [ ] Add persistent role-based authorization in the backend
- [ ] Connect to live inventory and order systems
- [ ] Add automatic price publishing with approval controls
- [ ] Replace development fallbacks with production error handling
- [ ] Use a dedicated Prophet or other advanced time-series implementation if required
- [ ] Deploy the frontend and backend using Docker and cloud infrastructure

---

## 🔒 Security Recommendations Before Production

- [ ] Never expose API keys in the frontend
- [ ] Restrict CORS to trusted frontend domains
- [ ] Move approval and product data to a secure database
- [ ] Validate and authorize every admin endpoint on the backend
- [ ] Add rate limits to prediction and external API endpoints
- [ ] Add structured logging without recording secrets
- [ ] Add input validation for product IDs and request bodies

---

## 📖 Summary

**PricePilot AI** is an explainable dynamic-pricing system. It uses historical retail data to forecast demand, applies elasticity to simulate different prices, selects the price with the highest projected profit, enriches the result with live market and news intelligence, and presents the final recommendation through an interactive Next.js dashboard.

<div align="center">

```
   Data Engineering  +  Machine Learning  +  Price Elasticity
             +  Profit Optimization  +  Multi-Agent AI
                  +  Web Application Development
```

**= one complete retail pricing decision platform**

</div>
