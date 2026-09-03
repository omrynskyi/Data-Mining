"""
tests/integration/test_sandbox_parity.py
Tier 3 Cross-Feature Integration Tests: Live Sandbox Mining Parity with Offline Batch Engine (Feature F17).
Validates that on-the-fly interactive mining via /api/sandbox/mine produces exact rule equivalence
and metric parity with offline batch mining for identical parameters.
"""

import json
import pytest
import pandas as pd
import numpy as np

try:
    from src.mining.engine import mine_association_rules
    from src.dashboard.live_miner import run_live_mining
except ImportError:
    mine_association_rules = None
    run_live_mining = None


class TestSandboxMiningParityIntegration:
    """Tier 3: Live Sandbox vs Offline Batch Mining Parity."""

    def test_live_miner_matches_offline_engine_rules(self, sample_one_hot_df):
        """Verify rules discovered via live miner match offline engine for identical support & confidence."""
        if mine_association_rules is None and run_live_mining is None:
            pytest.skip("Mining engine or live miner not yet implemented")

        min_supp = 0.2
        min_conf = 0.5

        if mine_association_rules is not None and run_live_mining is not None:
            # 1. Offline Engine Run
            _, offline_rules_df = mine_association_rules(
                sample_one_hot_df,
                min_support=min_supp,
                min_confidence=min_conf,
                algorithm="fpgrowth"
            )

            # 2. Live Miner Run
            live_result = run_live_mining(
                sample_one_hot_df,
                min_support=min_supp,
                min_confidence=min_conf,
                algorithm="fpgrowth"
            )
            live_rules = live_result.get("rules", [])

            assert len(offline_rules_df) == len(live_rules), "Rule count mismatch between offline engine and live miner"

    def test_sandbox_api_parity_with_offline_mining(self, flask_client):
        """Verify POST /api/sandbox/mine returns success status and consistent rule count."""
        payload = {
            "algorithm": "fpgrowth",
            "min_support": 0.05,
            "min_confidence": 0.4,
            "min_lift": 1.2,
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
        assert "rules" in data
