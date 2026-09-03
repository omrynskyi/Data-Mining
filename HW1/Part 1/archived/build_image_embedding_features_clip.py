"""Chunk 20 — Phase 4 follow-up: frozen CLIP image embeddings (backbone swap test).

Mirrors `build_image_embedding_features.py` exactly, swapping the frozen
backbone from ImageNet-pretrained ResNet18 to OpenAI's CLIP ViT-B/32 image
encoder (via `open_clip_torch`, installed for this chunk). Motivation: CLIP
was trained on image-caption pairs rather than 1000-class ImageNet labels,
so its embedding space plausibly captures higher-level, more
description-relevant visual concepts (coat type, breed appearance, "fluffy
puppy"-style cues) than ImageNet-classification features — worth testing as
a cheap, no-training diagnostic before considering the higher-cost,
higher-risk option of fine-tuning a backbone directly on this dataset.

Same design as the ResNet18 script: up to 3 photos per listing, frozen
weights (never fine-tuned), embeddings computed once globally, and two
pooling variants (`primary`, `capped3_mean`) from a single pass. Output is
a separate `.npz`/meta CSV pair (`image_embeddings_clip*`) so the ResNet18
artifacts remain untouched for comparison.
"""

from pathlib import Path

import numpy as np
import open_clip
import pandas as pd
import torch
from PIL import Image

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_ROOT = PROJECT_ROOT / "petfinder-adoption-prediction"
STAGE2_PATH = PROJECT_ROOT / "pipeline" / "data" / "listing_features_stage2.csv"
EMBEDDINGS_NPZ_PATH = PROJECT_ROOT / "pipeline" / "data" / "image_embeddings_clip.npz"
META_CSV_PATH = PROJECT_ROOT / "pipeline" / "data" / "image_embedding_clip_meta.csv"
UNREADABLE_LOG_PATH = PROJECT_ROOT / "pipeline" / "data" / "unreadable_train_images_embeddings_clip.csv"

MAX_IMAGES_PER_LISTING = 3
EMBEDDING_DIM = 512
BATCH_SIZE = 64
MODEL_NAME = "ViT-B-32-quickgelu"
PRETRAINED_TAG = "openai"


def build_model():
    device = torch.device("mps" if torch.backends.mps.is_available() else "cpu")
    model, _, preprocess = open_clip.create_model_and_transforms(MODEL_NAME, pretrained=PRETRAINED_TAG)
    model.eval().to(device)
    return model, preprocess, device


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
            out = model.encode_image(batch).cpu().numpy().astype(np.float32)
        for (pet_id, idx), vec in zip(batch_keys, out):
            embeddings_by_pet.setdefault(pet_id, {})[idx] = vec
        batch_tensors.clear()
        batch_keys.clear()

    for count, (pet_id, idx, path) in enumerate(jobs, start=1):
        try:
            tensor = preprocess(Image.open(path).convert("RGB"))
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
        }
    )
    full_meta = stage2[["PetID"]].merge(meta, on="PetID", how="left")
    full_meta["image_embedding_available"] = full_meta["image_embedding_available"].fillna(0).astype("int8")
    full_meta["image_embedding_count"] = full_meta["image_embedding_count"].fillna(0).astype("int8")
    full_meta.to_csv(META_CSV_PATH, index=False)

    pd.DataFrame(unreadable, columns=["filename", "error_type"]).to_csv(UNREADABLE_LOG_PATH, index=False)

    print(f"unreadable_image_files={len(unreadable)}")
    print(f"covered_listings={len(covered_pet_ids)}")
    print(f"npz_saved_to={EMBEDDINGS_NPZ_PATH}")
    print(f"npz_size_mb={EMBEDDINGS_NPZ_PATH.stat().st_size / 1e6:.1f}")
    print("coverage=")
    print(full_meta["image_embedding_available"].value_counts().sort_index().to_string())


if __name__ == "__main__":
    main()
