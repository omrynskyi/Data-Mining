# Project: Customer Segmentation Clustering & React Data Science Dashboard

## Overview
An end-to-end data mining and machine learning system following the CRISP-DM framework on the Mall Customer Segmentation dataset. The project includes automated data preparation, multi-algorithm clustering (K-Means, DBSCAN, Agglomerative), comprehensive evaluation metrics (Silhouette, Davies-Bouldin, Calinski-Harabasz, Inertia), an automated autoresearch hill-climbing optimization engine aligned with academic benchmark literature (`optimization_log.md`), and a modern React Data Science Admin Dashboard with interactive visualizations and automated component render tests.

---

## Architecture

```
                                    +------------------------------+
                                    |     Mall Customers Data      |
                                    |  (data/raw/Mall_Customers)   |
                                    +--------------+---------------+
                                                   |
                                                   v
+--------------------------------------------------+--------------------------------------------------+
| CRISP-DM Clustering Pipeline (src/ & run_pipeline.py)                                               |
|                                                                                                     |
|  1. Data Understanding & Ingestion (src/data_loader.py, src/data_understanding.py)                  |
|  2. Data Preparation & Scaling (src/data_preparation.py)                                            |
|  3. Modeling: K-Means, DBSCAN, Agglomerative, PCA (src/models.py)                                   |
|  4. Evaluation: Silhouette, DB Index, CH Index, Inertia (src/evaluation.py)                          |
|  5. Exporter: Generates JSON contracts & Joblib models (src/export.py)                               |
+-----------------------------------+----------------------------------+------------------------------+
                                    |                                  |
                                    v                                  v
+-----------------------------------+----------+       +---------------+------------------------------+
| Autoresearch Engine (src/autoresearch.py)    |       | Artifacts Storage (artifacts/ & public/data) |
| - Benchmarks against academic paper          |       | - pipeline_output.json                       |
| - Hill-climbing hyperparameter optimization  |       | - autoresearch_output.json                   |
| - Generates optimization_log.md              |       | - model.joblib, cluster_labels.csv           |
+----------------------------------------------+       +---------------+------------------------------+
                                                                       |
                                                                       v
                                                       +---------------+------------------------------+
                                                       | React Data Science Admin Dashboard           |
                                                       | (dashboard/ - Vite, React 18, TS, Tailwind)  |
                                                       |                                              |
                                                       | - Executive KPIs & Overview                  |
                                                       | - 2D & 3D Interactive Cluster Visualizer     |
                                                       | - Feature Distributions & Demographics       |
                                                       | - Persona Profiles & Business Insights       |
                                                       | - Autoresearch Lab & Model Comparison        |
                                                       | - Customer Explorer Table                    |
                                                       | - Vitest + React Testing Library Test Suite  |
                                                       +----------------------------------------------+
```

---

## Feature Inventory

| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| F1 | Dataset Acquisition & Ingestion | Automated loader with fallback for 200-record Mall Customer dataset | M1 | Survey |
| F2 | CRISP-DM Data Understanding | Descriptive statistics, outlier checks, demographic distributions, correlation analysis | M1 | Survey |
| F3 | Data Preparation & Feature Scaling | StandardScaler, MinMaxScaler, RobustScaler pipelines, feature subset transforms | M1 | Survey |
| F4 | Multi-Algorithm Clustering Engine | K-Means (k-means++), DBSCAN, Agglomerative clustering, 2D/3D PCA & t-SNE | M1 | Survey |
| F5 | Cluster Evaluation & Validation | Silhouette Score, Davies-Bouldin Index, Calinski-Harabasz Index, WCSS/Inertia | M1 | Survey |
| F6 | Pipeline CLI Runner | CLI entry point `run_pipeline.py` with arguments, logging, and exit code 0 | M1 | ORIGINAL_REQUEST §R1 |
| F7 | Dashboard Data Exporter | Generates structured `pipeline_output.json` with customer points, cluster stats, KPIs | M1 | Survey |
| F8 | Academic Benchmark Reference Alignment | References benchmark literature (e.g. 2D k=5 Silhouette ~0.554, 3D k=5/6 Silhouette ~0.452) | M2 | ORIGINAL_REQUEST §R3 |
| F9 | Autoresearch Hill-Climbing Optimizer | Iterative hill-climbing search over feature sets, scalers, algorithm parameters | M2 | ORIGINAL_REQUEST §R3 |
| F10 | Optimization Log Generation | Emits `optimization_log.md` detailing paper citation, baselines, iteration history, best config | M2 | ORIGINAL_REQUEST §R3 |
| F11 | Dashboard Project Scaffolding | Vite 5 + React 18/19 + TypeScript + Tailwind CSS + Lucide Icons + Recharts setup | M3 | ORIGINAL_REQUEST §R2 |
| F12 | Dashboard UI Visualizations & Views | 7 views: KPIs, 2D/3D Scatter, Distributions, Personas, Model Lab, Table, CRISP-DM guide | M3 | ORIGINAL_REQUEST §R2 |
| F13 | Dashboard Data Integration & State | Reads `pipeline_output.json` & `autoresearch_output.json` with robust fallback state | M3 | ORIGINAL_REQUEST §R2 |
| F14 | Build & Programmatic Render Tests | Clean `npm run build` and Vitest/Testing-Library component & chart render tests | M3 | ORIGINAL_REQUEST §R2 |
| F15 | Comprehensive E2E Verification | Tiers 1-4 opaque-box test suite + Tier 5 adversarial verification + integrity audit | M_FINAL | Project Pattern |

---

## Milestones

| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| E2E | E2E Test Suite Track | Design & implement opaque-box E2E test harness covering R1, R2, R3 (Tiers 1-4) | none | COMPLETE |
| M1 | CRISP-DM ML Pipeline | `src/` modules, `data/`, `run_pipeline.py`, metrics evaluation, artifact exports | none | COMPLETE |
| M2 | Autoresearch & Benchmark Alignment | `src/autoresearch.py`, `run_autoresearch.py`, `optimization_log.md`, best model export | M1 | COMPLETE |
| M3 | React Data Science Dashboard | `dashboard/` Vite app, UI components, chart visualizations, render tests, `npm run build` | M1 | COMPLETE |
| M_FINAL | Full E2E Pass & Adversarial Hardening | 100% E2E test pass, Tier 5 stress testing, forensic audit verification | M1, M2, M3, E2E | COMPLETE |

### Verified Acceptance Criteria

| Criterion | Command | Result |
|---|---|---|
| Pipeline execution | `python run_pipeline.py` | exit 0 · KMeans k=5 · Silhouette **0.5547**, DB **0.5722**, CH **248.65** |
| Autoresearch log | `python run_autoresearch.py --iterations 12` | exit 0 · `optimization_log.md` cites Kansal et al. (2018), baseline 0.4676 → **0.5595** (+19.65%), 101.01% of the published 0.5539 |
| Dashboard build | `cd dashboard && npm run build` | exit 0 · `dashboard/dist/index.html` emitted |
| Render tests | `cd dashboard && npm test` | **23/23** Vitest + React Testing Library tests pass |
| Full Python suite | `pytest` | **134 passed, 0 skipped** |

---

## Interface Contracts

### 1. Python Pipeline Entry Point (`run_pipeline.py`)
```bash
python run_pipeline.py [--data PATH] [--output-dir DIR] [--k INT] [--algorithm {kmeans,dbscan,agglomerative,all}] [--export-dashboard]
```
- **Inputs**: CSV dataset at `--data` (default: `data/raw/Mall_Customers.csv`).
- **Outputs**:
  - `artifacts/models/kmeans_model.joblib`, `dbscan_model.joblib`, `agglomerative_model.joblib`
  - `artifacts/metrics.json`
  - `artifacts/customer_segments.csv`
  - `artifacts/pipeline_output.json` (and optionally copied to `dashboard/public/data/pipeline_output.json`)
- **Return Code**: 0 on success, non-zero on failure.

### 2. Autoresearch Entry Point (`run_autoresearch.py`)
```bash
python run_autoresearch.py [--iterations INT] [--step-size FLOAT] [--output LOG_PATH]
```
- **Inputs**: Dataset, benchmark reference specification.
- **Outputs**:
  - `optimization_log.md` citing paper, baseline metrics, step-by-step tuning log, best metrics.
  - `artifacts/autoresearch_output.json` (and `dashboard/public/data/autoresearch_output.json`).
  - `artifacts/models/best_autoresearch_model.joblib`.
