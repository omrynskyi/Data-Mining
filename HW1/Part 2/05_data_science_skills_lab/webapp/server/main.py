"""FastAPI backend for the Data Science Skills Mastery Lab webapp.

Real data throughout: Titanic, Ames Housing, Credit Card Fraud, Online Retail
(webapp/data/), plus a bridge into the already-completed real Telco Customer
Churn CRISP-DM lab at the project root (artifacts/). No np.random synthesis
anywhere in this codebase.

Every expensive computation (the 5 ML/analytics pipelines) is computed ONCE at
startup and served from an in-memory cache (functools.lru_cache in the core
modules) on every subsequent request.
"""
import json
import logging
import re
import sys
import time
from pathlib import Path
from typing import List, Literal, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator

WEBAPP_ROOT = Path(__file__).resolve().parent.parent
PROJECT_ROOT = WEBAPP_ROOT.parent
sys.path.insert(0, str(WEBAPP_ROOT))  # makes "core" importable regardless of cwd

from core import telco_bridge  # noqa: E402
from core.analytics_skills_runner import calculate_ab_test, run_ecommerce_analytics  # noqa: E402
from core.ml_skills_runner import (  # noqa: E402
    run_data_quality_audit,
    run_fraud_detection_pipeline,
    run_house_prices_pipeline,
    run_titanic_pipeline,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
log = logging.getLogger("skills-lab-api")

app = FastAPI(title="Data Science Skills Mastery Lab API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

SKILLS_CATALOG_PATH = WEBAPP_ROOT / "core" / "skills_catalog.json"
SKILLS_CATALOG: List[dict] = json.loads(SKILLS_CATALOG_PATH.read_text())
SKILLS_BY_ID = {s["id"]: s for s in SKILLS_CATALOG}

_ready = False
_startup_timings: dict = {}


@app.on_event("startup")
def warm_caches():
    """Run every real pipeline ONCE at startup so GET endpoints serve from cache."""
    global _ready
    t0 = time.time()
    steps = [
        ("titanic", run_titanic_pipeline),
        ("house_prices", run_house_prices_pipeline),
        ("fraud", run_fraud_detection_pipeline),
        ("data_quality_audit", run_data_quality_audit),
        ("ecommerce", run_ecommerce_analytics),
        ("telco_benchmark", telco_bridge.get_telco_benchmark),
        ("telco_model", telco_bridge.load_telco_model),
    ]
    for name, fn in steps:
        t_step = time.time()
        try:
            fn()
        except Exception as e:  # noqa: BLE001 -- log and continue warming the rest
            log.error(f"startup warm-up failed for {name}: {e}")
            raise
        _startup_timings[name] = round(time.time() - t_step, 3)
    _ready = True
    log.info(f"all pipelines warmed in {time.time()-t0:.2f}s -- {_startup_timings}")


def _require_ready():
    if not _ready:
        raise HTTPException(status_code=503, detail="pipelines still warming up")


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

@app.get("/api/health")
def health():
    return {"status": "ok", "ready": _ready, "startup_timings_sec": _startup_timings}


# ---------------------------------------------------------------------------
# Skills catalog
# ---------------------------------------------------------------------------

@app.get("/api/skills/catalog")
def skills_catalog():
    return {"count": len(SKILLS_CATALOG), "skills": SKILLS_CATALOG}


# ---------------------------------------------------------------------------
# Benchmarks
# ---------------------------------------------------------------------------

@app.get("/api/benchmarks/titanic")
def benchmark_titanic():
    _require_ready()
    return run_titanic_pipeline()


@app.get("/api/benchmarks/house-prices")
def benchmark_house_prices():
    _require_ready()
    return run_house_prices_pipeline()


@app.get("/api/benchmarks/fraud")
def benchmark_fraud():
    _require_ready()
    return run_fraud_detection_pipeline()


@app.get("/api/benchmarks/ecommerce")
def benchmark_ecommerce():
    _require_ready()
    return run_ecommerce_analytics()


@app.get("/api/benchmarks/data-quality")
def benchmark_data_quality():
    _require_ready()
    return run_data_quality_audit()


@app.get("/api/benchmarks/telco")
def benchmark_telco():
    _require_ready()
    return telco_bridge.get_telco_benchmark()


# ---------------------------------------------------------------------------
# Telco live prediction -- real model, real inference contract
# ---------------------------------------------------------------------------

_CONTRACT = telco_bridge.get_inference_contract()
_SCHEMA = _CONTRACT["input"]["column_schema"]


def _allowed(col: str):
    return tuple(_SCHEMA[col]["allowed_values"])


class TelcoCustomerRecord(BaseModel):
    customerID: Optional[str] = None
    gender: Literal[_allowed("gender")]  # type: ignore[valid-type]
    SeniorCitizen: Literal[0, 1]
    Partner: Literal[_allowed("Partner")]  # type: ignore[valid-type]
    Dependents: Literal[_allowed("Dependents")]  # type: ignore[valid-type]
    tenure: int = Field(ge=0, le=100)
    PhoneService: Literal[_allowed("PhoneService")]  # type: ignore[valid-type]
    MultipleLines: Literal[_allowed("MultipleLines")]  # type: ignore[valid-type]
    InternetService: Literal[_allowed("InternetService")]  # type: ignore[valid-type]
    OnlineSecurity: Literal[_allowed("OnlineSecurity")]  # type: ignore[valid-type]
    OnlineBackup: Literal[_allowed("OnlineBackup")]  # type: ignore[valid-type]
    DeviceProtection: Literal[_allowed("DeviceProtection")]  # type: ignore[valid-type]
    TechSupport: Literal[_allowed("TechSupport")]  # type: ignore[valid-type]
    StreamingTV: Literal[_allowed("StreamingTV")]  # type: ignore[valid-type]
    StreamingMovies: Literal[_allowed("StreamingMovies")]  # type: ignore[valid-type]
    Contract: Literal[_allowed("Contract")]  # type: ignore[valid-type]
    PaperlessBilling: Literal[_allowed("PaperlessBilling")]  # type: ignore[valid-type]
    PaymentMethod: Literal[_allowed("PaymentMethod")]  # type: ignore[valid-type]
    MonthlyCharges: float = Field(ge=0, le=500)
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


class TelcoPredictRequest(BaseModel):
    customers: List[TelcoCustomerRecord]


@app.post("/api/telco/predict")
def telco_predict(req: TelcoPredictRequest):
    if len(req.customers) == 0:
        raise HTTPException(status_code=422, detail="customers list must not be empty")
    if len(req.customers) > 500:
        raise HTTPException(status_code=422, detail="batch size limited to 500 per request")
    t0 = time.time()
    try:
        records = [c.model_dump() for c in req.customers]
        predictions = telco_bridge.predict_churn(records)
    except Exception as e:  # noqa: BLE001 -- a bad-but-schema-valid payload shouldn't 500
        log.error(f"telco predict failed: {e}")
        raise HTTPException(status_code=422, detail=f"could not score payload: {e}")
    dt_ms = round((time.time() - t0) * 1000, 2)
    contract = telco_bridge.get_inference_contract()
    return {
        "model_version": "telco-churn-classifier-v1",
        "threshold": contract["output"]["chosen_threshold"],
        "latency_ms": dt_ms,
        "predictions": predictions,
    }


# ---------------------------------------------------------------------------
# A/B test calculator
# ---------------------------------------------------------------------------

class ABTestRequest(BaseModel):
    n_control: int = Field(gt=0)
    x_control: int = Field(ge=0)
    n_treatment: int = Field(gt=0)
    x_treatment: int = Field(ge=0)


@app.post("/api/ab-test/calculate")
def ab_test_calculate(req: ABTestRequest):
    try:
        return calculate_ab_test(req.n_control, req.x_control, req.n_treatment, req.x_treatment)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))


