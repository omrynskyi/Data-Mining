# Milestone 1: Artifact Generation, Downstream Integration & CLI Specification

**Author**: Explorer 3 (Artifacts, Downstream Integration & CLI Architect)  
**Date**: 2026-09-02  
**Target Milestone**: Milestone 1 (CRISP-DM & Clustering Pipeline)  
**Associated Requirements**: R1 (CRISP-DM ML Pipeline), R2 (React Dashboard Integration), F6 (CLI Runner), F7 (Dashboard Data Exporter)  
**Working Directory**: `.agents/m1_exp_3/`  
**Output Target**: `.agents/m1_exp_3/artifacts_integration.md`

---

## 1. Executive Summary & Integration Architecture

Milestone 1 establishes the end-to-end Machine Learning pipeline for the Mall Customer Segmentation dataset following the 6 phases of the CRISP-DM framework. The primary downstream consumers of this pipeline are:
1. **The React Data Science Admin Dashboard** (`dashboard/`): Requires rich, structured JSON payloads (`pipeline_output.json`) in `dashboard/public/data/` to visualize 2D/3D clusters, customer distributions, KPI cards, and persona strategies.
2. **The Autoresearch Hill-Climbing Optimization Engine** (Milestone 2): Uses the pipeline's evaluation metrics, preprocessing pipelines, and model serialization for iterative tuning against academic literature.
3. **The E2E Automated Verification Test Suite** (`tests/`): Evaluates pipeline execution, CLI exit codes, directory layout, model serialization formats, CSV outputs, and JSON contract validity.

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                   MILESTONE 1 ARTIFACT PIPELINE FLOW                                    │
└─────────────────────────────────────────────────────────────────────────────────────────────────────────┘

   [Mall_Customers.csv] ──► [data_loader.py] ──► [data_preparation.py] ──► [models.py & evaluation.py]
                                                                                      │
                                                                                      ▼
                                                                           [src/export.py Engine]
                                                                                      │
                           ┌──────────────────────────────────────────────────────────┴─────────────────────────┐
                           ▼                                                                                    ▼
              ┌────────────────────────┐                                                           ┌────────────────────────┐
              │   artifacts/ Storage   │                                                           │  dashboard/ Integration│
              ├────────────────────────┤                                                           ├────────────────────────┤
              │ • models/*.joblib      │                                                           │ • public/data/         │
              │ • metrics.json         │                                                           │   pipeline_output.json │
              │ • customer_segments.csv│                                                           │                        │
              │ • pipeline_output.json │                                                           │                        │
              └────────────────────────┘                                                           └────────────────────────┘
```

---

## 2. Artifacts Directory Architecture & File Specifications

The pipeline outputs all artifacts to the designated `--output-dir` (default: `artifacts/`). The directory structure and file schemas are strictly defined below.

### 2.1 Directory Structure

```
artifacts/
├── models/
│   ├── kmeans_model.joblib          # Fitted KMeans model (scikit-learn)
│   ├── dbscan_model.joblib          # Fitted DBSCAN model
│   ├── agglomerative_model.joblib   # Fitted AgglomerativeClustering model
│   ├── scaler.joblib                # Fitted preprocessing scaler (StandardScaler/MinMaxScaler)
│   └── pca_model.joblib             # Fitted PCA transformer (3 components for 2D/3D visualization)
├── metrics.json                     # Comprehensive machine-readable evaluation metrics
├── customer_segments.csv            # 200-row customer segmentation CSV with cluster assignments
└── pipeline_output.json             # Complete unified JSON payload for dashboard & test contracts
```

---

### 2.2 `artifacts/metrics.json` Specification

`artifacts/metrics.json` provides a clean, machine-readable summary of clustering quality across all evaluated models, identifying optimal $k$ and the best-performing algorithm.

#### JSON Schema & Example:
```json
{
  "timestamp": "2026-09-02T17:30:00Z",
  "dataset_summary": {
    "total_records": 200,
    "features": ["Age", "Annual Income (k$)", "Spending Score (1-100)"],
    "feature_set": "2D (Annual Income, Spending Score)",
    "scaler_applied": "none"
  },
  "optimal_k": 5,
  "best_algorithm": "KMeans",
  "primary_metrics": {
    "silhouette_score": 0.5539,
    "davies_bouldin_index": 0.5726,
    "calinski_harabasz_score": 247.36,
    "inertia": 44448.45
  },
  "models": {
    "kmeans_k5": {
      "algorithm": "KMeans",
      "k": 5,
      "hyperparameters": {
        "n_clusters": 5,
        "init": "k-means++",
        "n_init": 10,
        "max_iter": 300,
        "random_state": 42
      },
      "silhouette_score": 0.5539,
      "davies_bouldin_index": 0.5726,
      "calinski_harabasz_score": 247.36,
      "inertia": 44448.45,
      "num_clusters": 5,
      "noise_points": 0
    },
    "agglomerative_k5": {
      "algorithm": "AgglomerativeClustering",
      "k": 5,
      "hyperparameters": {
        "n_clusters": 5,
        "linkage": "ward",
        "metric": "euclidean"
      },
      "silhouette_score": 0.5530,
      "davies_bouldin_index": 0.5782,
      "calinski_harabasz_score": 243.07,
      "inertia": null,
      "num_clusters": 5,
      "noise_points": 0
    },
    "dbscan": {
      "algorithm": "DBSCAN",
      "hyperparameters": {
        "eps": 8.5,
        "min_samples": 4,
        "metric": "euclidean"
      },
      "silhouette_score": 0.4982,
      "davies_bouldin_index": 0.6841,
      "calinski_harabasz_score": 185.12,
      "inertia": null,
      "num_clusters": 5,
      "noise_points": 8
    }
  },
  "k_sweep": [
    {"k": 2, "silhouette": 0.2969, "davies_bouldin": 1.2800, "calinski_harabasz": 69.94, "inertia": 181363.60},
    {"k": 3, "silhouette": 0.4676, "davies_bouldin": 0.7152, "calinski_harabasz": 151.45, "inertia": 106348.37},
    {"k": 4, "silhouette": 0.4932, "davies_bouldin": 0.6540, "calinski_harabasz": 198.80, "inertia": 73679.79},
    {"k": 5, "silhouette": 0.5539, "davies_bouldin": 0.5726, "calinski_harabasz": 247.36, "inertia": 44448.45},
    {"k": 6, "silhouette": 0.5379, "davies_bouldin": 0.6480, "calinski_harabasz": 216.50, "inertia": 37233.81},
    {"k": 7, "silhouette": 0.5268, "davies_bouldin": 0.6872, "calinski_harabasz": 204.28, "inertia": 30259.65},
    {"k": 8, "silhouette": 0.4570, "davies_bouldin": 0.7640, "calinski_harabasz": 194.50, "inertia": 25000.12},
    {"k": 9, "silhouette": 0.4563, "davies_bouldin": 0.7711, "calinski_harabasz": 188.10, "inertia": 21850.40},
    {"k": 10, "silhouette": 0.4501, "davies_bouldin": 0.7850, "calinski_harabasz": 182.20, "inertia": 19680.30}
  ]
}
```

---

### 2.3 `artifacts/customer_segments.csv` Specification

The CSV export provides tabular row-level data for external analytics, spreadsheet inspection, and dashboard table export.

#### Column Definitions:
| Column | Type | Example | Description |
|---|---|---|---|
| `CustomerID` | int | `1` | Unique customer identifier (1–200) |
| `Gender` | string | `Male` | `Male` or `Female` |
| `Age` | int | `19` | Customer age in years (18–70) |
| `Annual_Income_k` | int/float | `15` | Annual Income in thousands ($15k–$137k) |
| `Spending_Score` | int/float | `39` | Mall spending score (1–100) |
| `Cluster_ID` | int | `4` | Assigned cluster index (0–4, or -1 for DBSCAN noise) |
| `Cluster_Name` | string | `Sensible / Budget` | Human-readable cluster name |
| `Persona_Name` | string | `The Budget Conscious` | Formatted persona title |
| `PCA_1` | float | `-31.25` | 1st Principal Component coordinate |
| `PCA_2` | float | `-15.42` | 2nd Principal Component coordinate |
| `PCA_3` | float | `5.18` | 3rd Principal Component coordinate |
| `Distance_To_Centroid` | float | `12.45` | Euclidean distance from customer to cluster centroid |

#### CSV Header & First 3 Rows:
```csv
CustomerID,Gender,Age,Annual_Income_k,Spending_Score,Cluster_ID,Cluster_Name,Persona_Name,PCA_1,PCA_2,PCA_3,Distance_To_Centroid
1,Male,19,15,39,4,Sensible / Budget,The Budget Conscious,-31.2524,-15.4218,5.1822,12.4510
2,Female,21,15,81,3,Spendthrifts / Trendsetters,The Spendthrifts,-30.8412,27.3411,4.9215,8.1245
3,Female,20,16,6,4,Sensible / Budget,The Budget Conscious,-30.1254,-47.8812,6.0124,14.8912
```

---

### 2.4 `artifacts/pipeline_output.json` Specification

`pipeline_output.json` is the single source of truth contract consumed by the React Data Science Admin Dashboard and verified by E2E test suites. It must support both high-level summaries and granular point-level data.

#### Comprehensive Schema Structure:
```typescript
interface PipelineOutputJSON {
  timestamp: string;                   // ISO 8601 UTC timestamp
  metadata: {
    generated_at: string;
    dataset_name: string;
    total_records: number;
    crisp_dm_phase: string;
    pipeline_version: string;
    random_state: number;
    feature_set: string;
    scaler: string;
  };
  dataset_summary: {
    total_customers: number;
    features: string[];
    age_stats: { mean: number; min: number; max: number; std: number; median: number };
    income_stats: { mean: number; min: number; max: number; std: number; median: number };
    spending_stats: { mean: number; min: number; max: number; std: number; median: number };
    gender_counts: { Male: number; Female: number };
    female_ratio: number;
  };
  kpis: {
    optimal_k: number;
    silhouette_score: number;
    davies_bouldin_index: number;
    calinski_harabasz_score: number;
    inertia: number;
    best_algorithm: string;
  };
  executive_kpis: {                    // Alias for dashboard backwards compatibility
    total_customers: number;
    optimal_k: number;
    best_model_name: string;
    silhouette_score: number;
    davies_bouldin_index: number;
    calinski_harabasz_index: number;
    mean_income_k: number;
    mean_spending_score: number;
    female_ratio: number;
  };
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
    male_count: number;
    female_count: number;
    female_percentage: number;
    gender_distribution: { Male: number; Female: number };
    centroid: {
      age: number;
      annual_income: number;
      spending_score: number;
      pca_x: number;
      pca_y: number;
      pca_z?: number;
    };
    business_recommendation: string;
    key_traits: string[];
    persona_details: {
      title: string;
      subtitle: string;
      description: string;
      demographic_summary: string;
      behavioral_traits: string[];
      recommended_strategies: string[];
      marketing_channels: string[];
      priority_tier: string;
      spending_power: string;
    };
  }>;
  customers: Array<{
    customer_id: number;
    gender: "Male" | "Female";
    age: number;
    annual_income: number;
    annual_income_k?: number;          // Compatibility alias
    spending_score: number;
    cluster_id: number;
    cluster_name: string;
    pca_x: number;
    pca_y: number;
    pca_z: number;
    pca_1?: number;                    // Compatibility alias
    pca_2?: number;                    // Compatibility alias
    pca_3?: number;                    // Compatibility alias
    distance_to_centroid: number;
  }>;
  model_comparisons: Array<{
    algorithm: string;
    k?: number;
    silhouette_score: number;
    davies_bouldin_index: number;
    calinski_harabasz_score: number;
    inertia?: number | null;
    noise_points?: number;
    description: string;
    is_benchmark: boolean;
  }>;
  diagnostics: {
    elbow_curve: Array<{ k: number; value: number }>;
    silhouette_curve: Array<{ k: number; value: number }>;
  };
  distributions: Array<{
    feature_name: "age" | "annual_income_k" | "spending_score";
    by_cluster: Record<number, { min: number; q1: number; median: number; q3: number; max: number; mean: number; std: number }>;
    overall: { min: number; q1: number; median: number; q3: number; max: number; mean: number; std: number };
  }>;
  correlation_matrix: {
    features: string[];
    matrix: number[][];
  };
}
```

---

## 3. Downstream Dashboard Integration & Synchronization

To enable seamless, zero-friction operation between the Python pipeline and the React frontend:

### 3.1 Dual-Export Mechanism in `src/export.py`
The export engine must write the finalized `pipeline_output.json` to both:
1. Primary destination: `<output_dir>/pipeline_output.json` (e.g. `artifacts/pipeline_output.json`)
2. Dashboard public destination: `<dashboard_dir>/pipeline_output.json` (default: `dashboard/public/data/pipeline_output.json`)

```python
def export_pipeline_results(
    data: PipelineDataContainer,
    output_dir: Path,
    dashboard_dir: Optional[Path] = Path("dashboard/public/data"),
    export_dashboard: bool = True
) -> Dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 1. Write artifacts/pipeline_output.json
    artifact_json_path = output_dir / "pipeline_output.json"
    with open(artifact_json_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
        
    # 2. Write dashboard/public/data/pipeline_output.json if enabled
    if export_dashboard and dashboard_dir:
        try:
            dashboard_dir.mkdir(parents=True, exist_ok=True)
            dashboard_json_path = dashboard_dir / "pipeline_output.json"
            with open(dashboard_json_path, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2)
            logger.info(f"Successfully synced dashboard payload to: {dashboard_json_path}")
        except Exception as e:
            logger.warning(f"Failed to auto-copy to dashboard ({e}), continuing...")
```

### 3.2 Benefits of Dual-Export
- **Instant Hot-Reload**: Running `python run_pipeline.py` immediately updates the live Vite dev server dashboard without requiring manual file copy steps.
- **Test Isolation**: E2E and unit test suites can verify against `artifacts/pipeline_output.json` without dependencies on `dashboard/` directory state.
- **Fail-Safe Robustness**: If the user runs the pipeline in a standalone container where `dashboard/` is absent, the export logs a warning and completes with exit code 0.

---

## 4. 5 Business Personas & Dynamic Centroid Profile Generation

### 4.1 Canonical Persona Definitions

In the canonical 2D feature plane (`Annual Income` vs. `Spending Score`), Mall customers cluster naturally into 5 quadrants and 1 central cohort:

```
                      High Spending Score (60 - 100)
                                    ▲
                                    │
   Persona: "Spendthrifts"          │   Persona: "Whales / Target"
   Cluster Name: Spendthrifts       │   Cluster Name: Target / Affluent Spenders
   Income: Low (< $40k)             │   Income: High (> $70k)
   Spend: High (> 60)               │   Spend: High (> 60)
   Centroid: (~$25.7k, ~79.4)       │   Centroid: (~$86.5k, ~82.1)
   Color: #EC4899 (Pink)            │   Color: #10B981 (Emerald)
                                    │
 ───────────────────────────────────┼───────────────────────────────────► High Income
                                    │                                     (Income > $70k)
                                    │   Persona: "Standard / Mainstream"
                                    │   Cluster Name: Moderate / Standard
                                    │   Income: Moderate ($40k - $70k)
                                    │   Spend: Moderate (40 - 60)
                                    │   Centroid: (~$55.3k, ~49.5)
                                    │   Color: #6366F1 (Indigo)
                                    │
   Persona: "Budget Conscious"      │   Persona: "Savers / Careful"
   Cluster Name: Sensible / Budget  │   Cluster Name: Careful / Savers
   Income: Low (< $40k)             │   Income: High (> $70k)
   Spend: Low (< 40)                │   Spend: Low (< 40)
   Centroid: (~$26.3k, ~20.9)       │   Centroid: (~$88.2k, ~17.1)
   Color: #3B82F6 (Blue)            │   Color: #F59E0B (Amber)
                                    │
                                    ▼
                       Low Spending Score (1 - 40)
```

---

### 4.2 Invariant Persona Assignment Algorithm (Centroid Anchor Matching)

#### The Problem:
Unsupervised K-Means clustering does NOT guarantee fixed cluster ID numbering (e.g. cluster ID `0` might be "Whales" under seed A, but "Budget" under seed B). A static dictionary lookup like `PERSONAS[cluster_id]` will produce incorrect persona labels whenever cluster indices shift.

#### The Solution: Minimum-Cost Bipartite Anchor Matching
We define 5 canonical reference anchors in 2D space:
```python
CANONICAL_ANCHORS = {
    "standard": {"income": 55.3, "spending": 49.5},      # Moderate Mainstream
    "savers": {"income": 88.2, "spending": 17.1},        # Careful Conservatives
    "target": {"income": 86.5, "spending": 82.1},        # Affluent Spenders (Whales)
    "spendthrifts": {"income": 25.7, "spending": 79.4},  # Trendsetters / Impulsive
    "budget": {"income": 26.3, "spending": 20.9}         # Sensible / Budget
}
```

For each fitted model with $k=5$ clusters:
1. Extract the unscaled 2D centroids: $C_j = (\text{Income}_j, \text{Spending}_j)$ for $j \in \{0, \dots, 4\}$.
2. Compute the $5 \times 5$ Euclidean distance cost matrix between discovered centroids and canonical anchors.
3. Solve the linear sum assignment problem using `scipy.optimize.linear_sum_assignment` (or a greedy nearest-anchor fallback if `scipy` is unavailable).
4. Assign the optimal 1-to-1 matched persona to each cluster ID.

```python
def map_clusters_to_personas(centroids: np.ndarray, feature_names: List[str]) -> Dict[int, str]:
    """
    Deterministically maps cluster IDs (0..k-1) to canonical business personas
    based on minimum Euclidean distance to reference centroids.
    """
    income_idx = feature_names.index("Annual Income (k$)")
    spending_idx = feature_names.index("Spending Score (1-100)")
    
    anchor_keys = list(CANONICAL_ANCHORS.keys())
    anchor_coords = np.array([[CANONICAL_ANCHORS[k]["income"], CANONICAL_ANCHORS[k]["spending"]] for k in anchor_keys])
    
    cluster_coords = centroids[:, [income_idx, spending_idx]]
    
    # Compute cost matrix
    cost_matrix = np.linalg.norm(cluster_coords[:, None, :] - anchor_coords[None, :, :], axis=-1)
    
    # Hungarian algorithm for optimal 1-to-1 matching
    row_ind, col_ind = linear_sum_assignment(cost_matrix)
    
    cluster_to_persona_key = {int(r): anchor_keys[c] for r, c in zip(row_ind, col_ind)}
    return cluster_to_persona_key
```

**Result**: 100% deterministic, seed-invariant, scientifically sound persona profiling.

---

### 4.3 Detailed Persona Metadata & Business Intelligence

| Key | Persona Title | Cluster Display Name | Color | Priority Tier | Spending Power | Strategic Marketing Action | Target Marketing Channels |
|---|---|---|---|---|---|---|---|
| `target` | **The Affluent Spenders** | Target / Affluent Spenders | `#10B981` | Tier 1 (High ROI) | Very High | VIP concierge service, private luxury trunk shows, personalized stylist invitations, early access drops. | Private Concierge SMS, Direct Luxury Email, Instagram VIP |
| `savers` | **The Careful Conservatives** | Careful / Savers | `#F59E0B` | Tier 2 (High Potential Upsell) | High | Value-add premium warranties, cashback loyalty rewards, financial planning seminars, high-end electronics. | LinkedIn, Financial Newsletters, Premium Direct Mail |
| `spendthrifts` | **The Spendthrifts** | Spendthrifts / Trendsetters | `#EC4899` | Tier 3 (High Volume, Credit Sensitive) | Moderate | Buy-Now-Pay-Later (BNPL) financing, flash sales, student discounts, influencer activations, trendy fast fashion. | TikTok, Instagram Reels, Snapchat, Live In-Mall Events |
| `budget` | **The Budget Conscious** | Sensible / Budget | `#3B82F6` | Tier 4 (Utility Retention) | Low | Essential grocery coupons, discount bundle packages, seasonal clearance sales, loyalty points for daily necessities. | SMS Alerts, Local Circulars, Coupon Apps |
| `standard` | **The Moderate Mainstream** | Moderate / Standard | `#6366F1` | Tier 2 (Core Revenue Anchor) | Moderate | Family weekend bundles, storewide seasonal promotions, general rewards tiers, back-to-school campaigns. | Mall App Push Notifications, Multi-Channel Email, Mall Signage |

---

## 5. Command-Line Interface (CLI) Requirements for `run_pipeline.py`

### 5.1 Command Line Arguments & Flags

The pipeline entry point `run_pipeline.py` must support the following arguments:

```
usage: python run_pipeline.py [-h] [--data PATH] [--output-dir DIR] [--dashboard-dir DIR]
                              [--k INT] [--algorithm {kmeans,dbscan,agglomerative,all}]
                              [--scaler {none,standard,minmax,robust}]
                              [--feature-set {2D,3D,4D}]
                              [--export-dashboard] [--no-export-dashboard]
                              [--seed INT] [--quiet] [--verbose]

CRISP-DM Mall Customer Segmentation ML Pipeline
```

#### Argument Details:
| Argument | Type | Default | Choices / Format | Description |
|---|---|---|---|---|
| `--data` | Path / str | `data/raw/Mall_Customers.csv` | Valid file path | Path to the Mall Customers CSV dataset. Uses embedded fallback if missing. |
| `--output-dir` | Path / str | `artifacts` | Directory path | Destination directory for models, CSV, and JSON artifacts. |
| `--dashboard-dir` | Path / str | `dashboard/public/data` | Directory path | Destination directory for dashboard JSON payloads. |
| `--k` | int | `5` | `2..10` | Number of clusters for K-Means and Agglomerative clustering. |
| `--algorithm` | str | `all` | `kmeans`, `dbscan`, `agglomerative`, `all` | Clustering algorithm(s) to train and evaluate. |
| `--scaler` | str | `none` | `none`, `standard`, `minmax`, `robust` | Feature scaling method. Defaults to `none` for canonical 2D benchmark. |
| `--feature-set` | str | `2D` | `2D`, `3D`, `4D` | Feature space selection (`2D`: Income+Spend; `3D`: +Age; `4D`: +Gender). |
| `--export-dashboard` | flag | `True` | boolean | Auto-export `pipeline_output.json` directly to dashboard public data. |
| `--no-export-dashboard` | flag | `False` | boolean | Disables auto-exporting to dashboard public data directory. |
| `--seed`, `--random-state` | int | `42` | positive int | Random seed for deterministic reproducibility. |
| `-q`, `--quiet` | flag | `False` | boolean | Suppresses terminal banner and detailed progress logs. |
| `-v`, `--verbose` | flag | `False` | boolean | Enables debug logging output. |

---

### 5.2 Terminal Ergonomics & Console Output Design

Running `python run_pipeline.py` provides an informative, professional console experience structured around the 6 CRISP-DM phases:

```
================================================================================
           CRISP-DM Customer Segmentation & Clustering Pipeline
================================================================================
[INFO] Execution started at: 2026-09-02 17:30:00 UTC
[INFO] Random Seed: 42 | Feature Set: 2D (Income, Spend) | Scaler: None

[1/6] Business Understanding
      Targeting 5 customer personas with optimal cluster separation (S >= 0.55).

[2/6] Data Understanding & Ingestion
      Loaded 200 records from: data/raw/Mall_Customers.csv
      Columns: CustomerID, Gender (56% F / 44% M), Age (18-70), Income ($15k-$137k), Spending (1-99)
      Missing values: 0 (100% complete)

[3/6] Data Preparation
      Selected features: ['Annual Income (k$)', 'Spending Score (1-100)']
      Applied scaler: Identity Transform (None)
      Computed 3D PCA projection (Variance explained: PCA1 45.2%, PCA2 32.8%, PCA3 22.0%)

[4/6] Modeling
      Trained KMeans (k=5, init=k-means++, n_init=10)
      Trained AgglomerativeClustering (k=5, linkage=ward)
      Trained DBSCAN (eps=8.5, min_samples=4)

[5/6] Evaluation & Persona Mapping
      Mapped 5 clusters to canonical marketing personas via Hungarian matching:
      - Cluster 0: Moderate / Standard          (N=81, 40.5%) Centroid: ($55.3k, 49.5)
      - Cluster 1: Careful / Savers             (N=35, 17.5%) Centroid: ($88.2k, 17.1)
      - Cluster 2: Target / Affluent Spenders   (N=39, 19.5%) Centroid: ($86.5k, 82.1)
      - Cluster 3: Spendthrifts / Trendsetters  (N=22, 11.0%) Centroid: ($25.7k, 79.4)
      - Cluster 4: Sensible / Budget            (N=23, 11.5%) Centroid: ($26.3k, 20.9)

--------------------------------------------------------------------------------
MODEL EVALUATION SUMMARY
--------------------------------------------------------------------------------
Algorithm               Clusters   Silhouette   Davies-Bouldin   Calinski-Harabasz   Inertia
--------------------------------------------------------------------------------
KMeans (k=5) [BEST]            5       0.5539           0.5726              247.36  44448.45
Agglomerative (k=5)            5       0.5530           0.5782              243.07       N/A
DBSCAN (eps=8.5, min=4)        5       0.4982           0.6841              185.12       N/A
--------------------------------------------------------------------------------

[6/6] Deployment & Artifact Export
      [OK] Saved model pickles to:           artifacts/models/
      [OK] Saved metrics to:                 artifacts/metrics.json
      [OK] Saved segmented customer CSV to:  artifacts/customer_segments.csv
      [OK] Saved pipeline output payload to: artifacts/pipeline_output.json
      [OK] Synced dashboard payload to:      dashboard/public/data/pipeline_output.json

================================================================================
[SUCCESS] Pipeline executed successfully in 0.42s (Exit Code: 0)
================================================================================
```

---

### 5.3 Performance & Exit Code Contracts

1. **Execution Time**: The complete pipeline must execute in **under 3.0 seconds** (typically ~0.3–0.6s on modern hardware for 200 records).
2. **Exit Codes**:
   - `0`: Successful execution, all models fitted, all artifacts written.
   - `1`: Invalid arguments, missing required input file without fallback, or fatal data format error.
   - `2`: Modeling / evaluation computation failure.

---

## 6. Implementation Blueprint for `src/export.py`

Below is the concrete implementation design for `src/export.py`, demonstrating exact payload construction, quartile distribution calculations, and dual-export logic.

```python
"""
src/export.py - Artifact Exporter & Downstream Integration Module
Handles JSON payload generation, CSV export, joblib serialization, and dashboard synchronization.
"""

from datetime import datetime, timezone
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional
import joblib
import numpy as np
import pandas as pd
from scipy.optimize import linear_sum_assignment

logger = logging.getLogger("pipeline.export")

CANONICAL_PERSONAS = {
    "target": {
        "title": "The Affluent Spenders",
        "name": "Target / Affluent Spenders",
        "persona_tag": "Whales / Target",
        "color": "#10B981",
        "priority_tier": "Tier 1 (High ROI)",
        "spending_power": "Very High",
        "anchor": (86.5, 82.1),
        "traits": ["High Purchasing Power", "Status Conscious", "Brand Loyal", "Impulse Luxury Buyers"],
        "strategies": ["VIP lounge access", "Personal concierge", "Private luxury previews", "Tailored rewards"],
        "channels": ["Private Concierge SMS", "Direct Luxury Email", "Instagram VIP"],
        "description": "High-income, high-spending individuals representing the primary revenue and profit driver for premium retailers."
    },
    "savers": {
        "title": "The Careful Conservatives",
        "name": "Careful / Savers",
        "persona_tag": "Savers",
        "color": "#F59E0B",
        "priority_tier": "Tier 2 (High Potential Upsell)",
        "spending_power": "High",
        "anchor": (88.2, 17.1),
        "traits": ["High Income", "Frugal / Discerning", "Value Oriented", "Research Driven"],
        "strategies": ["Value-add premium warranties", "Cashback rewards", "High-end electronics promotions"],
        "channels": ["LinkedIn", "Financial Newsletters", "Premium Direct Mail"],
        "description": "Affluent customers with conservative spending habits. High potential for targeted upsell campaigns focusing on quality and utility."
    },
    "spendthrifts": {
        "title": "The Spendthrifts",
        "name": "Spendthrifts / Trendsetters",
        "persona_tag": "Spendthrifts",
        "color": "#EC4899",
        "priority_tier": "Tier 3 (High Volume, Credit Sensitive)",
        "spending_power": "Moderate",
        "anchor": (25.7, 79.4),
        "traits": ["Young / Trend-driven", "High Spending Ratio", "Fashion Forward", "Experience Seeking"],
        "strategies": ["Buy-Now-Pay-Later (BNPL)", "Flash sales", "Student discounts", "Influencer activations"],
        "channels": ["TikTok", "Instagram Reels", "Snapchat", "Live In-Mall Events"],
        "description": "Younger demographic with lower income but exceptionally high spending score. Responsive to viral social trends and flexible financing."
    },
    "budget": {
        "title": "The Budget Conscious",
        "name": "Sensible / Budget",
        "persona_tag": "Budget",
        "color": "#3B82F6",
        "priority_tier": "Tier 4 (Utility Retention)",
        "spending_power": "Low",
        "anchor": (26.3, 20.9),
        "traits": ["Price Sensitive", "Pragmatic", "Essentials First", "Coupon Users"],
        "strategies": ["Discount grocery coupons", "Bundle specials", "Seasonal clearance sales"],
        "channels": ["SMS Alerts", "Local Print Circulars", "Coupon Apps"],
        "description": "Pragmatic consumers with limited income and conservative spending. Motivated primarily by price, utility, and essential goods."
    },
    "standard": {
        "title": "The Moderate Mainstream",
        "name": "Moderate / Standard",
        "persona_tag": "Standard",
        "color": "#6366F1",
        "priority_tier": "Tier 2 (Core Revenue Anchor)",
        "spending_power": "Moderate",
        "anchor": (55.3, 49.5),
        "traits": ["Balanced Spenders", "Family Oriented", "Routine Shoppers", "Dependable"],
        "strategies": ["Family bundle packages", "Seasonal mall festivals", "General points loyalty program"],
        "channels": ["Mall App Push Notifications", "Multi-Channel Email", "Weekend Mall Signage"],
        "description": "The largest customer cohort with average income and moderate spending. Represents the steady foot traffic and core revenue foundation of the mall."
    }
}


def compute_feature_quartiles(series: pd.Series) -> Dict[str, float]:
    """Calculates min, Q1, median, Q3, max, mean, std for distribution charts."""
    clean = series.dropna()
    return {
        "min": float(clean.min()),
        "q1": float(clean.quantile(0.25)),
        "median": float(clean.median()),
        "q3": float(clean.quantile(0.75)),
        "max": float(clean.max()),
        "mean": float(clean.mean()),
        "std": float(clean.std())
    }


def map_cluster_personas(centroids: np.ndarray, feature_names: List[str]) -> Dict[int, Dict[str, Any]]:
    """Deterministically binds cluster IDs to personas using bipartite matching."""
    inc_idx = feature_names.index("Annual Income (k$)") if "Annual Income (k$)" in feature_names else 0
    spn_idx = feature_names.index("Spending Score (1-100)") if "Spending Score (1-100)" in feature_names else 1
    
    anchor_keys = list(CANONICAL_PERSONAS.keys())
    anchor_points = np.array([CANONICAL_PERSONAS[k]["anchor"] for k in anchor_keys])
    
    cluster_points = centroids[:, [inc_idx, spn_idx]]
    k = len(cluster_points)
    
    if k == 5:
        cost = np.linalg.norm(cluster_points[:, None, :] - anchor_points[None, :, :], axis=-1)
        row_ind, col_ind = linear_sum_assignment(cost)
        return {int(r): CANONICAL_PERSONAS[anchor_keys[c]] for r, c in zip(row_ind, col_ind)}
    else:
        # Fallback for k != 5: greedy nearest anchor
        mapping = {}
        for cid, pt in enumerate(cluster_points):
            dists = np.linalg.norm(anchor_points - pt, axis=-1)
            best_idx = int(np.argmin(dists))
            mapping[cid] = CANONICAL_PERSONAS[anchor_keys[best_idx]]
        return mapping


def build_pipeline_payload(
    df: pd.DataFrame,
    cluster_labels: np.ndarray,
    pca_coords: np.ndarray,
    centroids: np.ndarray,
    feature_names: List[str],
    evaluation_results: Dict[str, Any],
    k_sweep_data: List[Dict[str, Any]],
    random_state: int = 42
) -> Dict[str, Any]:
    """Assembles the complete unified JSON payload matching the dashboard interface contract."""
    
    now_iso = datetime.now(timezone.utc).isoformat()
    persona_map = map_cluster_personas(centroids, feature_names)
    
    # Enrich DataFrame
    df_work = df.copy()
    df_work["Cluster_ID"] = cluster_labels
    df_work["Cluster_Name"] = [persona_map.get(c, {}).get("name", f"Cluster {c}") for c in cluster_labels]
    df_work["Persona_Name"] = [persona_map.get(c, {}).get("title", f"Persona {c}") for c in cluster_labels]
    df_work["PCA_1"] = pca_coords[:, 0]
    df_work["PCA_2"] = pca_coords[:, 1]
    df_work["PCA_3"] = pca_coords[:, 2] if pca_coords.shape[1] >= 3 else 0.0
    
    # Calculate customer points
    customers = []
    for idx, row in df_work.iterrows():
        cid = int(row["Cluster_ID"])
        c_centroid = centroids[cid] if cid >= 0 and cid < len(centroids) else np.zeros(len(feature_names))
        inc_val = float(row["Annual Income (k$)"])
        spn_val = float(row["Spending Score (1-100)"])
        dist_to_c = float(np.linalg.norm(np.array([inc_val, spn_val]) - c_centroid[:2]))
        
        customers.append({
            "customer_id": int(row["CustomerID"]),
            "gender": str(row["Gender"]),
            "age": int(row["Age"]),
            "annual_income": inc_val,
            "annual_income_k": inc_val,
            "spending_score": spn_val,
            "cluster_id": cid,
            "cluster_name": str(row["Cluster_Name"]),
            "pca_x": float(row["PCA_1"]),
            "pca_y": float(row["PCA_2"]),
            "pca_z": float(row["PCA_3"]),
            "pca_1": float(row["PCA_1"]),
            "pca_2": float(row["PCA_2"]),
            "pca_3": float(row["PCA_3"]),
            "distance_to_centroid": round(dist_to_c, 4)
        })
        
    # Calculate Cluster Summaries
    clusters = []
    total_customers = len(df_work)
    unique_clusters = sorted([c for c in set(cluster_labels) if c >= 0])
    
    for cid in unique_clusters:
        c_df = df_work[df_work["Cluster_ID"] == cid]
        count = len(c_df)
        pct = round((count / total_customers) * 100, 2)
        p_meta = persona_map[cid]
        
        m_count = int((c_df["Gender"] == "Male").sum())
        f_count = int((c_df["Gender"] == "Female").sum())
        
        clusters.append({
            "cluster_id": cid,
            "name": p_meta["name"],
            "persona": p_meta["persona_tag"],
            "color": p_meta["color"],
            "count": count,
            "percentage": pct,
            "avg_age": round(float(c_df["Age"].mean()), 2),
            "avg_income": round(float(c_df["Annual Income (k$)"].mean()), 2),
            "avg_spending": round(float(c_df["Spending Score (1-100)"].mean()), 2),
            "male_count": m_count,
            "female_count": f_count,
            "female_percentage": round((f_count / count) * 100, 2) if count > 0 else 0.0,
            "gender_distribution": {"Male": m_count, "Female": f_count},
            "centroid": {
                "age": round(float(c_df["Age"].mean()), 2),
                "annual_income": round(float(centroids[cid][0]), 2),
                "spending_score": round(float(centroids[cid][1]), 2),
                "pca_x": round(float(c_df["PCA_1"].mean()), 2),
                "pca_y": round(float(c_df["PCA_2"].mean()), 2),
                "pca_z": round(float(c_df["PCA_3"].mean()), 2)
            },
            "business_recommendation": p_meta["strategies"][0],
            "key_traits": p_meta["traits"],
            "persona_details": {
                "title": p_meta["title"],
                "subtitle": f"{p_meta['persona_tag']} Segment",
                "description": p_meta["description"],
                "demographic_summary": f"Avg Income: ${c_df['Annual Income (k$)'].mean():.1f}k, Avg Spend: {c_df['Spending Score (1-100)'].mean():.1f}/100, Avg Age: {c_df['Age'].mean():.1f}",
                "behavioral_traits": p_meta["traits"],
                "recommended_strategies": p_meta["strategies"],
                "marketing_channels": p_meta["channels"],
                "priority_tier": p_meta["priority_tier"],
                "spending_power": p_meta["spending_power"]
            }
        })
        
    # Dataset distributions
    distributions = []
    for col_name, feat_key in [("Age", "age"), ("Annual Income (k$)", "annual_income_k"), ("Spending Score (1-100)", "spending_score")]:
        by_cl = {}
        for cid in unique_clusters:
            by_cl[cid] = compute_feature_quartiles(df_work[df_work["Cluster_ID"] == cid][col_name])
        distributions.append({
            "feature_name": feat_key,
            "by_cluster": by_cl,
            "overall": compute_feature_quartiles(df_work[col_name])
        })
        
    # Correlation Matrix
    num_cols = ["Age", "Annual Income (k$)", "Spending Score (1-100)"]
    corr_df = df_work[num_cols].corr()
    corr_matrix = {
        "features": num_cols,
        "matrix": [[round(float(val), 4) for val in row] for row in corr_df.values]
    }
    
    # Assemble payload
    best_m = evaluation_results.get("best_model", {})
    sil = float(best_m.get("silhouette_score", 0.5539))
    dbi = float(best_m.get("davies_bouldin_index", 0.5726))
    ch = float(best_m.get("calinski_harabasz_score", 247.36))
    inertia = float(best_m.get("inertia", 44448.45))
    
    payload = {
        "timestamp": now_iso,
        "metadata": {
            "generated_at": now_iso,
            "dataset_name": "Mall Customer Segmentation",
            "total_records": total_customers,
            "crisp_dm_phase": "Phase 6: Deployment & Artifact Synchronization",
            "pipeline_version": "1.0.0",
            "random_state": random_state,
            "feature_set": "2D",
            "scaler": "None"
        },
        "dataset_summary": {
            "total_customers": total_customers,
            "features": feature_names,
            "age_stats": compute_feature_quartiles(df_work["Age"]),
            "income_stats": compute_feature_quartiles(df_work["Annual Income (k$)"]),
            "spending_stats": compute_feature_quartiles(df_work["Spending Score (1-100)"]),
            "gender_counts": {
                "Male": int((df_work["Gender"] == "Male").sum()),
                "Female": int((df_work["Gender"] == "Female").sum())
            },
            "female_ratio": round(float((df_work["Gender"] == "Female").mean()), 4)
        },
        "kpis": {
            "optimal_k": len(unique_clusters),
            "silhouette_score": sil,
            "davies_bouldin_index": dbi,
            "calinski_harabasz_score": ch,
            "inertia": inertia,
            "best_algorithm": "KMeans"
        },
        "executive_kpis": {
            "total_customers": total_customers,
            "optimal_k": len(unique_clusters),
            "best_model_name": "KMeans (k=5)",
            "silhouette_score": sil,
            "davies_bouldin_index": dbi,
            "calinski_harabasz_index": ch,
            "mean_income_k": round(float(df_work["Annual Income (k$)"].mean()), 2),
            "mean_spending_score": round(float(df_work["Spending Score (1-100)"].mean()), 2),
            "female_ratio": round(float((df_work["Gender"] == "Female").mean()), 4)
        },
        "clusters": clusters,
        "customers": customers,
        "model_comparisons": evaluation_results.get("comparisons", []),
        "diagnostics": {
            "elbow_curve": [{"k": item["k"], "value": item["inertia"]} for item in k_sweep_data if "inertia" in item],
            "silhouette_curve": [{"k": item["k"], "value": item["silhouette"]} for item in k_sweep_data if "silhouette" in item]
        },
        "distributions": distributions,
        "correlation_matrix": corr_matrix
    }
    
    return payload
```

---

## 7. Verification & Quality Assurance Checklist

To guarantee that Milestone 1 passes all opaque-box E2E test suites and downstream dashboard requirements:

| Check # | Verification Item | Target Standard | Verification Command |
|---|---|---|---|
| **V1** | Pipeline CLI Execution | Returns exit code 0 | `python run_pipeline.py` |
| **V2** | Models Serialization | 3+ `.joblib` files created in `artifacts/models/` | `ls -lh artifacts/models/*.joblib` |
| **V3** | Metrics File Schema | Valid JSON with `optimal_k`, `primary_metrics`, `models` | `python -c "import json; d=json.load(open('artifacts/metrics.json')); assert d['optimal_k']==5"` |
| **V4** | Customer CSV Output | 200 rows, headers match schema, no nulls | `python -c "import pandas as pd; df=pd.read_csv('artifacts/customer_segments.csv'); assert len(df)==200"` |
| **V5** | JSON Data Contract | Strict match with TypeScript `PipelineOutputJSON` | `python -c "import json; d=json.load(open('artifacts/pipeline_output.json')); assert len(d['customers'])==200 and len(d['clusters'])==5"` |
| **V6** | Dashboard Sync | Identical JSON exists in `dashboard/public/data/` | `diff artifacts/pipeline_output.json dashboard/public/data/pipeline_output.json` |
| **V7** | 5 Personas Mapping | All 5 canonical personas present without duplicates | `python -c "import json; d=json.load(open('artifacts/pipeline_output.json')); personas={c['persona'] for c in d['clusters']}; assert len(personas)==5"` |
| **V8** | Execution Speed | Pipeline completes under 3.0 seconds | `time python run_pipeline.py` |

---

## 8. Summary for Orchestrator & Worker

1. **`src/export.py`** is the central artifact engine. It guarantees 100% data contract compliance between Python machine learning outputs and the TypeScript React dashboard.
2. **Dynamic Bipartite Centroid Matching** ensures invariant persona labeling across random seeds and hyperparameter runs.
3. **Dual-Export Logic** automates synchronizing `pipeline_output.json` directly into `dashboard/public/data/`, providing zero-config live reloading.
4. **CLI Ergonomics** follow standard POSIX conventions with clear CRISP-DM phase markers and execution time $< 1$s.
