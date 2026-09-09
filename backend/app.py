from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routes.products import router as products_router
from routes.prediction import router as prediction_router
from routes.demand import router as demand_router
from routes.pricing_intelligence import router as pricing_intelligence_router
from routes.competitors import router as competitors_router
from routes.profitability import router as profitability_router
from routes.pricing_strategy import router as pricing_strategy_router
from routes.executive_reports import router as executive_reports_router

app = FastAPI(
title="Dynamic Pricing Optimization and Revenue Intelligence System",
version="1.0.0"
)

app.add_middleware(
CORSMiddleware,
allow_origins=[
"http://localhost:3000",
"http://127.0.0.1:3000",
"http://localhost:5173",
"http://127.0.0.1:5173",
],
allow_credentials=True,
allow_methods=["*"],
allow_headers=["*"],
)

app.include_router(products_router)
app.include_router(prediction_router)
app.include_router(demand_router)
app.include_router(pricing_intelligence_router)
app.include_router(competitors_router)
app.include_router(profitability_router)
app.include_router(pricing_strategy_router)
app.include_router(executive_reports_router)

@app.get("/")
def root():
    return {
"message": (
"Dynamic Pricing Optimization and "
"Revenue Intelligence System API is running"
)
}

@app.get("/health")
def health():
    return {
"status": "healthy"
}

@app.get("/api-info")
def api_info():
    return {
"status": "success",
"message": "API is running successfully",
"endpoints": {
"products": "/products/",
"price_prediction": "/prediction/predict",
"demand_forecasting": "/demand/forecast",
"pricing_intelligence": "/pricing-intelligence/",
"competitor_analysis": "/competitors/",
"profitability_analytics": "/profitability/",
"pricing_strategy": "/pricing-strategy/",
"pricing_strategy_product": "/pricing-strategy/{product_id}",
"executive_bi_reports": "/reports/executive",
"documentation": "/docs"
}
}
