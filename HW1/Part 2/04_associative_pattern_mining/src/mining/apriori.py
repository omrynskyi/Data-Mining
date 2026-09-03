"""
Apriori Frequent Itemset Mining Algorithm.
Features downward-closure candidate pruning and vectorized bitwise support counting.
"""

from itertools import combinations
from typing import Dict, FrozenSet, List, Optional, Set, Tuple
import numpy as np
import pandas as pd

from src.utils.logger import get_logger

logger = get_logger("crisp_dm.apriori")


def apriori(
    df: pd.DataFrame,
    min_support: float = 0.01,
    max_len: Optional[int] = None,
    use_colnames: bool = True,
    verbose: int = 0,
) -> pd.DataFrame:
    """
    Find frequent itemsets using the Apriori algorithm.

    Parameters:
    -----------
    df : pd.DataFrame
        One-hot encoded boolean DataFrame (rows=transactions, cols=items).
    min_support : float
        Minimum support threshold between 0.0 and 1.0.
    max_len : Optional[int]
        Maximum length of frequent itemsets to discover.
    use_colnames : bool
        If True, return item names instead of column indices.
    verbose : int
        Verbosity level.

    Returns:
    --------
    pd.DataFrame with columns ['support', 'itemsets', 'length'].
    """
    if df.empty:
        return pd.DataFrame(columns=["support", "itemsets", "length"])

    num_transactions, num_items = df.shape
    min_count = np.ceil(min_support * num_transactions)
    col_names = list(df.columns)

    # Convert DataFrame to 2D numpy boolean array for fast bitwise slicing
    matrix = df.values.astype(bool)

    frequent_itemsets: List[Tuple[float, FrozenSet]] = []

    # Step 1: L1 Frequent 1-itemsets
    item_counts = matrix.sum(axis=0)
    l1_indices = np.where(item_counts >= min_count)[0]

    current_l_sets: Dict[FrozenSet[int], int] = {}
    for idx in l1_indices:
        itemset = frozenset([int(idx)])
        count = int(item_counts[idx])
        supp = count / num_transactions
        current_l_sets[itemset] = count
        name_set = frozenset([col_names[idx]]) if use_colnames else itemset
        frequent_itemsets.append((supp, name_set))

    if verbose > 0:
        logger.info(f"Apriori: Found {len(current_l_sets)} frequent 1-itemsets (min_support={min_support})")

    k = 2
    while current_l_sets and (max_len is None or k <= max_len):
        prev_itemsets = list(current_l_sets.keys())
        prev_set_lookup: Set[FrozenSet[int]] = set(prev_itemsets)

        # Generate C_k candidates via L_{k-1} join
        candidates: Set[FrozenSet[int]] = set()
        n_prev = len(prev_itemsets)

        # Sort itemsets as sorted tuples for standard prefix joining
        sorted_prev = [sorted(list(s)) for s in prev_itemsets]
        sorted_prev.sort()

        for i in range(n_prev):
            for j in range(i + 1, n_prev):
                # Join if first k-2 items match
                if sorted_prev[i][:k - 2] == sorted_prev[j][:k - 2]:
                    cand = frozenset(sorted_prev[i] + [sorted_prev[j][k - 2]])
                    if len(cand) == k:
                        # Downward-closure pruning: all (k-1) subsets must be frequent
                        subsets_frequent = True
                        for sub in combinations(cand, k - 1):
                            if frozenset(sub) not in prev_set_lookup:
                                subsets_frequent = False
                                break
                        if subsets_frequent:
                            candidates.add(cand)
                else:
                    break

        if not candidates:
            break

        # Step 2: Count supports for candidates
        next_l_sets: Dict[FrozenSet[int], int] = {}
        for cand in candidates:
            cand_indices = list(cand)
            # Vectorized bitwise AND across candidate item columns
            mask = matrix[:, cand_indices[0]]
            for c_idx in cand_indices[1:]:
                mask = mask & matrix[:, c_idx]
            count = int(mask.sum())
            if count >= min_count:
                supp = count / num_transactions
                next_l_sets[cand] = count
                name_set = frozenset([col_names[idx] for idx in cand]) if use_colnames else cand
                frequent_itemsets.append((supp, name_set))

        if verbose > 0:
            logger.info(f"Apriori: Found {len(next_l_sets)} frequent {k}-itemsets")

        current_l_sets = next_l_sets
        k += 1

    if not frequent_itemsets:
        return pd.DataFrame(columns=["support", "itemsets", "length"])

    res_df = pd.DataFrame(frequent_itemsets, columns=["support", "itemsets"])
    res_df["length"] = res_df["itemsets"].apply(len)
    res_df = res_df.sort_values(by=["support", "length"], ascending=[False, True]).reset_index(drop=True)
    return res_df
