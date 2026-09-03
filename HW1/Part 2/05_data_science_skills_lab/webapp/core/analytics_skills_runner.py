"""Real analytics on the UCI Online Retail dataset, plus a dataset-independent
A/B test calculator.

run_ecommerce_analytics() is expensive (builds a real cohort matrix over ~542K
rows), so it is wrapped in functools.lru_cache(maxsize=1) -- computed once,
served from cache thereafter.
"""
import math
from functools import lru_cache

import numpy as np
import pandas as pd
from scipy import stats

from core.datasets import load_online_retail


def _clean_transactions(df: pd.DataFrame) -> pd.DataFrame:
    """Real non-cancelled transactions with a real non-null CustomerID.

    Excludes cancelled invoices (InvoiceNo starting with "C") and rows with
    missing CustomerID, per the documented real data-quality issues in this
    export. Does not touch the raw df returned by load_online_retail (that one
    stays raw for the data-quality-audit pipeline).
    """
    out = df.copy()
    out = out[~out["InvoiceNo"].astype(str).str.startswith("C")]
    out = out[out["CustomerID"].notna()]
    out = out[out["Quantity"] > 0]
    out = out[out["UnitPrice"] > 0]
    out["CustomerID"] = out["CustomerID"].astype(int)
    out["Revenue"] = out["Quantity"] * out["UnitPrice"]
    return out


@lru_cache(maxsize=1)
def run_ecommerce_analytics() -> dict:
    raw = load_online_retail()
    txns = _clean_transactions(raw)

    excluded_cancelled = int(raw["InvoiceNo"].astype(str).str.startswith("C").sum())
    excluded_missing_cust = int(raw["CustomerID"].isna().sum())

    # --- cohort retention matrix ---
    txns["order_month"] = txns["InvoiceDate"].dt.to_period("M")
    first_purchase = txns.groupby("CustomerID")["order_month"].min().rename("cohort_month")
    txns = txns.join(first_purchase, on="CustomerID")
    txns["months_since_first"] = (
        (txns["order_month"].dt.year - txns["cohort_month"].dt.year) * 12
        + (txns["order_month"].dt.month - txns["cohort_month"].dt.month)
    )

    cohort_sizes = txns.groupby("cohort_month")["CustomerID"].nunique()
    active_by_cohort_period = (
        txns.groupby(["cohort_month", "months_since_first"])["CustomerID"]
        .nunique()
        .reset_index(name="active_customers")
    )

    max_periods = 6
    cohort_matrix = []
    for cohort_month, cohort_size in cohort_sizes.items():
        row = {"cohort": str(cohort_month), "cohort_size": int(cohort_size)}
        sub = active_by_cohort_period[active_by_cohort_period["cohort_month"] == cohort_month]
        for period in range(max_periods + 1):
            match = sub[sub["months_since_first"] == period]
            active = int(match["active_customers"].iloc[0]) if len(match) else 0
            row[f"month_{period}"] = round(active / cohort_size * 100, 2) if cohort_size else None
        cohort_matrix.append(row)
    cohort_matrix.sort(key=lambda r: r["cohort"])

    # --- derived engagement funnel ---
    orders_per_customer = txns.groupby("CustomerID")["InvoiceNo"].nunique()
    spend_per_customer = txns.groupby("CustomerID")["Revenue"].sum()

    all_customers = orders_per_customer.index
    repeat_customers = orders_per_customer[orders_per_customer >= 2].index
    loyal_customers = orders_per_customer[orders_per_customer >= 5].index
    top_decile_cutoff = spend_per_customer.quantile(0.90)
    top_decile_customers = spend_per_customer[spend_per_customer >= top_decile_cutoff].index

    n_all = len(all_customers)
    funnel = [
        {"stage": "All customers (>=1 order)", "count": n_all,
         "conversion_from_previous_pct": 100.0, "conversion_from_start_pct": 100.0},
        {"stage": "Repeat (>=2 orders)", "count": len(repeat_customers),
         "conversion_from_previous_pct": round(len(repeat_customers) / n_all * 100, 2),
         "conversion_from_start_pct": round(len(repeat_customers) / n_all * 100, 2)},
        {"stage": "Loyal (>=5 orders)", "count": len(loyal_customers),
         "conversion_from_previous_pct": round(len(loyal_customers) / max(len(repeat_customers), 1) * 100, 2),
         "conversion_from_start_pct": round(len(loyal_customers) / n_all * 100, 2)},
        {"stage": "Top-decile spend (>=90th pct total revenue)", "count": len(top_decile_customers),
         "conversion_from_previous_pct": round(len(top_decile_customers) / max(len(loyal_customers), 1) * 100, 2),
         "conversion_from_start_pct": round(len(top_decile_customers) / n_all * 100, 2)},
    ]
    funnel_note = (
        "This transactional dataset has no browse/session event log, so the funnel is derived "
        "from real order-count and spend distributions, not a literal browse-to-purchase path: "
        "all customers -> repeat (2+ orders) -> loyal (5+ orders) -> top-decile by total real "
        "spend. Counts and conversion rates are computed directly from the cleaned transactions."
    )

    # --- revenue time series (monthly, excluding cancellations/returns) ---
    monthly_revenue = (
        txns.groupby(txns["InvoiceDate"].dt.to_period("M"))["Revenue"]
        .sum()
        .sort_index()
    )
    revenue_series = [
        {"month": str(m), "revenue": round(float(v), 2)}
        for m, v in monthly_revenue.items()
    ]
    revenue_note = (
        f"Monthly revenue = Quantity x UnitPrice summed per calendar month, computed only from "
        f"non-cancelled invoices with a valid CustomerID and positive Quantity/UnitPrice. "
        f"Excluded from this figure: {excluded_cancelled:,} real cancelled-invoice rows and "
        f"{excluded_missing_cust:,} rows with missing CustomerID (out of {len(raw):,} raw rows)."
    )

    return {
        "dataset": "UCI Online Retail (real transactions, cleaned view: "
                   f"{len(txns):,} of {len(raw):,} raw rows retained)",
        "cohort_retention": {
            "note": "Cohort = calendar month of each real customer's first non-cancelled "
                    "invoice; retention tracked by real months-since-first-purchase. Only rows "
                    "with a non-null CustomerID and non-cancelled invoices are used.",
            "matrix": cohort_matrix,
        },
        "engagement_funnel": {"note": funnel_note, "stages": funnel},
        "revenue_time_series": {"note": revenue_note, "monthly": revenue_series},
    }


