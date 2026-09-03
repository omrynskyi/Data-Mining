---
skill: programmatic-eda
pack: nimrodfisher/data-analytics-skills
crisp_dm_phase: 2 - Data Understanding
artifacts:
  - src/p2_programmatic_eda.py
  - artifacts/programmatic_eda/data_overview.txt
  - artifacts/programmatic_eda/null_profile.csv
  - artifacts/programmatic_eda/null_profile.txt
  - artifacts/programmatic_eda/outliers.csv
  - artifacts/programmatic_eda/outliers.txt
  - artifacts/programmatic_eda/distribution_summary.csv
  - artifacts/programmatic_eda/distribution_summary.txt
  - artifacts/programmatic_eda/correlation_strong_pairs.csv
  - artifacts/programmatic_eda/correlation.txt
  - reports/figures/p2_correlation_heatmap.png
---

## What the skill prescribes

A systematic, script-driven first pass over a new dataset before any deeper analysis:
(1) load and confirm the grain, (2) null profile against thresholds, (3) IQR + z-score
outlier detection, (4) descriptive stats and histograms, (5) correlation exploration
flagging `|r| >= 0.8`, (6) an EDA checklist sign-off, (7) write findings. The skill ships
five runnable scripts (`data_overview.py`, `null_profiler.py`, `outlier_detector.py`,
`distribution_summary.py`, `correlation_explorer.py`) that are meant to be run directly
against the dataset, not reimplemented.

This is deliberately the **structural/quality profiling pass** for this project — see
`exploratory-data-analysis.md` for the separate ML-readiness pass (target imbalance,
feature-target association, leakage) so the two skills don't duplicate each other.

## Applied to Telco churn

All 5 scripts were run for real (`src/p2_programmatic_eda.py`, `subprocess`-invoking each
script from `.claude/skills/programmatic-eda/scripts/`) against `data/Telco-Customer-Churn.csv`,
with `TotalCharges` coerced to numeric (the only pre-cleaning applied — everything else
profiled exactly as shipped).

**1. Structure (`data_overview.py`):** 7,043 rows × 21 columns, 7.42 MB in memory. 17 object
columns, 2 int64, 2 float64. Grain: one row per customer (`customerID` unique).

**2. Nulls (`null_profiler.py`):** only `TotalCharges` has nulls — 11 rows (0.16%), well under
the default 5% WARN threshold, so every column reports `OK`.

**3. Outliers (`outlier_detector.py`, IQR + z-score):** `SeniorCitizen` flags 1,142 "outliers"
(16.21%) — a **false positive**, an artifact of IQR on a 0/1 binary column, not a real anomaly.
`tenure`, `MonthlyCharges`, `TotalCharges` show **zero** IQR or z-score outliers — this dataset
has no extreme-value contamination in its numeric columns.

**4. Distributions (`distribution_summary.py`):** `tenure` is right-skewed toward short tenures
(skew 0.24, mode near 0-6 months — 1,371 of 7,043 customers). `MonthlyCharges` is mildly
left-skewed (skew -0.22) with visible bimodality (a low cluster near $20, a high cluster
near $80-100 — consistent with a DSL-vs-Fiber price split). `TotalCharges` is right-skewed
(skew 0.96), as expected from being roughly `tenure x MonthlyCharges`.

**5. Correlations (`correlation_explorer.py`, threshold 0.8):** exactly one pair clears the
0.8 bar: `tenure`-`TotalCharges` (r=0.826). `MonthlyCharges`-`TotalCharges` is strong but below
threshold (r=0.651). This is investigated precisely (not just flagged) as a target-leakage
question in `exploratory-data-analysis.md`, where the real relationship
(`TotalCharges ~= tenure * MonthlyCharges`, Pearson r=0.9996 on the derived product) is measured.

**EDA checklist sign-off:** grain confirmed (1 row = 1 customer, PK verified unique), null
thresholds all pass, no numeric outlier contamination requiring cleanup decisions, one
correlated pair flagged and handed off for the leakage-specific investigation.

## Outputs produced

- `src/p2_programmatic_eda.py` — runs all 5 skill scripts and builds the heatmap figure
- `artifacts/programmatic_eda/*.{txt,csv}` — real script stdout + CSV outputs for all 5 checks
- `reports/figures/p2_correlation_heatmap.png` — annotated numeric correlation matrix
