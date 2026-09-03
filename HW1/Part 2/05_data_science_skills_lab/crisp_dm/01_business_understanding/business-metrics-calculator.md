---
skill: business-metrics-calculator
pack: nimrodfisher/data-analytics-skills
crisp_dm_phase: 1 - Business Understanding
artifacts: [src/p1_business_metrics.py, artifacts/business_metrics.json, artifacts/business_metrics.md]
---

# Business Metrics Calculator — Telco Customer Churn

## What the skill prescribes

- Identify the business model type (SaaS subscription, e-commerce, etc.) and the calculation period; model type determines which metrics apply.
- Load and validate the underlying data (row counts, missing values, plausible ranges) before calculating anything.
- Calculate primary metrics (MRR, ARR, churn, etc.) using `scripts/saas_metrics.py` or an adapted equivalent.
- Calculate unit economics — LTV, CAC, LTV:CAC, payback period — documenting which lifetime assumptions were used.
- Compare each metric to the industry benchmark thresholds in `references/metric_definitions.md`; flag anything outside the acceptable range.
- Produce the metrics report (`assets/metrics_report_template.md`) with 3-5 key insights and any definition choices that differ from the standard.

## Applied to Telco churn

### Model type and period

Treated as a **subscription (SaaS-style) business** per the team framing: MonthlyCharges = recurring subscription price / MRR contribution, tenure = months since acquisition. Calculation period: this dataset is a **single cross-sectional snapshot** (7,043 customers, no dated ledger), not a monthly time series — this is the single most important definition choice in this write-up and is called out wherever it affects a formula.

### Data validation before calculating

- Row count: 7,043 customers, 0 duplicate `customerID`s (`data/processed/dataset_meta.json`).
- `TotalCharges` required numeric coercion (11 blank strings, all `tenure == 0`) before use.
- `Churn` recoded Yes/No -> 1/0.
- Script: `src/p1_business_metrics.py` (executed against the full raw file, all 7,043 rows — population-level, not the modeling train/test split).

### Metrics computed (real, from `artifacts/business_metrics.json`)

| Metric | Value | Definition used |
|---|---|---|
| MRR (all customers) | **$456,116.60** | `sum(MonthlyCharges)` |
| MRR (active only) | **$316,985.75** | same, `Churn == 0` |
| ARR (run-rate) | **$5,473,399.20** | MRR x 12 |
| ARPU (all customers) | **$64.76/mo** | `mean(MonthlyCharges)` |
| ARPU (active only) | **$61.27/mo** | same, active only |
| Logo churn rate (base) | **26.537%** | churned customers / total customers — matches `dataset_meta.json` exactly |
| Revenue churn rate (base) | **30.503%** | churned customers' MonthlyCharges / total MRR |
| Monthly churn rate (hazard, derived) | **0.820%/month** | churned customers / total customer-months of `tenure` (see Definition choices) |
| LTV — churn-rate-based | **$7,899.96** | ARPU / monthly hazard rate (no gross-margin factor — see gaps) |
| LTV — tenure-based (empirical) | **$2,283.30** | `mean(TotalCharges)` — actual revenue collected to date per customer |
| Revenue at risk — realized | **$139,130.85** (30.50% of total MRR) | churned customers' current MonthlyCharges |
| Revenue at risk — forward-looking | **$136,447.05** (43.05% of active MRR) | active Month-to-month customers' MonthlyCharges |

### ARPU / churn by contract (segment cut, real)

| Contract | ARPU | MRR | Logo churn rate |
|---|---|---|---|
| Month-to-month | $66.40 | $257,294.15 | **42.71%** |
| One year | $65.05 | $95,816.60 | 11.27% |
| Two year | $60.77 | $103,005.85 | 2.83% |

### Definition choices that differ from the standard (documented per the skill's step 6)

1. **Monthly churn rate is derived, not observed.** The dataset has no monthly ledger, so a true month-over-month logo churn rate can't be computed directly. Instead: `monthly_churn_rate = churned_customers / total_customer_months`, where `total_customer_months = sum(tenure)` across all 7,043 customers (227,990 customer-months). This is the standard technique for turning a single telco churn snapshot into an approximate hazard rate, and is explicitly labeled as such everywhere it's used (notably as the LTV denominator).
2. **LTV omits the gross-margin factor.** The textbook formula is `ARPU x gross_margin / monthly_churn_rate`; this dataset has no COGS field, so the churn-rate-based LTV above is a *revenue* LTV, not a *gross-profit* LTV. Flagged as a data gap, not silently assumed at 100% margin.
3. **No MRR waterfall (new/expansion/contraction/churned).** `scripts/saas_metrics.py`'s `mrr_components()` function expects a real waterfall; this snapshot can't populate it (no "starting" vs. "ending" period). Not attempted — would fabricate numbers.
4. **No CAC / LTV:CAC / payback period.** No acquisition-spend field exists in this dataset. Explicitly reported as `null` with a note in `artifacts/business_metrics.json`, rather than guessing a CAC.

### Benchmark comparison (`references/metric_definitions.md`)

- **Monthly logo churn (0.82%/month):** below the commonly cited SaaS "good" band (<2-3%/month) — but this is the *whole-base average* hazard rate, which is pulled down by long-tenured survivors; it should not be read as "churn is healthy." The base (whole-tenure) churn rate of 26.54% and the Month-to-month segment rate of 42.71% are the more decision-relevant numbers for the retention program and are far above any SaaS-good benchmark.
- **LTV:CAC ratio:** not gradable — no CAC data (see data gaps).
- **Revenue churn (30.50%) > logo churn (26.54%):** churn skews toward higher-MonthlyCharges accounts — a meaningful signal not visible from customer-count churn alone.

### Key insights (skill's step 6 requirement: 3-5 insights)

1. **Contract term is the dominant churn lever.** Month-to-month churn (42.71%) is 15x the Two-year rate (2.83%). Converting even a slice of the $257,294.15/mo Month-to-month MRR pool to longer contracts is the single highest-leverage retention action visible in Phase 1.
2. **Churn is value-skewed.** Revenue churn (30.50%) exceeds logo churn (26.54%) — the retention program should weight outreach by revenue, not just customer count, matching the "revenue-weighted ranked list" requirement from the stakeholder interview.
3. **$136,447.05/mo (43.05% of active MRR) sits in the highest-risk segment right now** (active Month-to-month customers) — this is the effective upper bound of near-term revenue exposure before any model-based scoring narrows it down in Phase 4.
4. **LTV has genuine uncertainty, not a single number.** The churn-rate-based estimate ($7,899.96) and the tenure-based empirical estimate ($2,283.30) differ by >3x — both are reported rather than picking one, since they answer different questions (extrapolated future value vs. revenue already realized).
5. **Unit economics (CAC, LTV:CAC, payback) cannot be completed with this dataset** — a clearly flagged scope boundary for the retention business case, not a silent omission.

## Outputs produced

- `src/p1_business_metrics.py` — executed successfully; every number above traces to this script's output.
- `artifacts/business_metrics.json` — full machine-readable metrics + benchmarks + documented data gaps.
- `artifacts/business_metrics.md` — the metrics report table (per `assets/metrics_report_template.md` structure).
