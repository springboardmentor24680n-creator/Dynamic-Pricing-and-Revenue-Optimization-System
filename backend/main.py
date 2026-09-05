import os
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
import requests

from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from passlib.context import CryptContext
from pydantic import BaseModel, Field
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import sessionmaker, declarative_base, Session

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
BACKEND_DIR = Path(__file__).resolve().parent
DATABASE_URL = f"sqlite:///{BASE_DIR / 'pricepilot.db'}"
SECRET_KEY = "change-this-secret-key"
ALGORITHM = "HS256"
ALLOWED_ROLES = {"admin", "pricing manager", "business analyst"}


# Load environment variables
load_dotenv(dotenv_path=BACKEND_DIR / ".env")
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")

from database.postgres import POSTGRES_URL
if POSTGRES_URL:
    DATABASE_URL = POSTGRES_URL

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

app = FastAPI(title="PricePilot AI API")

# Register AI router
from routes.ai import router as ai_router
app.include_router(ai_router)

# Register Dashboard router
from routes.dashboard import router as dashboard_router
app.include_router(dashboard_router)

# Register Seasonal Trends router
from routes.seasonal_trends import router as seasonal_trends_router
app.include_router(seasonal_trends_router)

# Register Competitor Monitoring router
from routes.competitor_monitoring import router as competitor_monitoring_router
app.include_router(competitor_monitoring_router)

# Register Pricing Comparison router
from routes.pricing_comparison import router as pricing_comparison_router
app.include_router(pricing_comparison_router)

# Register Market Intelligence router
from routes.market_intelligence import router as market_intelligence_router
app.include_router(market_intelligence_router)

# Register Profitability Analytics router
from routes.profitability import router as profitability_router
app.include_router(profitability_router)

# Register Pricing Strategy router
from routes.pricing_strategy import router as pricing_strategy_router
app.include_router(pricing_strategy_router)

# Register Executive BI router
from routes.executive_bi import router as executive_bi_router
app.include_router(executive_bi_router)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "http://0.0.0.0:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    name = Column(String)
    email = Column(String, unique=True, index=True)
    password_hash = Column(String)
    role = Column(String, default="manager")


class Product(Base):
    __tablename__ = "products"

    id = Column(String(50), primary_key=True)
    name = Column(String)
    category = Column(String)
    current_price = Column(Float)
    cost_price = Column(Float)
    stock = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_competitor_scan = Column(DateTime, nullable=True)
    next_competitor_scan = Column(DateTime, nullable=True, index=True, default=datetime.utcnow)
    monitoring_priority = Column(String(20), default="MEDIUM", index=True)


class SalesRecord(Base):
    __tablename__ = "sales_records"

    id = Column(Integer, primary_key=True)
    product_name = Column(String)
    units_sold = Column(Integer)
    revenue = Column(Float)
    price = Column(Float)


class CompetitorPrice(Base):
    __tablename__ = "competitor_prices"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(String(50), ForeignKey("products.id"), index=True)
    competitor_name = Column(String, index=True)
    competitor_product_name = Column(String)
    competitor_url = Column(String)
    competitor_price = Column(Float)
    currency = Column(String, default="USD")
    availability = Column(String, default="In Stock")
    last_checked = Column(DateTime, default=datetime.utcnow, index=True)
    previous_price = Column(Float, nullable=True)
    price_change = Column(Float, nullable=True)
    price_change_percent = Column(Float, nullable=True)
    data_source = Column(String(50), default="mock_fallback", nullable=True, index=True)
    rating = Column(Float, nullable=True)
    review_count = Column(Integer, nullable=True)
    relevance_score = Column(Float, nullable=True)


class CompetitorPriceHistory(Base):
    __tablename__ = "competitor_price_history"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(String(50), ForeignKey("products.id"), index=True)
    competitor_name = Column(String, index=True)
    competitor_price = Column(Float)
    currency = Column(String, default="USD")
    last_checked = Column(DateTime, default=datetime.utcnow, index=True)
    data_source = Column(String(50), default="mock_fallback", nullable=True, index=True)
    rating = Column(Float, nullable=True)
    review_count = Column(Integer, nullable=True)
    relevance_score = Column(Float, nullable=True)


