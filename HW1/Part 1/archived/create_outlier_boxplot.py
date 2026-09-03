"""Create a full-training-set outlier boxplot for PetFinder EDA."""

from pathlib import Path
import math

import matplotlib.pyplot as plt
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
TRAIN_PATH = PROJECT_ROOT / "petfinder-adoption-prediction" / "train" / "train.csv"
OUTPUT_PATH = PROJECT_ROOT / "pipeline" / "figures" / "outlier_boxplots.png"


def main() -> None:
    df = pd.read_csv(TRAIN_PATH)
    plot_data = pd.DataFrame(
        {
            "Age (months)": df["Age"],
            "log1p(Fee)": df["Fee"].clip(lower=0).map(math.log1p),
            "Quantity": df["Quantity"],
            "Photo count": df["PhotoAmt"],
            "Video count": df["VideoAmt"],
            "Description length (100s of chars)": df["Description"].fillna("").str.len() / 100,
        }
    )

    fig, axes = plt.subplots(2, 3, figsize=(15, 8))
    for axis, column in zip(axes.flat, plot_data.columns):
        axis.boxplot(
            plot_data[column].dropna(),
            vert=True,
            patch_artist=True,
            boxprops={"facecolor": "#76a5af"},
            medianprops={"color": "#1f1f1f", "linewidth": 1.5},
            flierprops={"marker": "o", "markersize": 2, "markerfacecolor": "#555555", "markeredgecolor": "#555555", "alpha": 0.45},
        )
        axis.grid(axis="y", alpha=0.25)
        axis.set_title(column)
        axis.set_xlabel("")
        axis.set_ylabel("")
        axis.set_xticks([])
    fig.suptitle(
        "PetFinder training data: univariate distributions and IQR-defined outlier candidates\n"
        "All 14,993 listings; points beyond whiskers are review candidates, not automatic errors",
        y=1.02,
        fontsize=14,
    )
    fig.tight_layout()
    fig.savefig(OUTPUT_PATH, dpi=180, bbox_inches="tight")


if __name__ == "__main__":
    main()
