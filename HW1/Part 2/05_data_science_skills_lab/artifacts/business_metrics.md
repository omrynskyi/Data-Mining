# Business Metrics — Telco Customer Churn

Computed from `data/Telco-Customer-Churn.csv` (n=7043), full population.
Source script: `src/p1_business_metrics.py`. Raw numbers: `artifacts/business_metrics.json`.

## Headline metrics

| Metric | Value |
|---|---|
| Customers (total / active / churned) | 7,043 / 5,174 / 1,869 |
| MRR (all customers) | $456,116.60 |
| MRR (active customers only) | $316,985.75 |
| ARR (run-rate, all customers) | $5,473,399.20 |
| ARPU (all customers) | $64.76 |
| ARPU (active customers only) | $61.27 |
| Logo churn rate (base) | 26.54% |
| Revenue churn rate (base) | 30.50% |
| Monthly churn rate (hazard, from customer-months) | 0.820%/month |
| LTV — churn-rate-based (ARPU / monthly churn) | $7,899.96 |
| LTV — tenure-based (mean TotalCharges) | $2,283.30 |
| Avg tenure (months) | 32.37 |
| Revenue at risk — realized (churned MRR) | $139,130.85 (30.50% of total MRR) |
| Revenue at risk — forward-looking (active Month-to-month MRR) | $136,447.05 (43.05% of active MRR) |

## ARPU by contract type

| Contract | ARPU | MRR contribution | Logo churn rate |
|---|---|---|---|
| Month-to-month | $66.40 | $257,294.15 | 42.71% |
| One year | $65.05 | $95,816.60 | 11.27% |
| Two year | $60.77 | $103,005.85 | 2.83% |

## Benchmark comparison

- **Monthly logo churn (0.82%/month):** SaaS "good" benchmark is
  typically <2-3%/month (`references/metric_definitions.md`). Telco's ~0.8%/month
  hazard rate is above the SaaS-good band, consistent with telecom being a higher-churn
  vertical than software subscriptions, and consistent with the 26.5%
  base (whole-tenure) churn rate.
- **LTV:CAC ratio:** cannot be graded — this dataset has no CAC / acquisition-spend field.
  Flagged as a data gap.
- **Revenue churn (30.50%):** exceeds logo churn rate (26.54%),
  meaning churned customers skew toward *higher*-than-average MonthlyCharges — churn is
  concentrated somewhat more in higher-value accounts, which increases urgency for the
  retention program.

## Data gaps (documented per business-metrics-calculator skill's definition-choice step)

- No CAC / acquisition spend field -> LTV:CAC and payback period cannot be computed.
- No gross-margin / COGS field -> LTV uses revenue, not gross-profit, basis.
- Single cross-sectional snapshot (no monthly ledger) -> MRR waterfall (new/expansion/contraction) and NRR cannot be computed as defined for a recurring SaaS ledger; monthly churn is approximated via customer-months.
