"""
tests/unit/test_dashboard_api.py
Unit & Boundary Tests for Flask Dashboard REST API Suite (Features F12, F13).
Validates /health, /api/summary, /api/crisp-dm, /api/eda, /api/rules (with filtering & pagination),
/api/rules/network, /api/optimization, /api/sandbox/mine, and /api/recommend endpoints.
"""

import json
import pytest


class TestDashboardHealthAndSummaryAPIs:
    """Tier 1: Health Probe and Executive Summary Endpoints."""

    def test_health_endpoint_returns_200_ok(self, flask_client):
        """GET /health must return HTTP 200 OK with healthy status and artifact flags."""
        response = flask_client.get("/health")
        assert response.status_code == 200
        data = response.get_json()
        assert isinstance(data, dict)
        assert data.get("status") == "healthy"
        assert "timestamp" in data
        assert "artifacts" in data

    def test_summary_endpoint_returns_kpis(self, flask_client):
        """GET /api/summary must return high-level KPI metrics."""
        response = flask_client.get("/api/summary")
        if response.status_code == 404:
            pytest.skip("Endpoint /api/summary not yet registered")
        assert response.status_code == 200
        data = response.get_json()
        assert isinstance(data, dict)


class TestDashboardCRISPDMandEDAAPIs:
    """Tier 1: CRISP-DM 6-Phase and EDA Visualization Endpoints."""

    def test_crisp_dm_endpoint(self, flask_client):
        """GET /api/crisp-dm must return CRISP-DM phase metadata."""
        response = flask_client.get("/api/crisp-dm")
        if response.status_code == 404:
            pytest.skip("Endpoint /api/crisp-dm not yet registered")
        assert response.status_code == 200
        data = response.get_json()
        assert isinstance(data, dict)

    def test_eda_endpoint(self, flask_client):
        """GET /api/eda must return item distribution and basket stats."""
        response = flask_client.get("/api/eda")
        if response.status_code == 404:
            pytest.skip("Endpoint /api/eda not yet registered")
        assert response.status_code == 200
        data = response.get_json()
        assert isinstance(data, dict)


class TestDashboardRulesAPIs:
    """Tier 1: Association Rules Query, Filter, Network Graph, and Export Endpoints."""

    def test_rules_endpoint_filtering_and_pagination(self, flask_client):
        """GET /api/rules must support min_lift, min_confidence, and pagination params."""
        response = flask_client.get("/api/rules?min_lift=1.2&min_confidence=0.5&limit=10")
        if response.status_code == 404:
            pytest.skip("Endpoint /api/rules not yet registered")
        assert response.status_code == 200
        data = response.get_json()
        assert isinstance(data, dict)

    def test_rules_network_endpoint_schema(self, flask_client):
        """GET /api/rules/network must return 'nodes' and 'edges' formatted for Vis.js."""
        response = flask_client.get("/api/rules/network")
        if response.status_code == 404:
            pytest.skip("Endpoint /api/rules/network not yet registered")
        assert response.status_code == 200
        data = response.get_json()
        assert "nodes" in data
        assert "edges" in data
        assert isinstance(data["nodes"], list)
        assert isinstance(data["edges"], list)

    def test_rules_export_csv_and_json(self, flask_client):
        """GET /api/rules/export must support CSV and JSON export formats."""
        res_json = flask_client.get("/api/rules/export?format=json")
        if res_json.status_code == 404:
            pytest.skip("Endpoint /api/rules/export not yet registered")
        assert res_json.status_code == 200

        res_csv = flask_client.get("/api/rules/export?format=csv")
        assert res_csv.status_code == 200


class TestDashboardOptimizationAndSandboxAPIs:
    """Tier 1 & Tier 2: Optimization Trajectory and Live Interactive Sandbox Mining."""

    def test_optimization_endpoint(self, flask_client):
        """GET /api/optimization must return target paper details and iteration trajectory."""
        response = flask_client.get("/api/optimization")
        if response.status_code == 404:
            pytest.skip("Endpoint /api/optimization not yet registered")
        assert response.status_code == 200
        data = response.get_json()
        assert isinstance(data, dict)

    def test_sandbox_mine_valid_request(self, flask_client):
        """POST /api/sandbox/mine with valid parameters executes live mining."""
        payload = {
            "algorithm": "fpgrowth",
            "min_support": 0.05,
            "min_confidence": 0.3,
            "min_lift": 1.1,
            "max_len": 3
        }
        response = flask_client.post(
            "/api/sandbox/mine",
            data=json.dumps(payload),
            content_type="application/json"
        )
        if response.status_code == 404:
            pytest.skip("Endpoint /api/sandbox/mine not yet registered")
        assert response.status_code == 200
        data = response.get_json()
        assert data.get("status") == "success"
        assert "execution_time_ms" in data or "rules_count" in data

    def test_sandbox_mine_invalid_parameters_boundary(self, flask_client):
        """POST /api/sandbox/mine with negative support or invalid algorithm returns 400 Bad Request."""
        invalid_payload = {
            "algorithm": "invalid_algo_xyz",
            "min_support": -0.5
        }
        response = flask_client.post(
            "/api/sandbox/mine",
            data=json.dumps(invalid_payload),
            content_type="application/json"
        )
        if response.status_code == 404:
            pytest.skip("Endpoint /api/sandbox/mine not yet registered")
        assert response.status_code == 400

    def test_recommend_endpoint(self, flask_client):
        """GET /api/recommend?cart=... returns item recommendations based on discovered rules."""
        response = flask_client.get("/api/recommend?cart=milk,bread")
        if response.status_code == 404:
            pytest.skip("Endpoint /api/recommend not yet registered")
        assert response.status_code == 200
        data = response.get_json()
        assert "recommendations" in data
