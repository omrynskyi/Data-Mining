# Explorer 1 Survey Report: Customer Segmentation & Dashboard

**Date**: 2026-09-02  
**Working Directory**: `/Users/oleg/Documents/Coding/SJSU/Data Mining/HW1/Part 2/03_customer_segmentation_clustering/.agents/explorer_0_1`  
**Workspace Root**: `/Users/oleg/Documents/Coding/SJSU/Data Mining/HW1/Part 2/03_customer_segmentation_clustering`  
**Author**: Explorer 1 (Subagent ID: `7755bb07-eae3-45ac-a896-82ca6786d0a7`)  
**Parent Orchestrator**: `205c1025-6744-49d9-995b-f49e76a9204f`

---

## 1. Executive Summary

This survey evaluates the environment, tooling, dataset status, and technical requirements for the **Customer Segmentation & Dashboard** project based on `ORIGINAL_REQUEST.md`.

### Key Findings
1. **Clean Workspace**: The workspace root currently contains only `ORIGINAL_REQUEST.md` and the `.agents/` directory. No legacy code or conflicting configurations exist.
2. **Python Environment**: Python 3.9.6 is installed with all essential data science, machine learning, and testing libraries pre-installed (`numpy 1.26.4`, `pandas 2.3.3`, `scipy 1.13.1`, `scikit-learn 1.6.1`, `matplotlib 3.9.4`, `seaborn 0.13.2`, `joblib 1.5.3`, `pytest 8.3.4`).
3. **Node/npm Environment**: Modern Node.js `v24.13.0` and npm `11.6.2` are installed and fully operational for scaffolding and building the React data science admin dashboard.
4. **Dataset State**: `Mall_Customers.csv` is not yet present locally in the workspace. The canonical 200-row dataset structure is well-defined, and an automated fetch script with an offline deterministic fallback must be established in `data/Mall_Customers.csv`.
5. **CRISP-DM Pipeline (R1) Readiness**: The required stages (Business Understanding, Data Understanding, Data Preparation, Modeling, Evaluation, Deployment) are fully specifiable with standard scikit-learn algorithms (K-Means, DBSCAN, Agglomerative Clustering) and multi-metric evaluations (Silhouette Score, Davies-Bouldin Index, Calinski-Harabasz Index, Inertia).

---

## 2. Workspace & Filesystem Audit

### 2.1 Workspace Root Inventory
Path: `/Users/oleg/Documents/Coding/SJSU/Data Mining/HW1/Part 2/03_customer_segmentation_clustering`

| Item | Type | Size | Status | Purpose |
|------|------|------|--------|---------|
| `ORIGINAL_REQUEST.md` | File | 2.28 KB | Existing | Top-level project specifications & requirements |
| `.agents/` | Directory | - | Existing | Agent metadata, briefings, dispatches, handoffs |

### 2.2 Recommended Project Directory Layout
To ensure clear modularity and compliance with project layout conventions:

```
03_customer_segmentation_clustering/
├── ORIGINAL_REQUEST.md
├── PROJECT.md                      # High-level architecture & specifications
├── requirements.txt                # Python dependencies specification
├── run_pipeline.py                 # Main CLI entrypoint for CRISP-DM ML pipeline
├── run_autoresearch.py             # Autoresearch & hill climbing optimization script
├── optimization_log.md             # Benchmark paper alignment log
├── data/
│   ├── raw/
│   │   └── Mall_Customers.csv      # Canonical 200-row customer dataset
│   └── processed/
│       └── scaled_customers.csv    # Preprocessed & scaled feature matrix
├── src/
│   ├── __init__.py
│   ├── data_loader.py              # Ingestion, validation, download fallback
│   ├── preprocessor.py            # Cleaning, encoding, scaling (StandardScaler/MinMax/Robust)
│   ├── clustering.py              # K-Means, DBSCAN, Agglomerative, GMM implementations
│   ├── evaluation.py              # Silhouette, Davies-Bouldin, Calinski-Harabasz, Elbow analysis
│   ├── profiling.py               # Customer persona profiling & cluster characterization
│   └── autoresearch.py            # Paper metric extraction & hill climbing optimizer
├── artifacts/
│   ├── models/                    # Serialized joblib models (kmeans, scaler, pca)
│   ├── metrics.json               # Full evaluation metrics across all models
│   ├── customer_segments.json     # Segmented customer records for React dashboard
│   ├── customer_segments.csv      # Flat tabular segment export
│   └── figures/                   # Static plots (elbow, silhouette, 2D/3D scatter)
├── dashboard/                     # React Data Science Admin Dashboard (Vite + React)
│   ├── package.json
│   ├── vite.config.ts
│   ├── src/
│   │   ├── components/            # Charts, KPI cards, Cluster Visualizer, Persona view
│   │   ├── data/                  # Symlink or bundled customer_segments.json
│   │   ├── App.tsx
│   │   └── main.tsx
│   └── tests/                     # Programmatic render tests (Vitest / Testing Library)
└── tests/                         # Pytest test suite for ML pipeline & autoresearch
    ├── test_data_loader.py
    ├── test_preprocessor.py
    ├── test_clustering.py
    ├── test_evaluation.py
    └── test_pipeline_e2e.py
```

