import math
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session

from services.demand_forecast_service import DemandForecastService
from services.seasonal_trend_service import SeasonalTrendService

logger = logging.getLogger("services.market_intelligence_service")

class MarketIntelligenceService:
    def __init__(self):
        self.demand_service = DemandForecastService()
        self.seasonal_service = SeasonalTrendService()

    def calculate_product_intelligence(
        self,
        db: Session,
        product_id: str,
        preloaded_competitors: List[Any] = None,
        preloaded_history: List[Any] = None,
        preloaded_sales: List[Any] = None
    ) -> Dict[str, Any]:
        """
        Synthesizes pricing, competitor metrics, forecasting, seasonality,
        and inventory metrics for a product.
        """
        from main import Product, CompetitorPrice, CompetitorPriceHistory, SalesRecord
        
        product = db.query(Product).filter(Product.id == product_id).first()
        if not product:
            raise ValueError(f"Product {product_id} not found")

        our_price = product.current_price or 0.0
        current_stock = product.stock or 0

        # 1. Fetch active competitor prices
        if preloaded_competitors is not None:
            competitors = preloaded_competitors
        else:
            competitors = db.query(CompetitorPrice).filter(
                CompetitorPrice.product_id == product_id,
                CompetitorPrice.competitor_price.isnot(None)
            ).all()
        
        prices = [c.competitor_price for c in competitors]
        competitor_count = len(prices)

        # Market metrics defaults
        market_average = 0.0
        market_median = 0.0
        market_min = 0.0
        market_max = 0.0
        cheaper_percentage = 0.0
        volatility = 0.0

        if competitor_count > 0:
            market_min = min(prices)
            market_max = max(prices)
            market_average = sum(prices) / competitor_count
            
            sorted_prices = sorted(prices)
            if competitor_count % 2 == 1:
                market_median = sorted_prices[competitor_count // 2]
            else:
                market_median = (sorted_prices[competitor_count // 2 - 1] + sorted_prices[competitor_count // 2]) / 2.0

            cheaper_count = sum(1 for p in prices if p < our_price)
            cheaper_percentage = (cheaper_count / competitor_count) * 100

            # Volatility (Std Dev)
            if competitor_count > 1:
                variance = sum((p - market_average) ** 2 for p in prices) / (competitor_count - 1)
                volatility = math.sqrt(variance)
            else:
                volatility = 0.0

        # 2. Competitive metrics
        competitive_pressure = cheaper_percentage
        
        if competitor_count == 0:
            pricing_pos = "no_competitors"
        elif our_price < market_min:
            pricing_pos = "lowest"
        elif our_price > market_max:
            pricing_pos = "highest"
        elif cheaper_percentage > 50.0:
            pricing_pos = "upper_mid"
        else:
            pricing_pos = "lower_mid"

        # Competitor price direction (7 days comparison)
        comp_price_direction = "stable"
        seven_days_ago = datetime.utcnow() - timedelta(days=7)
        
        if preloaded_history is not None:
            hist_records = [r for r in preloaded_history if r.last_checked <= seven_days_ago][:10]
            if not hist_records:
                hist_records = sorted(preloaded_history, key=lambda x: x.last_checked)[:10]
            
            recent_price_changes = sum(1 for r in preloaded_history if r.last_checked >= seven_days_ago)
        else:
            hist_records = db.query(CompetitorPriceHistory).filter(
                CompetitorPriceHistory.product_id == product_id,
                CompetitorPriceHistory.last_checked <= seven_days_ago
            ).order_by(CompetitorPriceHistory.last_checked.desc()).limit(10).all()
            
            if not hist_records:
                hist_records = db.query(CompetitorPriceHistory).filter(
                    CompetitorPriceHistory.product_id == product_id
                ).order_by(CompetitorPriceHistory.last_checked.asc()).limit(10).all()

            recent_price_changes = db.query(CompetitorPriceHistory).filter(
                CompetitorPriceHistory.product_id == product_id,
                CompetitorPriceHistory.last_checked >= seven_days_ago
            ).count()

        if hist_records and competitor_count > 0:
            valid_hist_prices = [r.competitor_price for r in hist_records if r.competitor_price is not None]
            if valid_hist_prices:
                hist_avg = sum(valid_hist_prices) / len(valid_hist_prices)
                if market_average > hist_avg + 0.01:
                    comp_price_direction = "increasing"
                elif market_average < hist_avg - 0.01:
                    comp_price_direction = "decreasing"

        # Strongest competitor pressure
        strongest_competitor_name = "N/A"
        strongest_competitor_gap = 0.0
        if competitor_count > 0:
            min_idx = prices.index(market_min)
            strongest_competitor_name = competitors[min_idx].competitor_name
            strongest_competitor_gap = our_price - market_min

        # 3. Demand forecasting metrics
        short_term_forecast = 0.0
        mid_term_forecast = 0.0
        long_term_forecast = 0.0
        demand_direction = "stable"
        daily_sales_rate = 0.0

        try:
            forecast_data = self.demand_service.get_forecast_for_product(
                product_id, db=db, preloaded_sales=preloaded_sales
            )
            if forecast_data:
                st_data = forecast_data.get("short_term", {})
                mt_data = forecast_data.get("mid_term", {})
                lt_data = forecast_data.get("long_term", {})

                short_term_forecast = st_data.get("expected_demand") or 0.0
                mid_term_forecast = mt_data.get("expected_demand") or 0.0
                long_term_forecast = lt_data.get("expected_demand") or 0.0
                
                daily_sales_rate = st_data.get("average_daily_demand") or 0.0

                st_daily = short_term_forecast / 30.0
                mt_daily = mid_term_forecast / 90.0

                if st_daily < mt_daily - 0.01:
                    demand_direction = "increasing"
                elif st_daily > mt_daily + 0.01:
                    demand_direction = "decreasing"
        except Exception as e:
            logger.error(f"Error fetching demand forecast metrics: {e}")

        # Check db fallback sales velocity if daily rate is 0
        if daily_sales_rate <= 0:
            if preloaded_sales is not None:
                sales_records = preloaded_sales
            else:
                sales_records = db.query(SalesRecord).filter(SalesRecord.product_name == product.name).all()
            hist_sales = sum(s.units_sold for s in sales_records) if sales_records else 0.0
            daily_sales_rate = hist_sales / 30.0 if hist_sales > 0 else 1.0 # fallback default to prevent division by 0

        # 4. Seasonal metrics
        seasonal_strength = 0.0
        current_season = "normal"
        peak_period = "N/A"
        low_period = "N/A"
        seasonal_breakdown = []

        try:
            seasonal_data = self.seasonal_service.get_seasonal_trends(
                product_id, db=db, preloaded_sales=preloaded_sales
            )
            if seasonal_data:
                peak_period = seasonal_data.get("peak_period") or "N/A"
                low_period = seasonal_data.get("low_period") or "N/A"
                
                avg_dem = seasonal_data.get("average_demand") or 0.0
                peak_dem = seasonal_data.get("peak_demand") or 0.0
                low_dem = seasonal_data.get("low_demand") or 0.0
                
                if avg_dem > 0:
                    seasonal_strength = (peak_dem - low_dem) / avg_dem
                
                # Check current season month breakdown ratio
                cur_month = datetime.utcnow().month
                breakdown = seasonal_data.get("seasonal_breakdown", [])
                seasonal_breakdown = breakdown
                month_row = next((b for b in breakdown if b.get("month_index") == cur_month), None)
                if month_row and avg_dem > 0:
                    ratio = month_row.get("average_demand", avg_dem) / avg_dem
                    if ratio > 1.1:
                        current_season = "peak"
                    elif ratio < 0.9:
                        current_season = "low"
        except Exception as e:
            logger.error(f"Error fetching seasonal trends metrics: {e}")

        # 5. Inventory metrics
        projected_demand = short_term_forecast
        days_of_supply = current_stock / daily_sales_rate if daily_sales_rate > 0 else 30.0
        
        if days_of_supply < 10.0:
            inventory_risk = "understock"
            stockout_risk = True
        elif days_of_supply > 45.0:
            inventory_risk = "overstock"
            stockout_risk = False
        else:
            inventory_risk = "healthy"
            stockout_risk = False

        # 6. Overall intelligence classification
        if stockout_risk:
            classification = "Stockout Risk"
        elif inventory_risk == "overstock":
            classification = "Overstock Risk"
        elif demand_direction == "increasing" and competitive_pressure < 30.0:
            classification = "High Demand Opportunity"
        elif competitive_pressure > 50.0:
            classification = "Competitive Threat"
        elif competitor_count > 0 and our_price > market_average and demand_direction == "increasing":
            classification = "Market Opportunity"
        else:
            classification = "Stable Market"

        # 7. Generate Insights list
        insights = []
        if stockout_risk:
            insights.append(f"Stockout risk is high! Current stock ({current_stock} units) provides only {days_of_supply:.1f} days of supply.")
        elif inventory_risk == "overstock":
            insights.append(f"Excess inventory detected ({current_stock} units). Estimated supply lasts {days_of_supply:.1f} days against projected demand.")
            
        if competitor_count > 0:
            insights.append(f"We are priced {pricing_pos.replace('_', ' ')} relative to competitors (Gap to min: INR {strongest_competitor_gap:,.2f}).")
            insights.append(f"Competitor prices are {comp_price_direction} with {volatility:,.2f} standard deviation volatility.")
        else:
            insights.append("No active competitors tracked. Market competition pricing pressure is low.")

        if demand_direction == "increasing":
            insights.append("Product demand is projected to rise over the next quarter.")
        elif demand_direction == "decreasing":
            insights.append("Sales projection curves display short-term demand reduction.")

        if current_season == "peak":
            insights.append(f"Currently in peak season. Peak period traditionally falls in {peak_period}.")
        elif current_season == "low":
            insights.append(f"Currently in off-season. Off-season low period historically falls in {low_period}.")

        return {
            "product_id": product.id,
            "product_name": product.name,
            "our_price": our_price,
            "classification": classification,
            "market_metrics": {
                "market_average_price": market_average,
                "market_median_price": market_median,
                "market_min_price": market_min,
                "market_max_price": market_max,
                "competitor_count": competitor_count,
                "cheaper_competitor_percentage": cheaper_percentage,
                "competitor_price_volatility": volatility
            },
            "competitive_metrics": {
                "competitive_pressure_score": competitive_pressure,
                "pricing_position": pricing_pos,
                "competitor_price_direction": comp_price_direction,
                "recent_price_changes": recent_price_changes,
                "strongest_competitor_pressure": {
                    "competitor_name": strongest_competitor_name,
                    "price_gap": strongest_competitor_gap
                }
            },
            "demand_metrics": {
                "short_term_forecast": short_term_forecast,
                "mid_term_forecast": mid_term_forecast,
                "long_term_forecast": long_term_forecast,
                "demand_direction": demand_direction
            },
            "seasonal_metrics": {
                "seasonal_strength": seasonal_strength,
                "current_season": current_season,
                "peak_period": peak_period,
                "low_period": low_period,
                "seasonal_breakdown": seasonal_breakdown
            },
            "inventory_metrics": {
                "current_inventory": current_stock,
                "projected_demand": projected_demand,
                "days_of_supply": days_of_supply,
                "inventory_risk": inventory_risk,
                "stockout_risk": stockout_risk
            },
            "insights": insights
        }

    def calculate_portfolio_intelligence(self, db: Session) -> Dict[str, Any]:
        """
        Aggregates market intelligence stats across all catalog products using bulk queries.
        """
        from main import Product, CompetitorPrice, CompetitorPriceHistory, SalesRecord
        products = db.query(Product).all()
        
        # 1. Bulk query active competitor prices
        competitors = db.query(CompetitorPrice).filter(
            CompetitorPrice.competitor_price.isnot(None)
        ).all()
        competitors_by_product = {}
        for c in competitors:
            competitors_by_product.setdefault(c.product_id, []).append(c)

        # 2. Bulk query competitor price history
        history_records = db.query(CompetitorPriceHistory).order_by(
            CompetitorPriceHistory.last_checked.desc()
        ).all()
        history_by_product = {}
        for h in history_records:
            history_by_product.setdefault(h.product_id, []).append(h)

        # 3. Bulk query sales records
        sales_records = db.query(SalesRecord).all()
        sales_by_product_name = {}
        for s in sales_records:
            sales_by_product_name.setdefault(s.product_name, []).append(s)

        portfolio = []
        classification_counts = {
            "Market Opportunity": 0,
            "Competitive Threat": 0,
            "Stable Market": 0,
            "High Demand Opportunity": 0,
            "Overstock Risk": 0,
            "Stockout Risk": 0
        }

        total_pressure = 0.0
        risk_count = 0
        pressure_products_count = 0

        for p in products:
            try:
                p_intel = self.calculate_product_intelligence(
                    db,
                    p.id,
                    preloaded_competitors=competitors_by_product.get(p.id),
                    preloaded_history=history_by_product.get(p.id),
                    preloaded_sales=sales_by_product_name.get(p.name)
                )
                portfolio.append(p_intel)
                
                cls_type = p_intel["classification"]
                classification_counts[cls_type] = classification_counts.get(cls_type, 0) + 1

                p_pressure = p_intel["competitive_metrics"]["competitive_pressure_score"]
                if p_pressure is not None:
                    total_pressure += p_pressure
                    pressure_products_count += 1
                
                if cls_type in ["Stockout Risk", "Overstock Risk", "Competitive Threat"]:
                    risk_count += 1
            except Exception as e:
                logger.error(f"Error calculating portfolio item for {p.id}: {e}")

        total_products = len(portfolio)
        average_pressure = total_pressure / pressure_products_count if pressure_products_count > 0 else 0.0

        return {
            "total_products": total_products,
            "average_market_pressure": average_pressure,
            "products_at_risk": risk_count,
            "classification_counts": classification_counts,
            "portfolio": portfolio
        }
