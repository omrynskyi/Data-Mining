"""
tests/unit/test_crisp_dm_stages.py
Unit & Boundary Tests for CRISP-DM 6-Phase Pipeline Stages (Feature F2).
Validates Business Understanding, Data Understanding (EDA), Data Preparation,
Modeling, Evaluation, and Deployment stage outputs.
"""

import pytest
import pandas as pd
import numpy as np

try:
    from src.eda.profiler import profile_dataset, compute_basket_size_stats, compute_item_frequency
    from src.deployment.pipeline import CRISPDMPipeline, run_crisp_dm_pipeline
except ImportError:
    profile_dataset = None
    compute_basket_size_stats = None
    compute_item_frequency = None
    CRISPDMPipeline = None
    run_crisp_dm_pipeline = None


class TestCRISPDMStage1BusinessUnderstanding:
    """Phase 1: Business Understanding formulation and parameter anchoring."""

    def test_business_understanding_metadata(self, sample_pipeline_summary_dict):
        """Verify business understanding stage contains required objectives and target KPIs."""
        bu = sample_pipeline_summary_dict["crisp_dm_stages"]["business_understanding"]
        assert "objective" in bu
        assert "target_kpi" in bu
        assert isinstance(bu["objective"], str)
        assert len(bu["objective"]) > 0


class TestCRISPDMStage2DataUnderstanding:
    """Phase 2: Data Understanding, EDA statistics, basket depth, and Pareto distribution."""

    def test_basket_size_distribution_stats(self, sample_clean_transactions):
        """Verify basket size stats calculation (min, max, mean, median, quartiles)."""
        if compute_basket_size_stats is None:
            pytest.skip("src.eda.profiler.compute_basket_size_stats not yet implemented")
        
        stats = compute_basket_size_stats(sample_clean_transactions)
        assert isinstance(stats, dict)
        expected_keys = {"min", "max", "mean", "median"}
        assert expected_keys.issubset(set(stats.keys()))
        assert stats["min"] >= 1
        assert stats["max"] >= stats["min"]
        assert stats["mean"] > 0

    def test_item_frequency_ranking(self, sample_clean_transactions):
        """Verify item frequency computes accurate counts and support proportions."""
        if compute_item_frequency is None:
            pytest.skip("src.eda.profiler.compute_item_frequency not yet implemented")
        
        freq_df = compute_item_frequency(sample_clean_transactions)
        assert isinstance(freq_df, (pd.DataFrame, list, dict))
        if isinstance(freq_df, pd.DataFrame):
            assert "item" in freq_df.columns
            assert "count" in freq_df.columns or "frequency" in freq_df.columns

    def test_data_understanding_summary_schema(self, sample_pipeline_summary_dict):
        """Verify Phase 2 Data Understanding matches expected schema."""
        du = sample_pipeline_summary_dict["crisp_dm_stages"]["data_understanding"]
        assert "raw_records_count" in du
        assert "unique_invoices" in du
        assert "unique_items" in du
        assert "basket_size_stats" in du
        assert du["raw_records_count"] > 0


class TestCRISPDMStage3DataPreparation:
    """Phase 3: Data Preparation cleaning audit, filtering steps, and matrix density."""

    def test_data_preparation_step_tracking(self, sample_pipeline_summary_dict):
        """Verify that applied cleaning steps are recorded in the summary."""
        dp = sample_pipeline_summary_dict["crisp_dm_stages"]["data_preparation"]
        assert "cleaning_steps_applied" in dp
        assert isinstance(dp["cleaning_steps_applied"], list)
        assert len(dp["cleaning_steps_applied"]) > 0
        assert "cleaned_transactions_count" in dp
        assert "matrix_shape" in dp
        assert "matrix_density_pct" in dp


class TestCRISPDMStage4Modeling:
    """Phase 4: Modeling frequent itemsets generation and rule extraction."""

    def test_modeling_stage_itemset_distribution(self, sample_pipeline_summary_dict):
        """Verify frequent itemsets count and itemset breakdown by length."""
        mod = sample_pipeline_summary_dict["crisp_dm_stages"]["modeling"]
        assert "frequent_itemsets_total" in mod
        assert mod["frequent_itemsets_total"] >= 0
        assert "itemsets_by_length" in mod
        assert "raw_rules_generated" in mod


class TestCRISPDMStage5Evaluation:
    """Phase 5: Evaluation, threshold filtering, redundancy pruning, and business categorization."""

    def test_evaluation_stage_metrics(self, sample_pipeline_summary_dict):
        """Verify evaluation metrics: filtering, redundancy counts, and business clusters."""
        ev = sample_pipeline_summary_dict["crisp_dm_stages"]["evaluation"]
        assert "rules_after_threshold_filtering" in ev
        assert "redundant_rules_pruned" in ev
        assert "final_actionable_rules_count" in ev
        assert "rule_categories" in ev
        assert ev["final_actionable_rules_count"] == (
            ev["rules_after_threshold_filtering"] - ev["redundant_rules_pruned"]
        )


class TestCRISPDMStage6Deployment:
    """Phase 6: Deployment artifact inventory and verification."""

    def test_deployment_artifacts_inventory(self, sample_pipeline_summary_dict):
        """Verify list of generated production artifacts."""
        dep = sample_pipeline_summary_dict["crisp_dm_stages"]["deployment"]
        assert "artifacts_generated" in dep
        assert isinstance(dep["artifacts_generated"], list)
        assert len(dep["artifacts_generated"]) >= 3


class TestCRISPDMPipelineOrchestrator:
    """End-to-End stage execution and state flow."""

    def test_crisp_dm_pipeline_execution_synthetic(self, tmp_path):
        """Verify pipeline execution on synthetic data generates all 6 stage outputs."""
        if CRISPDMPipeline is None and run_crisp_dm_pipeline is None:
            pytest.skip("CRISPDM pipeline orchestrator not yet implemented")
        
        output_dir = tmp_path / "artifacts"
        output_dir.mkdir()
        
        if CRISPDMPipeline is not None:
            pipeline = CRISPDMPipeline(dataset_name="synthetic", output_dir=str(output_dir))
            summary = pipeline.run()
        else:
            summary = run_crisp_dm_pipeline(dataset="synthetic", output_dir=str(output_dir))
        
        assert isinstance(summary, dict)
        assert "pipeline_metadata" in summary
        assert "crisp_dm_stages" in summary
        assert "top_rules" in summary
        
        stages = summary["crisp_dm_stages"]
        expected_stages = [
            "business_understanding",
            "data_understanding",
            "data_preparation",
            "modeling",
            "evaluation",
            "deployment"
        ]
        for st in expected_stages:
            assert st in stages, f"Missing CRISP-DM stage: {st}"
