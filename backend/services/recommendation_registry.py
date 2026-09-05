import os
import sys
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Any

# Ensure the backend directory is in the system path to allow absolute imports
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.append(str(BASE_DIR))

from database.mongodb import db, test_connection
from ml_pipeline.train_price_model import REPORTS_DIR

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("services.recommendation_registry")

class RecommendationRegistryService:
    """
    A reusable service designed to manage price recommendation logs and registers
    stored in the MongoDB 'recommendation_registry' collection.
    """
    def __init__(self, collection_name: str = "recommendation_registry"):
        self.collection_name = collection_name
        self.collection = db[collection_name] if db is not None else None

    def is_connected(self) -> bool:
        """
        Verifies database and connection health.
        """
        if self.collection is None:
            return False
        success, _ = test_connection()
        return success

    def register_recommendation(self, rec: Dict[str, Any]) -> bool:
        """
        Persists or updates a single recommendation entry in MongoDB.
        """
        if not self.is_connected():
            logger.warning("MongoDB client is not connected. Skipping registration.")
            return False
            
        try:
            # Structuring the required MongoDB schema fields
            doc = {
                "product_id": str(rec.get("stockcode")),
                "current_price": float(rec.get("current_price", 0.0)),
                "recommended_price": float(rec.get("recommended_price", 0.0)),
                "forecast_demand": float(rec.get("expected_demand", 0.0)),
                "revenue_gain": float(rec.get("revenue_improvement", 0.0)),
                "recommendation": str(rec.get("recommendation", "Maintain Price")),
                "confidence": float(rec.get("confidence", 87.83)),
                "timestamp": rec.get("timestamp") or datetime.now(timezone.utc).isoformat()
            }
            
            # Upsert document by product_id
            self.collection.update_one(
                {"product_id": doc["product_id"]},
                {"$set": doc},
                upsert=True
            )
            return True
        except Exception as e:
            logger.error(f"Failed to upsert recommendation for {rec.get('stockcode')}: {e}")
            return False

    def register_recommendations_batch(self, recs: List[Dict[str, Any]], confidence_val: float = 87.83) -> int:
        """
        Persists a batch of recommendations to MongoDB using upserts.
        """
        if not self.is_connected():
            logger.error("MongoDB is not connected. Cannot run batch upsert.")
            return 0
            
        inserted_count = 0
        current_time = datetime.now(timezone.utc).isoformat()
        
        for rec in recs:
            rec_copy = rec.copy()
            # Assign confidence and execution timestamp
            rec_copy["confidence"] = confidence_val
            rec_copy["timestamp"] = current_time
            if self.register_recommendation(rec_copy):
                inserted_count += 1
                
        return inserted_count

def main():
    logger.info("Initializing Recommendation Registry service run...")
    
    recommendations_path = REPORTS_DIR / "price_recommendations.json"
    confidence_path = REPORTS_DIR / "forecast_confidence.json"
    
    if not recommendations_path.exists():
        logger.error(f"Recommendations report not found at: {recommendations_path}. Run price_recommendation.py first.")
        sys.exit(1)
        
    try:
        # Load pre-computed recommendations
        logger.info(f"Loading price recommendations from: {recommendations_path}")
        with open(recommendations_path, "r", encoding="utf-8") as f:
            recs_data = json.load(f)
            
        recommendations = recs_data.get("recommendations", [])
        
        # Load forecast confidence level
        confidence_val = 87.83
        if confidence_path.exists():
            try:
                with open(confidence_path, "r", encoding="utf-8") as f:
                    conf_data = json.load(f)
                    # Pull average confidence for 90 days horizon
                    confidence_val = conf_data.get("90_days", {}).get("average_confidence_score", 87.83)
                    logger.info(f"Retrieved 90-day forecast confidence score: {confidence_val}%")
            except Exception as e:
                logger.warning(f"Failed to read confidence report: {e}. Defaulting to {confidence_val}%")
                
        # Initialize registry service
        registry = RecommendationRegistryService()
        
        # Verify MongoDB connection health
        if not registry.is_connected():
            logger.error("MongoDB connection check failed. Ensure MongoDB is running and MONGO_URI is valid.")
            sys.exit(1)
            
        logger.info(f"Registering {len(recommendations)} recommendations in MongoDB...")
        count = registry.register_recommendations_batch(recommendations, confidence_val)
        
        print("\n" + "="*80)
        print("                      RECOMMENDATION REGISTRY REPORT")
        print("="*80)
        print(f"MongoDB Collection Name : {registry.collection_name}")
        print(f"Total Source Entries    : {len(recommendations)}")
        print(f"Successfully Registered : {count} documents")
        print(f"Connection Status       : CONNECTED")
        print(f"Registry Timestamp      : {datetime.now(timezone.utc).isoformat()}")
        print("="*80 + "\n")
        
    except Exception as e:
        logger.error(f"Error during recommendation registration process: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()
