import os
import sys
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Any, Optional

# Ensure the backend directory is in the system path to allow absolute imports
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.append(str(BASE_DIR))

from database.mongodb import db, test_connection

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("services.model_versioning")

# Reference to the MongoDB collection
COLLECTION_NAME = "model_versions"
collection = db[COLLECTION_NAME] if db is not None else None

def is_db_connected() -> bool:
    """
    Checks if MongoDB connection is active.
    """
    if collection is None:
        return False
    success, _ = test_connection()
    return success

def register_model_version(
    model_name: str,
    version: str,
    algorithm: str,
    training_date: str,
    dataset_used: str,
    num_features: int,
    metrics: Dict[str, Any],
    file_path: str,
    status: str = "active",
    notes: Optional[str] = None
) -> bool:
    """
    Registers a new version of an ML model in MongoDB.
    
    If the registered version has a status of "active", all other versions
    for the same model_name are automatically set to "inactive".
    """
    if not is_db_connected():
        logger.warning("MongoDB is not connected. Cannot register model version.")
        return False
        
    try:
        current_time = datetime.now(timezone.utc).isoformat()
        
        doc = {
            "model_name": str(model_name),
            "version": str(version),
            "algorithm": str(algorithm),
            "training_date": str(training_date),
            "dataset_used": str(dataset_used),
            "num_features": int(num_features),
            "metrics": metrics,
            "file_path": str(file_path),
            "status": str(status).lower(),
            "notes": notes,
            "created_at": current_time
        }
        
        # If new version is marked active, deactivate existing ones first
        if doc["status"] == "active":
            logger.info(f"Deactivating prior active versions for model: {model_name}...")
            collection.update_many(
                {"model_name": doc["model_name"], "status": "active"},
                {"$set": {"status": "inactive"}}
            )
            
        # Upsert by model_name + version to prevent duplicate registration rows
        collection.update_one(
            {"model_name": doc["model_name"], "version": doc["version"]},
            {"$set": doc},
            upsert=True
        )
        logger.info(f"Successfully registered model version: {model_name} ({version})")
        return True
    except Exception as e:
        logger.error(f"Failed to register model version: {e}")
        return False

def get_latest_model(model_name: str) -> Optional[Dict[str, Any]]:
    """
    Retrieves the latest version of a model.
    Prioritizes the active version; otherwise falls back to the newest by creation date.
    """
    if not is_db_connected():
        logger.warning("MongoDB is not connected. Cannot query latest model.")
        return None
        
    try:
        # 1. Look for the active version first
        active_doc = collection.find_one(
            {"model_name": str(model_name), "status": "active"},
            {"_id": 0}
        )
        if active_doc:
            return active_doc
            
        # 2. Fallback to newest version by creation date
        fallback_doc = collection.find_one(
            {"model_name": str(model_name)},
            {"_id": 0},
            sort=[("created_at", -1)]
        )
        return fallback_doc
    except Exception as e:
        logger.error(f"Failed to query latest model version from MongoDB: {e}")
        return None

def get_all_versions(model_name: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Retrieves all model versions, optionally filtered by model name.
    Sorted by version/creation time descending.
    """
    if not is_db_connected():
        logger.warning("MongoDB is not connected. Cannot query model versions.")
        return []
        
    try:
        query = {}
        if model_name:
            query["model_name"] = str(model_name)
            
        cursor = collection.find(query, {"_id": 0}).sort("created_at", -1)
        return list(cursor)
    except Exception as e:
        logger.error(f"Failed to query model versions list: {e}")
        return []

if __name__ == "__main__":
    print("Testing Model Versioning Service...")
    
    if not is_db_connected():
        print("MongoDB is not connected. Ensure MongoDB is running and MONGO_URI is valid.")
        sys.exit(1)
        
    model_name_test = "test_price_model"
    
    print("\n1. Registering Version 1.0.0 (active)...")
    register_model_version(
        model_name=model_name_test,
        version="v1.0.0",
        algorithm="XGBoost Regressor",
        training_date=datetime.now(timezone.utc).isoformat(),
        dataset_used="online_retail_II.csv",
        num_features=14,
        metrics={"mae": 0.81, "rmse": 62.47, "mape": 0.15, "r2": 0.88},
        file_path="saved_models/price_prediction_xgboost.joblib",
        status="active",
        notes="Initial release"
    )
    
    print("\n2. Registering Version 1.1.0 (active, triggers auto-deactivation of v1.0.0)...")
    register_model_version(
        model_name=model_name_test,
        version="v1.1.0",
        algorithm="LightGBM Regressor",
        training_date=datetime.now(timezone.utc).isoformat(),
        dataset_used="online_retail_II.csv",
        num_features=14,
        metrics={"mae": 0.49, "rmse": 10.39, "mape": 0.08, "r2": 0.89},
        file_path="saved_models/price_prediction_lightgbm.joblib",
        status="active",
        notes="Improved accuracy using LightGBM"
    )
    
    print("\n3. Querying latest model version...")
    latest = get_latest_model(model_name_test)
    if latest:
        print(f"  Latest Model Version: {latest['version']} | Algorithm: {latest['algorithm']} | Status: {latest['status']}")
    
    print("\n4. Querying all registered versions...")
    versions = get_all_versions(model_name_test)
    print(f"  Found {len(versions)} versions:")
    for v in versions:
        print(f"    - Version: {v['version']} | Algorithm: {v['algorithm']} | Status: {v['status']} | Notes: {v['notes']}")
        
    print("\nVerification Test Completed!")
