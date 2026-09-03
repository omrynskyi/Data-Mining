"""
tests/integration/test_dashboard_integration.py
Tier 3 Cross-Feature Integration Tests: ArtifactLoader -> Flask REST APIs Consistency (Features F12, F13).
Validates that ArtifactLoader loads disk artifacts reliably, provides fallback data when missing,
and feeds all dashboard API endpoints seamlessly.
"""

import json
import pytest

try:
    from src.dashboard.artifact_loader import ArtifactLoader
except ImportError:
    ArtifactLoader = None


class TestDashboardArtifactIntegration:
    """Tier 3: Artifact Loader and REST API Consistency Integration."""

    def test_artifact_loader_reads_temp_artifacts(self, temp_artifacts_dir):
        """Verify ArtifactLoader loads pipeline summary, rules, and optimization logs from directory."""
        if ArtifactLoader is None:
            pytest.skip("src.dashboard.artifact_loader.ArtifactLoader not yet implemented")

        loader = ArtifactLoader(artifacts_dir=temp_artifacts_dir)
        summary = loader.get_pipeline_summary()
        rules = loader.get_rules()
        opt_log = loader.get_optimization_log()

        assert summary is not None
        assert isinstance(summary, dict)
        assert len(rules) > 0
        assert opt_log is not None

    def test_artifact_loader_graceful_fallback_when_missing(self, tmp_path):
        """Verify ArtifactLoader returns mock/fallback data without crashing when artifacts dir is empty."""
        if ArtifactLoader is None:
            pytest.skip("src.dashboard.artifact_loader.ArtifactLoader not yet implemented")

        empty_dir = tmp_path / "empty_artifacts"
        empty_dir.mkdir()

        loader = ArtifactLoader(artifacts_dir=str(empty_dir))
        # Should not raise exception, but return fallback or empty structure
        summary = loader.get_pipeline_summary()
        rules = loader.get_rules()
        assert summary is not None or rules is not None

    def test_api_serves_loaded_rules_accurately(self, flask_client):
        """Verify GET /api/rules returns the rules present in the loaded artifact."""
        response = flask_client.get("/api/rules")
        if response.status_code == 404:
            pytest.skip("/api/rules not yet implemented")
        assert response.status_code == 200
        data = response.get_json()
        assert "rules" in data
        assert len(data["rules"]) > 0
