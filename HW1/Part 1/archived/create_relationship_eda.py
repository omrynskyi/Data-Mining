"""Create sample-size-aware relationship plots for PetFinder EDA."""

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_ROOT = PROJECT_ROOT / "petfinder-adoption-prediction"
OUTPUT_PATH = PROJECT_ROOT / "pipeline" / "figures" / "relationship_eda.png"


def main() -> None:
    df = pd.read_csv(DATA_ROOT / "train" / "train.csv")
    states = pd.read_csv(DATA_ROOT / "StateLabels.csv").set_index("StateID")["StateName"]
    age_labels = ["0–2 mo", "3–6 mo", "7–12 mo", "13–60 mo", ">60 mo"]
    df["age_band"] = pd.cut(df["Age"], [-1, 2, 6, 12, 60, np.inf], labels=age_labels)
    df["pet_type"] = df["Type"].map({1: "Dog", 2: "Cat"})

    age_type = pd.pivot_table(
        df, index="age_band", columns="pet_type", values="AdoptionSpeed", aggfunc="mean", observed=True
    ).reindex(age_labels)
    age_n = df.groupby("age_band", observed=True).size().reindex(age_labels)
    state_summary = (
        df.assign(StateName=df["State"].map(states))
        .groupby("StateName")
        .agg(n=("AdoptionSpeed", "size"), mean_speed=("AdoptionSpeed", "mean"))
        .sort_values("mean_speed")
    )

    fig, axes = plt.subplots(1, 2, figsize=(15, 6))
    ax = axes[0]
    for column, color in [("Cat", "#4c78a8"), ("Dog", "#f58518")]:
        ax.plot(age_labels, age_type[column], marker="o", linewidth=2, label=column, color=color)
    for index, count in enumerate(age_n):
        ax.annotate(f"n={count:,}", (index, 3.16), ha="center", fontsize=9, color="#555555")
    ax.set_ylim(1.8, 3.25)
    ax.set_xlabel("Age band")
    ax.set_ylabel("Mean AdoptionSpeed (higher = slower)")
    ax.set_title("Adoption speed by age band and pet type")
    ax.legend(frameon=False)
    ax.grid(axis="y", alpha=0.25)

    ax = axes[1]
    y = np.arange(len(state_summary))
    ax.scatter(state_summary["mean_speed"], y, s=np.sqrt(state_summary["n"]) * 8, color="#54a24b", alpha=0.75)
    ax.set_yticks(y, state_summary.index)
    ax.set_xlim(2.1, 3.5)
    ax.set_xlabel("Mean AdoptionSpeed (higher = slower)")
    ax.set_title("State estimates; point area reflects listing count")
    ax.grid(axis="x", alpha=0.25)
    for pos, row in enumerate(state_summary.itertuples()):
        ax.annotate(f"n={row.n:,}", (row.mean_speed, pos), xytext=(6, 0), textcoords="offset points", va="center", fontsize=8)

    fig.suptitle("PetFinder relationship-focused EDA: descriptive associations, not causal effects", y=1.02, fontsize=14)
    fig.tight_layout()
    fig.savefig(OUTPUT_PATH, dpi=180, bbox_inches="tight")


if __name__ == "__main__":
    main()
