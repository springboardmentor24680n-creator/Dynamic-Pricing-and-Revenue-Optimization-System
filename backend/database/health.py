import logging
from sqlalchemy import text
from database import postgres, mongodb

# Configure logging
logger = logging.getLogger("database_health")

def test_sqlite_connection():
    """
    Tests the SQLite database connection.
    Attempts to import the active SQLAlchemy engine from main, with a fallback to dynamic instantiation.
    """
    try:
        from main import engine as sqlite_engine
        with sqlite_engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True, "SQLite Connected"
    except Exception as e:
        try:
            from pathlib import Path
            from sqlalchemy import create_engine
            BASE_DIR = Path(__file__).resolve().parent.parent.parent
            sqlite_db_url = f"sqlite:///{BASE_DIR / 'pricepilot.db'}"
            fallback_engine = create_engine(sqlite_db_url)
            with fallback_engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return True, "SQLite Connected (via fallback engine)"
        except Exception as fallback_err:
            return False, f"SQLite connection failed: {fallback_err} (original error: {e})"

def run_database_health_checks():
    """
    Runs health checks for SQLite, PostgreSQL, and MongoDB.
    Prints clear startup messages and logs errors.
    """
    print("\n--- Database Health Checks ---", flush=True)

    # 1. SQLite
    sqlite_ok, sqlite_msg = test_sqlite_connection()
    if sqlite_ok:
        print("[OK] SQLite Connected", flush=True)
    else:
        print("[FAIL] SQLite Connection Failed", flush=True)
        logger.error(sqlite_msg)

    # 2. PostgreSQL
    postgres_ok, postgres_msg = postgres.test_connection()
    if postgres_ok:
        print("[OK] PostgreSQL Connected", flush=True)
    else:
        print("[FAIL] PostgreSQL Connection Failed", flush=True)
        logger.error(postgres_msg)

    # 3. MongoDB
    mongo_ok, mongo_msg = mongodb.test_connection()
    if mongo_ok:
        print("[OK] MongoDB Connected", flush=True)
    else:
        print("[FAIL] MongoDB Connection Failed", flush=True)
        logger.error(mongo_msg)

    print("------------------------------\n", flush=True)
