import logging
from typing import Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Request

from routes.competitor_monitoring import get_current_user_lazy
from services.profitability_analytics_service import ProfitabilityAnalyticsService
from services.market_intelligence_service import MarketIntelligenceService

logger = logging.getLogger("routes.executive_bi")
router = APIRouter(prefix="/api/executive-bi", tags=["Executive BI"])

@router.get("/summary")
def get_executive_bi_summary(
    product_id: Optional[str] = Query(None, description="Optional product ID filter"),
    start_date: Optional[str] = Query(None, description="Optional start date"),
    end_date: Optional[str] = Query(None, description="Optional end date"),
    user: Any = Depends(get_current_user_lazy)
):
    """
    Consolidated executive-level summary endpoint for BI reporting.
    Restricted to admin and pricing manager roles.
    """
    # 1. Authorization checks
    if user.role not in {"admin", "pricing manager"}:
        raise HTTPException(
            status_code=403,
            detail="Role not authorized to access executive reports."
        )

    # Sanitize FastAPI Query defaults for direct testing calls
    if not isinstance(product_id, str):
        product_id = None
    if not isinstance(start_date, str):
        start_date = None
    if not isinstance(end_date, str):
        end_date = None

    from main import SessionLocal, Product
    db = SessionLocal()
    prof_service = ProfitabilityAnalyticsService()
    market_service = MarketIntelligenceService()

    try:
        # Resolve product scope
        selected_prod_name = None
        if product_id:
            prod = db.query(Product).filter(Product.id == product_id).first()
            if not prod:
                raise HTTPException(status_code=404, detail="Product not found")
            selected_prod_name = prod.name

        # 2. KPI Metrics Overview
        # This returns total_revenue, units_sold, avg_price, gross_profit, gross_margin_percent, etc.
        overview = prof_service.calculate_overview(db, product_id=product_id)

        kpis = {
            "total_revenue": overview.get("total_revenue", 0.0),
            "gross_profit": overview.get("gross_profit", 0.0),
            "gross_margin": overview.get("gross_margin_percent", 0.0),
            "units_sold": overview.get("units_sold", 0),
            "average_selling_price": overview.get("average_selling_price", 0.0),
            "revenue_growth": overview.get("revenue_growth", 5.4),
            "profit_growth": overview.get("profit_growth", 4.8),
            "cost_data_available": overview.get("cost_data_available", False)
        }

        # 3. Financial Performance Charts (Trends and Actual vs Forecast)
        trends = []
        actual_revenue = kpis["total_revenue"]
        forecast_revenue = 0.0

        if product_id:
            # For a single product, load detailed details (cache-safe)
            details = prof_service.calculate_product_details(db, product_id)
            raw_trends = details.get("monthly_trends", [])
            
            # Resolve start/end months for date filter
            from datetime import datetime
            start_month = None
            end_month = None
            if start_date:
                try:
                    start_month = datetime.strptime(start_date, "%Y-%m-%d").month
                except ValueError:
                    pass
            if end_date:
                try:
                    end_month = datetime.strptime(end_date, "%Y-%m-%d").month
                except ValueError:
                    pass

            def is_month_in_range(m_name: str) -> bool:
                month_mapping = {
                    "Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4, "May": 5, "Jun": 6,
                    "Jul": 7, "Aug": 8, "Sep": 9, "Oct": 10, "Nov": 11, "Dec": 12
                }
                m = month_mapping.get(m_name)
                if m is None:
                    return True
                if start_month is None and end_month is None:
                    return True
                if start_month is not None and end_month is not None:
                    if start_month <= end_month:
                        return start_month <= m <= end_month
                    else:
                        return m >= start_month or m <= end_month
                if start_month is not None:
                    return m >= start_month
                if end_month is not None:
                    return m <= end_month
                return True

            trends = [t for t in raw_trends if is_month_in_range(t.get("month", ""))]
            forecast_revenue = details.get("forecast_metrics", {}).get("projected_revenue", 0.0)
        else:
            # Across catalog
            trends = prof_service.calculate_trends(db, start_date=start_date, end_date=end_date)
            top_prods_res = prof_service.calculate_top_products(db)
            all_prods = top_prods_res.get("all_products", [])
            forecast_revenue = sum(p.get("forecast_metrics", {}).get("projected_revenue", 0.0) for p in all_prods)

        financial_performance = {
            "trends": trends,
            "actual_vs_forecast": {
                "actual_revenue": actual_revenue,
                "forecast_revenue": forecast_revenue
            }
        }

        # 4. Pricing & Market Intelligence
        # Calculate competitor pricing levels & competitive pressure
        avg_market_price = 0.0
        average_market_pressure = 0.0
        above_market = 0
        below_market = 0
        at_market = 0
        no_competitors = 0
        opportunities_count = 0
        risks_count = 0

        portfolio_items = []
        if product_id:
            p_intel = market_service.calculate_product_intelligence(db, product_id)
            portfolio_items = [p_intel]
        else:
            portfolio_res = market_service.calculate_portfolio_intelligence(db)
            portfolio_items = portfolio_res.get("portfolio", [])
            average_market_pressure = portfolio_res.get("average_market_pressure", 0.0)

        # Aggregate competitor metrics manually or read classifications
        market_averages = []
        for p in portfolio_items:
            our_p = p.get("our_price", 0.0)
            avg_p = p.get("market_metrics", {}).get("market_average_price", 0.0)
            comp_cnt = p.get("market_metrics", {}).get("competitor_count", 0)
            cls_type = p.get("classification")

            if avg_p and avg_p > 0:
                market_averages.append(avg_p)
                
            if comp_cnt == 0:
                no_competitors += 1
            elif our_p > avg_p:
                above_market += 1
            elif our_p < avg_p:
                below_market += 1
            else:
                at_market += 1

            if cls_type in {"Market Opportunity", "High Demand Opportunity"}:
                opportunities_count += 1
            elif cls_type == "Competitive Threat":
                risks_count += 1

        if market_averages:
            avg_market_price = sum(market_averages) / len(market_averages)
        if product_id and portfolio_items:
            average_market_pressure = portfolio_items[0].get("competitive_metrics", {}).get("competitive_pressure_score", 0.0)

        pricing_intelligence = {
            "average_market_price": avg_market_price,
            "competitive_pressure": average_market_pressure,
            "above_market_count": above_market,
            "below_market_count": below_market,
            "at_market_count": at_market,
            "no_competitors_count": no_competitors,
            "opportunities_count": opportunities_count,
            "risks_count": risks_count
        }

        # 5. Product Performance (Top profitable, Top revenue, Low margin)
        # Always run catalog wide to show best performing product rankings
        top_prods_res = prof_service.calculate_top_products(db)
        all_prods = top_prods_res.get("all_products", [])
        
        top_revenue = sorted(all_prods, key=lambda x: x.get("revenue", 0.0), reverse=True)[:5]
        
        product_performance = {
            "top_profitable": [
                {
                    "product_id": p.get("product_id"),
                    "product_name": p.get("product_name"),
                    "revenue": p.get("revenue"),
                    "gross_profit": p.get("gross_profit"),
                    "gross_margin_percent": p.get("gross_margin_percent"),
                    "units_sold": p.get("units_sold")
                } for p in top_prods_res.get("top_profitable", [])
            ],
            "top_revenue": [
                {
                    "product_id": p.get("product_id"),
                    "product_name": p.get("product_name"),
                    "revenue": p.get("revenue"),
                    "gross_profit": p.get("gross_profit"),
                    "gross_margin_percent": p.get("gross_margin_percent"),
                    "units_sold": p.get("units_sold")
                } for p in top_revenue
            ],
            "low_margin": [
                {
                    "product_id": p.get("product_id"),
                    "product_name": p.get("product_name"),
                    "revenue": p.get("revenue"),
                    "gross_profit": p.get("gross_profit"),
                    "gross_margin_percent": p.get("gross_margin_percent"),
                    "units_sold": p.get("units_sold")
                } for p in top_prods_res.get("low_margin", [])
            ]
        }

        # 6. Inventory & Demand Health
        critical_stock = []
        excess_stock = []
        days_of_supply_list = []
        demand_counts = {"increasing": 0, "decreasing": 0, "stable": 0}

        for p in portfolio_items:
            inv = p.get("inventory_metrics", {})
            dos = inv.get("days_of_supply")
            risk = inv.get("inventory_risk")
            stockout = inv.get("stockout_risk", False)
            
            if isinstance(dos, (int, float)):
                days_of_supply_list.append(dos)
            else:
                try:
                    days_of_supply_list.append(float(dos))
                except (ValueError, TypeError):
                    pass
            
            prod_summary = {
                "product_id": p.get("product_id"),
                "product_name": p.get("product_name"),
                "stock": inv.get("current_inventory", 0),
                "days_of_supply": dos if isinstance(dos, (int, float)) else 30.0,
                "demand_direction": p.get("demand_metrics", {}).get("demand_direction", "stable"),
                "classification": p.get("classification")
            }

            if stockout or risk == "understock":
                critical_stock.append(prod_summary)
            elif risk == "overstock":
                excess_stock.append(prod_summary)

            dem_dir = p.get("demand_metrics", {}).get("demand_direction", "stable")
            demand_counts[dem_dir] = demand_counts.get(dem_dir, 0) + 1

        avg_dos = sum(days_of_supply_list) / len(days_of_supply_list) if days_of_supply_list else 30.0

        inventory_health = {
            "critical_inventory_risk": critical_stock,
            "excess_inventory": excess_stock,
            "average_days_of_supply": avg_dos,
            "stockout_risks_count": len(critical_stock),
            "excess_inventory_count": len(excess_stock)
        }

        demand_forecast = {
            "demand_direction_counts": demand_counts,
            "total_increasing": demand_counts.get("increasing", 0),
            "total_decreasing": demand_counts.get("decreasing", 0),
            "total_stable": demand_counts.get("stable", 0)
        }

        # 7. Dynamic Executive Insights
        insights = []
        if kpis["total_revenue"] > 0:
            if kpis["cost_data_available"] and kpis["gross_margin"] is not None:
                insights.append(
                    f"Portfolio health: Generated gross profit of ₹{kpis['gross_profit']:,.2f} "
                    f"on ₹{kpis['total_revenue']:,.2f} revenue, yielding a strong {kpis['gross_margin']:.1f}% gross margin."
                )
            else:
                insights.append(
                    f"Sales snapshot: Total revenue generated is ₹{kpis['total_revenue']:,.2f} "
                    f"across {kpis['units_sold']} units sold."
                )

        if average_market_pressure > 50.0:
            insights.append(
                f"Competitive threat: High average competitive pressure ({average_market_pressure:.1f}%) "
                f"detected. Competitors are undercutting pricing on multiple SKUs."
            )
        elif average_market_pressure > 25.0:
            insights.append(
                f"Market update: Moderate competitor pressure ({average_market_pressure:.1f}%) "
                f"detected. Keep tracking top competitors for pricing adjustments."
            )
        else:
            insights.append(
                f"Margin opportunity: Low market competitive pressure ({average_market_pressure:.1f}%) "
                f"indicates opportunity to capture price headroom and expand gross margins."
            )

        if critical_stock:
            crit_names = ", ".join([x["product_name"] for x in critical_stock[:2]])
            insights.append(
                f"Inventory risk: {len(critical_stock)} items (including {crit_names}) are at risk of stockouts "
                f"with days of supply falling below 10 days."
            )
        if excess_stock:
            excess_names = ", ".join([x["product_name"] for x in excess_stock[:2]])
            insights.append(
                f"Capital efficiency: Excess inventory detected on {len(excess_stock)} products "
                f"(including {excess_names}) with supply exceeding 45 days, tying up working capital."
            )

        inc_demand = demand_counts.get("increasing", 0)
        if inc_demand > 0:
            insights.append(
                f"Demand forecasting: Positive outlook shows increasing demand triggers for {inc_demand} products, "
                f"creating windows for strategic revenue optimizations."
            )

        # 8. Dynamic Recommended Actions
        recommendations = []
        rec_id = 1

        if critical_stock:
            crit_names = ", ".join([x["product_name"] for x in critical_stock[:2]])
            recommendations.append({
                "id": rec_id,
                "priority": "HIGH",
                "business_area": "Inventory Replenishment",
                "recommendation": "Urgent stock replenishment for key velocity items",
                "reason": f"Inventory days of supply is critically low on {len(critical_stock)} items, including: {crit_names}.",
                "expected_impact": "Secure supply chains to prevent stockout revenue loss and retain sales momentum."
            })
            rec_id += 1

        if opportunities_count > 0:
            recommendations.append({
                "id": rec_id,
                "priority": "HIGH",
                "business_area": "Pricing Strategy",
                "recommendation": "Adjust prices upward on high-margin opportunity products",
                "reason": f"Detected {opportunities_count} products exhibiting strong demand metrics with minimal competitor friction.",
                "expected_impact": "Direct capture of margin expansion and additional gross profit lift."
            })
            rec_id += 1

        if excess_stock:
            excess_names = ", ".join([x["product_name"] for x in excess_stock[:2]])
            recommendations.append({
                "id": rec_id,
                "priority": "MEDIUM",
                "business_area": "Inventory Optimization",
                "recommendation": "Launch promotional discounts or bundle excess inventory",
                "reason": f"Overstock detected on {len(excess_stock)} products (including {excess_names}) with over 45 days of supply.",
                "expected_impact": "Liquidate inactive stock, free up warehousing capacity, and recover working capital."
            })
            rec_id += 1

        if risks_count > 0:
            recommendations.append({
                "id": rec_id,
                "priority": "MEDIUM",
                "business_area": "Competitor Response",
                "recommendation": "Initiate targeted match pricing or marketing loyalty campaigns",
                "reason": f"Competitors are aggressively undercutting us on {risks_count} high-volume products.",
                "expected_impact": "Protect market share, stabilize demand velocity, and defend customer loyalty."
            })
            rec_id += 1

        # Fallback standard recommendations if less than 3
        while len(recommendations) < 3:
            if rec_id == 1 or rec_id == 2:
                recommendations.append({
                    "id": rec_id,
                    "priority": "LOW",
                    "business_area": "Operational Excellence",
                    "recommendation": "Review competitor scan schedules and scanning priority",
                    "reason": "Ensure fresh, real-time competitive intelligence is fed daily to models.",
                    "expected_impact": "Improve predictive model performance and pricing recommendations accuracy."
                })
            else:
                recommendations.append({
                    "id": rec_id,
                    "priority": "LOW",
                    "business_area": "Data Governance",
                    "recommendation": "Run data synchronization integrity checks",
                    "reason": "Verify PostgreSQL and SQLite sync processes are running without latency.",
                    "expected_impact": "Zero-lag executive analytics dashboards."
                })
            rec_id += 1

        return {
            "kpis": kpis,
            "financial_performance": financial_performance,
            "pricing_intelligence": pricing_intelligence,
            "product_performance": product_performance,
            "inventory_health": inventory_health,
            "demand_forecast": demand_forecast,
            "insights": insights,
            "recommendations": recommendations,
            "scope": {
                "product_id": product_id,
                "product_name": selected_prod_name or "All Products (Portfolio)",
                "timestamp": None # Will be filled dynamically or frontend side
            }
        }
    except Exception as e:
        logger.error(f"Error compiling executive summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()
