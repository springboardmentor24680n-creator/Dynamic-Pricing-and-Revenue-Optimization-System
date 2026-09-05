import os
import logging
import requests
import difflib
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# Load env variables relative to backend directory
BACKEND_DIR = Path(__file__).resolve().parent.parent
load_dotenv(dotenv_path=BACKEND_DIR / ".env")

class OpenWebNinjaService:
    def __init__(self):
        # Read OPENWEB_NINJA_API_KEY from environment variables (fall back to OPENWEBNINJA_API_KEY)
        self.api_key = (os.getenv("OPENWEB_NINJA_API_KEY") or os.getenv("OPENWEBNINJA_API_KEY", "")).strip()
        self.endpoint = "https://api.openwebninja.com/realtime-product-search/v2/search"
        self.timeout = 10.0 # Strict timeout of 10s

    def search_product(self, product_name: str, product_id: str) -> List[Dict[str, Any]]:
        """
        Queries OpenWeb Ninja Google Shopping search API v2 for the given product name,
        normalizes the results, and filters them using text similarity matching.
        """
        # Default stats
        self.last_raw_count = 0
        self.last_normalized_count = 0
        self.last_relevant_count = 0
        self.last_api_status = "Success"

        if not self.api_key:
            logger.warning("OpenWeb Ninja API Key is missing. Skipping real competitor search.")
            self.last_api_status = "Not Configured"
            return []

        logger.info(f"OpenWeb Ninja v2: Searching for product ID '{product_id}' using query: '{product_name}'")
        
        headers = {
            "x-api-key": self.api_key,
            "Accept": "application/json"
        }
        params = {
            "q": product_name,
            "country": "IN"  # standard currency is INR
        }

        try:
            response = requests.get(self.endpoint, headers=headers, params=params, timeout=self.timeout)
            
            # Catch rate limit (HTTP 429) or other errors safely
            if response.status_code == 429:
                logger.error("OpenWeb Ninja API: Rate limit exceeded (HTTP 429).")
                self.last_api_status = "API RATE LIMITED"
                return []
            elif response.status_code != 200:
                logger.error(f"OpenWeb Ninja API returned error: HTTP {response.status_code} - {response.text}")
                self.last_api_status = f"API ERROR: HTTP {response.status_code}"
                return []

            payload = response.json()
            
            # Check envelope status
            if payload.get("status") == "ERROR":
                error_msg = payload.get("error", {}).get("message", "Unknown API error")
                logger.error(f"OpenWeb Ninja API status error: {error_msg}")
                self.last_api_status = f"API ERROR: {error_msg}"
                return []
                
            results = []
            if isinstance(payload, list):
                results = payload
            elif isinstance(payload, dict):
                data_block = payload.get("data")
                if isinstance(data_block, dict):
                    results = data_block.get("products") or data_block.get("shopping_results") or data_block.get("results") or data_block.get("offers")
                if not results:
                    results = payload.get("products") or payload.get("shopping_results") or payload.get("results") or payload.get("offers")
            
            if not isinstance(results, list):
                results = []

            self.last_raw_count = len(results)
            logger.info(f"OpenWeb Ninja v2: Retrieved {len(results)} raw search results.")
            
            normalized_results = self.normalize_results(results, product_id)
            self.last_normalized_count = len(normalized_results)
            
            matched_results = self.filter_relevant_results(normalized_results, product_name)
            self.last_relevant_count = len(matched_results)
            
            logger.info(f"OpenWeb Ninja v2: Matched {len(matched_results)}/{len(normalized_results)} relevant competitor listings.")
            return matched_results

        except requests.Timeout:
            logger.error("OpenWeb Ninja API search request timed out.")
            self.last_api_status = "API ERROR: Timeout"
            return []
        except requests.RequestException as e:
            logger.error(f"OpenWeb Ninja API connection error: {e}")
            self.last_api_status = f"API ERROR: Connection"
            return []
        except Exception as e:
            logger.error(f"Error executing OpenWeb Ninja search: {e}")
            self.last_api_status = f"API ERROR: {str(e)}"
            return []

    def normalize_results(self, results: List[Dict[str, Any]], product_id: str) -> List[Dict[str, Any]]:
        """
        Converts the v2 API response structure into standard schema properties.
        """
        normalized = []
        for item in results:
            # Extract title and merchant details (robust fallbacks)
            title = item.get("title") or item.get("product_title") or "Unknown Product"
            merchant = item.get("store_name") or item.get("source") or item.get("merchant") or item.get("merchant_name") or "Unknown Retailer"
            url = item.get("product_page_url") or item.get("link") or item.get("url") or item.get("product_url") or "https://google.com/shopping"
            
            # Extract prices (v2 schema)
            price_val = item.get("price") or item.get("extracted_price")
            orig_price_val = item.get("original_price") or item.get("extracted_original_price")
            
            # Clean price string using regex to extract numeric digits and decimals
            if isinstance(price_val, str):
                import re
                match = re.search(r"\d+(?:\.\d+)?", price_val.replace(",", ""))
                if match:
                    price_val = float(match.group())
                else:
                    price_val = 0.0
            if isinstance(orig_price_val, str):
                import re
                match = re.search(r"\d+(?:\.\d+)?", orig_price_val.replace(",", ""))
                if match:
                    orig_price_val = float(match.group())
                else:
                    orig_price_val = None

            # Store only valid numeric prices
            if not price_val or float(price_val) <= 0:
                continue

            # Availability formatting
            availability = item.get("availability") or ("In Stock" if item.get("in_stock", True) else "Out of Stock")
            rating = item.get("product_rating") or item.get("rating") or item.get("stars")
            reviews = item.get("product_num_reviews") or item.get("reviews_count") or item.get("review_count")

            # Detect currency from price symbol or fallback
            currency = item.get("currency")
            if not currency:
                raw_price = item.get("price")
                if isinstance(raw_price, str) and "$" in raw_price:
                    currency = "USD"
                elif isinstance(raw_price, str) and "₹" in raw_price:
                    currency = "INR"
                else:
                    currency = "INR"

            normalized.append({
                "product_id": product_id,
                "competitor_name": merchant,
                "competitor_product_name": title,
                "competitor_url": url,
                "competitor_price": round(float(price_val), 2),
                "original_price": round(float(orig_price_val), 2) if orig_price_val else None,
                "currency": currency,
                "availability": availability,
                "rating": float(rating) if rating is not None else None,
                "review_count": int(reviews) if reviews is not None else None,
                "data_source": "openwebninja",
                "collected_at": datetime.utcnow(),
                "raw_payload": item  # preserve raw fields for utility
            })
        return normalized

    def filter_relevant_results(self, normalized_items: List[Dict[str, Any]], our_name: str) -> List[Dict[str, Any]]:
        """
        Filters and ranks search results using sequence similarity matcher and token overlap.
        """
        try:
            threshold = float(os.getenv("COMPETITOR_MATCH_THRESHOLD", "0.70"))
        except ValueError:
            threshold = 0.70

        matched = []
        for item in normalized_items:
            score = self.compute_similarity(our_name, item["competitor_product_name"])
            # Require minimum relevance threshold
            if score >= threshold:
                item_copy = item.copy()
                item_copy["relevance_score"] = round(score, 3)
                matched.append(item_copy)
                
        # Sort by best similarity rank first
        matched.sort(key=lambda x: x["relevance_score"], reverse=True)
        return matched

    def compute_similarity(self, name1: str, name2: str) -> float:
        """
        Calculates similarity ratio between 0.0 and 1.0 using Jaccard token overlap,
        token containment, and difflib sequence matching algorithms.
        """
        n1_lower = name1.lower().strip()
        n2_lower = name2.lower().strip()

        # Tokenize
        t1 = set(n1_lower.split())
        t2 = set(n2_lower.split())
        if not t1:
            return 0.0

        # Standard Jaccard Similarity
        jaccard = len(t1.intersection(t2)) / len(t1.union(t2)) if t1.union(t2) else 0.0

        # Containment Coefficient: what fraction of our product name keywords are in the competitor title
        containment = len(t1.intersection(t2)) / len(t1)

        # Sequence Matcher Closeness
        seq_matcher = difflib.SequenceMatcher(None, n1_lower, n2_lower).ratio()

        # accessory check (avoid cases, adapters, covers if our product is the main unit)
        accessories = ["case", "cover", "stand", "bag", "sleeve", "mount", "strap", "sticker", "cable", "adapter", "charger", "holder"]
        is_accessory = any(acc in t2 for acc in accessories) and not any(acc in t1 for acc in accessories)

        if is_accessory:
            return 0.0

        # Containment boost: if all our product name keywords are present, ensure it meets match threshold
        if containment >= 0.9:
            return max(0.75, jaccard, seq_matcher)

        return max(jaccard, seq_matcher)
