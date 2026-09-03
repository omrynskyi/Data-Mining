"""Render the final-model class-recall table used in Findings.md as a PNG."""

from pathlib import Path

import matplotlib.pyplot as plt


OUTPUT_PATH = Path(__file__).resolve().parents[1] / "pipeline" / "figures" / "class_recall_table.png"


def main() -> None:
    columns = ["True AdoptionSpeed", "Recall", "Interpretation"]
    rows = [
        ["0: same-day", "0.0%", "The model cannot identify same-day adoptions."],
        ["1: 1-7 days", "11.2%", "Most of these listings are predicted as class 2."],
        ["2: 8-30 days", "60.7%", "This is the model's strongest middle category."],
        ["3: 31-90 days", "18.7%", "The model often predicts a neighboring category instead."],
        ["4: 100+ days", "50.0%", "The slowest-adoption category is identified moderately well."],
    ]

    figure, axis = plt.subplots(figsize=(13, 4.2))
    figure.patch.set_facecolor("white")
    axis.axis("off")
    axis.set_title(
        "Final model: recall by adoption-speed category",
        fontsize=18,
        fontweight="bold",
        color="#17365D",
        pad=18,
    )

    table = axis.table(
        cellText=rows,
        colLabels=columns,
        cellLoc="center",
        colLoc="center",
        colWidths=[0.24, 0.14, 0.62],
        bbox=[0.02, 0.09, 0.96, 0.78],
    )
    table.auto_set_font_size(False)
    table.set_fontsize(12)

    for (row, column), cell in table.get_celld().items():
        cell.set_edgecolor("#C9D3E1")
        cell.set_linewidth(0.9)
        if row == 0:
            cell.set_facecolor("#1F4E79")
            cell.set_text_props(color="white", fontweight="bold")
        elif row == 1:
            cell.set_facecolor("#FBE5E5")
            cell.set_text_props(color="#7A1E1E")
        else:
            cell.set_facecolor("#F7F9FC" if row % 2 else "#EAF0F7")

        if column in (0, 2) and row > 0:
            cell.set_text_props(ha="left", va="center")
            cell.PAD = 0.04

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(OUTPUT_PATH, dpi=220, bbox_inches="tight", facecolor="white")
    plt.close(figure)


if __name__ == "__main__":
    main()
