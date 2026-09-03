"""
Multi-Mode Fitness Evaluator (Feature F8).

Three fitness formulations score a candidate rule set:

1. **Paper matching** -- a weighted normalised squared relative error against the
   target paper's reported operating point, mapped into a bounded 0-100 score.
2. **Composite quality** -- an intrinsic, paper-agnostic measure of how good the
   discovered rule set is (confidence, lift, coverage, parsimony).
3. **Hybrid** -- a convex blend of the two, so the search reproduces the paper
   without collapsing onto degenerate rule sets that happen to hit the numbers.

Every fitness value is bounded in [0.0, 100.0]; loss is non-negative.
"""

from typing import Any, Dict, Optional, Tuple

import numpy as np

#: Metric dimensions compared against the target paper.
TARGET_DIMENSIONS = (
    "rule_count",
    "avg_support",
    "avg_confidence",
    "avg_lift",
    "coverage",
)

#: Relative importance of each dimension in the matching loss. Sums to 1.0.
DEFAULT_MATCH_WEIGHTS: Dict[str, float] = {
    "rule_count": 0.30,
    "avg_support": 0.15,
    "avg_confidence": 0.20,
    "avg_lift": 0.20,
    "coverage": 0.15,
}

#: Loss assigned when a candidate discovers no rules at all. The search must be
#: told unambiguously that an empty rule set is the worst possible outcome, not
#: merely a large relative error.
ZERO_RULE_LOSS = 1000.0

#: Lift value at which the composite quality term saturates.
COMPOSITE_LIFT_SATURATION = 4.0

#: Rule-set size that maximises the composite parsimony term.
COMPOSITE_IDEAL_RULE_COUNT = 60.0

#: Default blend weight for hybrid fitness (share given to paper matching).
DEFAULT_HYBRID_BETA = 0.70


def _as_target_metrics(target: Dict[str, Any]) -> Dict[str, float]:
    """
    Accept either a full paper profile or a bare target-metrics dictionary and
    return the metric dictionary in both cases.
    """
    if target is None:
        raise ValueError("A target paper profile or target metric dictionary is required.")
    if "target_metrics" in target and isinstance(target["target_metrics"], dict):
        return target["target_metrics"]
    return target


def _has_no_rules(achieved: Dict[str, Any]) -> bool:
    """True when the candidate configuration discovered zero rules."""
    return float(achieved.get("rule_count", 0) or 0) <= 0


def compute_matching_loss(
    achieved: Dict[str, Any],
    target: Dict[str, Any],
    weights: Optional[Dict[str, float]] = None,
) -> float:
    """
    Weighted normalised squared relative error against the target operating point.

        L = sum_i w_i * ((x_i - t_i) / t_i)^2

    Normalising by the target makes the five dimensions commensurable despite
    living on wildly different scales (a rule count of 50 vs a support of 0.025).

    Returns 0.0 for an exact match and :data:`ZERO_RULE_LOSS` for an empty rule set.
    """
    targets = _as_target_metrics(target)
    w = dict(DEFAULT_MATCH_WEIGHTS)
    if weights:
        w.update(weights)

    if _has_no_rules(achieved):
        return ZERO_RULE_LOSS

    total_weight = 0.0
    loss = 0.0

    for dimension in TARGET_DIMENSIONS:
        if dimension not in targets:
            continue

        target_value = float(targets[dimension])
        achieved_value = float(achieved.get(dimension, 0.0) or 0.0)
        weight = float(w.get(dimension, 0.0))

        # A zero target carries no relative scale; fall back to absolute error.
        denominator = abs(target_value) if abs(target_value) > 1e-12 else 1.0
        relative_error = (achieved_value - target_value) / denominator

        loss += weight * (relative_error ** 2)
        total_weight += weight

    if total_weight <= 0.0:
        return 0.0

    # Renormalise so a partially-specified target still yields a comparable loss.
    return float(loss / total_weight)


