# Feature Engineering Report — Telco Customer Churn
## Engineered features (9)
| Feature | dtype | Description |
|---|---|---|
| tenure_bucket | category | Lifecycle band from tenure (0-6mo ... 61mo+) |
| avg_monthly_spend | float64 | TotalCharges / tenure (fallback: MonthlyCharges if tenure==0) |
| spend_gap | float64 | avg_monthly_spend - MonthlyCharges (positive = price rose vs history) |
| num_addon_services | int64 | Count of the 6 add-on services subscribed (0-6) |
| has_internet | int64 | 1 if InternetService != 'No' |
| is_month_to_month | int64 | 1 if Contract == 'Month-to-month' |
| is_electronic_check | int64 | 1 if PaymentMethod == 'Electronic check' |
| charges_per_service | float64 | MonthlyCharges / count of active services |
| is_new_customer | int64 | 1 if tenure <= 3 months |

Sample stats (train, n=5,634):

|       |   avg_monthly_spend |   spend_gap |   num_addon_services |   charges_per_service |
|:------|--------------------:|------------:|---------------------:|----------------------:|
| count |             5634    |     5634    |              5634    |               5634    |
| mean  |               64.94 |        0.01 |                 2.06 |                 19.31 |
| std   |               30.22 |        2.6  |                 1.85 |                  6.08 |
| min   |               13.83 |      -19.13 |                 0    |                  8.65 |
| 25%   |               36.05 |       -1.13 |                 0    |                 14.86 |
| 50%   |               70.59 |        0    |                 2    |                 19.3  |
| 75%   |               90.46 |        1.18 |                 3    |                 22.4  |
| max   |              121.4  |       18.9  |                 6    |                 38.95 |

## Target encoding demo — `PaymentMethod x Contract` interaction (12 levels)
- Naive (fit on all rows incl. the row itself) univariate AUC of the encoded feature vs Churn: **0.7866**
- OOF (5-fold, excluding each row's own fold) univariate AUC: **0.7791**
- Inflation from leakage: **+0.0075** AUC points (+0.97% relative).

### Leakage stress test (target shuffled to pure noise)
- Naive encoding AUC on a column with NO real relationship to a (shuffled) target: **0.5216** (should be ~0.50; leakage manufactures apparent signal)
- OOF encoding AUC on the same shuffled target: **0.4917** (correctly stays near 0.50)
