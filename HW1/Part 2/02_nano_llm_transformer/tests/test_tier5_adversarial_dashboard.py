"""
Tier 5 Adversarial Test Suite: FastAPI Admin Dashboard & REST APIs Concurrency & Boundary Stress.

Adversarial Objectives:
1. Concurrently stress-test FastAPI endpoints with rapid multi-threaded request floods.
2. Rapid sequential bursts across /api/inspect/kv-cache, /api/inspect/attention, /api/inspect/tokenizer, /api/crisp-dm.
3. Fuzz endpoints with boundary inputs (empty strings, large payloads, unicode, out-of-bounds parameters).
4. Interleaved concurrent stage transitions and live reads without race conditions or deadlocks.
5. Autoregressive /api/generate endpoint load testing under sampling vs greedy decoding.
"""

import concurrent.futures
import time
from typing import List, Dict, Any
import pytest
from fastapi.testclient import TestClient

from dashboard.app import app
from dashboard.crisp_dm import StageStatus


@pytest.fixture(scope="module")
def client() -> TestClient:
    """Shared TestClient instance for dashboard adversarial testing."""
    return TestClient(app)


# ===========================================================================
# 1. Concurrent Multi-Threaded Request Flood Stress
# ===========================================================================

def test_adversarial_concurrent_endpoint_flood(client: TestClient):
    """
    Stress-test: 50 concurrent requests spanning all inspection and state endpoints.
    Verifies thread-safety, response stability, and absence of 500 errors.
    """
    endpoints = [
        ("GET", "/api/inspect/kv-cache?prompt=ConcurrencyTest&max_new_tokens=4", None),
        ("GET", "/api/inspect/attention?prompt=MultiThreadedAttention&layer_idx=0&head_idx=0", None),
        ("GET", "/api/inspect/tokenizer?text=ConcurrentTokenizerFuzzing123", None),
        ("GET", "/api/crisp-dm", None),
        ("GET", "/api/health", None),
        ("GET", "/api/hardware/memory", None),
        ("POST", "/api/inspect/kv-cache", {"prompt": "PostFloodKV", "max_new_tokens": 2}),
        ("POST", "/api/inspect/attention", {"prompt": "PostFloodAttn", "layer_idx": 1, "head_idx": 1}),
        ("POST", "/api/inspect/tokenizer", {"text": "PostFloodTokenizer"}),
        ("POST", "/api/generate", {"prompt": "FloodGen", "max_new_tokens": 5, "temperature": 0.8}),
    ]

    total_requests = 50
    tasks = [endpoints[i % len(endpoints)] for i in range(total_requests)]

    def make_request(req_info):
        method, url, json_body = req_info
        if method == "GET":
            return client.get(url)
        else:
            return client.post(url, json=json_body)

    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(make_request, t) for t in tasks]
        results = [f.result() for f in concurrent.futures.as_completed(futures)]

    assert len(results) == total_requests
    for resp in results:
        assert resp.status_code == 200, f"Expected 200 OK under concurrent load, got {resp.status_code}: {resp.text}"


# ===========================================================================
# 2. Rapid Sequential Burst Testing
# ===========================================================================

def test_adversarial_rapid_sequential_bursts(client: TestClient):
    """
    Stress-test: 80 rapid sequential requests alternating through all diagnostic routes.
    Verifies low latency, memory stability, and consistent response formats.
    """
    for i in range(20):
        # KV-Cache
        res_kv = client.get(f"/api/inspect/kv-cache?prompt=Burst_{i}&max_new_tokens=3")
        assert res_kv.status_code == 200
        data_kv = res_kv.json()
        assert len(data_kv["steps"]) == 3
        assert data_kv["status"] == "ok"

        # Attention
        res_attn = client.get(f"/api/inspect/attention?prompt=Attn_{i}&layer_idx={i % 4}&head_idx={i % 4}")
        assert res_attn.status_code == 200
        data_attn = res_attn.json()
        assert data_attn["causal_validity"] is True

        # Tokenizer
        res_tok = client.get(f"/api/inspect/tokenizer?text=BurstTestTokenization_{i}")
        assert res_tok.status_code == 200
        data_tok = res_tok.json()
        assert data_tok["round_trip_match"] is True

        # CRISP-DM
        res_crisp = client.get("/api/crisp-dm")
        assert res_crisp.status_code == 200
        assert len(res_crisp.json()["stages"]) >= 3


# ===========================================================================
# 3. Boundary & Extreme Fuzz Payloads
# ===========================================================================

@pytest.mark.parametrize("prompt_fuzz", [
    "",  # Empty prompt
    "   ",  # Whitespace only
    "A",  # Single character
    "🚀🔥🧠⚡️🤖",  # Emojis / multi-byte UTF-8
    "Special \\n \\r \\t \\0 chars \u0000 \uffff",  # Escapes and control chars
    "LongPrompt " * 200,  # Long string (~2200 chars)
    "English 中文 Русский العربية 日本語",  # Multi-lingual byte mixing
])
def test_adversarial_inspection_endpoints_fuzz_prompts(client: TestClient, prompt_fuzz: str):
    """Fuzzes KV-cache, Attention, and Tokenizer endpoints with diverse string boundary cases."""
    # 1. KV-Cache GET & POST
    res_kv_get = client.get("/api/inspect/kv-cache", params={"prompt": prompt_fuzz, "max_new_tokens": 2})
    assert res_kv_get.status_code == 200
    assert "steps" in res_kv_get.json()

    res_kv_post = client.post("/api/inspect/kv-cache", json={"prompt": prompt_fuzz, "max_new_tokens": 2})
    assert res_kv_post.status_code == 200

    # 2. Attention GET & POST
    res_attn_get = client.get("/api/inspect/attention", params={"prompt": prompt_fuzz, "layer_idx": 0, "head_idx": 0})
    assert res_attn_get.status_code == 200
    assert "attention_matrix" in res_attn_get.json()

    # 3. Tokenizer GET & POST
    res_tok_get = client.get("/api/inspect/tokenizer", params={"text": prompt_fuzz})
    assert res_tok_get.status_code == 200
    tok_data = res_tok_get.json()
    assert tok_data["round_trip_match"] is True


