"""
5-Dimensional Hyperparameter State Space for Hill Climbing (Feature F9).

A search state is one complete association-mining configuration:

    (min_support, min_confidence, min_lift, max_len, pruning_factor)

The first four are the thresholds handed to the mining engine. `pruning_factor`
controls redundancy pruning intensity: it is the minimum *relative* confidence
improvement a specialised rule must show over its most confident generalisation
in order to be retained. At 0.0 only rules that fail to improve at all are
pruned (classic redundancy pruning); at 1.0 a specialisation must double the
confidence of its generalisation to survive.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, Tuple

MAX_LEN_CHOICES: Tuple[int, ...] = (2, 3, 4, 5)


@dataclass(frozen=True)
class StateBounds:
    """Inclusive domain boundaries for every search dimension."""

    min_support_range: Tuple[float, float] = (0.002, 0.150)
    min_confidence_range: Tuple[float, float] = (0.100, 0.950)
    min_lift_range: Tuple[float, float] = (1.000, 10.000)
    max_len_choices: Tuple[int, ...] = MAX_LEN_CHOICES
    pruning_factor_range: Tuple[float, float] = (0.000, 1.000)

    def span(self, dimension: str) -> float:
        """Return the width of a continuous dimension, used to scale mutations."""
        spans = {
            "min_support": self.min_support_range[1] - self.min_support_range[0],
            "min_confidence": self.min_confidence_range[1] - self.min_confidence_range[0],
            "min_lift": self.min_lift_range[1] - self.min_lift_range[0],
            "pruning_factor": self.pruning_factor_range[1] - self.pruning_factor_range[0],
        }
        if dimension not in spans:
            raise KeyError(f"'{dimension}' is not a continuous search dimension.")
        return spans[dimension]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "min_support": list(self.min_support_range),
            "min_confidence": list(self.min_confidence_range),
            "min_lift": list(self.min_lift_range),
            "max_len": list(self.max_len_choices),
            "pruning_factor": list(self.pruning_factor_range),
        }


DEFAULT_BOUNDS = StateBounds()


def _clamp(value: float, low: float, high: float) -> float:
    """Clamp a scalar into [low, high]."""
    return float(min(max(float(value), low), high))


@dataclass
class OptimizationState:
    """
    One candidate point in the 5D mining hyperparameter space.

    Values are stored exactly as supplied so that an out-of-domain proposal can
    be inspected before being repaired; call :meth:`clip` to project the state
    back into the feasible region.
    """

    min_support: float = 0.020
    min_confidence: float = 0.500
    min_lift: float = 1.200
    max_len: int = 3
    pruning_factor: float = 0.500
    bounds: StateBounds = field(default=DEFAULT_BOUNDS, repr=False, compare=False)

    def clip(self) -> "OptimizationState":
        """Return a new state projected into the feasible domain."""
        b = self.bounds

        try:
            raw_max_len = int(round(float(self.max_len)))
        except (TypeError, ValueError):
            raw_max_len = MAX_LEN_CHOICES[0]

        choices = tuple(b.max_len_choices)
        clipped_max_len = min(choices, key=lambda c: (abs(c - raw_max_len), c))

        return OptimizationState(
            min_support=_clamp(self.min_support, *b.min_support_range),
            min_confidence=_clamp(self.min_confidence, *b.min_confidence_range),
            min_lift=_clamp(self.min_lift, *b.min_lift_range),
            max_len=int(clipped_max_len),
            pruning_factor=_clamp(self.pruning_factor, *b.pruning_factor_range),
            bounds=b,
        )

    def is_within_bounds(self) -> bool:
        """True when every dimension already lies inside the feasible domain."""
        b = self.bounds
        return (
            b.min_support_range[0] <= self.min_support <= b.min_support_range[1]
            and b.min_confidence_range[0] <= self.min_confidence <= b.min_confidence_range[1]
            and b.min_lift_range[0] <= self.min_lift <= b.min_lift_range[1]
            and int(self.max_len) in tuple(b.max_len_choices)
            and b.pruning_factor_range[0] <= self.pruning_factor <= b.pruning_factor_range[1]
        )

    def copy(self) -> "OptimizationState":
        """Return an independent duplicate of this state."""
        return OptimizationState(
            min_support=self.min_support,
            min_confidence=self.min_confidence,
            min_lift=self.min_lift,
            max_len=int(self.max_len),
            pruning_factor=self.pruning_factor,
            bounds=self.bounds,
        )

    def to_dict(self) -> Dict[str, Any]:
        """Serialise the state for JSON/CSV audit logs."""
        return {
            "min_support": round(float(self.min_support), 6),
            "min_confidence": round(float(self.min_confidence), 6),
            "min_lift": round(float(self.min_lift), 6),
            "max_len": int(self.max_len),
            "pruning_factor": round(float(self.pruning_factor), 6),
        }

    def signature(self) -> Tuple[float, float, float, int, float]:
        """Rounded tuple used to memoise repeated evaluations of the same point."""
        return (
            round(float(self.min_support), 6),
            round(float(self.min_confidence), 6),
            round(float(self.min_lift), 6),
            int(self.max_len),
            round(float(self.pruning_factor), 6),
        )

    @classmethod
    def from_dict(cls, data: Dict[str, Any], bounds: StateBounds = DEFAULT_BOUNDS) -> "OptimizationState":
        """Rebuild a state from its serialised form."""
        return cls(
            min_support=float(data.get("min_support", 0.020)),
            min_confidence=float(data.get("min_confidence", 0.500)),
            min_lift=float(data.get("min_lift", 1.200)),
            max_len=int(data.get("max_len", 3)),
            pruning_factor=float(data.get("pruning_factor", 0.500)),
            bounds=bounds,
        )
