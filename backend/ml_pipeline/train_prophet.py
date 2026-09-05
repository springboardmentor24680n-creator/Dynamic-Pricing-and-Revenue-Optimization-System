import os
import sys
import json
import logging
import time
import pickle
from datetime import datetime, timezone
from pathlib import Path
from typing import Tuple, List, Dict, Any

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from prophet import Prophet
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score, mean_absolute_percentage_error

# Ensure the backend directory is in the system path to allow absolute imports of ml_pipeline
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.append(str(BASE_DIR))

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("ml_pipeline.train_prophet")

FEATURES_DIR = BASE_DIR / "datasets" / "features"
SAVED_MODELS_DIR = BASE_DIR / "saved_models"
REPORTS_DIR = BASE_DIR / "reports"
PLOTS_DIR = REPORTS_DIR / "plots"

def find_demand_dataset(features_dir: Path) -> Path:
    """
    Recursively scans the features directory for a CSV dataset containing 'sales' or 'demand' column.
    """
    logger.info(f"Scanning features directory: {features_dir} for demand datasets...")
    for root, _, files in os.walk(features_dir):
        for file in files:
            if file.endswith(".csv"):
                file_path = Path(root) / file
                try:
                    header_df = pd.read_csv(file_path, nrows=0)
                    col_names = [col.lower() for col in header_df.columns]
                    if "sales" in col_names or "demand" in col_names:
                        logger.info(f"Found suitable demand dataset: {file_path}")
                        return file_path
                except Exception as e:
                    logger.warning(f"Error reading header of {file_path}: {e}")
    
    # Fallback to direct path
    direct_path = features_dir / "demand" / "train.csv"
    if direct_path.exists():
        logger.info(f"Using default demand dataset path: {direct_path}")
        return direct_path
        
    raise FileNotFoundError("Could not find any feature CSV dataset containing 'sales' or 'demand' column.")

