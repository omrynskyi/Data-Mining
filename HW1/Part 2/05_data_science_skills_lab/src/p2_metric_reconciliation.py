"""
Phase 2 - Data Understanding: metric-reconciliation skill.

Two real, independent sources for the same two metrics (churn rate, MRR):
  Source A = raw CSV, loaded fresh with pandas (data/Telco-Customer-Churn.csv)
  Source B = SQLite database, queried with SQL (artifacts/telco.db, built by p2_sql_setup.py)
  Source C = processed stratified train/test split, recombined (data/processed/{train,test}.csv)

Step 1: reconcile all three sources under the SAME metric definition (all 7,043 customers) —
expected to match exactly, since they're the same underlying data. This is the "clean"
reconciliation baseline.

Step 2: deliberately introduce one realistic definitional difference — churn rate and MRR
computed over ALL customers vs. computed EXCLUDING the 11 tenure==0 (never-billed) customers —
and reconcile the resulting delta line by line, per the skill's Step 5 (Analyze Discrepancies)
and Step 6 (Investigate Root Causes).
"""
import json
import pathlib
import sqlite3

import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "artifacts" / "metric_reconciliation"
OUT.mkdir(parents=True, exist_ok=True)


def compute_metrics(df: pd.DataFrame, label: str) -> dict:
    n = len(df)
    n_churned = int((df["Churn"] == "Yes").sum())
    churn_rate = n_churned / n
    mrr = float(df.loc[df["Churn"] == "No", "MonthlyCharges"].sum())
    n_active = int((df["Churn"] == "No").sum())
    return {"source": label, "n_customers": n, "n_churned": n_churned,
            "churn_rate": churn_rate, "n_active": n_active, "mrr": round(mrr, 2)}


# ---------------------------------------------------------------------------
# Source A: raw CSV via pandas
raw = pd.read_csv(ROOT / "data" / "Telco-Customer-Churn.csv")
raw["TotalCharges"] = pd.to_numeric(raw["TotalCharges"].str.strip(), errors="coerce")
metrics_a_all = compute_metrics(raw, "A: raw CSV (pandas), ALL customers")

# Source B: SQLite DB via SQL
conn = sqlite3.connect(ROOT / "artifacts" / "telco.db")
sql_all = """
SELECT
    COUNT(*) AS n_customers,
    SUM(CASE WHEN Churn='Yes' THEN 1 ELSE 0 END) AS n_churned,
    1.0*SUM(CASE WHEN Churn='Yes' THEN 1 ELSE 0 END)/COUNT(*) AS churn_rate,
    SUM(CASE WHEN Churn='No' THEN 1 ELSE 0 END) AS n_active,
    ROUND(SUM(CASE WHEN Churn='No' THEN MonthlyCharges ELSE 0 END), 2) AS mrr
FROM customers;
"""
row_b = pd.read_sql_query(sql_all, conn).iloc[0]
metrics_b_all = {"source": "B: SQLite DB (SQL), ALL customers", "n_customers": int(row_b.n_customers),
                  "n_churned": int(row_b.n_churned), "churn_rate": float(row_b.churn_rate),
                  "n_active": int(row_b.n_active), "mrr": float(row_b.mrr)}

# Source C: processed train+test split, recombined
train = pd.read_csv(ROOT / "data" / "processed" / "train.csv")
test = pd.read_csv(ROOT / "data" / "processed" / "test.csv")
combined = pd.concat([train, test], ignore_index=True)
# train/test already have Churn recoded to 0/1 int by 00_foundation.py — normalize back to Yes/No
# for a metric definition identical to Source A/B, to make the comparison apples-to-apples.
combined["Churn"] = combined["Churn"].map({1: "Yes", 0: "No"})
metrics_c_all = compute_metrics(combined, "C: train+test recombined (pandas), ALL customers")

