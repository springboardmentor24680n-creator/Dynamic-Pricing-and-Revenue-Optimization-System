import logging
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, Request
from jose import jwt, JWTError

from services.seasonal_trend_service import SeasonalTrendService

logger = logging.getLogger("routes.seasonal_trends")
router = APIRouter(prefix="/api/seasonal-trends", tags=["Seasonal Trends"])

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

@router.get("/{product_id}")
def get_seasonal_trends(product_id: str, user: Any = Depends(get_current_user_lazy)):
    """
    Returns seasonal demand analytics, breakdowns, and actionable recommendations.
    """
    service = SeasonalTrendService()
    try:
        return service.get_seasonal_trends(product_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error fetching seasonal trends for product {product_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
