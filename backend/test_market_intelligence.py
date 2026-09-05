import unittest
from datetime import datetime, timedelta
from database.postgres import SessionLocal
from services.market_intelligence_service import MarketIntelligenceService
from main import Product, CompetitorPrice, CompetitorPriceHistory, SalesRecord

class TestMarketIntelligence(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db = SessionLocal()
        cls.service = MarketIntelligenceService()

    @classmethod
    def tearDownClass(cls):
        cls.db.close()

    def setUp(self):
        self.db.rollback()
        # Clean up any leftover temp test records
        temp_ids = ["temp_intel_p"]
        self.db.query(CompetitorPriceHistory).filter(CompetitorPriceHistory.product_id.in_(temp_ids)).delete()
        self.db.query(CompetitorPrice).filter(CompetitorPrice.product_id.in_(temp_ids)).delete()
        self.db.query(SalesRecord).filter(SalesRecord.product_name == "Test Intel Product").delete()
        self.db.query(Product).filter(Product.id.in_(temp_ids)).delete()
        self.db.commit()

        # Seed temporary product
        self.product = Product(
            id="temp_intel_p",
            name="Test Intel Product",
            category="Test",
            current_price=100.0,
            cost_price=60.0,
            stock=20
        )
        self.db.add(self.product)
        
        # Seed 30 day sales baseline to avoid "Insufficient sales history" status in tests
        self.sales = SalesRecord(
            product_name="Test Intel Product",
            units_sold=60.0,  # 2 units per day average velocity
            revenue=6000.0
        )
        self.db.add(self.sales)
        self.db.commit()

    def tearDown(self):
        self.db.rollback()
        temp_ids = ["temp_intel_p"]
        self.db.query(CompetitorPriceHistory).filter(CompetitorPriceHistory.product_id.in_(temp_ids)).delete()
        self.db.query(CompetitorPrice).filter(CompetitorPrice.product_id.in_(temp_ids)).delete()
        self.db.query(SalesRecord).filter(SalesRecord.product_name == "Test Intel Product").delete()
        self.db.query(Product).filter(Product.id.in_(temp_ids)).delete()
        self.db.commit()

    def test_market_metrics_calculation(self):
        # Seed competitor prices: 80, 90, 110. Average: 93.33. Volatility (std dev): 15.27
        p1 = CompetitorPrice(product_id="temp_intel_p", competitor_name="Comp A", competitor_price=80.0)
        p2 = CompetitorPrice(product_id="temp_intel_p", competitor_name="Comp B", competitor_price=90.0)
        p3 = CompetitorPrice(product_id="temp_intel_p", competitor_name="Comp C", competitor_price=110.0)
        self.db.add_all([p1, p2, p3])
        self.db.commit()

        stats = self.service.calculate_product_intelligence(self.db, "temp_intel_p")
        mm = stats["market_metrics"]
        self.assertEqual(mm["competitor_count"], 3)
        self.assertAlmostEqual(mm["market_average_price"], 93.33333333333333)
        self.assertEqual(mm["market_median_price"], 90.0)
        self.assertEqual(mm["market_min_price"], 80.0)
        self.assertEqual(mm["market_max_price"], 110.0)
        self.assertAlmostEqual(mm["competitor_price_volatility"], 15.275252316519468)

    def test_competitive_pressure_and_pricing_position(self):
        # Our price = 100. Competitors: 80, 90, 120.
        # Cheaper percentage (cheaper competitor percentage) = 2/3 = 66.67%
        # Pricing position = "upper_mid" because cheaper_percentage > 50%
        p1 = CompetitorPrice(product_id="temp_intel_p", competitor_name="Comp A", competitor_price=80.0)
        p2 = CompetitorPrice(product_id="temp_intel_p", competitor_name="Comp B", competitor_price=90.0)
        p3 = CompetitorPrice(product_id="temp_intel_p", competitor_name="Comp C", competitor_price=120.0)
        self.db.add_all([p1, p2, p3])
        self.db.commit()

        stats = self.service.calculate_product_intelligence(self.db, "temp_intel_p")
        cm = stats["competitive_metrics"]
        self.assertEqual(cm["competitive_pressure_score"], 66.66666666666666)
        self.assertEqual(cm["pricing_position"], "upper_mid")
        self.assertEqual(cm["strongest_competitor_pressure"]["competitor_name"], "Comp A")
        self.assertEqual(cm["strongest_competitor_pressure"]["price_gap"], 20.0)

    def test_market_direction_increasing(self):
        # Current competitor price = 110.0
        # Competitor price history from 7 days ago = 90.0
        # Expected direction: increasing
        current = CompetitorPrice(product_id="temp_intel_p", competitor_name="Comp A", competitor_price=110.0)
        self.db.add(current)
        
        seven_days_ago = datetime.utcnow() - timedelta(days=8)
        history = CompetitorPriceHistory(
            product_id="temp_intel_p",
            competitor_name="Comp A",
            competitor_price=90.0,
            last_checked=seven_days_ago
        )
        self.db.add(history)
        self.db.commit()

        stats = self.service.calculate_product_intelligence(self.db, "temp_intel_p")
        self.assertEqual(stats["competitive_metrics"]["competitor_price_direction"], "increasing")

    def test_market_direction_decreasing(self):
        # Current competitor price = 80.0
        # History price from 7 days ago = 100.0
        # Expected direction: decreasing
        current = CompetitorPrice(product_id="temp_intel_p", competitor_name="Comp A", competitor_price=80.0)
        self.db.add(current)
        
        seven_days_ago = datetime.utcnow() - timedelta(days=8)
        history = CompetitorPriceHistory(
            product_id="temp_intel_p",
            competitor_name="Comp A",
            competitor_price=100.0,
            last_checked=seven_days_ago
        )
        self.db.add(history)
        self.db.commit()

        stats = self.service.calculate_product_intelligence(self.db, "temp_intel_p")
        self.assertEqual(stats["competitive_metrics"]["competitor_price_direction"], "decreasing")

    def test_demand_integration(self):
        stats = self.service.calculate_product_intelligence(self.db, "temp_intel_p")
        dm = stats["demand_metrics"]
        self.assertIn("short_term_forecast", dm)
        self.assertIn("mid_term_forecast", dm)
        self.assertIn("long_term_forecast", dm)
        self.assertIn(dm["demand_direction"], ["stable", "increasing", "decreasing"])

    def test_seasonal_integration(self):
        stats = self.service.calculate_product_intelligence(self.db, "temp_intel_p")
        sm = stats["seasonal_metrics"]
        self.assertIn("seasonal_strength", sm)
        self.assertIn("current_season", sm)
        self.assertIn("peak_period", sm)
        self.assertIn("low_period", sm)

    def test_inventory_risk_stockout(self):
        # Stock = 5, Daily sales rate = 2.0 (from setUp seed: 60 units/30 days).
        # Days of supply = 5 / 2.0 = 2.5 days (< 10 days) -> understock / Stockout Risk
        self.product.stock = 5
        self.db.commit()

        stats = self.service.calculate_product_intelligence(self.db, "temp_intel_p")
        im = stats["inventory_metrics"]
        self.assertEqual(im["inventory_risk"], "understock")
        self.assertTrue(im["stockout_risk"])
        self.assertEqual(stats["classification"], "Stockout Risk")

    def test_inventory_risk_overstock(self):
        # Stock = 100, Daily sales rate = 2.0.
        # Days of supply = 100 / 2 = 50 days (> 45 days) -> overstock / Overstock Risk
        self.product.stock = 500
        self.db.commit()

        stats = self.service.calculate_product_intelligence(self.db, "temp_intel_p")
        im = stats["inventory_metrics"]
        self.assertEqual(im["inventory_risk"], "overstock")
        self.assertFalse(im["stockout_risk"])
        self.assertEqual(stats["classification"], "Overstock Risk")

    def test_market_intelligence_endpoints(self):
        from routes.market_intelligence import get_portfolio_intelligence, get_product_intelligence

        # Test portfolio endpoint
        portfolio_res = get_portfolio_intelligence(user={"username": "swara", "role": "Pricing Manager"})
        self.assertIn("total_products", portfolio_res)
        self.assertIn("average_market_pressure", portfolio_res)
        self.assertIn("classification_counts", portfolio_res)

        # Test product endpoint
        product_res = get_product_intelligence(product_id="temp_intel_p", user={"username": "swara", "role": "Pricing Manager"})
        self.assertEqual(product_res["product_id"], "temp_intel_p")
        self.assertIn("market_metrics", product_res)
        self.assertIn("competitive_metrics", product_res)

if __name__ == "__main__":
    unittest.main()
