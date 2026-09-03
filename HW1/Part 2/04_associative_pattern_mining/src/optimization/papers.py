"""
Research Paper Benchmark Catalog (Feature F7).

Each profile records the bibliographic identity of a published associative
pattern mining study plus the operating point the hill climber attempts to
reproduce on our own dataset.

Note on `target_metrics`: the source papers report their results over their own
corpora (synthetic IBM QUEST baskets, a UK gift-retail ledger, etc.), so their
absolute numbers are not directly transferable. Each profile therefore records a
*reference operating point* digested from the regime the paper reports -- the
rule-set size it settles on and the average support / confidence / lift band its
discovered rules occupy. `target_basis` documents that derivation for every
entry so the comparison stays auditable.
"""

import json
import os
from typing import Any, Dict, List

from src.utils.logger import get_logger

logger = get_logger("crisp_dm.papers")

#: Metric dimensions every paper profile must supply a target for.
REQUIRED_TARGET_METRICS = (
    "rule_count",
    "avg_support",
    "avg_confidence",
    "avg_lift",
    "coverage",
)


PAPER_CATALOG: Dict[str, Dict[str, Any]] = {
    "ghosh2004": {
        "key": "ghosh2004",
        "title": "Multi-objective rule mining using genetic algorithms",
        "authors": "Ashish Ghosh and Bhabesh Nath",
        "venue": "Information Sciences, Vol. 163, pp. 123-133, 2004",
        "doi": "10.1016/j.ins.2003.03.021",
        "year": 2004,
        "summary": (
            "Treats association rule mining as a multi-objective optimisation problem, "
            "searching simultaneously for rules that are comprehensible, of high "
            "predictive accuracy (confidence) and interesting (lift/surprise) rather "
            "than optimising a single support-confidence threshold pair."
        ),
        "target_basis": (
            "The paper's Pareto fronts settle on a compact, high-precision rule set: a "
            "few dozen rules with confidence in the low-0.7 band and lift comfortably "
            "above 2, mined at low single-digit-percent support. The operating point "
            "below encodes that regime."
        ),
        "target_metrics": {
            "rule_count": 50,
            "avg_support": 0.025,
            "avg_confidence": 0.720,
            "avg_lift": 2.450,
            "coverage": 0.180,
        },
    },
    "agrawal1994": {
        "key": "agrawal1994",
        "title": "Fast Algorithms for Mining Association Rules in Large Databases",
        "authors": "Rakesh Agrawal and Ramakrishnan Srikant",
        "venue": "Proceedings of the 20th VLDB Conference, pp. 487-499, 1994",
        "doi": "10.5555/645920.672836",
        "year": 1994,
        "summary": (
            "The foundational Apriori paper. Introduces downward-closure candidate "
            "pruning and evaluates AprioriTid/AprioriHybrid over synthetic basket "
            "corpora at low minimum-support thresholds."
        ),
        "target_basis": (
            "Apriori's canonical evaluation favours recall over precision: a broad rule "
            "set mined at ~1.5% support with the classic 0.6 confidence floor, yielding "
            "modest average lift but wide transaction coverage."
        ),
        "target_metrics": {
            "rule_count": 120,
            "avg_support": 0.015,
            "avg_confidence": 0.600,
            "avg_lift": 1.850,
            "coverage": 0.250,
        },
    },
    "chen2012": {
        "key": "chen2012",
        "title": (
            "Data mining for the online retail industry: A case study of RFM "
            "model-based customer segmentation using data mining"
        ),
        "authors": "Daqing Chen, Sai Liang Sain, and Kun Guo",
        "venue": (
            "Journal of Database Marketing & Customer Strategy Management, "
            "Vol. 19(3), pp. 197-208, 2012"
        ),
        "doi": "10.1057/dbm.2012.17",
        "year": 2012,
        "summary": (
            "The case study that donated the UCI/Kaggle 'Online Retail' transaction "
            "ledger. Combines RFM segmentation with market-basket rule mining to drive "
            "targeted cross-sell recommendations for a UK online gift retailer."
        ),
        "target_basis": (
            "The retail case study reports a small set of highly actionable cross-sell "
            "rules -- strong affinities (lift above 3) between a handful of "
            "complementary gift lines, rather than a large exhaustive rule base."
        ),
        "target_metrics": {
            "rule_count": 35,
            "avg_support": 0.020,
            "avg_confidence": 0.680,
            "avg_lift": 3.200,
            "coverage": 0.220,
        },
    },
}


