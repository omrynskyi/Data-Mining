# Schema Mapping Document

**Project:** Telco churn — Phase 2 Data Understanding, raw extract to analytics-ready model
**Source system:** `data/Telco-Customer-Churn.csv` (raw Kaggle extract, as pandas reads it)
**Target system:** analytics-ready in-memory DataFrame consumed by Phase 3 (data-cleaning, feature-engineering) and Phase 4 (modeling)
**Analyst:** phase2-data-agent
**Date:** 2026-09-02
**Version:** 1.0

---

## Overview

**Purpose of mapping:** Document exactly how every raw column is cast/recoded before it reaches
modeling, so the transformation logic is auditable rather than buried in ad hoc script code.
**Total source columns:** 21
**Total target columns:** 21
**Direct matches (no cast needed):** 2 (`customerID`, `MonthlyCharges`)
**Requiring transformation:** 19
**Target columns with no source:** 0

`scripts/schema_compare.py` was run against `artifacts/schema_mapping/source_schema.csv` (raw
pandas dtypes) vs. `artifacts/schema_mapping/target_schema.csv` (proposed analytics dtypes) and
confirms these counts exactly (see `artifacts/schema_mapping/schema_compare_output.md`): 2 direct
matches, 19 type mismatches requiring a CAST, 0 unmapped columns either direction.

---

## Column mapping

See `artifacts/schema_mapping_raw_to_analytics.csv` for the full machine-readable version. Summary:

| Source column | Source type | Target column | Target type | Transformation | Notes |
|---|---|---|---|---|---|
| customerID | object | customer_id | object | Direct | unique key, 0 duplicates |
| gender | object | gender | category | `.astype('category')` | 2 levels |
| SeniorCitizen | int64 | senior_citizen | int8 | `.astype('int8')` | already 0/1 |
| Partner | object | partner | int8 | `(=='Yes').astype('int8')` | Yes/No -> 1/0 |
| Dependents | object | dependents | int8 | `(=='Yes').astype('int8')` | Yes/No -> 1/0 |
| tenure | int64 | tenure_months | int16 | `.astype('int16')` | 0-72 range |
| PhoneService | object | phone_service | int8 | `(=='Yes').astype('int8')` | Yes/No -> 1/0 |
| MultipleLines | object | multiple_lines | category | `.astype('category')` | kept 3-valued, see below |
| InternetService | object | internet_service | category | `.astype('category')` | 3 levels |
| OnlineSecurity...StreamingMovies (6 cols) | object | snake_case equiv. | category | `.astype('category')` | kept 3-valued, see below |
| Contract | object | contract | category | `.astype('category')` | 3 levels |
| PaperlessBilling | object | paperless_billing | int8 | `(=='Yes').astype('int8')` | Yes/No -> 1/0 |
| PaymentMethod | object | payment_method | category | `.astype('category')` | 4 levels |
| MonthlyCharges | float64 | monthly_charges | float64 | Direct | already correct type |
| TotalCharges | object | total_charges | float64 | `pd.to_numeric(str.strip(), errors='coerce')` | 11 blanks -> NaN, all at tenure==0 |
| Churn | object | churn | int8 | `(=='Yes').astype('int8')` | target label, Yes/No -> 1/0 |

**Design decision worth flagging:** `MultipleLines` and the 6 internet add-on columns are kept as
3-valued categoricals (`Yes` / `No` / `'No phone service'` or `'No internet service'`) rather than
collapsed to binary, because the "not applicable" sentinel is itself informative — it's perfectly
redundant with `PhoneService`/`InternetService` (verified 0 inconsistencies across all 7,043 rows
in `data_quality_scorecard.md`), but a tree-based model can still exploit it as a cheap
interaction-like signal without extra feature engineering. A linear model would need this
one-hot-encoded regardless, at which point the redundancy is harmless.

---

## Unmapped target columns (need derivation or default)

None. Every target column derives from exactly one source column (no cross-column derivations
needed at this mapping stage — `TotalCharges ≈ tenure × MonthlyCharges` is investigated as a
potential *feature engineering* derivation, not a raw-to-analytics mapping, in
`exploratory-data-analysis.md`'s leakage check).

## Unmapped source columns

None. All 21 raw columns map to exactly one target column.

---

## Type mismatch summary

| Column | Source type | Target type | Required CAST | Risk |
|---|---|---|---|---|
| TotalCharges | object | float64 | `pd.to_numeric(df['TotalCharges'].str.strip(), errors='coerce')` | **Medium** — naive `.astype(float)` without `.str.strip()` + `errors='coerce'` raises `ValueError` on the 11 blank strings; must use the coerce form and then explicitly decide how to handle the resulting NaNs downstream (impute 0, not drop rows) |
| SeniorCitizen | int64 | int8 | `.astype('int8')` | Low — values are 0/1 only, no truncation risk |
| tenure | int64 | int16 | `.astype('int16')` | Low — max observed value is 72, int16 range is ±32,767 |
| 8x Yes/No object columns | object | int8 | `(col=='Yes').astype('int8')` | Low — verified exhaustive 2-value domain for each (data-quality-audit `value_range_validator` PASS) |
| 8x categorical object columns | object | category | `.astype('category')` | Low — standard pandas-patterns downcast (see `pandas-patterns.md` for the measured memory reduction) |

---

## Validation rules

| Target column | Rule | Test query |
|---|---|---|
| customer_id | NOT NULL, UNIQUE | `SELECT COUNT(*) - COUNT(DISTINCT customerID) FROM customers_raw` — verified 0 (`artifacts/telco.db`) |
| total_charges | NULL only where tenure_months == 0 | `SELECT COUNT(*) FROM customers WHERE TotalCharges IS NULL AND tenure != 0` — verified 0 (`data_quality_scorecard.md`) |
| churn | value in {0, 1} after cast | `SELECT DISTINCT Churn FROM customers_raw` — verified {'Yes','No'} pre-cast, 0 other values |
| contract | value in {'Month-to-month','One year','Two year'} | verified via `value_range_validator.py --rules '{"Contract": {"allowed": [...]}}, PASS |

---

## Sign-off

| Role | Name | Date | Status |
|---|---|---|---|
| Source data owner | Kaggle dataset (blastchar/telco-customer-churn), no live owner | — | N/A — static snapshot |
| Target schema owner | phase2-data-agent | 2026-09-02 | Proposed |
| Engineering lead | (pending Phase 3 data-cleaning / feature-engineering handoff) | | Open |
| Analytics reviewer | (pending) | | Open |

---

*Template: schema_mapping_template.md (schema-mapper-mapping skill). Generated with
`scripts/schema_compare.py` — invoked by importing the module directly rather than via CLI, because
the script's `if __name__ == "__main__":` block never calls its own `main()` and instead always
prints a hardcoded orders/customers demo regardless of `--source`/`--target` args (same bug pattern
found independently in `sql_explainer.py`, see `sql-to-business-logic.md`).*
