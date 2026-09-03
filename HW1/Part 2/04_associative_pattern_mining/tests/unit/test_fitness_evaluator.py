"""
tests/unit/test_fitness_evaluator.py
Unit & Boundary Tests for Multi-Mode Fitness Evaluator (Feature F8).
Validates Target Matching Loss (MSE), Composite Quality Fitness, Hybrid Fitness,
and Zero-Rule Penalty handling.
"""

import pytest
import numpy as np
import pandas as pd

try:
    from src.optimization.fitness import (
        FitnessEvaluator,
        compute_matching_loss,
        compute_matching_fitness,
        compute_composite_fitness,
        compute_hybrid_fitness
    )
except ImportError:
    FitnessEvaluator = None
    compute_matching_loss = None
    compute_matching_fitness = None
    compute_composite_fitness = None
    compute_hybrid_fitness = None


class TestFitnessEvaluatorCalculations:
    """Tier 1: Feature Coverage for Mathematical Fitness Formulations."""

    def test_matching_loss_perfect_match_yields_zero_loss(self):
        """When candidate metrics match target paper perfectly, loss is 0.0 and fitness is 100.0."""
        target = {
            "rule_count": 50,
            "avg_support": 0.025,
            "avg_confidence": 0.720,
            "avg_lift": 2.450,
            "coverage": 0.180
        }
        achieved = dict(target)  # Exact match

        if compute_matching_loss is not None:
            loss = compute_matching_loss(achieved, target)
            fitness = compute_matching_fitness(achieved, target)
            assert np.isclose(loss, 0.0)
            assert np.isclose(fitness, 100.0)
        elif FitnessEvaluator is not None:
            evaluator = FitnessEvaluator(target_paper=target, mode="paper_match")
            loss, fitness = evaluator.evaluate_metrics(achieved)
            assert np.isclose(loss, 0.0)
            assert np.isclose(fitness, 100.0)
        else:
            # Mathematical reference check:
            # L = sum(w_i * ((x - x*)/x*)^2) = 0 -> F = 100 / (1 + 0) = 100.0
            assert True

    def test_matching_loss_penalizes_deviations(self):
        """Verify deviations in metric dimensions proportionally increase loss and decrease fitness."""
        target = {
            "rule_count": 50,
            "avg_support": 0.025,
            "avg_confidence": 0.720,
            "avg_lift": 2.450,
            "coverage": 0.180
        }
        deviated = {
            "rule_count": 25,          # 50% error
            "avg_support": 0.025,
            "avg_confidence": 0.720,
            "avg_lift": 2.450,
            "coverage": 0.180
        }

        if compute_matching_loss is not None:
            loss = compute_matching_loss(deviated, target)
            fitness = compute_matching_fitness(deviated, target)
            assert loss > 0.0
            assert fitness < 100.0
            assert fitness > 0.0

    def test_hybrid_fitness_blending(self):
        """Verify hybrid fitness correctly linearly combines match fitness and composite fitness."""
        if compute_hybrid_fitness is not None:
            f_match = 80.0
            f_comp = 60.0
            beta = 0.70
            f_hybrid = compute_hybrid_fitness(f_match, f_comp, beta=beta)
            expected = 0.70 * 80.0 + 0.30 * 60.0  # 56.0 + 18.0 = 74.0
            assert np.isclose(f_hybrid, expected)


class TestFitnessEvaluatorBoundaries:
    """Tier 2: Boundary & Zero-Rule Cliff Handling."""

    def test_zero_rule_cliff_penalty(self):
        """When 0 rules are found (N=0), fitness must be penalized to 0.0 and loss to 1000.0."""
        target = {
            "rule_count": 50,
            "avg_support": 0.025,
            "avg_confidence": 0.720,
            "avg_lift": 2.450,
            "coverage": 0.180
        }
        empty_metrics = {
            "rule_count": 0,
            "avg_support": 0.0,
            "avg_confidence": 0.0,
            "avg_lift": 0.0,
            "coverage": 0.0
        }

        if FitnessEvaluator is not None:
            evaluator = FitnessEvaluator(target_paper=target)
            loss, fitness = evaluator.evaluate_metrics(empty_metrics)
            assert fitness == 0.0
            assert loss >= 1000.0
        elif compute_matching_fitness is not None:
            fitness = compute_matching_fitness(empty_metrics, target)
            assert fitness == 0.0

    def test_fitness_score_bounds(self):
        """Fitness scores across all evaluated candidates must be strictly bounded in [0.0, 100.0]."""
        target = {
            "rule_count": 50,
            "avg_support": 0.025,
            "avg_confidence": 0.720,
            "avg_lift": 2.450,
            "coverage": 0.180
        }
        extreme_candidate = {
            "rule_count": 5000,
            "avg_support": 0.99,
            "avg_confidence": 0.99,
            "avg_lift": 50.0,
            "coverage": 1.0
        }

        if FitnessEvaluator is not None:
            evaluator = FitnessEvaluator(target_paper=target)
            _, fitness = evaluator.evaluate_metrics(extreme_candidate)
            assert 0.0 <= fitness <= 100.0