def compute_matching_fitness(
    achieved: Dict[str, Any],
    target: Dict[str, Any],
    weights: Optional[Dict[str, float]] = None,
) -> float:
    """
    Map the matching loss onto a bounded 0-100 score.

        F = 100 / (1 + L)

    A perfect match (L = 0) scores 100.0; the score decays smoothly and never
    reaches 0 for a non-empty rule set, so the search always has a gradient.
    An empty rule set is hard-clamped to 0.0.
    """
    if _has_no_rules(achieved):
        return 0.0

    loss = compute_matching_loss(achieved, target, weights=weights)
    fitness = 100.0 / (1.0 + max(0.0, loss))
    return float(np.clip(fitness, 0.0, 100.0))


def compute_composite_fitness(achieved: Dict[str, Any]) -> float:
    """
    Paper-agnostic quality of a rule set, bounded in [0, 100].

    Blends four normalised terms:

    * **confidence** (35%) -- mean predictive accuracy of the rules.
    * **lift** (30%) -- mean association strength, saturating at lift 4.0 so a
      handful of freak high-lift rules cannot dominate.
    * **coverage** (20%) -- share of transactions the rule set actually explains.
    * **parsimony** (15%) -- peaks at a human-reviewable rule count and decays
      logarithmically in either direction, penalising both empty and bloated sets.
    """
    if _has_no_rules(achieved):
        return 0.0

    avg_confidence = float(np.clip(float(achieved.get("avg_confidence", 0.0) or 0.0), 0.0, 1.0))

    avg_lift = max(0.0, float(achieved.get("avg_lift", 0.0) or 0.0))
    # Lift of 1.0 means independence -> no quality; saturate at the ceiling.
    lift_term = float(np.clip(
        (avg_lift - 1.0) / (COMPOSITE_LIFT_SATURATION - 1.0), 0.0, 1.0
    ))

    coverage = float(np.clip(float(achieved.get("coverage", 0.0) or 0.0), 0.0, 1.0))

    rule_count = max(1.0, float(achieved.get("rule_count", 0) or 0))
    # Symmetric in log-space around the ideal count: 10x too many rules is
    # penalised exactly as hard as 10x too few.
    log_ratio = np.log10(rule_count / COMPOSITE_IDEAL_RULE_COUNT)
    parsimony_term = float(np.clip(1.0 - abs(log_ratio) / 2.0, 0.0, 1.0))

    composite = (
        0.35 * avg_confidence
        + 0.30 * lift_term
        + 0.20 * coverage
        + 0.15 * parsimony_term
    )
    return float(np.clip(composite * 100.0, 0.0, 100.0))


def compute_hybrid_fitness(
    match_fitness: float,
    composite_fitness: float,
    beta: float = DEFAULT_HYBRID_BETA,
) -> float:
    """
    Convex blend of paper-matching and intrinsic quality fitness.

        F = beta * F_match + (1 - beta) * F_composite

    `beta` is the share of the score attributed to reproducing the paper.
    """
    b = float(np.clip(float(beta), 0.0, 1.0))
    blended = b * float(match_fitness) + (1.0 - b) * float(composite_fitness)
    return float(np.clip(blended, 0.0, 100.0))


