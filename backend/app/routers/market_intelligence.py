"""
PricePilot AI - Market Intelligence & Pricing Comparison Report Router

Exposes:
  * Market intelligence for a product (position, range, opportunity, insights).
  * A business-readable pricing comparison report that integrates the existing
    AI prediction and demand forecast as context.

All metrics are derived from real available data (verified live prices or
PricePilot reference prices) - nothing is fabricated or estimated.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.services.market_intelligence_service import MarketIntelligenceService
from app.services.pricing_comparison_report_service import PricingComparisonReportService

router = APIRouter(prefix="/api/v1/market-intelligence", tags=["Market Intelligence"])


@router.get("/{product_id}")
def market_intelligence(
    product_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Market intelligence for a product built from real competitor data.

    Includes competitor count/availability, verified & reference price ranges,
    average (only when sufficient verified prices exist), our price position,
    pricing opportunity and business-level insights. Unavailable data is
    reported as such - never invented.
    """
    try:
        service = MarketIntelligenceService(db)
        return service.analyze(product_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/{product_id}/report")
def pricing_comparison_report(
    product_id: int,
    horizon: int = Query(30, ge=7, le=365),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Business-readable pricing comparison report for one product.

    Combines product data, comparable competitors, price differences, market
    price range, positioning, key pricing insight, source links and the
    existing AI prediction + demand forecast (as context only).
    """
    try:
        service = PricingComparisonReportService(db)
        return service.generate(product_id, horizon=horizon)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))