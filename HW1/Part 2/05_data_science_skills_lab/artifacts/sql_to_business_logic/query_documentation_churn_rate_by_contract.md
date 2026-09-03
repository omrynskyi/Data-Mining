# Query Documentation

**Query name:** churn_rate_by_contract
**Owner:** Retention Analytics (phase2-data-agent)
**Date:** 2026-09-02
**Location:** `artifacts/sql/churn_rate_by_contract.sql`, run against `artifacts/telco.db`

---

## Business purpose

What is the churn rate for each contract type, and how many customers does that represent?

**Used by:** Retention team's monthly risk list, contract-mix strategy discussions
**Audience:** Retention managers, product/pricing team deciding whether to incentivize longer contracts

---

## Plain-language explanation

### What is being calculated (SELECT)

- `Contract` — the billing commitment type (Month-to-month / One year / Two year)
- `n_customers` — count of all customers (active and churned) on that contract type
- `n_churned` — count of those customers whose `Churn` flag is `'Yes'`
- `churn_rate_pct` — `n_churned / n_customers`, as a percentage, rounded to 2 decimals

### Data source (FROM)

- Start with: `customers` — a view over `customers_raw` that casts `TotalCharges` to numeric and nulls the 11 blank strings (that cast is irrelevant to this query, which doesn't touch `TotalCharges`, but the view is used uniformly across all Phase 2 SQL for consistency).

### Filters applied (WHERE)

- None — every customer in the extract is included (both currently active and already-churned).

### Grouping (GROUP BY)

- One row per `Contract` value (3 groups: Month-to-month, One year, Two year).

### Sorting (ORDER BY)

- Highest churn rate first, so the riskiest contract segment is on top.

---

## SQL

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

## Actual result (real run against artifacts/telco.db)

| Contract | n_customers | n_churned | churn_rate_pct |
|---|---|---|---|
| Month-to-month | 3875 | 1655 | 42.71 |
| One year | 1473 | 166 | 11.27 |
| Two year | 1695 | 48 | 2.83 |

---

## Key assumptions

| Assumption | Confidence | Impact if wrong |
|---|---|---|
| `Churn = 'Yes'`/`'No'` is a clean, exhaustive binary (no other values, no nulls) | High — verified in data-quality-audit (`Churn` value_range_validator PASS) | Low |
| Denominator includes churned customers (i.e. rate is historical/cumulative, not "active-customer" churn) | High, but worth stating explicitly to stakeholders — a reader could mistake this for a rate over *currently active* customers only | Medium — misreads the base population |

---

## Validation questions

- [x] Are filter conditions correct for the intended population? — no filter is applied on purpose; confirmed this is intended (cumulative churn rate, not point-in-time).
- [x] Does the GROUP BY grain match what one row should represent? — yes, one row per contract type.
- [x] Are NULL values handled explicitly in aggregations? — `Churn` has zero nulls (data-quality-audit), so the `CASE WHEN` is exhaustive; no silent NULL-drop risk.
- [x] Has the result been cross-checked against another source? — yes, see `metric-reconciliation.md`: the overall (unweighted) churn rate implied by this table (26.54%) reconciles exactly with `dataset_meta.json`'s `churn_rate_overall: 0.26537`.

---

## Change log

| Date | Author | Change |
|---|---|---|
| 2026-09-02 | phase2-data-agent | Initial version, run against `artifacts/telco.db` |

---

*Template: query_documentation_template.md (sql-to-business-logic skill)*

**Note on tooling:** `scripts/sql_explainer.py`'s automated first pass parsed this query's SELECT/GROUP BY/ORDER BY clauses correctly (see `artifacts/sql_to_business_logic/explain_churn_rate_by_contract.md`) — this simple, non-nested query is within the regex parser's capability. See `sql-to-business-logic.md` for where the automated parse broke down on the second, more complex query.
