"""
PricePilot AI - Dataset Processing Service
Real data processing pipeline using pandas:
  upload -> validate -> clean missing -> deduplicate -> convert types -> generate stats -> store
"""

import io
import json
import os
import uuid
from datetime import datetime

import pandas as pd
import numpy as np
from fastapi import HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.config import settings
from app.models.dataset import Dataset, ImportLog
from app.models.product import Product
from app.models.pricing_history import PricingHistory
from app.models.activity_log import ActivityLog


# Mapping from common CSV column names to product fields
COLUMN_ALIASES = {
    "name": ["name", "product_name", "product", "title", "item_name"],
    "sku": ["sku", "product_sku", "code", "item_code", "product_code"],
    "category": ["category", "product_category", "category_name", "type"],
    "base_price": ["base_price", "original_price", "list_price", "msrp"],
    "current_price": ["current_price", "price", "selling_price", "unit_price", "sale_price"],
    "cost_price": ["cost_price", "cost", "unit_cost", "purchase_price"],
    "stock_quantity": ["stock_quantity", "stock", "quantity", "inventory", "units_in_stock", "available_quantity"],
    "description": ["description", "details", "product_description"],
    "image_url": ["image_url", "image", "product_image", "image_link"],
    "revenue": ["revenue", "total_revenue", "sales_revenue"],
    "sale_date": ["sale_date", "date", "transaction_date", "order_date", "created_at"],
    "channel": ["sale_channel", "channel", "platform"],
    "region": ["region", "country", "location"],
    "customer_segment": ["customer_segment", "segment", "customer_type"],
}


def normalize_column_name(col: str) -> str:
    """Normalize a column name to a canonical product field."""
    cleaned = col.strip().lower().replace(" ", "_").replace("-", "_")
    for canonical, aliases in COLUMN_ALIASES.items():
        if cleaned in aliases or cleaned == canonical:
            return canonical
    return cleaned


