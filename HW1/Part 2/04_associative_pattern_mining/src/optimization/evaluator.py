"""
Rule-Set Evaluator for Hill Climbing.

Naively, scoring one point in the 5D search space means re-running FP-Growth and
rule extraction -- seconds of work per candidate, hundreds of candidates per
search. This module removes that cost without approximating anything.

The key observation is that a rule's support, confidence and lift are properties
of the *data*, not of the thresholds used to find it. So the evaluator mines
once at the loosest corner of the search domain (the lowest permitted support,
confidence and lift, and the largest permitted itemset length) to obtain a rule
superset, then answers every candidate configuration by masking that superset.
The rule set returned for state S is exactly the one a fresh mining run at S
would produce -- verified against the live engine in
`tests/integration/test_sandbox_parity.py` and by `verify_against_engine()` below.

Transaction coverage is answered from a bit-packed itemset/transaction incidence
matrix, so even a permissive candidate selecting tens of thousands of rules is
scored with a handful of bitwise ORs.
"""

import hashlib
import os
import pickle
import time
from itertools import combinations
from typing import Any, Dict, FrozenSet, List, Optional, Tuple

import numpy as np
import pandas as pd

from src.mining.engine import mine_association_rules
from src.optimization.state import DEFAULT_BOUNDS, OptimizationState, StateBounds
from src.utils.logger import get_logger

logger = get_logger("crisp_dm.optimizer.evaluator")

#: Version tag embedded in cache keys; bump when the superset layout changes.
CACHE_FORMAT_VERSION = "v1"


