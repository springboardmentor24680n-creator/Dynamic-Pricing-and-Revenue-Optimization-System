from fastapi import APIRouter

from database.session import SessionLocal

from models.product_model import Product
from models.competitor_model import CompetitorPrice


router = APIRouter(
    prefix="/reports",
    tags=["Executive Business Intelligence Reports"]
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
# EXECUTIVE BUSINESS INTELLIGENCE REPORT
# ============================================================

@router.get("/executive")
def get_executive_report():

    db = SessionLocal()

    try:

        # ----------------------------------------------------
        # GET PRODUCTS
        # ----------------------------------------------------

        products = (
            db.query(Product)
            .order_by(Product.id.asc())
            .all()
        )

        total_products = len(products)

        total_stock = sum(
            int(product.stock or 0)
            for product in products
        )

        inventory_value = sum(
            safe_float(product.price)
            * int(product.stock or 0)
            for product in products
        )


        # ----------------------------------------------------
        # CATEGORY ANALYSIS
        # ----------------------------------------------------

        categories = {}

        for product in products:

            category = (
                product.category
                or "Uncategorized"
            )

            if category not in categories:

                categories[category] = {

                    "category": category,

                    "products": 0,

                    "total_stock": 0,

                    "inventory_value": 0
                }

            categories[category]["products"] += 1

            categories[category]["total_stock"] += (
                int(product.stock or 0)
            )

            categories[category]["inventory_value"] += (
                safe_float(product.price)
                * int(product.stock or 0)
            )


        category_summary = list(
            categories.values()
        )

        for category in category_summary:

            category["inventory_value"] = round(
                category["inventory_value"],
                2
            )


        # ----------------------------------------------------
        # COMPETITOR DATA
        # ----------------------------------------------------

        competitor_records = (
            db.query(CompetitorPrice)
            .all()
        )

        total_competitor_records = len(
            competitor_records
        )


        # ----------------------------------------------------
        # PRICING POSITION ANALYSIS
        # ----------------------------------------------------

        below_market = 0
        above_market = 0
        competitive = 0
        products_with_market_data = 0

        pricing_details = []

        for product in products:

            records = (
                db.query(CompetitorPrice)
                .filter(
                    CompetitorPrice.product_id
                    == product.id
                )
                .order_by(
                    CompetitorPrice.monitored_at.desc()
                )
                .all()
            )

            # Latest record for each competitor
            unique_records = {}

            for record in records:

                competitor = normalize_text(
                    record.competitor_name
                )

                if (
                    competitor
                    and competitor not in unique_records
                ):
                    unique_records[
                        competitor
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

            products_with_market_data += 1

            average_market_price = (
                sum(prices) / len(prices)
            )

            current_price = safe_float(
                product.price
            )

            difference_percent = (
                (
                    current_price
                    - average_market_price
                )
                / average_market_price
            ) * 100

            if difference_percent <= -10:

                market_position = "Below Market"

                below_market += 1

                strategy = "Increase Price"

            elif difference_percent >= 10:

                market_position = "Above Market"

                above_market += 1

                strategy = "Reduce or Review Price"

            else:

                market_position = "Competitive"

                competitive += 1

                strategy = "Maintain Price"


            pricing_details.append({

                "product_id": product.id,

                "product_name":
                    product.product_name,

                "category":
                    product.category,

                "current_price":
                    round(current_price, 2),

                "market_average":
                    round(
                        average_market_price,
                        2
                    ),

                "difference_percent":
                    round(
                        difference_percent,
                        2
                    ),

                "market_position":
                    market_position,

                "recommended_strategy":
                    strategy
            })


        # ----------------------------------------------------
        # LOW STOCK PRODUCTS
        # ----------------------------------------------------

        low_stock_products = [

            {

                "product_id":
                    product.id,

                "product_name":
                    product.product_name,

                "category":
                    product.category,

                "stock":
                    int(product.stock or 0),

                "price":
                    safe_float(product.price)

            }

            for product in products

            if int(product.stock or 0) <= 5

        ]


        # ----------------------------------------------------
        # HIGH INVENTORY PRODUCTS
        # ----------------------------------------------------

        high_stock_products = [

            {

                "product_id":
                    product.id,

                "product_name":
                    product.product_name,

                "category":
                    product.category,

                "stock":
                    int(product.stock or 0),

                "inventory_value":
                    round(
                        safe_float(product.price)
                        * int(product.stock or 0),
                        2
                    )

            }

            for product in products

            if int(product.stock or 0) >= 50

        ]


        # ----------------------------------------------------
        # BUSINESS INSIGHTS
        # ----------------------------------------------------

        insights = []

        if below_market > 0:

            insights.append(
                f"{below_market} product(s) are "
                "priced significantly below the "
                "market and may have opportunities "
                "for price increases."
            )

        if above_market > 0:

            insights.append(
                f"{above_market} product(s) are "
                "priced significantly above the "
                "market and should be reviewed "
                "for competitiveness."
            )

        if low_stock_products:

            insights.append(
                f"{len(low_stock_products)} product(s) "
                "have low inventory and may require "
                "restocking."
            )

        if high_stock_products:

            insights.append(
                f"{len(high_stock_products)} product(s) "
                "have high inventory and may require "
                "promotional or pricing strategies "
                "to improve inventory movement."
            )

        if competitive > 0:

            insights.append(
                f"{competitive} product(s) are "
                "competitively priced based on "
                "available market data."
            )

        if not insights:

            insights.append(
                "Additional market and inventory data "
                "is required to generate detailed "
                "business insights."
            )


        # ----------------------------------------------------
        # RESPONSE
        # ----------------------------------------------------

        return {

            "status": "success",

            "executive_summary": {

                "total_products":
                    total_products,

                "total_inventory_units":
                    total_stock,

                "total_inventory_value":
                    round(
                        inventory_value,
                        2
                    ),

                "competitor_records":
                    total_competitor_records,

                "products_with_market_data":
                    products_with_market_data
            },


            "pricing_overview": {

                "below_market":
                    below_market,

                "above_market":
                    above_market,

                "competitive":
                    competitive
            },


            "inventory_overview": {

                "low_stock_products":
                    len(low_stock_products),

                "high_stock_products":
                    len(high_stock_products)
            },


            "category_summary":
                category_summary,


            "pricing_details":
                pricing_details,


            "low_stock_products":
                low_stock_products,


            "high_stock_products":
                high_stock_products,


            "business_insights":
                insights
        }

    finally:

        db.close()