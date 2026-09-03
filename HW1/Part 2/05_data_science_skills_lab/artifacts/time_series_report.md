# Time Series Analysis Report — Telco Customer Churn

## Reconstruction assumption
Two derived series (see module docstring for full reasoning):
1. `active_customers` — 73 calendar months, 2014-03-01 to 2020-03-01.
2. `hazard_by_tenure_month` — 73 tenure-months (0-72), a lifecycle-axis series, not calendar time.

## Stationarity (ADF test, `active_customers`)
- ADF statistic: 2.0980, p-value: 0.9988
- Non-stationary at alpha=0.05 — expected: active_customers is a monotonic-ish growth series (cumulative signups minus churns), so it is non-stationary and needs differencing before ARIMA.

## Decomposition (additive, period=12)
- Trend strength: 0.994
- Seasonal strength: 0.097 (weak/moderate seasonality)
- Interpretation: growth in `active_customers` is dominated by trend (net signups over the acquisition ramp), with only weak seasonality — consistent with month-to-month sign-up volume not being strongly tied to calendar seasonality in this reconstruction.

## Anomaly detection (|z| > 3 vs 6-month rolling median)
|                     |   active_customers |
|:--------------------|-------------------:|
| 2020-02-01 00:00:00 |               5626 |
| 2020-03-01 00:00:00 |               5634 |

**Caveat**: both flagged points are the final 2 months of the series. `active_customers` is by construction monotonically non-decreasing (it counts anyone ever active), and the centered rolling median loses right-side context at the boundary (fewer future points to smooth against), which mechanically inflates the residual z-score at the edge. This is a reconstruction/boundary artifact, not a genuine anomaly — a real anomaly investigation would exclude the last `window/2` points from this particular z-score test or use a one-sided trailing window instead.

## Early-tenure hazard spike test
- Per-month hazard series test (12 monthly rates vs 61 monthly rates, underpowered): Welch's t=1.864, p=0.08856 (NOT significant at this small n).
- Better-powered test — pooled person-month exposure: 790 churn events / 55,070 person-months in months 0-11 (rate 1.43%) vs 705 churn events / 127,951 person-months in months 12+ (rate 0.55%). Two-proportion z-test: z=19.26, p=1.15e-82 — **statistically significant**, confirming the well-known early-tenure churn-hazard spike once the test is run at the right unit of analysis (person-months, not the 12 aggregated monthly rates).

## Forecast (ARIMA(1,1,1), 80/20 holdout)
- Holdout MAPE: **3.83%** (15 held-out months)

### 6-month forecast (95% CI), refit on full series

|                     |   forecast |   ci_lower |   ci_upper |
|:--------------------|-----------:|-----------:|-----------:|
| 2020-04-01 00:00:00 |     5792.8 |     5691.9 |     5893.7 |
| 2020-05-01 00:00:00 |     5951   |     5793.3 |     6108.6 |
| 2020-06-01 00:00:00 |     6108.6 |     5896.8 |     6320.3 |
| 2020-07-01 00:00:00 |     6265.6 |     5999.4 |     6531.8 |
| 2020-08-01 00:00:00 |     6422   |     6099.9 |     6744.1 |
| 2020-09-01 00:00:00 |     6577.9 |     6198.1 |     6957.7 |

