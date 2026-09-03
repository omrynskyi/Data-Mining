---
skill: sql-to-business-logic
pack: nimrodfisher/data-analytics-skills
crisp_dm_phase: 2 - Data Understanding
artifacts:
  - artifacts/sql_to_business_logic/query_documentation_churn_rate_by_contract.md
  - artifacts/sql_to_business_logic/query_documentation_revenue_at_risk_by_contract.md
  - artifacts/sql_to_business_logic/explain_churn_rate_by_contract.md
  - artifacts/sql_to_business_logic/explain_revenue_at_risk_by_contract.md
---

## What the skill prescribes

Translate SQL into plain language for non-technical stakeholders: explain the FROM/JOIN
structure, WHERE filters as business rules, GROUP BY/aggregation grain, output-column meaning,
and flag issues with validation questions. Ships `scripts/sql_explainer.py` for an automated
first-pass structural parse.

## Applied to Telco churn

Ran the skill's own `sql_explainer.py` (via `explain_sql()`, see tooling note below) against
both real queries from `query-validation.md`, then completed the full human translation using
`assets/query_documentation_template.md` for each.

**`churn_rate_by_contract`** — automated parse worked correctly (simple query, no nested
subqueries): identified the 4 SELECT columns, the `customers` source, the `Contract` GROUP BY,
and the `churn_rate_pct DESC` sort. Human translation adds the business framing: this is a
**cumulative/historical** churn rate (denominator includes already-churned customers), not a
point-in-time active-customer rate — an important distinction called out explicitly so a reader
doesn't misread the base population. Cross-checked: implied overall rate (1,869/7,043=26.54%)
matches `dataset_meta.json`'s canonical value exactly.

**`revenue_at_risk_by_contract`** — the automated parser's regex-based comma-splitter
(`re.split(r",(?![^()]*\))", ...)`, which only handles one level of paren-nesting) **broke down**
on this query's nested `ROUND(..., (SELECT ... FROM ... WHERE ...), 4)` structure, mis-segmenting
the SELECT list and WHERE clause in the raw auto-generated output. This parser limitation is
documented explicitly rather than silently corrected, and the full human-written translation
replaces it: explains that `historical_churn_rate` deliberately uses the **full customer
population** (active + churned) per contract as its denominator, while `active_mrr` deliberately
uses **only active customers** — an intentional asymmetry that's easy to misread as a bug on a
skim, flagged as the key validation point for anyone reviewing this query.

**Bug found in the skill's tooling:** `sql_explainer.py`'s `if __name__ == "__main__":` block
never calls its own `main()` — running the script from the CLI with any `--input`/`--sql` args
always prints a hardcoded demo query instead (same defect pattern independently found in
`schema_compare.py` and `reconcile_metrics.py` — three scripts, two skill packs, one shared bug).
Worked around by importing `explain_sql()` from the module directly.

## Outputs produced

- `artifacts/sql_to_business_logic/query_documentation_*.md` — completed
  `query_documentation_template.md` for both queries: business purpose, plain-language
  SELECT/FROM/WHERE/GROUP BY/ORDER BY translation, real result tables, key assumptions with
  confidence ratings, and answered validation questions
- `artifacts/sql_to_business_logic/explain_*.md` — raw automated-parser output for both queries
  (kept as evidence of where the tool succeeded vs. broke down)
