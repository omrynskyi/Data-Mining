# Milestone 1 Blueprint: CRISP-DM & Clustering Pipeline

**Author**: Explorer 1 (Milestone 1 Lead Architecture Explorer)  
**Date**: 2026-09-02  
**Target Milestone**: Milestone 1 (CRISP-DM ML Pipeline, Feature Inventory F1-F7)  
**Working Directory**: `.agents/m1_exp_1/`  
**Workspace Root**: `/Users/oleg/Documents/Coding/SJSU/Data Mining/HW1/Part 2/03_customer_segmentation_clustering`  

---

## 1. Executive Summary & Architecture Overview

Milestone 1 establishes the foundational machine learning engine for the **Mall Customer Segmentation & React Data Science Dashboard** project. The implementation adheres strictly to the 6 phases of the **CRISP-DM** (Cross-Industry Standard Process for Data Mining) standard:

```
+-----------------------------------------------------------------------------------------------+
|                               CRISP-DM PIPELINE ARCHITECTURE                                  |
+-----------------------------------------------------------------------------------------------+
|  1. Business Understanding  --> src/config.py (KPI thresholds, Persona archetypes)            |
|  2. Data Understanding      --> src/data_loader.py, src/data_understanding.py                 |
|  3. Data Preparation        --> src/data_preparation.py (Scalers, Encoders, Feature Sets)     |
|  4. Modeling                --> src/models.py (K-Means, DBSCAN, Agglomerative, PCA 2D/3D)     |
|  5. Evaluation              --> src/evaluation.py (Silhouette, DB, CH, Inertia, K-Sweep)      |
|  6. Deployment / Export     --> src/export.py, run_pipeline.py (JSON/CSV artifacts, Joblib)   |
+-----------------------------------------------------------------------------------------------+
```

The pipeline processes the 200-record Mall Customer dataset, identifies behavioral clusters (reaching the benchmark 2D $S \approx 0.554$, $k=5$), profiles the segments into actionable business personas, serializes scikit-learn models via Joblib, and exports clean JSON/CSV contracts consumed by the React Data Science Admin Dashboard and the Autoresearch optimizer.

---

## 2. File Inventory & Worker Write Ownership

The Worker agent will implement and own the following files:

| File Path | Role | Key Classes / Functions |
|:---|:---|:---|
| `requirements.txt` | Dependency declarations | `pandas`, `numpy`, `scikit-learn`, `scipy`, `joblib`, `pytest` |
| `src/__init__.py` | Package initialization | Exposes pipeline modules |
| `src/config.py` | Constants & Configuration | Default paths, hyperparameter presets, Persona definitions, schema keys |
| `src/data_loader.py` | Data Acquisition & Validation | `DataLoader`, embedded 200-row fallback, schema sanitizer |
| `src/data_understanding.py` | EDA & Statistics | `DataUnderstanding`, summary stats, IQR outlier detection, correlations |
| `src/data_preparation.py` | Preprocessing & Scaling | `CustomerPreprocessor`, `DataPreparation`, StandardScaler/MinMax/Robust |
| `src/models.py` | Clustering & PCA Engine | `ClusteringModelFactory`, `train_kmeans`, `train_dbscan`, `train_agglomerative`, `compute_pca` |
| `src/evaluation.py` | Metric & Persona Profiling | `ClusterEvaluator`, Silhouette, DBI, CH, Inertia, `sweep_optimal_k`, persona profiler |
| `src/export.py` | Artifact & JSON Exporter | `ArtifactExporter`, joblib saver, `metrics.json`, `customer_segments.csv`, `pipeline_output.json` |
| `run_pipeline.py` | CLI Pipeline Entrypoint | `main()`, `run()`, argparse CLI, exit code handling |
| `tests/__init__.py` | Test package marker | Package initialization |
| `tests/test_data_loader.py` | Ingestion Unit Tests | Fallback test, schema test, corrupt data handling |
| `tests/test_pipeline.py` | Pipeline & Models Unit Tests | Preprocessing, models, evaluation metrics, export validation, CLI runner |

---

## 3. Detailed Component Blueprint & Method Signatures

### 3.1 `src/config.py`

Defines all immutable parameters, paths, column mappings, and marketing persona definitions.

