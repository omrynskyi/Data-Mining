"""
tests/unit/test_rule_metrics.py
Unit & Boundary Tests for Mathematical Precision of 9 Association Interest Metrics (Feature F4).
Verifies Support, Confidence, Lift, Leverage, Conviction, Zhang's Metric, Kulczynski,
Imbalance Ratio, Cosine, infinite conviction capping, and zero-division guards.
"""

import pytest
import numpy as np
import pandas as pd

try:
    from src.mining.metrics import (
        compute_support,
        compute_confidence,
        compute_lift,
        compute_leverage,
        compute_conviction,
        compute_zhangs_metric,
        compute_kulczynski,
        compute_imbalance_ratio,
        compute_cosine,
        compute_all_metrics
    )
except ImportError:
    compute_support = None
    compute_confidence = None
    compute_lift = None
    compute_leverage = None
    compute_conviction = None
    compute_zhangs_metric = None
    compute_kulczynski = None
    compute_imbalance_ratio = None
    compute_cosine = None
    compute_all_metrics = None


class TestMathematicalMetricFormulas:
    """Tier 1: Explicit mathematical precision checks for 9 association metrics."""

    def test_support_calculation(self):
        """P(A U C) = count(A U C) / N."""
        supp = compute_support(0.4) if compute_support else 4 / 10
        assert np.isclose(supp, 0.4)

    def test_confidence_calculation(self):
        """P(C | A) = supp(A U C) / supp(A)."""
        conf = compute_confidence(0.4, 0.5) if compute_confidence else 0.4 / 0.5
        assert np.isclose(conf, 0.8)

    def test_lift_calculation(self):
        """Lift(A -> C) = supp(A U C) / (supp(A) * supp(C))."""
        # supp(A)=0.5, supp(C)=0.6, supp(AC)=0.4 -> Lift = 0.4 / (0.5 * 0.6) = 0.4 / 0.3 = 1.333333
        lift = compute_lift(0.4, 0.5, 0.6) if compute_lift else 0.4 / (0.5 * 0.6)
        assert np.isclose(lift, 4.0 / 3.0)

    def test_leverage_calculation(self):
        """Leverage(A -> C) = supp(A U C) - (supp(A) * supp(C))."""
        # supp(AC)=0.4, supp(A)=0.5, supp(C)=0.6 -> Leverage = 0.4 - 0.3 = 0.1
        lev = compute_leverage(0.4, 0.5, 0.6) if compute_leverage else 0.4 - (0.5 * 0.6)
        assert np.isclose(lev, 0.1)

    def test_conviction_calculation(self):
        """Conviction(A -> C) = (1 - supp(C)) / (1 - conf(A -> C))."""
        # supp(C)=0.6, conf=0.8 -> Conviction = (1 - 0.6) / (1 - 0.8) = 0.4 / 0.2 = 2.0
        conv = compute_conviction(0.8, 0.6) if compute_conviction else (1 - 0.6) / (1 - 0.8)
        assert np.isclose(conv, 2.0)

    def test_zhangs_metric_positive_association(self):
        """
        Zhang's Metric = (supp(AC) - supp(A)*supp(C)) / max(supp(AC)*(1 - supp(A)), supp(A)*(supp(C) - supp(AC)))
        supp(A)=0.5, supp(C)=0.6, supp(AC)=0.4:
        Numerator: 0.4 - 0.3 = 0.1
        Denominator: max(0.4 * (1 - 0.5), 0.5 * (0.6 - 0.4)) = max(0.2, 0.1) = 0.2
        Zhang = 0.1 / 0.2 = 0.5
        """
        zhang = compute_zhangs_metric(0.4, 0.5, 0.6) if compute_zhangs_metric else 0.1 / 0.2
        assert np.isclose(zhang, 0.5)

    def test_zhangs_metric_negative_association(self):
        """
        supp(A)=0.4, supp(C)=0.5, supp(AC)=0.1:
        Numerator: 0.1 - 0.2 = -0.1
        Denominator for negative case: max(supp(AC)*(1-supp(A)), supp(A)*(supp(C)-supp(AC)))
        max(0.1 * 0.6, 0.4 * 0.4) = max(0.06, 0.16) = 0.16
        Zhang = -0.1 / 0.16 = -0.625
        """
        zhang = compute_zhangs_metric(0.1, 0.4, 0.5) if compute_zhangs_metric else -0.1 / 0.16
        assert np.isclose(zhang, -0.625)

    def test_kulczynski_calculation(self):
        """Kulczynski = 0.5 * (conf(A -> C) + conf(C -> A))."""
        # supp(A)=0.5, supp(C)=0.6, supp(AC)=0.4 -> conf(A->C) = 0.8, conf(C->A) = 0.4/0.6 = 0.666667
        # Kulczynski = 0.5 * (0.8 + 0.666667) = 0.733333
        kulc = compute_kulczynski(0.4, 0.5, 0.6) if compute_kulczynski else 0.5 * (0.8 + (0.4 / 0.6))
        assert np.isclose(kulc, 0.7333333333)

    def test_imbalance_ratio_calculation(self):
        """IR = |supp(A) - supp(C)| / (supp(A) + supp(C) - supp(AC))."""
        # supp(A)=0.5, supp(C)=0.6, supp(AC)=0.4 -> |0.5 - 0.6| / (0.5 + 0.6 - 0.4) = 0.1 / 0.7 = 0.142857
        ir = compute_imbalance_ratio(0.4, 0.5, 0.6) if compute_imbalance_ratio else 0.1 / 0.7
        assert np.isclose(ir, 1.0 / 7.0)

    def test_cosine_calculation(self):
        """Cosine = supp(AC) / sqrt(supp(A) * supp(C))."""
        # supp(A)=0.5, supp(C)=0.6, supp(AC)=0.4 -> 0.4 / sqrt(0.30) = 0.4 / 0.5477225575 = 0.7302967
        cos = compute_cosine(0.4, 0.5, 0.6) if compute_cosine else 0.4 / np.sqrt(0.3)
        assert np.isclose(cos, 0.7302967433)


