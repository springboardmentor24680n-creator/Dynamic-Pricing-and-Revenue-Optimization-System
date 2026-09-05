import os
from pathlib import Path
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base

from dotenv import load_dotenv

# Locate the backend directory to read the .env file
BACKEND_DIR = Path(__file__).resolve().parent.parent

# Ensure environment variables are loaded
load_dotenv(dotenv_path=BACKEND_DIR / ".env")

# Read configurations
POSTGRES_URL = os.getenv("POSTGRES_URL")
if not POSTGRES_URL:
    user = os.getenv("POSTGRES_USER", "postgres")
    password = os.getenv("POSTGRES_PASSWORD", "postgres")
    host = os.getenv("POSTGRES_HOST", "localhost")
    port = os.getenv("POSTGRES_PORT", "5432")
    db = os.getenv("POSTGRES_DB", "pricepilot")
    # Construct postgresql connection string
    POSTGRES_URL = f"postgresql://{user}:{password}@{host}:{port}/{db}"

# Initialize global engine and sessionmaker references
engine = None
SessionLocal = None
Base = declarative_base()

try:
    engine = create_engine(POSTGRES_URL, pool_pre_ping=True)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
except Exception as e:
    print(f"Warning: Failed to initialize PostgreSQL engine: {e}")

def test_connection():
    """
    Tests the connection to the PostgreSQL database.
    Returns:
        (bool, str): A tuple containing a success boolean and status/error message.
    """
    if engine is None:
        return False, "PostgreSQL engine is not initialized."
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return True, "PostgreSQL connection test successful."
    except Exception as e:
        return False, f"PostgreSQL connection test failed: {e}"
