from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    DateTime
)

from datetime import datetime

from models.user_model import Base


class CompetitorPrice(Base):

    __tablename__ = "competitor_prices"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    product_id = Column(
        Integer,
        nullable=False,
        index=True
    )

    product_name = Column(
        String(100),
        nullable=False
    )

    category = Column(
        String(100),
        nullable=False
    )

    your_price = Column(
        Float,
        nullable=False
    )

    competitor_name = Column(
        String(100),
        nullable=False
    )

    competitor_price = Column(
        Float,
        nullable=False
    )

    price_difference = Column(
        Float,
        nullable=False
    )

    price_difference_percent = Column(
        Float,
        nullable=False
   )

    competitive_status = Column(
        String(100),
        nullable=False
    )

    monitored_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )