---
skill: data-catalog-entry
pack: nimrodfisher/data-analytics-skills
crisp_dm_phase: 1 - Business Understanding
artifacts: [src/p1_data_catalog.py, artifacts/data_catalog_telco.json, artifacts/data_catalog_telco.md]
---

# Data Catalog Entry — Telco Customer Churn

## What the skill prescribes

- Extract technical metadata — schema, column names, types, keys, row count — via `scripts/catalog_extractor.py` (SQLAlchemy inspection for DB tables).
- Collect business context from the data owner: business purpose, owning team, criticality, known use cases.
- Write one-sentence plain-language descriptions per column, with example values and business rules.
- Assess data quality: completeness, freshness, duplicate rate, known issues.
- Document lineage: upstream sources, downstream consumers.
- Add governance details (access level, sensitivity, compliance tags) and publish via `assets/catalog_entry_template.md`.

## Applied to Telco churn

### Technical metadata extraction

`.claude/skills/data-catalog-entry/scripts/catalog_extractor.py` targets a live SQL database via `sqlalchemy.inspect()` — this project's source is a flat CSV, not a database connection, so `src/p1_data_catalog.py` performs the equivalent technical-metadata-extraction step (same fields: dtype, nullability, cardinality, example values, primary-key check) directly against `data/Telco-Customer-Churn.csv` with pandas, and renders through the same Markdown structure as `assets/catalog_entry_template.md` / the skill's own `render_markdown()`.

Executed: `python3 src/p1_data_catalog.py` -> profiled all 21 columns, wrote `artifacts/data_catalog_telco.{json,md}`.

### Business context (data-owner interview)

**[simulated stakeholder input]** — same VP of Customer Retention as `stakeholder-requirements-gathering.md`, plus a simulated Technical Owner (Analytics team):

> **Business purpose:** "This is our single source of truth for who our residential customers are, what they've bought, and whether they left. It backs every retention analysis we run."
>
> **Criticality:** "Critical — it's the only churn ground-truth we have."
>
> **Known use cases:** "Ad hoc churn cuts by contract type today; going forward, this scoring project."

### Column-by-column dictionary (real, computed — full table in `artifacts/data_catalog_telco.md`)

All 21 columns profiled with **dtype, null count/%, cardinality, example values, and business definition** computed directly from the file. Representative excerpt:

| Column | Dtype | Null % | Cardinality | Business definition |
|---|---|---|---|---|
| customerID | object | 0.0% | 7,043 (PK) | Unique customer identifier assigned at account creation. |
| tenure | int64 | 0.0% | 73 | Months the customer has been with the company (business framing: months since acquisition). |
| Contract | object | 0.0% | 3 | Contract term: Month-to-month / One year / Two year. Primary churn-risk driver dimension. |
| MonthlyCharges | float64 | 0.0% | 1,585 | Current recurring monthly charge (USD) — treated as MRR contribution. |
| TotalCharges | object | 0.156% (11 rows) | 6,531 | Cumulative billed to date (USD); ships as object due to blank-string placeholders for `tenure==0` customers — must be coerced with `pd.to_numeric(errors='coerce')`. |
| Churn | object | 0.0% | 2 | Target label: voluntary churn flag (Yes/No). |

(Full 21-row table with every column's dtype, null%, cardinality, 5 example values, and business definition: `artifacts/data_catalog_telco.md` / `.json`.)

### Data quality assessment (skill step 4)

- **Completeness:** 100% for 20/21 columns; `TotalCharges` at 99.844% (11 nulls after numeric coercion) — all 11 correspond to `tenure == 0` (brand-new, not-yet-billed customers), so this is expected structure, not a defect. Cross-checked against `data/processed/dataset_meta.json` (`totalcharges_nulls_after_coercion: 11`) — consistent.
- **Freshness:** static one-time snapshot (Kaggle download for this lab) — no refresh schedule; documented as such rather than left blank (per `catalog_standards.md`: "a blank known-issues field is a red flag").
- **Duplicate rate:** 0 duplicate `customerID`s (verified against `dataset_meta.json`).
- **Known issues:** `TotalCharges` dtype/coercion requirement (above) is the only known issue.

### Lineage

- **Upstream:** Kaggle `blastchar/telco-customer-churn` export (static download for this lab); in a real production system this would be the billing system + CRM.
- **Downstream:** this project's CRISP-DM churn-prediction pipeline (Phases 2-6) and the retention team's ranked risk list (planned Phase 6 deliverable).

### Governance

- **Access level:** internal.
- **Sensitivity:** PII (pseudonymous `customerID`, demographic fields `gender`/`SeniorCitizen`) + financial (`MonthlyCharges`, `TotalCharges`).
- **Compliance tags:** none applicable to this public Kaggle sample; would carry GDPR/CCPA-equivalent tags in a real production telecom system with real customer identities.
- **Access instructions:** public dataset for this lab — no request process needed here.

## Outputs produced

- `src/p1_data_catalog.py` — executed successfully; extracts and profiles all 21 columns directly from the CSV.
- `artifacts/data_catalog_telco.json` — full machine-readable catalog (all 21 columns + table-level metadata).
- `artifacts/data_catalog_telco.md` — full catalog entry rendered in `catalog_entry_template.md`'s structure (Overview / Ownership / Schema / Relationships / Data Quality / Lineage / Access & Governance / Sample query).
