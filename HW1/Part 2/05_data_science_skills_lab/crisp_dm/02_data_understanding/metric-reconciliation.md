---
skill: metric-reconciliation
pack: nimrodfisher/data-analytics-skills
crisp_dm_phase: 2 - Data Understanding
artifacts:
  - src/p2_metric_reconciliation.py
  - artifacts/metric_reconciliation/step1_baseline_reconciliation.csv
  - artifacts/metric_reconciliation/step2_definitional_difference.csv
  - artifacts/metric_reconciliation/step2_numeric_bridge.json
  - artifacts/telco.db
---

## What the skill prescribes

Systematically compare a metric across 2+ data sources, standardize formats, join/aggregate at
a common comparison level, compute absolute and percentage differences, investigate root causes
of any discrepancy, and produce a reconciliation report. No runnable scripts ship with this
skill (workflow guidance only) — see `metric-reconciliation-tracing.md` for the sibling skill
that does ship a script (`reconcile_metrics.py`) and is used for the deep-dive trace.

## Applied to Telco churn

Two real metrics — **churn rate** and **MRR** (sum of `MonthlyCharges` for active customers) —
computed independently from **three genuine sources**:

- **Source A** — raw CSV, loaded fresh with pandas (`data/Telco-Customer-Churn.csv`)
- **Source B** — SQLite database, queried with real SQL (`artifacts/telco.db`, built by
  `src/p2_sql_setup.py`)
- **Source C** — the processed stratified train/test split, recombined (`data/processed/{train,test}.csv`)

**Step 1 — baseline reconciliation (same metric definition, "ALL customers"):** all three
sources match to full float precision — churn rate 0.265370, MRR $316,985.75, both exact across
A/B/C (spread = 0.0 for both). This confirms the pipeline (raw CSV -> SQLite load -> train/test
split) introduces no silent data loss or transformation drift.

**Step 2 — deliberately introduced definitional difference:** recomputed both metrics
**excluding the 11 tenure==0 customers** (never-billed new joiners, `TotalCharges` null for
exactly these rows). Result:

| Definition | n | churn_rate | MRR |
|---|---|---|---|
| ALL customers | 7,043 | 0.265370 | $316,985.75 |
| EXCLUDING tenure==0 | 7,032 | 0.265785 | $316,530.15 |

**Numeric bridge, line by line:** none of the 11 excluded customers had churned (`Churn=='No'`
for all 11 — a brand-new customer cannot yet have churned), so removing them leaves the churn
**numerator** unchanged (1,869) while shrinking the **denominator** by 11 (7,043 -> 7,032),
mechanically raising the rate by +0.000415 (+0.0415 percentage points). For MRR, all 11 are
active, so their `$455.60` combined `MonthlyCharges` is subtracted exactly:
`$316,985.75 - $455.60 = $316,530.15`. Both bridges close to the cent / to 7 decimal places —
fully explained by this one 11-row adjustment, no residual gap.

Both deltas exceed the skill's suggested financial-metric tolerance (<0.1%): churn rate gap is
-0.1564%, MRR gap is +0.1437% — correctly flagged for investigation rather than silently
accepted, which is exactly what happens next in `metric-reconciliation-tracing.md`.

## Outputs produced

- `src/p2_metric_reconciliation.py` — computes all three sources under both definitions
- `artifacts/metric_reconciliation/step1_baseline_reconciliation.csv` — 3-source clean match
- `artifacts/metric_reconciliation/step2_definitional_difference.csv` — ALL vs EXCL. tenure==0
- `artifacts/metric_reconciliation/step2_numeric_bridge.json` — the exact line-by-line bridge
- `artifacts/telco.db` — the real SQLite database used as Source B
