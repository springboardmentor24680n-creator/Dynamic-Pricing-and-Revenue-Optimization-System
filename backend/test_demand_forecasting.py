import sys
import unittest
import uuid
from pathlib import Path

# Add backend to path
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.append(str(BASE_DIR))

from main import SessionLocal, Product, SalesRecord, get_product_forecast
from services.demand_forecast_service import DemandForecastService
from services.recommendation_service import RecommendationService

class TestDemandForecasting(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db = SessionLocal()
        cls.service = DemandForecastService()

    @classmethod
    def tearDownClass(cls):
        cls.db.close()

    def test_forecast_service_for_valid_product(self):
        """
        Verify forecast generation for a standard product with sales history.
        """
        product = self.db.query(Product).first()
        if not product:
            self.skipTest("No products found in DB for test.")

        # Seed some sales history if none exists to ensure test runs reliably
        sales_records = self.db.query(SalesRecord).filter(SalesRecord.product_name == product.name).all()
        if not sales_records:
            record = SalesRecord(
                product_name=product.name,
                units_sold=45,
                revenue=product.current_price * 45,
                price=product.current_price
            )
            self.db.add(record)
            self.db.commit()

        # Run forecast service
        forecast = self.service.get_forecast_for_product(product.id, competitor_price=product.current_price * 1.05)
        
        # Verify schema
        self.assertIn("product", forecast)
        self.assertIn("short_term", forecast)
        self.assertIn("mid_term", forecast)
        self.assertIn("long_term", forecast)
        self.assertIn("metrics", forecast)
        self.assertIn("seasonal_factor", forecast)
        self.assertIn("pricing_signal", forecast)
        self.assertIn("competitor_signal", forecast)
        self.assertIn("inventory_status", forecast)
        self.assertIn("stockout_risk", forecast)
        self.assertIn("generated_at", forecast)

        # Verify horizons
        for term in ["short_term", "mid_term", "long_term"]:
            data = forecast[term]
            self.assertIn("horizon", data)
            self.assertIn("forecast_days", data)
            self.assertIn("expected_demand", data)
            self.assertIn("average_daily_demand", data)
            self.assertIn("confidence", data)
            self.assertIn("trend", data)
            self.assertIn("model", data)
            self.assertIn("forecast", data)
            self.assertIsNotNone(data["expected_demand"])
            self.assertIsNotNone(data["confidence"])
            self.assertTrue(len(data["forecast"]) > 0)

        # Verify metrics
        self.assertIn("prophet", forecast["metrics"])
        self.assertIn("lightgbm", forecast["metrics"])

    def test_forecast_service_zero_sales(self):
        """
        Verify that a product with zero sales history returns a safe N/A / Insufficient sales history state.
        """
        # Create a mock product with no sales history
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
            forecast = self.service.get_forecast_for_product(mock_id)
            
            # Verify safe fallback values
            self.assertEqual(forecast["short_term"]["expected_demand"], None)
            self.assertEqual(forecast["short_term"]["confidence"], None)
            self.assertEqual(forecast["short_term"]["forecast"], [])
            self.assertEqual(forecast["short_term"]["trend"], "Insufficient product-level historical data")

        finally:
            self.db.delete(mock_product)
            self.db.commit()

    def test_multi_horizon_mathematically_distinct(self):
        """
        Verify that short-term, mid-term, and long-term forecasts are mathematically distinct.
        """
        product = self.db.query(Product).first()
        if not product:
            self.skipTest("No products found in DB for test.")

        forecast = self.service.get_forecast_for_product(product.id, competitor_price=product.current_price * 1.05)
        
        st_val = forecast["short_term"]["expected_demand"]
        mt_val = forecast["mid_term"]["expected_demand"]
        lt_val = forecast["long_term"]["expected_demand"]

        # Ensure they are not simple linear duration scaling
        self.assertNotEqual(st_val, mt_val / 3.0)
        self.assertNotEqual(lt_val, st_val * (365.0 / 30.0))

    def test_competitor_signal_price_impact(self):
        """
        Verify that competitor price changes dynamically adjust expected demand.
        """
        product = self.db.query(Product).first()
        if not product:
            self.skipTest("No products found in DB for test.")

        # Predict with a low competitor price (high competitor pressure -> lower demand)
        forecast_low = self.service.get_forecast_for_product(product.id, competitor_price=product.current_price * 0.70)
        # Predict with a high competitor price (low competitor pressure -> higher demand)
        forecast_high = self.service.get_forecast_for_product(product.id, competitor_price=product.current_price * 1.30)

        st_low = forecast_low["short_term"]["expected_demand"]
        st_high = forecast_high["short_term"]["expected_demand"]

        self.assertTrue(st_low < st_high)

    def test_zero_stock_product_handling(self):
        """
        Verify that a product with 0 stock triggers high stockout risk warning.
        """
        mock_id = f"test_{uuid.uuid4().hex[:8]}"
        mock_product = Product(
            id=mock_id,
            name=f"Mock Product {mock_id}",
            current_price=100.0,
            cost_price=70.0,
            stock=0
        )
        record = SalesRecord(
            product_name=mock_product.name,
            units_sold=45,
            revenue=4500.0,
            price=100.0
        )
        self.db.add(mock_product)
        self.db.add(record)
        self.db.commit()

        try:
            forecast = self.service.get_forecast_for_product(mock_id)
            self.assertEqual(forecast["stockout_risk"], True)
            self.assertEqual(forecast["inventory_status"], "Risk of Stockout")
        finally:
            self.db.delete(record)
            self.db.delete(mock_product)
            self.db.commit()

    def test_missing_market_data_handling(self):
        """
        Verify that missing competitor price details return safe explanatory text.
        """
        product = self.db.query(Product).first()
        if not product:
            self.skipTest("No products found in DB for test.")

        forecast = self.service.get_forecast_for_product(product.id, competitor_price=None)
        self.assertIn("No competitor price signal available", forecast["competitor_signal"])

    def test_recommendation_integration(self):
        """
        Verify that RecommendationService successfully integrates the forecast values.
        """
        product = self.db.query(Product).first()
        if not product:
            self.skipTest("No products found in DB for test.")

        rec_service = RecommendationService()
        
        # Verify that recommendation service now includes the demand forecasting service
        self.assertTrue(hasattr(rec_service, "demand_forecast_service"))
        self.assertIsNotNone(rec_service.demand_forecast_service)

        # Retrieve a pricing recommendation and check if expected_demand matches forecast expectations
        features = {"stockcode": product.id, "quantity": 10.0}
        res = rec_service.get_recommendation(
            product_features=features,
            current_price=product.current_price,
            current_inventory=product.stock,
            historical_sales=45.0,
            historical_revenue=product.current_price * 45,
            cost_price=product.cost_price
        )
        
        self.assertIn("pricing_analysis_report", res)
        self.assertIsNotNone(res["pricing_analysis_report"]["forecast_confidence"])

    def test_api_endpoint_function(self):
        """
        Verify the get_product_forecast function logic directly.
        """
        product = self.db.query(Product).first()
        if not product:
            self.skipTest("No products found in DB for test.")

        # Call endpoint logic directly
        data = get_product_forecast(
            product_id=product.id,
            competitor_price=product.current_price * 1.05,
            user=None  # Bypassing FastAPI dependency injection for direct python test
        )
        self.assertEqual(data["product"]["id"], product.id)
        self.assertIn("short_term", data)

if __name__ == "__main__":
    unittest.main()
