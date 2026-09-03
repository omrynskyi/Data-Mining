# Schema Comparison Report

## Direct Matches (same name, same type) (2)

| column | type |
| --- | --- |
| customerID | object |
| MonthlyCharges | float64 |

## Type Mismatches (same name, different type) (19)

| column | source_type | target_type |
| --- | --- | --- |
| gender | object | category |
| SeniorCitizen | int64 | int8 |
| Partner | object | int8 |
| Dependents | object | int8 |
| tenure | int64 | int16 |
| PhoneService | object | int8 |
| MultipleLines | object | category |
| InternetService | object | category |
| OnlineSecurity | object | category |
| OnlineBackup | object | category |
| DeviceProtection | object | category |
| TechSupport | object | category |
| StreamingTV | object | category |
| StreamingMovies | object | category |
| Contract | object | category |
| PaperlessBilling | object | int8 |
| PaymentMethod | object | category |
| TotalCharges | object | float64 |
| Churn | object | int8 |

## Unmapped Source Columns (in source, not in target) (0)

None.

## Target Columns With No Source (need derivation or default) (0)

None.

## Summary

- Direct matches: 2
- Type mismatches requiring a CAST: 19
- Source columns dropped or deferred: 0
- Target columns needing derivation: 0
