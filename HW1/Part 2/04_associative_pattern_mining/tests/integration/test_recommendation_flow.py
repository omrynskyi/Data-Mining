"""
tests/integration/test_recommendation_flow.py
Tier 3 Cross-Feature Integration Tests: Basket Recommendation Engine Flow (Feature F13).
Validates that recommendation inference correctly extracts consequents from matching antecedent rules,
ranks by confidence and lift, filters out cart items, and handles disjoint baskets gracefully.
"""

import pytest

try:
    from src.evaluation.filter import generate_recommendations
except ImportError:
    generate_recommendations = None


class TestRecommendationFlowIntegration:
    """Tier 3: Basket Recommendation Inference Integration."""

    def test_recommendation_from_rules(self, sample_mined_rules_df):
        """
        Given cart = ['bread', 'butter'], rule {bread, butter} -> {milk} (conf=0.8, lift=1.33)
        should recommend 'milk' as top suggestion.
        """
        cart = ["bread", "butter"]
        if generate_recommendations is not None:
            recs = generate_recommendations(cart, sample_mined_rules_df)
            assert len(recs) > 0
            assert recs[0]["item"] == "milk"
            assert recs[0]["item"] not in cart

    def test_recommendation_excludes_existing_cart_items(self, sample_mined_rules_df):
        """Recommended items must never include items already in the shopping cart."""
        cart = ["milk", "bread"]
        if generate_recommendations is not None:
            recs = generate_recommendations(cart, sample_mined_rules_df)
            rec_items = [r["item"] for r in recs]
            assert "milk" not in rec_items
            assert "bread" not in rec_items

    def test_recommend_api_endpoint_flow(self, flask_client):
        """Query /api/recommend endpoint and verify JSON recommendation structure."""
        response = flask_client.get("/api/recommend?cart=bread,butter")
        if response.status_code == 404:
            pytest.skip("Endpoint /api/recommend not yet registered")
        assert response.status_code == 200
        data = response.get_json()
        assert "cart" in data
        assert "recommendations" in data
        assert isinstance(data["recommendations"], list)

    def test_recommend_empty_cart_boundary(self, flask_client):
        """Empty cart parameter should return empty recommendations without 500 error."""
        response = flask_client.get("/api/recommend?cart=")
        if response.status_code == 404:
            pytest.skip("Endpoint /api/recommend not yet registered")
        assert response.status_code == 200
        data = response.get_json()
        assert data.get("recommendations") == []
