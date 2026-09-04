"""
PricePilot AI - Pricing Service
"""

from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from typing import Optional

from app.models.product import Product
from app.models.pricing_history import PricingHistory
from app.schemas.pricing import PriceUpdateRequest


class PricingService:
    """Service for manual price management with history tracking."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def update_price(self, product_id: int, data: PriceUpdateRequest, user_id: int) -> dict:
        """Update product price and record in pricing history."""
        product = self.db.query(Product).filter(Product.id == product_id).first()
        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Product not found",
            )
        
        old_price = product.current_price
        product.current_price = data.new_price
        
        history = PricingHistory(
            product_id=product_id,
            old_price=old_price,
            new_price=data.new_price,
            change_reason=data.reason,
            changed_by=user_id,
        )
        self.db.add(history)
        self.db.commit()
        self.db.refresh(product)

        # Price edits change model predictions (price is a model feature) and
        # every competitor price-range that referenced this product, so drop the
        # in-process analytics caches before the next read.
        try:
            from app.services.training_service import invalidate_analytics_caches
            invalidate_analytics_caches()
        except Exception:
            pass

        return {
            "message": "Price updated successfully",
            "product_id": product_id,
            "product_name": product.name,
            "old_price": round(old_price, 2),
            "new_price": round(data.new_price, 2),
            "change": round(data.new_price - old_price, 2),
        }
    
    def get_price_history(self, product_id: int, limit: int = 20) -> list:
        """Get pricing history for a product."""
        product = self.db.query(Product).filter(Product.id == product_id).first()
        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Product not found",
            )
        
        history = (
            self.db.query(PricingHistory)
            .filter(PricingHistory.product_id == product_id)
            .order_by(PricingHistory.created_at.desc())
            .limit(limit)
            .all()
        )
        
        return [
            {
                "old_price": round(h.old_price, 2) if h.old_price else None,
                "new_price": round(h.new_price, 2),
                "change_reason": h.change_reason,
                "changed_by": h.changed_by,
                "created_at": h.created_at.isoformat() if h.created_at else None,
            }
            for h in history
        ]
