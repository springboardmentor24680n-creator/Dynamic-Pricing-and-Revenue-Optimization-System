import os
import random
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Define 10 high-value e-commerce products across multiple categories
PRODUCTS = [
    {
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
    },
    {
        "product_id": "prod-2",
        "name": "Smart Fitness Watch Ultra",
        "category": "Wearables",
        "sku": "WEAR-SFW-002",
        "current_price": 249.50,
        "cost_price": 135.00,
        "competitor_price": 259.99,
        "competitor_name": "FitLife Direct",
        "inventory": 180,
        "historical_sales_30d": 980,
        "rating": 4.6,
        "demand_trend": "Stable",
        "elasticity_score": 1.20,
        "discount_percentage": 0,
        "seasonality_factor": "Medium (New Year & Summer)",
        "last_updated": "2026-08-18"
    },
    {
        "product_id": "prod-3",
        "name": "Ergonomic Mesh Office Chair",
        "category": "Office & Furniture",
        "sku": "FURN-EMC-003",
        "current_price": 329.00,
        "cost_price": 170.00,
        "competitor_price": 349.00,
        "competitor_name": "OfficeDepot Hub",
        "inventory": 75,
        "historical_sales_30d": 410,
        "rating": 4.8,
        "demand_trend": "Increasing",
        "elasticity_score": 0.85,
        "discount_percentage": 10,
        "seasonality_factor": "Constant",
        "last_updated": "2026-08-18"
    },
    {
        "product_id": "prod-4",
        "name": "Mechanical Gaming Keyboard RGB",
        "category": "Gaming & PC",
        "sku": "GAME-MGK-004",
        "current_price": 89.99,
        "cost_price": 42.00,
        "competitor_price": 79.99,
        "competitor_name": "CyberGear World",
        "inventory": 610,
        "historical_sales_30d": 2100,
        "rating": 4.5,
        "demand_trend": "Increasing",
        "elasticity_score": 1.70,
        "discount_percentage": 15,
        "seasonality_factor": "High (Q4 Holiday)",
        "last_updated": "2026-08-18"
    },
    {
        "product_id": "prod-5",
        "name": "Ultra-Wide 4K Monitor 34-inch",
        "category": "Display & PC",
        "sku": "ELEC-UWM-005",
        "current_price": 499.99,
        "cost_price": 310.00,
        "competitor_price": 529.99,
        "competitor_name": "VisionMarket",
        "inventory": 95,
        "historical_sales_30d": 310,
        "rating": 4.9,
        "demand_trend": "Decreasing",
        "elasticity_score": 1.10,
        "discount_percentage": 0,
        "seasonality_factor": "Medium",
        "last_updated": "2026-08-18"
    },
    {
        "product_id": "prod-6",
        "name": "Portable Espresso Coffee Maker",
        "category": "Home Appliances",
        "sku": "HOME-PEC-006",
        "current_price": 74.50,
        "cost_price": 32.00,
        "competitor_price": 69.99,
        "competitor_name": "KitchenBoutique",
        "inventory": 340,
        "historical_sales_30d": 840,
        "rating": 4.4,
        "demand_trend": "Increasing",
        "elasticity_score": 1.60,
        "discount_percentage": 8,
        "seasonality_factor": "High (Mother's Day & Holidays)",
        "last_updated": "2026-08-18"
    },
    {
        "product_id": "prod-7",
        "name": "Compact Robot Vacuum & Mop",
        "category": "Home Appliances",
        "sku": "HOME-RVM-007",
        "current_price": 389.00,
        "cost_price": 220.00,
        "competitor_price": 399.00,
        "competitor_name": "CleanTech Direct",
        "inventory": 115,
        "historical_sales_30d": 520,
        "rating": 4.6,
        "demand_trend": "Increasing",
        "elasticity_score": 1.35,
        "discount_percentage": 5,
        "seasonality_factor": "High (Spring & Black Friday)",
        "last_updated": "2026-08-18"
    },
    {
        "product_id": "prod-8",
        "name": "Pro Studio Condenser Microphone",
        "category": "Audio & Electronics",
        "sku": "AUD-PCM-008",
        "current_price": 149.00,
        "cost_price": 68.00,
        "competitor_price": 159.00,
        "competitor_name": "AudioStream Pro",
        "inventory": 260,
        "historical_sales_30d": 730,
        "rating": 4.8,
        "demand_trend": "Stable",
        "elasticity_score": 1.05,
        "discount_percentage": 0,
        "seasonality_factor": "Medium",
        "last_updated": "2026-08-18"
    },
    {
        "product_id": "prod-9",
        "name": "Smart Ambient LED Desk Lamp",
        "category": "Office & Furniture",
        "sku": "FURN-SAL-009",
        "current_price": 49.99,
        "cost_price": 18.50,
        "competitor_price": 44.99,
        "competitor_name": "Lumino Living",
        "inventory": 510,
        "historical_sales_30d": 1640,
        "rating": 4.5,
        "demand_trend": "Increasing",
        "elasticity_score": 1.80,
        "discount_percentage": 10,
        "seasonality_factor": "High (Back to School & Winter)",
        "last_updated": "2026-08-18"
    },
    {
        "product_id": "prod-10",
        "name": "Dual Wireless Fast Charging Station",
        "category": "Audio & Electronics",
        "sku": "ELEC-WCS-010",
        "current_price": 39.99,
        "cost_price": 14.00,
        "competitor_price": 42.50,
        "competitor_name": "PowerHub Supply",
        "inventory": 820,
        "historical_sales_30d": 2450,
        "rating": 4.6,
        "demand_trend": "Stable",
        "elasticity_score": 1.50,
        "discount_percentage": 12,
        "seasonality_factor": "High (Holiday Stocking)",
        "last_updated": "2026-08-18"
    }
]

