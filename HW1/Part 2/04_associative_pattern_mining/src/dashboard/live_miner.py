"""
Interactive Live Mining Sandbox (Feature F17).

Backs the dashboard's sandbox tab, where an analyst drags support/confidence/lift
sliders and re-mines the corpus on the spot. It calls the same
`mine_association_rules` facade the batch pipeline uses -- the sandbox is a thin
interactive skin over the production engine, not a reimplementation of it, so
what a user tunes here reproduces exactly under `run_pipeline.py`.

Parameter validation is strict and returns actionable messages: a sandbox that
silently clamps a nonsensical threshold teaches the analyst the wrong thing about
the data.
"""

import time
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

from src.data.loader import load_dataset
from src.data.preprocessor import clean_retail_data
from src.evaluation.filter import categorize_rules, compute_composite_scores
from src.mining.engine import mine_association_rules
from src.utils.logger import get_logger

logger = get_logger("crisp_dm.dashboard.sandbox")

SUPPORTED_ALGORITHMS = ("fpgrowth", "apriori")

#: Guard rails for interactive use. A support floor below this on a large corpus
#: can take minutes and stall the request, which is not a useful sandbox.
MIN_ALLOWED_SUPPORT = 0.001
MAX_RULES_RETURNED = 500


class SandboxValidationError(ValueError):
    """Raised when sandbox parameters are outside their permitted ranges."""


