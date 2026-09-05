import os
from pathlib import Path
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError

# Locate the backend directory to read the .env file
BACKEND_DIR = Path(__file__).resolve().parent.parent

def load_env_file():
    env_path = BACKEND_DIR / ".env"
    if not env_path.exists():
        return

    for line in env_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))

# Ensure environment variables are loaded
load_env_file()

# Read configurations
MONGO_URI = os.getenv("MONGO_URI")
if not MONGO_URI:
    user = os.getenv("MONGO_USER")
    password = os.getenv("MONGO_PASSWORD")
    host = os.getenv("MONGO_HOST", "localhost")
    port = os.getenv("MONGO_PORT", "27017")
    
    if user and password:
        MONGO_URI = f"mongodb://{user}:{password}@{host}:{port}/"
    else:
        MONGO_URI = f"mongodb://{host}:{port}/"

MONGO_DB_NAME = os.getenv("MONGO_DB", "pricepilot")

# Initialize global client and db references with error handling
client = None
db = None

try:
    # Use serverSelectionTimeoutMS=2000 to fail fast if MongoDB is not reachable
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=2000)
    db = client[MONGO_DB_NAME]
except Exception as e:
    print(f"Warning: Failed to initialize MongoDB client: {e}")

def test_connection():
    """
    Tests the connection to the MongoDB server.
    Returns:
        (bool, str): A tuple containing a success boolean and status/error message.
    """
    if client is None:
        return False, "MongoDB client is not initialized."
    try:
        # The admin command 'ping' is the standard way to check connection health in pymongo
        client.admin.command('ping')
        return True, "MongoDB connection test successful."
    except (ConnectionFailure, ServerSelectionTimeoutError) as e:
        return False, f"MongoDB connection test failed: {e}"
    except Exception as e:
        return False, f"MongoDB connection test failed with unexpected error: {e}"
