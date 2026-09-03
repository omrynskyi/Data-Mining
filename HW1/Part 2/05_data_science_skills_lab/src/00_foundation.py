"""Shared substrate for the skills lab: canonical typing + stratified split.
Deliberately minimal - the real cleaning/feature work is done by the
data-cleaning / feature-engineering / sklearn-pipelines skills downstream."""
import pandas as pd, numpy as np, json, hashlib, pathlib
from sklearn.model_selection import train_test_split

SEED = 42
ROOT = pathlib.Path(__file__).resolve().parents[1]
raw = ROOT / "data" / "Telco-Customer-Churn.csv"

df = pd.read_csv(raw)
sha = hashlib.sha256(raw.read_bytes()).hexdigest()

# TotalCharges ships as object: 11 blank strings for tenure==0 customers.
df["TotalCharges"] = pd.to_numeric(df["TotalCharges"].str.strip(), errors="coerce")
df["Churn"] = (df["Churn"] == "Yes").astype(int)

train, test = train_test_split(df, test_size=0.20, random_state=SEED, stratify=df["Churn"])
out = ROOT / "data" / "processed"
train.to_csv(out / "train.csv", index=False)
test.to_csv(out / "test.csv", index=False)

meta = {
    "source": "Kaggle blastchar/telco-customer-churn (IBM Telco Customer Churn)",
    "raw_sha256": sha, "rows": len(df), "cols": df.shape[1], "seed": SEED,
    "churn_rate_overall": round(df.Churn.mean(), 6),
    "churn_rate_train": round(train.Churn.mean(), 6),
    "churn_rate_test": round(test.Churn.mean(), 6),
    "n_train": len(train), "n_test": len(test),
    "totalcharges_nulls_after_coercion": int(df.TotalCharges.isna().sum()),
    "duplicate_customerIDs": int(df.customerID.duplicated().sum()),
}
(ROOT / "data" / "processed" / "dataset_meta.json").write_text(json.dumps(meta, indent=2))
print(json.dumps(meta, indent=2))
