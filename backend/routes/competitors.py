from fastapi import APIRouter, HTTPException
from database.session import SessionLocal
from models.product_model import Product
from models.competitor_model import CompetitorPrice

from sqlalchemy import func
from datetime import datetime


router = APIRouter(
    prefix="/competitor",
    tags=["Competitor Analysis"]
)


# ============================================================
# HELPERS
# ============================================================

def normalize_text(value):
    if value is None:
        return ""

    return " ".join(
        str(value).strip().lower().split()
    )


def safe_float(value, default=0):
    try:
        if value is None or value == "":
            return default

        return float(value)

    except (ValueError, TypeError):
        return default


# ============================================================
# GET ALL PRODUCTS FOR COMPETITOR ANALYSIS
# ============================================================

@router.get("/products")
def get_products():

    db = SessionLocal()

    try:

        products = (
            db.query(Product)
            .order_by(Product.id.asc())
            .all()
        )

        return {
            "status": "success",
            "products": [
                {
                    "id": product.id,
                    "product_name": product.product_name,
                    "category": product.category,
                    "price": safe_float(product.price),
                    "stock": int(product.stock or 0)
                }
                for product in products
            ]
        }

    finally:

        db.close()


# ============================================================
# GET SELECTED PRODUCT
# ============================================================

@router.get("/product/{product_id}")
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
            "status": "success",
            "product": {
                "id": product.id,
                "product_name": product.product_name,
                "category": product.category,
                "price": safe_float(product.price),
                "stock": int(product.stock or 0)
            }
        }

    finally:

        db.close()


# ============================================================
# MONITOR COMPETITOR PRICE
# ============================================================

@router.post("/monitor")
def monitor_competitor_price(
    product_id: int,
    competitor_name: str,
    competitor_price: float
):

    db = SessionLocal()

    try:

        # ----------------------------------------------------
        # FIND PRODUCT BY ID
        # ----------------------------------------------------

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

        # ----------------------------------------------------
        # VALIDATE INPUT
        # ----------------------------------------------------

        competitor_name = competitor_name.strip()

        if not competitor_name:

            raise HTTPException(
                status_code=400,
                detail="Competitor name is required."
            )

        competitor_price = safe_float(
            competitor_price
        )

        if competitor_price <= 0:

            raise HTTPException(
                status_code=400,
                detail="Competitor price must be greater than zero."
            )

        # ----------------------------------------------------
        # YOUR CURRENT PRICE
        # ----------------------------------------------------

        your_price = safe_float(
            product.price
        )

        # ----------------------------------------------------
        # DIFFERENCE
        # ----------------------------------------------------

        price_difference = (
            your_price -
            competitor_price
        )

        if competitor_price > 0:

            difference_percent = (
                price_difference /
                competitor_price
            ) * 100

        else:

            difference_percent = 0

        # ----------------------------------------------------
        # COMPETITIVE STATUS
        # ----------------------------------------------------

        if price_difference < 0:

            if abs(difference_percent) <= 5:

                competitive_status = (
                    "Your Price is Competitive"
                )

            else:

                competitive_status = (
                    "Your Price is Lower"
                )

        elif price_difference > 0:

            competitive_status = (
                "Your Price is Higher"
            )

        else:

            competitive_status = (
                "Price is Equal"
            )

        # ----------------------------------------------------
        # SAVE RECORD
        # ----------------------------------------------------

        record = CompetitorPrice(

            product_id=product.id,

            product_name=product.product_name,

            category=product.category,

            your_price=your_price,

            competitor_name=competitor_name,

            competitor_price=competitor_price,

            price_difference=price_difference,

            price_difference_percent=difference_percent,

            competitive_status=competitive_status,

            monitored_at=datetime.utcnow()
        )

        db.add(record)

        db.commit()

        db.refresh(record)

        return {

            "status": "success",

            "message": (
                "Competitor price monitored successfully."
            ),

            "record": {

                "id": record.id,

                "product_id": record.product_id,

                "product_name": record.product_name,

                "category": record.category,

                "your_price": record.your_price,

                "competitor_name": record.competitor_name,

                "competitor_price": record.competitor_price,

                "price_difference": round(
                    record.price_difference,
                    2
                ),

                "price_difference_percent": round(
                    record.price_difference_percent,
                    2
                ),

                "competitive_status":
                    record.competitive_status,

                "monitored_at":
                    record.monitored_at
            }
        }

    except HTTPException:

        raise

    except Exception as e:

        db.rollback()

        raise HTTPException(
            status_code=500,
            detail=(
                "Unable to monitor competitor price: "
                f"{str(e)}"
            )
        )

    finally:

        db.close()


# ============================================================
# GET COMPETITOR RECORDS FOR SELECTED PRODUCT
# ============================================================