```python
"""Configuration constants and defaults for the Customer Segmentation Pipeline."""
from pathlib import Path
from typing import Dict, List, Any

# Filesystem Paths
PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent
DATA_DIR: Path = PROJECT_ROOT / "data"
RAW_DATA_DIR: Path = DATA_DIR / "raw"
PROCESSED_DATA_DIR: Path = DATA_DIR / "processed"
DEFAULT_RAW_DATA_PATH: Path = RAW_DATA_DIR / "Mall_Customers.csv"

ARTIFACTS_DIR: Path = PROJECT_ROOT / "artifacts"
MODELS_DIR: Path = ARTIFACTS_DIR / "models"
DASHBOARD_DATA_DIR: Path = PROJECT_ROOT / "dashboard" / "public" / "data"

REMOTE_DATASET_URL: str = (
    "https://raw.githubusercontent.com/sharmaroshan/Clustering-of-Mall-Customers/master/Mall_Customers.csv"
)

# Schema & Column Aliases
RAW_COLUMN_ALIASES: Dict[str, str] = {
    "CustomerID": "customer_id",
    "Genre": "gender",
    "Gender": "gender",
    "Age": "age",
    "Annual Income (k$)": "annual_income",
    "Spending Score (1-100)": "spending_score",
}

CANONICAL_COLUMNS: List[str] = [
    "customer_id",
    "gender",
    "age",
    "annual_income",
    "spending_score",
]

# Feature Set Presets
FEATURE_SETS: Dict[str, List[str]] = {
    "2d": ["annual_income", "spending_score"],
    "3d": ["age", "annual_income", "spending_score"],
    "all": ["gender", "age", "annual_income", "spending_score"],
}

# Persona Taxonomy & Color Palette
PERSONA_PROFILES: Dict[str, Dict[str, Any]] = {
    "target_vip": {
        "name": "Target / VIP Spenders",
        "persona": "High income with high spending tendency. Primary luxury demographic and brand advocates.",
        "color": "#8B5CF6",  # Purple
        "business_recommendation": "Provide premium concierge loyalty programs, exclusive product previews, and high-touch customer support.",
        "key_traits": ["High purchasing power", "Brand sensitive", "Frequent buyers", "High average order value"],
    },
    "careful_savers": {
        "name": "Careful / Savers",
        "persona": "High income with low spending score. Highly selective shoppers with large unspent disposable capital.",
        "color": "#3B82F6",  # Blue
        "business_recommendation": "Deploy targeted promotional campaigns highlighting product longevity, quality assurance, and high-value proposition.",
        "key_traits": ["Frugal affluent", "Value-focused", "Low purchase frequency", "High income elasticity"],
    },
    "spendthrifts": {
        "name": "Spendthrifts / Impulsive",
        "persona": "Low annual income but disproportionately high spending score. Trend-driven, younger cohort.",
        "color": "#EC4899",  # Pink
        "business_recommendation": "Target with flexible buy-now-pay-later (BNPL) options, flash sales, influencer partnerships, and experiential marketing.",
        "key_traits": ["Impulse buyers", "Trend seekers", "Young demographic", "Social-media driven"],
    },
    "sensible_budget": {
        "name": "Sensible / Budget Shoppers",
        "persona": "Low annual income and low spending score. Value-conscious shoppers seeking utility and discounts.",
        "color": "#F59E0B",  # Amber
        "business_recommendation": "Offer essential bundle discounts, reward-point cashbacks, and clear budget-friendly value items.",
        "key_traits": ["Price sensitive", "Utility seekers", "Coupon redeemers", "Essential shoppers"],
    },
    "standard_moderate": {
        "name": "Standard / Moderate",
        "persona": "Moderate annual income and moderate spending score. Represents the core middle-market demographic.",
        "color": "#10B981",  # Emerald
        "business_recommendation": "Engage through regular seasonal newsletters, standardized loyalty points, and broad-appeal merchandise.",
        "key_traits": ["Mainstream consumers", "Steady purchase rate", "Predictable behavior", "Broad brand affinity"],
    },
}

DEFAULT_RANDOM_STATE: int = 42
DEFAULT_K: int = 5
```

---

### 3.2 `src/data_loader.py`

Handles dataset acquisition with a 3-tier fallback strategy:
1. **Tier 1**: Local filesystem check (`data/raw/Mall_Customers.csv` or user `--data` path).
2. **Tier 2**: HTTPS download from canonical GitHub repository with 5-second timeout.
3. **Tier 3**: Verbatim embedded CSV string containing all 200 records (ensures 100% offline self-containment).

```python
"""Data loading, acquisition, and validation module."""
import io
import os
import urllib.request
from pathlib import Path
from typing import Optional, Union
import pandas as pd
from src.config import (
    DEFAULT_RAW_DATA_PATH,
    REMOTE_DATASET_URL,
    RAW_COLUMN_ALIASES,
    CANONICAL_COLUMNS,
)

# Embedded canonical 200-row dataset for offline deterministic fallback
EMBEDDED_MALL_CUSTOMERS_CSV: str = """CustomerID,Genre,Age,Annual Income (k$),Spending Score (1-100)
0001,Male,19,15,39
0002,Male,21,15,81
0003,Female,20,16,6
0004,Female,23,16,77
0005,Female,31,17,40
... [Verbatim 200 records] ...
0199,Male,32,137,18
0200,Male,30,137,83
"""

class DataLoader:
    """Robust data loader with validation and multi-tier offline fallback."""

    def __init__(self, data_path: Optional[Union[str, Path]] = None):
        self.data_path = Path(data_path) if data_path else DEFAULT_RAW_DATA_PATH

    def load_raw_data(self, auto_download: bool = True) -> pd.DataFrame:
        """Loads raw CSV data via local disk, remote download, or embedded fallback."""
        # 1. Local Disk
        if self.data_path.exists() and self.data_path.stat().st_size > 0:
            df = pd.read_csv(self.data_path)
            return self.validate_and_clean(df)

        # 2. Remote Download
        if auto_download:
            try:
                self.data_path.parent.mkdir(parents=True, exist_ok=True)
                with urllib.request.urlopen(REMOTE_DATASET_URL, timeout=5) as response:
                    content = response.read().decode("utf-8")
                    df = pd.read_csv(io.StringIO(content))
                    # Cache to disk
                    df.to_csv(self.data_path, index=False)
                    return self.validate_and_clean(df)
            except Exception:
                pass  # Fall through to embedded fallback

        # 3. Embedded Offline Fallback
        df = pd.read_csv(io.StringIO(EMBEDDED_MALL_CUSTOMERS_CSV.strip()))
        self.data_path.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(self.data_path, index=False)
        return self.validate_and_clean(df)

    def validate_and_clean(self, df: pd.DataFrame) -> pd.DataFrame:
        """Normalizes schema, enforces types, and verifies domain invariants."""
        # Clean column names
        df_clean = df.copy()
        df_clean.columns = [str(c).strip() for c in df_clean.columns]
        
        # Rename aliases (Genre -> gender, CustomerID -> customer_id, etc.)
        rename_map = {}
        for col in df_clean.columns:
            if col in RAW_COLUMN_ALIASES:
                rename_map[col] = RAW_COLUMN_ALIASES[col]
        df_clean = df_clean.rename(columns=rename_map)

        # Ensure required canonical columns exist
        missing = [c for c in CANONICAL_COLUMNS if c not in df_clean.columns]
        if missing:
            raise ValueError(f"Dataset missing required canonical columns: {missing}")

        # Invariant checks
        if df_clean.isnull().any().any():
            raise ValueError("Dataset contains unexpected null/NaN values")

        df_clean["customer_id"] = df_clean["customer_id"].astype(int)
        df_clean["age"] = df_clean["age"].astype(int)
        df_clean["annual_income"] = df_clean["annual_income"].astype(int)
        df_clean["spending_score"] = df_clean["spending_score"].astype(int)
        df_clean["gender"] = df_clean["gender"].astype(str).str.capitalize()

        if not df_clean["gender"].isin(["Male", "Female"]).all():
            raise ValueError("Gender column contains unrecognized categories")

        if (df_clean["age"] < 10).any() or (df_clean["age"] > 120).any():
            raise ValueError("Age values outside valid human range [10, 120]")

        if (df_clean["annual_income"] < 0).any():
            raise ValueError("Annual income cannot be negative")

        if (df_clean["spending_score"] < 1).any() or (df_clean["spending_score"] > 100).any():
            raise ValueError("Spending score must be bounded within [1, 100]")

        return df_clean[CANONICAL_COLUMNS]
```

