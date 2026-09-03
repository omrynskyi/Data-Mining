A telecom subscription business wants to reduce voluntary churn. The retention team
can act on a ranked risk list monthly — this is an operational, recurring decision
(not a one-off strategic call), so favor a fast, actionable, directionally-correct
output over an exhaustive one (see decision_maker_framework.md calibration).

Key metric definitions (computed for real in artifacts/business_metrics.json):
- MRR: sum of MonthlyCharges, treated as each customer's recurring subscription
  price / MRR contribution. All-customer MRR = $456,116.60/mo; active-only = $316,985.75/mo.
- ARPU: $64.76/mo all customers ($61.27 active-only); by contract: Month-to-month
  $66.40, One year $65.05, Two year $60.77.
- Logo churn rate (base, whole-tenure): 26.537% (matches data/processed/dataset_meta.json).
- Revenue churn rate (base): 30.503% — churn skews toward higher-MonthlyCharges accounts.
- Monthly churn hazard rate (empirical, from customer-months of tenure): 0.82%/month.
- LTV: churn-rate-based $7,899.96 (ARPU / monthly hazard, no margin data available);
  tenure-based empirical (mean TotalCharges) $2,283.30.
- Revenue at risk: $139,130.85 already realized (churned customers' MRR, 30.5% of
  total MRR); $136,447.05 forward-looking exposure (active Month-to-month MRR, the
  highest-churn segment, 43.05% of active MRR).
- tenure = months since acquisition. Churn = voluntary churn flag (Yes/No raw,
  0/1 processed).

Business context: mid-size residential telecom provider. Product lines: phone
service (+ multiple lines), internet service (DSL / Fiber optic / none) with six
internet-dependent add-ons, billing via 4 payment methods, and 3 contract terms
(Month-to-month / One year / Two year). Month-to-month customers churn at 42.71%
vs. 11.27% (One year) and 2.83% (Two year) — contract term is the strongest
observed churn-risk dimension so far (Phase 1, pre-model).
