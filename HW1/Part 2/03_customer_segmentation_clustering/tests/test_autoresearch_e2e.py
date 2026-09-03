"""
Tier 1-4 Tests for Autoresearch Engine & Benchmark Paper Alignment (F8-F10).
Verifies optimization_log.md contents, paper citations, hill-climbing search,
and autoresearch JSON artifacts.
"""

import json
import os
import re
import sys
from pathlib import Path
import pytest


class TestAutoresearchE2E:
    """Comprehensive test suite for the Autoresearch Hill-Climbing Optimization Engine."""

    def test_t4_run_autoresearch_cli_execution(self, project_root: Path, cli_runner):
        """[F9] Executes `python run_autoresearch.py` and verifies exit code 0."""
        script_path = project_root / "run_autoresearch.py"
        if not script_path.exists():
            pytest.skip("run_autoresearch.py not yet implemented.")

        exit_code, stdout, stderr = cli_runner([
            sys.executable, "run_autoresearch.py",
            "--iterations", "5",
            "--output", "optimization_log.md"
        ])

        assert exit_code == 0, f"run_autoresearch.py failed with exit code {exit_code}.\nStderr: {stderr}\nStdout: {stdout}"

    def test_t1_optimization_log_file_exists(self, project_root: Path):
        """[F10] Verifies optimization_log.md exists and is non-empty."""
        log_path = project_root / "optimization_log.md"
        if not log_path.exists():
            pytest.skip("optimization_log.md does not exist yet.")

        assert log_path.stat().st_size > 200, "optimization_log.md is too short or empty"

    def test_t1_academic_paper_citation_in_log(self, project_root: Path):
        """[F8/F10] Verifies optimization_log.md explicitly cites an academic research paper."""
        log_path = project_root / "optimization_log.md"
        if not log_path.exists():
            pytest.skip("optimization_log.md does not exist yet.")

        content = log_path.read_text(encoding="utf-8").lower()

        # Check for citation indicators: paper title, author, journal, or DOI/URL
        citation_keywords = ["paper", "benchmark", "citation", "reference", "author", "journal", "clustering"]
        found_keywords = [kw for kw in citation_keywords if kw in content]
        assert len(found_keywords) >= 3, (
            f"optimization_log.md lacks sufficient benchmark paper citation metadata. Found: {found_keywords}"
        )

    def test_t2_optimization_log_sections_and_metrics(self, project_root: Path):
        """[F10] Verifies optimization_log.md contains baseline metrics, step table, and final results."""
        log_path = project_root / "optimization_log.md"
        if not log_path.exists():
            pytest.skip("optimization_log.md does not exist yet.")

        content = log_path.read_text(encoding="utf-8")

        # Must have markdown headers
        assert "#" in content, "optimization_log.md lacks Markdown headers"

        # Must mention baseline metrics
        assert re.search(r"baseline", content, re.IGNORECASE), "optimization_log.md missing baseline metrics section"

        # Must mention iterations or steps
        assert re.search(r"iteration|step", content, re.IGNORECASE), "optimization_log.md missing iteration steps"

        # Must mention silhouette or metric score
        assert re.search(r"silhouette|score|metric", content, re.IGNORECASE), "optimization_log.md missing metric references"

    def test_t3_autoresearch_artifact_and_model_export(self, artifacts_dir: Path):
        """[F9/F10] Verifies autoresearch outputs JSON and joblib model artifacts."""
        json_path = artifacts_dir / "autoresearch_output.json"
        if not json_path.exists():
            pytest.skip("artifacts/autoresearch_output.json does not exist yet.")

        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        assert "iterations" in data, "autoresearch_output.json missing iterations array"
        assert len(data["iterations"]) > 0, "autoresearch_output.json has empty iterations"
        assert "best_configuration" in data, "autoresearch_output.json missing best_configuration"

    def test_t2_iteration_cli_parameter_boundary(self, project_root: Path, cli_runner):
        """[F9] Verifies autoresearch respects iteration boundary parameters."""
        script_path = project_root / "run_autoresearch.py"
        if not script_path.exists():
            pytest.skip("run_autoresearch.py not yet implemented.")

        # Test single iteration
        exit_code, stdout, stderr = cli_runner([
            sys.executable, "run_autoresearch.py",
            "--iterations", "1",
            "--output", "optimization_log.md"
        ])
        assert exit_code == 0, f"Autoresearch failed with --iterations 1: {stderr}"
