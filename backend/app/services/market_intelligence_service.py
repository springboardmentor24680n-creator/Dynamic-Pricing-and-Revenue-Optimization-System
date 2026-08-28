"""
PricePilot AI - Market Intelligence Service
===========================================
Builds a business-level market intelligence layer from the competitor /
product information that is ACTUALLY available.

Data-integrity rules (same as the competitor module):
  * Verified metrics (min / max / average competitor price, market range,
    positioning) are ONLY computed from prices reported as "verified" by a
    permitted live provider. No provider is configured by default, so these
    are reported as unavailable rather than estimated.
  * Reference metrics are computed from the real PricePilot catalog prices of
    the comparable products and are ALWAYS labeled "reference data" — they are
    real internal data, never fabricated external prices.
  * Every business insight carries a support level and is only generated when
    the underlying data exists. If there is not enough data, the service says
    so explicitly instead of inventing a claim.

Connects to the AI layer only as CONTEXT: the AI suggested price and the
demand-forecast trend are surfaced next to the market data so a pricing
manager can see how the recommendation relates to the competitive landscape.
The existing prediction / forecasting models are never replaced.
"""

import logging
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.product import Product
from app.services.competitor_service import CompetitorService

logger = logging.getLogger(__name__)

CURRENCY = "$"

# Minimum number of verified prices before we claim a "market average".
MIN_VERIFIED_FOR_AVERAGE = 3
# Minimum number of verified prices before "clustered" language is allowed.
MIN_VERIFIED_FOR_CLUSTER = 3


def _money(v) -> str:
    return f"{CURRENCY}{v:,.2f}" if v is not None else "—"


