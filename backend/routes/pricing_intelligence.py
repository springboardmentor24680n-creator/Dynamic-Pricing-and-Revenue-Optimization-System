from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import joblib
import os
import csv


router = APIRouter(
    prefix="/pricing-intelligence",
    tags=["Pricing Intelligence"]
)


# ============================================================
# PATHS
# ============================================================

BASE_DIR = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)

PRICE_MODEL_PATH = os.path.join(
    BASE_DIR,
    "ml",
    "price_model.pkl"
)

DEMAND_MODEL_PATH = os.path.join(
    BASE_DIR,
    "ml",
    "demand_model.pkl"
)

DEMAND_HISTORY_PATH = os.path.join(
    BASE_DIR,
    "datasets",
    "demand_history.csv"
)


# ============================================================
# LOAD PRICE MODEL
# ============================================================

try:

    price_model = joblib.load(
        PRICE_MODEL_PATH
    )

except Exception as exc:

    print(
        f"Price model loading failed: {exc}"
    )

    price_model = None


# ============================================================
# LOAD DEMAND MODEL
# ============================================================

try:

    demand_model_package = joblib.load(
        DEMAND_MODEL_PATH
    )

    if isinstance(
        demand_model_package,
        dict
    ):

        demand_model = (
            demand_model_package.get("model")
        )

        demand_features = (
            demand_model_package.get(
                "features",
                []
            )
        )

        category_map = (
            demand_model_package.get(
                "category_map",
                {}
            )
        )

        model_r2 = (
            demand_model_package.get("r2")
        )

    else:

        demand_model = demand_model_package

        demand_features = []

        category_map = {}

        model_r2 = None

except Exception as exc:

    print(
        f"Demand model loading failed: {exc}"
    )

    demand_model = None
    demand_features = []
    category_map = {}
    model_r2 = None


# ============================================================
# REQUEST MODEL
# ============================================================

class PricingIntelligenceRequest(BaseModel):

    product_name: str

    category: str

    price: float

    stock: int

    units_sold: int = 0

    competitor_price: float

    discount: float

    forecast_days: int = 30


# ============================================================
# LOAD HISTORICAL SALES
# ============================================================

def get_historical_sales(
    product_name: str
):

    """
    Read demand_history.csv and calculate
    total historical units sold for the
    selected product.
    """

    if not os.path.exists(
        DEMAND_HISTORY_PATH
    ):

        print(
            "Demand history file not found:",
            DEMAND_HISTORY_PATH
        )

        return {
            "total_units_sold": 0,
            "records": 0,
            "average_daily_sales": 0
        }

    total_units_sold = 0
    records = 0

    try:

        with open(
            DEMAND_HISTORY_PATH,
            mode="r",
            encoding="utf-8-sig",
            newline=""
        ) as csv_file:

            reader = csv.DictReader(
                csv_file
            )

            for row in reader:

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

                requested_product_name = (
                    str(product_name)
                    .strip()
                    .lower()
                )

                if (
                    csv_product_name
                    != requested_product_name
                ):

                    continue

                try:

                    units_sold = float(
                        row.get(
                            "units_sold",
                            0
                        )
                        or 0
                    )

                except (
                    ValueError,
                    TypeError
                ):

                    units_sold = 0

                total_units_sold += units_sold

                records += 1

        total_units_sold = round(
            total_units_sold
        )

        if records > 0:

            average_daily_sales = round(
                total_units_sold / records,
                2
            )

        else:

            average_daily_sales = 0

        return {
            "total_units_sold":
                total_units_sold,

            "records":
                records,

            "average_daily_sales":
                average_daily_sales
        }

    except Exception as exc:

        print(
            "Historical sales loading error:",
            exc
        )

        return {
            "total_units_sold": 0,
            "records": 0,
            "average_daily_sales": 0
        }


# ============================================================
# DEMAND LEVEL
# ============================================================

