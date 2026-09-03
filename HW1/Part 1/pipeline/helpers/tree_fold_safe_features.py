"""Tree-model feature builder for PetFinder modeling (Chunk 12).

``fold_safe_features.FoldSafeFeatureBuilder`` was built for a linear model:
it one-hot encodes categoricals, imputes and scales numeric features, and
represents raw text as a large sparse TF-IDF block. Gradient-boosted trees
work differently and generally do better with:

- Categorical columns passed as native categories (not one-hot), letting the
  tree library find its own splits.
- Numeric columns left with missing values intact (both CatBoost and
  LightGBM route NaN through learned splits) rather than imputed/scaled.
- A dense, low-rank summary of the raw text rather than an 8,000-dimension
  sparse TF-IDF block, which is inefficient for axis-aligned tree splits.

This is a deliberate, documented divergence from the linear-model pipeline,
not an inconsistency: see ``crisp_dm_notes/04_modeling.md`` Chunk 12.

Chunk 14 adds an optional frozen-image-embedding block (see
``image_embedding_features.py``): raw ResNet18 embeddings are fixed,
target-independent features loaded globally, but the PCA that reduces them
to a compact dense block is a *learned* transform and is fit fold-safe here,
exactly like the text TF-IDF/SVD block below.

Fit on a training partition only. The TF-IDF vocabulary, the text SVD
components, the embedding mean-imputer, and the embedding PCA components are
all learned from that partition alone.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.decomposition import PCA, TruncatedSVD
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.impute import SimpleImputer

from helpers.fold_safe_features import CATEGORICAL_COLUMNS, FEATURE_GROUPS, text_for_vectorization
from helpers.image_embedding_features import get_raw_embeddings

CATEGORICAL_MISSING_SENTINEL = "missing"
DEFAULT_TABULAR_GROUPS = tuple(FEATURE_GROUPS)


@dataclass
class TreeFoldSafeFeatureBuilder:
    """Dense categorical + raw numeric + optional text-SVD/image-embedding table for one fold."""

    include_text: bool = True
    tabular_groups: tuple[str, ...] = DEFAULT_TABULAR_GROUPS
    tfidf_max_features: int = 8_000
    tfidf_min_df: int = 2
    text_svd_components: int = 100
    image_embedding_variant: str | None = None  # None, "primary", or "capped3_mean"
    image_embedding_backbone: str = "resnet18"  # "resnet18" (Ch14) or "clip" (Ch20)
    image_embedding_pca_components: int = 50

    def __post_init__(self) -> None:
        unknown_groups = set(self.tabular_groups) - set(FEATURE_GROUPS)
        if unknown_groups:
            raise ValueError(f"Unknown feature groups: {sorted(unknown_groups)}")
        self.numeric_columns_ = tuple(
            column for group in self.tabular_groups for column in FEATURE_GROUPS[group]
        )
        self.categorical_columns_ = tuple(CATEGORICAL_COLUMNS)
        self.tfidf_ = (
            TfidfVectorizer(
                lowercase=True,
                ngram_range=(1, 2),
                min_df=self.tfidf_min_df,
                max_features=self.tfidf_max_features,
                sublinear_tf=True,
                strip_accents="unicode",
            )
            if self.include_text
            else None
        )
        self.svd_ = None  # sized and fitted lazily in fit(), since n_components must be < n_docs
        self.embedding_imputer_ = None
        self.embedding_pca_ = None

    def _validate(self, frame: pd.DataFrame) -> None:
        required = set(self.categorical_columns_) | set(self.numeric_columns_)
        if self.include_text:
            required |= {"Name", "Description"}
        if self.image_embedding_variant is not None:
            required |= {"PetID"}
        missing = required - set(frame.columns)
        if missing:
            raise ValueError(f"Feature table lacks required columns: {sorted(missing)}")

    def _tabular_frame(self, frame: pd.DataFrame) -> pd.DataFrame:
        categorical = frame[list(self.categorical_columns_)].astype("object")
        categorical = categorical.where(categorical.notna(), CATEGORICAL_MISSING_SENTINEL)
        categorical = categorical.astype(str)
        numeric = frame[list(self.numeric_columns_)].astype(float)
        return pd.concat(
            [categorical.reset_index(drop=True), numeric.reset_index(drop=True)], axis=1
        )

    def fit(self, train_frame: pd.DataFrame) -> "TreeFoldSafeFeatureBuilder":
        self._validate(train_frame)
        if self.tfidf_ is not None:
            train_tfidf = self.tfidf_.fit_transform(text_for_vectorization(train_frame))
            n_components = min(self.text_svd_components, min(train_tfidf.shape) - 1)
            self.svd_ = TruncatedSVD(n_components=n_components, random_state=2026)
            self.svd_.fit(train_tfidf)
        if self.image_embedding_variant is not None:
            raw = get_raw_embeddings(
                train_frame["PetID"], self.image_embedding_variant, self.image_embedding_backbone
            )
            self.embedding_imputer_ = SimpleImputer(strategy="mean")
            imputed = self.embedding_imputer_.fit_transform(raw)
            n_components = min(self.image_embedding_pca_components, min(imputed.shape) - 1)
            self.embedding_pca_ = PCA(n_components=n_components, random_state=2026)
            self.embedding_pca_.fit(imputed)
        self.is_fitted_ = True
        return self

    def _text_svd_frame(self, frame: pd.DataFrame) -> pd.DataFrame:
        text_matrix = self.tfidf_.transform(text_for_vectorization(frame))
        svd_matrix = self.svd_.transform(text_matrix)
        return pd.DataFrame(
            svd_matrix,
            columns=[f"text_svd_{i}" for i in range(svd_matrix.shape[1])],
        )

    def _image_embedding_frame(self, frame: pd.DataFrame) -> pd.DataFrame:
        raw = get_raw_embeddings(frame["PetID"], self.image_embedding_variant, self.image_embedding_backbone)
        availability = (~np.isnan(raw).any(axis=1)).astype(float)
        imputed = self.embedding_imputer_.transform(raw)
        pca_matrix = self.embedding_pca_.transform(imputed)
        columns = [f"img_emb_pca_{i}" for i in range(pca_matrix.shape[1])]
        out = pd.DataFrame(pca_matrix, columns=columns)
        out["img_embedding_available"] = availability
        return out

    def transform(self, frame: pd.DataFrame) -> pd.DataFrame:
        if not getattr(self, "is_fitted_", False):
            raise RuntimeError("Call fit on a training partition before transform.")
        self._validate(frame)
        blocks = [self._tabular_frame(frame).reset_index(drop=True)]
        if self.tfidf_ is not None:
            blocks.append(self._text_svd_frame(frame))
        if self.image_embedding_variant is not None:
            blocks.append(self._image_embedding_frame(frame))
        if len(blocks) == 1:
            return blocks[0]
        return pd.concat(blocks, axis=1)

    def fit_transform(self, train_frame: pd.DataFrame) -> pd.DataFrame:
        return self.fit(train_frame).transform(train_frame)

    @property
    def categorical_feature_names(self) -> tuple[str, ...]:
        return self.categorical_columns_
