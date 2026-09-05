import sys
import unittest
from pathlib import Path
from datetime import datetime, timedelta

# Add backend to path
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.append(str(BASE_DIR))

from main import SessionLocal, Product, SalesRecord, CompetitorPrice
from services.pricing_strategy_service import PricingStrategyService

# Clean up any leftover test SKUs from previous crashed runs at import time
db_cleanup = SessionLocal()
try:
    db_cleanup.query(CompetitorPrice).filter(CompetitorPrice.product_id == "test_strategy_sku").delete()
    db_cleanup.query(SalesRecord).filter(SalesRecord.product_name == "Test Strategy Product").delete()
    db_cleanup.query(Product).filter(Product.id == "test_strategy_sku").delete()
    db_cleanup.commit()
except Exception as e:
    print(f"Error during import cleanup: {e}")
finally:
    db_cleanup.close()

class TestPricingStrategy(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db = SessionLocal()
        cls.service = PricingStrategyService()

        # Create a test product
        cls.test_prod_id = "test_strategy_sku"
        cls.test_prod_name = "Test Strategy Product"
        
        # Clean up if already exists
        existing = cls.db.query(Product).filter(Product.id == cls.test_prod_id).first()
        if existing:
            cls.db.delete(existing)
            cls.db.commit()

        cls.product = Product(
            id=cls.test_prod_id,
            name=cls.test_prod_name,
            category="TestCategory",
            current_price=2000.0,
            cost_price=1200.0,
            stock=50
        )
        cls.db.add(cls.product)
        cls.db.commit()

    @classmethod
    def tearDownClass(cls):
        # Final cleanup
        cls.db.query(CompetitorPrice).filter(CompetitorPrice.product_id == cls.test_prod_id).delete()
        cls.db.query(SalesRecord).filter(SalesRecord.product_name == cls.test_prod_name).delete()
        cls.db.query(Product).filter(Product.id == cls.test_prod_id).delete()
        cls.db.commit()
        cls.db.close()

    def mock_get_forecast_for_product(self, product_id, competitor_price=None, db=None):
        original_fc = self.original_get_forecast(product_id, competitor_price, db)
        if hasattr(self, "mock_forecast_direction") and self.mock_forecast_direction:
            original_fc["short_term"]["trend"] = self.mock_forecast_direction
        return original_fc

    def setUp(self):
        # Reset product details before each test
        self.product = self.db.query(Product).filter(Product.id == self.test_prod_id).first()
        self.product.current_price = 2000.0
        self.product.cost_price = 1200.0
        self.product.stock = 50
        self.db.commit()

        # Delete any associated competitor prices and sales records
        self.db.query(CompetitorPrice).filter(CompetitorPrice.product_id == self.test_prod_id).delete()
        self.db.query(SalesRecord).filter(SalesRecord.product_name == self.test_prod_name).delete()
        self.db.commit()

        # Setup mock
        if not hasattr(self.service.demand_service, "original_get_forecast"):
            self.original_get_forecast = self.service.demand_service.get_forecast_for_product
            self.service.demand_service.original_get_forecast = self.service.demand_service.get_forecast_for_product
        else:
            self.original_get_forecast = self.service.demand_service.original_get_forecast
        
        self.service.demand_service.get_forecast_for_product = self.mock_get_forecast_for_product
        self.mock_forecast_direction = None

        # Clear forecast cache to prevent test contamination
        from services.demand_forecast_service import DemandForecastService
        DemandForecastService._forecast_cache.clear()

    def tearDown(self):
        # Restore mock
        if hasattr(self, "original_get_forecast"):
            self.service.demand_service.get_forecast_for_product = self.original_get_forecast

    def test_response_structure(self):
        """
        Verify the pricing strategy response structure contains all required keys.
        """
        # Create a basic sales record so inventory is available
        sales = SalesRecord(product_name=self.test_prod_name, units_sold=30, revenue=60000.0, price=2000.0)
        self.db.add(sales)
        self.db.commit()

        res = self.service.get_pricing_strategy(self.db, self.test_prod_id)
        
        required_keys = [
            "product_id", "product_name", "strategy", "current_price", "recommended_price",
            "price_change", "price_change_percent", "confidence", "risk_level", "market_position",
            "competitor_metrics", "demand_metrics", "inventory_metrics", "profitability_metrics",
            "expected_impact", "reasons", "recommended_action", "monitoring_priority", "review_period_days"
        ]
        for key in required_keys:
            self.assertIn(key, res)

        # Check sub-structures
        self.assertIn("lowest_competitor_price", res["competitor_metrics"])
        self.assertIn("forecast_direction", res["demand_metrics"])
        self.assertIn("days_of_supply", res["inventory_metrics"])
        self.assertIn("gross_margin_percent", res["profitability_metrics"])
        self.assertIn("expected_revenue", res["expected_impact"])

    def test_invalid_product(self):
        """
        Verify that requesting a nonexistent product ID raises ValueError.
        """
        with self.assertRaises(ValueError):
            self.service.get_pricing_strategy(self.db, "nonexistent_sku")

    def test_missing_competitor_data(self):
        """
        Verify missing competitor data is handled gracefully (available: False).
        """
        self.mock_forecast_direction = "Stable"
        res = self.service.get_pricing_strategy(self.db, self.test_prod_id)
        self.assertFalse(res["competitor_metrics"]["available"])
        self.assertNilOrNone(res["competitor_metrics"]["lowest_competitor_price"])
        self.assertIn("Competitor data is unavailable.", res["reasons"])

    def test_missing_forecast_data(self):
        """
        Verify strategy generation succeeds when sales records are missing (causes empty forecast).
        """
        # With 0 sales records, demand forecasting indicates insufficient data
        res = self.service.get_pricing_strategy(self.db, self.test_prod_id)
        self.assertFalse(res["demand_metrics"]["available"])
        self.assertIn("Demand forecast is unavailable.", res["reasons"])

    def test_hold_price_recommendation(self):
        """
        Verify HOLD PRICE is recommended when current price aligns with competitor and no pressures exist.
        """
        self.mock_forecast_direction = "Stable"
        self.product.stock = 25
        self.db.commit()
        
        # Seed sales: 30 sold -> daily velocity = 1.0 -> days of supply = 25 (healthy inventory)
        sales = SalesRecord(product_name=self.test_prod_name, units_sold=30, revenue=60000.0, price=2000.0)
        self.db.add(sales)

        # Seed competitor close to current price
        comp = CompetitorPrice(product_id=self.test_prod_id, competitor_name="Comp A", competitor_price=2010.0, availability="In Stock")
        self.db.add(comp)
        self.db.commit()

        res = self.service.get_pricing_strategy(self.db, self.test_prod_id)
        self.assertEqual(res["strategy"], "HOLD PRICE")
        self.assertEqual(res["risk_level"], "LOW")
        self.assertEqual(res["monitoring_priority"], "LOW")

    def test_increase_price_recommendation(self):
        """
        Verify INCREASE PRICE or PREMIUM PRICING is recommended when competitor prices are higher.
        """
        self.mock_forecast_direction = "Increasing"
        # Seed sales
        sales = SalesRecord(product_name=self.test_prod_name, units_sold=30, revenue=60000.0, price=2000.0)
        self.db.add(sales)

        # Competitor is much higher, allowing space for an increase
        comp = CompetitorPrice(product_id=self.test_prod_id, competitor_name="Comp A", competitor_price=2600.0, availability="In Stock")
        self.db.add(comp)
        self.db.commit()

        res = self.service.get_pricing_strategy(self.db, self.test_prod_id)
        self.assertIn(res["strategy"], ["INCREASE PRICE", "PREMIUM PRICING", "DEMAND-BASED PRICING"])

    def test_decrease_price_recommendation(self):
        """
        Verify DECREASE PRICE is triggered under competitive pricing pressures.
        """
        self.mock_forecast_direction = "Decreasing"
        # Seed sales
        sales = SalesRecord(product_name=self.test_prod_name, units_sold=30, revenue=60000.0, price=2000.0)
        self.db.add(sales)

        # Competitor is lower
        comp = CompetitorPrice(product_id=self.test_prod_id, competitor_name="Comp A", competitor_price=1600.0, availability="In Stock")
        self.db.add(comp)
        self.db.commit()

        res = self.service.get_pricing_strategy(self.db, self.test_prod_id)
        self.assertIn(res["strategy"], ["DECREASE PRICE", "AGGRESSIVE COMPETITIVE PRICING", "CLEARANCE / INVENTORY REDUCTION"])

    def test_high_competitor_pressure(self):
        """
        Verify AGGRESSIVE COMPETITIVE PRICING is triggered when competitor is cheaper but we have good margins.
        """
        self.mock_forecast_direction = "Stable"
        self.product.stock = 25
        self.db.commit()
        
        sales = SalesRecord(product_name=self.test_prod_name, units_sold=30, revenue=60000.0, price=2000.0)
        self.db.add(sales)

        # Competitor is cheaper: 1500 (our price: 2000, cost: 1200 -> margin = 40% > 15%)
        # This represents high pressure (100% of competitors are cheaper)
        comp = CompetitorPrice(product_id=self.test_prod_id, competitor_name="Comp A", competitor_price=1500.0, availability="In Stock")
        self.db.add(comp)
        self.db.commit()

        res = self.service.get_pricing_strategy(self.db, self.test_prod_id)
        self.assertEqual(res["strategy"], "AGGRESSIVE COMPETITIVE PRICING")
        self.assertEqual(res["risk_level"], "HIGH")

    def test_low_competitor_pressure(self):
        """
        Verify low competitor pressure when competitors match or are more expensive.
        """
        self.mock_forecast_direction = "Stable"
        sales = SalesRecord(product_name=self.test_prod_name, units_sold=30, revenue=60000.0, price=2000.0)
        self.db.add(sales)

        # Competitors are matching or higher
        comp1 = CompetitorPrice(product_id=self.test_prod_id, competitor_name="Comp A", competitor_price=2000.0, availability="In Stock")
        comp2 = CompetitorPrice(product_id=self.test_prod_id, competitor_name="Comp B", competitor_price=2200.0, availability="In Stock")
        self.db.add(comp1)
        self.db.add(comp2)
        self.db.commit()

        res = self.service.get_pricing_strategy(self.db, self.test_prod_id)
        self.assertNotEqual(res["strategy"], "AGGRESSIVE COMPETITIVE PRICING")
        self.assertLessEqual(res["competitor_metrics"]["competitive_pressure"], 20.0)

    def test_high_inventory(self):
        """
        Verify CLEARANCE / INVENTORY REDUCTION is recommended under excess stock and stable/weak demand.
        """
        self.mock_forecast_direction = "Stable"
        # Set stock very high
        self.product.stock = 1000
        self.db.commit()

        # Seed moderate sales -> velocity = 0.5 -> days of supply = 2000 days (>30)
        sales = SalesRecord(product_name=self.test_prod_name, units_sold=15, revenue=30000.0, price=2000.0)
        self.db.add(sales)
        self.db.commit()

        res = self.service.get_pricing_strategy(self.db, self.test_prod_id)
        self.assertEqual(res["strategy"], "CLEARANCE / INVENTORY REDUCTION")
        self.assertEqual(res["risk_level"], "LOW")

    def test_low_inventory(self):
        """
        Verify PREMIUM PRICING is recommended when stock is low (< 10 days of supply) and competitor is higher.
        """
        self.mock_forecast_direction = "Increasing"
        # Set stock extremely low
        self.product.stock = 2
        self.db.commit()

        # Seed high sales -> velocity = 3.0 -> days of supply = 0.6 days (<10)
        sales = SalesRecord(product_name=self.test_prod_name, units_sold=90, revenue=180000.0, price=2000.0)
        self.db.add(sales)

        # Competitor is higher (no downward pressure)
        comp = CompetitorPrice(product_id=self.test_prod_id, competitor_name="Comp A", competitor_price=2400.0, availability="In Stock")
        self.db.add(comp)
        self.db.commit()

        res = self.service.get_pricing_strategy(self.db, self.test_prod_id)
        self.assertEqual(res["strategy"], "PREMIUM PRICING")
        self.assertEqual(res["monitoring_priority"], "HIGH")

    def assertNilOrNone(self, value):
        self.assertTrue(value is None)

if __name__ == "__main__":
    unittest.main()
