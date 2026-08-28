"""
PricePilot AI - Product Model
"""

from sqlalchemy import Column, Integer, String, Float, Text, DateTime, func
from sqlalchemy.orm import relationship

from app.database import Base


class Product(Base):
    """Product model with pricing and inventory information."""
    
    __tablename__ = "products"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False, index=True)
    sku = Column(String(50), unique=True, nullable=False, index=True)
    description = Column(Text)
    category = Column(String(100), index=True)
    base_price = Column(Float, nullable=False)
    current_price = Column(Float, nullable=False)
    cost_price = Column(Float)
    brand = Column(String(100), index=True)
    image_url = Column(String(500), default="")
    stock_quantity = Column(Integer, default=0)
    revenue = Column(Float, default=0.0)
    status = Column(String(20), default="active")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # Relationships
    pricing_history = relationship("PricingHistory", back_populates="product", cascade="all, delete-orphan")
