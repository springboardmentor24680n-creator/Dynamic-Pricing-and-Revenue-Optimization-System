import os
import sys
import json
import logging
import time
import pickle
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Any, Tuple

import pandas as pd
import numpy as np
import joblib

# Ensure the backend directory is in the system path to allow absolute imports
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.append(str(BASE_DIR))

# Import dataset lookup from the existing price training pipeline
from ml_pipeline.train_price_model import find_pricing_dataset, FEATURES_DIR, SAVED_MODELS_DIR, REPORTS_DIR

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("ml_pipeline.price_recommendation")

class PriceRecommendationEngine:
    """
    A modular price recommendation engine that combines:
    - Predicted Price (from LightGBM)
    - Forecasted Demand Trend (from Prophet reports)
    - Current Inventory levels (simulated via daily sales velocity)
    - Historical Sales and Revenue trends
    - Economic price elasticity of demand
    """
    def __init__(
        self,
        lgb_model_path: Path,
        trend_report_path: Path,
        elasticity: float = -1.5
    ):
        self.elasticity = elasticity
        self.model = self._load_model(lgb_model_path)
        self.prophet_trend = self._load_prophet_trend(trend_report_path)

    def _load_model(self, path: Path) -> Any:
        logger.info(f"Loading LightGBM price prediction model from: {path}")
        return joblib.load(path)

    def _load_prophet_trend(self, path: Path) -> str:
        """
        Loads the demand trend classification from the Prophet trend classification report.
        """
        if path.exists():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    report = json.load(f)
                    trend = report.get("forecast_period", {}).get("classification", "Stable")
                    logger.info(f"Loaded Prophet demand trend state: '{trend}'")
                    return trend
            except Exception as e:
                logger.warning(f"Failed to parse trend classification report: {e}")
        logger.info("Prophet demand trend classification report not found. Defaulting to 'Stable'.")
        return "Stable"

    def get_demand_multiplier(self) -> float:
        """
        Translates Prophet demand trend state into a price adjustment multiplier.
        """
        if self.prophet_trend in ["Seasonal", "Increasing"]:
            return 1.03  # Strong demand supports premium pricing
        elif self.prophet_trend == "Decreasing":
            return 0.97  # Falling demand warrants discount pricing
        else:
            return 1.00  # Stable demand

    def recommend_prices(self, df: pd.DataFrame, num_products: int = 100) -> List[Dict[str, Any]]:
        """
        Processes historical transactions, predicts baseline prices, overlays inventory and demand constraints,
        and estimates expected demand, revenue, and improvement metrics.
        """
        df = df.copy()
        
        # Sort chronologically to get the latest features representing current state
        date_col = "invoicedate" if "invoicedate" in df.columns else "date"
        if date_col in df.columns:
            df[date_col] = pd.to_datetime(df[date_col])
            df = df.sort_values(by=date_col)
            
        logger.info("Aggregating historical transactions and locating latest state features...")
        latest_df = df.groupby("stockcode").last().reset_index()
        
        # Calculate historical sales, average price, average daily volume, and total revenue
        agg_df = df.groupby("stockcode").agg({
            "price": "mean",
            "quantity": ["sum", "mean"],
            "revenue": "sum"
        }).reset_index()
        
        # Flatten column multi-index
        agg_df.columns = ["stockcode", "avg_price", "total_quantity", "avg_quantity", "total_revenue"]
        
        # Merge latest features with aggregated statistics
        product_df = pd.merge(latest_df, agg_df, on="stockcode")
        
        # Select top products by historical revenue
        product_df = product_df.sort_values(by="total_revenue", ascending=False).head(num_products)
        
        recommendations = []
        demand_mult = self.get_demand_multiplier()
        
        # Ensure category columns are category type for LightGBM
        for col in ["stockcode", "country"]:
            if col in product_df.columns:
                product_df[col] = product_df[col].astype("category")
                
        # Features list expected by the LightGBM model
        features = [
            "quantity", "revenue", "year", "month", "week", "day", "day_of_week", "quarter",
            "quantity_lag_1", "quantity_lag_7", "quantity_rolling_mean_7", "quantity_rolling_mean_14",
            "stockcode", "country"
        ]
        
        # Run price predictions
        logger.info(f"Running LightGBM price prediction over {len(product_df)} products...")
        X = product_df[features]
        predicted_prices = self.model.predict(X)
        product_df["predicted_price"] = predicted_prices
        
        # Iterate and generate recommendations
        for _, row in product_df.iterrows():
            stockcode = str(row["stockcode"])
            current_price = float(row["price"])
            pred_price = float(row["predicted_price"])
            avg_daily_sales = float(row["avg_quantity"])
            total_quantity = float(row["total_quantity"])
            total_revenue = float(row["total_revenue"])
            
            # Deterministic pseudo-random seed based on stockcode hash to simulate current inventory
            np.random.seed(abs(hash(stockcode)) % (2**32))
            days_of_supply = np.random.uniform(5, 45)
            current_inventory = int(avg_daily_sales * days_of_supply)
            
            # Inventory rule logic
            if days_of_supply < 10:
                inv_mult = 1.08  # Low stock: premium pricing to slow down sales and expand margins
                inv_status = "Low Inventory (Stockout Risk)"
            elif days_of_supply > 30:
                inv_mult = 0.92  # Excess stock: mark down to clear stock
                inv_status = "Excess Inventory (Clearance)"
            else:
                inv_mult = 1.00  # Balanced inventory
                inv_status = "Healthy Inventory Level"
                
            # Combine signals to compute recommended price
            recommended_price = pred_price * inv_mult * demand_mult
            
            # Apply safety bounds (P_rec must stay within +/- 20% of P_current)
            min_allowed = current_price * 0.80
            max_allowed = current_price * 1.20
            recommended_price = max(min_allowed, min(max_allowed, recommended_price))
            
            # Ensure price is valid
            recommended_price = max(0.01, recommended_price)
            
            # Price Difference calculations
            price_diff = recommended_price - current_price
            price_diff_pct = (price_diff / current_price) * 100
            
            # Formulate recommendation actions
            if price_diff_pct > 2.0:
                action = "Increase Price"
                reason = f"Supported by LightGBM model price (₹{pred_price:.2f}) and {inv_status}."
            elif price_diff_pct < -2.0:
                action = "Decrease Price"
                reason = f"Recommended by LightGBM model price (₹{pred_price:.2f}) and {inv_status}."
            else:
                action = "Maintain Price"
                reason = f"Current price is well-aligned with model predicted price (₹{pred_price:.2f}) and {inv_status}."
                
            # Economic demand elasticity projection
            # Elasticity is negative (e.g. -1.5): Price increase -> demand drops; price drop -> demand increases
            expected_demand_mult = 1.0 + (self.elasticity * (recommended_price - current_price) / current_price)
            # Clip multipliers to prevent extreme projections
            expected_demand_mult = max(0.2, min(2.0, expected_demand_mult))
            
            expected_demand = total_quantity * expected_demand_mult
            expected_revenue = expected_demand * recommended_price
            
            revenue_improvement = expected_revenue - total_revenue
            revenue_improvement_pct = (revenue_improvement / (total_revenue + 1e-5)) * 100
            
            recommendations.append({
                "stockcode": stockcode,
                "country": str(row["country"]),
                "current_price": round(current_price, 2),
                "predicted_price": round(pred_price, 2),
                "recommended_price": round(recommended_price, 2),
                "price_difference": round(price_diff, 2),
                "price_difference_percentage": round(price_diff_pct, 2),
                "current_inventory": int(current_inventory),
                "days_of_supply": round(days_of_supply, 1),
                "historical_sales": int(total_quantity),
                "historical_revenue": round(total_revenue, 2),
                "expected_demand": round(expected_demand, 2),
                "expected_revenue": round(expected_revenue, 2),
                "revenue_improvement": round(revenue_improvement, 2),
                "revenue_improvement_percentage": round(revenue_improvement_pct, 2),
                "recommendation": action,
                "reasoning": reason
            })
            
        return recommendations

