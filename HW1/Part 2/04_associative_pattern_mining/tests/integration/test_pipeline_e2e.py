"""
End-to-End Integration tests for CRISP-DM Pipeline and Artifact Generation.
"""

import json
import subprocess
import sys
from pathlib import Path
import pandas as pd
import pytest

from src.deployment.pipeline import CRISPDMPipeline


def test_pipeline_e2e_execution(tmp_path):
    """Test full pipeline execution producing valid summary and rules artifacts."""
    output_dir = tmp_path / "artifacts"
    pipeline = CRISPDMPipeline(
        dataset_name="synthetic",
        algorithm="fpgrowth",
        min_support=0.015,
        min_confidence=0.35,
        metric="lift",
        min_metric_val=1.2,
        output_dir=output_dir,
    )

    result = pipeline.run()
    assert result.execution_time_seconds > 0.0
    assert len(result.rules_df) > 0
    assert len(result.itemsets_df) > 0

    # 1. Check summary JSON
    summary_path = output_dir / "pipeline_summary.json"
    assert summary_path.exists()
    with open(summary_path, "r", encoding="utf-8") as f:
        summary_json = json.load(f)

    assert "pipeline_metadata" in summary_json
    assert "crisp_dm_stages" in summary_json
    assert "business_understanding" in summary_json["crisp_dm_stages"]
    assert "data_understanding" in summary_json["crisp_dm_stages"]
    assert "data_preparation" in summary_json["crisp_dm_stages"]
    assert "modeling" in summary_json["crisp_dm_stages"]
    assert "evaluation" in summary_json["crisp_dm_stages"]
    assert "deployment" in summary_json["crisp_dm_stages"]
    assert len(summary_json["top_rules"]) > 0

    # 2. Check rules JSON and CSV
    rules_json_path = output_dir / "rules.json"
    rules_csv_path = output_dir / "rules.csv"
    assert rules_json_path.exists()
    assert rules_csv_path.exists()

    with open(rules_json_path, "r", encoding="utf-8") as f:
        rules_list = json.load(f)
    assert len(rules_list) == len(result.rules_df)
    first_rule = rules_list[0]
    for metric_name in ["support", "confidence", "lift", "leverage", "conviction", "zhangs_metric", "kulczynski", "imbalance_ratio", "cosine"]:
        assert metric_name in first_rule

    # 3. Check frequent itemsets CSV
    itemsets_path = output_dir / "frequent_itemsets.csv"
    assert itemsets_path.exists()
    itemsets_df = pd.read_csv(itemsets_path)
    assert len(itemsets_df) == len(result.itemsets_df)
    assert "itemsets" in itemsets_df.columns
    assert "support" in itemsets_df.columns

    # 4. Check Markdown report
    report_path = output_dir / "pipeline_report.md"
    assert report_path.exists()
    report_text = report_path.read_text(encoding="utf-8")
    assert "# CRISP-DM Pipeline Report" in report_text
    assert "Top 10 Discovered Association Rules" in report_text


def test_cli_execution(tmp_path):
    """Test CLI execution using python run_pipeline.py."""
    out_dir = tmp_path / "cli_artifacts"
    cmd = [
        sys.executable,
        "run_pipeline.py",
        "--dataset", "synthetic",
        "--algorithm", "apriori",
        "--min-support", "0.02",
        "--min-confidence", "0.4",
        "--output-dir", str(out_dir),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    assert proc.returncode == 0, f"CLI failed with error:\n{proc.stderr}"
    assert (out_dir / "pipeline_summary.json").exists()
    assert (out_dir / "pipeline_report.md").exists()
