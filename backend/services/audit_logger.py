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
logger = logging.getLogger("services.audit_logger")

# Reference to the MongoDB collection
COLLECTION_NAME = "audit_logs"
collection = db[COLLECTION_NAME] if db is not None else None

def is_db_connected() -> bool:
    """
    Checks if MongoDB connection is active.
    """
    if collection is None:
        return False
    success, _ = test_connection()
    return success

def log_event(
    event: str,
    user: str,
    details: Union[Dict[str, Any], str],
    status: str = "success"
) -> bool:
    """
    Persists a structured audit log event in MongoDB.
    
    Args:
        event: Type of action/event (e.g. "User login", "Price prediction", etc.)
        user: Identifier of the user (e.g. username, email) or "system"
        details: Structured key-value dict or string describing log metadata details
        status: Outcome status of the event (e.g. "success", "failed", "info")
        
    Returns:
        bool: True if logged successfully, False otherwise.
    """
    if not is_db_connected():
        logger.warning("MongoDB is not connected. Cannot write to system audit logs.")
        return False
        
    try:
        current_time = datetime.now(timezone.utc).isoformat()
        
        # Ensure details is in a standard format
        formatted_details = details
        if not isinstance(details, (dict, str)):
            formatted_details = str(details)
            
        doc = {
            "event": str(event),
            "user": str(user),
            "timestamp": current_time,
            "details": formatted_details,
            "status": str(status).lower()
        }
        
        collection.insert_one(doc)
        logger.info(f"Successfully recorded audit event: {event} for user: {user}")
        return True
    except Exception as e:
        logger.error(f"Failed to record audit log: {e}")
        return False

def get_logs(
    filter_query: Optional[Dict[str, Any]] = None,
    limit: int = 100
) -> List[Dict[str, Any]]:
    """
    Queries historical audit log records, sorted by timestamp descending.
    
    Args:
        filter_query: MongoDB query filter dictionary (optional)
        limit: Maximum number of audit records to return
        
    Returns:
        List[Dict[str, Any]]: Audit log documents (excluding MongoDB ObjectID properties).
    """
    if not is_db_connected():
        logger.warning("MongoDB is not connected. Cannot query system audit logs.")
        return []
        
    try:
        query = filter_query if filter_query is not None else {}
        cursor = collection.find(query, {"_id": 0}).sort("timestamp", -1).limit(limit)
        return list(cursor)
    except Exception as e:
        logger.error(f"Failed to query system audit logs: {e}")
        return []

def get_recent_logs(limit: int = 10) -> List[Dict[str, Any]]:
    """
    Helper function to retrieve the most recent audit logs.
    
    Args:
        limit: Number of records to return
        
    Returns:
        List[Dict[str, Any]]: Recent audit log documents.
    """
    return get_logs(limit=limit)

if __name__ == "__main__":
    print("Testing Audit Logging Service...")
    
    if not is_db_connected():
        print("MongoDB is not connected. Ensure MongoDB is running and MONGO_URI is valid.")
        sys.exit(1)
        
    # Simulate logging a user login
    print("\n1. Logging login event...")
    log_event(
        event="User login",
        user="analyst_test@pricepilot.ai",
        details={"ip_address": "192.168.1.50", "client_agent": "Mozilla Chrome"},
        status="success"
    )
    
    # Simulate logging a price prediction
    print("\n2. Logging price prediction event...")
    log_event(
        event="Price prediction",
        user="analyst_test@pricepilot.ai",
        details={"product_id": "22423", "model_used": "LightGBM Regressor", "run_time_seconds": 0.045},
        status="success"
    )
    
    # Simulate logging a failed model registration
    print("\n3. Logging model registration failure event...")
    log_event(
        event="Model registration",
        user="system",
        details="Attempted to register model file 'invalid_model_path.pkl' (File Not Found)",
        status="failed"
    )
    
    print("\n4. Querying recent audit logs...")
    recent_logs = get_recent_logs(limit=5)
    print(f"  Retrieved {len(recent_logs)} recent logs:")
    for log in recent_logs:
        print(f"    - [{log['timestamp']}] Event: {log['event']} | User: {log['user']} | Status: {log['status']} | Details: {log['details']}")
        
    print("\n5. Querying filtered logs (status = 'failed')...")
    failed_logs = get_logs(filter_query={"status": "failed"}, limit=5)
    print(f"  Retrieved {len(failed_logs)} failed logs:")
    for log in failed_logs:
        print(f"    - [{log['timestamp']}] Event: {log['event']} | User: {log['user']} | Details: {log['details']}")
        
    print("\nVerification Test Completed!")
