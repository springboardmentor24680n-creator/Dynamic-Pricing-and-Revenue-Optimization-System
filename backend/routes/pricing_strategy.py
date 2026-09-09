from fastapi import APIRouter, HTTPException

from database.session import SessionLocal

from models.product_model import Product
from models.competitor_model import CompetitorPrice


router = APIRouter(
    prefix="/pricing-strategy",
    tags=["Pricing Strategy Recommendations"]
)


# ============================================================
# HELPERS
# ============================================================

def safe_float(value, default=0):

    try:

        if value is None or value == "":
            return default

        return float(value)

    except (ValueError, TypeError):

        return default


def normalize_text(value):

    if value is None:
        return ""

    return " ".join(
        str(value).strip().lower().split()
    )


# ============================================================
# GET PRODUCTS
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
# GET PRICING STRATEGY FOR PRODUCT
# ============================================================

@router.get("/{product_id}")
def get_pricing_strategy(product_id: int):

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
        # CURRENT PRODUCT INFORMATION
        # ----------------------------------------------------

        current_price = safe_float(
            product.price
        )

        stock = int(
            product.stock or 0
        )

        # ----------------------------------------------------
        # GET COMPETITOR RECORDS
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

            product_name = normalize_text(
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
                ) == product_name
            ]

        # ----------------------------------------------------
        # NO COMPETITOR DATA
        # ----------------------------------------------------

        if not records:

            return {

                "status": "success",

                "has_market_data": False,

                "product": {

                    "id": product.id,

                    "product_name":
                        product.product_name,

                    "category":
                        product.category,

                    "current_price":
                        current_price,

                    "stock":
                        stock

                },

                "strategy":
                    "Monitor Market",

                "recommended_price":
                    current_price,

                "price_change":
                    0,

                "price_change_percent":
                    0,

                "confidence":
                    "Low",

                "market_position":
                    "No Market Data",

                "recommendation": (
                    "No competitor prices are currently "
                    "available for this product. Continue "
                    "monitoring the market before making "
                    "a pricing change."
                )
            }

        # ----------------------------------------------------
        # KEEP LATEST RECORD FOR EACH COMPETITOR
        # ----------------------------------------------------

        unique_records = {}

        for record in records:

            competitor = normalize_text(
                record.competitor_name
            )

            if not competitor:
                continue

            if competitor not in unique_records:

                unique_records[
                    competitor
                ] = record

        latest_records = list(
            unique_records.values()
        )

        competitor_prices = [

            safe_float(
                record.competitor_price
            )

            for record in latest_records

            if safe_float(
                record.competitor_price
            ) > 0

        ]

        # ----------------------------------------------------
        # NO VALID PRICES
        # ----------------------------------------------------

        if not competitor_prices:

            return {

                "status": "success",

                "has_market_data": False,

                "product": {

                    "id": product.id,

                    "product_name":
                        product.product_name,

                    "category":
                        product.category,

                    "current_price":
                        current_price,

                    "stock":
                        stock

                },

                "strategy":
                    "Monitor Market",

                "recommended_price":
                    current_price,

                "price_change":
                    0,

                "price_change_percent":
                    0,

                "confidence":
                    "Low",

                "market_position":
                    "No Valid Market Data",

                "recommendation": (
                    "Competitor records exist, but valid "
                    "competitor prices are not available."
                )
            }

        # ----------------------------------------------------
        # MARKET CALCULATIONS
        # ----------------------------------------------------

        lowest_price = min(
            competitor_prices
        )

        highest_price = max(
            competitor_prices
        )

        average_price = (
            sum(competitor_prices)
            / len(competitor_prices)
        )

        difference = (
            current_price
            - average_price
        )

        if average_price > 0:

            difference_percent = (
                difference
                / average_price
            ) * 100

        else:

            difference_percent = 0

        # ----------------------------------------------------
        # DETERMINE MARKET POSITION
        # ----------------------------------------------------

        if difference_percent <= -10:

            market_position = (
                "Below Market"
            )

        elif difference_percent >= 10:

            market_position = (
                "Above Market"
            )

        else:

            market_position = (
                "Competitive"
            )

        # ----------------------------------------------------
        # STOCK ANALYSIS
        # ----------------------------------------------------

        if stock <= 5:

            stock_status = (
                "Low Stock"
            )

        elif stock >= 50:

            stock_status = (
                "High Stock"
            )

        else:

            stock_status = (
                "Normal Stock"
            )

        # ----------------------------------------------------
        # PRICING STRATEGY
        # ----------------------------------------------------

        if difference_percent <= -10:

            # Below market

            if stock >= 50:

                strategy = (
                    "Increase Price Gradually"
                )

                recommended_price = (
                    current_price * 1.05
                )

                recommendation = (
                    "Your current price is significantly "
                    "below the market average. Since stock "
                    "is high, consider a gradual price "
                    "increase to improve revenue while "
                    "remaining competitive."
                )

            else:

                strategy = (
                    "Increase Price"
                )

                recommended_price = (
                    current_price
                    + (
                        average_price
                        - current_price
                    ) * 0.50
                )

                recommendation = (
                    "Your price is below the monitored "
                    "market average. Consider increasing "
                    "the price gradually toward the market "
                    "average while monitoring demand."
                )

        elif difference_percent >= 10:

            # Above market

            if stock >= 50:

                strategy = (
                    "Reduce Price"
                )

                recommended_price = (
                    current_price
                    - (
                        current_price
                        - average_price
                    ) * 0.50
                )

                recommendation = (
                    "Your price is significantly above "
                    "the market average and inventory is "
                    "high. Consider reducing the price "
                    "to improve competitiveness and "
                    "inventory movement."
                )

            else:

                strategy = (
                    "Review Price"
                )

                recommended_price = (
                    current_price
                    - (
                        current_price
                        - average_price
                    ) * 0.25
                )

                recommendation = (
                    "Your price is above the monitored "
                    "market average. Review demand, "
                    "product differentiation and profit "
                    "margin before making a moderate "
                    "price adjustment."
                )

        else:

            # Competitive

            strategy = (
                "Maintain Price"
            )

            recommended_price = (
                current_price
            )

            recommendation = (
                "Your price is competitively positioned "
                "near the monitored market average. "
                "Maintain the current price and continue "
                "monitoring competitor movements."
            )

        # ----------------------------------------------------
        # PRICE CHANGE
        # ----------------------------------------------------

        price_change = (
            recommended_price
            - current_price
        )

        if current_price > 0:

            price_change_percent = (
                price_change
                / current_price
            ) * 100

        else:

            price_change_percent = 0

        # ----------------------------------------------------
        # CONFIDENCE LEVEL
        # ----------------------------------------------------

        competitors_count = len(
            competitor_prices
        )

        if competitors_count >= 3:

            confidence = "High"

        elif competitors_count == 2:

            confidence = "Medium"

        else:

            confidence = "Low"

        # ----------------------------------------------------
        # RESPONSE
        # ----------------------------------------------------

        return {

            "status":
                "success",

            "has_market_data":
                True,

            "product": {

                "id":
                    product.id,

                "product_name":
                    product.product_name,

                "category":
                    product.category,

                "current_price":
                    round(current_price, 2),

                "stock":
                    stock

            },

            "market_analysis": {

                "competitors_monitored":
                    competitors_count,

                "lowest_competitor":
                    round(lowest_price, 2),

                "highest_competitor":
                    round(highest_price, 2),

                "average_market_price":
                    round(average_price, 2),

                "market_position":
                    market_position,

                "price_difference":
                    round(difference, 2),

                "difference_percent":
                    round(difference_percent, 2)

            },

            "inventory_analysis": {

                "current_stock":
                    stock,

                "stock_status":
                    stock_status

            },

            "pricing_strategy": {

                "strategy":
                    strategy,

                "recommended_price":
                    round(recommended_price, 2),

                "price_change":
                    round(price_change, 2),

                "price_change_percent":
                    round(
                        price_change_percent,
                        2
                    ),

                "confidence":
                    confidence

            },

            "recommendation":
                recommendation
        }

    finally:

        db.close()


