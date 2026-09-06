import os
from fastapi import FastAPI, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, Any, List
from catalog_datasets import load_products_from_csv, load_training_dataset_df
from ml_engine import train_and_predict_models
from agent_orchestrator import execute_multi_agent_pipeline

app = FastAPI(
    title="PricePilot AI - Dynamic Pricing Optimization & Revenue Intelligence Engine",
    version="1.0.0"
)

# CORS middleware enabling Next.js frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory storage for User Approval Management System
# Default Admin email: vaibhavbhagat123455@gmail.com
PENDING_USERS_DB = [
    {
        "id": "req-101",
        "email": "sarah.analytics@enterprise.com",
        "name": "Sarah Connor",
        "requested_role": "Pricing Manager",
        "requested_at": "2026-08-18 14:30",
        "status": "pending"
    },
    {
        "id": "req-102",
        "email": "alex.merchant@retailcorp.io",
        "name": "Alex Mercer",
        "requested_role": "Business Analyst",
        "requested_at": "2026-08-18 15:45",
        "status": "pending"
    }
]

APPROVED_USERS_DB = [
    "vaibhavbhagat123455@gmail.com"
]

@app.get("/api/health")
def health_check():
    products = load_products_from_csv()
    df_train = load_training_dataset_df()
    return {
        "status": "online",
        "system": "PricePilot AI Engine",
        "admin_email": "vaibhavbhagat123455@gmail.com",
        "catalog_products_count": len(products),
        "training_dataset_rows": len(df_train),
        "ml_models": ["LightGBM", "XGBoost", "Prophet Time-Series"],
        "agents": ["OpenRouter (openai/gpt-oss-20b:free)", "Tavily Search Agent", "News API Agent"]
    }

@app.get("/api/products")
def get_products():
    """Returns product catalog dynamically loaded from root products_catalog.csv."""
    products = load_products_from_csv()
    return {"products": products}

@app.get("/api/predict/single/{product_id}")
def predict_single_product(product_id: str):
    """
    Trains ML models (LightGBM, XGBoost, Prophet) on retail_pricing_dataset.csv
    and executes Multi-Agent Orchestration for a single product.
    """
    products = load_products_from_csv()
    prod = next((p for p in products if p["id"] == product_id), None)
    if not prod:
        raise HTTPException(status_code=404, detail="Product not found in CSV catalog")
        
    ml_results = train_and_predict_models(product_id)
    agent_results = execute_multi_agent_pipeline(product_id, ml_results)
    
    return {
        "success": True,
        "prediction": ml_results,
        "multi_agent_insights": agent_results
    }

@app.post("/api/predict/all")
def predict_all_products():
    """
    Batch trains and predicts for ALL products loaded from products_catalog.csv.
    """
    products = load_products_from_csv()
    batch_results = []
    total_rev_before = 0.0
    total_rev_after = 0.0
    
    for prod in products:
        p_id = prod["id"]
        ml_res = train_and_predict_models(p_id)
        agent_res = execute_multi_agent_pipeline(p_id, ml_res)
        
        cur_30d_rev = prod["current_price"] * (prod.get("historical_sales_30d", 500))
        opt_30d_rev = ml_res["horizons"]["short_term"]["next_30_days"]["projected_revenue"]
        
        total_rev_before += cur_30d_rev
        total_rev_after += opt_30d_rev
        
        batch_results.append({
            "product_id": p_id,
            "product_name": prod["name"],
            "category": prod["category"],
            "current_price": prod["current_price"],
            "optimal_price": ml_res["optimal_price"],
            "recommended_change_pct": ml_res["recommended_price_change_pct"],
            "short_term_30d_demand": ml_res["horizons"]["short_term"]["next_30_days"]["predicted_demand"],
            "medium_term_6m_demand": ml_res["horizons"]["medium_term"]["next_6_months"]["predicted_demand"],
            "long_term_12m_demand": ml_res["horizons"]["long_term"]["next_12_months"]["predicted_demand"],
            "confidence_score": ml_res["forecast_confidence"],
            "brain_agent_summary": agent_res["brain_agent"]["executive_summary"]
        })
        
    overall_lift_pct = round(((total_rev_after - total_rev_before) / max(total_rev_before, 1.0)) * 100, 2)
    
    return {
        "success": True,
        "count": len(batch_results),
        "overall_revenue_lift_pct": overall_lift_pct,
        "total_30d_revenue_before": round(total_rev_before, 2),
        "total_30d_revenue_projected": round(total_rev_after, 2),
        "batch_predictions": batch_results
    }

