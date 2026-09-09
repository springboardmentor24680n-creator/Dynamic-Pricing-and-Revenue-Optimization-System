from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import joblib
import os
import csv
from pathlib import Path
from datetime import datetime, timedelta


router = APIRouter(
    prefix="/prediction",
    tags=["Price Prediction"]
)


# ==================================================
# MODEL
# ==================================================

BASE_DIR = Path(__file__).resolve().parent.parent

MODEL_PATH = BASE_DIR / "ml" / "price_model.pkl"

DATASET_PATH = (
    BASE_DIR
    / "datasets"
    / "products_dataset.csv"
)


if not MODEL_PATH.exists():
    raise RuntimeError(
        f"Price model not found: {MODEL_PATH}"
    )


model = joblib.load(MODEL_PATH)


# ==================================================
# REQUEST MODEL
# ==================================================

class PriceForecastRequest(BaseModel):
    product_id: int
    forecast_days: int


# ==================================================
# HELPER
# ==================================================

def number(value, default=0.0):

    try:
        return float(value)

    except (ValueError, TypeError):
        return default


def load_products():

    if not DATASET_PATH.exists():
        raise HTTPException(
            status_code=500,
            detail="products_dataset.csv not found."
        )

    rows = []

    with open(
        DATASET_PATH,
        mode="r",
        encoding="utf-8-sig",
        newline=""
    ) as file:

        reader = csv.DictReader(file)

        for row in reader:
            rows.append(row)

    return rows


# ==================================================
# EXISTING PRICE PREDICTION
# ==================================================

@router.post("/predict")
def predict_price(
    price: float,
    stock: int,
    units_sold: int,
    competitor_price: float,
    discount: float
):

    prediction = model.predict([[
        price,
        stock,
        units_sold,
        competitor_price,
        discount
    ]])

    recommended_price = round(
        float(prediction[0]),
        2
    )

    difference = round(
        recommended_price - price,
        2
    )

    if difference > 0:

        recommendation = "Increase Price"
        impact = "Increase Revenue"

    elif difference < 0:

        recommendation = "Decrease Price"
        impact = "Increase Sales Volume"

    else:

        recommendation = "Maintain Price"
        impact = "Maintain Current Pricing"

    return {

        "currentPrice": price,

        "stock": stock,

        "unitsSold": units_sold,

        "competitorPrice": competitor_price,

        "discount": discount,

        "recommendedPrice":
            recommended_price,

        "difference":
            difference,

        "recommendation":
            recommendation,

        "impact":
            impact,

        "predictionTime":
            datetime.now().strftime(
                "%d/%m/%Y, %I:%M:%S %p"
            )
    }


# ==================================================
# PRICE FORECASTING
# ==================================================

