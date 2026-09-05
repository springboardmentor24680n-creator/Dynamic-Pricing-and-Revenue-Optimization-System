import logging
from pathlib import Path
from typing import List, Union, Optional, Dict, Any
import pandas as pd

logger = logging.getLogger("ml_pipeline.data_cleaner")

def standardize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Standardizes column names to snake_case.
    Removes quotes, replaces spaces/hyphens with underscores, and lowercases.
    """
    df = df.copy()
    new_cols = []
    for col in df.columns:
        c = str(col).strip().replace('"', '').replace("'", "")
        c = c.replace(' ', '_').replace('-', '_').replace('.', '_')
        c = c.lower()
        while '__' in c:
            c = c.replace('__', '_')
        new_cols.append(c)
    df.columns = new_cols
    return df

def clean_data(
    df: pd.DataFrame,
    date_cols: Optional[List[str]] = None,
    numeric_non_negative_cols: Optional[List[str]] = None,
    missing_value_strategies: Optional[Dict[str, Any]] = None,
    drop_duplicates: bool = True,
) -> pd.DataFrame:
    """
    Cleans the DataFrame by executing the following pipeline:
    1. Standardizes column names.
    2. Drops duplicate rows.
    3. Converts date columns to datetime (coercing invalid values).
    4. Handles missing values column-by-column based on specified strategies.
    5. Filters out rows containing negative values in designated columns.
    """
    df = df.copy()
    
    # 1. Standardize columns
    df = standardize_columns(df)
    
    # Standardize parameters so they match the standardized column names
    std_date_cols = []
    if date_cols:
        for c in date_cols:
            c_std = str(c).strip().replace('"', '').replace("'", "").replace(' ', '_').replace('-', '_').replace('.', '_').lower()
            std_date_cols.append(c_std)
            
    std_non_neg_cols = []
    if numeric_non_negative_cols:
        for c in numeric_non_negative_cols:
            c_std = str(c).strip().replace('"', '').replace("'", "").replace(' ', '_').replace('-', '_').replace('.', '_').lower()
            std_non_neg_cols.append(c_std)
            
    std_strategies = {}
    if missing_value_strategies:
        for col, strat in missing_value_strategies.items():
            col_std = str(col).strip().replace('"', '').replace("'", "").replace(' ', '_').replace('-', '_').replace('.', '_').lower()
            std_strategies[col_std] = strat

    # 2. Remove duplicates
    if drop_duplicates:
        initial_len = len(df)
        df = df.drop_duplicates()
        removed = initial_len - len(df)
        if removed > 0:
            logger.info(f"Removed {removed} duplicate rows.")

    # 3. Convert date columns
    for col in std_date_cols:
        if col in df.columns:
            logger.info(f"Converting column '{col}' to datetime.")
            df[col] = pd.to_datetime(df[col], errors='coerce')
            invalid_dates = df[col].isnull().sum()
            if invalid_dates > 0:
                logger.warning(f"Removing {invalid_dates} rows with unparseable dates in '{col}'.")
                df = df.dropna(subset=[col])

    # 4. Remove obvious invalid records (non-negative columns check)
    for col in std_non_neg_cols:
        if col in df.columns:
            initial_len = len(df)
            df = df[df[col] >= 0]
            removed = initial_len - len(df)
            if removed > 0:
                logger.info(f"Removed {removed} invalid records where '{col}' < 0.")

    # 5. Handle missing values
    for col, strategy in std_strategies.items():
        if col in df.columns:
            null_count = df[col].isnull().sum()
            if null_count > 0:
                if strategy == 'drop':
                    df = df.dropna(subset=[col])
                    logger.info(f"Dropped {null_count} rows with missing value in '{col}' due to 'drop' strategy.")
                elif strategy == 'mean':
                    val = df[col].mean()
                    df[col] = df[col].fillna(val)
                    logger.info(f"Imputed {null_count} missing values in '{col}' with mean: {val}")
                elif strategy == 'median':
                    val = df[col].median()
                    df[col] = df[col].fillna(val)
                    logger.info(f"Imputed {null_count} missing values in '{col}' with median: {val}")
                elif strategy == 'mode':
                    val = df[col].mode()[0] if not df[col].mode().empty else None
                    if val is not None:
                        df[col] = df[col].fillna(val)
                        logger.info(f"Imputed {null_count} missing values in '{col}' with mode: {val}")
                else:
                    df[col] = df[col].fillna(strategy)
                    logger.info(f"Filled {null_count} missing values in '{col}' with value: {strategy}")

    # Default fallback for any remaining columns with null values
    remaining_nulls = df.isnull().sum()
    for col in remaining_nulls[remaining_nulls > 0].index:
        null_count = df[col].isnull().sum()
        if pd.api.types.is_numeric_dtype(df[col]):
            val = df[col].median()
            df[col] = df[col].fillna(val)
            logger.info(f"Default fallback: Imputed {null_count} nulls in numeric '{col}' with median: {val}")
        else:
            df[col] = df[col].fillna('Unknown')
            logger.info(f"Default fallback: Filled {null_count} nulls in categorical '{col}' with 'Unknown'")

    return df

def save_processed_data(
    df: pd.DataFrame, 
    dest_path: Union[str, Path]
) -> None:
    """
    Saves the cleaned DataFrame to the specified processed file path.
    """
    path = Path(dest_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)
    logger.info(f"Successfully saved cleaned dataset to: {path}")