@app.get("/api/seasonal-reports")
def get_seasonal_reports():
    """Generates structured seasonal demand & trend analysis report."""
    return {
        "title": "Q3-Q4 Executive Seasonal & Festival Demand Insights Report",
        "summary": "High seasonal elasticity detected across Audio, Electronics, Gaming, and Home Appliances due to upcoming Q4 holiday shopping, Diwali/Christmas surge, and festival demand.",
        "weekly_patterns": [
            {"day": "Monday", "demand_index": 0.92, "note": "Baseline inventory replenishment day"},
            {"day": "Tuesday", "demand_index": 0.95, "note": "Steady B2B & corporate procurement"},
            {"day": "Wednesday", "demand_index": 1.02, "note": "Mid-week discount campaign response"},
            {"day": "Thursday", "demand_index": 1.05, "note": "Pre-weekend browsing spike"},
            {"day": "Friday", "demand_index": 1.28, "note": "Peak conversion & weekend shopping trigger"},
            {"day": "Saturday", "demand_index": 1.35, "note": "Highest consumer order volume"},
            {"day": "Sunday", "demand_index": 1.15, "note": "Late evening mobile purchasing"}
        ],
        "seasonal_factors": [
            {"factor": "Back-To-School / Office Upgrade", "impact": "+18.4% Demand Lift", "affected_categories": ["Display & PC", "Office & Furniture"]},
            {"factor": "Q4 Holiday & Festival Season", "impact": "+34.2% Peak Surge", "affected_categories": ["Gaming & PC", "Home Appliances", "Audio & Electronics"]},
            {"factor": "New Year Fitness Spike", "impact": "+22.5% Demand Lift", "affected_categories": ["Wearables"]}
        ],
        "inventory_turnover_alerts": [
            {"product": "Ergonomic Mesh Office Chair", "stock": 75, "days_remaining": 5.4, "action": "Urgent Reorder Required"},
            {"product": "Ultra-Wide 4K Monitor 34-inch", "stock": 95, "days_remaining": 9.2, "action": "Optimal Stock Level"},
            {"product": "Compact Robot Vacuum & Mop", "stock": 115, "days_remaining": 6.8, "action": "Reorder Batch Suggested"}
        ]
    }

@app.get("/api/competitor-analysis")
def get_competitor_analysis():
    """Returns market competitor price tracking matrix computed from products_catalog.csv."""
    products = load_products_from_csv()
    matrix = []
    for prod in products:
        our_p = float(prod["current_price"])
        comp_p = float(prod.get("competitor_price", our_p))
        diff = comp_p - our_p
        diff_pct = (diff / max(our_p, 0.01)) * 100
        
        if diff > 5:
            position = "Underpriced (Opportunity to raise price)"
        elif diff < -5:
            position = "Premium (Risk of losing price-sensitive shoppers)"
        else:
            position = "Competitive (Price matched)"
            
        matrix.append({
            "product_id": prod["id"],
            "product_name": prod["name"],
            "category": prod["category"],
            "our_price": our_p,
            "competitor_name": prod.get("competitor_name", "Market Competitor"),
            "competitor_price": comp_p,
            "price_difference": round(diff, 2),
            "difference_pct": round(diff_pct, 1),
            "market_position": position
        })
        
    return {"competitor_matrix": matrix}

# ADMIN USER APPROVAL ENDPOINTS
@app.get("/api/admin/pending-users")
def get_pending_users():
    return {
        "admin_email": "vaibhavbhagat123455@gmail.com",
        "pending_requests": PENDING_USERS_DB,
        "approved_emails": APPROVED_USERS_DB
    }

@app.post("/api/admin/approve-user")
def approve_user(data: Dict[str, Any] = Body(...)):
    user_id = data.get("id")
    email = data.get("email")
    
    global PENDING_USERS_DB, APPROVED_USERS_DB
    PENDING_USERS_DB = [u for u in PENDING_USERS_DB if u["id"] != user_id]
    if email and email not in APPROVED_USERS_DB:
        APPROVED_USERS_DB.append(email)
        
    return {"success": True, "message": f"User {email} approved successfully!"}

@app.post("/api/admin/reject-user")
def reject_user(data: Dict[str, Any] = Body(...)):
    user_id = data.get("id")
    global PENDING_USERS_DB
    PENDING_USERS_DB = [u for u in PENDING_USERS_DB if u["id"] != user_id]
    return {"success": True, "message": "User request rejected."}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
