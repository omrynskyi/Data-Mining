# Data Cleaning Report — Telco Customer Churn
Train rows: 5,634  |  Test rows: 1,409
## 1. Deduplication
- Duplicate `customerID` in train: 0; test: 0. No action needed.
## 2. Missing `TotalCharges`
- Train: 8 nulls, test: 3 nulls (11 total, matches dataset_meta.json's 11).
- Every null has `tenure == 0`: these are brand-new customers billed for the first time this cycle, so no TotalCharges has accrued yet. This is missing-not-at-random but fully explained by an observed field (tenure).
- **Decision: impute 0** (domain-derived, not a train statistic) rather than drop or median-impute. Applied identically to train and test — no leakage risk since the constant does not depend on any split's statistics.
- Note: the `sklearn-pipelines` deliverable additionally keeps a `SimpleImputer(median)` as a structural safety net for any *other* numeric nulls introduced downstream; for this specific tenure==0 case the pipeline's custom transformer applies the same 0-fill before the ColumnTransformer runs, so the two artifacts agree.
## 3. Sentinel categories: "No internet service" / "No phone service"
- Affected columns (7): ['OnlineSecurity', 'OnlineBackup', 'DeviceProtection', 'TechSupport', 'StreamingTV', 'StreamingMovies', 'MultipleLines']
- `No internet service` rows (train): 1,214 (== count of `InternetService == 'No'`: 1,214, consistent).
- `No phone service` rows (train, MultipleLines): 559 (== count of `PhoneService == 'No'`: 559, consistent).
- **Decision: collapse to `'No'`.** The sentinel is 100% redundant with `InternetService`/`PhoneService` (verified equal counts above) — it encodes "doesn't have the base service" a second time inside every add-on column. Collapsing removes 6-7 duplicate one-hot columns per categorical without losing information, since `has_internet`/`has_phone` (built in feature-engineering) carries that fact once.
## 4. Dtype downcasting
- `SeniorCitizen`→int8, `tenure`→int16, `MonthlyCharges`/`TotalCharges`→float32, object categoricals→`category` dtype.
- Train memory: 5666.8 KB → 559.5 KB (90.1% reduction).
## 5. Outlier scan (IQR, train-only bounds)
| Column | Q1 | Q3 | IQR | Lower bound | Upper bound | # below | # above | % flagged |
|---|---|---|---|---|---|---|---|---|
| tenure | 9.00 | 55.00 | 46.00 | -60.00 | 124.00 | 0 | 0 | 0.00% |
| MonthlyCharges | 35.66 | 90.00 | 54.34 | -45.84 | 171.51 | 0 | 0 | 0.00% |
| TotalCharges | 402.98 | 3835.83 | 3432.85 | -4746.30 | 8985.10 | 0 | 0 | 0.00% |

**Decision: do NOT clip.** All three columns are bounded, business-meaningful quantities (tenure in [0,72] months = exactly the observation window; charges are real billed dollar amounts), not sensor noise or data-entry errors. IQR flags 0 points for tenure and TotalCharges (both right-skewed but within 1.5×IQR of the box) and 0 for MonthlyCharges — there are no extreme outliers, so the decision is moot for this dataset. Even if there were some, clipping tenure/charges would destroy exactly the long-tenure, high-spend customers whose behavior the model needs to learn, and — per the skill's own pitfall list — outliers that are real signal should be investigated, not deleted.
