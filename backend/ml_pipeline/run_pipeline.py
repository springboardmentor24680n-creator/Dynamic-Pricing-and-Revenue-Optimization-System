import os
import logging
import time
from pathlib import Path
from typing import List, Dict, Any, Optional

import pandas as pd
from data_loader import load_data
from data_cleaner import clean_data, save_processed_data, standardize_columns
from feature_engineering import (
    create_time_features,
    create_lag_features,
    create_rolling_features,
    create_revenue_feature,
    create_inventory_ratio_feature,
    save_engineered_data
)

# Set up logging to write to console
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("ml_pipeline.runner")

BASE_DIR = Path(__file__).resolve().parent.parent
RAW_DIR = BASE_DIR / "datasets" / "raw"
PROCESSED_DIR = BASE_DIR / "datasets" / "processed"
FEATURES_DIR = BASE_DIR / "datasets" / "features"

# Reusable configuration mapping based on dataset path suffixes
DATASET_CONFIGS = {
    "demand/train.csv": {
        "required_columns": ["date", "store", "item", "sales"],
        "date_cols": ["date"],
        "numeric_cols": ["sales"],
        "group_cols": ["store", "item"],
        "value_col": "sales",
        "lags": [1, 7, 14, 30],
        "windows": [7, 14, 30],
    },
    "online_retail/online_retail_ii.csv": {
        "required_columns": ["Invoice", "StockCode", "Quantity", "InvoiceDate", "Price"],
        "date_cols": ["InvoiceDate"],
        "numeric_cols": ["Quantity", "Price"],
        "group_cols": ["stockcode"],
        "value_col": "quantity",
        "lags": [1, 7],
        "windows": [7, 14],
        "revenue": ("quantity", "price"),
    },
    "rossmann/train.csv": {
        "required_columns": ["Store", "Date", "Sales", "Customers"],
        "date_cols": ["Date"],
        "numeric_cols": ["Sales", "Customers"],
        "group_cols": ["store"],
        "value_col": "sales",
        "lags": [1, 7, 14],
        "windows": [7, 14],
    },
    "rossmann/test.csv": {
        "required_columns": ["Store", "Date"],
        "date_cols": ["Date"],
        "numeric_cols": [],
        "group_cols": ["store"],
        "value_col": None,
        "lags": [],
        "windows": [],
    },
    "rossmann/store.csv": {
        "required_columns": ["Store"],
        "date_cols": [],
        "numeric_cols": ["competitiondistance"],
        "group_cols": ["store"],
        "value_col": None,
        "lags": [],
        "windows": [],
    }
}

