"""
FP-Growth Frequent Itemset Mining Algorithm.
Includes native high-performance FP-Tree implementation and mlxtend adapter.
"""

from collections import defaultdict
from typing import Dict, FrozenSet, List, Optional, Set, Tuple, Union
import numpy as np
import pandas as pd

from src.utils.logger import get_logger

logger = get_logger("crisp_dm.fpgrowth")


class FPNode:
    """Node in an FP-Tree."""

    def __init__(self, item: Optional[str], count: int, parent: Optional["FPNode"]):
        self.item = item
        self.count = count
        self.parent = parent
        self.children: Dict[str, "FPNode"] = {}
        self.node_link: Optional["FPNode"] = None

    def increment(self, count: int = 1) -> None:
        self.count += count


class FPTree:
    """Frequent Pattern Tree."""

    def __init__(self):
        self.root = FPNode(item=None, count=0, parent=None)
        self.header_table: Dict[str, List[Union[int, Optional[FPNode]]]] = {}

    def insert_transaction(self, transaction: List[str], count: int = 1) -> None:
        curr_node = self.root
        for item in transaction:
            if item in curr_node.children:
                curr_node.children[item].increment(count)
            else:
                new_node = FPNode(item=item, count=count, parent=curr_node)
                curr_node.children[item] = new_node

                # Update header table linked list
                if self.header_table[item][1] is None:
                    self.header_table[item][1] = new_node
                else:
                    head = self.header_table[item][1]
                    while head.node_link is not None:
                        head = head.node_link
                    head.node_link = new_node

            curr_node = curr_node.children[item]


def _build_fp_tree(
    transactions: List[Tuple[List[str], int]],
    min_count: int,
) -> Tuple[Optional[FPTree], Dict[str, int]]:
    """Build the initial FP-Tree from transactions and filter infrequent items."""
    # Count 1-itemset frequencies
    item_counts: Dict[str, int] = defaultdict(int)
    for trans, count in transactions:
        for item in trans:
            item_counts[item] += count

    # Filter infrequent items
    frequent_items = {k: v for k, v in item_counts.items() if v >= min_count}
    if not frequent_items:
        return None, {}

    # Initialize FP-Tree and header table
    tree = FPTree()
    for item, count in frequent_items.items():
        tree.header_table[item] = [count, None]

    # Insert transactions with items sorted descending by frequency
    for trans, count in transactions:
        filtered_trans = [item for item in trans if item in frequent_items]
        # Sort by frequency descending, then alphabetically for deterministic tree structure
        filtered_trans.sort(key=lambda item: (-frequent_items[item], item))
        if filtered_trans:
            tree.insert_transaction(filtered_trans, count)

    return tree, frequent_items


def _mine_fp_tree(
    tree: FPTree,
    min_count: int,
    prefix: Set[str],
    frequent_itemsets: Dict[FrozenSet[str], int],
    max_len: Optional[int] = None,
) -> None:
    """Recursively mine frequent itemsets from FP-Tree."""
    # Sort items in header table ascending by frequency (bottom-up mining)
    sorted_items = sorted(tree.header_table.items(), key=lambda x: (x[1][0], x[0]))

    for item, (count, node) in sorted_items:
        new_itemset = prefix | {item}
        if max_len is not None and len(new_itemset) > max_len:
            continue

        frequent_itemsets[frozenset(new_itemset)] = count

        # Collect prefix paths (conditional pattern base)
        conditional_patterns: List[Tuple[List[str], int]] = []
        curr_node = node
        while curr_node is not None:
            # Ascend to root to collect prefix path
            prefix_path = []
            path_parent = curr_node.parent
            while path_parent is not None and path_parent.item is not None:
                prefix_path.append(path_parent.item)
                path_parent = path_parent.parent

            if prefix_path:
                conditional_patterns.append((prefix_path, curr_node.count))
            curr_node = curr_node.node_link

        # Build conditional FP-Tree
        cond_tree, cond_items = _build_fp_tree(conditional_patterns, min_count)
        if cond_tree is not None:
            _mine_fp_tree(cond_tree, min_count, new_itemset, frequent_itemsets, max_len=max_len)


def fpgrowth_custom(
    df: pd.DataFrame,
    min_support: float = 0.01,
    max_len: Optional[int] = None,
    use_colnames: bool = True,
) -> pd.DataFrame:
    """Native pure-Python implementation of FP-Growth."""
    if df.empty:
        return pd.DataFrame(columns=["support", "itemsets", "length"])

    num_transactions = len(df)
    min_count = int(np.ceil(min_support * num_transactions))
    col_names = list(df.columns)

    # Convert boolean DataFrame into list of transaction item lists
    matrix = df.values.astype(bool)
    transactions: List[Tuple[List[str], int]] = []
    for row in matrix:
        items = [col_names[idx] if use_colnames else str(idx) for idx in np.where(row)[0]]
        if items:
            transactions.append((items, 1))

    tree, freq_items = _build_fp_tree(transactions, min_count)
    if tree is None:
        return pd.DataFrame(columns=["support", "itemsets", "length"])

    frequent_itemsets: Dict[FrozenSet[str], int] = {}
    _mine_fp_tree(tree, min_count, set(), frequent_itemsets, max_len=max_len)

    records = []
    for itemset, count in frequent_itemsets.items():
        supp = count / num_transactions
        records.append({"support": supp, "itemsets": itemset, "length": len(itemset)})

    res_df = pd.DataFrame(records)
    if res_df.empty:
        return pd.DataFrame(columns=["support", "itemsets", "length"])

    res_df = res_df.sort_values(by=["support", "length"], ascending=[False, True]).reset_index(drop=True)
    return res_df


def fpgrowth(
    df: pd.DataFrame,
    min_support: float = 0.01,
    max_len: Optional[int] = None,
    use_colnames: bool = True,
    engine: str = "auto",
) -> pd.DataFrame:
    """
    FP-Growth algorithm interface with automatic fallback between mlxtend and native implementation.

    Parameters:
    -----------
    df : pd.DataFrame
        One-hot encoded boolean DataFrame.
    min_support : float
        Minimum support threshold.
    max_len : Optional[int]
        Maximum length of itemsets.
    use_colnames : bool
        If True, return item names.
    engine : str
        'auto', 'mlxtend', or 'custom'.
    """
    if engine in ["auto", "mlxtend"]:
        try:
            import mlxtend.frequent_patterns as fp
            res = fp.fpgrowth(df, min_support=min_support, use_colnames=use_colnames, max_len=max_len)
            if not res.empty:
                res["length"] = res["itemsets"].apply(len)
                res = res.sort_values(by=["support", "length"], ascending=[False, True]).reset_index(drop=True)
            else:
                res["length"] = pd.Series(dtype=int)
            return res
        except Exception as e:
            if engine == "mlxtend":
                logger.warning(f"mlxtend fpgrowth failed ({e}), falling back to custom FP-Growth.")

    return fpgrowth_custom(df, min_support=min_support, max_len=max_len, use_colnames=use_colnames)
