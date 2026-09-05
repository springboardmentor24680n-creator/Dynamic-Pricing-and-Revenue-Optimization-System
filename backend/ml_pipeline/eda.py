import os
import json
import logging
import time
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional

import pandas as pd
import numpy as np

# Configure Matplotlib for headless execution
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("ml_pipeline.eda")

BASE_DIR = Path(__file__).resolve().parent.parent
FEATURES_DIR = BASE_DIR / "datasets" / "features"
REPORTS_DIR = BASE_DIR / "reports"
PLOTS_DIR = REPORTS_DIR / "plots"

class ExploratoryDataAnalysis:
    """
    Modular EDA engine that analyzes a dataset and generates:
    - Text profiling reports
    - Matplotlib visualizations
    - Metrics dictionaries for JSON serialization
    """
    def __init__(self, df: pd.DataFrame, dataset_name: str, reports_dir: Path, plots_dir: Path):
        self.df = df.copy()
        self.name = dataset_name
        self.reports_dir = reports_dir
        self.plots_dir = plots_dir
        
        # Directories preparation
        self.reports_dir.mkdir(parents=True, exist_ok=True)
        self.plots_dir.mkdir(parents=True, exist_ok=True)
        
        # Analyze schema
        self.date_col = self._find_date_column()
        self.numeric_cols = self.df.select_dtypes(include=[np.number]).columns.tolist()
        self.categorical_cols = self.df.select_dtypes(exclude=[np.number]).columns.tolist()
        
        # Key column lookups
        self.target_col = self._find_column_by_keywords(["sales", "quantity", "units_sold"])
        self.price_col = self._find_column_by_keywords(["price", "current_price", "cost_price"])
        self.revenue_col = self._find_column_by_keywords(["revenue"])

    def _find_date_column(self) -> Optional[str]:
        for col in self.df.columns:
            if "date" in str(col).lower() or "time" in str(col).lower():
                return col
        return None

    def _find_column_by_keywords(self, keywords: List[str]) -> Optional[str]:
        for col in self.df.columns:
            col_lower = str(col).lower()
            if any(kw in col_lower for kw in keywords):
                return col
        return None

    def analyze(self) -> Dict[str, Any]:
        """
        Computes all profiling metrics and saves a text report.
        """
        logger.info(f"Analyzing dataset profile: {self.name}")
        
        rows, cols = self.df.shape
        missing_report = self.df.isnull().sum().to_dict()
        duplicates = int(self.df.duplicated().sum())
        
        # Outlier counts using IQR
        outliers = {}
        for col in self.numeric_cols:
            q1 = self.df[col].quantile(0.25)
            q3 = self.df[col].quantile(0.75)
            iqr = q3 - q1
            lower_bound = q1 - 1.5 * iqr
            upper_bound = q3 + 1.5 * iqr
            outlier_count = int(((self.df[col] < lower_bound) | (self.df[col] > upper_bound)).sum())
            outliers[col] = outlier_count
            
        # Numerical stats
        num_stats = {}
        if self.numeric_cols:
            desc = self.df[self.numeric_cols].describe()
            for col in self.numeric_cols:
                num_stats[col] = {
                    "mean": float(desc.at["mean", col]) if not pd.isna(desc.at["mean", col]) else 0.0,
                    "std": float(desc.at["std", col]) if not pd.isna(desc.at["std", col]) else 0.0,
                    "min": float(desc.at["min", col]) if not pd.isna(desc.at["min", col]) else 0.0,
                    "25%": float(desc.at["25%", col]) if not pd.isna(desc.at["25%", col]) else 0.0,
                    "50%": float(desc.at["50%", col]) if not pd.isna(desc.at["50%", col]) else 0.0,
                    "75%": float(desc.at["75%", col]) if not pd.isna(desc.at["75%", col]) else 0.0,
                    "max": float(desc.at["max", col]) if not pd.isna(desc.at["max", col]) else 0.0
                }
                
        # Categorical stats
        cat_stats = {}
        for col in self.categorical_cols:
            val_counts = self.df[col].value_counts().head(5).to_dict()
            cat_stats[col] = {
                "unique_values": int(self.df[col].nunique()),
                "top_categories": {str(k): int(v) for k, v in val_counts.items()}
            }
            
        # Correlation Matrix
        correlations = {}
        if len(self.numeric_cols) > 1:
            corr_df = self.df[self.numeric_cols].corr().fillna(0)
            correlations = corr_df.to_dict()

        # Build text summary report
        report_path = self.reports_dir / f"{self.name.replace('/', '_')}_report.txt"
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(f"EXPLORATORY DATA ANALYSIS REPORT: {self.name}\n")
            f.write("="*60 + "\n\n")
            f.write(f"Dimensions: {rows} rows, {cols} columns\n")
            f.write(f"Duplicate Rows: {duplicates}\n\n")
            
            f.write("DATA TYPES:\n")
            for c, t in self.df.dtypes.items():
                f.write(f" - {c}: {t}\n")
            f.write("\n")
            
            f.write("MISSING VALUES SUMMARY:\n")
            for c, m in missing_report.items():
                if m > 0:
                    f.write(f" - {c}: {m} ({ (m/rows)*100:.2f}%)\n")
            f.write("\n")
            
            f.write("OUTLIERS SUMMARY (IQR Method):\n")
            for c, o in outliers.items():
                f.write(f" - {c}: {o} outliers\n")
            f.write("\n")
            
            f.write("NUMERICAL FEATURES STATISTICS:\n")
            for col, stats in num_stats.items():
                f.write(f" - {col}:\n")
                for k, v in stats.items():
                    f.write(f"     {k}: {v:.4f}\n")
            f.write("\n")
            
            f.write("CATEGORICAL FEATURES SUMMARY:\n")
            for col, stats in cat_stats.items():
                f.write(f" - {col} ({stats['unique_values']} unique values):\n")
                f.write(f"     Top categories: {stats['top_categories']}\n")
            f.write("\n")
            
        logger.info(f"Saved text report to: {report_path}")
        
        return {
            "rows": rows,
            "columns": cols,
            "duplicates": duplicates,
            "missing_values": missing_report,
            "outliers": outliers,
            "numerical_statistics": num_stats,
            "categorical_statistics": cat_stats,
            "correlation_matrix": correlations
        }

    def generate_charts(self):
        """
        Generates visualizations using Matplotlib only.
        """
        logger.info(f"Generating charts for: {self.name}")
        base_name = self.name.replace('/', '_')
        
        # 1. Sales / Demand Trend
        if self.date_col and self.target_col:
            plt.figure(figsize=(10, 5))
            trend = self.df.groupby(self.date_col)[self.target_col].sum().reset_index()
            trend[self.date_col] = pd.to_datetime(trend[self.date_col])
            trend = trend.sort_values(by=self.date_col)
            plt.plot(trend[self.date_col], trend[self.target_col], color="#1f77b4", linewidth=2)
            plt.title(f"Sales/Demand Trend over Time - {self.name}")
            plt.xlabel("Date")
            plt.ylabel("Volume / Sales")
            plt.grid(True, linestyle="--", alpha=0.5)
            plt.tight_layout()
            plt.savefig(self.plots_dir / f"{base_name}_demand_trend.png", dpi=150)
            plt.close()

        # 2. Revenue Distribution
        if self.revenue_col:
            plt.figure(figsize=(8, 5))
            plt.hist(self.df[self.revenue_col].dropna(), bins=50, color="#2ca02c", edgecolor="k", alpha=0.7)
            plt.title(f"Revenue Distribution - {self.name}")
            plt.xlabel("Revenue")
            plt.ylabel("Frequency")
            plt.grid(True, linestyle="--", alpha=0.5)
            plt.tight_layout()
            plt.savefig(self.plots_dir / f"{base_name}_revenue_distribution.png", dpi=150)
            plt.close()

        # 3. Price Distribution
        if self.price_col:
            plt.figure(figsize=(8, 5))
            plt.hist(self.df[self.price_col].dropna(), bins=50, color="#ff7f0e", edgecolor="k", alpha=0.7)
            plt.title(f"Price Distribution - {self.name}")
            plt.xlabel("Price")
            plt.ylabel("Frequency")
            plt.grid(True, linestyle="--", alpha=0.5)
            plt.tight_layout()
            plt.savefig(self.plots_dir / f"{base_name}_price_distribution.png", dpi=150)
            plt.close()

        # 4. Correlation Heatmap
        if len(self.numeric_cols) > 1:
            plt.figure(figsize=(10, 8))
            corr = self.df[self.numeric_cols].corr().fillna(0)
            
            im = plt.imshow(corr.values, cmap="coolwarm", vmin=-1, vmax=1)
            plt.colorbar(im)
            
            ticks = np.arange(len(self.numeric_cols))
            plt.xticks(ticks, self.numeric_cols, rotation=45, ha="right", fontsize=9)
            plt.yticks(ticks, self.numeric_cols, fontsize=9)
            
            for i in range(len(self.numeric_cols)):
                for j in range(len(self.numeric_cols)):
                    val = corr.iloc[i, j]
                    plt.text(j, i, f"{val:.2f}", ha="center", va="center", 
                             color="white" if abs(val) > 0.5 else "black", fontsize=8)
                             
            plt.title(f"Correlation Heatmap - {self.name}", fontsize=12)
            plt.tight_layout()
            plt.savefig(self.plots_dir / f"{base_name}_correlation_heatmap.png", dpi=150)
            plt.close()

        # 5. Numerical columns histograms (Up to 4 columns in subplots)
        cols_to_plot = [c for c in self.numeric_cols if c not in [self.target_col, self.price_col, self.revenue_col]][:4]
        if cols_to_plot:
            num_plots = len(cols_to_plot)
            fig, axes = plt.subplots(1, num_plots, figsize=(4 * num_plots, 4))
            if num_plots == 1:
                axes = [axes]
            for i, col in enumerate(cols_to_plot):
                axes[i].hist(self.df[col].dropna(), bins=30, color="#9467bd", edgecolor="k", alpha=0.7)
                axes[i].set_title(col, fontsize=10)
                axes[i].grid(True, linestyle="--", alpha=0.5)
            plt.suptitle(f"Numerical Feature Distributions - {self.name}", y=1.02)
            plt.tight_layout()
            plt.savefig(self.plots_dir / f"{base_name}_numerical_histograms.png", dpi=150)
            plt.close()

        # 6. Boxplots for important features
        box_cols = [c for c in [self.target_col, self.price_col, self.revenue_col] if c and c in self.df.columns]
        if box_cols:
            fig, axes = plt.subplots(1, len(box_cols), figsize=(4 * len(box_cols), 5))
            if len(box_cols) == 1:
                axes = [axes]
            for i, col in enumerate(box_cols):
                axes[i].boxplot(self.df[col].dropna())
                axes[i].set_title(f"Boxplot of {col}", fontsize=10)
                axes[i].grid(True, linestyle="--", alpha=0.5)
            plt.suptitle(f"Outlier Spread Profile - {self.name}", y=1.02)
            plt.tight_layout()
            plt.savefig(self.plots_dir / f"{base_name}_boxplots.png", dpi=150)
            plt.close()

