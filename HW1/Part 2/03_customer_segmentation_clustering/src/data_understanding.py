"""
CRISP-DM Phase 2: Data Understanding, Exploratory Data Analysis & Outlier Detection.
"""

from typing import Any, Dict, List
import numpy as np
import pandas as pd


class DataUnderstanding:
    """Computes EDA metrics, distribution statistics, and outlier boundaries."""

    def __init__(self, df: pd.DataFrame):
        self.df = df.copy()

    def get_summary_statistics(self) -> Dict[str, Dict[str, float]]:
        """Calculates univariate metrics for age, income, and spending score."""
        stats: Dict[str, Dict[str, float]] = {}
        for col in ["age", "annual_income", "spending_score"]:
            series = self.df[col].dropna()
            stats[col] = {
                "mean": round(float(series.mean()), 2),
                "std": round(float(series.std()), 2),
                "min": round(float(series.min()), 2),
                "q25": round(float(series.quantile(0.25)), 2),
                "median": round(float(series.median()), 2),
                "q75": round(float(series.quantile(0.75)), 2),
                "max": round(float(series.max()), 2),
                "skew": round(float(series.skew()), 4),
            }
        return stats

    def get_demographics(self) -> Dict[str, Any]:
        """Calculates gender counts, percentages, and female ratio."""
        counts = self.df["gender"].value_counts().to_dict()
        total = len(self.df)
        female_count = int(counts.get("Female", 0))
        male_count = int(counts.get("Male", 0))
        return {
            "gender_counts": {"Male": male_count, "Female": female_count},
            "gender_percentages": {
                "Male": round(float(male_count / total * 100), 2) if total > 0 else 0.0,
                "Female": round(float(female_count / total * 100), 2) if total > 0 else 0.0,
            },
            "female_ratio": round(float(female_count / total), 4) if total > 0 else 0.0,
            "total_customers": total,
        }

    def detect_outliers_iqr(self, multiplier: float = 1.5) -> Dict[str, Any]:
        """Identifies statistical outliers using the standard IQR rule."""
        outliers: Dict[str, Any] = {}
        for col in ["annual_income", "spending_score", "age"]:
            series = self.df[col]
            q1 = float(series.quantile(0.25))
            q3 = float(series.quantile(0.75))
            iqr = q3 - q1
            lower_bound = q1 - multiplier * iqr
            upper_bound = q3 + multiplier * iqr
            mask = (series < lower_bound) | (series > upper_bound)
            outlier_rows = self.df[mask]
            outliers[col] = {
                "lower_bound": round(lower_bound, 2),
                "upper_bound": round(upper_bound, 2),
                "q1": round(q1, 2),
                "q3": round(q3, 2),
                "iqr": round(iqr, 2),
                "outlier_count": int(mask.sum()),
                "outlier_customer_ids": outlier_rows["customer_id"].tolist() if "customer_id" in outlier_rows else [],
            }
        return outliers

    def get_correlation_matrix(self) -> Dict[str, Any]:
        """Computes pairwise Pearson correlation coefficients between numeric features."""
        num_cols = ["age", "annual_income", "spending_score"]
        corr = self.df[num_cols].corr()
        return {
            "features": num_cols,
            "matrix": [[round(float(corr.loc[r, c]), 4) for c in num_cols] for r in num_cols],
            "dict": {col: {c: round(float(corr.loc[col, c]), 4) for c in num_cols} for col in num_cols},
        }

    def get_dashboard_dataset_summary(self) -> Dict[str, Any]:
        """Formats dataset summary matching the pipeline_output.json schema."""
        summary_stats = self.get_summary_statistics()
        demographics = self.get_demographics()
        return {
            "total_customers": demographics["total_customers"],
            "features": ["age", "annual_income", "spending_score"],
            "age_stats": {
                "mean": summary_stats["age"]["mean"],
                "min": summary_stats["age"]["min"],
                "max": summary_stats["age"]["max"],
                "std": summary_stats["age"]["std"],
                "median": summary_stats["age"]["median"],
                "q1": summary_stats["age"]["q25"],
                "q3": summary_stats["age"]["q75"],
            },
            "income_stats": {
                "mean": summary_stats["annual_income"]["mean"],
                "min": summary_stats["annual_income"]["min"],
                "max": summary_stats["annual_income"]["max"],
                "std": summary_stats["annual_income"]["std"],
                "median": summary_stats["annual_income"]["median"],
                "q1": summary_stats["annual_income"]["q25"],
                "q3": summary_stats["annual_income"]["q75"],
            },
            "spending_stats": {
                "mean": summary_stats["spending_score"]["mean"],
                "min": summary_stats["spending_score"]["min"],
                "max": summary_stats["spending_score"]["max"],
                "std": summary_stats["spending_score"]["std"],
                "median": summary_stats["spending_score"]["median"],
                "q1": summary_stats["spending_score"]["q25"],
                "q3": summary_stats["spending_score"]["q75"],
            },
            "gender_counts": demographics["gender_counts"],
            "female_ratio": demographics["female_ratio"],
        }
