"""
Mathematical Interest Metrics for Association Rules.
Implements 9 standard and advanced association metrics with numerical safety guards.
"""

import math
from typing import Dict, Optional, Union
import numpy as np
import pandas as pd

from config import CONVICTION_MAX_CAP


def compute_support(joint_support: float) -> float:
    """Joint support P(A ∪ C)."""
    return float(joint_support)


def compute_confidence(joint_support: float, antecedent_support: float) -> float:
    """Confidence P(C | A) = P(A ∪ C) / P(A)."""
    if antecedent_support <= 0:
        return 0.0
    return min(1.0, float(joint_support / antecedent_support))


def compute_lift(joint_support: float, antecedent_support: float, consequent_support: float) -> float:
    """Lift P(A ∪ C) / (P(A) * P(C))."""
    denom = antecedent_support * consequent_support
    if denom <= 0:
        return 0.0
    return float(joint_support / denom)


def compute_leverage(joint_support: float, antecedent_support: float, consequent_support: float) -> float:
    """Leverage P(A ∪ C) - (P(A) * P(C))."""
    return float(joint_support - (antecedent_support * consequent_support))


def compute_conviction(
    confidence: float,
    consequent_support: float,
    max_cap: float = CONVICTION_MAX_CAP,
) -> float:
    """
    Conviction (1 - P(C)) / (1 - P(C | A)).
    Capped at max_cap when confidence is 1.0 to ensure numerical stability and JSON serializability.
    """
    if confidence >= 1.0:
        return float(max_cap)
    denom = 1.0 - confidence
    if denom <= 0:
        return float(max_cap)
    val = (1.0 - consequent_support) / denom
    return min(float(val), float(max_cap))


def compute_zhangs_metric(joint_support: float, antecedent_support: float, consequent_support: float) -> float:
    """
    Zhang's Metric: bounded association measure in [-1, 1].
    Z(A -> C) = (P(AC) - P(A)P(C)) / max( P(AC)(1 - P(A)), P(A)(P(C) - P(AC)) )
    """
    numerator = joint_support - (antecedent_support * consequent_support)
    term1 = joint_support * (1.0 - antecedent_support)
    term2 = antecedent_support * (consequent_support - joint_support)
    denominator = max(term1, term2)

    if denominator <= 0 or math.isclose(denominator, 0.0, abs_tol=1e-12):
        return 0.0

    zhang_val = numerator / denominator
    return max(-1.0, min(1.0, float(zhang_val)))


def compute_kulczynski(joint_support: float, antecedent_support: float, consequent_support: float) -> float:
    """
    Kulczynski Metric: average of conditional probabilities 0.5 * (conf(A->C) + conf(C->A)).
    Null-invariant metric bounded in [0, 1].
    """
    if antecedent_support <= 0 or consequent_support <= 0:
        return 0.0
    conf_a_c = joint_support / antecedent_support
    conf_c_a = joint_support / consequent_support
    return max(0.0, min(1.0, float(0.5 * (conf_a_c + conf_c_a))))


def compute_imbalance_ratio(joint_support: float, antecedent_support: float, consequent_support: float) -> float:
    """
    Imbalance Ratio: |P(A) - P(C)| / (P(A) + P(C) - P(AC)).
    Measures support asymmetry, bounded in [0, 1].
    """
    denom = antecedent_support + consequent_support - joint_support
    if denom <= 0:
        return 0.0
    val = abs(antecedent_support - consequent_support) / denom
    return max(0.0, min(1.0, float(val)))


def compute_cosine(joint_support: float, antecedent_support: float, consequent_support: float) -> float:
    """
    Cosine: P(AC) / sqrt(P(A) * P(C)).
    Geometric mean of directional confidences, bounded in [0, 1].
    """
    denom = math.sqrt(antecedent_support * consequent_support)
    if denom <= 0:
        return 0.0
    return max(0.0, min(1.0, float(joint_support / denom)))


def compute_all_metrics(
    joint_support: float,
    antecedent_support: float,
    consequent_support: float,
) -> Dict[str, float]:
    """Compute all 9 interest metrics for a given rule (A -> C)."""
    conf = compute_confidence(joint_support, antecedent_support)
    lift = compute_lift(joint_support, antecedent_support, consequent_support)
    lev = compute_leverage(joint_support, antecedent_support, consequent_support)
    conv = compute_conviction(conf, consequent_support)
    zhang = compute_zhangs_metric(joint_support, antecedent_support, consequent_support)
    kulc = compute_kulczynski(joint_support, antecedent_support, consequent_support)
    ir = compute_imbalance_ratio(joint_support, antecedent_support, consequent_support)
    cos = compute_cosine(joint_support, antecedent_support, consequent_support)

    return {
        "support": round(joint_support, 6),
        "confidence": round(conf, 6),
        "lift": round(lift, 6),
        "leverage": round(lev, 6),
        "conviction": round(conv, 6),
        "zhangs_metric": round(zhang, 6),
        "kulczynski": round(kulc, 6),
        "imbalance_ratio": round(ir, 6),
        "cosine": round(cos, 6),
    }
