import logging
from pathlib import Path
from typing import List, Union, Optional
import pandas as pd
import numpy as np

logger = logging.getLogger("ml_pipeline.feature_engineering")

def create_time_features(df: pd.DataFrame, date_col: str) -> pd.DataFrame:
    """
    Creates time-based features: Year, Month, Week, Day, DayOfWeek, Quarter.
    """
    df = df.copy()
    if date_col not in df.columns:
        raise ValueError(f"Date column '{date_col}' not found in DataFrame.")
        
    dt_s = pd.to_datetime(df[date_col])
    
    df['year'] = dt_s.dt.year
    df['month'] = dt_s.dt.month
    df['week'] = dt_s.dt.isocalendar().week.astype(int)
    df['day'] = dt_s.dt.day
    df['day_of_week'] = dt_s.dt.dayofweek
    df['quarter'] = dt_s.dt.quarter
    
    logger.info(f"Created time-based features from '{date_col}'.")
    return df

def create_lag_features(
    df: pd.DataFrame, 
    value_col: str, 
    group_cols: List[str], 
    lags: List[int],
    date_col: str = 'date'
) -> pd.DataFrame:
    """
    Creates lag features grouped by entity columns, sorting by date.
    Sorts by grouping key + date to prevent look-ahead bias and data leakage.
    """
    df = df.copy()
    if value_col not in df.columns:
        raise ValueError(f"Value column '{value_col}' not found.")
    for g_col in group_cols:
        if g_col not in df.columns:
            raise ValueError(f"Grouping column '{g_col}' not found.")
            
    # Sort to ensure correctness of shifts
    df = df.sort_values(by=group_cols + [date_col])
    
    for lag in lags:
        col_name = f"{value_col}_lag_{lag}"
        df[col_name] = df.groupby(group_cols)[value_col].shift(lag)
        logger.info(f"Created lag feature: {col_name}")
        
    return df

def create_rolling_features(
    df: pd.DataFrame, 
    value_col: str, 
    group_cols: List[str], 
    windows: List[int],
    date_col: str = 'date',
    shift: int = 1
) -> pd.DataFrame:
    """
    Creates rolling mean features grouped by entity columns, sorting by date.
    Shifts the value column by default (shift=1) to prevent look-ahead bias/leakage.
    """
    df = df.copy()
    if value_col not in df.columns:
        raise ValueError(f"Value column '{value_col}' not found.")
        
    df = df.sort_values(by=group_cols + [date_col])
    
    for window in windows:
        col_name = f"{value_col}_rolling_mean_{window}"
        # Shift data first, then roll to ensure no leakage from the current row
        if shift > 0:
            df[col_name] = df.groupby(group_cols)[value_col].transform(
                lambda x: x.shift(shift).rolling(window, min_periods=1).mean()
            )
        else:
            df[col_name] = df.groupby(group_cols)[value_col].transform(
                lambda x: x.rolling(window, min_periods=1).mean()
            )
        logger.info(f"Created rolling mean feature (window={window}, shift={shift}): {col_name}")
        
    return df

def create_revenue_feature(
    df: pd.DataFrame, 
    qty_col: str, 
    price_col: str,
    out_col: str = 'revenue'
) -> pd.DataFrame:
    """
    Creates a revenue feature by multiplying Quantity/Sales and Price.
    """
    df = df.copy()
    if qty_col in df.columns and price_col in df.columns:
        df[out_col] = df[qty_col] * df[price_col]
        logger.info(f"Created revenue feature '{out_col}' as '{qty_col}' * '{price_col}'")
    else:
        logger.warning(f"Skipping revenue feature creation: '{qty_col}' and/or '{price_col}' missing.")
    return df

def create_inventory_ratio_feature(
    df: pd.DataFrame, 
    stock_col: str, 
    sales_col: str,
    out_col: str = 'inventory_ratio',
    fill_value: float = 0.0
) -> pd.DataFrame:
    """
    Creates an inventory ratio: stock_col / (sales_col + epsilon) to prevent division by zero.
    """
    df = df.copy()
    if stock_col in df.columns and sales_col in df.columns:
        df[out_col] = df[stock_col] / (df[sales_col] + 1e-5)
        df[out_col] = df[out_col].replace([np.inf, -np.inf], np.nan).fillna(fill_value)
        logger.info(f"Created inventory ratio feature '{out_col}' as '{stock_col}' / '{sales_col}'")
    else:
        logger.warning(f"Skipping inventory ratio feature: '{stock_col}' and/or '{sales_col}' missing.")
    return df

def prepare_for_models(
    df: pd.DataFrame,
    date_col: str,
    target_col: str,
    categorical_cols: Optional[List[str]] = None,
) -> dict:
    """
    Formates the dataset specifically for different model engines:
    - Prophet: Expects 'ds' (datetime) and 'y' (target).
    - XGBoost: All features must be numeric. Encodes categorical variables to code indices.
    - LightGBM / CatBoost: Supports native categorical types. Converts columns to category type.
    """
    df = df.copy()
    prepared = {}
    
    # 1. Prophet
    if date_col in df.columns and target_col in df.columns:
        prophet_df = df[[date_col, target_col]].rename(columns={date_col: 'ds', target_col: 'y'})
        prepared['prophet'] = prophet_df
        logger.info("Prophet-formatted dataset created.")
        
    # 2. LightGBM and CatBoost
    lgb_df = df.copy()
    if categorical_cols:
        for col in categorical_cols:
            if col in lgb_df.columns:
                lgb_df[col] = lgb_df[col].astype('category')
        logger.info(f"Converted categoricals {categorical_cols} to pandas category for LightGBM/CatBoost.")
    prepared['lgbm_catboost'] = lgb_df
    
    # 3. XGBoost
    xgb_df = df.copy()
    if categorical_cols:
        for col in categorical_cols:
            if col in xgb_df.columns:
                if not pd.api.types.is_categorical_dtype(xgb_df[col]):
                    xgb_df[col] = xgb_df[col].astype('category')
                xgb_df[col] = xgb_df[col].cat.codes
        logger.info("Encoded categorical columns as integer codes for XGBoost compatibility.")
    prepared['xgboost'] = xgb_df
    
    return prepared

def save_engineered_data(
    df: pd.DataFrame, 
    dest_path: Union[str, Path]
) -> None:
    """
    Saves the engineered DataFrame to features path.
    """
    path = Path(dest_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)
    logger.info(f"Successfully saved engineered dataset to: {path}")
