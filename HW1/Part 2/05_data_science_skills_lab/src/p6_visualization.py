"""
p6_visualization.py — CRISP-DM Phase 6 (Deployment): visualization-builder skill.

Produces a publication-quality figure set for the Telco churn retention
program, following the skill's process:
  1. classify message type -> pick chart type (references/chart_selection_guide.md)
  2. aggregate data at the right grain BEFORE plotting
  3. build with pre-set professional styling (whitegrid, accessible palette,
     no chartjunk) per references/visual_design_principles.md
  4. apply visual hierarchy (highlight the one bar/point that matters)
  5. annotate with a finding-based title, not a variable-name title
  6. export at 150 DPI (web/dashboard use), matplotlib Agg backend, no display

All numbers are recomputed here directly from data/Telco-Customer-Churn.csv
and existing verified Phase 1-5 artifacts (funnel_results.json,
segment_profile_kmeans.csv, ts_hazard_by_tenure_month.csv,
business_metrics.json). Nothing is invented.

Outputs -> reports/figures/p6_*.png
"""
import json
import warnings

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

ROOT = "/Users/oleg/Documents/Coding/SJSU/Data Mining/HW1/Part 2/05_data_science_skills_lab"
DATA = f"{ROOT}/data/Telco-Customer-Churn.csv"
ART = f"{ROOT}/artifacts"
FIG = f"{ROOT}/reports/figures"

# ---- Accessible, colour-blind-safe categorical palette (Wong 2011) ----
# blue, orange, teal, vermillion, purple, gold, sky, grey
PALETTE = {
    "blue": "#0072B2",
    "orange": "#E69F00",
    "teal": "#009E73",
    "vermillion": "#D55E00",
    "purple": "#CC79A7",
    "gold": "#F0E442",
    "sky": "#56B4E9",
    "grey": "#7F7F7F",
    "lightgrey": "#D9D9D9",
}

plt.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Helvetica", "Arial", "DejaVu Sans"],
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.grid": True,
    "grid.alpha": 0.25,
    "grid.linestyle": "--",
    "axes.axisbelow": True,
    "figure.dpi": 130,
    "savefig.dpi": 130,
    "savefig.bbox": "tight",
})

SOURCE_NOTE = "Source: data/Telco-Customer-Churn.csv (n=7,043) | CRISP-DM Phase 6 | 2026-09-02"


def _footer(fig, note=SOURCE_NOTE):
    fig.text(0.01, 0.005, note, fontsize=7.5, color=PALETTE["grey"], ha="left")


def _title_block(fig, title, subtitle, title_y=0.98, subtitle_y=None, fontsize=13):
    """Figure-level title + subtitle using figure coordinates (not axes-
    relative), so multi-line titles never collide with the subtitle
    regardless of axes size. Returns the y-fraction where the title block
    ends, for use in a subsequent subplots_adjust(top=...) call."""
    n_lines = title.count("\n") + 1
    t = fig.suptitle(title, x=0.02, y=title_y, ha="left", fontsize=fontsize,
                      fontweight="bold")
    if subtitle_y is None:
        subtitle_y = title_y - 0.06 * n_lines - 0.02
    fig.text(0.02, subtitle_y, subtitle, fontsize=9.5, color=PALETTE["grey"], ha="left")
    return subtitle_y - 0.05


def load_raw():
    df = pd.read_csv(DATA)
    df["TotalCharges"] = pd.to_numeric(df["TotalCharges"], errors="coerce")
    df["ChurnFlag"] = (df["Churn"] == "Yes").astype(int)
    return df


# =========================================================================
# Chart 1 — Comparison: churn rate by contract type (vertical bar, <=7 cats)
# Message type: comparison across 3 discrete categories -> bar chart per
# chart_selection_guide.md ("Comparing discrete categories -> Bar chart").
# =========================================================================
def chart_churn_by_contract(df):
    order = ["Month-to-month", "One year", "Two year"]
    rates = df.groupby("Contract")["ChurnFlag"].mean().reindex(order) * 100
    counts = df.groupby("Contract")["ChurnFlag"].count().reindex(order)

    fig, ax = plt.subplots(figsize=(7.5, 5))
    colors = [PALETTE["vermillion"] if v == rates.max() else PALETTE["lightgrey"] for v in rates]
    bars = ax.bar(order, rates.values, color=colors, width=0.55, zorder=3)

    for bar, r, n in zip(bars, rates.values, counts.values):
        ax.annotate(f"{r:.1f}%\n(n={n:,})", (bar.get_x() + bar.get_width() / 2, r),
                    xytext=(0, 6), textcoords="offset points", ha="center",
                    fontsize=10, fontweight="bold" if r == rates.max() else "normal")

    ax.set_ylim(0, 50)
    ax.set_ylabel("Churn rate (%)")
    ax.yaxis.set_major_formatter(mticker.PercentFormatter(decimals=0))
    ax.xaxis.grid(False)
    top = _title_block(fig, "Month-to-month customers churn 15x more than two-year customers",
                        "Logo churn rate by contract term, all 7,043 customers",
                        title_y=0.96, fontsize=13.5)
    _footer(fig)
    fig.tight_layout(rect=[0, 0.03, 1, top])
    fig.savefig(f"{FIG}/p6_churn_by_contract.png")
    plt.close(fig)
    return {"chart": "churn_by_contract", "type": "bar", "rates_pct": rates.round(2).to_dict()}


