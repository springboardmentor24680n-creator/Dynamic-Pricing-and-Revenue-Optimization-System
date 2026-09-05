import os
import sys
import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict

import pandas as pd
import numpy as np
import lightgbm as lgb
import joblib

# Ensure the backend directory is in the system path to allow absolute imports of ml_pipeline
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.append(str(BASE_DIR))

# Import modular pipeline components from the existing XGBoost training pipeline
from ml_pipeline.train_price_model import (
    CategoricalEncoder,
    find_pricing_dataset,
    identify_target_and_date_cols,
    prepare_features,
    temporal_split,
    calculate_metrics,
    FEATURES_DIR,
    SAVED_MODELS_DIR,
    REPORTS_DIR
)

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("ml_pipeline.train_lightgbm")

def train_lightgbm(
    X_train: pd.DataFrame, 
    y_train: pd.Series, 
    X_val: pd.DataFrame, 
    y_val: pd.Series
) -> lgb.LGBMRegressor:
    """
    Trains the LightGBM Regressor model using reasonable default hyperparameters.
    """
    logger.info("Initializing LightGBM Regressor model...")
    
    model_params = {
        "n_estimators": 100,
        "max_depth": 6,
        "learning_rate": 0.1,
        "random_state": 42,
        "n_jobs": -1,
        "verbose": -1
    }
    
    model = lgb.LGBMRegressor(**model_params)
    
    logger.info("Fitting LightGBM model on the training set...")
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
    logger.info("Starting LightGBM dynamic price prediction training...")
    
    # 1. Locate and load dataset
    dataset_path = find_pricing_dataset(FEATURES_DIR)
    df = pd.read_csv(dataset_path, low_memory=False)
    logger.info(f"Successfully loaded dataset: {dataset_path} ({df.shape[0]} rows, {df.shape[1]} columns)")
    
    # 2. Identify target and date columns
    target_col, date_col = identify_target_and_date_cols(df)
    
    # Sort chronologically if date column is present
    if date_col:
        logger.info("Sorting dataset chronologically by date/time key...")
        df[date_col] = pd.to_datetime(df[date_col])
        df = df.sort_values(by=date_col).reset_index(drop=True)
        
    # 3. Prepare features
    # Since CategoricalEncoder from train_price_model is built to dynamically map 
    # category-supported algorithms, and LightGBM supports category dtype natively,
    # we initialize and run the same encoder.
    encoder = CategoricalEncoder()
    X, y, features = prepare_features(df, target_col, date_col, encoder)
    
    # 4. Split data (70% train, 15% validation, 15% test)
    X_train, X_val, X_test, y_train, y_val, y_test = temporal_split(X, y)
    logger.info(f"Split completed: Train={X_train.shape[0]} rows, Val={X_val.shape[0]} rows, Test={X_test.shape[0]} rows")
    
    # 5. Train model
    start_train_time = time.time()
    model = train_lightgbm(X_train, y_train, X_val, y_val)
    training_time = time.time() - start_train_time
    
    # 6. Evaluate model on splits
    logger.info("Evaluating model predictions across train, val, and test splits...")
    train_pred = model.predict(X_train)
    val_pred = model.predict(X_val)
    test_pred = model.predict(X_test)
    
    train_metrics = calculate_metrics(y_train, train_pred)
    val_metrics = calculate_metrics(y_val, val_pred)
    test_metrics = calculate_metrics(y_test, test_pred)
    
    # 7. Extract Feature Importance
    importances = model.feature_importances_
    total_imp = sum(importances) if sum(importances) > 0 else 1
    
    ranked_importances = sorted(
        zip(features, [float(imp) for imp in importances]), 
        key=lambda x: x[1], 
        reverse=True
    )
    feature_importance_dict = {feat: imp for feat, imp in ranked_importances}
    
    # 8. Save artifacts
    logger.info("Saving trained LightGBM model and evaluation report...")
    SAVED_MODELS_DIR.mkdir(parents=True, exist_ok=True)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    
    model_save_path = SAVED_MODELS_DIR / "price_prediction_lightgbm.joblib"
    joblib.dump(model, model_save_path)
    logger.info(f"Saved model joblib to: {model_save_path}")
    
    metrics_report = {
        "model_type": "LightGBM Regressor",
        "target_column": target_col,
        "dataset_name": dataset_path.name,
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
    
    metrics_save_path = REPORTS_DIR / "lightgbm_metrics.json"
    with open(metrics_save_path, "w", encoding="utf-8") as f:
        json.dump(metrics_report, f, indent=2)
    logger.info(f"Saved evaluation metrics report to: {metrics_save_path}")
    
    # 9. Print Training Summary
    print("\n" + "="*80)
    print("                    LIGHTGBM PRICE PREDICTION MODEL SUMMARY")
    print("="*80)
    print(f"Target Variable   : {target_col}")
    print(f"Dataset File      : {dataset_path.name}")
    print(f"Total Rows Loaded : {len(df)}")
    print(f"Split Sizes       : Train={X_train.shape[0]} rows, Val={X_val.shape[0]} rows, Test={X_test.shape[0]} rows")
    print("-"*80)
    print("EVALUATION METRICS:")
    print(f"  {'Metric':<10} | {'Training Set':<14} | {'Validation Set':<14} | {'Test Set':<14}")
    print(f"  {'-'*10} | {'-'*14} | {'-'*14} | {'-'*14}")
    for metric_name in ["mae", "rmse", "r2_score", "mape"]:
        tr_val = train_metrics[metric_name]
        va_val = val_metrics[metric_name]
        te_val = test_metrics[metric_name]
        print(f"  {metric_name.upper():<10} | {tr_val:<14.4f} | {va_val:<14.4f} | {te_val:<14.4f}")
    print("-"*80)
    print("FEATURE IMPORTANCE (Descending):")
    for feat, imp in ranked_importances[:10]:
        pct = (imp / total_imp) * 100
        print(f"  - {feat:<25}: {imp:.4f} ({pct:.2f}%)")
    if len(ranked_importances) > 10:
        print(f"  ... (+ {len(ranked_importances) - 10} more features)")
    print("="*80 + "\n")

if __name__ == "__main__":
    main()