---

### 3.3 `src/data_understanding.py`

Executes the CRISP-DM Data Understanding phase, computing descriptive statistics, demographic breakdowns, skewness, Pearson correlation matrix, and IQR-based outlier detection.

```python
"""CRISP-DM Data Understanding: Descriptive Statistics & Distribution Analysis."""
from typing import Dict, Any, List
import pandas as pd
import numpy as np

class DataUnderstanding:
    """Computes EDA metrics, distribution parameters, and outlier boundaries."""

    def __init__(self, df: pd.DataFrame):
        self.df = df.copy()

    def get_summary_statistics(self) -> Dict[str, Any]:
        """Calculates univariate metrics for age, income, and spending score."""
        stats = {}
        for col in ["age", "annual_income", "spending_score"]:
            series = self.df[col]
            stats[col] = {
                "mean": round(float(series.mean()), 2),
                "std": round(float(series.std()), 2),
                "min": int(series.min()),
                "q25": round(float(series.quantile(0.25)), 2),
                "median": round(float(series.median()), 2),
                "q75": round(float(series.quantile(0.75)), 2),
                "max": int(series.max()),
                "skew": round(float(series.skew()), 3),
            }
        return stats

    def get_demographics(self) -> Dict[str, Any]:
        """Calculates gender counts, percentages, and cross-tab distributions."""
        counts = self.df["gender"].value_counts().to_dict()
        total = len(self.df)
        return {
            "gender_counts": {k: int(v) for k, v in counts.items()},
            "gender_percentages": {k: round(float(v / total * 100), 2) for k, v in counts.items()},
            "total_customers": total,
        }

    def detect_outliers_iqr(self) -> Dict[str, Any]:
        """Identifies outliers using the 1.5 * IQR rule on income and spending."""
        outliers = {}
        for col in ["annual_income", "spending_score"]:
            q1 = float(self.df[col].quantile(0.25))
            q3 = float(self.df[col].quantile(0.75))
            iqr = q3 - q1
            lower_bound = q1 - 1.5 * iqr
            upper_bound = q3 + 1.5 * iqr
            mask = (self.df[col] < lower_bound) | (self.df[col] > upper_bound)
            outlier_rows = self.df[mask]
            outliers[col] = {
                "lower_bound": round(lower_bound, 2),
                "upper_bound": round(upper_bound, 2),
                "outlier_count": int(mask.sum()),
                "outlier_customer_ids": outlier_rows["customer_id"].tolist(),
            }
        return outliers

    def get_correlation_matrix(self) -> Dict[str, Dict[str, float]]:
        """Computes pairwise Pearson correlation coefficients between numeric features."""
        num_cols = ["age", "annual_income", "spending_score"]
        corr = self.df[num_cols].corr()
        return {col: {c: round(float(corr.loc[col, c]), 4) for c in num_cols} for col in num_cols}

    def get_dashboard_dataset_summary(self) -> Dict[str, Any]:
        """Formats dataset summary matching the pipeline_output.json schema."""
        summary_stats = self.get_summary_statistics()
        demographics = self.get_demographics()
        return {
            "total_customers": demographics["total_customers"],
            "features": ["age", "annual_income", "spending_score"],
            "age_stats": {
                "mean": summary_stats["age"]["mean"],
                "min": summary_stats["age"]["min"],
                "max": summary_stats["age"]["max"],
                "std": summary_stats["age"]["std"],
            },
            "income_stats": {
                "mean": summary_stats["annual_income"]["mean"],
                "min": summary_stats["annual_income"]["min"],
                "max": summary_stats["annual_income"]["max"],
                "std": summary_stats["annual_income"]["std"],
            },
            "spending_stats": {
                "mean": summary_stats["spending_score"]["mean"],
                "min": summary_stats["spending_score"]["min"],
                "max": summary_stats["spending_score"]["max"],
                "std": summary_stats["spending_score"]["std"],
            },
            "gender_counts": demographics["gender_counts"],
        }
```

---

### 3.4 `src/data_preparation.py`

Manages feature extraction, categorical encoding (Gender: Male=0, Female=1), and feature scaling (StandardScaler, MinMaxScaler, RobustScaler, or None).

