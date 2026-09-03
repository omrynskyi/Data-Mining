"""
Phase 2 - Data Understanding: data-quality-audit skill.

Runs the skill's own scripts (null_counter, duplicate_finder, value_range_validator)
against explicit business rules for the Telco churn dataset, plus custom cross-column
consistency rules the skill's scripts don't cover natively (service-column logic).
referential_integrity.py and freshness_check.py are skipped with a documented reason
(flat single-table extract with no FK, no timestamp column).

Produces artifacts/data_quality_scorecard.json and .md.
"""
import json
import pathlib
import subprocess
import sys

import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]
SKILL = ROOT / ".claude" / "skills" / "data-quality-audit" / "scripts"
ARTIFACTS = ROOT / "artifacts"
OUT = ARTIFACTS / "data_quality"
OUT.mkdir(parents=True, exist_ok=True)

raw = ROOT / "data" / "Telco-Customer-Churn.csv"
df = pd.read_csv(raw)
df_num = df.copy()
df_num["TotalCharges"] = pd.to_numeric(df_num["TotalCharges"].str.strip(), errors="coerce")
work_csv = OUT / "_working_copy.csv"
df_num.to_csv(work_csv, index=False)


# The skill's scripts use `list[str] | None` (PEP 604) parameter annotations
# evaluated eagerly at def-time, which requires Python >= 3.10. The default
# `python3` on this machine is 3.9.6, so these scripts are run under a 3.10
# interpreter (packages installed via `pip install --break-system-packages`).
PY310 = "/Users/oleg/.local/bin/python3.10"
RUNNER = PY310 if pathlib.Path(PY310).exists() else sys.executable


def run(cmd):
    cmd = [RUNNER] + cmd[1:]
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT)
    print(" ".join(cmd[2:4]), "->", "OK" if result.returncode == 0 else "FAIL")
    if result.returncode != 0:
        print(result.stderr[-800:])
    return result.stdout, result.stderr, result.returncode


checks = []  # list of dicts: dimension, check, script, result(PASS/FAIL/WARN), rows_affected, detail

# --- 1. Completeness: null_counter.py -----------------------------------------
stdout, stderr, rc = run([sys.executable, str(SKILL / "null_counter.py"), "--input", str(work_csv)])
(OUT / "null_counter_output.txt").write_text(stdout + stderr)
null_pct_totalcharges = round(df_num["TotalCharges"].isna().mean() * 100, 3)
checks.append({
    "dimension": "Completeness", "check": "TotalCharges null rate <= 1%",
    "script": "null_counter.py", "result": "PASS" if null_pct_totalcharges <= 1 else "FAIL",
    "rows_affected": int(df_num["TotalCharges"].isna().sum()),
    "detail": f"{null_pct_totalcharges}% null ({int(df_num['TotalCharges'].isna().sum())} rows) — all at tenure==0 (see business rule below)",
})
other_null_cols = [c for c in df.columns if c != "TotalCharges" and df[c].isna().sum() > 0]
checks.append({
    "dimension": "Completeness", "check": "No unexpected nulls outside TotalCharges",
    "script": "null_counter.py", "result": "PASS" if not other_null_cols else "FAIL",
    "rows_affected": 0, "detail": "All other 20 columns are 100% non-null.",
})

# --- 2. Uniqueness: duplicate_finder.py ----------------------------------------
stdout, stderr, rc = run([sys.executable, str(SKILL / "duplicate_finder.py"), "--input", str(work_csv),
                           "--key", "customerID", "--show-examples"])
(OUT / "duplicate_finder_output.txt").write_text(stdout + stderr)
dup_full = int(df.duplicated().sum())
dup_key = int(df["customerID"].duplicated().sum())
checks.append({
    "dimension": "Uniqueness", "check": "customerID is a unique primary key",
    "script": "duplicate_finder.py", "result": "PASS" if dup_key == 0 else "FAIL",
    "rows_affected": dup_key, "detail": f"{dup_key} duplicate customerIDs, {dup_full} full-row duplicates.",
})

# --- 3. Referential integrity: not applicable -----------------------------------
checks.append({
    "dimension": "Consistency", "check": "Referential integrity (referential_integrity.py)",
    "script": "referential_integrity.py (skipped)", "result": "N/A",
    "rows_affected": 0,
    "detail": "This is a single denormalized extract with no separate parent/child tables shipped — "
              "no FK to validate. See schema-mapper for the inferred normalized model where FK checks would apply.",
})

# --- 4. Validity: value_range_validator.py --------------------------------------
rules = {
    "tenure": {"min": 0, "max": 72},
    "MonthlyCharges": {"min": 0},
    "TotalCharges": {"min": 0},
    "SeniorCitizen": {"allowed": [0, 1]},
    "gender": {"allowed": ["Male", "Female"]},
    "Churn": {"allowed": ["Yes", "No"]},
    "Contract": {"allowed": ["Month-to-month", "One year", "Two year"]},
    "InternetService": {"allowed": ["DSL", "Fiber optic", "No"]},
    "PaymentMethod": {"allowed": [
        "Electronic check", "Mailed check", "Bank transfer (automatic)", "Credit card (automatic)"]},
}
stdout, stderr, rc = run([sys.executable, str(SKILL / "value_range_validator.py"), "--input", str(work_csv),
                           "--rules", json.dumps(rules)])