def main():
    logger.info("Starting EDA run across all engineered datasets...")
    
    # Discover engineered features
    extensions = [".csv"]
    all_files = []
    for ext in extensions:
        all_files.extend(list(FEATURES_DIR.glob(f"**/*{ext}")))
        
    feature_files = [f for f in all_files if f.is_file() and not f.name.startswith(".")]
    
    if not feature_files:
        logger.warning(f"No engineered feature datasets found in: {FEATURES_DIR}")
        return
        
    logger.info(f"Discovered {len(feature_files)} datasets to profile.")
    
    summary_report = {}
    for f in feature_files:
        rel_path = f.relative_to(FEATURES_DIR).as_posix()
        try:
            df = pd.read_csv(f)
            
            # Initialize EDA
            eda = ExploratoryDataAnalysis(
                df=df,
                dataset_name=rel_path,
                reports_dir=REPORTS_DIR,
                plots_dir=PLOTS_DIR
            )
            
            # Analyze metrics
            metrics = eda.analyze()
            summary_report[rel_path] = metrics
            
            # Generate charts
            eda.generate_charts()
            
            logger.info(f"Completed EDA processing for: {rel_path}")
        except Exception as e:
            logger.error(f"Error processing EDA for {rel_path}: {e}", exc_info=True)

    # Export report.json
    json_dest = REPORTS_DIR / "report.json"
    with open(json_dest, "w", encoding="utf-8") as f:
        json.dump(summary_report, f, indent=2)
    logger.info(f"Consolidated summary report successfully exported to: {json_dest}")

if __name__ == "__main__":
    main()
