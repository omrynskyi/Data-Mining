"""
Unit tests for 9 Association Rule Interest Metrics.
Validates mathematical definitions, edge cases, and numerical bounds.
"""

import math
import pytest

from config import CONVICTION_MAX_CAP
from src.mining.metrics import (
    compute_all_metrics,
    compute_confidence,
    compute_cosine,
    compute_imbalance_ratio,
    compute_kulczynski,
    compute_leverage,
    compute_lift,
    compute_support,
    compute_zhangs_metric,
)


def test_support_computation():
    assert compute_support(0.25) == 0.25
    assert compute_support(0.0) == 0.0


def test_confidence_computation():
    # supp(A) = 0.5, supp(AC) = 0.25 -> conf = 0.5
    assert compute_confidence(0.25, 0.5) == 0.5
    # supp(A) = 0 -> conf = 0.0 (safely handled)
    assert compute_confidence(0.25, 0.0) == 0.0
    # perfect implication supp(A) = 0.3, supp(AC) = 0.3 -> conf = 1.0
    assert compute_confidence(0.3, 0.3) == 1.0


def test_lift_computation():
    # supp(A) = 0.5, supp(C) = 0.5, supp(AC) = 0.25 -> independent, lift = 1.0
    assert math.isclose(compute_lift(0.25, 0.5, 0.5), 1.0)
    # positive association
    assert math.isclose(compute_lift(0.4, 0.5, 0.5), 1.6)
    # negative association
    assert math.isclose(compute_lift(0.1, 0.5, 0.5), 0.4)
    # zero denom
    assert compute_lift(0.1, 0.0, 0.5) == 0.0


def test_leverage_computation():
    # supp(AC) = 0.3, supp(A) = 0.5, supp(C) = 0.4 -> expected = 0.20 -> lev = 0.10
    assert math.isclose(compute_leverage(0.3, 0.5, 0.4), 0.10)
    # independence -> lev = 0.0
    assert math.isclose(compute_leverage(0.2, 0.5, 0.4), 0.0)


def test_conviction_and_capping():
    # conf = 0.5, supp(C) = 0.4 -> (1 - 0.4) / (1 - 0.5) = 0.6 / 0.5 = 1.2
    assert math.isclose(compute_all_metrics(0.25, 0.5, 0.4)["conviction"], 1.2)
    # 100% confidence -> conviction is capped at CONVICTION_MAX_CAP
    metrics = compute_all_metrics(0.5, 0.5, 0.4)
    assert metrics["confidence"] == 1.0
    assert metrics["conviction"] == CONVICTION_MAX_CAP


def test_zhangs_metric():
    # Positive association: supp(A) = 0.5, supp(C) = 0.5, supp(AC) = 0.4
    # numerator = 0.4 - 0.25 = 0.15
    # term1 = 0.4 * 0.5 = 0.20; term2 = 0.5 * (0.5 - 0.4) = 0.05 -> max = 0.20
    # Z = 0.15 / 0.20 = 0.75
    z_val = compute_zhangs_metric(0.4, 0.5, 0.5)
    assert math.isclose(z_val, 0.75)

    # Negative association: supp(A) = 0.5, supp(C) = 0.5, supp(AC) = 0.1
    # numerator = 0.1 - 0.25 = -0.15
    # term1 = 0.1 * 0.5 = 0.05; term2 = 0.5 * 0.4 = 0.20 -> max = 0.20
    # Z = -0.15 / 0.20 = -0.75
    z_neg = compute_zhangs_metric(0.1, 0.5, 0.5)
    assert math.isclose(z_neg, -0.75)


def test_kulczynski_metric():
    # supp(A) = 0.4, supp(C) = 0.5, supp(AC) = 0.2
    # conf(A->C) = 0.2/0.4 = 0.5; conf(C->A) = 0.2/0.5 = 0.4
    # Kulc = 0.5 * (0.5 + 0.4) = 0.45
    kulc = compute_kulczynski(0.2, 0.4, 0.5)
    assert math.isclose(kulc, 0.45)


def test_imbalance_ratio():
    # supp(A) = 0.6, supp(C) = 0.2, supp(AC) = 0.15
    # |0.6 - 0.2| / (0.6 + 0.2 - 0.15) = 0.4 / 0.65 = 0.615385
    ir = compute_imbalance_ratio(0.15, 0.6, 0.2)
    assert math.isclose(ir, 0.4 / 0.65, rel_tol=1e-4)

    # Symmetric support -> IR = 0.0
    ir_sym = compute_imbalance_ratio(0.2, 0.4, 0.4)
    assert ir_sym == 0.0


def test_cosine_metric():
    # supp(A) = 0.5, supp(C) = 0.5, supp(AC) = 0.25
    # Cosine = 0.25 / sqrt(0.25) = 0.5
    cos = compute_cosine(0.25, 0.5, 0.5)
    assert math.isclose(cos, 0.5)
