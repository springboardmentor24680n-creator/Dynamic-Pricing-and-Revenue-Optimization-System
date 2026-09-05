import unittest
from main import SessionLocal, Product, User
from routes.executive_bi import get_executive_bi_summary
from fastapi import HTTPException

class TestExecutiveBI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db = SessionLocal()

    @classmethod
    def tearDownClass(cls):
        cls.db.close()

    def setUp(self):
        self.db.rollback()
        # Clean up any leftover temp test records
        self.db.query(Product).filter(Product.id.like("temp_exec_%")).delete()
        self.db.query(User).filter(User.email.like("temp_exec_%")).delete()
        self.db.commit()

        # Clear Profitability cache to prevent test pollution
        from services.profitability_analytics_service import ProfitabilityAnalyticsService
        ProfitabilityAnalyticsService._details_cache.clear()

        # Seed temporary products and users
        self.admin_user = User(
            name="Temp Admin",
            email="temp_exec_admin@revenueiq.com",
            password_hash="fakehash",
            role="admin"
        )
        self.manager_user = User(
            name="Temp Manager",
            email="temp_exec_manager@revenueiq.com",
            password_hash="fakehash",
            role="pricing manager"
        )
        self.analyst_user = User(
            name="Temp Analyst",
            email="temp_exec_analyst@revenueiq.com",
            password_hash="fakehash",
            role="business analyst"
        )
        self.db.add_all([self.admin_user, self.manager_user, self.analyst_user])

        self.p1 = Product(
            id="temp_exec_p1",
            name="Temp Exec Prod 1",
            category="Test",
            current_price=100.0,
            cost_price=60.0,
            stock=5
        )
        self.db.add(self.p1)
        self.db.commit()

    def tearDown(self):
        self.db.rollback()
        self.db.query(Product).filter(Product.id.like("temp_exec_%")).delete()
        self.db.query(User).filter(User.email.like("temp_exec_%")).delete()
        self.db.commit()

    def test_executive_summary_unauthorized_role(self):
        """Verify that a user with business analyst role gets a 403 Forbidden exception."""
        with self.assertRaises(HTTPException) as context:
            get_executive_bi_summary(user=self.analyst_user)
        self.assertEqual(context.exception.status_code, 403)

    def test_executive_summary_authorized_role(self):
        """Verify that a manager role can call the summary calculation directly and obtain all keys."""
        data = get_executive_bi_summary(user=self.manager_user)
        
        self.assertIn("kpis", data)
        self.assertIn("financial_performance", data)
        self.assertIn("pricing_intelligence", data)
        self.assertIn("product_performance", data)
        self.assertIn("inventory_health", data)
        self.assertIn("demand_forecast", data)
        self.assertIn("insights", data)
        self.assertIn("recommendations", data)

    def test_executive_summary_with_product_filter(self):
        """Verify that passing a product_id filters the scope accordingly."""
        data = get_executive_bi_summary(product_id="temp_exec_p1", user=self.manager_user)
        
        self.assertEqual(data["scope"]["product_id"], "temp_exec_p1")
        self.assertEqual(data["scope"]["product_name"], "Temp Exec Prod 1")

    def test_executive_summary_portfolio_trends(self):
        """Verify that portfolio-wide trend calculations aggregate monthly data and return sorted months."""
        from services.seasonal_trend_service import PRODUCT_MAPPING
        from services.profitability_analytics_service import ProfitabilityAnalyticsService
        
        PRODUCT_MAPPING["temp_exec_p1"] = "TEMP_EXEC_S1"
        
        prof_service = ProfitabilityAnalyticsService()
        prof_service.seasonal_service.product_monthly_cache["TEMP_EXEC_S1"] = {
            1: 10.0,
            2: 20.0,
            5: 15.0
        }
        
        try:
            data = get_executive_bi_summary(user=self.manager_user)
            trends = data["financial_performance"]["trends"]
            self.assertTrue(len(trends) > 0)
            
            months = [t["month"] for t in trends]
            self.assertIn("Jan", months)
            self.assertIn("Feb", months)
            self.assertIn("May", months)
            
            jan_idx = months.index("Jan")
            feb_idx = months.index("Feb")
            may_idx = months.index("May")
            self.assertTrue(jan_idx < feb_idx < may_idx)
        finally:
            PRODUCT_MAPPING.pop("temp_exec_p1", None)
            prof_service.seasonal_service.product_monthly_cache.pop("TEMP_EXEC_S1", None)

    def test_executive_summary_single_product_trends_with_date_filter(self):
        """Verify that single product trend calculations filter correct month range."""
        from services.seasonal_trend_service import PRODUCT_MAPPING
        from services.profitability_analytics_service import ProfitabilityAnalyticsService
        
        PRODUCT_MAPPING["temp_exec_p1"] = "TEMP_EXEC_S1"
        
        prof_service = ProfitabilityAnalyticsService()
        prof_service.seasonal_service.product_monthly_cache["TEMP_EXEC_S1"] = {
            1: 10.0,
            2: 20.0,
            5: 15.0,
            6: 30.0
        }
        
        try:
            data = get_executive_bi_summary(
                product_id="temp_exec_p1",
                start_date="2026-02-01",
                end_date="2026-05-30",
                user=self.manager_user
            )
            trends = data["financial_performance"]["trends"]
            months = [t["month"] for t in trends]
            
            self.assertIn("Feb", months)
            self.assertIn("May", months)
            self.assertNotIn("Jan", months)
            self.assertNotIn("Jun", months)
        finally:
            PRODUCT_MAPPING.pop("temp_exec_p1", None)
            prof_service.seasonal_service.product_monthly_cache.pop("TEMP_EXEC_S1", None)
