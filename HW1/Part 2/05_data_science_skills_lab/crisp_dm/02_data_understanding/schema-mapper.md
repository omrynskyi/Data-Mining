---
skill: schema-mapper
pack: nimrodfisher/data-analytics-skills
crisp_dm_phase: 2 - Data Understanding
artifacts:
  - artifacts/schema/telco_erd.mmd
  - artifacts/schema/data_dictionary.csv
  - artifacts/schema/schema_quick_reference.md
---

## What the skill prescribes

Discover, document, and visualize a database schema: tables, columns, relationships, join
paths, an ERD (Mermaid), a data dictionary, and a quick-reference join guide. The skill's
default workflow assumes a live database connection or an `INFORMATION_SCHEMA` export.

## Applied to Telco churn

**No source database exists** — `data/Telco-Customer-Churn.csv` is a single flat, denormalized
mart (7,043 rows x 21 columns, one row per customer). Per the skill's "Handling Missing Context"
guidance ("If you have dbt project instead of database... use whatever you have access to"),
this was treated as a reverse-engineering exercise: infer a plausible normalized OLTP schema
this extract *could* have been built from, and say explicitly that it is inferred, not given.

**5-table normalized model** (`customer`, `subscription`, `service_addon`, `billing_account`,
`payment_method`), with every candidate key and cardinality claim verified against the real
data rather than assumed:

- `customer.customer_id` = `customerID` — verified unique across all 7,043 rows (0 duplicates,
  cross-checked against `data-quality-audit.md`'s `duplicate_finder.py` run)
- `subscription` is 1:1 with `customer` **in this snapshot** (modeled 1:* to allow for
  re-subscription history a real OLTP system would have)
- `service_addon` unpivots the 7 wide Yes/No/sentinel columns (`MultipleLines` +
  `OnlineSecurity`/`OnlineBackup`/`DeviceProtection`/`TechSupport`/`StreamingTV`/`StreamingMovies`)
  into an EAV-style table, one row per *applicable* addon. Row count is derived exactly from
  the data, not guessed: 7,043 x 7 possible slots, minus 682 `PhoneService=='No'` rows (no
  `MultipleLines` row emitted) minus 1,526 `InternetService=='No'` rows x 6 internet-addon
  columns = **39,463** applicable addon rows — verified by direct computation.
- `payment_method` is a 4-row lookup dimension — verified exactly 4 distinct `PaymentMethod`
  values in the source (`Electronic check`, `Mailed check`, `Bank transfer (automatic)`,
  `Credit card (automatic)`).
- `billing_account` is 1:1 with `subscription`, referencing `payment_method` many:1.

The ERD (`artifacts/schema/telco_erd.mmd`) documents these tables and relationships in Mermaid
`erDiagram` syntax. `schema_quick_reference.md` includes real join-path SQL for every edge and
shows how joining + pivoting the 5 tables back together reconstructs the flat CSV exactly.

## Outputs produced

- `artifacts/schema/telco_erd.mmd` — Mermaid ERD, 5 tables, keys and cardinalities marked
- `artifacts/schema/data_dictionary.csv` — full column-level catalog (24 columns across 5
  tables), each row noting which source CSV column(s) it derives from
- `artifacts/schema/schema_quick_reference.md` — join-path SQL, row-count derivation for the
  unpivoted `service_addon` table, and the explicit "this is inferred, not given" framing
