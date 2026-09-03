"""Independent verification harness.

Recomputes headline claims straight from the raw Kaggle CSV and checks them
against what the lab's artifacts assert. This deliberately does NOT import any
lab code -- if a phase script had a bug, importing it would reproduce the bug.
Exit code 1 if any check fails.
"""
import json, hashlib, pathlib, sys
import pandas as pd, numpy as np
from scipy.stats import chi2_contingency, pointbiserialr

ROOT = pathlib.Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "Telco-Customer-Churn.csv"
EXPECTED_SHA = "16320c9c1ec72448db59aa0a26a0b95401046bef5d02fd3aeb906448e3055e91"

checks = []
def check(name, got, want, tol=None, note=""):
    if tol is None:
        ok = got == want
    else:
        ok = want is not None and abs(got - want) <= tol
    checks.append((name, got, want, ok, note))

df = pd.read_csv(RAW)
df["TotalCharges"] = pd.to_numeric(df.TotalCharges.astype(str).str.strip(), errors="coerce")
churn = df.Churn.eq("Yes")

check("raw sha256", hashlib.sha256(RAW.read_bytes()).hexdigest(), EXPECTED_SHA)
check("row count", len(df), 7043)
check("col count", df.shape[1], 21)
check("duplicate customerIDs", int(df.customerID.duplicated().sum()), 0)
check("TotalCharges nulls", int(df.TotalCharges.isna().sum()), 11)
check("nulls are exactly tenure==0", int((df.TotalCharges.isna() & df.tenure.ne(0)).sum()), 0)

# --- business metrics vs artifacts/business_metrics.json -------------------
bm_path = ROOT / "artifacts" / "business_metrics.json"
bm = json.loads(bm_path.read_text()) if bm_path.exists() else {}
def find(d, *keys):
    """Locate the first numeric value under any of `keys`, at any nesting depth."""
    if isinstance(d, dict):
        for k, v in d.items():
            if k in keys and isinstance(v, (int, float)):
                return float(v)
        for v in d.values():
            r = find(v, *keys)
            if r is not None:
                return r
    return None

check("MRR (all)", round(df.MonthlyCharges.sum(), 2), find(bm, "mrr_all_customers", "mrr_total", "mrr"), tol=0.01)
check("ARPU", round(df.MonthlyCharges.mean(), 2), find(bm, "arpu_all_customers", "arpu", "arpu_monthly"), tol=0.01)
check("logo churn rate %", round(churn.mean() * 100, 3), 26.537, tol=0.001)
check("revenue churn %", round(df.loc[churn, "MonthlyCharges"].sum() / df.MonthlyCharges.sum() * 100, 3), 30.503, tol=0.001)
check("revenue at risk (realized)", round(df.loc[churn, "MonthlyCharges"].sum(), 2), 139130.85, tol=0.01)

# --- churn by contract ------------------------------------------------------
by_c = df.groupby("Contract").Churn.apply(lambda s: (s == "Yes").mean() * 100).round(2)
check("churn Month-to-month %", by_c["Month-to-month"], 42.71, tol=0.01)
check("churn One year %", by_c["One year"], 11.27, tol=0.01)
check("churn Two year %", by_c["Two year"], 2.83, tol=0.01)

# --- leakage verdict --------------------------------------------------------
d = df.dropna(subset=["TotalCharges"])
r_implied = np.corrcoef(d.TotalCharges, d.tenure * d.MonthlyCharges)[0, 1]
check("corr(TotalCharges, tenure*MonthlyCharges)", round(r_implied, 4), 0.9996, tol=0.0002)
max_target_corr = max(abs(np.corrcoef(d[c], d.Churn.eq("Yes").astype(int))[0, 1])
                      for c in ["tenure", "MonthlyCharges", "TotalCharges"])
check("no numeric feature |corr|>0.95 with target (leak test)", bool(max_target_corr < 0.95), True)

# --- association effect sizes ----------------------------------------------
def cramers_v(a, b):
    ct = pd.crosstab(a, b)
    return float(np.sqrt((chi2_contingency(ct)[0] / ct.values.sum()) / (min(ct.shape) - 1)))
check("Cramer's V Contract (full data)", round(cramers_v(df.Contract, df.Churn), 3), 0.405, tol=0.02)
check("Cramer's V gender ~ 0 (negative finding)", bool(cramers_v(df.gender, df.Churn) < 0.02), True)
check("point-biserial tenure", round(pointbiserialr(churn.astype(int), df.tenure)[0], 3), -0.352, tol=0.02)

# --- fiber anomaly ----------------------------------------------------------
fib = df.InternetService.eq("Fiber optic")
check("fiber churn %", round(churn[fib].mean() * 100, 2), 41.89, tol=0.02)
check("non-fiber churn %", round(churn[~fib].mean() * 100, 2), 14.49, tol=0.02)

# --- split integrity --------------------------------------------------------
tr = pd.read_csv(ROOT / "data/processed/train.csv")
te = pd.read_csv(ROOT / "data/processed/test.csv")
check("train+test == raw rows", len(tr) + len(te), 7043)
check("no train/test ID overlap", len(set(tr.customerID) & set(te.customerID)), 0)
check("stratification held (<0.5pp)", bool(abs(tr.Churn.mean() - te.Churn.mean()) * 100 < 0.5), True)

# --- final model metrics sanity (if present) --------------------------------
fm_path = ROOT / "artifacts" / "final_metrics.json"
if fm_path.exists():
    fm = json.loads(fm_path.read_text())
    auc = find(fm, "roc_auc", "test_roc_auc")
    pra = find(fm, "pr_auc", "average_precision", "test_pr_auc")
    if auc is not None:
        check("roc_auc plausible (0.75-0.90 for this dataset)", bool(0.75 <= auc <= 0.90), True,
              note=f"got {auc:.4f}; >0.90 on Telco churn usually means leakage")
    if pra is not None:
        check("pr_auc above 0.2654 no-skill baseline", bool(pra > 0.2654), True, note=f"got {pra:.4f}")
else:
    checks.append(("final_metrics.json present", False, True, None, "phase 4/5 still running"))

# --- report -----------------------------------------------------------------
w = max(len(n) for n, *_ in checks)
failed = 0
for name, got, want, ok, note in checks:
    if ok is None:
        mark = "SKIP"
    elif ok:
        mark = "PASS"
    else:
        mark = "FAIL"; failed += 1
    line = f"[{mark}] {name:<{w}}  got={got!r}"
    if not ok and want is not None:
        line += f"  expected={want!r}"
    if note:
        line += f"   # {note}"
    print(line)
print(f"\n{len(checks)-failed-sum(1 for c in checks if c[3] is None)} passed, "
      f"{failed} failed, {sum(1 for c in checks if c[3] is None)} skipped")
sys.exit(1 if failed else 0)
