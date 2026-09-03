---
skill: analysis-documentation
pack: nimrodfisher/data-analytics-skills
crisp_dm_phase: 6 - Deployment
artifacts:
  - artifacts/business_metrics.json
  - artifacts/data_quality_scorecard.md
  - crisp_dm/01_business_understanding/
  - crisp_dm/02_data_understanding/
  - crisp_dm/03_data_preparation/
---

## What the skill prescribes

Six-step process: confirm audience and scope (tiered structure for mixed audiences, per
`references/audience_depth_guide.md`); write the business context (question, requesting
stakeholders, decision, success criteria); document data sources (table/file, date range, row
count, quality issues); write the methodology (approach, tools/versions, assumptions,
alternatives considered); record results (metrics, visualizations with captions, findings
ranked by importance); write insights/recommendations/reproducibility, connecting each finding
to an action and documenting exact re-run steps. Uses `assets/analysis_doc_template.md`.

## Applied to Telco churn

This is the archival, handover-grade document for the whole lab — written for a mixed
audience (a future analyst re-running this work, and a business stakeholder deciding whether
to act on it), using the template's tiered structure.

---

# Analysis Documentation

**Title:** Telco Customer Churn — Full CRISP-DM Analysis
**Author:** Multi-agent analysis team (Phases 1-6)
**Date:** 2026-09-02
**Status:** Final (Phases 1-3, 6 complete; Phases 4-5 modeling in progress at time of writing —
see the "Reproducibility" section for how to check current status)
**Audience:** Executive / Analytical peer / Technical handover (tiered — see sections below)

## Question

Which Telco customers are likely to churn, why, and how much revenue is at stake — and what
should the business do about it?

## Key finding