def validate_parameters(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate and coerce a sandbox mining request.

    Raises
    ------
    SandboxValidationError : with a message naming the offending parameter.
    """
    if not isinstance(payload, dict):
        raise SandboxValidationError("Request body must be a JSON object.")

    algorithm = str(payload.get("algorithm", "fpgrowth")).lower().strip()
    if algorithm not in SUPPORTED_ALGORITHMS:
        raise SandboxValidationError(
            f"Unknown algorithm '{algorithm}'. Expected one of {list(SUPPORTED_ALGORITHMS)}."
        )

    def _number(name: str, default: float, low: float, high: float) -> float:
        raw = payload.get(name, default)
        try:
            value = float(raw)
        except (TypeError, ValueError):
            raise SandboxValidationError(f"Parameter '{name}' must be numeric, got {raw!r}.")
        if value != value:  # NaN
            raise SandboxValidationError(f"Parameter '{name}' must be a real number.")
        if not (low <= value <= high):
            raise SandboxValidationError(
                f"Parameter '{name}' must lie in [{low}, {high}], got {value}."
            )
        return value

    min_support = _number("min_support", 0.01, MIN_ALLOWED_SUPPORT, 1.0)
    min_confidence = _number("min_confidence", 0.3, 0.0, 1.0)
    min_lift = _number("min_lift", 1.0, 0.0, 1000.0)

    try:
        max_len = int(payload.get("max_len", 4))
    except (TypeError, ValueError):
        raise SandboxValidationError(
            f"Parameter 'max_len' must be an integer, got {payload.get('max_len')!r}."
        )
    if not (2 <= max_len <= 8):
        raise SandboxValidationError(f"Parameter 'max_len' must lie in [2, 8], got {max_len}.")

    try:
        top_n = int(payload.get("top_n", MAX_RULES_RETURNED))
    except (TypeError, ValueError):
        raise SandboxValidationError("Parameter 'top_n' must be an integer.")
    top_n = max(1, min(top_n, MAX_RULES_RETURNED))

    return {
        "algorithm": algorithm,
        "min_support": min_support,
        "min_confidence": min_confidence,
        "min_lift": min_lift,
        "max_len": max_len,
        "top_n": top_n,
        "sort_by": str(payload.get("sort_by", "lift")).lower().strip(),
    }


def run_live_mining(
    df_onehot: pd.DataFrame,
    min_support: float = 0.01,
    min_confidence: float = 0.3,
    min_lift: float = 1.2,
    max_len: int = 4,
    algorithm: str = "fpgrowth",
    top_n: int = MAX_RULES_RETURNED,
    sort_by: str = "lift",
) -> Dict[str, Any]:
    """
    Mine rules on demand and return a JSON-ready payload with timing diagnostics.

    Defaults mirror `mine_association_rules` so a sandbox run and a batch run at
    the same thresholds return the same rules -- the parity asserted by
    `tests/integration/test_sandbox_parity.py`.
    """
    started = time.perf_counter()

    itemsets_df, rules_df = mine_association_rules(
        df_onehot=df_onehot,
        min_support=min_support,
        min_confidence=min_confidence,
        metric="lift",
        min_metric_val=min_lift,
        max_len=max_len,
        algorithm=algorithm,
    )

    mining_ms = (time.perf_counter() - started) * 1000.0

    if not rules_df.empty:
        rules_df = compute_composite_scores(rules_df)
        rules_df = categorize_rules(rules_df)

        sort_column = sort_by if sort_by in rules_df.columns else "lift"
        rules_df = rules_df.sort_values(sort_column, ascending=False).reset_index(drop=True)

    total_rules = int(len(rules_df))
    trimmed = rules_df.head(top_n) if not rules_df.empty else rules_df

    rules: List[Dict[str, Any]] = []
    for position, (_, row) in enumerate(trimmed.iterrows(), start=1):
        rules.append(
            {
                "id": int(row.get("id", position) or position),
                "rank": position,
                "antecedents": list(row["antecedents"]),
                "consequents": list(row["consequents"]),
                "support": round(float(row.get("support", 0.0)), 6),
                "confidence": round(float(row.get("confidence", 0.0)), 6),
                "lift": round(float(row.get("lift", 0.0)), 6),
                "leverage": round(float(row.get("leverage", 0.0)), 6),
                "conviction": round(float(row.get("conviction", 0.0)), 6),
                "zhangs_metric": round(float(row.get("zhangs_metric", 0.0)), 6),
                "kulczynski": round(float(row.get("kulczynski", 0.0)), 6),
                "imbalance_ratio": round(float(row.get("imbalance_ratio", 0.0)), 6),
                "cosine": round(float(row.get("cosine", 0.0)), 6),
                "composite_score": round(float(row.get("composite_score", 0.0) or 0.0), 4),
                "rule_category": str(row.get("rule_category", "General Association")),
            }
        )

    itemsets_by_length: Dict[str, int] = {}
    if not itemsets_df.empty and "length" in itemsets_df.columns:
        for length, count in itemsets_df["length"].value_counts().sort_index().items():
            itemsets_by_length[f"k={int(length)}"] = int(count)

    elapsed_ms = (time.perf_counter() - started) * 1000.0

    return {
        "status": "success",
        "parameters": {
            "algorithm": algorithm,
            "min_support": min_support,
            "min_confidence": min_confidence,
            "min_lift": min_lift,
            "max_len": max_len,
        },
        "rules": rules,
        "rules_count": total_rules,
        "returned_count": len(rules),
        "truncated": total_rules > len(rules),
        "itemsets_count": int(len(itemsets_df)),
        "itemsets_by_length": itemsets_by_length,
        "execution_time_ms": round(elapsed_ms, 3),
        "mining_time_ms": round(mining_ms, 3),
        "transactions": int(len(df_onehot)),
        "items": int(df_onehot.shape[1]) if len(df_onehot) else 0,
        "metrics": _aggregate_metrics(rules_df),
    }


def _aggregate_metrics(rules_df: pd.DataFrame) -> Dict[str, float]:
    """Headline averages over a mined rule set, for the sandbox diagnostics strip."""
    if rules_df is None or rules_df.empty:
        return {"avg_support": 0.0, "avg_confidence": 0.0, "avg_lift": 0.0, "max_lift": 0.0}

    return {
        "avg_support": round(float(rules_df["support"].mean()), 6),
        "avg_confidence": round(float(rules_df["confidence"].mean()), 6),
        "avg_lift": round(float(rules_df["lift"].mean()), 6),
        "max_lift": round(float(rules_df["lift"].max()), 6),
    }


class TransactionCorpus:
    """
    Lazily-loaded, process-wide transaction matrix for the sandbox.

    Loading and cleaning the corpus costs a second or two, which is fine once but
    unacceptable per keystroke, so the encoded matrix is built on first use and
    reused for the life of the server.
    """

    def __init__(self, dataset_name: str = "synthetic", country: str = "all"):
        self.dataset_name = dataset_name
        self.country = country
        self._onehot: Optional[pd.DataFrame] = None
        self._metadata: Dict[str, Any] = {}

    def load(self) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """Return the one-hot matrix and its metadata, loading it on first call."""
        if self._onehot is not None:
            return self._onehot, self._metadata

        logger.info(f"Sandbox: loading transaction corpus '{self.dataset_name}'...")
        dataset = load_dataset(name_or_path=self.dataset_name)
        cleaned = clean_retail_data(
            df=dataset.raw_df,
            drop_cancellations=True,
            min_basket_size=2,
            country=self.country,
        )

        self._onehot = cleaned.onehot_df
        self._metadata = {
            "dataset_name": dataset.name,
            "transactions": int(len(cleaned.onehot_df)),
            "items": int(cleaned.onehot_df.shape[1]) if len(cleaned.onehot_df) else 0,
            "density_pct": round(float(cleaned.matrix_density_pct), 4),
        }
        logger.info(
            f"Sandbox corpus ready: {self._metadata['transactions']} baskets "
            f"x {self._metadata['items']} items."
        )
        return self._onehot, self._metadata

    def reset(self) -> None:
        """Drop the cached corpus so the next request reloads it from disk."""
        self._onehot = None
        self._metadata = {}
