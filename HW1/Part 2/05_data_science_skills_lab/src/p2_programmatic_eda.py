"""
Phase 2 - Data Understanding: programmatic-eda skill.

Runs the skill's own scripts (data_overview, null_profiler, outlier_detector,
distribution_summary, correlation_explorer) against the raw Telco CSV, using a
minimally-cleaned copy (TotalCharges coerced to numeric, Churn kept as Yes/No
so distribution scripts see it as categorical) so the profiling pass reflects
what an analyst would actually see on first contact with this file.

Outputs (under artifacts/programmatic_eda/):
  data_overview.txt, null_profile.csv, null_profile.txt,
  outliers.csv, outliers.txt, distribution_summary.csv, distribution_summary.txt,
  correlation_strong_pairs.csv, correlation.txt
Figure: reports/figures/p2_correlation_heatmap.png
"""
import pathlib
import subprocess
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]
SKILL = ROOT / ".claude" / "skills" / "programmatic-eda" / "scripts"
OUT = ROOT / "artifacts" / "programmatic_eda"
OUT.mkdir(parents=True, exist_ok=True)
FIG = ROOT / "reports" / "figures"
FIG.mkdir(parents=True, exist_ok=True)

raw = ROOT / "data" / "Telco-Customer-Churn.csv"
df = pd.read_csv(raw)
df["TotalCharges"] = pd.to_numeric(df["TotalCharges"].str.strip(), errors="coerce")

# working copy the skill scripts operate on (numeric TotalCharges, everything else as-shipped)
work_csv = OUT / "_working_copy.csv"
df.to_csv(work_csv, index=False)


def run(script, args, out_txt):
    cmd = [sys.executable, str(SKILL / script)] + args
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT)
    (OUT / out_txt).write_text(result.stdout + ("\n" + result.stderr if result.stderr else ""))
    print(f"--- {script} ---")
    print(result.stdout[:2000])
    if result.returncode != 0:
        print("STDERR:", result.stderr, file=sys.stderr)
    return result.stdout


# 1. Structural overview
run("data_overview.py", ["--input", str(work_csv), "--sample", "5"], "data_overview.txt")

# 2. Null profile
run("null_profiler.py", ["--input", str(work_csv), "--warn-pct", "5", "--fail-pct", "30",
                          "--output", str(OUT / "null_profile.csv")], "null_profile.txt")

# 3. Outlier detection (IQR + z-score) on numeric columns
run("outlier_detector.py", ["--input", str(work_csv), "--method", "both",
                             "--output", str(OUT / "outliers.csv")], "outliers.txt")

# 4. Distribution summary
run("distribution_summary.py", ["--input", str(work_csv), "--bins", "12",
                                 "--output", str(OUT / "distribution_summary.csv")], "distribution_summary.txt")

# 5. Correlation exploration (numeric only: SeniorCitizen, tenure, MonthlyCharges, TotalCharges)
run("correlation_explorer.py", ["--input", str(work_csv), "--threshold", "0.5",
                                 "--output", str(OUT / "correlation_strong_pairs.csv")], "correlation.txt")

# Correlation heatmap figure (numeric columns)
num = df.select_dtypes("number")
corr = num.corr()
fig, ax = plt.subplots(figsize=(5.5, 4.5))
im = ax.imshow(corr, vmin=-1, vmax=1, cmap="RdBu_r")
ax.set_xticks(range(len(corr.columns)))
ax.set_xticklabels(corr.columns, rotation=45, ha="right", fontsize=8)
ax.set_yticks(range(len(corr.columns)))
ax.set_yticklabels(corr.columns, fontsize=8)
for i in range(len(corr.columns)):
    for j in range(len(corr.columns)):
        ax.text(j, i, f"{corr.iloc[i, j]:.2f}", ha="center", va="center", fontsize=8)
ax.set_title("Numeric correlation matrix (raw CSV)")
fig.colorbar(im, ax=ax, shrink=0.8)
fig.tight_layout()
fig.savefig(FIG / "p2_correlation_heatmap.png", dpi=130)
plt.close(fig)

work_csv.unlink()  # keep artifacts dir clean of the intermediate copy
print("\nDone. Outputs in", OUT, "and figure in", FIG / "p2_correlation_heatmap.png")