---

## 3. Environment & Toolchain Audit

### 3.1 Python Toolchain
- **Python Version**: `Python 3.9.6` (darwin / macOS arm64/x86_64)
- **Interpreter Location**: `/usr/bin/python3`

#### Verified Python Packages

| Package | Installed Version | Role in Project | Verification Status |
|---------|-------------------|-----------------|---------------------|
| `numpy` | `1.26.4` | Vectorized numerical operations & array handling | Verified functional |
| `pandas` | `2.3.3` | DataFrame manipulation, CSV parsing, EDA statistics | Verified functional |
| `scipy` | `1.13.1` | Scientific routines, distance matrices, linkage | Verified functional |
| `scikit-learn` | `1.6.1` | Clustering (KMeans, DBSCAN, Agglomerative), Scalers, Metrics, PCA | Verified functional |
| `matplotlib` | `3.9.4` | Static figure generation (Elbow curve, Silhouette plots) | Verified functional |
| `seaborn` | `0.13.2` | Enhanced statistical visualizations | Verified functional |
| `joblib` | `1.5.3` | Model persistence & serialization | Verified functional |
| `pytest` | `8.3.4` | Automated test runner for pipeline & unit tests | Verified functional |

### 3.2 Node.js & Web Toolchain
- **Node.js Version**: `v24.13.0`
- **npm Version**: `11.6.2`
- **npx Version**: `11.6.2`
- **Capabilities**:
  - Full support for modern ECMAScript / TypeScript.
  - Fast frontend scaffolding via Vite (`npm create vite@latest dashboard -- --template react-ts` or `react`).
  - Support for React UI component libraries (Tailwind CSS, Lucide React, Recharts / Chart.js).
  - Modern frontend testing via Vitest + `@testing-library/react` + `jsdom`.

---

## 4. Dataset Identification & Ingestion Architecture

### 4.1 Canonical Dataset Specification
- **Dataset Name**: Mall Customer Segmentation Data (commonly sourced from Kaggle / UCI / academic papers)
- **Total Records**: Exactly **200 customer rows** (+ 1 header row)
- **Feature Set (5 Columns)**:
  1. `CustomerID`: Integer ID (`1` to `200`)
  2. `Gender` (or `Genre` in legacy CSVs): Categorical string (`"Male"`, `"Female"`)
  3. `Age`: Integer (`18` to `70` years)
  4. `Annual Income (k$)`: Integer (`15` to `137` k$)
  5. `Spending Score (1-100)`: Integer (`1` to `99`)

### 4.2 Data Ingestion & Sanitization Rules
1. **Header Alias Normalization**:
   - Strip leading/trailing whitespace from column headers.
   - Map `Genre` $\rightarrow$ `Gender`.
   - Normalize `Annual Income (k$)` and `Spending Score (1-100)` to clean variable identifiers (`annual_income`, `spending_score`).
2. **Missing & Range Validation**:
   - Verify 0 null/NaN values across all 200 records.
   - Enforce invariant checks: `Age >= 18`, `Annual Income >= 0`, `1 <= Spending Score <= 100`.
3. **Deterministic Fallback Ingestion**:
   - `src/data_loader.py` will first check if `data/raw/Mall_Customers.csv` exists locally.
   - If missing, it will attempt to download from raw GitHub repository (`https://raw.githubusercontent.com/sharmaroshan/Clustering-of-Mall-Customers/master/Mall_Customers.csv`).
   - If network access is restricted or unavailable, it embeds the canonical 200-row seed generator or fallback data structure to ensure 100% reliable offline reproduction.

---

## 5. R1: CRISP-DM Machine Learning Pipeline Specification

The machine learning pipeline must follow all six phases of the **CRISP-DM (Cross-Industry Standard Process for Data Mining)** methodology:

