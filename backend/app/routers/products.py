"""
PricePilot AI - Products Router
"""

import csv
import io

from fastapi import APIRouter, Depends, Query, status, Body
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import Optional, Dict

from app.database import get_db
from app.dependencies import get_current_user, require_role
from app.models.user import User
from app.schemas.product import ProductCreate, ProductUpdate, ProductResponse, ProductListResponse
from app.schemas.common import MessageResponse
from app.services.product import ProductService

router = APIRouter(prefix="/api/v1/products", tags=["Products"])


@router.get("/", response_model=ProductListResponse)
def list_products(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    category: Optional[str] = None,
    search: Optional[str] = None,
    status_filter: Optional[str] = Query(None, alias="status"),
    sort_by: Optional[str] = Query(None, pattern="^(name|brand|price|stock|revenue|created_at)$"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List products with pagination, filtering, search, and sorting."""
    service = ProductService(db)
    total, products = service.list_all(
        skip=skip, limit=limit, category=category, search=search,
        status_filter=status_filter, sort_by=sort_by, sort_order=sort_order,
    )
    return ProductListResponse(
        items=[ProductResponse.model_validate(p) for p in products],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get("/{product_id}", response_model=ProductResponse)
def get_product(
    product_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a single product by ID."""
    service = ProductService(db)
    product = service.get_by_id(product_id)
    return product


@router.post("/", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
def create_product(
    data: ProductCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["admin", "pricing_manager"])),
):
    """Create a new product."""
    service = ProductService(db)
    product = service.create(data, current_user.id)
    return product


@router.put("/{product_id}", response_model=ProductResponse)
def update_product(
    product_id: int,
    data: ProductUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["admin", "pricing_manager"])),
):
    """Update a product."""
    service = ProductService(db)
    product = service.update(product_id, data, current_user.id)
    return product


@router.patch("/{product_id}/status", response_model=ProductResponse)
def toggle_product_status(
    product_id: int,
    body: Dict = Body(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["admin", "pricing_manager"])),
):
    """Toggle a product's active/inactive status."""
    service = ProductService(db)
    product = service.set_status(product_id, body.get("status", "active"))
    return product


@router.delete("/{product_id}", response_model=MessageResponse)
def delete_product(
    product_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["admin"])),
):
    """Delete a product."""
    service = ProductService(db)
    service.delete(product_id)
    return MessageResponse(message="Product deleted successfully")


@router.post("/bulk-delete", response_model=MessageResponse)
def bulk_delete_products(
    body: Dict = Body(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["admin"])),
):
    """Bulk delete products by IDs."""
    service = ProductService(db)
    ids = body.get("ids", [])
    deleted = service.bulk_delete(ids)
    return MessageResponse(message=f"Deleted {deleted} products")


@router.post("/bulk-status", response_model=MessageResponse)
def bulk_update_status(
    body: Dict = Body(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["admin", "pricing_manager"])),
):
    """Bulk update product status."""
    service = ProductService(db)
    ids = body.get("ids", [])
    new_status = body.get("status", "active")
    updated = service.bulk_set_status(ids, new_status)
    return MessageResponse(message=f"Updated status of {updated} products")


@router.get("/categories/all", response_model=list)
def get_categories(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get all product categories."""
    service = ProductService(db)
    return service.get_categories()


@router.get("/export/csv")
def export_products_csv(
    category: Optional[str] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Export filtered products as CSV."""
    service = ProductService(db)
    _, products = service.list_all(skip=0, limit=10000, category=category, search=search)

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["name", "sku", "category", "brand", "base_price", "current_price", "cost_price",
                     "stock_quantity", "revenue", "status", "image_url", "description"])
    for p in products:
        writer.writerow([
            p.name, p.sku, p.category or "", p.brand or "", p.base_price, p.current_price,
            p.cost_price or 0, p.stock_quantity or 0, p.revenue or 0,
            p.status, p.image_url or "", p.description or "",
        ])
    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=products.csv"},
    )