def load_historical_data() -> pd.DataFrame:
    """
    Locates and reads the primary retail features dataset.
    """
    dataset_path = find_pricing_dataset(FEATURES_DIR)
    logger.info(f"Loading retail features dataset from: {dataset_path}")
    return pd.read_csv(dataset_path, low_memory=False)

def main():
    logger.info("Initializing Price Recommendation Engine run...")
    
    lgb_model_path = SAVED_MODELS_DIR / "price_prediction_lightgbm.joblib"
    trend_report_path = REPORTS_DIR / "trend_classification.json"
    report_save_path = REPORTS_DIR / "price_recommendations.json"
    
    if not lgb_model_path.exists():
        logger.error(f"LightGBM model not found at: {lgb_model_path}. Train LightGBM model first.")
        sys.exit(1)
        
    try:
        # Load retail dataset
        df = load_historical_data()
        
        # Initialize recommendation engine
        engine = PriceRecommendationEngine(
            lgb_model_path=lgb_model_path,
            trend_report_path=trend_report_path,
            elasticity=-1.5
        )
        
        # Generate recommendations for top 100 products
        recommendations = engine.recommend_prices(df, num_products=100)
        
        # Save output JSON
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        
        actions = [r["recommendation"] for r in recommendations]
        revenue_imp_pcts = [r["revenue_improvement_percentage"] for r in recommendations]
        avg_rev_improvement = sum(revenue_imp_pcts) / len(revenue_imp_pcts) if revenue_imp_pcts else 0.0
        
        report_output = {
            "run_date": datetime.now(timezone.utc).isoformat(),
            "elasticity_used": engine.elasticity,
            "demand_trend_used": engine.prophet_trend,
            "total_products_evaluated": len(recommendations),
            "summary_statistics": {
                "increase_price_count": actions.count("Increase Price"),
                "decrease_price_count": actions.count("Decrease Price"),
                "maintain_price_count": actions.count("Maintain Price"),
                "average_expected_revenue_improvement_percent": round(avg_rev_improvement, 2)
            },
            "recommendations": recommendations
        }
        
        with open(report_save_path, "w", encoding="utf-8") as f:
            json.dump(report_output, f, indent=2)
            
        logger.info(f"Successfully saved recommendations report to: {report_save_path}")
        
        # Print summary report
        print("\n" + "="*80)
        print("                      AI PRICE RECOMMENDATION SUMMARY REPORT")
        print("="*80)
        print(f"Prophet Demand Trend State : {engine.prophet_trend.upper()}")
        print(f"Total Products Evaluated   : {report_output['total_products_evaluated']}")
        print("-"*80)
        print("RECOMMENDATION ACTION DISTRIBUTION:")
        print(f"  - Increase Price : {report_output['summary_statistics']['increase_price_count']} products")
        print(f"  - Decrease Price : {report_output['summary_statistics']['decrease_price_count']} products")
        print(f"  - Maintain Price : {report_output['summary_statistics']['maintain_price_count']} products")
        print("-"*80)
        print(f"Average Expected Revenue Improvement : {report_output['summary_statistics']['average_expected_revenue_improvement_percent']:.2f}%")
        print("-"*80)
        print("SAMPLE PRICE RECOMMENDATIONS (Top 5 Products by Historical Revenue):")
        print(f"  {'StockCode':<10} | {'Current':<8} | {'Recommend':<9} | {'Diff':<7} | {'Action':<15} | {'Improvement':<11}")
        print(f"  {'-'*10} | {'-'*8} | {'-'*9} | {'-'*7} | {'-'*15} | {'-'*11}")
        for r in recommendations[:5]:
            print(
                f"  {r['stockcode']:<10} | "
                f"₹{r['current_price']:<7.2f} | "
                f"₹{r['recommended_price']:<8.2f} | "
                f"₹{r['price_difference']:+6.2f} | "
                f"{r['recommendation']:<15} | "
                f"{r['revenue_improvement_percentage']:+10.2f}%"
            )
        print("="*80 + "\n")
        
    except Exception as e:
        logger.error(f"Error during recommendation engine execution: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()
