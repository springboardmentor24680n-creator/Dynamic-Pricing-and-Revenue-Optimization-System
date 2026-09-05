import os
import sys
import logging
import pickle
from pathlib import Path
from typing import Dict, Any, List

import pandas as pd

# Ensure the backend directory is in the system path to allow absolute imports
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.append(str(BASE_DIR))

from ml_pipeline.train_price_model import SAVED_MODELS_DIR

logger = logging.getLogger("services.forecast_service")

class ForecastService:
    """
    A reusable service designed to load the pre-trained Prophet demand forecasting model
    and generate demand projections across varying horizons.
    """
    _forecast_cache = {}
    _model = None

    def __init__(self, model_path: Path = None):
        if model_path is None:
            model_path = SAVED_MODELS_DIR / "demand_forecast_prophet.pkl"
        self.model_path = model_path
        self.model = self._load_model()
        
    def _load_model(self) -> Any:
        if ForecastService._model is None:
            if not self.model_path.exists():
                raise FileNotFoundError(f"Prophet demand forecasting model not found at: {self.model_path}")
            logger.info(f"Loading Prophet demand model from: {self.model_path}")
            with open(self.model_path, "rb") as f:
                ForecastService._model = pickle.load(f)
        return ForecastService._model
            
    def generate_forecast(self, periods: int) -> pd.DataFrame:
        """
        Generates demand predictions for the specified future day count.
        """
        if periods not in ForecastService._forecast_cache:
            logger.info(f"Generating new Prophet forecast for {periods} periods...")
            future = self.model.make_future_dataframe(periods=periods)
            forecast = self.model.predict(future)
            ForecastService._forecast_cache[periods] = forecast
        return ForecastService._forecast_cache[periods]
        
    def generate_multi_horizon_forecasts(self) -> Dict[str, Any]:
        """
        Generates 7-day, 30-day, and 90-day forecasts, returning summarized demand and details.
        """
        # Run forecast for 90 days (covers 7, 30, and 90)
        forecast = self.generate_forecast(90)
        
        # The last 90 rows correspond to the forecast period.
        forecast_period = forecast.tail(90).reset_index(drop=True)
        
        horizons = {7: "7_days", 30: "30_days", 90: "90_days"}
        summaries = {}
        
        for days, name in horizons.items():
            df_slice = forecast_period.head(days)
            total_demand = float(df_slice["yhat"].sum())
            avg_demand = float(df_slice["yhat"].mean())
            
            # Forecast confidence width approximation
            # relative_width = (yhat_upper - yhat_lower) / yhat
            widths = (df_slice["yhat_upper"] - df_slice["yhat_lower"]) / (df_slice["yhat"] + 1e-5)
            avg_width = float(widths.mean())
            confidence_score = max(0.0, min(100.0, 100.0 * (1.0 - avg_width)))
            
            summaries[name] = {
                "horizon_days": days,
                "total_predicted_demand": round(total_demand, 2),
                "average_daily_demand": round(avg_demand, 2),
                "confidence_score_percent": round(confidence_score, 2),
                "predictions": [
                    {
                        "date": row["ds"].strftime("%Y-%m-%d"),
                        "forecast": round(float(row["yhat"]), 2),
                        "lower_bound": round(float(row["yhat_lower"]), 2),
                        "upper_bound": round(float(row["yhat_upper"]), 2)
                    }
                    for _, row in df_slice.iterrows()
                ]
            }
            
        return summaries

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("Testing ForecastService...")
    try:
        service = ForecastService()
        forecasts = service.generate_multi_horizon_forecasts()
        print("Forecast Projections Success!")
        for h, summary in forecasts.items():
            print(f"  Horizon: {h}")
            print(f"    Total Demand : {summary['total_predicted_demand']} units")
            print(f"    Avg Daily    : {summary['average_daily_demand']} units")
            print(f"    Confidence   : {summary['confidence_score_percent']}%")
    except Exception as e:
        print(f"Forecast Projections Failed: {e}")
