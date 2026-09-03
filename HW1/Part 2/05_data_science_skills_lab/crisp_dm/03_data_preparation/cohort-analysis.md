---
skill: cohort-analysis
pack: nimrodfisher/data-analytics-skills
crisp_dm_phase: 3 - Data Preparation
artifacts:
  - artifacts/cohort_retention_matrix.csv
  - artifacts/cohort_analysis_report.md
  - reports/figures/cohort_retention_heatmap.png
  - reports/figures/cohort_survival_curves.png
---

# cohort-analysis

## What the skill prescribes

Define cohort grouping + retention event → build a cohort × period membership table → compute
the period-over-period retention matrix → visualize as a heatmap + retention curves → interpret
using the retention glossary and cohort-pattern references.

## Applied to Telco churn — cross-sectional reconstruction, with the limitation stated up front

Telco churn ships as ONE snapshot row per customer (`tenure`, `Churn`), not an event log. To use
the skill's machinery, `src/p3_cohort_analysis.py` reconstructs a signup cohort: back-calculates
`join_date = snapshot(2020-03-01) - tenure months`, buckets into calendar quarters (25 cohorts,
sizes 105-495 — all above the skill's 100-user minimum), and computes retention via a life-table
/discrete-hazard method (adapting the shipped `retention_matrix.py` logic to duration+event data
instead of raw activity timestamps).

**KEY LIMITATION (stated explicitly per the brief)**: because cohort membership is back-derived
FROM `tenure` — which is also each customer's own outcome duration — the reconstruction is exact
for still-active (censored) customers but **systematically wrong for churned customers**: a
churned customer's `tenure` reflects time-to-churn, not time-to-snapshot, so back-calculating
their join date places them in a cohort bucket that looks more RECENT than their true signup
cohort. Net effect: reconstructed cohorts are not a true longitudinal panel — early churners from
a true historical cohort get silently reassigned to newer buckets, leaving older buckets
disproportionately populated by longer survivors.

**Quantified bias direction**: the oldest reconstructed cohort (2014Q1, n=434) sits, on average,
**+24.38 percentage points** above the whole-population pooled life-table survival curve at
matching tenure months — confirming the predicted upward survivorship bias in old reconstructed
cohorts. The pooled (non-cohort-split) curve, which uses every customer's own (tenure, churn)
pair once and isn't subject to this specific reassignment bias, is the safer number for "typical
hazard by tenure month."

**Early-tenure hazard spike** (pooled curve): mean hazard months 0-11 = **1.32%/mo** vs months
12+ = **0.60%/mo** — first-year hazard is **2.2x** later-tenure hazard (statistical confirmation
with proper power via person-month test in the time-series-analysis doc).

## Outputs produced

- `artifacts/cohort_retention_matrix.csv` — 25-cohort × 73-period life-table survival matrix.
- `artifacts/cohort_analysis_report.md` — definitions, limitation, bias quantification, hazard
  numbers.
- `reports/figures/cohort_retention_heatmap.png` — triangular retention heatmap (natural shape:
  newer cohorts have fewer observable periods, exactly as expected).
- `reports/figures/cohort_survival_curves.png` — pooled curve vs selected cohort curves.
