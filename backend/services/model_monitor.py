import os
import sys
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Any, Union, Optional

# Ensure the backend directory is in the system path to allow absolute imports
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.append(str(BASE_DIR))

from database.mongodb import db, test_connection

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("services.model_monitor")

# Reference to the MongoDB collection
COLLECTION_NAME = "model_monitoring"
collection = db[COLLECTION_NAME] if db is not None else None

def is_db_connected() -> bool:
    """
    Checks if MongoDB connection is active.
    """
    if collection is None:
        return False
    success, _ = test_connection()
    return success

def update_monitor(
    model_name: str,
    active_version: str,
    prediction_time_seconds: float,
    success: bool,
    model_status: str = "active",
    model_health: str = "Healthy"
) -> bool:
    """
    Updates the monitoring status, rolling latencies, and prediction counters for a model in MongoDB.
    """
    if not is_db_connected():
        logger.warning("MongoDB is not connected. Cannot update model monitor stats.")
        return False
        
    try:
        current_time = datetime.now(timezone.utc).isoformat()
        
        # 1. Retrieve existing monitor status for the model if it exists
        existing = collection.find_one({"model_name": model_name})
        
        if existing:
            total_predictions = existing.get("total_predictions", 0) + 1
            success_count = existing.get("total_successful_predictions", 0)
            failed_count = existing.get("total_failed_predictions", 0)
            avg_time = existing.get("average_prediction_time_seconds", 0.0)
            
            if success:
                # Update rolling average prediction time for successful requests
                # new_avg = ((old_avg * old_success) + new_time) / (old_success + 1)
                new_success_count = success_count + 1
                avg_time = ((avg_time * success_count) + prediction_time_seconds) / new_success_count
                success_count = new_success_count
            else:
                failed_count += 1
        else:
            total_predictions = 1
            success_count = 1 if success else 0
            failed_count = 0 if success else 1
            avg_time = prediction_time_seconds if success else 0.0
            
        doc = {
            "model_name": str(model_name),
            "active_version": str(active_version),
            "model_status": str(model_status),
            "total_predictions": int(total_predictions),
            "average_prediction_time_seconds": round(float(avg_time), 5),
            "last_prediction_timestamp": current_time,
            "model_health": str(model_health),
            "total_successful_predictions": int(success_count),
            "total_failed_predictions": int(failed_count),
            "last_updated": current_time
        }
        
        # Upsert document by model_name
        collection.update_one(
            {"model_name": model_name},
            {"$set": doc},
            upsert=True
        )
        logger.info(f"Successfully updated monitor logs for model: {model_name}")
        return True
    except Exception as e:
        logger.error(f"Failed to update model monitor: {e}")
        return False

def get_monitor_status(model_name: Optional[str] = None) -> Union[Optional[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Retrieves the monitoring document(s) from MongoDB (stripping ObjectID).
    """
    if not is_db_connected():
        logger.warning("MongoDB is not connected. Cannot query model monitor status.")
        return [] if model_name is None else None
        
    try:
        if model_name:
            return collection.find_one({"model_name": model_name}, {"_id": 0})
        else:
            return list(collection.find({}, {"_id": 0}))
    except Exception as e:
        logger.error(f"Failed to query model monitor: {e}")
        return [] if model_name is None else None

def reset_statistics(model_name: str) -> bool:
    """
    Resets metrics counters (predictions counts and rolling latency averages) for a model,
    while preserving version, status, and health fields.
    """
    if not is_db_connected():
        logger.warning("MongoDB is not connected. Cannot reset model monitor statistics.")
        return False
        
    try:
        current_time = datetime.now(timezone.utc).isoformat()
        
        # Reset counters in database
        collection.update_one(
            {"model_name": model_name},
            {
                "$set": {
                    "total_predictions": 0,
                    "average_prediction_time_seconds": 0.0,
                    "total_successful_predictions": 0,
                    "total_failed_predictions": 0,
                    "last_updated": current_time
                }
            }
        )
        logger.info(f"Successfully reset monitor statistics for model: {model_name}")
        return True
    except Exception as e:
        logger.error(f"Failed to reset model statistics: {e}")
        return False

if __name__ == "__main__":
    print("Testing Model Monitoring Service...")
    
    if not is_db_connected():
        print("MongoDB is not connected. Ensure MongoDB is running and MONGO_URI is valid.")
        sys.exit(1)
        
    model_name_test = "test_pricing_model"
    
    # Reset existing test entries if they exist
    reset_statistics(model_name_test)
    
    # Simulate a sequence of model inference predictions
    print("\n1. Simulating successful predictions with varied latency...")
    update_monitor(model_name_test, "v1.1.0", 0.045, True)
    update_monitor(model_name_test, "v1.1.0", 0.055, True)
    update_monitor(model_name_test, "v1.1.0", 0.050, True)
    
    # Simulate a failed prediction
    print("\n2. Simulating a failed prediction...")
    update_monitor(model_name_test, "v1.1.0", 0.000, False, model_health="Degraded")
    
    print("\n3. Querying model monitor status...")
    status = get_monitor_status(model_name_test)
    if status:
        print(f"  Model Name       : {status['model_name']}")
        print(f"  Active Version   : {status['active_version']}")
        print(f"  Health State     : {status['model_health']}")
        print(f"  Success/Failed   : {status['total_successful_predictions']} / {status['total_failed_predictions']}")
        print(f"  Average Latency  : {status['average_prediction_time_seconds']} seconds")
        print(f"  Last Run Time    : {status['last_prediction_timestamp']}")
        
    print("\n4. Resetting model statistics...")
    reset_statistics(model_name_test)
    reset_status = get_monitor_status(model_name_test)
    if reset_status:
        print(f"  Post-Reset Success/Failed : {reset_status['total_successful_predictions']} / {reset_status['total_failed_predictions']}")
        print(f"  Post-Reset Avg Latency    : {reset_status['average_prediction_time_seconds']} seconds")
        
    print("\nVerification Test Completed!")
