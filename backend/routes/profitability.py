from fastapi import APIRouter, HTTPException
from database.session import SessionLocal
from models.product_model import Product

import csv
from pathlib import Path


router = APIRouter(
    prefix="/profitability",
    tags=["Profitability Analytics"]
)


# ============================================================
# DATASET LOCATION
# ============================================================
#
# profitability.py is assumed to be inside:
#
# backend/routers/profitability.py
#
# CSV is assumed to be inside:
#
# backend/pricepilot_updated_dataset.csv
#
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent

DATASET_FILE = BASE_DIR /  "datasets" / "pricepilot_updated_dataset.csv"


# ============================================================
# SAFE NUMBER FUNCTIONS
# ============================================================

def safe_float(value, default=0.0):

    try:

        if value is None:
            return default

        value = str(value).strip()

        if value == "":
            return default

        return float(value)

    except (ValueError, TypeError):

        return default


def safe_int(value, default=0):

    try:

        if value is None:
            return default

        value = str(value).strip()

        if value == "":
            return default

        return int(float(value))

    except (ValueError, TypeError):

        return default


# ============================================================
# LOAD DATASET
# ============================================================

def load_dataset():

    if not DATASET_FILE.exists():

        raise HTTPException(
            status_code=500,
            detail=(
                f"The file '{DATASET_FILE.name}' could not be loaded. "
                f"Make sure it exists here: {DATASET_FILE}"
            )
        )

    try:

        with open(
            DATASET_FILE,
            "r",
            encoding="utf-8-sig",
            newline=""
        ) as file:

            reader = csv.DictReader(file)

            if not reader.fieldnames:

                raise HTTPException(
                    status_code=400,
                    detail="The profitability CSV has no columns."
                )

            required_columns = {
                "product_name",
                "category",
                "price",
                "stock",
                "units_sold",
                "competitor_price",
                "discount"
            }

            missing_columns = (
                required_columns -
                set(reader.fieldnames)
            )

            if missing_columns:

                raise HTTPException(
                    status_code=400,
                    detail=(
                        "Profitability CSV is missing columns: "
                        + ", ".join(
                            sorted(missing_columns)
                        )
                    )
                )

            rows = list(reader)

            return rows

    except HTTPException:

        raise

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=(
                "Unable to read profitability dataset: "
                f"{str(e)}"
            )
        )


# ============================================================
# PROFITABILITY ANALYTICS
# ============================================================