def prepare_prophet_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Finds date and sales columns, aggregates them to a daily level, and formats them for Prophet.
    """
    df = df.copy()
    
    # 1. Try to find exact matches first
    exact_targets = ["sales", "demand", "quantity"]
    for tgt in exact_targets:
        for col in df.columns:
            if col.lower() == tgt:
                target_col = col
                break
        if target_col:
            break
            
    exact_dates = ["date", "invoicedate", "datetime", "timestamp"]
    for dt in exact_dates:
        for col in df.columns:
            if col.lower() == dt:
                date_col = col
                break
        if date_col:
            break
            
    # 2. Fall back to substring matches if not found
    if not target_col:
        for col in df.columns:
            col_lower = col.lower()
            if "sales" in col_lower or "demand" in col_lower or "quantity" in col_lower:
                target_col = col
                break
                
    if not date_col:
        for col in df.columns:
            col_lower = col.lower()
            if "date" in col_lower or "time" in col_lower:
                date_col = col
                break
    
    if not target_col:
        raise ValueError("Could not automatically identify any target column (sales, demand, quantity).")
    if not date_col:
        raise ValueError("Could not automatically identify any date column (date, time).")
        
    logger.info(f"Using target column: '{target_col}' and date column: '{date_col}'")
    
    df[date_col] = pd.to_datetime(df[date_col])
    
    # Aggregate to daily level
    daily_df = df.groupby(df[date_col].dt.date)[target_col].sum().reset_index()
    
    # Rename for Prophet
    prophet_df = daily_df.rename(columns={date_col: "ds", target_col: "y"})
    prophet_df["ds"] = pd.to_datetime(prophet_df["ds"])
    prophet_df = prophet_df.dropna()
    
    logger.info(f"Aggregated dataset to daily level. Shape: {prophet_df.shape}")
    return prophet_df

def evaluate_prophet_model(df_prophet: pd.DataFrame, test_horizon: int = 90) -> Dict[str, float]:
    """
    Performs chronological splitting to evaluate model performance on the last test_horizon days.
    """
    train_df = df_prophet.iloc[:-test_horizon].copy()
    test_df = df_prophet.iloc[-test_horizon:].copy()
    
    logger.info(f"Training evaluation model on {len(train_df)} days, validating on last {len(test_df)} days...")
    
    eval_model = Prophet(
        yearly_seasonality=True,
        weekly_seasonality=True,
        daily_seasonality=False
    )
    eval_model.fit(train_df)
    
    future_dates = eval_model.make_future_dataframe(periods=test_horizon)
    forecast = eval_model.predict(future_dates)
    
    pred_test = forecast.tail(test_horizon)
    y_true = test_df["y"].values
    y_pred = pred_test["yhat"].values
    
    mae = mean_absolute_error(y_true, y_pred)
    rmse = np.sqrt(mean_squared_error(y_true, y_pred))
    mape = mean_absolute_percentage_error(y_true, y_pred)
    r2 = r2_score(y_true, y_pred)
    
    metrics = {
        "mae": float(mae),
        "rmse": float(rmse),
        "mape": float(mape),
        "r2_score": float(r2)
    }
    
    logger.info(f"Validation metrics - MAE: {mae:.2f}, RMSE: {rmse:.2f}, MAPE: {mape:.4%}, R²: {r2:.4f}")
    return metrics

def train_final_model(df_prophet: pd.DataFrame) -> Prophet:
    """
    Trains the final Prophet model on the entire historical dataset.
    """
    logger.info("Training final Prophet model on full historical dataset...")
    model = Prophet(
        yearly_seasonality=True,
        weekly_seasonality=True,
        daily_seasonality=False
    )
    model.fit(df_prophet)
    return model

def generate_forecasts(model: Prophet, df_prophet: pd.DataFrame, horizons: List[int] = [7, 30, 90]) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Generates multi-horizon forecasts starting from the day after the last historical date.
    """
    max_horizon = max(horizons)
    logger.info(f"Generating forecasts up to {max_horizon} days into the future...")
    
    future = model.make_future_dataframe(periods=max_horizon)
    forecast = model.predict(future)
    
    historical_end_date = df_prophet["ds"].max()
    future_forecast = forecast[forecast["ds"] > historical_end_date].copy()
    
    forecast_details = {}
    
    for h in horizons:
        horizon_df = future_forecast.head(h)
        total_demand = horizon_df["yhat"].sum()
        avg_demand = horizon_df["yhat"].mean()
        min_demand = horizon_df["yhat"].min()
        max_demand = horizon_df["yhat"].max()
        
        predictions_list = []
        for _, row in horizon_df.iterrows():
            # Calculate confidence score and classification
            epsilon = 1e-5
            width = row["yhat_upper"] - row["yhat_lower"]
            rel_width = width / (abs(row["yhat"]) + epsilon)
            
            # Confidence score is inverted relative width scaled to 0-100%
            conf_score = 100 * (1 - rel_width)
            conf_score = max(0.0, min(100.0, conf_score))
            
            if rel_width < 0.15:
                conf_class = "High"
            elif rel_width < 0.30:
                conf_class = "Medium"
            else:
                conf_class = "Low"
                
            predictions_list.append({
                "date": row["ds"].strftime("%Y-%m-%d"),
                "forecast": float(row["yhat"]),
                "lower_bound": float(row["yhat_lower"]),
                "upper_bound": float(row["yhat_upper"]),
                "confidence_score_percent": round(float(conf_score), 2),
                "confidence_classification": conf_class
            })
            
        forecast_details[f"{h}_days"] = {
            "horizon_days": h,
            "total_forecasted_demand": float(total_demand),
            "average_daily_demand": float(avg_demand),
            "min_daily_demand": float(min_demand),
            "max_daily_demand": float(max_demand),
            "predictions": predictions_list
        }
        
    return forecast, forecast_details

