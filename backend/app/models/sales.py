"""
PricePilot AI - Sales Model
"""

from sqlalchemy import Column, Integer, Float, String, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship

from app.database import Base


class Sale(Base):
    """Sales transaction records for analytics."""
    
    __tablename__ = "sales"
    
    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    quantity = Column(Integer, nullable=False, default=1)
    unit_price = Column(Float, nullable=False)
    unit_cost = Column(Float, nullable=True)
    total_amount = Column(Float, nullable=False)
    sale_date = Column(DateTime, server_default=func.now())
    sale_channel = Column(String(50))
    region = Column(String(100))
    customer_segment = Column(String(50))
    
    # Synthetic-history factors (set when sales history is auto-generated so the
    # demand forecasting / training pipeline can explain WHY a day sold what it did)
    season_factor = Column(Float, nullable=True)
    demand_factor = Column(Float, nullable=True)
    trend_factor = Column(Float, nullable=True)
    weekend_effect = Column(Float, nullable=True)
    festival_effect = Column(Float, nullable=True)
    
    created_at = Column(DateTime, server_default=func.now())
    
    # Relationships
    product = relationship("Product")
