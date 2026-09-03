# Customer Segmentation & Dashboard — Test Infrastructure Specification (TEST_INFRA)

## 1. Overview & Testing Philosophy

This document defines the comprehensive multi-tier test infrastructure for the **Customer Segmentation Clustering & React Data Science Dashboard** project. The test strategy guarantees strict adherence to the CRISP-DM framework, machine learning invariants, academic benchmark alignment via autoresearch, and frontend dashboard build and programmatic render integrity.

The test infrastructure is architected using a 5-tier testing methodology:
1. **Tier 1: Category-Partition & Interface Contract Tests**
2. **Tier 2: Boundary Value Analysis (BVA) & Edge Condition Tests**
3. **Tier 3: Pairwise Combinatorial & Algorithm Exploration Tests**
4. **Tier 4: Full Real-World End-to-End (E2E) Integration Scenarios**
5. **Tier 5: Adversarial, Resiliency & Integrity Hardening Tests**

---

## 2. Feature-to-Tier Traceability Matrix

| Feature ID | Feature Name | Tier 1 (Contracts) | Tier 2 (BVA) | Tier 3 (Pairwise) | Tier 4 (E2E) | Tier 5 (Adversarial) |
|---|---|---|---|---|---|---|
| **F1** | Dataset Acquisition & Ingestion | `T1_DATA_LOAD` | `T2_DATA_BVA` | `T3_DATA_COMBO` | `T4_E2E_PIPE` | `T5_CORRUPT_DATA` |
| **F2** | CRISP-DM Data Understanding | `T1_STATS_SCHEMA` | `T2_OUTLIER_BOUNDS` | `T3_DEMO_SEG` | `T4_E2E_PIPE` | `T5_MISSING_COLS` |
| **F3** | Data Prep & Feature Scaling | `T1_SCALER_TYPE` | `T2_SCALE_RANGE` | `T3_SCALER_FEAT` | `T4_E2E_PIPE` | `T5_ZERO_VAR` |
| **F4** | Multi-Algorithm Clustering | `T1_ALGO_EXEC` | `T2_K_BOUNDS` | `T3_ALGO_GRID` | `T4_E2E_PIPE` | `T5_DEGENERATE_CLUST` |
| **F5** | Cluster Evaluation Metrics | `T1_METRICS_SCHEMA`| `T2_METRICS_BOUNDS`| `T3_METRIC_COMP` | `T4_E2E_PIPE` | `T5_SINGLE_CLUSTER` |
| **F6** | Pipeline CLI Runner (`run_pipeline.py`) | `T1_CLI_ARGS` | `T2_CLI_DEFAULTS` | `T3_CLI_MODES` | `T4_E2E_PIPE` | `T5_CLI_BAD_ARGS` |
| **F7** | Dashboard Data Exporter | `T1_JSON_SCHEMA` | `T2_EXPORT_SIZE` | `T3_EXPORT_FORMAT`| `T4_E2E_PIPE` | `T5_SCHEMA_MUTATION` |
| **F8** | Benchmark Paper Alignment | `T1_PAPER_CITE` | `T2_TARGET_SCORES` | `T3_BENCH_MODELS` | `T4_E2E_AUTORES`| `T5_MISSING_CITE` |
| **F9** | Autoresearch Hill-Climbing | `T1_AUTORES_CLI` | `T2_ITER_BOUNDS` | `T3_HILL_TRAJ` | `T4_E2E_AUTORES`| `T5_LOCAL_MAXIMA` |
| **F10**| Optimization Log Generation | `T1_LOG_FORMAT` | `T2_LOG_STEPS` | `T3_LOG_DELTA` | `T4_E2E_AUTORES`| `T5_LOG_CORRUPTION` |
| **F11**| Dashboard Scaffolding | `T1_VITE_CONFIG` | `T2_PKG_DEPS` | `T3_TS_CONFIG` | `T4_E2E_DASH` | `T5_MISSING_DEPS` |
| **F12**| Dashboard UI Views | `T1_COMP_MOUNT` | `T2_EMPTY_STATE` | `T3_VIEW_SWITCH` | `T4_E2E_DASH` | `T5_INVALID_PAYLOAD`|
| **F13**| Dashboard Data Integration | `T1_DATA_HOOKS` | `T2_FALLBACK_DATA`| `T3_SYNC_STATE` | `T4_E2E_DASH` | `T5_UNPARSABLE_JSON`|
| **F14**| Build & Programmatic Tests | `T1_BUILD_CLEAN` | `T2_TEST_PASS_100`| `T3_BUNDLE_SIZE` | `T4_E2E_DASH` | `T5_STRICT_LINT` |

