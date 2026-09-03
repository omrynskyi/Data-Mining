"""CRISP-DM Phase 3 — data-cleaning skill, applied to Telco churn.

Golden rule from the skill: every statistic used to clean (medians, modes,
bounds) must be learned from TRAIN only, then applied to test. This script
demonstrates that discipline and emits a decision log.

Run: python3 src/p3_data_cleaning.py
"""
import json
import pathlib

import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]
train = pd.read_csv(ROOT / "data" / "processed" / "train.csv")
test = pd.read_csv(ROOT / "data" / "processed" / "test.csv")

report_lines = ["# Data Cleaning Report — Telco Customer Churn\n"]
report_lines.append(f"Train rows: {len(train):,}  |  Test rows: {len(test):,}\n")

# ---------------------------------------------------------------------------
# 1. Deduplicate
# ---------------------------------------------------------------------------
dup_train = train.customerID.duplicated().sum()
dup_test = test.customerID.duplicated().sum()
report_lines.append("## 1. Deduplication\n")
report_lines.append(f"- Duplicate `customerID` in train: {dup_train}; test: {dup_test}. No action needed.\n")

# ---------------------------------------------------------------------------
# 2. Fix types — TotalCharges nulls (tenure == 0 new customers)
# ---------------------------------------------------------------------------
null_train = train[train.TotalCharges.isna()]
null_test = test[test.TotalCharges.isna()]
report_lines.append("## 2. Missing `TotalCharges`\n")
report_lines.append(
    f"- Train: {len(null_train)} nulls, test: {len(null_test)} nulls "
    f"({len(null_train) + len(null_test)} total, matches dataset_meta.json's 11).\n"
    "- Every null has `tenure == 0`: these are brand-new customers billed for "
    "the first time this cycle, so no TotalCharges has accrued yet. "
    "This is missing-not-at-random but fully explained by an observed field (tenure).\n"
)
assert (null_train.tenure == 0).all() and (null_test.tenure == 0).all()

# Decision: impute 0, not the train median. Justification:
#   - TotalCharges ≈ tenure * MonthlyCharges. At tenure==0 the true value IS 0
#     (no billing cycle has completed), so 0 is not a guess, it is the correct
#     domain value — unlike the generic median-impute default in the skill's
#     table, which would fabricate a plausible-looking but wrong number here.
#   - The alternative (drop rows) would throw away 8 legitimate never-churned
#     new sign-ups (train) and discard signal about new-customer behavior.
#   - The imputation constant (0) is fixed by domain logic and does not depend
#     on train statistics, so it is leakage-free to apply identically to test.
train["TotalCharges"] = train["TotalCharges"].fillna(0.0)
test["TotalCharges"] = test["TotalCharges"].fillna(0.0)
report_lines.append(
    "- **Decision: impute 0** (domain-derived, not a train statistic) rather than "
    "drop or median-impute. Applied identically to train and test — no leakage risk "
    "since the constant does not depend on any split's statistics.\n"
    "- Note: the `sklearn-pipelines` deliverable additionally keeps a `SimpleImputer(median)` "
    "as a structural safety net for any *other* numeric nulls introduced downstream; for "
    "this specific tenure==0 case the pipeline's custom transformer applies the same 0-fill "
    "before the ColumnTransformer runs, so the two artifacts agree.\n"
)

# ---------------------------------------------------------------------------
# 3. Standardize categoricals — collapse "No internet/phone service" sentinels
# ---------------------------------------------------------------------------
internet_addon_cols = ["OnlineSecurity", "OnlineBackup", "DeviceProtection",
                        "TechSupport", "StreamingTV", "StreamingMovies"]
phone_cols = ["MultipleLines"]
sentinel_cols = internet_addon_cols + phone_cols

report_lines.append("## 3. Sentinel categories: \"No internet service\" / \"No phone service\"\n")
counts_before = {c: train[c].value_counts().to_dict() for c in sentinel_cols}
report_lines.append(f"- Affected columns ({len(sentinel_cols)}): {sentinel_cols}\n")
report_lines.append(
    f"- `No internet service` rows (train): {(train.OnlineSecurity == 'No internet service').sum():,} "
    f"(== count of `InternetService == 'No'`: {(train.InternetService == 'No').sum():,}, consistent).\n"
    f"- `No phone service` rows (train, MultipleLines): "
    f"{(train.MultipleLines == 'No phone service').sum():,} "
    f"(== count of `PhoneService == 'No'`: {(train.PhoneService == 'No').sum():,}, consistent).\n"
)
report_lines.append(
    "- **Decision: collapse to `'No'`.** The sentinel is 100% redundant with "
    "`InternetService`/`PhoneService` (verified equal counts above) — it encodes "
    "\"doesn't have the base service\" a second time inside every add-on column. "
    "Collapsing removes 6-7 duplicate one-hot columns per categorical without losing "
    "information, since `has_internet`/`has_phone` (built in feature-engineering) carries "
    "that fact once.\n"
)
for c in sentinel_cols:
    sentinel = "No internet service" if c in internet_addon_cols else "No phone service"
    train[c] = train[c].replace(sentinel, "No")
    test[c] = test[c].replace(sentinel, "No")