@router.get("/{product_name}")
def get_profitability(product_name: str):

    db = SessionLocal()

    try:

        # ====================================================
        # FIND PRODUCT IN DATABASE
        # ====================================================

        product = (
            db.query(Product)
            .filter(
                Product.product_name.ilike(
                    product_name
                )
            )
            .first()
        )

        if product is None:

            raise HTTPException(
                status_code=404,
                detail="Product not found."
            )

        # ====================================================
        # PRODUCT INFORMATION
        # ====================================================

        current_price = safe_float(
            product.price
        )

        stock = safe_int(
            product.stock
        )

        cost_price = safe_float(
            product.cost_price
        )

        # ====================================================
        # LOAD CSV
        # ====================================================

        rows = load_dataset()

        # ====================================================
        # FIND PRODUCT RECORDS
        # ====================================================

        selected_name = (
            product.product_name
            .strip()
            .lower()
        )

        product_rows = []

        for row in rows:

            csv_product_name = (
                str(
                    row.get(
                        "product_name",
                        ""
                    )
                )
                .strip()
                .lower()
            )

            if csv_product_name == selected_name:

                product_rows.append(row)

        # ====================================================
        # NO SALES RECORDS
        # ====================================================

        if not product_rows:

            raise HTTPException(
                status_code=404,
                detail=(
                    f"No sales records found for "
                    f"{product.product_name} in "
                    f"{DATASET_FILE.name}."
                )
            )

        # ====================================================
        # SALES CALCULATIONS
        # ====================================================

        historical_units = 0

        historical_revenue = 0.0

        discounted_revenue = 0.0

        latest_units_sold = 0

        latest_discount = 0.0

        dataset_competitor_price = None

        # ====================================================
        # PROCESS EACH CSV RECORD
        # ====================================================

        for row in product_rows:

            units = safe_int(
                row.get("units_sold")
            )

            row_price = safe_float(
                row.get(
                    "price"
                ),
                current_price
            )

            discount = safe_float(
                row.get("discount")
            )

            row_competitor = safe_float(
                row.get(
                    "competitor_price"
                )
            )

            # -----------------------------------------------
            # TOTAL UNITS
            # -----------------------------------------------

            historical_units += units

            # -----------------------------------------------
            # HISTORICAL REVENUE
            # -----------------------------------------------

            row_revenue = (
                row_price *
                units
            )

            historical_revenue += (
                row_revenue
            )

            # -----------------------------------------------
            # DISCOUNTED REVENUE
            # -----------------------------------------------

            discount_amount = (
                row_revenue *
                discount /
                100
            )

            row_discounted_revenue = (
                row_revenue -
                discount_amount
            )

            discounted_revenue += (
                row_discounted_revenue
            )

            # -----------------------------------------------
            # LATEST RECORD
            # -----------------------------------------------

            latest_units_sold = units

            latest_discount = discount

            # -----------------------------------------------
            # COMPETITOR PRICE
            # -----------------------------------------------

            if row_competitor > 0:

                dataset_competitor_price = (
                    row_competitor
                )

        # ====================================================
        # COMPETITOR PRICE
        # ====================================================

        if (
            product.competitor_price is not None
            and safe_float(
                product.competitor_price
            ) > 0
        ):

            competitor_price = safe_float(
                product.competitor_price
            )

        elif dataset_competitor_price is not None:

            competitor_price = (
                dataset_competitor_price
            )

        else:

            competitor_price = None

        # ====================================================
        # UNITS SOLD
        # ====================================================

        units_sold = historical_units

        # ====================================================
        # GROSS REVENUE
        # ====================================================

        gross_revenue = (
            current_price *
            units_sold
        )

        # ====================================================
        # HISTORICAL REVENUE
        # ====================================================

        historical_revenue = round(
            historical_revenue,
            2
        )

        # ====================================================
        # DISCOUNTED REVENUE
        # ====================================================

        discounted_revenue = round(
            discounted_revenue,
            2
        )

        # ====================================================
        # COST
        # ====================================================

        total_cost = (
            cost_price *
            units_sold
        )

        # ====================================================
        # GROSS PROFIT
        # ====================================================

        gross_profit = (
            gross_revenue -
            total_cost
        )

        # ====================================================
        # PROFIT MARGIN
        # ====================================================

        if gross_revenue > 0:

            profit_margin = (
                gross_profit /
                gross_revenue
            ) * 100

        else:

            profit_margin = 0.0

        # ====================================================
        # INVENTORY VALUE
        # ====================================================

        inventory_sales_value = (
            current_price *
            stock
        )

        # ====================================================
        # INVENTORY COST
        # ====================================================

        inventory_cost = (
            cost_price *
            stock
        )

        # ====================================================
        # INVENTORY PROFIT POTENTIAL
        # ====================================================

        inventory_profit_potential = (
            inventory_sales_value -
            inventory_cost
        )

        # ====================================================
        # TARGET PRICE
        # ====================================================

        if (
            competitor_price is not None
            and competitor_price > 0
        ):

            target_price = (
                current_price +
                competitor_price
            ) / 2

        else:

            target_price = current_price

        # ====================================================
        # PRICING POSITION
        # ====================================================

        if (
            competitor_price is None
            or competitor_price <= 0
        ):

            price_difference = None

            price_difference_percentage = None

            pricing_position = (
                "Competitor Data Unavailable"
            )

        else:

            price_difference = (
                competitor_price -
                current_price
            )

            price_difference_percentage = (
                abs(price_difference) /
                competitor_price
            ) * 100

            if current_price < competitor_price:

                pricing_position = (
                    "Below Competitor"
                )

            elif current_price > competitor_price:

                pricing_position = (
                    "Above Competitor"
                )

            else:

                pricing_position = (
                    "Equal to Competitor"
                )

        # ====================================================
        # PROFITABILITY STATUS
        # ====================================================

        if gross_profit > 0:

            profitability_status = (
                "Profitable"
            )

        elif gross_profit < 0:

            profitability_status = (
                "Loss"
            )

        else:

            profitability_status = (
                "Break Even"
            )

        # ====================================================
        # BUSINESS ASSESSMENT
        # ====================================================

        if gross_profit > 0:

            business_assessment = (
                f"{product.product_name} is currently "
                f"profitable based on recorded sales. "
                f"Gross profit is "
                f"₹{gross_profit:,.0f}, "
                f"with a profit margin of "
                f"{profit_margin:.2f}%."
            )

        elif gross_profit < 0:

            business_assessment = (
                f"{product.product_name} is currently "
                f"operating below cost. "
                f"The recorded sales generate a gross "
                f"loss of ₹{abs(gross_profit):,.0f}. "
                f"Pricing and product cost should be reviewed."
            )

        else:

            business_assessment = (
                f"{product.product_name} is currently "
                f"operating at break-even based on "
                f"the recorded sales and product cost."
            )

        # ====================================================
        # PRICING DESCRIPTION
        # ====================================================

        if (
            competitor_price is None
            or competitor_price <= 0
        ):

            pricing_description = (
                "Competitor pricing data is not available. "
                "Market position cannot be reliably assessed "
                "until valid competitor pricing is recorded."
            )

        elif current_price < competitor_price:

            pricing_description = (
                f"The current price of "
                f"₹{current_price:,.0f} is "
                f"{price_difference_percentage:.2f}% "
                f"below the monitored competitor price. "
                f"This provides a competitive market position."
            )

        elif current_price > competitor_price:

            pricing_description = (
                f"The current price of "
                f"₹{current_price:,.0f} is "
                f"{price_difference_percentage:.2f}% "
                f"above the monitored competitor price. "
                f"Demand and sales performance should be "
                f"reviewed to determine whether the premium "
                f"is sustainable."
            )

        else:

            pricing_description = (
                "The current price is equal to the "
                "monitored competitor price. Continue "
                "monitoring demand and market movements."
            )

        # ====================================================
        # RESPONSE
        # ====================================================

        return {

            "status": "success",

            "product": {

                "product_name":
                    product.product_name,

                "category":
                    product.category,

                "current_price":
                    round(
                        current_price,
                        2
                    ),

                "cost_price":
                    round(
                        cost_price,
                        2
                    ),

                "stock":
                    stock
            },

            "revenue": {

                "units_sold":
                    units_sold,

                "gross_revenue":
                    round(
                        gross_revenue,
                        2
                    ),

                "discounted_revenue":
                    discounted_revenue,

                "historical_units":
                    historical_units,

                "historical_revenue":
                    historical_revenue,

                "inventory_sales_value":
                    round(
                        inventory_sales_value,
                        2
                    )
            },

            "profitability": {

                "cost_per_unit":
                    round(
                        cost_price,
                        2
                    ),

                "total_cost":
                    round(
                        total_cost,
                        2
                    ),

                "gross_profit":
                    round(
                        gross_profit,
                        2
                    ),

                "profit_margin":
                    round(
                        profit_margin,
                        2
                    ),

                "inventory_cost":
                    round(
                        inventory_cost,
                        2
                    ),

                "inventory_profit_potential":
                    round(
                        inventory_profit_potential,
                        2
                    ),

                "status":
                    profitability_status
            },

            "pricing": {

                "competitor_price":
                    competitor_price,

                "target_price":
                    round(
                        target_price,
                        2
                    ),

                "price_difference":
                    price_difference,

                "price_difference_percentage":
                    (
                        round(
                            price_difference_percentage,
                            2
                        )
                        if price_difference_percentage
                        is not None
                        else None
                    ),

                "pricing_position":
                    pricing_position,

                "description":
                    pricing_description
            },

            "assessment": {

                "business_assessment":
                    business_assessment
            },

            "dataset": {

                "file":
                    DATASET_FILE.name,

                "records_found":
                    len(product_rows),

                "latest_units_sold":
                    latest_units_sold,

                "latest_discount":
                    latest_discount
            }
        }

    except HTTPException:

        raise

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=(
                "Unable to generate profitability "
                f"analysis: {str(e)}"
            )
        )

    finally:

        db.close()