```
+-------------------------------------------------------------------------------+
|                             CRISP-DM PIPELINE                                 |
+-------------------------------------------------------------------------------+
| 1. Business Understanding                                                     |
|    - Goal: Segment retail customers to target marketing and increase revenue |
|    - Target: High-value, moderate, budget, and spendthrift personas          |
+---------------------------------------+---------------------------------------+
                                        |
+---------------------------------------v---------------------------------------+
| 2. Data Understanding                                                         |
|    - Automated EDA: Summary statistics, distributions, skewness, outliers     |
|    - Correlation matrix (Age, Income, Spending Score)                         |
+---------------------------------------+---------------------------------------+
                                        |
+---------------------------------------v---------------------------------------+
| 3. Data Preparation                                                           |
|    - Header normalization & categorical encoding (Gender: Male=0, Female=1)   |
|    - Feature Scaling: StandardScaler / RobustScaler / MinMaxScaler            |
|    - Feature Matrix generation: 2D (Income & Score), 3D (Age, Income, Score),|
|      and 4D (Gender, Age, Income, Score) + PCA (2 components)                |
+---------------------------------------+---------------------------------------+
                                        |
+---------------------------------------v---------------------------------------+
| 4. Modeling                                                                   |
|    - Primary: K-Means (k=2 to 10; default optimal k=5; k-means++; n_init=10)  |
|    - Secondary: DBSCAN (eps, min_samples tuning; noise filtering)            |
|    - Benchmark: Agglomerative Hierarchical (Ward/Average) & GMM               |
+---------------------------------------+---------------------------------------+
                                        |
+---------------------------------------v---------------------------------------+
| 5. Evaluation                                                                 |
|    - Metrics: Silhouette Score, Davies-Bouldin Index, Calinski-Harabasz, WCSS|
|    - Elbow Method curve analysis across k=2..10                               |
|    - Persona profiling: Segment statistics (mean age, income, spend, size %) |
+---------------------------------------+---------------------------------------+
                                        |
+---------------------------------------v---------------------------------------+
| 6. Deployment & Artifact Export                                               |
|    - Entrypoint: python run_pipeline.py                                       |
|    - Saves models (joblib), metrics.json, customer_segments.json, plots       |
+-------------------------------------------------------------------------------+
```

### 5.1 Pipeline Execution Requirements (`run_pipeline.py`)
- **CLI Options**:
  - `--data-path`: Path to raw CSV (default: `data/raw/Mall_Customers.csv`).
  - `--output-dir`: Output directory for models and metrics (default: `artifacts/`).
  - `--n-clusters`: Cluster count for K-Means (default: `5`).
  - `--scaler`: Scaling method (`standard`, `minmax`, `robust`, `none`; default: `standard`).
  - `--features`: Feature set (`2d` [Income, Spending], `3d` [Age, Income, Spending], `all`; default: `2d`).
  - `--generate-plots`: Flag to export static PNG figures.
- **Exit Code**: 0 on clean completion; non-zero with descriptive traceback on error.

### 5.2 Key Evaluation Metrics for Mall Customer Segmentation
Based on academic benchmarks:
1. **Silhouette Coefficient**:
   - Measures intra-cluster cohesion vs. nearest-cluster separation (range: $[-1, 1]$).
   - Standard 2D K-Means ($k=5$) benchmark score: $\approx 0.554$ (unscaled) / $\approx 0.555$ (scaled).
2. **Davies-Bouldin Index (DBI)**:
   - Evaluates intra-cluster similarity relative to inter-cluster distance (lower is better; range: $[0, \infty)$).
   - Standard 2D K-Means ($k=5$) benchmark score: $\approx 0.572$.
3. **Calinski-Harabasz Score (Variance Ratio Criterion)**:
   - Ratio of between-cluster dispersion to within-cluster dispersion (higher is better).
   - Standard 2D K-Means ($k=5$) benchmark score: $\approx 247.3$.
4. **Inertia (Within-Cluster Sum of Squares - WCSS)**:
   - Used for the Elbow curve to validate $k=5$ inflection point.

### 5.3 5 Canonical Customer Personas ($k=5$ on Income & Spending Score)
1. **Cluster 0 — Target / VIP Spenders**: High Annual Income, High Spending Score. Prime audience for luxury marketing & premium loyalty programs.
2. **Cluster 1 — Standard / Average**: Moderate Annual Income, Moderate Spending Score. Core retail base; receptive to standard promotional offers.
3. **Cluster 2 — Careful / Conservative High Earners**: High Annual Income, Low Spending Score. High potential purchasing power; need tailored incentives to increase spending.
4. **Cluster 3 — Spendthrifts / Careless**: Low Annual Income, High Spending Score. Young/impulsive demographic; responsive to trendy campaigns and discount events.
5. **Cluster 4 — Sensible / Budget Conscious**: Low Annual Income, Low Spending Score. Budget-constrained shoppers; focus on essential value products and steep discounts.

---

## 6. Interface Contracts & Artifact Schema