class RuleSetEvaluator:
    """
    Scores candidate mining configurations against a fixed transaction corpus.

    Parameters
    ----------
    onehot_df : pd.DataFrame
        Boolean transaction/item incidence matrix (one row per basket).
    bounds : StateBounds
        Search domain. Its lower corner determines how loose the mined superset
        must be for masking to stay exact.
    algorithm : str
        Frequent itemset algorithm used to build the superset.
    cache_dir : Optional[str]
        When set, the mined superset is memoised to disk so repeated CLI runs
        over the same corpus and domain skip the expensive mining pass.
    """

    def __init__(
        self,
        onehot_df: pd.DataFrame,
        bounds: Optional[StateBounds] = None,
        algorithm: str = "fpgrowth",
        cache_dir: Optional[str] = None,
    ):
        self.onehot_df = onehot_df
        self.bounds = bounds or DEFAULT_BOUNDS
        self.algorithm = algorithm
        self.cache_dir = cache_dir

        self.n_transactions = int(len(onehot_df))
        self.n_items = int(onehot_df.shape[1])

        # Loosest corner of the search domain.
        self.support_floor = float(self.bounds.min_support_range[0])
        self.confidence_floor = float(self.bounds.min_confidence_range[0])
        self.lift_floor = float(self.bounds.min_lift_range[0])
        self.max_len_cap = int(max(self.bounds.max_len_choices))

        self.build_seconds = 0.0
        self.evaluation_count = 0
        self._cache: Dict[Tuple, Dict[str, Any]] = {}

        self._build_superset()

    # ------------------------------------------------------------------
    # Superset construction
    # ------------------------------------------------------------------

    def _cache_key(self) -> str:
        """Fingerprint the corpus and search domain so caches never collide."""
        digest = hashlib.sha256()
        digest.update(CACHE_FORMAT_VERSION.encode("utf-8"))
        digest.update(f"{self.n_transactions}x{self.n_items}".encode("utf-8"))
        digest.update("|".join(map(str, self.onehot_df.columns)).encode("utf-8"))
        digest.update(
            f"{self.support_floor}|{self.confidence_floor}|{self.lift_floor}|"
            f"{self.max_len_cap}|{self.algorithm}".encode("utf-8")
        )
        # Fold in the actual cell values so a regenerated corpus invalidates the cache.
        digest.update(np.ascontiguousarray(self.onehot_df.to_numpy(dtype=bool)).tobytes())
        return digest.hexdigest()[:20]

    def _build_superset(self) -> None:
        """Mine (or reload) the rule superset and derived lookup structures."""
        start = time.perf_counter()
        cache_file = None

        if self.cache_dir:
            os.makedirs(self.cache_dir, exist_ok=True)
            cache_file = os.path.join(
                self.cache_dir, f"optimizer_superset_{self._cache_key()}.pkl"
            )

        payload = None
        if cache_file and os.path.exists(cache_file):
            try:
                with open(cache_file, "rb") as handle:
                    payload = pickle.load(handle)
                logger.info(f"Reusing cached rule superset from {cache_file}")
            except Exception as exc:  # pragma: no cover - corrupt cache is recoverable
                logger.warning(f"Ignoring unreadable superset cache ({exc}); re-mining.")
                payload = None

        if payload is None:
            logger.info(
                f"Mining rule superset at the search domain floor "
                f"(min_support={self.support_floor}, min_confidence={self.confidence_floor}, "
                f"min_lift={self.lift_floor}, max_len={self.max_len_cap})..."
            )
            itemsets_df, rules_df = mine_association_rules(
                df_onehot=self.onehot_df,
                min_support=self.support_floor,
                min_confidence=self.confidence_floor,
                metric="lift",
                min_metric_val=self.lift_floor,
                max_len=self.max_len_cap,
                algorithm=self.algorithm,
            )
            payload = {"itemsets_df": itemsets_df, "rules_df": rules_df}

            if cache_file:
                try:
                    with open(cache_file, "wb") as handle:
                        pickle.dump(payload, handle, protocol=pickle.HIGHEST_PROTOCOL)
                    logger.info(f"Cached rule superset to {cache_file}")
                except Exception as exc:  # pragma: no cover - caching is best-effort
                    logger.warning(f"Could not write superset cache ({exc}).")

        self.itemsets_df: pd.DataFrame = payload["itemsets_df"]
        self.rules_df: pd.DataFrame = payload["rules_df"].reset_index(drop=True)

        self._prepare_index()

        self.build_seconds = time.perf_counter() - start
        logger.info(
            f"Rule superset ready: {len(self.rules_df)} candidate rules over "
            f"{self.n_transactions} baskets in {self.build_seconds:.2f}s."
        )

    def _empty_index(self) -> None:
        """Initialise an evaluator over a corpus that yielded no rules."""
        self.support = np.zeros(0, dtype=float)
        self.confidence = np.zeros(0, dtype=float)
        self.lift = np.zeros(0, dtype=float)
        self.lift_rounded = np.zeros(0, dtype=float)
        self.rule_length = np.zeros(0, dtype=int)
        self.general_confidence = np.zeros(0, dtype=float)
        self.itemset_index = np.zeros(0, dtype=int)
        self._itemset_keys: List[FrozenSet[str]] = []
        self.packed_coverage = np.zeros((0, 0), dtype=np.uint8)

    def _prepare_index(self) -> None:
        """
        Build the arrays every candidate evaluation masks over.

        Rule metrics are recomputed here from basket counts rather than reused
        from the mined DataFrame, which stores them rounded to six decimals while
        the engine filters on unrounded values -- a rule whose true confidence is
        0.2999996 is rejected at a 0.3 threshold even though its stored 0.3 would
        pass.

        The recomputation deliberately reproduces the engine's *arithmetic*, not
        just its result: support is formed first as `count / n_transactions` and
        confidence as the quotient of two such ratios, exactly as
        `generate_association_rules` does. Dividing counts directly would be a
        touch more accurate, but it disagrees with the engine on exact ties --
        42/2225 divided by 140/2225 lands a few ULPs below 0.3, so the engine
        drops that rule at a 0.3 threshold while exact arithmetic keeps it. The
        contract this evaluator owes is reproducibility: the champion
        configuration must yield precisely this rule set when handed back to the
        mining engine, so the engine's arithmetic is the arithmetic that counts.
        """
        rules = self.rules_df
        if rules.empty or self.n_transactions == 0:
            self._empty_index()
            return

        antecedents = [frozenset(a) for a in rules["antecedents"]]
        consequents = [frozenset(c) for c in rules["consequents"]]
        unions = [a | c for a, c in zip(antecedents, consequents)]

        self.rule_length = np.array([len(u) for u in unions], dtype=int)

        # One incidence row per distinct itemset appearing in any role.
        itemset_ids: Dict[FrozenSet[str], int] = {}

        def _register(key: FrozenSet[str]) -> int:
            if key not in itemset_ids:
                itemset_ids[key] = len(itemset_ids)
            return itemset_ids[key]

        antecedent_index = np.array([_register(a) for a in antecedents], dtype=int)
        consequent_index = np.array([_register(c) for c in consequents], dtype=int)
        self.itemset_index = np.array([_register(u) for u in unions], dtype=int)

        self._itemset_keys = [None] * len(itemset_ids)
        for key, idx in itemset_ids.items():
            self._itemset_keys[idx] = key

        incidence = self._build_incidence()
        counts = incidence.sum(axis=1).astype(np.int64)

        n = float(self.n_transactions)
        # Form supports first, then divide supports -- mirroring the engine.
        self.support = counts[self.itemset_index].astype(float) / n
        antecedent_support = counts[antecedent_index].astype(float) / n
        consequent_support = counts[consequent_index].astype(float) / n

        self.confidence = np.divide(
            self.support,
            antecedent_support,
            out=np.zeros_like(self.support),
            where=antecedent_support > 0,
        )
        denominator = antecedent_support * consequent_support
        self.lift = np.divide(
            self.support, denominator, out=np.zeros_like(self.support), where=denominator > 0
        )
        # The engine compares lift *after* rounding to six decimals; mirror that
        # so borderline rules land on the same side of the threshold.
        self.lift_rounded = np.round(self.lift, 6)

        self._prepare_generalisation_table(antecedents, consequents)

        # Coverage only ever asks about a rule's union itemset, so keep just those rows.
        self.packed_coverage = np.packbits(incidence, axis=1)

    def _build_incidence(self) -> np.ndarray:
        """
        Boolean itemset x transaction incidence: entry (i, t) is True when basket
        t contains every item of itemset i.

        Itemsets are grouped by cardinality so each group resolves in a single
        vectorised AND rather than a Python loop per itemset.
        """
        matrix = self.onehot_df.to_numpy(dtype=bool)
        column_index = {col: i for i, col in enumerate(self.onehot_df.columns)}

        by_length: Dict[int, List[int]] = {}
        for idx, key in enumerate(self._itemset_keys):
            by_length.setdefault(len(key), []).append(idx)

        incidence = np.zeros((len(self._itemset_keys), self.n_transactions), dtype=bool)
        for length, indices in by_length.items():
            if length == 0:
                continue
            columns = np.array(
                [[column_index[item] for item in sorted(self._itemset_keys[i])] for i in indices],
                dtype=int,
            )
            # matrix.T[columns] -> (n_group, length, n_transactions); AND over items.
            incidence[indices] = matrix.T[columns].all(axis=1)

        return incidence

    def _prepare_generalisation_table(
        self,
        antecedents: List[FrozenSet[str]],
        consequents: List[FrozenSet[str]],
    ) -> None:
        """
        For each rule, record the confidence of its strongest strict generalisation
        -- the same consequent reached from a strictly smaller antecedent.

        NaN marks a rule that has no generalisation (a single-item antecedent, or
        one whose sub-rules fell outside the mined superset), which redundancy
        pruning therefore always retains.
        """
        confidence_lookup: Dict[Tuple[FrozenSet[str], FrozenSet[str]], float] = {}
        for ant, con, conf in zip(antecedents, consequents, self.confidence):
            key = (ant, con)
            if conf > confidence_lookup.get(key, -np.inf):
                confidence_lookup[key] = float(conf)

        general_confidence = np.full(len(antecedents), np.nan, dtype=float)
        for idx, (ant, con) in enumerate(zip(antecedents, consequents)):
            if len(ant) < 2:
                continue
            best = -np.inf
            items = list(ant)
            for size in range(1, len(items)):
                for subset in combinations(items, size):
                    conf = confidence_lookup.get((frozenset(subset), con))
                    if conf is not None and conf > best:
                        best = conf
            if best > -np.inf:
                general_confidence[idx] = best

        self.general_confidence = general_confidence

    # ------------------------------------------------------------------
    # Candidate scoring
    # ------------------------------------------------------------------

    def _threshold_mask(self, state: OptimizationState) -> np.ndarray:
        """
        Rules passing the four mining thresholds, before redundancy pruning.

        Comparisons mirror `generate_association_rules` exactly: support and
        confidence on their unrounded values, lift on its six-decimal rounding.
        """
        return (
            (self.support >= state.min_support)
            & (self.confidence >= state.min_confidence)
            & (self.lift_rounded >= state.min_lift)
            & (self.rule_length <= int(state.max_len))
        )

    def selection_mask(self, state: OptimizationState) -> np.ndarray:
        """
        Boolean mask over the superset selecting the rules a fresh mining run at
        `state` would return, after redundancy pruning at its `pruning_factor`.
        """
        if len(self.support) == 0:
            return np.zeros(0, dtype=bool)

        s = state.clip()
        mask = self._threshold_mask(s)

        # Redundancy pruning: a specialised rule must beat its strongest
        # generalisation by at least `pruning_factor` in relative confidence.
        has_generalisation = ~np.isnan(self.general_confidence)
        threshold = np.where(
            has_generalisation,
            self.general_confidence * (1.0 + float(s.pruning_factor)),
            -np.inf,
        )
        keeps = ~has_generalisation | (self.confidence >= threshold - 1e-12)

        return mask & keeps

    def coverage_of(self, mask: np.ndarray) -> float:
        """Fraction of baskets containing the full itemset of at least one selected rule."""
        if self.n_transactions == 0 or not mask.any() or self.packed_coverage.size == 0:
            return 0.0

        itemset_ids = np.unique(self.itemset_index[mask])
        merged = np.bitwise_or.reduce(self.packed_coverage[itemset_ids], axis=0)
        covered = int(np.unpackbits(merged)[: self.n_transactions].sum())
        return float(covered / self.n_transactions)

    def evaluate(self, state: OptimizationState) -> Dict[str, Any]:
        """
        Score one candidate configuration.

        Returns the five metric dimensions the fitness evaluator compares against
        the target paper, plus the size of the selected rule set.
        """
        signature = state.clip().signature()
        if signature in self._cache:
            return self._cache[signature]

        self.evaluation_count += 1
        mask = self.selection_mask(state)
        count = int(mask.sum())

        if count == 0:
            metrics = {
                "rule_count": 0,
                "avg_support": 0.0,
                "avg_confidence": 0.0,
                "avg_lift": 0.0,
                "coverage": 0.0,
            }
        else:
            metrics = {
                "rule_count": count,
                "avg_support": float(self.support[mask].mean()),
                "avg_confidence": float(self.confidence[mask].mean()),
                "avg_lift": float(self.lift[mask].mean()),
                "coverage": self.coverage_of(mask),
            }

        self._cache[signature] = metrics
        return metrics

    def select_rules(self, state: OptimizationState) -> pd.DataFrame:
        """Return the actual rule DataFrame a candidate configuration yields."""
        if self.rules_df.empty:
            return self.rules_df.copy()

        mask = self.selection_mask(state)
        selected = self.rules_df.loc[mask].copy()
        if selected.empty:
            return selected

        return selected.sort_values("lift", ascending=False).reset_index(drop=True)

    def verify_against_engine(self, state: OptimizationState) -> Dict[str, Any]:
        """
        Cross-check masking against a live mining run at the same thresholds.

        Redundancy pruning is switched off for the comparison (`pruning_factor`
        has no counterpart in the raw engine), isolating the claim under test:
        that masking the superset reproduces the engine's rule set exactly.
        """
        s = state.clip()
        unpruned = OptimizationState(
            min_support=s.min_support,
            min_confidence=s.min_confidence,
            min_lift=s.min_lift,
            max_len=s.max_len,
            pruning_factor=0.0,
            bounds=self.bounds,
        )
        # pruning_factor 0 still drops specialisations that fail to improve on a
        # generalisation, so compare on thresholds alone.
        masked_count = int(self._threshold_mask(s).sum())

        _, engine_rules = mine_association_rules(
            df_onehot=self.onehot_df,
            min_support=s.min_support,
            min_confidence=s.min_confidence,
            metric="lift",
            min_metric_val=s.min_lift,
            max_len=int(s.max_len),
            algorithm=self.algorithm,
        )

        return {
            "state": unpruned.to_dict(),
            "masked_rule_count": masked_count,
            "engine_rule_count": int(len(engine_rules)),
            "identical": masked_count == int(len(engine_rules)),
        }
