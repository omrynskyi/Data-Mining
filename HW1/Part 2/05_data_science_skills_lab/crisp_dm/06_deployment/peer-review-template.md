---
skill: peer-review-template
pack: nimrodfisher/data-analytics-skills
crisp_dm_phase: 6 - Deployment
artifacts: [artifacts/peer_review_model_evaluation.md]
---

## What the skill prescribes

1. Agree scope with the author: logic check, statistical validity, code review, or
   presentation clarity.
2. Review analytical rigour: are question and method aligned, are assumptions valid, is the
   conclusion supported.
3. Review code/SQL: reproducibility, correctness, readability, performance.
4. Write categorized feedback: must-fix, should-fix, optional — specific, not vague.
5. Author responds per item: fixed / accepted-as-is-with-rationale / deferred.
6. Reviewer confirms must-fix items resolved and signs off.

## Applied to Telco churn

**Scope agreed**: full review (logic + statistical validity + code), since this is the highest-
stakes single artifact in the lab — the model that Phase 6 deployment and the executive
summary's $43K recommendation both depend on. Reviewed:
`crisp_dm/05_evaluation/model-evaluation.md`, `artifacts/final_metrics.json`, `artifacts/model.joblib`,
`src/p3_pipeline.py`, `src/p4_tuning.py`, `src/p4_imbalanced.py`.

### Analytical rigour review

- **Question/method alignment**: ✅ imbalanced target → PR-AUC/recall-first evaluation, not
  accuracy-led. Threshold tuned to a stated capacity constraint, not a default 0.5.
- **Leakage check**: ✅ independently re-verified — no numeric feature exceeds |corr|>0.95 with
  target (`verify_claims.py`), and ROC-AUC 0.8482 sits in the honest 0.75-0.90 range for this
  dataset rather than a leakage-suspicious >0.90.
- **LTV conflict**: ✅ resolved with a stated, checkable mechanism (survivorship bias from
  right-censoring), not just asserted — the algebra (ARPU/hazard implies 122-month lifetime vs.
  32.4-month observed mean, 72-month censoring) is shown, not hand-waved.

### Code review

**Must-fix (found, and fixed before this review closed)**: `model.joblib`'s pickled pipeline
requires `TotalCharges` pre-coerced to numeric — the raw CSV ships it as a string, and the
pipeline's `.isna()` check silently no-ops on a string column rather than raising. This would
have shipped a broken `inference_contract.json` to the serving layer. **Disposition: fixed** —
contract corrected, `model-serving`'s Pydantic validator now enforces the right input type, and
the fix is verified by a passing live request against the actual blank-`TotalCharges` case in
`serving_smoke_test.md`.

**Should-fix (raised, accepted-as-is with rationale)**: `model.joblib`'s reproducibility depends
on `src/` being on `sys.path` at load time (the pickle references `p3_pipeline.FeatureEngineer`
by module name) — a more portable design would package `p3_pipeline` properly or use
`cloudpickle` with an explicit module reference. **Author's rationale for accepting as-is**:
this is a documented, deterministic requirement (stated in `inference_contract.json` and
`model_card.md`), not a silent failure mode, and repackaging into a proper Python package is
out of scope for a lab exercise — deferred to a real-deployment follow-up, not treated as
blocking.

**Optional (noted, not required)**: the fairness parity check
(`artifacts/fairness_parity.json`) uses a default-threshold-style comparison rather than the
final `chosen_threshold` (0.2856) consistently across every subgroup metric shown — worth
re-running at the deployed threshold specifically if this model is used for anything with
fairness/compliance stakes beyond this lab.

### Statistical validity — one finding elevated to a standing caveat, not just a review comment

The Contract-type effect (42.7% vs 2.8% churn) is observational. The peer review confirms this
is *stated*, not just internally known — it appears in `model-evaluation.md`,
`ab-test-analysis.md`, `executive_summary.md`'s closing section, and `model_card.md`'s
limitations. **This is the review's main structural finding**: a claim this load-bearing needed
to survive into every downstream document, and a check confirms it did, rather than getting
lost between phases in a multi-agent lab.

## Outputs produced

- `artifacts/peer_review_model_evaluation.md` — this review, itemized must-fix/should-fix/
  optional with dispositions, standalone from this doc for reuse as a template instance.