```python
"""CRISP-DM Data Preparation: Encoding, Feature Subsets, and Scaling Pipelines."""
from typing import Tuple, List, Optional, Union
import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler, MinMaxScaler, RobustScaler
from src.config import FEATURE_SETS

class CustomerPreprocessor:
    """Prepares and transforms customer data for clustering algorithms."""

    def __init__(self, scaler_type: str = "standard", feature_set: str = "2d"):
        self.scaler_type = scaler_type.lower()
        self.feature_set_name = feature_set.lower()
        
        if self.feature_set_name not in FEATURE_SETS:
            raise ValueError(f"Unknown feature set '{feature_set}'. Must be one of {list(FEATURE_SETS.keys())}")
        self.feature_names = FEATURE_SETS[self.feature_set_name]

        if self.scaler_type == "standard":
            self.scaler: Optional[Any] = StandardScaler()
        elif self.scaler_type == "minmax":
            self.scaler = MinMaxScaler()
        elif self.scaler_type == "robust":
            self.scaler = RobustScaler()
        elif self.scaler_type == "none":
            self.scaler = None
        else:
            raise ValueError(f"Unknown scaler type '{scaler_type}'. Choose from 'standard', 'minmax', 'robust', 'none'.")
            
        self.is_fitted: bool = False

    def fit_transform(self, df: pd.DataFrame) -> Tuple[np.ndarray, pd.DataFrame]:
        """Fits scaler and transforms selected feature matrix."""
        df_processed = df.copy()
        # Encode gender if present in feature set
        if "gender" in self.feature_names:
            df_processed["gender_encoded"] = df_processed["gender"].map({"Male": 0, "Female": 1}).fillna(0)
            active_cols = ["gender_encoded" if c == "gender" else c for c in self.feature_names]
        else:
            active_cols = self.feature_names

        X_raw = df_processed[active_cols].values.astype(float)
        
        if self.scaler is not None:
            X_scaled = self.scaler.fit_transform(X_raw)
        else:
            X_scaled = X_raw

        self.is_fitted = True
        return X_scaled, df_processed

    def transform(self, df: pd.DataFrame) -> np.ndarray:
        """Transforms feature matrix using previously fitted scaler."""
        if not self.is_fitted and self.scaler is not None:
            raise RuntimeError("Preprocessor must be fitted before calling transform()")
        df_processed = df.copy()
        if "gender" in self.feature_names:
            df_processed["gender_encoded"] = df_processed["gender"].map({"Male": 0, "Female": 1}).fillna(0)
            active_cols = ["gender_encoded" if c == "gender" else c for c in self.feature_names]
        else:
            active_cols = self.feature_names

        X_raw = df_processed[active_cols].values.astype(float)
        return self.scaler.transform(X_raw) if self.scaler is not None else X_raw
```

---

### 3.5 `src/models.py`

Factory and training orchestration for K-Means ($k$-means++), Agglomerative Hierarchical clustering, DBSCAN, and Dimensionality Reduction (PCA 2D/3D).

```python
"""CRISP-DM Modeling: Clustering Algorithms (K-Means, Agglomerative, DBSCAN) & PCA."""
from typing import Dict, Any, Tuple, Optional
import numpy as np
from sklearn.cluster import KMeans, DBSCAN, AgglomerativeClustering
from sklearn.decomposition import PCA

class ClusteringModelFactory:
    """Trains and manages clustering models and PCA projections."""

    @staticmethod
    def train_kmeans(
        X: np.ndarray,
        k: int = 5,
        random_state: int = 42,
        n_init: int = 10,
        max_iter: int = 300,
    ) -> KMeans:
        """Fits K-Means model with k-means++ initialization."""
        km = KMeans(
            n_clusters=k,
            init="k-means++",
            n_init=n_init,
            max_iter=max_iter,
            random_state=random_state,
        )
        km.fit(X)
        return km

    @staticmethod
    def train_agglomerative(
        X: np.ndarray,
        k: int = 5,
        linkage: str = "ward",
        metric: str = "euclidean",
    ) -> AgglomerativeClustering:
        """Fits Agglomerative Hierarchical clustering model."""
        agg = AgglomerativeClustering(
            n_clusters=k,
            linkage=linkage,
            metric=metric,
        )
        agg.fit(X)
        return agg

    @staticmethod
    def train_dbscan(
        X: np.ndarray,
        eps: float = 0.35,
        min_samples: int = 5,
        metric: str = "euclidean",
    ) -> DBSCAN:
        """Fits density-based DBSCAN model."""
        dbs = DBSCAN(
            eps=eps,
            min_samples=min_samples,
            metric=metric,
        )
        dbs.fit(X)
        return dbs

    @staticmethod
    def compute_pca(X: np.ndarray, n_components: int = 3) -> Tuple[np.ndarray, PCA]:
        """Computes 2D or 3D PCA coordinates and fitted PCA transformer."""
        pca = PCA(n_components=n_components, random_state=42)
        coords = pca.fit_transform(X)
        return coords, pca

    def train_all_models(
        self,
        X: np.ndarray,
        k: int = 5,
        random_state: int = 42,
    ) -> Dict[str, Any]:
        """Trains KMeans, Agglomerative, and DBSCAN returning models and predictions."""
        km = self.train_kmeans(X, k=k, random_state=random_state)
        agg = self.train_agglomerative(X, k=k, linkage="ward")
        dbs = self.train_dbscan(X, eps=0.35, min_samples=5)

        return {
            "kmeans": {"model": km, "labels": km.labels_, "inertia": float(km.inertia_)},
            "agglomerative": {"model": agg, "labels": agg.labels_, "inertia": None},
            "dbscan": {"model": dbs, "labels": dbs.labels_, "inertia": None},
        }
```

---

### 3.6 `src/evaluation.py`

Calculates Silhouette Score, Davies-Bouldin Index, Calinski-Harabasz Index, Inertia, performs optimal $k$ hyperparameter sweeps across $k \in [2, 10]$, and synthesizes customer persona profiles.

