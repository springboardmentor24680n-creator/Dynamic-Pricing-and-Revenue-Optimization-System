import os
import sys
import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Tuple, List, Any

import pandas as pd
import numpy as np
import lightgbm as lgb
import joblib

# Ensure backend directory is in the system path to allow absolute imports
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.append(str(BASE_DIR))

from ml_pipeline.train_price_model import (
    CategoricalEncoder,
    calculate_metrics,
    FEATURES_DIR,
    SAVED_MODELS_DIR,
    REPORTS_DIR
)

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("ml_pipeline.train_demand_lightgbm")

def train_lightgbm_demand(
    X_train: pd.DataFrame, 
    y_train: pd.Series, 
    X_val: pd.DataFrame, 
    y_val: pd.Series
) -> lgb.LGBMRegressor:
    """
    Trains the LightGBM Regressor model for demand prediction.
    """
    logger.info("Initializing LightGBM Regressor for demand forecasting...")
    
    model_params = {
        "n_estimators": 100,
        "max_depth": 6,
        "learning_rate": 0.1,
        "random_state": 42,
        "n_jobs": -1,
        "verbose": -1
    }
    
    model = lgb.LGBMRegressor(**model_params)
    
    logger.info("Fitting LightGBM model on training set...")
    try:
        model.fit(
            X_train, 
            y_train, 
            eval_X=X_val, 
            eval_y=y_val
        )
    except TypeError:
        model.fit(
            X_train, 
            y_train, 
            eval_set=[(X_val, y_val)]
        )
    return model

def main():
    logger.info("Starting LightGBM demand forecasting model training...")
    
    # 1. Paths
    train_path = BASE_DIR / "datasets" / "training" / "lightgbm_price_train.csv"
    val_path = BASE_DIR / "datasets" / "training" / "lightgbm_price_val.csv"
    test_path = BASE_DIR / "datasets" / "training" / "lightgbm_price_test.csv"
    
    if not train_path.exists():
        logger.error(f"Training dataset not found at: {train_path}")
        sys.exit(1)
        
    # 2. Load splits
    logger.info("Loading dataset splits...")
    df_train = pd.read_csv(train_path)
    df_val = pd.read_csv(val_path)
    df_test = pd.read_csv(test_path)
    
    # Target: 'quantity' (demand)
    # Features: 'price', time features, lags, etc.
    target_col = "quantity"
    features = [
        "price", "year", "month", "week", "day", "day_of_week", "quarter",
        "quantity_lag_1", "quantity_lag_7", "quantity_rolling_mean_7", "quantity_rolling_mean_14",
        "stockcode", "country"
    ]
    
    # Drop rows with missing features or targets in splits
    df_train = df_train[features + [target_col]].dropna()
    df_val = df_val[features + [target_col]].dropna()
    df_test = df_test[features + [target_col]].dropna()
    
    # Encode categorical variables
    encoder = CategoricalEncoder()
    # Fit encoder on train categorical columns
    cat_cols = ["stockcode", "country"]
    
    for col in cat_cols:
        df_train[col] = df_train[col].astype(str).astype("category")
        df_val[col] = df_val[col].astype(str).astype("category")
        df_test[col] = df_test[col].astype(str).astype("category")
        
    X_train = df_train[features]
    y_train = df_train[target_col]
    X_val = df_val[features]
    y_val = df_val[target_col]
    X_test = df_test[features]
    y_test = df_test[target_col]
    
    # 3. Train model
    start_train_time = time.time()
    model = train_lightgbm_demand(X_train, y_train, X_val, y_val)
    training_time = time.time() - start_train_time
    
    # 4. Evaluate model
    logger.info("Evaluating model on splits...")
    train_pred = model.predict(X_train)
    val_pred = model.predict(X_val)
    test_pred = model.predict(X_test)
    
    train_metrics = calculate_metrics(y_train, train_pred)
    val_metrics = calculate_metrics(y_val, val_pred)
    test_metrics = calculate_metrics(y_test, test_pred)
    
    # 5. Extract Feature Importance
    importances = model.feature_importances_
    total_imp = sum(importances) if sum(importances) > 0 else 1
    ranked_importances = sorted(
        zip(features, [float(imp) for imp in importances]), 
        key=lambda x: x[1], 
        reverse=True
    )
    feature_importance_dict = {feat: imp for feat, imp in ranked_importances}
    
    # 6. Save artifacts
    SAVED_MODELS_DIR.mkdir(parents=True, exist_ok=True)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    
    model_save_path = SAVED_MODELS_DIR / "demand_prediction_lightgbm.joblib"
    joblib.dump(model, model_save_path)
    logger.info(f"Saved demand forecasting LightGBM model to: {model_save_path}")
    
    metrics_report = {
        "model_type": "LightGBM Demand Regressor",
        "target_column": target_col,
        "dataset_name": train_path.name,
        "train_samples": X_train.shape[0],
        "validation_samples": X_val.shape[0],
        "test_samples": X_test.shape[0],
        "features_used": features,
        "training_time": float(training_time),
        "training_date": datetime.now(timezone.utc).isoformat(),
        "metrics": {
            "train": train_metrics,
            "validation": val_metrics,
            "test": test_metrics
        },
        "feature_importances": feature_importance_dict
    }
    
    metrics_save_path = REPORTS_DIR / "demand_lightgbm_metrics.json"
    with open(metrics_save_path, "w", encoding="utf-8") as f:
        json.dump(metrics_report, f, indent=2)
    logger.info(f"Saved evaluation metrics report to: {metrics_save_path}")
    
    print("\n" + "="*80)
    print("                    LIGHTGBM DEMAND FORECASTING MODEL SUMMARY")
    print("="*80)
    print(f"Target Variable   : {target_col}")
    print(f"Split Sizes       : Train={X_train.shape[0]} rows, Val={X_val.shape[0]} rows, Test={X_test.shape[0]} rows")
    print("-"*80)
    print("EVALUATION METRICS:")
    for metric_name in ["mae", "rmse", "r2_score", "mape"]:
        print(f"  {metric_name.upper():<10} | Train: {train_metrics[metric_name]:.4f} | Val: {val_metrics[metric_name]:.4f} | Test: {test_metrics[metric_name]:.4f}")
    print("="*80 + "\n")

if __name__ == "__main__":
    main()
