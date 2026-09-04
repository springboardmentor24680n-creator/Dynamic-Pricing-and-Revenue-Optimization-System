"""
PricePilot AI - Model Training Service
=======================================
Real dataset-trained dynamic pricing engine.

Builds a rich training frame from the product catalog + sales history, trains
Linear Regression / Random Forest / XGBoost against the current selling price,
evaluates all three with MAE / RMSE / R², keeps the best model, serializes it
to disk (joblib) and records a ``model_runs`` row with full metadata.

Key properties:
  * Training runs in a background thread (never blocks the API).
  * Prediction loads the saved model - it NEVER retrains per prediction.
  * Models are only retrained after a new dataset import or an explicit
    admin retrain request.
"""

import json
import logging
import os
import threading
import time
from datetime import datetime

import numpy as np
import pandas as pd
from sqlalchemy.orm import Session

from app.config import settings
from app.models.activity_log import ActivityLog
from app.models.dataset import Dataset
from app.models.model_run import ModelRun
from app.models.product import Product
from app.models.sales import Sale

logger = logging.getLogger(__name__)

MIN_SAMPLES = 10
LOOKBACK_DAYS = 180


# Module-level cache for sales aggregates (scans ~216K rows).
_aggregates_cache: dict = None
_aggregates_cache_ts: float = 0


def _sales_aggregates(db: Session) -> dict:
    """Per-product sales aggregates over the lookback window.

    Returns {product_id: {total_units, avg_daily_units, sales_days, revenue,
    demand_slope, weekend_uplift}} using the same factors the sales-history
    generator records (so synthetic and real history are treated identically).

    The result is cached for 5 minutes to avoid scanning 200K+ rows on every
    prediction or report call.
    """
    import time as _time
    global _aggregates_cache, _aggregates_cache_ts
    now = _time.time()
    if _aggregates_cache is not None and (now - _aggregates_cache_ts) < 300:
        return _aggregates_cache
    since = datetime.utcnow() - pd.Timedelta(days=LOOKBACK_DAYS).to_pytimedelta()
    rows = (
        db.query(
            Sale.product_id,
            Sale.sale_date,
            Sale.quantity,
            Sale.total_amount,
            Sale.weekend_effect,
            Sale.festival_effect,
        )
        .filter(Sale.sale_date >= since)
        .all()
    )

    by_product = {}
    for product_id, sale_date, qty, amount, weekend, festival in rows:
        agg = by_product.setdefault(product_id, {
            "total_units": 0.0, "revenue": 0.0, "sales_days": set(),
            "weekend_units": 0.0, "weekday_units": 0.0,
            "festival_units": 0.0, "normal_units": 0.0,
            "recent_units": 0.0, "prior_units": 0.0,
        })
        qty = qty or 0
        amount = amount or 0
        agg["total_units"] += qty
        agg["revenue"] += amount
        if sale_date is not None:
            agg["sales_days"].add(sale_date.date())
            is_weekend = (weekend is not None and weekend > 1.2) or sale_date.weekday() >= 5
            is_festival = festival is not None and festival > 1.2
            if is_weekend:
                agg["weekend_units"] += qty
            else:
                agg["weekday_units"] += qty
            if is_festival:
                agg["festival_units"] += qty
            else:
                agg["normal_units"] += qty
            # Demand trend: compare most recent ~40% vs the prior 60%
            if sale_date.date() >= (datetime.utcnow().date() - pd.Timedelta(days=36)):
                agg["recent_units"] += qty
            else:
                agg["prior_units"] += qty

    aggregates = {}
    for product_id, agg in by_product.items():
        days = max(len(agg["sales_days"]), 1)
        aggregates[product_id] = {
            "total_units": agg["total_units"],
            "avg_daily_units": agg["total_units"] / days,
            "sales_days": len(agg["sales_days"]),
            "revenue": agg["revenue"],
            "weekend_uplift": (agg["weekend_units"] / max(agg["weekday_units"], 1)),
            "festival_share": (agg["festival_units"] / max(agg["normal_units"], 1)),
            "demand_slope": ((agg["recent_units"] - agg["prior_units"]) /
                             max(agg["prior_units"], 1)),
        }
    _aggregates_cache = aggregates
    _aggregates_cache_ts = _time.time()
    return aggregates


