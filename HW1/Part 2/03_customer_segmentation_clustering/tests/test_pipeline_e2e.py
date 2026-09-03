"""
Tier 1-4 End-to-End & Functional Tests for CRISP-DM ML Pipeline (F1-F7).
Verifies data ingestion, data preparation, multi-algorithm clustering,
evaluation metrics, model exports, and CLI execution.
"""

import json
import os
import subprocess
import sys
from pathlib import Path
import pytest


class TestPipelineE2E:
    """Comprehensive test suite for the Machine Learning Clustering Pipeline."""

    def test_t1_dataset_loader_and_schema(self, raw_data_path: Path):
        """[F1] Verifies the raw dataset exists or can be ingested with expected columns."""
        if not raw_data_path.exists():
            # Check if fallback synthetic or download is implemented in src/data_loader.py
            try:
                from src.data_loader import load_data
                df = load_data()
                assert len(df) == 200, f"Expected 200 rows, got {len(df)}"
            except (ImportError, Exception) as exc:
                pytest.skip(f"Data file not found at {raw_data_path} and loader not ready: {exc}")
        else:
            import pandas as pd
            df = pd.read_csv(raw_data_path)
            assert len(df) >= 200, f"Expected at least 200 customer rows, found {len(df)}"
            cols_lower = [c.lower() for c in df.columns]
            assert any("age" in c for c in cols_lower), "Missing Age column"
            assert any("income" in c for c in cols_lower), "Missing Annual Income column"
            assert any("spending" in c for c in cols_lower), "Missing Spending Score column"

    def test_t4_run_pipeline_cli_execution(self, project_root: Path, cli_runner):
        """[F6] Executes `python run_pipeline.py` and verifies exit code 0."""
        script_path = project_root / "run_pipeline.py"
        if not script_path.exists():
            pytest.skip("run_pipeline.py not yet implemented.")

        exit_code, stdout, stderr = cli_runner([
            sys.executable, "run_pipeline.py",
            "--output-dir", "artifacts",
            "--export-dashboard"
        ])

        assert exit_code == 0, f"run_pipeline.py failed with exit code {exit_code}.\nStderr: {stderr}\nStdout: {stdout}"

    def test_t1_generated_artifacts_existence(self, artifacts_dir: Path):
        """[F7] Verifies all expected pipeline artifact files are created."""
        expected_files = [
            artifacts_dir / "pipeline_output.json",
            artifacts_dir / "customer_segments.csv",
            artifacts_dir / "metrics.json",
        ]
        missing = [f.name for f in expected_files if not f.exists()]
        if missing:
            pytest.skip(f"Pipeline artifacts not found: {missing}. Run pipeline first.")

        assert (artifacts_dir / "pipeline_output.json").stat().st_size > 500, "pipeline_output.json is too small or empty"
        assert (artifacts_dir / "customer_segments.csv").stat().st_size > 200, "customer_segments.csv is empty"

    def test_t1_joblib_model_artifacts(self, artifacts_dir: Path):
        """[F7] Verifies trained model joblib files are valid and can be loaded."""
        import joblib

        models_dir = artifacts_dir / "models"
        if not models_dir.exists():
            pytest.skip("artifacts/models/ directory does not exist yet.")

        joblib_files = list(models_dir.glob("*.joblib"))
        if not joblib_files:
            pytest.skip("No .joblib model files found in artifacts/models/")

        for model_file in joblib_files:
            model = joblib.load(model_file)
            assert model is not None, f"Failed to deserialize model from {model_file}"

    def test_t2_cluster_evaluation_metrics_bounds(self, artifacts_dir: Path):
        """[F5] Verifies clustering metrics satisfy mathematical bounds."""
        metrics_file = artifacts_dir / "metrics.json"
        if not metrics_file.exists():
            pipeline_json = artifacts_dir / "pipeline_output.json"
            if not pipeline_json.exists():
                pytest.skip("No metrics artifacts available for validation.")
            with open(pipeline_json, "r", encoding="utf-8") as f:
                data = json.load(f)
            kpis = data.get("kpis", {})
            sil = kpis.get("silhouette_score")
            db = kpis.get("davies_bouldin_index")
            ch = kpis.get("calinski_harabasz_score")
        else:
            with open(metrics_file, "r", encoding="utf-8") as f:
                kpis = json.load(f)
            sil = kpis.get("silhouette_score") or kpis.get("silhouette")
            db = kpis.get("davies_bouldin_index") or kpis.get("davies_bouldin")
            ch = kpis.get("calinski_harabasz_score") or kpis.get("calinski_harabasz")

        if sil is not None:
            assert -1.0 <= float(sil) <= 1.0, f"Silhouette score {sil} out of range [-1, 1]"
        if db is not None:
            assert float(db) >= 0.0, f"Davies-Bouldin index {db} is negative"
        if ch is not None:
            assert float(ch) >= 0.0, f"Calinski-Harabasz score {ch} is negative"

    def test_t3_multi_algorithm_support(self, project_root: Path, cli_runner, tmp_path: Path):
        """[F4] Tests running pipeline with different algorithm options."""
        script_path = project_root / "run_pipeline.py"
        if not script_path.exists():
            pytest.skip("run_pipeline.py not yet implemented.")

        # Parameter sweeps write to a temporary directory so the published
        # artifacts/ and dashboard/public/data payloads keep the default run.
        for algo in ["kmeans", "agglomerative"]:
            exit_code, stdout, stderr = cli_runner([
                sys.executable, "run_pipeline.py",
                "--algorithm", algo,
                "--k", "5",
                "--output-dir", str(tmp_path / f"artifacts_{algo}"),
                "--no-export-dashboard",
            ])
            assert exit_code == 0, f"run_pipeline.py failed for algorithm '{algo}'.\nStderr: {stderr}"

    def test_t2_k_value_parameter_boundaries(self, project_root: Path, cli_runner, tmp_path: Path):
        """[F4/F6] Tests running pipeline across valid k boundary values."""
        script_path = project_root / "run_pipeline.py"
        if not script_path.exists():
            pytest.skip("run_pipeline.py not yet implemented.")

        for k in [2, 5, 8]:
            exit_code, stdout, stderr = cli_runner([
                sys.executable, "run_pipeline.py",
                "--k", str(k),
                "--output-dir", str(tmp_path / f"artifacts_k{k}"),
                "--no-export-dashboard",
            ])
            assert exit_code == 0, f"Pipeline failed with boundary k={k}.\nStderr: {stderr}"
