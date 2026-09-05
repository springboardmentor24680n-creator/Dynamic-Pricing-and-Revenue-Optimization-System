import sys
import math
from pathlib import Path

# Add backend to path
sys.path.append(str(Path(__file__).resolve().parent))

from main import SessionLocal, Product, SalesRecord
from services.pricing_service import PricingService
from services.forecast_service import ForecastService
from services.recommendation_service import RecommendationService

def test_product(rec_service, pricing_service, product_id, comp_price):
    db = SessionLocal()
    try:
        product = db.query(Product).filter(Product.id == product_id).first()
        if not product:
            print(f"Product {product_id} not found in database!")
            return False

        # Query historical sales records
        sales_records = db.query(SalesRecord).filter(SalesRecord.product_name == product.name).all()
        hist_sales = sum(r.units_sold for r in sales_records) if sales_records else 0.0
        hist_rev = sum(r.revenue for r in sales_records) if sales_records else 0.0

        # Get features
        features = pricing_service.get_features_for_product(product_id)
        if not features:
            features = {"stockcode": product_id, "quantity": 10.0}

        # Generate recommendation
        res = rec_service.get_recommendation(
            product_features=features,
            current_price=product.current_price,
            current_inventory=product.stock,
            historical_sales=hist_sales,
            historical_revenue=hist_rev,
            cost_price=product.cost_price,
            competitor_price=comp_price
        )

        daily_velocity = hist_sales / 30.0
        days_of_supply = res['pricing_analysis_report']['days_of_supply']

        print("=" * 70)
        print(f"TEST RESULT FOR {product.name.upper()} ({product_id}):")
        print(f"Stock                 : {product.stock} units")
        print(f"Historical Sales      : {hist_sales} units")
        print(f"Daily Velocity        : {daily_velocity:.4f} units/day")
        print(f"Days of Supply        : {days_of_supply} days")
        print(f"Recommended Price     : Rs. {res['recommended_price']:.2f}")
        
        # Verify mathematically that days_of_supply ≈ inventory / daily_sales_velocity
        if hist_sales > 0:
            expected_days = product.stock / daily_velocity
            print(f"Expected Days (formula): {expected_days:.4f}")
            # The days_of_supply returned in report is rounded to 1 decimal place.
            # We check that the difference between returned days_of_supply and expected_days is small (e.g. <= 0.15)
            assert abs(days_of_supply - expected_days) < 0.15, (
                f"Formula mismatch for {product_id}: got {days_of_supply}, expected ~{expected_days}"
            )
            print("Mathematical Verification: SUCCESS (days_of_supply ~ inventory / daily_sales_velocity)")
        else:
            assert days_of_supply == "Insufficient sales history", (
                f"Expected Insufficient sales history, got {days_of_supply}"
            )
            print("Mathematical Verification: SUCCESS (insufficient sales history state validated)")
        print("=" * 70 + "\n")
        return True

    except Exception as e:
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()

def test_zero_sales(rec_service, pricing_service):
    try:
        features = {"stockcode": "elec_nonexistent", "quantity": 10.0}
        res = rec_service.get_recommendation(
            product_features=features,
            current_price=59999.0,
            current_inventory=36.0,
            historical_sales=0.0,
            historical_revenue=0.0,
            cost_price=44999.0,
            competitor_price=47000.0
        )
        days_of_supply = res['pricing_analysis_report']['days_of_supply']
        velocity = res['pricing_analysis_report']['daily_sales_velocity']

        print("=" * 70)
        print("TEST RESULT FOR ZERO SALES PRODUCT:")
        print(f"Stock                 : 36 units")
        print(f"Historical Sales      : 0.0 units")
        print(f"Daily Velocity        : {velocity}")
        print(f"Days of Supply        : {days_of_supply}")

        assert days_of_supply == "Insufficient sales history", f"Expected 'Insufficient sales history', got {days_of_supply}"
        assert velocity == "N/A", f"Expected 'N/A', got {velocity}"
        print("Mathematical Verification: SUCCESS (zero-sales N/A state validated)")
        print("=" * 70 + "\n")
        return True
    except Exception as e:
        import traceback
        traceback.print_exc()
        return False

def run_tests():
    # Initialize services
    pricing_service = PricingService()
    forecast_service = ForecastService()
    rec_service = RecommendationService(
        pricing_service=pricing_service,
        forecast_service=forecast_service
    )

    success_laptop = test_product(rec_service, pricing_service, "elec_laptop", 47000.0)
    success_mouse = test_product(rec_service, pricing_service, "elec_mouse", 950.0)
    success_zero = test_zero_sales(rec_service, pricing_service)

    if success_laptop and success_mouse and success_zero:
        print("All recommendation tests completed successfully!")
    else:
        print("Some tests failed.")
        sys.exit(1)

if __name__ == "__main__":
    run_tests()

