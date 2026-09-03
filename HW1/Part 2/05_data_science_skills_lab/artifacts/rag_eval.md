# RAG Retrieval Evaluation — Telco Churn Project Docs

Hand-written eval set: 12 question -> expected-source-doc pairs, 
written from documents actually read in this session. A hit is 
doc-level: the retrieved chunk's source file equals the expected doc.

## Summary

| Retriever | MRR | Hit-rate@1 | Recall@3 | Recall@5 |
|---|---|---|---|---|
| sparse | 0.7361 | 0.6667 | 0.8333 | 0.8333 |
| dense | 0.6694 | 0.5833 | 0.75 | 0.8333 |
| hybrid | 0.7111 | 0.6667 | 0.75 | 0.8333 |

**Best by MRR: sparse** (0.7361)

## Per-question detail

| # | Question | Expected doc | sparse rank | dense rank | hybrid rank |
|---|---|---|---|---|---|
| 1 | What silhouette score did the k=3 customer segmentation achieve, and w… | `crisp_dm/03_data_preparation/segmentation-analysis.md` | None | None | None |
| 2 | Which step of the service-adoption funnel has the biggest absolute dro… | `crisp_dm/03_data_preparation/funnel-analysis.md` | 2 | 1 | 1 |
| 3 | What SHA-256 hash is the raw Telco CSV pinned to for reproducibility c… | `crisp_dm/04_modeling/reproducible-ml.md` | 1 | 1 | 1 |
| 4 | Which class-imbalance strategy was the cheapest leak-free first move a… | `crisp_dm/04_modeling/imbalanced-data.md` | 1 | 1 | 1 |
| 5 | What business rule links TotalCharges being null to the tenure column … | `crisp_dm/02_data_understanding/data-quality-audit.md` | 1 | 1 | 1 |
| 6 | How many tables does the reverse-engineered normalized schema for the … | `crisp_dm/02_data_understanding/schema-mapper.md` | 1 | 1 | 1 |
| 7 | What Optuna sampler was used for hyperparameter tuning and what metric… | `crisp_dm/04_modeling/hyperparameter-tuning.md` | 1 | 2 | 3 |
| 8 | Who is the primary audience for the retention risk dashboard and what … | `crisp_dm/06_deployment/dashboard-specification.md` | 1 | 1 | 1 |
| 9 | How is the ltv metric defined in the semantic model, and why can't LTV… | `artifacts/semantic_model_telco.yml` | 3 | 3 | 5 |
| 10 | What was the root business question the VP of Customer Retention actua… | `crisp_dm/01_business_understanding/stakeholder-requirements-gathering.md` | 1 | 5 | 1 |
| 11 | What two problems does the chart selection guidance say a 3D pie chart… | `crisp_dm/06_deployment/visualization-builder.md` | 1 | 1 | 1 |
| 12 | What is the grain of the Telco-Customer-Churn dataset and how many row… | `artifacts/data_catalog_telco.md` | None | None | None |
