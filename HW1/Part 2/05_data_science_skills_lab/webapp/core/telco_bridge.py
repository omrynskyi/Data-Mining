"""Bridge into the real, already-completed CRISP-DM Telco Customer Churn lab.

Nothing here is recomputed -- every number is read from real JSON/CSV artifacts
already produced at the project root by the CRISP-DM phases, or from the real
trained model artifact. This mirrors the exact, already-debugged inference
contract used by src/p6_serve.py (see artifacts/serving_smoke_test.md).
"""
import json
import sys
from functools import lru_cache
from pathlib import Path

import joblib
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
ARTIFACTS = PROJECT_ROOT / "artifacts"

sys.path.insert(0, str(PROJECT_ROOT / "src"))  # model.joblib pickles reference p3_pipeline by module name


def _read_json(name: str) -> dict:
    return json.loads((ARTIFACTS / name).read_text())


@lru_cache(maxsize=1)
def get_inference_contract() -> dict:
    return _read_json("inference_contract.json")


@lru_cache(maxsize=1)
def load_telco_model():
    """Load the real trained model ONCE and cache it (skill's #1 pitfall: never per request)."""
    return joblib.load(ARTIFACTS / "model.joblib")


@lru_cache(maxsize=1)
def get_telco_benchmark() -> dict:
    """Assemble the real Telco benchmark view from already-computed artifacts.

    Reads business metrics (MRR, ARPU, churn), model metrics (ROC-AUC, PR-AUC, ...),
    segment profiles, campaign EV table, and fairness parity -- no recomputation.
    """
    business_metrics = _read_json("business_metrics.json")
    final_metrics = _read_json("final_metrics.json")
    business_ev = _read_json("business_expected_value.json")
    fairness = _read_json("fairness_parity.json")
    contract = get_inference_contract()

    segments_path = ARTIFACTS / "segment_profile_kmeans.csv"
    segments_df = pd.read_csv(segments_path)
    segment_profiles = segments_df.to_dict(orient="records")

    return {
        "dataset": "Kaggle Telco Customer Churn (7,043 real customers), CRISP-DM lab at project root",
        "business_metrics": business_metrics,
        "model_metrics": final_metrics,
        "segment_profiles": segment_profiles,
        "campaign_expected_value": business_ev,
        "fairness_parity": fairness,
        "inference_contract_summary": {
            "chosen_threshold": contract["output"]["chosen_threshold"],
            "decision_rule": contract["output"]["decision_rule"],
            "risk_bands": contract["output"]["risk_bands"],
            "required_columns": contract["input"]["required_columns"],
        },
    }


def coerce_total_charges(df: pd.DataFrame) -> pd.DataFrame:
    """Real, already-discovered bug fix: TotalCharges must be pre-coerced to numeric
    before scoring. The pipeline's FeatureEngineer checks TotalCharges.isna(), which
    is a no-op on a string column, so the raw string/blank column must be coerced by
    the caller first.
    """
    df = df.copy()
    df["TotalCharges"] = pd.to_numeric(
        df["TotalCharges"].astype(str).str.strip(), errors="coerce"
    )
    return df


def predict_churn(records: list[dict]) -> list[dict]:
    """Score real customer records with the real trained model.

    records: list of dicts matching artifacts/inference_contract.json's required_columns
    (customerID optional, passthrough).
    """
    model = load_telco_model()
    contract = get_inference_contract()
    threshold = contract["output"]["chosen_threshold"]

    df = pd.DataFrame(records)
    df = coerce_total_charges(df)
    X = df.drop(columns=["customerID"], errors="ignore")

    proba = model.predict_proba(X)[:, 1]

    out = []
    ids = df.get("customerID", pd.Series([None] * len(df)))
    for cid, p in zip(ids, proba):
        p = float(p)
        if p >= threshold:
            band = "high"
        elif p >= threshold * 0.5:
            band = "medium"
        else:
            band = "low"
        out.append({
            "customerID": cid,
            "probability": round(p, 4),
            "risk_band": band,
            "flagged": bool(p >= threshold),
        })
    return out