```python
"""CRISP-DM Evaluation: Validation Metrics, K-Sweeps, and Persona Profiling."""
from typing import Dict, Any, List, Optional
import pandas as pd
import numpy as np
from sklearn.metrics import silhouette_score, davies_bouldin_score, calinski_harabasz_score
from src.config import PERSONA_PROFILES

class ClusterEvaluator:
    """Computes internal validation metrics, sweeps k values, and builds persona summaries."""

    @staticmethod
    def compute_metrics(
        X: np.ndarray,
        labels: np.ndarray,
        inertia: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Computes internal cluster validation metrics, gracefully handling noise & singletons."""
        unique_labels = set(labels)
        non_noise_mask = labels != -1
        non_noise_labels = labels[non_noise_mask]
        num_valid_clusters = len(set(non_noise_labels))
        noise_count = int((labels == -1).sum())

        if num_valid_clusters < 2:
            return {
                "silhouette_score": 0.0,
                "davies_bouldin_index": 99.0,
                "calinski_harabasz_score": 0.0,
                "inertia": round(inertia, 2) if inertia is not None else 0.0,
                "n_clusters": num_valid_clusters,
                "noise_count": noise_count,
            }

        X_valid = X[non_noise_mask]
        sil = float(silhouette_score(X_valid, non_noise_labels))
        dbi = float(davies_bouldin_score(X_valid, non_noise_labels))
        chi = float(calinski_harabasz_score(X_valid, non_noise_labels))

        return {
            "silhouette_score": round(sil, 4),
            "davies_bouldin_index": round(dbi, 4),
            "calinski_harabasz_score": round(chi, 2),
            "inertia": round(inertia, 2) if inertia is not None else 0.0,
            "n_clusters": num_valid_clusters,
            "noise_count": noise_count,
        }

    @staticmethod
    def sweep_k(
        X: np.ndarray,
        k_min: int = 2,
        k_max: int = 10,
        random_state: int = 42,
    ) -> Dict[str, Any]:
        """Sweeps k from k_min to k_max to determine optimal k via Silhouette and Inertia."""
        k_values = list(range(k_min, k_max + 1))
        silhouette_scores = []
        davies_bouldin_indices = []
        calinski_harabasz_scores = []
        inertias = []

        for k in k_values:
            km = KMeans(n_clusters=k, init="k-means++", n_init=10, random_state=random_state)
            km.fit(X)
            sil = float(silhouette_score(X, km.labels_))
            dbi = float(davies_bouldin_score(X, km.labels_))
            chi = float(calinski_harabasz_score(X, km.labels_))
            
            silhouette_scores.append(round(sil, 4))
            davies_bouldin_indices.append(round(dbi, 4))
            calinski_harabasz_scores.append(round(chi, 2))
            inertias.append(round(float(km.inertia_), 2))

        best_idx = int(np.argmax(silhouette_scores))
        optimal_k = k_values[best_idx]

        return {
            "k_values": k_values,
            "silhouette_scores": silhouette_scores,
            "davies_bouldin_indices": davies_bouldin_indices,
            "calinski_harabasz_scores": calinski_harabasz_scores,
            "inertias": inertias,
            "optimal_k": optimal_k,
        }

    @staticmethod
    def assign_persona(mean_income: float, mean_spending: float) -> str:
        """Determines persona profile key based on centroid coordinates in income/spend plane."""
        if mean_income > 65.0:
            if mean_spending > 60.0:
                return "target_vip"
            else:
                return "careful_savers"
        elif mean_income < 45.0:
            if mean_spending > 60.0:
                return "spendthrifts"
            else:
                return "sensible_budget"
        else:
            return "standard_moderate"

    def profile_clusters(
        self,
        df: pd.DataFrame,
        labels: np.ndarray,
    ) -> List[Dict[str, Any]]:
        """Aggregates demographic and spending metrics per cluster and attaches business persona."""
        df_eval = df.copy()
        df_eval["cluster_id"] = labels
        total_customers = len(df_eval)
        unique_clusters = sorted(list(set(labels)))
        profiles = []

        for cid in unique_clusters:
            if cid == -1:
                # Noise cluster representation
                sub = df_eval[df_eval["cluster_id"] == -1]
                profiles.append({
                    "cluster_id": -1,
                    "name": "Noise / Outliers",
                    "persona": "Unassigned anomalous customer records not fitting dense clusters.",
                    "color": "#94A3B8",
                    "count": len(sub),
                    "percentage": round(len(sub) / total_customers * 100, 2),
                    "avg_age": round(float(sub["age"].mean()), 2) if len(sub) > 0 else 0.0,
                    "avg_income": round(float(sub["annual_income"].mean()), 2) if len(sub) > 0 else 0.0,
                    "avg_spending": round(float(sub["spending_score"].mean()), 2) if len(sub) > 0 else 0.0,
                    "gender_distribution": {
                        "Male": int((sub["gender"] == "Male").sum()),
                        "Female": int((sub["gender"] == "Female").sum()),
                    },
                    "business_recommendation": "Review individual anomaly records for fraud or niche luxury behaviors.",
                    "key_traits": ["Statistical outliers", "Isolated points"],
                })
                continue

            sub = df_eval[df_eval["cluster_id"] == cid]
            avg_inc = float(sub["annual_income"].mean())
            avg_spd = float(sub["spending_score"].mean())
            avg_age = float(sub["age"].mean())
            count = len(sub)

            persona_key = self.assign_persona(avg_inc, avg_spd)
            persona_data = PERSONA_PROFILES[persona_key]

            gender_counts = sub["gender"].value_counts().to_dict()

            profiles.append({
                "cluster_id": int(cid),
                "name": persona_data["name"],
                "persona": persona_data["persona"],
                "color": persona_data["color"],
                "count": count,
                "percentage": round(count / total_customers * 100, 2),
                "avg_age": round(avg_age, 2),
                "avg_income": round(avg_inc, 2),
                "avg_spending": round(avg_spd, 2),
                "gender_distribution": {
                    "Male": int(gender_counts.get("Male", 0)),
                    "Female": int(gender_counts.get("Female", 0)),
                },
                "business_recommendation": persona_data["business_recommendation"],
                "key_traits": persona_data["key_traits"],
            })

        return profiles
```

---

### 3.7 `src/export.py`