@router.post("/forecast")
def forecast_price(
    request: PriceForecastRequest
):

    # --------------------------------------------------
    # 1. VALIDATE FORECAST PERIOD
    # --------------------------------------------------

    allowed_periods = [
        7,
        14,
        30,
        90,
        180,
        365
    ]

    if request.forecast_days not in allowed_periods:

        raise HTTPException(
            status_code=400,
            detail=(
                "Forecast period must be "
                "7, 14, 30, 90, 180, or 365 days."
            )
        )

    # --------------------------------------------------
    # 2. LOAD DATASET
    # --------------------------------------------------

    rows = load_products()

    # --------------------------------------------------
    # 3. FIND PRODUCT
    # --------------------------------------------------

    product = None

    for row in rows:

        try:

            row_product_id = int(
                row.get("id", 0)
            )

        except (ValueError, TypeError):

            row_product_id = 0

        if row_product_id == request.product_id:

            product = row
            break

    # If dataset does not contain ID,
    # use product_id as 1-based row position.

    if product is None:

        index = request.product_id - 1

        if 0 <= index < len(rows):

            product = rows[index]

    if product is None:

        raise HTTPException(
            status_code=404,
            detail="Product not found."
        )

    # --------------------------------------------------
    # 4. CURRENT VALUES
    # --------------------------------------------------

    product_name = product.get(
        "product_name",
        "Unknown Product"
    )

    category = product.get(
        "category",
        "Unknown"
    )

    current_price = number(
        product.get("price")
    )

    stock = int(
        number(
            product.get("stock")
        )
    )

    units_sold = int(
        number(
            product.get("units_sold")
        )
    )

    competitor_price = number(
        product.get("competitor_price")
    )

    discount = number(
        product.get("discount")
    )

    # --------------------------------------------------
    # 5. PREDICT OPTIMAL PRICE
    # --------------------------------------------------

    prediction = model.predict([[
        current_price,
        stock,
        units_sold,
        competitor_price,
        discount
    ]])

    recommended_price = max(
        float(prediction[0]),
        0
    )

    # --------------------------------------------------
    # 6. FORECAST TYPE
    # --------------------------------------------------

    if request.forecast_days <= 30:

        forecast_type = "Short Term"

    elif request.forecast_days <= 180:

        forecast_type = "Medium Term"

    else:

        forecast_type = "Long Term"

    # --------------------------------------------------
    # 7. PRICE CHANGE
    # --------------------------------------------------

    total_change = (
        recommended_price -
        current_price
    )

    # Spread the expected change
    # across the requested period.

    daily_change = (
        total_change /
        max(request.forecast_days, 1)
    )

    # --------------------------------------------------
    # 8. GENERATE FORECAST POINTS
    # --------------------------------------------------

    forecast_points = []

    checkpoint_days = [
        1,
        7,
        14,
        30,
        60,
        90,
        180,
        365
    ]

    for day in checkpoint_days:

        if day > request.forecast_days:
            continue

        forecasted_price = (
            current_price +
            daily_change * day
        )

        forecast_points.append({

            "day": day,

            "price": round(
                forecasted_price,
                2
            )
        })

    # Always include final day.

    if (
        not forecast_points
        or forecast_points[-1]["day"]
        != request.forecast_days
    ):

        final_price = (
            current_price +
            daily_change *
            request.forecast_days
        )

        forecast_points.append({

            "day":
                request.forecast_days,

            "price":
                round(
                    final_price,
                    2
                )
        })

    # --------------------------------------------------
    # 9. PRICE TREND
    # --------------------------------------------------

    if recommended_price > current_price:

        price_trend = "Increasing"

        recommendation = "Increase Price"

        impact = "Potential Revenue Increase"

    elif recommended_price < current_price:

        price_trend = "Decreasing"

        recommendation = "Decrease Price"

        impact = "Potential Sales Volume Increase"

    else:

        price_trend = "Stable"

        recommendation = "Maintain Price"

        impact = "Maintain Current Pricing"

    # --------------------------------------------------
    # 10. COMPETITOR POSITION
    # --------------------------------------------------

    if recommended_price < competitor_price:

        price_position = (
            "Below Competitor Price"
        )

    elif recommended_price > competitor_price:

        price_position = (
            "Above Competitor Price"
        )

    else:

        price_position = (
            "Same As Competitor"
        )

    # --------------------------------------------------
    # 11. FORECAST CHANGE PERCENTAGE
    # --------------------------------------------------

    if current_price > 0:

        change_percentage = (
            total_change /
            current_price
        ) * 100

    else:

        change_percentage = 0

    # --------------------------------------------------
    # 12. CONFIDENCE
    # --------------------------------------------------

    # The existing price model does not contain
    # evaluation metrics, so this is a model
    # confidence indicator, not prediction accuracy.

    confidence = 80

    if units_sold >= 200:

        confidence = 90

    elif units_sold >= 100:

        confidence = 85

    elif units_sold >= 50:

        confidence = 80

    else:

        confidence = 75

    # --------------------------------------------------
    # 13. RECOMMENDED ACTION
    # --------------------------------------------------

    if recommended_price > current_price:

        recommended_action = (
            "Gradually increase the product price "
            "toward the model-recommended price "
            "while monitoring demand and competitor pricing."
        )

    elif recommended_price < current_price:

        recommended_action = (
            "Consider reducing the product price "
            "toward the model-recommended price "
            "to improve sales volume."
        )

    else:

        recommended_action = (
            "Maintain the current price and "
            "continue monitoring market conditions."
        )

    # --------------------------------------------------
    # 14. RETURN FORECAST
    # --------------------------------------------------

    return {

        "product_id":
            request.product_id,

        "product_name":
            product_name,

        "category":
            category,

        "forecast_days":
            request.forecast_days,

        "forecast_type":
            forecast_type,

        "current_price":
            round(
                current_price,
                2
            ),

        "predicted_price":
            round(
                recommended_price,
                2
            ),

        "price_change":
            round(
                total_change,
                2
            ),

        "price_change_percentage":
            round(
                change_percentage,
                2
            ),

        "price_trend":
            price_trend,

        "competitor_price":
            round(
                competitor_price,
                2
            ),

        "price_position":
            price_position,

        "confidence":
            confidence,

        "recommendation":
            recommendation,

        "impact":
            impact,

        "recommended_action":
            recommended_action,

        "forecast_points":
            forecast_points,

        "forecast_generated_at":
            datetime.now().strftime(
                "%d/%m/%Y, %I:%M:%S %p"
            )
    }