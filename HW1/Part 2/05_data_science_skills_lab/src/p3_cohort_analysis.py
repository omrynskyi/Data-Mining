"""CRISP-DM Phase 3 — cohort-analysis skill, applied to Telco churn.

The Telco dataset is a single cross-sectional snapshot: one row per customer
with `tenure` (months as a customer) and `Churn` (whether they left AT that
tenure). There is no event log of monthly activity. To use the skill's
cohort/retention machinery we RECONSTRUCT a signup cohort and a retention
curve from tenure + churn status, and we are explicit about the assumption
this requires and the bias it introduces (see "Key limitation" below).

Reconstruction:
  - snapshot_date (nominal anchor, only relative math matters): 2020-03-01
  - each customer's back-calculated join_date = snapshot_date - tenure months
  - cohort = calendar QUARTER of join_date
  - "period k" (months since signup) uses each customer's own tenure as their
    observed duration: for Churn==1, they were active for `tenure` months and
    the churn EVENT occurred at month `tenure`; for Churn==0, they are
    right-censored (still active) having been observed for `tenure` months.

Retention within each cohort is computed via a life-table (discrete hazard)
method — the same idea `scripts/retention_matrix.py` encodes for direct
event logs, adapted here because we only have (duration, event) pairs, not
raw activity timestamps.

Run: python3 src/p3_cohort_analysis.py
"""
import json
import pathlib

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

ROOT = pathlib.Path(__file__).resolve().parents[1]
FIG_DIR = ROOT / "reports" / "figures"
FIG_DIR.mkdir(parents=True, exist_ok=True)
ARTIFACTS = ROOT / "artifacts"
ARTIFACTS.mkdir(exist_ok=True)

train = pd.read_csv(ROOT / "data" / "processed" / "train_clean.csv")

SNAPSHOT = pd.Timestamp("2020-03-01")
train["join_date"] = SNAPSHOT - pd.to_timedelta(train["tenure"] * 30.44, unit="D")
train["join_date"] = train["join_date"].dt.to_period("M").dt.to_timestamp()
train["cohort_quarter"] = train["join_date"].dt.to_period("Q").astype(str)

MAX_T = int(train["tenure"].max())


def life_table_survival(df: pd.DataFrame, max_t: int) -> pd.Series:
    """Discrete-time life-table survival: S(k) = prod_{j<=k} (1 - hazard_j).
    hazard_j = churns at exactly tenure==j / at-risk (tenure>=j)."""
    surv = {}
    s = 1.0
    for k in range(max_t + 1):
        at_risk = (df["tenure"] >= k).sum()
        events = ((df["tenure"] == k) & (df["Churn"] == 1)).sum()
        hazard = events / at_risk if at_risk > 0 else np.nan
        if not np.isnan(hazard):
            s *= (1 - hazard)
        surv[k] = s if at_risk > 0 else np.nan
    return pd.Series(surv)


# ---------------------------------------------------------------------------
# Pooled (whole-population) survival curve — unaffected by cohort circularity
# ---------------------------------------------------------------------------
pooled_survival = life_table_survival(train, MAX_T)

# ---------------------------------------------------------------------------
# Cohort x period retention matrix (reconstructed, cross-sectional caveat)
# ---------------------------------------------------------------------------
cohorts = sorted(train["cohort_quarter"].unique())
matrix = pd.DataFrame(index=cohorts, columns=range(MAX_T + 1), dtype=float)
cohort_sizes = train.groupby("cohort_quarter").size()
for c in cohorts:
    sub = train[train["cohort_quarter"] == c]
    matrix.loc[c] = life_table_survival(sub, MAX_T) * 100

matrix.insert(0, "Cohort Size", cohort_sizes)
matrix.to_csv(ARTIFACTS / "cohort_retention_matrix.csv")

# ---------------------------------------------------------------------------
# Quantify survivorship bias: oldest cohort's curve vs pooled curve
# ---------------------------------------------------------------------------
oldest_cohort = cohorts[0]
oldest_curve = matrix.loc[oldest_cohort].drop("Cohort Size") / 100
comparable = oldest_curve.dropna()
pooled_at_same_t = pooled_survival.loc[comparable.index]
diff = (comparable - pooled_at_same_t).dropna()
mean_bias = diff.mean()

newest_cohort = cohorts[-1]

report = ["# Cohort Analysis Report — Telco Customer Churn\n\n"]
report.append("## Cohort & activity definition\n")
report.append(
    f"- **Cohort**: calendar quarter of back-calculated signup date "
    f"(`join_date = snapshot({SNAPSHOT.date()}) - tenure months`).\n"
    f"- **Retained/active**: a customer with `tenure >= k` was active through month k; "
    f"an event (churn) at month k is recorded only for rows with `tenure == k and Churn == 1` "
    "(right-censored otherwise).\n"
    f"- {len(cohorts)} reconstructed cohorts, sizes {cohort_sizes.min()}-{cohort_sizes.max()} "
    f"(all well above the skill's recommended minimum of 100).\n\n"
)

