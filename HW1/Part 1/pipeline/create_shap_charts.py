"""Chunk 21 charts — visualize the SHAP-based direction analysis.

Reads `model_shap_analysis.json` (produced by `analyze_model_shap.py`) and
renders five figures. Palette follows the project's dataviz-skill reference:
diverging blue/red for signed SHAP direction (negative = pushes prediction
toward faster adoption, positive = toward slower), single sequential blue
for the magnitude-only overall importance ranking. The blue/red pair was
validated with the skill's palette validator (all checks pass, worst
adjacent CVD Delta E 21.6).
"""

import json
from pathlib import Path

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SHAP_PATH = PROJECT_ROOT / "pipeline" / "results" / "model_shap_analysis.json"
OUT_DIR = PROJECT_ROOT / "pipeline" / "figures"

# Palette (validated: node scripts/validate_palette.js "#2a78d6,#e34948" --mode light)
BLUE = "#2a78d6"    # negative SHAP: pushes prediction toward faster adoption
RED = "#e34948"     # positive SHAP: pushes prediction toward slower adoption
GRAY_MID = "#c3c2b7"
INK = "#0b0b0b"
INK_SECONDARY = "#52514e"
INK_MUTED = "#898781"
GRID = "#e1e0d9"
SURFACE = "#fcfcfb"

plt.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Helvetica", "Arial", "DejaVu Sans"],
    "axes.edgecolor": GRAY_MID,
    "axes.labelcolor": INK_SECONDARY,
    "text.color": INK,
    "xtick.color": INK_MUTED,
    "ytick.color": INK,
    "figure.facecolor": SURFACE,
    "axes.facecolor": SURFACE,
    "savefig.facecolor": SURFACE,
})


def diverging_color(value: float) -> str:
    return RED if value >= 0 else BLUE


def style_axis(ax, hide_spines=("top", "right", "left")):
    for s in hide_spines:
        ax.spines[s].set_visible(False)
    ax.tick_params(length=0)
    ax.set_axisbelow(True)


