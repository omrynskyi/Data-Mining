---
skill: schema-mapper-mapping
pack: nimrodfisher/data-analytics-skills (02-documentation-knowledge variant)
crisp_dm_phase: 2 - Data Understanding
artifacts:
  - artifacts/schema_mapping/source_schema.csv
  - artifacts/schema_mapping/target_schema.csv
  - artifacts/schema_mapping/schema_compare_output.md
  - artifacts/schema_mapping_raw_to_analytics.md
  - artifacts/schema_mapping_raw_to_analytics.csv
---

## What the skill prescribes

Document column-level mappings from a source schema to a target/analytics schema: collect
both schemas, map source->target columns (direct rename vs. derived/cast), document every
transformation rule explicitly, flag gaps in both directions, and produce a sign-off-ready
mapping document. Ships `scripts/schema_compare.py` to automate direct-name/type-mismatch
detection.

## Applied to Telco churn

Source = the raw CSV exactly as pandas reads it (21 columns, `object` dtype dominant, including
`TotalCharges` shipping as a **string** with 11 blank values). Target = the proposed
analytics-ready dtype scheme for Phase 3/4 (int8 for booleans, category for low-cardinality
strings, float64 for `TotalCharges` after coercion).

Both schemas were written out as real CSVs (`artifacts/schema_mapping/{source,target}_schema.csv`)
and run through the skill's own `scripts/schema_compare.py`, which found exactly **2 direct
matches** (`customerID`, `MonthlyCharges` — already correctly typed) and **19 type mismatches
requiring a CAST**, 0 columns dropped or added in either direction.

**Bug found in the skill's tooling:** `schema_compare.py`'s `if __name__ == "__main__":` block
defines `main()` (which parses `--source`/`--target`/`--output`) but never calls it — the script
always runs a hardcoded orders/customers demo instead, regardless of CLI args. This is the same
bug pattern independently found in `sql_explainer.py` (see `sql-to-business-logic.md`) and
`reconcile_metrics.py` (see `metric-reconciliation-tracing.md`) — three scripts across two
skill packs share this exact defect. Worked around by importing `load_schema`/`compare_schemas`/
`format_report` directly from the module rather than invoking the CLI.

Every one of the 19 casts is documented in `artifacts/schema_mapping_raw_to_analytics.csv` with
the exact pandas expression, e.g.:
- `TotalCharges: object -> float64` via `pd.to_numeric(df['TotalCharges'].str.strip(), errors='coerce')`
  — flagged **Medium risk** because a naive `.astype(float)` raises `ValueError` on the 11 blank
  strings; the resulting NaNs are meaningful (tenure==0, never billed) and must be imputed, not
  silently dropped
- `Churn: object -> int8` via `(df['Churn']=='Yes').astype('int8')` — this is the modeling target
- 6 service-addon columns deliberately **kept 3-valued** (`category`, not collapsed to binary) —
  a design decision documented and justified (the "not applicable" sentinel is fully redundant
  with `PhoneService`/`InternetService` but harmless and informative for tree models)

## Outputs produced

- `artifacts/schema_mapping/source_schema.csv`, `target_schema.csv` — the two schemas fed to
  `schema_compare.py`
- `artifacts/schema_mapping/schema_compare_output.md` — real script output (2 matches, 19
  mismatches)
- `artifacts/schema_mapping_raw_to_analytics.md` / `.csv` — full column-by-column mapping
  document with transformation rules, risk ratings, and validation rules (per the task's
  required deliverable path)