class CompetitorAlert(Base):
    __tablename__ = "competitor_alerts"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(String(50), ForeignKey("products.id"), index=True)
    competitor_name = Column(String, index=True)
    event_type = Column(String, index=True)
    previous_price = Column(Float, nullable=True)
    current_price = Column(Float)
    change_amount = Column(Float, nullable=True)
    change_percent = Column(Float, nullable=True)
    severity = Column(String)
    message = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    is_acknowledged = Column(Boolean, default=False)
    data_source = Column(String(50), default="mock_fallback", nullable=True)


class CompetitorMonitoringRun(Base):
    __tablename__ = "monitoring_runs"

    id = Column(Integer, primary_key=True, index=True)
    started_at = Column(DateTime, default=datetime.utcnow, index=True)
    completed_at = Column(DateTime, nullable=True)
    status = Column(String, index=True)
    source = Column(String)
    products_checked = Column(Integer, default=0)
    raw_products = Column(Integer, default=0)
    normalized_products = Column(Integer, default=0)
    relevant_competitors = Column(Integer, default=0)
    price_updates = Column(Integer, default=0)
    alerts_created = Column(Integer, default=0)
    api_requests = Column(Integer, default=0)
    fallback_used = Column(Boolean, default=False)
    error_message = Column(String, nullable=True)
    primary_provider = Column(String(50), nullable=True)
    successful_provider = Column(String(50), nullable=True)
    prices_api_requests = Column(Integer, default=0)
    openweb_ninja_requests = Column(Integer, default=0)


Base.metadata.create_all(bind=engine)


def run_schema_migrations():
    from sqlalchemy import text, inspect
    inspector = inspect(engine)
    
    alterations = [
        ("competitor_prices", "data_source", "VARCHAR(50) DEFAULT 'mock_fallback'"),
        ("competitor_prices", "rating", "DOUBLE PRECISION"),
        ("competitor_prices", "review_count", "INTEGER"),
        ("competitor_prices", "relevance_score", "DOUBLE PRECISION"),
        ("competitor_price_history", "data_source", "VARCHAR(50) DEFAULT 'mock_fallback'"),
        ("competitor_price_history", "rating", "DOUBLE PRECISION"),
        ("competitor_price_history", "review_count", "INTEGER"),
        ("competitor_price_history", "relevance_score", "DOUBLE PRECISION"),
        ("competitor_alerts", "data_source", "VARCHAR(50) DEFAULT 'mock_fallback'"),
        ("products", "last_competitor_scan", "TIMESTAMP"),
        ("products", "next_competitor_scan", "TIMESTAMP"),
        ("products", "monitoring_priority", "VARCHAR(20) DEFAULT 'MEDIUM'"),
        ("monitoring_runs", "primary_provider", "VARCHAR(50)"),
        ("monitoring_runs", "successful_provider", "VARCHAR(50)"),
        ("monitoring_runs", "prices_api_requests", "INTEGER DEFAULT 0"),
        ("monitoring_runs", "openweb_ninja_requests", "INTEGER DEFAULT 0"),
    ]
    
    is_sqlite = "sqlite" in str(engine.url)
    
    with engine.begin() as conn:
        for table, col, col_type in alterations:
            try:
                columns = [c["name"] for c in inspector.get_columns(table)]
                if col not in columns:
                    type_str = "FLOAT" if "DOUBLE PRECISION" in col_type and is_sqlite else col_type
                    conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {col} {type_str}"))
                    print(f"Migration: Added column '{col}' to table '{table}'")
            except Exception as e:
                print(f"Migration warning (table {table}, column {col}): {e}")
                
        # Index creation migrations
        indices_to_create = [
            ("idx_products_next_scan", "products", "next_competitor_scan"),
            ("idx_products_priority", "products", "monitoring_priority"),
            ("idx_alerts_created_at", "competitor_alerts", "created_at"),
            ("idx_history_last_checked", "competitor_price_history", "last_checked"),
            ("idx_competitor_prices_data_source", "competitor_prices", "data_source"),
            ("idx_competitor_prices_last_checked", "competitor_prices", "last_checked"),
            ("idx_competitor_history_data_source", "competitor_price_history", "data_source"),
        ]
        for idx_name, table, col in indices_to_create:
            try:
                conn.execute(text(f"CREATE INDEX IF NOT EXISTS {idx_name} ON {table} ({col})"))
                print(f"Migration: Created index '{idx_name}' on '{table}({col})'")
            except Exception as e:
                try:
                    conn.execute(text(f"CREATE INDEX {idx_name} ON {table} ({col})"))
                except Exception as inner_e:
                    print(f"Migration warning (index {idx_name}): {inner_e}")