class DatasetProcessingService:
    """Service that processes uploaded datasets into cleaned, analyzed data."""

    def __init__(self, db: Session):
        self.db = db

    def _read_file(self, content: bytes, filename: str) -> pd.DataFrame:
        """Read CSV or Excel content into a DataFrame."""
        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        try:
            if ext in ("xlsx", "xls"):
                return pd.read_excel(io.BytesIO(content))
            if ext == "csv":
                try:
                    return pd.read_csv(io.BytesIO(content))
                except Exception:
                    return pd.read_csv(io.BytesIO(content), sep=";")
            # Default: try CSV
            return pd.read_csv(io.BytesIO(content))
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Could not parse file '{filename}'. Supported formats: CSV, XLSX. Error: {str(e)}",
            )

    def _to_float(self, val):
        """Safely convert a value to float, stripping currency symbols."""
        if val is None:
            return None
        if isinstance(val, (int, float)):
            return float(val)
        s = str(val).strip()
        if not s or s.lower() in ("nan", "none", "null", "n/a"):
            return None
        s = s.replace("$", "").replace(",", "").replace("€", "").replace("£", "")
        try:
            return float(s)
        except ValueError:
            return None

    def _clean_dataframe(self, df: pd.DataFrame) -> tuple:
        """Apply the shared cleaning pipeline: normalize, fill missing, dedupe, convert types.
        Returns (cleaned_df, steps)."""
        steps = []

        # 1. Normalize column names
        df.columns = [normalize_column_name(c) for c in df.columns]
        steps.append(f"Normalized {len(df.columns)} columns")

        # 2. Validate: ensure at least one product identifier column
        has_name = "name" in df.columns
        has_sku = "sku" in df.columns
        has_price = "current_price" in df.columns or "base_price" in df.columns
        if not (has_name or has_sku):
            raise HTTPException(
                status_code=400,
                detail="Dataset is missing a product identifier column (expected 'name' or 'sku'). Found columns: "
                + ", ".join(df.columns.tolist()[:12]),
            )
        if not has_price:
            raise HTTPException(
                status_code=400,
                detail="Dataset is missing a price column (expected 'current_price', 'price', or 'base_price').",
            )
        steps.append("Validated required columns (name/sku + price)")

        # 3. Clean missing values
        missing_before = int(df.isna().sum().sum())
        id_col = "sku" if has_sku else "name"
        before_drop = len(df)
        df = df.dropna(subset=[id_col])
        dropped_ident = before_drop - len(df)

        numeric_cols = ["current_price", "base_price", "cost_price", "stock_quantity", "revenue"]
        for col in numeric_cols:
            if col in df.columns:
                df[col] = df[col].map(self._to_float)
                mean_val = df[col].mean()
                df[col] = df[col].fillna(round(mean_val, 2) if pd.notna(mean_val) else 0)
                df[col] = df[col].fillna(0)

        for col in ["category", "description", "image_url"]:
            if col in df.columns:
                df[col] = df[col].fillna("Uncategorized" if col == "category" else "")
        if "name" in df.columns:
            df["name"] = df["name"].fillna("Unnamed Product")
        missing_after = int(df.isna().sum().sum())
        steps.append(
            f"Cleaned missing values ({missing_before} → {missing_after} remaining; dropped {dropped_ident} rows without identifier)"
        )

        # 4. Remove duplicate rows
        dup_cols = [c for c in ["sku", "name"] if c in df.columns]
        dups_before = int(df.duplicated(subset=dup_cols).sum())
        df = df.drop_duplicates(subset=dup_cols, keep="first")
        steps.append(f"Removed {dups_before} duplicate rows")

        # 5. Convert data types
        if "stock_quantity" in df.columns:
            df["stock_quantity"] = df["stock_quantity"].astype(int)
        if "current_price" not in df.columns and "base_price" in df.columns:
            df["current_price"] = df["base_price"]
        if "current_price" in df.columns:
            df["current_price"] = df["current_price"].round(2)
        steps.append("Converted data types (prices → float, stock → integer)")

        # Return the cleaning metrics too so callers can record them in stats
        return df, steps, missing_after, dups_before

    def process_upload(self, content: bytes, filename: str, dataset_type: str, user_id: int,
                       stored_name: str = None) -> dict:
        """Full processing pipeline: validate, clean, dedupe, convert, stats, store."""
        df = self._read_file(content, filename)
        if df.empty:
            raise HTTPException(status_code=400, detail="The uploaded file is empty")

        total_rows = len(df)
        df, steps, missing_after, dups_before = self._clean_dataframe(df)

        # 6. Generate statistics
        final_rows = len(df)
        stats = self._compute_stats(df)

        # 7. Store processed dataset metadata
        dataset = Dataset(
            name=filename.rsplit(".", 1)[0] or "uploaded_dataset",
            dataset_type=dataset_type,
            file_name=stored_name or filename,
            source="upload",
            status="processed",
            rows=final_rows,
            columns=len(df.columns),
            missing_values=missing_after,
            duplicate_count=dups_before,
            category_count=stats["category_count"],
            avg_price=round(stats["avg_price"], 2),
            total_revenue=round(stats["total_revenue"], 2),
            health_score=round(stats["health_score"], 2),
            column_names=json.dumps(list(df.columns)),
            pipeline_steps=json.dumps(steps),
            preview_rows=json.dumps(stats["preview"], default=str),
            created_by=user_id,
        )
        self.db.add(dataset)
        self.db.flush()

        # Import log entries
        for step in steps:
            self.db.add(ImportLog(
                dataset_id=dataset.id,
                action=step.split(" ")[0].lower(),
                detail=step,
                rows_affected=final_rows,
                created_by=user_id,
            ))
        self.db.add(ImportLog(
            dataset_id=dataset.id,
            action="processed",
            detail=f"Dataset processed successfully: {final_rows} rows, {len(df.columns)} columns",
            rows_affected=final_rows,
            created_by=user_id,
        ))

        # Activity log
        self.db.add(ActivityLog(
            action=f"Dataset '{dataset.name}' processed",
            resource_type="dataset",
            resource_id=dataset.id,
            details=f"{final_rows} rows, {len(df.columns)} columns, health {stats['health_score']:.0f}%",
            user_id=user_id,
        ))

        self.db.commit()
        self.db.refresh(dataset)

        return {
            "dataset_id": dataset.id,
            "name": dataset.name,
            "rows": final_rows,
            "columns": len(df.columns),
            "missing_values": missing_after,
            "duplicate_count": dups_before,
            "category_count": stats["category_count"],
            "avg_price": round(stats["avg_price"], 2),
            "total_revenue": round(stats["total_revenue"], 2),
            "health_score": round(stats["health_score"], 2),
            "top_categories": stats["top_categories"],
            "top_products": stats["top_products"],
            "column_names": list(df.columns),
            "pipeline_steps": steps,
            "preview": stats["preview"],
        }

    def _compute_stats(self, df: pd.DataFrame) -> dict:
        """Compute statistics from the cleaned DataFrame."""
        final_rows = len(df)
        num_cols = df.select_dtypes(include=[np.number]).shape[1]
        missing = int(df.isna().sum().sum())

        # Category count
        category_count = df["category"].nunique() if "category" in df.columns else 0

        # Average price
        price_col = "current_price" if "current_price" in df.columns else None
        avg_price = float(df[price_col].mean()) if price_col and final_rows else 0.0

        # Revenue
        if "revenue" in df.columns:
            total_revenue = float(df["revenue"].sum())
        elif price_col and "stock_quantity" in df.columns:
            total_revenue = float((df[price_col] * df["stock_quantity"]).sum())
        else:
            total_revenue = avg_price * final_rows

        # Top categories
        top_categories = []
        if "category" in df.columns:
            cat_counts = df["category"].value_counts().head(6)
            top_categories = [
                {"category": str(c), "count": int(n)} for c, n in cat_counts.items()
            ]

        # Top products by revenue
        top_products = []
        if price_col:
            df_sorted = df.copy()
            if "revenue" in df.columns:
                df_sorted = df_sorted.sort_values("revenue", ascending=False)
            else:
                df_sorted["_est_rev"] = df_sorted[price_col] * df_sorted.get(
                    "stock_quantity", pd.Series(1, index=df_sorted.index)
                )
                df_sorted = df_sorted.sort_values("_est_rev", ascending=False)
            for _, row in df_sorted.head(5).iterrows():
                top_products.append({
                    "name": str(row.get("name", row.get("sku", "Product")))[:60],
                    "price": float(row.get(price_col, 0) or 0),
                    "revenue": float(row.get("revenue", 0) or 0),
                })

        # Health score: 100 - penalties for missing data, duplicates, low rows
        health = 100.0
        if final_rows < 10:
            health -= 25
        if missing > 0:
            health -= min(25, missing * 2)
        if num_cols < 3:
            health -= 15
        health = max(0, min(100, health))

        # Preview (first 6 rows)
        preview = []
        for _, row in df.head(6).iterrows():
            preview.append({
                str(k): ("" if pd.isna(v) else (str(v) if not isinstance(v, (np.floating, np.integer)) else float(v)))
                for k, v in row.items()
            })

        return {
            "category_count": category_count,
            "avg_price": avg_price,
            "total_revenue": total_revenue,
            "health_score": health,
            "top_categories": top_categories,
            "top_products": top_products,
            "preview": preview,
        }

    def import_to_products(self, dataset_id: int, user_id: int) -> dict:
        """Import a processed dataset's data into the product catalog."""
        dataset = self.db.query(Dataset).filter(Dataset.id == dataset_id).first()
        if not dataset:
            raise HTTPException(status_code=404, detail="Dataset not found")

        # Re-read the stored file (we keep the source file on disk)
        filepath = os.path.join(settings.DATA_DIR, dataset.file_name) if dataset.source == "upload" else None
        if not filepath or not os.path.exists(filepath):
            raise HTTPException(status_code=400, detail="Source file no longer available")

        df = self._read_file(open(filepath, "rb").read(), dataset.file_name)
        df, _, _, _ = self._clean_dataframe(df)

        inserted, skipped, errors = 0, 0, 0
        self._newly_imported = []
        for _, row in df.iterrows():
            try:
                sku = str(row.get("sku", "") or "").strip()
                name = str(row.get("name", "") or "").strip()
                if not sku and not name:
                    skipped += 1
                    continue
                if not sku:
                    sku = f"IMP-{uuid.uuid4().hex[:8].upper()}"

                existing = self.db.query(Product).filter(Product.sku == sku).first()
                if existing:
                    skipped += 1
                    continue

                current_price = self._to_float(row.get("current_price")) or 0
                if current_price <= 0:
                    skipped += 1
                    continue
                base_price = self._to_float(row.get("base_price")) or current_price
                cost_price = self._to_float(row.get("cost_price"))
                stock = int(row.get("stock_quantity", 0) or 0)
                revenue = self._to_float(row.get("revenue")) or 0.0

                product = Product(
                    name=name or f"Product {sku}",
                    sku=sku,
                    category=str(row.get("category", "Uncategorized") or "Uncategorized"),
                    base_price=base_price or current_price,
                    current_price=current_price,
                    cost_price=cost_price,
                    description=str(row.get("description", "") or ""),
                    image_url=str(row.get("image_url", "") or ""),
                    stock_quantity=stock,
                    revenue=revenue,
                )
                self.db.add(product)
                self.db.flush()
                self._newly_imported.append(product)

                self.db.add(PricingHistory(
                    product_id=product.id,
                    old_price=base_price or current_price,
                    new_price=current_price,
                    change_reason="Imported from dataset",
                    changed_by=user_id,
                ))
                inserted += 1
            except Exception:
                errors += 1
                continue

        # Capture the newly-imported product ids so the follow-up pipeline can
        # generate sales history + kick off AI training for exactly these rows.
        new_product_ids = [p.id for p in self._newly_imported]

        self.db.add(ImportLog(
            dataset_id=dataset_id,
            action="imported",
            detail=f"Imported {inserted} products into catalog (skipped {skipped}, errors {errors})",
            rows_affected=inserted,
            created_by=user_id,
        ))
        self.db.add(ActivityLog(
            action=f"Imported {inserted} products from dataset '{dataset.name}'",
            resource_type="dataset",
            resource_id=dataset.id,
            details=f"{inserted} inserted, {skipped} skipped (duplicate SKUs), {errors} errors",
            user_id=user_id,
        ))
        self.db.commit()

        # Auto-pipeline: generate realistic sales history for the new products
        # (if the dataset didn't provide it) and train the AI models on the
        # refreshed catalog - both in the background so the import returns fast.
        auto_pipeline = {}
        if inserted > 0:
            try:
                from app.services.sales_history_service import SalesHistoryService
                sales_svc = SalesHistoryService(self.db)
                auto_pipeline["sales_history"] = sales_svc.ensure_history_for_products(new_product_ids)
            except Exception as exc:  # noqa: BLE001 - never fail the import
                auto_pipeline["sales_history"] = {"error": str(exc)}
            try:
                from app.services.training_service import ModelTrainingService
                training_svc = ModelTrainingService(self.db)
                auto_pipeline["training_run_id"] = training_svc.start_background_training(
                    user_id, dataset_id=dataset_id, dataset_name=dataset.name
                )
            except Exception as exc:  # noqa: BLE001
                auto_pipeline["training_run_id"] = None
                auto_pipeline["training_error"] = str(exc)

        return {
            "inserted": inserted,
            "skipped": skipped,
            "errors": errors,
            "message": f"Imported {inserted} products (skipped {skipped} duplicates, {errors} errors)",
            "auto_pipeline": auto_pipeline,
        }

    def save_uploaded_file(self, content: bytes, filename: str) -> str:
        """Save an uploaded file to the data directory with a unique name.
        Returns the stored file name (unique per upload to avoid overwrites).
        """
        safe_name = filename.replace("\\", "/").split("/")[-1]
        # Unique prefix prevents a later same-named upload from corrupting earlier datasets
        stored_name = f"{uuid.uuid4().hex[:10]}_{safe_name}"
        path = os.path.join(settings.DATA_DIR, stored_name)
        os.makedirs(settings.DATA_DIR, exist_ok=True)
        with open(path, "wb") as f:
            f.write(content)
        return stored_name

    def list_datasets(self, user_id: int = None, limit: int = 50) -> list:
        """List processed datasets."""
        query = self.db.query(Dataset).order_by(Dataset.created_at.desc())
        if user_id:
            query = query.filter(Dataset.created_by == user_id)
        return query.limit(limit).all()

    def list_import_logs(self, limit: int = 50) -> list:
        """List recent import logs."""
        return (
            self.db.query(ImportLog)
            .order_by(ImportLog.created_at.desc())
            .limit(limit)
            .all()
        )

    def get_summary(self) -> dict:
        """Get dataset management summary statistics."""
        total_datasets = self.db.query(Dataset).count()
        total_products = self.db.query(Product).count()
        categories = self.db.query(Product.category).distinct().count()

        last = (
            self.db.query(Dataset)
            .order_by(Dataset.created_at.desc())
            .first()
        )

        return {
            "total_products": total_products,
            "total_categories": categories,
            "total_datasets": total_datasets,
            "last_import": last.created_at.isoformat() if last else None,
            "last_dataset": last.name if last else None,
            "status": f"{total_products} products loaded" if total_products else "No dataset loaded",
        }