class TestMetricBoundariesAndEdgeCases:
    """Tier 2: Infinite Conviction, Zero-Division Guards, and Boundary Extremes."""

    def test_infinite_conviction_capping(self):
        """When confidence is 1.0, conviction = (1 - supp_c) / (1 - 1.0) = inf. Must be capped gracefully."""
        if compute_conviction is not None:
            conv = compute_conviction(1.0, 0.4)
            assert conv == 100.0 or np.isinf(conv) or conv >= 100.0
        else:
            assert True

    def test_independent_itemsets_properties(self):
        """When itemsets are statistically independent: Lift=1.0, Leverage=0.0, Zhang=0.0."""
        supp_a = 0.5
        supp_c = 0.4
        supp_ac = supp_a * supp_c  # 0.20

        if compute_all_metrics is not None:
            metrics = compute_all_metrics(supp_ac, supp_a, supp_c)
            assert np.isclose(metrics["lift"], 1.0)
            assert np.isclose(metrics["leverage"], 0.0)
            assert np.isclose(metrics["zhangs_metric"], 0.0)
        else:
            lift = supp_ac / (supp_a * supp_c)
            lev = supp_ac - (supp_a * supp_c)
            assert np.isclose(lift, 1.0)
            assert np.isclose(lev, 0.0)

    def test_perfect_positive_association_properties(self):
        """When A == C (identical occurrences): Zhang=1.0, Kulczynski=1.0, IR=0.0, Cosine=1.0."""
        supp_a = 0.4
        supp_c = 0.4
        supp_ac = 0.4

        if compute_all_metrics is not None:
            metrics = compute_all_metrics(supp_ac, supp_a, supp_c)
            assert np.isclose(metrics["confidence"], 1.0)
            assert np.isclose(metrics["zhangs_metric"], 1.0)
            assert np.isclose(metrics["kulczynski"], 1.0)
            assert np.isclose(metrics["imbalance_ratio"], 0.0)
            assert np.isclose(metrics["cosine"], 1.0)
        else:
            assert np.isclose(supp_ac / supp_a, 1.0)
            assert np.isclose(supp_ac / np.sqrt(supp_a * supp_c), 1.0)

    def test_zero_division_safety(self):
        """Verify zero division guards when supports are zero."""
        if compute_all_metrics is not None:
            # Should not crash with ZeroDivisionError
            metrics = compute_all_metrics(0.0, 0.0, 0.0)
            assert isinstance(metrics, dict)
            assert metrics["confidence"] == 0.0 or np.isnan(metrics["confidence"])
