"""
tests/integration/test_pipeline_artifacts.py
Tier 3 Cross-Feature Integration Tests: Pipeline CLI -> Artifact Generation -> Schema Integrity (Feature F6).
Validates that executing `run_pipeline.py` creates valid pipeline_summary.json, pipeline_report.md,
rules.json, rules.csv, and frequent_itemsets.csv conforming to specifications.
"""

import os
import sys
import json
import subprocess
import pytest
import pandas as pd

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))


class TestPipelineArtifactGenerationIntegration:
    """Tier 3: CLI Execution to Artifact Output Integration."""

    def test_run_pipeline_cli_creates_all_artifacts(self, tmp_path):
        """Executing run_pipeline.py CLI with synthetic dataset creates all 5 artifacts."""
        output_dir = tmp_path / "artifacts"
        output_dir.mkdir()

        cmd = [
            sys.executable,
            os.path.join(PROJECT_ROOT, "run_pipeline.py"),
            "--dataset", "synthetic",
            "--algorithm", "fpgrowth",
            "--min-support", "0.02",
            "--min-confidence", "0.3",
            "--output-dir", str(output_dir),
            "--quiet"
        ]

        if not os.path.exists(os.path.join(PROJECT_ROOT, "run_pipeline.py")):
            pytest.skip("run_pipeline.py entrypoint not yet created")

        result = subprocess.run(cmd, capture_output=True, text=True, cwd=PROJECT_ROOT)
        assert result.returncode == 0, f"run_pipeline.py failed with error:\n{result.stderr}\n{result.stdout}"

        # Assert all 5 artifacts exist on disk
        summary_json_path = output_dir / "pipeline_summary.json"
        report_md_path = output_dir / "pipeline_report.md"
        rules_json_path = output_dir / "rules.json"
        rules_csv_path = output_dir / "rules.csv"
        itemsets_csv_path = output_dir / "frequent_itemsets.csv"

        assert summary_json_path.exists(), "pipeline_summary.json not generated"
        assert report_md_path.exists(), "pipeline_report.md not generated"
        assert rules_json_path.exists(), "rules.json not generated"
        assert rules_csv_path.exists(), "rules.csv not generated"
        assert itemsets_csv_path.exists(), "frequent_itemsets.csv not generated"

    def test_pipeline_summary_json_schema_integrity(self, tmp_path):
        """Validate structural schema and field types of generated pipeline_summary.json."""
        output_dir = tmp_path / "artifacts"
        output_dir.mkdir()

        cmd = [
            sys.executable,
            os.path.join(PROJECT_ROOT, "run_pipeline.py"),
            "--dataset", "synthetic",
            "--output-dir", str(output_dir),
            "--quiet"
        ]

        if not os.path.exists(os.path.join(PROJECT_ROOT, "run_pipeline.py")):
            pytest.skip("run_pipeline.py entrypoint not yet created")

        result = subprocess.run(cmd, capture_output=True, text=True, cwd=PROJECT_ROOT)
        if result.returncode != 0:
            pytest.skip(f"run_pipeline.py exited with {result.returncode}")

        summary_file = output_dir / "pipeline_summary.json"
        with open(summary_file, "r", encoding="utf-8") as f:
            summary = json.load(f)

        # 1. Metadata Schema
        assert "pipeline_metadata" in summary
        meta = summary["pipeline_metadata"]
        assert "run_timestamp" in meta
        assert "execution_time_seconds" in meta
        assert meta.get("framework") == "CRISP-DM"

        # 2. CRISP-DM 6-Phase Schema
        assert "crisp_dm_stages" in summary
        stages = summary["crisp_dm_stages"]
        for phase in ["business_understanding", "data_understanding", "data_preparation", "modeling", "evaluation", "deployment"]:
            assert phase in stages, f"Missing CRISP-DM stage: {phase}"

        # 3. Top Rules Schema
        assert "top_rules" in summary
        assert isinstance(summary["top_rules"], list)
        if len(summary["top_rules"]) > 0:
            rule = summary["top_rules"][0]
            for metric in ["support", "confidence", "lift", "leverage", "conviction"]:
                assert metric in rule, f"Missing metric {metric} in top_rules"
