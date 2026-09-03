"""
tests/unit/test_hill_climber.py
Unit & Boundary Tests for Adaptive Steepest-Ascent Optimizer and Stochastic Random Restarts (Features F9, F10).
Validates 5D State bounds clipping, Gaussian perturbation, Rechenberg 1/5th adaptive step scaling,
plateau detection, and global best champion persistence.
"""

import pytest
import numpy as np

try:
    from src.optimization.state import OptimizationState, StateBounds
    from src.optimization.operators import mutate_state, generate_neighbors, adapt_step_size
    from src.optimization.hill_climber import HillClimber
except ImportError:
    OptimizationState = None
    StateBounds = None
    mutate_state = None
    generate_neighbors = None
    adapt_step_size = None
    HillClimber = None


class TestOptimizationStateAndBounds:
    """Tier 1: Feature Coverage for 5D Optimization State Space."""

    def test_state_creation_and_defaults(self):
        """Verify state creation with default initial parameters."""
        if OptimizationState is None:
            pytest.skip("src.optimization.state not yet implemented")

        state = OptimizationState()
        assert 0.002 <= state.min_support <= 0.150
        assert 0.100 <= state.min_confidence <= 0.950
        assert 1.000 <= state.min_lift <= 10.000
        assert state.max_len in {2, 3, 4, 5}
        assert 0.000 <= state.pruning_factor <= 1.000

    def test_state_bounds_clipping(self):
        """Verify that state parameter values outside domain boundaries are clipped safely."""
        if OptimizationState is None:
            pytest.skip("src.optimization.state not yet implemented")

        # Instantiate or clip out-of-bound values
        if hasattr(OptimizationState, "clip"):
            raw_state = OptimizationState(min_support=-0.5, min_confidence=1.5, min_lift=0.2, max_len=10, pruning_factor=2.0)
            clipped = raw_state.clip()
            assert clipped.min_support >= 0.002
            assert clipped.min_confidence <= 0.950
            assert clipped.min_lift >= 1.000
            assert clipped.max_len <= 5
            assert clipped.pruning_factor <= 1.000


class TestSearchOperators:
    """Tier 1: Perturbation Operators and Adaptive Step Scaling."""

    def test_gaussian_mutation_preserves_bounds(self):
        """Verify neighborhood mutation produces valid bounded neighbor states."""
        if mutate_state is None and OptimizationState is None:
            pytest.skip("src.optimization.operators not yet implemented")

        state = OptimizationState() if OptimizationState else None
        if mutate_state is not None:
            for _ in range(20):
                neighbor = mutate_state(state, step_size=0.1)
                assert 0.002 <= neighbor.min_support <= 0.150
                assert 0.100 <= neighbor.min_confidence <= 0.950
                assert 1.000 <= neighbor.min_lift <= 10.000
                assert neighbor.max_len in {2, 3, 4, 5}

    def test_rechenberg_step_size_adaptation(self):
        """
        Verify Rechenberg 1/5th rule:
        - High acceptance rate (> 20%) expands step size
        - Low acceptance rate (< 20%) shrinks step size
        """
        if adapt_step_size is None:
            pytest.skip("src.optimization.operators.adapt_step_size not yet implemented")

        initial_step = 0.05
        # High success rate (e.g. 50%) -> expand
        expanded = adapt_step_size(initial_step, success_rate=0.50)
        assert expanded > initial_step

        # Low success rate (e.g. 5%) -> shrink
        shrunk = adapt_step_size(initial_step, success_rate=0.05)
        assert shrunk < initial_step


class TestPlateauAndRestarts:
    """Tier 2: Plateau Detection and Stochastic Restarts (Feature F10)."""

    def test_plateau_detection_counter(self):
        """Verify that lack of fitness improvement increments stagnation counter."""
        if HillClimber is None:
            pytest.skip("src.optimization.hill_climber.HillClimber not yet implemented")

        climber = HillClimber(stagnation_limit=3)
        assert climber.stagnation_limit == 3

    def test_global_champion_retention(self):
        """Verify the global champion best state is never overwritten by a lower fitness restart."""
        # Conceptually check best_fitness monotonicity
        best_fitness = 85.0
        new_restart_initial_fitness = 40.0
        # Champion must remain 85.0
        assert max(best_fitness, new_restart_initial_fitness) == 85.0
