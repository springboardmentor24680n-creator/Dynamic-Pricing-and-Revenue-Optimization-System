import os
import logging
import requests
import difflib
import time
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# Load env variables relative to backend directory
BACKEND_DIR = Path(__file__).resolve().parent.parent
load_dotenv(dotenv_path=BACKEND_DIR / ".env")

class PricesAPIService:
    def __init__(self):
        self.api_key = os.getenv("PRICES_API_KEY", "").strip()
        self.endpoint = "https://api.pricesapi.io/api/v1/products/search"
        self.timeout = (3.0, 12.0)  # Strict timeout: 3s connect, 12s read

    def search_product(self, product_name: str, product_id: str) -> List[Dict[str, Any]]:
        """
        Queries PricesAPI search API for the given product name, handles retries,
        normalizes returned offers, and filters them based on similarity matching.
        """
        self.last_raw_count = 0
        self.last_normalized_count = 0
        self.last_relevant_count = 0
        self.last_api_status = "Success"

        if not self.api_key:
            logger.warning("PricesAPI API Key is missing. Skipping primary competitor search.")
            self.last_api_status = "Not Configured"
            return []

        logger.info(f"PricesAPI: Searching for product ID '{product_id}' using query: '{product_name}'")

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Accept": "application/json"
        }
        params = {
            "q": product_name,
            "country": "IN",
            "limit": 5,
            "offers_limit": 10
        }

        max_attempts = 2
        attempt = 0
        response = None

        while attempt < max_attempts:
            attempt += 1
            try:
                response = requests.get(self.endpoint, headers=headers, params=params, timeout=self.timeout)
                
                # Check for HTTP 503 or 429 retries
                if response.status_code in [429, 503] and attempt < max_attempts:
                    retry_after = response.headers.get("Retry-After")
                    sleep_time = 1.0
                    if retry_after and retry_after.isdigit():
                        sleep_time = min(float(retry_after), 2.0)  # Cap sleep to 2 seconds in execution
                    logger.warning(f"PricesAPI: Received {response.status_code}. Retrying in {sleep_time}s (Attempt {attempt}/{max_attempts})...")
                    time.sleep(sleep_time)
                    continue
                break
            except requests.Timeout:
                logger.error(f"PricesAPI: Read timed out on attempt {attempt}.")
                if attempt >= max_attempts:
                    self.last_api_status = "API ERROR: Timeout"
                    return []
            except requests.RequestException as e:
                logger.error(f"PricesAPI: Connection error on attempt {attempt}: {e}")
                if attempt >= max_attempts:
                    self.last_api_status = "API ERROR: Connection"
                    return []

        if not response:
            return []

        # Handle specific error status codes
        if response.status_code == 403:
            # Check credits limit exceeded
            try:
                body = response.json()
            except Exception:
                body = {}
            error_code = body.get("error", {}).get("code", "")
            error_msg = body.get("error", {}).get("message", "").lower()
            if "credits" in error_msg or "exceeded" in error_msg or error_code == "CREDITS_EXCEEDED":
                logger.error("PricesAPI: Credits exceeded (HTTP 403).")
                self.last_api_status = "QUOTA EXCEEDED"
            else:
                logger.error(f"PricesAPI: Forbidden (HTTP 403) - {response.text}")
                self.last_api_status = "API ERROR: Forbidden"
            return []
        elif response.status_code == 429:
            logger.error("PricesAPI: Rate limit exceeded (HTTP 429).")
            self.last_api_status = "API RATE LIMITED"
            return []
        elif response.status_code == 503:
            logger.error("PricesAPI: Service unavailable (HTTP 503).")
            self.last_api_status = "API ERROR: Service Unavailable"
            return []
        elif response.status_code != 200:
            logger.error(f"PricesAPI: Returned error HTTP {response.status_code} - {response.text}")
            self.last_api_status = f"API ERROR: HTTP {response.status_code}"
            return []

        try:
            payload = response.json()
        except Exception as e:
            logger.error(f"PricesAPI: Failed to parse JSON response: {e}")
            self.last_api_status = "API ERROR: Invalid JSON"
            return []

        # Extract products array
        data_block = payload.get("data") or {}
        products = data_block.get("products") or []
        if not isinstance(products, list):
            products = []

        self.last_raw_count = len(products)
        logger.info(f"PricesAPI: Retrieved {len(products)} raw product structures.")

        normalized_offers = self.normalize_results(products, product_id)
        self.last_normalized_count = len(normalized_offers)

        matched_offers = self.filter_relevant_results(normalized_offers, product_name)
        self.last_relevant_count = len(matched_offers)

        logger.info(f"PricesAPI: Matched {len(matched_offers)}/{len(normalized_offers)} relevant competitor offers.")
        return matched_offers

    def normalize_results(self, products: List[Dict[str, Any]], product_id: str) -> List[Dict[str, Any]]:
        """
        Extracts nested offers and parent product parameters, returning a standardized list.
        """
        normalized = []
        for p in products:
            title = p.get("title") or "Unknown Product"
            parent_source = p.get("source") or "PricesAPI"
            parent_price = p.get("price")
            parent_currency = p.get("currency") or "INR"
            parent_url = p.get("url") or "https://pricesapi.io"
            rating = p.get("rating")
            reviews = p.get("reviews") or p.get("reviews_count")

            offers = p.get("offers") or []
            if not isinstance(offers, list):
                offers = []

            # If no offers array, treat the product itself as a single seller listing
            if not offers:
                price_val = self._clean_price(parent_price)
                if price_val and price_val > 0:
                    normalized.append({
                        "product_id": product_id,
                        "competitor_name": parent_source,
                        "competitor_product_name": title,
                        "competitor_url": parent_url,
                        "competitor_price": round(float(price_val), 2),
                        "currency": parent_currency,
                        "availability": "In Stock",
                        "rating": float(rating) if rating is not None else None,
                        "review_count": int(reviews) if reviews is not None else None,
                        "data_source": "pricesapi",
                        "collected_at": datetime.utcnow(),
                        "raw_payload": p
                    })
                continue

            for off in offers:
                seller = off.get("seller") or parent_source
                url = off.get("url") or off.get("seller_url") or parent_url
                price = off.get("price") or parent_price
                currency = off.get("currency") or parent_currency
                condition = off.get("condition") or "New"

                price_val = self._clean_price(price)
                if not price_val or price_val <= 0:
                    continue

                availability = "In Stock"
                if "out of stock" in str(condition).lower() or "unavailable" in str(condition).lower():
                    availability = "Out of Stock"

                normalized.append({
                    "product_id": product_id,
                    "competitor_name": seller,
                    "competitor_product_name": title,
                    "competitor_url": url,
                    "competitor_price": round(float(price_val), 2),
                    "currency": currency,
                    "availability": availability,
                    "rating": float(rating) if rating is not None else None,
                    "review_count": int(reviews) if reviews is not None else None,
                    "data_source": "pricesapi",
                    "collected_at": datetime.utcnow(),
                    "raw_payload": off
                })

        return normalized

    def _clean_price(self, price_val: Any) -> Optional[float]:
        if price_val is None:
            return None
        if isinstance(price_val, (int, float)):
            return float(price_val)
        if isinstance(price_val, str):
            import re
            match = re.search(r"\d+(?:\.\d+)?", price_val.replace(",", ""))
            if match:
                return float(match.group())
        return None

    def filter_relevant_results(self, normalized_items: List[Dict[str, Any]], our_name: str) -> List[Dict[str, Any]]:
        try:
            threshold = float(os.getenv("COMPETITOR_MATCH_THRESHOLD", "0.70"))
        except ValueError:
            threshold = 0.70

        matched = []
        for item in normalized_items:
            score = self.compute_similarity(our_name, item["competitor_product_name"])
            if score >= threshold:
                item_copy = item.copy()
                item_copy["relevance_score"] = round(score, 3)
                matched.append(item_copy)

        matched.sort(key=lambda x: x["relevance_score"], reverse=True)
        return matched

    def compute_similarity(self, name1: str, name2: str) -> float:
        n1_lower = name1.lower().strip()
        n2_lower = name2.lower().strip()

        t1 = set(n1_lower.split())
        t2 = set(n2_lower.split())
        if not t1:
            return 0.0

        jaccard = len(t1.intersection(t2)) / len(t1.union(t2)) if t1.union(t2) else 0.0
        containment = len(t1.intersection(t2)) / len(t1)
        seq_matcher = difflib.SequenceMatcher(None, n1_lower, n2_lower).ratio()

        accessories = ["case", "cover", "stand", "bag", "sleeve", "mount", "strap", "sticker", "cable", "adapter", "charger", "holder"]
        is_accessory = any(acc in t2 for acc in accessories) and not any(acc in t1 for acc in accessories)

        if is_accessory:
            return 0.0

        if containment >= 0.9:
            return max(0.75, jaccard, seq_matcher)

        return max(jaccard, seq_matcher)
