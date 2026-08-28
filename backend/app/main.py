"""
PricePilot AI - Dynamic Pricing & Revenue Intelligence System
Main Application Entry Point
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.config import settings
from app.database import engine, Base
from app.mongodb import mongo_db

# Core routers
from app.routers import auth
from app.routers import products
from app.routers import dashboard
from app.routers import pricing
from app.routers import datasets
from app.routers import users
from app.routers import access_requests

# Enterprise modules
from app.routers import ai
from app.routers import reports
from app.routers import sales
from app.routers import activity
from app.routers import competitors
from app.routers import market_intelligence
from app.routers import profitability
from app.routers import pricing_strategy
from app.routers import business_intelligence

# Data loaders
from app.loaders.retail_loader import router as retail_router
from app.loaders.ecommerce_loader import router as ecommerce_router
from app.seed_data import seed_database


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Non-destructive migration for pre-existing databases (adds new columns/tables)
    from app.database import migrate_schema
    migrate_schema()

    # Create database tables on startup (includes new Dataset / ImportLog /
    # Recommendation / AccessRequest models)
    import app.models.dataset  # noqa: F401 - register models
    import app.models.recommendation  # noqa: F401
    import app.models.access_request  # noqa: F401
    import app.models.model_run  # noqa: F401 - persisted AI training runs
    import app.models.analytics_cache  # noqa: F401 - analytics cache
    Base.metadata.create_all(bind=engine)
    
    # Seed sample products if database is empty
    from app.database import SessionLocal
    db = SessionLocal()
    try:
        seed_database(db)
    except Exception as e:
        print(f"Seeding skipped: {e}")
    finally:
        db.close()
    
    # Connect to MongoDB
    try:
        await mongo_db.connect()
    except Exception as e:
        print(f"MongoDB connection skipped: {e}")
    
    yield
    
    # Cleanup on shutdown
    await mongo_db.close()


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API Routes
app.include_router(auth.router)
app.include_router(products.router)
app.include_router(dashboard.router)
app.include_router(pricing.router)
app.include_router(datasets.router)
app.include_router(users.router)
app.include_router(access_requests.router)
app.include_router(ai.router)
app.include_router(reports.router)
app.include_router(sales.router)
app.include_router(activity.router)
app.include_router(competitors.router)
app.include_router(market_intelligence.router)
app.include_router(profitability.router)
app.include_router(pricing_strategy.router)
app.include_router(business_intelligence.router)

# Data Loaders
app.include_router(retail_router)
app.include_router(ecommerce_router)


@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "version": settings.APP_VERSION,
        "name": settings.APP_NAME,
    }
