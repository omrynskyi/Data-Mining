"""
Milestone 1 Challenger 2 Empirical Stress Test Suite.
Tests:
1. CLI flag matrix & combinatorial permutations
2. Joblib model serialization, deserialization, and inference on unseen test points
3. JSON output sanitization and JavaScript (Node.js) JSON.parse compatibility
"""

import itertools
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import joblib
import numpy as np
import pandas as pd
import pytest

from src.config import DEFAULT_RAW_DATA_PATH, PROJECT_ROOT
from src.data_preparation import CustomerPreprocessor
from src.export import sanitize_json


class TestCLIFlagCombinations:
    """Stress tests CLI flag permutations and error boundaries."""

    @pytest.mark.parametrize("algorithm", ["kmeans", "dbscan", "agglomerative", "all"])
    @pytest.mark.parametrize("scaler", ["standard", "minmax", "robust", "none"])
    @pytest.mark.parametrize("features", ["2d", "3d", "all", "4d"])
    def test_cli_matrix_permutations(self, tmp_path, algorithm, scaler, features):
        """Tests 64 combinations of algorithm, scaler, and feature set."""
        out_dir = tmp_path / f"out_{algorithm}_{scaler}_{features}"
        dash_dir = tmp_path / f"dash_{algorithm}_{scaler}_{features}"

        cmd = [
            sys.executable,
            str(PROJECT_ROOT / "run_pipeline.py"),
            "--data", str(DEFAULT_RAW_DATA_PATH),
            "--output-dir", str(out_dir),
            "--dashboard-dir", str(dash_dir),
            "--algorithm", algorithm,
            "--scaler", scaler,
            "--features", features,
            "--k", "4",
            "--random-state", "42",
            "--quiet",
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)
        assert result.returncode == 0, f"Failed with {result.stderr}"

        # Verify output files exist
        assert (out_dir / "metrics.json").exists()
        assert (out_dir / "customer_segments.csv").exists()
        assert (out_dir / "pipeline_output.json").exists()
        assert (out_dir / "models" / "kmeans_model.joblib").exists()
        assert (out_dir / "models" / "agglomerative_model.joblib").exists()
        assert (out_dir / "models" / "dbscan_model.joblib").exists()
        assert (out_dir / "models" / "pca_model.joblib").exists()
        if scaler != "none":
            assert (out_dir / "models" / "scaler.joblib").exists()

        # Check dashboard sync
        assert (dash_dir / "pipeline_output.json").exists()

    def test_no_export_dashboard_flag(self, tmp_path):
        """Verify --no-export-dashboard suppresses writing to dashboard directory."""
        out_dir = tmp_path / "out_no_dash"
        dash_dir = tmp_path / "dash_no_dash"

        cmd = [
            sys.executable,
            str(PROJECT_ROOT / "run_pipeline.py"),
            "--output-dir", str(out_dir),
            "--dashboard-dir", str(dash_dir),
            "--no-export-dashboard",
            "--quiet",
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        assert result.returncode == 0
        assert (out_dir / "pipeline_output.json").exists()
        assert not (dash_dir / "pipeline_output.json").exists()

    @pytest.mark.parametrize("k_val", [2, 3, 5, 8, 10, 20])
    def test_valid_k_values(self, tmp_path, k_val):
        """Tests different valid values of k."""
        out_dir = tmp_path / f"out_k_{k_val}"
        cmd = [
            sys.executable,
            str(PROJECT_ROOT / "run_pipeline.py"),
            "--output-dir", str(out_dir),
            "--k", str(k_val),
            "--no-export-dashboard",
            "--quiet",
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        assert result.returncode == 0
        with open(out_dir / "pipeline_output.json", "r") as f:
            data = json.load(f)
        assert len(data["clusters"]) == k_val

    @pytest.mark.parametrize("bad_k", [1, 0, -1, -5])
    def test_invalid_k_values_fail_gracefully(self, tmp_path, bad_k):
        """Tests that k < 2 is rejected with non-zero exit code."""
        out_dir = tmp_path / f"out_bad_k_{bad_k}"
        cmd = [
            sys.executable,
            str(PROJECT_ROOT / "run_pipeline.py"),
            "--output-dir", str(out_dir),
            "--k", str(bad_k),
            "--no-export-dashboard",
            "--quiet",
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        assert result.returncode != 0

    def test_reproducibility_with_random_state(self, tmp_path):
        """Tests that two runs with the same seed generate identical outputs."""
        out1 = tmp_path / "run1"
        out2 = tmp_path / "run2"

        for out in [out1, out2]:
            cmd = [
                sys.executable,
                str(PROJECT_ROOT / "run_pipeline.py"),
                "--output-dir", str(out),
                "--random-state", "12345",
                "--no-export-dashboard",
                "--quiet",
            ]
            res = subprocess.run(cmd, capture_output=True, text=True)
            assert res.returncode == 0

        with open(out1 / "pipeline_output.json") as f1, open(out2 / "pipeline_output.json") as f2:
            d1 = json.load(f1)
            d2 = json.load(f2)

        # Ignore timestamp diff
        del d1["timestamp"], d2["timestamp"]
        del d1["metadata"]["generated_at"], d2["metadata"]["generated_at"]
        assert d1 == d2

    def test_custom_data_path_and_missing_data(self, tmp_path):
        """Tests custom data input and non-existent input error."""
        # Non existent file
        cmd_bad = [
            sys.executable,
            str(PROJECT_ROOT / "run_pipeline.py"),
            "--data", "/non/existent/path/data.csv",
            "--output-dir", str(tmp_path / "bad_data"),
            "--quiet",
        ]
        res_bad = subprocess.run(cmd_bad, capture_output=True, text=True)
        assert res_bad.returncode != 0

        # Custom valid subset CSV
        custom_csv = tmp_path / "custom.csv"
        df = pd.read_csv(DEFAULT_RAW_DATA_PATH).head(50)
        df.to_csv(custom_csv, index=False)

        cmd_custom = [
            sys.executable,
            str(PROJECT_ROOT / "run_pipeline.py"),
            "--data", str(custom_csv),
            "--output-dir", str(tmp_path / "custom_out"),
            "--k", "3",
            "--no-export-dashboard",
            "--quiet",
        ]
        res_custom = subprocess.run(cmd_custom, capture_output=True, text=True)
        assert res_custom.returncode == 0
        with open(tmp_path / "custom_out" / "pipeline_output.json") as f:
            data = json.load(f)
        assert data["dataset_summary"]["total_customers"] == 50


class TestModelPersistenceAndInference:
    """Tests joblib model persistence, deserialization, and inference on new data."""

    @pytest.fixture(autouse=True)
    def setup_models(self, tmp_path):
        """Runs pipeline to generate fresh models for testing."""
        self.out_dir = tmp_path / "model_test_artifacts"
        cmd = [
            sys.executable,
            str(PROJECT_ROOT / "run_pipeline.py"),
            "--output-dir", str(self.out_dir),
            "--k", "5",
            "--features", "2d",
            "--scaler", "standard",
            "--random-state", "42",
            "--no-export-dashboard",
            "--quiet",
        ]
        subprocess.run(cmd, check=True)

    def test_kmeans_deserialization_and_predict(self):
        """Tests loading kmeans_model.joblib and predicting clusters for new samples."""
        kmeans_path = self.out_dir / "models" / "kmeans_model.joblib"
        scaler_path = self.out_dir / "models" / "scaler.joblib"
        pca_path = self.out_dir / "models" / "pca_model.joblib"

        assert kmeans_path.exists()
        assert scaler_path.exists()
        assert pca_path.exists()

        km = joblib.load(kmeans_path)
        scaler = joblib.load(scaler_path)
        pca = joblib.load(pca_path)

        # Create 5 synthetic test points corresponding to known clusters:
        # [Annual Income, Spending Score]
        # 1. High income, high spend (e.g., 85, 80)
        # 2. High income, low spend (e.g., 85, 20)
        # 3. Low income, high spend (e.g., 25, 80)
        # 4. Low income, low spend (e.g., 25, 20)
        # 5. Mid income, mid spend (e.g., 55, 50)
        test_points = np.array([
            [85.0, 80.0],
            [85.0, 20.0],
            [25.0, 80.0],
            [25.0, 20.0],
            [55.0, 50.0],
        ])

        scaled_points = scaler.transform(test_points)
        preds = km.predict(scaled_points)

        assert len(preds) == 5
        assert all(0 <= p < 5 for p in preds)
        # Verify that different distinct points are assigned to distinct clusters
        assert len(set(preds)) >= 4

        # Test PCA transform
        pca_coords = pca.transform(scaled_points)
        assert pca_coords.shape == (5, 2)

    def test_single_sample_inference(self):
        """Tests inference on a single sample (1, 2) shape."""
        km = joblib.load(self.out_dir / "models" / "kmeans_model.joblib")
        scaler = joblib.load(self.out_dir / "models" / "scaler.joblib")

        single_point = np.array([[70.0, 60.0]])
        scaled_point = scaler.transform(single_point)
        pred = km.predict(scaled_point)

        assert pred.shape == (1,)
        assert isinstance(int(pred[0]), int)

    def test_batch_large_inference(self):
        """Tests high volume batch inference (10,000 samples)."""
        km = joblib.load(self.out_dir / "models" / "kmeans_model.joblib")
        scaler = joblib.load(self.out_dir / "models" / "scaler.joblib")

        np.random.seed(42)
        large_batch = np.column_stack([
            np.random.uniform(10, 150, 10000),
            np.random.uniform(1, 100, 10000),
        ])

        scaled_batch = scaler.transform(large_batch)
        preds = km.predict(scaled_batch)
        assert len(preds) == 10000
        assert set(preds) == {0, 1, 2, 3, 4}

    def test_3d_and_4d_model_persistence(self, tmp_path):
        """Tests persistence and inference for 3D and 4D models."""
        for feat, dim in [("3d", 3), ("all", 4)]:
            out = tmp_path / f"model_{feat}"
            cmd = [
                sys.executable,
                str(PROJECT_ROOT / "run_pipeline.py"),
                "--output-dir", str(out),
                "--features", feat,
                "--k", "5",
                "--no-export-dashboard",
                "--quiet",
            ]
            subprocess.run(cmd, check=True)

            km = joblib.load(out / "models" / "kmeans_model.joblib")
            scaler = joblib.load(out / "models" / "scaler.joblib")
            pca = joblib.load(out / "models" / "pca_model.joblib")

            dummy_input = np.ones((5, dim))
            scaled = scaler.transform(dummy_input)
            preds = km.predict(scaled)
            assert len(preds) == 5

            pca_coords = pca.transform(scaled)
            assert pca_coords.shape[1] == min(3, dim)


class TestJSONSanitizationAndJsCompatibility:
    """Tests JSON serialization, absence of NaN/Infinity, and Node.js JSON.parse compatibility."""

    def _check_no_nan_inf(self, obj, path="root"):
        """Recursively checks that no NaN, Infinity, or -Infinity exists in Python object."""
        if isinstance(obj, float):
            assert not math.isnan(obj), f"Found NaN at {path}"
            assert not math.isinf(obj), f"Found Infinity at {path}"
        elif isinstance(obj, dict):
            for k, v in obj.items():
                self._check_no_nan_inf(v, f"{path}.{k}")
        elif isinstance(obj, (list, tuple)):
            for i, v in enumerate(obj):
                self._check_no_nan_inf(v, f"{path}[{i}]")

    def test_nodejs_json_parse_compatibility(self, tmp_path):
        """Runs Node.js script to JSON.parse all exported JSON artifacts."""
        out_dir = tmp_path / "json_test_artifacts"
        dash_dir = tmp_path / "json_test_dash"
        cmd = [
            sys.executable,
            str(PROJECT_ROOT / "run_pipeline.py"),
            "--output-dir", str(out_dir),
            "--dashboard-dir", str(dash_dir),
            "--algorithm", "all",
            "--k", "5",
            "--quiet",
        ]
        subprocess.run(cmd, check=True)

        json_files = [
            out_dir / "pipeline_output.json",
            out_dir / "metrics.json",
            dash_dir / "pipeline_output.json",
        ]

        for jf in json_files:
            assert jf.exists()

            # 1. Check Python json.loads
            with open(jf, "r", encoding="utf-8") as f:
                data = json.load(f)
            self._check_no_nan_inf(data)

            # 2. Check Node.js JSON.parse
            node_cmd = [
                "node",
                "-e",
                f"const fs = require('fs'); const data = JSON.parse(fs.readFileSync('{jf}', 'utf-8')); if (!data) process.exit(1);",
            ]
            node_res = subprocess.run(node_cmd, capture_output=True, text=True)
            assert node_res.returncode == 0, f"Node.js JSON.parse failed on {jf}: {node_res.stderr}"

    def test_sanitize_json_function_directly(self):
        """Tests the sanitize_json function with direct adversarial inputs."""
        adversarial_input = {
            "nan_val": float("nan"),
            "inf_val": float("inf"),
            "neg_inf_val": float("-inf"),
            "numpy_float": np.float64(3.14159265),
            "numpy_int": np.int64(42),
            "numpy_array": np.array([1.0, 2.0, float("nan")]),
            "nested": {
                "inner_nan": float("nan"),
                "valid": 100,
            },
            "list_with_nan": [1.0, float("nan"), "hello"],
        }

        sanitized = sanitize_json(adversarial_input)

        assert sanitized["nan_val"] is None
        assert sanitized["inf_val"] is None
        assert sanitized["neg_inf_val"] is None
        assert sanitized["numpy_float"] == 3.1416
        assert sanitized["numpy_int"] == 42
        assert sanitized["numpy_array"] == [1.0, 2.0, None]
        assert sanitized["nested"]["inner_nan"] is None
        assert sanitized["nested"]["valid"] == 100
        assert sanitized["list_with_nan"] == [1.0, None, "hello"]

        # Verify that serialized string is valid JSON
        serialized = json.dumps(sanitized)
        assert "NaN" not in serialized
        assert "Infinity" not in serialized

        # Parse with Node.js
        node_cmd = [
            "node",
            "-e",
            f"JSON.parse('{serialized}')",
        ]
        node_res = subprocess.run(node_cmd, capture_output=True, text=True)
        assert node_res.returncode == 0
