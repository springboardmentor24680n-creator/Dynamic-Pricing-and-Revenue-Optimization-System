# PricePilot AI

PricePilot AI is a dynamic pricing and revenue intelligence platform for retail products. It combines historical sales data, machine-learning demand forecasting, price elasticity, profit optimization, competitor research, seasonal intelligence, news analysis, and generative AI explanations in one dashboard.

The main question answered by the system is:

> What price should we set for this product now, and why?

## What the system does

For a selected product, PricePilot AI:

1. Loads product and historical sales data.
2. Creates pricing, promotion, calendar, and market features.
3. Trains LightGBM, XGBoost, and a time-series Ridge model.
4. Combines the model predictions using a weighted ensemble.
5. Applies price elasticity to estimate demand at different prices.
6. Calculates projected revenue and profit for 16 candidate prices.
7. Selects the candidate price with the highest projected profit.
8. Calculates forecast horizons, inventory burn rate, stockout risk, and reorder quantity.
9. Uses Tavily and News API to add current market context.
10. Uses OpenRouter as a master AI agent to generate an executive explanation.
11. Displays the results through a Next.js dashboard.

## High-level architecture

```text
products_catalog.csv
retail_pricing_dataset.csv
          |
          v
    Data Loading
          |
          v
  Feature Engineering
          |
          v
 LightGBM + XGBoost +
 Time-Series Ridge Model
          |
          v
  Weighted Demand Ensemble
          |
          v
 Price Elasticity + Profit Optimization
          |
          +------------------+
          |                  |
          v                  v
 Tavily Market Search   News API Agent
 Tavily Seasonal Search        |
          |                    |
          +--------+-----------+
                   v
          OpenRouter AI Brain
                   |
                   v
          Explainable Recommendation
                   |
                   v
             Next.js Dashboard
```

## Technology stack

### Frontend

- Next.js 14
- React 18
- TypeScript
- Tailwind CSS
- Recharts
- Lucide React
- Clerk authentication

### Backend

- Python
- FastAPI
- Uvicorn
- Pandas
- NumPy
- Scikit-learn
- LightGBM
- XGBoost
- Requests
- python-dotenv

### External services

- OpenRouter API — master AI explanation agent
- Tavily AI Search API — competitor and market research
- News API — current retail and category news
- Clerk — authentication and user identity

## Project structure

```text
Price pilot AI/
|
├── backend/
│   ├── main.py
│   ├── ml_engine.py
│   ├── agent_orchestrator.py
│   ├── catalog_datasets.py
│   ├── generate_and_save_dataset.py
│   └── requirements.txt
|
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
|
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

## Dataset description

### `products_catalog.csv`

This file contains the current state of the product catalog. It contains 10 products and fields such as:

- Product ID and SKU
- Product name and category
- Current price
- Cost price
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

This file contains approximately 3,650 historical daily records across the products. It includes:

- Date
- Product and category information
- Product price and cost price
- Competitor price
- Discount percentage
- Promotion flag
- Day of week
- Month
- Weekend flag
- Holiday flag
- Units sold
- Revenue
- Profit
- Elasticity score

The catalog represents the current business state. The historical dataset represents past demand behavior.

## Feature engineering

The ML engine creates the following derived features in `backend/ml_engine.py`:

```text
price_diff      = competitor_price - price
price_ratio     = price / competitor_price
discount_factor = 1 - discount_percent / 100
effective_price = price * discount_factor
day_index       = chronological record index
```

The final model features are:

```text
price
competitor_price
discount_percent
promotion_flag
day_of_week
month
is_weekend
is_holiday
price_diff
price_ratio
effective_price
day_index
```

## Machine-learning workflow

### LightGBM

LightGBM is used as a fast gradient-boosted tree regression model for tabular pricing and demand features.

Ensemble weight:

```text
40%
```

### XGBoost

XGBoost is used as a regularized non-linear regression model for price-response and demand prediction.

Ensemble weight:

```text
35%
```

### Time-series model

The project refers to this component as Prophet/time-series. In the current implementation, it is a Ridge regression model using time and seasonal features:

- Day index
- Month
- Day of week
- Weekend flag
- Holiday flag

Ensemble weight:

```text
25%
```

### Training and evaluation

The historical data is split chronologically into:

```text
80% training data
20% validation data
```

The models return evaluation metrics including:

- MAE — Mean Absolute Error
- RMSE — Root Mean Squared Error
- R² — coefficient of determination

### Ensemble prediction

The final daily demand estimate is calculated as:

```text
Ensemble Demand =
    0.40 × LightGBM Demand
  + 0.35 × XGBoost Demand
  + 0.25 × Time-Series Demand
