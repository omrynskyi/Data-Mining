"""Aggregate lightweight pixel features across every available PetFinder image.

The script is deliberately non-learned: it uses thumbnail-scale descriptive
statistics and does not inspect adoption labels. Corrupt/unreadable files are
counted rather than causing record removal.
"""

from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image, ImageFilter


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_ROOT = PROJECT_ROOT / "petfinder-adoption-prediction"
STAGE1_PATH = PROJECT_ROOT / "pipeline" / "data" / "listing_features_stage1.csv"
AGGREGATE_PATH = PROJECT_ROOT / "pipeline" / "data" / "image_pixel_features.csv"
STAGE2_PATH = PROJECT_ROOT / "pipeline" / "data" / "listing_features_stage2.csv"
THUMBNAIL_SIZE = (128, 128)


def summarize_image(path: Path) -> dict[str, float]:
    with Image.open(path) as image:
        image = image.convert("RGB")
        width, height = image.size
        thumbnail = image.copy()
        thumbnail.thumbnail(THUMBNAIL_SIZE)
        rgb = np.asarray(thumbnail, dtype=np.float32)
        luminance = 0.2126 * rgb[:, :, 0] + 0.7152 * rgb[:, :, 1] + 0.0722 * rgb[:, :, 2]
        red_green = rgb[:, :, 0] - rgb[:, :, 1]
        yellow_blue = 0.5 * (rgb[:, :, 0] + rgb[:, :, 1]) - rgb[:, :, 2]
        colorfulness = np.sqrt(red_green.var() + yellow_blue.var()) + 0.3 * np.sqrt(
            red_green.mean() ** 2 + yellow_blue.mean() ** 2
        )
        edges = np.asarray(thumbnail.convert("L").filter(ImageFilter.FIND_EDGES), dtype=np.float32)
        return {
            "image_width": width,
            "image_height": height,
            "image_aspect_ratio": width / height,
            "image_resolution_pixels": width * height,
            "image_brightness": luminance.mean(),
            "image_contrast": luminance.std(),
            "image_colorfulness": colorfulness,
            "image_edge_variance": edges.var(),
        }


def main() -> None:
    stage1 = pd.read_csv(STAGE1_PATH)
    pet_ids = set(stage1["PetID"])
    features = defaultdict(list)
    unreadable = []
    files = sorted((DATA_ROOT / "train_images").glob("*.jpg"))

    for index, path in enumerate(files, start=1):
        pet_id = path.stem.rsplit("-", 1)[0]
        if pet_id not in pet_ids:
            continue
        try:
            features[pet_id].append(summarize_image(path))
        except Exception as error:  # Data-quality capture; never drop the listing.
            unreadable.append({"filename": path.name, "error_type": type(error).__name__})
        if index % 10000 == 0:
            print(f"processed_files={index}/{len(files)}; listings_with_features={len(features)}")

    aggregate_rows = []
    source_columns = [
        "image_width",
        "image_height",
        "image_aspect_ratio",
        "image_resolution_pixels",
        "image_brightness",
        "image_contrast",
        "image_colorfulness",
        "image_edge_variance",
    ]
    for pet_id, image_summaries in features.items():
        per_image = pd.DataFrame(image_summaries)
        row = {"PetID": pet_id, "image_pixels_available": 1, "image_pixels_count": len(per_image)}
        for column in source_columns:
            row[f"{column}_mean"] = per_image[column].mean()
            row[f"{column}_max"] = per_image[column].max()
        row["image_aspect_ratio_sd"] = per_image["image_aspect_ratio"].std(ddof=0)
        aggregate_rows.append(row)

    aggregate = pd.DataFrame(aggregate_rows)
    aggregate.to_csv(AGGREGATE_PATH, index=False)
    stage2 = stage1.merge(aggregate, on="PetID", how="left", validate="one_to_one")
    stage2["image_pixels_available"] = stage2["image_pixels_available"].fillna(0).astype("int8")
    stage2.to_csv(STAGE2_PATH, index=False)

    pd.DataFrame(unreadable, columns=["filename", "error_type"]).to_csv(
        PROJECT_ROOT / "pipeline" / "data" / "unreadable_train_images.csv", index=False
    )
    print(f"input_image_files={len(files)}")
    print(f"unreadable_image_files={len(unreadable)}")
    print(f"aggregate_shape={aggregate.shape}")
    print(f"stage2_shape={stage2.shape}; stage2_unique_petid={stage2['PetID'].nunique()}")
    print("coverage=")
    print(stage2["image_pixels_available"].value_counts().sort_index().to_string())


if __name__ == "__main__":
    main()
