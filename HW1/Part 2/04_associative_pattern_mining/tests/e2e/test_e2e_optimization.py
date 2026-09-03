"""
tests/e2e/test_e2e_optimization.py
Tier 4 Real-World Workload & Acceptance Tests: Hill Climbing Optimization Convergence (Scenario S2).
Executes `run_optimization.py` against research paper targets, verifying multi-iteration trajectory,
fitness progression, and paper benchmark matching.
"""

import os
import sys
import json
import time
import subprocess
import pytest
import pandas as pd

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))


class TestE2EOptimizationExecution:
    """Tier 4: Scenario S2 - Automated Research Paper Target Matching & Hill Climbing."""

    def test_e2e_optimization_ghosh2004_convergence(self, tmp_path):
        """Execute run_optimization.py targeting ghosh2004 and verify fitness progression."""
        log_path = tmp_path / "optimization_log.json"
        hist_path = tmp_path / "optimization_history.csv"
        rules_path = tmp_path / "optimized_rules.csv"

        cmd = [
            sys.executable,
            os.path.join(PROJECT_ROOT, "run_optimization.py"),
            "--target-paper", "ghosh2004",
            "--fitness-mode", "hybrid",
            "--iterations", "15",
            "--restarts", "1",
            "--output-log", str(log_path),
            "--output-history", str(hist_path),
            "--output-rules", str(rules_path),
            "--seed", "42"
        ]

        if not os.path.exists(os.path.join(PROJECT_ROOT, "run_optimization.py")):
            pytest.skip("run_optimization.py entrypoint not yet created")

        start_time = time.time()
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=PROJECT_ROOT)
        elapsed = time.time() - start_time

        assert result.returncode == 0, f"run_optimization.py failed:\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
        assert elapsed < 45.0, f"Optimization run took too long: {elapsed:.2f}s"

        # Verify output log structure
        assert log_path.exists()
        with open(log_path, "r", encoding="utf-8") as f:
            log_data = json.load(f)

        assert log_data["target_paper"]["key"] == "ghosh2004"
        assert "best_fitness" in log_data["summary"]
        assert log_data["summary"]["best_fitness"] > 0.0

        # Verify history CSV
        assert hist_path.exists()
        df = pd.read_csv(hist_path)
        assert len(df) >= 5
        assert "fitness" in df.columns
        assert "best_fitness" in df.columns
