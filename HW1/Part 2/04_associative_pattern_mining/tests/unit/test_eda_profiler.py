"""
Unit tests for EDA Profiler.
"""

from src.eda.profiler import profile_dataset


def test_profile_dataset_stats(sample_raw_retail_df, sample_cleaned_dataset):
    profile = profile_dataset(sample_raw_retail_df, "sample", sample_cleaned_dataset)
    assert profile.raw_records_count == len(sample_raw_retail_df)
    assert profile.unique_invoices > 0
    assert profile.unique_items > 0
    assert profile.basket_size_stats["mean"] > 0
    assert len(profile.top_frequent_items) > 0
    assert "top_10_percent_items_coverage_pct" in profile.pareto_analysis
    assert profile.sparsity_pct >= 0.0 and profile.sparsity_pct <= 100.0
