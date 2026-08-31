"""
PricePilot AI - Machine Learning Service
Real dataset-trained AI price optimization engine.

Prediction NEVER retrains: it loads the latest persisted model (joblib on
disk, recorded in ``model_runs``), builds a feature vector for the product,
and derives a recommended price, expected revenue / profit, a confidence
score, and data-driven explanation factors from the trained model and the
product's actual sales history.
"""

import logging
import time

import numpy as np
import pandas as pd
from sqlalchemy.orm import Session

from app.models.activity_log import ActivityLog
from app.models.pricing_history import PricingHistory
from app.models.product import Product
from app.models.recommendation import Recommendation
from app.services.forecast_service import ForecastService
from app.services.training_service import ModelTrainingService, _sales_aggregates

logger = logging.getLogger(__name__)

MIN_SAMPLES = 10

# Short / medium / long-term price-forecast horizons (days)
PRICE_FORECAST_HORIZONS = [7, 30, 90, 180, 365]


class PricingMLService:
    """AI Pricing Optimization Engine - prediction from the persisted model."""

    def __init__(self, db: Session):
        self.db = db
        self.training = ModelTrainingService(db)

    # ------------------------------------------------------------------
    # Data preparation (shared with training)
    # ------------------------------------------------------------------
    def _product_row(self, product_id: int, aggregates: dict = None) -> dict:
        """Raw feature dict for one product (mirrors training frame rows).

        ``aggregates`` is an optional pre-computed ``_sales_aggregates`` map so
        batch analysis only scans the sales table once instead of per product.
        """
        product = self.db.query(Product).filter(Product.id == product_id).first()
        if not product:
            raise ValueError("Product not found")
        if not product.current_price or product.current_price <= 0:
            raise ValueError("Product has no valid price to optimize")

        base = product.base_price or product.current_price
        cost = product.cost_price or 0
        agg = (aggregates or _sales_aggregates(self.db)).get(product.id, {})
        return {
            "product_id": product.id,
            "name": product.name,
            "category": product.category or "Uncategorized",
            "brand": self._limit_brand(product.name.split(" ")[0] if product.name else "Unknown"),
            "current_price": product.current_price,
            "base_price": base,
            "cost_price": cost,
            "stock_quantity": product.stock_quantity or 0,
            "revenue": product.revenue or agg.get("revenue", 0) or 0,
            "margin_pct": ((product.current_price - cost) / product.current_price * 100)
                          if cost > 0 and product.current_price > 0 else 0,
            "price_deviation": ((product.current_price - base) / base * 100) if base else 0,
            "avg_daily_units": agg.get("avg_daily_units", 0),
            "total_units": agg.get("total_units", 0),
            "sales_days": agg.get("sales_days", 0),
            "demand_slope": agg.get("demand_slope", 0),
            "weekend_uplift": agg.get("weekend_uplift", 1.0),
            "festival_share": agg.get("festival_share", 0),
        }

    # Module-level cache so _limit_brand only scans all products once per
    # process lifetime (not per prediction call).
    _brand_cache: dict = None
    _brand_cache_ts: float = 0

    def _limit_brand(self, brand: str) -> str:
        """Limit brand to top 20 most common, group rest as 'Other'.
        Matches the training logic in training_service.py."""
        import time as _time
        now = _time.time()
        # Refresh cache every 300 seconds (5 min) or on first call.
        if PricingMLService._brand_cache is None or (now - PricingMLService._brand_cache_ts) > 300:
            products = self.db.query(Product).all()
            brand_counts = {}
            for p in products:
                b = (p.name.split(" ")[0] if p.name else "Unknown")
                brand_counts[b] = brand_counts.get(b, 0) + 1
            PricingMLService._brand_cache = sorted(
                brand_counts, key=brand_counts.get, reverse=True
            )[:20]
            PricingMLService._brand_cache_ts = now
        return brand if brand in PricingMLService._brand_cache else "Other"

    def _encode_row(self, row: dict, feature_cols: list) -> pd.DataFrame:
        """Turn a raw product dict into a one-row DataFrame aligned to the
        trained feature columns (recreates the one-hot dummies)."""
        df = pd.DataFrame([row])
        df = pd.get_dummies(df, columns=["category"], prefix="cat")
        df = pd.get_dummies(df, columns=["brand"], prefix="brand")
        # Map any brand not present in feature_cols to 'Other' so
        # one-hot columns match the trained model exactly.
        brand_cols_in_model = [c for c in feature_cols if c.startswith("brand_")]
        brand_cols_in_row = [c for c in df.columns if c.startswith("brand_")]
        for bc in brand_cols_in_row:
            if bc not in brand_cols_in_model:
                if "brand_Other" in brand_cols_in_model:
                    df["brand_Other"] = df.get("brand_Other", 0) + df[bc]
                df.drop(columns=[bc], inplace=True)
        for col in feature_cols:
            if col not in df.columns:
                df[col] = 0
        df = df.reindex(columns=feature_cols, fill_value=0)
        return df.replace([np.inf, -np.inf], 0).fillna(0).astype(float)

    # ------------------------------------------------------------------
    # Price trend analysis (from recorded price history + catalog anchors)
    # ------------------------------------------------------------------
    def _price_trend(self, product, history=None) -> dict:
        """Historical price direction for a product.

        Uses the pricing-history ledger when manual/AI price changes were
        recorded; otherwise anchors on the catalog base price vs the current
        price (both real dataset fields). Never fabricates points - with no
        data at all it returns a stable/unknown trend.

        ``history`` may be pre-loaded so trend + forecast share one query.
        """
        if history is None:
            history = (
                self.db.query(PricingHistory)
                .filter(PricingHistory.product_id == product.id)
                .order_by(PricingHistory.created_at.asc())
                .all()
            )
        points = []
        if history:
            # De-duplicate consecutive identical values (regardless of old/new
            # boundary) so the series reflects real price changes only.
            for h in history:
                for price in (h.old_price, h.new_price):
                    if price is None:
                        continue
                    if points and abs(points[-1]["price"] - price) < 1e-9:
                        continue
                    points.append({
                        "date": h.created_at.isoformat() if h.created_at else None,
                        "price": round(price, 2),
                    })
            source = "pricing_history"
        else:
            # No manual price changes on record: anchor on catalog base price.
            base = product.base_price or 0
            current = product.current_price or 0
            if base > 0 and current > 0:
                points = [
                    {"date": None, "price": round(base, 2), "key": "base"},
                    {"date": None, "price": round(current, 2), "key": "current"},
                ]
                source = "catalog_base_price"
            else:
                source = "none"

        if len(points) >= 2:
            first = points[0]["price"]
            last = points[-1]["price"]
            change_pct = ((last - first) / first * 100) if first else 0.0
            if change_pct > 2:
                trend = "increasing"
            elif change_pct < -2:
                trend = "decreasing"
            else:
                trend = "stable"
        else:
            change_pct = 0.0
            trend = "stable"

        return {
            "trend": trend,
            "change_pct": round(change_pct, 2),
            "points": points,
            "source": source,
        }

    # ------------------------------------------------------------------
    # Future price forecast (Milestone 2: price prediction module)
    # ------------------------------------------------------------------
    def _price_forecast(self, product, history=None) -> dict:
        """Forward price projection from the product's REAL dated price data.

        Builds a dated price series from the pricing-history ledger (recorded
        price changes with timestamps) anchored on the catalog base price at
        the product's creation date and the current price today. A linear
        trend is fitted over that series and extrapolated to the standard
        horizons (7d / 30d / 90d / 6m / 12m) with a widening uncertainty band
        derived from the fit residual. When no meaningful time span exists the
        forecast degrades honestly: it holds the current price flat and
        explains why. Never fabricates prices, confidence, or trends.

        ``history`` may be pre-loaded so trend + forecast share one query.
        """
        from datetime import datetime, timedelta

        now = datetime.utcnow()
        if history is None:
            history = (
                self.db.query(PricingHistory)
                .filter(PricingHistory.product_id == product.id)
                .order_by(PricingHistory.created_at.asc())
                .all()
            )

        # 1) Collect dated (date, price) observations --------------------------------
        points = []
        created = (product.created_at.replace(tzinfo=None)
                   if product.created_at else now - timedelta(days=180))
        base = product.base_price or product.current_price or 0
        current = product.current_price or 0
        if base > 0:
            points.append((created, float(base)))
        for h in history:
            dt = h.created_at.replace(tzinfo=None) if h.created_at else None
            if dt is None:
                continue
            # Never let a future-dated record (clock skew / bulk import) skew the fit
            if dt > now:
                dt = now
            if h.old_price is not None and h.old_price > 0:
                points.append((dt, float(h.old_price)))
            if h.new_price is not None and h.new_price > 0:
                points.append((dt, float(h.new_price)))
        if current > 0:
            points.append((now, float(current)))

        # 2) Sort + dedupe (date, price) duplicates ----------------------------------
        points.sort(key=lambda p: p[0])
        deduped = []
        seen = set()
        for dt, price in points:
            key = (dt.date(), round(price, 2))
            if key in seen:
                continue
            seen.add(key)
            deduped.append((dt, price))

        if len(deduped) < 2:
            return {
                "available": False,
                "message": ("Insufficient dated price history to project a future price - "
                            "the forecast holds the current price flat."),
                "trend": "stable",
                "change_pct": 0.0,
                "span_days": 0,
                "confidence": 0,
                "points": [{"date": d.date().isoformat(), "price": round(p, 2)}
                            for d, p in deduped],
                "horizons": [
                    {"days": h, "date": (now + timedelta(days=h)).date().isoformat(),
                     "price": round(current, 2), "lower": round(current, 2),
                     "upper": round(current, 2)}
                    for h in PRICE_FORECAST_HORIZONS
                ],
                "note": "No dated price changes on record - the future price is assumed "
                         "flat at the current price.",
            }

        # 3) Linear trend over the dated series --------------------------------------
        t0 = deduped[0][0]
        xs = np.array([(d - t0).days for d, _ in deduped], dtype=float)
        ys = np.array([p for _, p in deduped], dtype=float)
        try:
            slope, intercept = np.polyfit(xs, ys, 1)
        except np.linalg.LinAlgError:
            slope, intercept = 0.0, float(ys.mean())
        fitted = intercept + slope * xs
        residual_std = float(np.std(ys - fitted))
        span = max(float(xs[-1]), 1.0)
        last_price = ys[-1]

        ss_res = float(np.sum((ys - fitted) ** 2))
        ss_tot = float(np.sum((ys - np.mean(ys)) ** 2))
        r2 = 1 - ss_res / ss_tot if ss_tot > 0 else 0.0

        # 4) Project at each horizon with a widening band -----------------------------
        # Confidence & band width are damped by the number of observations so a
        # trivial 2-point fit never claims near-100% certainty or a zero-width
        # band (honest confidence from the actual evidence available).
        obs_factor = min(len(deduped) / 5.0, 1.0)
        horizons = []
        for h in PRICE_FORECAST_HORIZONS:
            target = last_price + slope * h
            band = residual_std * (0.6 + 1.6 * np.sqrt(h / max(span, 1))) + \
                   (0.01 * last_price) * (1.6 - obs_factor)  # floor when residual ~ 0
            # Honest range cap: extrapolating far beyond the observed span has no
            # evidentiary basis (e.g. 365 days from a 7-day window). Horizons beyond
            # ~3x the span are flagged unreliable so the UI can show 'beyond range'
            # instead of a misleading floored-at-zero price.
            reliable = h <= max(span * 3.0, 30.0)
            horizons.append({
                "days": h,
                "date": (now + timedelta(days=h)).date().isoformat(),
                "price": round(max(0.0, target), 2),
                "lower": round(max(0.0, target - band), 2),
                "upper": round(max(0.0, target + band), 2),
                "reliable": bool(reliable),
                "reason": ("beyond_reliable_range" if not reliable
                            else ("extrapolation" if h > span else "within_span")),
            })

        slope_perc = (slope / max(abs(last_price), 1e-9)) * 100
        if slope_perc > 0.05:
            trend = "increasing"
        elif slope_perc < -0.05:
            trend = "decreasing"
        else:
            trend = "stable"
        change_pct = ((horizons[1]["price"] - current) / max(current, 1e-9)) * 100 if current > 0 else 0.0
        confidence = round(max(0.0, min(98.0,
                            100 * max(r2, 0) * (0.6 + 0.4 * min(span / 180, 1)) * obs_factor)), 1)

        return {
            "available": True,
            "source": "pricing_history" if history else "catalog_anchors",
            "trend": trend,
            "change_pct": round(change_pct, 2),
            "span_days": int(xs[-1]),
            "r2": round(float(r2), 3),
            "confidence": confidence,
            "points": [{"date": d.date().isoformat(), "price": round(p, 2)}
                        for d, p in deduped],
            "horizons": horizons,
            "note": (
                f"Projected from {len(deduped)} dated price observations spanning "
                f"{int(xs[-1])} days; values beyond the observed window are linear "
                "extrapolations for directional planning only."
            ),
        }

    # ------------------------------------------------------------------
    # Portfolio price elasticity (learned from the actual dataset)
    # ------------------------------------------------------------------
    # Module-level cache for elasticity (expensive: builds entire training frame)
    _elasticity_cache: float = None
    _elasticity_cache_ts: float = 0

    def _learn_elasticity(self, frame: pd.DataFrame = None) -> float:
        """Learn portfolio price elasticity from the training data.

        Returns the elasticity coefficient (negative for normal goods).
        The result is cached for 10 minutes since the underlying dataset
        changes infrequently.
        """
        import time as _time
        now = _time.time()
        if PricingMLService._elasticity_cache is not None and (now - PricingMLService._elasticity_cache_ts) < 600:
            return PricingMLService._elasticity_cache
        try:
            from sklearn.linear_model import LinearRegression
            frame = frame if frame is not None else self.training.build_training_frame()
            if frame.empty or "__target__" not in frame.columns:
                return -1.2
            df = frame[frame["avg_daily_units"] > 0].copy()
            if len(df) < 10:
                return -1.2
            df["log_units"] = np.log(df["avg_daily_units"])
            df["log_price"] = np.log(df["__target__"])
            features = ["log_price"] + [c for c in df.columns if c.startswith("cat_")]
            X = df[features].values
            y = df["log_units"].values
            lr = LinearRegression().fit(X, y)
            result = float(lr.coef_[0])
            PricingMLService._elasticity_cache = result
            PricingMLService._elasticity_cache_ts = now
            return result
        except Exception:  # noqa: BLE001
            return -1.2

    # ------------------------------------------------------------------
    # Prediction
    # ------------------------------------------------------------------
    def predict_product(self, product_id: int, include_forecast: bool = False,
                        aggregates: dict = None, training_frame: pd.DataFrame = None,
                        model=None, feature_cols: list = None, run=None) -> dict:
        """Full price-optimization analysis for one product using the SAVED model.

        Never retrains. If no trained model exists yet, returns a clear
        insufficient-data payload pointing the user to run training.

        ``aggregates`` / ``training_frame`` are optional pre-computed artifacts
        so batch analysis scans the sales table / builds the frame only once.
        ``model`` / ``feature_cols`` / ``run`` are the already-loaded artifacts
        so batch analysis avoids a joblib disk load + DB query per product.
        """
        product = self.db.query(Product).filter(Product.id == product_id).first()
        if not product:
            raise ValueError("Product not found")

        # Load the dated price ledger ONCE so the trend + forecast share a query.
        price_history = (
            self.db.query(PricingHistory)
            .filter(PricingHistory.product_id == product_id)
            .order_by(PricingHistory.created_at.asc())
            .all()
        )

        if model is None:
            model, feature_cols, run = self.training.load_model()
        if model is None or not run:
            return {
                "product_id": product_id,
                "product_name": product.name,
                "current_price": round(product.current_price, 2),
                "suggested_price": None,
                "confidence_score": 0,
                "expected_revenue_change": None,
                "expected_revenue": None,
                "expected_profit": None,
                "price_difference": None,
                "factors": [],
                "recommendation": (
                    "No trained AI model available. Upload a pricing dataset, import it, "
                    "and run AI training (or click Retrain Model) — prediction always uses "
                    "the persisted model and never retrains."
                ),
                "insufficient_data": True,
                "best_model": None,
                "model_metrics": None,
                "model_info": self.training.model_info(),
                "revenue_curve": [],
                "demand_forecast": None,
                "price_trend": self._price_trend(product, history=price_history),
                "price_forecast": self._price_forecast(product, history=price_history),
            }        # Compute sales aggregates ONCE so _product_row and _learn_elasticity
        # (via build_training_frame) share the same expensive scan of 216K rows.
        if aggregates is None:
            from app.services.training_service import _sales_aggregates
            aggregates = _sales_aggregates(self.db)

        row = self._product_row(product_id, aggregates=aggregates)
        X_row = self._encode_row(row, feature_cols)
        start = time.time()
        predicted_price = float(model.predict(X_row.values)[0])
        prediction_ms = round((time.time() - start) * 1000, 2)


        current_price = product.current_price or 0
        cost = product.cost_price or 0

        # Suggested price: model-implied price, clamped to sane business bounds
        suggested = max(0.01, predicted_price)
        if cost > 0:
            suggested = max(suggested, round(cost * 1.05, 2))  # never below cost+5%
        # Keep recommendations realistic: within 0.5x .. 2x of the current price
        lo, hi = current_price * 0.5, current_price * 2.0
        suggested = round(min(max(suggested, lo), hi), 2)

        change_pct = ((suggested - current_price) / current_price * 100) if current_price else 0

        # Demand-driven revenue / profit estimate using learned elasticity
        # training_frame is None here for single-product; _learn_elasticity
        # has its own cache so the expensive build_training_frame() runs
        # at most once per 10 minutes.
        elasticity = self._learn_elasticity(training_frame)
        avg_daily_units = max(row["avg_daily_units"], (row["revenue"] or 0) /
                              max(current_price, 1) / max(30, 1))
        current_units_30d = max(avg_daily_units * 30, 1)
        if current_price > 0 and suggested != current_price:
            units_ratio = (suggested / current_price) ** elasticity
        else:
            units_ratio = 1.0
        expected_units_30d = current_units_30d * units_ratio
        current_revenue_30d = current_units_30d * current_price
        expected_revenue_30d = expected_units_30d * suggested
        expected_profit_30d = (suggested - cost) * expected_units_30d
        revenue_change_pct = ((expected_revenue_30d - current_revenue_30d) /
                              max(current_revenue_30d, 1)) * 100

        # Confidence: driven by real model quality + data volume
        r2 = run.accuracy or 0
        sample_factor = min(1.0, run.samples / 80)
        rel_mae = (run.mae or 0) / max(float(np.mean([current_price]) or 1), 1)
        error_penalty = min(0.25, rel_mae)
        confidence = round(max(35, min(98, (45 + 40 * max(r2, 0)) * (0.6 + 0.4 * sample_factor)
                                       - error_penalty * 100)), 2)

        # ---- Dynamic WHY factors (all derived from real data, never hardcoded) ----
        factors = self._explain_factors(row, suggested, current_price, cost, elasticity,
                                        expected_profit_30d, r2, run.samples)

        # Demand forecast signal folded in when requested
        demand_forecast = None
        if include_forecast:
            demand_forecast = ForecastService(self.db).get_demand_signal(product_id)
            if demand_forecast and demand_forecast.get("trend") != "unavailable":
                trend = demand_forecast.get("trend")
                growth = demand_forecast.get("growth_pct", 0)
                src = "Prophet" if demand_forecast.get("source") == "prophet" else "trend analysis"
                if trend == "up" and growth > 3:
                    factors.append(f"Demand forecast ({src}) projects +{growth:.1f}% revenue growth — supports the recommendation")
                elif trend == "down" and growth < -3:
                    factors.append(f"Demand forecast ({src}) projects {growth:.1f}% decline — conservative pricing protects volume")

        recommendation = (
            f"Model '{run.best_model}' (trained on {run.samples} records from '{run.dataset_name}', "
            f"R² {r2:.2f}) suggests setting the price to ${suggested:.2f} from ${current_price:.2f} "
            f"({change_pct:+.1f}%). At this price the model estimates ~{expected_units_30d:,.0f} units "
            f"over 30 days, ${expected_revenue_30d:,.0f} revenue and ${expected_profit_30d:,.0f} profit."
        )

        return {
            "product_id": product_id,
            "product_name": product.name,
            "current_price": round(current_price, 2),
            "suggested_price": suggested,
            "confidence_score": confidence,
            "expected_revenue_change": round(change_pct, 2),
            "expected_revenue": round(expected_revenue_30d, 2),
            "expected_profit": round(expected_profit_30d, 2),
            "price_difference": round(suggested - current_price, 2),
            "factors": factors,
            "recommendation": recommendation,
            "insufficient_data": False,
            "best_model": run.best_model,
            "model_metrics": {
                "mae": run.mae, "rmse": run.rmse, "r2": run.accuracy,
            },
            "model_info": run.to_dict(),
            "prediction_time_ms": prediction_ms,
            "elasticity": round(elasticity, 3),
            "revenue_curve": [
                {"price": round(p, 2),
                 "revenue": round(current_units_30d * (p / max(current_price, 0.01)) ** elasticity * p, 2)}
                for p in np.linspace(current_price * 0.7, current_price * 1.3, 13)
            ],
            "demand_forecast": demand_forecast,
            "price_trend": self._price_trend(product, history=price_history),
            "price_forecast": self._price_forecast(product, history=price_history),
        }

    def _explain_factors(self, row: dict, suggested, current_price, cost,
                         elasticity, expected_profit, r2, samples) -> list:
        """Build data-driven explanation strings for the recommendation."""
        factors = []
        margin_now = ((current_price - cost) / current_price * 100) if cost > 0 and current_price > 0 else 0
        margin_new = ((suggested - cost) / suggested * 100) if cost > 0 and suggested > 0 else 0
        if cost > 0:
            factors.append(
                f"Margin moves {margin_now:.1f}% → {margin_new:.1f}% at the suggested price "
                f"(cost ${cost:.2f})"
            )

        if row["avg_daily_units"] > 0:
            slope = row["demand_slope"]
            direction = "rising" if slope > 0.03 else ("declining" if slope < -0.03 else "stable")
            factors.append(
                f"Historical sales trend is {direction} ({slope * 100:+.1f}% over the last 6 months) "
                f"at {row['avg_daily_units']:.1f} units/day"
            )
            if row["weekend_uplift"] > 1.1:
                factors.append(f"Weekend demand lifts {row['weekend_uplift'] * 100:.0f}% vs weekdays")
            if row["festival_share"] > 0.05:
                factors.append(f"Festival days add {row['festival_share'] * 100:.0f}% volume over normal days")
        else:
            factors.append("Limited sales history for this product — recommendation leans on catalog pricing structure")

        if row["stock_quantity"] <= 0:
            factors.append("Out of stock — price is informational only")
        elif row["stock_quantity"] < 30:
            factors.append(f"Low stock ({row['stock_quantity']} units) — avoids discounting scarce inventory")

        if suggested > current_price:
            factors.append(f"Model sees room to raise price ({suggested - current_price:+.2f}) — current price sits below the level its attributes support")
        elif suggested < current_price:
            factors.append(f"Model suggests easing price ({suggested - current_price:+.2f}) to improve price-competitiveness for this product profile")
        else:
            factors.append("Model-implied price aligns with the current price — market equilibrium")

        factors.append(f"Portfolio price elasticity learned from your data: {elasticity:.2f}")
        if expected_profit > 0:
            factors.append(f"Projected 30-day profit at the suggested price: ${expected_profit:,.0f}")
        factors.append(f"Model confidence reflects R² {r2:.2f} across {samples} training records")
        return factors

    # ------------------------------------------------------------------
    # Backwards-compatible aliases used by the existing API
    # ------------------------------------------------------------------
    def analyze_product(self, product_id: int, include_forecast: bool = False) -> dict:
        """Alias of predict_product (kept for the /optimize route)."""
        return self.predict_product(product_id, include_forecast=include_forecast)

    def batch_analyze(self, category: str = None, include_forecast: bool = False) -> list:
        """Analyze every product (optionally filtered by category) using the saved model.

        The model, sales aggregates, and the elasticity training frame are all
        computed ONCE for the whole batch (not per product), keeping prediction
        O(N) with a single disk load instead of one per product.
        """
        query = self.db.query(Product)
        if category:
            query = query.filter(Product.category == category)
        products = query.all()
        if not products:
            return []
        # Load the model FIRST: if no trained model exists, bail before paying
        # for the expensive sales-aggregate + training-frame prep below.
        model, feature_cols, run = self.training.load_model()
        if model is None or not run:
            # No trained model: report it once instead of reloading per product.
            return []
        aggregates = _sales_aggregates(self.db)
        training_frame = self.training.build_training_frame()
        results = []
        for p in products:
            try:
                results.append(self.predict_product(
                    p.id, include_forecast=include_forecast,
                    aggregates=aggregates, training_frame=training_frame,
                    model=model, feature_cols=feature_cols, run=run,
                ))
            except ValueError:
                continue
        return results

    def save_recommendation(self, analysis: dict, user_id: int) -> Recommendation:
        """Persist an AI recommendation for the approval workflow."""
        product_id = analysis["product_id"]
        rec = Recommendation(
            product_id=product_id,
            recommended_price=analysis.get("suggested_price") or analysis["current_price"],
            current_price=analysis["current_price"],
            confidence_score=analysis.get("confidence_score", 0),
            expected_revenue_impact=analysis.get("expected_revenue_change", 0),
            factors_considered=" | ".join(analysis.get("factors", [])),
            status="pending",
        )
        self.db.add(rec)
        self.db.add(ActivityLog(
            action=f"AI recommendation generated for product #{product_id}",
            resource_type="product",
            resource_id=product_id,
            details=f"Suggested ${rec.recommended_price:.2f} (confidence {rec.confidence_score:.0f}%)",
            user_id=user_id,
        ))
        self.db.commit()
        self.db.refresh(rec)
        return rec

    def get_revenue_prediction(self, product_id: int, new_price: float) -> dict:
        """Predict revenue impact of a specific price change using the trained model."""
        product = self.db.query(Product).filter(Product.id == product_id).first()
        if not product:
            raise ValueError("Product not found")

        model, feature_cols, run = self.training.load_model()
        if model is None or not run:
            raise ValueError("No trained model available. Run AI training first.")

        row = self._product_row(product_id)
        X_row = self._encode_row(row, feature_cols)
        base_price_pred = float(model.predict(X_row.values)[0])

        # Simulate the requested price by overriding the target feature
        simulated = dict(row)
        simulated["current_price"] = new_price
        simulated["base_price"] = new_price
        simulated["price_deviation"] = 0.0
        X_sim = self._encode_row(simulated, feature_cols)
        expected_price = float(model.predict(X_sim.values)[0])

        elasticity = self._learn_elasticity()
        current_units = max(row["avg_daily_units"], 1)
        units_ratio = (new_price / max(product.current_price, 0.01)) ** elasticity
        expected_units = current_units * units_ratio
        expected_revenue = expected_units * new_price
        current_revenue = current_units * product.current_price
        change_pct = ((expected_revenue - current_revenue) / max(current_revenue, 1)) * 100

        return {
            "product_id": product_id,
            "product_name": product.name,
            "current_price": round(product.current_price, 2),
            "suggested_price": round(new_price, 2),
            "expected_units_sold": round(expected_units, 1),
            "expected_revenue": round(expected_revenue, 2),
            "current_revenue": round(current_revenue, 2),
            "revenue_change_pct": round(change_pct, 2),
            "confidence": round(min(95, 45 + run.accuracy * 40), 2),
            "mode": f"ml_model_{str(run.best_model or 'best').lower().replace(' ', '_')}",
        }

    def get_model_status(self) -> dict:
        """Report AI engine status from the persisted model runs (no retraining)."""
        run = self.training.latest_ready_run()
        pending = self.db.query(Recommendation).filter(Recommendation.status == "pending").count()
        applied = self.db.query(Recommendation).filter(Recommendation.status == "applied").count()
        rejected = self.db.query(Recommendation).filter(Recommendation.status == "rejected").count()

        training_state = self.training.training_status()
        samples = run.samples if run else self.db.query(Product).count()
        ready = run is not None

        _all_models = ["Linear Regression", "Random Forest", "XGBoost"]
        status = {
            "status": "ready" if ready else "insufficient_data",
            "samples": samples,
            "min_samples_required": MIN_SAMPLES,
            "models_available": _all_models,
            "recommendations_pending": pending,
            "recommendations_applied": applied,
            "recommendations_rejected": rejected,
            "training_in_progress": training_state["training_in_progress"],
            "forecasting": {
                "engine": "Prophet (weekly seasonality)",
                "forecastable_products": ForecastService(self.db).forecastable_count(),
                "min_history_days": ForecastService.MIN_HISTORY_DAYS,
            },
        }
        if ready:
            status["best_model"] = run.best_model
            status["accuracy"] = run.accuracy
            metrics = json_loads(run.metrics) or {}
            # Derive models_available from actually trained models, not a hardcoded list
            if metrics:
                status["models_available"] = list(metrics.keys())
            status["cv_errors"] = {
                name: m["mae"] for name, m in metrics.items()
            } if metrics else {}
            # Dashboard reads metrics from model_info — always expose the latest
            # READY run so a background retrain never blanks the Model Performance
            # card. training_in_progress remains the separate status signal.
            info = run.to_dict()
            info["has_model"] = True
            status["model_info"] = info
        else:
            status["model_info"] = self.training.model_info()
        return status


def json_loads(text):
    import json
    try:
        return json.loads(text or "{}")
    except (json.JSONDecodeError, TypeError):
        return {}
