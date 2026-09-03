## 2026-09-02T17:27:50Z

You are the Worker for Milestone 1: CRISP-DM & Clustering Pipeline.
Your Working Directory: /Users/oleg/Documents/Coding/SJSU/Data Mining/HW1/Part 2/03_customer_segmentation_clustering/.agents/m1_worker/
Workspace Root: /Users/oleg/Documents/Coding/SJSU/Data Mining/HW1/Part 2/03_customer_segmentation_clustering

Read ORIGINAL_REQUEST.md at: /Users/oleg/Documents/Coding/SJSU/Data Mining/HW1/Part 2/03_customer_segmentation_clustering/ORIGINAL_REQUEST.md
Read PROJECT.md at: /Users/oleg/Documents/Coding/SJSU/Data Mining/HW1/Part 2/03_customer_segmentation_clustering/PROJECT.md
Read Explorer 1 Plan at: /Users/oleg/Documents/Coding/SJSU/Data Mining/HW1/Part 2/03_customer_segmentation_clustering/.agents/m1_exp_1/m1_plan.md
Read Explorer 2 Metrics & Edge Cases at: /Users/oleg/Documents/Coding/SJSU/Data Mining/HW1/Part 2/03_customer_segmentation_clustering/.agents/m1_exp_2/edge_cases_and_metrics.md
Read Explorer 3 Downstream & CLI at: /Users/oleg/Documents/Coding/SJSU/Data Mining/HW1/Part 2/03_customer_segmentation_clustering/.agents/m1_exp_3/artifacts_integration.md

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Your Task:
Implement the complete, production-grade CRISP-DM Machine Learning Pipeline for the Mall Customer dataset:
1. `src/data_loader.py`: Acquire & parse Mall_Customers.csv (fetch/embedded fallback for 200 records), validate schema (CustomerID, Gender/Genre, Age, Annual Income, Spending Score), normalize columns. Save to `data/raw/Mall_Customers.csv`.
2. `src/data_understanding.py`: Business & data understanding exploration, descriptive statistics, outlier detection (IQR), demographic breakdown.
3. `src/data_preparation.py`: Preprocessing pipelines (StandardScaler, MinMaxScaler, RobustScaler, None), feature selection (2D: Income/Spending, 3D: Age/Income/Spending, All), categorical encoding.
4. `src/models.py`: Clustering algorithms:
   - K-Means with k-means++ initialization, n_init=10, random_state
   - DBSCAN with eps and min_samples
   - Agglomerative Clustering (Ward, Complete, Average)
   - PCA 2D & 3D projection transformations
5. `src/evaluation.py`: Silhouette Score, Davies-Bouldin Index, Calinski-Harabasz Index, Inertia/Elbow curve, dynamic persona profiling mapping 5 clusters to (Savers/Careful, Whales/Target, Spendthrifts/Impulsive, Budget/Sensible, Standard/Moderate).
6. `src/export.py`: Serializes models to `artifacts/models/*.joblib`, tabular results to `artifacts/customer_segments.csv`, metrics to `artifacts/metrics.json`, and full typed schema to `artifacts/pipeline_output.json` (also auto-synced to `dashboard/public/data/pipeline_output.json`).
7. `run_pipeline.py`: Top-level CLI entry point with argparse (`--data`, `--output-dir`, `--k`, `--scaler`, `--features`, `--algorithm`, `--export-dashboard`, `--random-state`), logging, error handling, exit code 0.
8. `requirements.txt`: Python package requirements.
9. Unit tests in `tests/test_data_loader.py` and `tests/test_pipeline.py`.
10. Execute `python run_pipeline.py` and verify all artifacts and metrics are produced. Execute `pytest tests/` and verify unit tests pass.
11. Write a complete handoff report to `/Users/oleg/Documents/Coding/SJSU/Data Mining/HW1/Part 2/03_customer_segmentation_clustering/.agents/m1_worker/handoff.md` with build & test verification outputs.
12. Send a message to orchestrator when completed.