@router.get("/product/{product_id}/records")
def get_product_competitor_records(
    product_id: int
):

    db = SessionLocal()

    try:

        # ----------------------------------------------------
        # FIND PRODUCT BY ID
        # ----------------------------------------------------

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

        # ----------------------------------------------------
        # IMPORTANT:
        # MATCH PRODUCT ID FIRST
        # ----------------------------------------------------

        records = (
            db.query(CompetitorPrice)
            .filter(
                CompetitorPrice.product_id == product.id
            )
            .order_by(
                CompetitorPrice.monitored_at.desc()
            )
            .all()
        )

        # ----------------------------------------------------
        # FALLBACK FOR OLD RECORDS
        # ----------------------------------------------------

        if not records:

            normalized_name = normalize_text(
                product.product_name
            )

            all_records = (
                db.query(CompetitorPrice)
                .all()
            )

            records = [
                record
                for record in all_records
                if normalize_text(
                    record.product_name
                ) == normalized_name
            ]

        # ----------------------------------------------------
        # RESPONSE
        # ----------------------------------------------------

        return {

            "status": "success",

            "product": {

                "id":
                    product.id,

                "product_name":
                    product.product_name,

                "category":
                    product.category,

                "your_price":
                    safe_float(product.price),

                "stock":
                    int(product.stock or 0)
            },

            "records": [

                {

                    "id":
                        record.id,

                    "product_id":
                        record.product_id,

                    "product_name":
                        record.product_name,

                    "category":
                        record.category,

                    "your_price":
                        safe_float(
                            record.your_price
                        ),

                    "competitor_name":
                        record.competitor_name,

                    "competitor_price":
                        safe_float(
                            record.competitor_price
                        ),

                    "price_difference":
                        round(
                            safe_float(
                                record.price_difference
                            ),
                            2
                        ),

                    "difference_percent":
                        round(
                            safe_float(
                                record.price_difference_percent
                            ),
                            2
                        ),

                    "competitive_status":
                        record.competitive_status,

                    "monitored_at":
                        record.monitored_at
                }

                for record in records
            ],

            "total_records":
                len(records)
        }

    finally:

        db.close()


# ============================================================
# PRICING COMPARISON REPORT
# ============================================================

