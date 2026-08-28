"""
PricePilot AI - Executive Business Intelligence Router
"""

from fastapi import APIRouter, Depends, Query, BackgroundTasks
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.services.business_intelligence_service import BusinessIntelligenceService
from app.services.analytics_precompute import AnalyticsPrecomputeService

router = APIRouter(prefix="/api/v1/business-intelligence", tags=["Business Intelligence"])


def _run_background_precompute(db_factory, days):
    """Run precomputation in background (detached from request)."""
    db = db_factory()
    try:
        svc = AnalyticsPrecomputeService(db)
        svc.precompute_all(days)
    except Exception as e:
        import logging
        logging.getLogger(__name__).error("Background precompute failed: %s", e)
    finally:
        db.close()


@router.get("/summary")
def get_executive_summary(
    days: int = Query(None, ge=1, le=365),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Full executive BI summary with KPIs, trends, alerts, and priority actions.

    Reads from precomputed cache. If cache is missing, triggers background
    precomputation and returns available data.
    """
    svc = BusinessIntelligenceService(db)
    return svc.executive_summary(days=days)


@router.post("/refresh")
def refresh_analytics(
    days: int = Query(None, ge=1, le=365),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Trigger background analytics refresh. Returns immediately."""
    from app.database import SessionLocal
    background_tasks.add_task(_run_background_precompute, SessionLocal, days)
    return {"status": "refresh_started", "message": "Analytics refresh triggered in background."}


@router.get("/cache-status")
def get_cache_status(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Get status of all analytics cache entries."""
    svc = AnalyticsPrecomputeService(db)
    return svc.cache_status()
