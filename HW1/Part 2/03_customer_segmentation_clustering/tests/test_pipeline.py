"""
Unit and Integration Tests for Pipeline Components, Machine Learning Models, and Evaluation Engine.
"""

import json
from pathlib import Path
import numpy as np
import pandas as pd
import pytest
from sklearn.cluster import KMeans

from src.data_loader import DataLoader
from src.data_preparation import CustomerPreprocessor
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


@pytest.fixture
def sample_data() -> pd.DataFrame:
    """Loads canonical Mall Customers dataset fixture."""
    loader = DataLoader()
    return loader.load_raw_data()


class TestDataUnderstanding:
    """Tests for exploratory data analysis, statistics, and outlier detection."""

    def test_summary_statistics_calculations(self, sample_data: pd.DataFrame):
        eda = DataUnderstanding(sample_data)
        stats = eda.get_summary_statistics()

        assert "age" in stats and "annual_income" in stats and "spending_score" in stats
        assert stats["age"]["min"] == 18
        assert stats["age"]["max"] == 70
        assert 38.0 <= stats["age"]["mean"] <= 39.5
        assert 60.0 <= stats["annual_income"]["mean"] <= 61.0
        assert 49.5 <= stats["spending_score"]["mean"] <= 51.0

    def test_demographics_and_female_ratio(self, sample_data: pd.DataFrame):
        eda = DataUnderstanding(sample_data)
        demo = eda.get_demographics()

        assert demo["total_customers"] == 200
        assert demo["gender_counts"]["Female"] == 112
        assert demo["gender_counts"]["Male"] == 88
        assert abs(demo["female_ratio"] - 0.56) < 0.01

    def test_outlier_detection_iqr(self, sample_data: pd.DataFrame):
        eda = DataUnderstanding(sample_data)
        outliers = eda.detect_outliers_iqr()

        assert "annual_income" in outliers
        assert outliers["annual_income"]["outlier_count"] == 2  # IDs 199 and 200 ($137k)
        assert 199 in outliers["annual_income"]["outlier_customer_ids"]
        assert 200 in outliers["annual_income"]["outlier_customer_ids"]
        assert outliers["spending_score"]["outlier_count"] == 0

    def test_correlation_matrix_computation(self, sample_data: pd.DataFrame):
        eda = DataUnderstanding(sample_data)
        corr = eda.get_correlation_matrix()

        assert len(corr["features"]) == 3
        assert np.allclose(corr["matrix"][0][0], 1.0)
        assert np.allclose(corr["matrix"][1][1], 1.0)
        assert np.allclose(corr["matrix"][2][2], 1.0)


class TestDataPreparation:
    """Tests for feature preprocessing, scaling pipelines, and categorical encodings."""

    def test_standard_scaler_transformation(self, sample_data: pd.DataFrame):
        prep = CustomerPreprocessor(scaler_type="standard", feature_set="2d")
        X_scaled, df_proc = prep.fit_transform(sample_data)

        assert X_scaled.shape == (200, 2)
        assert np.allclose(np.mean(X_scaled, axis=0), [0.0, 0.0], atol=1e-7)
        assert np.allclose(np.std(X_scaled, axis=0), [1.0, 1.0], atol=1e-7)

    def test_minmax_scaler_transformation(self, sample_data: pd.DataFrame):
        prep = CustomerPreprocessor(scaler_type="minmax", feature_set="3d")
        X_scaled, df_proc = prep.fit_transform(sample_data)

        assert X_scaled.shape == (200, 3)
        assert np.all(X_scaled >= 0.0)
        assert np.all(X_scaled <= 1.0)

    def test_unscaled_transformation(self, sample_data: pd.DataFrame):
        prep = CustomerPreprocessor(scaler_type="none", feature_set="2d")
        X_raw, _ = prep.fit_transform(sample_data)

        assert X_raw.shape == (200, 2)
        assert np.allclose(X_raw[:, 0], sample_data["annual_income"].values)
        assert np.allclose(X_raw[:, 1], sample_data["spending_score"].values)

    def test_categorical_gender_encoding_all_features(self, sample_data: pd.DataFrame):
        prep = CustomerPreprocessor(scaler_type="none", feature_set="all")
        X_all, df_proc = prep.fit_transform(sample_data)

        assert X_all.shape == (200, 4)
        assert "gender_encoded" in df_proc.columns
        assert set(np.unique(X_all[:, 0])) == {0.0, 1.0}


