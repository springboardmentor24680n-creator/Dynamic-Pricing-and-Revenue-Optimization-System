import logging
from typing import Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Query

from routes.competitor_monitoring import get_current_user_lazy
from services.profitability_analytics_service import ProfitabilityAnalyticsService

logger = logging.getLogger("routes.profitability")
router = APIRouter(prefix="/api/profitability", tags=["Profitability"])

@router.get("/overview")
def get_profitability_overview(
    product_id: Optional[str] = Query(None, description="Optional product ID filter"),
    user: Any = Depends(get_current_user_lazy)
):
    """
    Returns high-level profitability KPI metrics.
    """
    from main import SessionLocal
    db = SessionLocal()
    service = ProfitabilityAnalyticsService()
    try:
        overview = service.calculate_overview(db, product_id=product_id)
        return overview
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        logger.error(f"Error calculating profitability overview: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

@router.get("/product/{product_id}")
def get_product_profitability_details(
    product_id: str,
    user: Any = Depends(get_current_user_lazy)
):
    """
    Returns detailed profitability, forecast projections, and pricing recommendations impact for a product.
    """
    from main import SessionLocal
    db = SessionLocal()
    service = ProfitabilityAnalyticsService()
    try:
        details = service.calculate_product_details(db, product_id)
        return details
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        logger.error(f"Error fetching product profitability details for {product_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

@router.get("/trends")
def get_profitability_trends(
    user: Any = Depends(get_current_user_lazy)
):
    """
    Returns monthly aggregated revenue, cost, profit, and margin trends.
    """
    from main import SessionLocal
    db = SessionLocal()
    service = ProfitabilityAnalyticsService()
    try:
        trends = service.calculate_trends(db)
        return trends
    except Exception as e:
        logger.error(f"Error loading profitability trends: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

@router.get("/top-products")
def get_top_profitable_products(
    user: Any = Depends(get_current_user_lazy)
):
    """
    Returns lists of top performing products by profit/revenue and low-margin items.
    """
    from main import SessionLocal
    db = SessionLocal()
    service = ProfitabilityAnalyticsService()
    try:
        top_prods = service.calculate_top_products(db)
        return top_prods
    except Exception as e:
        logger.error(f"Error calculating top profitable products: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()
