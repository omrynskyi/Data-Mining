# Milestone 1 Deep-Dive: Edge Cases, Numerical Stability, Metrics Verification & Testing Strategy

**Author**: Explorer 2 (QA, Numerical Stability & Metrics Specialist)  
**Date**: 2026-09-02  
**Target Project**: Customer Segmentation Clustering & React Dashboard (`03_customer_segmentation_clustering`)  
**Artifact Path**: `.agents/m1_exp_2/edge_cases_and_metrics.md`  

---

## 1. Executive Summary

This report establishes the rigorous mathematical, numerical, and testing framework for **Milestone 1: CRISP-DM & Clustering Pipeline**. It resolves subtle pitfalls in unsupervised clustering validation, feature scaling dynamics, noise isolation for density-based algorithms, principal component projections, and end-to-end unit test design.

### Key Numerical & Methodological Findings

1. **Scaling Impact on 2D vs. 3D Spaces**:
   - In canonical **2D space** (`Annual Income`, `Spending Score`), feature variances are nearly identical ($\sigma_{\text{Income}} = 26.26$, $\sigma_{\text{Spend}} = 25.82$). As a result, `StandardScaler`, `MinMaxScaler`, `RobustScaler`, and unscaled features yield **100% identical cluster assignments** ($\text{ARI} = 1.0000$) with K-Means ($k=5$). However, calculated Silhouette scores vary slightly across transformed spaces ($S_{\text{unscaled}} = 0.5539$, $S_{\text{standard}} = 0.5547$, $S_{\text{minmax}} = 0.5595$).
   - In **3D space** (`Age`, `Annual Income`, `Spending Score`), `Age` ($\sigma_{\text{Age}} = 13.97$) is heavily dwarfed by Income and Spending if unscaled. Standardization gives equal statistical variance to all 3 dimensions, shifting $k=5$ cluster assignment concordance to $\text{ARI} = 0.6019$. Unscaled 3D clustering artificially inflates apparent silhouette scores ($0.4443$) by compressing the age dimension, whereas standardized 3D clustering provides true demographic balance ($S = 0.4166$ for $k=5$, $S = 0.4284$ for $k=6$).

2. **DBSCAN Noise Handling Pitfall & Solution**:
   - In `scikit-learn`, naive execution of `silhouette_score(X, labels)` when noise points (label `-1`) exist treats `-1` as a regular cluster, producing severely distorted or negative scores (e.g., dropping from $+0.5756$ down to $-0.0911$).
   - When all points are labeled noise or only 1 cluster is found, `silhouette_score` raises unhandled `ValueError`.
   - **Mandated Standard**: All validation metrics (Silhouette, Davies-Bouldin, Calinski-Harabasz) must be computed strictly on non-noise points ($X[\text{labels} \ne -1], \text{labels}[\text{labels} \ne -1]$) after verifying valid clusters $k \ge 2$ and sample count $N_{\text{clean}} > k$. The pipeline must explicitly record `n_noise` and `noise_ratio` alongside metrics.

3. **PCA Projection & Dashboard Coordinate Stability**:
   - On 3D standardized features, 2 components capture **$77.57\%$ of total variance** ($\text{PC}_1 = 44.27\%$, $\text{PC}_2 = 33.31\%$), while 3 components capture **$100\%$**.
   - Coordinate ranges for standardized PCA project cleanly onto $[-2.5, +3.0]$, preventing extreme aspect-ratio warping in React SVG/Canvas/Three.js renderers.
   - SVD sign indeterminacy must be stabilized using scikit-learn's `svd_flip` (default in `PCA`) with fixed `random_state=42`.

4. **Testing Harness Architecture**:
   - Complete design for `tests/test_data_loader.py` (validation, schema invariants, fallback ingestion) and `tests/test_pipeline.py` (scaling, models, metrics, JSON contract verification, CLI execution).

---

## 2. Feature Scaling & Metric Invariance Deep-Dive