def calculate_ab_test(n_control: int, x_control: int, n_treatment: int, x_treatment: int) -> dict:
    """Pure two-proportion z-test. No dataset dependency -- a live calculator.

    n_control / n_treatment: sample sizes. x_control / x_treatment: successes/conversions.
    """
    if n_control <= 0 or n_treatment <= 0:
        raise ValueError("sample sizes must be positive")
    if not (0 <= x_control <= n_control) or not (0 <= x_treatment <= n_treatment):
        raise ValueError("successes cannot exceed sample size or be negative")

    p_control = x_control / n_control
    p_treatment = x_treatment / n_treatment
    p_pool = (x_control + x_treatment) / (n_control + n_treatment)

    se_pool = math.sqrt(p_pool * (1 - p_pool) * (1 / n_control + 1 / n_treatment))
    z = (p_treatment - p_control) / se_pool if se_pool > 0 else 0.0
    p_value = 2 * (1 - stats.norm.cdf(abs(z)))

    se_diff = math.sqrt(
        p_control * (1 - p_control) / n_control + p_treatment * (1 - p_treatment) / n_treatment
    )
    diff = p_treatment - p_control
    ci_low = diff - 1.96 * se_diff
    ci_high = diff + 1.96 * se_diff

    relative_lift_pct = (diff / p_control * 100) if p_control > 0 else None

    return {
        "n_control": n_control,
        "n_treatment": n_treatment,
        "conversion_rate_control": round(p_control, 6),
        "conversion_rate_treatment": round(p_treatment, 6),
        "absolute_diff": round(diff, 6),
        "relative_lift_pct": round(relative_lift_pct, 4) if relative_lift_pct is not None else None,
        "z_statistic": round(float(z), 4),
        "p_value": round(float(p_value), 6),
        "significant_at_95pct": bool(p_value < 0.05),
        "confidence_interval_95pct": [round(ci_low, 6), round(ci_high, 6)],
    }
