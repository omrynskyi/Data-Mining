"""
Global Pytest Fixtures and Helpers for Customer Segmentation E2E Test Suite.
"""

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple
import pytest


@pytest.fixture(scope="session")
def project_root() -> Path:
    """Returns the absolute path to the project root directory."""
    return Path(__file__).resolve().parent.parent


@pytest.fixture(scope="session")
def raw_data_path(project_root: Path) -> Path:
    """Returns the path to the raw Mall Customers CSV dataset."""
    return project_root / "data" / "raw" / "Mall_Customers.csv"


@pytest.fixture(scope="session")
def artifacts_dir(project_root: Path) -> Path:
    """Returns the path to the artifacts directory."""
    return project_root / "artifacts"


@pytest.fixture(scope="session")
def dashboard_dir(project_root: Path) -> Path:
    """Returns the path to the React dashboard directory."""
    return project_root / "dashboard"


@pytest.fixture(scope="session")
def cli_runner(project_root: Path):
    """
    Executes CLI commands in the project root directory.
    Returns a function (cmd_args: List[str], env: dict) -> (exit_code, stdout, stderr).
    """
    def _run(cmd_args: List[str], cwd: Path = project_root, env: Dict[str, str] = None, timeout: int = 120) -> Tuple[int, str, str]:
        run_env = os.environ.copy()
        if env:
            run_env.update(env)
        # Add project_root to PYTHONPATH
        run_env["PYTHONPATH"] = str(project_root) + (os.pathsep + run_env.get("PYTHONPATH", "") if "PYTHONPATH" in run_env else "")
        
        proc = subprocess.run(
            cmd_args,
            cwd=str(cwd),
            env=run_env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout,
        )
        return proc.returncode, proc.stdout, proc.stderr

    return _run


@pytest.fixture
def validate_pipeline_json_schema():
    """
    Validates a dictionary against the expected PipelineOutputJSON schema.
    Returns (is_valid, error_message).
    """
    def _validate(data: Dict[str, Any]) -> Tuple[bool, str]:
        if not isinstance(data, dict):
            return False, "Root must be a JSON object (dictionary)"

        required_top_keys = ["timestamp", "dataset_summary", "kpis", "customers", "clusters", "model_comparisons"]
        for k in required_top_keys:
            if k not in data:
                return False, f"Missing required top-level key: {k}"

        # 1. Dataset Summary
        ds = data["dataset_summary"]
        if not isinstance(ds, dict):
            return False, "dataset_summary must be a dictionary"
        for stat_field in ["age_stats", "income_stats", "spending_stats"]:
            if stat_field not in ds:
                return False, f"dataset_summary missing {stat_field}"
            for metric in ["mean", "min", "max", "std"]:
                if metric not in ds[stat_field]:
                    return False, f"dataset_summary.{stat_field} missing {metric}"

        if "total_customers" not in ds or not isinstance(ds["total_customers"], (int, float)):
            return False, "dataset_summary missing valid total_customers"

        # 2. KPIs
        kpis = data["kpis"]
        if not isinstance(kpis, dict):
            return False, "kpis must be a dictionary"
        required_kpis = ["optimal_k", "silhouette_score", "davies_bouldin_index", "calinski_harabasz_score"]
        for rk in required_kpis:
            if rk not in kpis:
                return False, f"kpis missing {rk}"

        if not (-1.0 <= float(kpis["silhouette_score"]) <= 1.0):
            return False, f"silhouette_score {kpis['silhouette_score']} outside [-1, 1]"
        if float(kpis["davies_bouldin_index"]) < 0:
            return False, f"davies_bouldin_index {kpis['davies_bouldin_index']} is negative"
        if float(kpis["calinski_harabasz_score"]) < 0:
            return False, f"calinski_harabasz_score {kpis['calinski_harabasz_score']} is negative"

        # 3. Customers
        customers = data["customers"]
        if not isinstance(customers, list) or len(customers) == 0:
            return False, "customers must be a non-empty list"

        cust_sample = customers[0]
        cust_required_fields = ["customer_id", "gender", "age", "annual_income", "spending_score", "cluster_id"]
        for cf in cust_required_fields:
            if cf not in cust_sample:
                return False, f"Customer object missing required field {cf}"

        # 4. Clusters
        clusters = data["clusters"]
        if not isinstance(clusters, list) or len(clusters) == 0:
            return False, "clusters must be a non-empty list"
        clust_sample = clusters[0]
        clust_required_fields = ["cluster_id", "name", "persona", "count", "percentage", "avg_age", "avg_income", "avg_spending"]
        for clf in clust_required_fields:
            if clf not in clust_sample:
                return False, f"Cluster object missing required field {clf}"

        # 5. Model Comparisons
        models = data["model_comparisons"]
        if not isinstance(models, list) or len(models) == 0:
            return False, "model_comparisons must be a non-empty list"

        return True, "Valid"

    return _validate


@pytest.fixture
def validate_autoresearch_json_schema():
    """
    Validates a dictionary against the expected Autoresearch JSON schema.
    """
    def _validate(data: Dict[str, Any]) -> Tuple[bool, str]:
        if not isinstance(data, dict):
            return False, "Root must be a dictionary"

        required_keys = ["benchmark_paper", "baseline_metrics", "iterations", "best_configuration", "final_metrics"]
        for rk in required_keys:
            if rk not in data:
                return False, f"Missing autoresearch key: {rk}"

        # Benchmark paper check
        bp = data["benchmark_paper"]
        if not isinstance(bp, dict) or "title" not in bp:
            return False, "benchmark_paper must include at least 'title'"

        # Iterations check
        iters = data["iterations"]
        if not isinstance(iters, list):
            return False, "iterations must be a list"

        return True, "Valid"

    return _validate
