from fastapi import APIRouter, UploadFile, File, HTTPException
from database.session import SessionLocal

from models.dataset_model import DatasetRecord
from models.product_model import Product

import csv
import io
from datetime import datetime


router = APIRouter(
    prefix="/dataset",
    tags=["Dataset Management"]
)


# ============================================================
# REQUIRED CSV COLUMNS
# ============================================================

REQUIRED_COLUMNS = {
    "product_name",
    "category",
    "price",
    "stock",
    "units_sold",
    "competitor_price",
    "discount",
    "target_price"
}


# ============================================================
# NUMBER HELPERS
# ============================================================

def parse_float(value, default=0):
    if value is None:
        return default

    value = str(value).strip()

    if value == "":
        return default

    try:
        return float(value)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid numeric value: {value}"
        )


def parse_int(value, default=0):
    if value is None:
        return default

    value = str(value).strip()

    if value == "":
        return default

    try:
        return int(float(value))
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid integer value: {value}"
        )


def parse_date(value):
    if not value:
        return None

    value = str(value).strip()

    if not value:
        return None

    try:
        return datetime.strptime(
            value,
            "%Y-%m-%d"
        ).date()

    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Invalid date '{value}'. "
                "Expected YYYY-MM-DD."
            )
        )


# ============================================================
# CSV VALIDATION
# ============================================================

def validate_csv(file_content: bytes):

    try:
        text = file_content.decode("utf-8")

    except UnicodeDecodeError:

        raise HTTPException(
            status_code=400,
            detail="Please upload a valid UTF-8 CSV file."
        )

    reader = csv.DictReader(
        io.StringIO(text)
    )

    if not reader.fieldnames:

        raise HTTPException(
            status_code=400,
            detail="CSV file is empty."
        )

    columns = {
        column.strip()
        for column in reader.fieldnames
        if column
    }

    missing_columns = (
        REQUIRED_COLUMNS - columns
    )

    if missing_columns:

        raise HTTPException(
            status_code=400,
            detail=(
                "Missing columns: "
                + ", ".join(
                    sorted(missing_columns)
                )
            )
        )

    rows = list(reader)

    if not rows:

        raise HTTPException(
            status_code=400,
            detail="CSV file contains no products."
        )

    return rows


# ============================================================
# SAVE DATASET
# ============================================================

def save_dataset(rows):

    db = SessionLocal()

    try:

        # ----------------------------------------------------
        # Remove previous imported dataset
        # ----------------------------------------------------

        db.query(DatasetRecord).delete()

        # ----------------------------------------------------
        # Remove existing products
        #
        # Products will be rebuilt from the uploaded dataset.
        # ----------------------------------------------------

        db.query(Product).delete()

        db.commit()

        # ----------------------------------------------------
        # Track latest product information
        # ----------------------------------------------------

        latest_products = {}

        # ----------------------------------------------------
        # Insert dataset records
        # ----------------------------------------------------

        for row in rows:

            product_name = (
                row.get("product_name") or ""
            ).strip()

            category = (
                row.get("category") or ""
            ).strip()

            if not product_name:

                raise HTTPException(
                    status_code=400,
                    detail="Product name cannot be empty."
                )

            if not category:

                raise HTTPException(
                    status_code=400,
                    detail=(
                        f"Category missing for "
                        f"{product_name}."
                    )
                )

            price = parse_float(
                row.get("price")
            )

            stock = parse_int(
                row.get("stock")
            )

            units_sold = parse_int(
                row.get("units_sold")
            )

            competitor_price = parse_float(
                row.get("competitor_price"),
                None
            )

            discount = parse_float(
                row.get("discount")
            )

            target_price = parse_float(
                row.get("target_price"),
                None
            )

            date = parse_date(
                row.get("date")
            )

            # ------------------------------------------------
            # Dataset record
            # ------------------------------------------------

            record = DatasetRecord(

                date=date,

                product_name=product_name,

                category=category,

                price=price,

                stock=stock,

                units_sold=units_sold,

                competitor_price=competitor_price,

                discount=discount,

                target_price=target_price
            )

            db.add(record)

            # ------------------------------------------------
            # Keep latest information for Product table
            # ------------------------------------------------

            latest_products[product_name] = {
                "category": category,
                "price": price,
                "stock": stock,
                "competitor_price": competitor_price
            }

        db.commit()

        # ----------------------------------------------------
        # Create Product records
        # ----------------------------------------------------

        for product_name, data in latest_products.items():

            product = Product(

                product_name=product_name,

                category=data["category"],

                price=data["price"],

                stock=data["stock"],

                competitor_price=data[
                    "competitor_price"
                ]
            )

            db.add(product)

        db.commit()

        return len(rows)

    except HTTPException:

        db.rollback()
        raise

    except Exception as e:

        db.rollback()

        raise HTTPException(
            status_code=500,
            detail=(
                "Unable to save dataset: "
                f"{str(e)}"
            )
        )

    finally:

        db.close()


# ============================================================
# UPLOAD DATASET
# ============================================================

@router.post("/upload")
async def upload_dataset(
    file: UploadFile = File(...)
):

    if not file.filename.lower().endswith(".csv"):

        raise HTTPException(
            status_code=400,
            detail="Only CSV files are allowed."
        )

    content = await file.read()

    rows = validate_csv(content)

    product_count = save_dataset(rows)

    return {

        "message":
            "Dataset uploaded and saved successfully.",

        "filename":
            file.filename,

        "records":
            product_count
    }


# ============================================================
# REPLACE DATASET
# ============================================================

@router.post("/replace")
async def replace_dataset(
    file: UploadFile = File(...)
):

    if not file.filename.lower().endswith(".csv"):

        raise HTTPException(
            status_code=400,
            detail="Only CSV files are allowed."
        )

    content = await file.read()

    rows = validate_csv(content)

    product_count = save_dataset(rows)

    return {

        "message":
            "Dataset replaced successfully.",

        "filename":
            file.filename,

        "records":
            product_count
    }