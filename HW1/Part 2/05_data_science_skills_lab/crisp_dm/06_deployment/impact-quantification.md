---
skill: impact-quantification
pack: nimrodfisher/data-analytics-skills
crisp_dm_phase: 6 - Deployment
artifacts: [artifacts/business_expected_value.json, artifacts/impact_confidence_range.json]
---

## What the skill prescribes

1. Classify the impact type — this is a **revenue-protection (retained MRR)** case, offset by a
   **cost** (campaign spend), i.e. a net-EV / ROI calculation, not a pure growth or pure
   cost-reduction case.
2. Gather real inputs: baseline metric, affected population, expected lift, time horizon,
   confidence.
3. Build a point estimate.
4. **Add uncertainty bounds — never deliver a single number without a range.**
5. Document every estimated (not measured) assumption and its sensitivity.
6. Package as a stakeholder-ready estimate with range, assumptions, confidence, and a
   recommended action.

## Applied to Telco churn

This does not recompute the sizing model from scratch — Phase 5 (`model-evaluation.md`,
`artifacts/business_expected_value.json`) already built the full EV table by capacity level, on
the model's held-out test set; this skill packages that existing, already-computed result into
a proper impact estimate, with the range step the earlier work did not yet add.

### Point estimate

At the model's chosen capacity (**50% of the customer base contacted**, matching
`final_metrics.json`'s `chosen_threshold_capacity_pct`), the EV table gives:

| | |
|---|---|
| Customers contacted | 705 |
| True churners among them (precision@50%) | 46.5% → ~328 |
| Expected saves (at 30% assumed save rate) | 98.4 |
| Campaign cost ($50/contact) | $35,250 |
| Revenue preserved (12-month Month-to-month ARPU basis) | $78,405 |
| **Net expected value** | **$43,155** |
| ROI | 2.22x |

This is the single best net-EV point across every capacity level the table checked (5% through
100%) — net EV rises from $10,553 at 5% capacity to a peak near $43,155 around 50%, then falls
to $18,951 at 100% capacity as precision degrades toward the 26.5% base rate and the campaign
starts spending $50 on customers who were never going to churn. **Recommended action: run the
campaign at ~50% capacity**, not higher — the marginal customers beyond that point cost more to
contact than the expected revenue they protect.

### Uncertainty bounds — added here, not skipped

The point estimate rests on two **assumptions, not observed data**: $50/contact offer cost and
a 30% save rate. Rather than present $43,155 as if it were exact, `confidence_interval.py`
(run for real, not by hand) was applied at two confidence presets:

| Confidence | Range | Why this preset |
|---|---|---|
| **Medium (recommended reading)** | **$26K – $69K** | ±40/60% — a repeatable retention-offer program with an unvalidated save rate is the textbook medium-confidence case: the cost is knowable in advance, but the save rate is an industry-typical assumption, not measured from this data (no historical campaign exists in this dataset to calibrate against) |
| Low (conservative floor) | $13K – $108K | −70/+150% — if the save rate or offer cost assumption is badly wrong |

**Sensitivity, stated plainly**: net EV is roughly linear in save rate (95% saves scale to
~$40K, not zero and not $100K) but is far more sensitive to the LTV/value-of-a-save figure used
— because Phase 5 already rejected the hazard-based LTV ($7,899.96) as survivorship-biased and
used the conservative 12-month-ARPU basis ($796.80/save) instead, this estimate is itself
**already conservative** relative to using either LTV number directly. Recomputing net EV at
50% capacity with the tenure-based-LTV upper-sensitivity value ($2,283.30/save, also reported in
`business_expected_value.json`) gives $118,890 net EV — meaning the $43,155 primary figure is
closer to a floor than a ceiling, which matters for how a stakeholder should read the range
above: it likely understates rather than overstates.

### Assumptions documented (per the skill's step 5)

| Assumption | Value | Source | What would falsify it |
|---|---|---|---|
| Offer cost / contact | $50 | Typical telecom retention-offer order of magnitude; not observed in this dataset | An actual costed offer design from marketing |
| Save rate | 30% | Commonly cited 20–40% industry range; not observed | Results from a real retention campaign (the `ab-test-analysis` skill's future-test design is the way to measure this directly) |
| Value of a save | $796.80 (12mo Month-to-month ARPU) | Computed from real data, deliberately conservative vs. either LTV figure | A different decision horizon (e.g. 24mo) would roughly double this |
| Model precision @ 50% capacity | 46.5% | Measured on the real held-out test set (n=1,409) | Would degrade under production drift — see the `model-serving` monitoring plan |

## Outputs produced

- `artifacts/impact_confidence_range.json` — the two confidence-preset ranges, computed by the
  skill's own `confidence_interval.py`.
- Builds on (does not duplicate) `artifacts/business_expected_value.json` from Phase 5.
