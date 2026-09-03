"""Chunk 13 — Phase 4: hyperparameter tuning for CatBoost and LightGBM.

Selection criterion: mean out-of-fold Quadratic Weighted Kappa under
rescuer-grouped 5-fold CV (``GroupKFold`` on ``RescuerID``) — the more
conservative, deployment-realistic estimate identified in Chunk 12, where a
stratified-only comparison would have picked the wrong model (LightGBM) over
the model that actually generalizes better to unseen rescuers (CatBoost).
Stratified 5-fold CV is also reported for the winning configuration only, as
a secondary/optimistic reference, consistent with prior chunks.

Both models early-stop directly on Quadratic Weighted Kappa (CatBoost's
built-in ``WKappa`` eval metric; a custom kappa ``feval`` for LightGBM),
rather than log-loss, so the stopping criterion matches the metric that
matters for the stated business success criteria.

Leakage-safety design: within every *outer* CV fold, an *inner* holdout
(15% of the outer-training fold) is carved out purely to decide the
early-stopping iteration. The ``TreeFoldSafeFeatureBuilder`` is fit on the
inner-training partition only; the inner-eval and outer-validation partitions
are both transformed with that same fitted builder, so no fold (inner or
outer) ever contributes to a transformation it is later scored against. For
grouped outer folds, the inner split is also ``RescuerID``-grouped, so
early-stopping decisions cannot benefit from same-rescuer leakage either.

Hyperparameter search is a small, manually chosen grid (not exhaustive) sized
for a personal compute budget; see the CATBOOST_CANDIDATES / LIGHTGBM_CANDIDATES
lists below for the exact configurations tried.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import lightgbm
import numpy as np
import pandas as pd
from catboost import CatBoostClassifier
from lightgbm import LGBMClassifier
from sklearn.metrics import (
    accuracy_score,
    cohen_kappa_score,
    f1_score,
    mean_absolute_error,
)
from sklearn.model_selection import (
    GroupKFold,
    GroupShuffleSplit,
    StratifiedKFold,
    StratifiedShuffleSplit,
)


# This script now lives in archived/, but helpers/ and all data/results/figures
# still live under pipeline/ — add it to sys.path so the imports below resolve.
import sys as _sys
_sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "pipeline"))

from helpers.fold_safe_features import FEATURE_GROUPS, TARGET_COLUMN
from helpers.tree_fold_safe_features import TreeFoldSafeFeatureBuilder

PROJECT_ROOT = Path(__file__).resolve().parents[1]
FEATURE_TABLE = PROJECT_ROOT / "pipeline" / "data" / "listing_features_stage2.csv"
RESULTS_PATH = PROJECT_ROOT / "pipeline" / "results" / "tuning_results.json"

RANDOM_SEED = 2026
N_SPLITS = 5
INNER_EVAL_FRACTION = 0.15
MAX_ITERATIONS = 2000
EARLY_STOPPING_ROUNDS = 50
ALL_FEATURE_GROUPS = tuple(FEATURE_GROUPS)

CATBOOST_CANDIDATES = [
    {"depth": 6, "l2_leaf_reg": 3, "learning_rate": 0.05},
    {"depth": 6, "l2_leaf_reg": 10, "learning_rate": 0.05},
    {"depth": 4, "l2_leaf_reg": 5, "learning_rate": 0.05},
    {"depth": 8, "l2_leaf_reg": 10, "learning_rate": 0.03},
    {"depth": 6, "l2_leaf_reg": 5, "learning_rate": 0.1},
    {"depth": 4, "l2_leaf_reg": 10, "learning_rate": 0.03},
]

LIGHTGBM_CANDIDATES = [
    {"num_leaves": 31, "feature_fraction": 1.0, "bagging_fraction": 1.0, "min_child_samples": 20, "reg_lambda": 0.0},
    {"num_leaves": 15, "feature_fraction": 0.8, "bagging_fraction": 0.8, "min_child_samples": 30, "reg_lambda": 1.0},
    {"num_leaves": 15, "feature_fraction": 0.7, "bagging_fraction": 0.7, "min_child_samples": 50, "reg_lambda": 5.0},
    {"num_leaves": 20, "feature_fraction": 0.7, "bagging_fraction": 0.8, "min_child_samples": 40, "reg_lambda": 2.0},
    {"num_leaves": 10, "feature_fraction": 0.6, "bagging_fraction": 0.7, "min_child_samples": 50, "reg_lambda": 5.0},
    {"num_leaves": 7, "feature_fraction": 0.6, "bagging_fraction": 0.6, "min_child_samples": 60, "reg_lambda": 10.0},
]
LIGHTGBM_LEARNING_RATE = 0.05


def score(y_true: np.ndarray, y_pred: np.ndarray) -> dict:
    return {
        "qwk": float(cohen_kappa_score(y_true, y_pred, weights="quadratic")),
        "mae": float(mean_absolute_error(y_true, y_pred)),
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "macro_f1": float(f1_score(y_true, y_pred, average="macro")),
    }


def qwk_lgb_eval(y_true, y_pred_flat):
    preds = y_pred_flat.reshape(-1, 5).argmax(axis=1)
    return "qwk", cohen_kappa_score(y_true, preds, weights="quadratic"), True


def make_inner_split(train_frame: pd.DataFrame, train_y: np.ndarray, inner_groups: np.ndarray | None):
    if inner_groups is not None:
        splitter = GroupShuffleSplit(n_splits=1, test_size=INNER_EVAL_FRACTION, random_state=RANDOM_SEED)
        return next(splitter.split(train_frame, train_y, inner_groups))
    splitter = StratifiedShuffleSplit(n_splits=1, test_size=INNER_EVAL_FRACTION, random_state=RANDOM_SEED)
    return next(splitter.split(train_frame, train_y))


def fit_predict_catboost(candidate, X_inner_train, y_inner_train, X_inner_eval, y_inner_eval, X_outer_val, cat_idx):
    clf = CatBoostClassifier(
        loss_function="MultiClass",
        eval_metric="WKappa",
        iterations=MAX_ITERATIONS,
        learning_rate=candidate["learning_rate"],
        depth=candidate["depth"],
        l2_leaf_reg=candidate["l2_leaf_reg"],
        random_seed=RANDOM_SEED,
        verbose=False,
        cat_features=cat_idx,
    )
    clf.fit(
        X_inner_train,
        y_inner_train,
        eval_set=(X_inner_eval, y_inner_eval),
        use_best_model=True,
        early_stopping_rounds=EARLY_STOPPING_ROUNDS,
    )
    pred = clf.predict(X_outer_val).flatten().astype(int)
    return pred, clf.get_best_iteration()


def fit_predict_lightgbm(candidate, X_inner_train, y_inner_train, X_inner_eval, y_inner_eval, X_outer_val, cat_cols):
    X_inner_train = X_inner_train.copy()
    X_inner_eval = X_inner_eval.copy()
    X_outer_val = X_outer_val.copy()
    for column in cat_cols:
        X_inner_train[column] = X_inner_train[column].astype("category")
        categories = X_inner_train[column].cat.categories
        X_inner_eval[column] = pd.Categorical(X_inner_eval[column], categories=categories)
        X_outer_val[column] = pd.Categorical(X_outer_val[column], categories=categories)

    bagging_freq = 1 if candidate["bagging_fraction"] < 1.0 else 0
    clf = LGBMClassifier(
        objective="multiclass",
        num_class=5,
        n_estimators=MAX_ITERATIONS,
        learning_rate=LIGHTGBM_LEARNING_RATE,
        num_leaves=candidate["num_leaves"],
        feature_fraction=candidate["feature_fraction"],
        bagging_fraction=candidate["bagging_fraction"],
        bagging_freq=bagging_freq,
        min_child_samples=candidate["min_child_samples"],
        reg_lambda=candidate["reg_lambda"],
        random_state=RANDOM_SEED,
        verbosity=-1,
    )
    clf.fit(
        X_inner_train,
        y_inner_train,
        eval_set=[(X_inner_eval, y_inner_eval)],
        eval_metric=qwk_lgb_eval,
        categorical_feature=cat_cols,
        callbacks=[lightgbm.early_stopping(EARLY_STOPPING_ROUNDS, verbose=False)],
    )
    pred = clf.predict(X_outer_val)
    return pred, clf.best_iteration_


def run_cv(frame: pd.DataFrame, model_kind: str, candidate: dict, splitter, split_args, groups=None) -> dict:
    y = frame[TARGET_COLUMN].to_numpy()
    oof_pred = np.empty(len(frame), dtype=int)
    best_iterations = []

    for train_idx, val_idx in splitter.split(*split_args):
        train_frame = frame.iloc[train_idx]
        val_frame = frame.iloc[val_idx]
        train_y = y[train_idx]
        inner_groups = groups[train_idx] if groups is not None else None

        inner_train_pos, inner_eval_pos = make_inner_split(train_frame, train_y, inner_groups)
        inner_train_frame = train_frame.iloc[inner_train_pos]
        inner_eval_frame = train_frame.iloc[inner_eval_pos]
        inner_train_y = train_y[inner_train_pos]
        inner_eval_y = train_y[inner_eval_pos]

        builder = TreeFoldSafeFeatureBuilder(include_text=True, tabular_groups=ALL_FEATURE_GROUPS)
        X_inner_train = builder.fit_transform(inner_train_frame)
        X_inner_eval = builder.transform(inner_eval_frame)
        X_outer_val = builder.transform(val_frame)
        cat_cols = list(builder.categorical_feature_names)

        if model_kind == "catboost":
            cat_idx = [X_inner_train.columns.get_loc(c) for c in cat_cols]
            pred, best_iter = fit_predict_catboost(
                candidate, X_inner_train, inner_train_y, X_inner_eval, inner_eval_y, X_outer_val, cat_idx
            )
        else:
            pred, best_iter = fit_predict_lightgbm(
                candidate, X_inner_train, inner_train_y, X_inner_eval, inner_eval_y, X_outer_val, cat_cols
            )
        oof_pred[val_idx] = pred
        best_iterations.append(int(best_iter))

    result = score(y, oof_pred)
    result["best_iterations"] = best_iterations
    return result


def search(frame: pd.DataFrame, model_kind: str, candidates: list[dict], groups: np.ndarray) -> list[dict]:
    y = frame[TARGET_COLUMN].to_numpy()
    grouped = GroupKFold(n_splits=N_SPLITS)
    records = []
    for i, candidate in enumerate(candidates):
        t0 = time.time()
        res = run_cv(frame, model_kind, candidate, grouped, (frame, y, groups), groups=groups)
        elapsed = time.time() - t0
        print(f"  [{model_kind} candidate {i}] {candidate} -> grouped_qwk={res['qwk']:.4f} ({elapsed:.0f}s)")
        records.append({"candidate": candidate, "grouped": res})
    return records


def main() -> None:
    frame = pd.read_csv(FEATURE_TABLE)
    y = frame[TARGET_COLUMN].to_numpy()
    groups = frame["RescuerID"].to_numpy()

    results: dict = {}

    print("=== Grouped 5-fold CV search: CatBoost ===")
    cb_records = search(frame, "catboost", CATBOOST_CANDIDATES, groups)
    results["catboost_search"] = cb_records
    best_cb = max(cb_records, key=lambda r: r["grouped"]["qwk"])
    print(f"Best CatBoost candidate: {best_cb['candidate']} grouped_qwk={best_cb['grouped']['qwk']:.4f}")

    print("=== Grouped 5-fold CV search: LightGBM ===")
    lgb_records = search(frame, "lightgbm", LIGHTGBM_CANDIDATES, groups)
    results["lightgbm_search"] = lgb_records
    best_lgb = max(lgb_records, key=lambda r: r["grouped"]["qwk"])
    print(f"Best LightGBM candidate: {best_lgb['candidate']} grouped_qwk={best_lgb['grouped']['qwk']:.4f}")

    print("=== Stratified 5-fold CV, winning configurations only (secondary reference) ===")
    stratified = StratifiedKFold(n_splits=N_SPLITS, shuffle=True, random_state=RANDOM_SEED)
    strat_cb = run_cv(frame, "catboost", best_cb["candidate"], stratified, (frame, y), groups=None)
    print(f"  catboost winner stratified: {strat_cb}")
    strat_lgb = run_cv(frame, "lightgbm", best_lgb["candidate"], stratified, (frame, y), groups=None)
    print(f"  lightgbm winner stratified: {strat_lgb}")

    results["catboost_winner"] = {"candidate": best_cb["candidate"], "grouped": best_cb["grouped"], "stratified": strat_cb}
    results["lightgbm_winner"] = {"candidate": best_lgb["candidate"], "grouped": best_lgb["grouped"], "stratified": strat_lgb}

    RESULTS_PATH.write_text(json.dumps(results, indent=2))
    print(f"Saved full results to {RESULTS_PATH}")


if __name__ == "__main__":
    main()