def market_demand_level(
    predicted_demand,
    historical_demand,
    forecast_days
):

    historical_demand = float(
        historical_demand or 0
    )

    predicted_demand = float(
        predicted_demand or 0
    )

    if historical_demand <= 0:

        return "Insufficient Historical Data"

    historical_daily = (
        historical_demand / 30
    )

    expected_historical_period = (
        historical_daily *
        forecast_days
    )

    if expected_historical_period <= 0:

        return "Insufficient Historical Data"

    ratio = (
        predicted_demand /
        expected_historical_period
    )

    if ratio >= 1.20:

        return "High Demand"

    elif ratio <= 0.80:

        return "Low Demand"

    return "Stable Demand"


# ============================================================
# STOCK STATUS
# ============================================================

def get_stock_status(
    expected_stock,
    current_stock
):

    if expected_stock < 0:

        return "Stock Shortage"

    if (
        current_stock > 0
        and expected_stock
        <= current_stock * 0.25
    ):

        return "Low Stock"

    return "Sufficient Stock"


# ============================================================
# FORECAST TYPE
# ============================================================

def get_forecast_type(days):

    if days <= 30:

        return "Short Term"

    if days <= 180:

        return "Medium Term"

    return "Long Term"


# ============================================================
# CONFIDENCE
# ============================================================

def get_confidence():

    if model_r2 is None:

        return 80

    try:

        r2 = float(
            model_r2
        )

        return round(
            max(
                50,
                min(
                    r2 * 100,
                    95
                )
            )
        )

    except Exception:

        return 80


# ============================================================
# ENDPOINT
# ============================================================

