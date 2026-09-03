# Query Review: churn_rate_by_contract

**Reviewer:** phase2-data-agent
**Date:** 2026-09-02
**Engine:** SQLite (`artifacts/telco.db`)
**Query location:** `artifacts/sql/churn_rate_by_contract.sql`

---

## Query

```sql
SELECT
    Contract,
    COUNT(*) AS n_customers,
    SUM(CASE WHEN Churn = 'Yes' THEN 1 ELSE 0 END) AS n_churned,
    ROUND(100.0 * SUM(CASE WHEN Churn = 'Yes' THEN 1 ELSE 0 END) / COUNT(*), 2) AS churn_rate_pct
FROM customers
GROUP BY Contract
ORDER BY churn_rate_pct DESC;
```

---

## Correctness

| # | Finding | Severity | Location | Recommendation |
|---|---|---|---|---|
| 1 | `COUNT(*)` denominator is correct here because `Contract` and `Churn` are both 100%-populated (verified in data-quality-audit) — no null-related undercount risk. | LOW | line 2 | None needed; would recommend `COUNT(Contract)` defensively if this table's completeness guarantee weren't already verified. |

**Overall correctness verdict:** PASS

Notes:
- Result was cross-checked: overall weighted churn rate implied (Σn_churned/Σn_customers = 1869/7043 = 26.54%) matches `dataset_meta.json`'s `churn_rate_overall: 0.26537` exactly — see `metric-reconciliation.md`.

---

## Performance

| # | Finding | Severity | Estimated impact | Recommendation |
|---|---|---|---|---|
| 1 | `SCAN customers_raw` (full table scan) — expected and fine at 7,043 rows / no WHERE clause; `Contract` is unindexed. | LOW | Negligible at this scale (single-digit ms) | Not worth an index at current volume. If this table grows into the millions of rows and this query runs frequently, add `CREATE INDEX idx_customers_contract ON customers_raw(Contract);` to let SQLite use a covering scan for the GROUP BY. |
| 2 | `USE TEMP B-TREE FOR GROUP BY` and a second one `FOR ORDER BY` — two temp B-tree materializations. | LOW | Negligible at 7,043 rows | Same index as above would let SQLite satisfy the GROUP BY via index order and avoid one temp B-tree; the ORDER BY is on a computed column (`churn_rate_pct`) so it cannot be index-avoided regardless. |

**EXPLAIN / profile reviewed?** Yes — real `EXPLAIN QUERY PLAN` output from SQLite (`artifacts/sql/churn_rate_by_contract_explain_plan.csv`):

```
 id  parent  notused                       detail
  7       0      216           SCAN customers_raw
  9       0        0 USE TEMP B-TREE FOR GROUP BY
 55       0        0 USE TEMP B-TREE FOR ORDER BY
```

**Estimated scan size:** 7,043 rows (full table) — trivial for SQLite; no partitioning/indexing action warranted at this data volume.

Notes:
- `scripts/explain_plan_parser.py` only supports Postgres `EXPLAIN ANALYZE` text and Snowflake Query Profile JSON — SQLite's `EXPLAIN QUERY PLAN` output format (id/parent/notused/detail rows) is not one of its supported inputs, so it was not run against this plan. The plan was reviewed manually per the pattern in `references/engine_specific_guide.md` instead. This is a genuine coverage gap in the skill's tooling for SQLite targets, noted here rather than silently worked around.

---

## Style & Maintainability

| # | Finding | Severity | Recommendation |
|---|---|---|---|
| 1 | Repeats the `CASE WHEN Churn = 'Yes' THEN 1 ELSE 0 END` expression's logic across `n_churned` and `churn_rate_pct` (recomputed, not reused). | LOW | Acceptable for a 2-column-derived query; if the codebase accumulates more churn queries, promote `Churn = 'Yes'` to a boolean/int column at the view level (`customers` view) to avoid repeating the CASE. |

---

## Anti-Patterns Found

*(Cross-reference `references/sql_anti_patterns.md`)*

- [ ] Implicit type conversion
- [ ] NULL comparison error
- [ ] Fan-out join
- [ ] NOT IN with nullable subquery
- [ ] Function on indexed column in WHERE
- [ ] Correlated subquery in SELECT
- [ ] DISTINCT masking a join problem
- [x] ~~None found~~ — confirmed by `scripts/sql_lint.py --dialect postgres`: `[OK] No issues found`

**Tooling note:** `sql_lint.py`'s `--dialect` default (`"ansi"`) is not a valid sqlglot dialect string — `sqlglot.parse(sql, dialect="ansi")` raises `ValueError: Unknown dialect 'ansi'`. This is a bug in the skill script (sqlglot's generic/ANSI dialect is selected with `dialect=""`, not `"ansi"`). Worked around by linting under `--dialect postgres`, the closest available standard-SQL dialect to SQLite for this query (no Postgres/SQLite-specific syntax is used).

---

## Summary

**Approved for production?** Yes

Conditions (if any): none — query is correct, cheap at current data volume, and already cross-validated against `dataset_meta.json`.

**Estimated performance after fixes:** No fix needed at 7,043 rows; documented the indexing path for if/when this table scales.