run_schema_migrations()

INITIAL_PRODUCTS = [
    {"id": "elec_headphones", "name": "Wireless Headphones", "category": "Audio", "current_price": 1999.0, "cost_price": 1299.0, "stock": 85},
    {"id": "elec_smartwatch", "name": "Smartwatch", "category": "Wearables", "current_price": 3499.0, "cost_price": 2299.0, "stock": 64},
    {"id": "elec_speaker", "name": "Bluetooth Speaker", "category": "Audio", "current_price": 1499.0, "cost_price": 899.0, "stock": 92},
    {"id": "elec_mouse", "name": "Gaming Mouse", "category": "Peripherals", "current_price": 1199.0, "cost_price": 699.0, "stock": 120},
    {"id": "elec_keyboard", "name": "Mechanical Keyboard", "category": "Peripherals", "current_price": 2499.0, "cost_price": 1599.0, "stock": 78},
    {"id": "elec_monitor", "name": "4K Monitor", "category": "Displays", "current_price": 18999.0, "cost_price": 12999.0, "stock": 47},
    {"id": "elec_laptop", "name": "Laptop", "category": "Computers", "current_price": 59999.0, "cost_price": 44999.0, "stock": 36},
    {"id": "elec_smartphone", "name": "Smartphone", "category": "Mobiles", "current_price": 39999.0, "cost_price": 29999.0, "stock": 55},
    {"id": "elec_tablet", "name": "Tablet", "category": "Mobiles", "current_price": 27999.0, "cost_price": 19999.0, "stock": 41},
    {"id": "elec_webcam", "name": "Webcam", "category": "Accessories", "current_price": 3499.0, "cost_price": 2299.0, "stock": 70},
    {"id": "elec_ssd", "name": "External SSD", "category": "Storage", "current_price": 8999.0, "cost_price": 5999.0, "stock": 63},
    {"id": "elec_charger", "name": "Portable Charger", "category": "Accessories", "current_price": 1999.0, "cost_price": 1199.0, "stock": 88},
    {"id": "elec_lamp", "name": "Smart Lamp", "category": "Home", "current_price": 2999.0, "cost_price": 1899.0, "stock": 52},
    {"id": "elec_band", "name": "Fitness Band", "category": "Wearables", "current_price": 2499.0, "cost_price": 1499.0, "stock": 74},
    {"id": "elec_earbuds", "name": "Noise-Canceling Earbuds", "category": "Audio", "current_price": 2999.0, "cost_price": 1799.0, "stock": 91},
]

INITIAL_SALES = [
    {"product_name": "Wireless Headphones", "units_sold": 48, "revenue": 95952.0, "price": 1999.0},
    {"product_name": "Smartwatch", "units_sold": 36, "revenue": 125964.0, "price": 3499.0},
    {"product_name": "Bluetooth Speaker", "units_sold": 54, "revenue": 80946.0, "price": 1499.0},
    {"product_name": "Gaming Mouse", "units_sold": 72, "revenue": 86328.0, "price": 1199.0},
    {"product_name": "Mechanical Keyboard", "units_sold": 41, "revenue": 102459.0, "price": 2499.0},
    {"product_name": "4K Monitor", "units_sold": 27, "revenue": 512973.0, "price": 18999.0},
    {"product_name": "Laptop", "units_sold": 19, "revenue": 1_139_981.0, "price": 59999.0},
    {"product_name": "Smartphone", "units_sold": 33, "revenue": 1_319_967.0, "price": 39999.0},
    {"product_name": "Tablet", "units_sold": 22, "revenue": 615_978.0, "price": 27999.0},
    {"product_name": "Webcam", "units_sold": 60, "revenue": 209_940.0, "price": 3499.0},
    {"product_name": "External SSD", "units_sold": 28, "revenue": 251_972.0, "price": 8999.0},
    {"product_name": "Portable Charger", "units_sold": 67, "revenue": 133_933.0, "price": 1999.0},
    {"product_name": "Smart Lamp", "units_sold": 31, "revenue": 92_969.0, "price": 2999.0},
    {"product_name": "Fitness Band", "units_sold": 45, "revenue": 112_455.0, "price": 2499.0},
    {"product_name": "Noise-Canceling Earbuds", "units_sold": 58, "revenue": 173_942.0, "price": 2999.0},
]


