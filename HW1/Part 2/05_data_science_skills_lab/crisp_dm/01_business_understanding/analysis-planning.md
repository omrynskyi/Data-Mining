---
skill: analysis-planning
pack: nimrodfisher/data-analytics-skills
crisp_dm_phase: 1 - Business Understanding
artifacts: []
---

# Analysis Planning — Telco Customer Churn (full 6-phase CRISP-DM plan)

## What the skill prescribes

- Decompose the business question into sub-questions, each answerable with a single data pull or calculation (`references/scoping_framework.md`).
- Identify data dependencies per sub-question and assess availability (confirmed / likely / unknown).
- Sequence the work so outputs feed forward; identify parallelizable steps.
- Estimate effort per step (`references/effort_estimation.md`) and compare against the deadline.
- Log risks and dependencies (`references/risks_dependencies.md`).
- Produce the plan (`assets/analysis_plan_template.md`); optionally a kickoff doc (`assets/kickoff_doc_template.md`).

## Applied to Telco churn

### Business question decomposition (`scoping_framework.md`)

Root question (from `stakeholder-requirements-gathering.md`): *Which active customers have the highest churn probability and revenue at risk, ranked for monthly retention outreach?*

Test against the well-formed-question criteria: subject = active customers; metric = churn probability x revenue at risk; context = monthly, all residential segments; decision = retention outreach prioritization. Specific enough to decompose.

Decomposition pattern used: **component + causal chain** (churn risk = f(contract, services, tenure, billing) x revenue exposure).

| # | Sub-question | CRISP-DM phase | Dependencies |
|---|---|---|---|
| 1 | What does "done" mean, who's the audience, what's in/out of scope? | **1. Business Understanding** | None |
| 2 | What real SaaS-style metrics (MRR, ARPU, churn, LTV) describe the current state? | 1. Business Understanding | Sub-q 1 |
| 3 | What does the data actually look like — types, nulls, distributions, leakage risks? | **2. Data Understanding** | Sub-q 1 |
| 4 | Which columns are trustworthy / usable as-is vs. need cleaning? | 2. Data Understanding | Sub-q 3 |
| 5 | How should missing values, encodings, and feature transforms be handled without leakage? | **3. Data Preparation** | Sub-q 4 |
| 6 | What features best separate churned vs. retained customers? | 3. Data Preparation | Sub-q 5 |
| 7 | Which model(s) predict churn probability well, calibrated for ranking? | **4. Modeling** | Sub-q 6 |
| 8 | Does the model generalize, and is it fair/robust enough to act on? | **5. Evaluation** | Sub-q 7 |
| 9 | How is the ranked risk list produced, delivered, and kept current? | **6. Deployment** | Sub-q 8 |

Each sub-question maps 1:1 to a CRISP-DM phase — this *is* the project's phase plan.

### Data dependency map

| Sub-question | Data needed | Source | Availability |
|---|---|---|---|
| 2 | Full customer snapshot | `data/Telco-Customer-Churn.csv` | Confirmed |
| 3-4 | Same, column-level profiling | same + `artifacts/data_catalog_telco.md` | Confirmed |
| 5-6 | Train/test split (no leakage) | `data/processed/{train,test}.csv` | Confirmed (seed=42, stratified) |
| 7-8 | Same, feature matrix | derived from `data/processed/` | Confirmed, pending Phase 3 |
| 9 | Scored output target | none yet — to be defined in Phase 6 | Unknown (deployment target: file export vs. dashboard — decide in Phase 6) |

No blockers: every phase's core data dependency is already confirmed and versioned (`data/processed/dataset_meta.json`).

### Sequencing

Sequential by design — CRISP-DM phases 1-6 each build on the last; sub-questions 1 and 2 are already substantially parallel (this lab demonstrates 6 skills together as Phase 1). Within Phase 1, sub-questions 1 and 2 can run in parallel since metric calculation doesn't depend on the requirements doc's wording, only on the shared business framing — that's how this lab was executed (all 6 Phase-1 skills draw from the same framing, run independently).

### Effort estimate (`references/effort_estimation.md`)

