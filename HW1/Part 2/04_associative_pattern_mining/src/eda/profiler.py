"""
Data Understanding Profiler: basket sizes, item frequencies, Pareto/Zipf analysis, and matrix sparsity.
"""

from typing import Any, Dict, List, Optional
import numpy as np
import pandas as pd
from scipy import stats

from src.data.schema import CleanedDataset, EDAProfile
from src.utils.logger import get_logger

logger = get_logger("crisp_dm.eda")


def compute_basket_size_stats(transactions_list: List[List[str]]) -> Dict[str, float]:
    """Calculate descriptive statistics for basket sizes."""
    if not transactions_list:
        return {"min": 0, "q25": 0.0, "median": 0.0, "q75": 0.0, "max": 0, "mean": 0.0, "std": 0.0, "iqr": 0.0, "skewness": 0.0}
    arr = np.array([len(b) for b in transactions_list], dtype=float)
    q25 = float(np.percentile(arr, 25))
    median = float(np.median(arr))
    q75 = float(np.percentile(arr, 75))
    iqr = float(q75 - q25)
    skew_val = float(stats.skew(arr)) if len(arr) > 2 else 0.0

    return {
        "min": int(np.min(arr)),
        "q25": round(q25, 2),
        "median": round(median, 2),
        "q75": round(q75, 2),
        "max": int(np.max(arr)),
        "mean": round(float(np.mean(arr)), 2),
        "std": round(float(np.std(arr)), 2),
        "iqr": round(iqr, 2),
        "skewness": round(skew_val, 2),
    }


def compute_item_frequency(transactions_list: List[List[str]]) -> pd.DataFrame:
    """Compute item occurrence counts and frequency proportions across transactions."""
    if not transactions_list:
        return pd.DataFrame(columns=["item", "count", "frequency"])
    from collections import Counter
    counter = Counter()
    for basket in transactions_list:
        for item in set(basket):
            counter[item] += 1
    total_trans = len(transactions_list)
    records = [
        {"item": item, "count": count, "frequency": round(count / total_trans, 6)}
        for item, count in counter.most_common()
    ]
    return pd.DataFrame(records)



