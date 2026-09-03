"""
Association Rule Extraction and Metric Enrichment.
Extracts rules (A -> C) from frequent itemsets and computes the complete 9-metric evaluation suite.
"""

from itertools import combinations
from typing import Any, Dict, FrozenSet, List, Optional, Set, Tuple, Union
import numpy as np
import pandas as pd

from config import CONVICTION_MAX_CAP
from src.mining.metrics import compute_all_metrics
from src.utils.logger import get_logger

logger = get_logger("crisp_dm.rules")


def generate_association_rules(
    frequent_itemsets_df: pd.DataFrame,
    min_confidence: float = 0.3,
    metric: str = "lift",
    min_metric_val: float = 1.0,
) -> pd.DataFrame:
    """
    Extract association rules (A -> C) from frequent itemsets and calculate all 9 metrics.

    Parameters:
    -----------
    frequent_itemsets_df : pd.DataFrame
        DataFrame with 'support' and 'itemsets' (frozenset).
    min_confidence : float
        Minimum confidence threshold.
    metric : str
        Primary metric to filter by (e.g. 'lift', 'confidence', 'support', 'zhangs_metric').
    min_metric_val : float
        Minimum threshold value for the primary metric.

    Returns:
    --------
    pd.DataFrame containing association rules and 9 metrics.
    """
    if frequent_itemsets_df.empty:
        return pd.DataFrame(columns=[
            "id", "antecedents", "consequents", "antecedent_support", "consequent_support",
            "support", "confidence", "lift", "leverage", "conviction",
            "zhangs_metric", "kulczynski", "imbalance_ratio", "cosine"
        ])

    # Build fast support lookup dictionary: frozenset -> support float
    support_lookup: Dict[FrozenSet[str], float] = {
        frozenset(row["itemsets"]): float(row["support"])
        for _, row in frequent_itemsets_df.iterrows()
    }

    rules_records: List[Dict[str, Any]] = []
    rule_id = 1

    # Filter itemsets of length >= 2
    multi_itemsets = [
        (frozenset(row["itemsets"]), float(row["support"]))
        for _, row in frequent_itemsets_df.iterrows()
        if len(row["itemsets"]) >= 2
    ]

    for itemset, joint_support in multi_itemsets:
        k = len(itemset)
        items_list = list(itemset)

        # Generate all non-empty proper subsets as antecedents
        for r in range(1, k):
            for ant_tuple in combinations(items_list, r):
                ant = frozenset(ant_tuple)
                con = itemset - ant

                ant_supp = support_lookup.get(ant)
                con_supp = support_lookup.get(con)

                if ant_supp is None or con_supp is None:
                    continue

                conf = joint_support / ant_supp if ant_supp > 0 else 0.0
                if conf < min_confidence:
                    continue

                metrics_dict = compute_all_metrics(
                    joint_support=joint_support,
                    antecedent_support=ant_supp,
                    consequent_support=con_supp,
                )

                # Check primary metric filter
                metric_key = metric.lower().strip()
                current_metric_val = metrics_dict.get(metric_key, metrics_dict["lift"])
                if current_metric_val < min_metric_val:
                    continue

                rules_records.append({
                    "id": rule_id,
                    "antecedents": sorted(list(ant)),
                    "consequents": sorted(list(con)),
                    "antecedent_support": round(ant_supp, 6),
                    "consequent_support": round(con_supp, 6),
                    "support": metrics_dict["support"],
                    "confidence": metrics_dict["confidence"],
                    "lift": metrics_dict["lift"],
                    "leverage": metrics_dict["leverage"],
                    "conviction": metrics_dict["conviction"],
                    "zhangs_metric": metrics_dict["zhangs_metric"],
                    "kulczynski": metrics_dict["kulczynski"],
                    "imbalance_ratio": metrics_dict["imbalance_ratio"],
                    "cosine": metrics_dict["cosine"],
                })
                rule_id += 1

    if not rules_records:
        return pd.DataFrame(columns=[
            "id", "antecedents", "consequents", "antecedent_support", "consequent_support",
            "support", "confidence", "lift", "leverage", "conviction",
            "zhangs_metric", "kulczynski", "imbalance_ratio", "cosine"
        ])

    rules_df = pd.DataFrame(rules_records)

    # Sort rules descending by primary metric, then confidence, then support
    sort_cols = [metric.lower().strip()]
    if sort_cols[0] not in rules_df.columns:
        sort_cols = ["lift"]
    if "confidence" not in sort_cols:
        sort_cols.append("confidence")
    if "support" not in sort_cols:
        sort_cols.append("support")

    rules_df = rules_df.sort_values(by=sort_cols, ascending=[False] * len(sort_cols)).reset_index(drop=True)
    # Re-assign sequential IDs after sorting
    rules_df["id"] = list(range(1, len(rules_df) + 1))
    return rules_df