baseline = pd.DataFrame([metrics_a_all, metrics_b_all, metrics_c_all])
baseline.to_csv(OUT / "step1_baseline_reconciliation.csv", index=False)
print("=== Step 1: baseline reconciliation (same definition, 3 sources) ===")
print(baseline.to_string(index=False))

max_churn_rate_spread = baseline["churn_rate"].max() - baseline["churn_rate"].min()
max_mrr_spread = baseline["mrr"].max() - baseline["mrr"].min()
print(f"\nChurn rate spread across sources: {max_churn_rate_spread:.10f} "
      f"({'MATCH' if max_churn_rate_spread < 1e-9 else 'MISMATCH'})")
print(f"MRR spread across sources: ${max_mrr_spread:.2f} "
      f"({'MATCH' if abs(max_mrr_spread) < 0.01 else 'MISMATCH'})")

# ---------------------------------------------------------------------------
# Step 2: deliberate definitional difference — ALL customers vs EXCLUDING tenure==0
print("\n=== Step 2: introducing a definitional difference (ALL vs EXCL. tenure==0) ===")

metrics_a_excl = compute_metrics(raw[raw["tenure"] != 0], "A: raw CSV, EXCLUDING tenure==0 (11 rows)")

sql_excl = sql_all.replace("FROM customers;", "FROM customers WHERE tenure != 0;")
row_b_excl = pd.read_sql_query(sql_excl, conn).iloc[0]
metrics_b_excl = {"source": "B: SQLite DB, EXCLUDING tenure==0 (11 rows)",
                   "n_customers": int(row_b_excl.n_customers), "n_churned": int(row_b_excl.n_churned),
                   "churn_rate": float(row_b_excl.churn_rate), "n_active": int(row_b_excl.n_active),
                   "mrr": float(row_b_excl.mrr)}

delta_df = pd.DataFrame([metrics_a_all, metrics_a_excl])
delta_df.to_csv(OUT / "step2_definitional_difference.csv", index=False)
print(delta_df.to_string(index=False))

# Line-by-line bridge: Source A (ALL) -> adjustments -> Source A (EXCL tenure==0)
tenure0 = raw[raw["tenure"] == 0]
n_tenure0 = len(tenure0)
n_tenure0_churned = int((tenure0["Churn"] == "Yes").sum())
n_tenure0_active = int((tenure0["Churn"] == "No").sum())
tenure0_active_charges = float(tenure0.loc[tenure0["Churn"] == "No", "MonthlyCharges"].sum())

churn_rate_delta = metrics_a_excl["churn_rate"] - metrics_a_all["churn_rate"]
mrr_delta = metrics_a_excl["mrr"] - metrics_a_all["mrr"]

bridge = {
    "metric": "churn_rate",
    "source_A_value_ALL": metrics_a_all["churn_rate"],
    "adjustment_removed_rows": n_tenure0,
    "adjustment_removed_churned": n_tenure0_churned,
    "adjustment_removed_active": n_tenure0_active,
    "source_A_value_EXCL_tenure0": metrics_a_excl["churn_rate"],
    "delta": churn_rate_delta,
    "delta_pct_points": churn_rate_delta * 100,
}
bridge_mrr = {
    "metric": "mrr",
    "source_A_value_ALL": metrics_a_all["mrr"],
    "adjustment_removed_active_customers": n_tenure0_active,
    "adjustment_removed_monthly_charges_sum": round(tenure0_active_charges, 2),
    "source_A_value_EXCL_tenure0": metrics_a_excl["mrr"],
    "delta": round(mrr_delta, 2),
}
(OUT / "step2_numeric_bridge.json").write_text(json.dumps({"churn_rate": bridge, "mrr": bridge_mrr}, indent=2))
print("\n=== Numeric bridge: Source A (ALL) -> adjustments -> Source A (EXCL tenure==0) ===")
print(json.dumps({"churn_rate": bridge, "mrr": bridge_mrr}, indent=2))

conn.close()
print(f"\nOutputs written to {OUT}")
