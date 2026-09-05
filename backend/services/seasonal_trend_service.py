import os
import sys
import logging
import json
import math
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List

import pandas as pd
import numpy as np

# Ensure the backend directory is in the system path to allow absolute imports
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.append(str(BASE_DIR))

from ml_pipeline.train_price_model import REPORTS_DIR

logger = logging.getLogger("services.seasonal_trend_service")

# Map of database catalog product IDs to active stockcodes in the historical transaction dataset
PRODUCT_MAPPING = {
    "elec_headphones": "85123A",
    "elec_smartwatch": "85099B",
    "elec_speaker": "22423",
    "elec_mouse": "23843",
    "elec_keyboard": "47566",
    "elec_monitor": "84879",
    "elec_laptop": "22086",
    "elec_smartphone": "23166",
    "elec_tablet": "79321",
    "elec_webcam": "22197",
    "elec_ssd": "22386",
    "elec_charger": "84347",
    "elec_lamp": "POST",
    "elec_band": "DOT",
    "elec_earbuds": "M"
}

class SeasonalTrendService:
    """
    A service that performs product-specific seasonal demand, pricing, and inventory analysis
    for individual products using the project's historical transaction splits.
    """
    _product_monthly_cache = None
    _trend_classification = None

    def __init__(self):
        self.csv_path = BASE_DIR / "datasets" / "training" / "lightgbm_price_train.csv"
        self.seasonal_indices = {
            1: 0.82, 2: 0.85, 3: 0.91, 4: 0.96, 5: 1.02, 6: 1.14,
            7: 1.21, 8: 1.16, 9: 1.01, 10: 1.04, 11: 1.08, 12: 1.25
        }
        
        if SeasonalTrendService._product_monthly_cache is None:
            self.product_monthly_cache = {}
            self._pre_aggregate_sales_data()
            SeasonalTrendService._product_monthly_cache = self.product_monthly_cache
        else:
            self.product_monthly_cache = SeasonalTrendService._product_monthly_cache

        if SeasonalTrendService._trend_classification is None:
            self.trend_classification = self._load_trend_classification()
            SeasonalTrendService._trend_classification = self.trend_classification
        else:
            self.trend_classification = SeasonalTrendService._trend_classification

    def _pre_aggregate_sales_data(self):
        """
        Loads only the necessary columns from the large transaction CSV file and aggregates
        quantities by stockcode and month into a memory lookup table.
        """
        if not self.csv_path.exists():
            logger.warning(f"Historical sales dataset not found at {self.csv_path}. Caching skipped.")
            return

        try:
            logger.info(f"Pre-aggregating product-specific monthly sales from {self.csv_path}...")
            # Load only required columns to minimize memory footprint and load time
            df = pd.read_csv(self.csv_path, usecols=["stockcode", "month", "quantity"])
            df["stockcode"] = df["stockcode"].astype(str).str.strip()
            
            # Aggregate total quantity sold per stockcode per month
            grouped = df.groupby(["stockcode", "month"])["quantity"].sum().reset_index()
            
            # Build memory structure: {stockcode: {month: total_quantity}}
            cache = {}
            for _, row in grouped.iterrows():
                code = str(row["stockcode"])
                month = int(row["month"])
                qty = float(row["quantity"])
                
                if code not in cache:
                    cache[code] = {}
                cache[code][month] = qty
                
            self.product_monthly_cache = cache
            logger.info(f"Successfully aggregated and cached sales data for {len(cache)} unique stockcodes.")
        except Exception as e:
            logger.error(f"Error during dataset pre-aggregation: {e}")

    def _load_trend_classification(self) -> str:
        """
        Loads the overall portfolio trend classification from the Prophet report.
        """
        trend_path = REPORTS_DIR / "trend_classification.json"
        if trend_path.exists():
            try:
                with open(trend_path, "r", encoding="utf-8") as f:
                    trend_report = json.load(f)
                    return trend_report.get("forecast_period", {}).get("classification", "Stable")
            except Exception as e:
                logger.warning(f"Failed to read trend classification report: {e}")
        return "Stable"

    def get_seasonal_trends(self, product_id: str, db: Session = None, preloaded_sales: List = None) -> Dict[str, Any]:
        """
        Returns product-specific seasonal demand patterns, index curves, and actionable recommendations.
        """
        from main import SessionLocal, Product, SalesRecord
        
        close_db = False
        if db is None:
            db = SessionLocal()
            close_db = True
            
        try:
            product = db.query(Product).filter(Product.id == product_id).first()
            if not product:
                raise ValueError(f"Product {product_id} not found in database.")

            # Get historical sales records for baseline demand
            if preloaded_sales is not None:
                sales_records = preloaded_sales
            else:
                sales_records = db.query(SalesRecord).filter(SalesRecord.product_name == product.name).all()
            hist_sales = sum(r.units_sold for r in sales_records) if sales_records else 0.0
            
            month_names = {
                1: "January", 2: "February", 3: "March", 4: "April", 5: "May", 6: "June",
                7: "July", 8: "August", 9: "September", 10: "October", 11: "November", 12: "December"
            }

            # Map the product ID to the dataset stockcode
            stockcode = PRODUCT_MAPPING.get(product_id)
            prod_sales_history = self.product_monthly_cache.get(stockcode) if stockcode else None

            # Helper for clean insufficient data output schema
            def make_insufficient_data_response(message: str) -> Dict[str, Any]:
                return {
                    "product_id": product.id,
                    "product_name": product.name,
                    "trend": "Insufficient product-level historical data",
                    "seasonality": "Insufficient product-level historical data",
                    "peak_period": "Insufficient product-level historical data",
                    "low_period": "Insufficient product-level historical data",
                    "peak_demand": None,
                    "low_demand": None,
                    "average_demand": None,
                    "revenue_trend": "Insufficient product-level historical data",
                    "price_demand_relationship": message,
                    "inventory_status": message,
                    "seasonal_breakdown": [],
                    "insights": [message],
                    "recommendations": ["Establish longer product-level transaction logs to activate seasonal trend analysis."]
                }

            # Safe handle for zero database baseline sales
            if hist_sales <= 0:
                return make_insufficient_data_response("Insufficient sales history recorded in the database.")

            # Check if we have transaction records in our CSV cache for this stockcode
            if not prod_sales_history or len(prod_sales_history) < 3:
                return make_insufficient_data_response("Insufficient product-level historical data")

            # 1. Calculate product's own monthly average sales
            monthly_quantities = []
            for m in range(1, 13):
                qty = prod_sales_history.get(m, 0.0)
                monthly_quantities.append(qty)

            overall_avg = sum(monthly_quantities) / 12.0
            
            # Additional safety check for flat or empty historical volumes
            if overall_avg <= 0:
                return make_insufficient_data_response("Insufficient product-level historical data")

            # 2. Compute product's own monthly seasonal indices (centered around 1.0)
            indices = {m: (prod_sales_history.get(m, 0.0) / overall_avg) for m in range(1, 13)}

            # 3. Determine product's own peak and low periods
            peak_month_idx = max(indices, key=indices.get)
            low_month_idx = min(indices, key=indices.get)
            
            peak_period = month_names[peak_month_idx]
            low_period = month_names[low_month_idx]

            # 4. Calculate seasonality strength based on standard deviation of product's own indices
            indices_list = list(indices.values())
            std_deviation = np.std(indices_list)
            if std_deviation > 0.3:
                seasonality_strength = "Strong"
            elif std_deviation > 0.1:
                seasonality_strength = "Moderate"
            else:
                seasonality_strength = "Weak"

            # Expected peak and low quantities scaled to the product's actual 30-day baseline
            peak_demand = round(hist_sales * indices[peak_month_idx], 2)
            low_demand = round(hist_sales * indices[low_month_idx], 2)

            # 5. Build seasonal breakdown
            seasonal_breakdown = []
            stock_level = product.stock if product.stock is not None else 0
            current_price = product.current_price if product.current_price is not None else 0.0

            peak_stockout_risk = False
            for m in range(1, 13):
                m_index = indices[m]
                m_demand = round(hist_sales * m_index, 2)
                m_revenue = round(m_demand * current_price, 2)
                
                # Demand Status
                if m_index > 1.15:
                    m_demand_status = "High Demand"
                elif m_index < 0.85:
                    m_demand_status = "Low Demand"
                else:
                    m_demand_status = "Stable"

                # Inventory status during this month
                if stock_level < m_demand:
                    m_inv_status = "Risk of Stockout"
                    if m == peak_month_idx:
                        peak_stockout_risk = True
                elif stock_level > m_demand * 2.5:
                    m_inv_status = "Excess Inventory"
                elif stock_level < m_demand * 1.3:
                    m_inv_status = "Monitor"
                else:
                    m_inv_status = "Healthy"

                seasonal_breakdown.append({
                    "month_index": m,
                    "period": month_names[m],
                    "average_demand": m_demand,
                    "revenue": m_revenue,
                    "average_price": current_price,
                    "inventory": stock_level,
                    "demand_status": m_demand_status,
                    "inventory_status": m_inv_status
                })

            # Calculate overall inventory status summary
            if peak_stockout_risk:
                inventory_status_summary = "Risk of Stockout"
            elif stock_level < hist_sales * 0.7:
                inventory_status_summary = "Monitor"
            elif stock_level > hist_sales * 2.5:
                inventory_status_summary = "Excess Inventory"
            else:
                inventory_status_summary = "Healthy"

            # Price vs demand relationship description
            price_demand_desc = (
                f"Product-specific analysis for {product.name} indicates a '{seasonality_strength}' seasonality curve. "
                f"During peak periods like {peak_period}, demand rises to {peak_demand:.1f} units, representing a "
                f"{(indices[peak_month_idx]*100 - 100):+.1f}% volume shift. Adjusting margins during these peaks maximizes yield."
            )

            # Insights & Recommendations
            insights = [
                f"Demand peaks during {peak_period} with a projected product expectation of {peak_demand:.1f} units.",
                f"Lowest demand is expected in {low_period} (projected: {low_demand:.1f} units), marking the off-peak phase.",
                f"This product features a '{seasonality_strength}' seasonality profile.",
                f"Current stock of {stock_level} units translates to a '{inventory_status_summary}' rating relative to seasonal requirements."
            ]

            safety_stock_recommend = math.ceil(peak_demand * 1.3)
            recommendations = [
                f"Pre-allocate safety stock to at least {safety_stock_recommend} units before the {peak_period} peak period.",
                f"Launch off-peak pricing promotions or bundles in {low_period} (estimated demand: {low_demand:.1f} units) to spur volume.",
                f"Protect margin ceilings in {peak_period} to capitalize on organic seasonal traffic.",
                "Optimize warehouse space to match product-specific monthly demand trends rather than portfolio averages."
            ]

            return {
                "product_id": product.id,
                "product_name": product.name,
                "trend": self.trend_classification,
                "seasonality": seasonality_strength,
                "peak_period": peak_period,
                "low_period": low_period,
                "peak_demand": peak_demand,
                "low_demand": low_demand,
                "average_demand": round(hist_sales, 2),
                "revenue_trend": self.trend_classification,
                "price_demand_relationship": price_demand_desc,
                "inventory_status": inventory_status_summary,
                "seasonal_breakdown": seasonal_breakdown,
                "insights": insights,
                "recommendations": recommendations
            }

        finally:
            if close_db:
                db.close()
