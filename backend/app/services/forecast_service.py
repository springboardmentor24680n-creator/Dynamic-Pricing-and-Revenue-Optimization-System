"""
PricePilot AI - Demand Forecasting Service
Prophet-based revenue forecasting engine.

Builds daily revenue time series from the sales ledger, trains a Facebook
Prophet model with weekly seasonality, and produces N-day demand forecasts
with 80% confidence intervals. Forecasts are cached in the forecast_runs
table and surfaced to the pricing engine as a "demand signal" so price
optimization accounts for expected demand shifts.
"""

import json
import logging
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

from app.models.sales import Sale
from app.models.product import Product
from app.models.forecast import ForecastRun

# Honest data-coverage labeling: only fields that actually exist in the uploaded
# dataset / database are used by the forecasting & pricing pipeline. Market
# fields that are NOT present are reported as such instead of being fabricated.
DATA_COVERAGE = {
    "available": [
        "Sales volume (units)",
        "Revenue",
        "Current price",
        "Base price",
        "Product category",
        "Stock level",
        "Day of week",
        "Month",
        "Festival indicators",
    ],
    "unavailable": [
        "Competitor prices",
        "Market demand indices",
        "Economic indicators",
        "Discounts / promotions",
    ],
    "note": "Only fields that exist in the uploaded dataset are used. Unavailable market "
            "fields are reported as 'Not available in current dataset' rather than fabricated.",
}


