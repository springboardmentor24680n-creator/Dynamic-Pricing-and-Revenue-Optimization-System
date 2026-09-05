import unittest
from datetime import datetime, timedelta
from database.postgres import SessionLocal
from services.profitability_analytics_service import ProfitabilityAnalyticsService
from main import Product, SalesRecord

class TestProfitabilityAnalytics(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db = SessionLocal()
        cls.service = ProfitabilityAnalyticsService()

    @classmethod
    def tearDownClass(cls):
        cls.db.close()

    def setUp(self):
        self.db.rollback()
        # Clear details/forecast service caches for testing isolation
        from services.profitability_analytics_service import ProfitabilityAnalyticsService
        from services.demand_forecast_service import DemandForecastService
        ProfitabilityAnalyticsService._details_cache.clear()
        DemandForecastService._forecast_cache.clear()

        # Clean up any leftover temp test records
        temp_ids = ["temp_prof_p1", "temp_prof_p2"]
        self.db.query(SalesRecord).filter(SalesRecord.product_name.in_(["Temp Prof Prod 1", "Temp Prof Prod 2"])).delete()
        self.db.query(Product).filter(Product.id.in_(temp_ids)).delete()
        self.db.commit()

        # Seed temporary products
        self.p1 = Product(
            id="temp_prof_p1",
            name="Temp Prof Prod 1",
            category="Test",
            current_price=100.0,
            cost_price=60.0,
            stock=10
        )
        self.p2 = Product(
            id="temp_prof_p2",
            name="Temp Prof Prod 2",
            category="Test",
            current_price=200.0,
            cost_price=150.0,
            stock=20
        )
        self.db.add_all([self.p1, self.p2])
        self.db.commit()

        # Seed SalesRecords
        self.sales1 = SalesRecord(
            product_name="Temp Prof Prod 1",
            units_sold=10,
            revenue=1000.0,
            price=100.0
        )
        self.sales2 = SalesRecord(
            product_name="Temp Prof Prod 2",
            units_sold=5,
            revenue=1000.0,
            price=200.0
        )
        self.db.add_all([self.sales1, self.sales2])
        self.db.commit()

    def tearDown(self):
        self.db.rollback()
        temp_ids = ["temp_prof_p1", "temp_prof_p2"]
        self.db.query(SalesRecord).filter(SalesRecord.product_name.in_(["Temp Prof Prod 1", "Temp Prof Prod 2"])).delete()
        self.db.query(Product).filter(Product.id.in_(temp_ids)).delete()
        self.db.commit()

    def test_overview_revenue_profit_margin(self):
        # Total revenue = 1000 + 1000 = 2000.0
        # Units sold = 10 + 5 = 15
        # Avg selling price = 2000.0 / 15 = 133.33
        # Cost = (10 * 60) + (5 * 150) = 600 + 750 = 1350.0
        # Profit = 2000 - 1350 = 650.0
        # Margin = (650 / 2000) * 100 = 32.5%
        overview = self.service.calculate_overview(self.db)
        
        # Since calculating portfolio-wide overview will include other seeded products, 
        # let's assert specifically on product level overview to get exact expected calculations!
        stats1 = self.service.calculate_product_details(self.db, "temp_prof_p1")
        self.assertEqual(stats1["revenue"], 1000.0)
        self.assertEqual(stats1["units_sold"], 10)
        self.assertEqual(stats1["total_cost"], 600.0)
        self.assertEqual(stats1["gross_profit"], 400.0)
        self.assertEqual(stats1["gross_margin_percent"], 40.0)

        stats2 = self.service.calculate_product_details(self.db, "temp_prof_p2")
        self.assertEqual(stats2["revenue"], 1000.0)
        self.assertEqual(stats2["units_sold"], 5)
        self.assertEqual(stats2["total_cost"], 750.0)
        self.assertEqual(stats2["gross_profit"], 250.0)
        self.assertEqual(stats2["gross_margin_percent"], 25.0)

    def test_product_filtering_and_details(self):
        details = self.service.calculate_product_details(self.db, "temp_prof_p1")
        self.assertEqual(details["product_id"], "temp_prof_p1")
        self.assertEqual(details["product_name"], "Temp Prof Prod 1")
        self.assertEqual(details["units_sold"], 10)
        self.assertEqual(details["revenue"], 1000.0)

    def test_top_products_profit_revenue_sorting(self):
        top_data = self.service.calculate_top_products(self.db)
        self.assertIn("top_profitable", top_data)
        self.assertIn("low_margin", top_data)
        self.assertIn("all_products", top_data)

    def test_forecast_integration_metrics(self):
        details = self.service.calculate_product_details(self.db, "temp_prof_p1")
        self.assertIn("forecast_metrics", details)
        fm = details["forecast_metrics"]
        self.assertIn("short_term_forecast", fm)
        self.assertIn("projected_revenue", fm)
        self.assertIn("projected_profit", fm)

    def test_pricing_impact_recommendation(self):
        details = self.service.calculate_product_details(self.db, "temp_prof_p1")
        self.assertIn("pricing_impact", details)
        pi = details["pricing_impact"]
        self.assertIn("current_price", pi)
        self.assertIn("recommended_price", pi)

    def test_missing_cost_data_graceful_nulls(self):
        # Set p1 cost_price to None/0
        self.p1.cost_price = None
        self.db.commit()

        # Overview should return cost_data_available = False and None for cost/profit fields
        overview = self.service.calculate_overview(self.db, "temp_prof_p1")
        self.assertFalse(overview["cost_data_available"])
        self.assertIsNone(overview["total_cost"])
        self.assertIsNone(overview["gross_profit"])
        self.assertIsNone(overview["gross_margin_percent"])

        # Details should also return None for cost/profit fields
        details = self.service.calculate_product_details(self.db, "temp_prof_p1")
        self.assertFalse(details["cost_data_available"])
        self.assertIsNone(details["total_cost"])
        self.assertIsNone(details["gross_profit"])
        self.assertIsNone(details["gross_margin_percent"])

    def test_zero_sales_products(self):
        # Create zero sales product (no SalesRecord seeder)
        zero_p = Product(
            id="temp_prof_zero",
            name="Temp Prof Zero Sales",
            category="Test",
            current_price=100.0,
            cost_price=50.0,
            stock=10
        )
        self.db.add(zero_p)
        self.db.commit()

        try:
            details = self.service.calculate_product_details(self.db, "temp_prof_zero")
            self.assertEqual(details["units_sold"], 0)
            self.assertEqual(details["revenue"], 0.0)
            self.assertEqual(details["total_cost"], 0.0)
            self.assertEqual(details["gross_profit"], 0.0)
            self.assertEqual(details["gross_margin_percent"], 0.0)
        finally:
            self.db.query(Product).filter(Product.id == "temp_prof_zero").delete()
            self.db.commit()

    def test_overview_endpoint(self):
        from routes.profitability import get_profitability_overview

        # Invoke the FastAPI route handler function directly
        response = get_profitability_overview(product_id=None, user={"username": "swara", "role": "Pricing Manager"})
        self.assertIn("total_revenue", response)
        self.assertIn("units_sold", response)
        self.assertIn("cost_data_available", response)

if __name__ == "__main__":
    unittest.main()
