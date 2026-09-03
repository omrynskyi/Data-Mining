"""
Resilient Artifact Loader for the Admin Dashboard (Feature F12).

The dashboard has to stay useful whatever state the project is in: before the
pipeline has ever run, between a pipeline run and an optimization run, and while
either is midway through rewriting its outputs. Every accessor therefore returns
a well-formed structure rather than raising, and reports through
:meth:`availability` which artifacts are genuinely present so the UI can label
missing sections honestly instead of rendering silent zeros.

Loaded files are cached and invalidated on modification time, so re-running the
pipeline is picked up on the next request without restarting the server.
"""

import ast
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import pandas as pd

from config import ARTIFACTS_DIR
from src.utils.logger import get_logger

logger = get_logger("crisp_dm.dashboard.artifacts")

#: Filenames the dashboard reads, keyed by the logical artifact name.
ARTIFACT_FILES = {
    "pipeline_summary": "pipeline_summary.json",
    "pipeline_report": "pipeline_report.md",
    "rules_json": "rules.json",
    "rules_csv": "rules.csv",
    "frequent_itemsets": "frequent_itemsets.csv",
    "optimization_log": "optimization_log.json",
    "optimization_history": "optimization_history.csv",
    "optimized_rules": "optimized_rules.csv",
}


def parse_item_list(value: Any) -> List[str]:
    """
    Normalise an antecedent/consequent cell into a list of item labels.

    The same rule reaches us as a real list (JSON artifact), a Python-list repr
    (`rules.csv` written by `DataFrame.to_csv`), or a comma-joined string
    (`optimized_rules.csv`), so all three shapes are accepted.
    """
    if isinstance(value, (list, tuple, set, frozenset)):
        return [str(item).strip() for item in value if str(item).strip()]

    if value is None:
        return []

    text = str(value).strip()
    if not text or text.lower() == "nan":
        return []

    if text.startswith("[") and text.endswith("]"):
        try:
            parsed = ast.literal_eval(text)
            if isinstance(parsed, (list, tuple, set, frozenset)):
                return [str(item).strip() for item in parsed if str(item).strip()]
        except (ValueError, SyntaxError):
            inner = text[1:-1]
            return [
                part.strip().strip("'\"")
                for part in inner.split(",")
                if part.strip().strip("'\"")
            ]

    return [part.strip() for part in text.split(",") if part.strip()]


