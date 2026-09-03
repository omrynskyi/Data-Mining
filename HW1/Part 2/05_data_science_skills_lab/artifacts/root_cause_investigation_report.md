# Root Cause Investigation — Elevated Fiber Optic Churn

## 1. Validate the change

| InternetService   |   churn_rate |    n |
|:------------------|-------------:|-----:|
| DSL               |       0.1869 | 1937 |
| Fiber optic       |       0.4209 | 2483 |
| No                |       0.0725 | 1214 |

- Overall churn rate: 26.54%
- Fiber optic: 42.09% (n=2,483) vs Non-Fiber (DSL+No): 14.28% (n=3,151)
- Two-proportion z-test: z=23.47, p=8.66e-122 — far beyond the skill's "within ±1.5 std, close and stop" threshold; this is a real, large, statistically decisive gap (2.95x the non-fiber rate), not noise.

## 2-3. Decompose: segment mix vs within-segment rate (dimension = Contract)

| Contract       |   share_nonfiber |   share_fiber |   rate_nonfiber |   rate_fiber |   mix_contribution |   rate_contribution |
|:---------------|-----------------:|--------------:|----------------:|-------------:|-------------------:|--------------------:|
| Month-to-month |            0.443 |         0.687 |          0.2767 |       0.5507 |             0.0677 |              0.1883 |
| One year       |            0.234 |         0.176 |          0.0665 |       0.1858 |            -0.0039 |              0.0209 |
| Two year       |            0.323 |         0.137 |          0.0147 |       0.0706 |            -0.0027 |              0.0077 |

- Total rate gap to explain: Fiber - Non-Fiber = +27.81 pp.
- **Mix effect** (Fiber customers skew more month-to-month than non-fiber): +6.11 pp (22.0% of the gap).
- **Within-segment rate effect** (Fiber customers churn MORE than non-fiber customers even holding contract type fixed): +21.69 pp (78.0% of the gap).
- (mix + rate = +27.81 pp, reconciles to the total gap up to the standard interaction residual of this two-term decomposition.)

**Primary driver: within-segment rate effect (Fiber is worse even controlling for contract mix).**

## 4. Drill-down (shipped `drilldown_analyzer.py`) — churned-customer counts by PaymentMethod

```
======================================================================
  ROOT CAUSE DRILL-DOWN: CHURNED_CUSTOMERS
  Period A: Non-Fiber  →  Period B: Fiber
======================================================================

  DIMENSION: PAYMENTMETHOD
  Segment                              A             B        Change   Contribution
  ------------------------------------------------------------------
  Electronic check                   179           686          +507 [+283.2%]        +85.2%
  Bank transfer (automatic)           55           146           +91 [+165.4%]        +15.3%
  Mailed check                       155            93           -62 [-40.0%]        -10.4%
  Credit card (automatic)             61           120           +59 [+96.7%]         +9.9%

  TOP DRIVER: PaymentMethod = 'Electronic check'
  Drove +85.2% of total metric change.
  Investigate this segment first.
======================================================================
```

## 5. Hypotheses

- **H1 (price)**: Fiber customers pay more ($91.67 avg/mo vs $43.86) — ACCEPTED as a contributing factor, consistent with the within-segment rate effect above (price is not separately partialled out here, but the gap direction and magnitude are consistent with a price-sensitivity story; see `p3_ab_test_analysis.py` for a controlled comparison design).
- **H2 (payment method mix)**: Electronic check share is 51.1% among Fiber vs 19.8% among Non-Fiber — PARTIALLY ACCEPTED as a contributing mix factor (see drill-down table above; Electronic check is the single largest absolute contributor to the Fiber-vs-Non-Fiber churned-customer count gap).
- **H3 (data/measurement artifact)**: REJECTED. `InternetService` has no missing or malformed values, all three category counts are large and stable, and the elevated rate is confirmed by the z-test above at p << 0.001 — not a sparse-category fluke.

## Conclusion

The Fiber optic churn elevation (42.1% vs 14.3%) is real and decisively significant. Decomposition attributes 78% of the gap to a genuine within-segment effect (fiber customers churn more even at matched contract type) and 22% to contract-mix skew toward month-to-month. Recommended immediate action: prioritize retention offers for month-to-month Fiber customers (the compounded highest-risk cell — see `p3_segmentation_analysis.py`'s rule-based grid); short-term: investigate Fiber pricing/service-quality complaints as the likely within-segment driver; long-term: track whether Fiber's price premium vs perceived value is closing the gap over time (`p3_time_series_analysis.py`).
