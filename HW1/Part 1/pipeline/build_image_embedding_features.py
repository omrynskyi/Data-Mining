"""Chunk 14 — Phase 3 addendum: frozen pretrained image embeddings.

Extracts a frozen, ImageNet-pretrained ResNet18 penultimate-layer embedding
(512-dim, average-pooled, `fc` replaced with identity) for up to the first
three photos per listing. The network weights are frozen — not fine-tuned on
this dataset or its labels — so, consistent with the Stage 2 pixel features,
these embeddings are computed once globally rather than inside each CV fold.
Any *learned* dimensionality reduction fit on these embeddings (e.g., PCA)
must still be fit inside each training fold only; that happens in modeling
code (`tree_fold_safe_features.py`), not here.

Two pooling variants are produced from a single pass over the same up-to-
three images per listing, per the Phase 4 modeling-note experiment design
comparing "one primary image" against "capped multi-image (first three)"
pooling under the same compute budget:

- ``primary``: the embedding of the first available photo only.
- ``capped3_mean``: the mean-pooled embedding across whichever of the first
  three photos are actually present (1-3 images).

Listings with zero readable photos among the first three get
``image_embedding_available = 0`` and are omitted from the embedding arrays;
they are not dropped from the listing table, and downstream code must treat
them as missing, not zero.

Storage: raw embeddings are saved as a compact ``.npz`` (float32), not a CSV
column block like Stage 1/2 — 14,652 listings x 512 dims x 2 variants as CSV
text would be roughly 200MB; the binary format is under 60MB. A small CSV
(`image_embedding_meta.csv`) still records per-listing availability/count for
quick inspection without loading the full array.
"""

from pathlib import Path

import numpy as np
import pandas as pd
import torch
from torchvision.io import read_image
from torchvision.models import ResNet18_Weights, resnet18

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_ROOT = PROJECT_ROOT / "petfinder-adoption-prediction"
STAGE2_PATH = PROJECT_ROOT / "pipeline" / "data" / "listing_features_stage2.csv"
EMBEDDINGS_NPZ_PATH = PROJECT_ROOT / "pipeline" / "data" / "image_embeddings_resnet18.npz"
META_CSV_PATH = PROJECT_ROOT / "pipeline" / "data" / "image_embedding_meta.csv"
UNREADABLE_LOG_PATH = PROJECT_ROOT / "pipeline" / "data" / "unreadable_train_images_embeddings.csv"

MAX_IMAGES_PER_LISTING = 3
EMBEDDING_DIM = 512
BATCH_SIZE = 64


def build_model():
    device = torch.device("mps" if torch.backends.mps.is_available() else "cpu")
    weights = ResNet18_Weights.IMAGENET1K_V1
    model = resnet18(weights=weights)
    model.fc = torch.nn.Identity()
    model.eval().to(device)
    return model, weights.transforms(), device


def load_and_preprocess(path: Path, preprocess) -> torch.Tensor:
    img = read_image(str(path))
    if img.shape[0] == 1:
        img = img.repeat(3, 1, 1)
    elif img.shape[0] == 4:
        img = img[:3]
    return preprocess(img)


def main() -> None:
    stage2 = pd.read_csv(STAGE2_PATH)
    pet_ids = stage2["PetID"].tolist()

    model, preprocess, device = build_model()
    print(f"device={device}")

    jobs = []
    for pet_id in pet_ids:
        for i in range(1, MAX_IMAGES_PER_LISTING + 1):
            candidate = DATA_ROOT / "train_images" / f"{pet_id}-{i}.jpg"
            if candidate.exists():
                jobs.append((pet_id, i, candidate))
    print(f"images_to_embed={len(jobs)} across {len(pet_ids)} listings")

    embeddings_by_pet: dict[str, dict[int, np.ndarray]] = {}
    unreadable = []
    batch_tensors: list[torch.Tensor] = []
    batch_keys: list[tuple[str, int]] = []

    def flush_batch():
        if not batch_tensors:
            return
        with torch.no_grad():
            batch = torch.stack(batch_tensors).to(device)
            out = model(batch).cpu().numpy().astype(np.float32)
        for (pet_id, idx), vec in zip(batch_keys, out):
            embeddings_by_pet.setdefault(pet_id, {})[idx] = vec
        batch_tensors.clear()
        batch_keys.clear()

    for count, (pet_id, idx, path) in enumerate(jobs, start=1):
        try:
            tensor = load_and_preprocess(path, preprocess)
        except Exception as error:  # Data-quality capture; never drop the listing.
            unreadable.append({"filename": path.name, "error_type": type(error).__name__})
            continue
        batch_tensors.append(tensor)
        batch_keys.append((pet_id, idx))
        if len(batch_tensors) >= BATCH_SIZE:
            flush_batch()
        if count % 5000 == 0:
            print(f"processed_files={count}/{len(jobs)}")
    flush_batch()

    covered_pet_ids = sorted(embeddings_by_pet)
    primary = np.full((len(covered_pet_ids), EMBEDDING_DIM), np.nan, dtype=np.float32)
    capped3_mean = np.zeros((len(covered_pet_ids), EMBEDDING_DIM), dtype=np.float32)
    counts = np.zeros(len(covered_pet_ids), dtype=np.int8)

    for row_idx, pet_id in enumerate(covered_pet_ids):
        per_image = embeddings_by_pet[pet_id]
        available_indices = sorted(per_image)
        counts[row_idx] = len(available_indices)
        capped3_mean[row_idx] = np.mean([per_image[i] for i in available_indices], axis=0)
        if 1 in per_image:
            primary[row_idx] = per_image[1]

    np.savez_compressed(
        EMBEDDINGS_NPZ_PATH,
        pet_ids=np.array(covered_pet_ids, dtype=object),
        primary=primary,
        capped3_mean=capped3_mean,
        counts=counts,
    )

    meta = pd.DataFrame(
        {
            "PetID": covered_pet_ids,
            "image_embedding_available": 1,
            "image_embedding_count": counts,
            "image_embedding_primary_available": (~np.isnan(primary).any(axis=1)).astype(int),
        }
    )
    full_meta = stage2[["PetID"]].merge(meta, on="PetID", how="left")
    full_meta["image_embedding_available"] = full_meta["image_embedding_available"].fillna(0).astype("int8")
    full_meta["image_embedding_count"] = full_meta["image_embedding_count"].fillna(0).astype("int8")
    full_meta["image_embedding_primary_available"] = (
        full_meta["image_embedding_primary_available"].fillna(0).astype("int8")
    )
    full_meta.to_csv(META_CSV_PATH, index=False)

    pd.DataFrame(unreadable, columns=["filename", "error_type"]).to_csv(UNREADABLE_LOG_PATH, index=False)

    print(f"unreadable_image_files={len(unreadable)}")
    print(f"covered_listings={len(covered_pet_ids)}")
    print(f"npz_saved_to={EMBEDDINGS_NPZ_PATH}")
    print(f"npz_size_mb={EMBEDDINGS_NPZ_PATH.stat().st_size / 1e6:.1f}")
    print("coverage=")
    print(full_meta["image_embedding_available"].value_counts().sort_index().to_string())
    print("primary_available_among_covered=")
    print(full_meta.loc[full_meta["image_embedding_available"] == 1, "image_embedding_primary_available"].value_counts().to_string())


if __name__ == "__main__":
    main()
