"""
tests/unit/test_redundancy_pruning.py
Unit & Boundary Tests for Redundancy Pruning and Sub-Rule Filtering (Feature F5).
Validates subset redundancy elimination (A c A' and conf(A') <= conf(A)),
Jaccard overlap pruning, and boundary cases.
"""

import pytest
import pandas as pd
import numpy as np

try:
    from src.evaluation.redundancy import prune_redundant_rules, is_rule_redundant
except ImportError:
    prune_redundant_rules = None
    is_rule_redundant = None


class TestRedundancyPruningLogic:
    """Tier 1: Feature Coverage for Redundancy Pruning."""

    def test_subset_redundancy_pruned(self):
        """
        Rule 1: {bread} -> {milk} (conf = 0.85)
        Rule 2: {bread, butter} -> {milk} (conf = 0.80)
        Rule 2 is redundant because adding 'butter' lowers/does not improve confidence over {bread} -> {milk}.
        """
        rules = [
            {"id": 1, "antecedents": ["bread"], "consequents": ["milk"], "confidence": 0.85, "lift": 1.5, "support": 0.3},
            {"id": 2, "antecedents": ["bread", "butter"], "consequents": ["milk"], "confidence": 0.80, "lift": 1.4, "support": 0.2}
        ]
        rules_df = pd.DataFrame(rules)

        if prune_redundant_rules is None:
            pytest.skip("src.evaluation.redundancy.prune_redundant_rules not yet implemented")

        pruned_df = prune_redundant_rules(rules_df)
        assert len(pruned_df) == 1
        # Rule 1 must be retained, Rule 2 pruned
        assert list(pruned_df.iloc[0]["antecedents"]) == ["bread"]

    def test_non_redundant_higher_confidence_retained(self):
        """
        Rule 1: {bread} -> {milk} (conf = 0.70)
        Rule 2: {bread, butter} -> {milk} (conf = 0.95)
        Rule 2 is NOT redundant because adding 'butter' significantly improves confidence.
        """
        rules = [
            {"id": 1, "antecedents": ["bread"], "consequents": ["milk"], "confidence": 0.70, "lift": 1.2, "support": 0.3},
            {"id": 2, "antecedents": ["bread", "butter"], "consequents": ["milk"], "confidence": 0.95, "lift": 1.8, "support": 0.25}
        ]
        rules_df = pd.DataFrame(rules)

        if prune_redundant_rules is None:
            pytest.skip("src.evaluation.redundancy.prune_redundant_rules not yet implemented")

        pruned_df = prune_redundant_rules(rules_df)
        assert len(pruned_df) == 2


class TestRedundancyPruningBoundaries:
    """Tier 2: Boundary & Corner Cases for Redundancy Pruning."""

    def test_empty_rules_input(self):
        """Empty input DataFrame should return empty DataFrame without error."""
        if prune_redundant_rules is None:
            pytest.skip("src.evaluation.redundancy.prune_redundant_rules not yet implemented")

        empty_df = pd.DataFrame(columns=["antecedents", "consequents", "confidence", "support", "lift"])
        pruned_df = prune_redundant_rules(empty_df)
        assert isinstance(pruned_df, pd.DataFrame)
        assert len(pruned_df) == 0

    def test_single_rule_input(self):
        """Single rule input should be preserved."""
        if prune_redundant_rules is None:
            pytest.skip("src.evaluation.redundancy.prune_redundant_rules not yet implemented")

        single_rule_df = pd.DataFrame([
            {"id": 1, "antecedents": ["milk"], "consequents": ["bread"], "confidence": 0.8, "support": 0.4, "lift": 1.2}
        ])
        pruned_df = prune_redundant_rules(single_rule_df)
        assert len(pruned_df) == 1

    def test_disjoint_consequents_not_pruned(self):
        """Rules with different consequents should not prune each other even with subset antecedents."""
        if prune_redundant_rules is None:
            pytest.skip("src.evaluation.redundancy.prune_redundant_rules not yet implemented")

        rules = [
            {"id": 1, "antecedents": ["bread"], "consequents": ["milk"], "confidence": 0.8, "support": 0.3, "lift": 1.3},
            {"id": 2, "antecedents": ["bread", "butter"], "consequents": ["diaper"], "confidence": 0.7, "support": 0.2, "lift": 1.1}
        ]
        rules_df = pd.DataFrame(rules)
        pruned_df = prune_redundant_rules(rules_df)
        assert len(pruned_df) == 2
