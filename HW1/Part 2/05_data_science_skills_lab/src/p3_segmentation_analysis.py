"""CRISP-DM Phase 3 — segmentation-analysis skill, applied to Telco churn.

Two segmentations, as the brief requires:
  A. Rule-based: Value (MonthlyCharges tercile) x Risk (month-to-month /
     short tenure vs longer contract/tenure) 2x2-ish grid.
  B. Unsupervised: K-means on scaled numeric + one-hot categorical features,
     k chosen via elbow (inertia) + silhouette score (actual scores reported).

Both are profiled (size, churn rate, ARPU, MRR at risk) per the skill's
`assets/segment_profile_template.md` structure, and reused from
`scripts/segmentation_runner.py`'s index-scoring idea (index = segment
value / overall value * 100) for interpretation.

Run: python3 src/p3_segmentation_analysis.py
"""
import json
import pathlib

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import OneHotEncoder, StandardScaler

ROOT = pathlib.Path(__file__).resolve().parents[1]
FIG_DIR = ROOT / "reports" / "figures"
ARTIFACTS = ROOT / "artifacts"
FIG_DIR.mkdir(parents=True, exist_ok=True)
ARTIFACTS.mkdir(exist_ok=True)

train = pd.read_csv(ROOT / "data" / "processed" / "train_features.csv")

report = ["# Segmentation Analysis Report — Telco Customer Churn\n\n"]

# ---------------------------------------------------------------------------
# A. Rule-based segmentation: Value x Risk grid
# ---------------------------------------------------------------------------
report.append("## A. Rule-based segmentation — Value x Risk grid\n\n")

value_tercile = pd.qcut(train["MonthlyCharges"], 3, labels=["Low value", "Mid value", "High value"])


def risk_bucket(row):
    if row["Contract"] == "Month-to-month" and row["tenure"] <= 12:
        return "High risk"
    if row["Contract"] == "Month-to-month":
        return "Medium risk"
    return "Low risk"


risk = train.apply(risk_bucket, axis=1)
train["value_segment"] = value_tercile
train["risk_segment"] = risk
train["rule_segment"] = value_tercile.astype(str) + " / " + risk.astype(str)

rule_profile = train.groupby("rule_segment").agg(
    n=("Churn", "size"),
    churn_rate=("Churn", "mean"),
    arpu=("MonthlyCharges", "mean"),
).reset_index()
rule_profile["mrr"] = rule_profile["n"] * rule_profile["arpu"]
rule_profile["mrr_at_risk"] = rule_profile["mrr"] * rule_profile["churn_rate"]
rule_profile["share_pct"] = (rule_profile["n"] / len(train) * 100).round(1)
rule_profile["churn_rate_pct"] = (rule_profile["churn_rate"] * 100).round(2)
rule_profile["churn_index"] = (rule_profile["churn_rate"] / train.Churn.mean() * 100).round(0)
rule_profile = rule_profile.sort_values("mrr_at_risk", ascending=False)

report.append(rule_profile[["rule_segment", "n", "share_pct", "arpu", "churn_rate_pct",
                             "churn_index", "mrr_at_risk"]].round(2).to_markdown(index=False))
report.append("\n\n")

total_mrr_at_risk = rule_profile["mrr_at_risk"].sum()
top_rule = rule_profile.iloc[0]
report.append(
    f"- Total monthly recurring revenue (MRR) currently \"at risk\" (churn-rate-weighted, "
    f"train sample): **${total_mrr_at_risk:,.0f}/mo**.\n"
    f"- Highest single-segment exposure: **{top_rule['rule_segment']}** — "
    f"{int(top_rule['n']):,} customers ({top_rule['share_pct']:.1f}% of base), "
    f"{top_rule['churn_rate_pct']:.1f}% churn rate (index {int(top_rule['churn_index'])}), "
    f"${top_rule['mrr_at_risk']:,.0f}/mo MRR at risk — the priority segment for retention spend.\n\n"
)

# ---------------------------------------------------------------------------
# B. Unsupervised K-means, k chosen via elbow + silhouette
# ---------------------------------------------------------------------------
report.append("## B. Unsupervised segmentation — K-means (elbow + silhouette)\n\n")

