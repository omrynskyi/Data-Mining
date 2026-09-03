- Use only data/Telco-Customer-Churn.csv and its processed train/test split —
  no external enrichment data is available for this lab.
- Respect the train/test split already made (data/processed/{train,test}.csv,
  seed=42, stratified on Churn) — do not re-split or leak test rows into training.
- TotalCharges must be coerced to numeric (11 blank-string rows -> null) before
  any numeric use; do not silently drop those rows without noting it.
- Do not treat this as a monthly SaaS ledger — it is a single cross-sectional
  snapshot. Any "monthly" rate (e.g. churn hazard) is an approximation and must
  be labeled as such, not presented as a directly observed monthly figure.
- Report churn probability, not a hard yes/no label, so the retention team can
  rank and threshold it themselves (aligns with "ranked risk list" requirement).