@router.post("/")
def get_pricing_intelligence(
    request: PricingIntelligenceRequest
):

    # ========================================================
    # VALIDATION
    # ========================================================

    if price_model is None:

        raise HTTPException(
            status_code=500,
            detail=(
                "Price prediction model "
                "is not available."
            )
        )

    if demand_model is None:

        raise HTTPException(
            status_code=500,
            detail=(
                "Demand forecasting model "
                "is not available."
            )
        )

    if request.price <= 0:

        raise HTTPException(
            status_code=400,
            detail=(
                "Price must be greater than 0."
            )
        )

    if request.stock < 0:

        raise HTTPException(
            status_code=400,
            detail=(
                "Stock cannot be negative."
            )
        )

    if request.competitor_price <= 0:

        raise HTTPException(
            status_code=400,
            detail=(
                "Competitor price must be "
                "greater than 0."
            )
        )

    if (
        request.discount < 0
        or request.discount > 100
    ):

        raise HTTPException(
            status_code=400,
            detail=(
                "Discount must be between "
                "0 and 100."
            )
        )

    allowed_days = [
        7,
        14,
        30,
        90,
        180,
        365
    ]

    if (
        request.forecast_days
        not in allowed_days
    ):

        raise HTTPException(
            status_code=400,
            detail=(
                "Forecast days must be "
                "7, 14, 30, 90, 180, or 365."
            )
        )

    # ========================================================
    # 1. GET REAL HISTORICAL SALES
    # ========================================================

    historical_data = get_historical_sales(
        request.product_name
    )

    historical_sales = (
        historical_data[
            "total_units_sold"
        ]
    )

    historical_records = (
        historical_data[
            "records"
        ]
    )

    historical_average_daily = (
        historical_data[
            "average_daily_sales"
        ]
    )

    # ========================================================
    # 2. PRICE PREDICTION
    # ========================================================

    try:

        price_prediction = (
            price_model.predict(
                [[
                    request.price,
                    request.stock,
                    historical_sales,
                    request.competitor_price,
                    request.discount
                ]]
            )
        )

        recommended_price = round(
            float(
                price_prediction[0]
            ),
            2
        )

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=(
                "Price model prediction failed: "
                f"{str(exc)}"
            )
        )

    recommended_price = max(
        recommended_price,
        0.01
    )

    price_difference = round(
        recommended_price -
        request.price,
        2
    )

    price_change_percentage = round(
        (
            price_difference /
            request.price
        ) * 100,
        2
    )

    if price_difference > 0:

        recommendation = (
            "Increase Price"
        )

        business_impact = (
            "Increase Revenue"
        )

    elif price_difference < 0:

        recommendation = (
            "Decrease Price"
        )

        business_impact = (
            "Increase Sales Volume"
        )

    else:

        recommendation = (
            "Maintain Price"
        )

        business_impact = (
            "Stable Pricing"
        )

    # ========================================================
    # 3. COMPETITOR ANALYSIS
    # ========================================================

    competitor_difference = round(
        request.price -
        request.competitor_price,
        2
    )

    competitor_difference_percentage = round(
        (
            competitor_difference /
            request.competitor_price
        ) * 100,
        2
    )

    if (
        request.price >
        request.competitor_price
    ):

        competitor_status = (
            "Your Price is Higher"
        )

        price_position = (
            "Above Competitor Price"
        )

        market_recommendation = (
            "Your price is above the "
            "competitor price. Review "
            "pricing competitiveness."
        )

    elif (
        request.price <
        request.competitor_price
    ):

        competitor_status = (
            "Your Price is Lower"
        )

        price_position = (
            "Below Competitor Price"
        )

        market_recommendation = (
            "Your price is below the "
            "competitor price. The lower "
            "price may support sales volume."
        )

    else:

        competitor_status = (
            "Your Price is Equal"
        )

        price_position = (
            "Same As Competitor Price"
        )

        market_recommendation = (
            "Your price is aligned "
            "with the competitor."
        )

    # ========================================================
    # 4. DEMAND MODEL INPUT
    # ========================================================

    category_value = category_map.get(
        request.category,
        0
    )

    feature_values = {

        "price":
            request.price,

        "stock":
            request.stock,

        "competitor_price":
            request.competitor_price,

        "discount":
            request.discount,

        "units_sold":
            historical_sales,

        "category":
            category_value,

        "category_value":
            category_value,

        "competitor_avg_price":
            request.competitor_price,

        "market_demand_index":
            50,

        "competitor_count":
            1,

        "market_trend":
            1,

        "month":
            1,

        "day_of_week":
            0
    }

    # ========================================================
    # BUILD DEMAND INPUT
    # ========================================================

    if demand_features:

        demand_input = []

        for feature in demand_features:

            demand_input.append(
                feature_values.get(
                    feature,
                    0
                )
            )

    else:

        demand_input = [

            request.price,

            request.stock,

            request.competitor_price,

            request.discount,

            category_value,

            request.competitor_price,

            50,

            1,

            1,

            1,

            0
        ]

    # ========================================================
    # 5. DEMAND MODEL PREDICTION
    # ========================================================

    try:

        demand_prediction = (
            demand_model.predict(
                [demand_input]
            )
        )

        base_daily_demand = float(
            demand_prediction[0]
        )

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=(
                "Demand model prediction "
                f"failed: {str(exc)}"
            )
        )

    base_daily_demand = max(
        base_daily_demand,
        0.1
    )

    # ========================================================
    # 6. FORECAST DEMAND
    # ========================================================

    predicted_demand = round(
        base_daily_demand *
        request.forecast_days
    )

    predicted_demand = max(
        predicted_demand,
        1
    )

    # ========================================================
    # 7. HISTORICAL DEMAND
    # ========================================================

    historical_daily_demand = (
        historical_average_daily
    )

    demand_trend = market_demand_level(
        predicted_demand,
        historical_sales,
        request.forecast_days
    )

    # ========================================================
    # 8. INVENTORY
    # ========================================================

    expected_stock = (
        request.stock -
        predicted_demand
    )

    demand_status = get_stock_status(
        expected_stock,
        request.stock
    )

    # ========================================================
    # 9. FORECAST TYPE
    # ========================================================

    forecast_type = get_forecast_type(
        request.forecast_days
    )

    # ========================================================
    # 10. SEASONAL ANALYSIS
    # ========================================================

    if historical_sales <= 0:

        seasonal_pattern = (
            "Insufficient Historical Data"
        )

        seasonal_impact = "Unknown"

    elif predicted_demand > (
        historical_sales *
        (
            request.forecast_days /
            30
        ) *
        1.20
    ):

        seasonal_pattern = (
            "Increasing Seasonal Demand"
        )

        seasonal_impact = "High"

    elif predicted_demand < (
        historical_sales *
        (
            request.forecast_days /
            30
        ) *
        0.80
    ):

        seasonal_pattern = (
            "Decreasing Seasonal Demand"
        )

        seasonal_impact = "Low"

    else:

        seasonal_pattern = (
            "Stable Seasonal Demand"
        )

        seasonal_impact = "Medium"

    # ========================================================
    # 11. CONFIDENCE
    # ========================================================

    confidence = get_confidence()

    # ========================================================
    # 12. RECOMMENDED ACTION
    # ========================================================

    if expected_stock < 0:

        recommended_action = (
            "Increase inventory because "
            "predicted demand is higher than "
            "available stock. Use the AI "
            "pricing forecast while maintaining "
            "sufficient inventory."
        )

    elif recommendation == "Increase Price":

        recommended_action = (
            "Consider increasing price toward "
            "the AI-recommended price while "
            "monitoring competitor pricing "
            "and demand."
        )

    elif recommendation == "Decrease Price":

        recommended_action = (
            "Consider reducing price toward "
            "the AI-recommended price to "
            "improve competitiveness and "
            "sales volume."
        )

    else:

        recommended_action = (
            "Maintain the current price and "
            "monitor demand, inventory and "
            "competitor pricing."
        )

    # ========================================================
    # 13. FINAL RESPONSE
    # ========================================================

    return {

        "status":
            "success",

        "product": {

            "product_name":
                request.product_name,

            "category":
                request.category
        },

        "forecast": {

            "forecast_days":
                request.forecast_days,

            "forecast_type":
                forecast_type,

            "historical_sales":
                historical_sales,

            "historical_records":
                historical_records,

            "historical_daily_demand":
                historical_daily_demand,

            "predicted_daily_demand":
                round(
                    base_daily_demand,
                    2
                ),

            "predicted_demand":
                predicted_demand,

            "confidence":
                confidence
        },

        "price_intelligence": {

            "current_price":
                request.price,

            "recommended_price":
                recommended_price,

            "price_difference":
                price_difference,

            "price_change_percentage":
                price_change_percentage,

            "recommendation":
                recommendation,

            "business_impact":
                business_impact
        },

        "competitor_analysis": {

            "competitor_price":
                request.competitor_price,

            "price_difference":
                competitor_difference,

            "price_difference_percentage":
                competitor_difference_percentage,

            "status":
                competitor_status,

            "price_position":
                price_position,

            "recommendation":
                market_recommendation
        },

        "demand_forecast": {

            "forecast_days":
                request.forecast_days,

            "forecast_type":
                forecast_type,

            "historical_sales":
                historical_sales,

            "historical_records":
                historical_records,

            "historical_daily_demand":
                historical_daily_demand,

            "predicted_daily_demand":
                round(
                    base_daily_demand,
                    2
                ),

            "predicted_demand":
                predicted_demand,

            "current_stock":
                request.stock,

            "expected_stock":
                expected_stock,

            "demand_trend":
                demand_trend,

            "demand_status":
                demand_status,

            "confidence":
                confidence
        },

        "seasonal_analysis": {

            "seasonal_pattern":
                seasonal_pattern,

            "demand_level":
                demand_trend,

            "seasonal_impact":
                seasonal_impact,

            "confidence":
                confidence
        },

        "recommended_action":
            recommended_action
    }