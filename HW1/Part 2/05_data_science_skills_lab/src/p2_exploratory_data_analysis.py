"""
Phase 2 - Data Understanding: exploratory-data-analysis skill (param087/agent-ml-skills).

Modeling-readiness pass, deliberately distinct from programmatic-eda (which does the
systematic structural/quality profiling). This script covers exactly what the ML-pack
skill's workflow prescribes:
  1. Target distribution + class imbalance
  2. Feature/target association: Cramer's V for categoricals, point-biserial r for numerics
  3. Multicollinearity among numeric features
  4. Explicit target-leakage scan, including a direct investigation of whether
     TotalCharges ~= tenure * MonthlyCharges (and what that would mean for leakage)

Fit strictly on the TRAIN split only (data/processed/train.csv) to avoid leaking test
information into feature-selection decisions, per the skill's Pitfalls section.
"""
import itertools
import json
import pathlib

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "artifacts" / "exploratory_data_analysis"
OUT.mkdir(parents=True, exist_ok=True)
FIG = ROOT / "reports" / "figures"
FIG.mkdir(parents=True, exist_ok=True)

train = pd.read_csv(ROOT / "data" / "processed" / "train.csv")
# train.csv already has Churn recoded to 0/1 int8-ish by 00_foundation.py
target = "Churn"
numeric_cols = ["tenure", "MonthlyCharges", "TotalCharges"]
categorical_cols = [c for c in train.columns
                     if c not in numeric_cols + [target, "customerID", "SeniorCitizen"]]
# SeniorCitizen is 0/1 but semantically categorical/binary — treat as categorical for association tests
categorical_cols = ["SeniorCitizen"] + categorical_cols

report = {}

# ---------------------------------------------------------------------------
# 1. Target distribution + imbalance
n = len(train)
n_pos = int(train[target].sum())
n_neg = n - n_pos
imbalance_ratio = n_neg / n_pos
report["target"] = {"n_train": n, "n_churn": n_pos, "n_no_churn": n_neg,
                     "churn_rate": round(n_pos / n, 6), "imbalance_ratio_neg_to_pos": round(imbalance_ratio, 3)}
print("=== 1. Target distribution ===")
print(json.dumps(report["target"], indent=2))

fig, ax = plt.subplots(figsize=(4, 4))
ax.bar(["No churn", "Churn"], [n_neg, n_pos], color=["#4C72B0", "#DD8452"])
for i, v in enumerate([n_neg, n_pos]):
    ax.text(i, v + 30, f"{v}\n({v/n:.1%})", ha="center")
ax.set_title(f"Train target distribution (n={n})\nImbalance ratio {imbalance_ratio:.2f}:1")
ax.set_ylabel("count")
fig.tight_layout()
fig.savefig(FIG / "p2_target_distribution.png", dpi=130)
plt.close(fig)

# ---------------------------------------------------------------------------
# 2a. Cramer's V for categorical features vs target
def cramers_v(x: pd.Series, y: pd.Series) -> float:
    ct = pd.crosstab(x, y)
    chi2 = stats.chi2_contingency(ct, correction=False)[0]
    n_ = ct.sum().sum()
    r, k = ct.shape
    # bias correction (Bergsma 2013)
    phi2 = chi2 / n_
    phi2corr = max(0, phi2 - (k - 1) * (r - 1) / (n_ - 1))
    rcorr = r - (r - 1) ** 2 / (n_ - 1)
    kcorr = k - (k - 1) ** 2 / (n_ - 1)
    denom = min(kcorr - 1, rcorr - 1)
    return float(np.sqrt(phi2corr / denom)) if denom > 0 else float("nan")


cramers = []
for col in categorical_cols:
    v = cramers_v(train[col].astype(str), train[target])
    ct = pd.crosstab(train[col], train[target])
    chi2, p, dof, _ = stats.chi2_contingency(ct)
    cramers.append({"feature": col, "cramers_v": round(v, 4), "chi2": round(chi2, 2),
                     "p_value": p, "dof": dof})
cramers_df = pd.DataFrame(cramers).sort_values("cramers_v", ascending=False)
cramers_df.to_csv(OUT / "cramers_v_categorical_vs_target.csv", index=False)
print("\n=== 2a. Cramer's V — categorical features vs Churn ===")
print(cramers_df.to_string(index=False))

# ---------------------------------------------------------------------------
# 2b. Point-biserial correlation for numeric features vs target
pb = []
for col in numeric_cols:
    s = train[[col, target]].dropna()
    r, p = stats.pointbiserialr(s[target], s[col])
    pb.append({"feature": col, "point_biserial_r": round(r, 4), "p_value": p, "n": len(s)})
pb_df = pd.DataFrame(pb).sort_values("point_biserial_r", key=abs, ascending=False)
pb_df.to_csv(OUT / "point_biserial_numeric_vs_target.csv", index=False)
print("\n=== 2b. Point-biserial r — numeric features vs Churn ===")
print(pb_df.to_string(index=False))

