"""
Adaptive Steepest-Ascent Hill Climbing with Stochastic Restarts (Features F9, F10).

Each iteration samples a neighbourhood around the incumbent, evaluates all of it,
and moves to the best neighbour if it improves on the incumbent -- steepest
ascent rather than first-improvement, which is affordable here because scoring a
candidate is a masking operation (see `evaluator.py`).

Two mechanisms keep the search off local optima:

* **Rechenberg step adaptation** -- the mutation radius grows while proposals are
  being accepted and shrinks when they are not, so the search strides across
  plateaus and refines near peaks without hand-tuned schedules.
* **Stochastic restart** -- when the incumbent stops improving for
  `stagnation_limit` iterations the segment is abandoned and the search relaunches
  from a Latin Hypercube point. When no restart budget remains, the step size is
  instead kicked back to its initial value so the remaining iteration budget is
  spent escaping rather than idling.

The global champion is held outside the restart loop and is never overwritten by
a weaker segment, so `best_fitness` is monotonically non-decreasing across the
entire recorded trajectory.
"""

import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from src.optimization.evaluator import RuleSetEvaluator
from src.optimization.fitness import FitnessEvaluator
from src.optimization.operators import (
    adapt_step_size,
    generate_neighbors,
    latin_hypercube_states,
)
from src.optimization.papers import get_paper_profile
from src.optimization.state import DEFAULT_BOUNDS, OptimizationState, StateBounds
from src.utils.logger import get_logger

logger = get_logger("crisp_dm.optimizer")

#: Fitness improvement below this is treated as noise, not progress.
IMPROVEMENT_EPSILON = 1e-6

#: Fitness at or above this is treated as a match and terminates the search.
PERFECT_MATCH_FITNESS = 99.999


@dataclass
class OptimizationResult:
    """Outcome of a complete hill climbing search."""

    target_paper: Dict[str, Any]
    config: Dict[str, Any]
    best_state: OptimizationState
    best_metrics: Dict[str, Any]
    best_fitness: float
    best_loss: float
    initial_fitness: float
    history: List[Dict[str, Any]]
    iteration_trail: List[Dict[str, Any]]
    target_vs_achieved: Dict[str, Dict[str, float]]
    restarts_triggered: int
    total_iterations_run: int
    termination_reason: str
    execution_time_seconds: float
    best_rules_df: pd.DataFrame = field(default_factory=pd.DataFrame)
    dataset_metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def history_df(self) -> pd.DataFrame:
        """Trajectory as a DataFrame matching `optimization_history.csv`."""
        return pd.DataFrame(self.history)


