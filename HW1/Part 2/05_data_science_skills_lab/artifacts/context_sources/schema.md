Full column-by-column data dictionary: artifacts/data_catalog_telco.md
(machine-readable: artifacts/data_catalog_telco.json). Semantic layer (entities,
dimensions, metrics): artifacts/semantic_model_telco.yml.

```
-- data/Telco-Customer-Churn.csv (7,043 rows x 21 cols; one row per customer)
customerID          object   PK, 0 duplicates
gender               object  Male / Female
SeniorCitizen         int64  0/1
Partner               object Yes/No
Dependents            object Yes/No
tenure                 int64 months since acquisition, range 0-72
PhoneService          object Yes/No
MultipleLines         object Yes / No / No phone service
InternetService       object DSL / Fiber optic / No
OnlineSecurity        object Yes / No / No internet service   -- + 5 more add-on cols
OnlineBackup          object Yes / No / No internet service      of the same shape:
DeviceProtection      object Yes / No / No internet service      TechSupport,
StreamingTV           object Yes / No / No internet service      StreamingTV,
StreamingMovies       object Yes / No / No internet service      StreamingMovies
Contract               object Month-to-month / One year / Two year
PaperlessBilling      object Yes/No
PaymentMethod          object Electronic check / Mailed check /
                               Bank transfer (automatic) / Credit card (automatic)
MonthlyCharges        float64 recurring monthly charge, USD (= MRR contribution)
TotalCharges           object cumulative billed to date, USD; ships as object
                               (blank strings) -> coerce with pd.to_numeric(); 11
                               nulls, all tenure==0 customers
Churn                  object Yes/No (target)
```

Processed / split (data/processed/, seed=42, stratified 80/20):
- train.csv (5,634 rows), test.csv (1,409 rows)
- Churn recoded to 0/1; TotalCharges coerced to numeric
- data/processed/dataset_meta.json carries the verified split stats