# combined ranked association figure
assoc = pd.concat([
    cramers_df.rename(columns={"cramers_v": "association"})[["feature", "association"]].assign(metric="Cramer's V"),
    pb_df.rename(columns={"point_biserial_r": "association"})[["feature", "association"]].assign(
        association=lambda d: d["association"].abs(), metric="|point-biserial r|"),
]).sort_values("association", ascending=True)
fig, ax = plt.subplots(figsize=(6, 7))
colors = assoc["metric"].map({"Cramer's V": "#4C72B0", "|point-biserial r|": "#DD8452"})
ax.barh(assoc["feature"], assoc["association"], color=colors)
ax.set_xlabel("association strength with Churn")
ax.set_title("Feature-target association (train split only)")
handles = [plt.Rectangle((0, 0), 1, 1, color=c) for c in ["#4C72B0", "#DD8452"]]
ax.legend(handles, ["Cramer's V (categorical)", "|point-biserial r| (numeric)"], loc="lower right", fontsize=8)
fig.tight_layout()
fig.savefig(FIG / "p2_feature_target_association.png", dpi=130)
plt.close(fig)

# ---------------------------------------------------------------------------
# 3. Multicollinearity among numeric features
num_corr = train[numeric_cols].corr()
num_corr.to_csv(OUT / "numeric_multicollinearity.csv")
print("\n=== 3. Multicollinearity (numeric features, train only) ===")
print(num_corr.round(4).to_string())

high_corr_pairs = []
for a, b in itertools.combinations(numeric_cols, 2):
    r = num_corr.loc[a, b]
    if abs(r) >= 0.7:
        high_corr_pairs.append({"col_a": a, "col_b": b, "r": round(r, 4)})
report["multicollinearity_flags_r_ge_0.7"] = high_corr_pairs
print("Flagged pairs (|r| >= 0.7):", high_corr_pairs)

# ---------------------------------------------------------------------------
# 4. Target-leakage scan
print("\n=== 4. Target-leakage scan ===")

# 4a. Generic leakage-suspect scan: any feature with |corr| > 0.95 with target (numeric-encoded)
corr_t = train[numeric_cols + [target]].corr()[target].drop(target).abs()
leakage_suspects_generic = corr_t[corr_t > 0.95].index.tolist()
print("Generic |corr|>0.95 leakage suspects among numeric features:", leakage_suspects_generic or "none")

# 4b. Specific investigation: TotalCharges ~= tenure * MonthlyCharges
sub = train.dropna(subset=["TotalCharges"]).copy()
sub["tenure_x_monthly"] = sub["tenure"] * sub["MonthlyCharges"]
pearson_r, pearson_p = stats.pearsonr(sub["TotalCharges"], sub["tenure_x_monthly"])
sub["abs_pct_err"] = (sub["TotalCharges"] - sub["tenure_x_monthly"]).abs() / sub["TotalCharges"].clip(lower=1)

leakage_check = {
    "hypothesis": "TotalCharges approx= tenure * MonthlyCharges",
    "pearson_r_TotalCharges_vs_tenure_x_MonthlyCharges": round(pearson_r, 6),
    "pearson_p_value": pearson_p,
    "median_abs_pct_error": round(float(sub["abs_pct_err"].median()), 4),
    "mean_abs_pct_error": round(float(sub["abs_pct_err"].mean()), 4),
    "n": len(sub),
}
report["totalcharges_leakage_check"] = leakage_check
print(json.dumps(leakage_check, indent=2))

fig, ax = plt.subplots(figsize=(5, 5))
ax.scatter(sub["tenure_x_monthly"], sub["TotalCharges"], s=4, alpha=0.3)
lims = [0, max(sub["tenure_x_monthly"].max(), sub["TotalCharges"].max())]
ax.plot(lims, lims, color="red", lw=1, label="y=x")
ax.set_xlabel("tenure x MonthlyCharges")
ax.set_ylabel("TotalCharges")
ax.set_title(f"TotalCharges vs tenure*MonthlyCharges\nPearson r={pearson_r:.4f}")
ax.legend()
fig.tight_layout()
fig.savefig(FIG / "p2_totalcharges_leakage_scatter.png", dpi=130)
plt.close(fig)

# Verdict: is this leakage?
leakage_verdict = (
    "NOT target leakage. TotalCharges and tenure/MonthlyCharges are all *pre-outcome* billing "
    "attributes known at prediction time for an existing customer -- none of them encode the "
    "Churn outcome itself (r with Churn is weak-to-moderate per point-biserial results above, "
    f"not >0.95). The near-identity relationship (Pearson r={pearson_r:.4f} between TotalCharges "
    "and tenure*MonthlyCharges) is a REDUNDANCY / multicollinearity finding, not a leakage finding: "
    "TotalCharges is almost fully reconstructible from tenure and MonthlyCharges (both already in "
    "the feature set), so it carries little independent information for a model beyond what those "
    "two columns already supply. Recommendation for Phase 3 feature-engineering: consider dropping "
    "TotalCharges or replacing it with an engineered residual "
    "(TotalCharges - tenure*MonthlyCharges, capturing plan/price changes over the customer's "
    "tenure) rather than feeding all three raw columns into a linear model, where the near-collinearity "
    "would inflate coefficient variance without leaking the target."
)
report["totalcharges_leakage_verdict"] = leakage_verdict
print("\nVERDICT:", leakage_verdict)

(OUT / "eda_ml_report.json").write_text(json.dumps(report, indent=2, default=str))
print(f"\nOutputs written to {OUT} and figures to {FIG}")
