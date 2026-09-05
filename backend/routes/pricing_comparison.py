import logging
from typing import Any, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
import io

from routes.competitor_monitoring import get_current_user_lazy
from services.pricing_comparison_service import PricingComparisonService

logger = logging.getLogger("routes.pricing_comparison")
router = APIRouter(prefix="/api/pricing-comparison", tags=["Pricing Comparison"])

def parse_date(date_str: Optional[str]) -> Optional[datetime]:
    if not date_str:
        return None
    try:
        # Support YYYY-MM-DD
        return datetime.strptime(date_str.split("T")[0], "%Y-%m-%d")
    except ValueError:
        try:
            return datetime.fromisoformat(date_str)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid date format: {date_str}. Use YYYY-MM-DD.")

@router.get("/{product_id}")
def get_pricing_comparison(
    product_id: str,
    start_date: Optional[str] = Query(None, description="Start date YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="End date YYYY-MM-DD"),
    competitor: Optional[str] = Query(None, description="Competitor name filter"),
    user: Any = Depends(get_current_user_lazy)
):
    """
    Returns comparative pricing statistics for a product against monitored competitors.
    """
    from main import SessionLocal
    db = SessionLocal()
    service = PricingComparisonService()
    
    parsed_start = parse_date(start_date)
    parsed_end = parse_date(end_date)
    
    try:
        stats = service.calculate_pricing_comparison(
            db,
            product_id=product_id,
            start_date=parsed_start,
            end_date=parsed_end,
            competitor_filter=competitor
        )
        return stats
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        logger.error(f"Error calculating pricing comparison: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

@router.get("/{product_id}/history")
def get_pricing_comparison_history(
    product_id: str,
    start_date: Optional[str] = Query(None, description="Start date YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="End date YYYY-MM-DD"),
    competitor: Optional[str] = Query(None, description="Competitor name filter"),
    user: Any = Depends(get_current_user_lazy)
):
    """
    Returns historical pricing comparison points grouped by day.
    """
    from main import SessionLocal
    db = SessionLocal()
    service = PricingComparisonService()
    
    parsed_start = parse_date(start_date)
    parsed_end = parse_date(end_date)
    
    try:
        history = service.calculate_historical_comparison(
            db,
            product_id=product_id,
            start_date=parsed_start,
            end_date=parsed_end,
            competitor_filter=competitor
        )
        return history
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        logger.error(f"Error loading historical pricing comparison: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

@router.get("/{product_id}/export/pdf")
def export_pricing_comparison_pdf(
    product_id: str,
    start_date: Optional[str] = Query(None, description="Start date YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="End date YYYY-MM-DD"),
    competitor: Optional[str] = Query(None, description="Competitor name filter"),
    user: Any = Depends(get_current_user_lazy)
):
    """
    Exports the pricing comparison details as a formatted PDF document.
    """
    from main import SessionLocal
    db = SessionLocal()
    service = PricingComparisonService()
    
    parsed_start = parse_date(start_date)
    parsed_end = parse_date(end_date)
    
    try:
        stats = service.calculate_pricing_comparison(
            db,
            product_id=product_id,
            start_date=parsed_start,
            end_date=parsed_end,
            competitor_filter=competitor
        )
        pdf_bytes = service.generate_pdf_report(stats)
        
        return StreamingResponse(
            io.BytesIO(pdf_bytes),
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename=pricing_report_{product_id}.pdf"
            }
        )
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        logger.error(f"Error exporting PDF pricing report: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

@router.get("/{product_id}/export/csv")
def export_pricing_comparison_csv(
    product_id: str,
    start_date: Optional[str] = Query(None, description="Start date YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="End date YYYY-MM-DD"),
    competitor: Optional[str] = Query(None, description="Competitor name filter"),
    user: Any = Depends(get_current_user_lazy)
):
    """
    Exports the pricing comparison details as a CSV spreadsheet.
    """
    from main import SessionLocal
    db = SessionLocal()
    service = PricingComparisonService()
    
    parsed_start = parse_date(start_date)
    parsed_end = parse_date(end_date)
    
    try:
        stats = service.calculate_pricing_comparison(
            db,
            product_id=product_id,
            start_date=parsed_start,
            end_date=parsed_end,
            competitor_filter=competitor
        )
        csv_string = service.generate_csv_report(stats)
        
        return StreamingResponse(
            io.BytesIO(csv_string.encode("utf-8")),
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename=pricing_report_{product_id}.csv"
            }
        )
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        logger.error(f"Error exporting CSV pricing report: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()