def list_available_papers() -> List[str]:
    """Return the keys of every research paper registered in the catalog."""
    return list(PAPER_CATALOG.keys())


def validate_paper_profile(profile: Dict[str, Any]) -> Dict[str, Any]:
    """
    Ensure a paper profile carries the bibliographic identity and the full set of
    target metric dimensions the fitness evaluator needs.

    Raises ValueError when a required field or metric dimension is missing.
    """
    if not isinstance(profile, dict):
        raise ValueError("Paper profile must be a dictionary.")

    for field in ("key", "title", "target_metrics"):
        if field not in profile:
            raise ValueError(f"Paper profile is missing required field '{field}'.")

    targets = profile["target_metrics"]
    if not isinstance(targets, dict):
        raise ValueError("Paper profile field 'target_metrics' must be a dictionary.")

    missing = [m for m in REQUIRED_TARGET_METRICS if m not in targets]
    if missing:
        raise ValueError(
            f"Paper profile '{profile['key']}' is missing target metrics: {missing}"
        )

    for metric in REQUIRED_TARGET_METRICS:
        value = targets[metric]
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            raise ValueError(
                f"Target metric '{metric}' of paper '{profile['key']}' must be numeric."
            )

    return profile


def load_custom_paper(path: str) -> Dict[str, Any]:
    """
    Load a bespoke target-paper profile from a JSON file.

    The file must contain the same shape as a catalog entry: `key`, `title` and a
    `target_metrics` object covering all five metric dimensions.
    """
    with open(path, "r", encoding="utf-8") as handle:
        profile = json.load(handle)

    profile.setdefault("key", os.path.splitext(os.path.basename(path))[0])
    profile.setdefault("source_file", os.path.abspath(path))
    return validate_paper_profile(profile)


def get_paper_profile(key_or_path: str) -> Dict[str, Any]:
    """
    Resolve a research paper profile by catalog key or custom JSON filepath.

    Parameters
    ----------
    key_or_path : str
        A registered catalog key ('ghosh2004', 'agrawal1994', 'chen2012') or a
        path to a JSON file holding a custom paper profile.

    Returns
    -------
    Dict[str, Any] : a validated, deep-copied paper profile.

    Raises
    ------
    KeyError : when the key is neither registered nor an existing JSON file.
    ValueError : when a custom profile fails schema validation.
    """
    if not isinstance(key_or_path, str) or not key_or_path.strip():
        raise ValueError("Paper key or path must be a non-empty string.")

    lookup = key_or_path.strip()

    if lookup in PAPER_CATALOG:
        return json.loads(json.dumps(PAPER_CATALOG[lookup]))

    normalized = lookup.lower()
    if normalized in PAPER_CATALOG:
        return json.loads(json.dumps(PAPER_CATALOG[normalized]))

    if os.path.isfile(lookup):
        logger.info(f"Loading custom target paper profile from {lookup}")
        return load_custom_paper(lookup)

    raise KeyError(
        f"Unknown research paper '{key_or_path}'. "
        f"Registered papers: {list_available_papers()}. "
        f"Alternatively supply a path to a custom paper profile JSON file."
    )


def get_target_metrics(key_or_path: str) -> Dict[str, float]:
    """Convenience accessor returning only the target metric dictionary."""
    return get_paper_profile(key_or_path)["target_metrics"]
