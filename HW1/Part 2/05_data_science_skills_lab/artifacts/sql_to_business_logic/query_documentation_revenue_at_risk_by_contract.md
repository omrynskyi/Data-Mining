# Query Documentation

**Query name:** revenue_at_risk_by_contract
**Owner:** Retention Analytics (phase2-data-agent)
**Date:** 2026-09-02
**Location:** `artifacts/sql/revenue_at_risk_by_contract.sql`, run against `artifacts/telco.db`

---

## Business purpose

Of the recurring revenue currently on the books (active customers only), how much is exposed to churn each month if each contract type continues churning at its historical rate?

**Used by:** Retention team prioritization (which contract segment to intervene on first), finance revenue-at-risk forecasting
**Audience:** Retention managers, finance/FP&A

---

## Plain-language explanation

### What is being calculated (SELECT)

- `Contract` — contract type, from the outer query's `c1` alias
- `n_active_customers` — count of currently-active (`Churn = 'No'`) customers on that contract
- `active_mrr` — sum of `MonthlyCharges` across those active customers (the recurring revenue currently on the books for that segment)
- `historical_churn_rate` — a correlated scalar subquery: for that same contract type, `Yes`-churn count / total count across **all** customers (active + churned) — i.e., the empirical churn rate reused from `churn_rate_by_contract`
- `expected_monthly_revenue_at_risk` — `active_mrr × historical_churn_rate`: the modeled dollar amount of currently-active MRR expected to be lost per month if that segment's historical churn rate holds going forward

### Data source (FROM)

- Start with: `customers c1` (outer), filtered to active customers only.
- Two **correlated scalar subqueries** re-query `customers c2` for each outer row's contract type, to compute that contract type's historical churn rate. This is not a JOIN — each subquery executes once per outer group's contract value (only 3 distinct values here, so cheap; see `query-validation.md` for the performance note this pattern deserves at larger scale).

### Filters applied (WHERE)

- Outer query: `c1.Churn = 'No'` — only active customers contribute to `active_mrr` (revenue not yet lost).
- The churn-rate subqueries have no `WHERE` beyond the correlation (`c2.Contract = c1.Contract`) — deliberately: the churn rate is computed over the **full historical population** (active + churned) for that contract, not just active customers, because it's meant to represent the empirical probability of churn for a customer on that contract type.

### Grouping (GROUP BY)

- One row per `Contract` (again 3 groups), aggregating only active customers.

### Sorting (ORDER BY)

- Highest expected revenue at risk first.

---

## SQL

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

## Actual result (real run against artifacts/telco.db)

| Contract | n_active_customers | active_mrr | historical_churn_rate | expected_monthly_revenue_at_risk |
|---|---|---|---|---|
| Month-to-month | 2220 | $136,447.05 | 0.4271 | $58,276.09 |
| One year | 1307 | $81,698.15 | 0.1127 | $9,206.99 |
| Two year | 1647 | $98,840.55 | 0.0283 | $2,799.02 |

**Total active MRR:** $316,985.75. **Total expected monthly revenue at risk:** $70,282.10 (22.2% of active MRR) — driven overwhelmingly by the Month-to-month segment (83% of the total at-risk dollars despite being 42% of active accounts).

---

## Key assumptions

| Assumption | Confidence | Impact if wrong |
|---|---|---|
| Applying a *historical* (cross-sectional, cumulative) churn rate as a forward-looking monthly probability | Medium — this is a reasonable first-pass proxy for Phase 2 data understanding, not a calibrated survival/hazard model | Medium — actual monthly churn hazard differs from a cumulative rate; Phase 4 modeling should replace this with a proper time-to-churn or per-period hazard estimate |
| `MonthlyCharges` for a currently-active customer approximates the revenue that would be lost if they churn next month | High | Low |
| The three contract-type churn rates are stable, not currently trending | Low — not tested here (no timestamp column exists to test a trend) | Medium |

---

## Validation questions

- [x] Are filter conditions correct for the intended population? — yes: MRR is scoped to active customers (`c1.Churn='No'`), while the churn-rate denominator intentionally spans the full population — this asymmetry is correct for the intent but is exactly the kind of thing that needs to be called out to a reader, which this doc does above.
- [x] Does the GROUP BY grain match what one row should represent? — yes, one row per contract type.
- [x] Are NULL values handled explicitly in aggregations? — `MonthlyCharges` has zero nulls (data-quality-audit); `Churn` has zero nulls. No null-handling risk here (unlike a query that used `TotalCharges`, which has 11 nulls).
- [x] Has the result been cross-checked against another source? — yes: `historical_churn_rate` for each contract in this query matches `churn_rate_pct/100` from `churn_rate_by_contract` exactly (0.4271 / 0.1127 / 0.0283), confirming the correlated subquery computes the same thing as the standalone query.

---

## Change log

| Date | Author | Change |
|---|---|---|
| 2026-09-02 | phase2-data-agent | Initial version, run against `artifacts/telco.db` |

---

*Template: query_documentation_template.md (sql-to-business-logic skill)*

**Note on tooling — automated parser limitation found:** `scripts/sql_explainer.py`'s regex-based SELECT/WHERE splitter (`re.split(r",(?![^()]*\))", ...)`) assumes commas are only nested one level deep in parentheses. This query's `ROUND(..., (SELECT ... FROM ... WHERE ...), 4)` nests a `SELECT` with its own commas inside an outer `ROUND(...)`, which breaks the splitter — the raw auto-generated output (`artifacts/sql_to_business_logic/explain_revenue_at_risk_by_contract.md`) mis-segments the SELECT list and WHERE clause. Also worth flagging separately: the script's own `if __name__ == "__main__":` block never calls its `main()` function — it always prints a hardcoded demo query regardless of `--input`/`--sql` args, so the script currently cannot be invoked from the CLI as documented; both queries in this doc were run by importing `explain_sql()` directly from the module as a workaround. This translation document is the human-corrected version produced by manually walking the query structure per the skill's Process steps 2-5.
