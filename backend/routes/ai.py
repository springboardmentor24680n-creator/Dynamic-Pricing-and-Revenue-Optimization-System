import os
import sys
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any

from fastapi import APIRouter, HTTPException, Query

# Ensure the backend directory is in the system path to allow absolute imports
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.append(str(BASE_DIR))

from services.pricing_service import PricingService
from services.forecast_service import ForecastService
from services.recommendation_service import RecommendationService
from database.mongodb import db, test_connection
from ml_pipeline.train_price_model import SAVED_MODELS_DIR

logger = logging.getLogger("routes.ai")

router = APIRouter(prefix="/api/ai", tags=["AI Core Services"])

# Reuse service singletons if possible or instantiate on request
try:
    pricing_service = PricingService()
except Exception as e:
    logger.warning(f"Failed to pre-load PricingService: {e}")
    pricing_service = None

try:
    forecast_service = ForecastService()
except Exception as e:
    logger.warning(f"Failed to pre-load ForecastService: {e}")
    forecast_service = None

try:
    recommendation_service = RecommendationService(
        pricing_service=pricing_service,
        forecast_service=forecast_service
    )
except Exception as e:
    logger.warning(f"Failed to pre-load RecommendationService: {e}")
    recommendation_service = None


@router.get("/predict-price")
def predict_price(
    quantity: float = 10.0,
    revenue: float = 50.0,
    year: int = 2018,
    month: int = 3,
    week: int = 10,
    day: int = 5,
    day_of_week: int = 1,
    quarter: int = 1,
    quantity_lag_1: float = 12.0,
    quantity_lag_7: float = 8.0,
    quantity_rolling_mean_7: float = 9.5,
    quantity_rolling_mean_14: float = 10.2,
    stockcode: str = "22423",
    country: str = "United Kingdom"
):
    """
    Predicts optimal market price using LightGBM.
    """
    global pricing_service
    if pricing_service is None:
        try:
            pricing_service = PricingService()
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Pricing model failed to initialize: {e}")
            
    features = {
        "quantity": quantity,
        "revenue": revenue,
        "year": year,
        "month": month,
        "week": week,
        "day": day,
        "day_of_week": day_of_week,
        "quarter": quarter,
        "quantity_lag_1": quantity_lag_1,
        "quantity_lag_7": quantity_lag_7,
        "quantity_rolling_mean_7": quantity_rolling_mean_7,
        "quantity_rolling_mean_14": quantity_rolling_mean_14,
        "stockcode": stockcode,
        "country": country
    }
    
    try:
        opt_price = pricing_service.predict_optimal_price(features)
        return {
            "status": "success",
            "optimal_price": opt_price,
            "product_id": stockcode
        }
    except Exception as e:
        logger.error(f"Price prediction error: {e}")
        raise HTTPException(status_code=500, detail=f"Prediction failed: {e}")


@router.get("/forecast-demand")
def forecast_demand(horizon: str = Query("90_days", regex="^(7_days|30_days|90_days|all)$")):
    """
    Generates multi-horizon demand forecasting from the Prophet model.
    """
    global forecast_service
    if forecast_service is None:
        try:
            forecast_service = ForecastService()
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Forecasting model failed to initialize: {e}")
            
    try:
        summaries = forecast_service.generate_multi_horizon_forecasts()
        if horizon == "all":
            return {"status": "success", "forecasts": summaries}
            
        if horizon in summaries:
            return {"status": "success", "forecast": summaries[horizon]}
            
        raise HTTPException(status_code=400, detail=f"Invalid horizon selected. Choose from: 7_days, 30_days, 90_days, all")
    except Exception as e:
        logger.error(f"Demand forecast error: {e}")
        raise HTTPException(status_code=500, detail=f"Forecasting failed: {e}")