class FitnessEvaluator:
    """
    Stateful evaluator binding a target paper to a scoring mode.

    Modes
    -----
    ``paper_match``
        Score purely on distance to the paper's reported operating point.
    ``composite``
        Score purely on intrinsic rule-set quality.
    ``hybrid`` (default)
        Blend both, weighted by `beta`.
    """

    VALID_MODES = ("paper_match", "composite", "hybrid")

    def __init__(
        self,
        target_paper: Optional[Dict[str, Any]] = None,
        mode: str = "hybrid",
        beta: float = DEFAULT_HYBRID_BETA,
        weights: Optional[Dict[str, float]] = None,
    ):
        normalized_mode = str(mode).lower().strip()
        if normalized_mode not in self.VALID_MODES:
            raise ValueError(
                f"Unknown fitness mode '{mode}'. Expected one of {self.VALID_MODES}."
            )

        self.mode = normalized_mode
        self.beta = float(np.clip(float(beta), 0.0, 1.0))
        self.weights = dict(DEFAULT_MATCH_WEIGHTS)
        if weights:
            self.weights.update(weights)

        self.paper_profile = target_paper
        self.target_metrics: Optional[Dict[str, float]] = (
            _as_target_metrics(target_paper) if target_paper is not None else None
        )

        if self.mode != "composite" and self.target_metrics is None:
            raise ValueError(
                f"Fitness mode '{self.mode}' requires a target paper profile."
            )

        self.evaluation_count = 0

    def evaluate_metrics(self, achieved: Dict[str, Any]) -> Tuple[float, float]:
        """
        Score one candidate's achieved metrics.

        Returns
        -------
        (loss, fitness) : Tuple[float, float]
            `loss` is the paper-matching loss (:data:`ZERO_RULE_LOSS` for an empty
            rule set); `fitness` is bounded in [0.0, 100.0].
        """
        self.evaluation_count += 1

        # Zero-rule cliff: an empty rule set is unusable regardless of mode.
        if _has_no_rules(achieved):
            return ZERO_RULE_LOSS, 0.0

        if self.target_metrics is not None:
            loss = compute_matching_loss(achieved, self.target_metrics, weights=self.weights)
            match_fitness = compute_matching_fitness(
                achieved, self.target_metrics, weights=self.weights
            )
        else:
            loss = 0.0
            match_fitness = 0.0

        composite_fitness = compute_composite_fitness(achieved)

        if self.mode == "paper_match":
            fitness = match_fitness
        elif self.mode == "composite":
            fitness = composite_fitness
        else:
            fitness = compute_hybrid_fitness(match_fitness, composite_fitness, beta=self.beta)

        return float(loss), float(np.clip(fitness, 0.0, 100.0))

    def breakdown(self, achieved: Dict[str, Any]) -> Dict[str, float]:
        """Per-mode scores for one candidate, for dashboard display and audit logs."""
        if _has_no_rules(achieved):
            return {
                "loss": ZERO_RULE_LOSS,
                "match_fitness": 0.0,
                "composite_fitness": 0.0,
                "hybrid_fitness": 0.0,
            }

        match_fitness = (
            compute_matching_fitness(achieved, self.target_metrics, weights=self.weights)
            if self.target_metrics is not None
            else 0.0
        )
        composite_fitness = compute_composite_fitness(achieved)
        return {
            "loss": (
                compute_matching_loss(achieved, self.target_metrics, weights=self.weights)
                if self.target_metrics is not None
                else 0.0
            ),
            "match_fitness": round(match_fitness, 4),
            "composite_fitness": round(composite_fitness, 4),
            "hybrid_fitness": round(
                compute_hybrid_fitness(match_fitness, composite_fitness, beta=self.beta), 4
            ),
        }

    def compare_to_target(self, achieved: Dict[str, Any]) -> Dict[str, Dict[str, float]]:
        """
        Per-dimension target-versus-achieved comparison with percentage errors,
        matching the `target_vs_achieved` section of `optimization_log.json`.
        """
        if self.target_metrics is None:
            return {}

        comparison: Dict[str, Dict[str, float]] = {}
        for dimension in TARGET_DIMENSIONS:
            if dimension not in self.target_metrics:
                continue

            target_value = float(self.target_metrics[dimension])
            achieved_value = float(achieved.get(dimension, 0.0) or 0.0)
            denominator = abs(target_value) if abs(target_value) > 1e-12 else 1.0
            error_pct = abs(achieved_value - target_value) / denominator * 100.0

            comparison[dimension] = {
                "target": round(target_value, 6),
                "achieved": round(achieved_value, 6),
                "error_pct": round(error_pct, 4),
            }

        return comparison
