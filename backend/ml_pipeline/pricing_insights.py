import os
import sys
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Any, Tuple

# Ensure the backend directory is in the system path to allow absolute imports
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.append(str(BASE_DIR))

# Import reports directory lookup
from ml_pipeline.train_price_model import REPORTS_DIR

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("ml_pipeline.pricing_insights")

class AIInsightsGenerator:
    """
    An AI Insights Generator that takes price recommendations, applies business rules,
    and translates numeric variables into human-readable insights (High Demand, Low Demand,
    Inventory Running Low, Seasonal Demand, Competitor Advantage, Revenue Opportunity)
    with a detailed textual reasoning for every recommendation.
    """
    def __init__(self):
        pass

    def generate_insights(self, recommendations: List[Dict[str, Any]], demand_trend: str) -> List[Dict[str, Any]]:
        """
        Parses product metrics, assigns tag flags, and compiles detailed justification paragraphs.
        """
        # Calculate percentiles for sales volume (to detect High vs Low demand dynamically)
        sales_volumes = [r["historical_sales"] for r in recommendations]
        if sales_volumes:
            high_sales_thresh = np.percentile(sales_volumes, 80)
            low_sales_thresh = np.percentile(sales_volumes, 20)
        else:
            high_sales_thresh = 1000
            low_sales_thresh = 50

        insights_list = []

        for rec in recommendations:
            stockcode = rec["stockcode"]
            country = rec["country"]
            curr_p = rec["current_price"]
            pred_p = rec["predicted_price"]
            rec_p = rec["recommended_price"]
            diff = rec["price_difference"]
            diff_pct = rec["price_difference_percentage"]
            inventory = rec["current_inventory"]
            supply = rec["days_of_supply"]
            sales = rec["historical_sales"]
            revenue = rec["historical_revenue"]
            exp_demand = rec["expected_demand"]
            exp_revenue = rec["expected_revenue"]
            imp_pct = rec["revenue_improvement_percentage"]
            action = rec["recommendation"]

            tags = []
            reasoning_sentences = []

            # 1. High Demand / Low Demand Insight
            if sales >= high_sales_thresh:
                tags.append("High Demand")
                reasoning_sentences.append(f"historical sales volume of {sales} units is in the top 20% of catalog demand")
            elif sales <= low_sales_thresh:
                tags.append("Low Demand")
                reasoning_sentences.append(f"historical sales volume of {sales} units indicates low overall velocity")

            # 2. Inventory Running Low Insight
            if supply < 10:
                tags.append("Inventory Running Low")
                reasoning_sentences.append(f"stock levels are critical with only {supply} days of supply remaining ({inventory} units)")
            elif supply > 30:
                reasoning_sentences.append(f"stock levels are high with {supply} days of supply ({inventory} units)")
            else:
                reasoning_sentences.append(f"stock levels are healthy with {supply} days of supply ({inventory} units)")

            # 3. Seasonal Demand Insight
            if demand_trend in ["Seasonal", "Increasing"]:
                tags.append("Seasonal Demand")
                reasoning_sentences.append("forecast models indicate a strong seasonal demand phase")
            elif demand_trend == "Decreasing":
                reasoning_sentences.append("forecast models indicate a general seasonal demand contraction")

            # 4. Competitor Advantage Insight
            # If current price is lower than LightGBM baseline, we have pricing headroom / margin advantage
            if curr_p < pred_p * 0.95:
                tags.append("Competitor Advantage")
                reasoning_sentences.append(f"current price (₹{curr_p:.2f}) is below optimal baseline price (₹{pred_p:.2f}), offering pricing headroom")
            elif curr_p > pred_p * 1.05:
                reasoning_sentences.append(f"current price (₹{curr_p:.2f}) is higher than optimal baseline (₹{pred_p:.2f}), suggesting we are overpriced")

            # 5. Revenue Opportunity Insight
            if imp_pct > 5.0:
                tags.append("Revenue Opportunity")
                
            # Compile detailed justification paragraph
            joined_context = ", ".join(reasoning_sentences)
            
            if action == "Increase Price":
                action_text = f"We recommend increasing the price by ₹{diff:.2f} (+{diff_pct:.1f}%) to ₹{rec_p:.2f}."
                if imp_pct > 0.0:
                    outcome_text = f"This increase is designed to expand margins and slow down inventory draw, while capturing an expected revenue improvement of {imp_pct:.2f}%."
                else:
                    outcome_text = f"This increase is designed to defend product value and extend run-out time, with a projected change in revenue of {imp_pct:.2f}%."
            elif action == "Decrease Price":
                action_text = f"We recommend decreasing the price by ₹{abs(diff):.2f} ({diff_pct:.1f}%) to ₹{rec_p:.2f}."
                outcome_text = f"This markdown aims to clear inventory, stimulate volume sales, and capture a projected revenue improvement of {imp_pct:.2f}%."
            else:
                action_text = f"We recommend maintaining the price at ₹{rec_p:.2f}."
                outcome_text = "This matches baseline pricing and maintains competitive market alignment."

            reason_paragraph = f"For product {stockcode} in {country}, {joined_context}. {action_text} {outcome_text}"

            insights_list.append({
                "stockcode": stockcode,
                "country": country,
                "current_price": curr_p,
                "recommended_price": rec_p,
                "price_difference": diff,
                "price_difference_percentage": diff_pct,
                "expected_revenue_improvement_percentage": imp_pct,
                "recommendation": action,
                "insights": tags,
                "reason": reason_paragraph
            })

        return insights_list