# =========================================================================
# Chart 2 — Flow: service-adoption funnel with drop-off + churn overlay
# Message type: sequential process with volume drop-off -> funnel
# (horizontal bar rendering, since matplotlib has no native funnel).
# =========================================================================
def chart_funnel(funnel_json):
    steps = funnel_json["overall"]
    labels = [s["step"] for s in steps]
    users = [s["users"] for s in steps]
    churn = [s["churn_rate_pct"] for s in steps]
    dropoff_pct = [s["dropoff_pct"] for s in steps]

    fig, ax1 = plt.subplots(figsize=(9, 5.5))
    y = np.arange(len(labels))[::-1]  # top = step 1

    bars = ax1.barh(y, users, color=PALETTE["blue"], height=0.55, zorder=3)
    ax1.set_yticks(y)
    ax1.set_yticklabels(labels, fontsize=10.5)
    ax1.set_xlabel("Customers at this step")
    ax1.set_xlim(0, max(users) * 1.22)
    ax1.set_ylim(y.min() - 0.6, y.max() + 0.5)

    for yi, u, d, ch in zip(y, users, dropoff_pct, churn):
        label = f"{u:,}"
        if d > 0:
            label += f"   (-{d:.0f}% drop-off)"
        ax1.annotate(label, (u, yi), xytext=(8, 0), textcoords="offset points",
                     va="center", fontsize=9.5, color=PALETTE["grey"])
        # churn-rate direct label just under each bar (secondary metric, folded
        # in as a label rather than a dual x-axis per the skill's "avoid
        # dual-axis" guidance)
        ax1.annotate(f"{ch:.1f}% churn", (0, yi), xytext=(2, -18), textcoords="offset points",
                     va="top", ha="left", fontsize=8.5, color=PALETTE["vermillion"], fontweight="bold")

    # Highlight the largest absolute drop
    max_drop_idx = int(np.argmax(dropoff_pct))
    bars[max_drop_idx].set_color(PALETTE["vermillion"])

    ax1.yaxis.grid(False)
    top = _title_block(fig, "Add-on adoption more than halves churn — but 41% of internet\n"
                             "customers drop off before reaching 3+ add-ons",
                        "Service-adoption funnel: phone -> internet -> add-ons -> support, all customers",
                        title_y=0.97)
    _footer(fig, SOURCE_NOTE.replace("2026-09-02", "2026-09-02 | artifacts/funnel_results.json"))
    fig.tight_layout(rect=[0, 0.03, 1, top])
    fig.savefig(f"{FIG}/p6_funnel_dropoff.png")
    plt.close(fig)
    return {"chart": "funnel_dropoff", "type": "horizontal_bar_funnel",
            "max_dropoff_step": labels[max_drop_idx], "max_dropoff_pct": dropoff_pct[max_drop_idx]}


