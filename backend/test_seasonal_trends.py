import sys
import unittest
from pathlib import Path

# Add backend to path
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.append(str(BASE_DIR))

from main import SessionLocal, Product, SalesRecord
from routes.seasonal_trends import get_seasonal_trends
from services.seasonal_trend_service import SeasonalTrendService
from services.recommendation_service import RecommendationService

class TestSeasonalTrends(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db = SessionLocal()
        cls.service = SeasonalTrendService()

    @classmethod
    def tearDownClass(cls):
        cls.db.close()

    def test_seasonal_indices_calculation(self):
        """
        Verify that monthly seasonal indices are correctly computed or fall back to defaults.
        """
        indices = self.service.seasonal_indices
        self.assertEqual(len(indices), 12)
        for m in range(1, 13):
            self.assertIn(m, indices)
            self.assertGreater(indices[m], 0)

    def test_valid_product_seasonal_trends(self):
        """
        Verify seasonal trend parameters returned for a standard active product.
        """
        from services.seasonal_trend_service import PRODUCT_MAPPING
        product = None
        for p in self.db.query(Product).all():
            if p.id in PRODUCT_MAPPING:
                product = p
                break
        if not product:
            product = self.db.query(Product).first()
        if not product:
            self.skipTest("No products found in database.")

        # Ensure historical sales exist for standard product
        sales = self.db.query(SalesRecord).filter(SalesRecord.product_name == product.name).first()
        if not sales:
            record = SalesRecord(
                product_name=product.name,
                units_sold=30,
                revenue=product.current_price * 30,
                price=product.current_price
            )
            self.db.add(record)
            self.db.commit()

        data = self.service.get_seasonal_trends(product.id)
        
        # Verify schema
        self.assertEqual(data["product_id"], product.id)
        self.assertEqual(data["product_name"], product.name)
        self.assertIn(data["trend"], ["Increasing", "Decreasing", "Stable", "Seasonal"])
        self.assertIn(data["seasonality"], ["Weak", "Moderate", "Strong"])
        self.assertIsNotNone(data["peak_period"])
        self.assertIsNotNone(data["low_period"])
        self.assertTrue(len(data["seasonal_breakdown"]) == 12)
        self.assertTrue(len(data["insights"]) > 0)
        self.assertTrue(len(data["recommendations"]) > 0)

    def test_zero_sales_product_handling(self):
        """
        Verify that a product with zero sales returns a clean safe fallback.
        """
        import uuid
        mock_id = f"test_{uuid.uuid4().hex[:8]}"
        mock_product = Product(
            id=mock_id,
            name=f"Mock Product {mock_id}",
            current_price=100.0,
            cost_price=70.0,
            stock=10
        )
        self.db.add(mock_product)
        self.db.commit()

        try:
            data = self.service.get_seasonal_trends(mock_id)
            self.assertEqual(data["average_demand"], None)
            self.assertEqual(data["peak_demand"], None)
            self.assertEqual(data["low_demand"], None)
            self.assertEqual(data["seasonal_breakdown"], [])
            self.assertEqual(data["seasonality"], "Insufficient product-level historical data")
        finally:
            self.db.delete(mock_product)
            self.db.commit()

    def test_invalid_product_id(self):
        """
        Verify ValueError raised for nonexistent product ID.
        """
        with self.assertRaises(ValueError):
            self.service.get_seasonal_trends("nonexistent_id_12345")

    def test_recommendation_integration(self):
        """
        Verify that RecommendationService contains the seasonal variables.
        """
        product = self.db.query(Product).first()
        if not product:
            self.skipTest("No products found in DB for test.")

        rec_service = RecommendationService()
        
        # Verify that recommendation service now includes the seasonal service
        self.assertTrue(hasattr(rec_service, "seasonal_trend_service"))
        
        features = {"stockcode": product.id, "quantity": 10.0}
        res = rec_service.get_recommendation(
            product_features=features,
            current_price=product.current_price,
            current_inventory=product.stock,
            historical_sales=30.0,
            historical_revenue=product.current_price * 30.0,
            cost_price=product.cost_price
        )
        
        self.assertIn("seasonality", res)
        self.assertIn("peak_period", res)
        self.assertIn("low_period", res)
        self.assertIn("seasonal_insights", res)

    def test_api_route_function(self):
        """
        Verify the get_seasonal_trends route function logic directly.
        """
        product = self.db.query(Product).first()
        if not product:
            self.skipTest("No products found in DB for test.")

        data = get_seasonal_trends(
            product_id=product.id,
            user=None
        )
        self.assertEqual(data["product_id"], product.id)
        self.assertIn("seasonal_breakdown", data)

    def test_product_specific_seasonal_patterns(self):
        """
        Verify that different products with distinct synthetic sales history cache records
        return their respective custom peak and low periods and seasonality strengths.
        """
        # Inject dynamic mock mappings
        from services.seasonal_trend_service import PRODUCT_MAPPING
        PRODUCT_MAPPING["mock_smartwatch"] = "MOCK_SW"
        PRODUCT_MAPPING["mock_laptop"] = "MOCK_LT"
        PRODUCT_MAPPING["mock_speaker"] = "MOCK_SP"
        PRODUCT_MAPPING["mock_keyboard"] = "MOCK_KB"

        products_to_ensure = [
            {"id": "mock_smartwatch", "name": "Mock Smartwatch", "current_price": 3499.0, "cost_price": 2299.0, "stock": 64},
            {"id": "mock_laptop", "name": "Mock Laptop", "current_price": 59999.0, "cost_price": 44999.0, "stock": 36},
            {"id": "mock_speaker", "name": "Mock Speaker", "current_price": 1499.0, "cost_price": 899.0, "stock": 92},
            {"id": "mock_keyboard", "name": "Mock Keyboard", "current_price": 2499.0, "cost_price": 1599.0, "stock": 78}
        ]
        
        db_products = []
        db_sales = []
        for p_data in products_to_ensure:
            prod = self.db.query(Product).filter(Product.id == p_data["id"]).first()
            if not prod:
                prod = Product(
                    id=p_data["id"],
                    name=p_data["name"],
                    category="Test",
                    current_price=p_data["current_price"],
                    cost_price=p_data["cost_price"],
                    stock=p_data["stock"]
                )
                self.db.add(prod)
                db_products.append(prod)
                
            sales = self.db.query(SalesRecord).filter(SalesRecord.product_name == p_data["name"]).first()
            if not sales:
                sales = SalesRecord(
                    product_name=p_data["name"],
                    units_sold=30,
                    revenue=p_data["current_price"] * 30,
                    price=p_data["current_price"]
                )
                self.db.add(sales)
                db_sales.append(sales)
        self.db.commit()

        # Inject synthetic patterns in memory cache
        self.service.product_monthly_cache["MOCK_SW"] = {
            1: 100, 2: 100, 3: 500, 4: 100, 5: 100, 6: 100,
            7: 100, 8: 10, 9: 100, 10: 100, 11: 100, 12: 100
        }
        self.service.product_monthly_cache["MOCK_LT"] = {
            1: 100, 2: 5, 3: 100, 4: 100, 5: 100, 6: 100,
            7: 100, 8: 100, 9: 100, 10: 100, 11: 800, 12: 100
        }
        self.service.product_monthly_cache["MOCK_SP"] = {
            1: 100, 2: 100, 3: 100, 4: 100, 5: 100, 6: 600,
            7: 100, 8: 100, 9: 100, 10: 100, 11: 100, 12: 12
        }
        self.service.product_monthly_cache["MOCK_KB"] = {
            1: 100, 2: 100
        }

        try:
            trends_smartwatch = self.service.get_seasonal_trends("mock_smartwatch")
            trends_laptop = self.service.get_seasonal_trends("mock_laptop")
            trends_speaker = self.service.get_seasonal_trends("mock_speaker")
            trends_keyboard = self.service.get_seasonal_trends("mock_keyboard")

            # Smartwatch verification (March peak, August low)
            self.assertEqual(trends_smartwatch["peak_period"], "March")
            self.assertEqual(trends_smartwatch["low_period"], "August")
            self.assertEqual(trends_smartwatch["seasonality"], "Strong")

            # Laptop verification (November peak, February low)
            self.assertEqual(trends_laptop["peak_period"], "November")
            self.assertEqual(trends_laptop["low_period"], "February")
            self.assertEqual(trends_laptop["seasonality"], "Strong")

            # Speaker verification (June peak, December low)
            self.assertEqual(trends_speaker["peak_period"], "June")
            self.assertEqual(trends_speaker["low_period"], "December")
            self.assertEqual(trends_speaker["seasonality"], "Strong")

            # Keyboard verification (Insufficient data because of only 2 months)
            self.assertEqual(trends_keyboard["seasonality"], "Insufficient product-level historical data")
            self.assertEqual(trends_keyboard["peak_period"], "Insufficient product-level historical data")
        finally:
            # Clean up cache
            for mock_key in ["MOCK_SW", "MOCK_LT", "MOCK_SP", "MOCK_KB"]:
                self.service.product_monthly_cache.pop(mock_key, None)
            
            # Clean up PRODUCT_MAPPING keys
            for mock_id in ["mock_smartwatch", "mock_laptop", "mock_speaker", "mock_keyboard"]:
                PRODUCT_MAPPING.pop(mock_id, None)

            # Clean up Database
            for s in db_sales:
                self.db.delete(s)
            for p in db_products:
                self.db.delete(p)
            self.db.commit()

if __name__ == "__main__":
    unittest.main()
