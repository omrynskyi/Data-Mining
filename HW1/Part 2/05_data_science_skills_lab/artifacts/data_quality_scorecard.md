# Data Quality Scorecard: Telco-Customer-Churn.csv

**Assessed by:** Claude (phase2-data-agent)  
**Table / dataset:** `data/Telco-Customer-Churn.csv`  
**Pipeline / source:** Kaggle blastchar/telco-customer-churn, static snapshot extract  
**Assessment scope:** full table, 7,043 rows

---

## Quality Dimension Scores

| Dimension | Weight | Score (0-10) | Weighted | Key Issues |
|---|---|---|---|---|
| Completeness | 20% | 10.00 | 2.00 | none |
| Accuracy | 20% | 10.00 | 2.00 | none |
| Consistency | 20% | 10.00 | 2.00 | none |
| Timeliness | 15% | N/A | N/A | none |
| Uniqueness | 15% | 10.00 | 1.50 | none |
| Validity | 10% | 10.00 | 1.00 | none |
| **Overall** | **100%** |  | **10.00/10** |  |

**Overall verdict:** PASS (19 PASS / 0 FAIL / 2 N/A of 21 checks)

---

## All Checks Performed

| Dimension | Check | Script | Result | Rows affected | Detail |
|---|---|---|---|---|---|
| Completeness | TotalCharges null rate <= 1% | null_counter.py | PASS | 11 | 0.156% null (11 rows) — all at tenure==0 (see business rule below) |
| Completeness | No unexpected nulls outside TotalCharges | null_counter.py | PASS | 0 | All other 20 columns are 100% non-null. |
| Uniqueness | customerID is a unique primary key | duplicate_finder.py | PASS | 0 | 0 duplicate customerIDs, 0 full-row duplicates. |
| Consistency | Referential integrity (referential_integrity.py) | referential_integrity.py (skipped) | N/A | 0 | This is a single denormalized extract with no separate parent/child tables shipped — no FK to validate. See schema-mapper for the inferred normalized model where FK checks would apply. |
| Validity | tenure respects business rule {'min': 0, 'max': 72} | value_range_validator.py | PASS | 0 | within defined range/set |
| Validity | MonthlyCharges respects business rule {'min': 0} | value_range_validator.py | PASS | 0 | within defined range/set |
| Validity | TotalCharges respects business rule {'min': 0} | value_range_validator.py | PASS | 0 | within defined range/set |
| Validity | SeniorCitizen respects business rule {'allowed': [0, 1]} | value_range_validator.py | PASS | 0 | within defined range/set |
| Validity | gender respects business rule {'allowed': ['Male', 'Female']} | value_range_validator.py | PASS | 0 | within defined range/set |
| Validity | Churn respects business rule {'allowed': ['Yes', 'No']} | value_range_validator.py | PASS | 0 | within defined range/set |
| Validity | Contract respects business rule {'allowed': ['Month-to-month', 'One year', 'Two year']} | value_range_validator.py | PASS | 0 | within defined range/set |
| Validity | InternetService respects business rule {'allowed': ['DSL', 'Fiber optic', 'No']} | value_range_validator.py | PASS | 0 | within defined range/set |
| Validity | PaymentMethod respects business rule {'allowed': ['Electronic check', 'Mailed check', 'Bank transfer (automatic)', 'Credit card (automatic)']} | value_range_validator.py | PASS | 0 | within defined range/set |
| Consistency | TotalCharges null implies tenure==0 (never-billed new customer) | custom (pandas) | PASS | 0 | all 11 nulls are tenure==0 customers |
| Consistency | tenure==0 implies TotalCharges is null (no charges billed yet) | custom (pandas) | PASS | 0 | all tenure==0 rows have null TotalCharges |
| Consistency | PhoneService=='No' implies MultipleLines=='No phone service' | custom (pandas) | PASS | 0 | logic holds for all rows |
| Consistency | PhoneService=='Yes' implies MultipleLines != 'No phone service' | custom (pandas) | PASS | 0 | logic holds for all rows |
| Consistency | InternetService=='No' implies all 6 add-on columns=='No internet service' | custom (pandas) | PASS | 0 | logic holds for all rows and all 6 add-on columns |
| Consistency | InternetService != 'No' implies add-ons never 'No internet service' | custom (pandas) | PASS | 0 | logic holds for all rows |
| Accuracy | TotalCharges within 25% of tenure*MonthlyCharges for >=99% of billed rows | custom (pandas) | PASS | 28 | median abs pct error 2.0%; 28/7032 rows (0.4%) exceed 25% band, concentrated in low-tenure (partial first/last month billing) customers — expected, not a data error. |
| Timeliness | Freshness (freshness_check.py) | freshness_check.py (skipped) | N/A | 0 | Static Kaggle snapshot extract with no timestamp/updated_at column — freshness SLA is not applicable to this dataset. |

---

## Sign-off

**Approved for use in:** EDA, feature engineering, and modeling for churn prediction — with the caveat that TotalCharges nulls (11 rows, tenure==0) must be handled explicitly (impute 0 or drop) before modeling, and referential-integrity / freshness checks are N/A for this static single-table extract.
