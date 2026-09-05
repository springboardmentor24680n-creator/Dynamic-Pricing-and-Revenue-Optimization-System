import os
import sys
import math
import logging
from pathlib import Path
from typing import Dict, Any, List

# Ensure the backend directory is in the system path to allow absolute imports
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.append(str(BASE_DIR))

from services.pricing_service import PricingService
from services.forecast_service import ForecastService
from ml_pipeline.train_price_model import REPORTS_DIR

logger = logging.getLogger("services.recommendation_service")

class RecommendationService:
    """
    A reusable service designed to combine price predictions, demand forecasting,
    inventory parameters, and revenue metrics to output optimized pricing targets.
    """
    def __init__(
        self,
        pricing_service: PricingService = None,
        forecast_service: ForecastService = None,
        elasticity: float = -1.5
    ):
        self.pricing_service = pricing_service or PricingService()
        self.forecast_service = forecast_service or ForecastService()
        self.elasticity = elasticity
        self.prophet_trend = self._load_prophet_trend()
        
        # Load demand forecasting service
        try:
            from services.demand_forecast_service import DemandForecastService
            self.demand_forecast_service = DemandForecastService(
                pricing_service=self.pricing_service,
                forecast_service=self.forecast_service
            )
        except Exception as e:
            logger.warning(f"Failed to load DemandForecastService in RecommendationService: {e}")
            self.demand_forecast_service = None

        # Load seasonal trend service
        try:
            from services.seasonal_trend_service import SeasonalTrendService
            self.seasonal_trend_service = SeasonalTrendService()
        except Exception as e:
            logger.warning(f"Failed to load SeasonalTrendService in RecommendationService: {e}")
            self.seasonal_trend_service = None

    def _load_prophet_trend(self) -> str:
        """
        Retrieves pre-calculated demand trend states.
        """
        trend_path = REPORTS_DIR / "trend_classification.json"
        if trend_path.exists():
            try:
                import json
                with open(trend_path, "r", encoding="utf-8") as f:
                    report = json.load(f)
                    return report.get("forecast_period", {}).get("classification", "Stable")
            except Exception as e:
                logger.warning(f"Failed to read trend classification file: {e}")
        return "Stable"

    def get_demand_multiplier(self) -> float:
        if self.prophet_trend in ["Seasonal", "Increasing"]:
            return 1.03
        elif self.prophet_trend == "Decreasing":
            return 0.97
        else:
            return 1.00

    def get_recommendation(
        self,
        product_features: Dict[str, Any],
        current_price: float,
        current_inventory: float,
        historical_sales: float,
        historical_revenue: float,
        cost_price: float = None,
        competitor_price: float = None,
        db: Session = None
    ) -> Dict[str, Any]:
        """
        Evaluates candidate prices to maximize expected profit under margin, inventory, 
        seasonality, and competitor constraints.
        """
        stockcode = product_features.get("stockcode", "M")
        
        if competitor_price is None and stockcode:
            try:
                from main import CompetitorPrice
                close_db = False
                if db is None:
                    from main import SessionLocal
                    db_session = SessionLocal()
                    close_db = True
                else:
                    db_session = db
                try:
                    comp = db_session.query(CompetitorPrice).filter(
                        CompetitorPrice.product_id == stockcode
                    ).order_by(CompetitorPrice.competitor_price.asc()).first()
                    if comp:
                        competitor_price = comp.competitor_price
                except Exception as db_err:
                    logger.warning(f"Error querying competitor price in database: {db_err}")
                finally:
                    if close_db:
                        db_session.close()
            except Exception as e:
                logger.warning(f"Error querying competitor price in recommendation service: {e}")
        
        # 1. Inventory days of supply
        if stockcode:
            try:
                from main import Product, SalesRecord
                close_db = False
                if db is None:
                    from main import SessionLocal
                    db_session = SessionLocal()
                    close_db = True
                else:
                    db_session = db
                try:
                    product = db_session.query(Product).filter(Product.id == stockcode).first()
                    if product:
                        sales_records = db_session.query(SalesRecord).filter(SalesRecord.product_name == product.name).all()
                        if sales_records:
                            historical_sales = float(sum(s.units_sold for s in sales_records))
                            historical_revenue = float(sum(s.revenue for s in sales_records))
                        else:
                            historical_sales = 0.0
                            historical_revenue = 0.0
                finally:
                    if close_db:
                        db_session.close()
            except Exception as e:
                logger.warning(f"Error querying database for historical sales in recommendation service: {e}")

        # Correct calculation strictly using the historical sales source
        if historical_sales > 0:
            daily_sales_rate = historical_sales / 30.0
            days_of_supply = current_inventory / daily_sales_rate
            inv_status = "Low Inventory (Stockout Risk)" if days_of_supply < 10 else "Excess Inventory (Clearance)" if days_of_supply > 30 else "Healthy Inventory Level"
            supply_display = f"{days_of_supply:.1f} days of supply"
        else:
            daily_sales_rate = "N/A"
            days_of_supply = "Insufficient sales history"
            inv_status = "Insufficient sales history"
            supply_display = "insufficient sales history"

        # Internal decision days of supply to preserve pricing recommendation algorithm decisions
        daily_sales_fallback = max(0.01, float(product_features.get("quantity", 10.0)))
        daily_sales_rate_decision = historical_sales / 30.0 if historical_sales > 0 else daily_sales_fallback
        decision_days_of_supply = current_inventory / daily_sales_rate_decision if daily_sales_rate_decision > 0 else 30.0

        supply_log = f"{days_of_supply:.4f}" if isinstance(days_of_supply, (int, float)) else str(days_of_supply)
        velocity_log = f"{daily_sales_rate:.4f}" if isinstance(daily_sales_rate, (int, float)) else str(daily_sales_rate)
        print(f"stock: {current_inventory}")
        print(f"historical sales: {historical_sales}")
        print(f"daily sales velocity: {velocity_log}")
        print(f"days_of_supply: {supply_log}")
        
        logger.info(
            f"Days of Supply Calculation details: "
            f"Current Inventory = {current_inventory}, "
            f"Historical Sales = {historical_sales}, "
            f"Sales Period = 30 days, "
            f"Daily Sales Velocity = {velocity_log}, "
            f"Days of Supply = {supply_log}"
        )
        
        # 2. Demand multiplier based on Prophet trend
        demand_mult = self.get_demand_multiplier()
        
        # Safe denominator for division by current_price to prevent division by zero
        safe_current_price = max(0.01, current_price)
        
        # 3. Cost Price & Margins
        cost_price = cost_price if cost_price is not None else (current_price * 0.7)
        min_allowed_price = cost_price * 1.05  # strictly cost + 5% minimum margin

        # 5. Fetch actual confidence score (default to 80.0 to avoid executing full Prophet pipeline on single request)
        confidence_pct = 80.0

        # 4. Baseline demand (historical sales or integrated forecasting service)
        short_term_demand = None
        if self.demand_forecast_service:
            try:
                forecast_res = self.demand_forecast_service.get_forecast_for_product(stockcode, competitor_price=competitor_price)
                if forecast_res and forecast_res.get("short_term", {}).get("expected_demand") is not None:
                    short_term_demand = forecast_res["short_term"]["expected_demand"]
                    confidence_pct = forecast_res["short_term"]["confidence"] or confidence_pct
            except Exception as e:
                logger.warning(f"Failed to fetch short term forecast in recommendation: {e}")
        
        forecast_demand = short_term_demand if short_term_demand is not None else (historical_sales if historical_sales > 0 else 10.0)
        confidence_factor = confidence_pct / 100.0

        # Calculate dynamic competitor constraint limits if competitor_price is present
        if competitor_price is not None and competitor_price > 0:
            # Determine dynamic maximum premium over competitor
            base_max_premium = 0.05  # 5% by default
            
            # Low stock allows higher premium
            if decision_days_of_supply < 10:
                base_max_premium += 0.10
            elif decision_days_of_supply > 30:
                base_max_premium = 0.0  # No premium allowed over competitor to stimulate volume
                
            # Demand trend influence
            if self.prophet_trend in ["Increasing", "Seasonal"]:
                base_max_premium += 0.05
            elif self.prophet_trend == "Decreasing":
                base_max_premium = max(-0.05, base_max_premium - 0.08)
                
            # Final premium limit scaled by confidence
            max_premium_limit = base_max_premium * (0.3 + 0.7 * confidence_factor)
            max_competitor_bound = competitor_price * (1.0 + max_premium_limit)
        else:
            max_competitor_bound = current_price * 1.20

        # Grid search bounds:
        # Range: from min_allowed_price to max_bound
        max_bound = current_price * 1.20
        if competitor_price is not None and competitor_price > 0:
            if competitor_price > current_price:
                # If competitor is more expensive, we can increase price up to competitor or current * 1.20
                max_bound = max(max_bound, competitor_price)
            else:
                # If competitor is cheaper, limit price to competitor + allowed premium
                max_bound = min(max_bound, max_competitor_bound)
                
        # Guarantee search range includes current_price and competitor_price if valid
        max_bound = max(max_bound, min_allowed_price)
        
        step = (max_bound - min_allowed_price) / 100.0 if max_bound > min_allowed_price else 1.0
        candidates = [min_allowed_price + i * step for i in range(101)]
        
        valid_candidates = []
        for p_cand in candidates:
            # Constraint: Never recommend a price below cost + minimum margin (5%)
            if p_cand < min_allowed_price:
                continue

            # Constraint: If demand is weak, avoid unnecessarily increasing price
            if self.prophet_trend == "Decreasing" and p_cand > current_price:
                continue

            # Constraint: If inventory is high and demand is weak, consider a lower price
            if decision_days_of_supply > 30 and self.prophet_trend == "Decreasing" and p_cand > current_price * 0.99:
                continue

            # Adjust expected demand using price elasticity
            elasticity_ratio = 1.0 + (self.elasticity * (p_cand - current_price) / safe_current_price)
            elasticity_ratio = max(0.0, elasticity_ratio)
            
            # Competitor pricing sensitivity adjustment:
            competitor_mult = 1.0
            if competitor_price is not None and competitor_price > 0:
                if p_cand > competitor_price:
                    deviation = (p_cand - competitor_price) / competitor_price
                    # Calculate sensitivity factor based on inventory and trend
                    sensitivity = 4.0
                    if decision_days_of_supply < 10:
                        sensitivity -= 1.5
                    elif decision_days_of_supply > 30:
                        sensitivity += 1.0
                        
                    if self.prophet_trend in ["Increasing", "Seasonal"]:
                        sensitivity -= 1.0
                    elif self.prophet_trend == "Decreasing":
                        sensitivity += 1.5
                        
                    sensitivity = max(1.5, sensitivity)
                    competitor_mult = math.exp(-sensitivity * deviation)
                else:
                    deviation = (competitor_price - p_cand) / competitor_price
                    competitor_mult = 1.0 + 0.3 * deviation
                    competitor_mult = min(1.25, competitor_mult)

            # Combined expected demand (guarantee no negative demand)
            expected_demand = max(0.0, forecast_demand * elasticity_ratio * demand_mult * competitor_mult)
            
            # Calculate expected revenue and profit
            expected_revenue = p_cand * expected_demand
            expected_profit = (p_cand - cost_price) * expected_demand

            valid_candidates.append((p_cand, expected_demand, expected_revenue, expected_profit))

        # Fallback 1: Relax competitor/demand filter if no candidates overlap, keeping cost+margin constraint
        if not valid_candidates:
            for p_cand in candidates:
                if p_cand >= min_allowed_price:
                    elasticity_ratio = max(0.0, 1.0 + (self.elasticity * (p_cand - current_price) / safe_current_price))
                    expected_demand = max(0.0, forecast_demand * elasticity_ratio * demand_mult)
                    expected_revenue = p_cand * expected_demand
                    expected_profit = (p_cand - cost_price) * expected_demand
                    valid_candidates.append((p_cand, expected_demand, expected_revenue, expected_profit))

        # Fallback 2: Final absolute protector to prevent empty optimization list
        if not valid_candidates:
            expected_demand = max(0.0, forecast_demand)
            valid_candidates.append((current_price, expected_demand, current_price * expected_demand, (current_price - cost_price) * expected_demand))

        # 6. Optimize to maximize EXPECTED PROFIT
        best_candidate = max(valid_candidates, key=lambda x: x[3])
        recommended_price, expected_demand, expected_revenue, expected_profit = best_candidate

        # Strict competitor/inventory constraint enforcement:
        # If decision_days_of_supply > 30 and competitor price is available, do not exceed competitor price
        # (unless competitor price is below cost + margin, in which case keep at min_allowed_price)
        if decision_days_of_supply > 30 and competitor_price is not None and competitor_price > 0:
            upper_limit = max(competitor_price, min_allowed_price)
            recommended_price = min(recommended_price, upper_limit)
        else:
            recommended_price = max(recommended_price, min_allowed_price)

        # Recalculate metrics for final recommended price to guarantee mathematical consistency
        elasticity_ratio = 1.0 + (self.elasticity * (recommended_price - current_price) / safe_current_price)
        elasticity_ratio = max(0.0, elasticity_ratio)
        competitor_mult = 1.0
        if competitor_price is not None and competitor_price > 0:
            if recommended_price > competitor_price:
                deviation = (recommended_price - competitor_price) / competitor_price
                sensitivity = 4.0
                if decision_days_of_supply < 10:
                    sensitivity -= 1.5
                elif decision_days_of_supply > 30:
                    sensitivity += 1.0
                if self.prophet_trend in ["Increasing", "Seasonal"]:
                    sensitivity -= 1.0
                elif self.prophet_trend == "Decreasing":
                    sensitivity += 1.5
                sensitivity = max(1.5, sensitivity)
                competitor_mult = math.exp(-sensitivity * deviation)
            else:
                deviation = (competitor_price - recommended_price) / competitor_price
                competitor_mult = 1.0 + 0.3 * deviation
                competitor_mult = min(1.25, competitor_mult)
        
        expected_demand = max(0.0, forecast_demand * elasticity_ratio * demand_mult * competitor_mult)
        expected_revenue = recommended_price * expected_demand
        expected_profit = (recommended_price - cost_price) * expected_demand

        # Recommended action selection
        price_diff = recommended_price - current_price
        price_diff_pct = (price_diff / safe_current_price) * 100
        
        if price_diff_pct > 2.0:
            action = "Increase Price"
        elif price_diff_pct < -2.0:
            action = "Decrease Price"
        else:
            action = "Maintain Price"
            
        rev_gain = expected_revenue - historical_revenue
        rev_gain_pct = (rev_gain / (historical_revenue + 1e-5)) * 100
        
        # Compile dynamic specific reason explanation
        primary_reason = ""
        explanation = ""
        
        if competitor_price is not None and competitor_price > 0:
            is_margin_protect = abs(recommended_price - min_allowed_price) < 50.0
            is_capped_by_competitor = competitor_price < current_price and abs(recommended_price - max_competitor_bound) < 100.0
            
            if is_margin_protect:
                primary_reason = "margin protection due to cost limits"
                explanation = (
                    f"With inventory levels showing {supply_display} (excess stock) and competitor price at "
                    f"₹{competitor_price:.2f} creating strong price pressure, the price is set to the minimum margin constraint of "
                    f"₹{recommended_price:.2f} to protect profitability."
                )
            elif is_capped_by_competitor:
                primary_reason = "competitor price pressure"
                explanation = (
                    f"The recommended price is set to ₹{recommended_price:.2f} due to competitor price pressure from the cheaper "
                    f"competitor's price of ₹{competitor_price:.2f}. Charging a higher premium would severely reduce expected demand "
                    f"due to price elasticity and high inventory ({supply_display})."
                )
            elif decision_days_of_supply > 30 and price_diff_pct < -2.0:
                primary_reason = "excess inventory clearance"
                explanation = (
                    f"With inventory levels showing {supply_display} (excess stock) and competitor price at "
                    f"₹{competitor_price:.2f}, the price is reduced to ₹{recommended_price:.2f} to stimulate expected demand and "
                    f"accelerate inventory clearance while protecting margins."
                )
            elif decision_days_of_supply < 10 and price_diff_pct > 2.0:
                primary_reason = "low inventory capture premium"
                explanation = (
                    f"Due to low stock levels ({supply_display}) and strong {self.prophet_trend} demand, the "
                    f"price is increased to ₹{recommended_price:.2f} to capture a premium and maximize expected profit."
                )
            else:
                primary_reason = "competitor market alignment"
                explanation = (
                    f"Price is optimized to ₹{recommended_price:.2f} based on competitor alignment with the market price of "
                    f"₹{competitor_price:.2f}, expected demand of {expected_demand:.1f} units, and inventory levels showing "
                    f"{supply_display}."
                )
        else:
            if price_diff_pct > 2.0:
                primary_reason = "maximize expected profit"
                explanation = (
                    f"Price is increased to ₹{recommended_price:.2f} to maximize expected profit under strong {self.prophet_trend} "
                    f"demand and inventory levels showing {supply_display}."
                )
            elif price_diff_pct < -2.0:
                primary_reason = "stimulate quantity sales"
                explanation = (
                    f"Price is decreased to ₹{recommended_price:.2f} to stimulate expected demand and clear excess stock "
                    f"({supply_display})."
                )
            else:
                primary_reason = "maintain stable margins"
                explanation = (
                    f"Price is maintained at ₹{recommended_price:.2f} to maintain optimal margins under stable demand "
                    f"and healthy inventory levels ({supply_display})."
                )

        # Get seasonal trends
        seasonality_val = "Moderate"
        peak_period = "N/A"
        low_period = "N/A"
        seasonal_insights = []
        if self.seasonal_trend_service:
            try:
                seasonal_data = self.seasonal_trend_service.get_seasonal_trends(stockcode)
                seasonality_val = seasonal_data.get("seasonality", "Moderate")
                peak_period = seasonal_data.get("peak_period", "N/A")
                low_period = seasonal_data.get("low_period", "N/A")
                seasonal_insights = seasonal_data.get("insights", [])
            except Exception as e:
                logger.warning(f"Failed to load seasonal data in recommendation: {e}")

        comp_display = f"₹{competitor_price:.2f}" if competitor_price is not None else "N/A"
        reason_paragraph = f"For SKU {stockcode}, stock levels show {supply_display} ({inv_status}), cost price is ₹{cost_price:.2f} (with cost constraints applied), competitor price is {comp_display} if available, demand forecast indicates {self.prophet_trend} patterns. We recommend action: {action} ({price_diff_pct:+.1f}%) to ₹{recommended_price:.2f}. Reason: {primary_reason}."

        final_days_of_supply = round(days_of_supply, 1) if isinstance(days_of_supply, (int, float)) else days_of_supply
        final_daily_sales_velocity = round(float(daily_sales_rate), 4) if isinstance(daily_sales_rate, (int, float)) else daily_sales_rate

        return {
            "recommended_price": round(recommended_price, 2),
            "expected_revenue": round(expected_revenue, 2),
            "expected_demand": round(expected_demand, 2),
            "expected_profit": round(expected_profit, 2),
            "current_price": round(current_price, 2),
            "competitor_price": round(competitor_price, 2) if competitor_price is not None else None,
            "cost_price": round(cost_price, 2),
            "elasticity": self.elasticity,
            "demand_trend": self.prophet_trend,
            "seasonality": seasonality_val,
            "peak_period": peak_period,
            "low_period": low_period,
            "seasonal_insights": seasonal_insights,
            "recommendation": action,
            "reason": reason_paragraph,
            "model_signals": f"Inventory: {supply_display}, Cost limit: ₹{min_allowed_price:.2f}, Competitor: ₹{competitor_price if competitor_price else 0.0:.2f}",
            "confidence": confidence_pct,
            "current_inventory": int(current_inventory),
            "historical_sales": float(historical_sales),
            "daily_sales_velocity": final_daily_sales_velocity,
            "days_of_supply": final_days_of_supply,
            "sales_period_days": 30,
            "metrics": {
                "price_difference": round(price_diff, 2),
                "price_difference_percentage": round(price_diff_pct, 2),
                "revenue_gain": round(rev_gain, 2),
                "revenue_growth_percentage": round(rev_gain_pct, 2),
                "days_of_supply": final_days_of_supply
            },
            "pricing_analysis_report": {
                "current_price": round(current_price, 2),
                "recommended_price": round(recommended_price, 2),
                "price_change_percentage": round(price_diff_pct, 2),
                "competitor_price": round(competitor_price, 2) if competitor_price is not None else None,
                "cost_price": round(cost_price, 2),
                "minimum_allowed_price": round(min_allowed_price, 2),
                "expected_demand": round(expected_demand, 2),
                "expected_revenue": round(expected_revenue, 2),
                "expected_profit": round(expected_profit, 2),
                "current_stock": int(current_inventory),
                "current_inventory": int(current_inventory),
                "days_of_supply": final_days_of_supply,
                "price_elasticity": self.elasticity,
                "demand_trend": self.prophet_trend,
                "seasonality": "Strong" if self.prophet_trend in ["Seasonal", "Increasing"] else "Stable" if self.prophet_trend == "Stable" else "Decreasing",
                "forecast_confidence": confidence_pct,
                "model_used": "Prophet (Demand) + Expected Profit Maximization Engine",
                "summary": explanation,
                "historical_sales": float(historical_sales),
                "daily_sales_velocity": final_daily_sales_velocity,
                "forecast_demand": round(expected_demand, 2),
                "forecast_period": "90-day horizon",
                "sales_period_days": 30
            }
        }

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("Testing RecommendationService...")
    try:
        service = RecommendationService()
        test_features = {
            "quantity": 10.0,
            "revenue": 50.0,
            "year": 2018,
            "month": 3,
            "week": 10,
            "day": 5,
            "day_of_week": 1,
            "quarter": 1,
            "quantity_lag_1": 12.0,
            "quantity_lag_7": 8.0,
            "quantity_rolling_mean_7": 9.5,
            "quantity_rolling_mean_14": 10.2,
            "stockcode": "22423",
            "country": "United Kingdom"
        }
        res = service.get_recommendation(
            product_features=test_features,
            current_price=24.96,
            current_inventory=150.0,
            historical_sales=2600.0,
            historical_revenue=64896.0
        )
        print("Recommendation Calculation Success!")
        print(f"  Recommended Price: ${res['recommended_price']}")
        print(f"  Recommendation   : {res['recommendation']}")
        print(f"  Expected Demand  : {res['expected_demand']} units")
        print(f"  Expected Revenue : ${res['expected_revenue']}")
        print(f"  Confidence       : {res['confidence']}%")
        print(f"  Reason           : {res['reason']}")
    except Exception as e:
        print(f"Recommendation Calculation Failed: {e}")
