"""
Unit tests for Apriori, FP-Growth, and Association Rule Extraction.
"""

import pandas as pd
import pytest

from src.mining.apriori import apriori
from src.mining.engine import compare_algorithms, mine_association_rules
from src.mining.fpgrowth import fpgrowth, fpgrowth_custom
from src.mining.rules import generate_association_rules


def test_apriori_toy_dataset(simple_onehot_df):
    """Test Apriori itemset counts on canonical toy dataset."""
    itemsets = apriori(simple_onehot_df, min_support=0.3, max_len=3)
    assert not itemsets.empty
    # MILK appears in 6/10 -> supp=0.6, BREAD appears in 7/10 -> supp=0.7, BUTTER in 5/10 -> supp=0.5
    supp_dict = {tuple(sorted(list(row["itemsets"]))): row["support"] for _, row in itemsets.iterrows()}
    assert pytest.approx(supp_dict[("BREAD",)]) == 0.7
    assert pytest.approx(supp_dict[("MILK",)]) == 0.6
    assert pytest.approx(supp_dict[("BUTTER",)]) == 0.5
    assert pytest.approx(supp_dict[("BREAD", "BUTTER")]) == 0.5
    assert pytest.approx(supp_dict[("BREAD", "MILK")]) == 0.4


def test_fpgrowth_and_apriori_equivalence(simple_onehot_df):
    """Assert that Apriori, custom FP-Growth, and engine FP-Growth produce identical itemsets."""
    apr_res = apriori(simple_onehot_df, min_support=0.2, max_len=4)
    fp_custom_res = fpgrowth_custom(simple_onehot_df, min_support=0.2, max_len=4)
    fp_auto_res = fpgrowth(simple_onehot_df, min_support=0.2, max_len=4, engine="auto")

    apr_sets = {frozenset(s): round(supp, 4) for s, supp in zip(apr_res["itemsets"], apr_res["support"])}
    fp_custom_sets = {frozenset(s): round(supp, 4) for s, supp in zip(fp_custom_res["itemsets"], fp_custom_res["support"])}
    fp_auto_sets = {frozenset(s): round(supp, 4) for s, supp in zip(fp_auto_res["itemsets"], fp_auto_res["support"])}

    assert apr_sets == fp_custom_sets
    assert apr_sets == fp_auto_sets


def test_max_len_constraint(simple_onehot_df):
    """Test that max_len bounds the maximum size of frequent itemsets."""
    res_k2 = apriori(simple_onehot_df, min_support=0.1, max_len=2)
    assert all(res_k2["length"] <= 2)

    res_k3 = fpgrowth(simple_onehot_df, min_support=0.1, max_len=3)
    assert all(res_k3["length"] <= 3)


def test_rules_generation_from_itemsets(simple_onehot_df):
    """Test rule generation produces valid antecedents, consequents, and metrics."""
    itemsets = fpgrowth(simple_onehot_df, min_support=0.2)
    rules = generate_association_rules(itemsets, min_confidence=0.4, metric="lift", min_metric_val=1.0)

    assert not rules.empty
    for _, row in rules.iterrows():
        assert len(row["antecedents"]) >= 1
        assert len(row["consequents"]) >= 1
        assert row["confidence"] >= 0.4
        assert row["lift"] >= 1.0
        # Antecedent and consequent must be disjoint
        ant_set = set(row["antecedents"])
        con_set = set(row["consequents"])
        assert ant_set.isdisjoint(con_set)


def test_algorithm_comparison_benchmark(simple_onehot_df):
    """Test compare_algorithms utility."""
    cmp_stats = compare_algorithms(simple_onehot_df, min_support=0.2)
    assert cmp_stats["itemsets_identical"] is True
    assert cmp_stats["apriori_itemset_count"] > 0
    assert cmp_stats["fpgrowth_itemset_count"] > 0
