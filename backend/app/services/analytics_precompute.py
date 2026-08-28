"""
PricePilot AI - Analytics Precomputation Service
=================================================
Background computation engine that precomputes and caches expensive
analytics so Executive BI reads are fast (<500ms).

Architecture:
  DATA → Background Processing → Persisted Cache → Fast Dashboard

Cache Keys:
  - market_position: Full catalog market position analysis
  - demand_signals: Demand trend analysis for all products
  - ai_predictions: Cached ML predictions for all products
  - pricing_summary: Pricing strategy summary
  - executive_kpis: Top-level KPIs
"""

import logging
import time
import json
from datetime import datetime, timedelta

import numpy as np
from sqlalchemy import func, text
from sqlalchemy.orm import Session

from app.models.product import Product
from app.models.sales import Sale
from app.models.analytics_cache import AnalyticsCache

logger = logging.getLogger(__name__)

# Cache TTLs
MARKET_TTL_HOURS = 4
DEMAND_TTL_HOURS = 4
AI_PREDICTION_TTL_HOURS = 6
PRICING_TTL_HOURS = 4
KPI_TTL_HOURS = 1


def _safe_div(a, b, default=0.0):
    if b is None or b == 0:
        return default
    return a / b


def _round(v, d=2):
    if v is None:
        return 0.0
    try:
        if not np.isfinite(v):
            return 0.0
    except Exception:
        pass
    return round(float(v), d)


