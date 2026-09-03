#!/usr/bin/env python3
"""
Main CLI Runner for the CRISP-DM Mall Customer Segmentation Pipeline.
"""

import argparse
from datetime import datetime, timezone
import logging
from pathlib import Path
import sys
from typing import Any, Dict, List, Optional
import numpy as np
import pandas as pd

from src.config import (
    ARTIFACTS_DIR,
    DASHBOARD_DATA_DIR,
    DEFAULT_K,
    DEFAULT_RANDOM_STATE,
    DEFAULT_RAW_DATA_PATH,
)
from src.data_loader import DataLoader
from src.data_preparation import CustomerPreprocessor
from src.data_understanding import DataUnderstanding
from src.evaluation import ClusterEvaluator
from src.export import ArtifactExporter, compute_feature_quartiles, sanitize_json
from src.models import ClusteringModelFactory

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("run_pipeline")


def parse_args(args_list: Optional[List[str]] = None) -> argparse.Namespace:
    """Parses command-line arguments for the clustering pipeline."""
    parser = argparse.ArgumentParser(
        description="CRISP-DM Mall Customer Segmentation Machine Learning Pipeline"
    )
    parser.add_argument(
        "--data",
        "--data-path",
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
        "--dashboard-dir",
        type=str,
        default=str(DASHBOARD_DATA_DIR),
        help=f"Directory for dashboard public JSON data (default: {DASHBOARD_DATA_DIR})",
    )
    parser.add_argument(
        "--k",
        "--n-clusters",
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
        "--feature-set",
        type=str,
        choices=["2d", "3d", "all", "4d"],
        default="2d",
        help="Feature subset: '2d' (Income/Spend), '3d' (+Age), 'all'/'4d' (+Gender) (default: 2d)",
    )
    parser.add_argument(
        "--export-dashboard",
        dest="export_dashboard",
        action="store_true",
        default=True,
        help="Copy pipeline_output.json to dashboard/public/data/ (default: True)",
    )
    parser.add_argument(
        "--no-export-dashboard",
        dest="export_dashboard",
        action="store_false",
        help="Disable auto-exporting to dashboard directory",
    )
    parser.add_argument(
        "--random-state",
        "--seed",
        type=int,
        default=DEFAULT_RANDOM_STATE,
        help=f"Random seed for reproducibility (default: {DEFAULT_RANDOM_STATE})",
    )
    parser.add_argument(
        "-q",
        "--quiet",
        action="store_true",
        default=False,
        help="Suppress non-essential log output",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        default=False,
        help="Enable debug logging output",
    )

    return parser.parse_args(args_list)


