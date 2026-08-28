"""
PricePilot AI - Database Configuration
"""

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from app.config import settings

DATABASE_URL = settings.DATABASE_URL

# SQLite needs check_same_thread=False for FastAPI's threaded access
_connect_args = {}
if DATABASE_URL.startswith("sqlite"):
    _connect_args["check_same_thread"] = False

engine = create_engine(DATABASE_URL, connect_args=_connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """Dependency that provides a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def migrate_schema():
    """Non-destructive startup migration.

    Adds columns to existing tables that were introduced after the schema was
    first created (create_all only creates missing tables, never missing
    columns). Never drops data, tables, or indexes.
    """
    if DATABASE_URL.startswith("sqlite"):
        _migrate_sqlite()
    elif DATABASE_URL.startswith("postgresql"):
        _migrate_postgres()


def _migrate_sqlite():
    """SQLite-specific non-destructive migration."""
    try:
        import sqlite3
        db_path = DATABASE_URL.replace("sqlite:///", "")
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()

        # Users table new columns
        users_cols = {row[1] for row in cur.execute("PRAGMA table_info(users)").fetchall()}
        user_additions = {
            "google_id": "VARCHAR(100)",
            "avatar_url": "VARCHAR(500)",
            "notifications_enabled": "BOOLEAN DEFAULT 1",
            "profile_picture": "VARCHAR(500)",
            "is_google_user": "BOOLEAN DEFAULT 0",
            "approval_status": "VARCHAR(20) DEFAULT 'approved'",
        }
        for col, ddl in user_additions.items():
            if col not in users_cols:
                cur.execute(f"ALTER TABLE users ADD COLUMN {col} {ddl}")

        # Make hashed_password nullable (Google-only accounts have no password).
        # SQLite cannot ALTER a column to drop NOT NULL, so rebuild the table
        # in place with the new nullability, preserving all existing rows.
        hp_nullable = False
        for row in cur.execute("PRAGMA table_info(users)").fetchall():
            if row[1] == "hashed_password":
                hp_nullable = row[3] == 0  # notnull flag: 0 = nullable
        if not hp_nullable:
            cur.execute("ALTER TABLE users RENAME TO users_old")
            cur.execute("""CREATE TABLE users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username VARCHAR(50) NOT NULL UNIQUE,
                email VARCHAR(100) NOT NULL UNIQUE,
                full_name VARCHAR(100),
                hashed_password VARCHAR(255),
                role VARCHAR(20) NOT NULL DEFAULT 'data_analyst',
                is_active BOOLEAN DEFAULT 1,
                google_id VARCHAR(100),
                profile_picture VARCHAR(500),
                is_google_user BOOLEAN DEFAULT 0,
                avatar_url VARCHAR(500),
                notifications_enabled BOOLEAN DEFAULT 1,
                approval_status VARCHAR(20) DEFAULT 'approved',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )""")
            cur.execute("""INSERT INTO users (id, username, email, full_name, hashed_password,
                role, is_active, google_id, profile_picture, is_google_user,
                avatar_url, notifications_enabled, approval_status, created_at)
                SELECT id, username, email, full_name, hashed_password,
                role, is_active, google_id, profile_picture, is_google_user,
                avatar_url, notifications_enabled, approval_status, created_at
                FROM users_old""")
            cur.execute("DROP TABLE users_old")
            # Recreate the named indexes SQLAlchemy expects (dropped with users_old)
            cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS ix_users_username ON users (username)")
            cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS ix_users_email ON users (email)")
            cur.execute("CREATE INDEX IF NOT EXISTS ix_users_google_id ON users (google_id)")

        # Datasets / import_logs tables (create_all handles them, but ensure they exist)
        # Backfill approval_status for pre-existing users (defaults to 'approved'
        # via the column default, but make it explicit so existing accounts work)
        try:
            cur.execute("UPDATE users SET approval_status = 'approved' WHERE approval_status IS NULL")
        except Exception:
            pass

        # Role set migration: the old 'business_user' role was replaced by
        # 'data_analyst' (the role set is now admin / data_analyst / pricing_manager)
        try:
            cur.execute("UPDATE users SET role = 'data_analyst' WHERE role = 'business_user'")
        except Exception:
            pass
        try:
            cur.execute("UPDATE access_requests SET requested_role = 'data_analyst' WHERE requested_role = 'business_user'")
        except Exception:
            pass

        # access_requests.reason column (create_all won't add columns to an
        # existing table - reconcile manually for pre-existing SQLite DBs)
        try:
            ar_cols = {row[1] for row in cur.execute("PRAGMA table_info(access_requests)").fetchall()}
            if "reason" not in ar_cols:
                cur.execute("ALTER TABLE access_requests ADD COLUMN reason TEXT")
        except Exception:
            pass

        existing = {row[0] for row in cur.execute(
            "SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
        if "datasets" not in existing:
            cur.execute("""CREATE TABLE datasets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name VARCHAR(200) NOT NULL,
                dataset_type VARCHAR(50) NOT NULL DEFAULT 'custom',
                file_name VARCHAR(255),
                source VARCHAR(20) DEFAULT 'upload',
                status VARCHAR(20) DEFAULT 'processed',
                rows INTEGER DEFAULT 0,
                columns INTEGER DEFAULT 0,
                missing_values INTEGER DEFAULT 0,
                duplicate_count INTEGER DEFAULT 0,
                category_count INTEGER DEFAULT 0,
                avg_price FLOAT DEFAULT 0,
                total_revenue FLOAT DEFAULT 0,
                health_score FLOAT DEFAULT 0,
                column_names TEXT DEFAULT '[]',
                pipeline_steps TEXT DEFAULT '[]',
                preview_rows TEXT DEFAULT '[]',
                error_message TEXT,
                created_by INTEGER,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )""")
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Schema migration skipped: {e}")


def _migrate_postgres():
    """PostgreSQL-specific non-destructive migration.

    The SQLAlchemy User model gained google_id, profile_picture and
    is_google_user columns, and hashed_password became nullable (Google-only
    accounts store password=NULL). An existing PostgreSQL users table is
    updated in place: missing columns are added, NOT NULL is dropped from
    hashed_password, and the google_id index is created - without touching
    existing rows, other columns, or existing indexes. Idempotent: every step
    checks current state first, so re-runs are safe no-ops.
    """
    try:
        import psycopg2
        conn = psycopg2.connect(DATABASE_URL)
        conn.autocommit = True
        cur = conn.cursor()

        # Skip entirely if the table doesn't exist yet (fresh DB -> create_all builds it)
        cur.execute("SELECT to_regclass('public.users')")
        if cur.fetchone()[0] is None:
            conn.close()
            return

        # Discover existing columns
        cur.execute(
            """SELECT column_name FROM information_schema.columns
               WHERE table_schema = 'public' AND table_name = 'users'"""
        )
        existing = {row[0] for row in cur.fetchall()}

        # 1. Add columns introduced after the original schema
        additions = {
            "google_id": "VARCHAR(100)",
            "avatar_url": "VARCHAR(500)",
            "notifications_enabled": "BOOLEAN DEFAULT TRUE",
            "profile_picture": "VARCHAR(500)",
            "is_google_user": "BOOLEAN DEFAULT FALSE",
            "approval_status": "VARCHAR(20) DEFAULT 'approved'",
        }
        for col, ddl in additions.items():
            if col not in existing:
                cur.execute(f"ALTER TABLE users ADD COLUMN {col} {ddl}")
                print(f"PostgreSQL migration: added users.{col}")

        # 2. hashed_password must become nullable for Google-only accounts
        cur.execute(
            """SELECT is_nullable FROM information_schema.columns
               WHERE table_schema = 'public' AND table_name = 'users'
                 AND column_name = 'hashed_password'"""
        )
        row = cur.fetchone()
        if row and row[0] == "NO":
            cur.execute("ALTER TABLE users ALTER COLUMN hashed_password DROP NOT NULL")
            print("PostgreSQL migration: hashed_password is now nullable")

        # 3. Create the google_id index the model declares (create_all won't
        #    add indexes to an already-existing table)
        cur.execute("CREATE INDEX IF NOT EXISTS ix_users_google_id ON users (google_id)")

        # 3b. Backfill approval_status for existing accounts: every pre-existing
        #     user stays approved and keeps working (only new self-registrations
        #     are 'pending').
        cur.execute("UPDATE users SET approval_status = 'approved' WHERE approval_status IS NULL")

        # 3c. Role set migration: 'business_user' was replaced by 'data_analyst'
        #     (the role set is now admin / data_analyst / pricing_manager).
        cur.execute("UPDATE users SET role = 'data_analyst' WHERE role = 'business_user'")
        print("PostgreSQL migration: migrated business_user role to data_analyst")
        cur.execute("UPDATE access_requests SET requested_role = 'data_analyst' WHERE requested_role = 'business_user'")

        # 4. Reconcile the remaining model tables against the current SQLAlchemy
        #    models. Pre-existing tables may predate columns added later (e.g.
        #    products.image_url/status, sales.customer_segment,
        #    recommendations.factors_considered) which crashes every full-model
        #    SELECT. Additive + idempotent: missing columns are added as
        #    nullable (with a constant default when the model declares one),
        #    existing data and columns are never touched.
        from sqlalchemy import Integer, Float, Boolean, DateTime, String, Text as SAText  # noqa: F401

        def _column_ddl(col):
            t = col.type
            if isinstance(t, Integer):
                sql_type = "INTEGER"
            elif isinstance(t, Float):
                sql_type = "DOUBLE PRECISION"
            elif isinstance(t, Boolean):
                sql_type = "BOOLEAN"
            elif isinstance(t, DateTime):
                sql_type = "TIMESTAMP"
            elif isinstance(t, SAText):
                sql_type = "TEXT"
            elif isinstance(t, String):
                sql_type = f"VARCHAR({t.length or 255})"
            else:
                sql_type = "TEXT"
            ddl = f"{col.name} {sql_type}"
            default = col.default.arg if col.default is not None else None
            if default is not None and not callable(default):
                if isinstance(default, bool):
                    ddl += f" DEFAULT {'TRUE' if default else 'FALSE'}"
                elif isinstance(default, (int, float)):
                    ddl += f" DEFAULT {default}"
                elif isinstance(default, str):
                    ddl += f" DEFAULT '{default.replace(chr(39), chr(39)*2)}'"
            return ddl

        # Lazy imports to avoid a circular import (models import Base from this module)
        from app.models.product import Product
        from app.models.sales import Sale
        from app.models.recommendation import Recommendation
        from app.models.dataset import Dataset, ImportLog
        from app.models.pricing_history import PricingHistory
        from app.models.activity_log import ActivityLog
        from app.models.forecast import ForecastRun
        from app.models.access_request import AccessRequest
        from app.models.model_run import ModelRun

        reconcile = [
            ("products", Product), ("sales", Sale),
            ("recommendations", Recommendation), ("datasets", Dataset),
            ("import_logs", ImportLog), ("pricing_history", PricingHistory),
            ("activity_logs", ActivityLog), ("forecast_runs", ForecastRun),
            ("access_requests", AccessRequest), ("model_runs", ModelRun),
        ]

        # Analytics cache table (created via create_all, but columns added here
        # for pre-existing databases)
        from app.models.analytics_cache import AnalyticsCache
        cur.execute("SELECT to_regclass('public.analytics_cache')")
        if cur.fetchone()[0] is not None:
            cur.execute(
                """SELECT column_name FROM information_schema.columns
                   WHERE table_schema = 'public' AND table_name = 'analytics_cache'"""
            )
            existing_ac = {row[0] for row in cur.fetchall()}
            for col in AnalyticsCache.__table__.columns:
                if col.name in existing_ac or col.primary_key:
                    continue
                cur.execute(f"ALTER TABLE analytics_cache ADD COLUMN {_column_ddl(col)}")
                print(f"PostgreSQL migration: added analytics_cache.{col.name}")
        for table_name, model in reconcile:
            cur.execute("SELECT to_regclass(%s)", (f"public.{table_name}",))
            if cur.fetchone()[0] is None:
                continue
            cur.execute(
                """SELECT column_name FROM information_schema.columns
                   WHERE table_schema = 'public' AND table_name = %s""",
                (table_name,),
            )
            existing = {row[0] for row in cur.fetchall()}
            for col in model.__table__.columns:
                if col.name in existing or col.primary_key:
                    continue
                cur.execute(f"ALTER TABLE {table_name} ADD COLUMN {_column_ddl(col)}")
                print(f"PostgreSQL migration: added {table_name}.{col.name}")

        # 5. Backfill legacy renamed columns so historical rows keep their data
        #    after the additive migration above (no silent data loss).
        #    legacy -> current pairs discovered from the old schema.
        backfills = [
            ("recommendations", "factors", "factors_considered"),
            ("recommendations", "expected_revenue_change", "expected_revenue_impact"),
            ("sales", "customer_type", "customer_segment"),
        ]
        for table_name, legacy_col, new_col in backfills:
            cur.execute("SELECT to_regclass(%s)", (f"public.{table_name}",))
            if cur.fetchone()[0] is None:
                continue
            cur.execute(
                """SELECT column_name FROM information_schema.columns
                   WHERE table_schema = 'public' AND table_name = %s""",
                (table_name,),
            )
            cols = {row[0] for row in cur.fetchall()}
            if legacy_col in cols and new_col in cols:
                cur.execute(
                    f"UPDATE {table_name} SET {new_col} = {legacy_col} "
                    f"WHERE {new_col} IS NULL AND {legacy_col} IS NOT NULL"
                )
                if cur.rowcount:
                    print(f"PostgreSQL migration: backfilled {table_name}.{new_col} "
                          f"({cur.rowcount} row(s))")

        conn.close()
    except Exception as e:
        print(f"PostgreSQL schema migration skipped: {e}")
