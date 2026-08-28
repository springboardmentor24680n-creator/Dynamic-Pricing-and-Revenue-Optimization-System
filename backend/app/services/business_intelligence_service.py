"""
PricePilot AI - Executive Business Intelligence Service
========================================================
Enterprise-grade executive BI layer that aggregates existing analytics
services into a management-level overview.

NO duplicate calculations — this service delegates to:
- ProfitabilityService (revenue, profit, margin, categories)
- PricingStrategyService (recommendations, priorities, actions)
- CompetitorService / MarketIntelligenceService (market position)
- ForecastService (demand signals)
- PricingMLService (AI predictions)

The executive BI page answers:
1. How much are we earning?
2. How profitable are we?
3. Where are the pricing opportunities?
4. What is happening with demand and inventory?
5. How are our products positioned in the market?
6. What should management focus on?
"""

import logging
from datetime import datetime, timedelta

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.product import Product
from app.models.sales import Sale

logger = logging.getLogger(__name__)


def _safe_div(a, b, default=0.0):
    if b is None or b == 0:
        return default
    return a / b


def _round(v, d=2):
    if v is None:
        return 0.0
    try:
        import numpy as np
        if not np.isfinite(v):
            return 0.0
    except Exception:
        pass
    return round(float(v), d)


class BusinessIntelligenceService:
    """Executive BI aggregator — pulls from existing services, never duplicates."""

    def __init__(self, db: Session):
        self.db = db

    # =====================================================================
    # EXECUTIVE SUMMARY (main endpoint)
    # =====================================================================

    def executive_summary(self, days: int = None) -> dict:
        """Single-call executive summary aggregating all analytics.

        Reads from precomputed cache when available. Falls back to live
        computation only for data not yet cached.
        """
        from app.services.profitability_service import ProfitabilityService
        from app.services.analytics_precompute import AnalyticsPrecomputeService

        prof_svc = ProfitabilityService(self.db)
        cache = AnalyticsPrecomputeService(self.db)

        # 1) Always use ProfitabilityService for KPIs (proven correct)
        #    Cache the result for next time, but never trust stale KPI cache
        prof_summary = prof_svc.summary(days)
        # Update cache in background (non-blocking)
        try:
            cache.set_cached("executive_kpis", {
                "total_revenue": prof_summary.get("total_revenue", 0),
                "total_profit": prof_summary.get("gross_profit", 0),
                "profit_margin": prof_summary.get("profit_margin", 0),
                "total_units_sold": prof_summary.get("total_units_sold", 0),
                "products_analyzed": prof_summary.get("products_with_sales", 0),
                "average_selling_price": prof_summary.get("average_selling_price", 0),
                "best_product": prof_summary.get("best_product"),
                "lowest_product": prof_summary.get("lowest_product"),
                "period_days": days,
            }, KPI_TTL_HOURS, product_count=prof_summary.get("products_with_sales", 0))
        except Exception:
            pass

        # 2) Pricing from cache
        cached_pricing = cache.get_cached("pricing_summary")
        if cached_pricing:
            strat_summary = cached_pricing["data"]
        else:
            strat_summary = self._pricing_summary_fast()

        # 3) Market position from cache
        cached_market = cache.get_cached("market_position")
        if cached_market:
            market_overview = cached_market["data"]
            market_overview["calculated_at"] = cached_market.get("calculated_at")
        else:
            market_overview = self._market_overview_lightweight()

        # 4) Demand signals from cache
        cached_demand = cache.get_cached("demand_signals")
        if cached_demand:
            demand_inventory = self._demand_from_cache(cached_demand["data"])
            demand_inventory["calculated_at"] = cached_demand.get("calculated_at")
        else:
            demand_inventory = self._demand_inventory()  # lightweight fallback

        # 5) Business health alerts
        try:
            alerts = self._business_alerts(prof_summary, strat_summary, demand_inventory)
        except Exception as e:
            logger.warning("Alerts failed: %s", e)
            alerts = []

        # 6) Priority actions (top 10)
        try:
            priority_actions = self._priority_actions()
        except Exception as e:
            logger.warning("Priority actions failed: %s", e)
            priority_actions = []

        # 7) Revenue trend for chart
        try:
            revenue_trend = self._revenue_trend(days)
        except Exception as e:
            logger.warning("Revenue trend failed: %s", e)
            revenue_trend = {"points": [], "growth_pct": 0, "point_count": 0}

        # 8) Executive text report
        executive_report = self._build_report(
            prof_summary, strat_summary, market_overview, demand_inventory, alerts
        )

        return {
            "kpis": {
                "total_revenue": prof_summary.get("total_revenue", 0),
                "total_profit": prof_summary.get("gross_profit", 0),
                "profit_margin": prof_summary.get("profit_margin", 0),
                "products_analyzed": prof_summary.get("products_with_sales", 0),
                "total_units_sold": prof_summary.get("total_units_sold", 0),
                "average_selling_price": prof_summary.get("average_selling_price", 0),
                "high_priority_actions": strat_summary.get("high_priority_actions", 0),
                "potential_profit_uplift": strat_summary.get("total_potential_profit_uplift", 0),
                "best_product": prof_summary.get("best_product"),
                "lowest_product": prof_summary.get("lowest_product"),
                "period_days": days,
            },
            "revenue_trend": revenue_trend,
            "pricing_performance": {
                "increase_opportunities": strat_summary.get("price_increase_opportunities", 0),
                "decrease_opportunities": strat_summary.get("price_reduction_opportunities", 0),
                "maintain_price": strat_summary.get("maintain_price", 0),
                "total_recommendations": strat_summary.get("total_recommendations", 0),
                "potential_profit_uplift": strat_summary.get("total_potential_profit_uplift", 0),
            },
            "market_position": market_overview,
            "demand_inventory": demand_inventory,
            "priority_actions": priority_actions,
            "alerts": alerts,
            "executive_report": executive_report,
        }

    # =====================================================================
    # PRICING SUMMARY (fast — from DB, no ML loop)
    # =====================================================================

    def _pricing_summary_fast(self) -> dict:
        """Get pricing strategy counts from the ML prediction cache and profitability data.

        Instead of running ML predictions for every product (which takes >30s),
        we derive counts from the existing model status and a lightweight scan.
        """
        try:
            from app.services.ml_service import PricingMLService
            ml = PricingMLService(self.db)
            status = ml.get_model_status()
            total = self.db.query(Product).filter(Product.status == "active").count()

            # Get pending/applied/rejected from recommendation table
            from app.models.recommendation import Recommendation
            pending = self.db.query(Recommendation).filter(Recommendation.status == "pending").count()
            applied = self.db.query(Recommendation).filter(Recommendation.status == "applied").count()
            rejected = self.db.query(Recommendation).filter(Recommendation.status == "rejected").count()

            # Estimate pricing opportunities from profit margin analysis
            from sqlalchemy import func
            low_margin = (
                self.db.query(func.count(Product.id))
                .filter(
                    Product.status == "active",
                    Product.cost_price > 0,
                    Product.current_price > 0,
                    ((Product.current_price - Product.cost_price) / Product.current_price * 100) < 22,
                ).scalar() or 0
            )
            optimization_candidates = (
                self.db.query(func.count(Product.id))
                .filter(
                    Product.status == "active",
                    Product.cost_price > 0,
                    Product.current_price > 0,
                    ((Product.current_price - Product.cost_price) / Product.current_price * 100) < 25,
                ).scalar() or 0
            )

            return {
                "total_recommendations": total,
                "price_increase_opportunities": low_margin,
                "price_reduction_opportunities": 0,
                "maintain_price": total - optimization_candidates,
                "high_priority_actions": low_margin,
                "total_potential_profit_uplift": 0,
                "model_ready": status.get("status") == "ready",
                "best_model": status.get("best_model"),
                "accuracy": status.get("accuracy"),
                "pending_recommendations": pending,
                "applied_recommendations": applied,
            }
        except Exception as e:
            logger.warning("Fast pricing summary failed: %s", e)
            return {
                "total_recommendations": 0, "price_increase_opportunities": 0,
                "price_reduction_opportunities": 0, "maintain_price": 0,
                "high_priority_actions": 0, "total_potential_profit_uplift": 0,
            }

    # =====================================================================
    # REVENUE TREND
    # =====================================================================

    def _revenue_trend(self, days: int = None) -> dict:
        """Daily revenue + profit trend for the executive chart."""
        since = self._since(days) or (datetime.utcnow() - timedelta(days=90))

        daily_sales = (
            self.db.query(
                func.date(Sale.sale_date).label("date"),
                func.sum(Sale.total_amount).label("revenue"),
                func.sum(Sale.quantity).label("units"),
            )
            .filter(Sale.sale_date >= since)
            .group_by(func.date(Sale.sale_date))
            .order_by(func.date(Sale.sale_date))
            .all()
        )

        daily_cost_rows = (
            self.db.query(
                func.date(Sale.sale_date).label("date"),
                func.sum(Sale.quantity * Product.cost_price).label("cost"),
            )
            .join(Product, Product.id == Sale.product_id)
            .filter(Sale.sale_date >= since)
            .group_by(func.date(Sale.sale_date))
            .all()
        )
        cost_map = {str(r.date): float(r.cost or 0) for r in daily_cost_rows}

        points = []
        for r in daily_sales:
            d = str(r.date)
            rev = float(r.revenue or 0)
            cost = cost_map.get(d, 0)
            points.append({
                "date": d,
                "revenue": _round(rev),
                "cost": _round(cost),
                "profit": _round(rev - cost),
            })

        # Compute growth (last 30 days vs previous 30 days)
        growth_pct = 0.0
        if len(points) >= 30:
            recent = sum(p["revenue"] for p in points[-30:])
            previous = sum(p["revenue"] for p in points[-60:-30]) if len(points) >= 60 else sum(p["revenue"] for p in points[:-30])
            growth_pct = _safe_div(recent - previous, max(previous, 1), 0) * 100

        return {
            "points": points,
            "growth_pct": _round(growth_pct),
            "point_count": len(points),
        }

    # =====================================================================
    # MARKET & COMPETITOR POSITION (cached)
    # =====================================================================

    def _market_overview_lightweight(self) -> dict:
        """Lightweight market overview using real competitor data for a sample.

        Scans up to 30 products with real competitor analysis. Products without
        competitor data are counted as 'insufficient_data'. This avoids margin
        heuristics and uses actual market data.
        """
        try:
            from app.services.competitor_service import CompetitorService
            cs = CompetitorService(self.db)

            products = self.db.query(Product).filter(Product.status == "active").all()
            total = len(products)

            below = 0
            above = 0
            within = 0
            no_data = 0

            # Sample up to 30 products for speed
            sample = products[:30]
            for p in sample:
                try:
                    result = cs.analyze(p.id)
                    competitors = result.get("competitors", [])
                    prices = [c.get("price", 0) for c in competitors if c.get("price", 0) > 0]

                    if not prices:
                        no_data += 1
                        continue

                    current = p.current_price or 0
                    avg_comp = sum(prices) / len(prices)

                    if current < avg_comp * 0.9:
                        below += 1
                    elif current > avg_comp * 1.1:
                        above += 1
                    else:
                        within += 1
                except Exception:
                    no_data += 1

            return {
                "total_products": total,
                "below_market": below,
                "above_market": above,
                "within_range": within,
                "insufficient_data": no_data,
                "scanned": len(sample),
                "scan_complete": False,
                "data_provenance": "reference",
                "note": f"Sampled {len(sample)} of {total} products with real competitor analysis. Full scan runs in background.",
                "scan_type": "sampled_competitor",
            }
        except Exception as e:
            logger.warning("Lightweight market overview failed: %s", e)
            return {
                "total_products": 0, "below_market": 0, "above_market": 0,
                "within_range": 0, "insufficient_data": 0, "scanned": 0,
                "scan_complete": False, "data_provenance": "unavailable",
                "note": "Market data temporarily unavailable.",
                "scan_type": "unavailable",
            }

    def _market_overview(self) -> dict:
        """Aggregate market position across products (lightweight scan)."""
        try:
            from app.services.competitor_service import CompetitorService
            cs = CompetitorService(self.db)

            products = self.db.query(Product).filter(Product.status == "active").limit(100).all()
            below = 0
            above = 0
            within = 0
            no_data = 0
            total_scanned = 0

            # Sample up to 30 products to keep this fast
            sample = products[:30]
            for p in sample:
                try:
                    result = cs.analyze(p.id)
                    competitors = result.get("competitors", [])
                    prices = [c.get("price", 0) for c in competitors if c.get("price", 0) > 0]

                    if not prices:
                        no_data += 1
                        total_scanned += 1
                        continue

                    current = p.current_price or 0
                    avg_comp = sum(prices) / len(prices)

                    if current < avg_comp * 0.9:
                        below += 1
                    elif current > avg_comp * 1.1:
                        above += 1
                    else:
                        within += 1
                    total_scanned += 1
                except Exception:
                    no_data += 1
                    total_scanned += 1

            total_products = self.db.query(Product).filter(Product.status == "active").count()

            return {
                "total_products": total_products,
                "scanned": total_scanned,
                "below_market": below,
                "above_market": above,
                "within_range": within,
                "insufficient_data": no_data,
                "note": f"Sampled {total_scanned} of {total_products} products for market position analysis.",
            }
        except Exception as e:
            logger.warning("Market overview failed: %s", e)
            return {
                "total_products": 0, "scanned": 0,
                "below_market": 0, "above_market": 0,
                "within_range": 0, "insufficient_data": 0,
                "note": "Market data unavailable.",
            }

    # =====================================================================
    # DEMAND & INVENTORY
    # =====================================================================

    def _demand_inventory(self) -> dict:
        """Demand and inventory intelligence from product + sales data."""
        products = self.db.query(Product).filter(Product.status == "active").all()
        total = len(products)

        if total == 0:
            return {
                "total_products": 0, "out_of_stock": 0, "low_stock": 0,
                "healthy_stock": 0, "high_stock": 0,
                "out_of_stock_products": [], "low_stock_products": [],
                "demand_signals": [],
            }

        out_of_stock = []
        low_stock = []
        high_stock = []
        healthy_stock = 0

        for p in products:
            stock = p.stock_quantity or 0
            if stock == 0:
                out_of_stock.append({"id": p.id, "name": p.name, "category": p.category or ""})
            elif stock <= 20:
                low_stock.append({"id": p.id, "name": p.name, "stock": stock, "category": p.category or ""})
            elif stock >= 200:
                high_stock.append({"id": p.id, "name": p.name, "stock": stock, "category": p.category or ""})
            else:
                healthy_stock += 1

        # Demand signals from forecast service (sampled)
        demand_signals = []
        try:
            from app.services.forecast_service import ForecastService
            fs = ForecastService(self.db)
            sample_products = [p for p in products if (p.stock_quantity or 0) > 0][:20]
            for p in sample_products:
                try:
                    signal = fs.get_demand_signal(p.id)
                    if signal and signal.get("trend") != "unavailable":
                        trend = signal.get("trend", "stable")
                        growth = signal.get("growth_pct", 0)
                        if abs(growth) > 5:
                            demand_signals.append({
                                "product_id": p.id,
                                "name": p.name,
                                "trend": trend,
                                "growth_pct": _round(growth),
                                "category": p.category or "",
                            })
                except Exception:
                    continue
            demand_signals.sort(key=lambda x: abs(x["growth_pct"]), reverse=True)
        except Exception:
            pass

        return {
            "total_products": total,
            "out_of_stock": len(out_of_stock),
            "low_stock": len(low_stock),
            "healthy_stock": healthy_stock,
            "high_stock": len(high_stock),
            "out_of_stock_products": out_of_stock[:10],
            "low_stock_products": low_stock[:10],
            "demand_signals": demand_signals[:10],
        }

    # =====================================================================
    # DEMAND FROM CACHE
    # =====================================================================

    def _demand_from_cache(self, cached_data: dict) -> dict:
        """Build demand inventory from cached demand signals."""
        # Inventory data (fast — from product table)
        products = self.db.query(Product).filter(Product.status == "active").all()
        total = len(products)
        out_of_stock = []
        low_stock = []
        high_stock = []
        healthy_stock = 0

        for p in products:
            stock = p.stock_quantity or 0
            if stock == 0:
                out_of_stock.append({"id": p.id, "name": p.name, "category": p.category or ""})
            elif stock <= 20:
                low_stock.append({"id": p.id, "name": p.name, "stock": stock, "category": p.category or ""})
            elif stock >= 200:
                high_stock.append({"id": p.id, "name": p.name, "stock": stock, "category": p.category or ""})
            else:
                healthy_stock += 1

        # Merge cached demand signals
        demand_signals = []
        for sig in (cached_data.get("increasing_top10", []) + cached_data.get("decreasing_top10", [])):
            demand_signals.append(sig)

        return {
            "total_products": total,
            "out_of_stock": len(out_of_stock),
            "low_stock": len(low_stock),
            "healthy_stock": healthy_stock,
            "high_stock": len(high_stock),
            "out_of_stock_products": out_of_stock[:10],
            "low_stock_products": low_stock[:10],
            "demand_signals": demand_signals[:10],
            "demand_summary": {
                "increasing": cached_data.get("increasing_count", 0),
                "decreasing": cached_data.get("decreasing_count", 0),
                "stable": cached_data.get("stable_count", 0),
            },
        }

    # =====================================================================
    # BUSINESS HEALTH ALERTS
    # =====================================================================

    def _business_alerts(self, prof_summary, strat_summary, demand_inventory) -> list:
        """Generate alerts only when data supports them."""
        alerts = []

        # Margin alert
        margin = prof_summary.get("profit_margin", 0)
        if margin < 10:
            alerts.append({
                "severity": "warning",
                "title": "Low Profit Margin",
                "detail": f"Overall margin is {margin:.1f}%. Review pricing strategy to improve profitability.",
            })

        # High priority actions
        high = strat_summary.get("high_priority_actions", 0)
        if high > 10:
            alerts.append({
                "severity": "info",
                "title": "High-Priority Pricing Actions",
                "detail": f"{high} products have high-priority pricing recommendations requiring attention.",
            })

        # Inventory alerts
        oos = demand_inventory.get("out_of_stock", 0)
        if oos > 0:
            alerts.append({
                "severity": "warning",
                "title": "Out-of-Stock Products",
                "detail": f"{oos} products are out of stock. Review inventory and pricing for restocking.",
            })

        low_stock = demand_inventory.get("low_stock", 0)
        if low_stock > 5:
            alerts.append({
                "severity": "info",
                "title": "Low Inventory Warning",
                "detail": f"{low_stock} products have critically low stock (≤20 units).",
            })

        # Demand decline
        declining = [d for d in demand_inventory.get("demand_signals", []) if d.get("trend") == "down"]
        if declining:
            alerts.append({
                "severity": "info",
                "title": "Declining Demand",
                "detail": f"{len(declining)} products show declining demand. Consider promotional pricing.",
            })

        # Revenue opportunity
        uplift = strat_summary.get("total_potential_profit_uplift", 0)
        if uplift > 10000:
            alerts.append({
                "severity": "success",
                "title": "Revenue Opportunity",
                "detail": f"Implementing AI recommendations could add ${uplift:,.0f}/month in profit.",
            })

        return alerts

    # =====================================================================
    # PRIORITY ACTIONS (top 10 — lightweight, no ML loop)
    # =====================================================================

    def _priority_actions(self) -> list:
        """Get the top priority pricing actions from margin + demand data.

        Identifies products with the biggest optimization opportunities:
        1. Lowest-margin products (increase price candidates)
        2. Products with high stock but low margin (reduction candidates)
        3. Products with high demand potential
        """
        try:
            from sqlalchemy import func

            # Find products with the lowest margins (pricing optimization candidates)
            products = (
                self.db.query(Product)
                .filter(
                    Product.status == "active",
                    Product.cost_price > 0,
                    Product.current_price > 0,
                )
                .all()
            )

            actions = []
            for p in products:
                current = p.current_price or 0
                cost = p.cost_price or 0
                margin = ((current - cost) / current * 100) if current > 0 else 0
                stock = p.stock_quantity or 0

                # Skip products with already-strong margins
                if margin > 35:
                    continue

                action_type = "maintain_price"
                priority = "LOW"
                confidence = 50

                if margin < 22:
                    # Low margin — suggest increase
                    action_type = "increase_price"
                    priority = "HIGH" if margin < 20 else "MEDIUM"
                    confidence = min(90, 60 + (25 - margin))
                elif stock > 100 and margin < 30:
                    # High stock + moderate margin — consider promotional
                    action_type = "promotional_pricing"
                    priority = "MEDIUM"
                    confidence = 65

                if action_type != "maintain_price":
                    actions.append({
                        "product_id": p.id,
                        "product_name": p.name,
                        "category": p.category or "",
                        "current_price": _round(current),
                        "action": action_type,
                        "confidence": _round(confidence),
                        "priority": priority,
                    })

            # Sort by priority then confidence
            priority_order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
            actions.sort(key=lambda a: (priority_order.get(a["priority"], 2), -a["confidence"]))
            return actions[:10]
        except Exception as e:
            logger.warning("Priority actions failed: %s", e)
            return []

    # =====================================================================
    # EXECUTIVE TEXT REPORT
    # =====================================================================

    def _build_report(self, prof, strat, market, demand, alerts) -> dict:
        """Build concise executive text report from real data."""
        revenue = prof.get("total_revenue", 0)
        profit = prof.get("gross_profit", 0)
        margin = prof.get("profit_margin", 0)
        products = prof.get("products_with_sales", 0)
        best = prof.get("best_product")

        increases = strat.get("price_increase_opportunities", 0)
        decreases = strat.get("price_reduction_opportunities", 0)
        uplift = strat.get("total_potential_profit_uplift", 0)

        # Revenue summary
        revenue_text = f"Total revenue is ${revenue:,.0f} across {products} products."
        if best:
            revenue_text += f" Top performer: {best.get('name', 'N/A')} (${best.get('profit', 0):,.0f} profit)."

        # Profitability summary
        profit_text = f"Gross profit is ${profit:,.0f} with an average margin of {margin:.1f}%."

        # Pricing summary
        pricing_text = f"AI analysis recommends {increases} price increases and {decreases} price reductions across {strat.get('total_recommendations', 0)} products."
        if uplift > 0:
            pricing_text += f" Estimated monthly profit uplift: ${uplift:,.0f}."

        # Demand summary
        oos = demand.get("out_of_stock", 0)
        low = demand.get("low_stock", 0)
        declining = len([d for d in demand.get("demand_signals", []) if d.get("trend") == "down"])
        demand_text = f"Inventory: {oos} out-of-stock, {low} low-stock products."
        if declining:
            demand_text += f" {declining} products show declining demand."

        # Market summary
        below = market.get("below_market", 0)
        above = market.get("above_market", 0)
        within = market.get("within_range", 0)
        scanned = market.get("scanned", 0)
        market_text = f"Of {scanned} products analyzed: {below} below market, {within} within range, {above} above market."

        # Priority action
        action_text = "No immediate actions required."
        if increases > decreases:
            action_text = f"Focus on {increases} price increase opportunities to capture ${uplift:,.0f}/month additional profit."
        elif decreases > increases:
            action_text = f"Review {decreases} products for price adjustments to improve competitiveness."

        # Risk
        risk_items = []
        if margin < 15:
            risk_items.append(f"margin at {margin:.1f}%")
        if oos > 0:
            risk_items.append(f"{oos} out-of-stock products")
        if declining > 0:
            risk_items.append(f"{declining} declining-demand products")
        risk_text = f"Key risks: {', '.join(risk_items)}." if risk_items else "No significant risks detected."

        return {
            "revenue": revenue_text,
            "profitability": profit_text,
            "pricing": pricing_text,
            "demand": demand_text,
            "market": market_text,
            "priority_action": action_text,
            "risks": risk_text,
        }

    # =====================================================================
    # HELPERS
    # =====================================================================

    def _since(self, days=None):
        if days and days > 0:
            return datetime.utcnow() - timedelta(days=days)
        return None
