"""
CRISP-DM Phase 4: Modeling - Clustering Algorithms & Dimensionality Reduction.
"""

from typing import Any, Dict, Optional, Tuple, Union
import numpy as np
from sklearn.cluster import AgglomerativeClustering, DBSCAN, KMeans
from sklearn.decomposition import PCA


class ClusteringModelFactory:
    """Trains and manages clustering algorithms (K-Means, Agglomerative, DBSCAN) and PCA."""

    @staticmethod
    def train_kmeans(
        X: np.ndarray,
        k: int = 5,
        random_state: int = 42,
        n_init: int = 10,
        max_iter: int = 300,
    ) -> KMeans:
        """Fits K-Means model with k-means++ initialization."""
        if k < 2:
            raise ValueError(f"k must be at least 2, got {k}")
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
        if k < 2:
            raise ValueError(f"k must be at least 2, got {k}")
        # Note: In scikit-learn >= 1.2, metric replaced affinity
        agg = AgglomerativeClustering(
            n_clusters=k,
            linkage=linkage,
            metric=metric if linkage != "ward" else "euclidean",
        )
        agg.fit(X)
        return agg

    @staticmethod
    def train_dbscan(
        X: np.ndarray,
        eps: Optional[float] = None,
        min_samples: int = 5,
        metric: str = "euclidean",
    ) -> DBSCAN:
        """
        Fits Density-Based Spatial Clustering of Applications with Noise (DBSCAN).
        Adapts default eps based on feature variance if not explicitly provided.
        """
        if eps is None:
            # Estimate reasonable eps based on matrix scale
            std_mean = float(np.mean(np.std(X, axis=0)))
            eps = 0.35 if std_mean < 2.0 else 8.5

        dbs = DBSCAN(
            eps=eps,
            min_samples=min_samples,
            metric=metric,
        )
        dbs.fit(X)
        return dbs

    @staticmethod
    def compute_pca(
        X: np.ndarray,
        n_components: int = 3,
        random_state: int = 42,
    ) -> Tuple[np.ndarray, PCA]:
        """
        Computes 2D or 3D PCA projection coordinates.
        Ensures output always has at least 3 columns for 3D visualizers by padding if needed.
        """
        actual_components = min(n_components, X.shape[1])
        pca = PCA(n_components=actual_components, random_state=random_state)
        X_pca = pca.fit_transform(X)

        # Ensure (N, 3) matrix shape for consistent 3D dashboard visualizer
        if X_pca.shape[1] < 3:
            padding = np.zeros((X_pca.shape[0], 3 - X_pca.shape[1]))
            full_coords = np.hstack([X_pca, padding])
        else:
            full_coords = X_pca

        return full_coords, pca

    def train_all_models(
        self,
        X: np.ndarray,
        k: int = 5,
        random_state: int = 42,
    ) -> Dict[str, Any]:
        """Trains KMeans, Agglomerative, and DBSCAN returning models and predictions."""
        km = self.train_kmeans(X, k=k, random_state=random_state)
        agg = self.train_agglomerative(X, k=k, linkage="ward")
        dbs = self.train_dbscan(X, min_samples=5)

        return {
            "kmeans": {"model": km, "labels": km.labels_, "inertia": float(km.inertia_)},
            "agglomerative": {"model": agg, "labels": agg.labels_, "inertia": None},
            "dbscan": {"model": dbs, "labels": dbs.labels_, "inertia": None},
        }


# Convenience standalone functions
def train_kmeans(X: np.ndarray, k: int = 5, random_state: int = 42) -> KMeans:
    return ClusteringModelFactory.train_kmeans(X, k=k, random_state=random_state)


def train_agglomerative(X: np.ndarray, k: int = 5, linkage: str = "ward") -> AgglomerativeClustering:
    return ClusteringModelFactory.train_agglomerative(X, k=k, linkage=linkage)


def train_dbscan(X: np.ndarray, eps: Optional[float] = None, min_samples: int = 5) -> DBSCAN:
    return ClusteringModelFactory.train_dbscan(X, eps=eps, min_samples=min_samples)


def compute_pca(X: np.ndarray, n_components: int = 3, random_state: int = 42) -> Tuple[np.ndarray, PCA]:
    return ClusteringModelFactory.compute_pca(X, n_components=n_components, random_state=random_state)
