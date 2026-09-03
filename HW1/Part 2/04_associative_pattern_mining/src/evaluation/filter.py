"""
Multi-Metric Rule Filtering, Composite Quality Scoring, and Business Categorization.
"""

from typing import Any, Dict, List, Optional
import numpy as np
import pandas as pd

from src.utils.logger import get_logger

logger = get_logger("crisp_dm.filter")


def compute_composite_scores(
    rules_df: pd.DataFrame,
    w_lift: float = 0.40,
    w_conf: float = 0.30,
    w_zhang: float = 0.20,
    w_supp: float = 0.10,
) -> pd.DataFrame:
    """
    Calculate normalized composite quality score across multiple interest metrics.

    CompositeScore = w_lift * norm(lift) + w_conf * norm(conf) + w_zhang * norm(zhang) + w_supp * norm(supp)
    """
    if rules_df.empty:
        df = rules_df.copy()
        df["composite_score"] = pd.Series(dtype=float)
        return df

    df = rules_df.copy()

    # Lift normalization (min=1.0)
    lift_vals = df["lift"].values
    max_lift = np.max(lift_vals) if len(lift_vals) > 0 else 1.0
    norm_lift = (lift_vals - 1.0) / max(1e-6, max_lift - 1.0)
    norm_lift = np.clip(norm_lift, 0.0, 1.0)

    # Confidence normalization (already [0, 1])
    norm_conf = np.clip(df["confidence"].values, 0.0, 1.0)

    # Zhang's metric normalization (from [-1, 1] to [0, 1])
    zhang_vals = df["zhangs_metric"].values
    norm_zhang = (zhang_vals + 1.0) / 2.0
    norm_zhang = np.clip(norm_zhang, 0.0, 1.0)

    # Support normalization
    supp_vals = df["support"].values
    max_supp = np.max(supp_vals) if len(supp_vals) > 0 else 1.0
    norm_supp = supp_vals / max(1e-6, max_supp)
    norm_supp = np.clip(norm_supp, 0.0, 1.0)

    composite = (
        w_lift * norm_lift +
        w_conf * norm_conf +
        w_zhang * norm_zhang +
        w_supp * norm_supp
    )
    df["composite_score"] = np.round(composite, 4)
    return df


def categorize_rules(rules_df: pd.DataFrame) -> pd.DataFrame:
    """
    Assign actionable business categories to mined association rules.

    Categories:
    - High-Confidence Cross-Sells (conf >= 0.6, lift >= 1.5)
    - High-Lift Affinity Pairs (lift >= 3.0, conf >= 0.3)
    - Emerging Niche Bundles (supp < 0.05, lift >= 2.0, conf >= 0.4)
    - Strong Symmetric Associations (kulczynski >= 0.6, imbalance_ratio <= 0.3)
    - General Association (remaining rules)
    """
    if rules_df.empty:
        df = rules_df.copy()
        df["rule_category"] = pd.Series(dtype=str)
        return df

    df = rules_df.copy()
    categories = []

    for _, row in df.iterrows():
        conf = row.get("confidence", 0.0)
        lift = row.get("lift", 0.0)
        supp = row.get("support", 0.0)
        kulc = row.get("kulczynski", 0.0)
        ir = row.get("imbalance_ratio", 1.0)

        if conf >= 0.60 and lift >= 1.5:
            cat = "High-Confidence Cross-Sell"
        elif lift >= 3.0 and conf >= 0.30:
            cat = "High-Lift Affinity Pair"
        elif supp < 0.05 and lift >= 2.0 and conf >= 0.40:
            cat = "Emerging Niche Bundle"
        elif kulc >= 0.60 and ir <= 0.30:
            cat = "Strong Symmetric Association"
        else:
            cat = "General Association"

        categories.append(cat)

    df["rule_category"] = categories
    return df


