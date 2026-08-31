"""
PricePilot AI - Profitability Analytics Service
================================================
Enterprise-grade profitability analytics derived entirely from real product,
sales, pricing-history, and AI-prediction data.

No dummy data, no hardcoded values. Every metric updates dynamically.
"""

import logging
from datetime import datetime, timedelta, timezone

import numpy as np
from sqlalchemy import func, case, and_
from sqlalchemy.orm import Session

from app.models.product import Product
from app.models.sales import Sale

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _safe_div(a, b, default=0.0):
    """Safe division that returns *default* when the denominator is zero/None."""
    if b is None or b == 0:
        return default
    return a / b


def _round(v, d=2):
    if v is None or not np.isfinite(v):
        return 0.0
    return round(float(v), d)


# ---------------------------------------------------------------------------
# Core Service
# ---------------------------------------------------------------------------

class ProfitabilityService:
    """Compute profitability KPIs, trends, per-product and per-category
    breakdowns, AI pricing impact, opportunities, and alerts — all from
    real database data.
    """

    def __init__(self, db: Session):
        self.db = db

    # ======================================================================
    # A.  PROFITABILITY KPIs
    # ======================================================================

    def summary(self, days: int = None) -> dict:
        """Top-level profitability KPIs for the dashboard header."""
        since = self._since(days)

        # --- Sales aggregates ---
        sales_q = self.db.query(
            func.sum(Sale.total_amount).label("total_revenue"),
            func.sum(Sale.quantity).label("total_units"),
            func.count(func.distinct(Sale.product_id)).label("products_with_sales"),
        )
        if since:
            sales_q = sales_q.filter(Sale.sale_date >= since)
        row = sales_q.one()
        total_revenue = _safe_div(row.total_revenue, 1, 0)
        total_units = int(row.total_units or 0)

        # --- Cost from product cost_price × units sold ---
        cost_q = self.db.query(
            func.sum(Sale.quantity * Product.cost_price).label("total_cost"),
        ).join(Product, Product.id == Sale.product_id)
        if since:
            cost_q = cost_q.filter(Sale.sale_date >= since)
        total_cost = _safe_div(cost_q.scalar(), 1, 0)

        gross_profit = total_revenue - total_cost
        profit_margin = _safe_div(gross_profit, total_revenue, 0) * 100

        # --- Per-product metrics ---
        avg_selling_price = _safe_div(total_revenue, total_units, 0)
        products_with_sales = int(row.products_with_sales or 0)
        avg_profit_per_product = _safe_div(gross_profit, max(products_with_sales, 1), 0)

        # --- Best / lowest profitability products ---
        best, lowest = self._best_and_lowest_products(since)

        return {
            "total_revenue": _round(total_revenue),
            "total_cost": _round(total_cost),
            "gross_profit": _round(gross_profit),
            "profit_margin": _round(profit_margin),
            "average_selling_price": _round(avg_selling_price),
            "average_profit_per_product": _round(avg_profit_per_product),
            "total_units_sold": total_units,
            "products_with_sales": products_with_sales,
            "products_analyzed": products_with_sales,
            "best_product": best,
            "lowest_product": lowest,
            "period_days": days,
        }

    # ======================================================================
    # B.  PROFITABILITY TRENDS
    # ======================================================================

    def trends(self, days: int = None) -> dict:
        """Daily profitability trend for charts."""
        since = self._since(days) or (datetime.utcnow() - timedelta(days=180))

        # Daily revenue and units from sales
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

        # Daily cost: join with product to get cost_price
        daily_cost_rows = (
            self.db.query(
                func.date(Sale.sale_date).label("date"),
                func.sum(Sale.quantity * Product.cost_price).label("cost"),
            )
            .join(Product, Product.id == Sale.product_id)
            .filter(Sale.sale_date >= since)
            .group_by(func.date(Sale.sale_date))
            .order_by(func.date(Sale.sale_date))
            .all()
        )
        cost_map = {str(r.date): r.cost for r in daily_cost_rows}

        trend_points = []
        for r in daily_sales:
            d = str(r.date)
            rev = float(r.revenue or 0)
            cost = float(cost_map.get(d, 0) or 0)
            profit = rev - cost
            margin = _safe_div(profit, rev, 0) * 100
            trend_points.append({
                "date": d,
                "revenue": _round(rev),
                "cost": _round(cost),
                "profit": _round(profit),
                "margin": _round(margin),
                "units": int(r.units or 0),
            })

        # Margin trend (subset for chart)
        margin_trend = [
            {"date": p["date"], "margin": p["margin"]}
            for p in trend_points
        ]

        return {
            "daily": trend_points,
            "margin_trend": margin_trend,
            "point_count": len(trend_points),
        }

    # ======================================================================
    # C.  PRODUCT PROFITABILITY TABLE
    # ======================================================================

    def products(self, days: int = None, search: str = None,
                 sort_by: str = "profit", sort_order: str = "desc",
                 skip: int = 0, limit: int = 50) -> dict:
        """Per-product profitability table with sorting and search."""
        since = self._since(days)

        # Build per-product aggregates from sales
        agg_q = (
            self.db.query(
                Sale.product_id,
                func.sum(Sale.quantity).label("units_sold"),
                func.sum(Sale.total_amount).label("revenue"),
            )
        )
        if since:
            agg_q = agg_q.filter(Sale.sale_date >= since)
        agg_q = agg_q.group_by(Sale.product_id)
        agg_rows = agg_q.all()
        agg_map = {
            r.product_id: {"units_sold": int(r.units_sold or 0), "revenue": float(r.revenue or 0)}
            for r in agg_rows
        }

        # All active products
        products_q = self.db.query(Product).filter(Product.status == "active")
        if search:
            tokens = [t.strip() for t in search.split() if t.strip()]
            from sqlalchemy import or_
            for token in tokens:
                tp = f"%{token}%"
                products_q = products_q.filter(or_(
                    Product.name.ilike(tp),
                    Product.sku.ilike(tp),
                    Product.category.ilike(tp),
                    Product.brand.ilike(tp),
                ))

        all_products = products_q.all()

        rows = []
        for p in all_products:
            agg = agg_map.get(p.id, {"units_sold": 0, "revenue": 0})
            units = agg["units_sold"]
            revenue = agg["revenue"]
            cost_price = p.cost_price or 0
            current_price = p.current_price or 0
            cost = cost_price * units
            profit = revenue - cost
            margin = _safe_div(profit, revenue, 0) * 100
            status = self._profitability_status(margin)

            rows.append({
                "product_id": p.id,
                "name": p.name,
                "sku": p.sku,
                "category": p.category or "Uncategorized",
                "brand": p.brand or "",
                "units_sold": units,
                "selling_price": _round(current_price),
                "cost_price": _round(cost_price),
                "revenue": _round(revenue),
                "cost": _round(cost),
                "profit": _round(profit),
                "margin_pct": _round(margin),
                "status": status,
            })

        # Sort
        sort_key_map = {
            "revenue": lambda r: r["revenue"],
            "profit": lambda r: r["profit"],
            "margin": lambda r: r["margin_pct"],
            "units": lambda r: r["units_sold"],
            "name": lambda r: r["name"].lower(),
        }
        key_fn = sort_key_map.get(sort_by, sort_key_map["profit"])
        rows.sort(key=key_fn, reverse=(sort_order == "desc"))

        total = len(rows)
        paginated = rows[skip:skip + limit]

        return {
            "items": paginated,
            "total": total,
            "skip": skip,
            "limit": limit,
        }

    # ======================================================================
    # D.  PROFITABILITY BY CATEGORY
    # ======================================================================

    def categories(self, days: int = None) -> list:
        """Category-level profitability breakdown."""
        since = self._since(days)

        rows = (
            self.db.query(
                Product.category,
                func.sum(Sale.quantity).label("units"),
                func.sum(Sale.total_amount).label("revenue"),
                func.sum(Sale.quantity * Product.cost_price).label("cost"),
            )
            .join(Product, Product.id == Sale.product_id)
            .filter(Product.status == "active")
        )
        if since:
            rows = rows.filter(Sale.sale_date >= since)
        rows = rows.group_by(Product.category).all()

        categories = []
        for r in rows:
            rev = float(r.revenue or 0)
            cost = float(r.cost or 0)
            profit = rev - cost
            margin = _safe_div(profit, rev, 0) * 100
            categories.append({
                "category": r.category or "Uncategorized",
                "units_sold": int(r.units or 0),
                "revenue": _round(rev),
                "cost": _round(cost),
                "profit": _round(profit),
                "margin_pct": _round(margin),
            })
        categories.sort(key=lambda c: c["profit"], reverse=True)
        return categories

    # ======================================================================
    # E.  AI PRICING PROFITABILITY IMPACT
    # ======================================================================

    def ai_impact(self, days: int = None, top_n: int = 20) -> list:
        """For products with AI predictions, show current vs projected profit."""
        from app.services.ml_service import PricingMLService
        from app.services.training_service import _sales_aggregates

        since = self._since(days)

        # Pre-compute aggregates once
        aggregates = _sales_aggregates(self.db)

        # Get products with sales
        products_with_sales = set()
        sales_q = self.db.query(func.distinct(Sale.product_id))
        if since:
            sales_q = sales_q.filter(Sale.sale_date >= since)
        for (pid,) in sales_q.all():
            products_with_sales.add(pid)

        ml = PricingMLService(self.db)
        model, feature_cols, run = ml.training.load_model()
        if model is None or not run:
            return []

        # Evaluate AI impact for products with sales
        results = []
        products = self.db.query(Product).filter(
            Product.status == "active",
            Product.id.in_(list(products_with_sales)[:100]),
        ).all()

        for p in products:
            try:
                pred = ml.predict_product(
                    p.id, include_forecast=False,
                    aggregates=aggregates,
                    model=model, feature_cols=feature_cols, run=run,
                )
                if pred.get("insufficient_data"):
                    continue

                agg = aggregates.get(p.id, {})
                avg_daily = max(agg.get("avg_daily_units", 0), 1)
                units_30d = avg_daily * 30

                current_price = p.current_price or 0
                cost_price = p.cost_price or 0
                ai_price = pred.get("suggested_price", current_price)

                current_profit = (current_price - cost_price) * units_30d
                projected_profit = (ai_price - cost_price) * units_30d
                profit_change = projected_profit - current_profit

                current_margin = _safe_div(current_price - cost_price, current_price, 0) * 100
                projected_margin = _safe_div(ai_price - cost_price, ai_price, 0) * 100

                results.append({
                    "product_id": p.id,
                    "name": p.name,
                    "category": p.category or "Uncategorized",
                    "current_price": _round(current_price),
                    "ai_price": _round(ai_price),
                    "cost_price": _round(cost_price),
                    "current_profit_30d": _round(current_profit),
                    "projected_profit_30d": _round(projected_profit),
                    "profit_change": _round(profit_change),
                    "current_margin": _round(current_margin),
                    "projected_margin": _round(projected_margin),
                    "confidence": pred.get("confidence_score", 0),
                    "units_30d": _round(units_30d),
                })
            except Exception:
                continue

        # Sort by profit change (biggest improvement first)
        results.sort(key=lambda r: r["profit_change"], reverse=True)
        return results[:top_n]

    # ======================================================================
    # F.  PROFITABILITY OPPORTUNITIES & ALERTS
    # ======================================================================

    def opportunities(self, days: int = None) -> dict:
        """Data-driven profitability insights and alerts."""
        since = self._since(days)

        # Get per-product profitability
        product_data = self._per_product_profitability(since)
        if not product_data:
            return {"insights": [], "alerts": []}

        insights = []
        alerts = []

        # --- Products with high sales but low margins ---
        high_sales_low_margin = [
            p for p in product_data
            if p["units_sold"] > 50 and 0 < p["margin_pct"] < 5
        ]
        if high_sales_low_margin:
            top = sorted(high_sales_low_margin, key=lambda x: x["units_sold"], reverse=True)[:3]
            insights.append({
                "type": "opportunity",
                "title": "High Volume, Low Margin",
                "text": f"{len(high_sales_low_margin)} products have high sales but margins below 5%. "
                        f"Top: {top[0]['name']} ({top[0]['margin_pct']:.1f}% margin, {top[0]['units_sold']} units).",
                "severity": "warning",
            })

        # --- Products with high margins but low sales ---
        high_margin_low_sales = [
            p for p in product_data
            if p["margin_pct"] > 40 and 0 < p["units_sold"] < 10
        ]
        if high_margin_low_sales:
            top = sorted(high_margin_low_sales, key=lambda x: x["margin_pct"], reverse=True)[:3]
            insights.append({
                "type": "opportunity",
                "title": "High Margin, Low Volume",
                "text": f"{len(high_margin_low_sales)} products have strong margins but low sales volume. "
                        f"Consider marketing: {top[0]['name']} ({top[0]['margin_pct']:.1f}% margin, {top[0]['units_sold']} units).",
                "severity": "info",
            })

        # --- Loss-making products ---
        loss_products = [p for p in product_data if p["margin_pct"] < 0]
        if loss_products:
            top = sorted(loss_products, key=lambda x: x["margin_pct"])[:3]
            alerts.append({
                "type": "alert",
                "title": "Loss-Making Products",
                "text": f"{len(loss_products)} products are selling below cost. "
                        f"Worst: {top[0]['name']} ({top[0]['margin_pct']:.1f}% margin).",
                "severity": "critical",
            })

        # --- Low margin products (0-5%) ---
        low_margin = [p for p in product_data if 0 <= p["margin_pct"] < 5]
        if low_margin and not loss_products:
            alerts.append({
                "type": "alert",
                "title": "Low Margin Warning",
                "text": f"{len(low_margin)} products have margins below 5%. "
                        f"Review pricing strategy to avoid potential losses.",
                "severity": "warning",
            })

        # --- Top profitable category ---
        cat_data = self.categories(days)
        if cat_data:
            best_cat = cat_data[0]
            insights.append({
                "type": "insight",
                "title": "Top Category by Profit",
                "text": f"{best_cat['category']} generates ${best_cat['profit']:.0f} profit "
                        f"at {best_cat['margin_pct']:.1f}% margin from {best_cat['units_sold']} units.",
                "severity": "success",
            })

        # --- Revenue concentration risk ---
        total_revenue = sum(p["revenue"] for p in product_data)
        if total_revenue > 0:
            top5_revenue = sum(sorted([p["revenue"] for p in product_data], reverse=True)[:5])
            concentration = (top5_revenue / total_revenue) * 100
            if concentration > 60:
                alerts.append({
                    "type": "alert",
                    "title": "Revenue Concentration Risk",
                    "text": f"Top 5 products account for {concentration:.0f}% of total revenue. "
                            f"Diversify to reduce dependency on a few products.",
                    "severity": "warning",
                })

        # --- AI pricing impact ---
        ai_data = self.ai_impact(days, top_n=50)
        profitable_improvements = [a for a in ai_data if a["profit_change"] > 10]
        if profitable_improvements:
            total_uplift = sum(a["profit_change"] for a in profitable_improvements)
            insights.append({
                "type": "opportunity",
                "title": "AI Pricing Profit Opportunity",
                "text": f"{len(profitable_improvements)} products could gain a combined "
                        f"${total_uplift:,.0f}/month by adopting AI-recommended prices.",
                "severity": "success",
            })

        return {"insights": insights, "alerts": alerts}

    # ======================================================================
    # INTERNAL HELPERS
    # ======================================================================

    def _since(self, days=None):
        if days and days > 0:
            return datetime.utcnow() - timedelta(days=days)
        return None

    def _per_product_profitability(self, since=None) -> list:
        agg_q = (
            self.db.query(
                Sale.product_id,
                func.sum(Sale.quantity).label("units"),
                func.sum(Sale.total_amount).label("revenue"),
            )
        )
        if since:
            agg_q = agg_q.filter(Sale.sale_date >= since)
        agg_rows = agg_q.group_by(Sale.product_id).all()
        agg_map = {r.product_id: {"units": int(r.units or 0), "revenue": float(r.revenue or 0)} for r in agg_rows}

        products = self.db.query(Product).filter(Product.status == "active").all()
        rows = []
        for p in products:
            agg = agg_map.get(p.id, {"units": 0, "revenue": 0})
            cost = (p.cost_price or 0) * agg["units"]
            profit = agg["revenue"] - cost
            margin = _safe_div(profit, agg["revenue"], 0) * 100
            rows.append({
                "product_id": p.id,
                "name": p.name,
                "category": p.category or "Uncategorized",
                "units_sold": agg["units"],
                "revenue": agg["revenue"],
                "cost": cost,
                "profit": profit,
                "margin_pct": margin,
            })
        return rows

    def _best_and_lowest_products(self, since=None):
        rows = self._per_product_profitability(since)
        rows_with_sales = [r for r in rows if r["units_sold"] > 0]
        if not rows_with_sales:
            return None, None

        best = max(rows_with_sales, key=lambda r: r["profit"])
        lowest = min(rows_with_sales, key=lambda r: r["profit"])
        return (
            {
                "name": best["name"],
                "product_id": best["product_id"],
                "profit": _round(best["profit"]),
                "margin_pct": _round(best["margin_pct"]),
                "revenue": _round(best["revenue"]),
            },
            {
                "name": lowest["name"],
                "product_id": lowest["product_id"],
                "profit": _round(lowest["profit"]),
                "margin_pct": _round(lowest["margin_pct"]),
                "revenue": _round(lowest["revenue"]),
            },
        )

    @staticmethod
    def _profitability_status(margin: float) -> str:
        """Classify profitability from a computed margin (not hardcoded)."""
        if margin < 0:
            return "Loss"
        if margin < 5:
            return "Low Profitability"
        if margin < 20:
            return "Moderate Profitability"
        return "High Profitability"
