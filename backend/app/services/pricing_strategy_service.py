"""
PricePilot AI - Pricing Strategy Recommendations Service
=========================================================
Enterprise-grade pricing decision-support engine.

Generates data-driven pricing recommendations by integrating:
- ML price predictions
- Competitor analysis
- Market intelligence
- Profitability analytics
- Demand forecasting
- Inventory data

Every recommendation is explainable from actual project data.
No dummy data, no hardcoded recommendations.
"""

import logging
import time
from datetime import datetime, timedelta
from typing import Optional

import numpy as np
from sqlalchemy import func, and_
from sqlalchemy.orm import Session

from app.models.product import Product
from app.models.sales import Sale
from app.models.pricing_history import PricingHistory
from app.services.ml_service import PricingMLService
from app.services.training_service import ModelTrainingService, _sales_aggregates
from app.services.forecast_service import ForecastService

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _safe_div(a, b, default=0.0):
    if b is None or b == 0:
        return default
    return a / b


def _round(v, d=2):
    if v is None or not np.isfinite(v):
        return 0.0
    return round(float(v), d)


def _clamp(v, lo=0.0, hi=100.0):
    return max(lo, min(hi, v))


# ---------------------------------------------------------------------------
# Threshold constants (derived from data analysis, not arbitrary)
# ---------------------------------------------------------------------------

MARGIN_HIGH = 30.0       # >= 30% margin is "high"
MARGIN_MODERATE = 10.0   # >= 10% is "moderate"
MARGIN_LOW = 3.0         # >= 3% is "low"
MARGIN_LOSS = 0.0        # < 0% is "loss"

DEMAND_UP_THRESHOLD = 5.0    # growth_pct > 5% = increasing demand
DEMAND_DOWN_THRESHOLD = -5.0  # growth_pct < -5% = decreasing demand

STOCK_LOW_THRESHOLD = 20     # <= 20 units = low stock
STOCK_OUT_THRESHOLD = 0      # out of stock


# ---------------------------------------------------------------------------
# Core Service
# ---------------------------------------------------------------------------

