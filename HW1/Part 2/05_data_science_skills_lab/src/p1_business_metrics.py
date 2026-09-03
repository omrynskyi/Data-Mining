"""CRISP-DM Phase 1 - business-metrics-calculator skill applied to Telco churn.

Computes real SaaS/subscription metrics from the full raw Telco-Customer-Churn.csv
(population level, n=7043 - not the train/test split, since these are business
baseline metrics, not modeling artifacts).

Business framing (per team-lead brief):
  - MonthlyCharges = recurring subscription price (MRR contribution per customer)
  - tenure         = months since acquisition
  - Churn          = voluntary churn flag (Yes/No in raw file)

Formulas follow .claude/skills/business-metrics-calculator/references/metric_definitions.md.
This dataset is a single cross-sectional snapshot (not a monthly ledger), so a few
definitions are adapted with explicit, documented assumptions - see notes in output.

Outputs:
  artifacts/business_metrics.json
  artifacts/business_metrics.md
"""
import json
import pathlib

import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "Telco-Customer-Churn.csv"
OUT_JSON = ROOT / "artifacts" / "business_metrics.json"
OUT_MD = ROOT / "artifacts" / "business_metrics.md"

df = pd.read_csv(RAW)
df["TotalCharges"] = pd.to_numeric(df["TotalCharges"].str.strip(), errors="coerce")
df["ChurnFlag"] = (df["Churn"] == "Yes").astype(int)

n_customers = len(df)
n_churned = int(df["ChurnFlag"].sum())
n_active = n_customers - n_churned

# --- Revenue metrics ---------------------------------------------------------
mrr = float(df["MonthlyCharges"].sum())                     # snapshot MRR, all customers
mrr_active = float(df.loc[df["ChurnFlag"] == 0, "MonthlyCharges"].sum())
arr = mrr * 12
arpu = float(df["MonthlyCharges"].mean())                   # per customer, all customers
arpu_active = float(df.loc[df["ChurnFlag"] == 0, "MonthlyCharges"].mean())

arpu_by_contract = (
    df.groupby("Contract")["MonthlyCharges"].mean().round(2).to_dict()
)
mrr_by_contract = (
    df.groupby("Contract")["MonthlyCharges"].sum().round(2).to_dict()
)

# --- Churn metrics -------------------------------------------------------------
# Logo churn rate: standard cross-sectional definition = churned customers / total
# customers ever acquired (this snapshot has no explicit "start of month" cohort,
# so this is the population/base churn rate, matching dataset_meta.json).
logo_churn_rate = n_churned / n_customers

# Revenue churn rate: churned MRR / total (starting) MRR - churned customers'
# current MonthlyCharges stand in for "MRR they were contributing before churning".
churned_mrr = float(df.loc[df["ChurnFlag"] == 1, "MonthlyCharges"].sum())
revenue_churn_rate = churned_mrr / mrr

# Monthly (hazard) churn rate: this dataset has no monthly time series, but `tenure`
# lets us approximate an average monthly churn probability empirically:
#   monthly_churn_rate ~= churned customers / total customer-months observed
# i.e. of all the customer-months this base has collectively logged, this fraction
# ended in a churn event. This is the standard approach used to turn a single
# cross-sectional telco snapshot into a monthly hazard rate for LTV math.
total_customer_months = float(df["tenure"].sum())
monthly_churn_rate = n_churned / total_customer_months

logo_churn_by_contract = (
    df.groupby("Contract")["ChurnFlag"].mean().round(4).to_dict()
)

# --- LTV (two variants, per team-lead brief; no COGS data => no margin-adjusted LTV) ---
# Variant A: churn-rate-based simple LTV = ARPU / monthly churn rate (industry formula,
# omitting the gross-margin factor since Telco COGS isn't in this dataset).
ltv_churn_based = arpu / monthly_churn_rate

# Variant B: tenure-based / empirical LTV = average total revenue actually collected
# per customer over their observed lifetime = mean(TotalCharges). This is a directly
# observed number, not a formula extrapolation.
ltv_tenure_based = float(df["TotalCharges"].mean(skipna=True))
avg_tenure_months = float(df["tenure"].mean())

