"""
Tier 5 Adversarial & Resiliency Hardening Tests.
Verifies system handling of missing files, bad CLI arguments, invalid parameters,
and edge error conditions.
"""

import sys
from pathlib import Path
import pytest


class TestAdversarialResilience:
    """Tier 5 Adversarial and Robustness Test Suite."""

    def test_t5_invalid_algorithm_cli_rejection(self, project_root: Path, cli_runner):
        """[F6/Tier 5] Tests that invalid algorithm choices are rejected with non-zero exit code."""
        script_path = project_root / "run_pipeline.py"
        if not script_path.exists():
            pytest.skip("run_pipeline.py not yet implemented.")

        exit_code, stdout, stderr = cli_runner([
            sys.executable, "run_pipeline.py",
            "--algorithm", "unsupported_magic_clustering_algo"
        ])

        assert exit_code != 0, f"Expected non-zero exit code for invalid algorithm, but got {exit_code}"

    def test_t5_missing_input_file_graceful_failure(self, project_root: Path, cli_runner):
        """[F1/F6/Tier 5] Tests that non-existent data path does not crash unhandled or exits non-zero."""
        script_path = project_root / "run_pipeline.py"
        if not script_path.exists():
            pytest.skip("run_pipeline.py not yet implemented.")

        exit_code, stdout, stderr = cli_runner([
            sys.executable, "run_pipeline.py",
            "--data", "non_existent_directory/non_existent_file.csv"
        ])

        assert exit_code != 0, f"Expected non-zero exit code for missing data file, but got {exit_code}"

    def test_t5_negative_or_zero_k_rejection(self, project_root: Path, cli_runner):
        """[F4/F6/Tier 5] Tests that k <= 0 or k=1 is rejected or handled with informative exit code."""
        script_path = project_root / "run_pipeline.py"
        if not script_path.exists():
            pytest.skip("run_pipeline.py not yet implemented.")

        exit_code, stdout, stderr = cli_runner([
            sys.executable, "run_pipeline.py",
            "--k", "0"
        ])

        assert exit_code != 0, f"Expected non-zero exit code for k=0, but got {exit_code}"
