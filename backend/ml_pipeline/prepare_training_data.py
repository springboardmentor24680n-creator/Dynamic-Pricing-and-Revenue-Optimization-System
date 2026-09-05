import os
import json
import logging
from pathlib import Path
from typing import Tuple, List, Dict, Any

import pandas as pd
import numpy as np

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("ml_pipeline.prepare_data")

BASE_DIR = Path(__file__).resolve().parent.parent
FEATURES_DIR = BASE_DIR / "datasets" / "features"
TRAINING_DIR = BASE_DIR / "datasets" / "training"

def temporal_split(
    df: pd.DataFrame, 
    date_col: str, 
    train_pct: float = 0.70, 
    val_pct: float = 0.15
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Splits the DataFrame chronologically based on a date column.
    """
    df = df.copy()
    df[date_col] = pd.to_datetime(df[date_col])
    df = df.sort_values(by=date_col).reset_index(drop=True)
    
    n = len(df)
    train_idx = int(n * train_pct)
    val_idx = int(n * (train_pct + val_pct))
    
    df_train = df.iloc[:train_idx]
    df_val = df.iloc[train_idx:val_idx]
    df_test = df.iloc[val_idx:]
    
    return df_train, df_val, df_test

def prepare_xgb_price_data(df: pd.DataFrame) -> Tuple[pd.DataFrame, List[str], str]:
    """
    Formats dataset for XGBoost price prediction (all variables converted to numeric).
    Retains 'invoicedate' for temporal splitting.
    Target: 'price'
    """
    df = df.copy()
    target = "price"
    date_col = "invoicedate"
    
    features = [
        "quantity", "revenue", "year", "month", "week", "day", "day_of_week", "quarter",
        "quantity_lag_1", "quantity_lag_7", "quantity_rolling_mean_7", "quantity_rolling_mean_14",
        "stockcode", "country"
    ]
    
    features = [f for f in features if f in df.columns]
    
    # Convert categories to integer codes
    for col in ["stockcode", "country"]:
        if col in df.columns:
            df[col] = df[col].astype("category").cat.codes
            
    # Include target and date column
    out_df = df[[date_col] + features + [target]].dropna()
    return out_df, features, target

def prepare_lgbm_price_data(df: pd.DataFrame) -> Tuple[pd.DataFrame, List[str], str]:
    """
    Formats dataset for LightGBM price prediction (preserves categories as category type).
    Retains 'invoicedate' for temporal splitting.
    Target: 'price'
    """
    df = df.copy()
    target = "price"
    date_col = "invoicedate"
    
    features = [
        "quantity", "revenue", "year", "month", "week", "day", "day_of_week", "quarter",
        "quantity_lag_1", "quantity_lag_7", "quantity_rolling_mean_7", "quantity_rolling_mean_14",
        "stockcode", "country"
    ]
    
    features = [f for f in features if f in df.columns]
    
    # Cast categories
    for col in ["stockcode", "country"]:
        if col in df.columns:
            df[col] = df[col].astype("category")
            
    out_df = df[[date_col] + features + [target]].dropna()
    return out_df, features, target

def prepare_prophet_demand_data(df: pd.DataFrame) -> Tuple[pd.DataFrame, List[str], str]:
    """
    Formats dataset for Prophet demand forecasting.
    Expects 'ds' (datetime) and 'y' (target variable).
    Target: 'y'
    """
    df = df.copy()
    
    # Group by date to forecast aggregated total demand
    date_col = "date" if "date" in df.columns else "invoicedate"
    target_col = "sales" if "sales" in df.columns else "quantity"
    
    # Aggregate to daily level
    df[date_col] = pd.to_datetime(df[date_col]).dt.date
    daily_df = df.groupby(date_col)[target_col].sum().reset_index()
    
    # Rename columns for Prophet
    prophet_df = daily_df.rename(columns={date_col: "ds", target_col: "y"})
    prophet_df = prophet_df.dropna()
    
    return prophet_df, ["ds"], "y"

def prepare_catboost_revenue_data(df: pd.DataFrame) -> Tuple[pd.DataFrame, List[str], str]:
    """
    Formats dataset for CatBoost revenue prediction (categorical columns preserved as strings/objects).
    Retains 'invoicedate' for temporal splitting.
    Target: 'revenue'
    """
    df = df.copy()
    target = "revenue"
    date_col = "invoicedate"
    
    features = [
        "quantity", "price", "year", "month", "week", "day", "day_of_week", "quarter",
        "quantity_lag_1", "quantity_lag_7", "quantity_rolling_mean_7", "quantity_rolling_mean_14",
        "stockcode", "country"
    ]
    
    features = [f for f in features if f in df.columns]
    
    # Convert categories to object string type
    for col in ["stockcode", "country"]:
        if col in df.columns:
            df[col] = df[col].astype(str)
            
    out_df = df[[date_col] + features + [target]].dropna()
    return out_df, features, target

def save_split_data(
    df_train: pd.DataFrame, 
    df_val: pd.DataFrame, 
    df_test: pd.DataFrame, 
    model_name: str
) -> Tuple[int, int, int]:
    """
    Saves splits to backend/datasets/training/.
    """
    TRAINING_DIR.mkdir(parents=True, exist_ok=True)
    
    train_path = TRAINING_DIR / f"{model_name}_train.csv"
    val_path = TRAINING_DIR / f"{model_name}_val.csv"
    test_path = TRAINING_DIR / f"{model_name}_test.csv"
    
    df_train.to_csv(train_path, index=False)
    df_val.to_csv(val_path, index=False)
    df_test.to_csv(test_path, index=False)
    
    logger.info(f"Saved {model_name} splits to: {TRAINING_DIR}")
    return len(df_train), len(df_val), len(df_test)

def main():
    logger.info("Starting training data preparation runner...")
    
    # Load raw features datasets
    demand_feat_path = FEATURES_DIR / "demand" / "train.csv"
    retail_feat_path = FEATURES_DIR / "online_retail" / "online_retail_II.csv"
    
    if not demand_feat_path.exists() or not retail_feat_path.exists():
        logger.error("Engineered datasets are missing. Run run_pipeline.py first.")
        return
        
    df_demand = pd.read_csv(demand_feat_path)
    # Mixed type warning handled on low memory import
    df_retail = pd.read_csv(retail_feat_path, low_memory=False)
    
    logger.info("Engineered datasets successfully loaded.")
    
    summary = {}
    
    # -------------------------------------------------------------
    # 1. XGBoost Price Prediction (on Retail)
    # -------------------------------------------------------------
    logger.info("Preparing XGBoost price prediction sets...")
    xgb_df, xgb_features, xgb_target = prepare_xgb_price_data(df_retail)
    xgb_tr, xgb_va, xgb_te = temporal_split(xgb_df, date_col="invoicedate")
    
    # Save splits, dropping temporal index 'invoicedate' prior to export
    tr_sz, va_sz, te_sz = save_split_data(
        xgb_tr.drop(columns=["invoicedate"]), 
        xgb_va.drop(columns=["invoicedate"]), 
        xgb_te.drop(columns=["invoicedate"]), 
        "xgboost_price"
    )
    
    summary["xgboost_price_prediction"] = {
        "target_variable": xgb_target,
        "features_used": xgb_features,
        "train_size": tr_sz,
        "validation_size": va_sz,
        "test_size": te_sz,
        "total_records": tr_sz + va_sz + te_sz
    }
    
    # -------------------------------------------------------------
    # 2. LightGBM Price Prediction (on Retail)
    # -------------------------------------------------------------
    logger.info("Preparing LightGBM price prediction sets...")
    lgb_df, lgb_features, lgb_target = prepare_lgbm_price_data(df_retail)
    lgb_tr, lgb_va, lgb_te = temporal_split(lgb_df, date_col="invoicedate")
    
    # Save splits, dropping temporal index 'invoicedate' prior to export
    tr_sz, va_sz, te_sz = save_split_data(
        lgb_tr.drop(columns=["invoicedate"]), 
        lgb_va.drop(columns=["invoicedate"]), 
        lgb_te.drop(columns=["invoicedate"]), 
        "lightgbm_price"
    )
    
    summary["lightgbm_price_prediction"] = {
        "target_variable": lgb_target,
        "features_used": lgb_features,
        "train_size": tr_sz,
        "validation_size": va_sz,
        "test_size": te_sz,
        "total_records": tr_sz + va_sz + te_sz
    }

    # -------------------------------------------------------------
    # 3. Prophet Demand Forecasting (on Demand Train)
    # -------------------------------------------------------------
    logger.info("Preparing Prophet demand forecasting sets...")
    prophet_df, prophet_features, prophet_target = prepare_prophet_demand_data(df_demand)
    prophet_tr, prophet_va, prophet_te = temporal_split(prophet_df, date_col="ds")
    
    # Prophet requires retaining the 'ds' column
    tr_sz, va_sz, te_sz = save_split_data(prophet_tr, prophet_va, prophet_te, "prophet_demand")
    
    summary["prophet_demand_forecasting"] = {
        "target_variable": prophet_target,
        "features_used": prophet_features,
        "train_size": tr_sz,
        "validation_size": va_sz,
        "test_size": te_sz,
        "total_records": tr_sz + va_sz + te_sz
    }

    # -------------------------------------------------------------
    # 4. CatBoost Revenue Prediction (on Retail)
    # -------------------------------------------------------------
    logger.info("Preparing CatBoost revenue prediction sets...")
    cat_df, cat_features, cat_target = prepare_catboost_revenue_data(df_retail)
    cat_tr, cat_va, cat_te = temporal_split(cat_df, date_col="invoicedate")
    
    # Save splits, dropping temporal index 'invoicedate' prior to export
    tr_sz, va_sz, te_sz = save_split_data(
        cat_tr.drop(columns=["invoicedate"]), 
        cat_va.drop(columns=["invoicedate"]), 
        cat_te.drop(columns=["invoicedate"]), 
        "catboost_revenue"
    )
    
    summary["catboost_revenue_prediction"] = {
        "target_variable": cat_target,
        "features_used": cat_features,
        "train_size": tr_sz,
        "validation_size": va_sz,
        "test_size": te_sz,
        "total_records": tr_sz + va_sz + te_sz
    }

    # Export metadata summary
    summary_path = TRAINING_DIR / "summary.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
        
    print("\n" + "="*80)
    print("                      ML TRAINING DATASET SUMMARY REPORT")
    print("="*80)
    for model_name, stats in summary.items():
        print(f"\nModel/Task: {model_name.upper()}")
        print(f"  Target Variable: {stats['target_variable']}")
        print(f"  Features Count : {len(stats['features_used'])}")
        print(f"  Features Used  : {stats['features_used']}")
        print(f"  Split Sizes    : Train={stats['train_size']}, Val={stats['validation_size']}, Test={stats['test_size']}")
        print(f"  Total Records  : {stats['total_records']}")
    print("="*80 + "\n")

if __name__ == "__main__":
    main()
