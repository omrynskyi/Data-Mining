"""Chunk 15 — Phase 4: text-only ablation.

Isolates the standalone predictive value of raw listing language (`Name` +
`Description`) with no tabular, sentiment, or image features at all, using
the shortlist's recommended model for this experiment: TF-IDF + regularized
multinomial logistic regression (the same documented ordinal-logistic
approximation and hyperparameters as Chunk 11's linear baseline, so results
are directly comparable to that chunk's numbers).

This deliberately does not reuse ``FoldSafeFeatureBuilder`` (which always
includes the tabular/categorical block) or ``TreeFoldSafeFeatureBuilder``
(built for CatBoost/LightGBM, not a linear model) — a small, self-contained
pipeline is clearer for this one-off diagnostic than adding an unused-
elsewhere "text only" flag to either shared builder.

Purpose: decide whether a dedicated text branch would add diverse, orthogonal
signal to the CatBoost model (motivating a late-fusion ensemble), or whether
text's value is already captured by the combined model.
"""

from __future__ import annotations

import json
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.exceptions import ConvergenceWarning
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, cohen_kappa_score, f1_score, mean_absolute_error
from sklearn.model_selection import GroupKFold, StratifiedKFold


# This script now lives in archived/, but helpers/ and all data/results/figures
# still live under pipeline/ — add it to sys.path so the imports below resolve.
import sys as _sys
_sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "pipeline"))

from helpers.fold_safe_features import TARGET_COLUMN, text_for_vectorization

PROJECT_ROOT = Path(__file__).resolve().parents[1]
FEATURE_TABLE = PROJECT_ROOT / "pipeline" / "data" / "listing_features_stage2.csv"
RESULTS_PATH = PROJECT_ROOT / "pipeline" / "results" / "text_only_ablation_results.json"

RANDOM_SEED = 2026
N_SPLITS = 5
TFIDF_MAX_FEATURES = 8_000
TFIDF_MIN_DF = 2
LOGREG_C = 1.0
LOGREG_MAX_ITER = 1000


def score(y_true: np.ndarray, y_pred: np.ndarray) -> dict:
    return {
        "qwk": float(cohen_kappa_score(y_true, y_pred, weights="quadratic")),
        "mae": float(mean_absolute_error(y_true, y_pred)),
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "macro_f1": float(f1_score(y_true, y_pred, average="macro")),
    }


def run_cv(frame: pd.DataFrame, splitter, split_args, label: str) -> dict:
    y = frame[TARGET_COLUMN].to_numpy()
    oof_pred = np.empty(len(frame), dtype=int)
    convergence_warning_folds = 0

    for fold_idx, (train_idx, val_idx) in enumerate(splitter.split(*split_args)):
        train_frame = frame.iloc[train_idx]
        val_frame = frame.iloc[val_idx]
        train_y = y[train_idx]

        tfidf = TfidfVectorizer(
            lowercase=True,
            ngram_range=(1, 2),
            min_df=TFIDF_MIN_DF,
            max_features=TFIDF_MAX_FEATURES,
            sublinear_tf=True,
            strip_accents="unicode",
        )
        X_train = tfidf.fit_transform(text_for_vectorization(train_frame))
        X_val = tfidf.transform(text_for_vectorization(val_frame))

        clf = LogisticRegression(
            C=LOGREG_C, max_iter=LOGREG_MAX_ITER, solver="lbfgs", random_state=RANDOM_SEED
        )
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always", ConvergenceWarning)
            clf.fit(X_train, train_y)
        if any(issubclass(w.category, ConvergenceWarning) for w in caught):
            convergence_warning_folds += 1

        oof_pred[val_idx] = clf.predict(X_val)
        print(f"  [{label}] fold {fold_idx}: vocab_size={len(tfidf.vocabulary_)}")

    result = score(y, oof_pred)
    result["convergence_warning_folds"] = convergence_warning_folds
    return result


def main() -> None:
    frame = pd.read_csv(FEATURE_TABLE)
    y = frame[TARGET_COLUMN].to_numpy()
    groups = frame["RescuerID"].to_numpy()

    results = {}

    print("=== Stratified 5-fold CV: text-only (TF-IDF + logistic regression) ===")
    stratified = StratifiedKFold(n_splits=N_SPLITS, shuffle=True, random_state=RANDOM_SEED)
    results["stratified"] = run_cv(frame, stratified, (frame, y), "stratified")
    print(f"  {results['stratified']}")

    print("=== Rescuer-grouped 5-fold CV: text-only (TF-IDF + logistic regression) ===")
    grouped = GroupKFold(n_splits=N_SPLITS)
    results["grouped"] = run_cv(frame, grouped, (frame, y, groups), "grouped")
    print(f"  {results['grouped']}")

    RESULTS_PATH.write_text(json.dumps(results, indent=2))
    print(f"Saved full results to {RESULTS_PATH}")


if __name__ == "__main__":
    main()
