---
skill: time-series-analysis
pack: nimrodfisher/data-analytics-skills
crisp_dm_phase: 3 - Data Preparation
artifacts:
  - artifacts/time_series_report.md
  - artifacts/ts_forecast.json
  - artifacts/ts_active_customers_series.csv
  - artifacts/ts_hazard_by_tenure_month.csv
  - reports/figures/ts_decomposition.png
  - reports/figures/ts_hazard_by_tenure.png
  - reports/figures/ts_forecast.png
---

# time-series-analysis

## What the skill prescribes

Load and inspect the series → ADF stationarity test → decompose trend/seasonal/residual and
measure component strength → detect anomalies (|z| ≥ 2.5-3 vs rolling median) → fit ARIMA (or
moving average), validate on 80/20 holdout with MAPE → report with forecast + 95% CI.

## Applied to Telco churn — two reconstructed series, assumption stated up front

No event log exists, so `src/p3_time_series_analysis.py` builds two derived series and states
the reconstruction assumption in the module docstring: (1) `active_customers` by calendar month
(join month back-calculated as `snapshot - tenure`, exact for censored/active customers, an
approximation for churned ones — same caveat as cohort-analysis); (2) `hazard_by_tenure_month`,
indexed by months-since-signup (lifecycle axis), used specifically for the early-tenure spike
test.

**ADF test** (`active_customers`, 73 months): statistic 2.098, p=0.9988 — non-stationary, as
expected for a cumulative-growth series.

**Decomposition** (additive, period=12): trend strength **0.994**, seasonal strength **0.097**
(weak) — growth is dominated by trend (net signup accumulation), not calendar seasonality.

**Anomaly detection**: 2 points flagged (|z|>3, final 2 months) — but flagged and explicitly
caveated as a **reconstruction/boundary artifact**: `active_customers` is monotonically
non-decreasing by construction and the centered rolling median loses right-side context at the
series edge, mechanically inflating the residual there. Not treated as a real anomaly.

**Early-tenure hazard spike test** — run twice to show a power pitfall: the naive test (12
monthly hazard rates vs 61, treated as independent samples) is underpowered (Welch's t=1.864,
p=0.089, NOT significant). The correctly-powered test pools person-month exposure directly: 790
events / 55,070 person-months (months 0-11, rate 1.43%) vs 705 events / 127,951 person-months
(months 12+, rate 0.55%) — two-proportion z-test **z=19.26, p=1.15e-82**, decisively significant,
confirming the well-known early-tenure churn spike once tested at the right unit of analysis.

**Forecast**: ARIMA(1,1,1), 80/20 holdout (15 held-out months) — **MAPE 3.83%**. 6-month forecast
(refit on full series) projects active customers rising from ~5,634 to ~6,578 by month +6, with
95% CI widening from ±100 to ±380.

## Outputs produced

- `artifacts/time_series_report.md` — full ADF/decomposition/anomaly/hazard/forecast report.
- `artifacts/ts_forecast.json` — all numeric results (MAPE, ADF p, strengths, hazard rates,
  6-month forecast).
- `artifacts/ts_active_customers_series.csv`, `ts_hazard_by_tenure_month.csv` — the two series.
- `reports/figures/ts_decomposition.png`, `ts_hazard_by_tenure.png`, `ts_forecast.png`.