def save_plots(model: Prophet, forecast: pd.DataFrame, df_prophet: pd.DataFrame, plots_dir: Path):
    """
    Saves the Forecast plot, Trend plot, and Seasonality plot.
    """
    plots_dir.mkdir(parents=True, exist_ok=True)
    historical_end_date = df_prophet["ds"].max()
    
    try:
        plt.style.use('seaborn-v0_8-whitegrid')
    except:
        try:
            plt.style.use('ggplot')
        except:
            pass
            
    # 1. Forecast Plot
    fig1 = model.plot(forecast)
    ax = fig1.gca()
    ax.axvline(x=historical_end_date, color="red", linestyle="--", alpha=0.8, label="Forecast Start")
    ax.set_title("Prophet Demand Forecast (7, 30, 90-day Horizons)", fontsize=14, fontweight="bold", pad=15)
    ax.set_xlabel("Date", fontsize=12)
    ax.set_ylabel("Demand Volume", fontsize=12)
    ax.legend(loc="upper left")
    fig1.savefig(plots_dir / "forecast_plot.png", dpi=150)
    plt.close(fig1)
    logger.info(f"Saved forecast plot to: {plots_dir / 'forecast_plot.png'}")
    
    # 2. Trend Plot
    fig2, ax2 = plt.subplots(figsize=(12, 6))
    ax2.plot(forecast["ds"], forecast["trend"], color="#2ca02c", linewidth=2.5, label="Long-term Trend")
    ax2.fill_between(forecast["ds"], forecast["trend_lower"], forecast["trend_upper"], color="#2ca02c", alpha=0.15, label="Trend Uncertainty")
    ax2.axvline(x=historical_end_date, color="red", linestyle="--", alpha=0.8, label="Forecast Start")
    ax2.set_title("Prophet Demand Trend (Historical & Forecast)", fontsize=14, fontweight="bold", pad=15)
    ax2.set_xlabel("Date", fontsize=12)
    ax2.set_ylabel("Trend Value", fontsize=12)
    ax2.legend(loc="upper left")
    ax2.grid(True, linestyle="--", alpha=0.5)
    plt.tight_layout()
    fig2.savefig(plots_dir / "trend_plot.png", dpi=150)
    plt.close(fig2)
    logger.info(f"Saved trend plot to: {plots_dir / 'trend_plot.png'}")
    
    # 3. Seasonality Plot
    has_weekly = 'weekly' in forecast.columns
    has_yearly = 'yearly' in forecast.columns
    
    if has_weekly and has_yearly:
        fig3, (ax_w, ax_y) = plt.subplots(2, 1, figsize=(12, 10))
        
        # Weekly seasonality
        forecast_weekly = forecast.copy()
        forecast_weekly['day_of_week'] = pd.to_datetime(forecast_weekly['ds']).dt.day_name()
        day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        weekly_grouped = forecast_weekly.groupby('day_of_week')['weekly'].first().reindex(day_order)
        
        ax_w.plot(weekly_grouped.index, weekly_grouped.values, marker='o', color='#9467bd', linewidth=2, label="Weekly Effect")
        ax_w.set_title("Weekly Demand Seasonality Pattern", fontsize=12, fontweight="bold")
        ax_w.set_ylabel("Demand Offset", fontsize=10)
        ax_w.grid(True, linestyle="--", alpha=0.5)
        
        # Yearly seasonality
        forecast_yearly = forecast.copy()
        forecast_yearly['day_of_year'] = pd.to_datetime(forecast_yearly['ds']).dt.dayofyear
        yearly_grouped = forecast_yearly.groupby('day_of_year')['yearly'].first().sort_index()
        
        ax_y.plot(yearly_grouped.index, yearly_grouped.values, color='#d62728', linewidth=2, label="Yearly Effect")
        ax_y.set_title("Yearly Demand Seasonality Pattern", fontsize=12, fontweight="bold")
        ax_y.set_xlabel("Day of Year (1 - 365)", fontsize=10)
        ax_y.set_ylabel("Demand Offset", fontsize=10)
        ax_y.grid(True, linestyle="--", alpha=0.5)
        
        plt.tight_layout()
        fig3.savefig(plots_dir / "seasonality_plot.png", dpi=150)
        plt.close(fig3)
        logger.info(f"Saved seasonality plot to: {plots_dir / 'seasonality_plot.png'}")
    else:
        fig3, ax_s = plt.subplots(figsize=(12, 6))
        ax_s.plot(forecast["ds"], forecast.get("additive_terms", np.zeros(len(forecast))), color="#e377c2", linewidth=2)
        ax_s.set_title("Additive Seasonality Over Time", fontsize=14, fontweight="bold", pad=15)
        ax_s.set_xlabel("Date", fontsize=12)
        ax_s.set_ylabel("Seasonality Effect", fontsize=12)
        ax_s.grid(True, linestyle="--", alpha=0.5)
        plt.tight_layout()
        fig3.savefig(plots_dir / "seasonality_plot.png", dpi=150)
        plt.close(fig3)
        logger.info(f"Saved fallback seasonality plot to: {plots_dir / 'seasonality_plot.png'}")

