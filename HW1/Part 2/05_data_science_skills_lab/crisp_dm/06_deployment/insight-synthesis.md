---
skill: insight-synthesis
pack: nimrodfisher/data-analytics-skills
crisp_dm_phase: 6 - Deployment
artifacts:
  - artifacts/business_metrics.json
  - artifacts/root_cause_investigation_report.md
  - artifacts/funnel_analysis_report.md
  - artifacts/segmentation_report.md
  - artifacts/exploratory_data_analysis/cramers_v_categorical_vs_target.csv
---

## What the skill prescribes

Six-step process: (1) list every statistically meaningful finding as a plain factual
statement, without interpretation; (2) run each finding through **So What → Why → Now
What**; (3) attach a quantified business-impact estimate to each — "an insight without a
number is an observation"; (4) score each insight on impact x confidence x actionability
(1-3 scale each) and lead with the ones that score high on all three; (5) group related
insights, and explicitly surface contradictions rather than hiding them; (6) ship the top
3-5 as an insight brief (`assets/insight_brief_template.md`), not a dump of every finding.
The skill is explicit that a **finding** ("Fiber churn is 41.89%") is not yet an
**insight** ("Fiber churn is 41.89% because of a within-segment effect independent of
contract mix, worth ~$X/mo if fixed, and the fix is Y").

## Applied to Telco churn

Findings across Phases 1-3 were run through So What / Why / Now What and scored on the
skill's impact x confidence x actionability rubric (1-3 each, max 9). Five insights scored
7-9 and are presented below in priority order; lower-scoring findings (e.g. the payment-method
mix shift within Fiber, the early-tenure hazard spike) are documented in their source phase
reports but cut from this brief per the skill's own guidance not to dilute the signal.

### Governing insight

> **Churn at Telco is not one problem but three compounding ones — contract length, Fiber
> service, and shallow service adoption — and they stack on the same customers: the
> highest-exposure segment (43.3% of the base) is disproportionately month-to-month,
> Fiber-heavy, and add-on-poor, carrying $77,946/mo of MRR at risk in a single cluster.**

### 1. Contract length is the single largest, most actionable churn lever

**Finding:** Contract has the strongest association with churn of any feature measured
(Cramér's V = 0.411, full dataset). Month-to-month customers churn at 42.71%, one-year at
11.27%, two-year at 2.83% (n=7,043).
**So what:** A ~15x churn-rate spread sits inside one categorical variable Telco already
controls contractually (via pricing/incentive design), not one it has to infer from noisy
behavioral signals.
**Why:** Partly self-selection (price-sensitive, less-committed customers pick month-to-month)
and partly a real switching-cost/lock-in mechanism — the tenure-adjusted A/B analysis (`03_data_preparation/ab-test-analysis.md`) shows the gap shrinks from +39.88pp to +36.09pp
after controlling for tenure, but a large gap survives within every tenure stratum.
**Now what:** Design and power a real contract-upgrade incentive test on month-to-month
customers (spec already built: 8pp MDE is powerable today at 607/arm on the M2M+Fiber
subpopulation; 5pp needs 1,552/arm — see `03_data_preparation/ab-test-analysis.md`). Do not
ship a blanket "convert everyone to a 2-year contract" push on the *unadjusted* 93% relative
lift — that number is confounded and would overstate the causal effect.
**Confidence:** High for the association; Medium for the causal magnitude (observational data;
a real experiment is required before sizing ROI precisely).
**Impact x Confidence x Actionability:** 3 x 2 x 3 = 8.

### 2. Fiber optic churn is a real, quantified, mostly-service-level problem — not a mix artifact

**Finding:** Fiber optic customers churn at 41.89% vs 14.49% for non-Fiber (full dataset,
z=25.85, p≈2.4e-147) — a 2.9x gap. Decomposition (train split, `03_data_preparation/root-cause-investigation.md`)
attributes 78% of the gap to a **within-segment rate effect** (Fiber churns more even at
matched contract type) and only 22% to Fiber customers skewing toward month-to-month.
**So what:** The instinct to blame this entirely on "Fiber customers are disproportionately
month-to-month" is wrong for 78% of the gap. Something about the Fiber product or its price
($91.67 avg/mo vs $43.86 for non-Fiber, per the root-cause report) is driving churn on its own.
**Why:** Most likely price sensitivity and/or service-quality complaints; the dataset has no
NPS or support-ticket field to distinguish the two directly (a documented data gap).
Electronic check is the single largest contributor to the *count* of churned Fiber customers
(+85.2% of the churned-count gap in the drill-down), suggesting a correlated low-commitment
payment-method + Fiber population.
**Now what:** Prioritize retention spend on month-to-month + Fiber customers first (the
compounded highest-risk cell); commission a Fiber-specific price/quality survey since this
analysis cannot separate the two causes from billing data alone.
**Confidence:** High that the effect is real and large; Medium on the root cause (price vs.
quality) pending qualitative data Telco does not currently collect.
**Impact x Confidence x Actionability:** 3 x 2 x 2 = 7.

### 3. The churners are the higher-value customers — revenue churn (30.5%) outpaces logo churn (26.5%)

**Finding:** 26.537% of customers churned, but they represented 30.503% of MRR
($139,130.85/mo of $456,116.60/mo). Churned customers average $74.44/mo vs $61.27/mo for
active customers.
**So what:** A model or dashboard optimized purely for logo-churn accuracy will systematically
under-weight the customers whose loss hurts revenue the most. Retention spend allocated per-customer
rather than per-revenue-at-risk is misallocated.
**Why:** Higher MonthlyCharges correlates with Fiber + more add-ons (point-biserial r=+0.198
between MonthlyCharges and churn), and Fiber is itself the higher-churn product — the
revenue-weighting effect and the Fiber effect (insight #2) share a common driver.
**Now what:** Any churn-risk score used for retention targeting should be re-ranked by
`P(churn) x MonthlyCharges` (expected MRR at risk), not P(churn) alone — this is a one-line
change to a scoring query with an outsized effect on which customers get contacted first.
**Confidence:** High — this is a direct arithmetic fact from billing data, not a modeled estimate.
**Impact x Confidence x Actionability:** 2 x 3 x 3 = 8.

### 4. Add-ons and support are protective, not just correlated with commitment — the funnel shows churn falling as customers go deeper

**Finding:** Churn rate by funnel stage: has-phone 26.71% -> +internet 32.80% -> +≥1 add-on
29.82% -> +≥3 add-ons 21.52% -> +support add-on 14.01% (n=6,361 -> 1,463; see
`03_data_preparation/funnel-analysis.md`).
**So what:** Adding internet service alone *raises* churn risk (26.71% -> 32.80%), but
customers who go on to adopt add-ons and support see churn fall to roughly half the internet-only
rate. The dangerous population is internet subscribers with shallow add-on adoption, not
internet subscribers as a whole.
**Why:** Plausibly a mix of genuine product stickiness (more services = more switching cost)
and selection (customers who buy support add-ons are already more engaged/price-tolerant) —
this analysis cannot cleanly separate the two without an experiment.
**Now what:** Target internet-only and low-add-on customers (the 3,861 -> 1,993 drop-off,
41.0% of the prior step) with an add-on/support-bundle offer as a retention play, distinct from
the contract-length play in insight #1.
**Confidence:** Medium — directionally strong and large-sample, but selection vs. causation is
unresolved (same caveat as the skill's own note on cohort-style funnel reads).
**Impact x Confidence x Actionability:** 2 x 2 x 3 = 7.

### 5. One segment concentrates nearly a third of all revenue at risk

**Finding:** The k=3 unsupervised segmentation's cluster 1 ("new, mid-ARPU, month-to-month-heavy")
holds 2,439 customers (43.3% of the base), churns at 45.51% (churn index 172 vs. population),
and carries $77,946/mo of MRR at risk out of $109,353/mo total MRR at risk across the rule-based
value x risk grid (`03_data_preparation/segmentation-analysis.md`) — roughly 71% of all
identified at-risk MRR sits in this one group.
**So what:** Retention capacity is finite; this is the ranked target list, not a hypothesis to
re-derive per campaign.
**Why:** This cluster is the intersection of insights #1, #2, and #4 — new tenure, mostly
month-to-month, low add-on adoption — it is not a new driver, it is where the other three
compound.
**Now what:** Route the first wave of any retention campaign (contract-upgrade offer,
add-on bundle, or both) to this cluster before broader rollout; use `artifacts/segments.csv`
for the customer-level target list.
**Confidence:** High for the segment's existence and size (k=3 chosen over the higher-silhouette
k=2 specifically because it is more actionable — see `analysis-assumptions-log.md`); Medium
for whether cluster membership itself (vs. its component features) is the right targeting key.
**Impact x Confidence x Actionability:** 3 x 3 x 3 = 9.

---

## Negative findings (equally important — they kill wasted work)

- **gender has no association with churn** (Cramér's V = 0.008 on the full dataset, 0.000 on
  the train split, p=0.89). Any hypothesis or campaign segmentation built on a gender-based
  churn story should be dropped immediately — there is nothing there.
- **PhoneService has no meaningful association with churn** (Cramér's V = 0.011-0.012,
  p=0.20 on train). Phone-service upsell/downsell is not a churn lever; do not spend
  retention budget testing it as one.

These two null results matter as much as the positive ones: they stop two plausible-sounding
but empty lines of investigation (demographic targeting, phone-service bundling) before any
budget is spent validating them.

## What we don't know

- **The causal magnitude of the contract-length effect.** Only a randomized test (spec in
  `03_data_preparation/ab-test-analysis.md`) can replace "36.09pp tenure-adjusted association"
  with a defensible causal number.
- **Whether Fiber's within-segment churn effect is price or quality-driven** — the dataset has
  no complaint/NPS field to distinguish them (see insight #2).
- **The defensible LTV figure and therefore the precise dollar ceiling on retention spend** —
  Phase 5 is resolving a conflict between a hazard-based ($7,899.96) and tenure-based empirical
  ($2,283.30) estimate; see `impact-quantification.md` for how this synthesis handles it.

## Prioritisation rationale

Insights #1 and #5 scored highest (8 and 9) because they combine large, well-measured effects
with a direct, immediately actionable lever (contract offers, targeted campaign list). Insight
#3 (revenue-weighted targeting) is a one-line scoring change with outsized leverage, hence its
high score despite modest "impact" magnitude on its own. Insight #2 (Fiber) and #4 (funnel)
score 7 — real and large, but the recommended action is one step removed (a survey, a bundle
design) rather than a direct campaign. Several additional statistically valid findings
(payment-method mix inside Fiber, the 2.2x early-tenure hazard spike, `TotalCharges`
redundancy with `tenure x MonthlyCharges`) are documented in their source phase reports but
omitted here as lower-priority per the skill's cut-for-signal guidance.

## Recommended next steps

| Action | Priority | Owner | By |
|---|---|---|---|
| Route retention offers to segmentation cluster 1 (2,439 customers, $77,946/mo at risk) | High | Retention/CS | Immediate |
| Launch the powered contract-upgrade A/B test on M2M+Fiber (607/arm minimum) | High | Growth/Experimentation | Next quarter |
| Re-rank any churn-risk score by P(churn) x MonthlyCharges, not P(churn) alone | High | Data/Analytics | This sprint |
| Commission qualitative research (survey/NPS) on Fiber price vs. quality perception | Medium | Product/CX | Next quarter |
| Design an add-on/support bundle offer for internet-only, low-add-on customers | Medium | Product Marketing | Next quarter |

## Outputs produced

- This insight brief (`insight-synthesis.md`), following `assets/insight_brief_template.md`
- Feeds directly into `impact-quantification.md` (sizing) and `executive-summary-generator.md` /
  `data-narrative-builder.md` (delivery formats) for the same underlying insights
