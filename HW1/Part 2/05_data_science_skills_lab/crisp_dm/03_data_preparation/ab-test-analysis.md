---
skill: ab-test-analysis
pack: nimrodfisher/data-analytics-skills
crisp_dm_phase: 3 - Data Preparation
artifacts:
  - artifacts/ab_test_analysis_report.md
  - artifacts/ab_test_sample_size_scenarios.json
  - reports/figures/ab_test_tenure_adjusted.png
---

# ab-test-analysis

## What the skill prescribes

Confirm test design (hypothesis, arms, randomization unit, primary+guardrail metrics, split) →
SRM chi-square check → per-variant rate + 95% CI → two-proportion z-test → guardrail checks →
ship/no-ship recommendation. Pre-launch: sample-size formula
`n = 2(z_a/2+z_b)^2 p(1-p)/MDE^2`.

## Applied to Telco churn — honestly, in two parts, because there is no experiment here

Telco Customer Churn is **observational cross-sectional data. There was never a randomized
experiment.** `src/p3_ab_test_analysis.py` does not pretend otherwise.

### (a) Test design for a real future experiment

Hypothesis: offering a 1-year-contract discount to month-to-month (M2M) Fiber customers reduces
churn. Measured baseline (M2M+Fiber population): **55.07% churn** (n=1,707).

| MDE | Target rate | n/group | Total n |
|---|---|---|---|
| 3pp | 52.1% | 4,311 | 8,622 |
| 5pp | 50.1% | 1,552 | 3,104 |
| **8pp** | 47.1% | **607** | 1,214 |
| 10pp | 45.1% | 388 | 776 |

Current population gives 853/arm at 50/50 — the finest MDE powerable today without waiting for
more sign-ups is **8pp** (needs 607/arm); a 5pp MDE needs 1,552/arm, requiring eligibility
expansion or a longer run. Guardrails specified: ARPU (must not drop more than the discount's own
cost) and support-ticket rate (flagged as a required addition — not present in this dataset). SRM
check specified for post-launch validation of the randomization pipeline.

### (b) Observational analysis — Contract groups run through the skill's own analyzer

Ran the shipped `srm_check()` + `analyze_binary_metric()` on Month-to-month (n=3,102, 42.75%
churn) vs Two-year (n=1,359, 2.87% churn) as if they were experiment arms: **z=−26.60,
p≈0, 95% CI [−41.83%, −37.92%]** — a textbook "ship it" result if this were a real test.

**Why the naive causal read is invalid**: SRM technically flags (chi²=681, p≈0) but this is
**not meaningful** — SRM detects broken *randomization*; there was none here, contract choice is
customer self-selected, so the group-size imbalance reflects real self-selection, not an
assignment bug. The 93.3% "relative lift" is an association between two self-selected
populations, confounded by tenure, price sensitivity, and service type.

**Covariate-adjusted comparison (tenure-stratified)**: unadjusted M2M-vs-Two-year gap
**+39.88pp** → tenure-adjusted (within-stratum, reweighted to overall tenure distribution)
**+36.09pp**. The gap shrinks modestly after controlling for tenure (long-tenured customers are
mechanically both more likely to be on a long contract AND less likely to churn, since surviving
long enough to renew requires not having churned already) — but a large gap remains within every
tenure stratum (e.g. 0-12mo: 51.1% M2M vs 0% Two-year). Contract length still looks associated
with lower churn even among comparably-tenured customers, but the causal share of that remaining
gap cannot be established without the randomized test specified in part (a).

## Outputs produced

- `artifacts/ab_test_analysis_report.md` — full design spec + observational analysis + adjustment.
- `artifacts/ab_test_sample_size_scenarios.json` — sample-size table, SRM/significance results,
  unadjusted vs adjusted gap.
- `reports/figures/ab_test_tenure_adjusted.png` — churn by contract, per tenure stratum.
