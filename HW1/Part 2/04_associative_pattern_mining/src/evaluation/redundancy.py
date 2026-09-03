"""
Redundancy Pruning for Association Rules.

A rule earns its place only if it tells you something its own generalisations do
not. `{bread, butter} -> {milk}` at 0.80 confidence is noise when
`{bread} -> {milk}` already holds at 0.85: the extra condition narrows the
audience without improving the prediction. Pruning these keeps the rule set at a
size a human can actually review.
"""

from typing import Any, Dict, FrozenSet, Iterable, List, Optional, Set, Tuple, Union

import pandas as pd

from src.utils.logger import get_logger

logger = get_logger("crisp_dm.redundancy")


def _as_frozenset(value: Any) -> FrozenSet[str]:
    """Coerce an antecedent/consequent cell into a frozenset of item labels."""
    if isinstance(value, frozenset):
        return value
    if isinstance(value, (list, set, tuple)):
        return frozenset(str(item) for item in value)
    if value is None:
        return frozenset()

    text = str(value).strip()
    if not text:
        return frozenset()
    if text.startswith("[") and text.endswith("]"):
        text = text[1:-1]
    return frozenset(
        part.strip().strip("'\"") for part in text.split(",") if part.strip().strip("'\"")
    )


def is_rule_redundant(
    rule: Union[Dict[str, Any], pd.Series],
    reference_rules: Union[pd.DataFrame, Iterable[Dict[str, Any]]],
    tolerance: float = 0.0,
) -> bool:
    """
    Decide whether `rule` is made redundant by any rule in `reference_rules`.

    `rule` (A' -> C) is redundant when some reference rule (A -> C) shares its
    consequent, has a strictly smaller antecedent (A subset of A'), and is at
    least as confident. In other words the extra conditions in A' buy nothing.

    Parameters
    ----------
    rule : Dict[str, Any] or pd.Series
        The candidate rule, carrying `antecedents`, `consequents`, `confidence`.
    reference_rules : pd.DataFrame or iterable of dicts
        Rules the candidate is judged against. The candidate itself may be
        present; a rule is never redundant against itself.
    tolerance : float
        Confidence margin the candidate must clear to survive. At 0.0 a
        candidate must strictly beat its generalisation; raise it to demand a
        material improvement before a longer rule is kept.

    Returns
    -------
    bool : True when a simpler, at-least-as-confident rule exists.
    """
    antecedent = _as_frozenset(rule.get("antecedents") if hasattr(rule, "get") else rule["antecedents"])
    consequent = _as_frozenset(rule.get("consequents") if hasattr(rule, "get") else rule["consequents"])
    confidence = float(rule.get("confidence", 0.0) if hasattr(rule, "get") else rule["confidence"])

    if len(antecedent) <= 1:
        # A single-item antecedent has no strict non-empty subset, so nothing
        # can generalise it.
        return False

    records: Iterable[Any]
    if isinstance(reference_rules, pd.DataFrame):
        if reference_rules.empty:
            return False
        records = (row for _, row in reference_rules.iterrows())
    else:
        records = reference_rules

    for other in records:
        other_antecedent = _as_frozenset(other["antecedents"])
        if not (other_antecedent < antecedent):
            continue
        if _as_frozenset(other["consequents"]) != consequent:
            continue
        if confidence <= float(other["confidence"]) + tolerance:
            return True

    return False


def prune_redundant_rules(
    rules_df: pd.DataFrame,
    tolerance: float = 0.0,
    return_stats: bool = False,
) -> Union[pd.DataFrame, Tuple[pd.DataFrame, int]]:
    """
    Remove rules that a simpler, at-least-as-confident rule already covers.

    Rules are grouped by consequent and scanned in order of antecedent size, so
    each rule is only ever compared against genuine generalisations. A rule
    already marked redundant cannot itself prune anything -- otherwise a chain of
    weak rules could eliminate a strong one it never actually dominated.

    Parameters
    ----------
    rules_df : pd.DataFrame
        Mined association rules.
    tolerance : float
        Confidence margin a longer rule must clear to be retained.
    return_stats : bool
        When True, also return how many rules were pruned.

    Returns
    -------
    pd.DataFrame, or (pd.DataFrame, int) when `return_stats` is set.
    """
    if rules_df is None or rules_df.empty or len(rules_df) <= 1:
        result = rules_df.copy() if rules_df is not None else pd.DataFrame()
        return (result, 0) if return_stats else result

    initial_count = len(rules_df)
    redundant_indices: Set[int] = set()

    # Group by consequent; only rules sharing a consequent can generalise each other.
    by_consequent: Dict[FrozenSet[str], List[Tuple[Any, FrozenSet[str], float]]] = {}
    for idx, row in rules_df.iterrows():
        consequent = _as_frozenset(row["consequents"])
        by_consequent.setdefault(consequent, []).append(
            (idx, _as_frozenset(row["antecedents"]), float(row["confidence"]))
        )

    for rule_group in by_consequent.values():
        # Ascending antecedent size: generalisations are always visited first.
        rule_group.sort(key=lambda entry: len(entry[1]))

        for i, (idx_general, ant_general, conf_general) in enumerate(rule_group):
            if idx_general in redundant_indices:
                continue

            for idx_special, ant_special, conf_special in rule_group[i + 1:]:
                if idx_special in redundant_indices:
                    continue
                if ant_general < ant_special and conf_special <= conf_general + tolerance:
                    redundant_indices.add(idx_special)

    pruned_df = rules_df[[idx not in redundant_indices for idx in rules_df.index]].copy()
    pruned_df = pruned_df.reset_index(drop=True)
    pruned_df["id"] = list(range(1, len(pruned_df) + 1))

    pruned_count = initial_count - len(pruned_df)
    logger.info(
        f"Redundancy pruning: removed {pruned_count} redundant rules "
        f"({len(pruned_df)} retained)."
    )

    return (pruned_df, pruned_count) if return_stats else pruned_df