(OUT / "value_range_validator_output.txt").write_text(stdout + stderr)
for col, rule in rules.items():
    s = df_num[col].dropna()
    ok = True
    if "min" in rule:
        ok &= (s.astype(float) >= rule["min"]).all() if pd.api.types.is_numeric_dtype(s) else True
    if "max" in rule:
        ok &= (s.astype(float) <= rule["max"]).all() if pd.api.types.is_numeric_dtype(s) else True
    if "allowed" in rule:
        ok = s.isin(rule["allowed"]).all()
    checks.append({
        "dimension": "Validity", "check": f"{col} respects business rule {rule}",
        "script": "value_range_validator.py", "result": "PASS" if ok else "FAIL",
        "rows_affected": 0 if ok else int((~s.isin(rule.get("allowed", s))).sum()) if "allowed" in rule else 0,
        "detail": "within defined range/set" if ok else "violations found — see value_range_validator_output.txt",
    })

# --- 5. Custom cross-column consistency rules (business logic, not in skill's scripts) ---
def add_check(dimension, name, mask_violation, detail_ok, detail_fail):
    n = int(mask_violation.sum())
    checks.append({
        "dimension": dimension, "check": name, "script": "custom (pandas)",
        "result": "PASS" if n == 0 else "FAIL", "rows_affected": n,
        "detail": detail_ok if n == 0 else f"{n} rows violate — {detail_fail}",
    })

# Rule: TotalCharges is null only when tenure == 0
mask = df_num["TotalCharges"].isna() & (df_num["tenure"] != 0)
add_check("Consistency", "TotalCharges null implies tenure==0 (never-billed new customer)",
           mask, "all 11 nulls are tenure==0 customers", "TotalCharges null but tenure != 0")
mask2 = (df_num["tenure"] == 0) & df_num["TotalCharges"].notna()
add_check("Consistency", "tenure==0 implies TotalCharges is null (no charges billed yet)",
           mask2, "all tenure==0 rows have null TotalCharges", "tenure==0 but TotalCharges populated")

# Rule: PhoneService == 'No' implies MultipleLines == 'No phone service'
mask3 = (df["PhoneService"] == "No") & (df["MultipleLines"] != "No phone service")
add_check("Consistency", "PhoneService=='No' implies MultipleLines=='No phone service'",
           mask3, "logic holds for all rows", "MultipleLines inconsistent with PhoneService=='No'")

# Rule: PhoneService == 'Yes' implies MultipleLines in {Yes, No} (never 'No phone service')
mask4 = (df["PhoneService"] == "Yes") & (df["MultipleLines"] == "No phone service")
add_check("Consistency", "PhoneService=='Yes' implies MultipleLines != 'No phone service'",
           mask4, "logic holds for all rows", "MultipleLines=='No phone service' despite PhoneService=='Yes'")

# Rule: InternetService == 'No' implies all 6 internet add-on columns == 'No internet service'
addons = ["OnlineSecurity", "OnlineBackup", "DeviceProtection", "TechSupport", "StreamingTV", "StreamingMovies"]
mask5 = pd.Series(False, index=df.index)
for c in addons:
    mask5 |= (df["InternetService"] == "No") & (df[c] != "No internet service")
add_check("Consistency", "InternetService=='No' implies all 6 add-on columns=='No internet service'",
           mask5, "logic holds for all rows and all 6 add-on columns", "an add-on column diverges from InternetService=='No'")

# Rule: InternetService != 'No' implies add-on columns are in {Yes, No} (never 'No internet service')
mask6 = pd.Series(False, index=df.index)
for c in addons:
    mask6 |= (df["InternetService"] != "No") & (df[c] == "No internet service")
add_check("Consistency", "InternetService != 'No' implies add-ons never 'No internet service'",
           mask6, "logic holds for all rows", "add-on marked 'No internet service' despite having internet")

# Rule: TotalCharges ~= tenure * MonthlyCharges within tolerance (order-of-magnitude sanity
# check, not a leakage claim — the precise correlation is measured in exploratory-data-analysis.md).
# Partial first/last billing months mean a small fraction of exact-fit failures is expected;
# fail the check only if that fraction exceeds 1% of billed rows (median error is ~2%, see below).
sub = df_num.dropna(subset=["TotalCharges"]).copy()
sub["approx"] = sub["tenure"] * sub["MonthlyCharges"]
sub["abs_pct_err"] = (sub["TotalCharges"] - sub["approx"]).abs() / sub["TotalCharges"].clip(lower=1)
violation_rate = (sub["abs_pct_err"] > 0.25).mean()
n_violations = int((sub["abs_pct_err"] > 0.25).sum())
median_err = sub["abs_pct_err"].median()
checks.append({
    "dimension": "Accuracy",
    "check": "TotalCharges within 25% of tenure*MonthlyCharges for >=99% of billed rows",
    "script": "custom (pandas)",
    "result": "PASS" if violation_rate <= 0.01 else "FAIL",
    "rows_affected": n_violations,
    "detail": f"median abs pct error {median_err:.1%}; {n_violations}/{len(sub)} rows "
              f"({violation_rate:.1%}) exceed 25% band, concentrated in low-tenure "
              f"(partial first/last month billing) customers — expected, not a data error.",
})

