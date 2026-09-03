"""Chunk 18 — Phase 4 revisit: ordinal regression reformulation.

Phase 5 (Chunk 17) found the final multiclass model never predicts class 0
(same-day adoption) and rarely predicts class 3 — a direct consequence of
training on standard multiclass log-loss, which treats every wrong class as
equally wrong regardless of ordinal distance, combined with class 0's 2.7%
prevalence. This chunk tests the standard fix: treat `AdoptionSpeed` as a
continuous regression target (CatBoostRegressor, RMSE loss), which penalizes
being off by 4 classes far more than being off by 1, then convert the
continuous prediction back to a class either by naive rounding or by
optimized thresholds (the "OptimizedRounder" technique used by top solutions
in the original PetFinder Kaggle competition).

Per CRISP-DM's iterative principle, this revisits Phase 4 modeling because
Phase 5 evaluation exposed a flawed assumption (that multiclass classification
was an adequate formulation for this ordinal target) — documented here and
cross-referenced from `crisp_dm_notes/05_evaluation.md`.

Same features (full tabular/sentiment/vision-metadata/image-pixel set + TF-IDF
text + capped3_mean image embeddings), same CatBoost hyperparameters
(depth=6, l2_leaf_reg=3, learning_rate=0.05), and the same nested
inner-holdout protocol as Chunks 13/14/17, so this isolates the effect of the
objective/decoding change alone:

- Inner-train fits the regressor, early-stopped on RMSE against inner-eval.
- Thresholds are optimized on the inner-eval fold's continuous predictions
  (never the outer validation fold), maximizing QWK via Nelder-Mead —
  standard fold-safe practice matching the early-stopping design already
  used in this project.
- The outer validation fold is scored with: (a) naive rounding, and
  (b) the fold-specific optimized thresholds.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from catboost import CatBoostRegressor
from scipy.optimize import minimize
from sklearn.metrics import (
    accuracy_score,
    classification_report,
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

from helpers.fold_safe_features import FEATURE_GROUPS, TARGET_COLUMN
from helpers.tree_fold_safe_features import TreeFoldSafeFeatureBuilder

PROJECT_ROOT = Path(__file__).resolve().parents[1]
FEATURE_TABLE = PROJECT_ROOT / "pipeline" / "data" / "listing_features_stage2.csv"
RESULTS_PATH = PROJECT_ROOT / "pipeline" / "results" / "ordinal_regression_results.json"

RANDOM_SEED = 2026
N_SPLITS = 5
INNER_EVAL_FRACTION = 0.15
MAX_ITERATIONS = 2000
EARLY_STOPPING_ROUNDS = 50
ALL_FEATURE_GROUPS = tuple(FEATURE_GROUPS)
IMAGE_EMBEDDING_VARIANT = "capped3_mean"
CATBOOST_CONFIG = {"depth": 6, "l2_leaf_reg": 3, "learning_rate": 0.05}
INITIAL_THRESHOLDS = np.array([0.5, 1.5, 2.5, 3.5])


def score(y_true: np.ndarray, y_pred: np.ndarray) -> dict:
    return {
        "qwk": float(cohen_kappa_score(y_true, y_pred, weights="quadratic")),
        "mae": float(mean_absolute_error(y_true, y_pred)),
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "macro_f1": float(f1_score(y_true, y_pred, average="macro")),
    }


def apply_thresholds(preds: np.ndarray, thresholds: np.ndarray) -> np.ndarray:
    sorted_t = np.sort(thresholds)
    classes = np.zeros(len(preds), dtype=int)
    for t in sorted_t:
        classes += (preds > t).astype(int)
    return np.clip(classes, 0, 4)


def negative_qwk(thresholds: np.ndarray, preds: np.ndarray, true_labels: np.ndarray) -> float:
    classes = apply_thresholds(preds, thresholds)
    return -cohen_kappa_score(true_labels, classes, weights="quadratic")


def optimize_thresholds(preds: np.ndarray, true_labels: np.ndarray) -> np.ndarray:
    result = minimize(
        negative_qwk, INITIAL_THRESHOLDS, args=(preds, true_labels), method="Nelder-Mead"
    )
    return np.sort(result.x)


def make_inner_split(train_frame: pd.DataFrame, train_y: np.ndarray, inner_groups: np.ndarray | None):
    if inner_groups is not None:
        splitter = GroupShuffleSplit(n_splits=1, test_size=INNER_EVAL_FRACTION, random_state=RANDOM_SEED)
        return next(splitter.split(train_frame, train_y, inner_groups))
    splitter = StratifiedShuffleSplit(n_splits=1, test_size=INNER_EVAL_FRACTION, random_state=RANDOM_SEED)
    return next(splitter.split(train_frame, train_y))


def run_cv(frame: pd.DataFrame, splitter, split_args, groups=None, return_oof: bool = False) -> dict:
    y = frame[TARGET_COLUMN].to_numpy()
    oof_continuous = np.empty(len(frame), dtype=float)
    oof_naive = np.empty(len(frame), dtype=int)
    oof_optimized = np.empty(len(frame), dtype=int)
    best_iterations = []
    fold_thresholds = []

    for fold_idx, (train_idx, val_idx) in enumerate(splitter.split(*split_args)):
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
            image_embedding_variant=IMAGE_EMBEDDING_VARIANT,
        )
        X_inner_train = builder.fit_transform(inner_train_frame)
        X_inner_eval = builder.transform(inner_eval_frame)
        X_outer_val = builder.transform(val_frame)
        cat_cols = list(builder.categorical_feature_names)
        cat_idx = [X_inner_train.columns.get_loc(c) for c in cat_cols]

        reg = CatBoostRegressor(
            loss_function="RMSE",
            iterations=MAX_ITERATIONS,
            depth=CATBOOST_CONFIG["depth"],
            learning_rate=CATBOOST_CONFIG["learning_rate"],
            l2_leaf_reg=CATBOOST_CONFIG["l2_leaf_reg"],
            random_seed=RANDOM_SEED,
            verbose=False,
            cat_features=cat_idx,
        )
        reg.fit(
            X_inner_train,
            inner_train_y,
            eval_set=(X_inner_eval, inner_eval_y),
            use_best_model=True,
            early_stopping_rounds=EARLY_STOPPING_ROUNDS,
        )
        best_iterations.append(int(reg.get_best_iteration()))

        inner_eval_pred = reg.predict(X_inner_eval)
        thresholds = optimize_thresholds(inner_eval_pred, inner_eval_y)
        fold_thresholds.append(thresholds.tolist())

        val_pred_continuous = reg.predict(X_outer_val)
        oof_continuous[val_idx] = val_pred_continuous
        oof_naive[val_idx] = np.clip(np.round(val_pred_continuous), 0, 4).astype(int)
        oof_optimized[val_idx] = apply_thresholds(val_pred_continuous, thresholds)

        print(f"  fold {fold_idx}: best_iter={best_iterations[-1]} thresholds={np.round(thresholds, 3).tolist()}")

    result = {
        "naive_rounding": score(y, oof_naive),
        "optimized_thresholds": score(y, oof_optimized),
        "best_iterations": best_iterations,
        "fold_thresholds": fold_thresholds,
    }
    result["naive_rounding"]["classification_report"] = classification_report(
        y, oof_naive, output_dict=True, zero_division=0
    )
    result["optimized_thresholds"]["classification_report"] = classification_report(
        y, oof_optimized, output_dict=True, zero_division=0
    )
    if return_oof:
        result["oof_continuous"] = oof_continuous
        result["oof_naive"] = oof_naive
        result["oof_optimized"] = oof_optimized
    return result


def main() -> None:
    frame = pd.read_csv(FEATURE_TABLE)
    y = frame[TARGET_COLUMN].to_numpy()
    groups = frame["RescuerID"].to_numpy()

    results: dict = {}

    print("=== Grouped 5-fold CV: ordinal regression ===")
    grouped = GroupKFold(n_splits=N_SPLITS)
    grouped_result = run_cv(frame, grouped, (frame, y, groups), groups=groups)
    results["grouped"] = grouped_result
    print(f"  naive_rounding: {grouped_result['naive_rounding']['qwk']:.4f} qwk")
    print(f"  optimized_thresholds: {grouped_result['optimized_thresholds']['qwk']:.4f} qwk")

    print("=== Stratified 5-fold CV: ordinal regression ===")
    stratified = StratifiedKFold(n_splits=N_SPLITS, shuffle=True, random_state=RANDOM_SEED)
    stratified_result = run_cv(frame, stratified, (frame, y), groups=None)
    results["stratified"] = stratified_result
    print(f"  naive_rounding: {stratified_result['naive_rounding']['qwk']:.4f} qwk")
    print(f"  optimized_thresholds: {stratified_result['optimized_thresholds']['qwk']:.4f} qwk")

    RESULTS_PATH.write_text(json.dumps(results, indent=2))
    print(f"Saved full results to {RESULTS_PATH}")

    for design in ["grouped", "stratified"]:
        for variant in ["naive_rounding", "optimized_thresholds"]:
            cr = results[design][variant]["classification_report"]
            print(f"\n{design} / {variant} per-class recall:")
            for c in ["0", "1", "2", "3", "4"]:
                print(f"  class {c}: recall={cr[c]['recall']:.3f} support={int(cr[c]['support'])}")


if __name__ == "__main__":
    main()
