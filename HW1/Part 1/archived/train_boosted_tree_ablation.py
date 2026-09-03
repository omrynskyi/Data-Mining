"""Chunk 12 — Phase 4: boosted-tree comparison (CatBoost, LightGBM).

Repeats the Chunk 11 feature-family ablation and validation designs with two
gradient-boosted tree models (Phase 4 model shortlist items 3 and 4), using
``TreeFoldSafeFeatureBuilder`` (native categorical handling, raw numeric
values with missing data left intact, and a dense TruncatedSVD text summary
instead of sparse TF-IDF — see that module's docstring for the rationale).

Fixed, untuned hyperparameters are used throughout (200 trees, depth 6,
learning rate 0.1) — consistent with the Chunk 11 decision not to tune
against these comparison results. Hyperparameter search is deferred until a
model family is selected.

The ordinal-majority baseline is not recomputed here; it is on record in
Chunk 11 / ``baseline_ablation_results.json`` and is identical regardless of
model family (it never uses features).
"""

from __future__ import annotations

import json
import time
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from catboost import CatBoostClassifier
from lightgbm import LGBMClassifier
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    cohen_kappa_score,
    confusion_matrix,
    f1_score,
    mean_absolute_error,
)
from sklearn.model_selection import GroupKFold, StratifiedKFold


# This script now lives in archived/, but helpers/ and all data/results/figures
# still live under pipeline/ — add it to sys.path so the imports below resolve.
import sys as _sys
_sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "pipeline"))

from helpers.fold_safe_features import FEATURE_GROUPS, TARGET_COLUMN
from helpers.tree_fold_safe_features import TreeFoldSafeFeatureBuilder

PROJECT_ROOT = Path(__file__).resolve().parents[1]
FEATURE_TABLE = PROJECT_ROOT / "pipeline" / "data" / "listing_features_stage2.csv"
RESULTS_PATH = PROJECT_ROOT / "pipeline" / "results" / "boosted_tree_ablation_results.json"

RANDOM_SEED = 2026
N_SPLITS = 5
N_ESTIMATORS = 200
MAX_DEPTH = 6
LEARNING_RATE = 0.1

ABLATION_STEPS = [
    ("1_core_tabular", ("core_numeric",), False),
    ("2_plus_text_shape", ("core_numeric", "text_shape"), False),
    ("3_plus_sentiment", ("core_numeric", "text_shape", "sentiment"), False),
    (
        "4_plus_metadata_image",
        ("core_numeric", "text_shape", "sentiment", "vision_metadata", "image_pixels"),
        False,
    ),
    ("5_plus_tfidf_text", tuple(FEATURE_GROUPS), True),
]


def score(y_true: np.ndarray, y_pred: np.ndarray) -> dict:
    return {
        "qwk": float(cohen_kappa_score(y_true, y_pred, weights="quadratic")),
        "mae": float(mean_absolute_error(y_true, y_pred)),
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "macro_f1": float(f1_score(y_true, y_pred, average="macro")),
    }


def fit_predict_catboost(X_train, y_train, X_val, cat_idx):
    clf = CatBoostClassifier(
        loss_function="MultiClass",
        iterations=N_ESTIMATORS,
        depth=MAX_DEPTH,
        learning_rate=LEARNING_RATE,
        random_seed=RANDOM_SEED,
        verbose=False,
        cat_features=cat_idx,
    )
    clf.fit(X_train, y_train)
    return clf.predict(X_val).flatten().astype(int)


def fit_predict_lightgbm(X_train, y_train, X_val, cat_cols):
    X_train = X_train.copy()
    X_val = X_val.copy()
    for column in cat_cols:
        X_train[column] = X_train[column].astype("category")
        X_val[column] = pd.Categorical(X_val[column], categories=X_train[column].cat.categories)
    clf = LGBMClassifier(
        objective="multiclass",
        num_class=5,
        n_estimators=N_ESTIMATORS,
        max_depth=MAX_DEPTH,
        learning_rate=LEARNING_RATE,
        random_state=RANDOM_SEED,
        verbosity=-1,
    )
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        clf.fit(X_train, y_train, categorical_feature=cat_cols)
    return clf.predict(X_val)


def run_cv(frame: pd.DataFrame, splitter, split_args, feature_config, label: str) -> dict:
    feature_groups, include_text = feature_config
    y = frame[TARGET_COLUMN].to_numpy()
    oof_catboost = np.empty(len(frame), dtype=int)
    oof_lightgbm = np.empty(len(frame), dtype=int)
    n_features = None

    for fold_idx, (train_idx, val_idx) in enumerate(splitter.split(*split_args)):
        train_frame = frame.iloc[train_idx]
        val_frame = frame.iloc[val_idx]
        train_y = y[train_idx]

        builder = TreeFoldSafeFeatureBuilder(include_text=include_text, tabular_groups=feature_groups)
        X_train = builder.fit_transform(train_frame)
        X_val = builder.transform(val_frame)
        n_features = X_train.shape[1]
        cat_cols = list(builder.categorical_feature_names)
        cat_idx = [X_train.columns.get_loc(c) for c in cat_cols]

        start = time.time()
        oof_catboost[val_idx] = fit_predict_catboost(X_train, train_y, X_val, cat_idx)
        cb_seconds = time.time() - start

        start = time.time()
        oof_lightgbm[val_idx] = fit_predict_lightgbm(X_train, train_y, X_val, cat_cols)
        lgb_seconds = time.time() - start

        print(
            f"  [{label}] fold {fold_idx}: n_features={n_features} "
            f"catboost_s={cb_seconds:.1f} lightgbm_s={lgb_seconds:.1f}"
        )

    result = {"n_features": n_features}
    for model_name, oof_pred in [("catboost", oof_catboost), ("lightgbm", oof_lightgbm)]:
        result[model_name] = score(y, oof_pred)
        result[f"{model_name}_confusion_matrix"] = confusion_matrix(y, oof_pred).tolist()
        result[f"{model_name}_classification_report"] = classification_report(
            y, oof_pred, output_dict=True, zero_division=0
        )
    return result


def main() -> None:
    frame = pd.read_csv(FEATURE_TABLE)
    y = frame[TARGET_COLUMN].to_numpy()
    groups = frame["RescuerID"].to_numpy()

    results: dict[str, dict] = {}

    print("=== Stratified 5-fold CV: feature-family ablation (CatBoost, LightGBM) ===")
    stratified = StratifiedKFold(n_splits=N_SPLITS, shuffle=True, random_state=RANDOM_SEED)
    for name, feature_groups, include_text in ABLATION_STEPS:
        print(f"-- step {name} (include_text={include_text}) --")
        res = run_cv(frame, stratified, (frame, y), (feature_groups, include_text), name)
        results[f"stratified__{name}"] = res
        print(f"  catboost={res['catboost']}")
        print(f"  lightgbm={res['lightgbm']}")

    print("=== Rescuer-grouped 5-fold CV: full-feature robustness check ===")
    grouped = GroupKFold(n_splits=N_SPLITS)
    full_name, full_feature_groups, full_include_text = ABLATION_STEPS[-1]
    res = run_cv(
        frame, grouped, (frame, y, groups), (full_feature_groups, full_include_text), f"grouped_{full_name}"
    )
    results[f"grouped__{full_name}"] = res
    print(f"  catboost={res['catboost']}")
    print(f"  lightgbm={res['lightgbm']}")

    RESULTS_PATH.write_text(json.dumps(results, indent=2))
    print(f"Saved full results to {RESULTS_PATH}")


if __name__ == "__main__":
    main()