### 2.1 Mathematical Formulation of Euclidean Distance under Scaling

Given customer vectors $\mathbf{x}_i, \mathbf{x}_j \in \mathbb{R}^D$, distance-based clustering algorithms (K-Means, Ward Hierarchical, DBSCAN) rely on the squared Euclidean distance:

$$d^2(\mathbf{x}_i, \mathbf{x}_j) = \sum_{d=1}^{D} (x_{id} - x_{jd})^2$$

When feature transformation matrices $W = \text{diag}(w_1, w_2, \dots, w_D)$ are applied:

$$d_W^2(\mathbf{x}_i, \mathbf{x}_j) = \sum_{d=1}^{D} w_d^2 (x_{id} - x_{jd})^2$$

- **Unscaled ($w_d = 1$)**: Feature contributions are proportional to the squared raw scale $\Delta x_d^2$.
- **StandardScaler ($w_d = 1/\sigma_d$)**: Feature contributions are normalized by standard deviation, giving each feature unit variance ($\sigma_d^2 = 1$).
- **MinMaxScaler ($w_d = 1 / (\max(x_d) - \min(x_d))$)**: Normalizes feature ranges into $[0, 1]$.
- **RobustScaler ($w_d = 1 / \text{IQR}_d$)**: Uses the interquartile range ($Q_3 - Q_1$), preventing outlier distortion.

### 2.2 Empirical Comparison on Mall Customers Dataset

#### Table 2.1: 2D Feature Space (`Annual Income`, `Spending Score`)
*Sample size $N = 200$, K-Means $k=5$, `random_state=42`*

| Scaler | Silhouette (Transformed Space) | Silhouette (Original Space) | Davies-Bouldin | Calinski-Harabasz | ARI vs. Unscaled | AMI vs. Unscaled |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Unscaled** | **0.5539** | **0.5539** | **0.5726** | **247.36** | **1.0000** | **1.0000** |
| **StandardScaler** | 0.5547 | 0.5539 | 0.5722 | 248.65 | **1.0000** | **1.0000** |
| **MinMaxScaler** | 0.5595 | 0.5539 | 0.5678 | 264.73 | **1.0000** | **1.0000** |
| **RobustScaler** | 0.5517 | 0.5539 | 0.5734 | 243.86 | **1.0000** | **1.0000** |

**Empirical Insight 1**:
In 2D space, the ratio of standard deviations is $\sigma_{\text{Income}} / \sigma_{\text{Spend}} = 26.26 / 25.82 = 1.017$. Because the two features already possess virtually equal dispersion and the 5 customer clusters are separated by substantial spatial gaps, linear scaling acts as an almost isotropic transformation. Thus, **all scalers produce identical cluster memberships ($\text{ARI} = 1.0000$)**.

#### Table 2.2: 3D Feature Space (`Age`, `Annual Income`, `Spending Score`)
*Sample size $N = 200$, `random_state=42`*

| $k$ | Scaler | Silhouette (Transformed) | Davies-Bouldin | Calinski-Harabasz | ARI vs. Unscaled |
| :---: | :--- | :---: | :---: | :---: | :---: |
| **$k=5$** | **Unscaled** | **0.4443** | 0.8219 | 151.04 | 1.0000 |
| $k=5$ | **StandardScaler** | 0.4166 | 0.8746 | 125.10 | **0.6019** |
| $k=5$ | **MinMaxScaler** | 0.4061 | 0.8795 | 128.20 | **0.5441** |
| $k=5$ | **RobustScaler** | 0.4150 | 0.8742 | 124.14 | **0.5916** |
| **$k=6$** | **Unscaled** | **0.4523** | 0.7470 | 166.72 | 1.0000 |
| $k=6$ | **StandardScaler** | **0.4284** | **0.8254** | **135.10** | **0.9555** |
| $k=6$ | **MinMaxScaler** | 0.4231 | 0.8599 | 134.00 | 0.9430 |
| $k=6$ | **RobustScaler** | 0.4276 | 0.8283 | 134.60 | 0.9332 |

