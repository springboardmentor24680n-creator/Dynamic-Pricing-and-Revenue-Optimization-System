"""Task 1: Validate prediction accuracy & recommendation quality."""
import json
import time
import math
from app.database import SessionLocal
from app.models.product import Product
from app.models.sales import Sale
from app.models.model_run import ModelRun
from app.services.ml_service import PricingMLService
from app.services.pricing_strategy_service import PricingStrategyService
from app.services.training_service import ModelTrainingService

db = SessionLocal()

# --- Model runs ---
runs = db.query(ModelRun).all()
print("=== MODEL RUNS ===")
for r in runs:
    metrics = {}
    try:
        metrics = json.loads(r.metrics or "{}")
    except Exception:
        pass
    print(f"  run_id={r.id} status={r.status} best={r.best_model} acc={r.accuracy} "
          f"mae={r.mae} rmse={r.rmse} samples={r.samples} model_file={r.model_file}")
    if metrics:
        for name, m in metrics.items():
            print(f"      {name}: {m}")

# --- Ground truth on the training target: how well do we predict held-out prices ---
print("\n=== TRAINING FRAME / TARGET VALIDATION ===")
ts = ModelTrainingService(db)
frame = ts.build_training_frame()
print(f"Training frame rows: {len(frame)}")
print(f"Current-price range: {frame['__target__'].min():.2f} - {frame['__target__'].max():.2f}")

# Load model
model, feature_cols, run = ts.load_model()
print(f"Loaded model: {run.best_model if run else None}, feature cols: {len(feature_cols) if feature_cols else 0}")

# --- Sales-volume reality check for training targets ---
print("\n=== SALES vs MODEL INPUT SANITY ===")
sales_count = db.query(Sale).count()
products_count = db.query(Product).count()
print(f"Products: {products_count}, Sales rows: {sales_count}")

db.close()