class HillClimber:
    """
    Steepest-ascent hill climber over the 5D mining hyperparameter space.

    Every constructor argument has a default, so the climber can be instantiated
    for inspection (`HillClimber(stagnation_limit=3)`) without a corpus.
    """

    def __init__(
        self,
        target_paper: str = "ghosh2004",
        fitness_mode: str = "hybrid",
        iterations: int = 30,
        max_restarts: int = 3,
        neighbors_per_step: int = 12,
        initial_step_size: float = 0.05,
        stagnation_limit: int = 5,
        scout_samples: int = 768,
        beta: float = 0.70,
        seed: int = 42,
        bounds: Optional[StateBounds] = None,
        algorithm: str = "fpgrowth",
        cache_dir: Optional[str] = None,
        evaluator: Optional[RuleSetEvaluator] = None,
    ):
        self.target_paper_key = target_paper
        self.fitness_mode = fitness_mode
        self.iterations = max(1, int(iterations))
        self.max_restarts = max(1, int(max_restarts))
        self.neighbors_per_step = max(1, int(neighbors_per_step))
        self.initial_step_size = float(initial_step_size)
        self.stagnation_limit = int(stagnation_limit)
        self.scout_samples = max(0, int(scout_samples))
        self.beta = float(beta)
        self.seed = int(seed)
        self.bounds = bounds or DEFAULT_BOUNDS
        self.algorithm = algorithm
        self.cache_dir = cache_dir
        self.evaluator = evaluator
        self._scout_ranking: List[OptimizationState] = []

        self.paper_profile = get_paper_profile(target_paper) if target_paper else None
        self.fitness = FitnessEvaluator(
            target_paper=self.paper_profile,
            mode=fitness_mode,
            beta=self.beta,
        )
        self.rng = np.random.default_rng(self.seed)

    # ------------------------------------------------------------------

    def _config_dict(self) -> Dict[str, Any]:
        """Search configuration, mirrored into the audit log."""
        return {
            "iterations_per_restart": self.iterations,
            "max_restarts": self.max_restarts,
            "initial_step_size": self.initial_step_size,
            "fitness_mode": self.fitness_mode,
            "neighbors_per_step": self.neighbors_per_step,
            "scout_samples": self.scout_samples,
            "stagnation_limit": self.stagnation_limit,
            "hybrid_beta": self.beta,
            "seed": self.seed,
            "algorithm": self.algorithm,
            "search_bounds": self.bounds.to_dict(),
        }

    def _score(self, state: OptimizationState) -> Dict[str, Any]:
        """Evaluate a state into metrics plus loss and fitness."""
        metrics = self.evaluator.evaluate(state)
        loss, fitness = self.fitness.evaluate_metrics(metrics)
        return {"metrics": metrics, "loss": float(loss), "fitness": float(fitness)}

    @staticmethod
    def _row(
        iteration: int,
        restart_id: int,
        step_type: str,
        state: OptimizationState,
        scored: Dict[str, Any],
        global_best_fitness: float,
        step_size: float,
        accepted: bool,
    ) -> Dict[str, Any]:
        """One row of `optimization_history.csv`."""
        params = state.clip().to_dict()
        metrics = scored["metrics"]
        return {
            "iteration": int(iteration),
            "restart_id": int(restart_id),
            "step_type": step_type,
            "min_support": params["min_support"],
            "min_confidence": params["min_confidence"],
            "max_len": params["max_len"],
            "min_lift": params["min_lift"],
            "pruning_factor": params["pruning_factor"],
            "rule_count": int(metrics["rule_count"]),
            "avg_support": round(float(metrics["avg_support"]), 6),
            "avg_confidence": round(float(metrics["avg_confidence"]), 6),
            "avg_lift": round(float(metrics["avg_lift"]), 6),
            "coverage": round(float(metrics["coverage"]), 6),
            "loss": round(float(scored["loss"]), 6),
            "fitness": round(float(scored["fitness"]), 6),
            "best_fitness": round(float(global_best_fitness), 6),
            "step_size": round(float(step_size), 6),
            "accepted": bool(accepted),
        }

    def _scout(self) -> List[OptimizationState]:
        """
        Cheap stratified reconnaissance of the domain, ranked best-first.

        Threshold-driven metrics like `rule_count` are step functions of the
        thresholds, so the fitness surface is a terrace of plateaus and a climber
        dropped at a fixed point frequently strands on one. Because scoring a
        candidate is a masking operation costing microseconds, a Latin Hypercube
        scout is nearly free and buys a far better basin to start from.

        This is multi-start initialisation, not a replacement for the climb -- the
        scout only chooses where each segment begins. Segment 0 takes the best
        scouted point and each restart takes the next best, so restarts relaunch
        into the most promising basins found rather than into fresh noise.
        """
        if self.scout_samples <= 0:
            return []

        candidates = latin_hypercube_states(
            self.scout_samples, rng=self.rng, bounds=self.bounds
        )
        ranked = sorted(
            candidates, key=lambda state: self._score(state)["fitness"], reverse=True
        )

        logger.info(
            f"Scout swept {self.scout_samples} stratified points; "
            f"best starting fitness {self._score(ranked[0])['fitness']:.2f}/100."
        )
        return ranked

    def _initial_state(self, restart_id: int, restart_points: List[OptimizationState]) -> OptimizationState:
        """
        Pick the starting point for a search segment: the `restart_id`-th best
        scouted basin, falling back to stratified random points (and finally to
        the domain's default operating point) when scouting is disabled.
        """
        if restart_id < len(self._scout_ranking):
            return self._scout_ranking[restart_id]
        if restart_points:
            return restart_points[restart_id % len(restart_points)]
        return OptimizationState(bounds=self.bounds).clip()

    # ------------------------------------------------------------------

    def run(self, transactions_df: pd.DataFrame) -> OptimizationResult:
        """
        Execute the search over a one-hot encoded transaction matrix.

        Returns an :class:`OptimizationResult` carrying the champion state, its
        rule set, the full iteration trail, and the target-versus-achieved
        comparison against the selected research paper.
        """
        start = time.perf_counter()

        if self.evaluator is None:
            self.evaluator = RuleSetEvaluator(
                onehot_df=transactions_df,
                bounds=self.bounds,
                algorithm=self.algorithm,
                cache_dir=self.cache_dir,
            )

        history: List[Dict[str, Any]] = []
        trail: List[Dict[str, Any]] = []

        global_best_state: Optional[OptimizationState] = None
        global_best_scored: Optional[Dict[str, Any]] = None
        global_best_fitness = -np.inf

        initial_fitness: Optional[float] = None
        restarts_triggered = 0
        total_iterations = 0
        termination_reason = "Max iterations reached"
        converged = False

        self._scout_ranking = self._scout()
        restart_points = latin_hypercube_states(
            max(1, self.max_restarts), rng=self.rng, bounds=self.bounds
        )

        logger.info(
            f"Hill climbing towards '{self.paper_profile['key']}' "
            f"({self.fitness_mode} fitness): {self.iterations} iterations x "
            f"{self.max_restarts} restart segment(s), {self.neighbors_per_step} neighbours per step."
        )

        for restart_id in range(self.max_restarts):
            if converged:
                break
            if restart_id > 0:
                restarts_triggered += 1
                logger.info(f"[restart {restart_id}] relaunching from a Latin Hypercube point.")

            current = self._initial_state(restart_id, restart_points)
            current_scored = self._score(current)
            step_size = self.initial_step_size
            stagnation = 0

            if current_scored["fitness"] > global_best_fitness:
                global_best_fitness = current_scored["fitness"]
                global_best_state = current.clip()
                global_best_scored = current_scored

            if initial_fitness is None:
                initial_fitness = current_scored["fitness"]

            row = self._row(
                iteration=len(history) + 1,
                restart_id=restart_id,
                step_type="initial",
                state=current,
                scored=current_scored,
                global_best_fitness=global_best_fitness,
                step_size=step_size,
                accepted=True,
            )
            history.append(row)
            trail.append(self._trail_entry(row, current, current_scored, global_best_fitness))

            for _ in range(self.iterations):
                total_iterations += 1

                neighbors = generate_neighbors(
                    current,
                    n_neighbors=self.neighbors_per_step,
                    step_size=step_size,
                    rng=self.rng,
                    bounds=self.bounds,
                )
                scored_neighbors = [(n, self._score(n)) for n in neighbors]

                # Steepest ascent: adopt the single best neighbour, if it improves.
                best_neighbor, best_scored = max(
                    scored_neighbors, key=lambda pair: pair[1]["fitness"]
                )

                improvements = sum(
                    1
                    for _, s in scored_neighbors
                    if s["fitness"] > current_scored["fitness"] + IMPROVEMENT_EPSILON
                )
                success_rate = improvements / float(len(scored_neighbors))

                accepted = best_scored["fitness"] > current_scored["fitness"] + IMPROVEMENT_EPSILON
                if accepted:
                    current, current_scored = best_neighbor, best_scored
                    stagnation = 0
                    step_type = "improvement"
                else:
                    stagnation += 1
                    step_type = "plateau"

                if current_scored["fitness"] > global_best_fitness:
                    global_best_fitness = current_scored["fitness"]
                    global_best_state = current.clip()
                    global_best_scored = current_scored

                # Rechenberg 1/5th rule, applied on the observed acceptance rate.
                step_size = adapt_step_size(step_size, success_rate=success_rate)

                if stagnation >= self.stagnation_limit:
                    if restart_id < self.max_restarts - 1:
                        step_type = "restart_triggered"
                        stagnation = 0
                    else:
                        # No restart budget left: kick the step size back out and
                        # keep spending the iteration budget on escaping.
                        step_type = "step_kick"
                        step_size = self.initial_step_size
                        stagnation = 0

                row = self._row(
                    iteration=len(history) + 1,
                    restart_id=restart_id,
                    step_type=step_type,
                    state=current,
                    scored=current_scored,
                    global_best_fitness=global_best_fitness,
                    step_size=step_size,
                    accepted=accepted,
                )
                history.append(row)
                trail.append(self._trail_entry(row, current, current_scored, global_best_fitness))

                if global_best_fitness >= PERFECT_MATCH_FITNESS:
                    termination_reason = "Target metrics matched within tolerance"
                    converged = True
                    break

                if step_type == "restart_triggered":
                    break

        # Describe how the search actually ended, not how an intermediate
        # segment ended -- a mid-search restart is progress, not termination.
        if converged:
            termination_reason = "Target metrics matched within tolerance"
        elif restarts_triggered > 0:
            termination_reason = (
                f"Search budget exhausted after {restarts_triggered} stochastic restart(s)"
            )
        else:
            termination_reason = "Max iterations reached"

        if global_best_state is None:
            global_best_state = OptimizationState(bounds=self.bounds).clip()
            global_best_scored = self._score(global_best_state)
            global_best_fitness = global_best_scored["fitness"]

        best_metrics = global_best_scored["metrics"]
        best_rules = self.evaluator.select_rules(global_best_state)

        elapsed = time.perf_counter() - start
        logger.info(
            f"Search complete in {elapsed:.2f}s: best fitness {global_best_fitness:.2f}/100 "
            f"with {best_metrics['rule_count']} rules "
            f"(target {self.fitness.target_metrics['rule_count']})."
        )

        return OptimizationResult(
            target_paper=self.paper_profile,
            config=self._config_dict(),
            best_state=global_best_state,
            best_metrics=best_metrics,
            best_fitness=float(global_best_fitness),
            best_loss=float(global_best_scored["loss"]),
            initial_fitness=float(initial_fitness if initial_fitness is not None else 0.0),
            history=history,
            iteration_trail=trail,
            target_vs_achieved=self.fitness.compare_to_target(best_metrics),
            restarts_triggered=restarts_triggered,
            total_iterations_run=total_iterations,
            termination_reason=termination_reason,
            execution_time_seconds=elapsed,
            best_rules_df=best_rules,
            dataset_metadata={
                "total_transactions": self.evaluator.n_transactions,
                "unique_items": self.evaluator.n_items,
                "superset_rule_count": int(len(self.evaluator.rules_df)),
                "superset_build_seconds": round(self.evaluator.build_seconds, 4),
            },
        )

    def _trail_entry(
        self,
        row: Dict[str, Any],
        state: OptimizationState,
        scored: Dict[str, Any],
        global_best_fitness: float,
    ) -> Dict[str, Any]:
        """Richer nested record for `optimization_log.json`."""
        return {
            "iteration": row["iteration"],
            "restart_id": row["restart_id"],
            "step_type": row["step_type"],
            "current_state": state.clip().to_dict(),
            "metrics": {
                "rule_count": int(scored["metrics"]["rule_count"]),
                "avg_support": round(float(scored["metrics"]["avg_support"]), 6),
                "avg_confidence": round(float(scored["metrics"]["avg_confidence"]), 6),
                "avg_lift": round(float(scored["metrics"]["avg_lift"]), 6),
                "coverage": round(float(scored["metrics"]["coverage"]), 6),
            },
            "loss": row["loss"],
            "fitness": row["fitness"],
            "best_fitness": round(float(global_best_fitness), 6),
            "step_size": row["step_size"],
            "accepted": row["accepted"],
        }