def filter_rules(
    rules_df: pd.DataFrame,
    min_support: Optional[float] = None,
    min_confidence: Optional[float] = None,
    min_lift: Optional[float] = None,
    min_zhang: Optional[float] = None,
    min_kulczynski: Optional[float] = None,
    max_imbalance_ratio: Optional[float] = None,
    min_cosine: Optional[float] = None,
    top_n: Optional[int] = None,
) -> pd.DataFrame:
    """
    Apply multi-metric thresholds to association rules.
    """
    if rules_df.empty:
        return rules_df

    filtered = rules_df.copy()

    if min_support is not None:
        filtered = filtered[filtered["support"] >= min_support]
    if min_confidence is not None:
        filtered = filtered[filtered["confidence"] >= min_confidence]
    if min_lift is not None:
        filtered = filtered[filtered["lift"] >= min_lift]
    if min_zhang is not None:
        filtered = filtered[filtered["zhangs_metric"] >= min_zhang]
    if min_kulczynski is not None:
        filtered = filtered[filtered["kulczynski"] >= min_kulczynski]
    if max_imbalance_ratio is not None:
        filtered = filtered[filtered["imbalance_ratio"] <= max_imbalance_ratio]
    if min_cosine is not None:
        filtered = filtered[filtered["cosine"] >= min_cosine]

    if top_n is not None and top_n > 0:
        filtered = filtered.head(top_n)

    return filtered.reset_index(drop=True)


def _as_item_set(value: Any) -> set:
    """
    Coerce a rule's antecedent/consequent cell into a set of item labels.

    Rules arrive from three routes -- in-memory DataFrames (real lists), a JSON
    artifact (lists), and a CSV artifact (a string such as "['milk', 'bread']"
    or "milk, bread") -- so the accessor has to tolerate all three.
    """
    if isinstance(value, (list, set, frozenset, tuple)):
        return {str(v).strip() for v in value}

    if value is None:
        return set()

    text = str(value).strip()
    if not text:
        return set()

    # Bracketed repr of a Python list, as produced by DataFrame.to_csv.
    if text.startswith("[") and text.endswith("]"):
        inner = text[1:-1]
        return {
            part.strip().strip("'\"")
            for part in inner.split(",")
            if part.strip().strip("'\"")
        }

    return {part.strip() for part in text.split(",") if part.strip()}


def generate_recommendations(
    cart: List[str],
    rules_df: pd.DataFrame,
    top_n: int = 10,
    min_confidence: float = 0.0,
    min_lift: float = 1.0,
) -> List[Dict[str, Any]]:
    """
    Recommend next-basket items for a shopping cart from mined association rules.

    A rule fires when its entire antecedent is already in the cart; its consequent
    items then become candidates. Items already in the cart are never recommended,
    and when several rules propose the same item the strongest one wins, so each
    item appears once with the evidence that justified it.

    Candidates are ranked by confidence (how reliably the rule holds) and then by
    lift (how much the rule beats chance), which puts dependable recommendations
    above merely surprising ones.

    Parameters
    ----------
    cart : List[str]
        Items currently in the basket.
    rules_df : pd.DataFrame
        Mined rules carrying at least `antecedents`, `consequents`, `confidence`.
    top_n : int
        Maximum number of recommendations to return.
    min_confidence, min_lift : float
        Thresholds a rule must clear before it may recommend anything.

    Returns
    -------
    List[Dict[str, Any]] : ranked recommendations, best first.
    """
    cart_items = {str(item).strip() for item in (cart or []) if str(item).strip()}
    if not cart_items or rules_df is None or len(rules_df) == 0:
        return []

    best_by_item: Dict[str, Dict[str, Any]] = {}

    for _, row in rules_df.iterrows():
        confidence = float(row.get("confidence", 0.0) or 0.0)
        lift = float(row.get("lift", 0.0) or 0.0)
        if confidence < min_confidence or lift < min_lift:
            continue

        antecedents = _as_item_set(row.get("antecedents"))
        if not antecedents or not antecedents.issubset(cart_items):
            continue

        for item in _as_item_set(row.get("consequents")):
            if item in cart_items:
                continue

            candidate = {
                "item": item,
                "confidence": round(confidence, 6),
                "lift": round(lift, 6),
                "support": round(float(row.get("support", 0.0) or 0.0), 6),
                "matched_antecedents": sorted(antecedents),
                "rule": f"{{{', '.join(sorted(antecedents))}}} -> {{{item}}}",
            }

            incumbent = best_by_item.get(item)
            if incumbent is None or (candidate["confidence"], candidate["lift"]) > (
                incumbent["confidence"],
                incumbent["lift"],
            ):
                best_by_item[item] = candidate

    ranked = sorted(
        best_by_item.values(),
        key=lambda rec: (rec["confidence"], rec["lift"]),
        reverse=True,
    )

    for position, recommendation in enumerate(ranked, start=1):
        recommendation["rank"] = position

    return ranked[: max(0, int(top_n))]
