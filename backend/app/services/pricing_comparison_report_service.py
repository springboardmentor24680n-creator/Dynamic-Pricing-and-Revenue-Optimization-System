"""
PricePilot AI - Pricing Comparison Report Service
==================================================
Generates a clean, business-readable pricing comparison report for a selected
product. The report combines:

  * the product and its current PricePilot price,
  * genuine comparable products (matched from the catalog) with their
    reference prices, price differences and platform deep-links,
  * verified / reference market intelligence (range, positioning, insights),
  * source links for direct verification,
  * the EXISTING AI prediction and demand-forecast output as CONTEXT only.

Data-integrity rules: prices are either "verified" (permitted live provider)
or "reference" (real PricePilot catalog prices). Market averages are only
computed from verified prices when enough exist; otherwise reference data is
used and labeled. Business statements are only generated when the underlying
data supports them - the report says "insufficient data" instead of inventing
values. The existing AI prediction / forecasting models are never replaced.
"""

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.product import Product
from app.services.competitor_service import CompetitorService
from app.services.forecast_service import ForecastService
from app.services.market_intelligence_service import MarketIntelligenceService
from app.services.ml_service import PricingMLService

CURRENCY = "$"


def _money(v) -> str:
    return f"{CURRENCY}{v:,.2f}" if v is not None else "—"


