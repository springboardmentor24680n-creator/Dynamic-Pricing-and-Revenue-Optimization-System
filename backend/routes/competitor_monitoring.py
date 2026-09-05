import logging
from typing import Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Request, Query
from jose import jwt, JWTError

from services.competitor_monitoring_service import CompetitorMonitoringService

logger = logging.getLogger("routes.competitor_monitoring")
router = APIRouter(prefix="/api/competitor-monitoring", tags=["Competitor Monitoring"])

async def get_current_user_lazy(request: Request):
    """
    Lazy authentication dependency that decodes the JWT and queries the user
    from the database without causing circular imports during initialization.
    """
    from main import SECRET_KEY, ALGORITHM, SessionLocal, User
    
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid token")
    
    token = auth_header.split(" ")[1]
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
        
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email).first()
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        return user
    finally:
        db.close()

@router.get("/competitors")
def get_monitored_competitors(user: Any = Depends(get_current_user_lazy)):
    """
    Returns a distinct list of monitored competitor names.
    """
    from main import SessionLocal
    db = SessionLocal()
    service = CompetitorMonitoringService()
    try:
        return service.get_monitored_competitors(db)
    except Exception as e:
        logger.error(f"Error fetching monitored competitors: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

@router.get("/latest")
def get_latest_prices(
    product_id: Optional[str] = Query(None, description="Optional product ID filter"),
    user: Any = Depends(get_current_user_lazy)
):
    """
    Returns the latest competitor price listings, optionally filtered by product_id.
    """
    from main import SessionLocal
    db = SessionLocal()
    service = CompetitorMonitoringService()
    try:
        return service.get_latest_prices(db, product_id=product_id)
    except Exception as e:
        logger.error(f"Error fetching latest competitor prices: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

@router.get("/history/{product_id}")
def get_price_history(product_id: str, user: Any = Depends(get_current_user_lazy)):
    """
    Returns the price history for a specific product ID.
    """
    from main import SessionLocal
    db = SessionLocal()
    service = CompetitorMonitoringService()
    try:
        return service.get_price_history(db, product_id=product_id)
    except Exception as e:
        logger.error(f"Error fetching price history for product {product_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

@router.get("/comparison/{product_id}")
def get_comparison_data(product_id: str, user: Any = Depends(get_current_user_lazy)):
    """
    Returns comparison metrics between our price and competitor prices.
    """
    from main import SessionLocal
    db = SessionLocal()
    service = CompetitorMonitoringService()
    try:
        return service.get_comparison_data(db, product_id=product_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error fetching comparison data for product {product_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

@router.post("/trigger-update")
def trigger_price_update(
    product_id: Optional[str] = Query(None, description="Optional product ID filter"),
    user: Any = Depends(get_current_user_lazy)
):
    """
    Trigger simulated price scraping/update from mock data source using the standard monitoring workflow.
    """
    from main import SessionLocal
    db = SessionLocal()
    service = CompetitorMonitoringService()
    try:
        results = service.run_monitoring_cycle(db, product_id=product_id, force_all=True)
        if results.get("status") == "already_running":
            raise HTTPException(
                status_code=409,
                detail="A competitor monitoring scan is already in progress."
            )
        return {
            "status": "success",
            "source": results["source"],
            "fallback_used": results["fallback_used"],
            "products_checked": results["products_checked"],
            "raw_products": results.get("raw_products", 0),
            "normalized_products": results.get("normalized_products", 0),
            "relevant_competitors": results.get("relevant_competitors", 0),
            "price_updates": results["price_updates"],
            "alerts_created": results["alerts_created"],
            # Compatibility fields
            "competitors_checked": results["competitors_checked"],
            "price_changes_detected": results["price_changes_detected"],
            "alerts_generated": results["alerts_generated"],
            "updated_count": results["price_changes_detected"]
        }
    except Exception as e:
        logger.error(f"Error triggering competitor price update: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


@router.get("/alerts")
def get_alerts(user: Any = Depends(get_current_user_lazy)):
    """
    Returns all competitor price alerts.
    """
    from main import SessionLocal, CompetitorAlert
    db = SessionLocal()
    try:
        alerts = db.query(CompetitorAlert).order_by(CompetitorAlert.created_at.desc()).all()
        return [
            {
                "id": a.id,
                "product_id": a.product_id,
                "competitor_name": a.competitor_name,
                "event_type": a.event_type,
                "previous_price": a.previous_price,
                "current_price": a.current_price,
                "change_amount": a.change_amount,
                "change_percent": a.change_percent,
                "severity": a.severity,
                "message": a.message,
                "created_at": a.created_at.isoformat() if a.created_at else None,
                "is_acknowledged": a.is_acknowledged
            }
            for a in alerts
        ]
    except Exception as e:
        logger.error(f"Error retrieving alerts: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


@router.get("/alerts/{product_id}")
def get_alerts_for_product(product_id: str, user: Any = Depends(get_current_user_lazy)):
    """
    Returns competitor price alerts for a specific product ID.
    """
    from main import SessionLocal, CompetitorAlert
    db = SessionLocal()
    try:
        alerts = db.query(CompetitorAlert).filter(
            CompetitorAlert.product_id == product_id
        ).order_by(CompetitorAlert.created_at.desc()).all()
        return [
            {
                "id": a.id,
                "product_id": a.product_id,
                "competitor_name": a.competitor_name,
                "event_type": a.event_type,
                "previous_price": a.previous_price,
                "current_price": a.current_price,
                "change_amount": a.change_amount,
                "change_percent": a.change_percent,
                "severity": a.severity,
                "message": a.message,
                "created_at": a.created_at.isoformat() if a.created_at else None,
                "is_acknowledged": a.is_acknowledged
            }
            for a in alerts
        ]
    except Exception as e:
        logger.error(f"Error retrieving alerts for product {product_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


@router.post("/alerts/{alert_id}/acknowledge")
def acknowledge_alert(alert_id: int, user: Any = Depends(get_current_user_lazy)):
    """
    Acknowledges a competitor price alert.
    """
    from main import SessionLocal, CompetitorAlert
    db = SessionLocal()
    try:
        alert = db.query(CompetitorAlert).filter(CompetitorAlert.id == alert_id).first()
        if not alert:
            raise HTTPException(status_code=404, detail=f"Alert with ID {alert_id} not found.")
        alert.is_acknowledged = True
        db.commit()
        return {"status": "success", "message": f"Alert {alert_id} acknowledged."}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error acknowledging alert {alert_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


@router.get("/status")
def get_monitoring_status(user: Any = Depends(get_current_user_lazy)):
    """
    Returns competitor price monitoring status including dual-provider telemetry.
    """
    from main import SessionLocal, CompetitorPrice, CompetitorAlert, CompetitorMonitoringRun
    from services.scheduler import scheduler
    from services.competitor_monitoring_service import CompetitorMonitoringService
    import os
    
    db = SessionLocal()
    try:
        # Check if competitor monitoring job is present and scheduler is running
        job = scheduler.get_job("competitor_monitoring")
        enabled = scheduler.running and (job is not None)

        next_run = None
        if job and job.next_run_time:
            next_run = job.next_run_time.isoformat()

        # Load last run from DB
        last_run = db.query(CompetitorMonitoringRun).order_by(CompetitorMonitoringRun.started_at.desc()).first()
        service = CompetitorMonitoringService()
        usage = service.get_api_usage_stats(db)

        # Determine states based on Requirement 16
        if last_run is None:
            data_source = "mock_fallback"
            api_status = "Not Run Yet"
            last_run_iso = None
            comp_found = 0
            prod_checked = 0
            alerts_gen = 0
        else:
            last_run_iso = last_run.started_at.isoformat() if last_run.started_at else None
            comp_found = last_run.relevant_competitors
            prod_checked = last_run.products_checked
            alerts_gen = last_run.alerts_created

            if last_run.status == "budget_exhausted":
                data_source = "budget_exhausted"
                api_status = "API BUDGET EXHAUSTED"
            elif last_run.status == "failed":
                if "429" in str(last_run.error_message) or "rate" in str(last_run.error_message).lower():
                    data_source = "rate_limit"
                    api_status = "API RATE LIMITED"
                else:
                    data_source = "api_error"
                    api_status = f"API ERROR: {last_run.error_message}"
            elif last_run.fallback_used or last_run.source == "mock_fallback":
                data_source = "mock_fallback"
                api_status = "Fallback Active"
            else:
                data_source = last_run.source
                api_status = "Success"

        unique_competitors = db.query(CompetitorPrice.competitor_name).distinct().count()

        price_changes = db.query(CompetitorPrice).filter(
            CompetitorPrice.price_change.isnot(None),
            CompetitorPrice.price_change != 0.0
        ).count()

        active_alerts = db.query(CompetitorAlert).filter(
            CompetitorAlert.is_acknowledged == False
        ).count()

        # Dual provider telemetry
        prices_api_key = os.getenv("PRICES_API_KEY", "").strip()
        openweb_key = os.getenv("OPENWEB_NINJA_API_KEY", "").strip() or os.getenv("OPENWEBNINJA_API_KEY", "").strip()

        # Primary Status
        if not prices_api_key:
            primary_status = "Not Configured"
        elif usage["budget_status"] == "exhausted":
            primary_status = "QUOTA EXCEEDED"
        elif last_run and last_run.status == "failed" and last_run.source == "pricesapi":
            primary_status = "ERROR"
        else:
            primary_status = "LIVE"

        # Backup Status
        if not openweb_key:
            backup_status = "Not Configured"
        elif usage["openweb_status"] == "exhausted":
            backup_status = "QUOTA EXCEEDED"
        elif last_run and last_run.status == "failed" and last_run.source == "openwebninja":
            backup_status = "ERROR"
        else:
            backup_status = "LIVE"

        last_success = db.query(CompetitorMonitoringRun).filter(
            CompetitorMonitoringRun.status == "success"
        ).order_by(CompetitorMonitoringRun.started_at.desc()).first()

        last_successful_provider = last_success.successful_provider if last_success else "None"
        last_successful_scan = last_success.started_at.isoformat() if last_success and last_success.started_at else None

        return {
            "monitoring_enabled": enabled,
            "last_monitoring_run": last_run_iso,
            "next_scheduled_run": next_run,
            "number_of_competitors_monitored": unique_competitors,
            "number_of_price_changes_detected": price_changes,
            "number_of_active_alerts": active_alerts,
            "data_source": data_source,
            "api_status": api_status,
            "competitors_found": comp_found,
            "products_checked": prod_checked,
            "alerts_generated": alerts_gen,
            
            # Dual-provider extensions
            "primary_provider": "PricesAPI",
            "primary_status": primary_status,
            "backup_provider": "OpenWeb Ninja",
            "backup_status": backup_status,
            "current_data_source": last_run.source if last_run else "mock_fallback",
            "prices_api_requests_used": usage["requests_used_this_month"],
            "prices_api_requests_remaining": usage["requests_remaining"],
            "last_successful_provider": last_successful_provider,
            "last_successful_scan": last_successful_scan
        }
    except Exception as e:
        logger.error(f"Error fetching competitor monitoring status: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


@router.get("/runs")
def get_monitoring_runs(limit: int = 20, user: Any = Depends(get_current_user_lazy)):
    """
    Returns recent competitor monitoring scheduled or manual runs.
    """
    from main import SessionLocal, CompetitorMonitoringRun
    db = SessionLocal()
    try:
        runs = db.query(CompetitorMonitoringRun).order_by(CompetitorMonitoringRun.started_at.desc()).limit(limit).all()
        return [
            {
                "id": r.id,
                "started_at": r.started_at.isoformat() if r.started_at else None,
                "completed_at": r.completed_at.isoformat() if r.completed_at else None,
                "status": r.status,
                "source": r.source,
                "products_checked": r.products_checked,
                "raw_products": r.raw_products,
                "normalized_products": r.normalized_products,
                "relevant_competitors": r.relevant_competitors,
                "price_updates": r.price_updates,
                "alerts_created": r.alerts_created,
                "api_requests": r.api_requests,
                "fallback_used": r.fallback_used,
                "error_message": r.error_message,
                "primary_provider": r.primary_provider,
                "successful_provider": r.successful_provider,
                "prices_api_requests": r.prices_api_requests,
                "openweb_ninja_requests": r.openweb_ninja_requests
            }
            for r in runs
        ]
    except Exception as e:
        logger.error(f"Error fetching monitoring runs: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


@router.get("/api-usage")
def get_api_usage(user: Any = Depends(get_current_user_lazy)):
    """
    Returns monthly API requests usage stats and budget limits.
    """
    from main import SessionLocal
    db = SessionLocal()
    service = CompetitorMonitoringService()
    try:
        usage = service.get_api_usage_stats(db)
        return {
            "monthly_limit": usage["monthly_limit"],
            "requests_used": usage["requests_used_this_month"],
            "requests_remaining": usage["requests_remaining"],
            "estimated_monthly_usage": usage["estimated_monthly_usage"],
            "budget_status": usage["budget_status"]
        }
    except Exception as e:
        logger.error(f"Error fetching API usage stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


@router.get("/scheduler")
def get_scheduler_status(user: Any = Depends(get_current_user_lazy)):
    """
    Returns status parameters and configuration settings for the background monitoring scheduler.
    """
    from main import SessionLocal, Product, CompetitorMonitoringRun
    from services.scheduler import scheduler
    from datetime import datetime
    import os
    
    db = SessionLocal()
    try:
        enabled = os.getenv("COMPETITOR_MONITORING_ENABLED", "true").lower() == "true"
        
        try:
            interval_hours = int(os.getenv("COMPETITOR_SCAN_INTERVAL_HOURS", "6"))
        except ValueError:
            interval_hours = 6
            
        last_run = db.query(CompetitorMonitoringRun).order_by(CompetitorMonitoringRun.started_at.desc()).first()
        
        next_run = None
        if scheduler.running:
            job = scheduler.get_job("competitor_monitoring")
            if job and job.next_run_time:
                next_run = job.next_run_time.isoformat()
                
        now = datetime.utcnow()
        products_due = db.query(Product).filter(
            (Product.next_competitor_scan.is_(None)) | (Product.next_competitor_scan <= now)
        ).count()
        
        service = CompetitorMonitoringService()
        usage = service.get_api_usage_stats(db)
        
        return {
            "enabled": enabled,
            "interval_hours": interval_hours,
            "last_run": {
                "started_at": last_run.started_at.isoformat() if last_run and last_run.started_at else None,
                "status": last_run.status if last_run else "never",
                "source": last_run.source if last_run else None,
                "fallback_used": last_run.fallback_used if last_run else False
            } if last_run else None,
            "next_run": next_run,
            "status": last_run.status if last_run else "inactive",
            "products_due": products_due,
            "api_budget_remaining": usage["requests_remaining"]
        }
    except Exception as e:
        logger.error(f"Error fetching scheduler status: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()