def normalize_role(role: str) -> str:
    normalized = (role or "pricing manager").strip().lower()

    if normalized in {"admin", "administrator"}:
        return "admin"
    if normalized in {"manager", "pricing_manager", "pricing manager"}:
        return "pricing manager"
    if normalized in {"business_analyst", "business analyst", "analyst"}:
        return "business analyst"
    if normalized in {"user", "customer", "end_user", "end user"}:
        return "business analyst"

    return "pricing manager"


def seed_initial_data(db: Session):
    # 1. Clear old non-electronics products
    allowed_ids = {p["id"] for p in INITIAL_PRODUCTS}
    db.query(Product).filter(~Product.id.in_(allowed_ids)).delete(synchronize_session=False)
    db.commit()

    # 2. Seed INITIAL_PRODUCTS if not already present
    for p_data in INITIAL_PRODUCTS:
        existing = db.query(Product).filter(Product.id == p_data["id"]).first()
        if not existing:
            product = Product(
                id=p_data["id"],
                name=p_data["name"],
                category=p_data["category"],
                current_price=p_data["current_price"],
                cost_price=p_data["cost_price"],
                stock=p_data["stock"]
            )
            db.add(product)
    db.commit()

    # 3. Clear old non-electronics sales records
    allowed_names = {p["name"] for p in INITIAL_PRODUCTS}
    db.query(SalesRecord).filter(~SalesRecord.product_name.in_(allowed_names)).delete(synchronize_session=False)
    db.commit()

    # 4. Seed INITIAL_SALES if not already present
    for s_data in INITIAL_SALES:
        existing = db.query(SalesRecord).filter(SalesRecord.product_name == s_data["product_name"]).first()
        if not existing:
            record = SalesRecord(
                product_name=s_data["product_name"],
                units_sold=s_data["units_sold"],
                revenue=s_data["revenue"],
                price=s_data["price"]
            )
            db.add(record)
    db.commit()

    demo_users = [
        {
            "name": "Administrator",
            "email": "admin@revenueiq.com",
            "password": "admin123",
            "role": "admin",
        },
        {
            "name": "Pricing Manager",
            "email": "manager@revenueiq.com",
            "password": "manager123",
            "role": "pricing manager",
        },
        {
            "name": "Business Analyst",
            "email": "analyst@revenueiq.com",
            "password": "analyst123",
            "role": "business analyst",
        },
        {
            "name": "Standard User",
            "email": "user@revenueiq.com",
            "password": "user123",
            "role": "business analyst",
        },
    ]

    for demo_user in demo_users:
        existing = db.query(User).filter(User.email == demo_user["email"]).first()
        if existing is None:
            db.add(
                User(
                    name=demo_user["name"],
                    email=demo_user["email"],
                    password_hash=hash_password(demo_user["password"]),
                    role=normalize_role(demo_user["role"]),
                )
            )
        else:
            existing.name = demo_user["name"]
            existing.role = normalize_role(demo_user["role"])
            existing.password_hash = hash_password(demo_user["password"])

    db.commit()


