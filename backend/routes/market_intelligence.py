import logging
from typing import Any
from fastapi import APIRouter, Depends, HTTPException

from routes.competitor_monitoring import get_current_user_lazy
from services.market_intelligence_service import MarketIntelligenceService

logger = logging.getLogger("routes.market_intelligence")
router = APIRouter(prefix="/api/market-intelligence", tags=["Market Intelligence"])

@router.get("/portfolio")
def get_portfolio_intelligence(
    user: Any = Depends(get_current_user_lazy)
):
    """
    Returns summarized catalog-wide market intelligence metrics and classifications.
    """
    from main import SessionLocal
    db = SessionLocal()
    service = MarketIntelligenceService()
    try:
        portfolio_stats = service.calculate_portfolio_intelligence(db)
        return portfolio_stats
    except Exception as e:
        logger.error(f"Error calculating portfolio market intelligence: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

@router.get("/{product_id}")
def get_product_intelligence(
    product_id: str,
    user: Any = Depends(get_current_user_lazy)
):
    """
    Returns synthesized market intelligence details for a single product.
    """
    from main import SessionLocal
    db = SessionLocal()
    service = MarketIntelligenceService()
    try:
        stats = service.calculate_product_intelligence(db, product_id)
        return stats
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        logger.error(f"Error calculating product market intelligence for {product_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()
