"""CRISP-DM Phase 6 -- model-serving skill.

A real FastAPI service for artifacts/model.joblib, following
artifacts/inference_contract.json exactly (including its corrected
TotalCharges-coercion requirement, discovered while building the
llm-finetuning dataset).
"""
import json, logging, sys, time, uuid
from pathlib import Path
from typing import List, Literal, Optional

import joblib
import numpy as np
import pandas as pd
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, Field, field_validator

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))  # model.joblib pickles reference p3_pipeline by module name

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
log = logging.getLogger("churn-serving")

CONTRACT = json.loads((ROOT / "artifacts" / "inference_contract.json").read_text())
MODEL_VERSION = "telco-churn-classifier-v1"  # matches the MLflow registry version from experiment-tracking
THRESHOLD = CONTRACT["output"]["chosen_threshold"]

app = FastAPI(title="Telco Churn Risk API", version=MODEL_VERSION)
_model = None
_ready = False


@app.on_event("startup")
def load_model():
    """Load the model ONCE at startup, not per request (skill pitfall)."""
    global _model, _ready
    t0 = time.time()
    _model = joblib.load(ROOT / "artifacts" / "model.joblib")
    _ready = True
    log.info(f"model loaded in {time.time()-t0:.2f}s")


# ---- Pydantic request/response models, generated from inference_contract.json ----
_cat_schema = {k: v for k, v in CONTRACT["input"]["column_schema"].items() if v["dtype"] == "string"}


class CustomerRecord(BaseModel):
    customerID: Optional[str] = None
    gender: Literal["Female", "Male"]
    SeniorCitizen: Literal[0, 1]
    Partner: Literal["Yes", "No"]
    Dependents: Literal["Yes", "No"]
    tenure: int = Field(ge=0, le=100)
    PhoneService: Literal["Yes", "No"]
    MultipleLines: Literal["Yes", "No", "No phone service"]
    InternetService: Literal["DSL", "Fiber optic", "No"]
    OnlineSecurity: Literal["Yes", "No", "No internet service"]
    OnlineBackup: Literal["Yes", "No", "No internet service"]
    DeviceProtection: Literal["Yes", "No", "No internet service"]
    TechSupport: Literal["Yes", "No", "No internet service"]
    StreamingTV: Literal["Yes", "No", "No internet service"]
    StreamingMovies: Literal["Yes", "No", "No internet service"]
    Contract: Literal["Month-to-month", "One year", "Two year"]
    PaperlessBilling: Literal["Yes", "No"]
    PaymentMethod: Literal["Electronic check", "Mailed check", "Bank transfer (automatic)", "Credit card (automatic)"]
    MonthlyCharges: float = Field(ge=0, le=500)
    # Raw schema ships this as a string, sometimes blank (new tenure==0 customers).
    # Accept either a numeric value or a blank/whitespace string, per the corrected contract.
    TotalCharges: str

    @field_validator("TotalCharges")
    @classmethod
    def check_total_charges(cls, v):
        if v.strip() == "":
            return v
        try:
            float(v)
        except ValueError:
            raise ValueError(f"TotalCharges must be numeric or blank, got {v!r}")
        return v


class PredictRequest(BaseModel):
    customers: List[CustomerRecord]


class Prediction(BaseModel):
    customerID: Optional[str]
    probability: float
    risk_band: Literal["low", "medium", "high"]
    flagged: bool


class PredictResponse(BaseModel):
    model_version: str
    threshold: float
    request_id: str
    latency_ms: float
    predictions: List[Prediction]


def _risk_band(p: float) -> str:
    if p >= THRESHOLD:
        return "high"
    if p >= THRESHOLD * 0.5:
        return "medium"
    return "low"


def _score(records: List[CustomerRecord]) -> List[Prediction]:
    df = pd.DataFrame([r.model_dump() for r in records])
    # Corrected requirement from inference_contract.json: coerce TotalCharges to
    # numeric before scoring -- the pipeline's isna() check is a no-op on strings.
    df["TotalCharges"] = pd.to_numeric(df["TotalCharges"].astype(str).str.strip(), errors="coerce")
    X = df.drop(columns=["customerID"], errors="ignore")
    proba = _model.predict_proba(X)[:, 1]
    out = []
    for cid, p in zip(df.get("customerID", [None] * len(df)), proba):
        p = float(p)
        out.append(Prediction(customerID=cid, probability=round(p, 4),
                               risk_band=_risk_band(p), flagged=p >= THRESHOLD))
    return out


@app.get("/health")
def health():
    """Liveness: is the process up."""
    return {"status": "ok"}


@app.get("/ready")
def ready():
    """Readiness: is the model actually loaded and able to serve."""
    if not _ready:
        raise HTTPException(status_code=503, detail="model not loaded")
    return {"status": "ready", "model_version": MODEL_VERSION, "threshold": THRESHOLD}


@app.post("/predict", response_model=PredictResponse)
def predict(req: PredictRequest, request: Request):
    if not _ready:
        raise HTTPException(status_code=503, detail="model not loaded")
    if len(req.customers) == 0:
        raise HTTPException(status_code=422, detail="customers list must not be empty")
    if len(req.customers) > 500:
        raise HTTPException(status_code=422, detail="batch size limited to 500 per request")
    rid = str(uuid.uuid4())
    t0 = time.time()
    try:
        preds = _score(req.customers)
    except Exception as e:  # noqa: BLE001 -- a bad-but-schema-valid payload shouldn't 500 the worker
        log.error(f"[{rid}] scoring failed: {e}")
        raise HTTPException(status_code=422, detail=f"could not score payload: {e}")
    dt = (time.time() - t0) * 1000
    log.info(f"[{rid}] scored {len(req.customers)} customers in {dt:.1f}ms")
    return PredictResponse(model_version=MODEL_VERSION, threshold=THRESHOLD, request_id=rid,
                            latency_ms=round(dt, 2), predictions=preds)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8321)
