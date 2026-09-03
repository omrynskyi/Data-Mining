"""CRISP-DM Phase 3 — funnel-analysis skill, applied to Telco churn.

Models a SERVICE ADOPTION funnel (not a session/conversion funnel — this
dataset has no event log): among all customers, how many hold each
successively richer bundle of services, and what is the churn rate at each
stage? Steps are nested/cumulative (each step is a subset of the previous):

  1. has_phone            (PhoneService == 'Yes')
  2. + has_internet        (InternetService != 'No')
  3. + >=1 add-on service  (>= 1 of the 6 add-ons == 'Yes')
  4. + >=3 add-on services (>= 3 of the 6 add-ons == 'Yes')
  5. + has_support_addon   (TechSupport == 'Yes')

This reuses `funnel_analyzer.analyze_funnel()` from the skill's shipped
script for the conversion-rate/drop-off arithmetic, then adds churn-rate-
per-stage (not part of the shipped script) and a segment-by-contract
breakdown, as the skill's step 5 ("segment the funnel") prescribes.

Run: python3 src/p3_funnel_analysis.py
"""
import json
import pathlib
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / ".claude" / "skills" / "funnel-analysis" / "scripts"))
from funnel_analyzer import analyze_funnel, format_report  # noqa: E402

FIG_DIR = ROOT / "reports" / "figures"
ARTIFACTS = ROOT / "artifacts"
FIG_DIR.mkdir(parents=True, exist_ok=True)
ARTIFACTS.mkdir(exist_ok=True)

train = pd.read_csv(ROOT / "data" / "processed" / "train_clean.csv")
ADDON_COLS = ["OnlineSecurity", "OnlineBackup", "DeviceProtection",
              "TechSupport", "StreamingTV", "StreamingMovies"]

STEPS = ["Has phone", "+ Has internet", "+ >=1 add-on", "+ >=3 add-ons", "+ Support add-on"]


def build_funnel_flags(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    n_addon = (df[ADDON_COLS] == "Yes").sum(axis=1)
    df["step1"] = df["PhoneService"] == "Yes"
    df["step2"] = df["step1"] & (df["InternetService"] != "No")
    df["step3"] = df["step2"] & (n_addon >= 1)
    df["step4"] = df["step2"] & (n_addon >= 3)
    df["step5"] = df["step4"] & (df["TechSupport"] == "Yes")
    return df


def funnel_and_churn(df: pd.DataFrame) -> tuple[list, pd.DataFrame]:
    df = build_funnel_flags(df)
    counts = [int(df[f"step{i}"].sum()) for i in range(1, 6)]
    result = analyze_funnel(STEPS, counts)
    churn_rates = [round(df.loc[df[f"step{i}"], "Churn"].mean() * 100, 2) for i in range(1, 6)]
    for r, cr in zip(result, churn_rates):
        r["churn_rate_pct"] = cr
    return result, df


overall_result, flagged = funnel_and_churn(train)

report = ["# Funnel Analysis Report — Telco Service Adoption Funnel\n\n"]
report.append("## Overall funnel\n\n")
report.append(format_report(overall_result, "Service Adoption Funnel"))
report.append("\n\n| Step | Users | Step Conv % | Overall Conv % | Churn rate % |\n|---|---|---|---|---|\n")
for r in overall_result:
    report.append(f"| {r['step']} | {r['users']:,} | {r['step_conversion_pct']:.1f}% | "
                  f"{r['overall_conversion_pct']:.1f}% | {r['churn_rate_pct']:.2f}% |\n")

baseline_churn = train.Churn.mean() * 100
report.append(f"\nBaseline churn rate (all customers): **{baseline_churn:.2f}%**\n\n")
report.append(
    "Churn rate RISES as customers move deeper into the funnel through step 2 (adding internet), "
    "then FALLS steadily as they accumulate add-ons and support — i.e. add-on-rich, "
    "internet+support bundles are associated with materially lower churn than the base "
    "phone-or-bare-internet population, consistent with add-ons and support acting as retention "
    "levers (or as a marker of more engaged/price-tolerant customers).\n\n"
)

# ---------------------------------------------------------------------------
# Segment by contract type
# ---------------------------------------------------------------------------
report.append("## Segmented by contract type\n\n")
segment_summary = {}
for contract in ["Month-to-month", "One year", "Two year"]:
    sub = train[train.Contract == contract]
    result, _ = funnel_and_churn(sub)
    segment_summary[contract] = result
    report.append(f"### {contract} (n={len(sub):,})\n\n")
    report.append("| Step | Users | Step Conv % | Overall Conv % | Churn rate % |\n|---|---|---|---|---|\n")
    for r in result:
        report.append(f"| {r['step']} | {r['users']:,} | {r['step_conversion_pct']:.1f}% | "
                      f"{r['overall_conversion_pct']:.1f}% | {r['churn_rate_pct']:.2f}% |\n")
    report.append("\n")

report.append(
    "**Segment comparison**: Month-to-month customers have both the lowest overall funnel "
    f"conversion to the fully-loaded bundle (step 5) and the highest churn rate at every stage — "
    "the funnel and the churn-driver analysis point at the same lever: contract length, not "
    "service depth alone, is the dominant retention factor (see `p3_root_cause_investigation.py` "
    "and `p3_ab_test_analysis.py` for the quantified Contract effect).\n"
)

(ARTIFACTS / "funnel_analysis_report.md").write_text("".join(report))
(ARTIFACTS / "funnel_results.json").write_text(json.dumps({
    "overall": overall_result,
    "by_contract": segment_summary,
    "baseline_churn_pct": round(baseline_churn, 2),
}, indent=2))

# ---------------------------------------------------------------------------
# Visual
# ---------------------------------------------------------------------------
fig, ax1 = plt.subplots(figsize=(10, 6))
users = [r["users"] for r in overall_result]
churn = [r["churn_rate_pct"] for r in overall_result]
ax1.bar(STEPS, users, color="steelblue", alpha=0.7, label="Users at stage")
ax1.set_ylabel("Users", color="steelblue")
ax1.tick_params(axis="x", rotation=20)
ax2 = ax1.twinx()
ax2.plot(STEPS, churn, color="crimson", marker="o", lw=2, label="Churn rate %")
ax2.axhline(baseline_churn, color="gray", ls="--", lw=1, label="Baseline churn rate")
ax2.set_ylabel("Churn rate %", color="crimson")
ax1.set_title("Service Adoption Funnel: Volume and Churn Rate by Stage")
fig.legend(loc="upper right", bbox_to_anchor=(0.9, 0.88))
plt.tight_layout()
plt.savefig(FIG_DIR / "funnel_volume_churn.png", dpi=130)
plt.close()

print("".join(report))
print(f"\nSaved {ARTIFACTS/'funnel_analysis_report.md'}, {ARTIFACTS/'funnel_results.json'}")
print(f"Saved {FIG_DIR/'funnel_volume_churn.png'}")