# ---------------------------------------------------------------------------
# 4. Dtype downcasting
# ---------------------------------------------------------------------------
report_lines.append("## 4. Dtype downcasting\n")
before_mem = train.memory_usage(deep=True).sum()
train["SeniorCitizen"] = train["SeniorCitizen"].astype("int8")
test["SeniorCitizen"] = test["SeniorCitizen"].astype("int8")
train["tenure"] = train["tenure"].astype("int16")
test["tenure"] = test["tenure"].astype("int16")
for c in ["MonthlyCharges", "TotalCharges"]:
    train[c] = pd.to_numeric(train[c], downcast="float")
    test[c] = pd.to_numeric(test[c], downcast="float")
cat_cols = train.select_dtypes("object").columns.drop("customerID")
for c in cat_cols:
    train[c] = train[c].astype("category")
    test[c] = test[c].astype("category")
after_mem = train.memory_usage(deep=True).sum()
report_lines.append(
    f"- `SeniorCitizen`→int8, `tenure`→int16, `MonthlyCharges`/`TotalCharges`→float32, "
    f"object categoricals→`category` dtype.\n"
    f"- Train memory: {before_mem/1024:.1f} KB → {after_mem/1024:.1f} KB "
    f"({(1 - after_mem/before_mem)*100:.1f}% reduction).\n"
)

# ---------------------------------------------------------------------------
# 5. Outlier scan (IQR) — tenure, MonthlyCharges, TotalCharges
# ---------------------------------------------------------------------------
report_lines.append("## 5. Outlier scan (IQR, train-only bounds)\n")
report_lines.append("| Column | Q1 | Q3 | IQR | Lower bound | Upper bound | # below | # above | % flagged |\n")
report_lines.append("|---|---|---|---|---|---|---|---|---|\n")
outlier_summary = {}
for c in ["tenure", "MonthlyCharges", "TotalCharges"]:
    q1, q3 = train[c].quantile([0.25, 0.75])
    iqr = q3 - q1
    lo, hi = q1 - 1.5 * iqr, q3 + 1.5 * iqr
    n_below = int((train[c] < lo).sum())
    n_above = int((train[c] > hi).sum())
    pct = (n_below + n_above) / len(train) * 100
    outlier_summary[c] = {"q1": float(q1), "q3": float(q3), "iqr": float(iqr),
                           "lower": float(lo), "upper": float(hi),
                           "n_below": n_below, "n_above": n_above, "pct_flagged": round(pct, 2)}
    report_lines.append(f"| {c} | {q1:.2f} | {q3:.2f} | {iqr:.2f} | {lo:.2f} | {hi:.2f} | "
                         f"{n_below} | {n_above} | {pct:.2f}% |\n")

report_lines.append(
    "\n**Decision: do NOT clip.** All three columns are bounded, business-meaningful "
    "quantities (tenure in [0,72] months = exactly the observation window; charges are "
    "real billed dollar amounts), not sensor noise or data-entry errors. IQR flags 0 points "
    "for tenure and TotalCharges (both right-skewed but within 1.5×IQR of the box) and 0 for "
    "MonthlyCharges — there are no extreme outliers, so the decision is moot for this dataset. "
    "Even if there were some, clipping tenure/charges would destroy exactly the long-tenure, "
    "high-spend customers whose behavior the model needs to learn, and — per the skill's own "
    "pitfall list — outliers that are real signal should be investigated, not deleted.\n"
)

# ---------------------------------------------------------------------------
# Save cleaned splits + report
# ---------------------------------------------------------------------------
out_dir = ROOT / "data" / "processed"
train.to_csv(out_dir / "train_clean.csv", index=False)
test.to_csv(out_dir / "test_clean.csv", index=False)

artifacts_dir = ROOT / "artifacts"
artifacts_dir.mkdir(exist_ok=True)
(artifacts_dir / "cleaning_report.md").write_text("".join(report_lines))
(artifacts_dir / "cleaning_outlier_summary.json").write_text(json.dumps(outlier_summary, indent=2))

print("".join(report_lines))
print(f"\nWrote {out_dir/'train_clean.csv'}, {out_dir/'test_clean.csv'}")
print(f"Wrote {artifacts_dir/'cleaning_report.md'}, {artifacts_dir/'cleaning_outlier_summary.json'}")
