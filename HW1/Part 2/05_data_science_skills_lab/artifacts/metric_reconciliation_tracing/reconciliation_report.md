# Metric Reconciliation Report

**Metric:** Churn rate and Monthly Recurring Revenue (MRR)
**Period:** Full Kaggle snapshot (no date dimension in this static extract)
**Analyst:** phase2-data-agent
**Date:** 2026-09-02

---

## Values compared

| Source | Churn rate | MRR | Query / Pipeline |
|---|---|---|---|
| A — "ALL customers" definition | 0.265370 (26.5370%) | $316,985.75 | `SELECT COUNT(*), SUM(CASE WHEN Churn='Yes'...)... FROM customers` — no WHERE clause |
| B — "EXCLUDING tenure==0" definition | 0.265785 (26.5785%) | $316,530.15 | Same query + `WHERE tenure != 0` |

Both pulled from the same underlying table (`artifacts/telco.db` / `data/Telco-Customer-Churn.csv`
— confirmed identical to each other in Step 1 of `metric-reconciliation.md`'s baseline check, so
this is **not** a cross-system discrepancy; it is a controlled, single-system definitional A/B run
by design, to demonstrate the tracing workflow end-to-end).

**Churn rate — absolute difference:** −0.000415 (B − A) | **Percentage difference:** −0.1564% (using `reconcile_metrics.py`'s definition, `(A−B)/A`)
**MRR — absolute difference:** +$455.60 (A − B) | **Percentage difference:** +0.1437%
**Within tolerance:** No for both, against the skill's default 0.1% tolerance (`reconcile_metrics.py --tolerance 0.001`, matching the "Financial totals (operational) < 0.1%" guideline in `references/reconciliation_patterns.md`). Both runs returned `STATUS: INVESTIGATE` (see `artifacts/metric_reconciliation_tracing/reconcile_metrics_churn_rate.txt` and `_mrr.txt` — real script output, not simulated).

---

## Root cause

**Status:** Confirmed

**Cause category:** Filter difference (population/denominator scope) — specifically an
**inclusion/exclusion filter on `tenure == 0`**, per `references/reconciliation_patterns.md` §1.

**Description:**
Source B's query adds `WHERE tenure != 0`, excluding 11 customers who joined but have not yet
completed a billing cycle (`TotalCharges` is NULL for exactly these 11 rows — confirmed 1:1 overlap
in `data_quality_scorecard.md`). None of these 11 customers have churned (`Churn == 'No'` for all
11 — a brand-new customer cannot yet have churned by construction of this dataset). Removing them:
- **Leaves the numerator (`n_churned` = 1,869) unchanged** for churn rate — they contribute 0 to it.
- **Shrinks the denominator** from 7,043 to 7,032, which mechanically *increases* the churn rate
  (fewer non-churned customers diluting the same churn count) — explaining the sign of the delta.
- **Removes their `MonthlyCharges` from the active-customer MRR sum** (all 11 are `Churn=='No'`,
  i.e. active) — explaining why MRR strictly decreases when they're excluded.

## Evidence

**Steps taken to identify the cause** (following `references/reconciliation_patterns.md`'s
investigation sequence):

1. **Confirmed the numbers** — pulled Source A and Source B directly from `artifacts/telco.db` via
   `sqlite3`/pandas, not from a cached or intermediate report (`src/p2_metric_reconciliation.py`).
2. **Checked the grain** — both queries operate at customer grain, one row per `customerID`; grain
   is not the divergence (ruled out `references/reconciliation_patterns.md` §3).
3. **Aligned the period** — not applicable; this is a static snapshot with no time dimension
   (ruled out §4 time zone handling and §6 refresh lag entirely).
4. **Compared filters side by side** — Source A: no WHERE clause. Source B: `WHERE tenure != 0`.
   **This is the single line that differs between the two queries.**
5. **Compared joins** — neither query joins any table; ruled out §2 join type mismatches.
6. **Sample-level check** — pulled the 11 rows present in Source A but excluded from Source B:

   ```sql
   SELECT customerID, tenure, MonthlyCharges, TotalCharges, Churn
   FROM customers WHERE tenure = 0;
   -- 11 rows, all Churn = 'No', all TotalCharges IS NULL, MonthlyCharges sums to $455.60
   ```

   This sample-level pull is exactly what explains both deltas quantitatively (see bridge below) —
   confirming the root cause is fully explained by these 11 rows and nothing else.

**Key finding:** The one-line filter `WHERE tenure != 0` is the entire divergence. There is no
additional bug, timing issue, or calculation-logic difference — the two "sources" here are in fact
the same data under two different, both-legitimate, business definitions of "customer."

---

## Numeric bridge (Source A -> adjustments -> Source B)

**Churn rate:**

| Step | Value |
|---|---|
| Source A value (ALL customers, n=7,043) | 0.265370 |
| − Adjustment: remove 11 tenure==0 rows from denominator (0 of them churned, so numerator unchanged at 1,869) | denominator 7,043 → 7,032 |
| = Source B value (EXCL. tenure==0, n=7,032) | 0.265785 |
| **Bridge closes exactly:** 1,869 / 7,032 = 0.2657850 ✓ matches Source B to 7 decimal places | |

**MRR:**

| Step | Value |
|---|---|
| Source A value (ALL active customers) | $316,985.75 |
| − Adjustment: remove `MonthlyCharges` of the 11 active tenure==0 customers | −$455.60 |
| = Source B value (EXCL. tenure==0 active customers) | $316,530.15 |
| **Bridge closes exactly:** $316,985.75 − $455.60 = $316,530.15 ✓ | |

Both bridges close to the cent / to 7 decimal places using only the 11-row adjustment — no residual
unexplained gap, so the investigation is complete (no further divergence points to trace).

---

## Resolution

**Designated source of truth:** Neither is "more correct" — this is a genuine business-definition
choice, not a data error. Recommendation: **use "ALL customers" (Source A) as the default** for
churn-rate reporting, because it is the simpler, more conservative definition and matches
`dataset_meta.json`'s canonical `churn_rate_overall: 0.26537`, which downstream Phase 2/3 artifacts
(train/test split, EDA) already reference. Reserve "EXCLUDING tenure==0" for analyses specifically
about *billed* customer behavior (e.g., anything using `TotalCharges`, which is undefined for these
11 rows).

**Action required:**
- [x] No pipeline fix needed — both queries are correct for their stated definitions.
- [x] Definition clarification needed (owner: phase2-data-agent, by: 2026-09-02) — **done**: this
      report documents both definitions and recommends a default. Any dashboard or report citing a
      churn rate should state which of the two denominators it uses.
- [ ] Downstream consumers need recalculation — no, `dataset_meta.json`, `train.csv`/`test.csv`, and
      `data_quality_scorecard.md` all already use the "ALL customers" definition consistently.
- [x] Gap is outside the skill's default 0.1% financial-metric tolerance, but is now fully
      explained and closed — reclassified from INVESTIGATE to RESOLVED / ACCEPTED-AS-DEFINITIONAL.

---

## Preventive measure

Document the denominator explicitly in every future churn-rate query's column alias or a code
comment (e.g. `churn_rate_all_customers` vs. `churn_rate_billed_customers_only`) rather than a bare
`churn_rate`, so a future reader cannot silently mix the two. This is applied prospectively in
`artifacts/sql/churn_rate_by_contract.sql` (uses the ALL-customers definition, documented in
`sql-to-business-logic.md`).

---

*Template: reconciliation_report_template.md (metric-reconciliation-tracing skill). Reconciliation
math verified twice: once analytically in `src/p2_metric_reconciliation.py`
(`artifacts/metric_reconciliation/step2_numeric_bridge.json`), and once independently via the
skill's own `scripts/reconcile_metrics.py` `compare_values()`/`reconciliation_report()` functions
on the same two numbers (`artifacts/metric_reconciliation_tracing/reconcile_metrics_churn_rate.txt`,
`_mrr.txt`) — both agree. Note: `reconcile_metrics.py`'s `if __name__ == "__main__":` block, like
`sql_explainer.py` and `schema_compare.py` in this same skill pack, always runs its own hardcoded
demo instead of calling `main()`, so it was invoked by importing the module's functions directly.*
