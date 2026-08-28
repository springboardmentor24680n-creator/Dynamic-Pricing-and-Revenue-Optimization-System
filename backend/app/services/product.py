"""
PricePilot AI - Product Service
"""

from sqlalchemy import or_
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from typing import Optional, List

from app.models.product import Product
from app.models.pricing_history import PricingHistory
from app.models.activity_log import ActivityLog
from app.schemas.product import ProductCreate, ProductUpdate
from app.services.competitor_service import parse_brand


class ProductService:
    """Service for product CRUD operations."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create(self, data: ProductCreate, user_id: int) -> Product:
        """Create a new product."""
        existing = self.db.query(Product).filter(Product.sku == data.sku).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Product with this SKU already exists",
            )
        
        product = Product(
            name=data.name,
            sku=data.sku,
            category=data.category,
            brand=data.brand or parse_brand(data.name),
            base_price=data.base_price,
            current_price=data.current_price,
            cost_price=data.cost_price,
            description=data.description,
            stock_quantity=data.stock_quantity,
            revenue=data.revenue or 0.0,
            image_url=data.image_url or "",
        )
        self.db.add(product)
        self.db.flush()

        self.db.add(PricingHistory(
            product_id=product.id,
            old_price=data.base_price,
            new_price=data.current_price,
            change_reason="Product created",
            changed_by=user_id,
        ))
        self.db.add(ActivityLog(
            action=f"Product '{product.name}' created",
            resource_type="product",
            resource_id=product.id,
            details=f"SKU {product.sku}, price ${product.current_price:.2f}",
            user_id=user_id,
        ))
        self.db.commit()
        self.db.refresh(product)
        return product
    
    def get_by_id(self, product_id: int) -> Product:
        """Get a product by ID."""
        product = self.db.query(Product).filter(Product.id == product_id).first()
        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Product not found",
            )
        return product
    
    def list_all(self, skip: int = 0, limit: int = 20,
                 category: Optional[str] = None,
                 search: Optional[str] = None,
                 status_filter: Optional[str] = None,
                 sort_by: Optional[str] = None,
                 sort_order: str = "desc") -> tuple:
        """List products with pagination, filtering, search, and sorting."""
        query = self.db.query(Product)
        
        if category:
            query = query.filter(Product.category == category)
        if status_filter:
            query = query.filter(Product.status == status_filter)
        if search:
            # Tokenized dynamic search: split on whitespace and require every
            # token to match somewhere in name / SKU / description / category.
            # This makes "dell laptop", "samsung phone" and "nike shoes"
            # behave like a real e-commerce search instead of a single blob
            # match. Tokens are case-insensitive (ILIKE).
            tokens = [t.strip() for t in search.split() if t.strip()]
            for token in tokens:
                token_pattern = f"%{token}%"
                query = query.filter(
                    or_(
                        Product.name.ilike(token_pattern),
                        Product.sku.ilike(token_pattern),
                        Product.description.ilike(token_pattern),
                        Product.category.ilike(token_pattern),
                        Product.brand.ilike(token_pattern),
                    )
                )
        
        # Sorting
        sort_map = {
            "name": Product.name,
            "brand": Product.brand,
            "price": Product.current_price,
            "stock": Product.stock_quantity,
            "revenue": Product.revenue,
            "created_at": Product.created_at,
        }
        sort_col = sort_map.get(sort_by, Product.created_at)
        if sort_order == "asc":
            query = query.order_by(sort_col.asc())
        else:
            query = query.order_by(sort_col.desc())
        
        total = query.count()
        products = query.offset(skip).limit(limit).all()
        return total, products
    
    def update(self, product_id: int, data: ProductUpdate, user_id: Optional[int] = None) -> Product:
        """Update a product."""
        product = self.get_by_id(product_id)
        update_data = data.model_dump(exclude_unset=True)
        
        if "sku" in update_data:
            existing = (
                self.db.query(Product)
                .filter(Product.sku == update_data["sku"], Product.id != product_id)
                .first()
            )
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="SKU already in use by another product",
                )
        
        for field, value in update_data.items():
            setattr(product, field, value)
        # Auto-populate brand from name when name changes or brand is not set
        if "name" in update_data or not product.brand:
            product.brand = update_data.get("brand") or parse_brand(product.name or "")
        
        self.db.add(ActivityLog(
            action=f"Product '{product.name}' updated",
            resource_type="product",
            resource_id=product.id,
            user_id=user_id,
        ))
        self.db.commit()
        self.db.refresh(product)
        return product
    
    def set_status(self, product_id: int, new_status: str) -> Product:
        """Set a product's status (active/inactive)."""
        if new_status not in ("active", "inactive"):
            raise HTTPException(status_code=400, detail="Status must be 'active' or 'inactive'")
        product = self.get_by_id(product_id)
        product.status = new_status
        self.db.commit()
        self.db.refresh(product)
        return product
    
    def bulk_delete(self, ids: List[int]) -> int:
        """Delete multiple products by IDs. Returns count deleted."""
        if not ids:
            raise HTTPException(status_code=400, detail="No product IDs provided")
        deleted = 0
        for pid in ids:
            product = self.db.query(Product).filter(Product.id == pid).first()
            if product:
                self.db.delete(product)
                deleted += 1
        self.db.commit()
        return deleted
    
    def bulk_set_status(self, ids: List[int], new_status: str) -> int:
        """Set status for multiple products. Returns count updated."""
        if new_status not in ("active", "inactive"):
            raise HTTPException(status_code=400, detail="Status must be 'active' or 'inactive'")
        if not ids:
            raise HTTPException(status_code=400, detail="No product IDs provided")
        updated = 0
        for pid in ids:
            product = self.db.query(Product).filter(Product.id == pid).first()
            if product:
                product.status = new_status
                updated += 1
        self.db.commit()
        return updated
    
    def delete(self, product_id: int):
        """Delete a product."""
        product = self.get_by_id(product_id)
        self.db.delete(product)
        self.db.commit()
    
    def get_categories(self) -> list:
        """Get all distinct product categories."""
        results = self.db.query(Product.category).distinct().all()
        return [r[0] for r in results if r[0]]
