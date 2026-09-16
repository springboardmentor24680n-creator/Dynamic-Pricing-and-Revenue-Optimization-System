"""Profile pricing strategy + profitability hotspots - temporary diagnostic script."""
import time
from app.database import SessionLocal
from app.services.pricing_strategy_service import PricingStrategyService
from app.services.profitability_service import ProfitabilityService
from app.services.training_service import _sales_aggregates, ModelTrainingService
from app.services.forecast_service import ForecastService
from app.services.competitor_service import CompetitorService

db = SessionLocal()

# 1. Time sales aggregates (cached after first)
t0 = time.time(); agg = _sales_aggregates(db); t1 = time.time()
print(f"[1] _sales_aggregates (cold): {(t1-t0)*1000:.0f} ms")

# 2. Load model
t0 = time.time(); model, fc, run = ModelTrainingService(db).load_model(); t1 = time.time()
print(f"[2] load_model: {(t1-t0)*1000:.0f} ms")

# 3. Competitor analyze on 10 products (estimate per-product cost)
t0 = time.time()
cs = CompetitorService(db)
import random
from sqlalchemy import text
pids = [r[0] for r in db.execute(text("SELECT id FROM products ORDER BY id LIMIT 10"))]
for pid in pids[:5]:
    cs.analyze(pid)
t1 = time.time()
print(f"[3] CompetitorService.analyze x5: {(t1-t0)*1000:.0f} ms ({(t1-t0)*1000/5:.0f} ms each)")

# 4. Demand signal for 10 products
t0 = time.time()
fs = ForecastService(db)
for pid in pids[:10]:
    fs.get_demand_signal(pid)
t1 = time.time()
print(f"[4] get_demand_signal x10: {(t1-t0)*1000:.0f} ms ({(t1-t0)*1000/10:.0f} ms each)")

# 5. Single product recommendation (product_recommendation)
svc = PricingStrategyService(db)
t0 = time.time()
try:
    rec = svc.product_recommendation(pids[0])
    t1 = time.time()
    print(f"[5] product_recommendation x1: {(t1-t0)*1000:.0f} ms")
except Exception as e:
    print(f"[5] product_recommendation failed: {e}")

# 6. Profitability pieces
prof = ProfitabilityService(db)
t0 = time.time(); s = prof.summary(); t1 = time.time()
print(f"[6a] profitability.summary: {(t1-t0)*1000:.0f} ms")
t0 = time.time(); tr = prof.trends(days=90); t1 = time.time()
print(f"[6b] profitability.trends(90): {(t1-t0)*1000:.0f} ms")
t0 = time.time(); pp = prof._per_product_profitability(); t1 = time.time()
print(f"[6c] _per_product_profitability: {(t1-t0)*1000:.0f} ms")
t0 = time.time(); ai = prof.ai_impact(top_n=5); t1 = time.time()
print(f"[6d] profitability.ai_impact(top_n=5): {(t1-t0)*1000:.0f} ms")

db.close()