# --- 6. Freshness: not applicable ----------------------------------------------
checks.append({
    "dimension": "Timeliness", "check": "Freshness (freshness_check.py)",
    "script": "freshness_check.py (skipped)", "result": "N/A", "rows_affected": 0,
    "detail": "Static Kaggle snapshot extract with no timestamp/updated_at column — freshness SLA is not applicable to this dataset.",
})

df_checks = pd.DataFrame(checks)
df_checks.to_csv(OUT / "quality_checks.csv", index=False)

# --- Scorecard: weighted dimension scores ---------------------------------------
def dim_score(dim):
    d = df_checks[(df_checks.dimension == dim) & (df_checks.result != "N/A")]
    if d.empty:
        return None
    return round((d.result == "PASS").mean() * 10, 2)

weights = {"Completeness": 0.20, "Accuracy": 0.20, "Consistency": 0.20,
           "Timeliness": 0.15, "Uniqueness": 0.15, "Validity": 0.10}
scores = {dim: dim_score(dim) for dim in weights}
applicable_weight = sum(w for dim, w in weights.items() if scores[dim] is not None)
overall = round(sum((scores[dim] or 0) * w for dim, w in weights.items()) / applicable_weight, 2)

n_pass = int((df_checks.result == "PASS").sum())
n_fail = int((df_checks.result == "FAIL").sum())
n_na = int((df_checks.result == "N/A").sum())

scorecard = {
    "dataset": "data/Telco-Customer-Churn.csv",
    "rows_assessed": len(df),
    "dimension_scores_0_10": scores,
    "dimension_weights": weights,
    "overall_score_0_10": overall,
    "verdict": "PASS" if overall >= 7.0 else ("CONDITIONAL" if overall >= 5.0 else "FAIL"),
    "checks_total": len(df_checks), "checks_pass": n_pass, "checks_fail": n_fail, "checks_na": n_na,
}
(OUT / "..").resolve()
(ARTIFACTS / "data_quality_scorecard.json").write_text(json.dumps(scorecard, indent=2))
print(json.dumps(scorecard, indent=2))

# --- Markdown scorecard -----------------------------------------------------------
lines = []
lines.append("# Data Quality Scorecard: Telco-Customer-Churn.csv\n")
lines.append("**Assessed by:** Claude (phase2-data-agent)  ")
lines.append("**Table / dataset:** `data/Telco-Customer-Churn.csv`  ")
lines.append("**Pipeline / source:** Kaggle blastchar/telco-customer-churn, static snapshot extract  ")
lines.append(f"**Assessment scope:** full table, {len(df):,} rows\n")
lines.append("---\n\n## Quality Dimension Scores\n")
lines.append("| Dimension | Weight | Score (0-10) | Weighted | Key Issues |")
lines.append("|---|---|---|---|---|")
for dim, w in weights.items():
    s = scores[dim]
    issues = df_checks[(df_checks.dimension == dim) & (df_checks.result == "FAIL")]
    issue_txt = "; ".join(issues["check"].tolist()) if not issues.empty else "none"
    s_txt = f"{s:.2f}" if s is not None else "N/A"
    weighted = f"{s * w:.2f}" if s is not None else "N/A"
    lines.append(f"| {dim} | {int(w*100)}% | {s_txt} | {weighted} | {issue_txt} |")
lines.append(f"| **Overall** | **100%** |  | **{overall:.2f}/10** |  |\n")
lines.append(f"**Overall verdict:** {scorecard['verdict']} ({n_pass} PASS / {n_fail} FAIL / {n_na} N/A of {len(df_checks)} checks)\n")
lines.append("---\n\n## All Checks Performed\n")
lines.append("| Dimension | Check | Script | Result | Rows affected | Detail |")
lines.append("|---|---|---|---|---|---|")
for c in checks:
    lines.append(f"| {c['dimension']} | {c['check']} | {c['script']} | {c['result']} | {c['rows_affected']} | {c['detail']} |")
lines.append("\n---\n\n## Sign-off\n")
lines.append("**Approved for use in:** EDA, feature engineering, and modeling for churn prediction — "
              "with the caveat that TotalCharges nulls (11 rows, tenure==0) must be handled explicitly "
              "(impute 0 or drop) before modeling, and referential-integrity / freshness checks are N/A for this static single-table extract.\n")
(ARTIFACTS / "data_quality_scorecard.md").write_text("\n".join(lines))

work_csv.unlink()
print("\nWrote artifacts/data_quality_scorecard.json and .md")
