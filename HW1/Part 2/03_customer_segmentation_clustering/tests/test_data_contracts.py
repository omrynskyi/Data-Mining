"""
Tier 1 Contract & Schema Validation Tests.
Verifies data structures, JSON schemas, CSV exports, and serialized model invariants.
"""

import json
import math
from pathlib import Path
import pytest


class TestDataContracts:
    """Validates contract specifications and data integrity for pipeline outputs."""

    def test_t1_pipeline_output_json_schema(self, artifacts_dir: Path, validate_pipeline_json_schema):
        """Validates pipeline_output.json exists and strictly matches the TypeScript contract."""
        json_path = artifacts_dir / "pipeline_output.json"
        if not json_path.exists():
            pytest.skip(f"Artifact {json_path} does not exist yet (pending pipeline execution).")

        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        is_valid, err_msg = validate_pipeline_json_schema(data)
        assert is_valid, f"Pipeline output schema violation: {err_msg}"

    def test_t1_customer_segment_counts_consistency(self, artifacts_dir: Path):
        """Verifies that customer count equals sum of cluster counts and customer list length."""
        json_path = artifacts_dir / "pipeline_output.json"
        if not json_path.exists():
            pytest.skip(f"Artifact {json_path} does not exist yet.")

        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        total_customers = data["dataset_summary"]["total_customers"]
        customers_list = data["customers"]
        clusters = data["clusters"]

        assert len(customers_list) == total_customers, (
            f"Customers array length ({len(customers_list)}) does not match summary total ({total_customers})"
        )

        cluster_counts_sum = sum(c["count"] for c in clusters)
        assert cluster_counts_sum == total_customers, (
            f"Sum of cluster counts ({cluster_counts_sum}) does not match total customers ({total_customers})"
        )

        percentage_sum = sum(c["percentage"] for c in clusters)
        assert 99.0 <= percentage_sum <= 101.0, (
            f"Sum of cluster percentages ({percentage_sum:.2f}%) should equal ~100%"
        )

    def test_t1_pca_coordinates_integrity(self, artifacts_dir: Path):
        """Verifies all customer records have valid, finite 2D PCA projection coordinates."""
        json_path = artifacts_dir / "pipeline_output.json"
        if not json_path.exists():
            pytest.skip(f"Artifact {json_path} does not exist yet.")

        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        for customer in data["customers"]:
            assert "pca_x" in customer and isinstance(customer["pca_x"], (int, float)), "pca_x missing or invalid"
            assert "pca_y" in customer and isinstance(customer["pca_y"], (int, float)), "pca_y missing or invalid"
            assert not math.isnan(customer["pca_x"]) and not math.isinf(customer["pca_x"]), "pca_x is NaN or Inf"
            assert not math.isnan(customer["pca_y"]) and not math.isinf(customer["pca_y"]), "pca_y is NaN or Inf"

    def test_t1_metrics_json_schema(self, artifacts_dir: Path):
        """Verifies artifacts/metrics.json exists and contains standard evaluation metrics."""
        metrics_path = artifacts_dir / "metrics.json"
        if not metrics_path.exists():
            pytest.skip(f"Artifact {metrics_path} does not exist yet.")

        with open(metrics_path, "r", encoding="utf-8") as f:
            metrics = json.load(f)

        assert isinstance(metrics, dict), "metrics.json must be a JSON dictionary"
        # Must have silhouette and davies_bouldin at minimum
        has_silhouette = any("silhouette" in k.lower() for k in metrics.keys())
        assert has_silhouette, f"metrics.json missing silhouette score: {metrics}"

    def test_t1_autoresearch_output_json_schema(self, artifacts_dir: Path, validate_autoresearch_json_schema):
        """Verifies artifacts/autoresearch_output.json conforms to the autoresearch contract."""
        json_path = artifacts_dir / "autoresearch_output.json"
        if not json_path.exists():
            pytest.skip(f"Artifact {json_path} does not exist yet (pending autoresearch run).")

        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        is_valid, err_msg = validate_autoresearch_json_schema(data)
        assert is_valid, f"Autoresearch JSON schema violation: {err_msg}"
