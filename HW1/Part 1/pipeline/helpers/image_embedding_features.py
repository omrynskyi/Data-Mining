"""Loader for frozen image-embedding stores (Chunk 14: ResNet18; Chunk 20: CLIP).

The raw embeddings themselves are fixed, target-independent features (see
``build_image_embedding_features.py`` / ``build_image_embedding_features_clip.py``)
and are loaded once, globally, per backbone. Any *learned* reduction of them
(PCA) is fit fold-safe inside ``tree_fold_safe_features.py``, not here.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]  # pipeline/ (this module now lives in pipeline/helpers/)

BACKBONE_NPZ_PATHS = {
    "resnet18": PROJECT_ROOT / "data" / "image_embeddings_resnet18.npz",
    "clip": PROJECT_ROOT / "data" / "image_embeddings_clip.npz",
}

EMBEDDING_VARIANTS = ("primary", "capped3_mean")
EMBEDDING_DIM = 512


@lru_cache(maxsize=None)
def _load_store(backbone: str) -> dict[str, np.ndarray]:
    if backbone not in BACKBONE_NPZ_PATHS:
        raise ValueError(f"Unknown embedding backbone: {backbone!r}")
    data = np.load(BACKBONE_NPZ_PATHS[backbone], allow_pickle=True)
    pet_ids = data["pet_ids"]
    index = {pet_id: i for i, pet_id in enumerate(pet_ids)}
    return {
        "index": index,
        "primary": data["primary"],
        "capped3_mean": data["capped3_mean"],
    }


def get_raw_embeddings(pet_ids: pd.Series, variant: str, backbone: str = "resnet18") -> np.ndarray:
    """Return an (n_rows, 512) float32 array aligned to ``pet_ids``.

    Rows for listings without a covered embedding are all-NaN, never zero —
    callers must impute explicitly (fold-safe) rather than treating NaN as 0.
    """
    if variant not in EMBEDDING_VARIANTS:
        raise ValueError(f"Unknown embedding variant: {variant!r}")
    store = _load_store(backbone)
    index = store["index"]
    matrix = store[variant]
    out = np.full((len(pet_ids), EMBEDDING_DIM), np.nan, dtype=np.float32)
    for row, pet_id in enumerate(pet_ids):
        pos = index.get(pet_id)
        if pos is not None:
            out[row] = matrix[pos]
    return out
