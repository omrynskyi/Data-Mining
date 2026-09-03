"""
tests/integration/test_optimizer_masking_parity.py
Tier 3 Cross-Feature Integration Tests: Optimizer Evaluator vs Live Mining Engine.

The hill climber does not re-mine for every candidate. It mines once at the
loosest corner of the search domain and answers each candidate by masking that
superset (see `src/optimization/evaluator.py`). That is only legitimate if the
masked rule set is *identical* to what the mining engine returns at the same
thresholds -- otherwise the optimizer reports a champion configuration that does
not reproduce, and every metric in `optimization_log.json` is fiction.

These tests pin that equivalence across the search domain.
"""

import pytest

try:
    from src.optimization.evaluator import RuleSetEvaluator
    from src.optimization.state import OptimizationState
    from src.mining.engine import mine_association_rules
except ImportError:
    RuleSetEvaluator = None
    OptimizationState = None
    mine_association_rules = None


@pytest.fixture(scope="module")
def evaluator(request):
    """A RuleSetEvaluator over the shared toy corpus, built once for the module."""
    if RuleSetEvaluator is None:
        pytest.skip("src.optimization.evaluator not yet implemented")

    import pandas as pd

    # A corpus with enough structure to produce rules across a range of thresholds.
    baskets = [
        ["bread", "milk", "butter"], ["bread", "butter"], ["bread", "milk"],
        ["beer", "cookies"], ["bread", "milk", "butter", "cookies"],
        ["bread", "milk", "diaper"], ["beer", "diaper"], ["bread", "butter", "diaper"],
        ["milk", "diaper", "beer"], ["bread", "milk", "butter", "beer"],
        ["bread", "milk", "butter"], ["bread", "milk"], ["butter", "milk"],
        ["bread", "butter", "cookies"], ["milk", "cookies"], ["bread", "milk", "butter"],
    ]
    items = sorted({item for basket in baskets for item in basket})
    onehot = pd.DataFrame([{item: (item in basket) for item in items} for basket in baskets])

    return RuleSetEvaluator(onehot_df=onehot, cache_dir=None), onehot


# Thresholds spanning the interior and the edges of the search domain.
THRESHOLD_CASES = [
    (0.10, 0.30, 1.00, 4),
    (0.10, 0.50, 1.20, 3),
    (0.20, 0.60, 1.00, 2),
    (0.05, 0.40, 1.50, 5),
    (0.15, 0.25, 1.10, 4),
    (0.30, 0.70, 1.00, 3),
]


class TestEvaluatorEngineParity:
    """Tier 3: Masked superset must equal a fresh mining run at the same thresholds."""

    @pytest.mark.parametrize("min_support,min_confidence,min_lift,max_len", THRESHOLD_CASES)
    def test_masked_rule_count_matches_engine(
        self, evaluator, min_support, min_confidence, min_lift, max_len
    ):
        """Masking the superset yields exactly the engine's rule count."""
        evaluator_instance, _ = evaluator
        state = OptimizationState(
            min_support=min_support,
            min_confidence=min_confidence,
            min_lift=min_lift,
            max_len=max_len,
        )

        report = evaluator_instance.verify_against_engine(state)
        assert report["identical"], (
            f"Masked rule count {report['masked_rule_count']} != engine rule count "
            f"{report['engine_rule_count']} at {report['state']}"
        )

    def test_masked_rule_identities_match_engine(self, evaluator):
        """Beyond counts, the exact (antecedent, consequent) pairs must agree."""
        evaluator_instance, onehot = evaluator
        state = OptimizationState(
            min_support=0.10, min_confidence=0.40, min_lift=1.0, max_len=4, pruning_factor=0.0
        )

        mask = evaluator_instance._threshold_mask(state.clip())
        masked = {
            (frozenset(row["antecedents"]), frozenset(row["consequents"]))
            for _, row in evaluator_instance.rules_df.loc[mask].iterrows()
        }

        _, engine_rules = mine_association_rules(
            df_onehot=onehot,
            min_support=0.10,
            min_confidence=0.40,
            metric="lift",
            min_metric_val=1.0,
            max_len=4,
            algorithm="fpgrowth",
        )
        expected = {
            (frozenset(row["antecedents"]), frozenset(row["consequents"]))
            for _, row in engine_rules.iterrows()
        }

        assert masked == expected

    def test_metrics_are_consistent_with_selected_rules(self, evaluator):
        """Reported averages must describe the rule set actually selected."""
        evaluator_instance, _ = evaluator
        state = OptimizationState(min_support=0.10, min_confidence=0.40, min_lift=1.0, max_len=4)

        metrics = evaluator_instance.evaluate(state)
        selected = evaluator_instance.select_rules(state)

        assert metrics["rule_count"] == len(selected)
        if metrics["rule_count"] > 0:
            assert metrics["avg_confidence"] == pytest.approx(
                selected["confidence"].mean(), abs=1e-6
            )
            assert 0.0 <= metrics["coverage"] <= 1.0


class TestEvaluatorPruningAndBoundaries:
    """Tier 2: Redundancy pruning intensity and empty-selection behaviour."""

    def test_pruning_factor_is_monotonic(self, evaluator):
        """Raising the pruning factor can only remove rules, never add them."""
        evaluator_instance, _ = evaluator

        counts = []
        for pruning_factor in (0.0, 0.25, 0.5, 0.75, 1.0):
            state = OptimizationState(
                min_support=0.10, min_confidence=0.30, min_lift=1.0,
                max_len=4, pruning_factor=pruning_factor,
            )
            counts.append(evaluator_instance.evaluate(state)["rule_count"])

        for earlier, later in zip(counts, counts[1:]):
            assert later <= earlier, f"Pruning factor increased rule count: {counts}"

    def test_impossible_thresholds_yield_empty_selection(self, evaluator):
        """Thresholds no rule can satisfy return zero rules and zero coverage."""
        evaluator_instance, _ = evaluator
        state = OptimizationState(
            min_support=0.15, min_confidence=0.95, min_lift=10.0, max_len=2
        )

        metrics = evaluator_instance.evaluate(state)
        assert metrics["rule_count"] == 0
        assert metrics["coverage"] == 0.0
        assert evaluator_instance.select_rules(state).empty

    def test_coverage_never_exceeds_unity(self, evaluator):
        """Coverage is a fraction of baskets and must stay within [0, 1]."""
        evaluator_instance, _ = evaluator

        for min_support in (0.05, 0.10, 0.20, 0.30):
            state = OptimizationState(
                min_support=min_support, min_confidence=0.20, min_lift=1.0, max_len=5
            )
            coverage = evaluator_instance.evaluate(state)["coverage"]
            assert 0.0 <= coverage <= 1.0
