import os
import json
import logging
import inspect
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Tuple, List, Dict, Any

import pandas as pd
import numpy as np
import xgboost as xgb
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score, mean_absolute_percentage_error
import joblib

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("ml_pipeline.train_xgboost")

BASE_DIR = Path(__file__).resolve().parent.parent
FEATURES_DIR = BASE_DIR / "datasets" / "features"
SAVED_MODELS_DIR = BASE_DIR / "saved_models"
REPORTS_DIR = BASE_DIR / "reports"

class CategoricalEncoder:
    """
    A reusable categorical features preprocessor for XGBoost training/inference pipelines.
    Automatically detects string/object/categorical columns and encodes them.
    Preferred order:
    1. Pandas 'category' dtype if XGBoost supports categorical features.
    2. Otherwise, OneHotEncoder for low-cardinality columns.
    3. LabelEncoder for high-cardinality columns.
    """
    def __init__(self, cardinality_threshold: int = 10):
        self.cardinality_threshold = cardinality_threshold
        self.is_category_supported = self._check_xgboost_category_support()
        self.encoders = {}
        self.encoded_cols_info = {}
        self.categorical_cols = []
        self.low_card_cols = []
        self.high_card_cols = []
        self.one_hot_features_out = {}

    def _check_xgboost_category_support(self) -> bool:
        try:
            version_str = xgb.__version__
            parts = []
            for p in version_str.split('.'):
                num_str = "".join([c for c in p if c.isdigit()])
                if num_str:
                    parts.append(int(num_str))
            return parts >= [1, 5, 0]
        except Exception:
            return False


    def fit(self, df: pd.DataFrame, columns: List[str]):
        """
        Identifies and fits encoders for categorical columns.
        """
        self.categorical_cols = []
        self.low_card_cols = []
        self.high_card_cols = []
        self.encoders = {}
        self.encoded_cols_info = {}
        self.one_hot_features_out = {}

        for col in columns:
            if col not in df.columns:
                continue
                
            dtype = df[col].dtype
            is_cat = False
            # Check if categorical, object, or string dtype
            if isinstance(dtype, pd.CategoricalDtype) or dtype.name == "category":
                is_cat = True
            elif pd.api.types.is_object_dtype(dtype) or pd.api.types.is_string_dtype(dtype):
                # Ensure it's not a numeric or datetime column stored as object
                if not pd.api.types.is_numeric_dtype(dtype) and not pd.api.types.is_datetime64_any_dtype(dtype):
                    is_cat = True
                    
            if is_cat:
                self.categorical_cols.append(col)
                if self.is_category_supported:
                    self.encoded_cols_info[col] = "Pandas Category dtype"
                else:
                    cardinality = df[col].astype(str).nunique()
                    if cardinality <= self.cardinality_threshold:
                        self.low_card_cols.append(col)
                        from sklearn.preprocessing import OneHotEncoder
                        try:
                            encoder = OneHotEncoder(sparse_output=False, handle_unknown="ignore")
                        except TypeError:
                            encoder = OneHotEncoder(sparse=False, handle_unknown="ignore")
                        encoder.fit(df[[col]].astype(str))
                        self.encoders[col] = encoder
                        self.encoded_cols_info[col] = f"OneHotEncoder (cardinality: {cardinality})"
                    else:
                        self.high_card_cols.append(col)
                        from sklearn.preprocessing import LabelEncoder
                        encoder = LabelEncoder()
                        encoder.fit(df[col].astype(str))
                        self.encoders[col] = encoder
                        self.encoded_cols_info[col] = f"LabelEncoder (cardinality: {cardinality})"
                        
        if self.categorical_cols:
            print("\nCategorical Feature Encoding Summary:")
            for col, method in self.encoded_cols_info.items():
                print(f"  - '{col}': Encoded using {method}")
            print()
        else:
            logger.info("No categorical columns detected for encoding.")
            
        return self

    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Transforms the dataframe using the fitted encodings.
        """
        df = df.copy()
        for col in self.categorical_cols:
            if col not in df.columns:
                continue
                
            if self.is_category_supported:
                df[col] = df[col].astype("category")
            else:
                if col in self.low_card_cols:
                    encoder = self.encoders[col]
                    encoded_arr = encoder.transform(df[[col]].astype(str))
                    try:
                        feat_names = list(encoder.get_feature_names_out([col]))
                    except AttributeError:
                        feat_names = list(encoder.get_feature_names([col]))
                    self.one_hot_features_out[col] = feat_names
                    
                    encoded_df = pd.DataFrame(encoded_arr, columns=feat_names, index=df.index)
                    df = pd.concat([df.drop(columns=[col]), encoded_df], axis=1)
                elif col in self.high_card_cols:
                    encoder = self.encoders[col]
                    mapping = {cl: idx for idx, cl in enumerate(encoder.classes_)}
                    default_idx = len(encoder.classes_)
                    vals = df[col].astype(str)
                    df[col] = vals.map(mapping).fillna(default_idx).astype(int)
        return df



def find_pricing_dataset(features_dir: Path) -> Path:
    """
    Recursively scans the features directory for a CSV dataset containing a 'price' column.
    """
    logger.info(f"Scanning features directory: {features_dir} for pricing datasets...")
    for root, _, files in os.walk(features_dir):
        for file in files:
            if file.endswith(".csv"):
                file_path = Path(root) / file
                try:
                    # Read only the header first to check columns quickly
                    header_df = pd.read_csv(file_path, nrows=0)
                    if any("price" in col.lower() for col in header_df.columns):
                        logger.info(f"Found suitable pricing dataset: {file_path}")
                        return file_path
                except Exception as e:
                    logger.warning(f"Error reading header of {file_path}: {e}")
                    
    raise FileNotFoundError("Could not find any feature CSV dataset containing a 'price' column.")

def identify_target_and_date_cols(df: pd.DataFrame) -> Tuple[str, str]:
    """
    Automatically detects the target column (matching 'price') and temporal sorting column.
    """
    target_col = None
    date_col = None
    
    for col in df.columns:
        col_lower = col.lower()
        if "price" in col_lower:
            target_col = col
        elif "date" in col_lower or "time" in col_lower:
            date_col = col
            
    if not target_col:
        raise ValueError("Could not automatically identify any target column containing 'price'.")
        
    logger.info(f"Automatically identified target column: '{target_col}'")
    if date_col:
        logger.info(f"Automatically identified date/sorting column: '{date_col}'")
    else:
        logger.info("No date/sorting column identified. Data will be split randomly.")
        
    return target_col, date_col

def prepare_features(
    df: pd.DataFrame, 
    target_col: str, 
    date_col: str, 
    encoder: CategoricalEncoder = None
) -> Tuple[pd.DataFrame, pd.Series, List[str]]:
    """
    Cleans features, drops leakage or high-cardinality columns, and encodes categoricals.
    """
    df = df.copy()
    
    # Columns to exclude: identifiers, date columns, high-cardinality description text, and target
    exclude_keywords = ["invoice", "description", "customer_id", "id", date_col.lower() if date_col else ""]
    exclude_cols = []
    for col in df.columns:
        if col == target_col:
            continue
        col_lower = col.lower()
        if any(kw == col_lower or (len(kw) > 2 and kw in col_lower) for kw in exclude_keywords):
            exclude_cols.append(col)
            
    # Keep only columns not in exclude list
    features = [col for col in df.columns if col != target_col and col not in exclude_cols]
    
    # Drop rows containing missing target or features
    df = df.dropna(subset=[target_col] + features)
    
    # Encode categorical columns using CategoricalEncoder
    if encoder is not None:
        encoder.fit(df, features)
        df = encoder.transform(df)
        
        # Rebuild features list if column structure changed (e.g. OneHotEncoder)
        new_features = []
        for col in features:
            if col in encoder.categorical_cols and not encoder.is_category_supported:
                if col in encoder.low_card_cols:
                    new_features.extend(encoder.one_hot_features_out.get(col, []))
                else:
                    new_features.append(col)
            else:
                new_features.append(col)
        features = new_features
            
    X = df[features].reset_index(drop=True)
    y = df[target_col].reset_index(drop=True)
    
    logger.info(f"Prepared {len(features)} features for training: {features}")
    return X, y, features


def temporal_split(
    X: pd.DataFrame, 
    y: pd.Series
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.Series, pd.Series, pd.Series]:
    """
    Splits features and target chronologically (70% train, 15% validation, 15% test).
    Data is assumed to be sorted chronologically beforehand.
    """
    n = len(X)
    train_idx = int(n * 0.70)
    val_idx = int(n * 0.85)
    
    X_train, y_train = X.iloc[:train_idx].copy(), y.iloc[:train_idx].copy()
    X_val, y_val = X.iloc[train_idx:val_idx].copy(), y.iloc[train_idx:val_idx].copy()
    X_test, y_test = X.iloc[val_idx:].copy(), y.iloc[val_idx:].copy()
    
    return X_train, X_val, X_test, y_train, y_val, y_test

def calculate_metrics(y_true: pd.Series, y_pred: np.ndarray) -> Dict[str, float]:
    """
    Calculates regression metrics: MAE, RMSE, R2, MAPE.
    """
    mae = mean_absolute_error(y_true, y_pred)
    mse = mean_squared_error(y_true, y_pred)
    rmse = np.sqrt(mse)
    r2 = r2_score(y_true, y_pred)
    mape = mean_absolute_percentage_error(y_true, y_pred)
    
    return {
        "mae": float(mae),
        "rmse": float(rmse),
        "r2_score": float(r2),
        "mape": float(mape)
    }

def train_xgboost(
    X_train: pd.DataFrame, 
    y_train: pd.Series, 
    X_val: pd.DataFrame, 
    y_val: pd.Series
) -> xgb.XGBRegressor:
    """
    Trains the XGBoost Regressor model using reasonable default hyperparameters.
    """
    logger.info("Initializing XGBoost Regressor model...")
    
    # Check if category dtype is supported by the installed XGBoost
    try:
        sig = inspect.signature(xgb.XGBRegressor.__init__)
        is_category_supported = "enable_categorical" in sig.parameters
    except Exception:
        is_category_supported = False

    # Version-independent reasonable hyperparameter defaults
    model_params = {
        "n_estimators": 100,
        "max_depth": 6,
        "learning_rate": 0.1,
        "random_state": 42,
        "n_jobs": -1
    }
    if is_category_supported:
        model_params["enable_categorical"] = True
        logger.info("XGBoost categorical feature support enabled.")
        
    model = xgb.XGBRegressor(**model_params)
    
    logger.info("Fitting XGBoost model on the training set...")
    model.fit(
        X_train, 
        y_train, 
        eval_set=[(X_val, y_val)],
        verbose=20
    )
    return model


def main():
    logger.info("Starting XGBoost dynamic price prediction training...")
    
    # 1. Locate and load dataset
    dataset_path = find_pricing_dataset(FEATURES_DIR)
    # Mixed type warning handled on low memory import
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
    encoder = CategoricalEncoder()
    X, y, features = prepare_features(df, target_col, date_col, encoder)
    
    # 4. Split data (70% train, 15% validation, 15% test)
    X_train, X_val, X_test, y_train, y_val, y_test = temporal_split(X, y)
    logger.info(f"Split completed: Train={X_train.shape[0]} rows, Val={X_val.shape[0]} rows, Test={X_test.shape[0]} rows")
    
    # 5. Train model
    start_train_time = time.time()
    model = train_xgboost(X_train, y_train, X_val, y_val)
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
    ranked_importances = sorted(
        zip(features, [float(imp) for imp in importances]), 
        key=lambda x: x[1], 
        reverse=True
    )
    feature_importance_dict = {feat: imp for feat, imp in ranked_importances}
    
    # 8. Save artifacts
    logger.info("Saving trained model and evaluation report...")
    SAVED_MODELS_DIR.mkdir(parents=True, exist_ok=True)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    
    model_save_path = SAVED_MODELS_DIR / "price_prediction_xgboost.joblib"
    joblib.dump(model, model_save_path)
    logger.info(f"Saved model joblib to: {model_save_path}")
    
    encoder_save_path = SAVED_MODELS_DIR / "categorical_encoder.joblib"
    joblib.dump(encoder, encoder_save_path)
    logger.info(f"Saved categorical encoder to: {encoder_save_path}")
    
    
    metrics_report = {
        "model_type": "XGBoost Regressor",
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
    
    metrics_save_path = REPORTS_DIR / "model_metrics.json"
    with open(metrics_save_path, "w", encoding="utf-8") as f:
        json.dump(metrics_report, f, indent=2)
    logger.info(f"Saved evaluation metrics report to: {metrics_save_path}")
    
    # 9. Print Training Summary
    print("\n" + "="*80)
    print("                    XGBOOST PRICE PREDICTION MODEL SUMMARY")
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
        print(f"  - {feat:<25}: {imp:.4f} ({imp*100:.2f}%)")
    if len(ranked_importances) > 10:
        print(f"  ... (+ {len(ranked_importances) - 10} more features)")
    print("="*80 + "\n")

if __name__ == "__main__":
    main()
