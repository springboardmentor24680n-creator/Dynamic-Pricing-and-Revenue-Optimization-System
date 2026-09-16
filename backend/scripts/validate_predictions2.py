"""Task 1: Validate prediction + recommendation quality across products."""
import math
import time
from sqlalchemy import func
from app.database import SessionLocal
from app.models.product import Product
from app.models.sales import Sale
from app.services.ml_service import PricingMLService
from app.services.pricing_strategy_service import PricingStrategyService

db = SessionLocal()
ml = PricingMLService(db)
strategy = PricingStrategyService(db)

# ---- sample representative products from key categories ----
categories = ["Laptops", "Smartphones", "Headphones", "Shirts & Tops", "Shoes",
              "TVs & Monitors", "Smartwatches", "Accessories", "Tablets"]
products = []
for cat in categories:
    p = db.query(Product).filter(Product.category == cat).first()
    if p:
        products.append(p)

# add low/high stock & low sales edge products
low_stock = db.query(Product).filter(Product.stock_quantity.between(1, 5)).first()
high_stock = db.query(Product).filter(Product.stock_quantity >= 500).first()
low_sales = (db.query(Product, func.count(Sale.id).label("c"))
             .outerjoin(Sale, Sale.product_id == Product.id)
             .group_by(Product.id).having(func.count(Sale.id) <= 3).first())
if low_sales:
    products.append(low_sales[0])

seen = set()
print("=== PREDICTION VALIDATION PER PRODUCT ===")
errors = []
for p in products:
    if p.id in seen:
        continue
    seen.add(p.id)
    try:
        t0 = time.time()
        pred = ml.predict_product(p.id)
        dt = (time.time() - t0) * 1000
    except Exception as e:
        errors.append((p.id, p.name, f"EXC {e}"))
        print(f"  EXC {p.id} {p.name[:45]} -> {e}")
        continue

    cur = pred.get("current_price")
    sug = pred.get("suggested_price")
    conf = pred.get("confidence_score")
    cost = p.cost_price or 0
    flags = []
    if sug is None or (isinstance(sug, float) and (math.isnan(sug) or math.isinf(sug))):
        flags.append("NAN/INF")
    if sug is not None and sug < 0:
        flags.append("NEGATIVE")
    if cost > 0 and sug is not None and sug < cost - 1e-6:
        flags.append("BELOW_COST")
    if cur and sug is not None and not (0.4 * cur <= sug <= 2.6 * cur):
        flags.append(f"FAR({sug:.2f} vs {cur:.2f})")
    if not pred.get("insufficient_data") and (conf is None or not (0 <= conf <= 100)):
        flags.append("BAD_CONF")
    print(f"  #{p.id} {p.name[:48]:48s} cur={cur:>8.2f} sug={sug if sug is None else round(sug,2)} "
          f"cost={cost:>7.2f} conf={conf} {' '.join(flags) if flags else 'OK'} ({dt:.0f}ms)")
    if flags and "BELOW_COST" not in flags:
        errors.append((p.id, p.name, flags))

print("\n=== RECOMMENDATION VALIDATION (single-product endpoint) ===")
for p in products[:6]:
    try:
        rec = strategy.product_recommendation(p.id)
        action = rec["action"]
        margin = rec["current_margin"]
        rp = rec["recommended_price"]
        conf = rec["confidence"]
        print(f"  #{p.id} {p.name[:42]:42s} action={action:20s} margin={margin:6.1f}% "
              f"cur={rec['current_price']:>8.2f} rec={rp:>8.2f} conf={conf} prio={rec['priority']} demand={rec['demand_trend']}")
    except Exception as e:
        print(f"  EXC #{p.id}: {e}")

print("\n=== EDGE CASES ===")
for label, p in [("low_stock", low_stock), ("high_stock", high_stock)]:
    if not p:
        continue
    pred = ml.predict_product(p.id)
    print(f"  {label}: #{p.id} {p.name[:40]} stock={p.stock_quantity} sug={pred.get('suggested_price')} insuff={pred.get('insufficient_data')}")

# product with NO sales at all?
no_sales = (db.query(Product).outerjoin(Sale, Sale.product_id == Product.id)
            .filter(Sale.id.is_(None)).first())
if no_sales:
    pred = ml.predict_product(no_sales.id)
    print(f"  no_sales: #{no_sales.id} {no_sales.name[:40]} sug={pred.get('suggested_price')} insuff={pred.get('insufficient_data')} factors={len(pred.get('factors', []))}")

print("\n=== ERRORS: ", errors if errors else "NONE")
db.close()