@router.get("/recommend-price")
def recommend_price(
    stockcode: str,
    current_price: float = None,
    current_inventory: float = None,
    historical_sales: float = None,
    historical_revenue: float = None,
    competitor_price: float = None,
    quantity: float = 10.0,
    revenue: float = 50.0,
    year: int = 2018,
    month: int = 3,
    week: int = 10,
    day: int = 5,
    day_of_week: int = 1,
    quarter: int = 1,
    quantity_lag_1: float = 12.0,
    quantity_lag_7: float = 8.0,
    quantity_rolling_mean_7: float = 9.5,
    quantity_rolling_mean_14: float = 10.2,
    country: str = "United Kingdom"
):
    """
    Combines pricing model outputs, Prophet trends, stock level status, and price elasticity
    to return a complete pricing recommendation document based on real database records.
    """
    global recommendation_service
    if recommendation_service is None:
        try:
            recommendation_service = RecommendationService(
                pricing_service=pricing_service,
                forecast_service=forecast_service
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Recommendation engine failed to initialize: {e}")
            
    # Fetch real product and sales from PostgreSQL
    from main import SessionLocal, Product, SalesRecord
    db_conn = SessionLocal()
    cost_price = None
    try:
        product = db_conn.query(Product).filter(Product.id == stockcode).first()
        if not product:
            raise HTTPException(status_code=404, detail=f"Product with stockcode '{stockcode}' not found in database.")
        
        # Override with database values
        current_price = product.current_price
        current_inventory = product.stock
        cost_price = product.cost_price
        
        # Sum sales records matching the product description/name
        sales_records = db_conn.query(SalesRecord).filter(SalesRecord.product_name == product.name).all()
        if sales_records:
            historical_sales = sum(s.units_sold for s in sales_records)
            historical_revenue = sum(s.revenue for s in sales_records)
        else:
            historical_sales = 0.0
            historical_revenue = 0.0
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Database lookup error for product {stockcode}: {e}")
        raise HTTPException(status_code=500, detail=f"Database lookup failed: {e}")
    finally:
        db_conn.close()

    # Get features from preloaded in-memory features dataframe
    features = {}
    if pricing_service is not None:
        features = pricing_service.get_features_for_product(stockcode)

    if not features:
        features = {
            "quantity": quantity,
            "revenue": revenue,
            "year": year,
            "month": month,
            "week": week,
            "day": day,
            "day_of_week": day_of_week,
            "quarter": quarter,
            "quantity_lag_1": quantity_lag_1,
            "quantity_lag_7": quantity_lag_7,
            "quantity_rolling_mean_7": quantity_rolling_mean_7,
            "quantity_rolling_mean_14": quantity_rolling_mean_14,
            "stockcode": stockcode,
            "country": country
        }
    else:
        features["stockcode"] = stockcode

    try:
        rec = recommendation_service.get_recommendation(
            product_features=features,
            current_price=current_price,
            current_inventory=current_inventory,
            historical_sales=historical_sales,
            historical_revenue=historical_revenue,
            cost_price=cost_price,
            competitor_price=competitor_price
        )
        return {
            "status": "success",
            "product_id": stockcode,
            "recommendation": rec
        }
    except Exception as e:
        logger.error(f"Price recommendation error: {e}")
        raise HTTPException(status_code=500, detail=f"Recommendation failed: {e}")


@router.get("/model-status")
def model_status():
    """
    Reports the status of the pricing and forecasting models on disk and in MongoDB.
    """
    lgb_path = SAVED_MODELS_DIR / "price_prediction_lightgbm.joblib"
    prophet_path = SAVED_MODELS_DIR / "demand_forecast_prophet.pkl"
    
    lgb_exists = lgb_path.exists()
    prophet_exists = prophet_path.exists()
    
    mongo_status = "Disconnected"
    registered_models = []
    
    if db is not None:
        try:
            mongo_status = "Connected"
            cursor = db["model_registry"].find({}, {"_id": 0})
            registered_models = list(cursor)
        except Exception as e:
            mongo_status = f"Connection Error: {e}"
            
    return {
        "status": "success",
        "models": {
            "price_prediction_lightgbm": {
                "status": "active" if lgb_exists else "missing",
                "path": str(lgb_path)
            },
            "demand_forecast_prophet": {
                "status": "active" if prophet_exists else "missing",
                "path": str(prophet_path)
            }
        },
        "database_registry": {
            "status": mongo_status,
            "registered_models": registered_models
        }
    }


@router.get("/health")
def health():
    """
    Checks connection statuses and model integrity.
    """
    mongo_connected, mongo_msg = test_connection()
    
    lgb_ok = (SAVED_MODELS_DIR / "price_prediction_lightgbm.joblib").exists()
    prophet_ok = (SAVED_MODELS_DIR / "demand_forecast_prophet.pkl").exists()
    
    overall_status = "Healthy" if (mongo_connected and lgb_ok and prophet_ok) else "Degraded"
    
    return {
        "status": overall_status,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "checks": {
            "mongodb": {
                "connected": mongo_connected,
                "message": mongo_msg
            },
            "pricing_model_file": "ok" if lgb_ok else "missing",
            "forecasting_model_file": "ok" if prophet_ok else "missing"
        }
    }
