"""Chunk 14 (+ Chunk 20 backbone swap) — Phase 4: do frozen image embeddings
help CatBoost, and does the choice of frozen backbone matter?

Compares feature configurations, all using the Chunk 13 winning CatBoost
hyperparameters (``depth=6, l2_leaf_reg=3, learning_rate=0.05``) and the
identical inner-holdout, QWK-early-stopping protocol from
``tune_boosted_trees.py``, so the only thing that varies is the feature set:

1. No image embeddings (the Chunk 12/13 full tabular+text feature set).
2. + ``primary`` frozen ResNet18 embedding (first photo only), PCA-reduced.
3. + ``capped3_mean`` frozen ResNet18 embedding (mean of first 3 photos),
   PCA-reduced.
4. + ``capped3_mean`` frozen CLIP ViT-B/32 embedding (Chunk 20) — same
   pooling, same PCA, different pretrained backbone. CLIP was trained on
   image-caption pairs rather than 1000-class ImageNet labels, so this tests
   whether a more semantically-aware frozen backbone beats ResNet18 without
   any fine-tuning risk.

Both rescuer-grouped and stratified 5-fold CV are reported, since Chunks
12-13 established that the two designs can disagree on which configuration
is better.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import numpy as np
import pandas as pd
from catboost import CatBoostClassifier
from sklearn.metrics import accuracy_score, cohen_kappa_score, f1_score, mean_absolute_error
from sklearn.model_selection import GroupKFold, GroupShuffleSplit, StratifiedKFold, StratifiedShuffleSplit


# This script now lives in archived/, but helpers/ and all data/results/figures
# still live under pipeline/ — add it to sys.path so the imports below resolve.
import sys as _sys
_sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "pipeline"))

from helpers.fold_safe_features import FEATURE_GROUPS, TARGET_COLUMN
from helpers.tree_fold_safe_features import TreeFoldSafeFeatureBuilder

PROJECT_ROOT = Path(__file__).resolve().parents[1]
FEATURE_TABLE = PROJECT_ROOT / "pipeline" / "data" / "listing_features_stage2.csv"
RESULTS_PATH = PROJECT_ROOT / "pipeline" / "results" / "image_embedding_results.json"

RANDOM_SEED = 2026
N_SPLITS = 5
INNER_EVAL_FRACTION = 0.15
MAX_ITERATIONS = 2000
EARLY_STOPPING_ROUNDS = 50
ALL_FEATURE_GROUPS = tuple(FEATURE_GROUPS)

CATBOOST_CONFIG = {"depth": 6, "l2_leaf_reg": 3, "learning_rate": 0.05}

CONFIGS = [
    ("no_image_embeddings", None, "resnet18"),
    ("primary_image_embedding_resnet18", "primary", "resnet18"),
    ("capped3_mean_embedding_resnet18", "capped3_mean", "resnet18"),
    ("capped3_mean_embedding_clip", "capped3_mean", "clip"),
]


def score(y_true: np.ndarray, y_pred: np.ndarray) -> dict:
    return {
        "qwk": float(cohen_kappa_score(y_true, y_pred, weights="quadratic")),
        "mae": float(mean_absolute_error(y_true, y_pred)),
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "macro_f1": float(f1_score(y_true, y_pred, average="macro")),
    }


def make_inner_split(train_frame: pd.DataFrame, train_y: np.ndarray, inner_groups: np.ndarray | None):
    if inner_groups is not None:
        splitter = GroupShuffleSplit(n_splits=1, test_size=INNER_EVAL_FRACTION, random_state=RANDOM_SEED)
        return next(splitter.split(train_frame, train_y, inner_groups))
    splitter = StratifiedShuffleSplit(n_splits=1, test_size=INNER_EVAL_FRACTION, random_state=RANDOM_SEED)
    return next(splitter.split(train_frame, train_y))


def run_cv(
    frame: pd.DataFrame,
    image_embedding_variant: str | None,
    image_embedding_backbone: str,
    splitter,
    split_args,
    groups=None,
) -> dict:
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

        builder = TreeFoldSafeFeatureBuilder(
            include_text=True,
            tabular_groups=ALL_FEATURE_GROUPS,
            image_embedding_variant=image_embedding_variant,
            image_embedding_backbone=image_embedding_backbone,
        )
        X_inner_train = builder.fit_transform(inner_train_frame)
        X_inner_eval = builder.transform(inner_eval_frame)
        X_outer_val = builder.transform(val_frame)
        cat_cols = list(builder.categorical_feature_names)
        cat_idx = [X_inner_train.columns.get_loc(c) for c in cat_cols]

        clf = CatBoostClassifier(
            loss_function="MultiClass",
            eval_metric="WKappa",
            iterations=MAX_ITERATIONS,
            learning_rate=CATBOOST_CONFIG["learning_rate"],
            depth=CATBOOST_CONFIG["depth"],
            l2_leaf_reg=CATBOOST_CONFIG["l2_leaf_reg"],
            random_seed=RANDOM_SEED,
            verbose=False,
            cat_features=cat_idx,
        )
        clf.fit(
            X_inner_train,
            inner_train_y,
            eval_set=(X_inner_eval, inner_eval_y),
            use_best_model=True,
            early_stopping_rounds=EARLY_STOPPING_ROUNDS,
        )
        oof_pred[val_idx] = clf.predict(X_outer_val).flatten().astype(int)
        best_iterations.append(int(clf.get_best_iteration()))

    result = score(y, oof_pred)
    result["best_iterations"] = best_iterations
    result["n_features"] = X_inner_train.shape[1]
    return result


def main() -> None:
    frame = pd.read_csv(FEATURE_TABLE)
    y = frame[TARGET_COLUMN].to_numpy()
    groups = frame["RescuerID"].to_numpy()

    results: dict = {}
    grouped = GroupKFold(n_splits=N_SPLITS)
    stratified = StratifiedKFold(n_splits=N_SPLITS, shuffle=True, random_state=RANDOM_SEED)

    for name, variant, backbone in CONFIGS:
        print(f"=== {name} (variant={variant}, backbone={backbone}) ===")

        t0 = time.time()
        grouped_res = run_cv(frame, variant, backbone, grouped, (frame, y, groups), groups=groups)
        print(f"  grouped: {grouped_res} ({time.time()-t0:.0f}s)")

        t0 = time.time()
        stratified_res = run_cv(frame, variant, backbone, stratified, (frame, y), groups=None)
        print(f"  stratified: {stratified_res} ({time.time()-t0:.0f}s)")

        results[name] = {"grouped": grouped_res, "stratified": stratified_res}

    RESULTS_PATH.write_text(json.dumps(results, indent=2))
    print(f"Saved full results to {RESULTS_PATH}")


if __name__ == "__main__":
    main()