def profile_dataset(
    raw_df: pd.DataFrame,
    dataset_name: str = "dataset",
    cleaned_data: Optional[CleanedDataset] = None,
) -> EDAProfile:
    """
    Generate comprehensive EDA and Data Understanding profile for CRISP-DM Phase 2.

    Parameters:
    -----------
    raw_df : pd.DataFrame
        Raw transaction DataFrame.
    dataset_name : str
        Name/identifier of dataset.
    cleaned_data : Optional[CleanedDataset]
        Cleaned transaction data if already preprocessed.

    Returns:
    --------
    EDAProfile
    """
    raw_records_count = len(raw_df)
    cols = {c.lower(): c for c in raw_df.columns}

    invoice_col = cols.get("invoiceno") or cols.get("invoice_no") or cols.get("transaction") or cols.get("order_id") or cols.get("member_number")
    item_col = cols.get("description") or cols.get("itemdescription") or cols.get("item") or cols.get("product_name")
    cust_col = cols.get("customerid") or cols.get("customer_id") or cols.get("member_number")
    country_col = cols.get("country")
    date_col = cols.get("invoicedate") or cols.get("invoice_date") or cols.get("date")

    # Cancellations
    cancellation_count = 0
    if invoice_col:
        is_canc = raw_df[invoice_col].astype(str).str.upper().str.startswith("C")
        cancellation_count = int(is_canc.sum())
    cancellation_rate_pct = (cancellation_count / raw_records_count * 100.0) if raw_records_count > 0 else 0.0

    # Uniques
    unique_invoices = int(raw_df[invoice_col].nunique()) if invoice_col else 0
    unique_items = int(raw_df[item_col].dropna().nunique()) if item_col else 0
    unique_customers = int(raw_df[cust_col].dropna().nunique()) if cust_col else 0

    # Basket Size Statistics
    if cleaned_data is not None:
        basket_sizes = [len(b) for b in cleaned_data.transactions_list]
    elif invoice_col and item_col:
        grouped = raw_df.groupby(invoice_col)[item_col].nunique()
        basket_sizes = grouped.values.tolist()
    else:
        basket_sizes = [1]

    if basket_sizes:
        arr = np.array(basket_sizes, dtype=float)
        q25 = float(np.percentile(arr, 25))
        median = float(np.median(arr))
        q75 = float(np.percentile(arr, 75))
        iqr = float(q75 - q25)
        skew_val = float(stats.skew(arr)) if len(arr) > 2 else 0.0

        basket_size_stats = {
            "min": int(np.min(arr)),
            "q25": round(q25, 2),
            "median": round(median, 2),
            "q75": round(q75, 2),
            "max": int(np.max(arr)),
            "mean": round(float(np.mean(arr)), 2),
            "std": round(float(np.std(arr)), 2),
            "iqr": round(iqr, 2),
            "skewness": round(skew_val, 2),
        }

        # Histogram distribution
        max_b = min(int(np.max(arr)), 30)
        bins = list(range(1, max_b + 2))
        hist, bin_edges = np.histogram(arr, bins=bins)
        basket_size_distribution = [
            {"basket_size": int(bin_edges[i]), "count": int(hist[i])}
            for i in range(len(hist))
        ]
    else:
        basket_size_stats = {
            "min": 0, "q25": 0, "median": 0, "q75": 0,
            "max": 0, "mean": 0, "std": 0, "iqr": 0, "skewness": 0
        }
        basket_size_distribution = []

    # Matrix density / Sparsity
    if cleaned_data is not None:
        matrix_density_pct = cleaned_data.matrix_density_pct
    else:
        total_possible = unique_invoices * unique_items
        matrix_density_pct = (raw_records_count / total_possible * 100.0) if total_possible > 0 else 0.0
    sparsity_pct = max(0.0, 100.0 - matrix_density_pct)

    # Item Frequency and Pareto Analysis
    top_frequent_items = []
    pareto_analysis = {}
    if item_col:
        item_counts = raw_df[item_col].dropna().astype(str).str.strip().str.upper().value_counts()
        total_item_mentions = int(item_counts.sum())

        for item_name, count in item_counts.head(20).items():
            freq = round(count / unique_invoices, 4) if unique_invoices > 0 else 0.0
            top_frequent_items.append({
                "item": str(item_name),
                "count": int(count),
                "frequency": float(freq),
            })

        # Pareto (Cumulative percentage)
        n_items = len(item_counts)
        if n_items > 0:
            cum_counts = item_counts.cumsum().values
            top_10_pct_idx = max(1, int(n_items * 0.10))
            top_20_pct_idx = max(1, int(n_items * 0.20))
            top_50_pct_idx = max(1, int(n_items * 0.50))

            pareto_analysis = {
                "top_10_percent_items_coverage_pct": round(float(cum_counts[min(top_10_pct_idx, n_items - 1)] / total_item_mentions * 100.0), 2),
                "top_20_percent_items_coverage_pct": round(float(cum_counts[min(top_20_pct_idx, n_items - 1)] / total_item_mentions * 100.0), 2),
                "top_50_percent_items_coverage_pct": round(float(cum_counts[min(top_50_pct_idx, n_items - 1)] / total_item_mentions * 100.0), 2),
                "total_unique_items_analyzed": n_items,
            }

    # Country Distribution
    country_distribution = []
    if country_col:
        c_counts = raw_df[country_col].dropna().value_counts()
        for c_name, count in c_counts.head(10).items():
            country_distribution.append({
                "country": str(c_name),
                "count": int(count),
                "percentage": round(float(count / raw_records_count * 100.0), 2),
            })

    # Temporal Distribution
    temporal_stats = None
    if date_col:
        try:
            dates = pd.to_datetime(raw_df[date_col], errors="coerce").dropna()
            if not dates.empty:
                temporal_stats = {
                    "start_date": dates.min().strftime("%Y-%m-%d"),
                    "end_date": dates.max().strftime("%Y-%m-%d"),
                    "total_days_span": int((dates.max() - dates.min()).days),
                    "busiest_day_of_week": dates.dt.day_name().value_counts().index[0],
                    "busiest_hour_of_day": int(dates.dt.hour.value_counts().index[0]),
                }
        except Exception as e:
            logger.debug(f"Could not parse temporal stats: {e}")

    return EDAProfile(
        dataset_name=dataset_name,
        raw_records_count=raw_records_count,
        unique_invoices=unique_invoices,
        unique_items=unique_items,
        unique_customers=unique_customers,
        cancellation_rate_pct=cancellation_rate_pct,
        sparsity_pct=sparsity_pct,
        matrix_density_pct=matrix_density_pct,
        basket_size_stats=basket_size_stats,
        basket_size_distribution=basket_size_distribution,
        top_frequent_items=top_frequent_items,
        pareto_analysis=pareto_analysis,
        country_distribution=country_distribution,
        temporal_stats=temporal_stats,
    )