---

## 3. Tier-by-Tier Test Methodology & Test Cases

### Tier 1: Category-Partition & Interface Contract Tests
Validates interfaces, command signatures, output schemas, and data structures against exact interface contracts.

1. **`test_t1_pipeline_cli_interface`**:
   - **Target**: `run_pipeline.py` CLI interface.
   - **Partitions**: Valid `--data`, `--output-dir`, `--k`, `--algorithm {kmeans,dbscan,agglomerative,all}`, `--export-dashboard`.
   - **Contract**: CLI returns exit code 0 and logs execution progress.
2. **`test_t1_pipeline_output_json_schema`**:
   - **Target**: `artifacts/pipeline_output.json`.
   - **Contract**: Conforms strictly to `PipelineOutputJSON` TypeScript interface:
     - `timestamp`: ISO 8601 string.
     - `dataset_summary`: total_customers, features, age_stats, income_stats, spending_stats, gender_counts.
     - `kpis`: optimal_k, silhouette_score, davies_bouldin_index, calinski_harabasz_score, inertia, best_algorithm.
     - `customers`: Array of 200 items with (customer_id, gender, age, annual_income, spending_score, cluster_id, cluster_name, pca_x, pca_y).
     - `clusters`: Array of cluster metadata objects with personas, colors, averages, and recommendations.
     - `model_comparisons`: Array with comparative scores across evaluated algorithms.
3. **`test_t1_joblib_model_serialization`**:
   - **Target**: `artifacts/models/*.joblib`.
   - **Contract**: Artifacts are valid serializations loadable by `joblib.load()` with `.predict` or `.labels_` attributes.
4. **`test_t1_autoresearch_cli_interface`**:
   - **Target**: `run_autoresearch.py` CLI interface.
   - **Partitions**: `--iterations`, `--step-size`, `--output`.
   - **Contract**: Returns exit code 0 and produces `optimization_log.md` and `artifacts/autoresearch_output.json`.
5. **`test_t1_optimization_log_structure`**:
   - **Target**: `optimization_log.md`.
   - **Contract**: Contains academic paper title, authors, year, baseline metrics table, iteration step logs, and final optimized configuration.
6. **`test_t1_dashboard_package_integrity`**:
   - **Target**: `dashboard/package.json` and `dashboard/vite.config.ts`.
   - **Contract**: Contains build and test scripts (`build`, `test`), React 18/19, Lucide, Recharts/Chart.js dependencies.

---

### Tier 2: Boundary Value Analysis (BVA) & Edge Conditions
Tests mathematical boundaries, extreme parameters, and edge inputs.

1. **`test_t2_cluster_k_boundaries`**:
   - **Domain**: Cluster count $k \in [2, 10]$.
   - **Boundary Tests**: $k=2$ (minimum non-trivial), $k=5$ (canonical Mall Customer optimal), $k=10$ (upper bound).
   - **Invariant**: Generated clusters count == $k$, Silhouette score $\in [-1.0, 1.0]$.
2. **`test_t2_dbscan_parameter_boundaries`**:
   - **Domain**: $\epsilon \in (0.1, 2.0]$, `min_samples` $\in [2, 15]$.
   - **Boundary Tests**: Small $\epsilon$ (high noise / many outliers), large $\epsilon$ (single cluster fallback).
   - **Invariant**: Handled without unhandled exceptions or zero-division errors.
3. **`test_t2_metrics_mathematical_bounds`**:
   - **Silhouette Score**: Validated strictly within $[-1.0, 1.0]$.
   - **Davies-Bouldin Index**: Validated strictly $\ge 0.0$ (lower is better).
   - **Calinski-Harabasz Score**: Validated strictly $\ge 0.0$ (higher is better).
4. **`test_t2_autoresearch_iteration_bounds`**:
   - **Domain**: Iterations $= 1, 5, 20$.
   - **Invariant**: Iteration count in `optimization_log.md` matches requested iterations.
5. **`test_t2_empty_or_zero_values_handling`**:
   - **Data Boundaries**: Customer age $\ge 18$, Annual Income $\ge 0$, Spending Score $\in [1, 99]$.
   - **Invariant**: Summary statistics (min, max, mean, std) accurately match bounds.

