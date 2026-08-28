"""
PricePilot AI - Competitor Monitoring Router

Exposes competitor-product comparison for a selected catalog item and
marketplace-source metadata for the UI.

Business rule: competitors are products (exact or closely matching), not
marketplace websites. Amazon India, Flipkart, Croma, etc. are sources.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.services.competitor_service import CompetitorService

router = APIRouter(prefix="/api/v1/competitors", tags=["Competitor Monitoring"])


@router.get("/{product_id}")
def competitor_analysis(
    product_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Competitor-product comparison for a selected catalog item.

    Returns matched competitor products (exact or closely matching) with
    reference prices and marketplace source links for external verification.
    Marketplaces are sources, not competitors — live listing prices are
    unavailable unless a permitted provider confirms them.
    """
    try:
        service = CompetitorService(db)
        result = service.analyze(product_id)
        for i, comp in enumerate(result.get("competitors", []), start=1):
            comp["rank"] = i
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/platforms/list")
def platform_metadata(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Metadata about supported platforms, category targeting and the
    configured data provenance (reference vs. unavailable) for the UI."""
    service = CompetitorService(db)
    return service.platform_catalog()