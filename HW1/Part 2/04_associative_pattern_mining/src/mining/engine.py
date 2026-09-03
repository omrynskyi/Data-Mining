"""
Unified Mining Engine Facade for Associative Pattern Mining.
Orchestrates Apriori and FP-Growth frequent itemset discovery and rule extraction.
"""

from typing import Any, Dict, List, Optional, Tuple, Union
import pandas as pd

from src.mining.apriori import apriori
from src.mining.fpgrowth import fpgrowth
from src.mining.rules import generate_association_rules
from src.utils.logger import get_logger
from src.utils.timer import Timer

logger = get_logger("crisp_dm.engine")


def mine_frequent_itemsets(
    df_onehot: pd.DataFrame,
    min_support: float = 0.01,
    algorithm: str = "fpgrowth",
    max_len: Optional[int] = 4,
    engine: str = "auto",
) -> pd.DataFrame:
    """
    Mine frequent itemsets using Apriori or FP-Growth.

    Parameters:
    -----------
    df_onehot : pd.DataFrame
        One-hot encoded boolean transactions DataFrame.
    min_support : float
        Minimum support threshold.
    algorithm : str
        'fpgrowth', 'apriori', or 'custom_fpgrowth'.
    max_len : Optional[int]
        Maximum itemset size.
    engine : str
        'auto', 'mlxtend', or 'custom'.

    Returns:
    --------
    pd.DataFrame with columns ['support', 'itemsets', 'length'].
    """
    algo = algorithm.lower().strip()

    if algo in ["apriori", "apr"]:
        logger.info(f"Mining frequent itemsets using Apriori (min_support={min_support}, max_len={max_len})...")
        itemsets_df = apriori(df_onehot, min_support=min_support, max_len=max_len, use_colnames=True)
    else:
        logger.info(f"Mining frequent itemsets using FP-Growth (min_support={min_support}, max_len={max_len}, engine={engine})...")
        itemsets_df = fpgrowth(df_onehot, min_support=min_support, max_len=max_len, use_colnames=True, engine=engine)

    logger.info(f"Discovered {len(itemsets_df)} frequent itemsets.")
    return itemsets_df


def mine_association_rules(
    df_onehot: pd.DataFrame,
    min_support: float = 0.01,
    min_confidence: float = 0.3,
    metric: str = "lift",
    min_metric_val: float = 1.2,
    max_len: Optional[int] = 4,
    algorithm: str = "fpgrowth",
    engine: str = "auto",
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    End-to-end mining of frequent itemsets and association rules with 9 metrics.

    Returns:
    --------
    Tuple[pd.DataFrame, pd.DataFrame] -> (itemsets_df, rules_df)
    """
    itemsets_df = mine_frequent_itemsets(
        df_onehot=df_onehot,
        min_support=min_support,
        algorithm=algorithm,
        max_len=max_len,
        engine=engine,
    )

    logger.info(
        f"Extracting association rules (min_confidence={min_confidence}, filter={metric}>={min_metric_val})..."
    )
    rules_df = generate_association_rules(
        frequent_itemsets_df=itemsets_df,
        min_confidence=min_confidence,
        metric=metric,
        min_metric_val=min_metric_val,
    )

    logger.info(f"Generated {len(rules_df)} association rules.")
    return itemsets_df, rules_df


def compare_algorithms(
    df_onehot: pd.DataFrame,
    min_support: float = 0.01,
    max_len: Optional[int] = 4,
) -> Dict[str, Any]:
    """Benchmark Apriori vs FP-Growth runtime and output equivalence."""
    timer_apriori = Timer("Apriori")
    with timer_apriori:
        apriori_itemsets = apriori(df_onehot, min_support=min_support, max_len=max_len)

    timer_fpgrowth = Timer("FP-Growth")
    with timer_fpgrowth:
        fpgrowth_itemsets = fpgrowth(df_onehot, min_support=min_support, max_len=max_len)

    # Check set equivalence
    set_apr = {frozenset(s) for s in apriori_itemsets["itemsets"]}
    set_fp = {frozenset(s) for s in fpgrowth_itemsets["itemsets"]}
    is_identical = (set_apr == set_fp)

    return {
        "apriori_time_ms": round(timer_apriori.elapsed_ms, 2),
        "fpgrowth_time_ms": round(timer_fpgrowth.elapsed_ms, 2),
        "speedup_factor": round(timer_apriori.elapsed_seconds / max(1e-6, timer_fpgrowth.elapsed_seconds), 2),
        "apriori_itemset_count": len(apriori_itemsets),
        "fpgrowth_itemset_count": len(fpgrowth_itemsets),
        "itemsets_identical": is_identical,
    }