```

## Price elasticity and optimization

Price elasticity estimates how demand changes when price changes.

For every candidate price, the system estimates demand using:

```text
Estimated Demand =
    Ensemble Demand × (Current Price / Candidate Price) ^ Elasticity
```

It then calculates:

```text
Projected Revenue = Estimated Demand × Candidate Price

Projected Profit = Estimated Demand × (Candidate Price - Cost Price)
```

The engine evaluates 16 evenly spaced candidate prices between:

```text
Minimum price = max(Cost Price × 1.05, Current Price × 0.75)
Maximum price = Current Price × 1.35
```

The price with the highest projected profit is returned as the optimal price.

## Multi-agent AI system

The multi-agent pipeline is implemented in `backend/agent_orchestrator.py`.

### 1. Tavily market search agent

Searches the web for product and category pricing trends.

It provides:

- Market trend
- Market signal
- Competitor pricing context
- Estimated price impact
- Strategic pricing action
- Source URL

### 2. Tavily seasonal search agent

Searches for seasonal demand periods and shopping events such as:

- Q4 holiday demand
- Black Friday and Cyber Week
- Back-to-school demand
- Weekend shopping spikes
- Post-holiday clearance

It provides a suggested timing and reason for price adjustment.

### 3. News API agent

Fetches recent retail, e-commerce, and category news. The current implementation classifies text using keyword-based rules into categories such as:

- High Promo Season
- Bullish
- Stable

It returns the headline, source, date, trend factor, price impact, and business takeaway.

### 4. OpenRouter brain agent

OpenRouter acts as the master AI explanation layer. The default configured model is:

```text
openai/gpt-oss-20b:free
```

The prompt includes:

- Product name
- Category
- Current price
- Cost price
- Competitor price
- Optimal price
- Recommended price change
- Market trend
- News trend

The agent returns a concise executive pricing summary. It explains the recommendation but does not replace the numerical ML and optimization calculations.

## Backend API

The FastAPI server is implemented in `backend/main.py`.

### Health check

```http
GET /api/health
```

Returns backend status, product count, training row count, model names, and agent names.

### Product catalog

```http
GET /api/products
```

Returns products loaded from `products_catalog.csv`.

### Single-product prediction

```http
GET /api/predict/single/{product_id}
```

Runs the complete prediction and multi-agent pipeline for one product.

The response includes:

- Optimal price
- Price change percentage
- Margin before and after
- Model predictions and metrics
- Forecast horizons
- Seasonal report
- Inventory intelligence
- Revenue optimization curve
- Tavily results
- News API results
- OpenRouter summary

### Batch prediction

```http
POST /api/predict/all
```

Runs prediction for every catalog product and returns product-level results plus total projected revenue before and after optimization.

### Seasonal reports

```http
GET /api/seasonal-reports
```

Returns weekly demand patterns, seasonal factors, and inventory turnover alerts.

### Competitor analysis

```http
GET /api/competitor-analysis
```

Compares our product prices with competitor prices and classifies each product as:

- Underpriced
- Premium
- Competitive

### Admin endpoints

```http
GET  /api/admin/pending-users
POST /api/admin/approve-user
POST /api/admin/reject-user
```

These endpoints support the user approval workflow.

## Frontend modules

### Overview dashboard

Displays revenue trends, demand index, model information, ensemble information, and agent status.

### Product catalog

Displays products, categories, current prices, inventory, competitor prices, demand trends, and elasticity scores.

### Single-product prediction modal

Displays the complete analysis for one product:

- Optimal price
- Price change
- Model comparison
- Revenue optimization curve
- Short-, medium-, and long-term forecasts
- Seasonal analysis
- Inventory risk
- Competitor insights
- News insights
- OpenRouter explanation

### Competitor analysis

Displays price comparisons and market position.

### Revenue simulator

Allows the user to test price changes and promotional discounts and see estimated revenue and margin outcomes.

### Seasonal reports

Displays weekly demand patterns, seasonal demand factors, and inventory alerts.

### Admin user management

Allows the administrator to approve or reject pending users.

## Complete single-product request flow

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

## Installation

### Prerequisites

- Node.js 18 or newer
- npm
- Python 3.10 or newer

### Install frontend dependencies

```bash
npm install
```

### Install backend dependencies

```bash
python -m venv .venv
```

Activate the environment.

Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

macOS/Linux:

```bash
source .venv/bin/activate
```

Install the requirements:

```bash
pip install -r backend/requirements.txt
```

## Environment variables

Create a `.env` file in the project root. Use `.env.example` as a template.

```env
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=your_clerk_publishable_key
CLERK_SECRET_KEY=your_clerk_secret_key