---

### Tier 3: Pairwise Combinatorial & Algorithm Exploration Tests
Tests orthogonal combinations of feature subsets, scalers, and clustering models.

1. **`test_t3_feature_subset_and_scaler_matrix`**:
   - **Factors**:
     - Feature subsets: `[Annual Income, Spending Score]`, `[Age, Annual Income, Spending Score]`, `[Gender_Encoded, Age, Income, Spending]`.
     - Scalers: `StandardScaler`, `MinMaxScaler`, `RobustScaler`.
     - Algorithms: `KMeans`, `AgglomerativeClustering`, `DBSCAN`.
   - **Verification**: Evaluates full pairwise matrix to ensure no configuration raises unhandled exceptions and all return valid evaluation metrics.
2. **`test_t3_multi_model_comparison_consistency`**:
   - **Verification**: `pipeline_output.json` `model_comparisons` contains entries for KMeans, DBSCAN, and Agglomerative clustering with consistent metric calculations.

---

### Tier 4: Real-World End-to-End (E2E) Integration Scenarios
Executes complete workflows from data ingestion to dashboard render verification.

1. **`test_t4_full_crisp_dm_pipeline_e2e`**:
   - Executes `python run_pipeline.py --data data/raw/Mall_Customers.csv --output-dir artifacts --export-dashboard`.
   - Verifies generation of:
     - `artifacts/models/kmeans_model.joblib`
     - `artifacts/customer_segments.csv`
     - `artifacts/metrics.json`
     - `artifacts/pipeline_output.json`
     - `dashboard/public/data/pipeline_output.json`
   - Verifies exit code is 0.
2. **`test_t4_autoresearch_hill_climbing_e2e`**:
   - Executes `python run_autoresearch.py --iterations 5 --output optimization_log.md`.
   - Verifies:
     - Generation of `optimization_log.md` with benchmark citation and hill-climbing progress.
     - Generation of `artifacts/autoresearch_output.json` and `dashboard/public/data/autoresearch_output.json`.
     - Metric progression: Best Silhouette $\ge$ Baseline Silhouette or documented convergence.
3. **`test_t4_dashboard_build_and_render_e2e`**:
   - Executes `npm run build` in `dashboard/` directory.
   - Verifies clean build output (exit code 0, `dashboard/dist/index.html` created).
   - Executes Vitest / Testing-Library render tests (`npm test` / `npx vitest run`).
   - Verifies all dashboard views (KPIs, 2D/3D Scatter, Distributions, Personas, Autoresearch Lab, Customer Table, CRISP-DM Guide) render cleanly.

---

### Tier 5: Adversarial, Resiliency & Integrity Hardening Tests
Adversarial stress tests designed to ensure system robustness.

1. **`test_t5_missing_input_file_resilience`**:
   - Invoking pipeline with a non-existent dataset path should fail gracefully with a clear error message and non-zero exit code.
2. **`test_t5_corrupt_data_handling`**:
   - Test data loader with missing values or invalid data types to verify validation logic.
3. **`test_t5_invalid_cli_arguments`**:
   - Invalid `--algorithm invalid_choice` or negative `--k -1` returns non-zero exit code and informative help message.
4. **`test_t5_dashboard_missing_data_fallback`**:
   - Dashboard tests verify that if `pipeline_output.json` is temporarily unavailable or empty, the dashboard loads fallback default data without white-screening.

---

## 4. Test Execution Architecture

The test suite is structured as follows:

```
tests/
├── __init__.py
├── conftest.py                  # Pytest fixtures, paths, CLI helper functions
├── test_data_contracts.py       # Tier 1 Schema & Invariant contracts
├── test_pipeline_e2e.py         # Tiers 1-4 Pipeline & CRISP-DM ML tests
├── test_autoresearch_e2e.py     # Tiers 1-4 Autoresearch & Hill Climbing tests
├── test_dashboard_e2e.py        # Tiers 1-4 Dashboard Build & Vitest Render tests
├── test_adversarial.py          # Tier 5 Adversarial & Boundary stress tests
└── run_e2e_tests.py             # Master CLI Test Runner with formatted reporting
```

### Test Runner Commands
- **Master Test Runner**:
  ```bash
  python tests/run_e2e_tests.py
  ```
- **Pytest Master Suite**:
  ```bash
  pytest tests/ -v
  ```
- **Dashboard Component Tests**:
  ```bash
  cd dashboard && npm test
  ```
