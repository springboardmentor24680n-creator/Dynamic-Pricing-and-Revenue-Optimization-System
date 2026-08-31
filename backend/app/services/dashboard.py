"""
PricePilot AI - Dashboard Service
"""

from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta

from app.models.product import Product
from app.models.dataset import Dataset
from app.models.activity_log import ActivityLog
from app.models.recommendation import Recommendation
from app.models.sales import Sale
from app.schemas.dashboard import DashboardResponse, CategorySummary, RevenueSummary


class DashboardService:
    """Service for dashboard metrics and analytics."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_dashboard(self) -> DashboardResponse:
        """Get comprehensive dashboard data with KPIs and chart data."""
        # ---- Core counts ----
        total_products = self.db.query(func.count(Product.id)).scalar() or 0
        active_products = self.db.query(func.count(Product.id)).filter(
            Product.status == "active"
        ).scalar() or 0
        in_stock = self.db.query(func.count(Product.id)).filter(
            Product.stock_quantity > 0
        ).scalar() or 0
        out_of_stock = self.db.query(func.count(Product.id)).filter(
            Product.stock_quantity == 0
        ).scalar() or 0

        # ---- Categories ----
        category_rows = (
            self.db.query(Product.category, func.count(Product.id))
            .group_by(Product.category)
            .all()
        )
        categories = [
            CategorySummary(category=cat, product_count=count)
            for cat, count in category_rows if cat
        ]

        # ---- Revenue summary (sales-based, matches ProfitabilityService) ----
        total_revenue = float(
            self.db.query(func.coalesce(func.sum(Sale.total_amount), 0)).scalar()
        )
        total_cost = float(
            self.db.query(func.coalesce(func.sum(Sale.quantity * Product.cost_price), 0))
            .join(Product, Product.id == Sale.product_id)
            .scalar()
        )
        avg_price = float(
            self.db.query(func.coalesce(func.avg(Product.current_price), 0)).scalar()
        )
        margin = round(((total_revenue - total_cost) / total_revenue * 100) if total_revenue > 0 else 0, 2)

        revenue_summary = RevenueSummary(
            total_revenue=round(total_revenue, 2),
            average_price=round(avg_price, 2),
            min_price=round(self.db.query(func.min(Product.current_price)).scalar() or 0, 2),
            max_price=round(self.db.query(func.max(Product.current_price)).scalar() or 0, 2),
            total_cost=round(total_cost, 2),
            margin=margin,
        )

        # ---- Datasets ----
        total_datasets = self.db.query(func.count(Dataset.id)).scalar() or 0
        dataset_status = (
            f"{total_datasets} dataset(s) processed" if total_datasets else "No dataset loaded"
        )

        # ---- AI status ----
        ai_status = "Not ready"
        ai_samples = total_products
        pending_recs = self.db.query(func.count(Recommendation.id)).filter(
            Recommendation.status == "pending"
        ).scalar() or 0
        if ai_samples >= 10:
            ai_status = "Ready" if pending_recs == 0 else f"Ready · {pending_recs} pending review"

        # ---- Recent activity ----
        recent_activity = (
            self.db.query(ActivityLog)
            .order_by(ActivityLog.created_at.desc())
            .limit(8)
            .all()
        )

        # ---- Chart: Category distribution ----
        category_distribution = [
            {"name": cat, "value": count} for cat, count in category_rows if cat
        ]

        # ---- Chart: Price distribution (buckets) ----
        price_buckets = [0] * 6
        price_labels = ["< $25", "$25-50", "$50-100", "$100-200", "$200-500", "$500+"]
        products = self.db.query(Product.current_price).all()
        for (p,) in products:
            p = p or 0
            if p < 25:
                price_buckets[0] += 1
            elif p < 50:
                price_buckets[1] += 1
            elif p < 100:
                price_buckets[2] += 1
            elif p < 200:
                price_buckets[3] += 1
            elif p < 500:
                price_buckets[4] += 1
            else:
                price_buckets[5] += 1
        price_distribution = [
            {"range": label, "count": count}
            for label, count in zip(price_labels, price_buckets)
        ]

        # ---- Chart: Revenue trend (from sales table, last 14 days) ----
        revenue_trend = []
        since = datetime.utcnow() - timedelta(days=13)
        daily_rows = (
            self.db.query(
                func.date(Sale.sale_date).label("date"),
                func.coalesce(func.sum(Sale.total_amount), 0),
            )
            .filter(Sale.sale_date >= since)
            .group_by(func.date(Sale.sale_date))
            .order_by(func.date(Sale.sale_date))
            .all()
        )
        daily_map = {str(r[0]): float(r[1]) for r in daily_rows}
        for i in range(13, -1, -1):
            day = (datetime.utcnow() - timedelta(days=i)).strftime("%Y-%m-%d")
            revenue_trend.append({"date": day, "revenue": round(daily_map.get(day, 0.0), 2)})

        # ---- Chart: Recent imports (datasets) ----
        recent_imports = (
            self.db.query(Dataset)
            .order_by(Dataset.created_at.desc())
            .limit(5)
            .all()
        )

        return DashboardResponse(
            total_products=total_products,
            active_products=active_products,
            total_categories=len(categories),
            average_price=round(avg_price, 2),
            categories=categories,
            revenue_summary=revenue_summary,
            product_count=total_products,
            # Extra metrics (kept as extra attributes via dict-style access)
            in_stock=in_stock,
            out_of_stock=out_of_stock,
            total_revenue=round(total_revenue, 2),
            total_datasets=total_datasets,
            ai_status=ai_status,
            dataset_loaded=total_datasets > 0,
            dataset_status=dataset_status,
            recent_activity=[
                {
                    "id": log.id,
                    "action": log.action,
                    "details": log.details,
                    "resource_type": log.resource_type,
                    "created_at": log.created_at.isoformat() if log.created_at else None,
                }
                for log in recent_activity
            ],
            category_distribution=category_distribution,
            price_distribution=price_distribution,
            revenue_trend=revenue_trend,
            recent_imports=[
                {
                    "id": d.id,
                    "name": d.name,
                    "rows": d.rows,
                    "health_score": d.health_score,
                    "created_at": d.created_at.isoformat() if d.created_at else None,
                }
                for d in recent_imports
            ],
        )
