"""Chunk 19 — Phase 5 refresh: artifacts for the ordinal-regression model.

Chunk 18 found optimized-threshold ordinal regression beats the multiclass
model Phase 5 (Chunk 17) was evaluated against. This script regenerates the
two inputs Phase 5's error analysis needs for the new model, mirroring what
`train_final_model.py` produced for the old one:

1. Grouped-CV out-of-fold predictions (continuous + optimized-threshold
   class) with cohort metadata, for confusion-matrix/cohort-slice analysis.
2. Feature importances from a reference model fit on 100% of the labeled
   data (interpretability only, never used for scoring).

Reuses `train_ordinal_regression.run_cv` unmodified (aside from an additive
`return_oof` flag) so this reproduces exactly the same grouped-CV numbers
already reported in Chunk 18 (0.379 QWK) — this is a re-run for artifact
capture, not a new experiment or a full-data-refit correction (that
remains a documented pending item, same as it was for Chunk 14 before
Chunk 16 applied it).
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from catboost import CatBoostRegressor
from sklearn.model_selection import GroupKFold

from helpers.fold_safe_features import FEATURE_GROUPS, TARGET_COLUMN
from helpers.tree_fold_safe_features import TreeFoldSafeFeatureBuilder
from train_ordinal_regression import (
    ALL_FEATURE_GROUPS,
    CATBOOST_CONFIG,
    IMAGE_EMBEDDING_VARIANT,
    N_SPLITS,
    RANDOM_SEED,
    run_cv,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
FEATURE_TABLE = PROJECT_ROOT / "pipeline" / "data" / "listing_features_stage2.csv"
OOF_PATH = PROJECT_ROOT / "pipeline" / "results" / "ordinal_model_oof_predictions.csv"
FEATURE_IMPORTANCE_PATH = PROJECT_ROOT / "pipeline" / "results" / "ordinal_model_feature_importance.csv"


def main() -> None:
    frame = pd.read_csv(FEATURE_TABLE)
    groups = frame["RescuerID"].to_numpy()
    y = frame[TARGET_COLUMN].to_numpy()

    print("=== Grouped 5-fold CV (with OOF capture) ===")
    grouped = GroupKFold(n_splits=N_SPLITS)
    result = run_cv(frame, grouped, (frame, y, groups), groups=groups, return_oof=True)
    print(f"  naive_rounding qwk={result['naive_rounding']['qwk']:.4f}")
    print(f"  optimized_thresholds qwk={result['optimized_thresholds']['qwk']:.4f}")
    print("  (should match Chunk 18: 0.2886 naive, 0.3793 optimized)")

    oof_frame = frame[
        ["PetID", "RescuerID", "Type", "Age", "Breed1", "State", "Fee", "PhotoAmt",
         "image_pixels_available", "sentiment_available", "description_available", TARGET_COLUMN]
    ].copy()
    oof_frame["predicted_continuous"] = result["oof_continuous"]
    oof_frame["predicted_class_naive"] = result["oof_naive"]
    oof_frame["predicted_class"] = result["oof_optimized"]  # optimized thresholds = the adopted decoding
    oof_frame.to_csv(OOF_PATH, index=False)
    print(f"Saved OOF predictions to {OOF_PATH}")

    print("=== Reference regressor fit on 100% of labeled data (interpretability only) ===")
    full_iterations = int(round(np.mean(result["best_iterations"])))
    builder = TreeFoldSafeFeatureBuilder(
        include_text=True, tabular_groups=ALL_FEATURE_GROUPS, image_embedding_variant=IMAGE_EMBEDDING_VARIANT
    )
    X_full = builder.fit_transform(frame)
    cat_cols = list(builder.categorical_feature_names)
    cat_idx = [X_full.columns.get_loc(c) for c in cat_cols]
    reference_model = CatBoostRegressor(
        loss_function="RMSE",
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
    print(importances.head(15).to_string(index=False))


if __name__ == "__main__":
    main()
