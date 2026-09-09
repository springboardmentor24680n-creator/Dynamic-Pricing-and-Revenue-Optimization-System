
from fastapi import APIRouter, HTTPException
from database.session import SessionLocal
from models.product_model import Product
from models.product import ProductSchema

router = APIRouter(
    prefix="/products",
    tags=["Products"]
)


# ============================================================
# GET ALL PRODUCTS
# ============================================================

@router.get("/")
def get_products():

    db = SessionLocal()

    try:

        products = (
            db.query(Product)
            .order_by(Product.id.asc())
            .all()
        )

        # IMPORTANT:
        # Return plain dictionaries instead of SQLAlchemy
        # objects so the React frontend receives clean JSON.

        return [
            {
                "id": product.id,
                "product_name": product.product_name,
                "category": product.category,
                "price": product.price,
                "stock": product.stock
            }
            for product in products
        ]

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=f"Unable to load products: {str(e)}"
        )

    finally:

        db.close()


# ============================================================
# GET SINGLE PRODUCT
# ============================================================

@router.get("/{product_id}")
def get_product(product_id: int):

    db = SessionLocal()

    try:

        product = (
            db.query(Product)
            .filter(Product.id == product_id)
            .first()
        )

        if product is None:

            raise HTTPException(
                status_code=404,
                detail="Product not found."
            )

        return {
            "id": product.id,
            "product_name": product.product_name,
            "category": product.category,
            "price": product.price,
            "stock": product.stock
        }

    except HTTPException:

        raise

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=f"Unable to load product: {str(e)}"
        )

    finally:

        db.close()


# ============================================================
# ADD PRODUCT
# ============================================================

@router.post("/")
def add_product(product: ProductSchema):

    db = SessionLocal()

    try:

        product_name = (
            product.product_name or ""
        ).strip()

        category = (
            product.category or ""
        ).strip()

        if not product_name:

            raise HTTPException(
                status_code=400,
                detail="Product name is required."
            )

        if not category:

            raise HTTPException(
                status_code=400,
                detail="Category is required."
            )

        existing_product = (
            db.query(Product)
            .filter(
                Product.product_name.ilike(
                    product_name
                )
            )
            .first()
        )

        if existing_product:

            raise HTTPException(
                status_code=409,
                detail="Product already exists."
            )

        new_product = Product(
            product_name=product_name,
            category=category,
            price=product.price,
            stock=product.stock
        )

        db.add(new_product)

        db.commit()

        db.refresh(new_product)

        return {
            "message": "Product Added Successfully",
            "product": {
                "id": new_product.id,
                "product_name": new_product.product_name,
                "category": new_product.category,
                "price": new_product.price,
                "stock": new_product.stock
            }
        }

    except HTTPException:

        db.rollback()

        raise

    except Exception as e:

        db.rollback()

        raise HTTPException(
            status_code=500,
            detail=f"Unable to add product: {str(e)}"
        )

    finally:

        db.close()


# ============================================================
# UPDATE PRODUCT
# ============================================================

@router.put("/{product_id}")
def update_product(
    product_id: int,
    updated_product: ProductSchema
):

    db = SessionLocal()

    try:

        product = (
            db.query(Product)
            .filter(
                Product.id == product_id
            )
            .first()
        )

        if product is None:

            raise HTTPException(
                status_code=404,
                detail="Product not found."
            )

        product_name = (
            updated_product.product_name or ""
        ).strip()

        category = (
            updated_product.category or ""
        ).strip()

        if not product_name:

            raise HTTPException(
                status_code=400,
                detail="Product name is required."
            )

        if not category:

            raise HTTPException(
                status_code=400,
                detail="Category is required."
            )

        duplicate = (
            db.query(Product)
            .filter(
                Product.product_name.ilike(
                    product_name
                ),
                Product.id != product_id
            )
            .first()
        )

        if duplicate:

            raise HTTPException(
                status_code=409,
                detail=(
                    "Another product with this "
                    "name already exists."
                )
            )

        product.product_name = product_name

        product.category = category

        product.price = updated_product.price

        product.stock = updated_product.stock

        db.commit()

        db.refresh(product)

        return {
            "message": "Product Updated Successfully",
            "product": {
                "id": product.id,
                "product_name": product.product_name,
                "category": product.category,
                "price": product.price,
                "stock": product.stock
            }
        }

    except HTTPException:

        db.rollback()

        raise

    except Exception as e:

        db.rollback()

        raise HTTPException(
            status_code=500,
            detail=f"Unable to update product: {str(e)}"
        )

    finally:

        db.close()


# ============================================================
# DELETE PRODUCT
# ============================================================

@router.delete("/{product_id}")
def delete_product(product_id: int):

    db = SessionLocal()

    try:

        product = (
            db.query(Product)
            .filter(
                Product.id == product_id
            )
            .first()
        )

        if product is None:

            raise HTTPException(
                status_code=404,
                detail="Product not found."
            )

        db.delete(product)

        db.commit()

        return {
            "message": "Product Deleted Successfully"
        }

    except HTTPException:

        db.rollback()

        raise

    except Exception as e:

        db.rollback()

        raise HTTPException(
            status_code=500,
            detail=f"Unable to delete product: {str(e)}"
        )

    finally:

        db.close()