def run(args: argparse.Namespace) -> int:
    """Executes the complete CRISP-DM clustering pipeline."""
    if args.verbose:
        logger.setLevel(logging.DEBUG)
    elif args.quiet:
        logger.setLevel(logging.WARNING)

    # Validate parameters
    if args.k < 2:
        logger.error(f"Invalid cluster count k={args.k}. k must be an integer >= 2.")
        return 1

    try:
        now_iso = datetime.now(timezone.utc).isoformat()
        if not args.quiet:
            logger.info("================================================================================")
            logger.info("        CRISP-DM CUSTOMER SEGMENTATION & CLUSTERING PIPELINE                    ")
            logger.info("================================================================================")

        # ---------------------------------------------------------
        # CRISP-DM Phase 1 & 2: Ingestion & Data Understanding
        # ---------------------------------------------------------
        logger.info(f"[1/6] Ingesting & validating dataset from: {args.data}")
        loader = DataLoader(data_path=args.data)
        df_raw = loader.load_raw_data()
        logger.info(f"[2/6] Ingested {len(df_raw)} validated records. Running Exploratory Data Analysis...")

        eda = DataUnderstanding(df_raw)
        eda_summary = eda.get_dashboard_dataset_summary()
        outliers = eda.detect_outliers_iqr()
        corr_data = eda.get_correlation_matrix()

        # ---------------------------------------------------------
        # CRISP-DM Phase 3: Data Preparation & Scaling
        # ---------------------------------------------------------
        logger.info(
            f"[3/6] Preparing features (feature_set='{args.features}', scaler='{args.scaler}')..."
        )
        preprocessor = CustomerPreprocessor(
            scaler_type=args.scaler,
            feature_set=args.features,
        )
        X_scaled, df_prep = preprocessor.fit_transform(df_raw)

        # Compute 2D and 3D PCA projection coordinates
        pca_coords, pca_model = ClusteringModelFactory.compute_pca(
            X_scaled, n_components=3, random_state=args.random_state
        )

        # ---------------------------------------------------------
        # CRISP-DM Phase 4: Modeling
        # ---------------------------------------------------------
        logger.info(f"[4/6] Training clustering algorithms (k={args.k}, seed={args.random_state})...")
        model_factory = ClusteringModelFactory()

        # Fit individual models
        km = model_factory.train_kmeans(X_scaled, k=args.k, random_state=args.random_state)
        agg = model_factory.train_agglomerative(X_scaled, k=args.k, linkage="ward")
        dbs = model_factory.train_dbscan(X_scaled)

        # Select primary model labels based on --algorithm argument
        algo_choice = args.algorithm.lower()
        if algo_choice == "agglomerative":
            primary_labels = agg.labels_
            primary_model_name = f"Agglomerative (k={args.k})"
        elif algo_choice == "dbscan":
            primary_labels = dbs.labels_
            primary_model_name = "DBSCAN"
        else:
            primary_labels = km.labels_
            primary_model_name = f"KMeans (k={args.k})"

        # ---------------------------------------------------------
        # CRISP-DM Phase 5: Evaluation & Persona Profiling
        # ---------------------------------------------------------
        logger.info("[5/6] Evaluating internal validation metrics and profiling personas...")
        evaluator = ClusterEvaluator()

        km_metrics = evaluator.compute_metrics(X_scaled, km.labels_, inertia=float(km.inertia_))
        agg_metrics = evaluator.compute_metrics(X_scaled, agg.labels_)
        dbs_metrics = evaluator.compute_metrics(X_scaled, dbs.labels_)

        primary_metrics = evaluator.compute_metrics(
            X_scaled,
            primary_labels,
            inertia=float(km.inertia_) if algo_choice in ["kmeans", "all"] else None,
        )

        # K-Sweep over range [2, 10]
        k_sweep = evaluator.sweep_k(X_scaled, k_min=2, k_max=10, random_state=args.random_state)

        # Build dynamic cluster persona profiles
        cluster_profiles = evaluator.profile_clusters(df_raw, primary_labels)
        cluster_name_map = {cp["cluster_id"]: cp["name"] for cp in cluster_profiles}
        persona_title_map = {
            cp["cluster_id"]: cp.get("persona_details", {}).get("title", cp["name"])
            for cp in cluster_profiles
        }

        # Calculate distances to centroids for each customer
        df_segmented = df_raw.copy()
        df_segmented["cluster_id"] = primary_labels
        df_segmented["cluster_name"] = df_segmented["cluster_id"].map(cluster_name_map)
        df_segmented["persona_name"] = df_segmented["cluster_id"].map(persona_title_map)
        df_segmented["pca_x"] = np.round(pca_coords[:, 0], 4)
        df_segmented["pca_y"] = np.round(pca_coords[:, 1], 4)
        df_segmented["pca_z"] = np.round(pca_coords[:, 2], 4)

        # Calculate centroid coordinates in original space
        cluster_centroids: Dict[int, np.ndarray] = {}
        for cid in set(primary_labels):
            if cid == -1:
                cluster_centroids[-1] = np.array([df_raw["annual_income"].mean(), df_raw["spending_score"].mean()])
            else:
                sub = df_raw[df_segmented["cluster_id"] == cid]
                cluster_centroids[cid] = np.array([sub["annual_income"].mean(), sub["spending_score"].mean()])

        # Build customer payload array
        customers_payload: List[Dict[str, Any]] = []
        for idx, row in df_segmented.iterrows():
            cid = int(row["cluster_id"])
            c_center = cluster_centroids.get(cid, np.array([50.0, 50.0]))
            inc = float(row["annual_income"])
            spn = float(row["spending_score"])
            dist = float(np.linalg.norm(np.array([inc, spn]) - c_center))

            customers_payload.append({
                "customer_id": int(row["customer_id"]),
                "gender": str(row["gender"]),
                "age": int(row["age"]),
                "annual_income": inc,
                "annual_income_k": inc,
                "spending_score": spn,
                "cluster_id": cid,
                "cluster_name": str(row["cluster_name"]),
                "persona_name": str(row["persona_name"]),
                "pca_x": float(row["pca_x"]),
                "pca_y": float(row["pca_y"]),
                "pca_z": float(row["pca_z"]),
                "pca_1": float(row["pca_x"]),
                "pca_2": float(row["pca_y"]),
                "pca_3": float(row["pca_z"]),
                "distance_to_centroid": round(dist, 4),
            })

        # Calculate feature distributions across clusters
        distributions = []
        for feat_name, col_name in [
            ("age", "age"),
            ("annual_income_k", "annual_income"),
            ("spending_score", "spending_score"),
        ]:
            by_cluster = {}
            for cid in sorted(list(set(primary_labels))):
                sub_series = df_segmented[df_segmented["cluster_id"] == cid][col_name]
                by_cluster[cid] = compute_feature_quartiles(sub_series)
            distributions.append({
                "feature_name": feat_name,
                "by_cluster": by_cluster,
                "overall": compute_feature_quartiles(df_segmented[col_name]),
            })

        # Model Comparisons
        model_comparisons = [
            {
                "algorithm": "K-Means",
                "k": args.k,
                "silhouette_score": km_metrics["silhouette_score"],
                "davies_bouldin_index": km_metrics["davies_bouldin_index"],
                "calinski_harabasz_score": km_metrics["calinski_harabasz_score"],
                "inertia": km_metrics["inertia"],
                "noise_points": km_metrics["noise_count"],
                "description": f"K-Means with k-means++ initialization (k={args.k}).",
                "is_benchmark": True,
            },
            {
                "algorithm": "Agglomerative Hierarchical",
                "k": args.k,
                "silhouette_score": agg_metrics["silhouette_score"],
                "davies_bouldin_index": agg_metrics["davies_bouldin_index"],
                "calinski_harabasz_score": agg_metrics["calinski_harabasz_score"],
                "inertia": None,
                "noise_points": agg_metrics["noise_count"],
                "description": f"Hierarchical agglomerative clustering with Ward linkage (k={args.k}).",
                "is_benchmark": False,
            },
            {
                "algorithm": "DBSCAN",
                "k": dbs_metrics["n_clusters"],
                "silhouette_score": dbs_metrics["silhouette_score"],
                "davies_bouldin_index": dbs_metrics["davies_bouldin_index"],
                "calinski_harabasz_score": dbs_metrics["calinski_harabasz_score"],
                "inertia": None,
                "noise_points": dbs_metrics["noise_count"],
                "description": f"Density-based spatial clustering (clusters={dbs_metrics['n_clusters']}, noise={dbs_metrics['noise_count']}).",
                "is_benchmark": False,
            },
        ]

        # ---------------------------------------------------------
        # CRISP-DM Phase 6: Deployment & Export
        # ---------------------------------------------------------
        logger.info("[6/6] Exporting serialized models, metrics, and JSON payloads...")
        exporter = ArtifactExporter(
            artifacts_dir=args.output_dir,
            dashboard_dir=args.dashboard_dir,
        )

        # Save Joblib models
        models_dict = {
            "kmeans": km,
            "agglomerative": agg,
            "dbscan": dbs,
            "pca": pca_model,
        }
        if preprocessor.scaler is not None:
            models_dict["scaler"] = preprocessor.scaler
        exporter.save_joblib_models(models_dict)

        # Export customer segments CSV
        df_csv_export = df_segmented.rename(
            columns={
                "customer_id": "CustomerID",
                "gender": "Gender",
                "age": "Age",
                "annual_income": "Annual_Income_k",
                "spending_score": "Spending_Score",
                "cluster_id": "Cluster_ID",
                "cluster_name": "Cluster_Name",
                "persona_name": "Persona_Name",
                "pca_x": "PCA_1",
                "pca_y": "PCA_2",
                "pca_z": "PCA_3",
            }
        )
        exporter.export_customer_segments_csv(df_csv_export)

        # Export metrics.json
        metrics_payload = {
            "timestamp": now_iso,
            "optimal_k": k_sweep["optimal_k"],
            "best_algorithm": "KMeans",
            "silhouette_score": primary_metrics["silhouette_score"],
            "davies_bouldin_index": primary_metrics["davies_bouldin_index"],
            "calinski_harabasz_score": primary_metrics["calinski_harabasz_score"],
            "inertia": primary_metrics["inertia"],
            "primary_metrics": primary_metrics,
            "models": {
                f"kmeans_k{args.k}": {
                    "algorithm": "KMeans",
                    "k": args.k,
                    "silhouette_score": km_metrics["silhouette_score"],
                    "davies_bouldin_index": km_metrics["davies_bouldin_index"],
                    "calinski_harabasz_score": km_metrics["calinski_harabasz_score"],
                    "inertia": km_metrics["inertia"],
                },
                f"agglomerative_k{args.k}": {
                    "algorithm": "AgglomerativeClustering",
                    "k": args.k,
                    "silhouette_score": agg_metrics["silhouette_score"],
                    "davies_bouldin_index": agg_metrics["davies_bouldin_index"],
                    "calinski_harabasz_score": agg_metrics["calinski_harabasz_score"],
                    "inertia": None,
                },
                "dbscan": {
                    "algorithm": "DBSCAN",
                    "silhouette_score": dbs_metrics["silhouette_score"],
                    "davies_bouldin_index": dbs_metrics["davies_bouldin_index"],
                    "calinski_harabasz_score": dbs_metrics["calinski_harabasz_score"],
                    "n_clusters": dbs_metrics["n_clusters"],
                    "noise_points": dbs_metrics["noise_count"],
                },
            },
            "k_sweep": k_sweep["sweep_table"],
        }
        exporter.export_metrics_json(metrics_payload)

        # Export pipeline_output.json
        pipeline_payload = {
            "timestamp": now_iso,
            "metadata": {
                "generated_at": now_iso,
                "dataset_name": "Mall Customer Segmentation",
                "total_records": len(df_raw),
                "crisp_dm_phase": "Phase 6: Deployment & Artifact Synchronization",
                "pipeline_version": "1.0.0",
                "random_state": args.random_state,
                "feature_set": args.features,
                "scaler": args.scaler,
            },
            "dataset_summary": eda_summary,
            "kpis": {
                "optimal_k": k_sweep["optimal_k"],
                "silhouette_score": primary_metrics["silhouette_score"],
                "davies_bouldin_index": primary_metrics["davies_bouldin_index"],
                "calinski_harabasz_score": primary_metrics["calinski_harabasz_score"],
                "inertia": primary_metrics["inertia"],
                "best_algorithm": "KMeans",
            },
            "executive_kpis": {
                "total_customers": len(df_raw),
                "optimal_k": k_sweep["optimal_k"],
                "best_model_name": primary_model_name,
                "silhouette_score": primary_metrics["silhouette_score"],
                "davies_bouldin_index": primary_metrics["davies_bouldin_index"],
                "calinski_harabasz_index": primary_metrics["calinski_harabasz_score"],
                "mean_income_k": round(float(df_raw["annual_income"].mean()), 2),
                "mean_spending_score": round(float(df_raw["spending_score"].mean()), 2),
                "female_ratio": eda_summary.get("female_ratio", 0.56),
            },
            "clusters": cluster_profiles,
            "customers": customers_payload,
            "model_comparisons": model_comparisons,
            "diagnostics": {
                "elbow_curve": [{"k": row["k"], "value": row["inertia"]} for row in k_sweep["sweep_table"]],
                "silhouette_curve": [{"k": row["k"], "value": row["silhouette"]} for row in k_sweep["sweep_table"]],
            },
            "distributions": distributions,
            "correlation_matrix": {
                "features": corr_data["features"],
                "matrix": corr_data["matrix"],
            },
        }
        exporter.export_pipeline_output_json(
            pipeline_payload,
            export_to_dashboard=args.export_dashboard,
        )

        if not args.quiet:
            logger.info("================================================================================")
            logger.info(
                f"[SUCCESS] Pipeline complete! Silhouette: {primary_metrics['silhouette_score']}, Optimal k: {k_sweep['optimal_k']}"
            )
            logger.info(f"[SUCCESS] Output artifacts written to: {args.output_dir}/")
            logger.info("================================================================================")

        return 0

    except FileNotFoundError as fnf_err:
        logger.error(f"File error: {fnf_err}")
        return 1
    except Exception as exc:
        logger.error(f"Pipeline execution failed: {exc}", exc_info=args.verbose)
        return 1


def main() -> None:
    """CLI entry point."""
    args = parse_args()
    sys.exit(run(args))


if __name__ == "__main__":
    main()
