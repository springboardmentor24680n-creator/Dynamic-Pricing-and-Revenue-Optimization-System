import os
import sys
import json
import logging
from datetime import datetime, timezone
from pathlib import Path

# Add backend directory to sys.path if not present to enable imports of database
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.append(str(BASE_DIR))

# Import existing MongoDB connection
from database.mongodb import db

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("ml_pipeline.compare_models")

REPORTS_DIR = BASE_DIR / "reports"

def load_metrics(metrics_path: Path) -> dict:
    if not metrics_path.exists():
        raise FileNotFoundError(f"Metrics file not found at: {metrics_path}")
    with open(metrics_path, "r", encoding="utf-8") as f:
        return json.load(f)

def compare_models():
    logger.info("Initiating model comparison...")
    
    # 1. Load metrics for XGBoost and LightGBM
    xgboost_metrics_path = REPORTS_DIR / "model_metrics.json"
    lightgbm_metrics_path = REPORTS_DIR / "lightgbm_metrics.json"
    
    try:
        xgb_data = load_metrics(xgboost_metrics_path)
    except Exception as e:
        logger.error(f"Failed to load XGBoost metrics: {e}")
        return None
        
    try:
        lgb_data = load_metrics(lightgbm_metrics_path)
    except Exception as e:
        logger.error(f"Failed to load LightGBM metrics: {e}")
        return None
        
    # 2. Extract metrics (default to test, fallback to validation)
    xgb_metrics = xgb_data.get("metrics", {}).get("test", {})
    lgb_metrics = lgb_data.get("metrics", {}).get("test", {})
    
    split_used = "test"
    if not xgb_metrics or not lgb_metrics:
        xgb_metrics = xgb_data.get("metrics", {}).get("validation", {})
        lgb_metrics = lgb_data.get("metrics", {}).get("validation", {})
        split_used = "validation"
        
    # 3. Compare and determine best model (R² Score - higher is better)
    xgb_r2 = xgb_metrics.get("r2_score", -float("inf"))
    lgb_r2 = lgb_metrics.get("r2_score", -float("inf"))
    
    if lgb_r2 > xgb_r2:
        best_model = "LightGBM"
    else:
        best_model = "XGBoost"
        
    # 4. Create comparison report
    comparison_report = {
        "comparison_date": datetime.now(timezone.utc).isoformat(),
        "evaluation_split_used": split_used,
        "models": {
            "XGBoost": {
                "algorithm": xgb_data.get("model_type", "XGBoost Regressor"),
                "dataset": xgb_data.get("dataset_name"),
                "features_count": len(xgb_data.get("features_used", [])),
                "metrics": xgb_metrics
            },
            "LightGBM": {
                "algorithm": lgb_data.get("model_type", "LightGBM Regressor"),
                "dataset": lgb_data.get("dataset_name"),
                "features_count": len(lgb_data.get("features_used", [])),
                "metrics": lgb_metrics
            }
        },
        "comparison_metrics": {
            "mae_diff": float(xgb_metrics.get("mae", 0) - lgb_metrics.get("mae", 0)),
            "rmse_diff": float(xgb_metrics.get("rmse", 0) - lgb_metrics.get("rmse", 0)),
            "r2_diff": float(lgb_r2 - xgb_r2),
            "mape_diff": float(xgb_metrics.get("mape", 0) - lgb_metrics.get("mape", 0))
        },
        "best_performing_model": best_model
    }
    
    # 5. Save report to JSON
    comparison_save_path = REPORTS_DIR / "model_comparison.json"
    with open(comparison_save_path, "w", encoding="utf-8") as f:
        json.dump(comparison_report, f, indent=2)
    logger.info(f"Saved model comparison report to: {comparison_save_path}")
    
    # 6. Store comparison result in MongoDB
    if db is not None:
        try:
            db.model_comparison.update_one(
                {"comparison_id": "latest_model_comparison"},
                {"$set": {
                    "comparison_date": datetime.now(timezone.utc),
                    "evaluation_split_used": split_used,
                    "xgboost": comparison_report["models"]["XGBoost"],
                    "lightgbm": comparison_report["models"]["LightGBM"],
                    "best_performing_model": best_model,
                    "comparison_metrics": comparison_report["comparison_metrics"]
                }},
                upsert=True
            )
            print("Success: Model comparison successfully stored in MongoDB.")
        except Exception as e:
            logger.error(f"Failed to save comparison to MongoDB: {e}")
    else:
        logger.warning("MongoDB database connection is not initialized. Skipping DB save.")
        
    # 7. Print formatted comparison table
    print("\n" + "="*80)
    print(f"                    MODEL COMPARISON SUMMARY (Split: {split_used.upper()})")
    print("="*80)
    print(f"  {'Metric':<10} | {'XGBoost':<18} | {'LightGBM':<18} | {'Difference (XGB - LGB)':<22}")
    print(f"  {'-'*10} | {'-'*18} | {'-'*18} | {'-'*22}")
    
    for metric_name in ["mae", "rmse", "r2_score", "mape"]:
        xgb_val = xgb_metrics.get(metric_name)
        lgb_val = lgb_metrics.get(metric_name)
        
        if xgb_val is not None and lgb_val is not None:
            diff = xgb_val - lgb_val
            if metric_name == "r2_score":
                better_str = "LGB is better" if diff < 0 else "XGB is better"
                print(f"  {metric_name.upper():<10} | {xgb_val:<18.4f} | {lgb_val:<18.4f} | {diff:<+22.4f} ({better_str})")
            else:
                better_str = "LGB is better" if diff > 0 else "XGB is better"
                print(f"  {metric_name.upper():<10} | {xgb_val:<18.4f} | {lgb_val:<18.4f} | {diff:<+22.4f} ({better_str})")
        else:
            print(f"  {metric_name.upper():<10} | {'N/A':<18} | {'N/A':<18} | {'N/A':<22}")
            
    print("-"*80)
    print(f"  Best-Performing Model based on R² Score: {best_model.upper()}")
    print("="*80 + "\n")
    
    return comparison_report

if __name__ == "__main__":
    compare_models()
