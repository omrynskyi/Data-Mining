# A/B Test Analysis — Telco Customer Churn

**This dataset is observational, cross-sectional customer data. There was no randomized experiment.** Part (a) below specs a real future test. Part (b) runs the skill's analysis machinery on the existing Contract groups purely to demonstrate the mechanics, and then explains — with a quantified covariate adjustment — why treating that comparison as a causal A/B result would be wrong.

## (a) Test design — future experiment

**Hypothesis**: Offering a 1-year-contract discount to month-to-month (M2M) Fiber customers reduces their churn rate.

- **Population**: M2M + Fiber optic customers.
- **Randomization unit**: customer (customerID).
- **Primary metric**: churn within the observation window (proxy for the dataset's own cross-sectional churn indicator).
- **Guardrail metrics**: ARPU (monthly revenue per user — a discount that saves customers but craters revenue is not a win) and complaint/support-ticket rate (not available in this dataset; flagged as a required addition before launch).
- **Traffic split**: 50/50.

- **Measured baseline churn rate** (M2M Fiber customers, current population): **55.07%** (n=1,707).

### Required sample size (skill's formula: n = 2(z_a/2+z_b)^2 p(1-p)/MDE^2)

| MDE (absolute pp reduction) | Target rate | n per group | Total n |
|---|---|---|---|
| 3pp | 52.1% | 4,311 | 8,622 |
| 5pp | 50.1% | 1,552 | 3,104 |
| 8pp | 47.1% | 607 | 1,214 |
| 10pp | 45.1% | 388 | 776 |

- Current M2M-Fiber population is 1,707 customers — a 50/50 split gives 853 per arm. Reading the table above, the smallest MDE with a per-group requirement at or below 853 is **8pp** (needs 607/arm) — that is the finest effect this population can power today without waiting to accumulate more sign-ups; a 5pp MDE test would need 1,552/arm, i.e. expanding eligibility beyond pure M2M-Fiber or running long enough to grow the eligible pool.

**Guardrails**: stop and do not ship if ARPU per M2M-Fiber customer drops more than the discount's own cost, or if the treatment group's support-ticket rate rises significantly. **SRM check**: run `srm_check()` on realized vs intended 50/50 allocation after randomization executes; flag if p < 0.01 (see the skill's own guidance — do not interpret results if SRM is detected).

## (b) Observational analysis — Contract groups run through the skill's analyzer

```
============================================================
A/B TEST ANALYSIS REPORT
============================================================

--- Sample Ratio Mismatch (SRM) Check ---
  Control:   3,102  (expected 2,230)
  Treatment: 1,359  (expected 2,230)
  Chi2: 681.0242  |  p-value: 0.0
  SRM detected: YES — investigate before trusting results

--- Metric: churn (M2M vs Two-year, as if A/B arms) ---
  Control rate:   42.7466%
  Treatment rate: 2.8698%
  Absolute diff:  -39.8769%
  Relative lift:  -93.29%
  Z-score: -26.6012  |  p-value: 0.0
  95% CI for diff: [-41.8310%, -37.9227%]

  VERDICT: SIGNIFICANT at alpha=0.05
  Recommendation: Treatment shows a statistically significant negative effect. Do not ship.
============================================================
```

**SRM check is not meaningful here** — SRM detects broken RANDOMIZATION (bot filtering, stickiness bugs, etc.). There was no randomization: customers *chose* their contract length. The group-size imbalance above (M2M n vs Two-year n) reflects real self-selection into contract type, not an assignment bug, so the SRM chi-square result is reported for completeness only and carries no diagnostic meaning in this context.

**The naive causal read** — "switching a customer from month-to-month to a two-year contract would cut their churn probability by 93.3%" — **is invalid.** Contract choice is confounded with everything that makes a customer committed in the first place: tenure, price sensitivity, service type, and (unobserved) satisfaction. The z-test above is measuring an association between two self-selected populations, not the causal effect of a contract-length intervention.

### Covariate-adjusted comparison — stratified by tenure bucket

| tenure_stratum   |   n_m2m |   churn_m2m_pct |   n_2yr |   churn_2yr_pct |   abs_diff_pp |
|:-----------------|--------:|----------------:|--------:|----------------:|--------------:|
| 0-12mo           |    1594 |           51.07 |      55 |            0    |         51.07 |
| 13-24mo          |     580 |           38.28 |      72 |            0    |         38.28 |
| 25-48mo          |     650 |           32.77 |     227 |            1.76 |         31.01 |
| 49-72mo          |     278 |           27.7  |    1005 |            3.48 |         24.22 |

- **Unadjusted** M2M-vs-Two-year churn gap: **+39.88 pp**.
- **Tenure-adjusted** (within-stratum gaps, weighted by overall tenure distribution): **+36.09 pp**.
- The gap shrinks after controlling for tenure (+39.88pp -> +36.09pp), which is exactly what the skill's guidance asks us to check: even after removing the part of the raw gap that tenure alone explains (long-tenured customers are both more likely to be on a long contract AND less likely to churn, mechanically, since surviving long enough to renew requires not having churned), a large gap remains within every tenure stratum — Contract length still looks associated with lower churn even among comparably-tenured customers, but the true causal share of that remaining gap cannot be established without a randomized test (part (a) above).
