# Executive Summary — Telco Customer Churn Retention Program

**Prepared for:** VP Customer Success / CRO · **Decision needed by:** next monthly retention
planning cycle · **Analysis basis:** 7,043-customer account snapshot, held-out-test-validated
risk model

## Situation

We are losing 26.5% of our customer base and 30.5% of monthly recurring revenue to voluntary
churn — disproportionately our higher-value accounts (churned customers average $74.44/mo vs
$61.27/mo for retained ones). $139,131/mo in MRR has already been lost; a further $136,447/mo
sits in active month-to-month accounts at immediate risk. This analysis built and validated a
churn-risk model, sized a targeted retention campaign against it, and quantified the return.

## Key findings (ranked by decision impact)

1. **Contract type is the single strongest, and most actionable, churn lever.** Month-to-month
   customers churn at 42.7% vs 2.8% for two-year contracts — a ~15x gap that is also the
   easiest lever to pull (a contract-upgrade incentive), unlike most of the other risk factors.
2. **A validated model can rank customers well enough to fund a profitable campaign.**
   PR-AUC 0.668 / ROC-AUC 0.848 on held-out data (not leakage-inflated — verified no feature
   exceeds 0.95 correlation with the target). At the recommended 50%-capacity threshold, the
   model achieves 46.5% precision — nearly double the 26.5% base rate.
3. **The recommended campaign nets an estimated $43K/cycle** (range $26K–$69K under realistic
   assumption uncertainty), contacting the top 705 highest-risk customers at $50/contact,
   assuming a 30% save rate — both assumptions explicitly flagged as estimates pending a real
   pilot, not observed facts.
4. **Fiber-optic internet customers churn 3x the rate of non-fiber (41.9% vs 14.5%)**, and the
   effect is mostly a real service-quality/price signal (78% within-segment), not just a mix
   shift (22%) — this is a product/pricing question, not only a retention-outreach one.
5. **Two plausible-sounding hypotheses are dead ends, and killing them now saves budget**:
   gender and phone-service status have **no measurable relationship with churn**
   (Cramér's V ≈ 0.01–0.02, not statistically distinguishable from zero). Do not fund
   segmentation or messaging built on either.

## Recommendations

| Action | Owner | Expected outcome | By when |
|---|---|---|---|
| Launch the risk-ranked retention campaign at 50% contact capacity (705 customers) | Retention team lead | ~98 saves, ~$43K net value per monthly cycle | Next monthly cycle |
| Pilot a contract-upgrade incentive specifically for month-to-month customers | Retention team lead | Directly targets the single largest churn driver (42.7% vs 2.8%) | Within pilot's 2-cycle test window |
| Investigate fiber-optic service/pricing complaints as a root cause, not just a retention target | Product/pricing owner | Addresses 78% within-segment effect, not just the 22% mix effect | Next quarterly product review |
| Run a true randomized A/B test on the contract-incentive offer before scaling it | Analytics team | Converts the current observational Contract-churn association into a causal, defensible number (design + sample sizes already computed) | Before company-wide rollout |
| Stand up production monitoring (input drift, prediction drift, monthly label-based re-validation) before scaling contact volume | ML/Data engineering | Prevents silent model degradation | Before scaling past pilot |

## Decision needed

**Approve the $35,250/cycle retention campaign budget** (705 contacts × $50) for the next
monthly cycle, with a monitoring checkpoint at 60 days to compare *actual* saves against the
budgeted 98.4 expected saves before committing to an ongoing run rate. Expected return: $43K net
value per cycle (conservative estimate — see `impact-quantification.md` for the range and why
it likely understates rather than overstates).

## What this analysis is *not*

The Contract-type churn gap is measured on **observational data, not a randomized experiment**
— it is a real, tenure-adjusted, still-large effect (unadjusted +39.9pp, tenure-adjusted
+36.1pp), but it should be treated as strong prior evidence for a pilot, not as proof a contract
incentive will fully close the gap. A properly powered A/B test design is already specified
(`crisp_dm/03_data_preparation/ab-test-analysis.md`) and should run before this is scaled beyond
a pilot.