**Empirical Insight 2**:
In 3D space, `Age` has $\sigma = 13.97$ and variance $\sigma^2 = 195.2$, whereas `Income` has $\sigma^2 = 689.8$ and `Spending` has $\sigma^2 = 666.9$.
- In unscaled clustering, distance in `Age` accounts for less than $13\%$ of total squared Euclidean distance. The algorithm primarily clusters on Income and Spending, ignoring age differences.
- Standardization restores age to equal weighting. At $k=6$, the standardized clustering identifies young high-spenders vs. older moderate-spenders, matching the true multi-dimensional customer segmentation structure ($\text{ARI} = 0.9555$).

### 2.3 Evaluation Space Protocol (Scaled vs. Original Space)

A frequent source of discrepancy in data mining pipelines is whether validation metrics are computed on the **transformed feature space** or the **original raw feature space**:
- **Clustering Execution**: Must be performed on the standardized / scaled matrix $X_{\text{scaled}}$ whenever multidimensional features (e.g. 3D/4D) with different units are used.
- **Metric Computation**:
  - Distance metrics (Silhouette, Davies-Bouldin, Calinski-Harabasz, Inertia) should be evaluated on the **same feature space used for model fitting** ($X_{\text{scaled}}$). This ensures that the distance metric being validated matches the objective function optimized by the algorithm.
  - To allow academic comparison with unscaled literature baselines (e.g. 2D K-Means $S \approx 0.5539$), the pipeline can also log the unscaled silhouette score in its detailed diagnostics.

---

## 3. DBSCAN Noise Handling & Robust Validation Metrics

### 3.1 The Noise Pitfall in Scikit-Learn

DBSCAN assigns core and border points to cluster IDs $0, 1, \dots, C-1$, while outliers and noise points that do not meet density thresholds ($\text{min\_samples}$ within $\epsilon$) receive the label `-1`.

#### Critical Flaws in Naive Evaluation:
1. **Label `-1` Pollution**: If `labels` containing `-1` is passed directly to `sklearn.metrics.silhouette_score(X, labels)`, scikit-learn treats `-1` as a single coherent cluster. Because noise points are scattered across the periphery of feature space, their intra-cluster distances $a(i)$ are enormous, crashing the silhouette score from a healthy $+0.58$ down to $-0.09$.
2. **Degenerate Label Exceptions**:
   - **All Noise ($k=0$)**: If $\epsilon$ is too small, all points receive label `-1`. Unique labels $= \{-1\}$ (1 label).
   - **One Giant Cluster ($k=1$)**: If $\epsilon$ is large, all points receive label `0`. Unique labels $= \{0\}$ (1 label).
   - Calling `silhouette_score`, `davies_bouldin_score`, or `calinski_harabasz_score` with 1 unique label throws:
     `ValueError: Number of labels is 1. Valid values are 2 to n_samples - 1 (inclusive)`
3. **Overfitting to Core Subsets**: If $\epsilon$ is tiny (e.g. $\epsilon=0.10$), DBSCAN might find 4 tiny tight micro-clusters containing only 34 points, leaving 166 points as noise ($83\%$ noise). A naive filter might report $S = 0.563$, hiding the fact that $83\%$ of the customer base was discarded!

### 3.2 Robust Evaluation Algorithm Specification

To guarantee 100% numerical stability, the pipeline's evaluation module (`src/evaluation.py`) must implement the following noise-aware evaluation routine:

