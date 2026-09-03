# Telco-Customer-Churn

## Overview

**Name:** `data/Telco-Customer-Churn.csv`  
**Type:** flat file (CSV) — modeled as a table  
**Domain:** Customer / Subscription (Telecom)  
**Criticality:** critical  

**Description:**  
One row per residential telecom customer, capturing subscribed services, account/contract attributes, billing amounts, and whether the customer churned. Source: Kaggle blastchar/telco-customer-churn (IBM Telco Customer Churn sample dataset).

**Grain:** One row per customer (customerID), snapshot at time of extract.

---

## Ownership

- **Business Owner:** [simulated stakeholder input] VP of Customer Retention
- **Technical Owner:** [simulated stakeholder input] Data Science / Analytics team (this project)
- **Last reviewed:** 2026-09-02

---

## Schema

**Row Count (at extraction):** 7,043  
**Column Count:** 21  
**Extracted:** 2026-09-02T23:13:00.510401+00:00  
**Duplicate customerIDs:** 0

| Column | Dtype (raw) | Nullable | Null % | Cardinality | Example values | Business definition |
| --- | --- | --- | --- | --- | --- | --- |
| customerID | object | No (0.0%) | PK | 7043 | 7590-VHVEG, 5575-GNVDE, 3668-QPYBK, 7795-CFOCW, 9237-HQITU | Unique customer identifier assigned at account creation. Primary key. |
| gender | object | No (0.0%) | — | 2 | Female, Male | Customer's self-reported gender at signup (Male/Female, as captured by this legacy system). |
| SeniorCitizen | int64 | No (0.0%) | — | 2 | 0, 1 | Whether the account holder is 65+ (1) or not (0), self-reported at signup. |
| Partner | object | No (0.0%) | — | 2 | Yes, No | Whether the customer has a partner (spouse/domestic partner) on the account profile. |
| Dependents | object | No (0.0%) | — | 2 | No, Yes | Whether the customer has dependents (children/other dependents) on the account profile. |
| tenure | int64 | No (0.0%) | — | 73 | 1, 34, 2, 45, 8 | Number of months the customer has been with the company as of the snapshot date. Used as the acquisition-to-date clock (business framing: months since acquisition). |
| PhoneService | object | No (0.0%) | — | 2 | No, Yes | Whether the customer subscribes to the phone service line. |
| MultipleLines | object | No (0.0%) | — | 3 | No phone service, No, Yes | Whether the customer has multiple phone lines (No / Yes / No phone service). |
| InternetService | object | No (0.0%) | — | 3 | DSL, Fiber optic, No | Internet service technology subscribed to (DSL / Fiber optic / No internet service). |
| OnlineSecurity | object | No (0.0%) | — | 3 | No, Yes, No internet service | Whether the customer subscribes to the online security add-on (requires internet service). |
| OnlineBackup | object | No (0.0%) | — | 3 | Yes, No, No internet service | Whether the customer subscribes to the online backup add-on (requires internet service). |
| DeviceProtection | object | No (0.0%) | — | 3 | No, Yes, No internet service | Whether the customer subscribes to the device protection add-on (requires internet service). |
| TechSupport | object | No (0.0%) | — | 3 | No, Yes, No internet service | Whether the customer subscribes to the tech support add-on (requires internet service). |
| StreamingTV | object | No (0.0%) | — | 3 | No, Yes, No internet service | Whether the customer subscribes to the streaming TV add-on (requires internet service). |
| StreamingMovies | object | No (0.0%) | — | 3 | No, Yes, No internet service | Whether the customer subscribes to the streaming movies add-on (requires internet service). |
| Contract | object | No (0.0%) | — | 3 | Month-to-month, One year, Two year | Contract commitment term: Month-to-month, One year, or Two year. Primary churn-risk driver dimension. |
| PaperlessBilling | object | No (0.0%) | — | 2 | Yes, No | Whether the customer is enrolled in paperless billing (Yes/No). |
| PaymentMethod | object | No (0.0%) | — | 4 | Electronic check, Mailed check, Bank transfer (automatic), Credit card (automatic) | How the customer pays their bill (Electronic check, Mailed check, Bank transfer (automatic), Credit card (automatic)). |
| MonthlyCharges | float64 | No (0.0%) | — | 1585 | 29.85, 56.95, 53.85, 42.3, 70.7 | Current recurring monthly charge in USD - treated as the customer's MRR contribution (business framing). |
| TotalCharges | object | Yes (0.156%) | — | 6531 | 29.85, 1889.5, 108.15, 1840.75, 151.65 | Cumulative amount billed to the customer to date (USD). Approximately tenure x MonthlyCharges, with small deviations from mid-cycle rate changes; blank for 11 customers with tenure=0 (billed nothing yet). |
| Churn | object | No (0.0%) | — | 2 | No, Yes | Target label: whether the customer churned (voluntarily left) during the observation window (Yes/No). |

### Notes on individual columns

- **TotalCharges:** Ships as object dtype (blank strings for tenure=0 rows); 11 rows become null after pd.to_numeric coercion (see data/processed/dataset_meta.json).

---

## Relationships

**Primary key:** `customerID` (0 duplicates confirmed)

**Foreign keys:** none — single flat table.

---

## Data Quality

- **Completeness:** 100% for 20/21 columns; `TotalCharges` has 11 nulls (0.16%) after numeric coercion, all corresponding to `tenure == 0` (brand-new customers who have not yet been billed) — expected, not a defect.
- **Freshness:** static snapshot (one-time Kaggle download for this lab); no refresh schedule.
- **Known issues:** `TotalCharges` ships as `object` dtype due to blank-string placeholders and must be coerced with `pd.to_numeric(..., errors='coerce')` before numeric use (see `src/00_foundation.py`).

---

## Lineage

**Upstream sources:**
- Kaggle dataset export (static, one-time download for this lab); in production this would be the billing system + CRM.

**Downstream consumers:**
- CRISP-DM churn-prediction pipeline (this project, phases 2-6)
- Retention team ranked risk list (planned deliverable)

---

## Access & Governance

**Access level:** internal  
**Sensitivity:** PII (customerID is a pseudonymous key; gender, SeniorCitizen are demographic attributes) + billing/financial (MonthlyCharges, TotalCharges)  
**Compliance tags:** none applicable - public Kaggle sample; would be PII/financial in a real production telecom system  

**Access instructions:**  
Public Kaggle dataset — no access request needed for this lab. In a production system this would sit behind the standard customer-data access request process.

---

## Sample query

```python
import pandas as pd
df = pd.read_csv('data/Telco-Customer-Churn.csv')
df.head(10)
```

---

*Generated by `src/p1_data_catalog.py` on 2026-09-02T23:13:00.510401+00:00. Template: data-catalog-entry/assets/catalog_entry_template.md*