"""
Neighbourhood Perturbation & Adaptive Step Sizing Operators (Features F9, F10).

The hill climber explores by Gaussian mutation of the continuous dimensions plus
a bounded random walk on the discrete `max_len` dimension. Step size adapts via
Rechenberg's 1/5th success rule, and stalled searches are relaunched from Latin
Hypercube or uniform random restart points.
"""

from typing import List, Optional

import numpy as np

from src.optimization.state import DEFAULT_BOUNDS, OptimizationState, StateBounds

#: Rechenberg's target success rate. Above it the search is too timid (expand
#: the step); below it the search is over-reaching (shrink the step).
RECHENBERG_TARGET_RATE = 0.20

#: Multiplicative expansion / contraction factors applied per adaptation.
STEP_EXPANSION_FACTOR = 1.15
STEP_CONTRACTION_FACTOR = 0.85

#: Hard limits on the step size, as a fraction of each dimension's span.
MIN_STEP_SIZE = 0.005
MAX_STEP_SIZE = 0.500

#: Probability of stepping `max_len` by +-1 is this multiple of the step size.
MAX_LEN_MUTATION_SCALE = 3.0


def _resolve_rng(rng: Optional[np.random.Generator]) -> np.random.Generator:
    """Return the supplied generator, or a fresh default one."""
    return rng if rng is not None else np.random.default_rng()


def mutate_state(
    state: Optional[OptimizationState],
    step_size: float = 0.05,
    rng: Optional[np.random.Generator] = None,
    bounds: Optional[StateBounds] = None,
) -> OptimizationState:
    """
    Produce one Gaussian-perturbed neighbour of `state`.

    Each continuous dimension is displaced by a normal deviate whose standard
    deviation is `step_size` times that dimension's span, so a single step size
    means the same *relative* move on every axis. `max_len` takes a bounded
    +-1 random walk. The result is always projected back into the feasible domain.
    """
    generator = _resolve_rng(rng)
    domain = bounds or (state.bounds if state is not None else DEFAULT_BOUNDS)
    base = state.copy() if state is not None else OptimizationState(bounds=domain)

    sigma = float(np.clip(step_size, MIN_STEP_SIZE, MAX_STEP_SIZE))

    proposal = OptimizationState(
        min_support=base.min_support + generator.normal(0.0, sigma * domain.span("min_support")),
        min_confidence=base.min_confidence + generator.normal(0.0, sigma * domain.span("min_confidence")),
        min_lift=base.min_lift + generator.normal(0.0, sigma * domain.span("min_lift")),
        max_len=int(base.max_len),
        pruning_factor=base.pruning_factor + generator.normal(0.0, sigma * domain.span("pruning_factor")),
        bounds=domain,
    )

    # Discrete dimension: step by +-1 with a probability tied to the step size.
    if generator.random() < min(1.0, sigma * MAX_LEN_MUTATION_SCALE):
        direction = 1 if generator.random() < 0.5 else -1
        proposal.max_len = int(base.max_len) + direction

    return proposal.clip()


def generate_neighbors(
    state: OptimizationState,
    n_neighbors: int = 4,
    step_size: float = 0.05,
    rng: Optional[np.random.Generator] = None,
    bounds: Optional[StateBounds] = None,
) -> List[OptimizationState]:
    """
    Sample `n_neighbors` independent mutations of `state` for a steepest-ascent
    step: the whole neighbourhood is evaluated and only the best is adopted.
    """
    generator = _resolve_rng(rng)
    count = max(1, int(n_neighbors))
    return [
        mutate_state(state, step_size=step_size, rng=generator, bounds=bounds)
        for _ in range(count)
    ]


def adapt_step_size(
    step_size: float,
    success_rate: float,
    target_rate: float = RECHENBERG_TARGET_RATE,
    expansion: float = STEP_EXPANSION_FACTOR,
    contraction: float = STEP_CONTRACTION_FACTOR,
) -> float:
    """
    Rechenberg's 1/5th success rule.

    When more than one in five proposals is accepted the search is making easy
    progress and should stride further; when fewer are accepted it is overshooting
    and should refine. The step size is clamped to [MIN_STEP_SIZE, MAX_STEP_SIZE].
    """
    current = float(np.clip(step_size, MIN_STEP_SIZE, MAX_STEP_SIZE))
    rate = float(success_rate)

    if rate > target_rate:
        adapted = current * float(expansion)
    elif rate < target_rate:
        adapted = current * float(contraction)
    else:
        adapted = current

    return float(np.clip(adapted, MIN_STEP_SIZE, MAX_STEP_SIZE))


def random_state(
    rng: Optional[np.random.Generator] = None,
    bounds: Optional[StateBounds] = None,
) -> OptimizationState:
    """Draw a uniformly random feasible state, used for stochastic restarts."""
    generator = _resolve_rng(rng)
    domain = bounds or DEFAULT_BOUNDS

    return OptimizationState(
        min_support=float(generator.uniform(*domain.min_support_range)),
        min_confidence=float(generator.uniform(*domain.min_confidence_range)),
        min_lift=float(generator.uniform(*domain.min_lift_range)),
        max_len=int(generator.choice(list(domain.max_len_choices))),
        pruning_factor=float(generator.uniform(*domain.pruning_factor_range)),
        bounds=domain,
    ).clip()


def latin_hypercube_states(
    n_samples: int,
    rng: Optional[np.random.Generator] = None,
    bounds: Optional[StateBounds] = None,
) -> List[OptimizationState]:
    """
    Stratified restart points via Latin Hypercube sampling.

    Each continuous axis is split into `n_samples` equal strata and sampled once
    per stratum, then the per-axis orderings are shuffled independently. This
    spreads restarts across the domain far more evenly than independent uniform
    draws, which is what makes a handful of restarts worth taking.
    """
    generator = _resolve_rng(rng)
    domain = bounds or DEFAULT_BOUNDS
    count = max(1, int(n_samples))

    def _stratified(low: float, high: float) -> np.ndarray:
        strata = (np.arange(count) + generator.random(count)) / count
        generator.shuffle(strata)
        return low + strata * (high - low)

    supports = _stratified(*domain.min_support_range)
    confidences = _stratified(*domain.min_confidence_range)
    lifts = _stratified(*domain.min_lift_range)
    prunings = _stratified(*domain.pruning_factor_range)

    choices = list(domain.max_len_choices)
    lengths = [choices[i % len(choices)] for i in range(count)]
    generator.shuffle(lengths)

    return [
        OptimizationState(
            min_support=float(supports[i]),
            min_confidence=float(confidences[i]),
            min_lift=float(lifts[i]),
            max_len=int(lengths[i]),
            pruning_factor=float(prunings[i]),
            bounds=domain,
        ).clip()
        for i in range(count)
    ]