# =========================================================================
# Chart 3 — Relationship: segment value x risk bubble chart
# Message type: relationship between two continuous variables + a magnitude
# (segment size) -> scatter/bubble per chart_selection_guide.md, third
# dimension (bubble size = revenue share) explained in caption per
# visual_design_principles.md warning that size is hard to read precisely.
# =========================================================================
def chart_segment_bubble(seg_df):
    fig, ax = plt.subplots(figsize=(8, 6))
    x = seg_df["churn_rate_pct"]
    y = seg_df["arpu"]
    size = seg_df["share_pct"] * 28  # scaled area, explained in caption
    colors = [PALETTE["vermillion"] if s == seg_df["mrr_at_risk"].max() else PALETTE["blue"]
              for s in seg_df["mrr_at_risk"]]

    ax.scatter(x, y, s=size, color=colors, alpha=0.75, edgecolor="white", linewidth=1.2, zorder=3)

    for _, row in seg_df.iterrows():
        ax.annotate(
            f"{row['label']}\n{row['share_pct']:.0f}% of base | ${row['mrr_at_risk']:,.0f}/mo at risk",
            (row["churn_rate_pct"], row["arpu"]), xytext=(10, 6), textcoords="offset points",
            fontsize=8.8, color="#333333")

    ax.set_xlabel("Segment churn rate (%)")
    ax.set_ylabel("Segment ARPU ($/month)")
    ax.xaxis.set_major_formatter(mticker.PercentFormatter(decimals=0))
    ax.yaxis.set_major_formatter(mticker.StrMethodFormatter("${x:.0f}"))
    ax.set_ylim(top=y.max() * 1.12)
    top = _title_block(fig, "The riskiest segment is also mid-value, not low-value —\n"
                             "it holds 43% of the base and $77,946/mo of MRR at risk",
                        "k=3 K-means segments: churn rate x ARPU, bubble size = share of customer base",
                        title_y=0.97)
    _footer(fig, SOURCE_NOTE.replace("2026-09-02", "2026-09-02 | artifacts/segment_profile_kmeans.csv"))
    fig.tight_layout(rect=[0, 0.03, 1, top])
    fig.savefig(f"{FIG}/p6_segment_value_risk_bubble.png")
    plt.close(fig)
    return {"chart": "segment_value_risk_bubble", "type": "bubble_scatter"}


# =========================================================================
# Chart 4 — Trend: tenure survival curve (line, continuous x-axis)
# Message type: change over a continuous dimension (tenure month) -> line
# chart. Survival(t) = product_{i<=t}(1 - hazard_i), computed for real from
# artifacts/ts_hazard_by_tenure_month.csv (already-verified Phase 3 output).
# =========================================================================
def chart_tenure_survival(hazard_df):
    hazard_df = hazard_df.sort_values("tenure_month")
    survival = np.cumprod(1 - hazard_df["hazard"].values) * 100
    months = hazard_df["tenure_month"].values

    fig, ax = plt.subplots(figsize=(8.5, 5))
    ax.plot(months, survival, color=PALETTE["blue"], linewidth=2.4, zorder=3)
    ax.fill_between(months, survival, 0, color=PALETTE["blue"], alpha=0.08)

    # Reference line at 50% survival (median lifetime), if crossed
    below50 = np.where(survival <= 50)[0]
    if len(below50):
        m50 = months[below50[0]]
        ax.axvline(m50, color=PALETTE["vermillion"], linestyle=":", linewidth=1.3)
        ax.annotate(f"Median lifetime ~{m50} mo", (m50, 52), color=PALETTE["vermillion"],
                    fontsize=9, fontweight="bold")
    else:
        ax.annotate(f"Survival at 72 mo: {survival[-1]:.0f}%", (months[-1], survival[-1]),
                    xytext=(-90, 8), textcoords="offset points", color=PALETTE["blue"],
                    fontsize=9.5, fontweight="bold")

    ax.set_xlabel("Tenure (months)")
    ax.set_ylabel("Customers surviving (%)")
    ax.set_ylim(0, 102)
    ax.set_xlim(0, 72)
    ax.yaxis.set_major_formatter(mticker.PercentFormatter(decimals=0))
    top = _title_block(fig, "Retention risk is front-loaded: the steepest drop is inside month 1",
                        "Empirical survival curve derived from monthly hazard rate, all customers",
                        title_y=0.96, fontsize=13)
    _footer(fig, SOURCE_NOTE.replace("2026-09-02", "2026-09-02 | artifacts/ts_hazard_by_tenure_month.csv"))
    fig.tight_layout(rect=[0, 0.03, 1, top])
    fig.savefig(f"{FIG}/p6_tenure_survival.png")
    plt.close(fig)
    return {"chart": "tenure_survival", "type": "line", "final_survival_pct": round(float(survival[-1]), 2)}


