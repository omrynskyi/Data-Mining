# Funnel Analysis Report — Telco Service Adoption Funnel

## Overall funnel

=================================================================
  SERVICE ADOPTION FUNNEL
=================================================================
  Step                      Users   Step Conv   Overall    Drop-off
  -------------------------------------------------------------
  Has phone                 5,075      100.0%    100.0%           —
  + Has internet            3,861       76.1%     76.1%  -1,214 (23.9%)
  + >=1 add-on              3,381       87.6%     66.6%  -480 (12.4%)
  + >=3 add-ons             1,993       59.0%     39.3%  -1,388 (41.0%)
  + Support add-on          1,179       59.2%     23.2%  -814 (40.8%)
  -------------------------------------------------------------
  Overall funnel conversion: 23.2%

  HIGHEST IMPACT DROP-OFF:
  → + >=3 add-ons: lost 1,388 users (41.0% of prior step)
  This is the best place to focus optimisation effort.
=================================================================

| Step | Users | Step Conv % | Overall Conv % | Churn rate % |
|---|---|---|---|---|
| Has phone | 5,075 | 100.0% | 100.0% | 26.80% |
| + Has internet | 3,861 | 76.1% | 76.1% | 32.94% |
| + >=1 add-on | 3,381 | 87.6% | 66.6% | 30.14% |
| + >=3 add-ons | 1,993 | 59.0% | 39.3% | 21.88% |
| + Support add-on | 1,179 | 59.2% | 23.2% | 14.25% |

Baseline churn rate (all customers): **26.54%**

Churn rate RISES as customers move deeper into the funnel through step 2 (adding internet), then FALLS steadily as they accumulate add-ons and support — i.e. add-on-rich, internet+support bundles are associated with materially lower churn than the base phone-or-bare-internet population, consistent with add-ons and support acting as retention levers (or as a marker of more engaged/price-tolerant customers).

## Segmented by contract type

### Month-to-month (n=3,102)

| Step | Users | Step Conv % | Overall Conv % | Churn rate % |
|---|---|---|---|---|
| Has phone | 2,797 | 100.0% | 100.0% | 43.12% |
| + Has internet | 2,375 | 84.9% | 84.9% | 47.54% |
| + >=1 add-on | 1,910 | 80.4% | 68.3% | 45.92% |
| + >=3 add-ons | 742 | 38.9% | 26.5% | 41.78% |
| + Support add-on | 305 | 41.1% | 10.9% | 30.49% |

### One year (n=1,173)

| Step | Users | Step Conv % | Overall Conv % | Churn rate % |
|---|---|---|---|---|
| Has phone | 1,053 | 100.0% | 100.0% | 11.21% |
| + Has internet | 768 | 72.9% | 72.9% | 14.58% |
| + >=1 add-on | 755 | 98.3% | 71.7% | 14.70% |
| + >=3 add-ons | 584 | 77.3% | 55.5% | 16.61% |
| + Support add-on | 340 | 58.2% | 32.3% | 16.18% |

### Two year (n=1,359)

| Step | Users | Step Conv % | Overall Conv % | Churn rate % |
|---|---|---|---|---|
| Has phone | 1,225 | 100.0% | 100.0% | 2.94% |
| + Has internet | 718 | 58.6% | 58.6% | 4.32% |
| + >=1 add-on | 716 | 99.7% | 58.5% | 4.33% |
| + >=3 add-ons | 667 | 93.2% | 54.5% | 4.35% |
| + Support add-on | 534 | 80.1% | 43.6% | 3.75% |

**Segment comparison**: Month-to-month customers have both the lowest overall funnel conversion to the fully-loaded bundle (step 5) and the highest churn rate at every stage — the funnel and the churn-driver analysis point at the same lever: contract length, not service depth alone, is the dominant retention factor (see `p3_root_cause_investigation.py` and `p3_ab_test_analysis.py` for the quantified Contract effect).
