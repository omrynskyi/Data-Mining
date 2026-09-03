---
skill: data-cleaning
pack: param087/agent-ml-skills
crisp_dm_phase: 3 - Data Preparation
artifacts:
  - data/processed/train_clean.csv
  - data/processed/test_clean.csv
  - artifacts/cleaning_report.md
  - artifacts/cleaning_outlier_summary.json
---

# data-cleaning

## What the skill prescribes

Turn raw data into a consistent, model-ready table without leaking information from the
future or the test split. The golden rule: every statistic used to clean (medians, modes,
bounds, category maps) must be learned from TRAIN only, then applied to test. Process:
deduplicate → fix types → standardize categoricals → handle missing values (per-column
strategy table) → treat outliers (cap/flag, never blindly delete) → validate.

## Applied to Telco churn

Ran `src/p3_data_cleaning.py` against `data/processed/train.csv` / `test.csv` (the stratified
80/20 split from `src/00_foundation.py`, seed 42).

1. **Deduplicate**: 0 duplicate `customerID` in either split — no action needed.
2. **Missing `TotalCharges`**: 8 nulls in train, 3 in test (11 total, matches
   `dataset_meta.json`). Every null has `tenure == 0` — brand-new customers with no completed
   billing cycle. **Decision: impute 0**, not the skill's default median-impute. Justification:
   `TotalCharges ≈ tenure * MonthlyCharges`, so at `tenure==0` the true value IS 0 — this is a
   domain fact, not a train statistic, so applying the same constant to train and test carries
   no leakage risk (unlike a train-median impute, which would fabricate a plausible-but-wrong
   number for a case the skill's own missing-value table doesn't quite cover).
3. **Sentinel categories**: `"No internet service"` (6 columns: OnlineSecurity, OnlineBackup,
   DeviceProtection, TechSupport, StreamingTV, StreamingMovies — 1,214 rows each, train) and
   `"No phone service"` (MultipleLines — 559 rows) are 100% redundant with
   `InternetService == 'No'` / `PhoneService == 'No'` (counts verified equal). **Decision:
   collapse to `'No'`** — removes duplicate one-hot columns without losing information, since
   `has_internet`/`has_phone` (feature-engineering step) carries that fact once.
4. **Dtype downcasting**: `SeniorCitizen`→int8, `tenure`→int16, charges→float32, object
   categoricals→`category`. Train memory: 5,666.8 KB → 559.5 KB (90.1% reduction).
5. **Outlier scan (IQR, train-only bounds)** on tenure, MonthlyCharges, TotalCharges: **0 points
   flagged in all three columns** — every value sits within `[Q1-1.5×IQR, Q3+1.5×IQR]`.
   **Decision: do NOT clip**, per the skill's own pitfall list (outliers that are real signal
   should be investigated, not deleted) — moot here since there's nothing to clip, but the
   reasoning is recorded for the modeling phase: even if there were extreme values, tenure/charges
   are bounded business quantities, not sensor noise, and clipping would destroy exactly the
   long-tenure, high-spend customers whose behavior the model needs.

## Outputs produced

- `data/processed/train_clean.csv`, `data/processed/test_clean.csv` — cleaned splits (5,634 /
  1,409 rows).
- `artifacts/cleaning_report.md` — full decision log with counts and justifications.
- `artifacts/cleaning_outlier_summary.json` — IQR bounds and flagged counts per column.
