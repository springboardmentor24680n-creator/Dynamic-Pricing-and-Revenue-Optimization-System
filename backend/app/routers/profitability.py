"""
PricePilot AI - Profitability Analytics Router
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.services.profitability_service import ProfitabilityService

router = APIRouter(prefix="/api/v1/profitability", tags=["Profitability Analytics"])


@router.get("/summary")
def profitability_summary(
    days: int = Query(None, ge=1, le=365),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Top-level profitability KPIs: revenue, cost, profit, margin, best/lowest."""
    return ProfitabilityService(db).summary(days=days)


@router.get("/trends")
def profitability_trends(
    days: int = Query(None, ge=1, le=365),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Daily profitability trend: revenue vs cost vs profit over time."""
    return ProfitabilityService(db).trends(days=days)


@router.get("/products")
def profitability_products(
    days: int = Query(None, ge=1, le=365),
    search: str = Query(None),
    sort_by: str = Query("profit", pattern="^(revenue|profit|margin|units|name)$"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Per-product profitability table with sorting and search."""
    return ProfitabilityService(db).products(
        days=days, search=search, sort_by=sort_by,
        sort_order=sort_order, skip=skip, limit=limit,
    )


@router.get("/categories")
def profitability_categories(
    days: int = Query(None, ge=1, le=365),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Category-level profitability breakdown."""
    return ProfitabilityService(db).categories(days=days)


@router.get("/ai-impact")
def profitability_ai_impact(
    days: int = Query(None, ge=1, le=365),
    top_n: int = Query(20, ge=1, le=50),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """AI pricing profit impact: current vs recommended price profitability."""
    return ProfitabilityService(db).ai_impact(days=days, top_n=top_n)


@router.get("/opportunities")
def profitability_opportunities(
    days: int = Query(None, ge=1, le=365),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Data-driven profitability insights and alerts."""
    return ProfitabilityService(db).opportunities(days=days)