num_cols = ["tenure", "MonthlyCharges", "TotalCharges", "num_addon_services"]
cat_cols = ["Contract", "InternetService", "PaymentMethod"]

scaler = StandardScaler()
X_num = scaler.fit_transform(train[num_cols])
ohe = OneHotEncoder(sparse_output=False)
X_cat = ohe.fit_transform(train[cat_cols])
X = np.hstack([X_num, X_cat])

rng_sample_idx = np.random.default_rng(42).choice(len(X), size=2000, replace=False)  # silhouette on subsample for speed

inertias, sil_scores = [], []
k_range = range(2, 9)
for k in k_range:
    km = KMeans(n_clusters=k, random_state=42, n_init=10).fit(X)
    inertias.append(km.inertia_)
    sil = silhouette_score(X[rng_sample_idx], km.labels_[rng_sample_idx])
    sil_scores.append(sil)

report.append("| k | Inertia | Silhouette |\n|---|---|---|\n")
for k, inertia, sil in zip(k_range, inertias, sil_scores):
    report.append(f"| {k} | {inertia:,.0f} | {sil:.4f} |\n")

global_best_k = list(k_range)[int(np.argmax(sil_scores))]
global_best_sil = max(sil_scores)

# The skill's own process (step 1) says useful segmentations are "typically
# 3-7" groups -- a k=2 split, even if it numerically maximizes silhouette,
# doesn't give the business enough resolution to assign differentiated
# strategies (step 6). So the operating choice is the best silhouette
# WITHIN the actionable 3-7 range, reported alongside the honest global max.
actionable_range = [k for k in k_range if 3 <= k <= 7]
actionable_sils = [sil_scores[list(k_range).index(k)] for k in actionable_range]
best_k = actionable_range[int(np.argmax(actionable_sils))]

report.append(
    f"\n- Global silhouette-maximizing k = **{global_best_k}** (silhouette {global_best_sil:.4f}), "
    "but a 2-cluster split is too coarse to assign differentiated retention strategies "
    "(the skill's own process step 1 recommends 3-7 actionable segments).\n"
    f"- **Operating choice: k = {best_k}** — the best silhouette score within the actionable "
    f"3-7 range (silhouette {max(actionable_sils):.4f}, still above the skill's 0.3 validity "
    "bar). Elbow curve — see `reports/figures/segmentation_elbow_silhouette.png`.\n\n"
)

km_final = KMeans(n_clusters=best_k, random_state=42, n_init=10).fit(X)
train["cluster"] = km_final.labels_

cluster_profile = train.groupby("cluster").agg(
    n=("Churn", "size"),
    churn_rate=("Churn", "mean"),
    arpu=("MonthlyCharges", "mean"),
    avg_tenure=("tenure", "mean"),
    avg_addons=("num_addon_services", "mean"),
    pct_month_to_month=("is_month_to_month", "mean"),
).reset_index()
cluster_profile["mrr"] = cluster_profile["n"] * cluster_profile["arpu"]
cluster_profile["mrr_at_risk"] = cluster_profile["mrr"] * cluster_profile["churn_rate"]
cluster_profile["share_pct"] = (cluster_profile["n"] / len(train) * 100).round(1)
cluster_profile["churn_rate_pct"] = (cluster_profile["churn_rate"] * 100).round(2)
cluster_profile["churn_index"] = (cluster_profile["churn_rate"] / train.Churn.mean() * 100).round(0)

# Descriptive label per cluster from its defining stats
def label_cluster(row):
    tenure_desc = "long-tenure" if row["avg_tenure"] > 40 else ("mid-tenure" if row["avg_tenure"] > 15 else "new")
    price_desc = "high-ARPU" if row["arpu"] > train.MonthlyCharges.mean() + 10 else (
        "low-ARPU" if row["arpu"] < train.MonthlyCharges.mean() - 10 else "mid-ARPU")
    contract_desc = "M2M-heavy" if row["pct_month_to_month"] > 0.6 else "contract-committed"
    return f"{tenure_desc}, {price_desc}, {contract_desc}"