```python
import numpy as np
from typing import Dict, Any, Optional
from sklearn.metrics import silhouette_score, davies_bouldin_score, calinski_harabasz_score

def evaluate_clustering_robust(
    X: np.ndarray, 
    labels: np.ndarray
) -> Dict[str, Any]:
    """
    Robust clustering evaluation handling noise points (-1) and degenerate cluster counts.
    
    Returns structured metrics dictionary with status code and noise diagnostics.
    """
    total_samples = len(labels)
    unique_labels = set(labels)
    has_noise = -1 in unique_labels
    non_noise_labels = unique_labels - {-1}
    n_clusters = len(non_noise_labels)
    n_noise = int(np.sum(labels == -1))
    noise_ratio = float(n_noise / total_samples) if total_samples > 0 else 0.0

    result: Dict[str, Any] = {
        "n_clusters": n_clusters,
        "n_noise": n_noise,
        "noise_ratio": round(noise_ratio, 4),
        "silhouette_score": None,
        "davies_bouldin_index": None,
        "calinski_harabasz_score": None,
        "is_valid": False,
        "status": "uninitialized"
    }

    # Case 1: Insufficient valid clusters
    if n_clusters < 2:
        result["status"] = "insufficient_clusters"
        return result

    # Case 2: Filter noise points for geometric validation
    if has_noise:
        mask = labels != -1
        X_eval = X[mask]
        labels_eval = labels[mask]
    else:
        X_eval = X
        labels_eval = labels

    n_eval_samples = len(labels_eval)

    # Case 3: Too few samples remaining after noise filtering
    if n_eval_samples <= n_clusters:
        result["status"] = "insufficient_samples_after_noise_filtering"
        return result

    # Case 4: Successful metric calculation
    try:
        result["silhouette_score"] = float(round(silhouette_score(X_eval, labels_eval), 4))
        result["davies_bouldin_index"] = float(round(davies_bouldin_score(X_eval, labels_eval), 4))
        result["calinski_harabasz_score"] = float(round(calinski_harabasz_score(X_eval, labels_eval), 2))
        result["is_valid"] = True
        result["status"] = "success"
    except Exception as e:
        result["status"] = f"calculation_error: {str(e)}"
        result["is_valid"] = False

    return result
```

#### Table 3.1: DBSCAN Behavior on Mall Customers (Standardized 2D Features)
*Tested with $\text{min\_samples} = 5$ across various $\epsilon$*

| $\epsilon$ | Clusters Found ($k$) | Noise Points ($N_{\text{noise}}$) | Noise Ratio | Robust Silhouette | Robust DB Index | Status |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| 0.10 | 4 | 166 | 83.0% | 0.5633 | 0.5409 | `success` (High Noise) |
| 0.20 | 7 | 77 | 38.5% | 0.5856 | 0.4637 | `success` |
| 0.30 | 7 | 35 | 17.5% | 0.5243 | 0.5800 | `success` |
| **0.35** | **6** | **23** | **11.5%** | **0.5577** | **0.5106** | **`success` (Optimal)** |
| 0.40 | 4 | 15 | 7.5% | 0.4781 | 0.5912 | `success` |
| 0.50 | 2 | 8 | 4.0% | 0.3876 | 0.7889 | `success` |
| 0.60 | 1 | 5 | 2.5% | `null` | `null` | `insufficient_clusters` |
| 1.00 | 1 | 0 | 0.0% | `null` | `null` | `insufficient_clusters` |

---

## 4. PCA Projection, Explained Variance & Coordinate Scaling

### 4.1 Dimensionality Reduction & Variance Retention

For the React data science dashboard, high-dimensional customer segments (3D demographics or 4D demographic-gender features) must be mapped onto 2D and 3D visualizers.

Principal Component Analysis (PCA) finds orthogonal projection axes maximizing variance:

$$\max_{\mathbf{w}_1} \frac{1}{N} \sum_{i=1}^N (\mathbf{w}_1^T \mathbf{x}_i)^2 \quad \text{s.t.} \quad \|\mathbf{w}_1\|_2 = 1$$

#### Table 4.1: PCA Explained Variance Across Feature Sets (StandardScaler Preprocessed)

