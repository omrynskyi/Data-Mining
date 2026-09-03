---
skill: data-quality-audit
pack: nimrodfisher/data-analytics-skills
crisp_dm_phase: 2 - Data Understanding
artifacts:
  - src/p2_data_quality_audit.py
  - artifacts/data_quality_scorecard.json
  - artifacts/data_quality_scorecard.md
  - artifacts/data_quality/quality_checks.csv
  - artifacts/data_quality/null_counter_output.txt
  - artifacts/data_quality/duplicate_finder_output.txt
  - artifacts/data_quality/value_range_validator_output.txt
---

## What the skill prescribes

A formal quality assessment against explicit business rules and a weighted scorecard: null
audit, duplicate detection, referential integrity, value-range validation, freshness, then
map findings to quality dimensions (Completeness, Accuracy, Consistency, Timeliness,
Uniqueness, Validity) with severity and a 0-10 score per dimension.

## Applied to Telco churn

Explicit business rules were defined and tested in code (`src/p2_data_quality_audit.py`),
running the skill's own `null_counter.py`, `duplicate_finder.py`, and `value_range_validator.py`
scripts plus custom cross-column consistency checks the skill's scripts don't cover natively:

- `tenure >= 0` and `<= 72` (observed max), `MonthlyCharges > 0`, `TotalCharges >= 0`
- `SeniorCitizen`, `gender`, `Churn`, `Contract`, `InternetService`, `PaymentMethod` each
  restricted to their documented value sets
- **TotalCharges is null only when tenure==0** (and vice versa) — both directions tested
- **PhoneService=='No' implies MultipleLines=='No phone service'** (and the converse)
- **InternetService=='No' implies all 6 add-on columns=='No internet service'** (and the converse),
  checked across all 6 columns individually
- **TotalCharges within 25% of tenure x MonthlyCharges** for >=99% of billed rows (an accuracy
  sanity check, not the precise leakage/redundancy measurement — that's in
  `exploratory-data-analysis.md`)
- `customerID` uniqueness (primary key)
- Referential integrity and freshness are explicitly marked **N/A** with a documented reason
  (single denormalized extract, no FK, no timestamp column) rather than silently skipped

**Environment note (found, not hidden):** the skill's own `null_counter.py` and
`duplicate_finder.py` use PEP 604 (`X | None`) type-hint syntax evaluated at function-definition
time, which raises `TypeError` under this machine's default Python 3.9.6. Fixed by running those
two scripts under a separately-provisioned Python 3.10 interpreter
(`pip install --break-system-packages pandas numpy` into `/Users/oleg/.local/bin/python3.10`)
rather than patching the read-only skill scripts.

**Result: 21 checks run, 19 PASS, 0 FAIL, 2 N/A.** Every dimension scores 10.0/10 except
Timeliness (N/A, excluded from the weighted average). **Overall score: 10.0/10 — PASS.**
The only near-miss during development was the 25%-band accuracy check, which failed under an
overly strict 0-tolerance version before being corrected to the realistic >=99%-of-rows
threshold — median deviation from `tenure*MonthlyCharges` is 1.97%, concentrated in low-tenure
customers with partial first/last-month billing, which is expected, not an error.

## Outputs produced

- `src/p2_data_quality_audit.py` — runs the checks, computes the weighted scorecard
- `artifacts/data_quality_scorecard.json` / `.md` — the scorecard (dimension scores, verdict, all
  21 checks with rows-affected and detail)
- `artifacts/data_quality/*.csv`, `*.txt` — raw script outputs from `null_counter.py`,
  `duplicate_finder.py`, `value_range_validator.py`