class MarketIntelligenceService:
    """Market intelligence for a single product, built from real competitor data."""

    def __init__(self, db: Session):
        self.db = db
        self.competitor = CompetitorService(db)

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------
    def analyze(self, product_id: int, _precomputed_comparison=None) -> dict:
        product = self.db.query(Product).filter(Product.id == product_id).first()
        if not product:
            raise ValueError("Product not found")

        # Reuse already-computed competitor data when available
        # (avoids a redundant competitor.analyze() call from the report).
        comparison = _precomputed_comparison if _precomputed_comparison is not None else self.competitor.analyze(product_id)
        competitors = comparison.get("competitors", [])

        verified = self._collect_verified_prices(competitors)
        reference = self._collect_reference_prices(competitors)

        metrics = self._compute_metrics(product, verified, reference)
        positioning = self._positioning(product.current_price, metrics)
        insights, opportunity = self._build_insights(product, verified, reference, metrics, positioning)

        return {
            "product": {
                "id": product.id,
                "name": product.name,
                "brand": comparison["product"]["brand"],
                "category": product.category,
                "current_price": round(product.current_price or 0, 2),
            },
            "as_of": datetime.now(timezone.utc).isoformat(),
            "price_source": self._source_label(verified, reference),
            "competitors": {
                "found": len(competitors),
                "available": len(competitors),
                "unavailable": 0,
                "with_verified_price": len(verified),
                "with_reference_price": len(reference),
                "marketplace_sources_for_category": (
                    comparison["comparison"].get("marketplace_sources_for_category")
                    or comparison["comparison"].get("platforms", [])
                ),
                "platforms": comparison["comparison"].get("platforms", []),
            },
            "verified_prices": self._verified_block(verified),
            "reference_prices": self._reference_block(reference),
            "market": {
                "range": metrics["range"],
                "positioning": positioning,
            },
            "pricing_opportunity": opportunity,
            "insights": insights,
            "note": (
                "Verified metrics are computed only from live prices confirmed by a "
                "permitted source. With no live provider configured, market range and "
                "positioning are derived from PricePilot reference prices of comparable "
                "products and are labeled as reference data. No value is estimated."
            ),
        }

    # ------------------------------------------------------------------
    # Price collection (real data only)
    # ------------------------------------------------------------------
    def _collect_verified_prices(self, competitors: list) -> list:
        """Verified listing prices for competitor products on marketplace sources.

        Each row is a price for a competitor *product* on a *source* — the
        marketplace is never treated as the competitor itself.
        """
        out = []
        for c in competitors:
            comp_name = c.get("name") or (c.get("competitor_product") or {}).get("name")
            if not comp_name:
                continue
            sources = c.get("marketplace_sources") or c.get("platforms") or []
            for src in sources:
                price_source = src.get("price_source") or src.get("price_status")
                if price_source == "verified" and src.get("price"):
                    out.append({
                        "competitor_product": comp_name,
                        "marketplace": src.get("marketplace") or src.get("platform"),
                        "price": round(float(src["price"]), 2),
                        "url": src.get("url"),
                        "competitor": comp_name,
                        "platform": src.get("marketplace") or src.get("platform"),
                    })
        return out

    def _collect_reference_prices(self, competitors: list) -> list:
        """Reference catalog prices of matched competitor products."""
        out = []
        for c in competitors:
            comp_name = c.get("name") or (c.get("competitor_product") or {}).get("name")
            price = c.get("price")
            if price is None:
                price = c.get("reference_price")
            price_source = c.get("price_source") or c.get("price_status")
            if comp_name and price and price_source == "reference":
                out.append({
                    "competitor_product": comp_name,
                    "price": round(float(price), 2),
                    "competitor": comp_name,
                })
        return out

    # ------------------------------------------------------------------
    # Metric computation
    # ------------------------------------------------------------------
    def _compute_metrics(self, product, verified: list, reference: list) -> dict:
        range_ = self._market_range(product.current_price, verified, reference)
        return {
            "range": range_,
            "verified_count": len(verified),
            "reference_count": len(reference),
        }

    def _market_range(self, our_price, verified: list, reference: list) -> dict:
        """Lowest/highest competitor price and (if supported) average.

        Verified prices win when present; otherwise reference prices are used
        and clearly labeled. When neither exists the range is unavailable.
        """
        our = our_price or 0
        if verified:
            prices = [v["price"] for v in verified]
            low, high = min(prices), max(prices)
            return {
                "low": round(low, 2),
                "high": round(high, 2),
                "spread": round(high - low, 2),
                "avg": round(sum(prices) / len(prices), 2) if len(prices) >= MIN_VERIFIED_FOR_AVERAGE else None,
                "count": len(prices),
                "source": "verified",
                "enough_for_avg": len(prices) >= MIN_VERIFIED_FOR_AVERAGE,
                "our_price_in_range": low <= our <= high,
                "diff_vs_avg_pct": self._diff_pct(our_price, sum(prices) / len(prices)),
            }
        if reference:
            prices = [r["price"] for r in reference]
            low, high = min(prices), max(prices)
            return {
                "low": round(low, 2),
                "high": round(high, 2),
                "spread": round(high - low, 2),
                "avg": round(sum(prices) / len(prices), 2),
                "count": len(prices),
                "source": "reference",
                "enough_for_avg": True,
                "our_price_in_range": low <= our <= high,
                "diff_vs_avg_pct": self._diff_pct(our_price, sum(prices) / len(prices)),
            }
        return {
            "low": None, "high": None, "spread": None, "avg": None, "count": 0,
            "source": "unavailable", "enough_for_avg": False,
            "our_price_in_range": None, "diff_vs_avg_pct": None,
        }

    @staticmethod
    def _diff_pct(our_price, market) -> float:
        """% difference between our price and a market/reference figure."""
        if not our_price or not market:
            return None
        return round(((our_price - market) / market) * 100, 1)

    def _positioning(self, our_price, metrics: dict) -> dict:
        rng = metrics["range"]
        if rng["low"] is None:
            return {
                "level": "unknown",
                "label": "Not enough competitor data to determine price positioning.",
                "data_supported": False,
            }
        our = our_price or 0
        if our < rng["low"]:
            level, phrase = "below_range", "below"
        elif our > rng["high"]:
            level, phrase = "above_range", "above"
        else:
            level, phrase = "within_range", "within"
        source = "verified competitor range" if rng["source"] == "verified" else "comparable catalog range (reference data)"
        return {
            "level": level,
            "label": f"PricePilot price is {phrase} the {source}.",
            "data_supported": True,
        }

    # ------------------------------------------------------------------
    # Blocks
    # ------------------------------------------------------------------
    def _verified_block(self, verified: list) -> dict:
        if not verified:
            return {
                "available": False,
                "count": 0,
                "note": (
                    "Verified prices: 0. No live verified competitor prices are "
                    "available from a permitted source in this deployment. Any "
                    "reference/catalog prices shown are NOT live external prices; "
                    "they are real internal catalog data. Prices are never estimated."
                ),
            }
        prices = [v["price"] for v in verified]
        return {
            "available": True,
            "count": len(prices),
            "values": verified,
            "min": round(min(prices), 2),
            "max": round(max(prices), 2),
            "avg": round(sum(prices) / len(prices), 2) if len(prices) >= MIN_VERIFIED_FOR_AVERAGE else None,
            "enough_for_avg": len(prices) >= MIN_VERIFIED_FOR_AVERAGE,
            "note": f"Average is reported only with at least {MIN_VERIFIED_FOR_AVERAGE} verified prices (currently {len(prices)}).",
        }

    def _reference_block(self, reference: list) -> dict:
        if not reference:
            return {
                "available": False,
                "count": 0,
                "note": "No comparable products with a reference price were found.",
            }
        prices = [r["price"] for r in reference]
        return {
            "available": True,
            "count": len(prices),
            "min": round(min(prices), 2),
            "max": round(max(prices), 2),
            "avg": round(sum(prices) / len(prices), 2),
            "values": reference,
            "note": "Reference prices are PricePilot catalog prices of comparable products (real internal data, not live external prices).",
        }

    def _source_label(self, verified: list, reference: list) -> str:
        if verified:
            return "verified" if not reference else "mixed"
        if reference:
            return "reference"
        return "unavailable"

    # ------------------------------------------------------------------
    # Business insights & opportunity
    # ------------------------------------------------------------------
    def _build_insights(self, product, verified: list, reference: list,
                        metrics: dict, positioning: dict) -> tuple:
        insights = []
        rng = metrics["range"]

        # 1. Market range
        if rng["low"] is not None:
            if rng["source"] == "verified":
                insight = (
                    f"Verified competitor prices are clustered around "
                    f"{_money(rng['low'])}–{_money(rng['high'])}."
                    if metrics["verified_count"] >= MIN_VERIFIED_FOR_CLUSTER
                    else f"Verified competitor prices range from {_money(rng['low'])} to {_money(rng['high'])}."
                )
                support = "high"
            else:
                insight = (
                    f"Among comparable products in the PricePilot catalog, prices range from "
                    f"{_money(rng['low'])} to {_money(rng['high'])} (reference data, not live)."
                )
                support = "medium"
            insights.append({"text": insight, "support": support})

        # 2. Price position vs average/midpoint
        avg = rng.get("avg")
        if avg is not None and rng["diff_vs_avg_pct"] is not None:
            pct = rng["diff_vs_avg_pct"]
            source_word = "verified competitor average" if rng["source"] == "verified" else "reference average"
            if abs(pct) < 0.05:
                text = f"Current price is essentially at the {source_word} ({_money(avg)})."
            else:
                text = (
                    f"Current price is approximately {abs(pct):.0f}% "
                    f"{'above' if pct > 0 else 'below'} the {source_word} ({_money(avg)})."
                )
            insights.append({"text": text, "support": "high" if rng["source"] == "verified" else "medium"})

        # 3. Positioning
        if positioning["data_supported"]:
            insights.append({"text": positioning["label"], "support": "high" if rng["source"] == "verified" else "medium"})

        # 4. Price difference from market low (opportunity signal)
        if rng["low"] is not None and rng["source"] == "verified":
            insights.append({
                "text": f"Lowest verified competitor price is {_money(rng['low'])} ({self._diff_pct(product.current_price, rng['low']):+.0f}% vs PricePilot).",
                "support": "high",
            })

        if not insights:
            insights.append({
                "text": "Insufficient verified market data to make a live competitive pricing recommendation.",
                "support": "none",
            })
        elif verified is None or not verified:
            # Reference-derived metrics exist but no live verified price does:
            # say so explicitly so reference/catalog prices are never mistaken
            # for live external competitor prices.
            insights.insert(0, {
                "text": (
                    "No verified live competitor prices are available for this product. "
                    "The range and positioning above use PricePilot reference prices "
                    "(real internal catalog data, not live external prices)."
                ),
                "support": "medium",
            })

        # Pricing opportunity (data-driven)
        opportunity = self._opportunity(product, rng, positioning)
        return insights, opportunity

    def _opportunity(self, product, rng: dict, positioning: dict) -> dict:
        if rng["low"] is None:
            return {
                "text": "Insufficient verified market data to make a live competitive pricing recommendation.",
                "actionable": False,
                "data_supported": False,
                "basis": "unavailable",
            }

        our = product.current_price or 0
        source_word = "market" if rng["source"] == "verified" else "comparable catalog prices"
        midpoint = round((rng["low"] + rng["high"]) / 2, 2)

        if our > rng["high"]:
            text = (
                f"This product is priced above most verified competitors. A lower price position "
                f"toward the market midpoint ({_money(midpoint)}) may improve competitiveness."
                if rng["source"] == "verified"
                else f"This product is priced above most comparable products. A lower price toward the reference midpoint ({_money(midpoint)}) may improve competitiveness."
            )
        elif our < rng["low"]:
            text = "PricePilot is currently positioned below most verified competitors — a modest price increase may be feasible."
        else:
            text = "This product is priced within the competitive range — monitor demand before adjusting price."
        return {
            "text": text,
            "actionable": True,
            "data_supported": True,
            "basis": source_word,
        }