def seed_competitor_data(db: Session):
    # Retrieve all products
    products = db.query(Product).all()
    if not products:
        return
        
    from services.competitor_monitoring_service import CompetitorMonitoringService
    service = CompetitorMonitoringService()
    
    # We populate latest competitor price and some history entries for each product
    for product in products:
        # Check if we already have competitor prices for this product
        existing = db.query(CompetitorPrice).filter(CompetitorPrice.product_id == product.id).first()
        if not existing:
            # Let's seed mock prices
            mock_data = service.get_mock_data(product.id, db)
            for item in mock_data:
                # Add latest price
                comp_price_rec = CompetitorPrice(
                    product_id=item["product_id"],
                    competitor_name=item["competitor_name"],
                    competitor_product_name=item["competitor_product_name"],
                    competitor_url=item["competitor_url"],
                    competitor_price=item["competitor_price"],
                    currency=item["currency"],
                    availability=item["availability"],
                    last_checked=datetime.utcnow() - timedelta(days=2),
                    previous_price=round(item["competitor_price"] * 0.98, 2),
                    price_change=round(item["competitor_price"] - round(item["competitor_price"] * 0.98, 2), 2),
                    price_change_percent=2.0
                )
                db.add(comp_price_rec)
                
                # Add price history
                history_rec1 = CompetitorPriceHistory(
                    product_id=item["product_id"],
                    competitor_name=item["competitor_name"],
                    competitor_price=round(item["competitor_price"] * 0.98, 2),
                    currency=item["currency"],
                    last_checked=datetime.utcnow() - timedelta(days=5)
                )
                history_rec2 = CompetitorPriceHistory(
                    product_id=item["product_id"],
                    competitor_name=item["competitor_name"],
                    competitor_price=item["competitor_price"],
                    currency=item["currency"],
                    last_checked=datetime.utcnow() - timedelta(days=2)
                )
                db.add(history_rec1)
                db.add(history_rec2)
                
    db.commit()


class RegisterRequest(BaseModel):
    name: str
    email: str
    password: str
    role: str = "manager"


class LoginRequest(BaseModel):
    email: str
    password: str


class GoogleAuthRequest(BaseModel):
    credential: str = ""
    email: str = ""
    name: str = ""
    role: str = "business analyst"


class ProductRequest(BaseModel):
    name: str = Field(min_length=1)
    category: str = Field(min_length=1)
    current_price: float = Field(ge=0)
    cost_price: float = Field(ge=0)
    stock: int = Field(ge=0)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def to_dict(instance):
    return {column.name: getattr(instance, column.name) for column in instance.__table__.columns}


def hash_password(password):
    return pwd_context.hash(password)


def verify_password(password, password_hash):
    return pwd_context.verify(password, password_hash)


def create_token(data: dict):
    payload = data.copy()
    payload["exp"] = datetime.utcnow() + timedelta(hours=8)
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def verify_google_token(credential: str):
    if not credential:
        return None

    try:
        response = requests.get(
            f"https://oauth2.googleapis.com/tokeninfo?id_token={credential}",
            timeout=5,
        )
    except requests.RequestException:
        return None

    if response.status_code != 200:
        return None

    payload = response.json()

    if GOOGLE_CLIENT_ID and payload.get("aud") not in {GOOGLE_CLIENT_ID, None}:
        return None

    return payload


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

    user = db.query(User).filter(User.email == email).first()

    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    return user


@app.on_event("startup")
def initialize_database():
    try:
        from database.health import run_database_health_checks
        run_database_health_checks()
    except Exception as e:
        print(f"Error running database health checks: {e}")

    db = SessionLocal()
    try:
        seed_initial_data(db)
        try:
            seed_competitor_data(db)
        except Exception as ce:
            print(f"Error seeding competitor data: {ce}")
    finally:
        db.close()

    try:
        from services.scheduler import start_scheduler
        start_scheduler()
    except Exception as se:
        print(f"Error starting scheduler: {se}")


@app.on_event("shutdown")
def shutdown_scheduler():
    try:
        from services.scheduler import stop_scheduler
        stop_scheduler()
    except Exception as e:
        print(f"Error stopping scheduler: {e}")


@app.get("/")
def home():
    return {"message": "PricePilot AI backend running"}


@app.post("/auth/register")
def register(data: RegisterRequest, db: Session = Depends(get_db)):
    existing_user = db.query(User).filter(User.email == data.email).first()

    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    role = normalize_role(data.role)
    user = User(
        name=data.name,
        email=data.email,
        password_hash=hash_password(data.password),
        role=role,
    )

    db.add(user)
    db.commit()

    return {"message": "User registered successfully"}


@app.post("/auth/login")
def login(data: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == data.email).first()

    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token = create_token({"sub": user.email, "role": user.role})

    return {
        "access_token": token,
        "token_type": "bearer",
        "role": user.role,
    }