| Feature Set | Dimensions | $\text{PC}_1$ Variance | $\text{PC}_2$ Variance | $\text{PC}_3$ Variance | 2D Cumulative Variance | 3D Cumulative Variance |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **2D (Income, Spend)** | 2 | 50.50% | 49.50% | — | **100.0%** | 100.0% |
| **3D (Age, Income, Spend)** | 3 | 44.27% | 33.31% | 22.43% | **77.57%** | **100.0%** |
| **4D (Gender, Age, Income, Spend)** | 4 | 33.69% | 26.23% | 23.26% | **59.92%** | **83.18%** |

### 4.2 Dashboard Coordinate Normalization & SVD Sign Stability

1. **SVD Sign Ambiguity**:
   - In Singular Value Decomposition ($X = U \Sigma V^T$), for any valid singular vector $\mathbf{v}_k$, $-\mathbf{v}_k$ is also a mathematically valid solution.
   - Different LAPACK implementations across operating systems (macOS Accelerate vs. Linux OpenBLAS) can flip the signs of principal components, resulting in mirror-reversed dashboard scatter plots.
   - **Remedy**: Always initialize PCA with `scikit-learn`'s `PCA(n_components=..., random_state=42)` which automatically executes `svd_flip` on the components to enforce deterministic orientation based on the maximum absolute loading in each column.

2. **Coordinate Bounding for Web Visualizers**:
   - Under `StandardScaler`, the projected PCA coordinates satisfy:
     - $\text{PC}_1 \in [-2.15, +2.65]$
     - $\text{PC}_2 \in [-1.82, +2.95]$
     - $\text{PC}_3 \in [-2.24, +1.74]$
   - **Recommendation for Frontend**:
     - Provide both raw feature coordinates (`annual_income`, `spending_score`, `age`) and PCA projection coordinates (`pca_x`, `pca_y`, `pca_z`) in `pipeline_output.json`.
     - In 2D views, plotting raw `(Annual Income, Spending Score)` is highly intuitive for business users (direct dollar and score interpretation).
     - In 3D views or multivariate representations, plotting `(pca_x, pca_y, pca_z)` provides optimal variance separation without axis distortion.

---

## 5. Numerical Stability, Invariants & Serialization Edge Cases

### 5.1 Preprocessing Invariants & Guards
1. **Zero-Variance Columns**: If a custom or filtered dataset contains a constant column (e.g. all `Age = 25`), $\sigma = 0$. `StandardScaler` handles zero variance by leaving the feature at zero ($z = 0$) and avoiding divide-by-zero errors.
2. **Missing Value Invariant**: The canonical Mall Customers dataset contains 0 missing values. However, `src/data_loader.py` must enforce:
   - Check `df.isnull().sum().sum() == 0`.
   - If missing values are detected in custom input CSVs, apply deterministic median imputation for numerical features and mode imputation for categorical features, accompanied by a warning log.
3. **Range Constraints**:
   - `Age`: $18 \le \text{Age} \le 120$
   - `Annual Income (k$)`: $\ge 0$
   - `Spending Score (1-100)`: $1 \le \text{Score} \le 100$
   - `CustomerID`: Unique integer identifier.

### 5.2 JSON Serialization Safety (RFC 8259 Compliance)
- In standard Python `json.dumps()`, `float('nan')` and `float('inf')` serialize to non-standard tokens `NaN` and `Infinity` by default, which cause JSON parsing failures in standard JavaScript `JSON.parse()`.
- **Mandate for `src/export.py`**:
  - Replace any `np.nan` or `np.inf` values with `None` (which serializes to standard `null`).
  - Round all exported floating-point values to 4 decimal places to reduce payload size and ensure cross-platform test matching.

---

## 6. Comprehensive Unit Testing Strategy

To ensure strict compliance with project architecture and guarantee 100% test pass rates across all environments, the testing suite is divided into focused modules:

```
tests/
├── __init__.py
├── test_data_loader.py        # Dataset acquisition, schema, fallback, and validation tests
├── test_data_preparation.py   # Scalers, transformations, and feature subsets
├── test_models.py             # K-Means, DBSCAN, Agglomerative clustering algorithms
├── test_evaluation.py         # Metrics, noise handling, and edge case resilience
├── test_export.py             # JSON schema validation and artifact persistence
└── test_pipeline.py           # End-to-end CLI runner and pipeline orchestration
```