# ---------------------------------------------------------------------------
# Skills execute router
# ---------------------------------------------------------------------------

_BENCHMARK_FN = {
    "titanic": run_titanic_pipeline,
    "house": run_house_prices_pipeline,
    "fraud": run_fraud_detection_pipeline,
    "ecommerce": run_ecommerce_analytics,
    "telco": telco_bridge.get_telco_benchmark,
}


def _skill_highlight(skill_id: str, benchmark_result: dict) -> Optional[dict]:
    """A handful of skills get a specific, relevant slice of their benchmark's
    real result rather than the full payload, per the router's design."""
    if skill_id == "imbalanced-data":
        return {
            "sampling_note": benchmark_result["sampling_note"],
            "baseline_logreg": benchmark_result["baseline_logreg"],
            "balanced_logreg": benchmark_result["balanced_logreg"],
            "f1_optimal_threshold": benchmark_result["f1_optimal_threshold"],
        }
    if skill_id == "data-quality-audit":
        return run_data_quality_audit()
    if skill_id == "segmentation-analysis":
        return {"segment_profiles": benchmark_result["segment_profiles"]}
    if skill_id == "business-metrics-calculator":
        return {"business_metrics": benchmark_result["business_metrics"]}
    if skill_id == "model-evaluation":
        return {"metrics": benchmark_result["metrics"], "confusion_matrix": benchmark_result["confusion_matrix"]}
    if skill_id == "ml-debugging":
        return {"baseline_logreg": benchmark_result["baseline_logreg"],
                "balanced_logreg": benchmark_result["balanced_logreg"]}
    if skill_id == "cohort-analysis":
        return {"cohort_retention": benchmark_result["cohort_retention"]}
    if skill_id == "funnel-analysis":
        return {"engagement_funnel": benchmark_result["engagement_funnel"]}
    if skill_id == "time-series-analysis":
        return {"revenue_time_series": benchmark_result["revenue_time_series"]}
    return None


