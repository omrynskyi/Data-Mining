"""Real tests against a live FastAPI server for the Data Science Skills Mastery Lab API.

Run with the server already started:
    uvicorn main:app --host 127.0.0.1 --port 8005
    pytest webapp/server/test_api.py -v

Uses FastAPI's TestClient (starlette test client), which runs real startup/shutdown
events against the real app -- exercises the real pipelines, not mocks.
"""
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parent))
from main import app  # noqa: E402

GOOD_CUSTOMER = {
    "customerID": "7590-VHVEG",
    "gender": "Female",
    "SeniorCitizen": 0,
    "Partner": "Yes",
    "Dependents": "No",
    "tenure": 1,
    "PhoneService": "No",
    "MultipleLines": "No phone service",
    "InternetService": "DSL",
    "OnlineSecurity": "No",
    "OnlineBackup": "Yes",
    "DeviceProtection": "No",
    "TechSupport": "No",
    "StreamingTV": "No",
    "StreamingMovies": "No",
    "Contract": "Month-to-month",
    "PaperlessBilling": "Yes",
    "PaymentMethod": "Electronic check",
    "MonthlyCharges": 29.85,
    "TotalCharges": "29.85",
}


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["ready"] is True


def test_skills_catalog_has_48_entries(client):
    r = client.get("/api/skills/catalog")
    assert r.status_code == 200
    body = r.json()
    assert body["count"] == 48
    assert len(body["skills"]) == 48
    for skill in body["skills"]:
        assert skill["pitfalls"], f"{skill['id']} has no pitfalls"
        assert skill["benchmark_link"] in ("titanic", "house", "fraud", "ecommerce", "telco")


def test_titanic_benchmark_real_survival_rate(client):
    r = client.get("/api/benchmarks/titanic")
    assert r.status_code == 200
    body = r.json()
    assert abs(body["real_survival_rate"] - 0.3838) < 0.001
    assert 0.0 <= body["metrics"]["roc_auc"] <= 1.0
    assert len(body["confusion_matrix"]["matrix"]) == 2


def test_house_prices_benchmark(client):
    r = client.get("/api/benchmarks/house-prices")
    assert r.status_code == 200
    body = r.json()
    assert abs(body["real_sale_price_mean"] - 180796.06) < 1.0
    assert body["metrics"]["r2"] > 0.5


def test_fraud_benchmark_real_rate(client):
    r = client.get("/api/benchmarks/fraud")
    assert r.status_code == 200
    body = r.json()
    assert abs(body["real_full_dataset_fraud_rate_pct"] - 0.1727) < 0.001
    assert "sampling_note" in body
    assert body["baseline_logreg"]["metrics"]["precision"] > 0


def test_ecommerce_benchmark(client):
    r = client.get("/api/benchmarks/ecommerce")
    assert r.status_code == 200
    body = r.json()
    assert len(body["cohort_retention"]["matrix"]) > 0
    assert len(body["engagement_funnel"]["stages"]) == 4
    assert len(body["revenue_time_series"]["monthly"]) > 0


def test_data_quality_benchmark(client):
    r = client.get("/api/benchmarks/data-quality")
    assert r.status_code == 200
    body = r.json()
    assert body["real_issues"]["missing_customer_id_pct"] > 20
    assert 0 <= body["quality_score"] <= 100


def test_telco_benchmark_real_churn_rate(client):
    r = client.get("/api/benchmarks/telco")
    assert r.status_code == 200
    body = r.json()
    assert abs(body["business_metrics"]["churn"]["logo_churn_rate_base_pct"] - 26.537) < 0.01
    assert abs(body["model_metrics"]["roc_auc"] - 0.8482) < 0.001


def test_telco_predict_real_customer(client):
    r = client.post("/api/telco/predict", json={"customers": [GOOD_CUSTOMER]})
    assert r.status_code == 200
    body = r.json()
    assert len(body["predictions"]) == 1
    pred = body["predictions"][0]
    assert 0.0 <= pred["probability"] <= 1.0
    assert pred["risk_band"] in ("low", "medium", "high")


def test_telco_predict_tenure_zero_blank_total_charges(client):
    edge_customer = dict(GOOD_CUSTOMER)
    edge_customer["tenure"] = 0
    edge_customer["TotalCharges"] = " "
    r = client.post("/api/telco/predict", json={"customers": [edge_customer]})
    assert r.status_code == 200


def test_telco_predict_malformed_enum_returns_422(client):
    bad_customer = dict(GOOD_CUSTOMER)
    bad_customer["Contract"] = "Lifetime"
    r = client.post("/api/telco/predict", json={"customers": [bad_customer]})
    assert r.status_code == 422


def test_telco_predict_empty_list_returns_422(client):
    r = client.post("/api/telco/predict", json={"customers": []})
    assert r.status_code == 422


def test_ab_test_calculate(client):
    r = client.post("/api/ab-test/calculate", json={
        "n_control": 1000, "x_control": 100, "n_treatment": 1000, "x_treatment": 130,
    })
    assert r.status_code == 200
    body = r.json()
    assert body["significant_at_95pct"] is True
    assert abs(body["absolute_diff"] - 0.03) < 1e-9


def test_ab_test_malformed_returns_422(client):
    r = client.post("/api/ab-test/calculate", json={
        "n_control": 100, "x_control": 200, "n_treatment": 100, "x_treatment": 10,
    })
    assert r.status_code == 422


@pytest.mark.parametrize("skill_id,expected_link", [
    ("imbalanced-data", "fraud"),
    ("data-quality-audit", "ecommerce"),
    ("sklearn-pipelines", "titanic"),
    ("cohort-analysis", "ecommerce"),
    ("business-metrics-calculator", "telco"),
])
def test_skills_execute_routes_correctly(client, skill_id, expected_link):
    r = client.post("/api/skills/execute", json={"skill_id": skill_id})
    assert r.status_code == 200
    body = r.json()
    assert body["benchmark_link"] == expected_link
    assert body["result"]


def test_skills_execute_data_quality_audit_returns_real_quality_result(client):
    r = client.post("/api/skills/execute", json={"skill_id": "data-quality-audit"})
    assert r.status_code == 200
    body = r.json()
    assert "quality_score" in body["result"]
    assert "real_issues" in body["result"]


def test_skills_execute_unknown_skill_404(client):
    r = client.post("/api/skills/execute", json={"skill_id": "not-a-real-skill"})
    assert r.status_code == 404


def test_crisp_dm_report(client):
    r = client.get("/api/crisp-dm/report")
    assert r.status_code == 200
    body = r.json()
    assert body["total_skills"] == 48
    assert len(body["phases"]) == 6
    assert sum(p["skill_count"] for p in body["phases"]) == 48
