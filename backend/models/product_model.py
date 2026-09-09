from sqlalchemy import Column, Integer, String, Float, DateTime
from datetime import datetime

from models.user_model import Base


class Product(Base):
    __tablename__ = "products"

    # =========================================================
    # PRIMARY KEY
    # =========================================================

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    # =========================================================
    # PRODUCT INFORMATION
    # =========================================================

    product_name = Column(
        String(100),
        nullable=False
    )

    category = Column(
        String(100),
        nullable=False
    )

    # =========================================================
    # PRICING
    # =========================================================

    # Current selling price
    price = Column(
        Float,
        nullable=False
    )

    # Product purchase/manufacturing cost
    # Used for Gross Profit and Profit Margin calculations
    cost_price = Column(
        Float,
        nullable=True
    )

    # =========================================================
    # INVENTORY
    # =========================================================

    stock = Column(
        Integer,
        nullable=False,
        default=0
    )

    # =========================================================
    # COMPETITOR MONITORING
    # =========================================================

    competitor_price = Column(
        Float,
        nullable=True
    )

    competitor_name = Column(
        String(100),
        nullable=True
    )

    competitor_updated_at = Column(
        DateTime,
        default=datetime.utcnow
    )