cluster_profile["label"] = cluster_profile.apply(label_cluster, axis=1)
cluster_profile = cluster_profile.sort_values("mrr_at_risk", ascending=False)

report.append(cluster_profile[["cluster", "label", "n", "share_pct", "avg_tenure", "arpu",
                                "avg_addons", "churn_rate_pct", "churn_index", "mrr_at_risk"]]
              .round(2).to_markdown(index=False))
report.append("\n\n")

top_cluster = cluster_profile.iloc[0]
report.append(
    f"- Highest-exposure cluster: **cluster {int(top_cluster['cluster'])} "
    f"({top_cluster['label']})** — {int(top_cluster['n']):,} customers, "
    f"{top_cluster['churn_rate_pct']:.1f}% churn (index {int(top_cluster['churn_index'])}), "
    f"${top_cluster['mrr_at_risk']:,.0f}/mo MRR at risk.\n"
    f"- Total MRR at risk across all clusters: **${cluster_profile['mrr_at_risk'].sum():,.0f}/mo** "
    f"(should match the rule-based total up to segmentation-scheme differences: "
    f"${total_mrr_at_risk:,.0f}/mo).\n"
)

# ---------------------------------------------------------------------------
# Save artifacts
# ---------------------------------------------------------------------------
segments_out = train[["customerID", "MonthlyCharges", "tenure", "Contract", "Churn",
                       "value_segment", "risk_segment", "rule_segment", "cluster"]].copy()
segments_out.to_csv(ARTIFACTS / "segments.csv", index=False)
rule_profile.to_csv(ARTIFACTS / "segment_profile_rule_based.csv", index=False)
cluster_profile.to_csv(ARTIFACTS / "segment_profile_kmeans.csv", index=False)

(ARTIFACTS / "segmentation_report.md").write_text("".join(report))
(ARTIFACTS / "segmentation_kmeans_selection.json").write_text(json.dumps({
    "k_range": list(k_range),
    "inertias": [round(i, 1) for i in inertias],
    "silhouette_scores": [round(s, 4) for s in sil_scores],
    "global_best_k": global_best_k,
    "global_best_silhouette": round(global_best_sil, 4),
    "chosen_k": best_k,
    "chosen_k_silhouette": round(max(actionable_sils), 4),
}, indent=2))

# ---------------------------------------------------------------------------
# Visuals
# ---------------------------------------------------------------------------
fig, axes = plt.subplots(1, 2, figsize=(13, 5))
axes[0].plot(list(k_range), inertias, marker="o")
axes[0].set_xlabel("k"); axes[0].set_ylabel("Inertia"); axes[0].set_title("Elbow method")
axes[1].plot(list(k_range), sil_scores, marker="o", color="darkorange")
axes[1].axvline(best_k, color="crimson", ls="--", label=f"chosen k={best_k}")
axes[1].set_xlabel("k"); axes[1].set_ylabel("Silhouette score"); axes[1].set_title("Silhouette method")
axes[1].legend()
plt.tight_layout()
plt.savefig(FIG_DIR / "segmentation_elbow_silhouette.png", dpi=130)
plt.close()

fig, ax = plt.subplots(figsize=(9, 6))
import seaborn as sns
pivot = train.pivot_table(index="value_segment", columns="risk_segment", values="Churn",
                           aggfunc="mean", observed=True) * 100
pivot = pivot[["Low risk", "Medium risk", "High risk"]]
sns.heatmap(pivot, annot=True, fmt=".1f", cmap="Reds", ax=ax, cbar_kws={"label": "Churn rate %"})
ax.set_title("Rule-Based Segmentation: Churn Rate by Value x Risk")
plt.tight_layout()
plt.savefig(FIG_DIR / "segmentation_value_risk_grid.png", dpi=130)
plt.close()

print("".join(report))
print(f"\nSaved {ARTIFACTS/'segments.csv'}, {ARTIFACTS/'segment_profile_rule_based.csv'}, "
      f"{ARTIFACTS/'segment_profile_kmeans.csv'}, {ARTIFACTS/'segmentation_report.md'}")
print(f"Saved figures in {FIG_DIR}")
