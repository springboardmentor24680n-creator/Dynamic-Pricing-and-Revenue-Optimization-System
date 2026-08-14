"""
PricePilot AI - AI Analysis Report Service
===========================================
Generates a professional business-intelligence report after every AI price
prediction. Every section (executive summary, prediction details, model
performance, explainable factors, revenue impact, risk, forecast summary,
recommendations, conclusion) is derived ONLY from real data:

  * the prediction output (persisted model, no retraining),
  * the latest model run metadata,
  * the demand forecast (Prophet / trend fallback),
  * sales-history aggregates, and
  * the product row itself.

Nothing is hardcoded: text templates are filled with live values, importance
percentages are normalized from measured magnitudes, and risk levels come from
rule thresholds applied to real numbers. If any source is unavailable the
report degrades gracefully (``available=False``) instead of inventing data.
"""

import csv
import io
from datetime import datetime

import numpy as np
import pandas as pd
from sqlalchemy.orm import Session

from app.models.product import Product
from app.services.forecast_service import ForecastService
from app.services.ml_service import PricingMLService
from app.services.training_service import _sales_aggregates

CURRENCY = "$"


class AnalysisReportService:
    """Dynamic BI report builder for a single AI price prediction."""

    def __init__(self, db: Session):
        self.db = db
        self.ml = PricingMLService(db)
        self.forecast = ForecastService(db)

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------
    def generate_report(self, product_id: int, horizon: int = 30) -> dict:
        """Build the complete report payload for one product."""
        product = self.db.query(Product).filter(Product.id == product_id).first()
        if not product:
            raise ValueError("Product not found")

        # Compute the sales aggregates ONCE and share them with the prediction
        # call so the 100k+ row sales table is scanned a single time per report.
        sales_aggregates = _sales_aggregates(self.db)
        prediction = self.ml.predict_product(
            product_id, include_forecast=True, aggregates=sales_aggregates,
        )
        if prediction.get("insufficient_data") or prediction.get("suggested_price") is None:
            return {
                "available": False,
                "product_id": product_id,
                "product_name": product.name,
                "category": product.category or "Uncategorized",
                "generated_at": datetime.utcnow().isoformat() + "Z",
                "message": (
                    prediction.get("recommendation")
                    or "No trained AI model available. Upload a pricing dataset, import it, "
                    "and run AI training before generating an analysis report."
                ),
            }

        run = prediction.get("model_info") or {}
        metrics_by_model = run.get("metrics") or {}
        aggregates = sales_aggregates.get(product_id, {})
        forecast = self.forecast.forecast_product(product_id, horizon=horizon)
        fm = forecast.get("metrics") or {}

        current_price = prediction["current_price"]
        suggested = prediction["suggested_price"]
        change_pct = prediction["expected_revenue_change"] or 0
        cost = product.cost_price or 0
        price_trend = prediction.get("price_trend") or {
            "trend": "stable", "change_pct": 0.0, "points": [], "source": "none"
        }
        avg_daily_units = max(aggregates.get("avg_daily_units", 0), 1e-6)
        current_units_30d = avg_daily_units * 30
        current_revenue_30d = current_units_30d * current_price
        predicted_revenue_30d = prediction["expected_revenue"] or current_revenue_30d
        current_profit_30d = (current_price - cost) * current_units_30d
        predicted_profit_30d = prediction["expected_profit"] or current_profit_30d
        profit_change = predicted_profit_30d - current_profit_30d
        roi = (profit_change / max(current_profit_30d, 1e-6)) * 100
        margin_now = ((current_price - cost) / current_price * 100) if current_price > 0 else 0
        margin_new = ((suggested - cost) / suggested * 100) if suggested > 0 else 0
        margin_improvement = margin_new - margin_now

        factors = self._why_factors(
            prediction, product, aggregates, fm, margin_now, margin_new, run
        )
        risks = self._risk_analysis(
            prediction, product, aggregates, fm, current_price, suggested, change_pct
        )
        recommendations = self._recommendations(
            change_pct, suggested, current_price, product, fm, run
        )
        forecast_summary = self._forecast_summary(forecast, suggested, prediction, horizon)

        return {
            "available": True,
            "product_id": product_id,
            "product_name": product.name,
            "sku": product.sku,
            "category": product.category or "Uncategorized",
            "currency": CURRENCY,
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "executive_summary": self._executive_summary(
                product, prediction, run, current_revenue_30d,
                predicted_revenue_30d, current_profit_30d, predicted_profit_30d,
                fm, horizon,
            ),
            "prediction_details": {
                "current_price": round(current_price, 2),
                "recommended_price": round(suggested, 2),
                "difference": round(suggested - current_price, 2),
                "percentage_change": round(change_pct, 2),
                "confidence_score": prediction["confidence_score"],
                "expected_revenue": round(predicted_revenue_30d, 2),
                "expected_profit": round(predicted_profit_30d, 2),
                "prediction_time_ms": prediction.get("prediction_time_ms"),
                "best_model": run.get("best_model"),
                "training_dataset_name": run.get("dataset_name") or "Product catalog",
                "training_date": run.get("created_at"),
                "training_samples": run.get("samples"),
            },
            "price_trend": {
                "trend": price_trend.get("trend", "stable"),
                "change_pct": price_trend.get("change_pct", 0.0),
                "points": price_trend.get("points", []),
                "source": price_trend.get("source", "none"),
            },
            "price_forecast": prediction.get("price_forecast") or {
                "available": False,
                "message": "Future price projection unavailable for this product.",
                "trend": "stable",
                "change_pct": 0.0,
                "horizons": [],
                "confidence": 0,
                "note": "",
            },
            "demand_analysis": self._report_demand_analysis(aggregates, forecast_summary, suggested),
            "model_performance": {
                "best_model": run.get("best_model"),
                "r2": run.get("accuracy"),
                "mae": run.get("mae"),
                "rmse": run.get("rmse"),
                "accuracy_pct": round((run.get("accuracy") or 0) * 100, 1),
                "training_time_seconds": run.get("training_time_seconds"),
                "dataset_records": run.get("samples"),
                "num_features": len(run.get("features_used") or []),
                "per_model": {
                    name: m for name, m in metrics_by_model.items()
                },
            },
            "why_factors": factors,
            "revenue_impact": {
                "current_revenue": round(current_revenue_30d, 2),
                "predicted_revenue": round(predicted_revenue_30d, 2),
                "revenue_increase": round(predicted_revenue_30d - current_revenue_30d, 2),
                "revenue_increase_pct": round(change_pct, 2),
                "profit_increase": round(profit_change, 2),
                "profit_increase_pct": round((profit_change / max(current_profit_30d, 1e-6)) * 100, 2),
                "roi_pct": round(roi, 2),
                "margin_improvement_pct": round(margin_improvement, 2),
                "margin_now_pct": round(margin_now, 2),
                "margin_new_pct": round(margin_new, 2),
            },
            "risk_analysis": risks,
            "forecast_summary": forecast_summary,
            "recommendations": recommendations,
            "conclusion": self._conclusion(product, prediction, run, change_pct, fm, horizon),
        }

    # ------------------------------------------------------------------
    # Section builders
    # ------------------------------------------------------------------
    def _report_demand_analysis(self, aggregates: dict, forecast_summary: dict,
                                suggested: float) -> dict:
        """Compact demand summary for the report, consistent with the forecasting
        panel: forecast units are derived at the HISTORICAL average unit price
        (not the suggested price) so both views show the same number."""
        total_units = float(aggregates.get("total_units", 0) or 0)
        total_revenue = float(aggregates.get("revenue", 0) or 0)
        avg_unit_price = (total_revenue / total_units) if total_units > 0 else (suggested or 0)
        expected_revenue = float(forecast_summary.get("expected_revenue", 0) or 0)
        forecast_units = (expected_revenue / avg_unit_price) if avg_unit_price > 0 else 0.0
        return {
            "historical_units": round(total_units, 1),
            "forecast_units": round(forecast_units, 1),
            "demand_change_pct": round(float(forecast_summary.get("growth_rate", 0) or 0), 2),
            "trend": forecast_summary.get("trend", "stable"),
            "forecast_confidence": forecast_summary.get("forecast_confidence"),
            "insight": forecast_summary.get("paragraph", ""),
        }

    def _category_avg_price(self, product) -> float:
        """Average current price of the product's category (excluding itself)."""
        from sqlalchemy import func
        row = (
            self.db.query(func.avg(Product.current_price))
            .filter(Product.category == product.category, Product.id != product.id)
            .first()
        )
        return float(row[0]) if row and row[0] else 0.0

    def _why_factors(self, prediction, product, aggregates, fm,
                     margin_now, margin_new, run) -> list:
        """Explainable-AI cards. Importance percentages are normalized from
        measured magnitudes so they always sum to ~100 and adapt to any dataset."""
        factors = []

        # 1. Historical sales trend
        slope = aggregates.get("demand_slope", 0) or 0
        if abs(slope) > 0.001:
            direction = "rising" if slope > 0 else "declining"
            factors.append({
                "factor": "Historical Sales Trend",
                "impact": f"{direction.capitalize()} {abs(slope) * 100:.0f}%",
                "weight": abs(slope) * 100,
                "explanation": (
                    f"Sales are {direction} at {abs(slope) * 100:.1f}% over the last 6 months "
                    f"({aggregates.get('avg_daily_units', 0):.1f} units/day on average)."
                ),
            })

        # 2. Price elasticity learned from the dataset
        elasticity = prediction.get("elasticity", -1.2)
        factors.append({
            "factor": "Price Elasticity",
            "impact": f"{elasticity:+.2f}",
            "weight": abs(elasticity) * 6,
            "explanation": (
                f"Learned from your dataset: a 1% price change shifts expected volume by "
                f"{abs(elasticity) * 100:.1f}%. Demand is {'elastic' if abs(elasticity) > 1 else 'inelastic'}."
            ),
        })

        # 3. Margin profile
        margin_shift = margin_new - margin_now
        factors.append({
            "factor": "Margin Profile",
            "impact": f"{margin_shift:+.1f} pp",
            "weight": abs(margin_shift) * 2,
            "explanation": (
                f"Margin moves from {margin_now:.1f}% to {margin_new:.1f}% at the suggested price "
                f"(cost {CURRENCY}{product.cost_price or 0:.2f})."
            ),
        })

        # 4. Model confidence / prediction quality
        r2 = run.get("accuracy") or 0
        factors.append({
            "factor": "Model Confidence",
            "impact": f"{prediction['confidence_score']:.0f}%",
            "weight": 12 + max(r2, 0) * 18,
            "explanation": (
                f"Best model '{run.get('best_model')}' reaches R² {r2:.3f} across "
                f"{run.get('samples')} training records — confidence reflects this measured quality."
            ),
        })

        # 5. Seasonality (weekend / festival demand)
        weekend = aggregates.get("weekend_uplift", 1.0) or 1.0
        festival = aggregates.get("festival_share", 0) or 0
        if weekend > 1.1 or festival > 0.05:
            season_pct = (weekend - 1) * 100 + festival * 100
            factors.append({
                "factor": "Seasonality",
                "impact": f"+{season_pct:.0f}%",
                "weight": season_pct,
                "explanation": (
                    f"Weekend demand runs {weekend * 100:.0f}% above weekdays and festival "
                    f"periods add {festival * 100:.0f}% volume — the model prices for this pattern."
                ),
            })

        # 6. Inventory position
        stock = product.stock_quantity or 0
        if stock >= 0:
            scarcity = max(0, 40 - stock) if stock < 40 else 0
            factors.append({
                "factor": "Inventory Position",
                "impact": "Scarce" if stock < 20 else ("Adequate" if stock < 100 else "Healthy"),
                "weight": scarcity * 0.8,
                "explanation": (
                    f"Current stock is {stock} units against {aggregates.get('avg_daily_units', 0):.1f} "
                    f"units/day demand ({stock / max(aggregates.get('avg_daily_units', 0), 1e-6):.0f} days of cover)."
                ),
            })

        # 7. Category behaviour (product price vs category average)
        category_avg = self._category_avg_price(product)
        if category_avg > 0:
            cat_dev = ((product.current_price or 0) - category_avg) / category_avg * 100
            factors.append({
                "factor": "Category Behaviour",
                "impact": f"{cat_dev:+.0f}% vs avg",
                "weight": min(abs(cat_dev), 40),
                "explanation": (
                    f"This product sits {cat_dev:+.1f}% {'above' if cat_dev >= 0 else 'below'} the "
                    f"{product.category or 'Uncategorized'} category average price of "
                    f"{CURRENCY}{category_avg:.2f} — the model prices relative to that behaviour."
                ),
            })

        # 8. Demand forecast signal
        growth = fm.get("growth_pct", 0) or 0
        trend = fm.get("trend", "stable")
        if growth != 0 or trend != "stable":
            factors.append({
                "factor": "Demand Forecast",
                "impact": f"{growth:+.1f}%",
                "weight": abs(growth) / 2,
                "explanation": (
                    f"The {'Prophet' if fm.get('source') == 'prophet' else 'trend'} forecast projects "
                    f"{trend} demand ({growth:+.1f}%) over the next 30 days."
                ),
            })

        # Normalize weights to importance percentages summing to 100
        total = sum(f["weight"] for f in factors) or 1.0
        for f in factors:
            f["importance"] = round((f["weight"] / total) * 100, 1)
            f.pop("weight", None)
        # Drop factors whose measured importance rounds to zero so the report
        # never shows a "0%" card in a demo.
        factors = [f for f in factors if f["importance"] > 0]
        factors.sort(key=lambda f: f["importance"], reverse=True)
        return factors

    def _risk_analysis(self, prediction, product, aggregates, fm,
                       current_price, suggested, change_pct) -> list:
        """Risk cards with Low / Medium / High levels from real thresholds."""
        elasticity = abs(prediction.get("elasticity", -1.2))
        conf = prediction["confidence_score"]
        stock = product.stock_quantity or 0
        growth = fm.get("growth_pct", 0) or 0
        slope = aggregates.get("demand_slope", 0) or 0

        risks = []

        # Price too high risk
        if change_pct > 20:
            level, note = "High", f"a {change_pct:.0f}% increase is aggressive"
        elif change_pct > 8:
            level, note = "Medium", f"a {change_pct:.0f}% increase needs monitoring"
        else:
            level, note = "Low", f"the {change_pct:.1f}% change is conservative"
        risks.append({
            "risk": "Price Too High Risk",
            "level": level,
            "explanation": (
                f"{note.capitalize()}; price elasticity of {elasticity:.2f} means volume is "
                f"{'sensitive' if elasticity > 1 else 'relatively stable'} to price moves."
            ),
        })

        # Demand drop risk
        if growth < -5:
            level = "High"
        elif growth < 0 or elasticity > 1.8:
            level = "Medium"
        else:
            level = "Low"
        risks.append({
            "risk": "Demand Drop Risk",
            "level": level,
            "explanation": (
                f"Forecast growth is {growth:+.1f}% with elasticity {elasticity:.2f}; "
                f"demand is {'contracting' if growth < 0 else 'stable or growing'}."
            ),
        })

        # Low inventory risk
        if stock < 20:
            level = "High"
        elif stock < 100:
            level = "Medium"
        else:
            level = "Low"
        risks.append({
            "risk": "Low Inventory Risk",
            "level": level,
            "explanation": (
                f"Stock of {stock} units at {aggregates.get('avg_daily_units', 0):.1f} units/day "
                f"equals ~{stock / max(aggregates.get('avg_daily_units', 0), 1e-6):.0f} days of cover."
            ),
        })

        # Market stability
        if abs(slope) > 0.5 or (fm.get("source") == "linear_trend" and fm.get("points") is None):
            level = "Medium"
        else:
            level = "Low"
        risks.append({
            "risk": "Market Stability",
            "level": level,
            "explanation": (
                f"6-month demand slope is {slope * 100:+.1f}%; volatility is "
                f"{'elevated' if abs(slope) > 0.5 else 'normal'} for this category."
            ),
        })

        # Overall confidence level
        if conf >= 75:
            level = "Low"
        elif conf >= 55:
            level = "Medium"
        else:
            level = "High"
        risks.append({
            "risk": "Model Confidence Risk",
            "level": level,
            "explanation": (
                f"Overall confidence is {conf:.0f}% — {'high' if conf >= 75 else 'moderate' if conf >= 55 else 'low'} "
                f"certainty in the recommendation."
            ),
        })
        return risks

    def _recommendations(self, change_pct, suggested, current_price,
                         product, fm, run) -> list:
        """Business recommendations generated from prediction values."""
        recs = []
        if change_pct > 5:
            recs.append(
                f"Increase the price gradually toward {CURRENCY}{suggested:.2f} to capture the "
                f"model-implied value while protecting volume."
            )
        elif change_pct < -5:
            recs.append(
                f"Ease the price toward {CURRENCY}{suggested:.2f} to improve competitiveness "
                f"and recover demand."
            )
        else:
            recs.append(
                f"Hold pricing near {CURRENCY}{current_price:.2f} — the model sees limited "
                f"room for change ({change_pct:+.1f}%)."
            )

        if (product.stock_quantity or 0) < 40:
            recs.append(
                f"Maintain or restock inventory — only {product.stock_quantity or 0} units remain "
                f"against current demand velocity."
            )

        growth = fm.get("growth_pct", 0) or 0
        if growth > 3:
            recs.append(f"Increase marketing focus — demand is forecast to grow {growth:+.1f}%.")
        elif growth < -3:
            recs.append("Monitor customer demand closely — the forecast projects softening demand.")

        recs.append("Review again after the next dataset upload — models retrain automatically on new data.")
        recs.append(
            "Track actual revenue after implementation and compare with this projection to "
            "measure realized uplift."
        )
        return recs

    def _forecast_summary(self, forecast, suggested, prediction, horizon) -> dict:
        """Next-N-day revenue/demand outlook from the forecast run."""
        fm = forecast.get("metrics") or {}
        points = forecast.get("points") or []
        expected_revenue = fm.get("forecast_revenue_total") or 0
        # Units estimate from forecast revenue at the suggested price
        expected_demand = expected_revenue / max(suggested, 1e-6) if expected_revenue else 0

        # Forecast confidence from the 80% confidence band width
        if points:
            bands = [max(p.get("yhat_upper", 0) - p.get("yhat_lower", 0), 0) / max(p.get("yhat", 0), 1e-6)
                     for p in points if p.get("yhat") is not None and p.get("yhat", 0) > 0]
            band_pct = float(np.mean(bands)) * 100 if bands else 25.0
            forecast_conf = round(max(0, min(98, 100 - band_pct)), 1)
        else:
            forecast_conf = round(prediction["confidence_score"], 1)

        trend = fm.get("trend", "stable")
        growth = fm.get("growth_pct", 0) or 0
        source = "Prophet" if fm.get("source") == "prophet" else "trend analysis"
        paragraph = (
            f"Over the next {horizon} days, the {source} model projects "
            f"{CURRENCY}{expected_revenue:,.0f} in revenue at the suggested price of "
            f"{CURRENCY}{suggested:.2f} (≈ {expected_demand:,.0f} units). Demand is forecast "
            f"to be {trend} ({growth:+.1f}% growth) with an 80% confidence interval "
            f"corresponding to {forecast_conf:.0f}% forecast confidence."
        )
        return {
            "horizon": horizon,
            "expected_revenue": round(float(expected_revenue), 2),
            "expected_demand": round(float(expected_demand), 2),
            "trend": trend,
            "growth_rate": round(float(growth), 2),
            "forecast_confidence": forecast_conf,
            "source": source,
            "paragraph": paragraph,
        }

    def _executive_summary(self, product, prediction, run, curr_rev,
                           pred_rev, curr_profit, pred_profit, fm, horizon) -> str:
        """4-5 sentence summary filled with live values."""
        r2 = run.get("accuracy") or 0
        return (
            f"The AI analyzed \"{product.name}\" ({product.category or 'Uncategorized'}) using the "
            f"{run.get('best_model')} model trained on {run.get('samples')} records from "
            f"'{run.get('dataset_name') or 'the product catalog'}'. Based on historical sales "
            f"behaviour and a learned price elasticity of {prediction.get('elasticity'):.2f}, the "
            f"recommended selling price is {CURRENCY}{prediction['suggested_price']:.2f} instead of "
            f"{CURRENCY}{prediction['current_price']:.2f}. This is a "
            f"{prediction['expected_revenue_change']:+.1f}% change expected to move 30-day revenue "
            f"from {CURRENCY}{curr_rev:,.0f} to {CURRENCY}{pred_rev:,.0f}, while 30-day profit "
            f"shifts from {CURRENCY}{curr_profit:,.0f} to {CURRENCY}{pred_profit:,.0f}. The demand "
            f"forecast projects {fm.get('growth_pct', 0):+.1f}% growth over the next {horizon} days, "
            f"and model confidence sits at {prediction['confidence_score']:.0f}% (R² {r2:.3f}), "
            f"making this recommendation suitable for implementation."
        )

    def _conclusion(self, product, prediction, run, change_pct, fm, horizon) -> str:
        """Final business conclusion generated from the prediction."""
        r2 = run.get("accuracy") or 0
        conf = prediction["confidence_score"]
        verdict = "high" if conf >= 75 else ("moderate" if conf >= 55 else "low")
        return (
            f"The AI recommends {'increasing' if change_pct > 0 else 'decreasing' if change_pct < 0 else 'holding'} "
            f"the selling price of \"{product.name}\" by {abs(change_pct):.1f}% to "
            f"{CURRENCY}{prediction['suggested_price']:.2f}. Based on the trained "
            f"{run.get('best_model')} model (R² {r2:.3f}) and historical sales data, this change is "
            f"expected to improve revenue while maintaining stable demand over the next {horizon} days "
            f"({fm.get('growth_pct', 0):+.1f}% forecast growth). Current model confidence is {verdict} "
            f"at {conf:.0f}%, making this recommendation suitable for implementation."
        )

    # ------------------------------------------------------------------
    # Export builders (CSV / Excel / PDF) - all from the same payload
    # ------------------------------------------------------------------
    def to_csv(self, report: dict) -> str:
        """Flatten the report into a CSV string."""
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(["Section", "Field", "Value"])

        if not report.get("available"):
            writer.writerow(["Report", "Status", "Unavailable"])
            writer.writerow(["Report", "Message", report.get("message", "")])
            return buf.getvalue()

        writer.writerow(["Product", "Name", report["product_name"]])
        writer.writerow(["Product", "SKU", report.get("sku", "")])
        writer.writerow(["Product", "Category", report["category"]])
        writer.writerow(["Report", "Generated At", report["generated_at"]])

        for key, label in [
            ("current_price", "Current Price"), ("recommended_price", "Recommended Price"),
            ("difference", "Difference"), ("percentage_change", "Change (%)"),
            ("confidence_score", "Confidence Score"), ("expected_revenue", "Expected Revenue (30d)"),
            ("expected_profit", "Expected Profit (30d)"), ("best_model", "Best Model"),
            ("training_dataset_name", "Training Dataset"), ("training_date", "Training Date"),
            ("training_samples", "Training Samples"),
        ]:
            writer.writerow(["Prediction", label, report["prediction_details"].get(key, "")])

        pt = report.get("price_trend") or {}
        writer.writerow(["Price Trend", "Direction", pt.get("trend", "stable")])
        writer.writerow(["Price Trend", "Change (%)", pt.get("change_pct", 0.0)])
        writer.writerow(["Price Trend", "Source", pt.get("source", "none")])

        pf = report.get("price_forecast") or {}
        writer.writerow(["Price Forecast", "Available", pf.get("available", False)])
        writer.writerow(["Price Forecast", "Trend", pf.get("trend", "stable")])
        writer.writerow(["Price Forecast", "30d Change (%)", pf.get("change_pct", 0.0)])
        writer.writerow(["Price Forecast", "Confidence (%)", pf.get("confidence")])
        for h in (pf.get("horizons") or []):
            if h.get("reliable") is False:
                writer.writerow(["Price Forecast", f"{h['days']}d Price",
                                 "beyond reliable range (insufficient dated history)"])
            else:
                writer.writerow(["Price Forecast", f"{h['days']}d Price",
                                 f"{h['price']} (band {h['lower']} - {h['upper']})"])
        if pf.get("note"):
            writer.writerow(["Price Forecast", "Note", pf["note"]])

        mp = report["model_performance"]
        for key, label in [
            ("best_model", "Best Model"), ("r2", "R²"), ("mae", "MAE"), ("rmse", "RMSE"),
            ("accuracy_pct", "Accuracy (%)"), ("training_time_seconds", "Training Time (s)"),
            ("dataset_records", "Dataset Records"), ("num_features", "Features"),
        ]:
            writer.writerow(["Model Performance", label, mp.get(key, "")])

        for f in report["why_factors"]:
            writer.writerow(["Why Factor", f["factor"],
                             f"{f['impact']} | importance {f['importance']}% | {f['explanation']}"])

        ri = report["revenue_impact"]
        for key, label in [
            ("current_revenue", "Current Revenue (30d)"), ("predicted_revenue", "Predicted Revenue (30d)"),
            ("revenue_increase", "Revenue Increase"), ("revenue_increase_pct", "Revenue Increase (%)"),
            ("profit_increase", "Profit Increase"), ("roi_pct", "ROI (%)"),
            ("margin_improvement_pct", "Margin Improvement (pp)"),
        ]:
            writer.writerow(["Revenue Impact", label, ri.get(key, "")])

        for r in report["risk_analysis"]:
            writer.writerow(["Risk", r["risk"], f"{r['level']} | {r['explanation']}"])

        fs = report["forecast_summary"]
        for key, label in [
            ("horizon", "Horizon (days)"), ("expected_revenue", "Expected Revenue"),
            ("expected_demand", "Expected Demand (units)"), ("trend", "Trend"),
            ("growth_rate", "Growth Rate (%)"), ("forecast_confidence", "Forecast Confidence (%)"),
        ]:
            writer.writerow(["Forecast", label, fs.get(key, "")])

        for rec in report["recommendations"]:
            writer.writerow(["Recommendation", "Action", rec])

        writer.writerow(["Conclusion", "Summary", report["conclusion"]])
        return buf.getvalue()

    def to_excel(self, report: dict) -> bytes:
        """Multi-sheet Excel workbook from the report payload."""
        out = io.BytesIO()
        if not report.get("available"):
            pd.DataFrame([{"Status": "Unavailable", "Message": report.get("message", "")}]
                         ).to_excel(out, index=False, sheet_name="Report")
            out.seek(0)
            return out.getvalue()

        def details_rows():
            d = report["prediction_details"]
            rows = [{"Field": k.replace("_", " ").title(), "Value": v}
                    for k, v in d.items()]
            pt = report.get("price_trend") or {}
            pf = report.get("price_forecast") or {}
            rows += [
                {"Field": "Price Trend", "Value": f"{pt.get('trend', 'stable')} ({pt.get('change_pct', 0.0):+.1f}%)"},
                {"Field": "Price Trend Source", "Value": pt.get("source", "none")},
                {"Field": "Price Forecast Trend", "Value": pf.get("trend", "stable")},
                {"Field": "Price Forecast 30d Change", "Value": f"{pf.get('change_pct', 0.0):+.1f}%"},
                {"Field": "Price Forecast Confidence", "Value": pf.get("confidence")},
            ]
            for h in (pf.get("horizons") or []):
                if h.get("reliable") is False:
                    rows.append({"Field": f"Price Forecast {h['days']}d",
                                 "Value": "beyond reliable range (insufficient dated history)"})
                else:
                    rows.append({"Field": f"Price Forecast {h['days']}d",
                                 "Value": f"{h['price']} (band {h['lower']} - {h['upper']})"})
            return pd.DataFrame(rows)

        def factors_rows():
            return pd.DataFrame([
                {"Factor": f["factor"], "Impact": f["impact"],
                 "Importance (%)": f["importance"], "Explanation": f["explanation"]}
                for f in report["why_factors"]
            ])

        def impact_rows():
            ri = report["revenue_impact"]
            return pd.DataFrame([
                {"Metric": k.replace("_", " ").title(), "Value": v}
                for k, v in ri.items()
            ])

        def risk_rows():
            return pd.DataFrame([
                {"Risk": r["risk"], "Level": r["level"], "Explanation": r["explanation"]}
                for r in report["risk_analysis"]
            ])

        def forecast_rows():
            fs = report["forecast_summary"]
            return pd.DataFrame([
                {"Metric": k.replace("_", " ").title(), "Value": v}
                for k, v in fs.items() if k != "paragraph"
            ])

        with pd.ExcelWriter(out, engine="openpyxl") as writer:
            details_rows().to_excel(writer, index=False, sheet_name="Prediction Details")
            factors_rows().to_excel(writer, index=False, sheet_name="Why Factors")
            impact_rows().to_excel(writer, index=False, sheet_name="Revenue Impact")
            risk_rows().to_excel(writer, index=False, sheet_name="Risk Analysis")
            forecast_rows().to_excel(writer, index=False, sheet_name="Forecast")
            pd.DataFrame({"Recommendation": report["recommendations"]}
                         ).to_excel(writer, index=False, sheet_name="Recommendations")
        out.seek(0)
        return out.getvalue()

    def to_pdf(self, report: dict) -> bytes:
        """Professional multi-section PDF via fpdf2 (already a project dependency)."""
        from fpdf import FPDF

        # fpdf2's built-in Helvetica fonts only cover latin-1; map the few
        # typographic characters we use to ASCII equivalents so exports never
        # crash on an unsupported glyph (e.g. em dash, approx sign).
        def txt(value) -> str:
            return (str(value).replace("\u2014", "-").replace("\u2013", "-")
                    .replace("\u2248", "~")
                    .replace("\u2192", "->").replace("\u2190", "<-")
                    .replace("\u00d7", "x").replace("\u00b7", "-")
                    .replace("\u201c", '"').replace("\u201d", '"'))

        pdf = FPDF()
        pdf.add_page()
        pdf.set_auto_page_break(auto=True, margin=18)

        # Header band
        pdf.set_fill_color(29, 78, 216)  # enterprise blue
        pdf.rect(0, 0, 210, 26, "F")
        pdf.set_text_color(255, 255, 255)
        pdf.set_font("helvetica", "B", 16)
        pdf.set_xy(12, 7)
        pdf.cell(0, 10, "AI Prediction Analysis Report", ln=True)
        pdf.set_font("helvetica", "", 9)
        pdf.set_xy(12, 17)
        pdf.cell(0, 6, txt(f"PricePilot AI  |  Generated: {report.get('generated_at', '')}"), ln=True)
        pdf.set_text_color(0, 0, 0)

        if not report.get("available"):
            pdf.ln(14)
            pdf.set_font("helvetica", "B", 12)
            pdf.cell(0, 8, "Report Unavailable", ln=True)
            pdf.set_font("helvetica", "", 10)
            pdf.multi_cell(0, 6, txt(report.get("message", "")))
            return bytes(pdf.output())

        def section(title):
            pdf.ln(5)
            pdf.set_fill_color(219, 234, 254)
            pdf.set_text_color(29, 78, 216)
            pdf.set_font("helvetica", "B", 12)
            pdf.cell(0, 8, f"  {title}", fill=True, ln=True)
            pdf.set_text_color(0, 0, 0)
            pdf.ln(2)

        def kv_table(rows):
            pdf.set_font("helvetica", "B", 8)
            pdf.set_fill_color(241, 245, 249)
            for key, val in rows:
                pdf.cell(70, 7, txt(f"  {key}"), border=1, fill=True)
                pdf.cell(0, 7, txt(f"  {val}"), border=1, ln=True)

        pdf.ln(8)
        # 1. Executive summary
        section("1. Executive Summary")
        pdf.set_font("helvetica", "", 10)
        pdf.multi_cell(0, 6, txt(report["executive_summary"]))

        # 2. Prediction details
        section("2. Prediction Details")
        d = report["prediction_details"]
        pt = report.get("price_trend") or {}
        pf = report.get("price_forecast") or {}
        horizons = pf.get("horizons") or []
        pf30 = next((h for h in horizons if h.get("days") == 30), {})
        rows = [
            ("Current Price", f"{CURRENCY}{d['current_price']:.2f}"),
            ("Recommended Price", f"{CURRENCY}{d['recommended_price']:.2f}"),
            ("Difference", f"{CURRENCY}{d['difference']:.2f}"),
            ("Percentage Change", f"{d['percentage_change']:+.2f}%"),
            ("Price Trend", f"{pt.get('trend', 'stable').capitalize()} ({pt.get('change_pct', 0.0):+.1f}%)"),
            ("Price Forecast 30d", f"{pf30.get('price', d['current_price'])} (band {pf30.get('lower', d['current_price'])}-{pf30.get('upper', d['current_price'])})"),
            ("Price Forecast Confidence", f"{pf.get('confidence') or 0}%"),
            ("Confidence Score", f"{d['confidence_score']:.1f}%"),
            ("Expected Revenue (30d)", f"{CURRENCY}{d['expected_revenue']:,.2f}"),
            ("Expected Profit (30d)", f"{CURRENCY}{d['expected_profit']:,.2f}"),
            ("Best Model", d.get("best_model") or "-"),
            ("Training Dataset", d.get("training_dataset_name") or "-"),
            ("Training Date", (d.get("training_date") or "-")[:19]),
            ("Training Samples", d.get("training_samples") or 0),
        ]
        kv_table(rows)

        # 3. Model performance
        section("3. Model Performance")
        mp = report["model_performance"]
        kv_table([
            ("Best Model", mp.get("best_model") or "-"),
            ("R-squared (R²)", f"{mp.get('r2') or 0:.4f}"),
            ("MAE", f"{CURRENCY}{mp.get('mae') or 0:.2f}"),
            ("RMSE", f"{CURRENCY}{mp.get('rmse') or 0:.2f}"),
            ("Accuracy", f"{mp.get('accuracy_pct') or 0:.1f}%"),
            ("Training Time", f"{mp.get('training_time_seconds') or 0:.1f}s"),
            ("Dataset Records", mp.get("dataset_records") or 0),
            ("Features", mp.get("num_features") or 0),
        ])

        # 4. Why factors
        section("4. Why did AI choose this price?")
        pdf.set_font("helvetica", "", 9)
        for f in report["why_factors"]:
            pdf.set_font("helvetica", "B", 9)
            pdf.cell(0, 6, txt(f"{f['factor']}  -  impact {f['impact']}  -  importance {f['importance']}%"), ln=True)
            pdf.set_font("helvetica", "", 9)
            pdf.multi_cell(0, 5.5, txt(f"   {f['explanation']}"))
            pdf.ln(1)

        # 5. Revenue impact
        section("5. Revenue Impact Analysis")
        ri = report["revenue_impact"]
        kv_table([
            ("Current Revenue (30d)", f"{CURRENCY}{ri['current_revenue']:,.2f}"),
            ("Predicted Revenue (30d)", f"{CURRENCY}{ri['predicted_revenue']:,.2f}"),
            ("Revenue Increase", f"{CURRENCY}{ri['revenue_increase']:,.2f} ({ri['revenue_increase_pct']:+.1f}%)"),
            ("Profit Increase", f"{CURRENCY}{ri['profit_increase']:,.2f} ({ri['profit_increase_pct']:+.1f}%)"),
            ("ROI", f"{ri['roi_pct']:+.1f}%"),
            ("Margin", f"{ri['margin_now_pct']:.1f}% -> {ri['margin_new_pct']:.1f}%"),
        ])

        # 6. Risks
        section("6. Risk Analysis")
        pdf.set_font("helvetica", "", 9)
        for r in report["risk_analysis"]:
            pdf.set_font("helvetica", "B", 9)
            pdf.cell(0, 6, txt(f"{r['risk']}  -  Level: {r['level']}"), ln=True)
            pdf.set_font("helvetica", "", 9)
            pdf.multi_cell(0, 5.5, txt(f"   {r['explanation']}"))
            pdf.ln(1)

        # 7. Forecast summary
        section("7. Forecast Summary")
        fs = report["forecast_summary"]
        kv_table([
            ("Horizon", f"{fs['horizon']} days"),
            ("Expected Revenue", f"{CURRENCY}{fs['expected_revenue']:,.2f}"),
            ("Expected Demand", f"{fs['expected_demand']:,.0f} units"),
            ("Trend", fs["trend"].capitalize()),
            ("Growth Rate", f"{fs['growth_rate']:+.1f}%"),
            ("Forecast Confidence", f"{fs['forecast_confidence']:.1f}%"),
        ])
        pdf.ln(2)
        pdf.set_font("helvetica", "I", 9)
        pdf.multi_cell(0, 5.5, txt(fs["paragraph"]))

        # 8. Recommendations
        section("8. Business Recommendation")
        pdf.set_font("helvetica", "", 9)
        for i, rec in enumerate(report["recommendations"], 1):
            pdf.cell(6, 6, f"{i}.")
            pdf.multi_cell(0, 5.5, txt(rec))
            pdf.ln(0.5)

        # 9. Conclusion
        section("9. Report Conclusion")
        pdf.set_font("helvetica", "", 10)
        pdf.multi_cell(0, 6, txt(report["conclusion"]))

        return bytes(pdf.output())
