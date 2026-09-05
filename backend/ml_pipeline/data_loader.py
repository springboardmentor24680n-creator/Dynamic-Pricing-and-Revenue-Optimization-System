import os
import logging
from pathlib import Path
from typing import List, Union, Optional
import pandas as pd

logger = logging.getLogger("ml_pipeline.data_loader")
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

def detect_file_format(file_path: Union[str, Path]) -> str:
    """
    Detects whether the file is CSV or Excel based on the file extension.
    """
    suffix = Path(file_path).suffix.lower()
    if suffix in ['.csv']:
        return 'csv'
    elif suffix in ['.xlsx', '.xls', '.xlsm', '.xlsb']:
        return 'excel'
    else:
        raise ValueError(f"Unsupported file format '{suffix}' for file: {file_path}")

def load_data(
    file_path: Union[str, Path], 
    required_columns: Optional[List[str]] = None,
    **kwargs
) -> pd.DataFrame:
    """
    Loads data from a CSV or Excel file into a Pandas DataFrame.
    Validates required columns and logs dataset details.
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")
        
    fmt = detect_file_format(path)
    logger.info(f"Loading data from: {path} (Format: {fmt.upper()})")
    
    try:
        if fmt == 'csv':
            df = pd.read_csv(path, **kwargs)
        else:
            try:
                df = pd.read_excel(path, **kwargs)
            except ImportError as e:
                logger.error("Required dependency 'openpyxl' is missing for reading Excel files.")
                raise ImportError(
                    "Please install 'openpyxl' to load Excel files: pip install openpyxl"
                ) from e
    except Exception as e:
        logger.error(f"Failed to load file {path.name}: {e}")
        raise e

    # Log dataset stats
    rows, cols = df.shape
    missing_by_col = df.isnull().sum()
    total_missing = missing_by_col.sum()
    
    logger.info(f"Successfully loaded '{path.name}'")
    logger.info(f"Dimensions: {rows} rows, {cols} columns")
    logger.info(f"Total missing values: {total_missing}")
    
    if total_missing > 0:
        non_zero_missing = missing_by_col[missing_by_col > 0]
        missing_pct = (non_zero_missing / rows) * 100
        missing_summary = {
            col: f"{val} ({missing_pct[col]:.2f}%)" 
            for col, val in non_zero_missing.items()
        }
        logger.info(f"Missing values by column: {missing_summary}")

    # Validate required columns
    if required_columns:
        # Strip quotes and spaces from columns to perform clean comparison
        existing_cols_clean = [str(c).strip().replace('"', '').replace("'", "") for c in df.columns]
        req_cols_clean = [str(c).strip().replace('"', '').replace("'", "") for c in required_columns]
        
        missing_cols = [
            req for req, req_clean in zip(required_columns, req_cols_clean)
            if req_clean not in existing_cols_clean
        ]
        if missing_cols:
            raise ValueError(
                f"Validation failed: Missing required columns {missing_cols} in {path.name}. "
                f"Available columns: {list(df.columns)}"
            )
        logger.info(f"Validated all required columns exist in {path.name}.")
        
    return df
