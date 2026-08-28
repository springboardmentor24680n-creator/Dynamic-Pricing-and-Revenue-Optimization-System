"""
PricePilot AI - Analytics Cache Model
Stores precomputed analytics for fast executive BI reads.
"""

from sqlalchemy import Column, Integer, String, Float, Text, DateTime, func, JSON
from app.database import Base


class AnalyticsCache(Base):
    """Precomputed analytics cache with TTL and versioning."""

    __tablename__ = "analytics_cache"

    id = Column(Integer, primary_key=True, index=True)
    cache_key = Column(String(100), unique=True, nullable=False, index=True)
    # e.g. "market_position", "demand_signals", "ai_predictions", "pricing_summary"

    data = Column(JSON, nullable=False)
    # The cached analytics payload

    status = Column(String(20), default="READY")
    # READY | PROCESSING | STALE | UNAVAILABLE

    calculated_at = Column(DateTime, server_default=func.now())
    expires_at = Column(DateTime, nullable=True)
    # When the cache entry should be considered stale

    model_version = Column(String(50), nullable=True)
    # ML model version used for predictions (if applicable)

    data_version = Column(String(50), nullable=True)
    # Hash or version of underlying data

    product_count = Column(Integer, default=0)
    # Number of products included in this computation

    compute_time_ms = Column(Float, nullable=True)
    # How long the computation took

    error_message = Column(Text, nullable=True)
    # If status=UNAVAILABLE, the reason

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
