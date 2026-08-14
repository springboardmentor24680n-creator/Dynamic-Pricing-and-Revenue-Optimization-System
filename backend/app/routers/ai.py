"""
PricePilot AI - AI Pricing Engine Router
Real ML-powered price optimization using Random Forest, XGBoost, and Linear Regression.

Models are trained on user-uploaded datasets (persisted to disk + model_runs),
and prediction loads the saved model - it never retrains per request.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Body
from fastapi.responses import Response
from sqlalchemy.orm import Session
from typing import Optional, Dict

from app.database import get_db
from app.dependencies import get_current_user, require_role
from app.models.user import User
from app.services.ml_service import PricingMLService
from app.services.forecast_service import ForecastService
from app.services.training_service import ModelTrainingService

router = APIRouter(prefix="/api/v1/ai", tags=["AI Pricing Engine"])


@router.get("/status")
def get_ai_status(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get AI engine status: data availability, persisted model, training state."""
    service = PricingMLService(db)
    return service.get_model_status()


@router.get("/model-info")
def get_model_info(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Full metadata of the latest AI training run (best model, metrics, features,
    dataset, training date, prediction-time source)."""
    service = ModelTrainingService(db)
    return service.model_info()


@router.post("/train")
def train_models(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["admin", "pricing_manager"])),
):
    """Kick off a background training run on the current catalog + sales history.
    Returns immediately; training completes in the background."""
    service = ModelTrainingService(db)
    run_id = service.start_background_training(current_user.id)
    return {
        "message": "AI training started in the background",
        "run_id": run_id,
        "status": "training",
    }


@router.post("/retrain")
def retrain_models(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["admin", "pricing_manager"])),
):
    """Manually retrain the models with the latest data (background)."""
    service = ModelTrainingService(db)
    run_id = service.start_background_training(current_user.id)
    return {
        "message": "AI model retraining started in the background",
        "run_id": run_id,
        "status": "training",
    }


@router.get("/predict/{product_id}")
def predict_product(
    product_id: int,
    include_forecast: bool = Query(False, description="Fold the demand forecast into the recommendation"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Predict the optimal price for a product using the persisted trained model.

    Never retrains - loads the saved model and scores the product instantly.
    Returns recommended price, expected revenue / profit, confidence and
    data-driven explanation factors.
    """
    try:
        service = PricingMLService(db)
        return service.predict_product(product_id, include_forecast=include_forecast)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/forecast")
def forecast_portfolio(
    horizon: int = Query(30, ge=7, le=365),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Quick demand outlook across the whole catalog (fast trend analysis)."""
    service = ForecastService(db)
    return service.portfolio_summary(horizon)


@router.get("/forecast/{product_id}")
def forecast_product_demand(
    product_id: int,
    horizon: int = Query(30, ge=7, le=365),
    force: bool = Query(False, description="Re-train the Prophet model, ignoring the cache"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Prophet demand forecast for one product with confidence intervals."""
    try:
        service = ForecastService(db)
        return service.forecast_product(product_id, horizon, force, current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/optimize/{product_id}")
def optimize_product_price(
    product_id: int,
    include_forecast: bool = Query(False, description="Fold the demand forecast into the recommendation"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["admin", "pricing_manager"])),
):
    """Get AI-powered price optimization for a product (alias of predict)."""
    try:
        service = PricingMLService(db)
        result = service.analyze_product(product_id, include_forecast=include_forecast)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/optimize/{product_id}/save")
def save_recommendation(
    product_id: int,
    body: Dict = Body(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["admin", "pricing_manager"])),
):
    """Persist an AI recommendation to the approval workflow."""
    service = PricingMLService(db)
    analysis = service.analyze_product(product_id)
    if analysis.get("insufficient_data"):
        raise HTTPException(status_code=400, detail=analysis["recommendation"])
    rec = service.save_recommendation(analysis, current_user.id)
    return {
        "message": "Recommendation saved for approval",
        "recommendation_id": rec.id,
        "status": rec.status,
        "recommended_price": rec.recommended_price,
        "confidence_score": rec.confidence_score,
    }


@router.get("/batch-optimize")
def batch_optimize_prices(
    category: Optional[str] = Query(None),
    include_forecast: bool = Query(False),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["admin", "pricing_manager"])),
):
    """Batch analyze all products (optionally filtered by category)."""
    service = PricingMLService(db)
    results = service.batch_analyze(category, include_forecast=include_forecast)
    return {"total_analyzed": len(results), "results": results}


@router.post("/predict-revenue/{product_id}")
def predict_revenue_impact(
    product_id: int,
    new_price: float = Query(..., gt=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["admin", "pricing_manager"])),
):
    """Predict revenue impact of a price change using the trained model."""
    try:
        service = PricingMLService(db)
        result = service.get_revenue_prediction(product_id, new_price)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/report/{product_id}")
def ai_analysis_report(
    product_id: int,
    horizon: int = Query(30, ge=7, le=365),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Full AI Prediction Analysis Report for one product.

    A dynamic business-intelligence report (executive summary, prediction
    details, model performance, explainable factors, revenue impact, risk,
    forecast summary, recommendations, conclusion) built entirely from the
    persisted model, the prediction output, sales history, and the forecast.
    Never retrains and never uses hardcoded values.
    """
    from app.services.analysis_report_service import AnalysisReportService
    try:
        service = AnalysisReportService(db)
        return service.generate_report(product_id, horizon=horizon)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/report/{product_id}/export")
def export_ai_analysis_report(
    product_id: int,
    format: str = Query(..., pattern="^(csv|xlsx|pdf)$"),
    horizon: int = Query(30, ge=7, le=365),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Export the AI Prediction Analysis Report as CSV, Excel, or PDF."""
    from app.services.analysis_report_service import AnalysisReportService
    try:
        service = AnalysisReportService(db)
        report = service.generate_report(product_id, horizon=horizon)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    filename = f"ai_analysis_report_{product_id}"

    if format == "csv":
        data = service.to_csv(report)
        return Response(
            content=data,
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}.csv"},
        )

    if format == "xlsx":
        data = service.to_excel(report)
        return Response(
            content=data,
            media_type=("application/vnd.openxmlformats-officedocument."
                        "spreadsheetml.sheet"),
            headers={"Content-Disposition": f"attachment; filename={filename}.xlsx"},
        )

    data = service.to_pdf(report)
    return Response(
        content=data,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}.pdf"},
    )
