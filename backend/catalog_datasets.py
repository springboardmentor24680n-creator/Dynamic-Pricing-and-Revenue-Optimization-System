import os
import pandas as pd
import numpy as np
from typing import List, Dict, Any

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CATALOG_CSV_PATH = os.path.join(ROOT_DIR, "products_catalog.csv")
TRAINING_CSV_PATH = os.path.join(ROOT_DIR, "retail_pricing_dataset.csv")

def load_products_from_csv() -> List[Dict[str, Any]]:
    """Loads all products directly from root products_catalog.csv"""
    if os.path.exists(CATALOG_CSV_PATH):
        try:
            df = pd.read_csv(CATALOG_CSV_PATH)
            # Normalize column names
            df["id"] = df["product_id"]
            records = df.to_dict(orient="records")
            for r in records:
                r["id"] = str(r.get("product_id") or r.get("id"))
                r["current_price"] = float(r.get("current_price", 0))
                r["cost_price"] = float(r.get("cost_price", 0))
                r["competitor_price"] = float(r.get("competitor_price", 0))
                r["inventory"] = int(r.get("inventory", 0))
                r["historical_sales_30d"] = int(r.get("historical_sales_30d", 0))
                r["elasticity_score"] = float(r.get("elasticity_score", 1.2))
                r["rating"] = float(r.get("rating", 4.5))
            return records
        except Exception as e:
            print(f"Error loading {CATALOG_CSV_PATH}: {e}")

    # Fallback default catalog
    return [
        {
            "id": "prod-1",
            "product_id": "prod-1",
            "name": "Wireless Noise-Canceling Headphones",
            "category": "Audio & Electronics",
            "sku": "AUD-WNC-001",
            "current_price": 199.99,
            "cost_price": 110.00,
            "competitor_price": 189.99,
            "competitor_name": "TechGiant Store",
            "inventory": 420,
            "historical_sales_30d": 1250,
            "rating": 4.7,
            "demand_trend": "Increasing",
            "elasticity_score": 1.45,
            "discount_percentage": 5,
            "seasonality_factor": "High (Holiday & Back to School)",
            "last_updated": "2026-08-18"
        }
    ]

# Export PRODUCTS_DATASET dynamically loaded from CSV
PRODUCTS_DATASET = load_products_from_csv()

def load_training_dataset_df() -> pd.DataFrame:
    """Loads historical time-series transactions dataset from retail_pricing_dataset.csv"""
    if os.path.exists(TRAINING_CSV_PATH):
        try:
            return pd.read_csv(TRAINING_CSV_PATH)
        except Exception as e:
            print(f"Error reading {TRAINING_CSV_PATH}: {e}")
            
    # If file doesn't exist, regenerate it
    from generate_and_save_dataset import generate_csv_datasets
    generate_csv_datasets()
    return pd.read_csv(TRAINING_CSV_PATH)

def get_product_training_slice(product_id: str) -> pd.DataFrame:
    """Returns the historical time-series rows for a specific product."""
    df = load_training_dataset_df()
    prod_df = df[df["product_id"] == product_id].copy()
    if prod_df.empty:
        prod_df = df[df["product_id"] == "prod-1"].copy()
    return prod_df
