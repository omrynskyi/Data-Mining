---
skill: query-validation
pack: nimrodfisher/data-analytics-skills
crisp_dm_phase: 2 - Data Understanding
artifacts:
  - artifacts/sql/churn_rate_by_contract.sql
  - artifacts/sql/revenue_at_risk_by_contract.sql
  - artifacts/sql/revenue_at_risk_by_contract_cte_rewrite.sql
  - artifacts/sql/churn_rate_by_contract_explain_plan.csv
  - artifacts/sql/revenue_at_risk_by_contract_explain_plan.csv
  - artifacts/query_validation/query_review_churn_rate_by_contract.md
  - artifacts/query_validation/query_review_revenue_at_risk_by_contract.md
  - artifacts/query_validation/optimization_recommendations_revenue_at_risk.md
  - artifacts/query_validation/lint_churn_rate.txt
  - artifacts/query_validation/lint_revenue_at_risk.txt
  - artifacts/query_validation/cardinality.txt
---

## What the skill prescribes

Review a SQL query for correctness, performance, and style before it reaches production: lint
with `sql_lint.py` (sqlglot-based), check anti-patterns, parse an EXPLAIN plan if available,
estimate join cardinality/fan-out risk, check engine-specific behavior, and produce a filled
review template plus ranked optimization recommendations.

## Applied to Telco churn

Two real queries were written, run, and reviewed against a real SQLite database
(`artifacts/telco.db`, built by `src/p2_sql_setup.py` from the raw CSV):

- `churn_rate_by_contract.sql` — churn rate and volume by contract type
- `revenue_at_risk_by_contract.sql` — active MRR by contract, weighted by that contract's
  historical churn rate, i.e. modeled monthly revenue expected to be lost

**Real EXPLAIN QUERY PLAN** was pulled from SQLite for both (not simulated) and reviewed
manually — `scripts/explain_plan_parser.py` only supports Postgres `EXPLAIN ANALYZE` text and
Snowflake JSON profiles, not SQLite's plan format, a genuine coverage gap documented rather than
worked around silently.

**Finding on `revenue_at_risk_by_contract`:** the EXPLAIN plan showed **two separate full-table
scans** (`SCAN customers_raw` nested under `CORRELATED SCALAR SUBQUERY 1` and `...2`) because the
churn-rate subquery was written twice (once for `historical_churn_rate`, once inline for
`expected_monthly_revenue_at_risk`). Rewrote as a CTE (`artifacts/sql/revenue_at_risk_by_contract_cte_rewrite.sql`),
**verified the rewrite produces byte-identical results** (`df_orig.equals(df_cte) == True`), and
measured a real speedup: 4.29ms -> 3.66ms average over 200 runs (1.17x) at this table's 7,043-row
scale, with the underlying scan count confirmed reduced from 3 to 2 via a second real EXPLAIN
QUERY PLAN. The gain is modest at this size but the fix is about read-pattern scalability, not
current latency — documented explicitly in `optimization_recommendations_revenue_at_risk.md`.

**Bug found in the skill's tooling:** `sql_lint.py --dialect ansi` (the script's own default)
raises `ValueError: Unknown dialect 'ansi'` — sqlglot's generic dialect is selected with
`dialect=""`, not the literal string `"ansi"`. Worked around by linting under `--dialect postgres`
(the closest standard-SQL dialect to this query's syntax). Both queries passed lint clean
(`churn_rate_by_contract`: `[OK] No issues found`; `revenue_at_risk_by_contract`: one WARN for
"no WHERE/LIMIT — full table scan likely," expected and accepted for a 3-group aggregate query).

`scripts/cardinality_estimator.py` was run on the CTE rewrite's join shape
(`customers`(7,043) join `contract_dim`(3), many-to-one) — confirms **LOW fan-out risk**,
estimated output ~7,043 rows, matching the left table exactly.

**Verdict:** both queries approved for production. `churn_rate_by_contract` unconditionally.
`revenue_at_risk_by_contract` with the condition that the CTE rewrite replace the duplicated
correlated subquery before this query is promoted to a shared/scheduled query library.

## Outputs produced

- `artifacts/sql/*.sql` — the two production queries plus the verified CTE rewrite
- `artifacts/sql/*_explain_plan.csv` — real `EXPLAIN QUERY PLAN` output for both queries
- `artifacts/query_validation/query_review_*.md` — filled `query_review_template.md` for each
  query (correctness / performance / style / anti-patterns / summary)
- `artifacts/query_validation/optimization_recommendations_revenue_at_risk.md` — the CTE fix
  with measured before/after benchmark and correctness verification
- `artifacts/query_validation/lint_*.txt`, `cardinality.txt` — real script output
