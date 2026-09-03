"""Build a row-preserving Stage 1 PetFinder feature table.

This script performs no target encoding, scaling, imputation, clipping, or model
fitting. It joins low-cost sentiment and image-metadata summaries by PetID while
retaining availability flags for missing supplementary files.
"""

from collections import defaultdict
from pathlib import Path
import json

import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_ROOT = PROJECT_ROOT / "petfinder-adoption-prediction"
OUTPUT_PATH = PROJECT_ROOT / "pipeline" / "data" / "listing_features_stage1.csv"


def collect_sentiment_features(pet_ids: set[str]) -> pd.DataFrame:
    rows = []
    for path in (DATA_ROOT / "train_sentiment").glob("*.json"):
        if path.stem not in pet_ids:
            continue
        payload = json.loads(path.read_text())
        document = payload.get("documentSentiment", {})
        rows.append(
            {
                "PetID": path.stem,
                "sentiment_available": 1,
                "sentiment_score": document.get("score", np.nan),
                "sentiment_magnitude": document.get("magnitude", np.nan),
                "sentiment_sentence_count": len(payload.get("sentences", [])),
                "sentiment_token_count": len(payload.get("tokens", [])),
                "sentiment_entity_count": len(payload.get("entities", [])),
            }
        )
    return pd.DataFrame(rows)


def collect_metadata_features(pet_ids: set[str]) -> pd.DataFrame:
    summaries = defaultdict(lambda: {"images": 0, "label_counts": [], "scores": [], "labels": set(), "color_counts": [], "crop_counts": []})
    for path in (DATA_ROOT / "train_metadata").glob("*.json"):
        pet_id = path.stem.rsplit("-", 1)[0]
        if pet_id not in pet_ids:
            continue
        payload = json.loads(path.read_text())
        summary = summaries[pet_id]
        summary["images"] += 1
        labels = payload.get("labelAnnotations", []) or []
        summary["label_counts"].append(len(labels))
        summary["scores"].extend(label["score"] for label in labels if "score" in label)
        summary["labels"].update(label["description"] for label in labels if "description" in label)
        colors = payload.get("imagePropertiesAnnotation", {}).get("dominantColors", {}).get("colors", []) or []
        summary["color_counts"].append(len(colors))
        crop_hints = payload.get("cropHintsAnnotation", {}).get("cropHints", []) or []
        summary["crop_counts"].append(len(crop_hints))

    rows = []
    for pet_id, summary in summaries.items():
        scores = summary["scores"]
        rows.append(
            {
                "PetID": pet_id,
                "metadata_available": 1,
                "metadata_image_count": summary["images"],
                "vision_labels_per_image_mean": np.mean(summary["label_counts"]),
                "vision_label_score_mean": np.mean(scores) if scores else np.nan,
                "vision_label_score_max": np.max(scores) if scores else np.nan,
                "vision_unique_label_count": len(summary["labels"]),
                "vision_colors_per_image_mean": np.mean(summary["color_counts"]),
                "vision_crop_hints_per_image_mean": np.mean(summary["crop_counts"]),
            }
        )
    return pd.DataFrame(rows)


def main() -> None:
    table = pd.read_csv(DATA_ROOT / "train" / "train.csv")
    pet_ids = set(table["PetID"])

    # Text fields stay raw for future train-fold text vectorization; these are safe
    # row-local diagnostics, not learned representations.
    table["name_available"] = table["Name"].notna().astype("int8")
    table["description_available"] = table["Description"].notna().astype("int8")
    table["name_char_count"] = table["Name"].fillna("").str.len()
    table["description_char_count"] = table["Description"].fillna("").str.len()
    table["description_word_count"] = table["Description"].fillna("").str.findall(r"\b\w+\b").str.len()

    sentiment = collect_sentiment_features(pet_ids)
    metadata = collect_metadata_features(pet_ids)
    table = table.merge(sentiment, how="left", on="PetID", validate="one_to_one")
    table = table.merge(metadata, how="left", on="PetID", validate="one_to_one")
    table["sentiment_available"] = table["sentiment_available"].fillna(0).astype("int8")
    table["metadata_available"] = table["metadata_available"].fillna(0).astype("int8")

    # Raw missing feature values intentionally remain missing; imputation belongs
    # inside model-specific training folds.
    table.to_csv(OUTPUT_PATH, index=False)
    print(f"wrote={OUTPUT_PATH}")
    print(f"shape={table.shape}")
    print(f"PetID_unique={table['PetID'].nunique()}")
    print("availability=")
    print(table[["sentiment_available", "metadata_available"]].value_counts().sort_index().to_string())
    print("missing_derived_features=")
    print(table.isna().sum().loc[lambda x: x.gt(0)].to_string())


if __name__ == "__main__":
    main()
