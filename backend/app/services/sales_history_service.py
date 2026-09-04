"""
PricePilot AI - Sales History Generator
========================================
Ensures every product in the catalog has realistic daily sales history so the
demand-forecasting and training pipelines always have data to learn from.

When a dataset is imported and a product has little or no sales history, this
service generates 180 days of deterministic, realistic daily sales rows with
the demand factors stored alongside each row (so the pipeline can explain WHY
a day sold what it did):

  product_id, date, units sold, revenue, price,
  season_factor, demand_factor, trend_factor, weekend_effect, festival_effect

Generation is non-destructive (dates that already have sales are skipped),
deterministic per product (seeded by SKU), and batched for large catalogs.
"""

import math
import random
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.models.sales import Sale
from app.models.product import Product

DAYS_TO_GENERATE = 180
MIN_HISTORY_DAYS = 30  # products with fewer daily records than this get history
BATCH_SIZE = 2000

CHANNELS = ["Online", "Retail", "Marketplace", "Wholesale"]
REGIONS = ["North", "South", "East", "West", "Central"]
SEGMENTS = ["Consumer", "SMB", "Enterprise", "Government"]


def _monthly_season_factor(month: int) -> float:
    """Retail seasonality: trough in Feb, peaks around Nov/Dec holidays."""
    # Cosine shaped with peak in late November
    return 0.82 + 0.28 * (0.5 + 0.5 * math.cos((month - 11) / 12 * 2 * math.pi))


def _is_festival(date: datetime) -> float:
    """Festival uplift multiplier for notable dates (Black Friday, holidays)."""
    d = date.date()
    # Black Friday: last Friday of November (and the day after)
    if date.month == 11:
        last_friday = None
        for day in range(22, 32):
            try:
                candidate = d.replace(day=day)
            except ValueError:
                continue
            if candidate.weekday() == 4:
                last_friday = candidate
        if last_friday and d == last_friday:
            return 1.45
        if last_friday and d == last_friday + timedelta(days=1):
            return 1.25
    # Year-end holidays (Dec 20 - Jan 1)
    if (date.month == 12 and date.day >= 20) or (date.month == 1 and date.day <= 2):
        return 1.3
    # Valentine's day spike
    if date.month == 2 and date.day in (13, 14):
        return 1.3
    return 1.0


def _existing_dates(db: Session, product_id: int) -> set:
    """Return the set of dates that already have sales for this product."""
    rows = db.query(Sale.sale_date).filter(Sale.product_id == product_id).all()
    return {r[0].date() if r[0] else None for r in rows}


def _history_day_count(db: Session, product_id: int) -> int:
    """Count distinct days with sales for a product."""
    existing = _existing_dates(db, product_id)
    return len([d for d in existing if d is not None])


def _generate_daily_rows(product: Product, existing: set) -> list:
    """Build 180 days of daily sales rows for a product (skipping existing dates).

    Volume is driven by a per-product base demand plus factors, all recorded
    on the row so the pipeline can explain the numbers later.
    """
    price = product.current_price or 10.0
    stock = product.stock_quantity or 50
    rng = random.Random(f"{product.sku or product.id}-sales-hist")

    # Base daily demand: cheaper + higher stock => more units
    base_units = max(1, min(30, int(stock / 25)))
    price_factor = max(0.5, min(3.0, 120 / max(price, 1)))
    base = max(1, int(base_units * price_factor))

    # Per-product demand personality (stable over the window)
    demand_tilt = rng.uniform(0.75, 1.35)

    rows = []
    today = datetime.utcnow().date()
    for day_offset in range(DAYS_TO_GENERATE):
        date = today - timedelta(days=day_offset)
        if date in existing:
            continue
        day = datetime.combine(date, datetime.min.time()).replace(hour=12)

        month_factor = _monthly_season_factor(date.month)
        weekend = 1.6 if date.weekday() >= 5 else 1.0
        # Gentle growth toward the present (0.8 -> 1.2) so trends are learnable
        trend = 0.82 + 0.38 * (day_offset / DAYS_TO_GENERATE)
        festival = _is_festival(day)
        demand = demand_tilt * rng.uniform(0.55, 1.45)

        units = max(1, int(base * month_factor * weekend * trend * festival * demand))
        unit_price = round(price * rng.uniform(0.93, 1.08), 2)
        total = round(unit_price * units, 2)

        rows.append(Sale(
            product_id=product.id,
            quantity=units,
            unit_price=unit_price,
            total_amount=total,
            sale_date=day,
            sale_channel=rng.choice(CHANNELS),
            region=rng.choice(REGIONS),
            customer_segment=rng.choice(SEGMENTS),
            season_factor=round(month_factor, 3),
            demand_factor=round(demand, 3),
            trend_factor=round(trend, 3),
            weekend_effect=round(weekend, 3),
            festival_effect=round(festival, 3),
        ))
    return rows


class SalesHistoryService:
    """Generates realistic daily sales history for products that lack it."""

    def __init__(self, db: Session):
        self.db = db

    def ensure_history_for_products(self, product_ids=None) -> dict:
        """Generate 180 days of sales history for products with sparse history.

        ``product_ids`` restricts work to a specific set (e.g. freshly imported
        products); ``None`` means the whole catalog.
        """
        query = self.db.query(Product)
        if product_ids:
            query = query.filter(Product.id.in_(list(product_ids)))
        products = query.all()

        generated_products = 0
        total_rows = 0
        batch = []

        for product in products:
            day_count = _history_day_count(self.db, product.id)
            if day_count >= MIN_HISTORY_DAYS:
                continue
            existing = _existing_dates(self.db, product.id)
            rows = _generate_daily_rows(product, existing)
            if not rows:
                continue
            batch.extend(rows)
            total_rows += len(rows)
            generated_products += 1
            if len(batch) >= BATCH_SIZE:
                self.db.add_all(batch)
                self.db.commit()
                batch = []

        if batch:
            self.db.add_all(batch)
            self.db.commit()

        if generated_products > 0 or total_rows > 0:
            # New sales rows were written: cached sales aggregates, demand
            # signals and any predictions built from them are now outdated.
            try:
                from app.services.training_service import invalidate_analytics_caches
                invalidate_analytics_caches()
            except Exception:
                pass

        return {
            "products_generated": generated_products,
            "rows_generated": total_rows,
        }

    def ensure_history_for_product(self, product_id: int) -> int:
        """Generate history for a single product; returns rows added."""
        result = self.ensure_history_for_products([product_id])
        return result["rows_generated"]