@app.post("/api/skills/execute")
def skills_execute(payload: dict):
    _require_ready()
    skill_id = payload.get("skill_id")
    if not skill_id:
        raise HTTPException(status_code=422, detail="skill_id is required")
    skill = SKILLS_BY_ID.get(skill_id)
    if not skill:
        raise HTTPException(status_code=404, detail=f"unknown skill_id: {skill_id}")

    benchmark_link = skill["benchmark_link"]
    fn = _BENCHMARK_FN[benchmark_link]
    result = fn()

    highlight = _skill_highlight(skill_id, result)

    return {
        "skill_id": skill_id,
        "skill_name": skill["name"],
        "benchmark_link": benchmark_link,
        "result": highlight if highlight is not None else result,
    }


# ---------------------------------------------------------------------------
# CRISP-DM report
# ---------------------------------------------------------------------------

_PHASE_NAMES = {
    "01_business_understanding": "1 - Business Understanding",
    "02_data_understanding": "2 - Data Understanding",
    "03_data_preparation": "3 - Data Preparation",
    "04_modeling": "4 - Modeling",
    "05_evaluation": "5 - Evaluation",
    "06_deployment": "6 - Deployment",
}


@app.get("/api/crisp-dm/report")
def crisp_dm_report():
    phases: dict = {name: [] for name in _PHASE_NAMES.values()}
    for skill in SKILLS_CATALOG:
        doc_link = skill.get("doc_link") or ""
        m = re.search(r"crisp_dm/([^/]+)/", doc_link)
        phase_dir = m.group(1) if m else None
        phase_name = _PHASE_NAMES.get(phase_dir, "Unassigned")
        phases[phase_name].append({
            "id": skill["id"],
            "name": skill["name"],
            "category": skill["category"],
            "doc_link": skill["doc_link"],
        })

    return {
        "project": "Data Science Skills Mastery Lab -- Kaggle Telco Customer Churn CRISP-DM",
        "total_skills": len(SKILLS_CATALOG),
        "phases": [
            {"phase": name, "skill_count": len(skills), "skills": skills}
            for name, skills in phases.items()
        ],
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8005)
