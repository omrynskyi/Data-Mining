"""Chunk 16 — Phase 4 close-out: final model, full-data refit.

Trains the chosen final configuration — CatBoost with the Chunk 13 winning
hyperparameters (`depth=6, l2_leaf_reg=3, learning_rate=0.05`), the full
tabular/sentiment/vision-metadata/image-pixel feature set, TF-IDF text
(PCA/SVD-reduced), and the `capped3_mean` frozen ResNet18 image embeddings
(Chunk 14's winning modality addition) — with the Chunk 13 full-data-refit
correction applied: per-fold iteration counts are taken exactly as selected
by Chunk 14's early-stopping run (`image_embedding_results.json`), then each
fold is refit on the *complete* outer-training fold rather than the
early-stopping protocol's 85% inner-training subset.

Produces three things:

1. Final CV metrics (both stratified and rescuer-grouped 5-fold), the
   headline numbers for Phase 4/5.
2. Out-of-fold predictions + predicted class probabilities from the
   rescuer-grouped run, saved with cohort metadata, for Phase 5 error-slice
   and calibration analysis. Grouped CV is used because Phase 1-4 repeatedly
   established it as the more realistic, conservative estimate for this
   dataset's rescuer-overlap risk.
3. One reference model fit on 100% of the labeled data (iterations = the
   rounded mean of the grouped per-fold iteration counts), used only for
   feature-importance / interpretability reporting in Phase 5 — never for
   scoring, since that would be circular.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from catboost import CatBoostClassifier
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
IMAGE_EMBEDDING_RESULTS_PATH = PROJECT_ROOT / "pipeline" / "results" / "image_embedding_results.json"
OOF_PREDICTIONS_PATH = PROJECT_ROOT / "pipeline" / "results" / "final_model_oof_predictions.csv"
FEATURE_IMPORTANCE_PATH = PROJECT_ROOT / "pipeline" / "results" / "final_model_feature_importance.csv"
CV_METRICS_PATH = PROJECT_ROOT / "pipeline" / "results" / "final_model_cv_metrics.json"

RANDOM_SEED = 2026
N_SPLITS = 5
ALL_FEATURE_GROUPS = tuple(FEATURE_GROUPS)
IMAGE_EMBEDDING_VARIANT = "capped3_mean"
CATBOOST_CONFIG = {"depth": 6, "l2_leaf_reg": 3, "learning_rate": 0.05}
N_CLASSES = 5


def score(y_true: np.ndarray, y_pred: np.ndarray) -> dict:
    return {
        "qwk": float(cohen_kappa_score(y_true, y_pred, weights="quadratic")),
        "mae": float(mean_absolute_error(y_true, y_pred)),
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "macro_f1": float(f1_score(y_true, y_pred, average="macro")),
    }


def build_features(train_frame, val_frame):
    builder = TreeFoldSafeFeatureBuilder(
        include_text=True,
        tabular_groups=ALL_FEATURE_GROUPS,
        image_embedding_variant=IMAGE_EMBEDDING_VARIANT,
    )
    X_train = builder.fit_transform(train_frame)
    X_val = builder.transform(val_frame)
    cat_cols = list(builder.categorical_feature_names)
    cat_idx = [X_train.columns.get_loc(c) for c in cat_cols]
    return X_train, X_val, cat_idx, cat_cols


def run_fixed_iteration_cv(frame, iterations_per_fold, splitter, split_args, collect_oof: bool):
    y = frame[TARGET_COLUMN].to_numpy()
    oof_pred = np.empty(len(frame), dtype=int)
    oof_proba = np.zeros((len(frame), N_CLASSES)) if collect_oof else None

    for fold_idx, (train_idx, val_idx) in enumerate(splitter.split(*split_args)):
        train_frame = frame.iloc[train_idx]
        val_frame = frame.iloc[val_idx]
        train_y = y[train_idx]
        n_iter = iterations_per_fold[fold_idx]

        X_train, X_val, cat_idx, _ = build_features(train_frame, val_frame)
        clf = CatBoostClassifier(
            loss_function="MultiClass",
            iterations=n_iter,
            depth=CATBOOST_CONFIG["depth"],
            learning_rate=CATBOOST_CONFIG["learning_rate"],
            l2_leaf_reg=CATBOOST_CONFIG["l2_leaf_reg"],
            random_seed=RANDOM_SEED,
            verbose=False,
            cat_features=cat_idx,
        )
        clf.fit(X_train, train_y)
        pred = clf.predict(X_val).flatten().astype(int)
        oof_pred[val_idx] = pred
        if collect_oof:
            oof_proba[val_idx] = clf.predict_proba(X_val)
        print(f"  fold {fold_idx}: n_iter={n_iter} (fixed, full training fold)")

    result = score(y, oof_pred)
    return result, oof_pred, oof_proba


def main() -> None:
    frame = pd.read_csv(FEATURE_TABLE)
    y = frame[TARGET_COLUMN].to_numpy()
    groups = frame["RescuerID"].to_numpy()
    embedding_results = json.loads(IMAGE_EMBEDDING_RESULTS_PATH.read_text())
    winner = embedding_results[f"{IMAGE_EMBEDDING_VARIANT}_embedding"]

    print("=== Final config, grouped 5-fold CV, full-data refit ===")
    grouped = GroupKFold(n_splits=N_SPLITS)
    grouped_metrics, grouped_pred, grouped_proba = run_fixed_iteration_cv(
        frame, winner["grouped"]["best_iterations"], grouped, (frame, y, groups), collect_oof=True
    )
    print(f"  {grouped_metrics}")

    print("=== Final config, stratified 5-fold CV, full-data refit ===")
    stratified = StratifiedKFold(n_splits=N_SPLITS, shuffle=True, random_state=RANDOM_SEED)
    stratified_metrics, _, _ = run_fixed_iteration_cv(
        frame, winner["stratified"]["best_iterations"], stratified, (frame, y), collect_oof=False
    )
    print(f"  {stratified_metrics}")

    CV_METRICS_PATH.write_text(
        json.dumps({"grouped": grouped_metrics, "stratified": stratified_metrics}, indent=2)
    )

    oof_frame = frame[
        ["PetID", "RescuerID", "Type", "Age", "Breed1", "State", "Fee", "PhotoAmt",
         "image_pixels_available", "sentiment_available", "description_available", TARGET_COLUMN]
    ].copy()
    oof_frame["predicted_class"] = grouped_pred
    for c in range(N_CLASSES):
        oof_frame[f"proba_class_{c}"] = grouped_proba[:, c]
    oof_frame.to_csv(OOF_PREDICTIONS_PATH, index=False)
    print(f"Saved grouped-CV OOF predictions to {OOF_PREDICTIONS_PATH}")

    print("=== Reference model fit on 100% of labeled data (interpretability only) ===")
    full_iterations = int(round(np.mean(winner["grouped"]["best_iterations"])))
    builder = TreeFoldSafeFeatureBuilder(
        include_text=True, tabular_groups=ALL_FEATURE_GROUPS, image_embedding_variant=IMAGE_EMBEDDING_VARIANT
    )
    X_full = builder.fit_transform(frame)
    cat_cols = list(builder.categorical_feature_names)
    cat_idx = [X_full.columns.get_loc(c) for c in cat_cols]
    reference_model = CatBoostClassifier(
        loss_function="MultiClass",
        iterations=full_iterations,
        depth=CATBOOST_CONFIG["depth"],
        learning_rate=CATBOOST_CONFIG["learning_rate"],
        l2_leaf_reg=CATBOOST_CONFIG["l2_leaf_reg"],
        random_seed=RANDOM_SEED,
        verbose=False,
        cat_features=cat_idx,
    )
    reference_model.fit(X_full, y)
    importances = pd.DataFrame(
        {"feature": X_full.columns, "importance": reference_model.get_feature_importance()}
    ).sort_values("importance", ascending=False)
    importances.to_csv(FEATURE_IMPORTANCE_PATH, index=False)
    print(f"reference_model_iterations={full_iterations}")
    print(f"Saved feature importances to {FEATURE_IMPORTANCE_PATH}")
    print(importances.head(20).to_string(index=False))


if __name__ == "__main__":
    main()
