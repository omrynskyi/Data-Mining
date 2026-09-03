"""
Optimization Audit Logger (Feature F11).

Serialises a completed search into the three artifacts the dashboard and the
acceptance tests consume:

* ``optimization_log.json``    -- target paper, config, summary, per-dimension
                                  target-vs-achieved comparison, full trail.
* ``optimization_history.csv`` -- flat iteration-by-iteration trajectory.
* ``optimized_rules.csv``      -- the rule set the champion configuration yields.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional, Union

import pandas as pd

from src.deployment.exporter import CustomJSONEncoder
from src.optimization.hill_climber import OptimizationResult
from src.utils.logger import get_logger

logger = get_logger("crisp_dm.optimizer.logger")

#: Column order of `optimization_history.csv`, fixed by the M2 interface contract.
HISTORY_COLUMNS = [
    "iteration",
    "restart_id",
    "step_type",
    "min_support",
    "min_confidence",
    "max_len",
    "min_lift",
    "pruning_factor",
    "rule_count",
    "avg_support",
    "avg_confidence",
    "avg_lift",
    "coverage",
    "loss",
    "fitness",
    "best_fitness",
    "step_size",
    "accepted",
]


def build_optimization_log(
    result: OptimizationResult,
    dataset_name: str = "synthetic_retail",
) -> Dict[str, Any]:
    """Assemble the `optimization_log.json` payload from a search result."""
    paper = result.target_paper or {}

    return {
        "metadata": {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "execution_time_seconds": round(result.execution_time_seconds, 4),
            "seed": result.config.get("seed"),
            "dataset": dataset_name,
            "total_transactions": result.dataset_metadata.get("total_transactions", 0),
            "unique_items": result.dataset_metadata.get("unique_items", 0),
            "candidate_rule_superset": result.dataset_metadata.get("superset_rule_count", 0),
            "superset_build_seconds": result.dataset_metadata.get("superset_build_seconds", 0.0),
        },
        "target_paper": {
            "key": paper.get("key"),
            "title": paper.get("title"),
            "authors": paper.get("authors"),
            "venue": paper.get("venue"),
            "doi": paper.get("doi"),
            "summary": paper.get("summary"),
            "target_basis": paper.get("target_basis"),
            "target_metrics": paper.get("target_metrics", {}),
        },
        "config": result.config,
        "summary": {
            "total_iterations_run": result.total_iterations_run,
            "restarts_triggered": result.restarts_triggered,
            "termination_reason": result.termination_reason,
            "initial_fitness": round(result.initial_fitness, 4),
            "best_fitness": round(result.best_fitness, 4),
            "best_loss": round(result.best_loss, 6),
            "fitness_improvement": round(result.best_fitness - result.initial_fitness, 4),
            "evaluations": len(result.history),
        },
        "target_vs_achieved": result.target_vs_achieved,
        "best_hyperparameters": result.best_state.to_dict(),
        "best_metrics": {
            "rule_count": int(result.best_metrics.get("rule_count", 0)),
            "avg_support": round(float(result.best_metrics.get("avg_support", 0.0)), 6),
            "avg_confidence": round(float(result.best_metrics.get("avg_confidence", 0.0)), 6),
            "avg_lift": round(float(result.best_metrics.get("avg_lift", 0.0)), 6),
            "coverage": round(float(result.best_metrics.get("coverage", 0.0)), 6),
        },
        "iteration_trail": result.iteration_trail,
    }


def export_optimization_log(
    result: OptimizationResult,
    path: Union[str, Path],
    dataset_name: str = "synthetic_retail",
) -> str:
    """Write `optimization_log.json` and return its path."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)

    payload = build_optimization_log(result, dataset_name=dataset_name)
    with open(target, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, cls=CustomJSONEncoder)

    logger.info(f"Exported optimization log to: {target}")
    return str(target)


def export_optimization_history(
    result: OptimizationResult,
    path: Union[str, Path],
) -> str:
    """Write the flat trajectory CSV and return its path."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)

    df = pd.DataFrame(result.history)
    if df.empty:
        df = pd.DataFrame(columns=HISTORY_COLUMNS)
    else:
        df = df.reindex(columns=HISTORY_COLUMNS)

    df.to_csv(target, index=False)
    logger.info(f"Exported {len(df)} optimization iterations to: {target}")
    return str(target)


def export_optimized_rules(
    result: OptimizationResult,
    path: Union[str, Path],
) -> str:
    """Write the champion configuration's rule set and return its path."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)

    rules = result.best_rules_df
    if rules is None or rules.empty:
        pd.DataFrame(
            columns=[
                "id", "antecedents", "consequents", "support", "confidence",
                "lift", "leverage", "conviction", "zhangs_metric",
                "kulczynski", "imbalance_ratio", "cosine",
            ]
        ).to_csv(target, index=False)
        logger.warning(f"Champion configuration yielded no rules; wrote empty {target}")
        return str(target)

    serialisable = rules.copy()
    for column in ("antecedents", "consequents"):
        if column in serialisable.columns:
            serialisable[column] = serialisable[column].apply(
                lambda items: ", ".join(sorted(items))
                if isinstance(items, (list, set, frozenset))
                else str(items)
            )

    serialisable.to_csv(target, index=False)
    logger.info(f"Exported {len(serialisable)} optimized rules to: {target}")
    return str(target)


def export_all(
    result: OptimizationResult,
    log_path: Union[str, Path],
    history_path: Union[str, Path],
    rules_path: Optional[Union[str, Path]] = None,
    dataset_name: str = "synthetic_retail",
) -> Dict[str, str]:
    """Write every optimization artifact, returning a name -> path mapping."""
    written = {
        "optimization_log": export_optimization_log(result, log_path, dataset_name=dataset_name),
        "optimization_history": export_optimization_history(result, history_path),
    }
    if rules_path is not None:
        written["optimized_rules"] = export_optimized_rules(result, rules_path)
    return written