### 6.1 `artifacts/metrics.json` Contract
```json
{
  "timestamp": "2026-09-02T12:00:00Z",
  "dataset": {
    "total_records": 200,
    "features_used": ["Annual Income (k$)", "Spending Score (1-100)"],
    "scaler": "StandardScaler"
  },
  "primary_model": {
    "algorithm": "KMeans",
    "n_clusters": 5,
    "random_state": 42,
    "metrics": {
      "silhouette_score": 0.5546,
      "davies_bouldin_index": 0.5722,
      "calinski_harabasz_index": 247.3589,
      "inertia": 44.433
    }
  },
  "comparison_models": [
    {
      "algorithm": "DBSCAN",
      "params": {"eps": 0.3, "min_samples": 5},
      "n_clusters": 5,
      "noise_points": 12,
      "metrics": {
        "silhouette_score": 0.421,
        "davies_bouldin_index": 0.784
      }
    },
    {
      "algorithm": "AgglomerativeClustering",
      "params": {"n_clusters": 5, "linkage": "ward"},
      "metrics": {
        "silhouette_score": 0.553,
        "davies_bouldin_index": 0.584
      }
    }
  ],
  "elbow_analysis": {
    "k_values": [2, 3, 4, 5, 6, 7, 8, 9, 10],
    "inertias": [269.4, 157.7, 108.9, 44.4, 37.2, 30.1, 25.0, 21.8, 19.6],
    "silhouette_scores": [0.297, 0.468, 0.493, 0.555, 0.538, 0.527, 0.457, 0.456, 0.456]
  }
}
```

### 6.2 `artifacts/customer_segments.json` Contract (For React Dashboard)
```json
{
  "summary": {
    "total_customers": 200,
    "num_clusters": 5,
    "cluster_names": {
      "0": "Careful Earners",
      "1": "Standard Shoppers",
      "2": "Target / VIP Spenders",
      "3": "Spendthrifts",
      "4": "Budget Shoppers"
    }
  },
  "cluster_profiles": [
    {
      "cluster_id": 0,
      "name": "Target / VIP Spenders",
      "count": 39,
      "percentage": 19.5,
      "avg_age": 32.7,
      "avg_income": 86.5,
      "avg_spending_score": 82.1,
      "gender_ratio": {"Female": 0.54, "Male": 0.46},
      "description": "High income, high spending. Prime segment for premium products."
    }
  ],
  "records": [
    {
      "customer_id": 1,
      "gender": "Male",
      "age": 19,
      "annual_income": 15,
      "spending_score": 39,
      "cluster": 4,
      "cluster_name": "Budget Shoppers",
      "pca_x": -0.842,
      "pca_y": -0.412
    }
  ]
}
```

---

## 7. Downstream Dependencies & Implementation Recommendations

1. **For Track B Implementers (Milestone 1: Pipeline)**:
   - Create modular Python code in `src/` to ensure reusability by `run_pipeline.py`, `run_autoresearch.py`, and `pytest`.
   - Ensure `run_pipeline.py` executes cleanly without requiring external manual file movements.
2. **For Track B Implementers (Milestone 2: Autoresearch & Hill Climbing)**:
   - `run_autoresearch.py` should import clustering and evaluation utilities from `src/`.
   - Hill climber will explore parameter permutations (feature subsets, scaling methods, $k$, initialization methods, linkage) to maximize the Silhouette score / minimize DBI, outputting steps into `optimization_log.md`.
3. **For Track B Implementers (Milestone 3: React Dashboard)**:
   - Scaffold dashboard inside `dashboard/` with Vite (`npm create vite@latest dashboard -- --template react-ts`).
   - Readily consume `artifacts/customer_segments.json` (and `metrics.json`) or fall back to an internal bundled sample if the backend pipeline has not been executed yet.
   - Include Vitest / Testing Library render tests inside `dashboard/` executing via `npm test`.
4. **For Track A Test Engineers**:
   - Provide opaque-box test suites in `tests/` checking CLI flags, exit codes, output file existence, schema adherence, metric sanity ($0 < \text{Silhouette} \le 1$), and dashboard build artifacts (`dashboard/dist/index.html`).

---

## 8. Conclusion & Action Items

- **Environment**: 100% Ready (Python 3.9.6 + scikit-learn + pandas + pytest, Node v24.13.0 + npm 11.6.2).
- **Dataset Strategy**: Store canonical 200 records in `data/raw/Mall_Customers.csv` with automated download + deterministic embedded fallback in `src/data_loader.py`.
- **Pipeline Architecture**: Standardized CRISP-DM modular architecture with `run_pipeline.py` generating models (`joblib`), metrics (`metrics.json`), and dashboard payload (`customer_segments.json`).
- **Proceed to Phase 1 Dual-Track Launch**: Specification is complete and ready for handoff to Orchestrator.