def main():
    data = json.loads(SHAP_PATH.read_text())
    features = {f["feature"]: f for f in data["top_features"]}

    # ---------- Figure 1: overall importance ranking ----------
    ranked = sorted(data["top_features"], key=lambda f: f["mean_abs_shap"], reverse=True)[:15]
    names = [f["feature"] for f in ranked][::-1]
    vals = [f["mean_abs_shap"] for f in ranked][::-1]

    fig, ax = plt.subplots(figsize=(7.5, 6))
    ax.barh(names, vals, color=BLUE, height=0.6)
    for i, v in enumerate(vals):
        ax.text(v + max(vals) * 0.015, i, f"{v:.3f}", va="center", fontsize=8.5, color=INK_SECONDARY)
    ax.set_xlabel("Mean absolute SHAP value  (typical impact on predicted adoption-speed score)")
    ax.set_title("What matters most: top 15 features by average impact", fontsize=12, color=INK, pad=12)
    ax.grid(axis="x", color=GRID, linewidth=0.8, zorder=0)
    style_axis(ax)
    fig.tight_layout()
    fig.savefig(OUT_DIR / "shap_chart_1_overall_importance.png", dpi=150)
    plt.close(fig)

    # ---------- Figure 2: numeric trends (Age, Quantity, Fee) ----------
    numeric_feats = ["Age", "Quantity", "Fee"]
    fig, axes = plt.subplots(1, 3, figsize=(11, 4), sharey=True)
    quartile_labels = ["Q1\n(lowest)", "Q2", "Q3", "Q4\n(highest)"]
    for ax, feat in zip(axes, numeric_feats):
        raw_means = features[feat]["direction"]["mean_shap_by_quartile"]
        # Quantity/Fee are heavily zero/one-inflated, so some quartile bins are
        # empty (None) — plot only populated bins rather than a placeholder gap.
        labels_here = [lbl for lbl, m in zip(quartile_labels, raw_means) if m is not None]
        means = [m for m in raw_means if m is not None]
        if len(means) == 2:
            # Only two bins survived (e.g. Quantity/Fee): "Q1"/"Q4" would wrongly
            # imply Q2/Q3 were skipped rather than genuinely empty. Use plain labels.
            labels_here = ["Low", "High"]
        colors = [diverging_color(m) for m in means]
        ax.bar(labels_here, means, color=colors, width=0.6, zorder=3)
        ax.axhline(0, color=GRAY_MID, linewidth=1, zorder=2)
        ax.set_title(feat, fontsize=11, color=INK)
        ax.grid(axis="y", color=GRID, linewidth=0.8, zorder=0)
        style_axis(ax, hide_spines=("top", "right"))
        ax.tick_params(axis="x", labelsize=8.5)
    axes[0].set_ylabel("Mean SHAP value\n(effect on predicted adoption speed)", fontsize=9.5)
    fig.suptitle("Higher age, more pets per listing, and higher fees all predict slower adoption",
                 fontsize=12, color=INK, y=1.03)
    fig.text(0.5, -0.06,
              "Bars above zero (red) push the prediction toward slower adoption; below zero (blue) toward faster.",
              ha="center", fontsize=9, color=INK_SECONDARY)
    fig.tight_layout()
    fig.savefig(OUT_DIR / "shap_chart_2_numeric_trends.png", dpi=150, bbox_inches="tight")
    plt.close(fig)

    # ---------- Figure 3: categorical effects (Sterilized, Vaccinated, Gender) ----------
    cat_feats = ["Sterilized", "Vaccinated", "Gender"]
    fig, axes = plt.subplots(1, 3, figsize=(12, 4.2))
    for ax, feat in zip(axes, cat_feats):
        cats = features[feat]["by_category"]
        labels = [f"{c['label']}\n(n={c['count']:,})" for c in cats]
        means = [c["mean_shap"] for c in cats]
        colors = [diverging_color(m) for m in means]
        y_pos = np.arange(len(labels))
        ax.barh(y_pos, means, color=colors, height=0.55, zorder=3)
        ax.set_yticks(y_pos)
        ax.set_yticklabels(labels, fontsize=9)
        ax.axvline(0, color=GRAY_MID, linewidth=1, zorder=2)
        ax.set_title(feat, fontsize=11, color=INK)
        ax.grid(axis="x", color=GRID, linewidth=0.8, zorder=0)
        style_axis(ax)
        ax.invert_yaxis()
    fig.suptitle("Sterilized/vaccinated pets predict slower adoption — likely an age/tenure\n"
                 "confound, not a causal effect (see note below)",
                 fontsize=12, color=INK, y=1.08)
    fig.text(0.5, -0.05,
              "Red = predicts slower adoption; blue = predicts faster. Do not read this as advice against sterilizing shelter animals.",
              ha="center", fontsize=9, color=INK_SECONDARY, wrap=True)
    fig.tight_layout()
    fig.savefig(OUT_DIR / "shap_chart_3_sterilized_vaccinated_gender.png", dpi=150, bbox_inches="tight")
    plt.close(fig)

    # ---------- Figure 4: breed effects (top + bottom, with small-n caution) ----------
    breed_cats = features["Breed1"]["by_category"]
    top8 = breed_cats[:8]
    bottom8 = breed_cats[8:][::-1]
    combined = top8 + bottom8
    # Small-n flag is folded into the tick label itself (not a floating annotation)
    # so it never collides with a bar that runs the full width of the axis.
    labels = [f"{c['label']} (n={c['count']}{', small n' if c['count'] < 100 else ''})" for c in combined]
    means = [c["mean_shap"] for c in combined]
    colors = [diverging_color(m) for m in means]

    fig, ax = plt.subplots(figsize=(9.5, 6.5))
    y_pos = np.arange(len(labels))
    ax.barh(y_pos, means, color=colors, height=0.6, zorder=3)
    ax.set_yticks(y_pos)
    ax.set_yticklabels(labels, fontsize=8.5)
    ax.axvline(0, color=GRAY_MID, linewidth=1, zorder=2)
    ax.axhline(7.5, color=GRID, linewidth=1, linestyle=(0, (3, 3)), zorder=2)
    ax.set_title("Breed effects: common generic breeds predict slower adoption;\n"
                  "'fastest' breeds shown are mostly too small a sample to trust",
                  fontsize=11.5, color=INK, pad=10)
    ax.set_xlabel("Mean SHAP value (effect on predicted adoption speed)")
    ax.grid(axis="x", color=GRID, linewidth=0.8, zorder=0)
    style_axis(ax)
    ax.invert_yaxis()
    fig.tight_layout()
    fig.savefig(OUT_DIR / "shap_chart_4_breed_effects.png", dpi=150)
    plt.close(fig)

    # ---------- Figure 5: state effects (with small-n caution) ----------
    state_cats = features["State"]["by_category"]
    top10 = state_cats[:10]
    labels = [f"{c['label']} (n={c['count']}{', small n' if c['count'] < 100 else ''})" for c in top10]
    means = [c["mean_shap"] for c in top10]
    colors = [diverging_color(m) for m in means]

    fig, ax = plt.subplots(figsize=(8.5, 5))
    y_pos = np.arange(len(labels))
    ax.barh(y_pos, means, color=colors, height=0.6, zorder=3)
    ax.set_yticks(y_pos)
    ax.set_yticklabels(labels, fontsize=9)
    ax.axvline(0, color=GRAY_MID, linewidth=1, zorder=2)
    ax.set_title("States with the strongest 'slower adoption' signal\n(most have too few listings to trust)",
                  fontsize=11.5, color=INK, pad=10)
    ax.set_xlabel("Mean SHAP value (effect on predicted adoption speed)")
    ax.grid(axis="x", color=GRID, linewidth=0.8, zorder=0)
    style_axis(ax)
    ax.invert_yaxis()
    fig.tight_layout()
    fig.savefig(OUT_DIR / "shap_chart_5_state_effects.png", dpi=150)
    plt.close(fig)

    print("Saved 5 charts to analysis_outputs/figures/shap_chart_*.png")


if __name__ == "__main__":
    main()