class TestClusteringModels:
    """Tests for K-Means, Agglomerative, DBSCAN, and PCA model implementations."""

    def test_kmeans_clustering_k5(self, sample_data: pd.DataFrame):
        prep = CustomerPreprocessor(scaler_type="standard", feature_set="2d")
        X, _ = prep.fit_transform(sample_data)

        km = train_kmeans(X, k=5, random_state=42)
        assert len(km.labels_) == 200
        assert len(set(km.labels_)) == 5
        assert km.inertia_ > 0

    def test_agglomerative_ward_k5(self, sample_data: pd.DataFrame):
        prep = CustomerPreprocessor(scaler_type="standard", feature_set="2d")
        X, _ = prep.fit_transform(sample_data)

        agg = train_agglomerative(X, k=5, linkage="ward")
        assert len(agg.labels_) == 200
        assert len(set(agg.labels_)) == 5

    def test_dbscan_clustering_and_noise(self, sample_data: pd.DataFrame):
        prep = CustomerPreprocessor(scaler_type="standard", feature_set="2d")
        X, _ = prep.fit_transform(sample_data)

        dbs = train_dbscan(X, eps=0.35, min_samples=5)
        assert len(dbs.labels_) == 200
        assert -1 in dbs.labels_  # Confirms noise points are detected

    def test_pca_projections_2d_and_3d(self, sample_data: pd.DataFrame):
        prep = CustomerPreprocessor(scaler_type="standard", feature_set="3d")
        X, _ = prep.fit_transform(sample_data)

        coords, pca = compute_pca(X, n_components=3, random_state=42)
        assert coords.shape == (200, 3)
        assert len(pca.explained_variance_ratio_) == 3
        assert np.isclose(np.sum(pca.explained_variance_ratio_), 1.0)


class TestClusterEvaluation:
    """Tests for Silhouette score, Davies-Bouldin, Calinski-Harabasz, and persona profiling."""

    def test_evaluation_metrics_k5_kmeans_benchmark(self, sample_data: pd.DataFrame):
        prep = CustomerPreprocessor(scaler_type="none", feature_set="2d")
        X, _ = prep.fit_transform(sample_data)
        km = train_kmeans(X, k=5, random_state=42)

        evaluator = ClusterEvaluator()
        metrics = evaluator.compute_metrics(X, km.labels_, inertia=km.inertia_)

        assert metrics["is_valid"] is True
        assert 0.550 <= metrics["silhouette_score"] <= 0.560
        assert 0.560 <= metrics["davies_bouldin_index"] <= 0.585
        assert 240.0 <= metrics["calinski_harabasz_score"] <= 255.0

    def test_dbscan_noise_filtering_in_evaluation(self, sample_data: pd.DataFrame):
        prep = CustomerPreprocessor(scaler_type="standard", feature_set="2d")
        X, _ = prep.fit_transform(sample_data)
        dbs = train_dbscan(X, eps=0.35, min_samples=5)

        evaluator = ClusterEvaluator()
        metrics = evaluator.compute_metrics(X, dbs.labels_)

        assert metrics["is_valid"] is True
        assert metrics["noise_count"] > 0
        assert metrics["silhouette_score"] > 0.40  # Filtered non-noise points yield high silhouette

    def test_optimal_k_sweep_peak_at_5(self, sample_data: pd.DataFrame):
        prep = CustomerPreprocessor(scaler_type="standard", feature_set="2d")
        X, _ = prep.fit_transform(sample_data)

        evaluator = ClusterEvaluator()
        sweep = evaluator.sweep_k(X, k_min=2, k_max=10, random_state=42)

        assert sweep["optimal_k"] == 5
        assert len(sweep["k_values"]) == 9
        assert len(sweep["silhouette_scores"]) == 9

    def test_persona_profiling_hungarian_bipartite_matching(self, sample_data: pd.DataFrame):
        prep = CustomerPreprocessor(scaler_type="none", feature_set="2d")
        X, _ = prep.fit_transform(sample_data)
        km = train_kmeans(X, k=5, random_state=42)

        evaluator = ClusterEvaluator()
        profiles = evaluator.profile_clusters(sample_data, km.labels_)

        assert len(profiles) == 5
        persona_names = [p["name"] for p in profiles]
        # Verify 5 distinct personas without duplication
        assert len(set(persona_names)) == 5
        assert sum(p["count"] for p in profiles) == 200
        assert np.isclose(sum(p["percentage"] for p in profiles), 100.0, atol=0.1)


