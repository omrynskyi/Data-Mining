#!/usr/bin/env python3
"""
Acceptance Test Script: Data Science Admin Dashboard & CRISP-DM Verification.

Requirements:
1. Launches/tests dashboard application locally via FastAPI TestClient.
2. Asserts HTTP 200 OK on KV-cache, attention heatmaps, and tokenizer endpoints.
3. Programmatically reads CRISP-DM pipeline tracker state, confirming it tracks
   at least 3 stages (e.g. Data Preparation, Modeling, Evaluation).
4. Verifies interactive Admin Web Dashboard UI routes.

Usage:
    python test_dashboard.py
    pytest test_dashboard.py -v
"""

import sys
import os
from pathlib import Path
from typing import Dict, Any

# Ensure project root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def run_dashboard_verification():
    print("=" * 70)
    print(" ACCEPTANCE CRITERIA 2: DASHBOARD & CRISP-DM VERIFICATION")
    print("=" * 70)

    try:
        from fastapi.testclient import TestClient
        from dashboard.app import app
        from dashboard.crisp_dm import CrispDMTracker
    except ImportError as e:
        print(f"[-] Import failed: {e}")
        print("[-] Ensure dashboard package is implemented per PROJECT.md interface contracts.")
        return False

    client = TestClient(app)

    # 1. UI Root & Dashboard HTML Routes
    print("\n[1/4] Verifying Admin Web Dashboard UI Endpoints (HTTP GET)...")
    for route in ["/", "/dashboard"]:
        res = client.get(route)
        assert res.status_code == 200, f"Route {route} failed with status {res.status_code}"
        assert "text/html" in res.headers.get("content-type", ""), f"Route {route} did not return HTML"
        assert len(res.text) > 100, f"Route {route} returned empty/short HTML"
        print(f"    [+] {route:<20} -> Status 200 OK | Content-Type: text/html | Length: {len(res.text)} bytes")

    # 2. Programmatic CRISP-DM Tracker Verification (>= 3 stages guaranteed)
    print("\n[2/4] Verifying CRISP-DM Pipeline Tracker State (>= 3 stages)...")
    res_crisp = client.get("/api/crisp-dm")
    assert res_crisp.status_code == 200, f"CRISP-DM endpoint failed with {res_crisp.status_code}"
    crisp_data = res_crisp.json()
    assert "stages" in crisp_data, "CRISP-DM payload missing 'stages' dictionary"
    
    stages_dict = crisp_data["stages"]
    tracked_stage_keys = list(stages_dict.keys())
    print(f"    [+] Total stages tracked: {len(tracked_stage_keys)}")
    for k, v in stages_dict.items():
        print(f"        - {k:<25}: Name='{v.get('name', k)}', Status='{v.get('status')}'")

    # Explicit assertion of at least 3 stages including Data Preparation, Modeling, and Evaluation
    required_stages = ["data_preparation", "modeling", "evaluation"]
    assert len(tracked_stage_keys) >= 3, (
        f"CRISP-DM tracker must track >= 3 stages, but only found {len(tracked_stage_keys)}"
    )
    for req in required_stages:
        assert req in stages_dict, f"Required CRISP-DM stage '{req}' not found in tracker state"
        stage_obj = stages_dict[req]
        assert "status" in stage_obj, f"Stage '{req}' missing 'status'"
        assert "metrics" in stage_obj, f"Stage '{req}' missing 'metrics'"

    print(f"    [+] Programmatic check PASSED: Tracks required stages {required_stages}")

    # 3. Model Inspection Endpoints (KV-Cache, Attention Heatmap, Tokenizer)
    print("\n[3/4] Verifying Live Diagnostic Inspection Endpoints (HTTP GET & POST)...")

    # A. KV-Cache Endpoint
    res_kv_get = client.get("/api/inspect/kv-cache?prompt=Hello&max_new_tokens=4")
    assert res_kv_get.status_code == 200, f"KV-cache GET failed: {res_kv_get.status_code}"
    kv_json = res_kv_get.json()
    assert "steps" in kv_json, "KV-cache response missing 'steps'"
    assert len(kv_json["steps"]) == 4, f"KV-cache steps mismatch: {len(kv_json['steps'])} != 4"
    print(f"    [+] GET  /api/inspect/kv-cache -> Status 200 OK | {len(kv_json['steps'])} generation steps profiled")

    res_kv_post = client.post("/api/inspect/kv-cache", json={"prompt": "Transformer", "max_new_tokens": 2})
    assert res_kv_post.status_code == 200, f"KV-cache POST failed: {res_kv_post.status_code}"
    print(f"    [+] POST /api/inspect/kv-cache -> Status 200 OK")

    # B. Attention Heatmap Endpoint
    res_attn_get = client.get("/api/inspect/attention?prompt=TestPrompt&layer_idx=0&head_idx=0")
    assert res_attn_get.status_code == 200, f"Attention GET failed: {res_attn_get.status_code}"
    attn_json = res_attn_get.json()
    assert "attention_matrix" in attn_json, "Attention response missing 'attention_matrix'"
    assert attn_json.get("causal_validity") is True, "Attention heatmap failed causal validity check"
    print(f"    [+] GET  /api/inspect/attention -> Status 200 OK | Matrix size {len(attn_json['attention_matrix'])}x{len(attn_json['attention_matrix'][0])}")

    res_attn_post = client.post("/api/inspect/attention", json={"prompt": "Attention", "layer_idx": 0, "head_idx": 0})
    assert res_attn_post.status_code == 200, f"Attention POST failed: {res_attn_post.status_code}"
    print(f"    [+] POST /api/inspect/attention -> Status 200 OK")

    # C. Tokenizer Inspection Endpoint
    res_tok_get = client.get("/api/inspect/tokenizer?text=TestingTokenizer")
    assert res_tok_get.status_code == 200, f"Tokenizer GET failed: {res_tok_get.status_code}"
    tok_json = res_tok_get.json()
    assert "tokens" in tok_json, "Tokenizer response missing 'tokens'"
    assert "compression_ratio" in tok_json, "Tokenizer response missing 'compression_ratio'"
    assert tok_json.get("round_trip_match") is True, "Tokenizer round trip match failed"
    print(f"    [+] GET  /api/inspect/tokenizer -> Status 200 OK | Tokens: {tok_json['token_count']}, Compression: {tok_json['compression_ratio']:.2f}")

    res_tok_post = client.post("/api/inspect/tokenizer", json={"text": "ByteTokenizer"})
    assert res_tok_post.status_code == 200, f"Tokenizer POST failed: {res_tok_post.status_code}"
    print(f"    [+] POST /api/inspect/tokenizer -> Status 200 OK")

    # 4. Health & Hardware Memory Endpoints
    print("\n[4/4] Verifying Health & Hardware Telemetry Endpoints...")
    res_health = client.get("/api/health")
    assert res_health.status_code == 200, f"Health endpoint failed: {res_health.status_code}"
    print(f"    [+] GET  /api/health            -> Status 200 OK | Health Status: {res_health.json().get('status')}")

    res_mem = client.get("/api/hardware/memory")
    assert res_mem.status_code == 200, f"Hardware memory endpoint failed: {res_mem.status_code}"
    mem_json = res_mem.json()
    assert mem_json.get("within_memory_budget") is True, "Memory exceeded predefined ceiling"
    print(f"    [+] GET  /api/hardware/memory   -> Status 200 OK | Process RSS: {mem_json.get('process_rss_mb'):.2f} MB (Within 4.0GB Budget)")

    print("\n" + "=" * 70)
    print(" ALL DASHBOARD & CRISP-DM CHECKS PASSED (100%)")
    print("=" * 70)
    return True


# Pytest test function wrapper
def test_dashboard_acceptance():
    assert run_dashboard_verification() is True


if __name__ == "__main__":
    success = run_dashboard_verification()
    sys.exit(0 if success else 1)