Churn is concentrated and explainable: contract length (Cramér's V=0.411) and Fiber optic
service (41.89% vs. 14.49% churn, most of it a genuine within-segment effect, not just mix) are
the two strongest, most actionable drivers, and they compound in one segment holding 43.3% of
the customer base and $77,946/mo of revenue at risk. Revenue churn (30.5%) outpaces logo churn
(26.5%) because the customers leaving pay more on average than the customers who stay.

## Context

Telco Customer Churn (Kaggle `blastchar/telco-customer-churn`) is a common churn-modeling
benchmark dataset repurposed here as a full data-science-skills demonstration lab, running
CRISP-DM end to end with 48 distinct analytics-skill packages applied across all six phases.
The business framing (Phase 1) treats it as if commissioned by a telecom's customer-success and
finance leadership to answer: who is at risk, how much revenue that represents, and what a
retention program should prioritize first.

## Data sources

| Source | Table / file | Date range | Row count | Notes |
|---|---|---|---|---|
| Kaggle blastchar/telco-customer-churn | `data/Telco-Customer-Churn.csv` | Single snapshot (no explicit date; no timestamp field) | 7,043 | 21 columns; 11 rows have blank `TotalCharges` (all tenure=0, imputed); no duplicate customerIDs; data quality score 10.00/10, 19/21 checks pass, 2 N/A (no FKs shipped, no freshness SLA on a static extract) — see `artifacts/data_quality_scorecard.md` and the QA re-assessment of that score in `analysis-qa-checklist.md` |
| Derived: train/test split | `data/processed/train*.csv`, `test*.csv` | n/a | 5,634 train / 1,409 test | seed=42, stratified on `Churn`; used for all feature-selection and model-facing statistics to avoid leakage |

## Approach

1. **Business Understanding (Phase 1):** defined MRR/ARPU/churn metric formulas, a data
   catalog, and a semantic model; flagged the missing CAC field as an open data gap up front.
2. **Data Understanding (Phase 2):** structural/quality profiling (10.0/10 scorecard),
   modeling-readiness EDA on the train split (association strength ranking, leakage scan —
   `TotalCharges ≈ tenure x MonthlyCharges`, r=0.9996, ruled redundancy not leakage), schema
   mapping, SQL validation against a loaded SQLite mirror.
3. **Data Preparation (Phase 3):** cleaning (sentinel collapse, TotalCharges imputation),
   feature engineering, a leakage-safe sklearn pipeline, cohort/time-series reconstruction
   (with a quantified survivorship bias), a root-cause decomposition of the Fiber-churn gap, a
   funnel analysis of service adoption, k-means segmentation, and an A/B test design +
   observational-comparison demonstration.
4. **Modeling / Evaluation (Phases 4-5):** in progress at time of writing — see
   Reproducibility below for how to check status; this document's findings are all drawn from
   Phases 1-3, which do not depend on model output.
5. **Deployment (Phase 6, this document's phase):** governance/communication skills (insight
   synthesis, translation, methodology explanation, assumptions log, this document, QA/peer
   review, retrospective) plus a parallel technical track (visualization, dashboard spec, RAG,
   fine-tuning, model-serving specs) owned by a separate agent.

## Findings

### 1. Contract length is the dominant churn driver
Month-to-month 42.71% churn, one-year 11.27%, two-year 2.83% (Cramér's V=0.411, strongest of
16 categorical features tested). See `crisp_dm/02_data_understanding/exploratory-data-analysis.md`.

### 2. Fiber optic churn is real and mostly not a contract-mix artifact
41.89% vs. 14.49% non-Fiber (full population, z=25.85, p≈2.4e-147); decomposition attributes
78% to a within-segment rate effect, 22% to contract mix. See
`crisp_dm/03_data_preparation/root-cause-investigation.md`.

### 3. Revenue churn outpaces logo churn
26.537% of customers churned but they represented 30.503% of MRR ($139,130.85 of
$456,116.60/mo); churners average $74.44/mo vs. $61.27/mo for retained customers. See
`artifacts/business_metrics.json`.

### 4. Add-ons and support are protective; internet-only adoption is the danger zone
Churn by funnel stage: 26.71% (phone) -> 32.80% (+internet) -> 29.82% (+1 add-on) -> 21.52%
(+3 add-ons) -> 14.01% (+support). See `crisp_dm/03_data_preparation/funnel-analysis.md`.

### 5. One segment concentrates most of the identified revenue at risk
K-means cluster "new, mid-ARPU, month-to-month-heavy": 2,439 customers (43.3% of base), 45.5%
churn, $77,946/mo at risk of $109,353/mo total rule-based MRR at risk. See
`crisp_dm/03_data_preparation/segmentation-analysis.md`.

### Negative findings (equally documented)
`gender` (Cramér's V=0.008) and `PhoneService` (V=0.011) show no meaningful association with
churn — rule out demographic-targeting and phone-service-upsell hypotheses.

## Key assumptions

| Assumption | Confidence | Impact if wrong |
|---|---|---|
| Cross-sectional cohort reconstruction biases older cohorts' survival curves upward (+24.38pp measured) | High | High |
| Contract-vs-churn comparison is observational, not causal | High | Critical |
| Tenure-based LTV ($2,283.30), not hazard-based ($7,899.96), is the defensible figure | Medium | Critical |
| k=3 chosen over silhouette-optimal k=2 for actionability | High | Medium |

Full log with rationale, risk scores, and validation status: `analysis-assumptions-log.md`.

## Caveats and limitations

- **Single cross-sectional snapshot** — no monthly ledger, so MRR waterfall (new/expansion/
  contraction) and true NRR cannot be computed as normally defined; approximated via customer-
  month hazard rate instead, documented as an open gap rather than silently faked.
- **No CAC or gross-margin field** — LTV:CAC ratio and payback period cannot be computed; LTV
  itself is revenue-basis, not gross-profit-basis.
- **Cohort curves for individual quarters are directionally informative but not point-accurate**
  for the reason documented in finding/assumption #1 above — use the pooled hazard curve for
  any number that needs to be defensible in a decision.
- **The Contract effect size (93% relative churn reduction, unadjusted) is not a causal claim.**
  A tenure-adjusted comparison brings it to +36.09pp remaining gap; only a real randomized test
  (specced, not yet run) can produce a causal number.

## Recommendations / next steps

1. Route the first wave of retention offers to segmentation cluster 1 (2,439 customers,
   $77,946/mo at risk) — Retention/CS, immediate.
2. Launch the powered contract-upgrade A/B test on month-to-month Fiber customers (minimum
   607/arm for an 8pp MDE) before committing budget to a broad contract-conversion campaign —
   Growth/Experimentation, next quarter.
3. Re-rank churn-risk scoring by `P(churn) x MonthlyCharges` rather than `P(churn)` alone, given
   finding #3 — Data/Analytics, this sprint.
4. Resolve the LTV conflict via Phase 5's ruling before finalizing any ROI-based business case —
   see `impact-quantification.md` for how this was handled at time of writing.

## Reproducibility

**Code location:** `src/p1_*.py` through `src/p6c_*.py`, one script per skill applied, phase-prefixed.
**Data pull:** `data/Telco-Customer-Churn.csv` (read-only input); processed splits under `data/processed/`.
**To reproduce:**
1. `pip install -r requirements.txt` (pandas, numpy, scipy, sklearn, matplotlib, seaborn,
   statsmodels; Python 3.9.6 — note two upstream skill scripts use PEP 604 `X | None` syntax and
   will crash on 3.9; see `analysis-retrospective.md`)
2. Run phase scripts in order (`p1_` -> `p2_` -> `p3_` -> `p4_` -> `p6c_`); each writes its
   artifacts to `artifacts/` and figures to `reports/figures/`
3. Ledgers (`artifacts/ledger_phase*.jsonl`) record which skill produced which artifact, one
   line per skill, for audit purposes
4. **Check current phase status:** `ls artifacts/final_metrics.json artifacts/model_card.md` —
   presence indicates Phase 4/5 modeling has completed; this document and the rest of Phase 6b
   were finalized before confirming that file's arrival (see `analysis-retrospective.md` for
   what that means for the model-dependent Phase 6 deliverables).

## Outputs produced

- This document, following `assets/analysis_doc_template.md`
- Synthesizes and cross-references all Phase 1-3 deliverables rather than duplicating their
  full detail; serves as the single entry point for a new reader or auditor