def invalidate_analytics_caches():
    """Drop every module-level analytics cache (aggregates, predictions,
    elasticity, brand map, demand signals, competitor ranges).

    Called after any catalog mutation: dataset import, manual price update,
    sales-history generation, and model retraining. Local imports keep the
    dependency graph acyclic (ml_service imports this module at the top).
    """
    global _aggregates_cache, _aggregates_cache_ts
    _aggregates_cache = None
    _aggregates_cache_ts = 0
    try:
        from app.services.ml_service import PricingMLService
        PricingMLService.clear_prediction_cache()
        PricingMLService._elasticity_cache = None
        PricingMLService._elasticity_cache_ts = 0
        PricingMLService._brand_cache = None
        PricingMLService._brand_cache_ts = 0
    except Exception:  # noqa: BLE001
        logger.debug("ML cache clear skipped", exc_info=True)
    try:
        from app.services.forecast_service import clear_demand_signal_cache
        clear_demand_signal_cache()
    except Exception:  # noqa: BLE001
        logger.debug("Forecast cache clear skipped", exc_info=True)
    try:
        from app.services.pricing_strategy_service import clear_signal_caches
        clear_signal_caches()
    except Exception:  # noqa: BLE001
        logger.debug("Strategy cache clear skipped", exc_info=True)


