import os
import sys
import json
import logging
from datetime import datetime, timezone
from pathlib import Path

# Ensure the backend directory is in the system path to allow absolute imports
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.append(str(BASE_DIR))

# Import reports directory lookup
from ml_pipeline.train_price_model import REPORTS_DIR

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("ml_pipeline.revenue_optimizer")

def main():
    logger.info("Starting Revenue Optimization report generation...")
    
    recommendations_path = REPORTS_DIR / "price_recommendations.json"
    optimization_save_path = REPORTS_DIR / "revenue_optimization.json"
    
    if not recommendations_path.exists():
        logger.error(f"Recommendations report not found at: {recommendations_path}. Run price_recommendation.py first.")
        sys.exit(1)
        
    try:
        # Load pre-computed price recommendations
        logger.info(f"Loading price recommendations from: {recommendations_path}")
        with open(recommendations_path, "r", encoding="utf-8") as f:
            recs_data = json.load(f)
            
        recommendations = recs_data.get("recommendations", [])
        
        # 1. Compute Overall Metrics
        total_curr_rev = sum(r["historical_revenue"] for r in recommendations)
        total_pred_rev = sum(r["expected_revenue"] for r in recommendations)
        total_gain = total_pred_rev - total_curr_rev
        total_growth_pct = (total_gain / (total_curr_rev + 1e-5)) * 100
        
        # 2. Action Breakdown
        actions = ["Increase Price", "Decrease Price", "Maintain Price"]
        action_breakdown = {}
        for act in actions:
            act_recs = [r for r in recommendations if r["recommendation"] == act]
            curr_rev = sum(r["historical_revenue"] for r in act_recs)
            pred_rev = sum(r["expected_revenue"] for r in act_recs)
            gain = pred_rev - curr_rev
            growth_pct = (gain / (curr_rev + 1e-5)) * 100 if curr_rev > 0 else 0.0
            
            action_breakdown[act] = {
                "product_count": len(act_recs),
                "current_revenue": round(curr_rev, 2),
                "predicted_revenue": round(pred_rev, 2),
                "revenue_gain": round(gain, 2),
                "revenue_growth_percentage": round(growth_pct, 2)
            }
            
        # 3. Top Gain Contributors (ranked by revenue_improvement descending)
        top_gain = sorted(recommendations, key=lambda x: x["revenue_improvement"], reverse=True)[:10]
        top_gain_list = []
        for r in top_gain:
            top_gain_list.append({
                "stockcode": r["stockcode"],
                "country": r["country"],
                "current_price": r["current_price"],
                "recommended_price": r["recommended_price"],
                "historical_revenue": r["historical_revenue"],
                "expected_revenue": r["expected_revenue"],
                "revenue_gain": r["revenue_improvement"],
                "revenue_growth_percentage": r["revenue_improvement_percentage"]
            })
            
        # 4. Top Growth Opportunities (ranked by revenue_improvement_percentage descending)
        top_growth = sorted(recommendations, key=lambda x: x["revenue_improvement_percentage"], reverse=True)[:10]
        top_growth_list = []
        for r in top_growth:
            top_growth_list.append({
                "stockcode": r["stockcode"],
                "country": r["country"],
                "current_price": r["current_price"],
                "recommended_price": r["recommended_price"],
                "historical_revenue": r["historical_revenue"],
                "expected_revenue": r["expected_revenue"],
                "revenue_gain": r["revenue_improvement"],
                "revenue_growth_percentage": r["revenue_improvement_percentage"]
            })
            
        # Create output json
        report = {
            "run_date": datetime.now(timezone.utc).isoformat(),
            "total_products_optimized": len(recommendations),
            "overall_metrics": {
                "total_current_revenue": round(total_curr_rev, 2),
                "total_predicted_revenue": round(total_pred_rev, 2),
                "total_revenue_gain": round(total_gain, 2),
                "total_revenue_growth_percentage": round(total_growth_pct, 2)
            },
            "action_breakdown": action_breakdown,
            "top_gain_contributors": top_gain_list,
            "top_growth_opportunities": top_growth_list
        }
        
        with open(optimization_save_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)
            
        logger.info(f"Successfully saved revenue optimization report to: {optimization_save_path}")
        
        # Print a beautiful summary to the console
        print("\n" + "="*80)
        print("                      REVENUE OPTIMIZATION SUMMARY REPORT")
        print("="*80)
        print(f"Total Products Optimized    : {report['total_products_optimized']}")
        print(f"Total Current Revenue       : ₹{report['overall_metrics']['total_current_revenue']:,.2f}")
        print(f"Total Predicted Revenue     : ₹{report['overall_metrics']['total_predicted_revenue']:,.2f}")
        print(f"Total Revenue Gain (Net)    : ₹{report['overall_metrics']['total_revenue_gain']:+,.2f}")
        print(f"Total Revenue Growth        : {report['overall_metrics']['total_revenue_growth_percentage']:+.2f}%")
        print("-"*80)
        print("ACTION SEGMENT SUMMARY:")
        print(f"  {'Action':<15} | {'Count':<5} | {'Current Rev':<14} | {'Predicted Rev':<14} | {'Growth':<7}")
        print(f"  {'-'*15} | {'-'*5} | {'-'*14} | {'-'*14} | {'-'*7}")
        for act, details in action_breakdown.items():
            print(
                f"  {act:<15} | "
                f"{details['product_count']:<5} | "
                f"₹{details['current_revenue']:<13,.2f} | "
                f"₹{details['predicted_revenue']:<13,.2f} | "
                f"{details['revenue_growth_percentage']:+6.2f}%"
            )
        print("-"*80)
        print("TOP 3 REVENUE GAIN CONTRIBUTORS:")
        for idx, item in enumerate(top_gain_list[:3]):
            print(f"  {idx+1}. StockCode {item['stockcode']} ({item['country']})")
            print(f"     Price: ₹{item['current_price']:.2f} -> ₹{item['recommended_price']:.2f} (change: {item['revenue_growth_percentage']:+.2f}%)")
            print(f"     Gain : ₹{item['revenue_gain']:+,.2f} (expected: ₹{item['expected_revenue']:,.2f})")
        print("="*80 + "\n")
        
    except Exception as e:
        logger.error(f"Error during revenue optimization report generation: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()