class AnalyticsPrecomputeService:
    """Precompute and cache analytics for fast executive BI reads."""

    def __init__(self, db: Session):
        self.db = db

    # =====================================================================
    # CACHE READ/WRITE
    # =====================================================================

    def get_cached(self, key: str) -> dict | None:
        """Read a cached analytics entry if still valid."""
        entry = self.db.query(AnalyticsCache).filter(
            AnalyticsCache.cache_key == key,
            AnalyticsCache.status == "READY",
        ).first()

        if not entry:
            return None

        # Check if expired
        if entry.expires_at and entry.expires_at.replace(tzinfo=None) < datetime.utcnow():
            return None

        return {
            "data": entry.data,
            "calculated_at": entry.calculated_at.isoformat() if entry.calculated_at else None,
            "product_count": entry.product_count,
            "compute_time_ms": entry.compute_time_ms,
            "model_version": entry.model_version,
            "status": entry.status,
        }

    def set_cached(self, key: str, data: dict, ttl_hours: float,
                   product_count: int = 0, compute_time_ms: float = 0,
                   model_version: str = None):
        """Write or update a cached analytics entry."""
        now = datetime.utcnow()
        expires = now + timedelta(hours=ttl_hours)

        entry = self.db.query(AnalyticsCache).filter(
            AnalyticsCache.cache_key == key
        ).first()

        if entry:
            entry.data = data
            entry.status = "READY"
            entry.calculated_at = now
            entry.expires_at = expires
            entry.product_count = product_count
            entry.compute_time_ms = compute_time_ms
            entry.model_version = model_version
            entry.updated_at = now
            entry.error_message = None
        else:
            entry = AnalyticsCache(
                cache_key=key,
                data=data,
                status="READY",
                calculated_at=now,
                expires_at=expires,
                product_count=product_count,
                compute_time_ms=compute_time_ms,
                model_version=model_version,
            )
            self.db.add(entry)

        self.db.commit()

    def set_status(self, key: str, status: str, error: str = None):
        """Update cache status (e.g. PROCESSING, UNAVAILABLE)."""
        entry = self.db.query(AnalyticsCache).filter(
            AnalyticsCache.cache_key == key
        ).first()
        if entry:
            entry.status = status
            entry.error_message = error
            entry.updated_at = datetime.utcnow()
            self.db.commit()

    # =====================================================================
    # PRECOMPUTE: MARKET POSITION
    # =====================================================================

    def precompute_market_position(self) -> dict:
        """Precompute market position for the entire catalog."""
        start = time.time()

        try:
            from app.services.competitor_service import CompetitorService
            cs = CompetitorService(self.db)

            products = self.db.query(Product).filter(Product.status == "active").all()
            total = len(products)

            below = 0
            above = 0
            within = 0
            no_data = 0

            # Process in batches to manage memory
            for p in products:
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

            elapsed = (time.time() - start) * 1000

            data = {
                "total_products": total,
                "below_market": below,
                "above_market": above,
                "within_range": within,
                "insufficient_data": no_data,
                "scanned": total,
                "scan_complete": True,
                "data_provenance": "reference",  # competitor prices are reference/catalog data
                "note": f"Full catalog analyzed using competitor product matching. {no_data} products had insufficient competitor data.",
                "scan_type": "competitor_analysis",
            }

            self.set_cached("market_position", data, MARKET_TTL_HOURS,
                          product_count=total, compute_time_ms=elapsed)

            logger.info("Market position precomputed: %d products in %.1fs", total, elapsed / 1000)
            return data

        except Exception as e:
            elapsed = (time.time() - start) * 1000
            self.set_cached("market_position", {
                "total_products": 0, "below_market": 0, "above_market": 0,
                "within_range": 0, "insufficient_data": 0, "scan_complete": False,
            }, MARKET_TTL_HOURS, error=str(e))
            logger.error("Market position precompute failed: %s", e)
            return {}

    # =====================================================================
    # PRECOMPUTE: DEMAND SIGNALS
    # =====================================================================

    def precompute_demand_signals(self) -> dict:
        """Precompute demand signals for all products with sufficient data."""
        start = time.time()

        try:
            from app.services.forecast_service import ForecastService
            fs = ForecastService(self.db)

            products = self.db.query(Product).filter(Product.status == "active").all()
            total = len(products)

            increasing = []
            decreasing = []
            stable = []
            insufficient = 0

            for p in products:
                try:
                    signal = fs.get_demand_signal(p.id)
                    if signal and signal.get("trend") != "unavailable":
                        trend = signal.get("trend", "stable")
                        growth = signal.get("growth_pct", 0)
                        entry = {
                            "product_id": p.id,
                            "name": p.name,
                            "category": p.category or "",
                            "trend": trend,
                            "growth_pct": _round(growth),
                        }

                        if trend == "up" and growth > 3:
                            increasing.append(entry)
                        elif trend == "down" and growth < -3:
                            decreasing.append(entry)
                        else:
                            stable.append(entry)
                    else:
                        insufficient += 1
                except Exception:
                    insufficient += 1

            increasing.sort(key=lambda x: x["growth_pct"], reverse=True)
            decreasing.sort(key=lambda x: x["growth_pct"])

            elapsed = (time.time() - start) * 1000

            data = {
                "total_products": total,
                "increasing_count": len(increasing),
                "decreasing_count": len(decreasing),
                "stable_count": len(stable),
                "insufficient_data": insufficient,
                "increasing_top10": increasing[:10],
                "decreasing_top10": decreasing[:10],
                "scan_complete": True,
            }

            self.set_cached("demand_signals", data, DEMAND_TTL_HOURS,
                          product_count=total, compute_time_ms=elapsed)

            logger.info("Demand signals precomputed: %d products in %.1fs", total, elapsed / 1000)
            return data

        except Exception as e:
            elapsed = (time.time() - start) * 1000
            self.set_cached("demand_signals", {
                "total_products": 0, "increasing_count": 0, "decreasing_count": 0,
                "stable_count": 0, "insufficient_data": 0,
                "increasing_top10": [], "decreasing_top10": [], "scan_complete": False,
            }, DEMAND_TTL_HOURS, error=str(e))
            logger.error("Demand signals precompute failed: %s", e)
            return {}

    # =====================================================================
    # PRECOMPUTE: AI PREDICTIONS (batch)
    # =====================================================================

    def precompute_ai_predictions(self) -> dict:
        """Precompute ML predictions for all products using the saved model."""
        start = time.time()

        try:
            from app.services.ml_service import PricingMLService
            from app.services.training_service import _sales_aggregates

            ml = PricingMLService(self.db)
            model, feature_cols, run = ml.training.load_model()

            if model is None or not run:
                self.set_status("ai_predictions", "UNAVAILABLE", "No trained model")
                return {"predictions": [], "model_version": None, "status": "unavailable"}

            # Pre-compute aggregates once
            aggregates = _sales_aggregates(self.db)
            training_frame = self.ml_training_frame_safe(ml)

            products = self.db.query(Product).filter(Product.status == "active").all()
            total = len(products)

            predictions = []
            for p in products:
                try:
                    pred = ml.predict_product(
                        p.id, aggregates=aggregates,
                        training_frame=training_frame,
                        model=model, feature_cols=feature_cols, run=run,
                    )
                    if not pred.get("insufficient_data"):
                        predictions.append({
                            "product_id": p.id,
                            "name": p.name,
                            "category": p.category or "",
                            "current_price": _round(pred.get("current_price", 0)),
                            "suggested_price": _round(pred.get("suggested_price", 0)),
                            "confidence": _round(pred.get("confidence_score", 0)),
                            "price_change_pct": _round(pred.get("expected_revenue_change", 0)),
                            "expected_profit": _round(pred.get("expected_profit", 0)),
                            "expected_revenue": _round(pred.get("expected_revenue", 0)),
                        })
                except Exception:
                    continue

            elapsed = (time.time() - start) * 1000
            model_version = f"run_{run.id}" if run else None

            data = {
                "predictions": predictions,
                "total_predicted": len(predictions),
                "total_products": total,
                "model_version": model_version,
                "best_model": run.best_model,
                "accuracy": run.accuracy,
            }

            self.set_cached("ai_predictions", data, AI_PREDICTION_TTL_HOURS,
                          product_count=total, compute_time_ms=elapsed,
                          model_version=model_version)

            logger.info("AI predictions precomputed: %d/%d in %.1fs",
                       len(predictions), total, elapsed / 1000)
            return data

        except Exception as e:
            elapsed = (time.time() - start) * 1000
            self.set_status("ai_predictions", "UNAVAILABLE", str(e))
            logger.error("AI predictions precompute failed: %s", e)
            return {"predictions": [], "status": "unavailable"}

    def ml_training_frame_safe(self, ml) -> None:
        """Try to build training frame, return None on failure."""
        try:
            return ml.training.build_training_frame()
        except Exception:
            return None

    # =====================================================================
    # PRECOMPUTE: PRICING SUMMARY
    # =====================================================================

    def precompute_pricing_summary(self) -> dict:
        """Precompute pricing summary from ML predictions cache or direct analysis."""
        start = time.time()

        try:
            # Try to use cached AI predictions first
            cached = self.get_cached("ai_predictions")
            if cached and cached.get("data", {}).get("predictions"):
                preds = cached["data"]["predictions"]
                increases = sum(1 for p in preds if p.get("suggested_price", 0) > p.get("current_price", 0) * 1.02)
                decreases = sum(1 for p in preds if p.get("suggested_price", 0) < p.get("current_price", 0) * 0.98)
                maintain = len(preds) - increases - decreases

                total = self.db.query(Product).filter(Product.status == "active").count()

                # Calculate potential uplift
                total_uplift = sum(
                    p.get("expected_profit", 0)
                    for p in preds
                    if p.get("price_change_pct", 0) > 0
                )

                elapsed = (time.time() - start) * 1000

                data = {
                    "total_recommendations": total,
                    "price_increase_opportunities": increases,
                    "price_reduction_opportunities": decreases,
                    "maintain_price": maintain,
                    "high_priority_actions": increases,  # increases are high priority
                    "total_potential_profit_uplift": _round(total_uplift),
                }

                self.set_cached("pricing_summary", data, PRICING_TTL_HOURS,
                              product_count=total, compute_time_ms=elapsed)
                return data

            # Fallback: direct margin analysis
            from sqlalchemy import func as sqlfunc
            low_margin = (
                self.db.query(sqlfunc.count(Product.id))
                .filter(
                    Product.status == "active",
                    Product.cost_price > 0,
                    Product.current_price > 0,
                    ((Product.current_price - Product.cost_price) / Product.current_price * 100) < 22,
                ).scalar() or 0
            )
            total = self.db.query(Product).filter(Product.status == "active").count()

            elapsed = (time.time() - start) * 1000

            data = {
                "total_recommendations": total,
                "price_increase_opportunities": low_margin,
                "price_reduction_opportunities": 0,
                "maintain_price": total - low_margin,
                "high_priority_actions": low_margin,
                "total_potential_profit_uplift": 0,
                "source": "margin_analysis",
            }

            self.set_cached("pricing_summary", data, PRICING_TTL_HOURS,
                          product_count=total, compute_time_ms=elapsed)
            return data

        except Exception as e:
            elapsed = (time.time() - start) * 1000
            self.set_cached("pricing_summary", {
                "total_recommendations": 0, "price_increase_opportunities": 0,
                "price_reduction_opportunities": 0, "maintain_price": 0,
                "high_priority_actions": 0, "total_potential_profit_uplift": 0,
            }, PRICING_TTL_HOURS, error=str(e))
            logger.error("Pricing summary precompute failed: %s", e)
            return {}

    # =====================================================================
    # PRECOMPUTE: EXECUTIVE KPIs
    # =====================================================================

    def precompute_executive_kpis(self, days: int = None) -> dict:
        """Precompute executive KPIs from sales + products.

        Falls back to the ProfitabilityService if direct SQL queries fail.
        """
        start = time.time()

        try:
            since = None
            if days and days > 0:
                since = datetime.utcnow() - timedelta(days=days)

            # Revenue
            rev_q = self.db.query(
                func.sum(Sale.total_amount).label("total_revenue"),
                func.sum(Sale.quantity).label("total_units"),
                func.count(func.distinct(Sale.product_id)).label("products_with_sales"),
            )
            if since:
                rev_q = rev_q.filter(Sale.sale_date >= since)
            rev_row = rev_q.one()
            total_revenue = float(rev_row.total_revenue or 0)
            total_units = int(rev_row.total_units or 0)

            # Cost
            cost_q = self.db.query(
                func.sum(Sale.quantity * Product.cost_price).label("total_cost"),
            ).join(Product, Product.id == Sale.product_id)
            if since:
                cost_q = cost_q.filter(Sale.sale_date >= since)
            total_cost = float(cost_q.scalar() or 0)

            gross_profit = total_revenue - total_cost
            profit_margin = _safe_div(gross_profit, total_revenue, 0) * 100

            # Best/lowest product (wrapped in try/except so KPIs aren't blocked)
            best_product = None
            try:
                best_row = (
                    self.db.query(
                        Product.id, Product.name,
                        func.sum(Sale.total_amount).label("revenue"),
                        func.sum(Sale.quantity).label("units"),
                    )
                    .join(Product, Product.id == Sale.product_id)
                )
                if since:
                    best_row = best_row.filter(Sale.sale_date >= since)
                best_row = best_row.group_by(Product.id).order_by(
                    func.sum(Sale.total_amount).desc()
                ).first()

                if best_row:
                    cost_for_best = float(self.db.query(
                        func.sum(Sale.quantity * Product.cost_price)
                    ).join(Product, Product.id == Sale.product_id)
                     .filter(Product.id == best_row.id, *( [Sale.sale_date >= since] if since else [])).scalar() or 0)
                    best_revenue = float(best_row.revenue or 0)
                    best_profit = best_revenue - cost_for_best
                    best_margin = _safe_div(best_profit, best_revenue, 0) * 100
                    best_product = {
                        "name": best_row.name, "product_id": best_row.id,
                        "profit": _round(best_profit), "margin_pct": _round(best_margin),
                        "revenue": _round(best_revenue),
                    }
            except Exception as e:
                logger.warning("Best product query failed: %s", e)

            elapsed = (time.time() - start) * 1000

            data = {
                "total_revenue": _round(total_revenue),
                "total_profit": _round(gross_profit),
                "profit_margin": _round(profit_margin),
                "total_units_sold": total_units,
                "products_analyzed": int(rev_row.products_with_sales or 0),
                "average_selling_price": _round(_safe_div(total_revenue, total_units, 0)),
                "best_product": best_product,
                "period_days": days,
            }

            self.set_cached("executive_kpis", data, KPI_TTL_HOURS,
                          product_count=int(rev_row.products_with_sales or 0),
                          compute_time_ms=elapsed)
            return data

        except Exception as e:
            elapsed = (time.time() - start) * 1000
            logger.error("Executive KPIs precompute failed: %s", e)
            # Fallback: use the ProfitabilityService which is proven to work
            try:
                from app.services.profitability_service import ProfitabilityService
                prof_svc = ProfitabilityService(self.db)
                prof_summary = prof_svc.summary(days)
                data = {
                    "total_revenue": prof_summary.get("total_revenue", 0),
                    "total_profit": prof_summary.get("gross_profit", 0),
                    "profit_margin": prof_summary.get("profit_margin", 0),
                    "total_units_sold": prof_summary.get("total_units_sold", 0),
                    "products_analyzed": prof_summary.get("products_with_sales", 0),
                    "average_selling_price": prof_summary.get("average_selling_price", 0),
                    "best_product": prof_summary.get("best_product"),
                    "period_days": days,
                }
                self.set_cached("executive_kpis", data, KPI_TTL_HOURS,
                              product_count=prof_summary.get("products_with_sales", 0),
                              compute_time_ms=elapsed)
                return data
            except Exception as e2:
                logger.error("Fallback KPI computation also failed: %s", e2)
                return {}

    # =====================================================================
    # FULL PRECOMPUTE (all analytics)
    # =====================================================================

    def precompute_all(self, days: int = None) -> dict:
        """Run all precomputation tasks and return status."""
        results = {}

        # KPIs are fast — always run
        results["kpi"] = self.precompute_executive_kpis(days)

        # Market position is expensive — run in background
        try:
            results["market"] = self.precompute_market_position()
        except Exception as e:
            results["market"] = {"error": str(e)}

        # Demand signals — run in background
        try:
            results["demand"] = self.precompute_demand_signals()
        except Exception as e:
            results["demand"] = {"error": str(e)}

        # AI predictions — most expensive, run in background
        try:
            results["ai_predictions"] = self.precompute_ai_predictions()
        except Exception as e:
            results["ai_predictions"] = {"error": str(e)}

        # Pricing summary — depends on AI predictions
        try:
            results["pricing"] = self.precompute_pricing_summary()
        except Exception as e:
            results["pricing"] = {"error": str(e)}

        return results

    # =====================================================================
    # INVALIDATE (when data changes)
    # =====================================================================

    def invalidate_all(self):
        """Mark all caches as stale (e.g. after dataset import or retrain)."""
        self.db.query(AnalyticsCache).update({AnalyticsCache.status: "STALE"})
        self.db.commit()

    def invalidate_key(self, key: str):
        """Mark a specific cache key as stale."""
        entry = self.db.query(AnalyticsCache).filter(
            AnalyticsCache.cache_key == key
        ).first()
        if entry:
            entry.status = "STALE"
            self.db.commit()

    # =====================================================================
    # STATUS
    # =====================================================================

    def cache_status(self) -> dict:
        """Get status of all cache entries."""
        entries = self.db.query(AnalyticsCache).all()
        return {
            e.cache_key: {
                "status": e.status,
                "calculated_at": e.calculated_at.isoformat() if e.calculated_at else None,
                "expires_at": e.expires_at.isoformat() if e.expires_at else None,
                "product_count": e.product_count,
                "compute_time_ms": e.compute_time_ms,
            }
            for e in entries
        }
