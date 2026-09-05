import sys
import unittest
from pathlib import Path

# Add backend to path
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.append(str(BASE_DIR))

from main import SessionLocal, Product, CompetitorPrice, CompetitorPriceHistory, CompetitorAlert
from services.competitor_monitoring_service import CompetitorMonitoringService

class TestCompetitorMonitoring(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import os
        os.environ["TESTING"] = "true"
        cls.db = SessionLocal()
        cls.service = CompetitorMonitoringService()

    @classmethod
    def tearDownClass(cls):
        import os
        if "TESTING" in os.environ:
            del os.environ["TESTING"]
        cls.db.close()

    def setUp(self):
        import os
        from unittest.mock import patch
        self.db.rollback()
        
        # Clean up any leftover temp test records
        from main import Product, CompetitorPrice, CompetitorPriceHistory, CompetitorAlert, CompetitorMonitoringRun
        temp_ids = ["temp_alert_p", "temp_error_p", "temp_p1", "temp_p2", "temp_p3", "temp_fallback_p", "temp_both_fail_p"]
        self.db.query(CompetitorAlert).filter(CompetitorAlert.product_id.in_(temp_ids)).delete()
        self.db.query(CompetitorPrice).filter(CompetitorPrice.product_id.in_(temp_ids)).delete()
        self.db.query(CompetitorPriceHistory).filter(CompetitorPriceHistory.product_id.in_(temp_ids)).delete()
        self.db.query(Product).filter(Product.id.in_(temp_ids)).delete()
        self.db.query(CompetitorMonitoringRun).delete()
        self.db.commit()
        
        self.orig_getenv = os.getenv
        def mock_getenv(key, default=None):
            if key in ["OPENWEBNINJA_API_KEY", "OPENWEB_NINJA_API_KEY", "PRICES_API_KEY"]:
                return ""
            return self.orig_getenv(key, default)
        self.getenv_patcher = patch("os.getenv", side_effect=mock_getenv)
        self.getenv_patcher.start()

    def tearDown(self):
        self.db.rollback()
        self.getenv_patcher.stop()

    def test_price_validation_valid(self):
        """Verify that valid prices pass validation and return float."""
        self.assertEqual(self.service.validate_price(100), 100.0)
        self.assertEqual(self.service.validate_price(10.55), 10.55)
        self.assertEqual(self.service.validate_price("12.34"), 12.34)

    def test_price_validation_invalid_missing(self):
        """Verify that missing/invalid prices raise ValueError."""
        with self.assertRaises(ValueError):
            self.service.validate_price(None)
        with self.assertRaises(ValueError):
            self.service.validate_price("not-a-number")
        with self.assertRaises(ValueError):
            self.service.validate_price(-5.0)

    def test_calculate_price_change_increase(self):
        """Verify calculations for a price increase."""
        res = self.service.calculate_price_change(120.0, 100.0)
        self.assertEqual(res["price_change"], 20.0)
        self.assertEqual(res["price_change_percent"], 20.0)

    def test_calculate_price_change_decrease(self):
        """Verify calculations for a price decrease."""
        res = self.service.calculate_price_change(80.0, 100.0)
        self.assertEqual(res["price_change"], -20.0)
        self.assertEqual(res["price_change_percent"], -20.0)

    def test_calculate_price_change_unchanged(self):
        """Verify calculations when price is unchanged."""
        res = self.service.calculate_price_change(100.0, 100.0)
        self.assertEqual(res["price_change"], 0.0)
        self.assertEqual(res["price_change_percent"], 0.0)

    def test_calculate_price_change_invalid_previous(self):
        """Verify price change calculations handle invalid/none/zero previous price gracefully."""
        res1 = self.service.calculate_price_change(100.0, None)
        self.assertEqual(res1["price_change"], 0.0)
        self.assertEqual(res1["price_change_percent"], 0.0)

        res2 = self.service.calculate_price_change(100.0, 0.0)
        self.assertEqual(res2["price_change"], 0.0)
        self.assertEqual(res2["price_change_percent"], 0.0)

    def test_determine_trend_increase(self):
        """Verify trend for price increase."""
        self.assertEqual(self.service.determine_trend(5.0), "increased")

    def test_determine_trend_decrease(self):
        """Verify trend for price decrease."""
        self.assertEqual(self.service.determine_trend(-5.0), "decreased")

    def test_determine_trend_stable(self):
        """Verify trend for stable/unchanged price."""
        self.assertEqual(self.service.determine_trend(0.0), "stable")

    def test_mock_data_generation(self):
        """Verify mock data generation retrieves structured dicts based on active product."""
        product = self.db.query(Product).first()
        if not product:
            self.skipTest("No products in database to test mock generation.")
        
        mock_data = self.service.get_mock_data(product.id, self.db)
        self.assertGreater(len(mock_data), 0)
        for item in mock_data:
            self.assertEqual(item["product_id"], product.id)
            self.assertIn("competitor_name", item)
            self.assertIn("competitor_price", item)
            self.assertGreater(item["competitor_price"], 0)

    def test_update_and_history_storage(self):
        """Verify updating competitor prices stores latest price, calculates deltas, and saves history."""
        # Find a product to test
        product = self.db.query(Product).first()
        if not product:
            self.skipTest("No products in database to test updates.")

        # Ensure no residual test records for our specific test competitor
        test_comp_name = "TempTestComp"
        self.db.query(CompetitorPrice).filter(
            CompetitorPrice.product_id == product.id,
            CompetitorPrice.competitor_name == test_comp_name
        ).delete()
        self.db.query(CompetitorPriceHistory).filter(
            CompetitorPriceHistory.product_id == product.id,
            CompetitorPriceHistory.competitor_name == test_comp_name
        ).delete()
        self.db.commit()

        # 1. Create a baseline record manually
        baseline = CompetitorPrice(
            product_id=product.id,
            competitor_name=test_comp_name,
            competitor_product_name="Temp Test Product",
            competitor_url="https://test.com/123",
            competitor_price=100.0,
            currency="USD",
            availability="In Stock",
            previous_price=None,
            price_change=0.0,
            price_change_percent=0.0
        )
        self.db.add(baseline)
        
        hist_baseline = CompetitorPriceHistory(
            product_id=product.id,
            competitor_name=test_comp_name,
            competitor_price=100.0,
            currency="USD"
        )
        self.db.add(hist_baseline)
        self.db.commit()

        # 2. Trigger mock update using service
        original_get_mock_data = self.service.get_mock_data
        
        try:
            self.service.get_mock_data = lambda p_id, db: [
                {
                    "product_id": p_id,
                    "competitor_name": test_comp_name,
                    "competitor_product_name": "Temp Test Product",
                    "competitor_url": "https://test.com/123",
                    "competitor_price": 120.0,  # 20% increase
                    "currency": "USD",
                    "availability": "In Stock"
                }
            ]

            # Run update for this product
            updated = self.service.update_competitor_prices(self.db, product_id=product.id)
            self.assertEqual(len(updated), 1)

            # Query updated price record
            price_rec = self.db.query(CompetitorPrice).filter(
                CompetitorPrice.product_id == product.id,
                CompetitorPrice.competitor_name == test_comp_name
            ).first()

            self.assertIsNotNone(price_rec)
            self.assertEqual(price_rec.competitor_price, 120.0)
            self.assertEqual(price_rec.previous_price, 100.0)
            self.assertEqual(price_rec.price_change, 20.0)
            self.assertEqual(price_rec.price_change_percent, 20.0)

            # Query history records
            history_recs = self.db.query(CompetitorPriceHistory).filter(
                CompetitorPriceHistory.product_id == product.id,
                CompetitorPriceHistory.competitor_name == test_comp_name
            ).all()

            # We should have the baseline history and the new updated history (2 records total)
            self.assertEqual(len(history_recs), 2)
            prices = [h.competitor_price for h in history_recs]
            self.assertIn(100.0, prices)
            self.assertIn(120.0, prices)

        finally:
            # Restore original method
            self.service.get_mock_data = original_get_mock_data
            
            # Clean up test records
            self.db.query(CompetitorPrice).filter(
                CompetitorPrice.product_id == product.id,
                CompetitorPrice.competitor_name == test_comp_name
            ).delete()
            self.db.query(CompetitorPriceHistory).filter(
                CompetitorPriceHistory.product_id == product.id,
                CompetitorPriceHistory.competitor_name == test_comp_name
            ).delete()
            self.db.commit()

    def test_run_monitoring_cycle_increase(self):
        """Verify that an increase in competitor price triggers a PRICE_INCREASE alert."""
        product = self.db.query(Product).first()
        if not product:
            self.skipTest("No products in database.")
        
        test_comp_name = "TestIncreaseComp"
        
        # Clean old records
        self.db.query(CompetitorPrice).filter(
            CompetitorPrice.product_id == product.id,
            CompetitorPrice.competitor_name == test_comp_name
        ).delete()
        self.db.query(CompetitorAlert).filter(
            CompetitorAlert.product_id == product.id,
            CompetitorAlert.competitor_name == test_comp_name
        ).delete()
        self.db.commit()

        # Seed baseline price
        baseline = CompetitorPrice(
            product_id=product.id,
            competitor_name=test_comp_name,
            competitor_product_name="Test Product",
            competitor_url="https://test.com",
            competitor_price=100.0,
            currency="USD",
            availability="In Stock",
            previous_price=None,
            price_change=0.0,
            price_change_percent=0.0
        )
        self.db.add(baseline)
        self.db.commit()

        original_get_mock_data = self.service.get_mock_data
        try:
            # Mock competitor price to 103.0 (3% increase, which is below 5% threshold)
            self.service.get_mock_data = lambda p_id, db: [
                {
                    "product_id": p_id,
                    "competitor_name": test_comp_name,
                    "competitor_product_name": "Test Product",
                    "competitor_url": "https://test.com",
                    "competitor_price": 103.0,
                    "currency": "USD",
                    "availability": "In Stock"
                }
            ]

            results = self.service.run_monitoring_cycle(self.db, product_id=product.id)
            self.assertEqual(results["price_changes_detected"], 1)
            self.assertEqual(results["alerts_generated"], 1)

            # Query the alert
            alert = self.db.query(CompetitorAlert).filter(
                CompetitorAlert.product_id == product.id,
                CompetitorAlert.competitor_name == test_comp_name
            ).first()
            self.assertIsNotNone(alert)
            self.assertEqual(alert.event_type, "PRICE_INCREASE")
            self.assertEqual(alert.severity, "low")
            self.assertEqual(alert.previous_price, 100.0)
            self.assertEqual(alert.current_price, 103.0)
            self.assertEqual(alert.change_amount, 3.0)
            self.assertEqual(alert.change_percent, 3.0)
            self.assertFalse(alert.is_acknowledged)

        finally:
            self.service.get_mock_data = original_get_mock_data
            self.db.query(CompetitorPrice).filter(
                CompetitorPrice.product_id == product.id,
                CompetitorPrice.competitor_name == test_comp_name
            ).delete()
            self.db.query(CompetitorAlert).filter(
                CompetitorAlert.product_id == product.id,
                CompetitorAlert.competitor_name == test_comp_name
            ).delete()
            self.db.commit()

    def test_run_monitoring_cycle_decrease(self):
        """Verify that a decrease in competitor price triggers a PRICE_DECREASE alert."""
        product = self.db.query(Product).first()
        if not product:
            self.skipTest("No products in database.")
        
        test_comp_name = "TestDecreaseComp"
        
        # Clean old records
        self.db.query(CompetitorPrice).filter(
            CompetitorPrice.product_id == product.id,
            CompetitorPrice.competitor_name == test_comp_name
        ).delete()
        self.db.query(CompetitorAlert).filter(
            CompetitorAlert.product_id == product.id,
            CompetitorAlert.competitor_name == test_comp_name
        ).delete()
        self.db.commit()

        # Seed baseline price
        baseline = CompetitorPrice(
            product_id=product.id,
            competitor_name=test_comp_name,
            competitor_product_name="Test Product",
            competitor_url="https://test.com",
            competitor_price=100.0,
            currency="USD",
            availability="In Stock",
            previous_price=None,
            price_change=0.0,
            price_change_percent=0.0
        )
        self.db.add(baseline)
        self.db.commit()

        original_get_mock_data = self.service.get_mock_data
        try:
            # Mock competitor price to 97.0 (3% decrease, which is below 5% threshold)
            self.service.get_mock_data = lambda p_id, db: [
                {
                    "product_id": p_id,
                    "competitor_name": test_comp_name,
                    "competitor_product_name": "Test Product",
                    "competitor_url": "https://test.com",
                    "competitor_price": 97.0,
                    "currency": "USD",
                    "availability": "In Stock"
                }
            ]

            results = self.service.run_monitoring_cycle(self.db, product_id=product.id)
            self.assertEqual(results["price_changes_detected"], 1)
            self.assertEqual(results["alerts_generated"], 1)

            # Query the alert
            alert = self.db.query(CompetitorAlert).filter(
                CompetitorAlert.product_id == product.id,
                CompetitorAlert.competitor_name == test_comp_name
            ).first()
            self.assertIsNotNone(alert)
            self.assertEqual(alert.event_type, "PRICE_DECREASE")
            self.assertEqual(alert.severity, "low")
            self.assertEqual(alert.previous_price, 100.0)
            self.assertEqual(alert.current_price, 97.0)
            self.assertEqual(alert.change_amount, -3.0)
            self.assertEqual(alert.change_percent, -3.0)

        finally:
            self.service.get_mock_data = original_get_mock_data
            self.db.query(CompetitorPrice).filter(
                CompetitorPrice.product_id == product.id,
                CompetitorPrice.competitor_name == test_comp_name
            ).delete()
            self.db.query(CompetitorAlert).filter(
                CompetitorAlert.product_id == product.id,
                CompetitorAlert.competitor_name == test_comp_name
            ).delete()
            self.db.commit()

    def test_run_monitoring_cycle_unchanged(self):
        """Verify that an unchanged price does not trigger any alert."""
        product = self.db.query(Product).first()
        if not product:
            self.skipTest("No products in database.")
        
        test_comp_name = "TestUnchangedComp"
        
        # Clean old records
        self.db.query(CompetitorPrice).filter(
            CompetitorPrice.product_id == product.id,
            CompetitorPrice.competitor_name == test_comp_name
        ).delete()
        self.db.query(CompetitorAlert).filter(
            CompetitorAlert.product_id == product.id,
            CompetitorAlert.competitor_name == test_comp_name
        ).delete()
        self.db.commit()

        # Seed baseline price
        baseline = CompetitorPrice(
            product_id=product.id,
            competitor_name=test_comp_name,
            competitor_product_name="Test Product",
            competitor_url="https://test.com",
            competitor_price=100.0,
            currency="USD",
            availability="In Stock",
            previous_price=None,
            price_change=0.0,
            price_change_percent=0.0
        )
        self.db.add(baseline)
        self.db.commit()

        original_get_mock_data = self.service.get_mock_data
        try:
            # Mock competitor price to 100.0 (unchanged)
            self.service.get_mock_data = lambda p_id, db: [
                {
                    "product_id": p_id,
                    "competitor_name": test_comp_name,
                    "competitor_product_name": "Test Product",
                    "competitor_url": "https://test.com",
                    "competitor_price": 100.0,
                    "currency": "USD",
                    "availability": "In Stock"
                }
            ]

            results = self.service.run_monitoring_cycle(self.db, product_id=product.id)
            self.assertEqual(results["price_changes_detected"], 0)
            self.assertEqual(results["alerts_generated"], 0)

            # Query to verify no alert was created
            alert = self.db.query(CompetitorAlert).filter(
                CompetitorAlert.product_id == product.id,
                CompetitorAlert.competitor_name == test_comp_name
            ).first()
            self.assertIsNone(alert)

        finally:
            self.service.get_mock_data = original_get_mock_data
            self.db.query(CompetitorPrice).filter(
                CompetitorPrice.product_id == product.id,
                CompetitorPrice.competitor_name == test_comp_name
            ).delete()
            self.db.commit()

    def test_significant_price_change_detection(self):
        """Verify that competitor price change exceeding threshold triggers SIGNIFICANT_PRICE_CHANGE."""
        product = self.db.query(Product).first()
        if not product:
            self.skipTest("No products in database.")
        
        test_comp_name = "TestSignificantComp"
        
        # Clean old records
        self.db.query(CompetitorPrice).filter(
            CompetitorPrice.product_id == product.id,
            CompetitorPrice.competitor_name == test_comp_name
        ).delete()
        self.db.query(CompetitorAlert).filter(
            CompetitorAlert.product_id == product.id,
            CompetitorAlert.competitor_name == test_comp_name
        ).delete()
        self.db.commit()

        # Seed baseline price
        baseline = CompetitorPrice(
            product_id=product.id,
            competitor_name=test_comp_name,
            competitor_product_name="Test Product",
            competitor_url="https://test.com",
            competitor_price=100.0,
            currency="USD",
            availability="In Stock",
            previous_price=None,
            price_change=0.0,
            price_change_percent=0.0
        )
        self.db.add(baseline)
        self.db.commit()

        import os
        # Set threshold env var to 5
        os.environ["COMPETITOR_PRICE_ALERT_THRESHOLD_PERCENT"] = "5"

        original_get_mock_data = self.service.get_mock_data
        try:
            # Mock competitor price to 110.0 (10% increase, which is >= 5% threshold)
            self.service.get_mock_data = lambda p_id, db: [
                {
                    "product_id": p_id,
                    "competitor_name": test_comp_name,
                    "competitor_product_name": "Test Product",
                    "competitor_url": "https://test.com",
                    "competitor_price": 110.0,
                    "currency": "USD",
                    "availability": "In Stock"
                }
            ]

            results = self.service.run_monitoring_cycle(self.db, product_id=product.id)
            self.assertEqual(results["price_changes_detected"], 1)
            self.assertEqual(results["alerts_generated"], 1)

            # Query the alert
            alert = self.db.query(CompetitorAlert).filter(
                CompetitorAlert.product_id == product.id,
                CompetitorAlert.competitor_name == test_comp_name
            ).first()
            self.assertIsNotNone(alert)
            self.assertEqual(alert.event_type, "SIGNIFICANT_PRICE_CHANGE")
            self.assertEqual(alert.severity, "high")
            self.assertEqual(alert.previous_price, 100.0)
            self.assertEqual(alert.current_price, 110.0)
            self.assertEqual(alert.change_amount, 10.0)
            self.assertEqual(alert.change_percent, 10.0)

        finally:
            self.service.get_mock_data = original_get_mock_data
            self.db.query(CompetitorPrice).filter(
                CompetitorPrice.product_id == product.id,
                CompetitorPrice.competitor_name == test_comp_name
            ).delete()
            self.db.query(CompetitorAlert).filter(
                CompetitorAlert.product_id == product.id,
                CompetitorAlert.competitor_name == test_comp_name
            ).delete()
            self.db.commit()

    def test_alert_acknowledgement(self):
        """Verify that alerts can be retrieved and marked as acknowledged."""
        product = self.db.query(Product).first()
        if not product:
            self.skipTest("No products in database.")
            
        # Create a test alert manually
        alert = CompetitorAlert(
            product_id=product.id,
            competitor_name="TestAckComp",
            event_type="PRICE_INCREASE",
            previous_price=100.0,
            current_price=105.0,
            change_amount=5.0,
            change_percent=5.0,
            severity="low",
            message="Test Alert message",
            is_acknowledged=False
        )
        self.db.add(alert)
        self.db.commit()
        
        alert_id = alert.id
        
        try:
            # Verify initial state
            retrieved = self.db.query(CompetitorAlert).filter(CompetitorAlert.id == alert_id).first()
            self.assertIsNotNone(retrieved)
            self.assertFalse(retrieved.is_acknowledged)
            
            # Acknowledge
            retrieved.is_acknowledged = True
            self.db.commit()
            
            # Verify acknowledged state
            updated = self.db.query(CompetitorAlert).filter(CompetitorAlert.id == alert_id).first()
            self.assertTrue(updated.is_acknowledged)
            
        finally:
            self.db.query(CompetitorAlert).filter(CompetitorAlert.id == alert_id).delete()
            self.db.commit()

    def test_one_competitor_failing(self):
        """Verify that one competitor failing doesn't stop the monitoring cycle for others."""
        # Retrieve two products
        products = self.db.query(Product).limit(2).all()
        if len(products) < 2:
            self.skipTest("Need at least 2 products to test single failure propagation.")
            
        prod1, prod2 = products[0], products[1]
        
        # Clean old records
        self.db.query(CompetitorPrice).filter(
            CompetitorPrice.product_id.in_([prod1.id, prod2.id]),
            CompetitorPrice.competitor_name == "TechMart"
        ).delete()
        self.db.commit()

        # Seed baselines
        baseline1 = CompetitorPrice(
            product_id=prod1.id,
            competitor_name="TechMart",
            competitor_product_name="Test Prod 1",
            competitor_url="https://test.com",
            competitor_price=100.0,
            currency="USD",
            availability="In Stock",
            previous_price=None,
            price_change=0.0,
            price_change_percent=0.0
        )
        baseline2 = CompetitorPrice(
            product_id=prod2.id,
            competitor_name="TechMart",
            competitor_product_name="Test Prod 2",
            competitor_url="https://test.com",
            competitor_price=100.0,
            currency="USD",
            availability="In Stock",
            previous_price=None,
            price_change=0.0,
            price_change_percent=0.0
        )
        self.db.add(baseline1)
        self.db.add(baseline2)
        self.db.commit()

        original_get_mock_data = self.service.get_mock_data
        try:
            # Mock get_mock_data so that prod1 competitor price is invalid (None or negative, which fails validation),
            # but prod2 has a valid update.
            def mock_get_mock(p_id, db):
                if p_id == prod1.id:
                    return [
                        {
                            "product_id": p_id,
                            "competitor_name": "TechMart",
                            "competitor_product_name": "Test Prod 1",
                            "competitor_url": "https://test.com",
                            "competitor_price": -50.0,  # Invalid! Fails validation.
                            "currency": "USD",
                            "availability": "In Stock"
                        }
                    ]
                else:
                    return [
                        {
                            "product_id": p_id,
                            "competitor_name": "TechMart",
                            "competitor_product_name": "Test Prod 2",
                            "competitor_url": "https://test.com",
                            "competitor_price": 105.0,  # Valid 5% increase
                            "currency": "USD",
                            "availability": "In Stock"
                        }
                    ]
            
            self.service.get_mock_data = mock_get_mock

            # Run monitoring cycle across all products
            results = self.service.run_monitoring_cycle(self.db)
            
            # The second product should have successfully processed despite the first one throwing a ValueError inside validate_price
            self.assertGreaterEqual(results["competitors_checked"], 1)
            
            # Query updated price record for prod2 to ensure it successfully committed
            price_rec2 = self.db.query(CompetitorPrice).filter(
                CompetitorPrice.product_id == prod2.id,
                CompetitorPrice.competitor_name == "TechMart"
            ).first()
            self.assertIsNotNone(price_rec2)
            self.assertEqual(price_rec2.competitor_price, 105.0)

        finally:
            self.service.get_mock_data = original_get_mock_data
            self.db.query(CompetitorPrice).filter(
                CompetitorPrice.product_id.in_([prod1.id, prod2.id]),
                CompetitorPrice.competitor_name == "TechMart"
            ).delete()
            self.db.commit()

    def test_monitoring_status(self):
        """Verify the fields and logic of the competitor monitoring status retrieval."""
        from services.scheduler import scheduler, start_scheduler
        from routes.competitor_monitoring import get_monitoring_status
        
        start_scheduler()
        try:
            status = get_monitoring_status(user=None)
            self.assertIn("monitoring_enabled", status)
            self.assertIn("last_monitoring_run", status)
            self.assertIn("next_scheduled_run", status)
            self.assertIn("number_of_competitors_monitored", status)
            self.assertIn("number_of_price_changes_detected", status)
            self.assertIn("number_of_active_alerts", status)
            self.assertIn("data_source", status)
            self.assertIn("api_status", status)
            self.assertTrue(status["monitoring_enabled"])
        finally:
            if scheduler.get_job("competitor_monitoring"):
                scheduler.remove_job("competitor_monitoring")

    def test_openweb_ninja_normalization(self):
        from services.openweb_ninja_service import OpenWebNinjaService
        srv = OpenWebNinjaService()
        raw_results = [
            {
                "title": "Wireless Headphones Pro",
                "link": "https://test.com/item1",
                "price": "₹1,999.00",
                "extracted_price": 1999.0,
                "currency": "INR",
                "source": "Amazon.in",
                "availability": "In Stock",
                "rating": 4.5,
                "reviews_count": 120
            }
        ]
        norm = srv.normalize_results(raw_results, "elec_headphones")
        self.assertEqual(len(norm), 1)
        self.assertEqual(norm[0]["competitor_price"], 1999.0)
        self.assertEqual(norm[0]["competitor_name"], "Amazon.in")
        self.assertEqual(norm[0]["data_source"], "openwebninja")

    def test_openweb_ninja_v2_normalization(self):
        from services.openweb_ninja_service import OpenWebNinjaService
        srv = OpenWebNinjaService()
        raw_results = [
            {
                "product_title": "Wireless Headphones V2",
                "product_url": "https://test.com/item2",
                "price": 3499.0,
                "original_price": 3999.0,
                "currency": "INR",
                "merchant_name": "Flipkart",
                "in_stock": True,
                "stars": 4.8,
                "review_count": 350
            }
        ]
        norm = srv.normalize_results(raw_results, "elec_smartwatch")
        self.assertEqual(len(norm), 1)
        self.assertEqual(norm[0]["competitor_price"], 3499.0)
        self.assertEqual(norm[0]["original_price"], 3999.0)
        self.assertEqual(norm[0]["competitor_name"], "Flipkart")
        self.assertEqual(norm[0]["availability"], "In Stock")
        self.assertEqual(norm[0]["rating"], 4.8)
        self.assertEqual(norm[0]["review_count"], 350)

    def test_openweb_ninja_relevance_matching(self):
        import os
        from services.openweb_ninja_service import OpenWebNinjaService
        srv = OpenWebNinjaService()
        
        # Test exact/high similarity matches
        self.assertGreaterEqual(srv.compute_similarity("Wireless Headphones", "Wireless Headphones Pro"), 0.70)
        
        # Test low similarity mismatch
        self.assertLess(srv.compute_similarity("Wireless Headphones", "Kitchen Knife Set"), 0.40)
        
        # Test filter matching logic
        items = [
            {
                "product_id": "elec_headphones",
                "competitor_name": "Amazon",
                "competitor_product_name": "Wireless Headphones Pro",
                "competitor_url": "http://link",
                "competitor_price": 1999.0,
                "currency": "INR",
                "availability": "In Stock"
            },
            {
                "product_id": "elec_headphones",
                "competitor_name": "Amazon",
                "competitor_product_name": "Kitchen Knife Set",
                "competitor_url": "http://link",
                "competitor_price": 1999.0,
                "currency": "INR",
                "availability": "In Stock"
            }
        ]
        os.environ["COMPETITOR_MATCH_THRESHOLD"] = "0.70"
        matched = srv.filter_relevant_results(items, "Wireless Headphones")
        self.assertEqual(len(matched), 1)
        self.assertEqual(matched[0]["competitor_product_name"], "Wireless Headphones Pro")

    def test_openweb_ninja_errors(self):
        from unittest.mock import patch
        import requests
        from services.openweb_ninja_service import OpenWebNinjaService
        
        srv = OpenWebNinjaService()
        srv.api_key = "test_key"
        
        with patch("requests.get", side_effect=requests.Timeout("Timeout info")):
            res = srv.search_product("Wireless Headphones", "elec_headphones")
            self.assertEqual(res, [])
            
        with patch("requests.get", side_effect=requests.RequestException("RequestException info")):
            res = srv.search_product("Wireless Headphones", "elec_headphones")
            self.assertEqual(res, [])

    def test_monitoring_cycle_with_fallback(self):
        import os
        from unittest.mock import patch
        from main import CompetitorPrice
        
        orig_getenv = os.getenv
        def mock_getenv(key, default=None):
            if key in ["OPENWEBNINJA_API_KEY", "OPENWEB_NINJA_API_KEY", "PRICES_API_KEY"]:
                return ""
            return orig_getenv(key, default)
            
        # Force empty key call inside run_monitoring_cycle to test fallback paths
        with patch("os.getenv", side_effect=mock_getenv):
            results = self.service.run_monitoring_cycle(self.db, force_all=True)
            self.assertGreaterEqual(results["competitors_checked"], 1)
            recs = self.db.query(CompetitorPrice).filter(CompetitorPrice.product_id.like("temp_%")).all()
            for r in recs:
                self.assertIn(r.data_source, ["mock_fallback", "openwebninja"])

    def test_scheduler_due_selection_and_priority_sorting(self):
        from main import Product
        from datetime import datetime, timedelta
        
        # Create temp products
        p1 = Product(id="temp_p1", name="Temp Prod 1", current_price=100.0, monitoring_priority="MEDIUM", next_competitor_scan=datetime.utcnow() - timedelta(hours=1))
        p2 = Product(id="temp_p2", name="Temp Prod 2", current_price=200.0, monitoring_priority="HIGH", next_competitor_scan=datetime.utcnow() - timedelta(hours=2))
        p3 = Product(id="temp_p3", name="Temp Prod 3", current_price=300.0, monitoring_priority="LOW", next_competitor_scan=datetime.utcnow() + timedelta(hours=5))
        
        self.db.add_all([p1, p2, p3])
        self.db.commit()
        
        try:
            due = self.service.get_due_products(self.db, max_limit=10)
            due_ids = [p.id for p in due]
            
            # Check p3 is not in due list
            self.assertNotIn("temp_p3", due_ids)
            # Check priority sorting: temp_p2 (HIGH) must come before temp_p1 (MEDIUM)
            self.assertIn("temp_p1", due_ids)
            self.assertIn("temp_p2", due_ids)
            self.assertTrue(due_ids.index("temp_p2") < due_ids.index("temp_p1"))
        finally:
            self.db.delete(p1)
            self.db.delete(p2)
            self.db.delete(p3)
            self.db.commit()

    def test_request_budget_enforcement(self):
        from unittest.mock import patch
        from main import CompetitorMonitoringRun
        import os
        
        orig_getenv = os.getenv
        def mock_getenv(key, default=None):
            if key in ["OPENWEBNINJA_API_KEY", "OPENWEB_NINJA_API_KEY"]:
                return "mock_key"
            return orig_getenv(key, default)
            
        with patch("os.getenv", side_effect=mock_getenv):
            with patch.object(self.service, "get_api_usage_stats", return_value={"budget_status": "exhausted", "monthly_limit": 100, "requests_used_this_month": 100, "requests_remaining": 0, "estimated_monthly_usage": 100.0}):
                res = self.service.run_monitoring_cycle(self.db)
                self.assertEqual(res["status"], "budget_exhausted")
                
                # Check run history logged
                last_run = self.db.query(CompetitorMonitoringRun).order_by(CompetitorMonitoringRun.started_at.desc()).first()
                self.assertIsNotNone(last_run)
                self.assertEqual(last_run.status, "budget_exhausted")

    def test_alerts_detection_and_deduplication(self):
        from main import Product, CompetitorPrice, CompetitorAlert
        from datetime import datetime
        import os
        
        p = Product(id="temp_alert_p", name="Alert Product", current_price=100.0, monitoring_priority="HIGH")
        self.db.add(p)
        self.db.commit()
        
        try:
            # 1. Clean existing alerts
            self.db.query(CompetitorAlert).filter(CompetitorAlert.product_id == "temp_alert_p").delete()
            self.db.query(CompetitorPrice).filter(CompetitorPrice.product_id == "temp_alert_p").delete()
            self.db.commit()
            
            # 2. Simulate new competitor scan (NEW_COMPETITOR)
            mock_items = [{
                "product_id": "temp_alert_p",
                "competitor_name": "TestComp",
                "competitor_product_name": "TestComp Product",
                "competitor_url": "http://test",
                "competitor_price": 95.0, # undercuts by 5% (> 2%)
                "currency": "INR",
                "availability": "In Stock",
                "data_source": "openwebninja"
            }]
            
            from unittest.mock import patch
            orig_getenv = os.getenv
            def mock_getenv(key, default=None):
                if key in ["OPENWEBNINJA_API_KEY", "OPENWEB_NINJA_API_KEY"]:
                    return "mock_key"
                return orig_getenv(key, default)
                
            with patch("os.getenv", side_effect=mock_getenv):
                with patch("services.openweb_ninja_service.OpenWebNinjaService.search_product", return_value=mock_items):
                    # First run: inserts NEW_COMPETITOR alert
                    self.service.run_monitoring_cycle(self.db, product_id="temp_alert_p")
                    
                    alerts = self.db.query(CompetitorAlert).filter(
                        CompetitorAlert.product_id == "temp_alert_p",
                        CompetitorAlert.event_type == "NEW_COMPETITOR"
                    ).all()
                    self.assertEqual(len(alerts), 1)
                    
                    # Second run: duplicate check prevents duplicate alert insertion
                    self.service.run_monitoring_cycle(self.db, product_id="temp_alert_p")
                    alerts_after = self.db.query(CompetitorAlert).filter(
                        CompetitorAlert.product_id == "temp_alert_p",
                        CompetitorAlert.event_type == "NEW_COMPETITOR"
                    ).all()
                    self.assertEqual(len(alerts_after), 1) # deduplicated!
        finally:
            self.db.query(CompetitorAlert).filter(CompetitorAlert.product_id == "temp_alert_p").delete()
            self.db.query(CompetitorPrice).filter(CompetitorPrice.product_id == "temp_alert_p").delete()
            self.db.query(CompetitorPriceHistory).filter(CompetitorPriceHistory.product_id == "temp_alert_p").delete()
            self.db.delete(p)
            self.db.commit()

    def test_api_errors_retains_prices(self):
        from main import Product, CompetitorPrice, CompetitorMonitoringRun, CompetitorPriceHistory
        from services.openweb_ninja_service import OpenWebNinjaService
        from unittest.mock import patch
        import os
        
        p = Product(id="temp_error_p", name="Error Product", current_price=100.0, monitoring_priority="MEDIUM")
        self.db.add(p)
        self.db.commit()
        
        price = CompetitorPrice(product_id="temp_error_p", competitor_name="OldComp", competitor_product_name="Old SKU", competitor_price=90.0, currency="INR")
        self.db.add(price)
        self.db.commit()
        
        try:
            orig_getenv = os.getenv
            def mock_getenv(key, default=None):
                if key in ["OPENWEBNINJA_API_KEY", "OPENWEB_NINJA_API_KEY"]:
                    return "mock_key"
                return orig_getenv(key, default)
                
            def mock_search_fail(self_instance, q, pid):
                self_instance.last_api_status = "API RATE LIMITED"
                return []
                
            with patch("os.getenv", side_effect=mock_getenv):
                with patch.object(OpenWebNinjaService, "search_product", mock_search_fail):
                    res = self.service.run_monitoring_cycle(self.db, product_id="temp_error_p")
                    self.assertEqual(res["status"], "failed")
                    self.assertEqual(res["api_status"], "API RATE LIMITED")
                    
                    # Verify old record is retained (not deleted, not overridden with mock fallback data)
                    rec = self.db.query(CompetitorPrice).filter(CompetitorPrice.product_id == "temp_error_p").first()
                    self.assertIsNotNone(rec)
                    self.assertEqual(rec.competitor_name, "OldComp")
                    self.assertEqual(rec.competitor_price, 90.0)
        finally:
            self.db.query(CompetitorPrice).filter(CompetitorPrice.product_id == "temp_error_p").delete()
            self.db.query(CompetitorPriceHistory).filter(CompetitorPriceHistory.product_id == "temp_error_p").delete()
            self.db.delete(p)
            self.db.commit()

    def test_prices_api_service_normalization(self):
        from services.prices_api_service import PricesAPIService
        service = PricesAPIService()
        mock_payload = [
            {
                "title": "Mechanical Keyboard Core",
                "source": "TechShopper",
                "price": 1200.0,
                "currency": "INR",
                "url": "https://techshopper.com/kb",
                "rating": 4.5,
                "reviews_count": 89,
                "offers": [
                  {
                    "seller": "FastShip India",
                    "seller_url": "https://fastship.in/kb",
                    "price": 1150.0,
                    "currency": "INR",
                    "condition": "New"
                  }
                ]
            }
        ]
        res = service.normalize_results(mock_payload, "temp_p")
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0]["competitor_name"], "FastShip India")
        self.assertEqual(res[0]["competitor_price"], 1150.0)
        self.assertEqual(res[0]["rating"], 4.5)

    def test_prices_api_service_credits_exhausted(self):
        from services.prices_api_service import PricesAPIService
        from unittest.mock import patch, MagicMock
        service = PricesAPIService()
        service.api_key = "mock_key"
        
        mock_resp = MagicMock()
        mock_resp.status_code = 403
        mock_resp.json.return_value = {"error": {"code": "CREDITS_EXCEEDED", "message": "out of credits"}}
        
        with patch("requests.get", return_value=mock_resp):
            res = service.search_product("Mechanical Keyboard", "temp_p")
            self.assertEqual(res, [])
            self.assertEqual(service.last_api_status, "QUOTA EXCEEDED")

    def test_prices_api_fallback_to_openweb(self):
        from services.prices_api_service import PricesAPIService
        from services.openweb_ninja_service import OpenWebNinjaService
        from main import Product, CompetitorPrice, CompetitorPriceHistory
        from unittest.mock import patch
        import os
        
        p = Product(id="temp_fallback_p", name="Fallback Product", current_price=100.0, monitoring_priority="MEDIUM")
        self.db.add(p)
        self.db.commit()
        
        try:
            orig_getenv = os.getenv
            def mock_getenv(key, default=None):
                if key in ["PRICES_API_KEY", "OPENWEB_NINJA_API_KEY", "OPENWEBNINJA_API_KEY"]:
                    return "mock_key"
                return orig_getenv(key, default)
                
            def mock_prices_fail(self_instance, q, pid):
                self_instance.last_api_status = "QUOTA EXCEEDED"
                return []
                
            def mock_openweb_success(self_instance, q, pid):
                return [{
                    "product_id": pid,
                    "competitor_name": "OpenWebSeller",
                    "competitor_product_name": "Fallback Product Spec",
                    "competitor_url": "https://openweb.com/offer",
                    "competitor_price": 95.0,
                    "currency": "INR",
                    "availability": "In Stock",
                    "rating": 4.0,
                    "review_count": 10,
                    "data_source": "openwebninja"
                }]
                
            with patch("os.getenv", side_effect=mock_getenv):
                with patch.object(PricesAPIService, "search_product", mock_prices_fail):
                    with patch.object(OpenWebNinjaService, "search_product", mock_openweb_success):
                        res = self.service.run_monitoring_cycle(self.db, product_id="temp_fallback_p")
                        self.assertEqual(res["fallback_used"], True)
                        self.assertEqual(res["source"], "openwebninja")
                        
                        rec = self.db.query(CompetitorPrice).filter(CompetitorPrice.product_id == "temp_fallback_p").first()
                        self.assertIsNotNone(rec)
                        self.assertEqual(rec.competitor_name, "OpenWebSeller")
                        self.assertEqual(rec.competitor_price, 95.0)
                        self.assertEqual(rec.data_source, "openwebninja")
        finally:
            self.db.query(CompetitorAlert).filter(CompetitorAlert.product_id == "temp_fallback_p").delete()
            self.db.query(CompetitorPrice).filter(CompetitorPrice.product_id == "temp_fallback_p").delete()
            self.db.query(CompetitorPriceHistory).filter(CompetitorPriceHistory.product_id == "temp_fallback_p").delete()
            self.db.delete(p)
            self.db.commit()

    def test_both_providers_failing_preserves_records(self):
        from services.prices_api_service import PricesAPIService
        from services.openweb_ninja_service import OpenWebNinjaService
        from main import Product, CompetitorPrice, CompetitorPriceHistory
        from unittest.mock import patch
        import os
        
        p = Product(id="temp_both_fail_p", name="Both Fail Product", current_price=100.0, monitoring_priority="MEDIUM")
        self.db.add(p)
        self.db.commit()
        
        price = CompetitorPrice(product_id="temp_both_fail_p", competitor_name="PreservedComp", competitor_product_name="Preserved SKU", competitor_price=85.0, currency="INR")
        self.db.add(price)
        self.db.commit()
        
        try:
            orig_getenv = os.getenv
            def mock_getenv(key, default=None):
                if key in ["PRICES_API_KEY", "OPENWEB_NINJA_API_KEY", "OPENWEBNINJA_API_KEY"]:
                    return "mock_key"
                return orig_getenv(key, default)
                
            def mock_prices_fail(self_instance, q, pid):
                self_instance.last_api_status = "API ERROR: Timeout"
                return []
                
            def mock_openweb_fail(self_instance, q, pid):
                self_instance.last_api_status = "API RATE LIMITED"
                return []
                
            with patch("os.getenv", side_effect=mock_getenv):
                with patch.object(PricesAPIService, "search_product", mock_prices_fail):
                    with patch.object(OpenWebNinjaService, "search_product", mock_openweb_fail):
                        res = self.service.run_monitoring_cycle(self.db, product_id="temp_both_fail_p")
                        self.assertEqual(res["status"], "failed")
                        
                        rec = self.db.query(CompetitorPrice).filter(CompetitorPrice.product_id == "temp_both_fail_p").first()
                        self.assertIsNotNone(rec)
                        self.assertEqual(rec.competitor_name, "PreservedComp")
                        self.assertEqual(rec.competitor_price, 85.0)
                        
                        mock_names = ["TechMart", "CompTech", "ApexMarket", "FailingComp"]
                        mock_count = self.db.query(CompetitorPrice).filter(
                            CompetitorPrice.product_id == "temp_both_fail_p",
                            CompetitorPrice.competitor_name.in_(mock_names)
                        ).count()
                        self.assertEqual(mock_count, 0)
        finally:
            self.db.query(CompetitorAlert).filter(CompetitorAlert.product_id == "temp_both_fail_p").delete()
            self.db.query(CompetitorPrice).filter(CompetitorPrice.product_id == "temp_both_fail_p").delete()
            self.db.query(CompetitorPriceHistory).filter(CompetitorPriceHistory.product_id == "temp_both_fail_p").delete()
            self.db.delete(p)
            self.db.commit()

if __name__ == "__main__":
    unittest.main()