| Phase | Task type | Estimate | Multiplier applied | Adjusted |
|---|---|---|---|---|
| 1. Business Understanding | Requirements + planning + metrics + catalog + semantic model | ~1 day (6 skill demos) | 1.0x (familiar data) | ~1 day |
| 2. Data Understanding | EDA on <20-column dataset | 1-2h | 1.0x | 1-2h |
| 3. Data Preparation | Cleaning + feature engineering, leakage-safe | 0.5-1 day | 1.0x | 0.5-1 day |
| 4. Modeling | Standard algorithm, clean data, imbalanced target (26.5% churn) | 1-3 days | 1.3x (imbalanced-data care) | 1.5-4 days |
| 5. Evaluation | Model evaluation + calibration for ranking | 3-5h | 1.0x | 3-5h |
| 6. Deployment | Ranked-list export / lightweight serving | 0.5-1 day | 1.0x | 0.5-1 day |
| **Total** | | | | **~4.5-8 days** |
| **Buffer (15%)** | | | | **~0.7-1.2 days** |
| **Revised estimate** | | | | **~5-9 days** |

No external dependency delays expected — data is already downloaded and split; no access requests pending.

### Risks and dependencies (`references/risks_dependencies.md`)

| Risk / Dependency | Probability | Timeline impact | Mitigation |
|---|---|---|---|
| Target is imbalanced (26.5% churn) — naive accuracy misleading | High (known now) | Could invalidate Phase 5 conclusions if unaddressed | Use the `imbalanced-data` skill in Phase 4; report precision/recall/PR-AUC, not just accuracy |
| No CAC/margin data — LTV:CAC, payback period unavailable | Certain (known now) | None to timeline; scopes out one deliverable | Documented as a data gap in `business-metrics-calculator.md`; not blocking |
| `TotalCharges` has 11 nulls (tenure=0 rows) | Certain (known now) | Low — small n | Coerce numeric, impute or exclude per `data-cleaning` skill in Phase 3, fit on train only |
| Cross-sectional snapshot (no time series) limits "monthly" metric validity | Certain (known now) | Low — affects interpretation, not feasibility | All "monthly" figures explicitly labeled as approximations (see `artifacts/business_metrics.json`) |
| Model overfits given only 5,634 training rows and 19 features | Medium | +0.5 day if retuning needed | Cross-validation in Phase 4/5 (`sklearn-pipelines`, `hyperparameter-tuning` skills) |

**Escalation trigger status:** none triggered — no dependency currently threatens >20% timeline slip, and no key assumption has been invalidated.

### Analysis plan (`assets/analysis_plan_template.md`, filled)

**Project:** Telco Voluntary Churn Risk Scoring
**Analyst:** Data Science Skills Lab (this project)
**Requestor:** VP of Customer Retention [simulated stakeholder input]
**Date created:** 2026-09-02
**Target delivery date:** End of lab
**Status:** In progress (Phase 1 of 6)

**Business Question:** *(as above)*

**Sub-Questions and Sequencing:** *(table above, mapped 1:1 to CRISP-DM phases 1-6)*

**Total estimated effort:** ~4.5-8 hours-days (see table) | **Buffer (15%):** ~0.7-1.2 days | **Revised estimate:** ~5-9 days

**Data Plan:** `data/Telco-Customer-Churn.csv` (confirmed) -> `data/processed/{train,test}.csv` (confirmed).

**Approach Summary:** Full CRISP-DM cycle. Phase 1 establishes business framing, real baseline metrics, a semantic model, and a data catalog (this lab's current deliverable — 6 skills). Phases 2-3 profile and prepare data leakage-safely. Phase 4 trains a churn-probability classifier tuned for ranking under class imbalance. Phase 5 evaluates generalization and calibration. Phase 6 produces the ranked, revenue-weighted risk list the retention team consumes monthly.

**Risks and Dependencies:** *(table above)*

**Milestones:**

| Milestone | Target | Status |
|---|---|---|
| Requirements confirmed | Phase 1 | Done (`stakeholder-requirements-gathering.md`) |
| Data access confirmed | Phase 1 | Done — `data/processed/dataset_meta.json` |
| Business metrics + semantic model + catalog complete | Phase 1 | Done (this batch of 6 skill docs) |
| Data understanding (EDA) complete | Phase 2 | Pending |
| Data preparation complete | Phase 3 | Pending |
| Model trained & tuned | Phase 4 | Pending |
| Model evaluated | Phase 5 | Pending |
| Ranked risk list delivered | Phase 6 | Pending |

**Out of Scope:** Enterprise accounts (not in dataset), real-time scoring, CAC-based unit economics (no data).

## Outputs produced

- This document — full 6-phase CRISP-DM analysis plan (serves as `analysis_plan_template.md`, filled), covering all later phases of this lab.
- Risk/dependency log embedded above (`risks_dependencies.md` applied).
- No separate kickoff doc produced — this is a self-directed lab exercise, not a multi-party stakeholder kickoff; the analysis plan above serves as the equivalent artifact.
