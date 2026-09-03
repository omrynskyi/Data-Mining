# QA Sign-off — Telco Churn Skills Lab

**Reviewer**: Claude (this session) · **Intended audience**: SJSU Data Mining HW1 grader / lab
readers · **Scope reviewed**: all 48 skill demonstrations, CRISP-DM phases 1-6.

## Automated checks
`qa_runner.py` against `artifacts/mlflow_runs_comparison.csv`: 4 checks, 0 FAIL, 1 WARN
(non-standard MLflow dotted column names — reviewed, not actionable).

`src/verify_claims.py` (26 independent checks against the raw CSV, no lab-code imports):
**26/26 PASS.**

## Issues found
5 real issues found and resolved — see `analysis-qa-checklist.md` for the full table. None
were data-correctness failures in the final numbers; all were either upstream skill-pack bugs
(documented, worked around) or a genuine hand-off contract error caught and fixed before it
reached the serving layer.

## Delivery decision
**APPROVED for delivery**, with the stated limitations (single cross-sectional snapshot,
observational Contract-churn relationship, LTV conflict resolved and documented) carried
forward into the executive summary rather than hidden.