class ModelTrainingService:
    """Trains, persists, and loads the price-optimization ML models."""

    def __init__(self, db: Session):
        self.db = db

    # ------------------------------------------------------------------
    # Training data
    # ------------------------------------------------------------------
    def build_training_frame(self) -> pd.DataFrame:
        """Build the training DataFrame.

        Features (whatever the catalog provides):
          base_price, cost_price, stock_quantity, revenue,
          margin_pct, price_deviation, avg_daily_units, total_units,
          sales_days, demand_slope, weekend_uplift, festival_share,
          category (one-hot), brand-derived prefix
        Target: current_price (the selling price the dataset actually used).
        """
        products = self.db.query(Product).all()
        aggregates = _sales_aggregates(self.db)

        rows = []
        for p in products:
            if not p.current_price or p.current_price <= 0:
                continue
            base = p.base_price or p.current_price
            cost = p.cost_price or 0
            agg = aggregates.get(p.id, {})
            rows.append({
                "product_id": p.id,
                "name": p.name,
                "category": p.category or "Uncategorized",
                "brand": (p.name.split(" ")[0] if p.name else "Unknown"),
                "current_price": p.current_price,
                "base_price": base,
                "cost_price": cost,
                "stock_quantity": p.stock_quantity or 0,
                "revenue": p.revenue or agg.get("revenue", 0) or 0,
                "margin_pct": ((p.current_price - cost) / p.current_price * 100)
                              if cost > 0 and p.current_price > 0 else 0,
                "price_deviation": ((p.current_price - base) / base * 100) if base else 0,
                "avg_daily_units": agg.get("avg_daily_units", 0),
                "total_units": agg.get("total_units", 0),
                "sales_days": agg.get("sales_days", 0),
                "demand_slope": agg.get("demand_slope", 0),
                "weekend_uplift": agg.get("weekend_uplift", 1.0),
                "festival_share": agg.get("festival_share", 0),
            })
        df = pd.DataFrame(rows)
        if df.empty:
            return df

        # One-hot encode categorical features (category + brand)
        # Limit brand encoding to top 20 most common brands to avoid
        # feature explosion (hundreds of sparse one-hot columns).
        top_brands = df["brand"].value_counts().head(20).index.tolist()
        df["brand"] = df["brand"].apply(lambda b: b if b in top_brands else "Other")
        df = pd.get_dummies(df, columns=["category"], prefix="cat")
        df = pd.get_dummies(df, columns=["brand"], prefix="brand")

        # Numeric features used by the model (drop identifiers / target)
        feature_cols = [c for c in df.columns
                        if c not in ("product_id", "name", "current_price")]
        X = df[feature_cols].replace([np.inf, -np.inf], 0).fillna(0).astype(float)
        y = df["current_price"].astype(float)
        return pd.concat([df[["product_id", "name"]], X, y.rename("__target__")], axis=1)

    # ------------------------------------------------------------------
    # Model training + evaluation
    # ------------------------------------------------------------------
    def _train_and_evaluate(self, X: np.ndarray, y: np.ndarray) -> tuple:
        """Train LR / RF / XGB with cross-validation. Returns
        (best_model, best_name, metrics_by_model, feature_cols, error)."""
        from sklearn.ensemble import RandomForestRegressor
        from sklearn.linear_model import LinearRegression
        from sklearn.model_selection import cross_val_predict
        from sklearn.preprocessing import StandardScaler
        from sklearn.pipeline import Pipeline
        from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
        import xgboost as xgb

        if X.shape[0] < MIN_SAMPLES:
            return None, None, None, None, (
                f"Insufficient data to train AI models. Need at least {MIN_SAMPLES} products "
                f"with pricing data; currently have {X.shape[0]}."
            )

        candidates = {
            "Linear Regression": Pipeline([
                ("scaler", StandardScaler()),
                ("model", LinearRegression()),
            ]),
            "Random Forest": RandomForestRegressor(
                n_estimators=120, max_depth=8, random_state=42, n_jobs=-1,
            ),
            "XGBoost": xgb.XGBRegressor(
                n_estimators=150, max_depth=6, learning_rate=0.08,
                subsample=0.9, colsample_bytree=0.9, random_state=42,
                n_jobs=-1, verbosity=0,
            ),
        }

        metrics = {}
        best_model, best_name, best_score = None, None, -np.inf
        for name, model in candidates.items():
            try:
                cv = min(5, X.shape[0])
                y_pred = cross_val_predict(model, X, y, cv=cv, n_jobs=-1)
                mae = float(mean_absolute_error(y, y_pred))
                rmse = float(np.sqrt(mean_squared_error(y, y_pred)))
                r2 = float(r2_score(y, y_pred))
                metrics[name] = {"mae": round(mae, 4), "rmse": round(rmse, 4), "r2": round(r2, 4)}
                if r2 > best_score:
                    best_score = r2
                    best_name = name
            except Exception as exc:  # noqa: BLE001
                logger.warning("Training %s failed: %s", name, exc)
                continue

        if best_name is None:
            return None, None, None, None, "All models failed to train."

        # Refit the best model on the full data for production predictions
        best_model = candidates[best_name]
        best_model.fit(X, y)
        return best_model, best_name, metrics, None, None

    def _feature_importances(self, model, feature_cols) -> dict:
        """Importance per feature (tree models: feature_importances_,
        linear: |coefficient| normalized)."""
        try:
            if hasattr(model, "named_steps") and "model" in model.named_steps:
                inner = model.named_steps["model"]
            else:
                inner = model
            if hasattr(inner, "feature_importances_"):
                imp = np.abs(inner.feature_importances_)
            elif hasattr(inner, "coef_"):
                imp = np.abs(inner.coef_)
            else:
                return {}
            imp = np.nan_to_num(imp, nan=0.0)
            total = float(imp.sum())
            if total <= 0:
                return {}
            return {f: round(float(v / total), 4) for f, v in zip(feature_cols, imp)}
        except Exception:  # noqa: BLE001
            return {}

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------
    def _model_path(self, run_id: int) -> str:
        os.makedirs(settings.MODEL_DIR, exist_ok=True)
        return os.path.join(settings.MODEL_DIR, f"price_model_{run_id}.joblib")

    def run_training(self, user_id: int, dataset_id: int = None, dataset_name: str = None,
                     synchronous: bool = False, existing_run: ModelRun = None):
        """Execute one full training run and persist its metadata.

        Returns the ModelRun row. ``synchronous=True`` blocks (used for tests);
        the API path uses ``start_background_training``.

        ``existing_run`` lets a background worker update the exact row that was
        pre-created (and whose id was returned to the API caller) instead of
        creating a second orphan row.
        """
        if existing_run is not None:
            run = existing_run
            run.status = "training"
        else:
            run = ModelRun(status="training", created_by=user_id)
        if dataset_id:
            run.dataset_id = dataset_id
            ds = self.db.query(Dataset).filter(Dataset.id == dataset_id).first()
            run.dataset_name = dataset_name or (ds.name if ds else None)
        else:
            run.dataset_name = dataset_name or "Product catalog"
        self.db.add(run)
        self.db.commit()
        self.db.refresh(run)

        start = time.time()
        try:
            # Ensure every product has realistic daily sales history before
            # training (covers pre-existing catalog products that predate the
            # auto-history feature, not just freshly imported ones). This feeds
            # real sales aggregates into the training frame, lets Prophet
            # forecast, and lets the price-elasticity regression learn from
            # actual demand data instead of falling back to a constant.
            try:
                from app.services.sales_history_service import SalesHistoryService
                SalesHistoryService(self.db).ensure_history_for_products()
            except Exception as exc:  # noqa: BLE001 - training must not fail on this
                logger.warning("Sales history generation skipped: %s", exc)

            frame = self.build_training_frame()
            if frame.empty:
                raise ValueError("No products with a valid price to train on.")

            X = frame.drop(columns=["product_id", "name", "__target__"]).values
            y = frame["__target__"].values
            feature_cols = list(frame.drop(columns=["product_id", "name", "__target__"]).columns)

            model, best_name, metrics, _, error = self._train_and_evaluate(X, y)
            if model is None:
                raise ValueError(error or "Training failed")

            run.status = "ready"
            run.best_model = best_name
            run.target = "current_price"
            run.metrics = json.dumps(metrics)
            run.accuracy = round(metrics[best_name]["r2"], 4)
            run.mae = round(metrics[best_name]["mae"], 4)
            run.rmse = round(metrics[best_name]["rmse"], 4)
            run.samples = X.shape[0]
            run.features_used = json.dumps(feature_cols)
            run.feature_importances = json.dumps(self._feature_importances(model, feature_cols))
            run.model_file = self._model_path(run.id)

            import joblib
            joblib.dump({"model": model, "features": feature_cols}, run.model_file)

            self.db.add(ActivityLog(
                action="AI models retrained",
                resource_type="model",
                details=(f"Best model '{best_name}' · R² {run.accuracy:.3f} · "
                         f"{run.samples} records · {run.dataset_name}"),
                user_id=user_id,
            ))
            logger.info("Training run %s complete: %s R2=%.3f", run.id, best_name, run.accuracy)
        except Exception as exc:  # noqa: BLE001
            run.status = "failed"
            run.error_message = str(exc)
            logger.exception("Training run %s failed", run.id)
        finally:
            run.training_time_seconds = round(time.time() - start, 2)
            self.db.commit()
            self.db.refresh(run)
            # New model version + possibly regenerated sales history: cached
            # predictions / aggregates / demand signals are now outdated.
            invalidate_analytics_caches()
        return run

    def start_background_training(self, user_id: int, dataset_id: int = None,
                                  dataset_name: str = None) -> int:
        """Kick off training in a daemon thread with its own DB session.

        Pre-creates the ModelRun row so the caller can report a concrete run id;
        the worker thread then updates that SAME row (never an orphan).
        Returns the ModelRun id.
        """
        run = ModelRun(status="training", created_by=user_id)
        if dataset_id:
            run.dataset_id = dataset_id
            ds = self.db.query(Dataset).filter(Dataset.id == dataset_id).first()
            run.dataset_name = dataset_name or (ds.name if ds else None)
        else:
            run.dataset_name = dataset_name or "Product catalog"
        self.db.add(run)
        self.db.commit()
        self.db.refresh(run)
        run_id = run.id

        def _worker():
            from app.database import SessionLocal
            from app.models.model_run import ModelRun as RunModel
            worker_db = SessionLocal()
            try:
                # Re-attach the pre-created row in the worker's session so we
                # update the exact run whose id was returned to the caller.
                worker_run = worker_db.query(RunModel).filter(RunModel.id == run_id).first()
                svc = ModelTrainingService(worker_db)
                svc.run_training(user_id, dataset_id, dataset_name, synchronous=True,
                                 existing_run=worker_run)
            finally:
                worker_db.close()

        t = threading.Thread(target=_worker, daemon=True)
        t.start()
        return run_id

    # ------------------------------------------------------------------
    # Loading the saved model
    # ------------------------------------------------------------------
    def latest_ready_run(self) -> ModelRun:
        """The most recent successfully trained model run."""
        return (
            self.db.query(ModelRun)
            .filter(ModelRun.status == "ready")
            .order_by(ModelRun.id.desc())
            .first()
        )

    def load_model(self):
        """Load (model, feature_cols, run) from the latest ready run, or
        (None, None, None) when no trained model exists."""
        import joblib
        run = self.latest_ready_run()
        if not run or not run.model_file or not os.path.exists(run.model_file):
            return None, None, None
        try:
            artifact = joblib.load(run.model_file)
            return artifact["model"], artifact["features"], run
        except Exception:  # noqa: BLE001
            logger.exception("Failed to load model %s", run.model_file)
            return None, None, None

    def model_info(self) -> dict:
        """Full metadata of the latest training run for the API / UI."""
        run = (
            self.db.query(ModelRun)
            .order_by(ModelRun.id.desc())
            .first()
        )
        if not run:
            return {
                "has_model": False,
                "status": "untrained",
                "message": "No AI model trained yet. Upload a dataset and run training.",
            }
        info = run.to_dict()
        info["has_model"] = run.status == "ready"
        info["message"] = {
            "training": "AI model is training in the background…",
            "ready": f"Model '{run.best_model}' is ready (R² {run.accuracy:.3f}).",
            "failed": f"Last training attempt failed: {run.error_message or 'unknown error'}",
        }.get(run.status, "Unknown training state")
        return info

    def training_status(self) -> dict:
        """Lightweight status for polls: is training in progress right now?"""
        latest = (
            self.db.query(ModelRun)
            .order_by(ModelRun.id.desc())
            .first()
        )
        return {
            "training_in_progress": bool(latest and latest.status == "training"),
            "latest_status": latest.status if latest else "untrained",
        }
