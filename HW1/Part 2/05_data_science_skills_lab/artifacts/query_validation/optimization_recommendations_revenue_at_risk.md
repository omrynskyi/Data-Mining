# Query Optimization Recommendations: revenue_at_risk_by_contract

**Date:** 2026-09-02
**Original runtime:** 4.29 ms average (200-run loop, SQLite, 7,043-row table)
**Target runtime:** N/A at this scale — optimization is about read-pattern scalability, not current latency.

---

## Priority 1 — Replace duplicated correlated subquery with a CTE

**Problem:** The query computes `historical_churn_rate` via a correlated scalar subquery, then repeats the *identical* subquery a second time to compute `expected_monthly_revenue_at_risk`. EXPLAIN QUERY PLAN confirms two separate `SCAN customers_raw` sub-plans nested under `CORRELATED SCALAR SUBQUERY 1` and `CORRELATED SCALAR SUBQUERY 2`.

**Root cause:** The churn rate per contract was expressed inline twice instead of computed once and joined.

**Recommendation:**

```sql
-- Before
SELECT
    c1.Contract,
    COUNT(*) AS n_active_customers,
    ROUND(SUM(c1.MonthlyCharges), 2) AS active_mrr,
    ROUND((SELECT 1.0*SUM(CASE WHEN c2.Churn='Yes' THEN 1 ELSE 0 END)/COUNT(*)
           FROM customers c2 WHERE c2.Contract = c1.Contract), 4) AS historical_churn_rate,
    ROUND(SUM(c1.MonthlyCharges) *
          (SELECT 1.0*SUM(CASE WHEN c2.Churn='Yes' THEN 1 ELSE 0 END)/COUNT(*)
           FROM customers c2 WHERE c2.Contract = c1.Contract), 2) AS expected_monthly_revenue_at_risk
FROM customers c1
WHERE c1.Churn = 'No'
GROUP BY c1.Contract
ORDER BY expected_monthly_revenue_at_risk DESC;

-- After
WITH contract_churn AS (
    SELECT Contract, 1.0*SUM(CASE WHEN Churn='Yes' THEN 1 ELSE 0 END)/COUNT(*) AS rate
    FROM customers GROUP BY Contract
)
SELECT
    c1.Contract,
    COUNT(*) AS n_active_customers,
    ROUND(SUM(c1.MonthlyCharges), 2) AS active_mrr,
    ROUND(cc.rate, 4) AS historical_churn_rate,
    ROUND(SUM(c1.MonthlyCharges) * cc.rate, 2) AS expected_monthly_revenue_at_risk
FROM customers c1
JOIN contract_churn cc ON cc.Contract = c1.Contract
WHERE c1.Churn = 'No'
GROUP BY c1.Contract, cc.rate
ORDER BY expected_monthly_revenue_at_risk DESC;
```

**Verification performed:** Both versions were actually run against `artifacts/telco.db`. Results are byte-identical (`df_orig.equals(df_cte) == True`) across all 5 output columns and all 3 rows. `EXPLAIN QUERY PLAN` on the rewrite shows the churn-rate computation collapsed into a single `CO-ROUTINE contract_churn` materialized once, then joined via `SEARCH cc USING AUTOMATIC COVERING INDEX` — down from 3 total `SCAN customers_raw` passes (1 outer + 2 subquery) to 2 (1 for the CTE, 1 for the outer query).

**Expected impact (measured, not estimated):** 200-iteration timing loop, same connection, same machine:

| Version | Avg latency | `SCAN customers_raw` count |
|---|---|---|
| Original (duplicated correlated subquery) | 4.29 ms | 3 |
| CTE rewrite | 3.66 ms | 2 |

**1.17x real speedup** at 7,043 rows. The gain is modest here because SQLite's page cache makes repeat full-table scans of a 7K-row table cheap regardless. The recommendation is made primarily for **scalability**, not current latency: the row-read count scales linearly with table size × (1 + number of duplicated subquery occurrences), so on a multi-million-row production customers table the same query would do 3x the necessary I/O, and the CTE form's advantage would grow accordingly.

**Risk:** Low — verified semantically equivalent by direct result comparison, not just reasoning about the SQL.

---

## Priority 2 — Add an index on `Contract` if this table grows

**Problem:** Both queries in this analysis (`churn_rate_by_contract`, `revenue_at_risk_by_contract`) GROUP BY `Contract` on an unindexed column, forcing `USE TEMP B-TREE FOR GROUP BY`.

**Root cause:** No index exists on `customers_raw(Contract)` — reasonable for a 7K-row one-off analytical extract, not for a queried-often production table.

**Recommendation:**

```sql
CREATE INDEX idx_customers_raw_contract ON customers_raw(Contract);
```

**Expected impact:** Not benchmarked — at 7,043 rows the temp B-tree materialization is sub-millisecond and not worth the write-side index-maintenance cost. This is documented as a forward-looking recommendation, not applied to `artifacts/telco.db`, consistent with the audit verdict below.

**Risk:** Low — standard covering index for a 3-valued low-cardinality column; trades a small amount of write/storage overhead for GROUP BY speed on read-heavy workloads.

---

## Priority 3 — None found

No further performance issues were identified; `sql_lint.py` found no style/syntax anti-patterns beyond the correlated-subquery pattern already addressed in Priority 1.

---

## Changes NOT Recommended

| Suggestion | Why skipped |
|---|---|
| Materializing `contract_churn` as a persistent table refreshed on a schedule | Out of scope — this is a static Kaggle snapshot with no refresh cadence; premature for a one-off Phase 2 analysis. |
| Adding indexes on `Churn` or `MonthlyCharges` | Neither is used in an equality/range filter that would benefit from an index at this scale; `Churn='No'`/`'Yes'` on a 2-valued column has poor selectivity and SQLite's query planner would likely ignore such an index anyway. |

---

## Benchmark Results (after fixes)

| Version | Runtime (avg of 200 runs) | Scans of customers_raw | Notes |
|---|---|---|---|
| Original | 4.29 ms | 3 | Baseline, correlated subquery duplicated |
| After Priority 1 fix (CTE) | 3.66 ms | 2 | Measured directly, `EXPLAIN QUERY PLAN` confirms fewer scan sub-plans; **results verified identical** |
| After Priority 2 (index, not applied) | Not measured | 2 | Left as a scaling recommendation; no measurable benefit at current row count |
