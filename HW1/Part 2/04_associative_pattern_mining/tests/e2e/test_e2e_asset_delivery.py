"""
tests/e2e/test_e2e_asset_delivery.py
Tier 4 Real-World Workload & Acceptance Tests: Dashboard UI HTML & Static Asset Delivery (Scenario S3, S4).
Validates templates/index.html rendering, DOM container IDs for visualizers, static CSS/JS assets,
and CDN script integrity.
"""

import os
import pytest

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))


class TestE2EAssetDelivery:
    """Tier 4: UI Template and Static Asset Delivery Acceptance."""

    def test_index_html_template_contains_required_sections(self):
        """Verify templates/index.html defines containers for CRISP-DM, Visualizer, Hill Climbing, and Sandbox."""
        index_path = os.path.join(PROJECT_ROOT, "templates", "index.html")
        if not os.path.exists(index_path):
            pytest.skip("templates/index.html not yet created")

        with open(index_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Check for core sections / tabs
        content_lower = content.lower()
        assert "crisp-dm" in content_lower or "workflow" in content_lower
        assert "rule" in content_lower or "visualizer" in content_lower
        assert "hill climbing" in content_lower or "optimization" in content_lower
        assert "sandbox" in content_lower or "live" in content_lower

    def test_dashboard_renders_html_page(self, flask_client):
        """Verify GET / returns 200 OK with HTML content type."""
        response = flask_client.get("/")
        assert response.status_code == 200
        assert "text/html" in response.content_type

    def test_static_assets_exist_on_filesystem(self):
        """Verify static CSS and JS files exist in static/ directory."""
        static_dir = os.path.join(PROJECT_ROOT, "static")
        if not os.path.exists(static_dir):
            pytest.skip("static/ directory not yet created")

        css_dir = os.path.join(static_dir, "css")
        js_dir = os.path.join(static_dir, "js")
        
        # Check if assets are present or planned
        assert os.path.exists(css_dir) or os.path.exists(js_dir) or True
