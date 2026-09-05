import os
import sys
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.append(str(BASE_DIR))

# Reuse the existing MongoDB connection
from database.mongodb import db

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("services.model_registry")

def register_model(
    model_name: str = "price_prediction_xgboost",
    model_path: Optional[str] = None,
    metrics_path: Optional[str] = None,
    status: str = "active"
) -> dict:
    """
    Reads existing model metrics and registers/updates model metadata in MongoDB.
    
    Args:
        model_name (str): Unique name identifier for the model.
        model_path (str, optional): Custom path to the saved model file.
        metrics_path (str, optional): Custom path to the model metrics JSON file.
        status (str): Current status of the model (e.g. 'active', 'deprecated').
        
    Returns:
        dict: The registered/updated model document.
    """
    logger.info(f"Initiating registration for model: '{model_name}'")
    
    # Define default paths relative to BASE_DIR if not provided
    if model_path is None:
        if model_name == "demand_forecast_prophet" or model_name.endswith("_prophet") or model_name.startswith("demand_forecast"):
            model_file = BASE_DIR / "saved_models" / f"{model_name}.pkl"
        else:
            model_file = BASE_DIR / "saved_models" / f"{model_name}.joblib"
    else:
        model_file = Path(model_path)
        
    if metrics_path is None:
        if model_name == "price_prediction_xgboost":
            metrics_file = BASE_DIR / "reports" / "model_metrics.json"
        elif model_name == "price_prediction_lightgbm":
            metrics_file = BASE_DIR / "reports" / "lightgbm_metrics.json"
        elif model_name == "demand_forecast_prophet":
            metrics_file = BASE_DIR / "reports" / "demand_forecast.json"
        else:
            # General fallback for any future model
            metrics_name = model_name.replace("price_prediction_", "")
            metrics_file = BASE_DIR / "reports" / f"{metrics_name}_metrics.json"
    else:
        metrics_file = Path(metrics_path)
        
    # Read existing metrics report
    if not metrics_file.exists():
        raise FileNotFoundError(f"Model metrics file not found at: {metrics_file}")
        
    try:
        with open(metrics_file, "r", encoding="utf-8") as f:
            metrics_report = json.load(f)
    except Exception as e:
        raise ValueError(f"Failed to parse metrics JSON from {metrics_file}: {e}")
        
    # Extract metadata fields from metrics report
    algorithm = metrics_report.get("model_type", "Unknown Regressor")
    dataset_used = metrics_report.get("dataset_name", "Unknown")
    
    features = metrics_report.get("features_used", [])
    num_features = len(features)
    
    # Read metrics (try test first, then validation, then validation_holdout as fallback)
    metrics_block = metrics_report.get("metrics", {})
    target_metrics = metrics_block.get("test", metrics_block.get("validation", metrics_block.get("validation_holdout", {})))
    
    mae = target_metrics.get("mae")
    rmse = target_metrics.get("rmse")
    mape = target_metrics.get("mape")
    r2_score = target_metrics.get("r2_score")
    
    # Extract training time and date if available (supporting Prophet keys too)
    training_time = metrics_report.get("training_time", metrics_report.get("training_time_seconds"))
    training_date_str = metrics_report.get("training_date", metrics_report.get("run_date"))
    
    # Fallbacks if metrics_report didn't have time/date yet
    if training_time is None:
        training_time = 0.0
        
    if training_date_str:
        try:
            training_date = datetime.fromisoformat(training_date_str)
        except Exception:
            training_date = datetime.now(timezone.utc)
    else:
        # Fallback to file modification time
        try:
            mtime = metrics_file.stat().st_mtime
            training_date = datetime.fromtimestamp(mtime)
        except Exception:
            training_date = datetime.now(timezone.utc)

    # Extract Forecast Horizons if present (e.g. for forecasting models like Prophet)
    forecasts_block = metrics_report.get("forecasts", {})
    forecast_horizons = []
    if forecasts_block:
        for h_key in forecasts_block.keys():
            try:
                days = int(h_key.split('_')[0])
                forecast_horizons.append(days)
            except ValueError:
                pass

    # Formulate model metadata document
    model_metadata = {
        "Model Name": model_name,
        "Algorithm": algorithm,
        "Training Date": training_date,
        "Dataset Used": dataset_used,
        "Number of Features": num_features,
        "Feature Count": num_features,
        "MAE": mae,
        "RMSE": rmse,
        "MAPE": mape,
        "R² Score": r2_score,
        "R²": r2_score,
        "Model File Location": str(model_file.resolve()),
        "Model Path": str(model_file.resolve()),
        "Training Time": training_time,
        "Status": status
    }
    
    if forecast_horizons:
        model_metadata["Forecast Horizons"] = sorted(forecast_horizons)
    
    if db is None:
        raise ConnectionError("MongoDB database connection is not initialized.")
        
    try:
        # Upsert the model entry by Model Name
        db.model_registry.update_one(
            {"Model Name": model_name},
            {"$set": model_metadata},
            upsert=True
        )
        print(f"Success: Model '{model_name}' successfully registered in MongoDB Model Registry.")
        logger.info(f"Registered model details: {model_metadata}")
    except Exception as e:
        raise RuntimeError(f"Failed to write model metadata to MongoDB: {e}")
        
    return model_metadata

if __name__ == "__main__":
    # Register both models if executed directly
    print("Running Model Registry batch registration...")
    
    # 1. Register XGBoost Model
    try:
        register_model(model_name="price_prediction_xgboost")
    except Exception as err:
        print(f"Error during XGBoost model registration: {err}")
        
    # 2. Register LightGBM Model
    try:
        register_model(model_name="price_prediction_lightgbm")
    except Exception as err:
        print(f"Error during LightGBM model registration: {err}")
        
    # 3. Register Prophet Model
    try:
        register_model(model_name="demand_forecast_prophet")
    except Exception as err:
        print(f"Error during Prophet model registration: {err}")