- **Return Code**: 0 on success.

### 3. Dashboard Data Schema (`pipeline_output.json`)
```typescript
interface PipelineOutputJSON {
  timestamp: string;
  dataset_summary: {
    total_customers: number;
    features: string[];
    age_stats: { mean: number; min: number; max: number; std: number };
    income_stats: { mean: number; min: number; max: number; std: number };
    spending_stats: { mean: number; min: number; max: number; std: number };
    gender_counts: { Male: number; Female: number };
  };
  kpis: {
    optimal_k: number;
    silhouette_score: number;
    davies_bouldin_index: number;
    calinski_harabasz_score: number;
    inertia: number;
    best_algorithm: string;
  };
  customers: Array<{
    customer_id: number;
    gender: 'Male' | 'Female';
    age: number;
    annual_income: number;
    spending_score: number;
    cluster_id: number;
    cluster_name: string;
    pca_x: number;
    pca_y: number;
    pca_z?: number;
  }>;
  clusters: Array<{
    cluster_id: number;
    name: string;
    persona: string;
    color: string;
    count: number;
    percentage: number;
    avg_age: number;
    avg_income: number;
    avg_spending: number;
    gender_distribution: { Male: number; Female: number };
    business_recommendation: string;
    key_traits: string[];
  }>;
  model_comparisons: Array<{
    algorithm: string;
    k?: number;
    silhouette_score: number;
    davies_bouldin_index: number;
    calinski_harabasz_score: number;
    description: string;
  }>;
}
```

### 4. React Dashboard Interface & Build Contract
- **Directory**: `dashboard/`
- **Commands**:
  - `npm run build`: Compiles production bundle to `dashboard/dist` with 0 errors.
  - `npm test` or `npx vitest run`: Executes programmatic component & chart rendering tests, 100% passing.

---

## Code Layout

```
.
├── data/
│   ├── raw/
│   │   └── Mall_Customers.csv
│   └── processed/
├── src/
│   ├── __init__.py
│   ├── config.py
│   ├── data_loader.py
│   ├── data_understanding.py
│   ├── data_preparation.py
│   ├── models.py
│   ├── evaluation.py
│   ├── autoresearch.py
│   └── export.py
├── artifacts/
│   ├── models/
│   ├── metrics.json
│   ├── customer_segments.csv
│   └── pipeline_output.json
├── dashboard/
│   ├── public/
│   │   └── data/
│   │       ├── pipeline_output.json
│   │       └── autoresearch_output.json
│   ├── src/
│   │   ├── components/
│   │   │   ├── Navbar.tsx
│   │   │   ├── KpiCards.tsx
│   │   │   ├── ClusterVisualizer2D.tsx
│   │   │   ├── ClusterVisualizer3D.tsx
│   │   │   ├── DistributionsChart.tsx
│   │   │   ├── PersonaCards.tsx
│   │   │   ├── AutoresearchLab.tsx
│   │   │   ├── CustomerTable.tsx
│   │   │   └── CrispDmGuide.tsx
│   │   ├── types/
│   │   │   └── index.ts
│   │   ├── data/
│   │   │   └── defaultData.ts
│   │   ├── __tests__/
│   │   │   └── dashboard.test.tsx
│   │   ├── App.tsx
│   │   ├── main.tsx
│   │   └── index.css
│   ├── package.json
│   ├── tsconfig.json
│   ├── vite.config.ts
│   └── tailwind.config.js
├── tests/
│   ├── __init__.py
│   ├── test_data_loader.py
│   ├── test_pipeline.py
│   ├── test_autoresearch.py
│   └── test_e2e.py
├── scripts/
│   └── generate_default_data.py    # regenerates the dashboard's offline snapshot
├── run_pipeline.py
├── run_autoresearch.py
├── optimization_log.md
├── requirements.txt
├── TEST_INFRA.md
├── TEST_READY.md
└── PROJECT.md
```