class PricingComparisonReportService:
    """Business report that ties product data + competitors + market intel + AI."""

    def __init__(self, db: Session):
        self.db = db
        self.competitor = CompetitorService(db)
        self.market = MarketIntelligenceService(db)
        self.ml = PricingMLService(db)
        self.forecast = ForecastService(db)

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------
    def generate(self, product_id: int, horizon: int = 30) -> dict:
        product = self.db.query(Product).filter(Product.id == product_id).first()
        if not product:
            raise ValueError("Product not found")

        comparison = self.competitor.analyze(product_id)
        competitors = comparison.get("competitors", [])
        # Pass pre-computed comparison to market.analyze() to avoid
        # a redundant competitor.analyze() call inside it.
        market = self.market.analyze(product_id, _precomputed_comparison=comparison)
        # Pass pre-computed data to _ai_context to avoid redundant
        # competitor.analyze() + market.analyze() calls inside it.
        ai = self._ai_context(product, horizon, _precomputed_comparison=comparison, _precomputed_market=market)

        verified = market["verified_prices"]["values"] if market["verified_prices"].get("available") else []
        reference = market["reference_prices"].get("values", [])

        key_insight, recommendations = self._key_insight_and_recommendations(
            product, market, ai, verified, reference
        )

        return {
            "report_title": "Pricing Comparison Report",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "product": {
                "name": product.name,
                "sku": product.sku,
                "brand": comparison["product"]["brand"],
                "category": product.category,
                "current_price": round(product.current_price or 0, 2),
                "base_price": round(product.base_price or 0, 2),
                "image_url": product.image_url,
                "parsed_specs": comparison["product"].get("parsed_specs", {}),
            },
            "pricepilot_price": round(product.current_price or 0, 2),
            "market_price_range": market["market"]["range"],
            "price_positioning": market["market"]["positioning"],
            "verified_prices": market["verified_prices"],
            "reference_prices": market["reference_prices"],
            "price_source": market["price_source"],
            "competitors": [
                {
                    "rank": c.get("rank"),
                    "competitor_product": c.get("competitor_product") or {
                        "product_id": c.get("product_id"),
                        "name": c.get("name"),
                        "brand": c.get("brand"),
                        "model": c.get("model"),
                        "category": c.get("category"),
                    },
                    "name": c["name"],
                    "brand": c["brand"],
                    "model": c.get("model"),
                    "category": c["category"],
                    "match_type": c.get("match_type", "comparable"),
                    "price": c.get("price", c.get("reference_price")),
                    "price_source": c.get("price_source", c.get("price_status")),
                    "price_label": c.get("price_label", c.get("reference_price_label")),
                    "reference_price": c["reference_price"],
                    "reference_price_label": c["reference_price_label"],
                    "price_status": c["price_status"],
                    "price_difference": c["price_difference"],
                    "price_difference_pct": c["price_difference_pct"],
                    "match_reasons": c["match_reasons"],
                    "marketplace_sources": c.get("marketplace_sources") or c.get("platforms"),
                    "platforms": c.get("platforms"),
                }
                for c in competitors
            ],
            "price_differences": {
                "vs_average_pct": market["market"]["range"].get("diff_vs_avg_pct"),
                "vs_low_pct": self._diff_pct(product.current_price, market["market"]["range"].get("low")),
                "vs_high_pct": self._diff_pct(product.current_price, market["market"]["range"].get("high")),
                "source": market["market"]["range"].get("source"),
            },
            "key_pricing_insight": key_insight,
            "recommendations": recommendations,
            "source_links": self._source_links(competitors),
            "ai_context": ai,
            "data_quality": {
                "comparables_found": len(competitors),
                "verified_price_count": len(verified),
                "reference_price_count": len(reference),
                "note": market["note"],
            },
        }

    # ------------------------------------------------------------------
    # AI context (never replaces the prediction/forecast systems)
    # ------------------------------------------------------------------
    def _ai_context(self, product: Product, horizon: int, *,
                     _precomputed_comparison=None, _precomputed_market=None) -> dict:
        try:
            pred = self.ml.predict_product(product.id, include_forecast=True)
        except Exception as exc:  # noqa: BLE001 - degrade gracefully
            return {
                "available": False,
                "note": f"AI prediction unavailable ({exc}).",
                "integration": None,
            }

        available = not pred.get("insufficient_data")
        demand = pred.get("demand_forecast") or {}
        trend = demand.get("trend", "unavailable")
        growth = demand.get("growth_pct")

        integration = None
        if available:
            suggested = pred.get("suggested_price")
            mkt_avg = None
            mkt_source = "reference"
            # Reuse already-computed market data instead of calling
            # self.market.analyze() a second time (expensive).
            try:
                if _precomputed_market is not None:
                    mkt = _precomputed_market["market"]["range"]
                else:
                    mkt = self.market.analyze(product.id)["market"]["range"]
                mkt_avg = mkt.get("avg")
                mkt_source = mkt.get("source", "reference")
            except Exception:  # noqa: BLE001
                mkt_avg = None
            if mkt_avg and suggested:
                diff = ((suggested - mkt_avg) / mkt_avg) * 100
                source_word = "verified market average" if mkt_source == "verified" else "reference average"
                integration = (
                    f"The AI model suggests {_money(suggested)}, which is "
                    f"{abs(diff):.0f}% {'above' if diff > 0 else 'below'} the "
                    f"{source_word} ({_money(mkt_avg)}) - use this alongside competitor "
                    f"data when deciding the final price."
                )
            elif suggested:
                integration = (
                    f"The AI model suggests {_money(suggested)} (confidence "
                    f"{pred.get('confidence_score', 0):.0f}%). Competitor price data can refine "
                    f"the final decision but does not replace the model."
                )

        return {
            "available": available,
            "suggested_price": pred.get("suggested_price"),
            "confidence_score": pred.get("confidence_score"),
            "expected_revenue_change": pred.get("expected_revenue_change"),
            "expected_revenue": pred.get("expected_revenue"),
            "expected_profit": pred.get("expected_profit"),
            "best_model": pred.get("best_model"),
            "demand_trend": trend,
            "demand_growth_pct": growth,
            "integration": integration,
            "note": (
                "AI prediction and demand forecast are shown as CONTEXT alongside the "
                "competitive landscape. They come from the existing persisted models and "
                "are not replaced or modified by the market intelligence layer."
            ),
        }

    @staticmethod
    def _diff_pct(our_price, market) -> float:
        if not our_price or not market:
            return None
        return round(((our_price - market) / market) * 100, 1)

    # ------------------------------------------------------------------
    # Key insight + recommendations (business language, data-supported)
    # ------------------------------------------------------------------
    def _key_insight_and_recommendations(self, product, market, ai,
                                         verified: list, reference: list) -> tuple:
        rng = market["market"]["range"]
        positioning = market["market"]["positioning"]
        opportunity = market["pricing_opportunity"]
        recommendations = []

        # Key insight: prefer a concrete, supported statement.
        key_insight = None
        for ins in market["insights"]:
            if ins["support"] == "high":
                key_insight = ins["text"]
                break
        if not key_insight:
            for ins in market["insights"]:
                if ins["support"] == "medium":
                    key_insight = ins["text"]
                    break
        if not key_insight:
            key_insight = "Insufficient competitor data to derive a key pricing insight."

        # Recommendations (business-level).
        if opportunity.get("data_supported"):
            recommendations.append({
                "kind": "market",
                "text": opportunity["text"],
                "support": "data-supported",
            })
        if ai.get("available"):
            rec = (
                f"The AI model suggests pricing this product at {_money(ai['suggested_price'])} "
                f"(confidence {ai.get('confidence_score', 0):.0f}%), a "
                f"{ai.get('expected_revenue_change', 0):+.1f}% expected 30-day revenue change. "
            )
            if ai.get("demand_trend") and ai["demand_trend"] != "unavailable":
                direction = {
                    "up": "rising demand", "down": "softening demand", "stable": "stable demand",
                }.get(ai["demand_trend"], "stable demand")
                growth = ai.get("demand_growth_pct")
                rec += f"Demand is {direction}" + (f" ({growth:+.1f}% growth)." if growth is not None else ".")
            recommendations.append({"kind": "ai", "text": rec, "support": "model-based"})

        if not recommendations:
            recommendations.append({
                "kind": "none",
                "text": "Insufficient data to make a reliable pricing recommendation for this product.",
                "support": "insufficient-data",
            })

        return key_insight, recommendations

    # ------------------------------------------------------------------
    # Source links (deduped, real URLs only)
    # ------------------------------------------------------------------
    def _source_links(self, competitors: list) -> list:
        seen, links = set(), []
        for c in competitors:
            comp_name = c.get("name") or (c.get("competitor_product") or {}).get("name")
            brand = c.get("brand") or (c.get("competitor_product") or {}).get("brand") or comp_name
            sources = c.get("marketplace_sources") or c.get("platforms") or []
            for src in sources:
                url = src.get("url")
                marketplace = src.get("marketplace") or src.get("platform")
                if url and url not in seen:
                    seen.add(url)
                    price_source = src.get("price_source") or src.get("price_status", "unavailable")
                    links.append({
                        "label": f"{comp_name or brand} on {marketplace}",
                        "marketplace": marketplace,
                        "platform": marketplace,
                        "url": url,
                        "price_source": price_source,
                        "price_status": price_source,
                    })
        return links[:30]