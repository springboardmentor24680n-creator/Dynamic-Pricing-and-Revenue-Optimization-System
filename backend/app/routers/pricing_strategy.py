"""
PricePilot AI - Pricing Strategy Recommendations Router
"""

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.services.pricing_strategy_service import PricingStrategyService

router = APIRouter(prefix="/api/v1/pricing-strategy", tags=["Pricing Strategy"])


@router.get("/recommendations")
def get_recommendations(
    category: str = Query(None),
    search: str = Query(None),
    sort_by: str = Query("priority"),
    sort_order: str = Query("desc"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Get pricing strategy recommendations for all products."""
    svc = PricingStrategyService(db)
    return svc.all_recommendations(
        category=category, search=search,
        sort_by=sort_by, sort_order=sort_order,
        skip=skip, limit=limit,
    )


@router.get("/recommendations/{product_id}")
def get_product_recommendation(
    product_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Get detailed pricing recommendation for a single product."""
    svc = PricingStrategyService(db)
    try:
        return svc.product_recommendation(product_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/summary")
def get_summary(
    category: str = Query(None),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Get summary KPIs for pricing strategy."""
    svc = PricingStrategyService(db)
    return svc.summary(category=category)


@router.get("/categories")
def get_categories(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Get available product categories."""
    svc = PricingStrategyService(db)
    return svc.categories()