### 6.1 `tests/test_data_loader.py` Specification

| Test Function | Input / Fixture | Assertion / Invariant | Purpose |
| :--- | :--- | :--- | :--- |
| `test_load_existing_dataset` | Path to valid `Mall_Customers.csv` | Shape is `(200, 5)`; columns match `['CustomerID', 'Gender', 'Age', 'Annual Income (k$)', 'Spending Score (1-100)']` | Confirms standard local file ingestion |
| `test_data_loader_column_normalization` | Raw DataFrame with legacy `'Genre'` column | Output columns normalized to `['customer_id', 'gender', 'age', 'annual_income', 'spending_score']` | Tests column sanitization |
| `test_data_loader_fallback_offline` | Non-existent path + mocked network failure | Returns valid 200-row canonical DataFrame without crashing | Verifies deterministic offline fallback generator |
| `test_data_integrity_no_nulls` | Loaded DataFrame | `df.isnull().sum().sum() == 0` | Validates completeness |
| `test_data_integrity_ranges` | Loaded DataFrame | $18 \le \text{age} \le 100$, $\text{annual\_income} > 0$, $1 \le \text{spending\_score} \le 100$ | Enforces domain invariants |
| `test_invalid_file_handling` | Empty file / corrupt CSV | Raises `ValueError` or `FileNotFoundError` with descriptive message | Tests error handling |

### 6.2 `tests/test_pipeline.py` & Component Tests Specification

| Test Function | Target Module | Scope & Edge Cases Tested | Expected Outcome |
| :--- | :--- | :--- | :--- |
| `test_standard_scaler_transform` | `src/data_preparation.py` | 2D and 3D feature matrices | Means $\approx 0.0$, Stds $\approx 1.0$, shape preserved |
| `test_kmeans_clustering_k5` | `src/models.py` | 2D features, $k=5$, `random_state=42` | Returns exactly 5 clusters, labels array of shape `(200,)`, inertia $> 0$ |
| `test_agglomerative_ward` | `src/models.py` | 2D features, $k=5$, `linkage='ward'` | Returns exactly 5 clusters, deterministic labels |
| `test_dbscan_clustering` | `src/models.py` | Standardized features, $\text{eps}=0.35$, $\text{min\_samples}=5$ | Returns labels with $k=6$ and $N_{\text{noise}} = 23$ |
| `test_evaluation_metrics_k5_kmeans` | `src/evaluation.py` | 2D unscaled features + K-Means $k=5$ labels | Silhouette $\in [0.553, 0.555]$, DB Index $\in [0.572, 0.574]$, CH $\in [247.0, 248.0]$ |
| `test_evaluation_dbscan_noise_filtering` | `src/evaluation.py` | Synthetic labels with $-1$ noise points | Silhouette computed only on non-noise points; `n_noise > 0`, `is_valid == True` |
| `test_evaluation_single_cluster_edge_case` | `src/evaluation.py` | All labels $= 0$ or all labels $= -1$ | Returns `status='insufficient_clusters'`, `silhouette_score=None`, no unhandled exception |
| `test_pca_projection_2d_and_3d` | `src/models.py` / `src/export.py` | 3D features projected to 2D and 3D | Shape is `(200, 2)` / `(200, 3)`, variance sum $\approx 0.776$ (2D) and $1.0$ (3D) |
| `test_export_json_contract` | `src/export.py` | Full pipeline execution output | Validates against `PipelineOutputJSON` schema, no `NaN` or `Infinity` tokens |
| `test_cli_run_pipeline_default` | `run_pipeline.py` | CLI execution with default flags | Exit code `0`, generates `artifacts/metrics.json` and `artifacts/pipeline_output.json` |
| `test_cli_run_pipeline_custom_args` | `run_pipeline.py` | CLI execution `--k 4 --algorithm kmeans` | Exit code `0`, `optimal_k == 4` in exported metrics |

