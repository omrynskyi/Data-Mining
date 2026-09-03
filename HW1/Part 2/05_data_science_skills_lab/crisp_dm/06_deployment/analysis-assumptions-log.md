---
skill: analysis-assumptions-log
pack: nimrodfisher/data-analytics-skills
crisp_dm_phase: 6 - Deployment
artifacts:
  - src/p6c_assumptions_log.py
  - artifacts/assumptions_log_telco.json
  - artifacts/assumptions_log_report.txt
---

## What the skill prescribes

Six-step process: initialize a structured log (`scripts/assumptions_tracker.py`); enumerate
data assumptions (representativeness, missing-value handling, quality issues); enumerate
business logic assumptions (metric definitions, inclusion/exclusion rules); enumerate
statistical assumptions (distributional/independence/model assumptions); assess impact and
flag critical ones (unvalidated + low confidence + high/critical impact); validate and close,
exporting a peer-review-ready log via `assets/assumptions_log_template.md`.

**Shipped-script note:** `scripts/assumptions_tracker.py` defines a proper argparse `main()`
but its `if __name__ == "__main__":` guard calls `_demo()` unconditionally and never calls
`main()` — so running it directly with `--load`/`--report`/`--validate` silently falls through
to the hardcoded demo instead of honoring the CLI args. Since `.claude/skills/` is read-only,
`src/p6c_assumptions_log.py` imports `new_log`, `add_assumption`, `report`, and `get_critical`
directly from the module rather than invoking the broken CLI (see
`analysis-retrospective.md` for the full list of upstream skill-pack bugs found this lab).

## Applied to Telco churn

`src/p6c_assumptions_log.py` logs 10 real assumptions this lab made across all four
categories, run through the tracker's own risk-scoring. Full report: `artifacts/assumptions_log_report.txt`
/ `artifacts/assumptions_log_telco.json`.

### Summary

| Total assumptions | Validated | Flagged critical by script | High-risk-score (>=6) unvalidated |
|---|---|---|---|
| 10 | 0 | 0 | 3 (#5 risk=6, #7 risk=7, #4 risk=5*) |

\* #4 scores 5, included because a +24.38pp measured bias is a large, already-quantified effect
even though its risk formula lands at 5.

**A real gap in the script's own critical-flagging logic, found while using it:**
`get_critical()` only flags assumptions with **confidence == "low"**. Two of this lab's
highest-stakes assumptions (#5, observational Contract comparison, and #7, the LTV conflict)
are rated **high/medium confidence with critical impact** — the risk-scoring table in
`references/assumption_categories.md` itself scores medium-confidence + critical-impact at
**7** ("Validate before presenting"), the highest score in the whole matrix, yet
`get_critical()`'s hardcoded filter (`confidence == "low"`) never surfaces them. Relying on the
script's `sys.exit(1 if critical else 0)` gate alone would have silently shipped this analysis
with its two most consequential assumptions unflagged. Treated manually as critical for this
delivery; noted as a tool defect in `analysis-retrospective.md`.

### Data assumptions

| # | Assumption | Confidence | Impact if wrong | Risk | Validated |
|---|---|---|---|---|---|
| 1 | 11 blank `TotalCharges` = unbilled tenure=0 signups; impute $0 | High | Low | 3 | No — but corroborating check (100% at tenure=0) already run |
| 2 | 'No internet/phone service' sentinels collapsed to 'No' | High | Medium | 3 | No — reversible from `InternetService`/`PhoneService` if ever needed |
| 3 | `tenure` stands in for signup recency (no signup_date field exists) | Medium | High | 6 | No — bias already quantified, not assumed away (see #4) |

### Business logic assumptions

| # | Assumption | Confidence | Impact if wrong | Risk | Validated |
|---|---|---|---|---|---|
| 4 | Cross-sectional cohort reconstruction biases older cohorts' survival curves upward | High | High | 5 | Yes — magnitude directly measured (+24.38pp vs. pooled baseline); mitigation applied (use pooled hazard curve for decisions) |
| 5 | Contract-vs-churn comparison is observational, not causal | High | Critical | 6** | No — real experiment designed and powered but not run |
| 6 | k=3 chosen over silhouette-optimal k=2 for segmentation | High | Medium | 3 | Yes — explicit trade-off documented, alternative (k=2) re-derivable from same table |
| 7 | Tenure-based LTV ($2,283.30) is the defensible figure, not hazard-based ($7,899.96) | Medium | Critical | 7** | **Blocking** on Phase 5's written ruling — see below |

\*\* Risk scores 6 and 7 — both above the "validate before presenting" line in the skill's own
scoring table — despite not tripping the script's `get_critical()` filter (see gap noted above).

### Statistical assumptions

| # | Assumption | Confidence | Impact if wrong | Risk | Validated |
|---|---|---|---|---|---|
| 8 | Association metrics (Cramér's V, point-biserial r) computed on train split only | High | Low | 3 | Yes — cross-checked against full-population recomputation this phase; values close, not identical (documented in QA doc) |
| 9 | Two-term mix/rate decomposition needs no separate interaction term | Medium | Low | 3 | No — residual is small enough not to change the 78/22 headline |

### Technical assumptions

| # | Assumption | Confidence | Impact if wrong | Risk | Validated |
|---|---|---|---|---|---|
| 10 | Seed=42 applied consistently gives reproducible splits/results | High | Low | 3 | Yes — `repro_determinism_proof.json` |

### Critical assumptions requiring validation (manually flagged — see script gap above)

| # | Assumption | Validation plan | Owner | Status |
|---|---|---|---|---|
| 5 | Contract length's causal effect on churn is unknown | Run the powered A/B test specced in `03_data_preparation/ab-test-analysis.md` (607/arm minimum, 8pp MDE) before sizing any contract-campaign ROI off the observational number | Growth/Experimentation | Open |
| 7 | LTV figure conflict ($7,899.96 vs $2,283.30) | Resolved by Phase 5's written ruling in `model-evaluation.md` / `final_metrics.json`; `impact-quantification.md` states and uses whichever figure Phase 5 rules defensible | Phase 5 modeling agent | **Blocking `impact-quantification.md`** — see that doc for resolution status at time of writing |

## Outputs produced

- `src/p6c_assumptions_log.py` — builds the log via the skill's own tracker functions (imported
  directly, bypassing the broken CLI entry point)
- `artifacts/assumptions_log_telco.json` — structured log, all 10 entries
- `artifacts/assumptions_log_report.txt` — the tracker's own formatted report output