def auto_detect_config(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Fallback method to auto-detect settings for unrecognized datasets.
    """
    cols = df.columns.tolist()
    std_cols = [str(c).lower().strip().replace(' ', '_').replace('-', '_') for c in cols]
    
    date_cols = []
    numeric_cols = []
    group_cols = []
    
    for c, std_c in zip(cols, std_cols):
        if "date" in std_c or "time" in std_c:
            date_cols.append(c)
        elif pd.api.types.is_numeric_dtype(df[c]):
            numeric_cols.append(c)
            if "id" in std_c or "store" in std_c or "item" in std_c or "code" in std_c:
                group_cols.append(c)
        elif "id" in std_c or "store" in std_c or "item" in std_c or "code" in std_c or "category" in std_c:
            group_cols.append(c)

    value_col = numeric_cols[0] if numeric_cols else None
    
    return {
        "required_columns": [],
        "date_cols": date_cols,
        "numeric_cols": numeric_cols,
        "group_cols": group_cols if group_cols else ( [cols[0]] if cols else [] ),
        "value_col": value_col,
        "lags": [1, 7] if value_col and group_cols else [],
        "windows": [7] if value_col and group_cols else [],
    }

def run_pipeline_for_file(raw_file_path: Path) -> Dict[str, Any]:
    """
    Loads, cleans, and engineers features for a single file.
    Returns metrics dictionary for the final summary report.
    """
    logger.info(f"Processing: {raw_file_path.name}")
    start_time = time.time()
    
    # 1. Match suffix to config
    config = None
    normalized_path = raw_file_path.as_posix().lower()
    for suffix, cfg in DATASET_CONFIGS.items():
        if normalized_path.endswith(suffix.lower()):
            config = cfg
            break
            
    # Load raw data header first to build auto config if not matched
    if config is None:
        logger.info(f"No predefined config for {raw_file_path.name}. Auto-detecting schema...")
        temp_df = pd.read_csv(raw_file_path, nrows=5) if raw_file_path.suffix == '.csv' else pd.read_excel(raw_file_path, nrows=5)
        config = auto_detect_config(temp_df)
        
    # 2. Load
    df_raw = load_data(raw_file_path, required_columns=config.get("required_columns"))
    rows_loaded = len(df_raw)
    initial_nulls = df_raw.isnull().sum().sum()
    
    # Standardize column mapping to apply strategy
    strategy = {}
    for col in df_raw.columns:
        col_lower = str(col).lower().strip()
        if "customer" in col_lower or "id" in col_lower or "invoice" in col_lower:
            strategy[col] = "Unknown"
        elif pd.api.types.is_numeric_dtype(df_raw[col]):
            strategy[col] = "median"
            
    # 3. Clean
    cleaned_df = clean_data(
        df_raw,
        date_cols=config.get("date_cols"),
        numeric_non_negative_cols=config.get("numeric_cols"),
        missing_value_strategies=strategy,
        drop_duplicates=True
    )
    
    # Save cleaned
    rel_path = raw_file_path.relative_to(RAW_DIR)
    processed_dest = PROCESSED_DIR / rel_path
    save_processed_data(cleaned_df, processed_dest)
    
    # Metrics
    rows_removed = rows_loaded - len(cleaned_df)
    final_nulls = cleaned_df.isnull().sum().sum()
    # Missing values fixed includes those filled or deleted via dropna
    missing_values_fixed = initial_nulls - final_nulls

    # 4. Feature Engineering
    fe_df = cleaned_df.copy()
    
    # Standardize date column name for feature functions
    std_date_cols = [c for c in cleaned_df.columns if "date" in c]
    date_col = std_date_cols[0] if std_date_cols else None
    
    if date_col:
        fe_df = create_time_features(fe_df, date_col=date_col)
        
    # Create Lag and Rolling features if values/groups exist
    value_col = config.get("value_col")
    group_cols = config.get("group_cols")
    
    # Standardize grouping columns to snake_case matches
    if group_cols:
        group_cols = [str(g).lower().replace(' ', '_').replace('-', '_').replace('.', '_') for g in group_cols]
        group_cols = [g for g in group_cols if g in fe_df.columns]
        
    if value_col:
        value_col = str(value_col).lower().replace(' ', '_').replace('-', '_').replace('.', '_')
        
    if value_col and group_cols and date_col:
        # Lags
        lags = config.get("lags", [])
        if lags:
            fe_df = create_lag_features(fe_df, value_col=value_col, group_cols=group_cols, lags=lags, date_col=date_col)
        # Rolling
        windows = config.get("windows", [])
        if windows:
            fe_df = create_rolling_features(fe_df, value_col=value_col, group_cols=group_cols, windows=windows, date_col=date_col)
            
    # Revenue (if specified)
    rev_config = config.get("revenue")
    if rev_config:
        qty_col = str(rev_config[0]).lower()
        price_col = str(rev_config[1]).lower()
        fe_df = create_revenue_feature(fe_df, qty_col=qty_col, price_col=price_col, out_col="revenue")
        
    # Save Engineered
    features_dest = FEATURES_DIR / rel_path
    save_engineered_data(fe_df, features_dest)
    
    features_created = len(fe_df.columns) - len(cleaned_df.columns)
    processing_time = time.time() - start_time
    
    return {
        "dataset_name": rel_path.as_posix(),
        "rows_loaded": rows_loaded,
        "rows_removed": rows_removed,
        "missing_values_fixed": missing_values_fixed,
        "features_created": features_created,
        "processing_time": processing_time
    }

def main():
    logger.info("Initializing Pipeline Runner...")
    
    # Discover all CSV/Excel files recursively
    extensions = [".csv", ".xlsx", ".xls", ".xlsm", ".xlsb"]
    all_files = []
    
    for ext in extensions:
        all_files.extend(list(RAW_DIR.glob(f"**/*{ext}")))
        
    # Filter files that contain .gitkeep or other system artifacts
    raw_files = [f for f in all_files if f.is_file() and not f.name.startswith(".")]
    
    if not raw_files:
        logger.warning(f"No raw files found in: {RAW_DIR}")
        return
        
    logger.info(f"Discovered {len(raw_files)} files: {[f.relative_to(RAW_DIR).as_posix() for f in raw_files]}")
    
    results = []
    for f in raw_files:
        try:
            res = run_pipeline_for_file(f)
            results.append(res)
        except Exception as e:
            logger.error(f"Error processing dataset {f.name}: {e}", exc_info=True)
            
    # Print detailed final report
    print("\n" + "="*80)
    print("                      ML DATA PIPELINE EXECUTION SUMMARY REPORT")
    print("="*80)
    header = f"{'Dataset Name':<35} | {'Loaded':<10} | {'Removed':<8} | {'NaN Fixed':<10} | {'Features':<8} | {'Time (s)':<8}"
    print(header)
    print("-"*80)
    
    for r in results:
        line = (
            f"{r['dataset_name']:<35} | "
            f"{r['rows_loaded']:<10} | "
            f"{r['rows_removed']:<8} | "
            f"{r['missing_values_fixed']:<10} | "
            f"{r['features_created']:<8} | "
            f"{r['processing_time']:<8.2f}"
        )
        print(line)
    print("="*80 + "\n")

if __name__ == "__main__":
    main()
