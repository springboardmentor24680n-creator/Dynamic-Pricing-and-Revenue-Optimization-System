import os
import sys
import logging
import threading
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import List, Dict, Any, Optional

# Ensure the backend directory is in the system path to allow absolute imports
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.append(str(BASE_DIR))

logger = logging.getLogger("services.competitor_monitoring_service")

_monitoring_lock = threading.Lock()

_last_run_time: Optional[datetime] = None
_last_data_source: str = "mock_fallback"
_last_successful_api_call: Optional[datetime] = None
_api_status: str = "Not Configured"
_last_competitors_found: int = 0
_last_products_checked: int = 0
_last_alerts_generated: int = 0

def get_last_run_time() -> Optional[datetime]:
    global _last_run_time
    return _last_run_time

def get_last_data_source() -> str:
    global _last_data_source
    return _last_data_source

def get_last_successful_api_call() -> Optional[datetime]:
    global _last_successful_api_call
    return _last_successful_api_call

def get_api_status() -> str:
    global _api_status
    return _api_status

def get_last_competitors_found() -> int:
    global _last_competitors_found
    return _last_competitors_found

def get_last_products_checked() -> int:
    global _last_products_checked
    return _last_products_checked

def get_last_alerts_generated() -> int:
    global _last_alerts_generated
    return _last_alerts_generated

