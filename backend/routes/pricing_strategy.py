import logging
from typing import Any
from fastapi import APIRouter, Depends, HTTPException
from routes.competitor_monitoring import get_current_user_lazy
from services.pricing_strategy_service import PricingStrategyService

logger = logging.getLogger("routes.pricing_strategy")
router = APIRouter(prefix="/api/pricing-strategy", tags=["Pricing Strategy"])

@router.get("/{product_id}")
def get_pricing_strategy(
    product_id: str,
    user: Any = Depends(get_current_user_lazy)
):
    """
    Exposes pricing strategy recommendations combining competitor, demand, inventory, and profitability signals.
    """
    from main import SessionLocal
    db = SessionLocal()
    service = PricingStrategyService()
    try:
        strategy_res = service.get_pricing_strategy(db, product_id)
        return strategy_res
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        logger.error(f"Error generating pricing strategy: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()