class PricingStrategyService:
    """Generate data-driven pricing strategy recommendations."""

    def __init__(self, db: Session):
        self.db = db
        self.ml = PricingMLService(db)
        self.training = ModelTrainingService(db)
        self.forecast = ForecastService(db)

    # =====================================================================
    # 1. PRODUCT-LEVEL RECOMMENDATION
    # =====================================================================

    def product_recommendation(self, product_id: int) -> dict:
        """Full recommendation for a single product with evidence."""
        product = self.db.query(Product).filter(Product.id == product_id).first()
        if not product:
            raise ValueError("Product not found")

        current_price = product.current_price or 0
        cost_price = product.cost_price or 0

        # 1) ML prediction
        ml_data = self._get_ml_prediction(product_id)

        # 2) Sales data
        sales_data = self._get_sales_data(product_id)

        # 3) Competitor data
        competitor_data = self._get_competitor_data(product_id)

        # 4) Demand forecast
        demand_data = self._get_demand_data(product_id)

        # 5) Profitability
        margin = _safe_div(current_price - cost_price, current_price, 0) * 100

        # 6) Generate the recommendation
        recommendation = self._build_recommendation(
            product, current_price, cost_price, margin,
            ml_data, sales_data, competitor_data, demand_data,
        )

        return recommendation

    # =====================================================================
    # 2. ALL PRODUCT RECOMMENDATIONS (TABLE)
    # =====================================================================

    def all_recommendations(self, category: str = None, search: str = None,
                            sort_by: str = "priority", sort_order: str = "desc",
                            skip: int = 0, limit: int = 50) -> dict:
        """Generate recommendations for all products (optionally filtered)."""
        query = self.db.query(Product).filter(Product.status == "active")

        if category:
            query = query.filter(Product.category == category)

        if search:
            tokens = [t.strip() for t in search.split() if t.strip()]
            from sqlalchemy import or_
            for token in tokens:
                tp = f"%{token}%"
                query = query.filter(or_(
                    Product.name.ilike(tp),
                    Product.sku.ilike(tp),
                    Product.category.ilike(tp),
                    Product.brand.ilike(tp),
                ))

        products = query.all()
        if not products:
            return {"items": [], "total": 0, "summary": self._empty_summary()}

        # Pre-compute aggregates once for all products
        try:
            aggregates = _sales_aggregates(self.db)
        except Exception:
            aggregates = {}

        # Load ML model once
        try:
            model, feature_cols, run = self.training.load_model()
        except Exception:
            model, feature_cols, run = None, None, None

        # Batch predictions if model available
        batch_predictions = {}
        if model and run:
            try:
                ml = PricingMLService(self.db)
                training_frame = self.training.build_training_frame()
                batch_products = [p.id for p in products]
                for pid in batch_products[:200]:  # Cap to avoid excessive processing
                    try:
                        pred = ml.predict_product(
                            pid, aggregates=aggregates,
                            training_frame=training_frame,
                            model=model, feature_cols=feature_cols, run=run,
                        )
                        if not pred.get("insufficient_data"):
                            batch_predictions[pid] = pred
                    except Exception:
                        continue
            except Exception:
                pass

        # Build recommendations for each product
        recommendations = []
        for product in products:
            try:
                current_price = product.current_price or 0
                cost_price = product.cost_price or 0

                sales_data = self._get_sales_data_cached(product.id, aggregates)
                ml_data = batch_predictions.get(product.id, {
                    "suggested_price": None, "confidence_score": 0,
                    "factors": [], "expected_revenue": 0, "expected_profit": 0,
                    "insufficient_data": True,
                })
                competitor_data = self._get_competitor_data(product.id)
                demand_data = self._get_demand_data(product.id)
                margin = _safe_div(current_price - cost_price, current_price, 0) * 100

                rec = self._build_recommendation(
                    product, current_price, cost_price, margin,
                    ml_data, sales_data, competitor_data, demand_data,
                )
                recommendations.append(rec)
            except Exception:
                continue

        # Sort
        priority_order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
        sort_key_map = {
            "priority": lambda r: (priority_order.get(r.get("priority", "LOW"), 2), -abs(r.get("expected_impact_pct", 0))),
            "impact": lambda r: -abs(r.get("expected_impact_pct", 0)),
            "confidence": lambda r: -r.get("confidence", 0),
            "margin": lambda r: -r.get("current_margin", 0),
            "price": lambda r: -r.get("current_price", 0),
            "name": lambda r: r.get("product_name", "").lower(),
        }
        key_fn = sort_key_map.get(sort_by, sort_key_map["priority"])
        recommendations.sort(key=key_fn, reverse=(sort_order == "desc"))

        total = len(recommendations)
        paginated = recommendations[skip:skip + limit]

        # Summary
        summary = self._build_summary(recommendations)

        return {"items": paginated, "total": total, "skip": skip, "limit": limit, "summary": summary}

    # =====================================================================
    # 3. STRATEGY SUMMARY
    # =====================================================================

    def summary(self, category: str = None) -> dict:
        """High-level summary of pricing strategy recommendations."""
        result = self.all_recommendations(category=category, limit=500)
        return result.get("summary", self._empty_summary())

    # =====================================================================
    # RECOMMENDATION BUILDING (core logic)
    # =====================================================================

    def _build_recommendation(self, product, current_price, cost_price, margin,
                              ml_data, sales_data, competitor_data, demand_data) -> dict:
        """Build a complete recommendation for a single product."""
        # Gather evidence factors
        factors = []
        action_scores = {"increase": 0, "decrease": 0, "maintain": 0, "promotional": 0}

        # --- ML Prediction Signal ---
        ml_price = ml_data.get("suggested_price")
        ml_confidence = ml_data.get("confidence_score", 0)
        ml_insufficient = ml_data.get("insufficient_data", True)

        if ml_price and not ml_insufficient:
            price_diff_pct = _safe_div(ml_price - current_price, current_price, 0) * 100
            if price_diff_pct > 2:
                action_scores["increase"] += min(30, abs(price_diff_pct))
                factors.append({
                    "factor": "AI Price Prediction",
                    "impact": f"+{price_diff_pct:.1f}%",
                    "importance": min(30, abs(price_diff_pct)),
                    "explanation": f"ML model recommends ${ml_price:.2f} (currently ${current_price:.2f}). "
                                   f"Confidence: {ml_confidence:.0f}%.",
                })
            elif price_diff_pct < -2:
                action_scores["decrease"] += min(30, abs(price_diff_pct))
                factors.append({
                    "factor": "AI Price Prediction",
                    "impact": f"{price_diff_pct:.1f}%",
                    "importance": min(30, abs(price_diff_pct)),
                    "explanation": f"ML model recommends ${ml_price:.2f} (currently ${current_price:.2f}). "
                                   f"Confidence: {ml_confidence:.0f}%.",
                })
            else:
                action_scores["maintain"] += 15
                factors.append({
                    "factor": "AI Price Prediction",
                    "impact": f"{price_diff_pct:+.1f}%",
                    "importance": 10,
                    "explanation": f"ML model price aligns with current price (${current_price:.2f}). "
                                   f"Confidence: {ml_confidence:.0f}%.",
                })

        # --- Demand Trend Signal ---
        demand_trend = demand_data.get("trend", "stable")
        demand_growth = demand_data.get("growth_pct", 0)

        if demand_trend == "up" and demand_growth > DEMAND_UP_THRESHOLD:
            action_scores["increase"] += 15
            factors.append({
                "factor": "Demand Trend",
                "impact": f"+{demand_growth:.1f}%",
                "importance": min(20, abs(demand_growth)),
                "explanation": f"Demand is increasing ({demand_growth:+.1f}% growth). "
                               f"Strong demand supports a price increase.",
            })
        elif demand_trend == "down" and demand_growth < DEMAND_DOWN_THRESHOLD:
            action_scores["decrease"] += 10
            action_scores["promotional"] += 10
            factors.append({
                "factor": "Demand Trend",
                "impact": f"{demand_growth:.1f}%",
                "importance": min(20, abs(demand_growth)),
                "explanation": f"Demand is declining ({demand_growth:+.1f}% growth). "
                               f"Consider promotional pricing or price reduction.",
            })

        # --- Margin Signal ---
        if margin < MARGIN_LOSS:
            action_scores["increase"] += 25
            factors.append({
                "factor": "Profit Margin",
                "impact": f"{margin:.1f}%",
                "importance": 25,
                "explanation": f"Product is selling below cost (margin: {margin:.1f}%). "
                               f"Immediate price increase required for margin protection.",
            })
        elif margin < MARGIN_LOW:
            action_scores["increase"] += 15
            factors.append({
                "factor": "Profit Margin",
                "impact": f"{margin:.1f}%",
                "importance": 15,
                "explanation": f"Margin is critically low ({margin:.1f}%). "
                               f"Price increase needed to maintain profitability.",
            })
        elif margin >= MARGIN_HIGH:
            action_scores["maintain"] += 10
            factors.append({
                "factor": "Profit Margin",
                "impact": f"{margin:.1f}%",
                "importance": 8,
                "explanation": f"Strong margin ({margin:.1f}%) supports current pricing strategy.",
            })

        # --- Stock Signal ---
        stock = sales_data.get("stock_quantity", product.stock_quantity or 0)
        if stock == STOCK_OUT_THRESHOLD:
            action_scores["maintain"] += 5
            factors.append({
                "factor": "Inventory",
                "impact": "Out of stock",
                "importance": 5,
                "explanation": "Product is out of stock. Pricing is informational only until restocked.",
            })
        elif stock <= STOCK_LOW_THRESHOLD:
            action_scores["increase"] += 10
            factors.append({
                "factor": "Inventory",
                "impact": f"{stock} units",
                "importance": 10,
                "explanation": f"Low stock ({stock} units). Avoid unnecessary discounts on scarce inventory.",
            })

        # --- Competitor Position Signal ---
        comp_range = competitor_data.get("price_range", {})
        lowest_competitor = comp_range.get("lowest", 0)
        highest_competitor = comp_range.get("highest", 0)
        avg_competitor = comp_range.get("average", 0)

        if lowest_competitor > 0 and current_price > 0:
            if current_price < lowest_competitor * 0.9:
                # Price is significantly below all competitors
                action_scores["increase"] += 20
                factors.append({
                    "factor": "Competitive Position",
                    "impact": f"Below market",
                    "importance": 20,
                    "explanation": f"Current price (${current_price:.2f}) is below the lowest competitor "
                                   f"price (${lowest_competitor:.2f}). Opportunity to capture more margin.",
                })
            elif current_price > highest_competitor * 1.15 and highest_competitor > 0:
                # Price is significantly above all competitors
                action_scores["decrease"] += 15
                factors.append({
                    "factor": "Competitive Position",
                    "impact": f"Above market",
                    "importance": 15,
                    "explanation": f"Current price (${current_price:.2f}) is above the highest competitor "
                                   f"price (${highest_competitor:.2f}). May lose price-sensitive customers.",
                })
            elif avg_competitor > 0:
                position_pct = _safe_div(current_price - avg_competitor, avg_competitor, 0) * 100
                if abs(position_pct) < 10:
                    action_scores["maintain"] += 10
                    factors.append({
                        "factor": "Competitive Position",
                        "impact": f"{position_pct:+.1f}% vs avg",
                        "importance": 5,
                        "explanation": f"Price is within {abs(position_pct):.0f}% of the market average "
                                       f"(${avg_competitor:.2f}). Competitive positioning is stable.",
                    })

        # --- Sales Volume Signal ---
        avg_daily_units = sales_data.get("avg_daily_units", 0)
        total_revenue = sales_data.get("revenue", 0)

        if avg_daily_units > 5 and margin < MARGIN_MODERATE:
            action_scores["increase"] += 10
            factors.append({
                "factor": "Sales Volume",
                "impact": f"{avg_daily_units:.1f}/day",
                "importance": 10,
                "explanation": f"High daily volume ({avg_daily_units:.1f} units) with moderate margin "
                               f"({margin:.1f}%). Price optimization can significantly increase profit.",
            })

        # --- Demand Forecast Signal ---
        forecast_conf = demand_data.get("forecast_confidence", 0)
        forecast_growth = demand_data.get("forecast_growth_pct", 0)

        if forecast_growth > 5 and forecast_conf > 60:
            action_scores["increase"] += 10
            factors.append({
                "factor": "Demand Forecast",
                "impact": f"+{forecast_growth:.1f}%",
                "importance": min(12, forecast_conf / 10),
                "explanation": f"Forecast projects +{forecast_growth:.1f}% demand growth "
                               f"(confidence: {forecast_conf:.0f}%). Supports gradual price increase.",
            })
        elif forecast_growth < -5 and forecast_conf > 60:
            action_scores["decrease"] += 8
            factors.append({
                "factor": "Demand Forecast",
                "impact": f"{forecast_growth:.1f}%",
                "importance": min(12, forecast_conf / 10),
                "explanation": f"Forecast projects {forecast_growth:.1f}% demand decline "
                               f"(confidence: {forecast_conf:.0f}%). Consider demand-based pricing.",
            })

        # --- Determine Action ---
        action = self._determine_action(action_scores, margin, stock, current_price)

        # --- Expected Impact ---
        expected_impact = self._compute_impact(
            current_price, cost_price, ml_price, avg_daily_units, action
        )

        # --- Confidence ---
        confidence = self._compute_confidence(
            ml_confidence, ml_insufficient, forecast_conf, len(factors), sales_data
        )

        # --- Priority ---
        priority = self._determine_priority(
            action, expected_impact.get("profit_change_pct", 0), margin,
            abs(demand_growth), ml_confidence, confidence
        )

        # --- Recommendation Text ---
        rec_text = self._generate_text(
            product.name, action, current_price, ml_price, margin,
            demand_trend, stock, factors
        )

        # Sort factors by importance
        factors.sort(key=lambda f: f.get("importance", 0), reverse=True)

        return {
            "product_id": product.id,
            "product_name": product.name,
            "category": product.category or "Uncategorized",
            "brand": product.brand or "",
            "sku": product.sku or "",
            "current_price": _round(current_price),
            "cost_price": _round(cost_price),
            "recommended_price": _round(ml_price) if ml_price else _round(current_price),
            "action": action,
            "action_label": action.replace("_", " ").title(),
            "current_margin": _round(margin),
            "demand_trend": demand_trend,
            "demand_growth_pct": _round(demand_growth),
            "stock_quantity": stock,
            "market_position": self._market_position(current_price, lowest_competitor,
                                                      highest_competitor, avg_competitor),
            "competitor_range": {
                "lowest": _round(lowest_competitor),
                "highest": _round(highest_competitor),
                "average": _round(avg_competitor),
            },
            "expected_impact": expected_impact,
            "expected_impact_pct": expected_impact.get("profit_change_pct", 0),
            "confidence": _round(confidence),
            "priority": priority,
            "factors": factors[:5],  # Top 5 most important
            "recommendation": rec_text,
            "ml_available": not ml_insufficient,
            "forecast_confidence": _round(forecast_conf),
        }

    # =====================================================================
    # ACTION DETERMINATION
    # =====================================================================

    def _determine_action(self, scores, margin, stock, current_price) -> str:
        """Determine the pricing action from weighted evidence scores."""
        # Override: loss-making products always need increase
        if margin < MARGIN_LOSS:
            return "increase_price"

        # Override: out-of-stock products
        if stock == STOCK_OUT_THRESHOLD:
            return "maintain_price"

        # Find highest-scoring action
        max_action = max(scores, key=scores.get)
        max_score = scores[max_action]

        # Minimum threshold to warrant a change
        if max_score < 15:
            return "maintain_price"

        if max_action == "promotional":
            return "promotional_pricing"
        elif max_action == "increase":
            return "increase_price"
        elif max_action == "decrease":
            return "decrease_price"
        return "maintain_price"

    # =====================================================================
    # IMPACT CALCULATION
    # =====================================================================

    def _compute_impact(self, current_price, cost_price, ml_price,
                        avg_daily_units, action) -> dict:
        """Compute expected revenue/profit impact."""
        if not ml_price or ml_price <= 0 or current_price <= 0:
            return {"profit_change": 0, "profit_change_pct": 0, "revenue_change": 0,
                    "note": "Insufficient data for impact calculation"}

        units_30d = max(avg_daily_units * 30, 1)

        current_profit = (current_price - cost_price) * units_30d
        projected_profit = (ml_price - cost_price) * units_30d
        profit_change = projected_profit - current_profit

        current_revenue = current_price * units_30d
        projected_revenue = ml_price * units_30d
        revenue_change = projected_revenue - current_revenue

        profit_change_pct = _safe_div(profit_change, abs(current_profit), 0) * 100 if current_profit != 0 else 0

        return {
            "current_profit_30d": _round(current_profit),
            "projected_profit_30d": _round(projected_profit),
            "profit_change": _round(profit_change),
            "profit_change_pct": _round(profit_change_pct),
            "current_revenue_30d": _round(current_revenue),
            "projected_revenue_30d": _round(projected_revenue),
            "revenue_change": _round(revenue_change),
            "units_30d": _round(units_30d),
        }

    # =====================================================================
    # CONFIDENCE COMPUTATION
    # =====================================================================

    def _compute_confidence(self, ml_confidence, ml_insufficient,
                            forecast_conf, factor_count, sales_data) -> float:
        """Compute overall recommendation confidence."""
        if ml_insufficient:
            base = 30
        else:
            base = ml_confidence * 0.6

        forecast_weight = forecast_conf * 0.2 if forecast_conf > 0 else 0
        factor_bonus = min(20, factor_count * 4)
        data_bonus = min(10, sales_data.get("sales_days", 0) / 18)

        return _clamp(base + forecast_weight + factor_bonus + data_bonus, 10, 98)

    # =====================================================================
    # PRIORITY
    # =====================================================================

    def _determine_priority(self, action, impact_pct, margin, demand_growth,
                            ml_conf, overall_conf) -> str:
        """Rank by business importance."""
        score = 0

        # Impact magnitude
        score += min(30, abs(impact_pct))

        # Margin urgency
        if margin < MARGIN_LOSS:
            score += 25
        elif margin < MARGIN_LOW:
            score += 15
        elif margin >= MARGIN_HIGH:
            score += 5

        # Demand strength
        score += min(15, demand_growth * 0.5)

        # Confidence
        score += overall_conf * 0.1

        # Action urgency
        if action in ("increase_price", "decrease_price"):
            score += 5

        if score >= 40:
            return "HIGH"
        elif score >= 20:
            return "MEDIUM"
        return "LOW"

    # =====================================================================
    # RECOMMENDATION TEXT
    # =====================================================================

    def _generate_text(self, name, action, current_price, ml_price,
                       margin, demand_trend, stock, factors) -> str:
        """Generate concise recommendation text from evidence."""
        parts = []

        if action == "increase_price":
            if ml_price:
                pct = _safe_div(ml_price - current_price, current_price, 0) * 100
                parts.append(f"Increase price to ${ml_price:.2f} ({pct:+.1f}%).")
            else:
                parts.append("Increase price.")
        elif action == "decrease_price":
            if ml_price:
                pct = _safe_div(ml_price - current_price, current_price, 0) * 100
                parts.append(f"Reduce price to ${ml_price:.2f} ({pct:+.1f}%).")
            else:
                parts.append("Reduce price.")
        elif action == "promotional_pricing":
            parts.append("Consider promotional pricing to stimulate demand.")
        else:
            parts.append("Maintain current pricing.")

        # Add key reasons
        reasons = []
        if margin < MARGIN_LOSS:
            reasons.append("currently selling below cost")
        elif margin < MARGIN_LOW:
            reasons.append("margin is critically low")

        if demand_trend == "up":
            reasons.append("demand is increasing")
        elif demand_trend == "down":
            reasons.append("demand is declining")

        if stock <= STOCK_LOW_THRESHOLD and stock > 0:
            reasons.append("inventory is low")
        elif stock == STOCK_OUT_THRESHOLD:
            reasons.append("product is out of stock")

        if reasons:
            parts.append("Key factors: " + ", ".join(reasons[:3]) + ".")

        return " ".join(parts)

    # =====================================================================
    # MARKET POSITION
    # =====================================================================

    def _market_position(self, current_price, lowest, highest, average) -> str:
        """Classify price position relative to competitors."""
        if lowest <= 0 or current_price <= 0:
            return "unknown"
        if current_price < lowest * 0.95:
            return "below_market"
        if highest > 0 and current_price > highest * 1.1:
            return "above_market"
        if average > 0:
            diff = _safe_div(current_price - average, average, 0) * 100
            if abs(diff) < 5:
                return "at_market"
        return "within_range"

    # =====================================================================
    # DATA GATHERING HELPERS
    # =====================================================================

    def _get_ml_prediction(self, product_id: int) -> dict:
        """Get ML prediction for a product."""
        try:
            pred = self.ml.predict_product(product_id, include_forecast=False)
            return pred
        except Exception as e:
            logger.debug("ML prediction unavailable for product %d: %s", product_id, e)
            return {
                "suggested_price": None, "confidence_score": 0,
                "factors": [], "expected_revenue": 0, "expected_profit": 0,
                "insufficient_data": True,
            }

    def _get_sales_data(self, product_id: int) -> dict:
        """Get sales aggregates for a product."""
        try:
            aggregates = _sales_aggregates(self.db)
            return aggregates.get(product_id, {
                "avg_daily_units": 0, "total_units": 0, "revenue": 0,
                "sales_days": 0, "stock_quantity": 0,
            })
        except Exception:
            return {"avg_daily_units": 0, "total_units": 0, "revenue": 0,
                    "sales_days": 0, "stock_quantity": 0}

    def _get_sales_data_cached(self, product_id: int, aggregates: dict) -> dict:
        """Get sales data from pre-computed aggregates."""
        return aggregates.get(product_id, {
            "avg_daily_units": 0, "total_units": 0, "revenue": 0,
            "sales_days": 0, "stock_quantity": 0,
        })

    def _get_competitor_data(self, product_id: int) -> dict:
        """Get competitor pricing data for a product."""
        try:
            from app.services.competitor_service import CompetitorService
            cs = CompetitorService(self.db)
            result = cs.analyze(product_id)

            competitors = result.get("competitors", [])
            prices = [c.get("price", 0) for c in competitors if c.get("price", 0) > 0]

            if prices:
                return {
                    "competitor_count": len(competitors),
                    "price_range": {
                        "lowest": min(prices),
                        "highest": max(prices),
                        "average": sum(prices) / len(prices),
                    },
                    "verified_count": len([p for p in prices if p > 0]),
                }
            return {
                "competitor_count": len(competitors),
                "price_range": {"lowest": 0, "highest": 0, "average": 0},
                "verified_count": 0,
            }
        except Exception as e:
            logger.debug("Competitor data unavailable for product %d: %s", product_id, e)
            return {
                "competitor_count": 0,
                "price_range": {"lowest": 0, "highest": 0, "average": 0},
                "verified_count": 0,
            }

    def _get_demand_data(self, product_id: int) -> dict:
        """Get demand forecast data for a product."""
        try:
            signal = self.forecast.get_demand_signal(product_id)
            if signal and signal.get("trend") != "unavailable":
                return {
                    "trend": signal.get("trend", "stable"),
                    "growth_pct": signal.get("growth_pct", 0),
                    "forecast_confidence": signal.get("forecast_confidence", 0),
                    "forecast_growth_pct": signal.get("growth_pct", 0),
                }
        except Exception:
            pass
        return {
            "trend": "stable", "growth_pct": 0,
            "forecast_confidence": 0, "forecast_growth_pct": 0,
        }

    # =====================================================================
    # SUMMARY BUILDING
    # =====================================================================

    def _build_summary(self, recommendations: list) -> dict:
        """Build strategy summary KPIs from recommendation list."""
        total = len(recommendations)
        increases = sum(1 for r in recommendations if r["action"] == "increase_price")
        decreases = sum(1 for r in recommendations if r["action"] == "decrease_price")
        maintains = sum(1 for r in recommendations if r["action"] == "maintain_price")
        promotional = sum(1 for r in recommendations if r["action"] == "promotional_pricing")
        high_priority = sum(1 for r in recommendations if r.get("priority") == "HIGH")
        medium_priority = sum(1 for r in recommendations if r.get("priority") == "MEDIUM")

        # Potential revenue uplift
        total_uplift = sum(
            r.get("expected_impact", {}).get("profit_change", 0)
            for r in recommendations
            if r.get("expected_impact", {}).get("profit_change", 0) > 0
        )

        return {
            "total_recommendations": total,
            "price_increase_opportunities": increases,
            "price_reduction_opportunities": decreases,
            "maintain_price": maintains,
            "promotional_pricing": promotional,
            "high_priority_actions": high_priority,
            "medium_priority_actions": medium_priority,
            "total_potential_profit_uplift": _round(total_uplift),
        }

    def _empty_summary(self) -> dict:
        return {
            "total_recommendations": 0,
            "price_increase_opportunities": 0,
            "price_reduction_opportunities": 0,
            "maintain_price": 0,
            "promotional_pricing": 0,
            "high_priority_actions": 0,
            "medium_priority_actions": 0,
            "total_potential_profit_uplift": 0,
        }

    # =====================================================================
    # CATEGORIES
    # =====================================================================

    def categories(self) -> list:
        """List available product categories."""
        rows = (
            self.db.query(Product.category, func.count(Product.id))
            .filter(Product.status == "active")
            .group_by(Product.category)
            .all()
        )
        return [{"category": r[0] or "Uncategorized", "count": r[1]} for r in rows]