class TestArtifactExporter:
    """Tests for artifact saving, joblib serialization, and JSON schema compatibility."""

    def test_export_models_and_json_contracts(self, tmp_path: Path, sample_data: pd.DataFrame):
        prep = CustomerPreprocessor(scaler_type="standard", feature_set="2d")
        X, _ = prep.fit_transform(sample_data)
        km = train_kmeans(X, k=5, random_state=42)
        coords, pca = compute_pca(X, n_components=3)

        exporter = ArtifactExporter(artifacts_dir=tmp_path / "artifacts", dashboard_dir=tmp_path / "dashboard")

        # Save models
        saved_paths = exporter.save_joblib_models({"kmeans": km, "pca": pca, "scaler": prep.scaler})
        assert "kmeans" in saved_paths
        assert Path(saved_paths["kmeans"]).exists()

        # Save metrics
        metrics_file = exporter.export_metrics_json({"optimal_k": 5, "silhouette_score": 0.5547})
        assert metrics_file.exists()

        # Save segments CSV
        df_seg = sample_data.copy()
        df_seg["cluster_id"] = km.labels_
        csv_file = exporter.export_customer_segments_csv(df_seg)
        assert csv_file.exists()

        # Save pipeline_output.json
        payload = {
            "timestamp": "2026-09-02T12:00:00Z",
            "dataset_summary": {
                "total_customers": 200,
                "features": ["annual_income", "spending_score"],
                "age_stats": {"mean": 38.8, "min": 18, "max": 70, "std": 13.9, "median": 36.0, "q1": 28.7, "q3": 49.0},
                "income_stats": {"mean": 60.5, "min": 15, "max": 137, "std": 26.2, "median": 61.5, "q1": 41.5, "q3": 78.0},
                "spending_stats": {"mean": 50.2, "min": 1, "max": 99, "std": 25.8, "median": 50.0, "q1": 34.7, "q3": 73.0},
                "gender_counts": {"Male": 88, "Female": 112},
                "female_ratio": 0.56,
            },
            "kpis": {
                "optimal_k": 5,
                "silhouette_score": 0.5547,
                "davies_bouldin_index": 0.5722,
                "calinski_harabasz_score": 248.65,
                "inertia": 65.57,
                "best_algorithm": "KMeans",
            },
            "customers": [
                {
                    "customer_id": 1,
                    "gender": "Male",
                    "age": 19,
                    "annual_income": 15.0,
                    "spending_score": 39.0,
                    "cluster_id": 0,
                    "cluster_name": "Sensible / Budget",
                    "pca_x": -0.8,
                    "pca_y": -0.4,
                    "pca_z": 0.1,
                }
            ],
            "clusters": [
                {
                    "cluster_id": 0,
                    "name": "Sensible / Budget",
                    "persona": "Budget",
                    "color": "#3B82F6",
                    "count": 23,
                    "percentage": 11.5,
                    "avg_age": 45.2,
                    "avg_income": 26.3,
                    "avg_spending": 20.9,
                }
            ],
            "model_comparisons": [
                {
                    "algorithm": "K-Means",
                    "k": 5,
                    "silhouette_score": 0.5547,
                    "davies_bouldin_index": 0.5722,
                    "calinski_harabasz_score": 248.65,
                    "description": "K-Means k=5",
                }
            ],
        }
        json_file = exporter.export_pipeline_output_json(payload, export_to_dashboard=True)
        assert json_file.exists()
        assert (tmp_path / "dashboard" / "pipeline_output.json").exists()
