"""CRISP-DM Phase 3 — ab-test-analysis skill, applied to Telco churn.

IMPORTANT: Telco Customer Churn is OBSERVATIONAL cross-sectional data — there
was never a randomized experiment. This script does NOT pretend otherwise.
Two honest, separate parts, per the brief:

  (a) TEST DESIGN — spec a real FUTURE experiment ("offer a 1-year contract
      discount to month-to-month Fiber customers") using the skill's power-
      analysis formula and guardrails, on the measured baseline rate.
  (b) OBSERVATIONAL ANALYSIS — run the skill's significance-test machinery
      (`ab_test_analyzer.py`) on the existing Contract groups as if they were
      experiment arms, get the same numbers a real A/B report would show,
      then explicitly flag why the naive causal reading is invalid (no
      randomization — contract choice is customer self-selected) and show a
      covariate-adjusted (tenure-stratified) comparison demonstrating how
      the "effect" changes once a confound is controlled.

Run: python3 src/p3_ab_test_analysis.py
"""
import json
import math
import pathlib
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / ".claude" / "skills" / "ab-test-analysis" / "scripts"))
from ab_test_analyzer import srm_check, analyze_binary_metric, format_report  # noqa: E402

FIG_DIR = ROOT / "reports" / "figures"
ARTIFACTS = ROOT / "artifacts"
FIG_DIR.mkdir(parents=True, exist_ok=True)
ARTIFACTS.mkdir(exist_ok=True)

train = pd.read_csv(ROOT / "data" / "processed" / "train_clean.csv")

report = ["# A/B Test Analysis — Telco Customer Churn\n\n"]
report.append(
    "**This dataset is observational, cross-sectional customer data. There was no randomized "
    "experiment.** Part (a) below specs a real future test. Part (b) runs the skill's analysis "
    "machinery on the existing Contract groups purely to demonstrate the mechanics, and then "
    "explains — with a quantified covariate adjustment — why treating that comparison as a causal "
    "A/B result would be wrong.\n\n"
)

# ---------------------------------------------------------------------------
# (a) Test design: power analysis for a FUTURE experiment
# ---------------------------------------------------------------------------
report.append("## (a) Test design — future experiment\n\n")
report.append(
    "**Hypothesis**: Offering a 1-year-contract discount to month-to-month (M2M) Fiber "
    "customers reduces their churn rate.\n\n"
    "- **Population**: M2M + Fiber optic customers.\n"
    "- **Randomization unit**: customer (customerID).\n"
    "- **Primary metric**: churn within the observation window (proxy for the dataset's own "
    "cross-sectional churn indicator).\n"
    "- **Guardrail metrics**: ARPU (monthly revenue per user — a discount that saves customers "
    "but craters revenue is not a win) and complaint/support-ticket rate (not available in this "
    "dataset; flagged as a required addition before launch).\n"
    "- **Traffic split**: 50/50.\n\n"
)

m2m_fiber = train[(train.Contract == "Month-to-month") & (train.InternetService == "Fiber optic")]
baseline_p = m2m_fiber.Churn.mean()
baseline_n = len(m2m_fiber)
report.append(f"- **Measured baseline churn rate** (M2M Fiber customers, current population): "
              f"**{baseline_p*100:.2f}%** (n={baseline_n:,}).\n\n")


def required_n_per_group(p, mde, alpha=0.05, power=0.80):
    z_alpha = 1.96 if alpha == 0.05 else 2.576
    z_beta = 0.84 if power == 0.80 else 1.2816
    return math.ceil(2 * (z_alpha + z_beta) ** 2 * p * (1 - p) / mde ** 2)


report.append("### Required sample size (skill's formula: n = 2(z_a/2+z_b)^2 p(1-p)/MDE^2)\n\n")
report.append("| MDE (absolute pp reduction) | Target rate | n per group | Total n |\n"
               "|---|---|---|---|\n")
mde_scenarios = [0.03, 0.05, 0.08, 0.10]
sample_sizes = {}
for mde in mde_scenarios:
    n = required_n_per_group(baseline_p, mde)
    sample_sizes[mde] = n
    report.append(f"| {mde*100:.0f}pp | {(baseline_p-mde)*100:.1f}% | {n:,} | {n*2:,} |\n")