class ForecastService:
    """Prophet-based demand & revenue forecasting engine."""

    MIN_HISTORY_DAYS = 7      # minimum daily points required for a Prophet fit
    MIN_TREND_POINTS = 3      # minimum points for the fast linear-trend fallback
    CACHE_MAX_AGE_HOURS = 6   # re-train if the cached run is older than this
    DEFAULT_HORIZON = 30
    MAX_HORIZON = 365         # supports 7d .. 12m (short/medium/long term)
    MIN_SEASONAL_DAYS = 14    # at least 2 full weeks before weekly patterns are claimed
    MIN_MONTHLY_DAYS = 45     # ~1.5 months before monthly patterns are claimed

    # Business seasonality analysis: a season is only claimed when the dataset
    # actually covers enough of it; otherwise it is reported as insufficient.
    SEASON_DEFS = [
        {"name": "Winter", "months": (12, 1, 2), "label": "Dec\u2013Feb"},
        {"name": "Spring", "months": (3, 4, 5), "label": "Mar\u2013May"},
        {"name": "Summer", "months": (6, 7, 8), "label": "Jun\u2013Aug"},
        {"name": "Autumn", "months": (9, 10, 11), "label": "Sep\u2013Nov"},
    ]
    MIN_SEASON_DAYS = 21       # >= 3 weeks of a season before a pattern is claimed
    FULL_SEASON_DAYS = 60      # >= 2/3 of a season => full coverage (else partial)
    MIN_FESTIVAL_DAYS = 2      # >= 2 recorded festival days before festival impact is claimed
    SEASON_INDEX_THRESHOLD = 0.10  # +/-10% vs yearly average => higher/lower

    def __init__(self, db: Session):
        self.db = db

    # ------------------------------------------------------------------
    # Data preparation
    # ------------------------------------------------------------------
    def _daily_series(self, product_id: int) -> pd.DataFrame:
        """Aggregate sales into a daily revenue series (indexed by date)."""
        sales = (
            self.db.query(Sale)
            .filter(Sale.product_id == product_id)
            .order_by(Sale.sale_date.asc())
            .all()
        )
        if not sales:
            return pd.DataFrame(columns=["date", "revenue", "units"])

        df = pd.DataFrame(
            [{"date": s.sale_date.date(), "revenue": s.total_amount or 0, "units": s.quantity or 0}
             for s in sales]
        )
        daily = df.groupby("date", as_index=False).agg(
            revenue=("revenue", "sum"),
            units=("units", "sum"),
        ).sort_values("date")
        return daily

    # ------------------------------------------------------------------
    # Fast statistical trend (portfolio views + signal fallback)
    # ------------------------------------------------------------------
    def _quick_trend(self, daily: pd.DataFrame, horizon: int, include_points: bool = False) -> dict:
        """Cheap linear-trend estimate used before/without a full Prophet fit."""
        if daily.empty or len(daily) < self.MIN_TREND_POINTS:
            return None

        x = np.arange(len(daily), dtype=float)
        y = daily["revenue"].astype(float).values
        # Normalize for stability
        scale = max(float(np.max(y)), 1e-9)
        slope, intercept = np.polyfit(x, y / scale, 1)
        slope = slope * scale  # revenue/day

        avg_daily = float(np.mean(y))
        last_actual = float(y[-1])
        x_future = x[-1] + 1 + np.arange(horizon)
        y_future = intercept * scale + slope * x_future
        forecast_total = max(0.0, float(np.sum(y_future)))

        growth_pct = ((forecast_total / horizon) / max(avg_daily, 1e-9) - 1) * 100 if avg_daily > 0 else 0.0
        trend = "up" if slope > avg_daily * 0.02 else ("down" if slope < -avg_daily * 0.02 else "stable")

        result = {
            "trend": trend,
            "growth_pct": round(growth_pct, 2),
            "avg_daily_revenue": round(avg_daily, 2),
            "forecast_revenue_total": round(forecast_total, 2),
            "last_actual": round(last_actual, 2),
            "daily_change": round(slope, 2),
            "source": "linear_trend",
            "points": None,
        }
        if include_points:
            last_date = daily["date"].iloc[-1]
            result["points"] = [
                {
                    "date": (last_date + timedelta(days=i + 1)).strftime("%Y-%m-%d"),
                    "yhat": round(float(max(v, 0)), 2),
                    "yhat_lower": round(float(max(v * 0.8, 0)), 2),
                    "yhat_upper": round(float(max(v * 1.2, 0)), 2),
                }
                for i, v in enumerate(y_future)
            ]
        return result

    # ------------------------------------------------------------------
    # Prophet fit
    # ------------------------------------------------------------------
    def _fit_prophet(self, daily: pd.DataFrame, horizon: int) -> dict:
        """Train Prophet on daily revenue and forecast `horizon` days ahead.

        Returns ``None`` when history is too short OR when the Prophet/STAN
        backend is unavailable (e.g. missing CmdStan binaries), so callers can
        degrade to the fast trend estimate instead of failing.
        """
        df = daily[["date", "revenue"]].rename(columns={"date": "ds", "revenue": "y"})
        df["ds"] = pd.to_datetime(df["ds"])
        df["y"] = df["y"].astype(float)

        if len(df) < self.MIN_HISTORY_DAYS:
            return None

        try:
            from prophet import Prophet  # imported lazily: heavy dependency

            model = Prophet(
                growth="linear",
                weekly_seasonality=True,
                yearly_seasonality=False,
                daily_seasonality=False,
                interval_width=0.8,  # 80% confidence interval
                seasonality_mode="additive",
            )
            model.fit(df)
            future = model.make_future_dataframe(periods=horizon, freq="D")
            forecast = model.predict(future)
        except Exception as exc:  # noqa: BLE001 - degrade gracefully on any backend failure
            logger.warning("Prophet fit failed, falling back to trend estimate: %s", exc)
            return None

        last_actual_date = df["ds"].max()
        history_points = []
        for _, row in df.iterrows():
            history_points.append({
                "date": row["ds"].strftime("%Y-%m-%d"),
                "actual": round(float(row["y"]), 2),
            })

        forecast_points = []
        for _, row in forecast.iterrows():
            if row["ds"] <= last_actual_date:
                continue
            forecast_points.append({
                "date": row["ds"].strftime("%Y-%m-%d"),
                "yhat": round(float(max(row["yhat"], 0)), 2),
                "yhat_lower": round(float(max(row["yhat_lower"], 0)), 2),
                "yhat_upper": round(float(max(row["yhat_upper"], 0)), 2),
            })

        # Prophet decomposition: the fitted trend and weekly-seasonality
        # components for EVERY date (history + forecast horizon), read directly
        # from the model's predict() output - real fitted values, never synthetic.
        components = []
        for _, row in forecast.iterrows():
            components.append({
                "date": row["ds"].strftime("%Y-%m-%d"),
                "trend": round(float(np.nan_to_num(row.get("trend", 0.0))), 2),
                "weekly": round(float(np.nan_to_num(row.get("weekly", 0.0))), 2),
            })

        actual_total = float(df["y"].sum())
        forecast_total = float(sum(p["yhat"] for p in forecast_points))
        avg_daily = actual_total / max(len(df), 1)

        # Growth vs the trailing average of the same length as the horizon
        window = min(horizon, len(df))
        trailing = float(df["y"].tail(window).mean()) if window > 0 else 0.0
        forecast_daily = forecast_total / max(len(forecast_points), 1)
        growth_pct = ((forecast_daily / max(trailing, 1e-9)) - 1) * 100 if trailing > 0 else 0.0

        trend = "up" if growth_pct > 3 else ("down" if growth_pct < -3 else "stable")

        return {
            "trend": trend,
            "growth_pct": round(growth_pct, 2),
            "avg_daily_revenue": round(avg_daily, 2),
            "forecast_revenue_total": round(forecast_total, 2),
            "last_actual": round(float(df["y"].iloc[-1]), 2),
            "source": "prophet",
            "points": forecast_points,
            "history": history_points,
            "components": components,
            "trained_on_days": len(df),
        }

    # ------------------------------------------------------------------
    # Seasonal & demand analysis (computed from REAL sales, never fabricated)
    # ------------------------------------------------------------------
    def _seasonality_analysis(self, daily: pd.DataFrame) -> dict:
        """Day-of-week and monthly demand patterns from actual sales history.

        Returns ``supported: False`` with a clear message when the history is too
        thin to identify a reliable pattern - the engine never invents seasonality.
        """
        if daily is None or daily.empty or len(daily) < self.MIN_SEASONAL_DAYS:
            return {
                "supported": False,
                "message": "At least 14 days of sales history are needed to identify reliable seasonal patterns.",
            }
        df = daily.copy()
        df["date"] = pd.to_datetime(df["date"])
        df["weekday"] = df["date"].dt.dayofweek
        df["month"] = df["date"].dt.month

        day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        dow = df.groupby("weekday")["units"].mean()
        week_avg = float(dow.mean()) or 1e-9
        day_of_week = [
            {"day": day_names[d],
             "index": round(float(dow.get(d, 0)) / week_avg, 2),
             "avg_units": round(float(dow.get(d, 0)), 2)}
            for d in range(7)
        ]

        weekend_avg = float(df[df["weekday"] >= 5]["units"].mean() or 0)
        weekday_avg = float(df[df["weekday"] < 5]["units"].mean() or 0)
        weekend_pct = round(((weekend_avg / max(weekday_avg, 1e-9)) - 1) * 100, 1) if weekday_avg > 0 else 0.0

        monthly = None
        if len(df) >= self.MIN_MONTHLY_DAYS and df["month"].nunique() >= 2:
            mavg = df.groupby("month")["units"].mean()
            month_avg = float(mavg.mean()) or 1e-9
            month_names = {1: "Jan", 2: "Feb", 3: "Mar", 4: "Apr", 5: "May", 6: "Jun",
                           7: "Jul", 8: "Aug", 9: "Sep", 10: "Oct", 11: "Nov", 12: "Dec"}
            monthly = [
                {"month": month_names[m],
                 "index": round(float(mavg.get(m, 0)) / month_avg, 2),
                 "avg_units": round(float(mavg.get(m, 0)), 2)}
                for m in sorted(mavg.index)
            ]

        insights = []
        if abs(weekend_pct) >= 10:
            insights.append(
                f"Weekend demand runs {weekend_pct:+.0f}% "
                f"{'above' if weekend_pct > 0 else 'below'} weekdays."
            )
        peak_day = max(day_of_week, key=lambda r: r["index"])
        if peak_day["index"] > 1.15:
            insights.append(f"Peak weekday is {peak_day['day']} at {peak_day['index']:.2f}x the weekly average.")
        peak_month = max(monthly, key=lambda r: r["index"]) if monthly else None
        if peak_month and peak_month["index"] > 1.15:
            insights.append(f"Peak month is {peak_month['month']} at {peak_month['index']:.2f}x the monthly average.")

        return {
            "supported": True,
            "day_of_week": day_of_week,
            "monthly": monthly,
            "weekend_vs_weekday_pct": weekend_pct,
            "peak_day": peak_day["day"],
            "peak_month": peak_month["month"] if peak_month else None,
            "insights": insights,
            "insight_text": (" ".join(insights)
                              or "Sales are evenly distributed across the week - no strong seasonal pattern."),
        }

    def _business_seasonality(self, daily: pd.DataFrame, product_id: int) -> dict:
        """Business-oriented seasonal demand analysis from REAL sales.

        Compares average daily units during each calendar season (Winter,
        Spring, Summer, Autumn) against the product's overall yearly average,
        and measures festival-period demand using the ``festival_effect``
        column recorded in the dataset (real uplift days, never fabricated).

        Seasons the dataset does not cover enough of are reported as
        'Insufficient historical data' rather than being invented.
        """
        seasons = []
        insights = []

        if daily is not None and not daily.empty:
            df = daily.copy()
            df["date"] = pd.to_datetime(df["date"])
            df["month"] = df["date"].dt.month
            year_avg = float(df["units"].mean()) or 1e-9

            for season in self.SEASON_DEFS:
                sub = df[df["month"].isin(season["months"])]
                days = int(sub["date"].nunique()) if not sub.empty else 0
                if days < self.MIN_SEASON_DAYS:
                    seasons.append({
                        "season": season["name"],
                        "months": season["label"],
                        "supported": False,
                        "days_covered": days,
                        "insight": (
                            f"Insufficient historical data - only {days} day(s) of "
                            f"{season['name'].lower()} sales are covered in the current dataset."
                        ),
                    })
                    continue
                season_avg = float(sub["units"].mean())
                index = round(season_avg / max(year_avg, 1e-9), 2)
                change_pct = round((index - 1) * 100, 1)
                if index >= 1 + self.SEASON_INDEX_THRESHOLD:
                    direction = "higher"
                elif index <= 1 - self.SEASON_INDEX_THRESHOLD:
                    direction = "lower"
                else:
                    direction = "stable"
                coverage = "" if days >= self.FULL_SEASON_DAYS else f" (partial coverage - {days} days)"
                if direction == "higher":
                    insight = (
                        f"Demand is higher during {season['name'].lower()} "
                        f"(+{change_pct:.0f}% vs the dataset average){coverage}."
                    )
                elif direction == "lower":
                    insight = (
                        f"{season['name'].capitalize()} demand is lower than the dataset average "
                        f"({change_pct:+.0f}%){coverage}."
                    )
                else:
                    insight = (
                        f"Demand during {season['name'].lower()} tracks the dataset average "
                        f"({change_pct:+.0f}%){coverage}."
                    )
                seasons.append({
                    "season": season["name"],
                    "months": season["label"],
                    "supported": True,
                    "days_covered": days,
                    "avg_daily_units": round(season_avg, 2),
                    "year_avg_daily_units": round(year_avg, 2),
                    "index": index,
                    "change_pct": change_pct,
                    "direction": direction,
                    "insight": insight,
                })
                if direction != "stable":
                    insights.append(insight)

        # Festival impact from the recorded festival_effect column (real uplift
        # days, e.g. Valentine's / year-end), measured against the product's own
        # baseline demand.
        festival = {"supported": False, "days_found": 0}
        try:
            fest_dates = {
                r[0].date() if r[0] else None
                for r in self.db.query(Sale.sale_date)
                .filter(Sale.product_id == product_id, Sale.festival_effect.isnot(None),
                        Sale.festival_effect > 1.0)
                .distinct().all()
            }
            fest_dates.discard(None)
        except Exception:  # noqa: BLE001 - column may not exist on older schemas
            fest_dates = set()
        if fest_dates and daily is not None and not daily.empty:
            df = daily.copy()
            df["date"] = pd.to_datetime(df["date"])
            fest_mask = df["date"].dt.date.isin(fest_dates)
            fest_days_in_data = int(fest_mask.sum())
            if fest_days_in_data >= self.MIN_FESTIVAL_DAYS:
                fest_avg = float(df[fest_mask]["units"].mean() or 0)
                # Weekend-adjusted baseline: compare festival days only against
                # non-festival days of the same weekday type, so a festival
                # landing on a weekend isn't inflated by the weekend effect.
                fest_weekdays = set(df[fest_mask]["date"].dt.dayofweek)
                base_mask = (~fest_mask) & df["date"].dt.dayofweek.isin(fest_weekdays)
                if base_mask.any():
                    norm_avg = float(df[base_mask]["units"].mean() or 0)
                else:
                    # No non-festival day of the same weekday type (e.g. every
                    # matching weekday in a short window was a festival day):
                    # fall back to the unadjusted normal-day mean so a real
                    # festival effect is never silently reported as zero.
                    norm_avg = float(df[~fest_mask]["units"].mean() or 0)
                uplift = round(((fest_avg / max(norm_avg, 1e-9)) - 1) * 100, 1) if norm_avg > 0 else 0.0
                festival = {
                    "supported": True,
                    "days_found": fest_days_in_data,
                    "avg_festival_units": round(fest_avg, 2),
                    "avg_normal_units": round(norm_avg, 2),
                    "uplift_pct": uplift,
                    "baseline_note": "weekday-adjusted vs non-festival days of the same weekday type",
                    "insight": (
                        f"Demand is {abs(uplift):.0f}% {'higher' if uplift >= 0 else 'lower'} during "
                        f"recorded festival periods ({fest_days_in_data} festival days in the current "
                        "dataset window)."
                    ),
                }
                insights.append(festival["insight"])
            else:
                festival = {
                    "supported": False,
                    "days_found": fest_days_in_data,
                    "insight": (
                        "Insufficient historical data - the current dataset records only "
                        f"{fest_days_in_data} festival day(s), not enough to reliably measure "
                        "festival-period demand."
                    ),
                }
        else:
            festival["insight"] = (
                "Insufficient historical data - no festival-period days are recorded in the current dataset."
            )

        return {
            "supported": True,
            "seasons": seasons,
            "festival": festival,
            "insights": insights,
            "note": "Seasonal and festival patterns are computed from actual sales in the uploaded "
                    "dataset. Seasons with too little coverage are reported as insufficient data "
                    "rather than estimated.",
        }

    def _demand_analysis(self, daily: pd.DataFrame, horizon: int,
                         forecast_revenue_total: float) -> dict:
        """Compact analyst summary: historical vs forecast demand (units),
        demand change %, trend and a plain-language business insight."""
        if daily is None or daily.empty:
            return {"available": False, "message": "No sales history available."}
        total_units = float(daily["units"].sum())
        if total_units <= 0:
            return {"available": False,
                    "message": "No sellable volume recorded for this product - demand analysis unavailable."}
        total_amount = float(daily["revenue"].sum())
        days = len(daily)
        # total_units > 0 is guaranteed by the guard above
        avg_unit_price = total_amount / total_units
        historical_daily_units = total_units / max(days, 1)

        # Forecast units = forecast revenue at the realized average unit price
        forecast_units = (forecast_revenue_total / avg_unit_price) if avg_unit_price > 0 else 0.0
        forecast_daily_units = forecast_units / max(horizon, 1)

        # Compare forecast daily volume vs the trailing window of the same length
        window = min(horizon, days)
        trailing_units = float(daily["units"].tail(window).sum())
        trailing_daily = trailing_units / max(window, 1)
        change_pct = ((forecast_daily_units / max(trailing_daily, 1e-9)) - 1) * 100 if trailing_daily > 0 else 0.0
        trend = "up" if change_pct > 3 else ("down" if change_pct < -3 else "stable")

        if trend == "up":
            insight = (
                f"Demand is expected to increase over the next {horizon} days "
                f"(~{forecast_daily_units:,.1f} units/day), suggesting inventory should be "
                "monitored closely."
            )
        elif trend == "down":
            insight = (
                f"Demand is expected to soften over the next {horizon} days "
                f"(~{forecast_daily_units:,.1f} units/day), suggesting conservative restocking."
            )
        else:
            insight = (
                f"Demand is expected to remain stable over the next {horizon} days "
                f"(~{forecast_daily_units:,.1f} units/day)."
            )

        return {
            "available": True,
            "historical_units": round(total_units, 1),
            "historical_days": days,
            "avg_daily_units": round(historical_daily_units, 2),
            "forecast_units": round(forecast_units, 1),
            "forecast_daily_units": round(forecast_daily_units, 2),
            "demand_change_pct": round(change_pct, 2),
            "trend": trend,
            "avg_unit_price": round(avg_unit_price, 2),
            "insight": insight,
        }

    def _forecast_confidence(self, points: list) -> float:
        """Forecast confidence from the 80% confidence band width (narrow band
        = higher confidence)."""
        if not points:
            return None
        bands = [max(p.get("yhat_upper", 0) - p.get("yhat_lower", 0), 0) / max(p.get("yhat", 0), 1e-6)
                 for p in points if p.get("yhat") is not None and p.get("yhat", 0) > 0]
        band_pct = float(np.mean(bands)) * 100 if bands else 25.0
        return round(max(0, min(98, 100 - band_pct)), 1)

    def _build_response(self, product, horizon, daily, points, history, metrics,
                        cached=False, created_at=None, fallback=False,
                        fallback_reason=None, seasonality=None, demand=None,
                        components=None, business_seasonality=None) -> dict:
        """Assemble the forecast payload, adding the seasonal analysis, compact
        demand analysis, data-coverage labeling and an honest note when the
        requested horizon stretches beyond the available history.

        ``seasonality`` / ``demand`` may be precomputed (and stored in the
        ForecastRun payload at creation) so cache hits never re-scan sales.
        """
        if seasonality is None:
            seasonality = self._seasonality_analysis(daily)
        if demand is None:
            demand = self._demand_analysis(daily, horizon, metrics.get("forecast_revenue_total", 0))
        if components is None:
            components = metrics.get("components")
        if business_seasonality is None:
            business_seasonality = self._business_seasonality(daily, product.id)
        history_days = len(history) if history else (len(daily) if daily is not None else 0)
        # Keep the returned metrics dict flat (KPI values only) - seasonal /
        # demand / component / business-seasonality payloads live at the top
        # level of the response.
        resp_metrics = {k: v for k, v in metrics.items()
                        if k not in ("seasonality", "demand_analysis", "components",
                                     "business_seasonality")}
        resp = {
            "product_id": product.id,
            "product_name": product.name,
            "horizon": horizon,
            "points": points,
            "history": history,
            "metrics": resp_metrics,
            "seasonality": seasonality,
            "demand_analysis": demand,
            "business_seasonality": business_seasonality,
            "components": components,
            "data_coverage": DATA_COVERAGE,
            "insufficient_data": False,
            "cached": cached,
        }
        if created_at:
            resp["created_at"] = created_at
        if fallback:
            resp["fallback"] = True
            resp["fallback_reason"] = fallback_reason
        # Honest limitation: a horizon longer than the observed history is an
        # extrapolation, not a measured forecast.
        if horizon > history_days:
            resp["horizon_note"] = (
                f"The {horizon}-day horizon exceeds the available sales history "
                f"({history_days} days). Values beyond day {history_days} are extrapolations "
                "with reduced confidence - use them only for directional planning."
            )
        return resp

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def _load_cached(self, product_id: int, horizon: int):
        """Return a fresh-enough cached forecast run for this product, if any."""
        run = (
            self.db.query(ForecastRun)
            .filter(ForecastRun.product_id == product_id, ForecastRun.horizon == horizon)
            .order_by(ForecastRun.created_at.desc())
            .first()
        )
        if not run:
            return None
        age = datetime.utcnow() - (run.created_at.replace(tzinfo=None) if run.created_at else datetime.utcnow())
        if age.total_seconds() > self.CACHE_MAX_AGE_HOURS * 3600:
            return None
        try:
            return {
                "points": json.loads(run.points),
                "history": json.loads(run.history),
                "metrics": json.loads(run.metrics),
                "created_at": run.created_at.isoformat() if run.created_at else None,
            }
        except (json.JSONDecodeError, TypeError):
            return None

    def _serve_cached(self, product, horizon: int, cached: dict) -> dict:
        """Serve a cached forecast run.

        Runs created by this build store the seasonality + demand payloads in
        the metrics JSON, so a full cache hit needs ZERO sales-table queries.
        Older cached runs (created before this feature) fall back to computing
        those two payloads from the daily series exactly once.
        """
        metrics = dict(cached["metrics"])
        if metrics.get("forecast_confidence") is None:
            metrics["forecast_confidence"] = self._forecast_confidence(cached["points"])
        stored_seasonality = metrics.get("seasonality")
        stored_demand = metrics.get("demand_analysis")
        stored_components = metrics.get("components")
        stored_business = metrics.get("business_seasonality")
        if isinstance(stored_seasonality, dict) and isinstance(stored_demand, dict):
            return self._build_response(
                product, horizon, None, cached["points"], cached["history"],
                metrics, cached=True, created_at=cached["created_at"],
                seasonality=stored_seasonality, demand=stored_demand,
                components=stored_components, business_seasonality=stored_business,
            )
        # Legacy cache entry: compute the payloads once (single product scan).
        daily = self._daily_series(product.id)
        return self._build_response(
            product, horizon, daily, cached["points"], cached["history"],
            metrics, cached=True, created_at=cached["created_at"],
            seasonality=stored_seasonality if isinstance(stored_seasonality, dict) else None,
            demand=stored_demand if isinstance(stored_demand, dict) else None,
            components=stored_components if isinstance(stored_components, list) else None,
            business_seasonality=stored_business if isinstance(stored_business, dict) else None,
        )

    def forecast_product(self, product_id: int, horizon: int = DEFAULT_HORIZON,
                         force: bool = False, user_id: int = None) -> dict:
        """Forecast demand for one product with confidence intervals.

        Returns points (forecast), history (actuals), metrics, seasonal
        analysis, a compact demand analysis, data-coverage labeling and a flag
        describing whether a real Prophet fit or the fast fallback was used.
        Cache hits with stored payloads never re-scan the sales table.
        """
        product = self.db.query(Product).filter(Product.id == product_id).first()
        if not product:
            raise ValueError("Product not found")

        horizon = max(7, min(horizon, self.MAX_HORIZON))

        # Fast path: a fresh cached run (with the stored decomposition) avoids
        # the sales scan entirely. Legacy runs predating the decomposition
        # feature are refit once so components are always available.
        if not force:
            cached = self._load_cached(product_id, horizon)
            if cached and isinstance(cached["metrics"].get("components"), list) \
                    and isinstance(cached["metrics"].get("business_seasonality"), dict):
                return self._serve_cached(product, horizon, cached)

        daily = self._daily_series(product_id)
        if len(daily) < self.MIN_TREND_POINTS:
            return {
                "product_id": product_id,
                "product_name": product.name,
                "horizon": horizon,
                "points": [],
                "history": [],
                "metrics": {},
                "seasonality": self._seasonality_analysis(daily),
                "demand_analysis": self._demand_analysis(daily, horizon, 0.0),
                "business_seasonality": self._business_seasonality(daily, product_id),
                "components": None,
                "data_coverage": DATA_COVERAGE,
                "insufficient_data": True,
                "cached": False,
                "recommendation": (
                    f"Not enough sales history for '{product.name}' to run a demand forecast. "
                    f"Need at least {self.MIN_HISTORY_DAYS} days of sales data; currently "
                    f"available: {len(daily)} days. Generate sales activity or upload a dataset "
                    "with transactions to enable Prophet forecasting."
                ),
            }

        result = self._fit_prophet(daily, horizon)
        if result is None:
            # Fall back to the fast trend if Prophet cannot fit (too little history
            # or an unavailable STAN backend).
            fallback = self._quick_trend(daily, horizon, include_points=True)
            if fallback is None:
                return {
                    "product_id": product_id,
                    "product_name": product.name,
                    "horizon": horizon,
                    "points": [],
                    "history": [],
                    "metrics": {},
                    "seasonality": self._seasonality_analysis(daily),
                    "demand_analysis": self._demand_analysis(daily, horizon, 0.0),
                    "business_seasonality": self._business_seasonality(daily, product_id),
                    "components": None,
                    "data_coverage": DATA_COVERAGE,
                    "insufficient_data": True,
                    "cached": False,
                    "recommendation": f"Insufficient sales history for '{product.name}' to forecast demand.",
                }
            points = fallback.pop("points") or []
            fallback["forecast_confidence"] = self._forecast_confidence(points)
            return self._build_response(
                product, horizon, daily, points,
                [{"date": d.strftime("%Y-%m-%d"), "actual": round(float(v), 2)}
                 for d, v in zip(daily["date"], daily["revenue"])],
                fallback, fallback=True,
                fallback_reason=("limited_history" if len(daily) < self.MIN_HISTORY_DAYS
                                 else "prophet_unavailable"),
            )

        # Persist the forecast run for caching (seasonality + demand payloads
        # stored so later cache hits never re-scan the sales table).
        metrics = {k: v for k, v in result.items()
                   if k not in ("points", "history", "trained_on_days")}
        metrics["forecast_confidence"] = self._forecast_confidence(result["points"])
        seasonality = self._seasonality_analysis(daily)
        demand = self._demand_analysis(daily, horizon, metrics.get("forecast_revenue_total", 0))
        business_seasonality = self._business_seasonality(daily, product_id)
        metrics["seasonality"] = seasonality
        metrics["demand_analysis"] = demand
        metrics["business_seasonality"] = business_seasonality
        run = ForecastRun(
            product_id=product_id,
            horizon=horizon,
            points=json.dumps(result["points"]),
            history=json.dumps(result["history"]),
            metrics=json.dumps(metrics),
            model_info=f"Prophet weekly-seasonality, {result['trained_on_days']} days history",
            created_by=user_id,
        )
        self.db.add(run)
        self.db.commit()

        return self._build_response(
            product, horizon, daily, result["points"], result["history"], metrics,
            seasonality=seasonality, demand=demand,
        )

    def get_demand_signal(self, product_id: int, horizon: int = DEFAULT_HORIZON) -> dict:
        """Lightweight demand signal for the pricing engine.

        Prefers a fresh cached Prophet forecast; otherwise computes the fast
        linear trend. Never triggers a full Prophet re-fit (keeps optimize fast).
        """
        cached = self._load_cached(product_id, horizon)
        if cached:
            return {
                "trend": cached["metrics"].get("trend", "stable"),
                "growth_pct": cached["metrics"].get("growth_pct", 0),
                "avg_daily_revenue": cached["metrics"].get("avg_daily_revenue", 0),
                "forecast_revenue_total": cached["metrics"].get("forecast_revenue_total", 0),
                "source": "prophet",
            }
        daily = self._daily_series(product_id)
        trend = self._quick_trend(daily, horizon)
        if trend is None:
            return {"trend": "unavailable", "growth_pct": 0, "source": "none"}
        return trend

    def forecastable_count(self) -> int:
        """Count products with enough sales history to forecast (single cheap query)."""
        from sqlalchemy import func, distinct

        days_per_product = (
            self.db.query(Sale.product_id, func.count(distinct(Sale.sale_date)).label("days"))
            .group_by(Sale.product_id)
            .subquery()
        )
        return self.db.query(func.count(days_per_product.c.product_id))\
            .filter(days_per_product.c.days >= self.MIN_HISTORY_DAYS).scalar() or 0

    def portfolio_summary(self, horizon: int = DEFAULT_HORIZON) -> dict:
        """Quick demand outlook across the whole catalog (fast, no Prophet fits)."""
        horizon = max(7, min(horizon, self.MAX_HORIZON))
        products = self.db.query(Product).all()
        rows = []
        total_forecast = 0.0
        for p in products:
            daily = self._daily_series(p.id)
            signal = self._quick_trend(daily, horizon)
            if signal is None:
                continue
            total_forecast += signal["forecast_revenue_total"]
            rows.append({
                "product_id": p.id,
                "product_name": p.name,
                "category": p.category or "Uncategorized",
                "current_price": round(p.current_price, 2),
                **{k: v for k, v in signal.items() if k != "points"},
            })

        rows.sort(key=lambda r: r["growth_pct"], reverse=True)
        top_growing = [r for r in rows if r["trend"] == "up"][:5]
        top_declining = [r for r in reversed(rows) if r["trend"] == "down"][:5]

        return {
            "horizon": horizon,
            "products_analyzed": len(rows),
            "total_forecast_revenue": round(total_forecast, 2),
            "top_growing": top_growing,
            "top_declining": top_declining,
            "products": rows,
        }
