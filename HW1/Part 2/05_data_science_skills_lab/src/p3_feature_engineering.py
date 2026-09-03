"""CRISP-DM Phase 3 — feature-engineering skill, applied to Telco churn.

Builds the engineered feature set and demonstrates leakage-safe out-of-fold
(OOF) target encoding vs naive full-data target encoding, with real numbers.

Run: python3 src/p3_feature_engineering.py
"""
import json
import pathlib

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import KFold

ROOT = pathlib.Path(__file__).resolve().parents[1]
train = pd.read_csv(ROOT / "data" / "processed" / "train_clean.csv")
test = pd.read_csv(ROOT / "data" / "processed" / "test_clean.csv")

ADDON_COLS = ["OnlineSecurity", "OnlineBackup", "DeviceProtection",
              "TechSupport", "StreamingTV", "StreamingMovies"]


def engineer(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    # tenure_bucket — standard telco lifecycle bands
    bins = [-1, 6, 12, 24, 48, 60, 200]
    labels = ["0-6mo", "7-12mo", "13-24mo", "25-48mo", "49-60mo", "61mo+"]
    df["tenure_bucket"] = pd.cut(df["tenure"], bins=bins, labels=labels)

    # avg_monthly_spend and its gap vs the current MonthlyCharges rate.
    # tenure==0 -> TotalCharges is 0 (see data-cleaning); avg spend undefined,
    # fall back to the current MonthlyCharges rate (best available estimate).
    df["avg_monthly_spend"] = np.where(
        df["tenure"] > 0, df["TotalCharges"] / df["tenure"], df["MonthlyCharges"]
    )
    df["spend_gap"] = df["avg_monthly_spend"] - df["MonthlyCharges"]

    df["num_addon_services"] = (df[ADDON_COLS] == "Yes").sum(axis=1)
    df["has_internet"] = (df["InternetService"] != "No").astype(int)
    df["is_month_to_month"] = (df["Contract"] == "Month-to-month").astype(int)
    df["is_electronic_check"] = (df["PaymentMethod"] == "Electronic check").astype(int)

    # charges_per_service: MonthlyCharges spread over count of active services
    # (phone + internet base + add-ons), floor of 1 to avoid div-by-zero.
    n_services = (
        (df["PhoneService"] == "Yes").astype(int)
        + df["has_internet"]
        + (df[ADDON_COLS] == "Yes").sum(axis=1)
    ).clip(lower=1)
    df["charges_per_service"] = df["MonthlyCharges"] / n_services

    df["is_new_customer"] = (df["tenure"] <= 3).astype(int)
    return df


train_fe = engineer(train)
test_fe = engineer(test)

report = ["# Feature Engineering Report — Telco Customer Churn\n"]
new_cols = ["tenure_bucket", "avg_monthly_spend", "spend_gap", "num_addon_services",
            "has_internet", "is_month_to_month", "is_electronic_check",
            "charges_per_service", "is_new_customer"]
report.append(f"## Engineered features ({len(new_cols)})\n")
report.append("| Feature | dtype | Description |\n|---|---|---|\n")
descriptions = {
    "tenure_bucket": "Lifecycle band from tenure (0-6mo ... 61mo+)",
    "avg_monthly_spend": "TotalCharges / tenure (fallback: MonthlyCharges if tenure==0)",
    "spend_gap": "avg_monthly_spend - MonthlyCharges (positive = price rose vs history)",
    "num_addon_services": "Count of the 6 add-on services subscribed (0-6)",
    "has_internet": "1 if InternetService != 'No'",
    "is_month_to_month": "1 if Contract == 'Month-to-month'",
    "is_electronic_check": "1 if PaymentMethod == 'Electronic check'",
    "charges_per_service": "MonthlyCharges / count of active services",
    "is_new_customer": "1 if tenure <= 3 months",
}
for c in new_cols:
    report.append(f"| {c} | {train_fe[c].dtype} | {descriptions[c]} |\n")

report.append(f"\nSample stats (train, n={len(train_fe):,}):\n\n")
report.append(train_fe[["avg_monthly_spend", "spend_gap", "num_addon_services",
                         "charges_per_service"]].describe().round(2).to_markdown())
report.append("\n")

# ---------------------------------------------------------------------------
# Leakage-safe target encoding demo: PaymentMethod x Contract interaction
# ---------------------------------------------------------------------------
train_fe["pm_contract"] = train_fe["PaymentMethod"].astype(str) + " | " + train_fe["Contract"].astype(str)
report.append(f"\n## Target encoding demo — `PaymentMethod x Contract` interaction "
              f"({train_fe['pm_contract'].nunique()} levels)\n")

y = train_fe["Churn"].values
col = train_fe["pm_contract"]
prior = y.mean()


def naive_target_encode(col, y, prior, smoothing=10):
    """Encode using stats computed from ALL rows, including the row being encoded."""
    df = pd.DataFrame({"col": col, "y": y})
    agg = df.groupby("col")["y"].agg(["mean", "count"])
    smooth = (agg["mean"] * agg["count"] + prior * smoothing) / (agg["count"] + smoothing)
    return df["col"].map(smooth).values


def oof_target_encode(col, y, prior, n_splits=5, smoothing=10, seed=42):
    """Encode each fold using stats fit on the OTHER folds only (leakage-safe)."""
    oof = np.zeros(len(col))
    kf = KFold(n_splits=n_splits, shuffle=True, random_state=seed)
    df = pd.DataFrame({"col": col.reset_index(drop=True), "y": y})
    for tr_idx, val_idx in kf.split(df):
        agg = df.iloc[tr_idx].groupby("col")["y"].agg(["mean", "count"])
        smooth = (agg["mean"] * agg["count"] + prior * smoothing) / (agg["count"] + smoothing)
        oof[val_idx] = df.iloc[val_idx]["col"].map(smooth).fillna(prior).values
    return oof


naive_enc = naive_target_encode(col, y, prior)
oof_enc = oof_target_encode(col, y, prior)

naive_auc = roc_auc_score(y, naive_enc)
oof_auc = roc_auc_score(y, oof_enc)

# Cross-validated AUC using ONLY this single encoded feature as the score,
# evaluated on held-out folds, to show how each encoding "performs" out of
# sample. Naive encoding was fit on the same rows it scores -> inflated.
# OOF encoding was fit excluding each row's own fold -> honest.
report.append(
    f"- Naive (fit on all rows incl. the row itself) univariate AUC of the encoded "
    f"feature vs Churn: **{naive_auc:.4f}**\n"
    f"- OOF (5-fold, excluding each row's own fold) univariate AUC: **{oof_auc:.4f}**\n"
    f"- Inflation from leakage: **{(naive_auc - oof_auc):+.4f}** AUC points "
    f"({(naive_auc - oof_auc) / oof_auc * 100:+.2f}% relative).\n"
)

# A sharper, standard illustration: shuffle the target (pure noise) and show
# naive target encoding still "detects signal" out of a column with no true
# relationship to churn, purely from encoding leakage, while OOF does not.
rng = np.random.default_rng(42)
y_shuffled = rng.permutation(y)
naive_noise_auc = roc_auc_score(y_shuffled, naive_target_encode(col, y_shuffled, y_shuffled.mean()))
oof_noise_auc = roc_auc_score(y_shuffled, oof_target_encode(col, y_shuffled, y_shuffled.mean()))
report.append(
    "\n### Leakage stress test (target shuffled to pure noise)\n"
    f"- Naive encoding AUC on a column with NO real relationship to a (shuffled) target: "
    f"**{naive_noise_auc:.4f}** (should be ~0.50; leakage manufactures apparent signal)\n"
    f"- OOF encoding AUC on the same shuffled target: **{oof_noise_auc:.4f}** "
    f"(correctly stays near 0.50)\n"
)

train_fe["pm_contract_te_oof"] = oof_enc
# For test, fit the encoder on the FULL train (no leakage — test never seen)
full_agg = pd.DataFrame({"col": col, "y": y}).groupby("col")["y"].agg(["mean", "count"])
full_smooth = (full_agg["mean"] * full_agg["count"] + prior * 10) / (full_agg["count"] + 10)
test_fe["pm_contract"] = test_fe["PaymentMethod"].astype(str) + " | " + test_fe["Contract"].astype(str)
test_fe["pm_contract_te_oof"] = test_fe["pm_contract"].map(full_smooth).fillna(prior).values

out_dir = ROOT / "data" / "processed"
train_fe.to_csv(out_dir / "train_features.csv", index=False)
test_fe.to_csv(out_dir / "test_features.csv", index=False)

artifacts_dir = ROOT / "artifacts"
(artifacts_dir / "feature_engineering_report.md").write_text("".join(report))
(artifacts_dir / "target_encoding_leakage_demo.json").write_text(json.dumps({
    "naive_auc_real_target": round(float(naive_auc), 4),
    "oof_auc_real_target": round(float(oof_auc), 4),
    "inflation_auc_points": round(float(naive_auc - oof_auc), 4),
    "naive_auc_shuffled_target": round(float(naive_noise_auc), 4),
    "oof_auc_shuffled_target": round(float(oof_noise_auc), 4),
    "n_levels": int(train_fe["pm_contract"].nunique()),
}, indent=2))

print("".join(report))
print(f"\nWrote {out_dir/'train_features.csv'}, {out_dir/'test_features.csv'}")
print(f"Wrote {artifacts_dir/'feature_engineering_report.md'}, {artifacts_dir/'target_encoding_leakage_demo.json'}")