Manages serialization to disk:
1. Joblib models (`artifacts/models/*.joblib`)
2. CSV segments (`artifacts/customer_segments.csv`)
3. JSON metrics (`artifacts/metrics.json`)
4. Dashboard integration JSON (`artifacts/pipeline_output.json` and `dashboard/public/data/pipeline_output.json`)

```python
"""Artifact and Data Contract Exporter."""
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional
import joblib
import pandas as pd
import numpy as np
from src.config import ARTIFACTS_DIR, MODELS_DIR, DASHBOARD_DATA_DIR

def sanitize_json(obj: Any) -> Any:
    """Converts numpy primitives and arrays into native JSON-serializable Python types."""
    if isinstance(obj, np.integer):
        return int(obj)
    elif isinstance(obj, (np.floating, float)):
        return round(float(obj), 4)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, dict):
        return {str(k): sanitize_json(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [sanitize_json(v) for v in obj]
    return obj

class ArtifactExporter:
    """Serializes pipeline models, metrics, and dashboard payloads."""

    def __init__(self, artifacts_dir: Optional[Path] = None):
        self.artifacts_dir = Path(artifacts_dir) if artifacts_dir else ARTIFACTS_DIR
        self.models_dir = self.artifacts_dir / "models"
        self.models_dir.mkdir(parents=True, exist_ok=True)

    def save_joblib_models(self, models: Dict[str, Any]) -> Dict[str, str]:
        """Saves fitted models and scalers into .joblib files."""
        saved_paths = {}
        for name, model_obj in models.items():
            if model_obj is not None:
                file_path = self.models_dir / f"{name}_model.joblib"
                joblib.dump(model_obj, file_path)
                saved_paths[name] = str(file_path)
        return saved_paths

    def export_customer_segments_csv(
        self,
        df_segmented: pd.DataFrame,
        filename: str = "customer_segments.csv",
    ) -> Path:
        """Exports tabular CSV containing customer data with assigned cluster and PCA coordinates."""
        output_path = self.artifacts_dir / filename
        df_segmented.to_csv(output_path, index=False)
        return output_path

    def export_metrics_json(
        self,
        metrics_payload: Dict[str, Any],
        filename: str = "metrics.json",
    ) -> Path:
        """Exports metrics and k-sweep results to artifacts/metrics.json."""
        output_path = self.artifacts_dir / filename
        sanitized = sanitize_json(metrics_payload)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(sanitized, f, indent=2)
        return output_path

    def export_pipeline_output_json(
        self,
        payload: Dict[str, Any],
        export_to_dashboard: bool = True,
    ) -> Path:
        """Exports structured payload adhering strictly to PROJECT.md schema."""
        output_path = self.artifacts_dir / "pipeline_output.json"
        sanitized = sanitize_json(payload)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(sanitized, f, indent=2)

        if export_to_dashboard:
            DASHBOARD_DATA_DIR.mkdir(parents=True, exist_ok=True)
            dashboard_file = DASHBOARD_DATA_DIR / "pipeline_output.json"
            shutil.copyfile(output_path, dashboard_file)

        return output_path
```

---

### 3.8 `run_pipeline.py` (CLI Runner)

Main entrypoint orchestration supporting command-line arguments, error logging, and standard return codes.

