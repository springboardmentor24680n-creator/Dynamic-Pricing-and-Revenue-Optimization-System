import os
import sys
import json
import logging
import pickle
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any

import pandas as pd
import numpy as np

# Ensure the backend directory is in the system path to allow absolute imports
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.append(str(BASE_DIR))

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("services.trend_classifier")

class TrendClassifierService:
    """
    A reusable service designed to classify time-series trends and seasonal patterns
    from forecast dataframes containing trend and seasonal components.
    """
    def __init__(self, trend_threshold: float = 0.02, seasonality_threshold: float = 0.40):
        self.trend_threshold = trend_threshold
        self.seasonality_threshold = seasonality_threshold

    def classify_trend(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Classifies the trend of a DataFrame containing Prophet forecast values into one of:
        - 'Increasing'
        - 'Decreasing'
        - 'Stable'
        - 'Seasonal' (if seasonality dominates trend variation)
        """
        trend_vals = df["trend"].values
        if len(trend_vals) < 2:
            return {
                "classification": "Stable",
                "metrics": {
                    "trend_percentage_change": 0.0,
                    "trend_start_value": float(trend_vals[0]) if len(trend_vals) > 0 else 0.0,
                    "trend_end_value": float(trend_vals[0]) if len(trend_vals) > 0 else 0.0,
                    "seasonality_strength": 0.0,
                    "trend_variance": 0.0,
                    "seasonality_variance": 0.0
                }
            }
            
        trend_start = trend_vals[0]
        trend_end = trend_vals[-1]
        
        # Calculate percentage change over the period
        trend_change = (trend_end - trend_start) / (abs(trend_start) + 1e-5)
        
        # Calculate combined seasonal variance
        var_seasonal = 0.0
        if "additive_terms" in df.columns:
            var_seasonal = df["additive_terms"].var()
        else:
            seasonal_effect = np.zeros(len(df))
            has_seasonality = False
            if "weekly" in df.columns:
                seasonal_effect += df["weekly"]
                has_seasonality = True
            if "yearly" in df.columns:
                seasonal_effect += df["yearly"]
                has_seasonality = True
            if has_seasonality:
                var_seasonal = pd.Series(seasonal_effect).var()
                
        var_trend = df["trend"].var()
        
        if pd.isna(var_seasonal):
            var_seasonal = 0.0
        if pd.isna(var_trend):
            var_trend = 0.0
            
        total_var = var_trend + var_seasonal
        seasonality_strength = var_seasonal / total_var if total_var > 0 else 0.0
        
        # Classification criteria
        if seasonality_strength > self.seasonality_threshold and var_seasonal > 0.01:
            classification = "Seasonal"
        else:
            if trend_change > self.trend_threshold:
                classification = "Increasing"
            elif trend_change < -self.trend_threshold:
                classification = "Decreasing"
            else:
                classification = "Stable"
                
        return {
            "classification": classification,
            "metrics": {
                "trend_percentage_change": round(float(trend_change) * 100, 2),
                "trend_start_value": float(trend_start),
                "trend_end_value": float(trend_end),
                "seasonality_strength": round(float(seasonality_strength), 4),
                "trend_variance": float(var_trend),
                "seasonality_variance": float(var_seasonal)
            }
        }

def main():
    logger.info("Initializing demand trend classification runner...")
    
    saved_models_dir = BASE_DIR / "saved_models"
    reports_dir = BASE_DIR / "reports"
    features_dir = BASE_DIR / "datasets" / "features"
    
    model_path = saved_models_dir / "demand_forecast_prophet.pkl"
    if not model_path.exists():
        logger.error(f"Prophet model pickle not found at: {model_path}. Please train the model first.")
        sys.exit(1)
        
    # Import loading helpers from train_prophet module
    try:
        from ml_pipeline.train_prophet import find_demand_dataset, prepare_prophet_data
        dataset_path = find_demand_dataset(features_dir)
        df = pd.read_csv(dataset_path)
        df_prophet = prepare_prophet_data(df)
    except Exception as e:
        logger.error(f"Failed to load dataset: {e}")
        sys.exit(1)
        
    # Load model pickle without retraining
    logger.info(f"Loading Prophet model from: {model_path}")
    with open(model_path, "rb") as f:
        model = pickle.load(f)
        
    # Generate predictions (90 days future)
    logger.info("Running forecast prediction for classification...")
    future = model.make_future_dataframe(periods=90)
    forecast = model.predict(future)
    
    # Split forecast
    historical_end_date = df_prophet["ds"].max()
    future_forecast = forecast[forecast["ds"] > historical_end_date]
    
    # Run classification service
    classifier = TrendClassifierService()
    overall_results = classifier.classify_trend(forecast)
    forecast_results = classifier.classify_trend(future_forecast)
    
    # Assemble report
    report = {
        "model_type": "Prophet",
        "dataset_name": dataset_path.name,
        "run_date": datetime.now(timezone.utc).isoformat(),
        "overall_period": {
            "start_date": forecast["ds"].min().strftime("%Y-%m-%d"),
            "end_date": forecast["ds"].max().strftime("%Y-%m-%d"),
            "classification": overall_results["classification"],
            "metrics": overall_results["metrics"]
        },
        "forecast_period": {
            "start_date": future_forecast["ds"].min().strftime("%Y-%m-%d"),
            "end_date": future_forecast["ds"].max().strftime("%Y-%m-%d"),
            "classification": forecast_results["classification"],
            "metrics": forecast_results["metrics"]
        }
    }
    
    # Save JSON results
    reports_dir.mkdir(parents=True, exist_ok=True)
    report_save_path = reports_dir / "trend_classification.json"
    with open(report_save_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    logger.info(f"Saved trend classification report to: {report_save_path}")
    
    # Print execution summary
    print("\n" + "="*80)
    print("                      DEMAND TREND CLASSIFICATION REPORT")
    print("="*80)
    print(f"Overall Period Classification : {report['overall_period']['classification'].upper()}")
    print(f"  Range                       : {report['overall_period']['start_date']} to {report['overall_period']['end_date']}")
    print(f"  Start Value                 : {report['overall_period']['metrics']['trend_start_value']:.2f}")
    print(f"  End Value                   : {report['overall_period']['metrics']['trend_end_value']:.2f}")
    print(f"  Trend Change (%)            : {report['overall_period']['metrics']['trend_percentage_change']:.2f}%")
    print(f"  Seasonality Strength        : {report['overall_period']['metrics']['seasonality_strength']:.4f}")
    print("-"*80)
    print(f"Forecast Period (90 Days)     : {report['forecast_period']['classification'].upper()}")
    print(f"  Range                       : {report['forecast_period']['start_date']} to {report['forecast_period']['end_date']}")
    print(f"  Start Value                 : {report['forecast_period']['metrics']['trend_start_value']:.2f}")
    print(f"  End Value                   : {report['forecast_period']['metrics']['trend_end_value']:.2f}")
    print(f"  Trend Change (%)            : {report['forecast_period']['metrics']['trend_percentage_change']:.2f}%")
    print(f"  Seasonality Strength        : {report['forecast_period']['metrics']['seasonality_strength']:.4f}")
    print("="*80 + "\n")

if __name__ == "__main__":
    main()