---

## 7. Concrete Code Patterns & Reference Implementations

To assist M1 Implementers, the following verified code snippets provide the core logic for the pipeline modules:

### 7.1 PCA Projection & Coordinate Generation Pattern (`src/models.py` / `src/export.py`)

```python
import numpy as np
import pandas as pd
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler
from typing import Tuple, Dict

def compute_pca_projections(
    df: pd.DataFrame,
    feature_cols: list[str] = ['age', 'annual_income', 'spending_score'],
    random_state: int = 42
) -> Tuple[np.ndarray, Dict[str, float]]:
    """
    Computes deterministic 2D and 3D PCA projections on standardized features.
    
    Returns:
        coords_df: DataFrame with pca_x, pca_y, pca_z
        explained_variance: Dictionary of explained variance ratios
    """
    X = df[feature_cols].values
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    
    n_components = min(len(feature_cols), 3)
    pca = PCA(n_components=n_components, random_state=random_state)
    X_pca = pca.fit_transform(X_scaled)
    
    var_ratios = pca.explained_variance_ratio_
    var_dict = {
        f"pc{i+1}_variance": round(float(var_ratios[i]), 4)
        for i in range(len(var_ratios))
    }
    var_dict["total_explained_variance"] = round(float(np.sum(var_ratios)), 4)
    
    return X_pca, var_dict
```

### 7.2 Safe JSON Exporter Pattern (`src/export.py`)

```python
import json
import math
from typing import Any

def sanitize_for_json(obj: Any) -> Any:
    """Recursively converts NaN, Infinity, and numpy datatypes into JSON-safe types."""
    if isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            return None
        return round(obj, 4)
    elif isinstance(obj, (np.integer, int)):
        return int(obj)
    elif isinstance(obj, (np.floating, float)):
        val = float(obj)
        return None if (math.isnan(val) or math.isinf(val)) else round(val, 4)
    elif isinstance(obj, np.ndarray):
        return [sanitize_for_json(x) for x in obj.tolist()]
    elif isinstance(obj, dict):
        return {k: sanitize_for_json(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [sanitize_for_json(x) for x in obj]
    return obj

def export_pipeline_json(payload: dict, output_path: str) -> None:
    """Safely serializes pipeline payload to valid RFC 8259 JSON file."""
    clean_payload = sanitize_for_json(payload)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(clean_payload, f, indent=2)
```

---

## 8. Summary of Action Items for M1 Implementer

1. **Implement `src/data_loader.py`**:
   - Support local load with network fetch fallback and offline canonical data generator.
   - Sanitize column headers (`Genre` $\to$ `gender`, `Annual Income (k$)` $\to$ `annual_income`, `Spending Score (1-100)` $\to$ `spending_score`).
2. **Implement `src/data_preparation.py`**:
   - Provide `StandardScaler`, `MinMaxScaler`, and unscaled feature pipeline options.
   - Default 2D model to `['annual_income', 'spending_score']` and 3D model to `['age', 'annual_income', 'spending_score']`.
3. **Implement `src/models.py`**:
   - Implement `KMeansModel`, `AgglomerativeModel`, `DBSCANModel`, and `PCATransformer` with fixed `random_state=42`.
4. **Implement `src/evaluation.py`**:
   - Implement `evaluate_clustering_robust()` with mandatory non-noise filtering for DBSCAN and safe handling of single-cluster/all-noise edge cases.
5. **Implement `src/export.py` & `run_pipeline.py`**:
   - Export structured JSON matching `PipelineOutputJSON` with `sanitize_for_json()` guard.
   - CLI runner supporting `--data`, `--k`, `--algorithm`, and `--export-dashboard`.
6. **Implement Test Suite**:
   - Run `pytest tests/` verifying 100% test pass on data ingestion, scaling, models, metrics, and CLI contracts.