```python
#!/usr/bin/env python3
"""Main CLI Runner for the CRISP-DM Mall Customer Segmentation Pipeline."""
import argparse
import sys
import logging
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd
import numpy as np

from src.config import (
    DEFAULT_RAW_DATA_PATH,
    ARTIFACTS_DIR,
    DEFAULT_K,
    DEFAULT_RANDOM_STATE,
)
from src.data_loader import DataLoader
from src.data_understanding import DataUnderstanding
from src.data_preparation import CustomerPreprocessor
from src.models import ClusteringModelFactory
from src.evaluation import ClusterEvaluator
from src.export import ArtifactExporter

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("run_pipeline")

def parse_args():
    parser = argparse.ArgumentParser(
        description="CRISP-DM Mall Customer Segmentation Machine Learning Pipeline"
    )
    parser.add_argument(
        "--data", "--data-path",
        type=str,
        default=str(DEFAULT_RAW_DATA_PATH),
        help=f"Path to input CSV dataset (default: {DEFAULT_RAW_DATA_PATH})",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=str(ARTIFACTS_DIR),
        help=f"Directory to save output models and metrics (default: {ARTIFACTS_DIR})",
    )
    parser.add_argument(
        "--k", "--n-clusters",
        type=int,
        default=DEFAULT_K,
        help=f"Number of clusters for K-Means and Agglomerative (default: {DEFAULT_K})",
    )
    parser.add_argument(
        "--algorithm",
        type=str,
        choices=["kmeans", "dbscan", "agglomerative", "all"],
        default="all",
        help="Clustering algorithm to train (default: all)",
    )
    parser.add_argument(
        "--scaler",
        type=str,
        choices=["standard", "minmax", "robust", "none"],
        default="standard",
        help="Feature scaling method (default: standard)",
    )
    parser.add_argument(
        "--features",
        type=str,
        choices=["2d", "3d", "all"],
        default="2d",
        help="Feature subset to cluster: '2d' (Income, Spend), '3d' (+Age), 'all' (+Gender) (default: 2d)",
    )
    parser.add_argument(
        "--export-dashboard",
        action="store_true",
        default=True,
        help="Copy pipeline_output.json to dashboard/public/data/ (default: True)",
    )
    parser.add_argument(
        "--random-state",
        type=int,
        default=DEFAULT_RANDOM_STATE,
        help=f"Random seed for reproducibility (default: {DEFAULT_RANDOM_STATE})",
    )
    return parser.parse_args()

def run_pipeline(args) -> int:
    try:
        logger.info("============================================================")
        logger.info("   CRISP-DM MALL CUSTOMER SEGMENTATION PIPELINE             ")
        logger.info("============================================================")

        # 1. Data Understanding & Ingestion
        logger.info(f"Phase 1 & 2: Ingesting dataset from {args.data}...")
        loader = DataLoader(data_path=args.data)
        df_raw = loader.load_raw_data()
        logger.info(f"Loaded {len(df_raw)} validated customer records.")

        eda = DataUnderstanding(df_raw)
        eda_summary = eda.get_dashboard_dataset_summary()
        outliers = eda.detect_outliers_iqr()
        logger.info(f"EDA Complete. Identified {outliers['annual_income']['outlier_count']} income outliers.")

        # 2. Data Preparation
        logger.info(f"Phase 3: Preparing features with scaler '{args.scaler}', feature set '{args.features}'...")
        preprocessor = CustomerPreprocessor(scaler_type=args.scaler, feature_set=args.features)
        X_scaled, df_prep = preprocessor.fit_transform(df_raw)

        # 3. Modeling
        logger.info(f"Phase 4: Training clustering models (k={args.k})...")
        model_factory = ClusteringModelFactory()
        models_dict = model_factory.train_all_models(X_scaled, k=args.k, random_state=args.random_state)
        
        # PCA 2D/3D Projections for Dashboard
        pca_coords, pca_model = model_factory.compute_pca(X_scaled, n_components=3)

        # 4. Evaluation
        logger.info("Phase 5: Evaluating model metrics & generating persona profiles...")
        evaluator = ClusterEvaluator()
        
        # Primary model evaluation (K-Means)
        km_labels = models_dict["kmeans"]["labels"]
        primary_metrics = evaluator.compute_metrics(
            X_scaled, km_labels, inertia=models_dict["kmeans"]["inertia"]
        )
        
        # Comparison models evaluation
        agg_metrics = evaluator.compute_metrics(X_scaled, models_dict["agglomerative"]["labels"])
        dbs_metrics = evaluator.compute_metrics(X_scaled, models_dict["dbscan"]["labels"])
        
        # K-Sweep
        k_sweep_results = evaluator.sweep_k(X_scaled, k_min=2, k_max=10, random_state=args.random_state)
        
        # Persona profiling
        cluster_profiles = evaluator.profile_clusters(df_raw, km_labels)

        # Map cluster names and PCA onto customer records
        cluster_name_map = {cp["cluster_id"]: cp["name"] for cp in cluster_profiles}
        df_segmented = df_raw.copy()
        df_segmented["cluster_id"] = km_labels
        df_segmented["cluster_name"] = df_segmented["cluster_id"].map(cluster_name_map)
        df_segmented["pca_x"] = np.round(pca_coords[:, 0], 4)
        df_segmented["pca_y"] = np.round(pca_coords[:, 1], 4)
        df_segmented["pca_z"] = np.round(pca_coords[:, 2], 4)

        customers_payload = []
        for _, row in df_segmented.iterrows():
            customers_payload.append({
                "customer_id": int(row["customer_id"]),
                "gender": str(row["gender"]),
                "age": int(row["age"]),
                "annual_income": int(row["annual_income"]),
                "spending_score": int(row["spending_score"]),
                "cluster_id": int(row["cluster_id"]),
                "cluster_name": str(row["cluster_name"]),
                "pca_x": float(row["pca_x"]),
                "pca_y": float(row["pca_y"]),
                "pca_z": float(row["pca_z"]),
            })

        # Model Comparisons Payload
        model_comparisons = [
            {
                "algorithm": "K-Means",
                "k": args.k,
                "silhouette_score": primary_metrics["silhouette_score"],
                "davies_bouldin_index": primary_metrics["davies_bouldin_index"],
                "calinski_harabasz_score": primary_metrics["calinski_harabasz_score"],
                "description": f"Standard Lloyd algorithm with k-means++ initialization (k={args.k}).",
            },
            {
                "algorithm": "Agglomerative Hierarchical",
                "k": args.k,
                "silhouette_score": agg_metrics["silhouette_score"],
                "davies_bouldin_index": agg_metrics["davies_bouldin_index"],
                "calinski_harabasz_score": agg_metrics["calinski_harabasz_score"],
                "description": "Hierarchical bottom-up clustering with Ward variance minimization.",
            },
            {
                "algorithm": "DBSCAN",
                "k": dbs_metrics["n_clusters"],
                "silhouette_score": dbs_metrics["silhouette_score"],
                "davies_bouldin_index": dbs_metrics["davies_bouldin_index"],
                "calinski_harabasz_score": dbs_metrics["calinski_harabasz_score"],
                "description": f"Density-based spatial clustering (eps=0.35, min_samples=5, noise={dbs_metrics['noise_count']}).",
            },
        ]

        # 5. Deployment & Export
        logger.info("Phase 6: Exporting models, CSV, and JSON contracts...")
        exporter = ArtifactExporter(artifacts_dir=Path(args.output_dir))
        
        # Save models
        models_to_save = {
            "kmeans": models_dict["kmeans"]["model"],
            "agglomerative": models_dict["agglomerative"]["model"],
            "dbscan": models_dict["dbscan"]["model"],
            "pca": pca_model,
        }
        if preprocessor.scaler is not None:
            models_to_save["scaler"] = preprocessor.scaler
        exporter.save_joblib_models(models_to_save)

        # Save CSV
        exporter.export_customer_segments_csv(df_segmented)

        # Save metrics.json
        exporter.export_metrics_json({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "primary_metrics": primary_metrics,
            "comparison_metrics": {
                "agglomerative": agg_metrics,
                "dbscan": dbs_metrics,
            },
            "k_sweep": k_sweep_results,
        })

        # Save pipeline_output.json
        pipeline_output_payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "dataset_summary": eda_summary,
            "kpis": {
                "optimal_k": k_sweep_results["optimal_k"],
                "silhouette_score": primary_metrics["silhouette_score"],
                "davies_bouldin_index": primary_metrics["davies_bouldin_index"],
                "calinski_harabasz_score": primary_metrics["calinski_harabasz_score"],
                "inertia": primary_metrics["inertia"],
                "best_algorithm": "KMeans",
            },
            "customers": customers_payload,
            "clusters": cluster_profiles,
            "model_comparisons": model_comparisons,
        }
        exporter.export_pipeline_output_json(
            pipeline_output_payload, export_to_dashboard=args.export_dashboard
        )

        logger.info("============================================================")
        logger.info(f" Pipeline Success! Silhouette: {primary_metrics['silhouette_score']}, Optimal k: {k_sweep_results['optimal_k']}")
        logger.info(f" Artifacts written to {args.output_dir}/")
        logger.info("============================================================")
        return 0

    except Exception as e:
        logger.error(f"Pipeline failed with error: {e}", exc_info=True)
        return 1

def main():
    args = parse_args()
    sys.exit(run_pipeline(args))

if __name__ == "__main__":
    main()
```

