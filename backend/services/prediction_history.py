import os
import sys
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Any

# Ensure the backend directory is in the system path to allow absolute imports
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.append(str(BASE_DIR))

from database.mongodb import db, test_connection

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("services.prediction_history")

# Reference to the MongoDB collection
COLLECTION_NAME = "prediction_history"
collection = db[COLLECTION_NAME] if db is not None else None

def is_db_connected() -> bool:
    """
    Checks if MongoDB connection is active.
    """
    if collection is None:
        return False
    success, _ = test_connection()
    return success

def save_prediction(
    product_id: str,
    current_price: float,
    recommended_price: float,
    forecast_demand: float,
    model_used: str,
    confidence: float,
    user: str = None
) -> bool:
    """
    Logs a single price prediction event to MongoDB.
    
    Args:
        product_id: Identifier of the product (e.g. stockcode)
        current_price: Current pricing level
        recommended_price: Optimized/suggested pricing target
        forecast_demand: Projected demand volume
        model_used: Algorithm/Model name used (e.g. LightGBM)
        confidence: Confidence level percentage
        user: Identifier of the user triggering the run (optional)
        
    Returns:
        bool: True if prediction was logged successfully, False otherwise.
    """
    if not is_db_connected():
        logger.warning("MongoDB is not connected. Cannot save prediction to history registry.")
        return False
        
    try:
        doc = {
            "product_id": str(product_id),
            "current_price": float(current_price),
            "recommended_price": float(recommended_price),
            "forecast_demand": float(forecast_demand),
            "model_used": str(model_used),
            "confidence": float(confidence),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "user": user
        }
        
        # Insert log record into MongoDB collection
        collection.insert_one(doc)
        logger.info(f"Successfully logged prediction history for product: {product_id}")
        return True
    except Exception as e:
        logger.error(f"Failed to save prediction history in MongoDB: {e}")
        return False

def get_prediction_history(limit: int = 100) -> List[Dict[str, Any]]:
    """
    Retrieves historical price prediction logs from MongoDB, sorted by timestamp descending.
    
    Args:
        limit: Maximum number of history entries to return
        
    Returns:
        List[Dict[str, Any]]: Log documents (excluding MongoDB ObjectID properties).
    """
    if not is_db_connected():
        logger.warning("MongoDB is not connected. Cannot retrieve prediction history registry.")
        return []
        
    try:
        # Query logs, sort by timestamp descending (newest first)
        cursor = collection.find({}, {"_id": 0}).sort("timestamp", -1).limit(limit)
        return list(cursor)
    except Exception as e:
        logger.error(f"Failed to query prediction history from MongoDB: {e}")
        return []

if __name__ == "__main__":
    print("Testing Prediction History Service...")
    
    if not is_db_connected():
        print("MongoDB is not connected. Ensure MongoDB is running and MONGO_URI is valid.")
        sys.exit(1)
        
    # Save a mock prediction log
    print("Logging sample prediction record...")
    success = save_prediction(
        product_id="TEST_PROD_123",
        current_price=10.99,
        recommended_price=12.49,
        forecast_demand=450.0,
        model_used="LightGBM Regressor",
        confidence=89.5,
        user="pricing_manager_test"
    )
    
    if success:
        print("Logged successfully! Querying prediction logs...")
        history = get_prediction_history(limit=5)
        print(f"Retrieved {len(history)} history records:")
        for idx, item in enumerate(history):
            print(f"  {idx+1}. Product: {item['product_id']} | Price: ${item['current_price']} -> ${item['recommended_price']} | Model: {item['model_used']} | Time: {item['timestamp']} | User: {item['user']}")
    else:
        print("Failed to save prediction record.")
        sys.exit(1)
