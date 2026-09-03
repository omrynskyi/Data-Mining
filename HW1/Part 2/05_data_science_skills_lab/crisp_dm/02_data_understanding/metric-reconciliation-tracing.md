---
skill: metric-reconciliation-tracing
pack: nimrodfisher/data-analytics-skills (02-documentation-knowledge variant)
crisp_dm_phase: 2 - Data Understanding
artifacts:
  - artifacts/metric_reconciliation_tracing/reconciliation_report.md
  - artifacts/metric_reconciliation_tracing/reconcile_metrics_churn_rate.txt
  - artifacts/metric_reconciliation_tracing/reconcile_metrics_mrr.txt
---

## What the skill prescribes

Trace a metric discrepancy to root cause and closure: define scope, pull both sources, compute
the gap, walk each computation path step by step, classify the root cause using the reference
guide's categories (definition mismatch, freshness, grain, calculation bug), then document
resolution and a preventive measure in `assets/reconciliation_report_template.md`. Ships
`scripts/reconcile_metrics.py` (`compare_values()` + `reconciliation_report()`) for the
numeric comparison step.

## Applied to Telco churn

Took the discrepancy discovered in `metric-reconciliation.md` (churn rate and MRR under
"ALL customers" vs. "EXCLUDING tenure==0" definitions) and ran the full investigation sequence
to closure:

1. **Confirmed the numbers** directly from `artifacts/telco.db`, not a cached report.
2. **Checked the grain** — both queries are customer-grain; ruled out.
3. **Aligned the period** — N/A, static snapshot with no time dimension; ruled out timezone/lag.
4. **Compared filters side by side** — the *entire* divergence is one line: `WHERE tenure != 0`.
5. **Compared joins** — neither query joins anything; ruled out.
6. **Sample-level check** — pulled the 11 `tenure==0` rows directly and confirmed: all
   `Churn=='No'`, all `TotalCharges IS NULL`, `MonthlyCharges` sums to exactly $455.60.
7. **Documented root cause**: a population/denominator scoping difference (an inclusion filter
   on `tenure==0`), classified under "Filter differences" per
   `references/reconciliation_patterns.md`.

The skill's own `scripts/reconcile_metrics.py` was run on the real numbers (imported directly —
see tooling note below) to independently confirm the gap classification:

```
Churn rate — ALL (0.2654) vs EXCL. tenure==0 (0.2658): -0.1564% -> STATUS: INVESTIGATE
MRR         — ALL ($316,985.75) vs EXCL. tenure==0 ($316,530.15): +0.1437% -> STATUS: INVESTIGATE
```

Both exceed the skill's 0.1% default tolerance, correctly triggering the INVESTIGATE path. The
investigation closes with **both numeric bridges reconciling exactly** to the 11-row adjustment
(no residual, unexplained gap) — reclassified from INVESTIGATE to RESOLVED / ACCEPTED-AS-DEFINITIONAL,
with a recommendation to standardize on the "ALL customers" definition as the reporting default
(it already matches `dataset_meta.json`'s canonical `churn_rate_overall: 0.26537`) and to always
name the denominator explicitly in future churn-rate query aliases.

**Tooling bug found:** `reconcile_metrics.py`'s `if __name__ == "__main__":` block always runs a
hardcoded demo (two literal numbers, 125000 vs 118120) rather than calling its own `main()` —
identical bug pattern to `sql_explainer.py` and `schema_compare.py` (three scripts, two skill
packs). Worked around by importing `compare_values()`/`reconciliation_report()` directly and
calling them on the real churn-rate and MRR numbers.

## Outputs produced

- `artifacts/metric_reconciliation_tracing/reconciliation_report.md` — the completed
  `reconciliation_report_template.md`, including the full numeric bridge and resolution
- `artifacts/metric_reconciliation_tracing/reconcile_metrics_churn_rate.txt`,
  `_mrr.txt` — real output from the skill's own `reconcile_metrics.py` functions
