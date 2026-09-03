---
skill: feature-engineering
pack: param087/agent-ml-skills
crisp_dm_phase: 3 - Data Preparation
artifacts:
  - data/processed/train_features.csv
  - data/processed/test_features.csv
  - artifacts/feature_engineering_report.md
  - artifacts/target_encoding_leakage_demo.json
---

# feature-engineering

## What the skill prescribes

Express signal in a form the model can use without leaking target or test information into a
feature. Covers categorical encoding strategy by cardinality, numeric transforms, datetime
features, and — the sharpest pitfall — leakage-safe (out-of-fold) target encoding for
high-cardinality columns.

## Applied to Telco churn

Ran `src/p3_feature_engineering.py` on the cleaned splits from the data-cleaning step.

**9 engineered features**: `tenure_bucket` (0-6mo…61mo+ lifecycle bands), `avg_monthly_spend`
(`TotalCharges/tenure`, falls back to `MonthlyCharges` at tenure==0), `spend_gap`
(`avg_monthly_spend - MonthlyCharges`), `num_addon_services` (count of 6 add-ons, 0-6),
`has_internet`, `is_month_to_month`, `is_electronic_check`, `charges_per_service`
(`MonthlyCharges / active-service-count`), `is_new_customer` (tenure ≤ 3).

**Leakage-safe target encoding demo** — `PaymentMethod x Contract` interaction (12 levels),
comparing naive full-data encoding vs 5-fold OOF encoding:

| | Naive (fit on all rows) | OOF (5-fold, leakage-safe) |
|---|---|---|
| Univariate AUC vs real Churn target | **0.7866** | **0.7791** |
| Inflation from leakage | — | **+0.0075 AUC** (+0.97% relative) |

**Stress test** (target shuffled to pure noise, so the true relationship is exactly zero):
- Naive encoding AUC on shuffled target: **0.5216** (leakage manufactures apparent signal out of
  nothing — should be ~0.50).
- OOF encoding AUC on shuffled target: **0.4917** (correctly stays near chance).

This demonstrates the skill's core pitfall concretely: fitting a target encoder on the same rows
it scores inflates apparent predictive power even when using smoothing (m=10), and the effect
persists even on a column with zero true relationship to the target.

## Outputs produced

- `data/processed/train_features.csv`, `data/processed/test_features.csv` — feature-engineered
  splits (test's `pm_contract_te_oof` encoded using the encoder fit on full train — no leakage,
  since test was never used to fit it).
- `artifacts/feature_engineering_report.md` — feature table + encoding comparison.
- `artifacts/target_encoding_leakage_demo.json` — the four AUC numbers above.