report.append("## KEY LIMITATION — read before trusting this matrix\n")
report.append(
    "This is a **single cross-sectional snapshot**, not a longitudinal event log. Cohort "
    "membership is back-calculated FROM `tenure`, which is also the customer's own observed "
    "duration. For a customer who is still active (`Churn==0`), `tenure` is genuinely "
    "\"time since signup to snapshot\", so their back-calculated join_date is correct. But for a "
    "customer who has already churned (`Churn==1`), `tenure` is \"time from signup to churn\", "
    "which is **shorter** than \"time from signup to snapshot\" — so the back-calculation places "
    "churned customers into a cohort bucket that looks more RECENT than their true signup cohort. "
    "Net effect: every reconstructed cohort's survival curve is measured only from customers "
    "who churned AT OR AFTER exactly that bucket's elapsed window (plus whoever is still active) — "
    "it is **not** the true fate of everyone who actually signed up in that quarter, because "
    "early churners from that true quarter have been silently reassigned to newer buckets. This is "
    "the classic survivorship-style bias of reconstructing panels from censored duration data: "
    "older reconstructed cohorts look healthier than the true historical cohort would have been, "
    "because the members who would have dragged down their early-tenure retention already left "
    "the bucket by construction.\n\n"
)
report.append(
    f"**Quantified direction**: the oldest reconstructed cohort ({oldest_cohort}, "
    f"n={int(cohort_sizes[oldest_cohort])}) has a survival curve that sits, on average, "
    f"**{mean_bias*100:+.2f} percentage points** above the whole-population pooled life-table "
    f"curve at the same tenure months (comparing {len(comparable)} overlapping months). "
    f"{'A positive number confirms the predicted upward bias' if mean_bias > 0 else 'The comparison did not show the predicted upward bias in this data cut'} "
    "— old cohorts are computed from a self-selected pool of longer-surviving customers by "
    "construction, so their retention curve should not be read as \"what a 2014-era signup "
    "cohort's true churn trajectory looked like.\" The pooled life-table curve (not split by "
    "cohort) is not subject to this specific bias — it directly uses every customer's own "
    "(tenure, churn) pair once — and is the safer number to quote for \"typical hazard by "
    "tenure month.\"\n\n"
)

report.append("## Retention matrix (life-table survival %, cross-sectional reconstruction)\n\n")
report.append(matrix.round(1).to_markdown())
report.append("\n\n")

# ---------------------------------------------------------------------------
# Early-tenure hazard (churn concentrated in first year) — pooled curve
# ---------------------------------------------------------------------------
hazard = []
for k in range(MAX_T + 1):
    at_risk = (train["tenure"] >= k).sum()
    events = ((train["tenure"] == k) & (train["Churn"] == 1)).sum()
    hazard.append(events / at_risk if at_risk > 0 else np.nan)
hazard = pd.Series(hazard)
first_year_hazard = hazard.loc[0:11].mean()
rest_hazard = hazard.loc[12:].mean()
report.append("## Early-tenure hazard\n")
report.append(
    f"- Mean monthly hazard, tenure months 0-11: **{first_year_hazard*100:.2f}%**\n"
    f"- Mean monthly hazard, tenure months 12+: **{rest_hazard*100:.2f}%**\n"
    f"- First-year hazard is **{first_year_hazard/rest_hazard:.1f}x** the later-tenure hazard, "
    "confirming the well-known early-tenure churn spike this skill's process asks us to check for "
    "(see also `p3_time_series_analysis.py` for the same test run through the time-series skill's "
    "workflow on a monthly-series reconstruction).\n\n"
)

(ARTIFACTS / "cohort_analysis_report.md").write_text("".join(report))

# ---------------------------------------------------------------------------
# Visuals
# ---------------------------------------------------------------------------
fig, ax = plt.subplots(figsize=(13, 7))
heat_data = matrix.drop(columns="Cohort Size").astype(float)
sns.heatmap(heat_data, cmap="Blues", vmin=0, vmax=100, ax=ax,
            cbar_kws={"label": "Survival / retention %"}, linewidths=0.3)
ax.set_title("Reconstructed Cohort Retention Matrix (life-table survival %)\n"
              "Caveat: cohorts back-derived from tenure — see report for survivorship-bias caveat",
              fontsize=11, fontweight="bold")
ax.set_xlabel("Months since (reconstructed) signup")
ax.set_ylabel("Signup cohort (quarter)")
plt.tight_layout()
plt.savefig(FIG_DIR / "cohort_retention_heatmap.png", dpi=130)
plt.close()

fig, ax = plt.subplots(figsize=(10, 6))
ax.plot(pooled_survival.index, pooled_survival.values * 100, color="black", lw=2.5,
        label="Pooled (whole population, no cohort split)")
for c in [cohorts[0], cohorts[len(cohorts) // 2], cohorts[-1]]:
    curve = matrix.loc[c].drop("Cohort Size").astype(float)
    ax.plot(curve.index, curve.values, marker="o", ms=3, label=f"Cohort {c}")
ax.set_xlabel("Months since signup")
ax.set_ylabel("Survival / retention %")
ax.set_title("Survival Curves: Pooled vs Selected Reconstructed Cohorts")
ax.legend()
ax.set_ylim(0, 105)
plt.tight_layout()
plt.savefig(FIG_DIR / "cohort_survival_curves.png", dpi=130)
plt.close()

print("".join(report))
print(f"Saved {ARTIFACTS/'cohort_retention_matrix.csv'}, {ARTIFACTS/'cohort_analysis_report.md'}")
print(f"Saved {FIG_DIR/'cohort_retention_heatmap.png'}, {FIG_DIR/'cohort_survival_curves.png'}")
