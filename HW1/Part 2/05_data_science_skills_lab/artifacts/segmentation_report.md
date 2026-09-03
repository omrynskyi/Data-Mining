# Segmentation Analysis Report — Telco Customer Churn

## A. Rule-based segmentation — Value x Risk grid

| rule_segment             |   n |   share_pct |   arpu |   churn_rate_pct |   churn_index |   mrr_at_risk |
|:-------------------------|----:|------------:|-------:|-----------------:|--------------:|--------------:|
| High value / Medium risk | 716 |        12.7 |  95.91 |            43.72 |           165 |      30018.3  |
| Mid value / High risk    | 648 |        11.5 |  69.97 |            55.56 |           209 |      25188.2  |
| High value / High risk   | 299 |         5.3 |  92.46 |            76.92 |           290 |      21266.8  |
| High value / Low risk    | 863 |        15.3 | 100.56 |            12.05 |            45 |      10458.3  |
| Mid value / Medium risk  | 505 |         9   |  69.83 |            29.5  |           111 |      10404.5  |
| Low value / High risk    | 647 |        11.5 |  30.79 |            34.62 |           130 |       6897.33 |
| Mid value / Low risk     | 724 |        12.9 |  68.23 |             5.94 |            22 |       2934.04 |
| Low value / Medium risk  | 287 |         5.1 |  32.84 |            17.42 |            66 |       1642.08 |
| Low value / Low risk     | 945 |        16.8 |  24.73 |             2.33 |             9 |        543.97 |

- Total monthly recurring revenue (MRR) currently "at risk" (churn-rate-weighted, train sample): **$109,353/mo**.
- Highest single-segment exposure: **High value / Medium risk** — 716 customers (12.7% of base), 43.7% churn rate (index 165), $30,018/mo MRR at risk — the priority segment for retention spend.

## B. Unsupervised segmentation — K-means (elbow + silhouette)

| k | Inertia | Silhouette |
|---|---|---|
| 2 | 20,884 | 0.3369 |
| 3 | 16,139 | 0.3075 |
| 4 | 14,242 | 0.2811 |
| 5 | 12,243 | 0.2833 |
| 6 | 10,991 | 0.2903 |
| 7 | 9,971 | 0.2776 |
| 8 | 9,240 | 0.2785 |

- Global silhouette-maximizing k = **2** (silhouette 0.3369), but a 2-cluster split is too coarse to assign differentiated retention strategies (the skill's own process step 1 recommends 3-7 actionable segments).
- **Operating choice: k = 3** — the best silhouette score within the actionable 3-7 range (silhouette 0.3075, still above the skill's 0.3 validity bar). Elbow curve — see `reports/figures/segmentation_elbow_silhouette.png`.

|   cluster | label                                      |    n |   share_pct |   avg_tenure |   arpu |   avg_addons |   churn_rate_pct |   churn_index |   mrr_at_risk |
|----------:|:-------------------------------------------|-----:|------------:|-------------:|-------:|-------------:|-----------------:|--------------:|--------------:|
|         1 | new, mid-ARPU, M2M-heavy                   | 2439 |        43.3 |        14.5  |  70.22 |         1.69 |            45.51 |           172 |      77946    |
|         2 | long-tenure, high-ARPU, contract-committed | 1863 |        33.1 |        57.73 |  88.61 |         3.96 |            14.65 |            55 |      24190.5  |
|         0 | mid-tenure, low-ARPU, contract-committed   | 1332 |        23.6 |        30.11 |  22.12 |         0.07 |             8.41 |            32 |       2477.48 |

- Highest-exposure cluster: **cluster 1 (new, mid-ARPU, M2M-heavy)** — 2,439 customers, 45.5% churn (index 172), $77,946/mo MRR at risk.
- Total MRR at risk across all clusters: **$104,614/mo** (should match the rule-based total up to segmentation-scheme differences: $109,353/mo).
