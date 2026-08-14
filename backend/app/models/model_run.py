"""
PricePilot AI - Trained Model Run Model
Stores metadata about every AI training run so the engine can report the
best model, evaluation metrics (MAE / RMSE / R²), the dataset it was trained
on, the features used, and where the serialized model lives on disk.

Prediction never retrains: it loads the latest ready ModelRun's serialized
model file and scores products against it.
"""

from sqlalchemy import Column, Integer, String, Float, Text, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship

from app.database import Base


class ModelRun(Base):
    """A persisted ML training run with evaluation metrics and model file path."""

    __tablename__ = "model_runs"

    id = Column(Integer, primary_key=True, index=True)
    status = Column(String(20), default="training")  # training, ready, failed
    best_model = Column(String(60))
    target = Column(String(60), default="current_price")

    # Evaluation metrics for every candidate model: JSON
    # {"Linear Regression": {"mae":..., "rmse":..., "r2":...}, ...}
    metrics = Column(Text, default="{}")
    # Best-model headline metrics (denormalized for fast reads)
    accuracy = Column(Float, default=0.0)      # R² of the best model
    mae = Column(Float, default=0.0)
    rmse = Column(Float, default=0.0)

    samples = Column(Integer, default=0)
    features_used = Column(Text, default="[]")  # JSON list of feature names
    feature_importances = Column(Text, default="{}")  # JSON {feature: importance}

    # Which dataset was this trained on?
    dataset_id = Column(Integer, ForeignKey("datasets.id", ondelete="SET NULL"))
    dataset_name = Column(String(200))

    # Serialized model location (relative to settings.MODEL_DIR)
    model_file = Column(String(255))

    training_time_seconds = Column(Float, default=0.0)
    error_message = Column(Text)

    created_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    created_at = Column(DateTime, server_default=func.now())

    # Relationships
    dataset = relationship("Dataset")
    user = relationship("User")

    def to_dict(self) -> dict:
        """Serializable summary for the API."""
        import json
        try:
            metrics = json.loads(self.metrics or "{}")
        except (json.JSONDecodeError, TypeError):
            metrics = {}
        try:
            features = json.loads(self.features_used or "[]")
        except (json.JSONDecodeError, TypeError):
            features = []
        return {
            "id": self.id,
            "status": self.status,
            "best_model": self.best_model,
            "target": self.target,
            "metrics": metrics,
            "accuracy": self.accuracy,
            "mae": self.mae,
            "rmse": self.rmse,
            "samples": self.samples,
            "features_used": features,
            "dataset_id": self.dataset_id,
            "dataset_name": self.dataset_name,
            "model_file": self.model_file,
            "training_time_seconds": self.training_time_seconds,
            "error_message": self.error_message,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