OPENROUTER_API_KEY=your_openrouter_key
OPENROUTER_MODEL=openai/gpt-oss-20b:free

TAVILY_API_KEY=your_tavily_key
NEWS_API_KEY=your_news_api_key

NEXT_PUBLIC_API_URL=http://127.0.0.1:8000
```

Never commit or upload `.env`. It may contain private API keys. Use `.env.example` when sharing the project.

## Running the project

### Start the backend

From the project root:

```bash
python backend/main.py
```

The FastAPI backend runs at:

```text
http://127.0.0.1:8000
```

Health check:

```text
http://127.0.0.1:8000/api/health
```

### Start the frontend

In a second terminal:

```bash
npm run dev
```

The frontend is normally available at:

```text
http://localhost:3000
```

### Production build

```bash
npm run build
npm start
```

## Fallback behavior

The application has development fallbacks:

- If the product API fails, the frontend uses fallback catalog data.
- If Tavily is unavailable, predefined market insights are returned.
- If News API is unavailable, predefined news insights are returned.
- If OpenRouter fails, a predefined executive summary is returned.

This allows the UI to continue working during development without all external API keys.

## Important implementation notes

- The backend retrains models during prediction requests. For production, model caching or scheduled training should be added.
- User approval data is stored in memory and is lost when the backend restarts.
- The product and training data are CSV-based rather than stored in a database.
- The frontend batch prediction modal currently performs a simplified local simulation, although the backend contains a complete `/api/predict/all` endpoint.
- The time-series component is implemented using Ridge regression with seasonal features, although the interface labels it as Prophet/time-series.
- The backend currently allows all CORS origins for development.
- API calls depend on valid keys and network access.
- The current system recommends prices but does not yet automatically publish them to a real commerce platform.

## Future improvements

- Add PostgreSQL or another persistent database.
- Add scheduled model retraining and model caching.
- Store recommendations and actual sales outcomes.
- Add A/B testing for pricing strategies.
- Add model drift monitoring.
- Add SHAP-based model explanations.
- Add persistent role-based authorization in the backend.
- Connect to live inventory and order systems.
- Add automatic price publishing with approval controls.
- Replace development fallbacks with production error handling.
- Use a dedicated Prophet or other advanced time-series implementation if required.
- Deploy the frontend and backend using Docker and cloud infrastructure.

## Security recommendations before production

- Never expose API keys in the frontend.
- Restrict CORS to trusted frontend domains.
- Move approval and product data to a secure database.
- Validate and authorize every admin endpoint on the backend.
- Add rate limits to prediction and external API endpoints.
- Add structured logging without recording secrets.
- Add input validation for product IDs and request bodies.

## Summary

PricePilot AI is an explainable dynamic-pricing system. It uses historical retail data to forecast demand, applies elasticity to simulate different prices, selects the price with the highest projected profit, enriches the result with live market and news intelligence, and presents the final recommendation through an interactive Next.js dashboard.

The project connects:

```text
Data Engineering
        +
Machine Learning
        +
Price Elasticity
        +
Profit Optimization
        +
Multi-Agent AI
        +
Web Application Development
```

into one complete retail pricing decision platform.
