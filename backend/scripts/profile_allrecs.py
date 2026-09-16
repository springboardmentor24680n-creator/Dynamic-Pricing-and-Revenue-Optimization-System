"""Break down the cost phases inside PricingStrategyService.all_recommendations."""
import time
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models.product import Product
from app.services.training_service import _sales_aggregates, ModelTrainingService
from app.services.pricing_strategy_service import PricingStrategyService
from app.services.forecast_service import ForecastService
from app.services.competitor_service import CompetitorService
from app.services.ml_service import PricingMLService

db = SessionLocal()
svc = PricingStrategyService(db)

# Phase 1: products query + aggregates
t0 = time.time()
query = db.query(Product).filter(Product.status == "active")
products = query.all()
t1 = time.time()
print(f"products query: {(t1-t0)*1000:.0f} ms ({len(products)} products)")

t0 = time.time()
aggregates = _sales_aggregates(db)
t1 = time.time()
print(f"aggregates (maybe cached): {(t1-t0)*1000:.0f} ms")

# Phase 2: load model
t0 = time.time()
model, feature_cols, run = ModelTrainingService(db).load_model()
t1 = time.time()
print(f"load model: {(t1-t0)*1000:.0f} ms run={run.id if run else None}")

# Phase 3: build training frame (for elasticity batch)
t0 = time.time()
training_frame = ModelTrainingService(db).build_training_frame()
t1 = time.time()
print(f"build_training_frame: {(t1-t0)*1000:.0f} ms")

# Phase 4: batch ML predictions first 200
t0 = time.time()
ml = PricingMLService(db)
batch_products = [p.id for p in products][:200]
cnt = 0
for pid in batch_products:
    try:
        pred = ml.predict_product(pid, aggregates=aggregates, training_frame=training_frame,
                                  model=model, feature_cols=feature_cols, run=run)
        cnt += 1
    except Exception:
        pass
t1 = time.time()
print(f"batch ml predict 200 products: {(t1-t0)*1000:.0f} ms ({cnt} ok) -> avg {(t1-t0)*1000/max(len(batch_products),1):.0f} ms/prod")

# Phase 5: competitor + demand per product (subset measure, extrapolate)
cs = CompetitorService(db)
fs = ForecastService(db)
t0 = time.time()
for p in products[:50]:
    try:
        svc._get_competitor_data(p.id)
    except Exception:
        pass
t1 = time.time()
print(f"competitor x50: {(t1-t0)*1000:.0f} ms -> x398 ~ {(t1-t0)*1000/50*398:.0f} ms")

t0 = time.time()
for p in products[:50]:
    try:
        svc._get_demand_data(p.id)
    except Exception:
        pass
t1 = time.time()
print(f"demand x50: {(t1-t0)*1000:.0f} ms -> x398 ~ {(t1-t0)*1000/50*398:.0f} ms")

# Phase 6: one full build rec
p = products[0]
cur = p.current_price or 0
cost = p.cost_price or 0
t0 = time.time()
try:
    sales_data = svc._get_sales_data_cached(p.id, aggregates)
    ml_data = {"suggested_price": 1005.73, "confidence_score": 83.6, "factors": [], "expected_revenue": 0, "expected_profit": 0, "insufficient_data": False}
    comp = svc._get_competitor_data(p.id)
    dem = svc._get_demand_data(p.id)
    margin = (cur - cost) / cur * 100 if cur else 0
    rec = svc._build_recommendation(p, cur, cost, margin, ml_data, sales_data, comp, dem)
    t1 = time.time()
    print(f"single _build_recommendation (with cached inputs): {(t1-t0)*1000:.0f} ms")
except Exception as e:
    print("build failed", e)

db.close()