def print_summary(df_prophet: pd.DataFrame, eval_metrics: Dict[str, float], forecast_details: Dict[str, Any]):
    """
    Prints a detailed demand forecasting execution summary to the console.
    """
    print("\n" + "="*80)
    print("                      PROPHET DEMAND FORECASTING SUMMARY")
    print("="*80)
    print(f"Historical Data Range : {df_prophet['ds'].min().strftime('%Y-%m-%d')} to {df_prophet['ds'].max().strftime('%Y-%m-%d')}")
    print(f"Total Historical Days : {len(df_prophet)}")
    print("-"*80)
    print("VALIDATION METRICS (Chronological Split):")
    print(f"  MAE   : {eval_metrics['mae']:.4f}")
    print(f"  RMSE  : {eval_metrics['rmse']:.4f}")
    print(f"  MAPE  : {eval_metrics['mape']:.4%}")
    print(f"  R²    : {eval_metrics['r2_score']:.4f}")
    print("-"*80)
    print("FORECAST HORIZONS SUMMARY:")
    for key, info in forecast_details.items():
        print(f"\n  Horizon: {info['horizon_days']} Days ({key.replace('_', ' ')})")
        print(f"    Total Forecasted Demand : {info['total_forecasted_demand']:.2f}")
        print(f"    Average Daily Demand    : {info['average_daily_demand']:.2f}")
        print(f"    Min Daily Demand        : {info['min_daily_demand']:.2f}")
        print(f"    Max Daily Demand        : {info['max_daily_demand']:.2f}")
        
        first_pred = info['predictions'][0]
        last_pred = info['predictions'][-1]
        print(f"    Start Forecast ({first_pred['date']}) : {first_pred['forecast']:.2f} (Interval: [{first_pred['lower_bound']:.2f}, {first_pred['upper_bound']:.2f}]) - Conf: {first_pred.get('confidence_classification', 'N/A')} ({first_pred.get('confidence_score_percent', 0.0):.1f}%)")
        print(f"    End Forecast ({last_pred['date']})   : {last_pred['forecast']:.2f} (Interval: [{last_pred['lower_bound']:.2f}, {last_pred['upper_bound']:.2f}]) - Conf: {last_pred.get('confidence_classification', 'N/A')} ({last_pred.get('confidence_score_percent', 0.0):.1f}%)")
    print("="*80 + "\n")

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Prophet Demand Forecasting Pipeline")
    parser.add_argument("--inference-only", action="store_true", help="Generate reports/plots from saved model without retraining")
    args = parser.parse_args()
    
    # 1. Discover and load dataset
    dataset_path = find_demand_dataset(FEATURES_DIR)
    df = pd.read_csv(dataset_path)
    logger.info(f"Loaded dataset from: {dataset_path} (Shape: {df.shape})")
    
    # 2. Prepare dataset
    df_prophet = prepare_prophet_data(df)
    
    model_save_path = SAVED_MODELS_DIR / "demand_forecast_prophet.pkl"
    report_save_path = REPORTS_DIR / "demand_forecast.json"
    
    if args.inference_only:
        logger.info("Running in inference-only mode...")
        # Load existing model
        if not model_save_path.exists():
            raise FileNotFoundError(f"Model pickle not found at: {model_save_path}. Run training first.")
        with open(model_save_path, "rb") as f:
            final_model = pickle.load(f)
        logger.info(f"Successfully loaded model from: {model_save_path}")
        
        # Load validation metrics from existing report if it exists
        eval_metrics = {"mae": 0.0, "rmse": 0.0, "mape": 0.0, "r2_score": 0.0}
        if report_save_path.exists():
            try:
                with open(report_save_path, "r", encoding="utf-8") as f:
                    old_report = json.load(f)
                    eval_metrics = old_report.get("metrics", {}).get("validation_holdout", eval_metrics)
                logger.info("Restored historical validation metrics from existing JSON report.")
            except Exception as e:
                logger.warning(f"Could not restore historical validation metrics: {e}")
        training_time = 0.0
    else:
        logger.info("Running in training and evaluation mode...")
        # 3. Model evaluation
        test_horizon = 90
        if len(df_prophet) <= test_horizon * 2:
            test_horizon = int(len(df_prophet) * 0.15)
            
        eval_metrics = evaluate_prophet_model(df_prophet, test_horizon=test_horizon)
        
        # 4. Fit final model
        start_train_time = time.time()
        final_model = train_final_model(df_prophet)
        training_time = time.time() - start_train_time
        logger.info(f"Trained final model in {training_time:.2f} seconds.")
        
        # 6. Save final model
        SAVED_MODELS_DIR.mkdir(parents=True, exist_ok=True)
        with open(model_save_path, "wb") as f:
            pickle.dump(final_model, f)
        logger.info(f"Saved Prophet model pickle to: {model_save_path}")
        
    # 5. Generate forecasts (7, 30, 90 days)
    forecast, forecast_details = generate_forecasts(final_model, df_prophet, horizons=[7, 30, 90])
    
    # 7. Save JSON report
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    report_data = {
        "model_type": "Prophet",
        "dataset_name": dataset_path.name,
        "historical_data_range": {
            "start": df_prophet["ds"].min().strftime("%Y-%m-%d"),
            "end": df_prophet["ds"].max().strftime("%Y-%m-%d")
        },
        "train_samples": len(df_prophet),
        "training_time_seconds": float(training_time),
        "run_date": datetime.now(timezone.utc).isoformat(),
        "metrics": {
            "validation_holdout": eval_metrics
        },
        "forecasts": forecast_details
    }
    
    with open(report_save_path, "w", encoding="utf-8") as f:
        json.dump(report_data, f, indent=2)
    logger.info(f"Saved forecast results JSON to: {report_save_path}")
    
    # Save a separate forecast confidence report
    confidence_save_path = REPORTS_DIR / "forecast_confidence.json"
    horizon_summaries = {}
    for h in [7, 30, 90]:
        h_key = f"{h}_days"
        h_preds = forecast_details[h_key]["predictions"]
        
        scores = [p["confidence_score_percent"] for p in h_preds]
        classes = [p["confidence_classification"] for p in h_preds]
        
        avg_score = sum(scores) / len(scores) if scores else 0.0
        
        horizon_summaries[h_key] = {
            "horizon_days": h,
            "average_confidence_score": round(avg_score, 2),
            "high_confidence_count": classes.count("High"),
            "medium_confidence_count": classes.count("Medium"),
            "low_confidence_count": classes.count("Low")
        }
        
    confidence_report = {
        "model_type": "Prophet",
        "dataset_name": dataset_path.name,
        "run_date": datetime.now(timezone.utc).isoformat(),
        "horizons_confidence_summary": horizon_summaries,
        "predictions_confidence": forecast_details["90_days"]["predictions"]
    }
    
    with open(confidence_save_path, "w", encoding="utf-8") as f:
        json.dump(confidence_report, f, indent=2)
    logger.info(f"Saved forecast confidence report to: {confidence_save_path}")
    
    # 8. Save plots
    save_plots(final_model, forecast, df_prophet, PLOTS_DIR)
    
    # 9. Print summary report
    print_summary(df_prophet, eval_metrics, forecast_details)

if __name__ == "__main__":
    main()
