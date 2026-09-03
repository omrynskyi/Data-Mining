"""Run a non-model validation of the PetFinder fold-safe feature builder."""

from pathlib import Path

import pandas as pd
from sklearn.model_selection import StratifiedShuffleSplit


# This script now lives in archived/, but helpers/ and all data/results/figures
# still live under pipeline/ — add it to sys.path so the imports below resolve.
import sys as _sys
_sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "pipeline"))

from helpers.fold_safe_features import FoldSafeFeatureBuilder, IDENTIFIER_COLUMNS, REDUNDANT_COLUMNS, TARGET_COLUMN


PROJECT_ROOT = Path(__file__).resolve().parents[1]
FEATURE_TABLE = PROJECT_ROOT / "pipeline" / "data" / "listing_features_stage2.csv"


def main() -> None:
    frame = pd.read_csv(FEATURE_TABLE)
    splitter = StratifiedShuffleSplit(n_splits=1, test_size=0.20, random_state=2026)
    train_index, validation_index = next(splitter.split(frame, frame[TARGET_COLUMN]))
    train = frame.iloc[train_index].copy()
    validation = frame.iloc[validation_index].copy()

    builder = FoldSafeFeatureBuilder()
    train_matrix = builder.fit_transform(train)
    validation_matrix = builder.transform(validation)

    print("split=StratifiedShuffleSplit(test_size=0.20, random_state=2026)")
    print(f"train_rows={len(train)}; validation_rows={len(validation)}")
    print(f"train_matrix_shape={train_matrix.shape}; validation_matrix_shape={validation_matrix.shape}")
    print(f"tfidf_vocabulary_size={len(builder.tfidf_.vocabulary_) if builder.tfidf_ else 0}")
    print(f"excluded_identifiers_present_in_input={set(IDENTIFIER_COLUMNS).issubset(frame.columns)}")
    print(f"excluded_redundancies_present_in_input={set(REDUNDANT_COLUMNS).issubset(frame.columns)}")
    print("policy=")
    print(builder.policy_summary())


if __name__ == "__main__":
    main()
