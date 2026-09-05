import unittest
from datetime import datetime, timedelta
from database.postgres import SessionLocal
from services.pricing_comparison_service import PricingComparisonService
from main import Product, CompetitorPrice, CompetitorPriceHistory

class TestPricingComparison(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db = SessionLocal()
        cls.service = PricingComparisonService()

    @classmethod
    def tearDownClass(cls):
        cls.db.close()

    def setUp(self):
        self.db.rollback()
        # Clean up any leftover temp test records
        temp_ids = ["temp_comp_p"]
        self.db.query(CompetitorPriceHistory).filter(CompetitorPriceHistory.product_id.in_(temp_ids)).delete()
        self.db.query(CompetitorPrice).filter(CompetitorPrice.product_id.in_(temp_ids)).delete()
        self.db.query(Product).filter(Product.id.in_(temp_ids)).delete()
        self.db.commit()

        # Seed temporary product
        self.product = Product(
            id="temp_comp_p",
            name="Test Comparison Product",
            category="Test",
            current_price=100.0,
            cost_price=60.0,
            stock=10
        )
        self.db.add(self.product)
        self.db.commit()

    def tearDown(self):
        self.db.rollback()
        temp_ids = ["temp_comp_p"]
        self.db.query(CompetitorPriceHistory).filter(CompetitorPriceHistory.product_id.in_(temp_ids)).delete()
        self.db.query(CompetitorPrice).filter(CompetitorPrice.product_id.in_(temp_ids)).delete()
        self.db.query(Product).filter(Product.id.in_(temp_ids)).delete()
        self.db.commit()

    def test_market_average_calculation(self):
        # 3 competitors with prices: 80, 90, 110. Average is 93.3333...
        p1 = CompetitorPrice(product_id="temp_comp_p", competitor_name="Comp A", competitor_price=80.0)
        p2 = CompetitorPrice(product_id="temp_comp_p", competitor_name="Comp B", competitor_price=90.0)
        p3 = CompetitorPrice(product_id="temp_comp_p", competitor_name="Comp C", competitor_price=110.0)
        self.db.add_all([p1, p2, p3])
        self.db.commit()

        stats = self.service.calculate_pricing_comparison(self.db, "temp_comp_p")
        self.assertEqual(stats["competitor_count"], 3)
        self.assertAlmostEqual(stats["average_competitor_price"], 93.33333333333333)

    def test_median_calculation_odd_count(self):
        # 3 competitors: 80, 95, 110. Median is 95
        p1 = CompetitorPrice(product_id="temp_comp_p", competitor_name="Comp A", competitor_price=80.0)
        p2 = CompetitorPrice(product_id="temp_comp_p", competitor_name="Comp B", competitor_price=95.0)
        p3 = CompetitorPrice(product_id="temp_comp_p", competitor_name="Comp C", competitor_price=110.0)
        self.db.add_all([p1, p2, p3])
        self.db.commit()

        stats = self.service.calculate_pricing_comparison(self.db, "temp_comp_p")
        self.assertEqual(stats["median_competitor_price"], 95.0)

    def test_median_calculation_even_count(self):
        # 4 competitors: 80, 90, 100, 110. Median is (90+100)/2 = 95
        p1 = CompetitorPrice(product_id="temp_comp_p", competitor_name="Comp A", competitor_price=80.0)
        p2 = CompetitorPrice(product_id="temp_comp_p", competitor_name="Comp B", competitor_price=90.0)
        p3 = CompetitorPrice(product_id="temp_comp_p", competitor_name="Comp C", competitor_price=100.0)
        p4 = CompetitorPrice(product_id="temp_comp_p", competitor_name="Comp D", competitor_price=110.0)
        self.db.add_all([p1, p2, p3, p4])
        self.db.commit()

        stats = self.service.calculate_pricing_comparison(self.db, "temp_comp_p")
        self.assertEqual(stats["median_competitor_price"], 95.0)

    def test_price_gap_calculation(self):
        # Our price = 100. Average competitor price = 80.
        # Gap absolute = 100 - 80 = 20.
        # Gap percent = (20 / 80) * 100 = 25%
        p1 = CompetitorPrice(product_id="temp_comp_p", competitor_name="Comp A", competitor_price=70.0)
        p2 = CompetitorPrice(product_id="temp_comp_p", competitor_name="Comp B", competitor_price=90.0)
        self.db.add_all([p1, p2])
        self.db.commit()

        stats = self.service.calculate_pricing_comparison(self.db, "temp_comp_p")
        self.assertEqual(stats["price_gap_absolute"], 20.0)
        self.assertEqual(stats["price_gap_percent"], 25.0)

    def test_cheaper_higher_counts(self):
        # Our price = 100. Competitors: 80 (cheaper), 100 (equal), 120 (higher)
        p1 = CompetitorPrice(product_id="temp_comp_p", competitor_name="Comp A", competitor_price=80.0)
        p2 = CompetitorPrice(product_id="temp_comp_p", competitor_name="Comp B", competitor_price=100.0)
        p3 = CompetitorPrice(product_id="temp_comp_p", competitor_name="Comp C", competitor_price=120.0)
        self.db.add_all([p1, p2, p3])
        self.db.commit()

        stats = self.service.calculate_pricing_comparison(self.db, "temp_comp_p")
        self.assertEqual(stats["cheaper_competitor_count"], 1)
        self.assertEqual(stats["higher_competitor_count"], 1)
        self.assertEqual(stats["equal_price_count"], 1)

    def test_competitive_pressure_score(self):
        # Our price = 100. Competitors: 80 (cheaper), 90 (cheaper), 110 (higher), 120 (higher)
        # 2 of 4 cheaper = 50% pressure
        p1 = CompetitorPrice(product_id="temp_comp_p", competitor_name="Comp A", competitor_price=80.0)
        p2 = CompetitorPrice(product_id="temp_comp_p", competitor_name="Comp B", competitor_price=90.0)
        p3 = CompetitorPrice(product_id="temp_comp_p", competitor_name="Comp C", competitor_price=110.0)
        p4 = CompetitorPrice(product_id="temp_comp_p", competitor_name="Comp D", competitor_price=120.0)
        self.db.add_all([p1, p2, p3, p4])
        self.db.commit()

        stats = self.service.calculate_pricing_comparison(self.db, "temp_comp_p")
        self.assertEqual(stats["competitive_pressure"], 50.0)

    def test_ranking_positioning(self):
        # Our price = 100. Competitors: 80, 90. We are more expensive than all. Rank: 3 of 3. Position: highest
        p1 = CompetitorPrice(product_id="temp_comp_p", competitor_name="Comp A", competitor_price=80.0)
        p2 = CompetitorPrice(product_id="temp_comp_p", competitor_name="Comp B", competitor_price=90.0)
        self.db.add_all([p1, p2])
        self.db.commit()

        stats = self.service.calculate_pricing_comparison(self.db, "temp_comp_p")
        self.assertEqual(stats["market_position"], "highest")
        self.assertEqual(stats["market_position_rank"], "3 of 3")

    def test_empty_competitor_records(self):
        stats = self.service.calculate_pricing_comparison(self.db, "temp_comp_p")
        self.assertEqual(stats["competitor_count"], 0)
        self.assertEqual(stats["lowest_competitor_price"], 0.0)
        self.assertEqual(stats["market_position"], "no_competitors")

    def test_historical_trends_grouping(self):
        # 2 competitors on Day 1, 2 competitors on Day 2
        day1 = datetime.utcnow() - timedelta(days=2)
        day2 = datetime.utcnow() - timedelta(days=1)

        h1 = CompetitorPriceHistory(product_id="temp_comp_p", competitor_name="Comp A", competitor_price=80.0, last_checked=day1)
        h2 = CompetitorPriceHistory(product_id="temp_comp_p", competitor_name="Comp B", competitor_price=100.0, last_checked=day1)
        h3 = CompetitorPriceHistory(product_id="temp_comp_p", competitor_name="Comp A", competitor_price=90.0, last_checked=day2)
        h4 = CompetitorPriceHistory(product_id="temp_comp_p", competitor_name="Comp B", competitor_price=110.0, last_checked=day2)
        self.db.add_all([h1, h2, h3, h4])
        self.db.commit()

        history = self.service.calculate_historical_comparison(self.db, "temp_comp_p")
        self.assertEqual(len(history), 2)
        self.assertEqual(history[0]["date"], day1.strftime("%Y-%m-%d"))
        self.assertEqual(history[0]["average"], 90.0)
        self.assertEqual(history[0]["lowest"], 80.0)
    def test_pricing_comparison_endpoints(self):
        from routes.pricing_comparison import get_pricing_comparison, get_pricing_comparison_history

        # Test pricing comparison stats endpoint
        stats_res = get_pricing_comparison(
            product_id="temp_comp_p",
            start_date=None,
            end_date=None,
            competitor=None,
            user={"username": "swara", "role": "Pricing Manager"}
        )
        self.assertEqual(stats_res["product_id"], "temp_comp_p")
        self.assertEqual(stats_res["competitor_count"], 0)

        # Test pricing comparison history endpoint
        history_res = get_pricing_comparison_history(
            product_id="temp_comp_p",
            start_date=None,
            end_date=None,
            competitor=None,
            user={"username": "swara", "role": "Pricing Manager"}
        )
        self.assertEqual(len(history_res), 0)

if __name__ == "__main__":
    unittest.main()
