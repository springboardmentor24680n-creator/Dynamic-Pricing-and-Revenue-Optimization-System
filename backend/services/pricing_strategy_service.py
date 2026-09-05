import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session

from services.pricing_comparison_service import PricingComparisonService
from services.demand_forecast_service import DemandForecastService
from services.seasonal_trend_service import SeasonalTrendService
from services.recommendation_service import RecommendationService

logger = logging.getLogger("services.pricing_strategy_service")

class PricingStrategyService:
    def __init__(self):
        self.comparison_service = PricingComparisonService()
        self.demand_service = DemandForecastService()
        self.seasonal_service = SeasonalTrendService()
        self.rec_service = RecommendationService()

    def get_pricing_strategy(self, db: Session, product_id: str) -> Dict[str, Any]:
        """
        Calculates and returns a comprehensive pricing strategy recommendation for a product.
        """
        from main import Product, SalesRecord, CompetitorPrice
        
        # 1. Fetch Product
        product = db.query(Product).filter(Product.id == product_id).first()
        if not product:
            raise ValueError(f"Product with ID '{product_id}' not found.")

        current_price = product.current_price or 0.0
        cost_price = product.cost_price or 0.0
        stock = product.stock or 0

        # 2. Fetch Sales Records
        sales_records = db.query(SalesRecord).filter(SalesRecord.product_name == product.name).all()
        historical_sales = sum(s.units_sold for s in sales_records) if sales_records else 0.0
        historical_revenue = sum(s.revenue for s in sales_records) if sales_records else 0.0

        # 3. Query Competitor Prices & Pricing Comparison
        competitor_metrics = {
            "lowest_competitor_price": None,
            "highest_competitor_price": None,
            "average_competitor_price": None,
            "median_competitor_price": None,
            "price_gap": None,
            "price_gap_percent": None,
            "competitive_pressure": None,
            "market_position": "no_competitors",
            "competitor_count": 0,
            "available": False
        }
        
        comp_price = None
        try:
            comp_stats = self.comparison_service.calculate_pricing_comparison(db, product_id)
            if comp_stats and comp_stats.get("competitor_count", 0) > 0:
                competitor_metrics.update({
                    "lowest_competitor_price": comp_stats.get("lowest_competitor_price"),
                    "highest_competitor_price": comp_stats.get("highest_competitor_price"),
                    "average_competitor_price": comp_stats.get("average_competitor_price"),
                    "median_competitor_price": comp_stats.get("median_competitor_price"),
                    "price_gap": comp_stats.get("price_gap_absolute"),
                    "price_gap_percent": comp_stats.get("price_gap_percent"),
                    "competitive_pressure": comp_stats.get("competitive_pressure"),
                    "market_position": comp_stats.get("market_position"),
                    "competitor_count": comp_stats.get("competitor_count"),
                    "available": True
                })
                comp_price = comp_stats.get("lowest_competitor_price")
        except Exception as e:
            logger.warning(f"Failed to fetch pricing comparison for strategy: {e}")

        # 4. Query Demand Forecast
        demand_metrics = {
            "forecast_direction": "Stable",
            "demand_trend": "Stable",
            "expected_demand": None,
            "confidence": None,
            "available": False
        }
        
        short_term_forecast = None
        confidence_pct = 80.0
        try:
            fc = self.demand_service.get_forecast_for_product(product_id, competitor_price=comp_price, db=db)
            if fc and fc.get("short_term") and fc["short_term"].get("expected_demand") is not None:
                st = fc["short_term"]
                demand_metrics.update({
                    "forecast_direction": st.get("trend", "Stable"),
                    "demand_trend": st.get("trend", "Stable"),
                    "expected_demand": st.get("expected_demand"),
                    "confidence": st.get("confidence", 80.0),
                    "available": True
                })
                short_term_forecast = st.get("expected_demand")
                confidence_pct = st.get("confidence") or 80.0
        except Exception as e:
            logger.warning(f"Failed to fetch demand forecast for strategy: {e}")

        # 5. Query Seasonal trends
        seasonal_metrics = {
            "seasonality": "Stable",
            "peak_period": "N/A",
            "low_period": "N/A",
            "seasonal_status": "Stable",
            "available": False
        }
        try:
            seasonal_data = self.seasonal_service.get_seasonal_trends(product_id, db=db, preloaded_sales=sales_records)
            if seasonal_data and "Insufficient" not in seasonal_data.get("seasonality", ""):
                seasonal_metrics.update({
                    "seasonality": seasonal_data.get("seasonality"),
                    "peak_period": seasonal_data.get("peak_period"),
                    "low_period": seasonal_data.get("low_period"),
                    "seasonal_status": "Peak Period" if seasonal_data.get("seasonality") in ["Strong", "Moderate"] and datetime.now().strftime("%B") == seasonal_data.get("peak_period") else "Normal",
                    "available": True
                })
        except Exception as e:
            logger.warning(f"Failed to fetch seasonal trends for strategy: {e}")

        # 6. Inventory details
        inventory_metrics = {
            "current_stock": stock,
            "days_of_supply": None,
            "daily_sales_velocity": None,
            "status": "Insufficient sales history",
            "available": False
        }
        
        # Calculate days of supply
        days_of_supply = None
        daily_sales_rate = 0.0
        if historical_sales > 0:
            daily_sales_rate = historical_sales / 30.0
            days_of_supply = stock / daily_sales_rate
            inv_status = "Low Inventory (Stockout Risk)" if days_of_supply < 10 else "Excess Inventory (Clearance)" if days_of_supply > 30 else "Healthy Inventory Level"
            inventory_metrics.update({
                "days_of_supply": round(days_of_supply, 1),
                "daily_sales_velocity": round(daily_sales_rate, 4),
                "status": inv_status,
                "available": True
            })
        else:
            inventory_metrics.update({
                "days_of_supply": "Insufficient sales history",
                "daily_sales_velocity": "N/A",
                "status": "Insufficient sales history",
                "available": False
            })

        # 7. Profitability metrics
        gross_margin = current_price - cost_price
        gross_margin_percent = (gross_margin / current_price * 100) if current_price > 0 else 0.0
        profitability_metrics = {
            "cost_price": cost_price,
            "gross_margin": round(gross_margin, 2),
            "gross_margin_percent": round(gross_margin_percent, 2),
            "available": cost_price > 0
        }

        # 8. Call Recommendation Service for optimized recommended price and impact
        rec_price = current_price
        expected_demand = short_term_forecast if short_term_forecast is not None else (historical_sales if historical_sales > 0 else 10.0)
        expected_revenue = current_price * expected_demand
        expected_profit = (current_price - cost_price) * expected_demand
        rec_available = False

        try:
            # We construct a product features dict similar to RecommendationService requirements
            features = self.rec_service.pricing_service.get_features_for_product(product_id)
            if not features:
                features = {"stockcode": product_id, "quantity": 10.0}
            else:
                features["stockcode"] = product_id

            rec_res = self.rec_service.get_recommendation(
                product_features=features,
                current_price=current_price,
                current_inventory=stock,
                historical_sales=historical_sales,
                historical_revenue=historical_revenue,
                cost_price=cost_price,
                competitor_price=comp_price,
                db=db
            )
            if rec_res:
                rec_price = rec_res.get("recommended_price") or current_price
                expected_demand = rec_res.get("expected_demand") or expected_demand
                expected_revenue = rec_res.get("expected_revenue") or expected_revenue
                expected_profit = rec_res.get("expected_profit") or expected_profit
                rec_available = True
        except Exception as e:
            logger.warning(f"Failed to generate base recommendation for strategy: {e}")

        # Price Difference
        price_change = rec_price - current_price
        price_change_percent = (price_change / current_price * 100) if current_price > 0 else 0.0

        # Compile expected impact
        expected_margin_percent = ((rec_price - cost_price) / rec_price * 100) if rec_price > 0 else 0.0
        expected_impact = {
            "current_price": current_price,
            "recommended_price": rec_price,
            "price_change_percent": round(price_change_percent, 2),
            "expected_revenue": round(expected_revenue, 2) if rec_available else "Insufficient data",
            "expected_profit": round(expected_profit, 2) if rec_available and cost_price > 0 else "Insufficient data",
            "expected_margin": round(expected_margin_percent, 2) if cost_price > 0 else "Insufficient data",
            "expected_units_sold": round(expected_demand, 1) if rec_available else "Insufficient data",
            "available": rec_available
        }

        # 9. Evaluate Pricing Strategy Rules (Scoring/Selection System)
        strategy = "HOLD PRICE"
        reasons = []
        risk_level = "MEDIUM"
        monitoring_priority = "MEDIUM"
        review_period_days = 14

        # Check conditions
        is_high_inventory = days_of_supply is not None and days_of_supply > 30
        is_low_inventory = days_of_supply is not None and days_of_supply < 10
        is_increasing_demand = demand_metrics["forecast_direction"] == "Increasing" or demand_metrics["demand_trend"] in ["Increasing", "Seasonal"]
        is_decreasing_demand = demand_metrics["forecast_direction"] == "Decreasing" or demand_metrics["demand_trend"] == "Decreasing"
        
        comp_avg = competitor_metrics["average_competitor_price"]
        comp_lowest = competitor_metrics["lowest_competitor_price"]
        comp_pressure = competitor_metrics["competitive_pressure"] or 0.0

        # Evaluate rules in priority order
        if is_high_inventory and (is_decreasing_demand or demand_metrics["forecast_direction"] == "Stable"):
            strategy = "CLEARANCE / INVENTORY REDUCTION"
            reasons.append(f"Current stock of {stock} units represents {inventory_metrics['days_of_supply']} days of supply, exceeding the healthy threshold.")
            reasons.append("Demand forecast indicates stable or decreasing sales momentum, necessitating price clearance to unlock capital.")
            risk_level = "LOW"
            monitoring_priority = "MEDIUM"
            review_period_days = 7
        elif seasonal_metrics["available"] and seasonal_metrics["seasonality"] in ["Strong", "Moderate"] and seasonal_metrics["seasonal_status"] == "Peak Period":
            strategy = "SEASONAL PRICING"
            reasons.append(f"Product has {seasonal_metrics['seasonality'].lower()} seasonality with peak demand typically observed in {seasonal_metrics['peak_period']}.")
            reasons.append("Current pricing cycle aligns with the historical high-volume demand peak, supporting optimization.")
            risk_level = "LOW"
            monitoring_priority = "MEDIUM"
            review_period_days = 10
        elif is_low_inventory and competitor_metrics["available"] and (comp_lowest is not None and current_price < comp_lowest):
            strategy = "PREMIUM PRICING"
            reasons.append(f"Extremely low inventory of {stock} units ({inventory_metrics['days_of_supply']} days) presents a stockout risk.")
            reasons.append(f"Our price is below the lowest competitor price (₹{comp_lowest:.2f}), allowing us to capture a premium.")
            risk_level = "MEDIUM"
            monitoring_priority = "HIGH"
            review_period_days = 7
        elif competitor_metrics["available"] and comp_pressure > 50.0 and gross_margin_percent > 15.0:
            strategy = "AGGRESSIVE COMPETITIVE PRICING"
            reasons.append(f"High competitive pressure detected: {comp_pressure:.1f}% of monitored competitors are cheaper.")
            reasons.append(f"Our healthy gross margin of {gross_margin_percent:.1f}% allows room for matching competitor positions.")
            risk_level = "HIGH"
            monitoring_priority = "HIGH"
            review_period_days = 5
        elif is_increasing_demand and not is_low_inventory:
            strategy = "DEMAND-BASED PRICING"
            reasons.append("Demand forecasting models predict rising sales trends for this product category.")
            reasons.append("Stable inventory levels support captures of increased buyer willingness-to-pay.")
            risk_level = "MEDIUM"
            monitoring_priority = "MEDIUM"
            review_period_days = 14
        elif price_change_percent > 2.0:
            strategy = "INCREASE PRICE"
            reasons.append(f"Recommendation engine identifies potential for a {price_change_percent:+.1f}% price increase.")
            reasons.append("Margins are enhanced while maintaining expected demand and competitive alignment.")
            risk_level = "MEDIUM"
            monitoring_priority = "LOW"
            review_period_days = 14
        elif price_change_percent < -2.0:
            strategy = "DECREASE PRICE"
            reasons.append(f"Recommendation engine suggests a {price_change_percent:.1f}% price reduction.")
            reasons.append("Lower prices will stimulate expected volume sales to optimize total gross margin.")
            risk_level = "MEDIUM"
            monitoring_priority = "LOW"
            review_period_days = 14
        else:
            strategy = "HOLD PRICE"
            reasons.append("Pricing signals are stable. Current price aligns with competitor averages and demand forecasts.")
            reasons.append("No immediate inventory pressure or margin deviations are detected.")
            risk_level = "LOW"
            monitoring_priority = "LOW"
            review_period_days = 30

        # Format details into reasons list
        if competitor_metrics["available"] and comp_avg:
            diff_pct = ((current_price - comp_avg) / comp_avg * 100)
            reasons.append(f"Competitor prices are {abs(diff_pct):.1f}% {'above' if diff_pct < 0 else 'below'} our current price.")
            reasons.append(f"Current competitive pressure is {comp_pressure:.1f}%.")
        elif not competitor_metrics["available"]:
            reasons.append("Competitor data is unavailable.")
            
        if demand_metrics["available"]:
            reasons.append(f"Demand forecast indicates {demand_metrics['forecast_direction'].lower()} demand direction.")
        else:
            reasons.append("Demand forecast is unavailable.")

        if inventory_metrics["available"]:
            reasons.append(f"Current inventory represents {inventory_metrics['days_of_supply']} days of supply.")
        else:
            reasons.append("Inventory data is unavailable.")

        if profitability_metrics["available"]:
            reasons.append(f"Current gross margin is {gross_margin_percent:.1f}%.")
        else:
            reasons.append("Profitability metrics are unavailable.")

        # Create recommended action text
        if strategy == "HOLD PRICE":
            recommended_action = "Maintain the current product price and review after the next pricing cycle."
        elif strategy == "INCREASE PRICE":
            recommended_action = f"Increase the product price by approximately {price_change_percent:.1f}% (₹{price_change:+.2f}) and monitor competitor movement over the next pricing cycle."
        elif strategy == "DECREASE PRICE":
            recommended_action = f"Decrease the product price by approximately {abs(price_change_percent):.1f}% (₹{abs(price_change):.2f}) to stimulate sales velocity."
        elif strategy == "PREMIUM PRICING":
            recommended_action = f"Leverage low inventory status to raise the price towards ₹{rec_price:.2f} (a {price_change_percent:+.1f}% increase) and capture high-intent demand."
        elif strategy == "AGGRESSIVE COMPETITIVE PRICING":
            recommended_action = f"Reduce the price to ₹{rec_price:.2f} to match or beat aggressive competitor positions while protecting a minimum 15% margin."
        elif strategy == "CLEARANCE / INVENTORY REDUCTION":
            recommended_action = f"Mark down the price by {abs(price_change_percent):.1f}% to stimulate sales and clear the excess stock quickly."
        elif strategy == "DEMAND-BASED PRICING":
            recommended_action = f"Adjust the price upward dynamically to ₹{rec_price:.2f} to capitalize on the increasing market demand."
        elif strategy == "SEASONAL PRICING":
            recommended_action = f"Align pricing with peak seasonal demand at ₹{rec_price:.2f} and schedule a post-season review in {review_period_days} days."
        else:
            recommended_action = "Review recommended after next pricing cycle."

        return {
            "product_id": product_id,
            "product_name": product.name,
            "strategy": strategy,
            "current_price": round(current_price, 2),
            "recommended_price": round(rec_price, 2),
            "price_change": round(price_change, 2),
            "price_change_percent": round(price_change_percent, 2),
            "confidence": confidence_pct,
            "risk_level": risk_level,
            "market_position": competitor_metrics["market_position"],
            "competitor_metrics": competitor_metrics,
            "demand_metrics": demand_metrics,
            "inventory_metrics": inventory_metrics,
            "profitability_metrics": profitability_metrics,
            "expected_impact": expected_impact,
            "reasons": reasons,
            "recommended_action": recommended_action,
            "monitoring_priority": monitoring_priority,
            "review_period_days": review_period_days
        }