class ArtifactLoader:
    """Reads pipeline and optimization artifacts from disk with graceful fallbacks."""

    def __init__(self, artifacts_dir: Optional[Union[str, Path]] = None):
        self.artifacts_dir = Path(artifacts_dir) if artifacts_dir else Path(ARTIFACTS_DIR)
        self._cache: Dict[str, Any] = {}
        self._mtimes: Dict[str, float] = {}

    # ------------------------------------------------------------------
    # Low-level file access
    # ------------------------------------------------------------------

    def path_for(self, key: str) -> Path:
        """Absolute path of a logical artifact."""
        return self.artifacts_dir / ARTIFACT_FILES.get(key, key)

    def exists(self, key: str) -> bool:
        """True when the artifact file is present on disk."""
        return self.path_for(key).is_file()

    def _is_stale(self, key: str) -> bool:
        """True when the cached copy predates the file on disk."""
        path = self.path_for(key)
        if not path.is_file():
            return key in self._cache
        try:
            return self._mtimes.get(key) != path.stat().st_mtime
        except OSError:
            return True

    def _load_json(self, key: str) -> Optional[Any]:
        """Read a JSON artifact, returning None when absent or unreadable."""
        path = self.path_for(key)
        if not path.is_file():
            self._cache.pop(key, None)
            self._mtimes.pop(key, None)
            return None

        if key in self._cache and not self._is_stale(key):
            return self._cache[key]

        try:
            with open(path, "r", encoding="utf-8") as handle:
                data = json.load(handle)
        except (json.JSONDecodeError, OSError) as exc:
            # A pipeline run midway through writing this file is expected, not fatal.
            logger.warning(f"Could not read {path.name}: {exc}")
            return self._cache.get(key)

        self._cache[key] = data
        self._mtimes[key] = path.stat().st_mtime
        return data

    def _load_csv(self, key: str) -> Optional[pd.DataFrame]:
        """Read a CSV artifact, returning None when absent or unreadable."""
        path = self.path_for(key)
        if not path.is_file():
            self._cache.pop(key, None)
            self._mtimes.pop(key, None)
            return None

        if key in self._cache and not self._is_stale(key):
            return self._cache[key]

        try:
            frame = pd.read_csv(path)
        except (pd.errors.ParserError, pd.errors.EmptyDataError, OSError) as exc:
            logger.warning(f"Could not read {path.name}: {exc}")
            return self._cache.get(key)

        self._cache[key] = frame
        self._mtimes[key] = path.stat().st_mtime
        return frame

    # ------------------------------------------------------------------
    # Pipeline artifacts
    # ------------------------------------------------------------------

    def get_pipeline_summary(self) -> Dict[str, Any]:
        """
        CRISP-DM pipeline summary, or an empty-but-valid skeleton when the
        pipeline has not been run yet.
        """
        summary = self._load_json("pipeline_summary")
        if isinstance(summary, dict):
            return summary

        return {
            "pipeline_metadata": {},
            "crisp_dm_stages": {},
            "top_rules": [],
            "_available": False,
        }

    def get_pipeline_report(self) -> str:
        """Markdown pipeline report, or an empty string when absent."""
        path = self.path_for("pipeline_report")
        if not path.is_file():
            return ""
        try:
            return path.read_text(encoding="utf-8")
        except OSError:
            return ""

    def get_rules(self) -> List[Dict[str, Any]]:
        """
        Mined association rules as JSON-ready dictionaries.

        Prefers `rules.json` (which preserves list-valued antecedents) and falls
        back to `rules.csv`, normalising item lists either way.
        """
        rules = self._load_json("rules_json")
        if isinstance(rules, list) and rules:
            return [self._normalise_rule(rule, index) for index, rule in enumerate(rules)]

        frame = self._load_csv("rules_csv")
        if frame is not None and not frame.empty:
            records = frame.to_dict(orient="records")
            return [self._normalise_rule(rule, index) for index, rule in enumerate(records)]

        return []

    def get_rules_df(self) -> pd.DataFrame:
        """Mined rules as a DataFrame with list-valued antecedents/consequents."""
        rules = self.get_rules()
        if not rules:
            return pd.DataFrame(
                columns=[
                    "id", "antecedents", "consequents", "support",
                    "confidence", "lift", "leverage", "conviction",
                ]
            )
        return pd.DataFrame(rules)

    @staticmethod
    def _normalise_rule(rule: Dict[str, Any], index: int) -> Dict[str, Any]:
        """Coerce one rule record into the shape the REST API promises."""
        normalised = dict(rule)
        normalised["id"] = int(rule.get("id", index + 1) or index + 1)
        normalised["antecedents"] = parse_item_list(rule.get("antecedents"))
        normalised["consequents"] = parse_item_list(rule.get("consequents"))

        for metric in (
            "support", "confidence", "lift", "leverage", "conviction",
            "zhangs_metric", "kulczynski", "imbalance_ratio", "cosine",
            "antecedent_support", "consequent_support", "composite_score",
        ):
            if metric in normalised:
                try:
                    value = float(normalised[metric])
                except (TypeError, ValueError):
                    value = 0.0
                # NaN and infinities are not valid JSON; clamp them out here.
                normalised[metric] = value if value == value and abs(value) != float("inf") else 0.0

        return normalised

    def get_frequent_itemsets(self) -> List[Dict[str, Any]]:
        """Discovered frequent itemsets as dictionaries."""
        frame = self._load_csv("frequent_itemsets")
        if frame is None or frame.empty:
            return []

        records = []
        for index, row in enumerate(frame.to_dict(orient="records")):
            record = dict(row)
            record["items"] = parse_item_list(record.get("itemsets"))
            record["length"] = int(record.get("length", len(record["items"])) or len(record["items"]))
            try:
                record["support"] = float(record.get("support", 0.0))
            except (TypeError, ValueError):
                record["support"] = 0.0
            record["id"] = index + 1
            records.append(record)
        return records

    # ------------------------------------------------------------------
    # Optimization artifacts
    # ------------------------------------------------------------------

    def get_optimization_log(self) -> Dict[str, Any]:
        """
        Hill climbing audit log, or an empty-but-valid skeleton when the
        optimizer has not been run yet.
        """
        log = self._load_json("optimization_log")
        if isinstance(log, dict):
            return log

        return {
            "metadata": {},
            "target_paper": {},
            "config": {},
            "summary": {},
            "target_vs_achieved": {},
            "best_hyperparameters": {},
            "iteration_trail": [],
            "_available": False,
        }

    def get_optimization_history(self) -> List[Dict[str, Any]]:
        """
        Iteration-by-iteration trajectory.

        Prefers `optimization_history.csv`, falling back to the `iteration_trail`
        embedded in the JSON log so the convergence chart still renders if only
        one of the two artifacts survived.
        """
        frame = self._load_csv("optimization_history")
        if frame is not None and not frame.empty:
            return frame.to_dict(orient="records")

        trail = self.get_optimization_log().get("iteration_trail") or []
        flattened = []
        for entry in trail:
            row = {
                key: entry.get(key)
                for key in ("iteration", "restart_id", "step_type", "loss", "fitness", "best_fitness", "step_size", "accepted")
            }
            row.update(entry.get("current_state") or {})
            row.update(entry.get("metrics") or {})
            flattened.append(row)
        return flattened

    def get_optimized_rules(self) -> List[Dict[str, Any]]:
        """Rule set produced by the champion hyperparameter configuration."""
        frame = self._load_csv("optimized_rules")
        if frame is None or frame.empty:
            return []
        records = frame.to_dict(orient="records")
        return [self._normalise_rule(rule, index) for index, rule in enumerate(records)]

    # ------------------------------------------------------------------
    # Aggregate views
    # ------------------------------------------------------------------

    def availability(self) -> Dict[str, bool]:
        """
        Which artifact families are present, for `/health` and for UI sections
        that must say "not generated yet" rather than show empty charts.
        """
        summary = self.get_pipeline_summary()
        stages = summary.get("crisp_dm_stages") or {}
        return {
            "eda": bool(stages.get("data_understanding")),
            "pipeline": bool(summary.get("crisp_dm_stages")),
            "rules": bool(self.get_rules()),
            "optimization": bool(self.get_optimization_log().get("iteration_trail")),
        }

    def get_eda(self) -> Dict[str, Any]:
        """Data-understanding profile extracted from the pipeline summary."""
        stages = self.get_pipeline_summary().get("crisp_dm_stages") or {}
        understanding = stages.get("data_understanding") or {}
        preparation = stages.get("data_preparation") or {}

        return {
            "available": bool(understanding),
            "dataset_name": understanding.get("dataset_name", "unknown"),
            "raw_records_count": understanding.get("raw_records_count", 0),
            "unique_invoices": understanding.get("unique_invoices", 0),
            "unique_items": understanding.get("unique_items", 0),
            "unique_customers": understanding.get("unique_customers", 0),
            "cancellation_rate_pct": understanding.get("cancellation_rate_pct", 0.0),
            "sparsity_pct": understanding.get("sparsity_pct", 0.0),
            "matrix_density_pct": understanding.get("matrix_density_pct", 0.0),
            "basket_size_stats": understanding.get("basket_size_stats", {}),
            "basket_size_distribution": understanding.get("basket_size_distribution", []),
            "top_frequent_items": understanding.get(
                "top_frequent_items", understanding.get("top_5_frequent_items", [])
            ),
            "pareto_analysis": understanding.get("pareto_analysis", {}),
            "country_distribution": understanding.get("country_distribution", []),
            "cleaning_steps_applied": preparation.get("cleaning_steps_applied", []),
            "matrix_shape": preparation.get("matrix_shape", []),
        }

    def summary_kpis(self) -> Dict[str, Any]:
        """Headline numbers for the dashboard's overview strip."""
        summary = self.get_pipeline_summary()
        metadata = summary.get("pipeline_metadata") or {}
        stages = summary.get("crisp_dm_stages") or {}
        understanding = stages.get("data_understanding") or {}
        preparation = stages.get("data_preparation") or {}
        modeling = stages.get("modeling") or {}
        evaluation = stages.get("evaluation") or {}

        rules = self.get_rules()
        optimization = self.get_optimization_log()
        opt_summary = optimization.get("summary") or {}
        paper = optimization.get("target_paper") or {}

        def _mean(metric: str) -> float:
            values = [float(rule.get(metric, 0.0) or 0.0) for rule in rules]
            return round(sum(values) / len(values), 6) if values else 0.0

        return {
            "dataset_name": metadata.get("dataset_name", understanding.get("dataset_name", "not generated")),
            "algorithm": metadata.get("algorithm", "-"),
            "framework": metadata.get("framework", "CRISP-DM"),
            "run_timestamp": metadata.get("run_timestamp"),
            "execution_time_seconds": metadata.get("execution_time_seconds", 0.0),
            "parameters": metadata.get("parameters", {}),
            "transactions": preparation.get("cleaned_transactions_count", understanding.get("unique_invoices", 0)),
            "unique_items": preparation.get("cleaned_unique_items_count", understanding.get("unique_items", 0)),
            "raw_records": understanding.get("raw_records_count", 0),
            "sparsity_pct": understanding.get("sparsity_pct", 0.0),
            "frequent_itemsets": modeling.get("frequent_itemsets_total", 0),
            "itemsets_by_length": modeling.get("itemsets_by_length", {}),
            "raw_rules_generated": modeling.get("raw_rules_generated", 0),
            "redundant_rules_pruned": evaluation.get("redundant_rules_pruned", 0),
            "rules_count": len(rules),
            "rule_categories": evaluation.get("rule_categories", {}),
            "avg_confidence": _mean("confidence"),
            "avg_lift": _mean("lift"),
            "avg_support": _mean("support"),
            "max_lift": round(max([float(r.get("lift", 0.0) or 0.0) for r in rules], default=0.0), 6),
            "optimization": {
                "available": bool(opt_summary),
                "target_paper_key": paper.get("key"),
                "target_paper_title": paper.get("title"),
                "best_fitness": opt_summary.get("best_fitness", 0.0),
                "initial_fitness": opt_summary.get("initial_fitness", 0.0),
                "best_loss": opt_summary.get("best_loss", 0.0),
                "iterations": opt_summary.get("total_iterations_run", 0),
                "restarts": opt_summary.get("restarts_triggered", 0),
                "best_hyperparameters": optimization.get("best_hyperparameters", {}),
            },
            "artifacts": self.availability(),
        }