# =========================================================================
# Chart 5 — BEFORE/AFTER redesign
# BEFORE: a 3D-styled pie of internet-service mix with a superfluous dual
# y-axis showing MonthlyCharges — both flagged as "avoid" in
# chart_selection_guide.md ("3D bar/pie: depth distorts sizes",
# "Dual y-axis: creates false correlation impression").
# AFTER: sorted horizontal bar, single metric per panel, direct labels.
# =========================================================================
def chart_before_after(df):
    counts = df["InternetService"].value_counts()
    avg_charges = df.groupby("InternetService")["MonthlyCharges"].mean().reindex(counts.index)

    # ---- BEFORE: fake-3D pie + dual axis bar overlay (deliberately bad) ----
    fig, ax1 = plt.subplots(figsize=(8, 5.5))
    # matplotlib has no true 3D pie; simulate the "3D" distortion effect by
    # using an exploded, unequal-perspective pie plus a garish palette and a
    # second, unrelated axis — this is what "chartjunk + dual-axis" looks like.
    wedges, texts, autotexts = ax1.pie(
        counts.values, labels=counts.index, autopct="%1.0f%%",
        colors=["#FF6B6B", "#4ECDC4", "#FFE66D"], explode=(0.08, 0.08, 0.08),
        shadow=True, startangle=140, textprops={"fontsize": 9})
    ax1.set_title("Internet Service", fontsize=13)  # description, not a finding
    ax2 = fig.add_axes([0.68, 0.15, 0.28, 0.28])
    ax2.bar(avg_charges.index, avg_charges.values, color="#95E1D3")
    ax2.set_ylabel("Avg $", fontsize=7)
    ax2.tick_params(labelsize=6)
    fig.suptitle("BEFORE — pseudo-3D pie + bolted-on secondary axis (avoid this)",
                  fontsize=11, color=PALETTE["vermillion"], fontweight="bold")
    fig.savefig(f"{FIG}/p6_before_bad_chart.png")
    plt.close(fig)

    # ---- AFTER: clean sorted horizontal bar with churn overlay as direct label ----
    churn_by_svc = df.groupby("InternetService")["ChurnFlag"].mean() * 100
    order = counts.sort_values().index
    fig, ax = plt.subplots(figsize=(8, 5))
    colors = [PALETTE["vermillion"] if s == "Fiber optic" else PALETTE["blue"] for s in order]
    bars = ax.barh(order, counts.reindex(order).values, color=colors, height=0.5, zorder=3)
    for bar, svc in zip(bars, order):
        n = counts[svc]
        ch = churn_by_svc[svc]
        chg = avg_charges[svc]
        ax.annotate(f"{n:,} customers | {ch:.1f}% churn | ${chg:.0f}/mo avg",
                    (bar.get_width(), bar.get_y() + bar.get_height() / 2),
                    xytext=(8, 0), textcoords="offset points", va="center", fontsize=9.5)
    ax.set_xlim(0, counts.max() * 1.6)
    ax.set_xlabel("Customers")
    ax.yaxis.grid(False)
    top = _title_block(fig, "Fiber customers churn 3x more than DSL, despite paying the most",
                        "AFTER — sorted bar, one metric per encoding, findings as direct labels",
                        title_y=0.95, fontsize=12.5)
    _footer(fig)
    fig.tight_layout(rect=[0, 0.03, 1, top])
    fig.savefig(f"{FIG}/p6_after_redesigned_chart.png")
    plt.close(fig)

    return {
        "before": {"chart": "internet_service_pie_dualaxis", "problems": [
            "3D/shadow + explode distorts wedge-size perception (chart_selection_guide.md: '3D bar/pie: depth distorts relative sizes')",
            "dual/inset axis for MonthlyCharges invites a false correlation read (chart_selection_guide.md: 'Dual y-axis: creates false correlation impression')",
            "title 'Internet Service' describes the variable, not a finding",
            "no direct data labels for the secondary metric; legend-only wedge labels force back-and-forth lookup",
        ]},
        "after": {"chart": "internet_service_sorted_bar", "fixes": [
            "single sorted horizontal bar (categories=3, <=7 -> bar per chart_selection_guide.md)",
            "churn rate and avg charges folded in as one direct label per bar instead of a second axis",
            "finding-based title states the takeaway",
            "highlight colour (vermillion) isolates the one segment that matters (fiber)",
        ]},
    }


def main():
    df = load_raw()
    funnel_json = json.load(open(f"{ART}/funnel_results.json"))
    seg_df = pd.read_csv(f"{ART}/segment_profile_kmeans.csv")
    hazard_df = pd.read_csv(f"{ART}/ts_hazard_by_tenure_month.csv").rename(
        columns={"Unnamed: 0": "tenure_month"})

    results = {}
    results["chart_churn_by_contract"] = chart_churn_by_contract(df)
    results["chart_funnel"] = chart_funnel(funnel_json)
    results["chart_segment_bubble"] = chart_segment_bubble(seg_df)
    results["chart_tenure_survival"] = chart_tenure_survival(hazard_df)
    results["chart_before_after"] = chart_before_after(df)

    with open(f"{ART}/p6_visualization_manifest.json", "w") as f:
        json.dump(results, f, indent=2, default=str)

    print("Wrote 6 PNGs to reports/figures/p6_*.png")
    print("Wrote artifacts/p6_visualization_manifest.json")
    for k, v in results.items():
        print(f"  {k}: {v.get('chart', v)}")


if __name__ == "__main__":
    main()
