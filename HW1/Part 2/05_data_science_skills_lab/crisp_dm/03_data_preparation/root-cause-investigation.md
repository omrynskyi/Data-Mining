---
skill: root-cause-investigation
pack: nimrodfisher/data-analytics-skills
crisp_dm_phase: 3 - Data Preparation
artifacts:
  - artifacts/root_cause_investigation_report.md
  - artifacts/root_cause_decomposition.json
  - reports/figures/root_cause_decomposition.png
---

# root-cause-investigation

## What the skill prescribes

5-step process: validate the change beyond normal variance (z-score/std-dev check) → establish a
timeline/comparison → decompose the metric into constituents → drill down systematically across
dimensions, ranked by contribution (`drilldown_analyzer.py`) → test explicit hypotheses,
accept/reject each with evidence → report primary driver + tiered recommendations.

## Applied to Telco churn — elevated Fiber optic churn

`src/p3_root_cause_investigation.py` runs the full process on a real, first-verified anomaly.

**1. Validate**: Fiber optic churn = **42.09%** (n=2,483) vs Non-Fiber (DSL+No) = **14.28%**
(n=3,151), overall 26.54%. Two-proportion z-test: **z=23.47, p=8.66e-122** — far beyond the
skill's "close and stop within ±1.5σ" threshold; a real, decisive gap (2.95x).

**2-3. Decompose (mix vs rate, dimension = Contract)** — Kitagawa/Oaxaca-style decomposition of
the Fiber-minus-Non-Fiber rate gap (+27.81pp total):

| Effect | Contribution | Share of gap |
|---|---|---|
| **Mix effect** (Fiber skews more month-to-month: 68.7% vs 44.3%) | +6.11pp | 22.0% |
| **Within-segment rate effect** (Fiber churns more even at matched contract type) | **+21.69pp** | **78.0%** |

**Primary driver: within-segment rate effect** — even among month-to-month customers only, Fiber
churns at 55.1% vs DSL/No's 27.7%; contract mix explains under a quarter of the gap.

**4. Drill-down** (shipped `drilldown_analyzer.py`, dimension=PaymentMethod, metric=churned-count):
Electronic check is the single largest absolute contributor to the Fiber-vs-Non-Fiber
churned-customer count gap (+507 churned customers, **+85.2%** of the total contribution) —
Fiber customers use Electronic check at 51.1% vs 19.8% for Non-Fiber.

**5. Hypotheses**: H1 (price) — Fiber averages $91.67/mo vs $43.86/mo, ACCEPTED as contributing,
consistent with the rate effect. H2 (payment-method mix) — PARTIALLY ACCEPTED, largest single mix
contributor per the drill-down. H3 (data/measurement artifact) — REJECTED (no missing/malformed
values, large stable category counts, p<<0.001).

**Conclusion**: real, decisive elevation, 78% within-segment / 22% mix. Immediate action:
prioritize retention offers for month-to-month Fiber customers (compounded highest-risk cell);
short-term: investigate Fiber pricing/service-quality; long-term: track the price-value gap over
time.

## Outputs produced

- `artifacts/root_cause_investigation_report.md` — full 5-step writeup with tables.
- `artifacts/root_cause_decomposition.json` — z-test + mix/rate decomposition numbers.
- `reports/figures/root_cause_decomposition.png` — mix vs rate contribution bar chart.