import numpy as np

def main():
    logger.info("Starting AI Insights Generator run...")
    
    recommendations_path = REPORTS_DIR / "price_recommendations.json"
    insights_save_path = REPORTS_DIR / "pricing_insights.json"
    
    if not recommendations_path.exists():
        logger.error(f"Recommendations report not found at: {recommendations_path}. Run price_recommendation.py first.")
        sys.exit(1)
        
    try:
        # Load pre-computed price recommendations
        logger.info(f"Loading price recommendations from: {recommendations_path}")
        with open(recommendations_path, "r", encoding="utf-8") as f:
            recs_data = json.load(f)
            
        recommendations = recs_data.get("recommendations", [])
        demand_trend = recs_data.get("demand_trend_used", "Stable")
        
        # Instantiate Insights Generator
        generator = AIInsightsGenerator()
        
        # Generate human-readable insights and reasonings
        insights = generator.generate_insights(recommendations, demand_trend)
        
        # Compute summary counts for tags
        all_tags = []
        for item in insights:
            all_tags.extend(item["insights"])
            
        unique_tags = ["High Demand", "Low Demand", "Inventory Running Low", "Seasonal Demand", "Competitor Advantage", "Revenue Opportunity"]
        tag_counts = {tag: all_tags.count(tag) for tag in unique_tags}
        
        # Assemble insights report JSON
        report_output = {
            "run_date": datetime.now(timezone.utc).isoformat(),
            "total_products_evaluated": len(insights),
            "demand_trend_state": demand_trend,
            "insights_statistics": tag_counts,
            "product_insights": insights
        }
        
        with open(insights_save_path, "w", encoding="utf-8") as f:
            json.dump(report_output, f, indent=2)
            
        logger.info(f"Successfully saved pricing insights to: {insights_save_path}")
        
        # Print a beautiful terminal report
        print("\n" + "="*80)
        print("                      AI PRICING INSIGHTS GENERATION REPORT")
        print("="*80)
        print(f"Total Products Evaluated   : {report_output['total_products_evaluated']}")
        print(f"Prophet Demand Trend State : {report_output['demand_trend_state'].upper()}")
        print("-"*80)
        print("INSIGHT TAG DISTRIBUTION:")
        for tag, count in tag_counts.items():
            print(f"  - {tag:<25} : {count} products")
        print("-"*80)
        print("SAMPLE DETAILED INSIGHTS (Top 3 Products):")
        for item in insights[:3]:
            print(f"\n  Product StockCode : {item['stockcode']}")
            print(f"    Current Price   : ₹{item['current_price']:.2f} | Recommended: ₹{item['recommended_price']:.2f}")
            print(f"    Action          : {item['recommendation'].upper()}")
            print(f"    Insight Tags    : {item['insights']}")
            # Wrap textual reason for clean presentation
            reason = item['reason']
            # Simple word-wrap print
            print("    Reasoning       : ", end="")
            words = reason.split()
            line = ""
            for w in words:
                if len(line) + len(w) > 65:
                    print(line)
                    print("                      " + w, end=" ")
                    line = ""
                else:
                    line += w + " "
            if line:
                print(line)
        print("="*80 + "\n")
        
    except Exception as e:
        logger.error(f"Error during insights generation: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()