class CompetitorMonitoringService:
    """
    A service handling Phase 1 of Competitor Monitoring.
    This includes price validation, change and percentage calculations, trend classification,
    seeding and retrieving mock competitor price updates, saving latest prices, and saving history records.
    """

    def validate_price(self, price: Any) -> float:
        """
        Validates if the competitor price is non-null, numeric, and non-negative.
        Raises ValueError if validation fails.
        """
        if price is None:
            raise ValueError("Competitor price cannot be None.")
        
        # Check type
        if not isinstance(price, (int, float)):
            try:
                price = float(price)
            except (ValueError, TypeError):
                raise ValueError("Competitor price must be a valid numeric value.")
        
        if price < 0:
            raise ValueError("Competitor price cannot be negative.")
            
        return float(price)

    def calculate_price_change(self, current_price: float, previous_price: Optional[float]) -> Dict[str, float]:
        """
        Calculates the absolute price change and percentage price change.
        """
        # Validate current price
        current_price = self.validate_price(current_price)

        if previous_price is None or previous_price <= 0:
            return {
                "price_change": 0.0,
                "price_change_percent": 0.0
            }
        
        previous_price = self.validate_price(previous_price)
        
        price_change = current_price - previous_price
        price_change_percent = (price_change / previous_price) * 100
        
        return {
            "price_change": round(price_change, 2),
            "price_change_percent": round(price_change_percent, 2)
        }

    def determine_trend(self, price_change: float) -> str:
        """
        Determines if the competitor price trend is increased, decreased, or stable.
        """
        if price_change > 0.0001:
            return "increased"
        elif price_change < -0.0001:
            return "decreased"
        else:
            return "stable"

    def get_mock_data(self, product_id: str, db_conn: Any) -> List[Dict[str, Any]]:
        """
        Generates controlled/mock competitor data based on the product's actual current price.
        This provides a deterministic baseline for testing and development.
        """
        from main import Product
        product = db_conn.query(Product).filter(Product.id == product_id).first()
        if not product:
            return []

        # We construct 3 competitors for each product with prices relative to product.current_price
        price = product.current_price or 100.0
        
        return [
            {
                "product_id": product_id,
                "competitor_name": "TechMart",
                "competitor_product_name": f"TechMart {product.name} Pro",
                "competitor_url": f"https://techmart.com/item/{product_id}",
                "competitor_price": round(price * 0.97, 2), # 3% cheaper
                "currency": "INR",
                "availability": "In Stock"
            },
            {
                "product_id": product_id,
                "competitor_name": "CompTech",
                "competitor_product_name": f"CompTech {product.name}",
                "competitor_url": f"https://comptech.com/shop/{product_id}",
                "competitor_price": round(price * 1.02, 2), # 2% more expensive
                "currency": "INR",
                "availability": "In Stock"
            },
            {
                "product_id": product_id,
                "competitor_name": "ApexMarket",
                "competitor_product_name": f"Apex {product.name} Prime",
                "competitor_url": f"https://apexmarket.com/p/{product_id}",
                "competitor_price": round(price * 0.94, 2), # 6% cheaper
                "currency": "INR",
                "availability": "In Stock"
            }
        ]

    def update_competitor_prices(self, db_conn: Any, product_id: Optional[str] = None) -> List[Any]:
        """
        Simulates fetching and updating competitor prices from mock data.
        Updates the latest prices, logs the history, and computes price change metrics.
        """
        from main import Product, CompetitorPrice, CompetitorPriceHistory

        if product_id:
            products = db_conn.query(Product).filter(Product.id == product_id).all()
        else:
            products = db_conn.query(Product).all()

        updated_records = []

        for product in products:
            mock_items = self.get_mock_data(product.id, db_conn)
            for item in mock_items:
                # 1. Validate price
                try:
                    price_val = self.validate_price(item["competitor_price"])
                except ValueError as e:
                    logger.error(f"Skipping update due to validation error: {e}")
                    continue

                # 2. Check for existing record
                existing = db_conn.query(CompetitorPrice).filter(
                    CompetitorPrice.product_id == product.id,
                    CompetitorPrice.competitor_name == item["competitor_name"]
                ).first()

                previous_price = None
                if existing:
                    previous_price = existing.competitor_price
                    
                    # Calculate changes
                    deltas = self.calculate_price_change(price_val, previous_price)
                    
                    existing.competitor_product_name = item["competitor_product_name"]
                    existing.competitor_url = item["competitor_url"]
                    existing.previous_price = previous_price
                    existing.competitor_price = price_val
                    existing.price_change = deltas["price_change"]
                    existing.price_change_percent = deltas["price_change_percent"]
                    existing.currency = item["currency"]
                    existing.availability = item["availability"]
                    existing.last_checked = datetime.utcnow()
                    
                    record_to_append = existing
                else:
                    # New record - deltas are 0
                    deltas = {"price_change": 0.0, "price_change_percent": 0.0}
                    new_rec = CompetitorPrice(
                        product_id=product.id,
                        competitor_name=item["competitor_name"],
                        competitor_product_name=item["competitor_product_name"],
                        competitor_url=item["competitor_url"],
                        competitor_price=price_val,
                        currency=item["currency"],
                        availability=item["availability"],
                        last_checked=datetime.utcnow(),
                        previous_price=None,
                        price_change=0.0,
                        price_change_percent=0.0
                    )
                    db_conn.add(new_rec)
                    record_to_append = new_rec

                # 3. Add to price history
                history = CompetitorPriceHistory(
                    product_id=product.id,
                    competitor_name=item["competitor_name"],
                    competitor_price=price_val,
                    currency=item["currency"],
                    last_checked=datetime.utcnow()
                )
                db_conn.add(history)
                updated_records.append(record_to_append)

        db_conn.commit()
        return updated_records

    def get_monitored_competitors(self, db_conn: Any) -> List[str]:
        """
        Retrieves a distinct list of monitored competitor names.
        """
        from main import CompetitorPrice
        results = db_conn.query(CompetitorPrice.competitor_name).distinct().all()
        return [r[0] for r in results if r[0]]

    def get_latest_prices(self, db_conn: Any, product_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Retrieves the latest competitor prices, optionally filtered by product_id.
        """
        from main import CompetitorPrice
        query = db_conn.query(CompetitorPrice)
        if product_id:
            query = query.filter(CompetitorPrice.product_id == product_id)
        
        records = query.all()
        result = []
        for rec in records:
            result.append({
                "id": rec.id,
                "product_id": rec.product_id,
                "competitor_name": rec.competitor_name,
                "competitor_product_name": rec.competitor_product_name,
                "competitor_url": rec.competitor_url,
                "competitor_url_source": rec.competitor_url,  # aliased for compatibility
                "competitor_price": rec.competitor_price,
                "currency": rec.currency,
                "availability": rec.availability,
                "last_checked": rec.last_checked.isoformat() if rec.last_checked else None,
                "previous_price": rec.previous_price,
                "price_change": rec.price_change,
                "price_change_percent": rec.price_change_percent,
                "trend": self.determine_trend(rec.price_change or 0.0)
            })
        return result

    def get_price_history(self, db_conn: Any, product_id: str) -> List[Dict[str, Any]]:
        """
        Retrieves the full price history for a given product ID.
        """
        from main import CompetitorPriceHistory
        records = db_conn.query(CompetitorPriceHistory).filter(
            CompetitorPriceHistory.product_id == product_id
        ).order_by(CompetitorPriceHistory.last_checked.asc()).all()

        result = []
        for rec in records:
            result.append({
                "id": rec.id,
                "product_id": rec.product_id,
                "competitor_name": rec.competitor_name,
                "competitor_price": rec.competitor_price,
                "currency": rec.currency,
                "last_checked": rec.last_checked.isoformat() if rec.last_checked else None
            })
        return result

    def get_comparison_data(self, db_conn: Any, product_id: str) -> Dict[str, Any]:
        """
        Retrieves comparison data comparing the system product price against competitors.
        """
        from main import Product
        product = db_conn.query(Product).filter(Product.id == product_id).first()
        if not product:
            raise ValueError(f"Product with ID {product_id} not found.")

        competitors = self.get_latest_prices(db_conn, product_id=product_id)
        
        comparison_list = []
        for comp in competitors:
            diff = product.current_price - comp["competitor_price"]
            diff_percent = (diff / comp["competitor_price"] * 100) if comp["competitor_price"] > 0 else 0.0
            comparison_list.append({
                "competitor_name": comp["competitor_name"],
                "competitor_product_name": comp["competitor_product_name"],
                "competitor_price": comp["competitor_price"],
                "our_price": product.current_price,
                "price_difference": round(diff, 2),
                "price_difference_percent": round(diff_percent, 2),
                "position": "premium" if diff > 0.01 else ("discount" if diff < -0.01 else "parity")
            })

        return {
            "product_id": product.id,
            "product_name": product.name,
                "currency": "INR",  # fallback standard currency
                "competitors": comparison_list
            }

    def get_due_products(self, db_conn: Any, max_limit: int = 5) -> List[Any]:
        """
        Retrieves products due for a competitor price scan.
        Filters by next_competitor_scan <= current time or next_competitor_scan is None.
        Sorts priority order: HIGH first, then MEDIUM, then LOW.
        Limits the output to max_limit.
        """
        from main import Product
        from datetime import datetime
        from sqlalchemy import case
        
        now = datetime.utcnow()
        due_products = db_conn.query(Product).filter(
            (Product.next_competitor_scan.is_(None)) | (Product.next_competitor_scan <= now)
        ).order_by(
            case(
                (Product.monitoring_priority == "HIGH", 0),
                (Product.monitoring_priority == "MEDIUM", 1),
                else_=2
            ),
            Product.next_competitor_scan.asc()
        ).limit(max_limit).all()
        return due_products

    def get_api_usage_stats(self, db_conn: Any) -> Dict[str, Any]:
        """
        Queries monitoring_runs to compute monthly and daily API requests usage for both providers.
        """
        from main import CompetitorMonitoringRun
        from datetime import datetime
        from sqlalchemy import func
        
        now = datetime.utcnow()
        today_start = datetime(now.year, now.month, now.day)
        month_start = datetime(now.year, now.month, 1)
        
        # 1. PricesAPI Limits & Usage
        try:
            prices_limit = int(os.getenv("PRICES_API_MONTHLY_LIMIT", "1000"))
        except ValueError:
            prices_limit = 1000

        prices_used_month = db_conn.query(func.sum(CompetitorMonitoringRun.prices_api_requests)).filter(
            CompetitorMonitoringRun.started_at >= month_start
        ).scalar() or 0
        
        prices_used_today = db_conn.query(func.sum(CompetitorMonitoringRun.prices_api_requests)).filter(
            CompetitorMonitoringRun.started_at >= today_start
        ).scalar() or 0

        prices_remaining = max(0, prices_limit - prices_used_month)
        prices_status = "exhausted" if prices_used_month >= prices_limit else "active"

        # 2. OpenWeb Ninja Limits & Usage
        try:
            openweb_limit = int(os.getenv("OPENWEB_NINJA_MONTHLY_LIMIT", "100"))
        except ValueError:
            openweb_limit = 100

        # Legacy fallback query: if old runs didn't record openweb_ninja_requests but recorded api_requests, we check that too!
        openweb_used_month = db_conn.query(func.sum(
            func.coalesce(CompetitorMonitoringRun.openweb_ninja_requests, CompetitorMonitoringRun.api_requests)
        )).filter(
            CompetitorMonitoringRun.started_at >= month_start
        ).scalar() or 0

        openweb_used_today = db_conn.query(func.sum(
            func.coalesce(CompetitorMonitoringRun.openweb_ninja_requests, CompetitorMonitoringRun.api_requests)
        )).filter(
            CompetitorMonitoringRun.started_at >= today_start
        ).scalar() or 0

        openweb_remaining = max(0, openweb_limit - openweb_used_month)
        openweb_status = "exhausted" if openweb_used_month >= openweb_limit else "active"

        import calendar
        day_of_month = now.day
        _, total_days = calendar.monthrange(now.year, now.month)
        if day_of_month > 0:
            estimated_prices = round((prices_used_month / day_of_month) * total_days, 1)
            estimated_openweb = round((openweb_used_month / day_of_month) * total_days, 1)
        else:
            estimated_prices = 0.0
            estimated_openweb = 0.0

        return {
            "monthly_limit": prices_limit,
            "requests_used_today": prices_used_today,
            "requests_used_this_month": prices_used_month,
            "requests_remaining": prices_remaining,
            "estimated_monthly_usage": estimated_prices,
            "budget_status": prices_status,
            
            # OpenWeb Ninja stats for backend/router
            "openweb_limit": openweb_limit,
            "openweb_used_today": openweb_used_today,
            "openweb_used_this_month": openweb_used_month,
            "openweb_remaining": openweb_remaining,
            "openweb_estimated_monthly": estimated_openweb,
            "openweb_status": openweb_status
        }

    def run_monitoring_cycle(self, db_conn: Any, product_id: Optional[str] = None, force_all: bool = True) -> Dict[str, Any]:
        """
        Wrapper to ensure lock is acquired and released.
        """
        if not _monitoring_lock.acquire(blocking=False):
            logger.warning("Competitor monitoring cycle is already running. Skipping duplicate concurrent run.")
            return {
                "status": "already_running",
                "fallback_used": False,
                "competitors_checked": 0,
                "price_changes_detected": 0,
                "alerts_generated": 0,
                "source": "already_running",
                "products_checked": 0,
                "raw_products": 0,
                "normalized_products": 0,
                "relevant_competitors": 0,
                "competitors_found": 0,
                "price_updates": 0,
                "alerts_created": 0
            }
        try:
            return self._run_monitoring_cycle_locked(db_conn, product_id, force_all)
        finally:
            _monitoring_lock.release()

    def _run_monitoring_cycle_locked(self, db_conn: Any, product_id: Optional[str] = None, force_all: bool = True) -> Dict[str, Any]:
        """
        Executes the periodic or manual competitor price monitoring cycle (Phase 2 & 3 & 5 & PricesAPI).
        """
        logger.info("Competitor monitoring started")
        
        from services.prices_api_service import PricesAPIService
        from services.openweb_ninja_service import OpenWebNinjaService
        
        prices_service = PricesAPIService()
        openweb_service = OpenWebNinjaService()
        
        from main import Product, CompetitorPrice, CompetitorPriceHistory, CompetitorAlert, CompetitorMonitoringRun
        
        source_label = "pricesapi" if prices_service.api_key else ("openwebninja" if openweb_service.api_key else "mock_fallback")
        
        # 1. Initialize Run Log
        run_log = CompetitorMonitoringRun(
            started_at=datetime.utcnow(),
            status="running",
            source=source_label,
            primary_provider="pricesapi" if prices_service.api_key else None,
            successful_provider=None,
            prices_api_requests=0,
            openweb_ninja_requests=0
        )
        db_conn.add(run_log)
        db_conn.commit()

        # 2. Check Request Budget
        usage = self.get_api_usage_stats(db_conn)
        prices_exhausted = (prices_service.api_key and usage.get("budget_status") == "exhausted")
        openweb_exhausted = (openweb_service.api_key and (usage.get("openweb_status") == "exhausted" or usage.get("budget_status") == "exhausted"))

        has_active_provider = False
        if prices_service.api_key and not prices_exhausted:
            has_active_provider = True
        elif openweb_service.api_key and not openweb_exhausted:
            has_active_provider = True
        elif not prices_service.api_key and not openweb_service.api_key:
            # Fall back to simulation only when both keys are empty/missing
            has_active_provider = True

        if not has_active_provider:
            logger.warning("Monitoring halted: All configured live API request budgets are exhausted.")
            run_log.completed_at = datetime.utcnow()
            run_log.status = "budget_exhausted"
            db_conn.commit()
            return {
                "status": "budget_exhausted",
                "fallback_used": False,
                "competitors_checked": 0,
                "price_changes_detected": 0,
                "alerts_generated": 0,
                "source": source_label,
                "products_checked": 0,
                "raw_products": 0,
                "normalized_products": 0,
                "relevant_competitors": 0,
                "competitors_found": 0,
                "price_updates": 0,
                "alerts_created": 0
            }

        try:
            price_change_alert_pct = float(os.getenv("COMPETITOR_PRICE_CHANGE_ALERT_PERCENT", "3.0"))
        except ValueError:
            price_change_alert_pct = 3.0

        try:
            undercut_alert_pct = float(os.getenv("COMPETITOR_UNDERCUT_ALERT_PERCENT", "2.0"))
        except ValueError:
            undercut_alert_pct = 2.0

        try:
            min_refresh_min = int(os.getenv("COMPETITOR_MIN_REFRESH_MINUTES", "15"))
        except ValueError:
            min_refresh_min = 15

        # 3. Select products to scan
        if product_id:
            products = db_conn.query(Product).filter(Product.id == product_id).all()
        elif force_all:
            products = db_conn.query(Product).all()
        else:
            try:
                max_run_requests = int(os.getenv("COMPETITOR_MAX_REQUESTS_PER_RUN", "5"))
            except ValueError:
                max_run_requests = 5
            products = self.get_due_products(db_conn, max_limit=max_run_requests)

        if not products:
            logger.info("No products are currently due for scanning.")
            run_log.completed_at = datetime.utcnow()
            run_log.status = "success"
            db_conn.commit()
            return {
                "competitors_checked": 0,
                "price_changes_detected": 0,
                "alerts_generated": 0,
                "source": source_label,
                "products_checked": 0,
                "raw_products": 0,
                "normalized_products": 0,
                "relevant_competitors": 0,
                "competitors_found": 0,
                "price_updates": 0,
                "alerts_created": 0,
                "fallback_used": False
            }

        checked_count = 0
        changes_detected = 0
        alerts_generated = 0
        prices_api_requests_count = 0
        openweb_ninja_requests_count = 0
        cycle_sources = set()
        
        total_raw_products = 0
        total_normalized_products = 0
        total_relevant_competitors = 0
        global _last_successful_api_call, _api_status
        api_results_count = 0

        try:
            prices_api_max_requests = int(os.getenv("PRICES_API_MAX_REQUESTS_PER_RUN", "5"))
        except ValueError:
            prices_api_max_requests = 5

        try:
            openweb_max_requests = int(os.getenv("COMPETITOR_MAX_REQUESTS_PER_RUN", "5"))
        except ValueError:
            openweb_max_requests = 5

        product_results = {}
        for product in products:
            items_to_process = []
            product_successful_provider = None
            
            # Caching check
            cached_records = db_conn.query(CompetitorPrice).filter(
                CompetitorPrice.product_id == product.id
            ).all()
            
            use_cached = False
            if cached_records and os.getenv("TESTING") != "true":
                newest_check = max((cr.last_checked for cr in cached_records if cr.last_checked), default=None)
                if newest_check and (datetime.utcnow() - newest_check).total_seconds() / 60 < min_refresh_min:
                    if any(cr.data_source in ["pricesapi", "openwebninja"] for cr in cached_records):
                        use_cached = True
                        
            if use_cached:
                logger.info(f"Reusing cached live data for product {product.id} within {min_refresh_min} min limit.")
                cached_source = "pricesapi"
                for cr in cached_records:
                    if cr.data_source in ["pricesapi", "openwebninja"]:
                        cached_source = cr.data_source
                        items_to_process.append({
                            "product_id": cr.product_id,
                            "competitor_name": cr.competitor_name,
                            "competitor_product_name": cr.competitor_product_name,
                            "competitor_url": cr.competitor_url,
                            "competitor_price": cr.competitor_price,
                            "currency": cr.currency,
                            "availability": cr.availability,
                            "rating": cr.rating,
                            "review_count": cr.review_count,
                            "data_source": cr.data_source
                        })
                total_raw_products += len(items_to_process)
                total_normalized_products += len(items_to_process)
                total_relevant_competitors += len(items_to_process)
                api_results_count += len(items_to_process)
                product_successful_provider = cached_source
            else:
                # 1. Try PricesAPI as the primary provider
                tried_prices = False
                if prices_service.api_key and not prices_exhausted:
                    if prices_api_requests_count < prices_api_max_requests:
                        tried_prices = True
                        logger.info(f"Triggering PricesAPI search: query='{product.name}'")
                        items_to_process = prices_service.search_product(product.name, product.id)
                        prices_api_requests_count += 1
                        
                        total_raw_products += getattr(prices_service, "last_raw_count", 0)
                        total_normalized_products += getattr(prices_service, "last_normalized_count", 0)
                        total_relevant_competitors += getattr(prices_service, "last_relevant_count", 0)
                        
                        if items_to_process:
                            product_successful_provider = "pricesapi"
                            api_results_count += len(items_to_process)
                            _last_successful_api_call = datetime.utcnow()
                            _api_status = getattr(prices_service, "last_api_status", "Success")
                        else:
                            _api_status = getattr(prices_service, "last_api_status", "Success")
                            logger.warning(f"PricesAPI returned no results or failed for product {product.id}. Status: {_api_status}")

                # 2. Try OpenWeb Ninja as the secondary backup provider
                if not product_successful_provider:
                    if openweb_service.api_key and not openweb_exhausted:
                        if openweb_ninja_requests_count < openweb_max_requests:
                            if tried_prices:
                                logger.info(f"PricesAPI unavailable -> Checking OpenWeb Ninja...")
                            
                            logger.info(f"Triggering OpenWeb Ninja search: query='{product.name}'")
                            items_to_process = openweb_service.search_product(product.name, product.id)
                            openweb_ninja_requests_count += 1
                            
                            total_raw_products += getattr(openweb_service, "last_raw_count", 0)
                            total_normalized_products += getattr(openweb_service, "last_normalized_count", 0)
                            total_relevant_competitors += getattr(openweb_service, "last_relevant_count", 0)
                            
                            if items_to_process:
                                product_successful_provider = "openwebninja"
                                api_results_count += len(items_to_process)
                                _last_successful_api_call = datetime.utcnow()
                                _api_status = getattr(openweb_service, "last_api_status", "Success")
                            else:
                                _api_status = getattr(openweb_service, "last_api_status", "Success")
                                logger.warning(f"OpenWeb Ninja returned no results or failed for product {product.id}. Status: {_api_status}")

            product_results[product.id] = (items_to_process, product_successful_provider)

        use_live_api = (api_results_count > 0)
        any_key_configured = bool(prices_service.api_key) or bool(openweb_service.api_key)

        # If live monitoring is configured, but failed to return any results
        if any_key_configured and api_results_count == 0:
            if os.getenv("TESTING") == "true":
                logger.error("Live monitoring failed. Keeping existing records (testing mode).")
                run_log.completed_at = datetime.utcnow()
                run_log.status = "failed"
                last_err = getattr(prices_service, "last_api_status", "Success")
                if last_err in ["Success", "Not Configured"] and openweb_service.api_key:
                    last_err = getattr(openweb_service, "last_api_status", "Success")
                run_log.error_message = last_err
                run_log.prices_api_requests = prices_api_requests_count
                run_log.openweb_ninja_requests = openweb_ninja_requests_count
                db_conn.commit()
                return {
                    "competitors_checked": 0,
                    "price_changes_detected": 0,
                    "alerts_generated": 0,
                    "source": source_label,
                    "products_checked": len(products),
                    "raw_products": total_raw_products,
                    "normalized_products": total_normalized_products,
                    "relevant_competitors": total_relevant_competitors,
                    "competitors_found": 0,
                    "price_updates": 0,
                    "alerts_created": 0,
                    "fallback_used": False,
                    "status": "failed",
                    "api_status": last_err
                }
            else:
                logger.warning("Live monitoring failed to return any results. Falling back to simulation/fallback.")
                use_live_api = False

        # Purge old mock data if live sync succeeds
        if use_live_api:
            mock_names = ["TechMart", "CompTech", "ApexMarket", "FailingComp"]
            db_conn.query(CompetitorPrice).filter(
                (CompetitorPrice.data_source == "mock_fallback") | 
                (CompetitorPrice.competitor_name.in_(mock_names))
            ).delete(synchronize_session=False)

            db_conn.query(CompetitorPriceHistory).filter(
                (CompetitorPriceHistory.data_source == "mock_fallback") |
                (CompetitorPriceHistory.competitor_name.in_(mock_names))
            ).delete(synchronize_session=False)

            db_conn.query(CompetitorAlert).filter(
                (CompetitorAlert.data_source == "mock_fallback") |
                (CompetitorAlert.competitor_name.in_(mock_names))
            ).delete(synchronize_session=False)
            db_conn.commit()

        for product in products:
            items_to_process, product_successful_provider = product_results.get(product.id, ([], None))
            
            if not use_live_api:
                # No keys configured: legacy mock fallback runs
                items_to_process = []
                logger.info(f"Using mock competitor fallback data for product {product.id}")
                mock_items = self.get_mock_data(product.id, db_conn)
                for item in mock_items:
                    items_to_process.append({
                        **item,
                        "data_source": "mock_fallback"
                    })
                total_raw_products += len(mock_items)
                total_normalized_products += len(mock_items)
                total_relevant_competitors += len(mock_items)
                product_successful_provider = "mock_fallback"

            for item in items_to_process:
                checked_count += 1
                cycle_sources.add(item.get("data_source", "mock_fallback"))
                
                try:
                    price_val = self.validate_price(item["competitor_price"])
                    competitor_name = item["competitor_name"]
                    our_price = product.current_price or 100.0

                    existing = db_conn.query(CompetitorPrice).filter(
                        CompetitorPrice.product_id == product.id,
                        CompetitorPrice.competitor_name == competitor_name
                    ).first()

                    event_type = None
                    severity = "low"
                    message = ""
                    price_change = 0.0
                    price_change_percent = 0.0

                    if existing:
                        previous_price = existing.competitor_price
                        deltas = self.calculate_price_change(price_val, previous_price)
                        price_change = deltas["price_change"]
                        price_change_percent = deltas["price_change_percent"]
                        
                        existing.competitor_product_name = item["competitor_product_name"]
                        existing.competitor_url = item["competitor_url"]
                        existing.previous_price = previous_price
                        existing.competitor_price = price_val
                        existing.price_change = price_change
                        existing.price_change_percent = price_change_percent
                        existing.currency = item["currency"]
                        existing.availability = item["availability"]
                        existing.last_checked = datetime.utcnow()
                        existing.rating = item.get("rating")
                        existing.review_count = item.get("review_count")
                        existing.relevance_score = item.get("relevance_score")
                        existing.data_source = item.get("data_source", "mock_fallback")
                    else:
                        previous_price = None
                        new_rec = CompetitorPrice(
                            product_id=product.id,
                            competitor_name=competitor_name,
                            competitor_product_name=item["competitor_product_name"],
                            competitor_url=item["competitor_url"],
                            competitor_price=price_val,
                            currency=item["currency"],
                            availability=item["availability"],
                            last_checked=datetime.utcnow(),
                            previous_price=None,
                            price_change=0.0,
                            price_change_percent=0.0,
                            data_source=item.get("data_source", "mock_fallback"),
                            rating=item.get("rating"),
                            review_count=item.get("review_count"),
                            relevance_score=item.get("relevance_score")
                        )
                        db_conn.add(new_rec)

                    history = CompetitorPriceHistory(
                        product_id=product.id,
                        competitor_name=competitor_name,
                        competitor_price=price_val,
                        currency=item["currency"],
                        last_checked=datetime.utcnow(),
                        data_source=item.get("data_source", "mock_fallback"),
                        rating=item.get("rating"),
                        review_count=item.get("review_count"),
                        relevance_score=item.get("relevance_score")
                    )
                    db_conn.add(history)

                    # Price Change Alert Classification
                    is_mock = item.get("data_source", "mock_fallback") == "mock_fallback"
                    if is_mock:
                        if previous_price is not None:
                            if price_change > 0.0001:
                                trend = "increased"
                            elif price_change < -0.0001:
                                trend = "decreased"
                            else:
                                trend = "unchanged"

                            if trend != "unchanged":
                                changes_detected += 1
                                try:
                                    mock_threshold = float(os.getenv("COMPETITOR_PRICE_ALERT_THRESHOLD_PERCENT", "5.0"))
                                except ValueError:
                                    mock_threshold = 5.0
                                is_significant = abs(price_change_percent) >= mock_threshold
                                if is_significant:
                                    event_type = "SIGNIFICANT_PRICE_CHANGE"
                                    severity = "high"
                                    message = f"Significant competitor price change for {product.name} ({competitor_name}): {previous_price} -> {price_val} ({price_change_percent:+.2f}%)"
                                elif trend == "increased":
                                    event_type = "PRICE_INCREASE"
                                    severity = "low"
                                    message = f"Competitor price increased for {product.name} ({competitor_name}): {previous_price} -> {price_val} ({price_change_percent:+.2f}%)"
                                else:
                                    event_type = "PRICE_DECREASE"
                                    severity = "low"
                                    message = f"Competitor price decreased for {product.name} ({competitor_name}): {previous_price} -> {price_val} ({price_change_percent:+.2f}%)"
                    else:
                        # Real Live API Alerts
                        if previous_price is None:
                            event_type = "NEW_COMPETITOR"
                            severity = "low"
                            message = f"New competitor {competitor_name} for product {product.name}: {item['currency']} {price_val}"
                        else:
                            was_undercut = (previous_price < our_price) and ((our_price - previous_price) / our_price >= undercut_alert_pct / 100)
                            is_undercut = (price_val < our_price) and ((our_price - price_val) / our_price >= undercut_alert_pct / 100)
                            
                            if is_undercut and not was_undercut:
                                event_type = "COMPETITOR_UNDERCUT"
                                severity = "high"
                                message = f"Competitor {competitor_name} is undercutting product {product.name}: {item['currency']} {price_val} vs our {our_price} (undercutting by {((our_price - price_val) / our_price * 100):.1f}%)"
                            elif not is_undercut and was_undercut and price_val >= our_price:
                                event_type = "COMPETITOR_BACK_ABOVE"
                                severity = "medium"
                                message = f"Competitor {competitor_name} price is back above our price for product {product.name}: {item['currency']} {price_val} vs our {our_price}"
                            elif abs(price_change_percent) >= price_change_alert_pct:
                                changes_detected += 1
                                if price_change_percent > 0:
                                    event_type = "PRICE_INCREASE"
                                    severity = "low"
                                    message = f"Competitor price increased for {product.name} ({competitor_name}): {previous_price} -> {price_val} ({price_change_percent:+.2f}%)"
                                else:
                                    event_type = "PRICE_DECREASE"
                                    severity = "low"
                                    message = f"Competitor price decreased for {product.name} ({competitor_name}): {previous_price} -> {price_val} ({price_change_percent:+.2f}%)"

                    if event_type:
                        # Alert Deduplication
                        duplicate = db_conn.query(CompetitorAlert).filter(
                            CompetitorAlert.product_id == product.id,
                            CompetitorAlert.competitor_name == competitor_name,
                            CompetitorAlert.event_type == event_type,
                            CompetitorAlert.current_price == price_val
                        ).first()
                        
                        if not duplicate:
                            alert = CompetitorAlert(
                                product_id=product.id,
                                competitor_name=competitor_name,
                                event_type=event_type,
                                previous_price=previous_price,
                                current_price=price_val,
                                change_amount=price_change if previous_price else 0.0,
                                change_percent=price_change_percent if previous_price else 0.0,
                                severity=severity,
                                message=message,
                                created_at=datetime.utcnow(),
                                is_acknowledged=False,
                                data_source=item.get("data_source", "mock_fallback")
                            )
                            db_conn.add(alert)
                            alerts_generated += 1

                    if item.get("availability") == "Out of Stock":
                        dup_out = db_conn.query(CompetitorAlert).filter(
                            CompetitorAlert.product_id == product.id,
                            CompetitorAlert.competitor_name == competitor_name,
                            CompetitorAlert.event_type == "COMPETITOR_OUT_OF_STOCK"
                        ).first()
                        if not dup_out:
                            alert = CompetitorAlert(
                                product_id=product.id,
                                competitor_name=competitor_name,
                                event_type="COMPETITOR_OUT_OF_STOCK",
                                previous_price=previous_price,
                                current_price=price_val,
                                change_amount=price_change,
                                change_percent=price_change_percent,
                                severity="medium",
                                message=f"Competitor {competitor_name} is Out of Stock for product {product.name}",
                                created_at=datetime.utcnow(),
                                is_acknowledged=False,
                                data_source=item.get("data_source", "mock_fallback")
                            )
                            db_conn.add(alert)
                            alerts_generated += 1

                except Exception as e:
                    logger.error(f"Error processing competitor {item.get('competitor_name')} for product {product.id}: {e}")
                    continue

            # Disappeared Competitor Check (Only for live API monitoring)
            if use_live_api and product_successful_provider in ["pricesapi", "openwebninja"]:
                current_competitor_names = {item["competitor_name"] for item in items_to_process}
                previous_prices = db_conn.query(CompetitorPrice).filter(CompetitorPrice.product_id == product.id).all()
                for prev_rec in previous_prices:
                    if prev_rec.competitor_name not in current_competitor_names:
                        dup_disappeared = db_conn.query(CompetitorAlert).filter(
                            CompetitorAlert.product_id == product.id,
                            CompetitorAlert.competitor_name == prev_rec.competitor_name,
                            CompetitorAlert.event_type == "COMPETITOR_DISAPPEARED"
                        ).first()
                        
                        if not dup_disappeared:
                            disappeared_alert = CompetitorAlert(
                                product_id=product.id,
                                competitor_name=prev_rec.competitor_name,
                                event_type="COMPETITOR_DISAPPEARED",
                                previous_price=prev_rec.competitor_price,
                                current_price=prev_rec.competitor_price,
                                change_amount=0.0,
                                change_percent=0.0,
                                severity="medium",
                                message=f"Competitor {prev_rec.competitor_name} has disappeared from listings for product {product.name}",
                                created_at=datetime.utcnow(),
                                is_acknowledged=False,
                                data_source=prev_rec.data_source or "mock_fallback"
                            )
                            db_conn.add(disappeared_alert)
                            alerts_generated += 1
                            
                        db_conn.delete(prev_rec)

            # Update scan tracking times on product row
            try:
                interval_hours = int(os.getenv("COMPETITOR_SCAN_INTERVAL_HOURS", "6"))
            except ValueError:
                interval_hours = 6
                
            priority = str(product.monitoring_priority).upper()
            if priority == "HIGH":
                multiplier = 1
            elif priority == "LOW":
                multiplier = 4
            else:
                multiplier = 2
                
            product.last_competitor_scan = datetime.utcnow()
            product.next_competitor_scan = datetime.utcnow() + timedelta(hours=interval_hours * multiplier)

        db_conn.commit()

        # Update last run parameters
        global _last_run_time, _last_data_source, _last_competitors_found, _last_products_checked, _last_alerts_generated
        _last_run_time = datetime.utcnow()
        _last_products_checked = len(products)
        _last_competitors_found = checked_count
        _last_alerts_generated = alerts_generated

        if "pricesapi" in cycle_sources:
            _last_data_source = "pricesapi"
        elif "openwebninja" in cycle_sources:
            _last_data_source = "openwebninja"
        else:
            _last_data_source = "mock_fallback"

        logger.info(f"Competitors checked: {checked_count}")
        logger.info(f"Price changes detected: {changes_detected}")
        logger.info(f"Alerts generated: {alerts_generated}")
        logger.info("Monitoring completed")

        # Complete Run Log
        run_log.completed_at = datetime.utcnow()
        run_log.status = "success"
        run_log.products_checked = len(products)
        run_log.raw_products = total_raw_products
        run_log.normalized_products = total_normalized_products
        run_log.relevant_competitors = total_relevant_competitors
        run_log.price_updates = changes_detected
        run_log.alerts_created = alerts_generated
        run_log.prices_api_requests = prices_api_requests_count
        run_log.openweb_ninja_requests = openweb_ninja_requests_count
        run_log.api_requests = prices_api_requests_count + openweb_ninja_requests_count
        run_log.fallback_used = (_last_data_source in ["openwebninja", "mock_fallback"])
        run_log.successful_provider = _last_data_source
        db_conn.commit()

        return {
            "competitors_checked": checked_count,
            "price_changes_detected": changes_detected,
            "alerts_generated": alerts_generated,
            "source": _last_data_source,
            "products_checked": len(products),
            "raw_products": total_raw_products,
            "normalized_products": total_normalized_products,
            "relevant_competitors": total_relevant_competitors,
            "competitors_found": checked_count,
            "price_updates": changes_detected,
            "alerts_created": alerts_generated,
            "fallback_used": (_last_data_source in ["openwebninja", "mock_fallback"])
        }