# ============================================================
# GET STRATEGIES FOR ALL PRODUCTS WITH MARKET DATA
# ============================================================

@router.get("/")
def get_all_pricing_strategies():

    db = SessionLocal()

    try:

        products = (
            db.query(Product)
            .order_by(Product.id.asc())
            .all()
        )

        strategies = []

        for product in products:

            records = (
                db.query(CompetitorPrice)
                .filter(
                    CompetitorPrice.product_id
                    == product.id
                )
                .all()
            )

            if not records:
                continue

            unique_records = {}

            for record in records:

                name = normalize_text(
                    record.competitor_name
                )

                if name:
                    unique_records[
                        name
                    ] = record

            prices = [

                safe_float(
                    record.competitor_price
                )

                for record in
                unique_records.values()

                if safe_float(
                    record.competitor_price
                ) > 0

            ]

            if not prices:
                continue

            current_price = safe_float(
                product.price
            )

            average_price = (
                sum(prices)
                / len(prices)
            )

            difference_percent = (
                (
                    current_price
                    - average_price
                )
                / average_price
            ) * 100

            if difference_percent <= -10:

                strategy = (
                    "Increase Price"
                )

            elif difference_percent >= 10:

                strategy = (
                    "Reduce or Review Price"
                )

            else:

                strategy = (
                    "Maintain Price"
                )

            strategies.append({

                "product_id":
                    product.id,

                "product_name":
                    product.product_name,

                "category":
                    product.category,

                "current_price":
                    round(current_price, 2),

                "average_market_price":
                    round(average_price, 2),

                "difference_percent":
                    round(
                        difference_percent,
                        2
                    ),

                "strategy":
                    strategy

            })

        return {

            "status":
                "success",

            "total":
                len(strategies),

            "strategies":
                strategies
        }

    finally:

        db.close()