@router.get("/report/{product_id}")
def pricing_comparison_report(
    product_id: int
):

    db = SessionLocal()

    try:

        # ----------------------------------------------------
        # FIND PRODUCT
        # ----------------------------------------------------

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

        # ----------------------------------------------------
        # GET RECORDS
        # ----------------------------------------------------

        records = (
            db.query(CompetitorPrice)
            .filter(
                CompetitorPrice.product_id == product.id
            )
            .all()
        )

        # ----------------------------------------------------
        # FALLBACK FOR OLD DATA
        # ----------------------------------------------------

        if not records:

            normalized_name = normalize_text(
                product.product_name
            )

            all_records = (
                db.query(CompetitorPrice)
                .all()
            )

            records = [
                record
                for record in all_records
                if normalize_text(
                    record.product_name
                ) == normalized_name
            ]

        # ----------------------------------------------------
        # NO DATA
        # ----------------------------------------------------

        if not records:

            return {

                "status": "success",

                "has_data": False,

                "message": (
                    "No competitor data available "
                    "for this product yet."
                ),

                "product": {

                    "id":
                        product.id,

                    "product_name":
                        product.product_name,

                    "category":
                        product.category,

                    "your_price":
                        safe_float(product.price)
                },

                "competitors_monitored": 0,

                "lowest_competitor": None,

                "highest_competitor": None,

                "average_competitor": None,

                "price_difference": None,

                "difference_percent": None,

                "market_position":
                    "No Market Data",

                "competitors": []
            }

        # ----------------------------------------------------
        # COMPETITOR PRICES
        # ----------------------------------------------------

        prices = [

            safe_float(
                record.competitor_price
            )

            for record in records

            if safe_float(
                record.competitor_price
            ) > 0

        ]

        # ----------------------------------------------------
        # REMOVE DUPLICATE COMPETITOR NAMES
        # ----------------------------------------------------

        unique_records = {}

        for record in records:

            name = normalize_text(
                record.competitor_name
            )

            if not name:
                continue

            price = safe_float(
                record.competitor_price
            )

            # Keep latest record for same competitor

            unique_records[name] = record

        latest_records = list(
            unique_records.values()
        )

        unique_prices = [

            safe_float(
                record.competitor_price
            )

            for record in latest_records

            if safe_float(
                record.competitor_price
            ) > 0

        ]

        if not unique_prices:

            return {

                "status": "success",

                "has_data": False,

                "message":
                    "No valid competitor prices found.",

                "product": {

                    "id":
                        product.id,

                    "product_name":
                        product.product_name,

                    "category":
                        product.category,

                    "your_price":
                        safe_float(product.price)
                },

                "competitors_monitored": 0,

                "competitors": []
            }

        # ----------------------------------------------------
        # PRICE CALCULATIONS
        # ----------------------------------------------------

        your_price = safe_float(
            product.price
        )

        lowest_price = min(
            unique_prices
        )

        highest_price = max(
            unique_prices
        )

        average_price = (
            sum(unique_prices) /
            len(unique_prices)
        )

        price_difference = (
            your_price -
            average_price
        )

        if average_price > 0:

            difference_percent = (
                price_difference /
                average_price
            ) * 100

        else:

            difference_percent = 0

        # ----------------------------------------------------
        # MARKET POSITION
        # ----------------------------------------------------

        if difference_percent <= -10:

            market_position = "Below Market"

        elif difference_percent >= 10:

            market_position = "Above Market"

        else:

            market_position = "Competitive"

        # ----------------------------------------------------
        # COMPETITOR DETAILS
        # ----------------------------------------------------

        competitor_details = []

        for record in latest_records:

            competitor_price = safe_float(
                record.competitor_price
            )

            difference = (
                your_price -
                competitor_price
            )

            if competitor_price > 0:

                difference_pct = (
                    difference /
                    competitor_price
                ) * 100

            else:

                difference_pct = 0

            if difference < 0:

                if abs(difference_pct) <= 5:

                    status = (
                        "Your Price is Competitive"
                    )

                else:

                    status = (
                        "Your Price is Lower"
                    )

            elif difference > 0:

                status = (
                    "Your Price is Higher"
                )

            else:

                status = (
                    "Price is Equal"
                )

            competitor_details.append({

                "competitor":
                    record.competitor_name,

                "competitor_price":
                    competitor_price,

                "difference":
                    round(
                        difference,
                        2
                    ),

                "difference_percent":
                    round(
                        difference_pct,
                        2
                    ),

                "status":
                    status
            })

        # ----------------------------------------------------
        # STRATEGIC RECOMMENDATION
        # ----------------------------------------------------

        if market_position == "Below Market":

            recommendation = (
                "Your price is below the monitored "
                "market average. Review demand, "
                "inventory and profit margin before "
                "considering a price increase."
            )

        elif market_position == "Above Market":

            recommendation = (
                "Your price is above the monitored "
                "market average. Review demand and "
                "competitor positioning to determine "
                "whether the premium is sustainable."
            )

        else:

            recommendation = (
                "Your price is competitively positioned "
                "near the monitored market average. "
                "Continue monitoring competitor movements."
            )

        # ----------------------------------------------------
        # RESPONSE
        # ----------------------------------------------------

        return {

            "status":
                "success",

            "has_data":
                True,

            "product": {

                "id":
                    product.id,

                "product_name":
                    product.product_name,

                "category":
                    product.category,

                "your_price":
                    your_price
            },

            "competitors_monitored":
                len(unique_records),

            "lowest_competitor":
                round(
                    lowest_price,
                    2
                ),

            "highest_competitor":
                round(
                    highest_price,
                    2
                ),

            "average_competitor":
                round(
                    average_price,
                    2
                ),

            "price_difference":
                round(
                    abs(price_difference),
                    2
                ),

            "difference_percent":
                round(
                    difference_percent,
                    2
                ),

            "market_position":
                market_position,

            "competitors":
                competitor_details,

            "recommendation":
                recommendation
        }

    finally:

        db.close()


# ============================================================
# ALL COMPETITOR RECORDS
# ============================================================

@router.get("/records")
def get_all_competitor_records():

    db = SessionLocal()

    try:

        records = (
            db.query(CompetitorPrice)
            .order_by(
                CompetitorPrice.monitored_at.desc()
            )
            .all()
        )

        return {

            "status":
                "success",

            "total":
                len(records),

            "records": [

                {

                    "id":
                        record.id,

                    "product_id":
                        record.product_id,

                    "product_name":
                        record.product_name,

                    "category":
                        record.category,

                    "your_price":
                        safe_float(
                            record.your_price
                        ),

                    "competitor_name":
                        record.competitor_name,

                    "competitor_price":
                        safe_float(
                            record.competitor_price
                        ),

                    "price_difference":
                        round(
                            safe_float(
                                record.price_difference
                            ),
                            2
                        ),

                    "difference_percent":
                        round(
                            safe_float(
                                record.price_difference_percent
                            ),
                            2
                        ),

                    "competitive_status":
                        record.competitive_status,

                    "monitored_at":
                        record.monitored_at
                }

                for record in records
            ]
        }

    finally:

        db.close()