---

## 4. Exact Data Schema Adherence (`pipeline_output.json`)

The output schema is designed to match `PROJECT.md` §Interface Contracts §3 verbatim:

```json
{
  "timestamp": "2026-09-02T12:00:00Z",
  "dataset_summary": {
    "total_customers": 200,
    "features": ["age", "annual_income", "spending_score"],
    "age_stats": { "mean": 38.85, "min": 18, "max": 70, "std": 13.97 },
    "income_stats": { "mean": 60.56, "min": 15, "max": 137, "std": 26.26 },
    "spending_stats": { "mean": 50.2, "min": 1, "max": 99, "std": 25.82 },
    "gender_counts": { "Male": 88, "Female": 112 }
  },
  "kpis": {
    "optimal_k": 5,
    "silhouette_score": 0.5547,
    "davies_bouldin_index": 0.5722,
    "calinski_harabasz_score": 248.65,
    "inertia": 65.57,
    "best_algorithm": "KMeans"
  },
  "customers": [
    {
      "customer_id": 1,
      "gender": "Male",
      "age": 19,
      "annual_income": 15,
      "spending_score": 39,
      "cluster_id": 4,
      "cluster_name": "Sensible / Budget Shoppers",
      "pca_x": -0.8421,
      "pca_y": -0.4124,
      "pca_z": 0.1245
    }
  ],
  "clusters": [
    {
      "cluster_id": 0,
      "name": "Standard / Moderate",
      "persona": "Moderate annual income and moderate spending score. Represents the core middle-market demographic.",
      "color": "#10B981",
      "count": 81,
      "percentage": 40.5,
      "avg_age": 42.72,
      "avg_income": 55.3,
      "avg_spending": 49.52,
      "gender_distribution": { "Male": 33, "Female": 48 },
      "business_recommendation": "Engage through regular seasonal newsletters, standardized loyalty points, and broad-appeal merchandise.",
      "key_traits": ["Mainstream consumers", "Steady purchase rate", "Predictable behavior", "Broad brand affinity"]
    }
  ],
  "model_comparisons": [
    {
      "algorithm": "K-Means",
      "k": 5,
      "silhouette_score": 0.5547,
      "davies_bouldin_index": 0.5722,
      "calinski_harabasz_score": 248.65,
      "description": "Standard Lloyd algorithm with k-means++ initialization (k=5)."
    }
  ]
}
```

---

## 5. Testing & Verification Blueprint for Worker

The Worker will implement comprehensive unit and integration tests under `tests/`:

### 5.1 `tests/test_data_loader.py`
- `test_load_local_dataset`: Asserts that `DataLoader` successfully loads existing `Mall_Customers.csv`.
- `test_embedded_fallback_when_file_missing`: Asserts that when pointing to a non-existent path with network disabled, `DataLoader` loads the 200 records cleanly.
- `test_schema_validation_and_cleaning`: Tests column renaming (e.g. `Genre` $\to$ `gender`), type casting, and invariant validation.
- `test_invalid_schema_raises`: Tests that corrupt/missing columns or out-of-bound values raise `ValueError`.

### 5.2 `tests/test_pipeline.py`
- `test_customer_preprocessor_scalers`: Asserts correct shapes and scaling properties for `StandardScaler`, `MinMaxScaler`, and `None`.
- `test_clustering_models_training`: Asserts that `train_kmeans`, `train_agglomerative`, `train_dbscan` produce valid label arrays of length 200.
- `test_cluster_evaluation_metrics`: Asserts $0.50 < S < 0.60$ for 2D $k=5$ K-Means, $DBI < 0.70$, $CH > 200$.
- `test_optimal_k_sweep`: Asserts `sweep_k` tests $k=2..10$ and selects $k=5$ as the optimal silhouette peak.
- `test_artifact_export_integrity`: Asserts that `ArtifactExporter` creates `.joblib` files, `metrics.json`, `customer_segments.csv`, and valid `pipeline_output.json`.
- `test_run_pipeline_cli`: Executes `subprocess.run([sys.executable, "run_pipeline.py"])` and verifies return code 0 and artifact presence.

---

## 6. Implementation Sequence for Worker

1. **Step 1**: Write `requirements.txt` with standard ML packages.
2. **Step 2**: Create `src/__init__.py` and `src/config.py`.
3. **Step 3**: Implement `src/data_loader.py` with embedded fallback and schema validation.
4. **Step 4**: Implement `src/data_understanding.py` and `src/data_preparation.py`.
5. **Step 5**: Implement `src/models.py` and `src/evaluation.py`.
6. **Step 6**: Implement `src/export.py` and `run_pipeline.py`.
7. **Step 7**: Write test suites in `tests/test_data_loader.py` and `tests/test_pipeline.py`.
8. **Step 8**: Execute `pytest tests/` and `python run_pipeline.py` to confirm exit code 0 and 100% test pass rate.
