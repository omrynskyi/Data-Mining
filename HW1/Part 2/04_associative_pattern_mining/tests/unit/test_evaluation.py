"""
Unit tests for Evaluation, Filter, and Redundancy Pruning.
"""

import pandas as pd
import pytest

from src.evaluation.filter import categorize_rules, compute_composite_scores, filter_rules
from src.evaluation.redundancy import prune_redundant_rules


def test_composite_scores_and_categorization():
    rules_df = pd.DataFrame([
        {
            "id": 1,
            "antecedents": ["A"],
            "consequents": ["B"],
            "support": 0.05,
            "confidence": 0.70,
            "lift": 3.5,
            "leverage": 0.03,
            "conviction": 2.0,
            "zhangs_metric": 0.8,
            "kulczynski": 0.65,
            "imbalance_ratio": 0.1,
            "cosine": 0.60,
        },
        {
            "id": 2,
            "antecedents": ["C"],
            "consequents": ["D"],
            "support": 0.01,
            "confidence": 0.35,
            "lift": 1.4,
            "leverage": 0.005,
            "conviction": 1.1,
            "zhangs_metric": 0.2,
            "kulczynski": 0.30,
            "imbalance_ratio": 0.5,
            "cosine": 0.25,
        },
    ])

    scored = compute_composite_scores(rules_df)
    assert "composite_score" in scored.columns
    assert scored.loc[0, "composite_score"] > scored.loc[1, "composite_score"]

    categorized = categorize_rules(scored)
    assert categorized.loc[0, "rule_category"] == "High-Confidence Cross-Sell"


def test_redundancy_pruning():
    """
    Test that rule A, B -> C is pruned if A -> C already exists with equal or higher confidence.
    """
    rules_df = pd.DataFrame([
        # Simpler rule: {A} -> {C}, conf = 0.8
        {"id": 1, "antecedents": ["A"], "consequents": ["C"], "confidence": 0.80, "support": 0.04},
        # More complex rule with lower confidence: {A, B} -> {C}, conf = 0.75 -> REDUNDANT
        {"id": 2, "antecedents": ["A", "B"], "consequents": ["C"], "confidence": 0.75, "support": 0.03},
        # More complex rule with higher confidence: {A, D} -> {C}, conf = 0.95 -> NOT REDUNDANT
        {"id": 3, "antecedents": ["A", "D"], "consequents": ["C"], "confidence": 0.95, "support": 0.02},
    ])

    pruned_df, pruned_count = prune_redundant_rules(rules_df, return_stats=True)
    assert pruned_count == 1
    assert len(pruned_df) == 2
    # Verify the remaining rules are {A}->{C} and {A, D}->{C}
    ants = [set(row["antecedents"]) for _, row in pruned_df.iterrows()]
    assert {"A"} in ants
    assert {"A", "D"} in ants
    assert {"A", "B"} not in ants
