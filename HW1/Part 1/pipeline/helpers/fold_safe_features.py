"""Leakage-safe feature policy and transformer for PetFinder modeling.

Call ``fit`` on a training partition only, then call ``transform`` on validation
or future data. No target-derived statistic, text vocabulary, imputation value,
category map, or scaling parameter is learned outside the training partition.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd
from scipy.sparse import csr_matrix, hstack
from sklearn.compose import ColumnTransformer
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, RobustScaler


TARGET_COLUMN = "AdoptionSpeed"
IDENTIFIER_COLUMNS = ("PetID", "RescuerID")
REDUNDANT_COLUMNS = ("metadata_image_count", "image_pixels_count")

CATEGORICAL_COLUMNS = (
    "Type", "Breed1", "Breed2", "Gender", "Color1", "Color2", "Color3",
    "MaturitySize", "FurLength", "Vaccinated", "Dewormed", "Sterilized",
    "Health", "State",
)

FEATURE_GROUPS = {
    "core_numeric": ("Age", "Quantity", "Fee", "VideoAmt", "PhotoAmt"),
    "text_shape": (
        "name_available", "description_available", "name_char_count",
        "description_char_count", "description_word_count",
    ),
    "sentiment": (
        "sentiment_available", "sentiment_score", "sentiment_magnitude",
        "sentiment_sentence_count", "sentiment_token_count", "sentiment_entity_count",
    ),
    "vision_metadata": (
        "metadata_available", "vision_labels_per_image_mean",
        "vision_label_score_mean", "vision_label_score_max",
        "vision_unique_label_count", "vision_colors_per_image_mean",
        "vision_crop_hints_per_image_mean",
    ),
    "image_pixels": (
        "image_pixels_available", "image_width_mean", "image_width_max",
        "image_height_mean", "image_height_max", "image_aspect_ratio_mean",
        "image_aspect_ratio_max", "image_resolution_pixels_mean",
        "image_resolution_pixels_max", "image_brightness_mean",
        "image_brightness_max", "image_contrast_mean", "image_contrast_max",
        "image_colorfulness_mean", "image_colorfulness_max",
        "image_edge_variance_mean", "image_edge_variance_max",
        "image_aspect_ratio_sd",
    ),
}
DEFAULT_TABULAR_GROUPS = tuple(FEATURE_GROUPS)


def text_for_vectorization(frame: pd.DataFrame) -> pd.Series:
    """Make text presence explicit without fitting any learned transformation."""
    name = frame["Name"].fillna("[NO_NAME]").astype(str)
    description = frame["Description"].fillna("[NO_DESCRIPTION]").astype(str)
    return "name " + name + " description " + description


@dataclass
class FoldSafeFeatureBuilder:
    """Sparse tabular + optional TF-IDF representation fitted on one fold."""

    include_text: bool = True
    tabular_groups: tuple[str, ...] = DEFAULT_TABULAR_GROUPS
    tfidf_max_features: int = 8_000
    tfidf_min_df: int = 2

    def __post_init__(self) -> None:
        unknown_groups = set(self.tabular_groups) - set(FEATURE_GROUPS)
        if unknown_groups:
            raise ValueError(f"Unknown feature groups: {sorted(unknown_groups)}")
        self.numeric_columns_ = tuple(
            column for group in self.tabular_groups for column in FEATURE_GROUPS[group]
        )
        self.tabular_columns_ = CATEGORICAL_COLUMNS + self.numeric_columns_
        self.tabular_preprocessor_ = ColumnTransformer(
            transformers=[
                (
                    "categorical",
                    Pipeline(
                        steps=[
                            ("impute", SimpleImputer(strategy="most_frequent")),
                            ("one_hot", OneHotEncoder(handle_unknown="ignore", sparse_output=True)),
                        ]
                    ),
                    list(CATEGORICAL_COLUMNS),
                ),
                (
                    "numeric",
                    Pipeline(
                        steps=[
                            ("impute", SimpleImputer(strategy="median", add_indicator=True)),
                            ("scale", RobustScaler()),
                        ]
                    ),
                    list(self.numeric_columns_),
                ),
            ],
            sparse_threshold=1.0,
        )
        self.tfidf_ = TfidfVectorizer(
            lowercase=True,
            ngram_range=(1, 2),
            min_df=self.tfidf_min_df,
            max_features=self.tfidf_max_features,
            sublinear_tf=True,
            strip_accents="unicode",
        ) if self.include_text else None

    def _validate_frame(self, frame: pd.DataFrame) -> None:
        missing = set(self.tabular_columns_) - set(frame.columns)
        if self.include_text:
            missing |= {"Name", "Description"} - set(frame.columns)
        if missing:
            raise ValueError(f"Feature table lacks required columns: {sorted(missing)}")

    def fit(self, train_frame: pd.DataFrame) -> "FoldSafeFeatureBuilder":
        self._validate_frame(train_frame)
        self.tabular_preprocessor_.fit(train_frame)
        if self.tfidf_ is not None:
            self.tfidf_.fit(text_for_vectorization(train_frame))
        self.is_fitted_ = True
        return self

    def transform(self, frame: pd.DataFrame) -> csr_matrix:
        if not getattr(self, "is_fitted_", False):
            raise RuntimeError("Call fit on a training partition before transform.")
        self._validate_frame(frame)
        tabular = self.tabular_preprocessor_.transform(frame)
        if self.tfidf_ is None:
            return csr_matrix(tabular)
        text = self.tfidf_.transform(text_for_vectorization(frame))
        return hstack([tabular, text], format="csr")

    def fit_transform(self, train_frame: pd.DataFrame) -> csr_matrix:
        return self.fit(train_frame).transform(train_frame)

    def policy_summary(self) -> dict[str, object]:
        return {
            "target": TARGET_COLUMN,
            "excluded_identifiers": IDENTIFIER_COLUMNS,
            "excluded_redundancies": REDUNDANT_COLUMNS,
            "categorical_columns": CATEGORICAL_COLUMNS,
            "numeric_feature_groups": self.tabular_groups,
            "include_text": self.include_text,
        }
