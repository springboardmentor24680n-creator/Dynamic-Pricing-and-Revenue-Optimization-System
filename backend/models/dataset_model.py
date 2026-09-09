from sqlalchemy import Column, Integer, String, Float, Date
from models.user_model import Base


class DatasetRecord(Base):
    __tablename__ = "dataset_records"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    date = Column(
        Date,
        nullable=True
    )

    product_name = Column(
        String(100),
        nullable=False,
        index=True
    )

    category = Column(
        String(100),
        nullable=False
    )

    price = Column(
        Float,
        nullable=False
    )

    stock = Column(
        Integer,
        nullable=False,
        default=0
    )

    units_sold = Column(
        Integer,
        nullable=False,
        default=0
    )

    competitor_price = Column(
        Float,
        nullable=True
    )

    discount = Column(
        Float,
        nullable=True,
        default=0
    )

    target_price = Column(
        Float,
        nullable=True
    )