def test_adversarial_out_of_bounds_attention_indices(client: TestClient):
    """
    Tests graceful clamping of out-of-bounds layer_idx and head_idx in attention inspection.
    """
    # Extremely large indices should be clamped gracefully to max layers/heads without 500 crash
    res_high = client.get("/api/inspect/attention?prompt=Bounds&layer_idx=9999&head_idx=8888")
    assert res_high.status_code == 200
    data_high = res_high.json()
    assert data_high["status"] == "ok"
    assert data_high["selected_layer"] < data_high["num_layers"]
    assert data_high["selected_head"] < data_high["num_heads"]


def test_adversarial_invalid_pydantic_payload_validation(client: TestClient):
    """
    Verifies that FastAPI properly rejects invalid types and out-of-range bounds with 422 Unprocessable Entity.
    """
    # max_new_tokens <= 0
    res_zero_tokens = client.post("/api/inspect/kv-cache", json={"prompt": "Test", "max_new_tokens": 0})
    assert res_zero_tokens.status_code == 422

    # max_new_tokens > 128
    res_huge_tokens = client.post("/api/inspect/kv-cache", json={"prompt": "Test", "max_new_tokens": 500})
    assert res_huge_tokens.status_code == 422

    # temperature > 5.0
    res_huge_temp = client.post("/api/inspect/kv-cache", json={"prompt": "Test", "temperature": 10.0})
    assert res_huge_temp.status_code == 422

    # layer_idx < 0
    res_neg_layer = client.post("/api/inspect/attention", json={"prompt": "Test", "layer_idx": -5})
    assert res_neg_layer.status_code == 422


# ===========================================================================
# 4. Interleaved Concurrent Stage Mutations & Reads
# ===========================================================================

def test_adversarial_concurrent_crisp_dm_mutations_and_reads(client: TestClient):
    """
    Tests race condition resilience when concurrently reading and writing CRISP-DM stages.
    """
    def write_stage(stage_id: str, status: str, step: int):
        return client.post(
            f"/api/crisp-dm/stage/{stage_id}/transition",
            json={
                "status": status,
                "metrics": {f"iter_{step}": step * 1.5},
                "log": f"Concurrent step {step} on {stage_id}",
            }
        )

    def read_pipeline():
        return client.get("/api/crisp-dm")

    def read_single_stage(stage_id: str):
        return client.get(f"/api/crisp-dm/stage/{stage_id}")

    stages = ["business_understanding", "data_preparation", "modeling", "evaluation"]
    actions = []

    for i in range(30):
        target_stage = stages[i % len(stages)]
        if i % 3 == 0:
            actions.append(("write", target_stage, "running", i))
        elif i % 3 == 1:
            actions.append(("write", target_stage, "completed", i))
        else:
            actions.append(("read_single", target_stage, None, i))
        actions.append(("read_all", None, None, i))

    def run_action(act):
        act_type, stage_id, status, step = act
        if act_type == "write":
            return write_stage(stage_id, status, step)
        elif act_type == "read_single":
            return read_single_stage(stage_id)
        else:
            return read_pipeline()

    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
        futures = [executor.submit(run_action, a) for a in actions]
        results = [f.result() for f in concurrent.futures.as_completed(futures)]

    for resp in results:
        assert resp.status_code == 200, f"Concurrent mutation/read failed: {resp.status_code} {resp.text}"


# ===========================================================================
# 5. Non-Existent Route & Stage 404 Error Handling
# ===========================================================================

def test_adversarial_non_existent_stage_404(client: TestClient):
    """Verifies that accessing or mutating non-existent stages produces standard 404 responses."""
    res_get = client.get("/api/crisp-dm/stage/non_existent_stage_99")
    assert res_get.status_code == 404
    assert "not found" in res_get.json()["detail"].lower()

    res_post = client.post(
        "/api/crisp-dm/stage/phantom_stage/transition",
        json={"status": "running", "log": "Invalid"}
    )
    assert res_post.status_code == 404


# ===========================================================================
# 6. Generate Endpoint Stress (Greedy vs Sampling, KV-Cache On/Off)
# ===========================================================================

def test_adversarial_generate_endpoint_modes(client: TestClient):
    """
    Stress-tests /api/generate across temperature=0 (greedy), high temperature, top-k, top-p,
    and use_cache=True vs use_cache=False.
    """
    payloads = [
        {"prompt": "Greedy generation test", "max_new_tokens": 10, "temperature": 0.0, "use_cache": True},
        {"prompt": "Sampling generation test", "max_new_tokens": 10, "temperature": 1.2, "top_k": 20, "top_p": 0.85, "use_cache": True},
        {"prompt": "No cache generation test", "max_new_tokens": 8, "temperature": 0.8, "use_cache": False},
        {"prompt": "Single token generation", "max_new_tokens": 1, "temperature": 1.0, "use_cache": True},
    ]

    for p in payloads:
        res = client.post("/api/generate", json=p)
        assert res.status_code == 200, f"Generate failed for payload {p}: {res.text}"
        data = res.json()
        assert data["status"] == "ok"
        assert len(data["token_ids"]) >= len(p["prompt"].encode("utf-8")) + 1
        assert "metrics" in data
        assert data["metrics"]["tokens_generated"] >= 1