smallest_powered_mde = min(mde for mde in mde_scenarios if sample_sizes[mde] <= baseline_n // 2)
report.append(
    f"\n- Current M2M-Fiber population is {baseline_n:,} customers — a 50/50 split gives "
    f"{baseline_n//2:,} per arm. Reading the table above, the smallest MDE with a per-group "
    f"requirement at or below {baseline_n//2:,} is **{smallest_powered_mde*100:.0f}pp** "
    f"(needs {sample_sizes[smallest_powered_mde]:,}/arm) — that is the finest effect this "
    "population can power today without waiting to accumulate more sign-ups; a 5pp MDE test "
    f"would need {sample_sizes[0.05]:,}/arm, i.e. expanding eligibility beyond pure M2M-Fiber "
    "or running long enough to grow the eligible pool.\n\n"
    "**Guardrails**: stop and do not ship if ARPU per M2M-Fiber customer drops more than the "
    "discount's own cost, or if the treatment group's support-ticket rate rises significantly. "
    "**SRM check**: run `srm_check()` on realized vs intended 50/50 allocation after randomization "
    "executes; flag if p < 0.01 (see the skill's own guidance — do not interpret results if SRM "
    "is detected).\n\n"
)

# ---------------------------------------------------------------------------
# (b) Observational analysis: Contract as if it were an experiment arm
# ---------------------------------------------------------------------------
report.append("## (b) Observational analysis — Contract groups run through the skill's analyzer\n\n")

m2m = train[train.Contract == "Month-to-month"]
two_yr = train[train.Contract == "Two year"]
n_m2m, conv_m2m = len(m2m), int(m2m.Churn.sum())
n_2yr, conv_2yr = len(two_yr), int(two_yr.Churn.sum())

srm = srm_check(n_m2m, n_2yr, expected_split=0.5)
result = analyze_binary_metric(n_m2m, conv_m2m, n_2yr, conv_2yr, alpha=0.05)
report.append("```\n" + format_report(srm, result, "churn (M2M vs Two-year, as if A/B arms)") + "\n```\n\n")

report.append(
    "**SRM check is not meaningful here** — SRM detects broken RANDOMIZATION (bot filtering, "
    "stickiness bugs, etc.). There was no randomization: customers *chose* their contract length. "
    "The group-size imbalance above (M2M n vs Two-year n) reflects real self-selection into "
    "contract type, not an assignment bug, so the SRM chi-square result is reported for "
    "completeness only and carries no diagnostic meaning in this context.\n\n"
    f"**The naive causal read** — \"switching a customer from month-to-month to a two-year "
    f"contract would cut their churn probability by {abs(result['relative_lift_pct']):.1f}%\" — "
    "**is invalid.** Contract choice is confounded with everything that makes a customer "
    "committed in the first place: tenure, price sensitivity, service type, and (unobserved) "
    "satisfaction. The z-test above is measuring an association between two self-selected "
    "populations, not the causal effect of a contract-length intervention.\n\n"
)

# ---------------------------------------------------------------------------
# Covariate-adjusted comparison, stratified by tenure bucket
# ---------------------------------------------------------------------------
report.append("### Covariate-adjusted comparison — stratified by tenure bucket\n\n")
bins = [-1, 12, 24, 48, 72]
labels = ["0-12mo", "13-24mo", "25-48mo", "49-72mo"]
train["tenure_stratum"] = pd.cut(train["tenure"], bins=bins, labels=labels)

strat_rows = []
for stratum in labels:
    sub = train[train.tenure_stratum == stratum]
    sub_m2m = sub[sub.Contract == "Month-to-month"]
    sub_2yr = sub[sub.Contract == "Two year"]
    if len(sub_m2m) < 10 or len(sub_2yr) < 10:
        continue
    r_m2m, r_2yr = sub_m2m.Churn.mean(), sub_2yr.Churn.mean()
    strat_rows.append({
        "tenure_stratum": stratum,
        "n_m2m": len(sub_m2m), "churn_m2m_pct": round(r_m2m * 100, 2),
        "n_2yr": len(sub_2yr), "churn_2yr_pct": round(r_2yr * 100, 2),
        "abs_diff_pp": round((r_m2m - r_2yr) * 100, 2),
    })
strat_df = pd.DataFrame(strat_rows)
report.append(strat_df.to_markdown(index=False))

# Use a consistent sign convention throughout this section: M2M rate minus
# Two-year rate (matches the stratified table above). Note this is the
# NEGATIVE of `result["absolute_diff"]` printed in the analyzer block above,
# which follows the skill's own control->treatment convention
# (Two-year - M2M); both describe the same gap, just with opposite sign.
unadjusted_diff = (m2m.Churn.mean() - two_yr.Churn.mean()) * 100
# Weighted-average within-stratum difference (standardized to overall tenure distribution)
weights = train["tenure_stratum"].value_counts(normalize=True)
adjusted_diff = sum(row["abs_diff_pp"] * weights.get(row["tenure_stratum"], 0) for row in strat_rows)

report.append(
    f"\n\n- **Unadjusted** M2M-vs-Two-year churn gap: **{unadjusted_diff:+.2f} pp**.\n"
    f"- **Tenure-adjusted** (within-stratum gaps, weighted by overall tenure distribution): "
    f"**{adjusted_diff:+.2f} pp**.\n"
    f"- The gap {'shrinks' if abs(adjusted_diff) < abs(unadjusted_diff) else 'stays similar or grows'} "
    f"after controlling for tenure ({unadjusted_diff:+.2f}pp -> {adjusted_diff:+.2f}pp), which is "
    "exactly what the skill's guidance asks us to check: even after removing the part of the "
    "raw gap that tenure alone explains (long-tenured customers are both more likely to be on a "
    "long contract AND less likely to churn, mechanically, since surviving long enough to renew "
    "requires not having churned), a large gap remains within every tenure stratum — Contract "
    "length still looks associated with lower churn even among comparably-tenured customers, "
    "but the true causal share of that remaining gap cannot be established without a "
    "randomized test (part (a) above).\n"
)

(ARTIFACTS / "ab_test_analysis_report.md").write_text("".join(report))
(ARTIFACTS / "ab_test_sample_size_scenarios.json").write_text(json.dumps({
    "baseline_churn_rate_m2m_fiber": round(float(baseline_p), 4),
    "baseline_n_m2m_fiber": baseline_n,
    "sample_size_per_group_by_mde": {f"{k}": v for k, v in sample_sizes.items()},
    "observational_contract_comparison": {
        "srm": srm, "significance_result": result,
    },
    "unadjusted_diff_pp": round(float(unadjusted_diff), 3),
    "tenure_adjusted_diff_pp": round(float(adjusted_diff), 3),
}, indent=2, default=str))

# ---------------------------------------------------------------------------
# Visual
# ---------------------------------------------------------------------------
fig, ax = plt.subplots(figsize=(9, 5))
x = np.arange(len(strat_df))
w = 0.35
ax.bar(x - w/2, strat_df["churn_m2m_pct"], w, label="Month-to-month", color="crimson")
ax.bar(x + w/2, strat_df["churn_2yr_pct"], w, label="Two year", color="steelblue")
ax.set_xticks(x); ax.set_xticklabels(strat_df["tenure_stratum"])
ax.set_ylabel("Churn rate %")
ax.set_title(f"Contract Churn Gap by Tenure Stratum\nUnadjusted: {unadjusted_diff:+.1f}pp -> "
             f"Tenure-adjusted: {adjusted_diff:+.1f}pp")
ax.legend()
plt.tight_layout()
plt.savefig(FIG_DIR / "ab_test_tenure_adjusted.png", dpi=130)
plt.close()

print("".join(report))
print(f"\nSaved {ARTIFACTS/'ab_test_analysis_report.md'}, {ARTIFACTS/'ab_test_sample_size_scenarios.json'}")
print(f"Saved {FIG_DIR/'ab_test_tenure_adjusted.png'}")