@app.post("/auth/google")
def google_login(data: GoogleAuthRequest, db: Session = Depends(get_db)):
    payload = verify_google_token(data.credential)

    if payload:
        email = payload.get("email")
        name = payload.get("name") or data.name or (email.split("@", 1)[0] if email else "Google User")
    else:
        email = data.email
        name = data.name or (email.split("@", 1)[0] if email else "Google User")

    if not email:
        raise HTTPException(status_code=400, detail="Google email is required")

    role = normalize_role(data.role)
    user = db.query(User).filter(User.email == email).first()

    if not user:
        user = User(
            name=name,
            email=email,
            password_hash=hash_password(os.urandom(16).hex()),
            role=role,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    else:
        user.name = name or user.name
        user.role = role
        db.commit()

    token = create_token({"sub": user.email, "role": user.role})

    return {
        "access_token": token,
        "token_type": "bearer",
        "role": user.role,
        "user_name": user.name,
    }


@app.get("/api/forecast/{product_id}")
def get_product_forecast(
    product_id: str,
    competitor_price: float = Query(None),
    user: User = Depends(get_current_user)
):
    from services.demand_forecast_service import DemandForecastService
    try:
        service = DemandForecastService()
        return service.get_forecast_for_product(product_id, competitor_price=competitor_price)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/products")
def create_product(
    data: ProductRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    import uuid
    # Product.id is a String(50) primary key — must supply one explicitly
    product = Product(
        id=str(uuid.uuid4())[:20],
        **data.dict()
    )

    db.add(product)
    db.commit()
    db.refresh(product)

    return to_dict(product)


@app.get("/products")
def list_products(db: Session = Depends(get_db)):
    products = db.query(Product).all()
    return [to_dict(product) for product in products]


@app.get("/sales")
def get_sales(db: Session = Depends(get_db)):
    sales = db.query(SalesRecord).all()
    return [to_dict(record) for record in sales]


@app.get("/sales/count")
def get_sales_count(db: Session = Depends(get_db)):
    return {"sales_count": db.query(SalesRecord).count()}


@app.get("/sales/sample")
def get_sales_sample(db: Session = Depends(get_db)):
    sales = db.query(SalesRecord).order_by(SalesRecord.id).limit(10).all()
    return [to_dict(record) for record in sales]


@app.put("/products/{product_id}")
def update_product(
    product_id: str,
    data: ProductRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    product = db.query(Product).filter(Product.id == product_id).first()

    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    product.name = data.name
    product.category = data.category
    product.current_price = data.current_price
    product.cost_price = data.cost_price
    product.stock = data.stock

    db.commit()
    db.refresh(product)

    return product


@app.delete("/products/{product_id}")
def delete_product(
    product_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    product = db.query(Product).filter(Product.id == product_id).first()

    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    db.delete(product)
    db.commit()

    return {"message": "Product deleted"}


@app.post("/datasets/upload-sales")
def upload_sales_dataset(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    df = pd.read_csv(file.file)

    # Support both the original schema and common retail CSV columns
    required_columns = {"product_name", "price", "quantity_sold"}
    if not required_columns.issubset(df.columns):
        raise HTTPException(
            status_code=400,
            detail="CSV must contain product_name, price, quantity_sold",
        )

    for _, row in df.iterrows():
        product_name = row["product_name"]
        price = float(row["price"])
        units_sold = int(row.get("quantity_sold", row.get("units_sold", 0)))
        revenue = float(row.get("revenue", price * units_sold))

        record = SalesRecord(
            product_name=product_name,
            units_sold=units_sold,
            revenue=revenue,
            price=price,
        )
        db.add(record)

    db.commit()

    return {
        "message": "Dataset uploaded successfully",
        "rows": len(df),
    }


@app.get("/dashboard")
def dashboard(db: Session = Depends(get_db)):
    products = db.query(Product).all()
    sales = db.query(SalesRecord).all()

    total_revenue = sum(s.revenue for s in sales)
    total_units = sum(s.units_sold for s in sales)

    if products:
        average_price = sum(p.current_price for p in products) / len(products)
    else:
        average_price = 0

    return {
        "total_products": len(products),
        "total_revenue": total_revenue,
        "total_units_sold": total_units,
        "average_product_price": round(average_price, 2),
    }