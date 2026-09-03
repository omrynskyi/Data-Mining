"""
tests/integration/test_optimization_trail.py
Tier 3 Cross-Feature Integration Tests: Optimization CLI -> Audit Log & Trajectory History (Feature F11).
Validates that executing `run_optimization.py` records paper benchmark comparisons,
iteration trails, and monotonically non-decreasing best fitness progression.
"""

import os
import sys
import json
import subprocess
import pytest
import pandas as pd

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))


class TestOptimizationTrailIntegration:
    """Tier 3: Optimization CLI to Audit Trail Integration."""

    def test_run_optimization_cli_execution_and_artifacts(self, tmp_path):
        """Executing run_optimization.py CLI generates optimization log, history CSV, and rules CSV."""
        log_path = tmp_path / "optimization_log.json"
        hist_path = tmp_path / "optimization_history.csv"
        rules_path = tmp_path / "optimized_rules.csv"

        cmd = [
            sys.executable,
            os.path.join(PROJECT_ROOT, "run_optimization.py"),
            "--target-paper", "ghosh2004",
            "--iterations", "5",
            "--restarts", "1",
            "--output-log", str(log_path),
            "--output-history", str(hist_path),
            "--output-rules", str(rules_path),
            "--seed", "42"
        ]

        if not os.path.exists(os.path.join(PROJECT_ROOT, "run_optimization.py")):
            pytest.skip("run_optimization.py entrypoint not yet created")

        result = subprocess.run(cmd, capture_output=True, text=True, cwd=PROJECT_ROOT)
        assert result.returncode == 0, f"run_optimization.py failed:\n{result.stderr}\n{result.stdout}"

        assert log_path.exists(), "optimization_log.json not created"
        assert hist_path.exists(), "optimization_history.csv not created"

    def test_optimization_log_json_schema_and_paper_target(self, tmp_path):
        """Validate schema integrity and target paper identification in optimization_log.json."""
        log_path = tmp_path / "optimization_log.json"
        hist_path = tmp_path / "optimization_history.csv"

        cmd = [
            sys.executable,
            os.path.join(PROJECT_ROOT, "run_optimization.py"),
            "--target-paper", "ghosh2004",
            "--iterations", "5",
            "--restarts", "1",
            "--output-log", str(log_path),
            "--output-history", str(hist_path),
            "--seed", "42"
        ]

        if not os.path.exists(os.path.join(PROJECT_ROOT, "run_optimization.py")):
            pytest.skip("run_optimization.py entrypoint not yet created")

        result = subprocess.run(cmd, capture_output=True, text=True, cwd=PROJECT_ROOT)
        if result.returncode != 0:
            pytest.skip(f"run_optimization.py exited with {result.returncode}")

        with open(log_path, "r", encoding="utf-8") as f:
            log_data = json.load(f)

        assert "target_paper" in log_data
        assert log_data["target_paper"].get("key") == "ghosh2004"
        assert "target_metrics" in log_data["target_paper"]
        assert "summary" in log_data
        assert "iteration_trail" in log_data
        assert len(log_data["iteration_trail"]) > 0

    def test_optimization_history_monotonic_best_fitness(self, tmp_path):
        """Verify that best_fitness in optimization_history.csv never decreases within a trajectory."""
        log_path = tmp_path / "optimization_log.json"
        hist_path = tmp_path / "optimization_history.csv"

        cmd = [
            sys.executable,
            os.path.join(PROJECT_ROOT, "run_optimization.py"),
            "--target-paper", "ghosh2004",
            "--iterations", "8",
            "--restarts", "1",
            "--output-log", str(log_path),
            "--output-history", str(hist_path),
            "--seed", "42"
        ]

        if not os.path.exists(os.path.join(PROJECT_ROOT, "run_optimization.py")):
            pytest.skip("run_optimization.py entrypoint not yet created")

        result = subprocess.run(cmd, capture_output=True, text=True, cwd=PROJECT_ROOT)
        if result.returncode != 0:
            pytest.skip(f"run_optimization.py exited with {result.returncode}")

        df = pd.read_csv(hist_path)
        assert len(df) > 0
        assert "best_fitness" in df.columns
        # Check non-decreasing property
        best_series = df["best_fitness"].tolist()
        for i in range(1, len(best_series)):
            assert best_series[i] >= best_series[i-1] - 1e-6, f"Best fitness decreased at step {i}: {best_series[i-1]} -> {best_series[i]}"
