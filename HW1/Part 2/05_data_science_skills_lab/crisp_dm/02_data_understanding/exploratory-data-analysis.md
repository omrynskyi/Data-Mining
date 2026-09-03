---
skill: exploratory-data-analysis
pack: param087/agent-ml-skills
crisp_dm_phase: 2 - Data Understanding
artifacts:
  - src/p2_exploratory_data_analysis.py
  - artifacts/exploratory_data_analysis/eda_ml_report.json
  - artifacts/exploratory_data_analysis/cramers_v_categorical_vs_target.csv
  - artifacts/exploratory_data_analysis/point_biserial_numeric_vs_target.csv
  - artifacts/exploratory_data_analysis/numeric_multicollinearity.csv
  - reports/figures/p2_target_distribution.png
  - reports/figures/p2_feature_target_association.png
  - reports/figures/p2_totalcharges_leakage_scatter.png
---

## What the skill prescribes

The modeling-readiness EDA pass: shape/types, missingness, **target distribution/class
balance**, univariate/bivariate analysis, correlation, and an explicit **leakage scan** —
flagging features with `|corr| > 0.95` with the target, IDs, timestamps, or post-outcome
columns. Explicitly warns to fit only on the training split to avoid leaking test information
into feature decisions.

This is deliberately distinct from `programmatic-eda.md` (the structural/quality profiling
pass on the full dataset) — this pass is fit on `data/processed/train.csv` **only** (5,634
rows), per the skill's own Pitfalls section.

## Applied to Telco churn

**1. Target distribution + imbalance:** 1,495 churned / 4,139 not-churned in train (26.54%
churn rate, matching `dataset_meta.json`). Imbalance ratio 2.77:1 — moderate, not severe;
worth noting for Phase 4 metric choice (accuracy alone would be misleading) but not requiring
aggressive resampling.

**2. Feature-target association** (train only):
- **Cramer's V (categorical, 16 features):** `Contract` strongest (V=0.4107, chi2 p<1e-207),
  followed by `OnlineSecurity` (0.3506), `TechSupport` (0.3444), `InternetService` (0.3261),
  `PaymentMethod` (0.3103). Weakest: `gender` (V=0.0000, p=0.89 — no association at all),
  `PhoneService` (0.0120, p=0.20 — not significant).
- **Point-biserial r (numeric, 3 features):** `tenure` strongest (r=-0.3456, p~8.6e-158 —
  longer-tenured customers churn less), `MonthlyCharges` (r=+0.1980), `TotalCharges`
  (r=-0.1948).

**3. Multicollinearity (numeric features):** one pair flagged at the `|r|>=0.7` threshold —
`tenure`-`TotalCharges` (r=0.8294). `MonthlyCharges`-`TotalCharges` is r=0.6540, below the flag
threshold but still worth watching for a linear model.

**4. Target-leakage scan — the specific TotalCharges investigation:**
- Generic scan (`|corr|>0.95` with target among numeric features): **none found** — no numeric
  feature is a disguised copy of the target.
- **Direct hypothesis test:** `TotalCharges ~= tenure * MonthlyCharges` — measured
  **Pearson r = 0.9996** (p~0.0, n=5,626) between `TotalCharges` and the derived product.
  Median absolute percentage error is **1.97%**, mean **3.20%**.
- **Verdict: NOT target leakage.** `TotalCharges`, `tenure`, and `MonthlyCharges` are all
  pre-outcome billing attributes known at prediction time — none encodes the `Churn` outcome
  itself (their point-biserial correlations with `Churn` are weak-to-moderate, nowhere near the
  0.95 leakage-suspect threshold). The near-identity relationship is a **redundancy /
  multicollinearity** finding, not leakage: `TotalCharges` is almost fully reconstructible from
  two columns already in the feature set. **Recommendation for Phase 3:** drop `TotalCharges`
  or replace it with an engineered residual (`TotalCharges - tenure*MonthlyCharges`, which would
  capture mid-tenure plan/price changes) rather than feeding all three raw, near-collinear
  columns into a linear model.

## Outputs produced

- `src/p2_exploratory_data_analysis.py` — computes all of the above on train only
- `artifacts/exploratory_data_analysis/eda_ml_report.json` — full structured results including
  the leakage verdict text
- `artifacts/exploratory_data_analysis/cramers_v_categorical_vs_target.csv`,
  `point_biserial_numeric_vs_target.csv`, `numeric_multicollinearity.csv` — ranked tables
- `reports/figures/p2_target_distribution.png`, `p2_feature_target_association.png`,
  `p2_totalcharges_leakage_scatter.png` — supporting figures
