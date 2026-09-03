"""Chunk 13 addendum — refit tuned winners on full training folds.

The hyperparameter search in ``tune_boosted_trees.py`` selected the iteration
count via an inner 15% holdout used for early stopping. That holdout is
necessary to pick the number of trees without touching the outer validation
fold, but it means every candidate in the search was trained on ~85% of each
outer-training fold, unlike Chunk 12's untuned comparison, which trained on
100% of it. That is a confound: CatBoost's tuned grouped QWK (0.339) came in
below its untuned Chunk 12 result (0.347), and it is not possible to tell
from the search alone whether that is because the tuned hyperparameters are
worse or because the tuned run had less data to learn from.

This script isolates the hyperparameter effect: for each winning
configuration, refit with the iteration count already selected by early
stopping (fixed, no further early stopping) on the *complete* outer-training
fold, then score on the same outer validation fold used throughout. Per-fold
iteration counts are the exact ``best_iterations`` values written by the
search to ``tuning_results.json``.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from catboost import CatBoostClassifier
from lightgbm import LGBMClassifier
from sklearn.metrics import accuracy_score, cohen_kappa_score, f1_score, mean_absolute_error
from sklearn.model_selection import GroupKFold, StratifiedKFold


# This script now lives in archived/, but helpers/ and all data/results/figures
# still live under pipeline/ — add it to sys.path so the imports below resolve.
import sys as _sys
_sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "pipeline"))

from helpers.fold_safe_features import FEATURE_GROUPS, TARGET_COLUMN
from helpers.tree_fold_safe_features import TreeFoldSafeFeatureBuilder

PROJECT_ROOT = Path(__file__).resolve().parents[1]
FEATURE_TABLE = PROJECT_ROOT / "pipeline" / "data" / "listing_features_stage2.csv"
TUNING_RESULTS_PATH = PROJECT_ROOT / "pipeline" / "results" / "tuning_results.json"
OUTPUT_PATH = PROJECT_ROOT / "pipeline" / "results" / "tuned_full_data_refit_results.json"

RANDOM_SEED = 2026
N_SPLITS = 5
ALL_FEATURE_GROUPS = tuple(FEATURE_GROUPS)


def score(y_true: np.ndarray, y_pred: np.ndarray) -> dict:
    return {
        "qwk": float(cohen_kappa_score(y_true, y_pred, weights="quadratic")),
        "mae": float(mean_absolute_error(y_true, y_pred)),
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "macro_f1": float(f1_score(y_true, y_pred, average="macro")),
    }


def run_fixed_iteration_cv(frame, model_kind, candidate, iterations_per_fold, splitter, split_args):
    y = frame[TARGET_COLUMN].to_numpy()
    oof_pred = np.empty(len(frame), dtype=int)

    for fold_idx, (train_idx, val_idx) in enumerate(splitter.split(*split_args)):
        train_frame = frame.iloc[train_idx]
        val_frame = frame.iloc[val_idx]
        train_y = y[train_idx]
        n_iter = iterations_per_fold[fold_idx]

        builder = TreeFoldSafeFeatureBuilder(include_text=True, tabular_groups=ALL_FEATURE_GROUPS)
        X_train = builder.fit_transform(train_frame)
        X_val = builder.transform(val_frame)
        cat_cols = list(builder.categorical_feature_names)

        if model_kind == "catboost":
            cat_idx = [X_train.columns.get_loc(c) for c in cat_cols]
            clf = CatBoostClassifier(
                loss_function="MultiClass",
                iterations=n_iter,
                depth=candidate["depth"],
                learning_rate=candidate["learning_rate"],
                l2_leaf_reg=candidate["l2_leaf_reg"],
                random_seed=RANDOM_SEED,
                verbose=False,
                cat_features=cat_idx,
            )
            clf.fit(X_train, train_y)
            pred = clf.predict(X_val).flatten().astype(int)
        else:
            X_train = X_train.copy()
            X_val = X_val.copy()
            for column in cat_cols:
                X_train[column] = X_train[column].astype("category")
                X_val[column] = pd.Categorical(X_val[column], categories=X_train[column].cat.categories)
            bagging_freq = 1 if candidate["bagging_fraction"] < 1.0 else 0
            clf = LGBMClassifier(
                objective="multiclass",
                num_class=5,
                n_estimators=n_iter,
                learning_rate=0.05,
                num_leaves=candidate["num_leaves"],
                feature_fraction=candidate["feature_fraction"],
                bagging_fraction=candidate["bagging_fraction"],
                bagging_freq=bagging_freq,
                min_child_samples=candidate["min_child_samples"],
                reg_lambda=candidate["reg_lambda"],
                random_state=RANDOM_SEED,
                verbosity=-1,
            )
            clf.fit(X_train, train_y, categorical_feature=cat_cols)
            pred = clf.predict(X_val)

        oof_pred[val_idx] = pred
        print(f"  [{model_kind}] fold {fold_idx}: n_iter={n_iter} (fixed, full training fold)")

    return score(y, oof_pred)


def main() -> None:
    frame = pd.read_csv(FEATURE_TABLE)
    y = frame[TARGET_COLUMN].to_numpy()
    groups = frame["RescuerID"].to_numpy()
    tuning_results = json.loads(TUNING_RESULTS_PATH.read_text())

    results = {}
    grouped = GroupKFold(n_splits=N_SPLITS)
    stratified = StratifiedKFold(n_splits=N_SPLITS, shuffle=True, random_state=RANDOM_SEED)

    for model_kind, key in [("catboost", "catboost_winner"), ("lightgbm", "lightgbm_winner")]:
        winner = tuning_results[key]
        candidate = winner["candidate"]

        print(f"=== {model_kind} winner {candidate}: full-data refit, grouped CV ===")
        grouped_res = run_fixed_iteration_cv(
            frame, model_kind, candidate, winner["grouped"]["best_iterations"], grouped, (frame, y, groups)
        )
        print(f"  grouped={grouped_res}")

        print(f"=== {model_kind} winner {candidate}: full-data refit, stratified CV ===")
        stratified_res = run_fixed_iteration_cv(
            frame, model_kind, candidate, winner["stratified"]["best_iterations"], stratified, (frame, y)
        )
        print(f"  stratified={stratified_res}")

        results[model_kind] = {"candidate": candidate, "grouped": grouped_res, "stratified": stratified_res}

    OUTPUT_PATH.write_text(json.dumps(results, indent=2))
    print(f"Saved full results to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