# --- Revenue at risk -----------------------------------------------------------
# (a) Already realized: MRR lost to customers who have already churned.
revenue_at_risk_realized = churned_mrr

# (b) Forward-looking exposure: MRR currently held by ACTIVE customers in the
# highest-churn segment (Month-to-month contracts), i.e. revenue most exposed to
# near-term churn if no retention action is taken. This is a business-understanding
# proxy only - Phase 4/5 will replace it with a model-based risk score.
active_mtm_mrr = float(
    df.loc[(df["ChurnFlag"] == 0) & (df["Contract"] == "Month-to-month"), "MonthlyCharges"].sum()
)
active_mtm_customers = int(((df["ChurnFlag"] == 0) & (df["Contract"] == "Month-to-month")).sum())

# --- Benchmark comparison (thresholds from references/metric_definitions.md) --
def grade_ltv_cac(ratio):
    if ratio is None:
        return "n/a (no CAC data in dataset)"
    if ratio < 1:
        return "destroying value"
    if ratio < 3:
        return "marginal"
    if ratio < 5:
        return "healthy"
    return "very efficient / under-investing"

benchmarks = {
    "logo_churn_rate_monthly_benchmark": {
        "value": round(monthly_churn_rate, 6),
        "value_pct": round(monthly_churn_rate * 100, 2),
        "benchmark_note": "SaaS 'good' monthly logo churn is often cited as <2-3%/month; "
                           "telecom subscription churn tends to run higher. This value is "
                           "the empirical customer-month hazard rate derived from `tenure`.",
    },
    "ltv_cac_ratio": {
        "value": None,
        "note": "CAC not present in this dataset (no acquisition-cost field) - cannot "
                "compute LTV:CAC. Flagged as an open data gap for Phase 1 stakeholder doc.",
    },
}

metrics = {
    "population": {
        "n_customers": n_customers,
        "n_churned": n_churned,
        "n_active": n_active,
    },
    "revenue": {
        "mrr_all_customers": round(mrr, 2),
        "mrr_active_customers_only": round(mrr_active, 2),
        "arr_all_customers": round(arr, 2),
        "arpu_all_customers": round(arpu, 2),
        "arpu_active_customers_only": round(arpu_active, 2),
        "arpu_by_contract": arpu_by_contract,
        "mrr_by_contract": mrr_by_contract,
    },
    "churn": {
        "logo_churn_rate_base": round(logo_churn_rate, 6),
        "logo_churn_rate_base_pct": round(logo_churn_rate * 100, 3),
        "revenue_churn_rate_base": round(revenue_churn_rate, 6),
        "revenue_churn_rate_base_pct": round(revenue_churn_rate * 100, 3),
        "monthly_churn_rate_hazard": round(monthly_churn_rate, 6),
        "monthly_churn_rate_hazard_pct": round(monthly_churn_rate * 100, 3),
        "total_customer_months_observed": total_customer_months,
        "logo_churn_rate_by_contract": logo_churn_by_contract,
    },
    "ltv": {
        "ltv_churn_rate_based": round(ltv_churn_based, 2),
        "ltv_churn_rate_based_formula": "ARPU / monthly_churn_rate_hazard (no gross-margin "
                                         "factor: COGS not in dataset)",
        "ltv_tenure_based_empirical": round(ltv_tenure_based, 2),
        "ltv_tenure_based_formula": "mean(TotalCharges) - actual revenue collected per "
                                     "customer over observed lifetime",
        "avg_tenure_months": round(avg_tenure_months, 2),
    },
    "revenue_at_risk": {
        "realized_churned_mrr": round(revenue_at_risk_realized, 2),
        "realized_churned_mrr_pct_of_total_mrr": round(revenue_at_risk_realized / mrr * 100, 2),
        "forward_looking_active_month_to_month_mrr": round(active_mtm_mrr, 2),
        "forward_looking_active_month_to_month_mrr_pct_of_active_mrr": round(
            active_mtm_mrr / mrr_active * 100, 2
        ),
        "forward_looking_active_month_to_month_customers": active_mtm_customers,
        "note": "'Realized' = MRR already lost to customers who churned. 'Forward-looking' "
                "= MRR still held by active Month-to-month customers (the segment with the "
                "highest observed churn rate), i.e. revenue most exposed if no retention "
                "action is taken. Phase 4 modeling will replace this segment proxy with a "
                "per-customer risk score.",
    },
    "benchmarks": benchmarks,
    "data_gaps": [
        "No CAC / acquisition spend field -> LTV:CAC and payback period cannot be computed.",
        "No gross-margin / COGS field -> LTV uses revenue, not gross-profit, basis.",
        "Single cross-sectional snapshot (no monthly ledger) -> MRR waterfall "
        "(new/expansion/contraction) and NRR cannot be computed as defined for a "
        "recurring SaaS ledger; monthly churn is approximated via customer-months.",
    ],
}

OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
OUT_JSON.write_text(json.dumps(metrics, indent=2))

# --- Markdown table -------------------------------------------------------------
md = f"""# Business Metrics — Telco Customer Churn

Computed from `data/Telco-Customer-Churn.csv` (n={n_customers}), full population.
Source script: `src/p1_business_metrics.py`. Raw numbers: `artifacts/business_metrics.json`.

## Headline metrics

| Metric | Value |
|---|---|
| Customers (total / active / churned) | {n_customers:,} / {n_active:,} / {n_churned:,} |
| MRR (all customers) | ${mrr:,.2f} |
| MRR (active customers only) | ${mrr_active:,.2f} |
| ARR (run-rate, all customers) | ${arr:,.2f} |
| ARPU (all customers) | ${arpu:,.2f} |
| ARPU (active customers only) | ${arpu_active:,.2f} |
| Logo churn rate (base) | {logo_churn_rate*100:.2f}% |
| Revenue churn rate (base) | {revenue_churn_rate*100:.2f}% |
| Monthly churn rate (hazard, from customer-months) | {monthly_churn_rate*100:.3f}%/month |
| LTV — churn-rate-based (ARPU / monthly churn) | ${ltv_churn_based:,.2f} |
| LTV — tenure-based (mean TotalCharges) | ${ltv_tenure_based:,.2f} |
| Avg tenure (months) | {avg_tenure_months:.2f} |
| Revenue at risk — realized (churned MRR) | ${revenue_at_risk_realized:,.2f} ({revenue_at_risk_realized/mrr*100:.2f}% of total MRR) |
| Revenue at risk — forward-looking (active Month-to-month MRR) | ${active_mtm_mrr:,.2f} ({active_mtm_mrr/mrr_active*100:.2f}% of active MRR) |

## ARPU by contract type

| Contract | ARPU | MRR contribution | Logo churn rate |
|---|---|---|---|
"""
for c in arpu_by_contract:
    md += f"| {c} | ${arpu_by_contract[c]:,.2f} | ${mrr_by_contract[c]:,.2f} | {logo_churn_by_contract[c]*100:.2f}% |\n"

md += f"""
## Benchmark comparison

- **Monthly logo churn ({monthly_churn_rate*100:.2f}%/month):** SaaS "good" benchmark is
  typically <2-3%/month (`references/metric_definitions.md`). Telco's ~{monthly_churn_rate*100:.1f}%/month
  hazard rate is above the SaaS-good band, consistent with telecom being a higher-churn
  vertical than software subscriptions, and consistent with the {logo_churn_rate*100:.1f}%
  base (whole-tenure) churn rate.
- **LTV:CAC ratio:** cannot be graded — this dataset has no CAC / acquisition-spend field.
  Flagged as a data gap.
- **Revenue churn ({revenue_churn_rate*100:.2f}%):** exceeds logo churn rate ({logo_churn_rate*100:.2f}%),
  meaning churned customers skew toward *higher*-than-average MonthlyCharges — churn is
  concentrated somewhat more in higher-value accounts, which increases urgency for the
  retention program.

## Data gaps (documented per business-metrics-calculator skill's definition-choice step)

{chr(10).join(f"- {g}" for g in metrics["data_gaps"])}
"""

OUT_MD.write_text(md)
print(json.dumps(metrics, indent=2))
