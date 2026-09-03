"""Render the model-comparison table used in Findings.md as a PNG."""

from pathlib import Path

import matplotlib.pyplot as plt


OUTPUT_PATH = Path(__file__).resolve().parents[1] / "pipeline" / "figures" / "model_comparison_table.png"


def main() -> None:
    columns = ["Model", "Stratified QWK", "Rescuer-grouped QWK"]
    rows = [
        ["Majority-class baseline", "0.000", "-0.012"],
        ["Logistic regression with all features", "0.323", "0.294"],
        ["CatBoost multiclass classifier", "0.374", "0.353"],
        ["LightGBM classifier", "0.396", "0.330"],
        ["Final CatBoost ordinal regression\nwith optimized thresholds", "0.417", "0.379"],
    ]

    figure, axis = plt.subplots(figsize=(14.5, 4.25))
    figure.patch.set_facecolor("white")
    axis.axis("off")
    axis.set_title(
        "Model comparison: 5-fold cross-validation QWK",
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
        colWidths=[0.52, 0.24, 0.24],
        bbox=[0.02, 0.13, 0.94, 0.74],
    )
    table.auto_set_font_size(False)
    table.set_fontsize(12)

    for (row, column), cell in table.get_celld().items():
        cell.set_edgecolor("#C9D3E1")
        cell.set_linewidth(0.9)
        if row == 0:
            cell.set_facecolor("#1F4E79")
            cell.set_text_props(color="white", fontweight="bold")
        elif row == len(rows):
            cell.set_facecolor("#E2F0D9")
            cell.set_text_props(fontweight="bold", color="#1F3D24")
        else:
            cell.set_facecolor("#F7F9FC" if row % 2 else "#EAF0F7")

        if column == 0 and row > 0:
            cell.set_text_props(ha="left", va="center")
            cell.PAD = 0.04

    figure.text(
        0.5,
        0.045,
        "Higher QWK is better. Rescuer-grouped QWK was the primary model-selection criterion.",
        ha="center",
        fontsize=10.5,
        color="#4A5568",
    )
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(OUTPUT_PATH, dpi=220, bbox_inches="tight", facecolor="white")
    plt.close(figure)


if __name__ == "__main__":
    main()
