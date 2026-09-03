# Query Review: revenue_at_risk_by_contract

**Reviewer:** phase2-data-agent
**Date:** 2026-09-02
**Engine:** SQLite (`artifacts/telco.db`)
**Query location:** `artifacts/sql/revenue_at_risk_by_contract.sql`

---

## Query

```sql
SELECT
    c1.Contract,
    COUNT(*) AS n_active_customers,
    ROUND(SUM(c1.MonthlyCharges), 2) AS active_mrr,
    ROUND(
        (SELECT 1.0 * SUM(CASE WHEN c2.Churn = 'Yes' THEN 1 ELSE 0 END) / COUNT(*)
         FROM customers c2 WHERE c2.Contract = c1.Contract),
        4
    ) AS historical_churn_rate,
    ROUND(
        SUM(c1.MonthlyCharges) *
        (SELECT 1.0 * SUM(CASE WHEN c2.Churn = 'Yes' THEN 1 ELSE 0 END) / COUNT(*)
         FROM customers c2 WHERE c2.Contract = c1.Contract),
        2
    ) AS expected_monthly_revenue_at_risk
FROM customers c1
WHERE c1.Churn = 'No'
GROUP BY c1.Contract
ORDER BY expected_monthly_revenue_at_risk DESC;
```

---

## Correctness

| # | Finding | Severity | Location | Recommendation |
|---|---|---|---|---|
| 1 | The churn-rate subquery denominator (`COUNT(*) FROM customers c2 WHERE c2.Contract = c1.Contract`) deliberately spans **all** customers on that contract (active + churned), while the outer query's `active_mrr` deliberately spans only active customers. This asymmetry is intentional and correct for the metric's definition, but is easy to misread as a bug on a quick skim. | MED | subquery vs. outer WHERE | Documented explicitly in `sql-to-business-logic.md`'s translation; recommend a SQL comment in the source (`-- churn rate uses ALL customers on this contract, not just active ones`) before this query is promoted to a shared query library. |
| 2 | The same churn-rate subquery is duplicated verbatim (once for `historical_churn_rate`, once inline for `expected_monthly_revenue_at_risk`) rather than computed once and reused. | LOW | 2 occurrences | Rewrite with a CTE (see Performance Priority 1 below) — fixes both the duplication and a performance concern together. |

**Overall correctness verdict:** PASS — verified `historical_churn_rate` values (0.4271 / 0.1127 / 0.0283) exactly match `churn_rate_pct/100` from the independently-written `churn_rate_by_contract` query, confirming both computations agree.

---

## Performance

| # | Finding | Severity | Estimated impact | Recommendation |
|---|---|---|---|---|
| 1 | **Correlated scalar subquery evaluated per outer group, twice.** EXPLAIN QUERY PLAN shows two full `SCAN customers_raw` passes nested under `CORRELATED SCALAR SUBQUERY 1` and `CORRELATED SCALAR SUBQUERY 2` — i.e. the entire table is rescanned once per outer contract group *per subquery occurrence*. At 3 contract groups × 2 subqueries × 7,043-row scan, that's ~42K row-reads instead of the ~7K a single pre-aggregated pass would need. | MED | ~6x more row-reads than necessary; still sub-second at this table size (7K rows), but would not scale to a multi-million-row production table. | Rewrite using a CTE that computes churn rate per contract once: `WITH contract_churn AS (SELECT Contract, 1.0*SUM(CASE WHEN Churn='Yes' THEN 1 ELSE 0 END)/COUNT(*) AS rate FROM customers GROUP BY Contract) SELECT c1.Contract, COUNT(*), SUM(c1.MonthlyCharges), cc.rate, SUM(c1.MonthlyCharges)*cc.rate FROM customers c1 JOIN contract_churn cc ON cc.Contract = c1.Contract WHERE c1.Churn='No' GROUP BY c1.Contract, cc.rate;` — single scan for the churn-rate CTE, one JOIN (3 rows on the right side, no fan-out risk per `cardinality_estimator.py`), no duplication. |

**EXPLAIN / profile reviewed?** Yes — real `EXPLAIN QUERY PLAN` output (`artifacts/sql/revenue_at_risk_by_contract_explain_plan.csv`):

```
 id  parent  notused                       detail
  7       0      216           SCAN customers_raw
 11       0        0 USE TEMP B-TREE FOR GROUP BY
 49       0        0 CORRELATED SCALAR SUBQUERY 1
 54      49      216           SCAN customers_raw
 75       0        0 CORRELATED SCALAR SUBQUERY 2
 80      75      216           SCAN customers_raw
106       0        0 USE TEMP B-TREE FOR ORDER BY
```
This confirms the duplicated-subquery finding above directly: two separate `SCAN customers_raw` sub-plans, one per subquery occurrence, each themselves nested under the outer scan/group-by.

**Estimated scan size:** ~3 × 7,043-row rescans (correlated subquery per group) ≈ 21K logical row reads for the subqueries alone, on top of the outer 7K-row scan. Trivial in absolute terms at this table size (whole query completes in milliseconds), but flagged because the *pattern* (correlated subquery duplicated across output columns) doesn't scale and should be fixed before this query is reused against a larger production table.

Notes:
- `scripts/cardinality_estimator.py` was run on the CTE-rewrite's join shape (`customers` ⋈ `contract_dim`(3 rows) on `Contract`, many-to-one) and confirms LOW fan-out risk: estimated output ≈ 7,043 rows, matching the left table size exactly (see `artifacts/query_validation/cardinality.txt`).

---

## Style & Maintainability

| # | Finding | Severity | Recommendation |
|---|---|---|---|
| 1 | Two nearly-identical correlated subqueries differ only in whether the result multiplies `SUM(c1.MonthlyCharges)`. | MED | Same CTE rewrite as Performance #1 removes this duplication. |
| 2 | No SQL comment documents why the churn-rate subquery intentionally uses a different population (all customers) than the outer query (active only). | LOW | Add inline comment; see Correctness #1. |

---

## Anti-Patterns Found

*(Cross-reference `references/sql_anti_patterns.md`)*

- [ ] Implicit type conversion
- [ ] NULL comparison error
- [ ] Fan-out join
- [ ] NOT IN with nullable subquery
- [x] **Correlated subquery in SELECT** — present twice (see Performance #1); low-severity at current data volume but a real anti-pattern to fix before scaling.
- [ ] Function on indexed column in WHERE
- [ ] DISTINCT masking a join problem

`scripts/sql_lint.py --dialect postgres` output: `[OK] No issues found` — the linter's syntax/style checks don't catch the duplicated-correlated-subquery pattern (it's a semantic/performance issue, not a syntax one), which is why the manual EXPLAIN-plan-driven review above was still necessary per the skill's step 3.

---

## Summary

**Approved for production?** Yes, with conditions

Conditions (if any):
1. Before this query is added to a shared/scheduled query library (vs. this one-off Phase 2 analysis), rewrite with the CTE form in Performance #1 to remove the duplicated correlated subquery.
2. Add the inline comment from Correctness #1 documenting the intentional active-vs-all population asymmetry between `active_mrr` and `historical_churn_rate`.

**Estimated performance after fixes:** No measurable change at 7,043 rows (already sub-second); the CTE rewrite is about *robustness at scale*, not fixing a current bottleneck — see `optimization_recommendations.md` for the row-read reduction math (~42K → ~7K logical reads, ~6x).
