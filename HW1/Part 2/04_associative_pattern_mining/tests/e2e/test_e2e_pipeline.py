"""
tests/e2e/test_e2e_pipeline.py
Tier 4 Real-World Workload & Acceptance Tests: Full CRISP-DM Pipeline Execution (Scenario S1).
Executes `run_pipeline.py` end-to-end against datasets, verifying artifact creation,
rule discovery, and stage timing.
"""

import os
import sys
import json
import time
import subprocess
import pytest

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))


class TestE2EPipelineExecution:
    """Tier 4: Scenario S1 - Full CRISP-DM Market Basket Analysis Pipeline."""

    def test_e2e_pipeline_full_execution_synthetic(self, tmp_path):
        """Execute run_pipeline.py end-to-end with all default arguments."""
        output_dir = tmp_path / "artifacts"
        output_dir.mkdir()

        cmd = [
            sys.executable,
            os.path.join(PROJECT_ROOT, "run_pipeline.py"),
            "--dataset", "synthetic",
            "--algorithm", "fpgrowth",
            "--min-support", "0.01",
            "--min-confidence", "0.3",
            "--output-dir", str(output_dir)
        ]

        if not os.path.exists(os.path.join(PROJECT_ROOT, "run_pipeline.py")):
            pytest.skip("run_pipeline.py entrypoint not yet created")

        start_time = time.time()
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=PROJECT_ROOT)
        elapsed = time.time() - start_time

        assert result.returncode == 0, f"run_pipeline.py failed:\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
        assert elapsed < 30.0, f"Pipeline execution took too long: {elapsed:.2f}s"

        # Validate summary artifact content
        summary_path = output_dir / "pipeline_summary.json"
        assert summary_path.exists()
        with open(summary_path, "r", encoding="utf-8") as f:
            summary = json.load(f)

        assert "crisp_dm_stages" in summary
        assert summary["crisp_dm_stages"]["modeling"]["frequent_itemsets_total"] > 0
        assert len(summary["top_rules"]) > 0

    def test_e2e_pipeline_with_apriori_algorithm(self, tmp_path):
        """Execute run_pipeline.py with --algorithm apriori."""
        output_dir = tmp_path / "artifacts_apriori"
        output_dir.mkdir()

        cmd = [
            sys.executable,
            os.path.join(PROJECT_ROOT, "run_pipeline.py"),
            "--dataset", "synthetic",
            "--algorithm", "apriori",
            "--min-support", "0.02",
            "--min-confidence", "0.3",
            "--output-dir", str(output_dir),
            "--quiet"
        ]

        if not os.path.exists(os.path.join(PROJECT_ROOT, "run_pipeline.py")):
            pytest.skip("run_pipeline.py entrypoint not yet created")

        result = subprocess.run(cmd, capture_output=True, text=True, cwd=PROJECT_ROOT)
        assert result.returncode == 0, f"Apriori pipeline run failed:\n{result.stderr}\n{result.stdout}"
        assert (output_dir / "pipeline_summary.json").exists()
