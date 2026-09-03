---
skill: segmentation-analysis
pack: nimrodfisher/data-analytics-skills
crisp_dm_phase: 3 - Data Preparation
artifacts:
  - artifacts/segments.csv
  - artifacts/segment_profile_rule_based.csv
  - artifacts/segment_profile_kmeans.csv
  - artifacts/segmentation_kmeans_selection.json
  - artifacts/segmentation_report.md
  - reports/figures/segmentation_elbow_silhouette.png
  - reports/figures/segmentation_value_risk_grid.png
---

# segmentation-analysis

## What the skill prescribes

Define the segmentation goal → select 3-7 variables → run segmentation (rule-based OR k-means
via `segmentation_runner.py`'s index-scoring idea) → profile each segment (size, churn, ARPU,
defining traits) → validate (silhouette > 0.3 for clustering) → map to strategy.

## Applied to Telco churn — both rule-based AND unsupervised, as required

### A. Rule-based: Value (MonthlyCharges tercile) x Risk (contract/tenure) grid

9 segments (3 value tiers × 3 risk tiers: High/Medium/Low risk from Contract type + tenure ≤ 12).
Total MRR "at risk" (churn-rate-weighted): **$109,353/mo**. Highest exposure: **High value /
Medium risk** (month-to-month, tenure > 12) — 716 customers (12.7% of base), 43.7% churn rate
(index 165 vs population), **$30,018/mo MRR at risk**.

### B. Unsupervised: K-means on scaled numeric + one-hot categorical features

Features: tenure, MonthlyCharges, TotalCharges, num_addon_services (scaled) + Contract,
InternetService, PaymentMethod (one-hot). Swept k=2..8:

| k | Inertia | Silhouette |
|---|---|---|
| 2 | 20,884 | **0.3369** (global max) |
| 3 | 16,139 | **0.3075** |
| 4 | 14,242 | 0.2811 |
| 5-8 | 9,240-12,243 | 0.2776-0.2903 |

The global silhouette maximum is k=2, but a 2-cluster split doesn't give the business enough
resolution to assign differentiated strategies (the skill's own process step 1 recommends 3-7
actionable segments) — so the **operating choice is k=3**, the best silhouette within that
actionable range (0.3075, still above the skill's 0.3 validity bar).

**3-cluster profile**:

| Cluster | Label | n | Share | Avg tenure | ARPU | Churn rate | Index | MRR at risk |
|---|---|---|---|---|---|---|---|---|
| 1 | new, mid-ARPU, M2M-heavy | 2,439 | 43.3% | 14.5mo | $70.22 | **45.5%** | 172 | **$77,946/mo** |
| 2 | long-tenure, high-ARPU, contract-committed | 1,863 | 33.1% | 57.7mo | $88.61 | 14.7% | 55 | $24,191/mo |
| 0 | mid-tenure, low-ARPU, contract-committed | 1,332 | 23.6% | 30.1mo | $22.12 | 8.4% | 32 | $2,477/mo |

Total MRR at risk across clusters: $104,614/mo (reconciles with the rule-based $109,353/mo up to
scheme differences). Cluster 1 — new, mid-spend, month-to-month-heavy customers — is the priority
segment, consistent with the rule-based grid's top exposure cell.

## Outputs produced

- `artifacts/segments.csv` — per-customer segment/cluster assignments.
- `artifacts/segment_profile_rule_based.csv`, `artifacts/segment_profile_kmeans.csv` — profile
  tables.
- `artifacts/segmentation_kmeans_selection.json` — full elbow/silhouette sweep + k decision.
- `reports/figures/segmentation_elbow_silhouette.png`, `segmentation_value_risk_grid.png`.