def generate_csv_datasets():
    # Save Products Catalog CSV to root directory
    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    catalog_path = os.path.join(root_dir, "products_catalog.csv")
    training_data_path = os.path.join(root_dir, "retail_pricing_dataset.csv")

    df_catalog = pd.DataFrame(PRODUCTS)
    df_catalog.to_csv(catalog_path, index=False)
    print(f"Saved products catalog with {len(df_catalog)} products to {catalog_path}")

    # Generate Time-Series Training Dataset across 365 days for each product
    records = []
    today = datetime.now()
    random.seed(42)
    np.random.seed(42)

    for prod in PRODUCTS:
        base_price = prod["current_price"]
        cost = prod["cost_price"]
        elasticity = prod["elasticity_score"]
        base_daily_demand = prod["historical_sales_30d"] / 30.0

        for i in range(365, 0, -1):
            dt = today - timedelta(days=i)
            date_str = dt.strftime("%Y-%m-%d")
            day_of_week = dt.weekday()
            month = dt.month
            is_weekend = 1 if day_of_week in [5, 6] else 0
            is_holiday = 1 if (month == 11 and dt.day >= 20) or (month == 12 and dt.day >= 15) or (month == 1 and dt.day <= 5) else 0

            # Realistic price fluctuation
            price_noise = random.uniform(-0.06, 0.06)
            price = round(base_price * (1.0 + price_noise), 2)
            comp_price = round(price * (1.0 + random.uniform(-0.04, 0.08)), 2)
            promo = 1 if random.random() < 0.12 else 0
            discount_pct = random.choice([0, 5, 10, 15]) if promo else 0

            seasonal_mult = 1.0 + (0.30 if is_holiday else 0.0) + (0.12 if is_weekend else 0.0)
            if month in [8, 9] and "Office" in prod["category"]:
                seasonal_mult += 0.20

            price_ratio = base_price / max(price * (1 - discount_pct / 100.0), 1.0)
            demand = int(base_daily_demand * seasonal_mult * (price_ratio ** elasticity) * random.uniform(0.88, 1.12))
            demand = max(1, demand)

            revenue = round(demand * price * (1 - discount_pct / 100.0), 2)
            profit = round(demand * (price * (1 - discount_pct / 100.0) - cost), 2)

            records.append({
                "date": date_str,
                "product_id": prod["product_id"],
                "product_name": prod["name"],
                "category": prod["category"],
                "sku": prod["sku"],
                "price": price,
                "cost_price": cost,
                "competitor_price": comp_price,
                "competitor_name": prod["competitor_name"],
                "discount_percent": discount_pct,
                "promotion_flag": promo,
                "day_of_week": day_of_week,
                "month": month,
                "is_weekend": is_weekend,
                "is_holiday": is_holiday,
                "units_sold": demand,
                "revenue": revenue,
                "profit": profit,
                "elasticity_score": elasticity
            })

    df_train = pd.DataFrame(records)
    df_train.to_csv(training_data_path, index=False)
    print(f"Saved complete dynamic pricing training dataset with {len(df_train)} rows to {training_data_path}")

if __name__ == "__main__":
    generate_csv_datasets()
