"""CRISP-DM Phase 6 -- llm-finetuning skill.

No GPU available (CPU-only, Python 3.9). This script produces the artifacts
that genuinely precede a fine-tune -- a real, validated instruction dataset
generated from actual customer records and their real churn-risk drivers --
and stops there. Training is NOT executed; that is stated explicitly in the
doc, not implied by silence.

Use case: turn a customer's risk-model output into a retention-agent
talking-point brief -- short, specific, grounded in the customer's actual
account facts, ready to hand to a human agent before a retention call.
"""
import json, sys, random
from pathlib import Path
import pandas as pd
from transformers import AutoTokenizer

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import joblib
from p4_repro import set_all_seeds

set_all_seeds(42)
ARTIFACTS = ROOT / "artifacts"

model = joblib.load(ARTIFACTS / "model.joblib")
fm = json.loads((ARTIFACTS / "final_metrics.json").read_text())
thr = fm["chosen_threshold"]

df = pd.read_csv(ROOT / "data" / "Telco-Customer-Churn.csv")
# The pipeline's FeatureEngineer checks TotalCharges.isna() to detect the 11
# blank-string tenure==0 rows; that check only works on an already-numeric
# column, so the true raw (string) CSV must be coerced before scoring -- the
# pipeline does NOT do this itself (see inference_contract.json's corrected note).
df["TotalCharges"] = pd.to_numeric(df["TotalCharges"].astype(str).str.strip(), errors="coerce")
X = df.drop(columns=["Churn"])
proba = model.predict_proba(X)[:, 1]
df = df.assign(risk_score=proba)

SYSTEM = ("You are a retention-call briefing assistant for a telecom's customer-success team. "
          "Given a customer's account facts and churn risk score, write a concise brief a human "
          "agent can read in under 15 seconds before calling: the top 2-3 concrete risk drivers "
          "grounded ONLY in the facts given, and one suggested talking point. Never invent facts "
          "not present in the input.")


def brief_target(row):
    """Deterministic, template-grounded target -- this stands in for a human-written
    gold label. Every clause is derived from a real column value on this row, so
    the 'assistant' targets are dataset-grounded, not hallucinated."""
    drivers = []
    if row.Contract == "Month-to-month":
        drivers.append("month-to-month contract (no lock-in)")
    if row.InternetService == "Fiber optic":
        drivers.append("fiber internet plan (highest-churn segment, 41.9% base rate)")
    if row.tenure <= 6:
        drivers.append(f"new customer ({int(row.tenure)} months tenure)")
    if row.TechSupport == "No" and row.InternetService != "No":
        drivers.append("no tech support add-on")
    if row.PaymentMethod == "Electronic check":
        drivers.append("pays by electronic check (highest-churn payment method)")
    if row.MonthlyCharges > df.MonthlyCharges.median():
        drivers.append(f"above-median monthly charge (${row.MonthlyCharges:.2f})")
    if not drivers:
        drivers.append("no single dominant risk factor -- risk driven by a combination of minor signals")
    drivers = drivers[:3]

    if row.Contract == "Month-to-month" and row.tenure <= 12:
        talk = "Offer a discounted 1-year contract to convert this new month-to-month customer before the risk window closes."
    elif row.TechSupport == "No" and row.InternetService != "No":
        talk = "Offer a complimentary trial of Tech Support -- add-on customers churn at roughly half the base rate."
    elif row.PaymentMethod == "Electronic check":
        talk = "Offer to switch billing to autopay/credit card, which correlates with materially lower churn."
    else:
        talk = "Acknowledge tenure and loyalty; offer a modest retention discount tied to contract renewal."

    band = "HIGH" if row.risk_score >= thr else ("MEDIUM" if row.risk_score >= thr * 0.5 else "LOW")
    return (f"Risk: {band} ({row.risk_score:.2f}). "
            f"Key drivers: {'; '.join(drivers)}. "
            f"Suggested talking point: {talk}")


def user_msg(row):
    fields = {
        "contract": row.Contract, "internet_service": row.InternetService,
        "tenure_months": int(row.tenure), "monthly_charges": round(float(row.MonthlyCharges), 2),
        "payment_method": row.PaymentMethod, "tech_support": row.TechSupport,
        "online_security": row.OnlineSecurity, "paperless_billing": row.PaperlessBilling,
        "risk_score": round(float(row.risk_score), 4),
    }
    return "Customer account facts:\n" + json.dumps(fields, indent=2) + "\n\nWrite the brief."


records = []
for _, row in df.iterrows():
    records.append({
        "messages": [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": user_msg(row)},
            {"role": "assistant", "content": brief_target(row)},
        ]
    })

# dedup on the (user, assistant) content pair -- exact duplicates would just be
# repeated near-identical rows (e.g. two customers with identical facts)
seen, deduped = set(), []
for r in records:
    key = (r["messages"][1]["content"], r["messages"][2]["content"])
    if key not in seen:
        seen.add(key)
        deduped.append(r)
n_dropped = len(records) - len(deduped)

rng = random.Random(42)
rng.shuffle(deduped)
n_val = max(50, int(0.1 * len(deduped)))
val, train = deduped[:n_val], deduped[n_val:]

out_path = ARTIFACTS / "finetune_dataset.jsonl"
with open(out_path, "w") as f:
    for r in train:
        f.write(json.dumps({**r, "split": "train"}) + "\n")
    for r in val:
        f.write(json.dumps({**r, "split": "val"}) + "\n")

# ---- real tokenizer-based length stats (gpt2, cached locally -- offline) ----
tok = AutoTokenizer.from_pretrained("gpt2")


def n_tokens(rec):
    text = "\n".join(m["content"] for m in rec["messages"])
    return len(tok(text)["input_ids"])


lens = [n_tokens(r) for r in deduped]
stats = {
    "n_total_raw": len(records),
    "n_exact_duplicates_dropped": n_dropped,
    "n_deduped": len(deduped),
    "n_train": len(train),
    "n_val": len(val),
    "tokenizer": "gpt2 (offline cached; stand-in for the target base model's tokenizer -- "
                 "swap for the real one before training)",
    "token_len_min": min(lens),
    "token_len_max": max(lens),
    "token_len_mean": round(sum(lens) / len(lens), 1),
    "token_len_p50": sorted(lens)[len(lens) // 2],
    "token_len_p95": sorted(lens)[int(len(lens) * 0.95)],
}
(ARTIFACTS / "finetune_dataset_stats.json").write_text(json.dumps(stats, indent=2))
print(json.dumps(stats, indent=2))
print(f"\nwrote {out_path}")
