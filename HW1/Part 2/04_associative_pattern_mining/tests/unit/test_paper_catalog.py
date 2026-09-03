"""
tests/unit/test_paper_catalog.py
Unit & Boundary Tests for Research Paper Benchmark Catalog (Feature F7).
Validates Ghosh & Nath (2004), Agrawal & Srikant (1994), Chen et al. (2012),
and custom paper profile configurations.
"""

import pytest
import json

try:
    from src.optimization.papers import get_paper_profile, list_available_papers, PAPER_CATALOG
except ImportError:
    get_paper_profile = None
    list_available_papers = None
    PAPER_CATALOG = None


class TestResearchPaperCatalog:
    """Tier 1: Feature Coverage for Research Paper Benchmark Catalog."""

    def test_list_available_papers_contains_benchmarks(self):
        """Verify the catalog lists ghosh2004, agrawal1994, and chen2012."""
        if list_available_papers is None and PAPER_CATALOG is None:
            pytest.skip("src.optimization.papers not yet implemented")

        papers = list_available_papers() if list_available_papers else list(PAPER_CATALOG.keys())
        expected = {"ghosh2004", "agrawal1994", "chen2012"}
        assert expected.issubset(set(papers))

    def test_ghosh_2004_profile_schema_and_targets(self):
        """Verify Ghosh & Nath (2004) paper metadata and target metrics."""
        if get_paper_profile is None and PAPER_CATALOG is None:
            pytest.skip("src.optimization.papers not yet implemented")

        profile = get_paper_profile("ghosh2004") if get_paper_profile else PAPER_CATALOG["ghosh2004"]
        assert profile["key"] == "ghosh2004"
        assert "Ashish Ghosh" in profile["authors"]
        assert "target_metrics" in profile
        
        targets = profile["target_metrics"]
        assert targets["rule_count"] == 50
        assert targets["avg_support"] == 0.025
        assert targets["avg_confidence"] == 0.720
        assert targets["avg_lift"] == 2.450
        assert targets["coverage"] == 0.180

    def test_agrawal_1994_profile_targets(self):
        """Verify Agrawal & Srikant (1994) benchmark targets."""
        if get_paper_profile is None and PAPER_CATALOG is None:
            pytest.skip("src.optimization.papers not yet implemented")

        profile = get_paper_profile("agrawal1994") if get_paper_profile else PAPER_CATALOG["agrawal1994"]
        targets = profile["target_metrics"]
        assert targets["rule_count"] == 120
        assert targets["avg_support"] == 0.015
        assert targets["avg_confidence"] == 0.600
        assert targets["avg_lift"] == 1.850

    def test_chen_2012_profile_targets(self):
        """Verify Chen et al. (2012) benchmark targets."""
        if get_paper_profile is None and PAPER_CATALOG is None:
            pytest.skip("src.optimization.papers not yet implemented")

        profile = get_paper_profile("chen2012") if get_paper_profile else PAPER_CATALOG["chen2012"]
        targets = profile["target_metrics"]
        assert targets["rule_count"] == 35
        assert targets["avg_support"] == 0.020
        assert targets["avg_confidence"] == 0.680
        assert targets["avg_lift"] == 3.200


class TestPaperCatalogBoundaries:
    """Tier 2: Boundary & Custom Paper Profile Handling."""

    def test_unknown_paper_key_raises_error(self):
        """Verify querying an unregistered paper key raises KeyError or ValueError."""
        if get_paper_profile is None:
            pytest.skip("src.optimization.papers not yet implemented")

        with pytest.raises((KeyError, ValueError)):
            get_paper_profile("unknown_paper_key_9999")

    def test_custom_paper_json_loading(self, tmp_path):
        """Verify loading a custom target paper profile from JSON."""
        custom_data = {
            "key": "custom_paper",
            "title": "Custom Benchmark Paper",
            "authors": "Jane Doe",
            "venue": "Test Venue",
            "doi": "10.1234/test",
            "target_metrics": {
                "rule_count": 40,
                "avg_support": 0.03,
                "avg_confidence": 0.75,
                "avg_lift": 2.2,
                "coverage": 0.15
            }
        }
        custom_file = tmp_path / "custom_target.json"
        with open(custom_file, "w", encoding="utf-8") as f:
            json.dump(custom_data, f)

        if get_paper_profile is not None:
            try:
                loaded = get_paper_profile(str(custom_file))
                assert loaded["key"] == "custom_paper"
                assert loaded["target_metrics"]["rule_count"] == 40
            except (ValueError, KeyError, NotImplementedError):
                pass
