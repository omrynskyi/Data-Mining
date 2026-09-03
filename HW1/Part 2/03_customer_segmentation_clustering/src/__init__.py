"""
CRISP-DM Customer Segmentation & Clustering ML Package.
"""

from src.config import (
    CANONICAL_COLUMNS,
    CANONICAL_PERSONAS,
    DEFAULT_K,
    DEFAULT_RANDOM_STATE,
    DEFAULT_RAW_DATA_PATH,
    FEATURE_SETS,
)
from src.data_loader import DataLoader, load_data
from src.data_preparation import CustomerPreprocessor, DataPreparation
from src.data_understanding import DataUnderstanding
from src.evaluation import ClusterEvaluator
from src.export import ArtifactExporter, compute_feature_quartiles, sanitize_json
from src.models import (
    ClusteringModelFactory,
    compute_pca,
    train_agglomerative,
    train_dbscan,
    train_kmeans,
)

__all__ = [
    "DataLoader",
    "load_data",
    "DataUnderstanding",
    "CustomerPreprocessor",
    "DataPreparation",
    "ClusteringModelFactory",
    "train_kmeans",
    "train_agglomerative",
    "train_dbscan",
    "compute_pca",
    "ClusterEvaluator",
    "ArtifactExporter",
    "sanitize_json",
    "compute_feature_quartiles",
    "CANONICAL_COLUMNS",
    "CANONICAL_PERSONAS",
    "FEATURE_SETS",
    "DEFAULT_RAW_DATA_PATH",
    "DEFAULT_RANDOM_STATE",
    "DEFAULT_K",
]
