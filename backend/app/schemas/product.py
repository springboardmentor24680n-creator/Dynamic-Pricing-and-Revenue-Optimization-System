"""
PricePilot AI - Product Schemas
"""

from pydantic import BaseModel, field_validator
from typing import Optional
from datetime import datetime


class ProductBase(BaseModel):
    """Base product schema."""
    name: str
    sku: str
    description: Optional[str] = None
    category: Optional[str] = None
    brand: Optional[str] = None
    base_price: float
    current_price: float
    cost_price: Optional[float] = None
    image_url: Optional[str] = ""
    stock_quantity: Optional[int] = 0
    revenue: Optional[float] = 0.0
    
    @field_validator("current_price")
    @classmethod
    def validate_price(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("Price must be positive")
        return v


class ProductCreate(ProductBase):
    """Schema for creating a product."""
    pass


class ProductUpdate(BaseModel):
    """Schema for updating a product."""
    name: Optional[str] = None
    sku: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    brand: Optional[str] = None
    base_price: Optional[float] = None
    current_price: Optional[float] = None
    cost_price: Optional[float] = None
    stock_quantity: Optional[int] = None
    revenue: Optional[float] = None
    status: Optional[str] = None


class ProductResponse(ProductBase):
    """Schema for product response."""
    id: int
    status: str
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class ProductListResponse(BaseModel):
    """Schema for paginated product list."""
    items: list[ProductResponse]
    total: int
    skip: int = 0
    limit: int = 20
