"""Chunk 11 — Phase 4: baseline and feature-family ablation.

Trains, per feature-family ablation step defined in ``fold_safe_features.py``:

1. A per-fold majority-class baseline (the ordinal majority baseline from the
   Phase 4 model shortlist).
2. A multinomial logistic regression — the documented approximation for
   ordinal logistic regression, since no ordinal implementation (e.g. ``mord``)
   is installed in this environment.

All feature construction (imputation, one-hot encoding, scaling, TF-IDF) is
fit inside each training fold only, using ``FoldSafeFeatureBuilder``. Out-of-
fold predictions are scored with Quadratic Weighted Kappa (primary metric per
Phase 1 success criteria), MAE, accuracy, and macro-F1.

Two validation designs are run:

- Stratified 5-fold CV across every ablation step, to measure incremental
  value of each feature family under an in-distribution estimate.
- Rescuer-grouped 5-fold CV (``GroupKFold`` on ``RescuerID``) for the
  full-feature step only, to check robustness against the rescuer-overlap
  risk documented in Phase 2.

No hyperparameter tuning against these results occurs in this chunk; C=1.0 is
the sklearn default. A quick single-split sanity check showed QWK stable
across C in [0.1, 0.3, 1.0], so tuning is deferred to a later chunk once a
model family is chosen.
"""

from __future__ import annotations

import json
import time
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.exceptions import ConvergenceWarning
from sklearn.linear_model import LogisticRegression
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

from helpers.fold_safe_features import FEATURE_GROUPS, FoldSafeFeatureBuilder, TARGET_COLUMN

PROJECT_ROOT = Path(__file__).resolve().parents[1]
FEATURE_TABLE = PROJECT_ROOT / "pipeline" / "data" / "listing_features_stage2.csv"
RESULTS_PATH = PROJECT_ROOT / "pipeline" / "results" / "baseline_ablation_results.json"

RANDOM_SEED = 2026
N_SPLITS = 5
LOGREG_MAX_ITER = 1000
LOGREG_C = 1.0

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


def majority_class(train_targets: np.ndarray) -> int:
    values, counts = np.unique(train_targets, return_counts=True)
    return int(values[np.argmax(counts)])


def score(y_true: np.ndarray, y_pred: np.ndarray) -> dict:
    return {
        "qwk": float(cohen_kappa_score(y_true, y_pred, weights="quadratic")),
        "mae": float(mean_absolute_error(y_true, y_pred)),
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "macro_f1": float(f1_score(y_true, y_pred, average="macro")),
    }


def run_cv(frame: pd.DataFrame, splitter, split_args, feature_config, label: str) -> dict:
    feature_groups, include_text = feature_config
    y = frame[TARGET_COLUMN].to_numpy()
    oof_majority = np.empty(len(frame), dtype=int)
    oof_model = np.empty(len(frame), dtype=int)
    n_features = None
    convergence_warning_folds = 0

    for fold_idx, (train_idx, val_idx) in enumerate(splitter.split(*split_args)):
        train_frame = frame.iloc[train_idx]
        val_frame = frame.iloc[val_idx]
        train_y = y[train_idx]

        oof_majority[val_idx] = majority_class(train_y)

        builder = FoldSafeFeatureBuilder(include_text=include_text, tabular_groups=feature_groups)
        X_train = builder.fit_transform(train_frame)
        X_val = builder.transform(val_frame)
        n_features = X_train.shape[1]

        clf = LogisticRegression(
            C=LOGREG_C, max_iter=LOGREG_MAX_ITER, solver="lbfgs", random_state=RANDOM_SEED
        )
        start = time.time()
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always", ConvergenceWarning)
            clf.fit(X_train, train_y)
        elapsed = time.time() - start
        if any(issubclass(w.category, ConvergenceWarning) for w in caught):
            convergence_warning_folds += 1
        oof_model[val_idx] = clf.predict(X_val)
        print(
            f"  [{label}] fold {fold_idx}: n_features={n_features} "
            f"fit_seconds={elapsed:.1f} converged={convergence_warning_folds == 0}"
        )

    result = {
        "n_features": n_features,
        "convergence_warning_folds": convergence_warning_folds,
        "majority_baseline": score(y, oof_majority),
        "logistic_regression": score(y, oof_model),
        "logreg_confusion_matrix": confusion_matrix(y, oof_model).tolist(),
        "logreg_classification_report": classification_report(
            y, oof_model, output_dict=True, zero_division=0
        ),
    }
    return result


def main() -> None:
    frame = pd.read_csv(FEATURE_TABLE)
    y = frame[TARGET_COLUMN].to_numpy()
    groups = frame["RescuerID"].to_numpy()

    results: dict[str, dict] = {}

    print("=== Stratified 5-fold CV: feature-family ablation ===")
    stratified = StratifiedKFold(n_splits=N_SPLITS, shuffle=True, random_state=RANDOM_SEED)
    for name, feature_groups, include_text in ABLATION_STEPS:
        print(f"-- step {name} (include_text={include_text}) --")
        res = run_cv(frame, stratified, (frame, y), (feature_groups, include_text), name)
        results[f"stratified__{name}"] = res
        print(f"  majority={res['majority_baseline']}")
        print(f"  logreg={res['logistic_regression']}")

    print("=== Rescuer-grouped 5-fold CV: full-feature robustness check ===")
    grouped = GroupKFold(n_splits=N_SPLITS)
    full_name, full_feature_groups, full_include_text = ABLATION_STEPS[-1]
    res = run_cv(
        frame, grouped, (frame, y, groups), (full_feature_groups, full_include_text), f"grouped_{full_name}"
    )
    results[f"grouped__{full_name}"] = res
    print(f"  majority={res['majority_baseline']}")
    print(f"  logreg={res['logistic_regression']}")

    RESULTS_PATH.write_text(json.dumps(results, indent=2))
    print(f"Saved full results to {RESULTS_PATH}")


if __name__ == "__main__":
    main()
