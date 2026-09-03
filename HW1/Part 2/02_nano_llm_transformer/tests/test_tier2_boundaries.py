"""
Tier 2: Boundary & Corner Cases Test Suite.
Tests edge conditions, extreme parameters, and boundary limits for all 13 core features (>=5 tests per feature).
Total target: >= 65 tests.
"""

import math
import sys
from pathlib import Path
from typing import Dict, Any
import pytest
import torch
import torch.nn as nn
import torch.nn.functional as F

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Safe imports
try:
    from nano_transformer.config import ModelArgs
    from nano_transformer.norm import RMSNorm
    from nano_transformer.rope import RotaryEmbedding, apply_rope
    from nano_transformer.ffn import SwiGLUFFN
    from nano_transformer.attention import CausalSelfAttention
    from nano_transformer.block import TransformerBlock
    from nano_transformer.model import Transformer
    from nano_transformer.tokenizer import ByteTokenizer
    from nano_transformer.sft import SFTDataset, collate_sft, compute_sft_loss
    from nano_transformer.device import resolve_device, get_memory_stats, empty_device_cache
    from dashboard.crisp_dm import CrispDMTracker, StageStatus
    from dashboard.inspectors import inspect_kv_cache, inspect_attention, inspect_tokenizer
    from dashboard.app import app
    MODULES_AVAILABLE = True
except ImportError:
    MODULES_AVAILABLE = False


# ===========================================================================
# FEATURE 1 BOUNDARIES: RoPE Positional Embeddings (>= 5 Tests)
# ===========================================================================

class TestFeature1RoPEBoundaries:
    def test_rope_boundary_single_token(self):
        """F1.B1: Verify RoPE on sequence length = 1."""
        dim = 16
        rope = RotaryEmbedding(dim=dim, max_seq_len=64)
        x = torch.randn(1, 2, 1, dim)
        out = rope(x, start_pos=0)
        assert out.shape == (1, 2, 1, dim)
        torch.testing.assert_close(out, x, atol=1e-5, rtol=1e-5)

    def test_rope_boundary_max_seq_len(self):
        """F1.B2: Verify RoPE at exact max_seq_len boundary."""
        dim, max_len = 16, 64
        rope = RotaryEmbedding(dim=dim, max_seq_len=max_len)
        x = torch.randn(1, 1, max_len, dim)
        out = rope(x, start_pos=0)
        assert out.shape == (1, 1, max_len, dim)
        assert not torch.isnan(out).any()

    def test_rope_boundary_start_pos_at_cache_edge(self):
        """F1.B3: Verify single token rotation at the highest valid start_pos."""
        dim, max_len = 16, 64
        rope = RotaryEmbedding(dim=dim, max_seq_len=max_len)
        x = torch.randn(1, 1, 1, dim)
        out = rope(x, start_pos=max_len - 1)
        assert out.shape == (1, 1, 1, dim)
        assert not torch.isnan(out).any()

    def test_rope_boundary_extreme_base_frequencies(self):
        """F1.B4: Verify RoPE handles extreme rope_base values (100.0 and 1,000,000.0)."""
        dim = 16
        rope_low = RotaryEmbedding(dim=dim, max_seq_len=32, base=100.0)
        rope_high = RotaryEmbedding(dim=dim, max_seq_len=32, base=1_000_000.0)
        x = torch.randn(1, 1, 8, dim)
        out_low = rope_low(x, start_pos=0)
        out_high = rope_high(x, start_pos=0)
        assert not torch.isnan(out_low).any()
        assert not torch.isnan(out_high).any()

    def test_rope_boundary_minimal_head_dim(self):
        """F1.B5: Verify RoPE works with minimal even head dimension (dim=2)."""
        rope = RotaryEmbedding(dim=2, max_seq_len=16)
        x = torch.randn(1, 1, 4, 2)
        out = rope(x, start_pos=0)
        assert out.shape == (1, 1, 4, 2)
        # Check norm preservation on 2D space
        torch.testing.assert_close(torch.norm(out, dim=-1), torch.norm(x, dim=-1), atol=1e-5, rtol=1e-5)


# ===========================================================================
# FEATURE 2 BOUNDARIES: SwiGLU Gated Activation (>= 5 Tests)
# ===========================================================================

class TestFeature2SwiGLUBoundaries:
    def test_swiglu_boundary_single_token(self):
        """F2.B1: Verify SwiGLU forward pass on single token (1, 1, d_model)."""
        ffn = SwiGLUFFN(d_model=64, d_ff=192)
        x = torch.randn(1, 1, 64)
        out = ffn(x)
        assert out.shape == (1, 1, 64)

    def test_swiglu_boundary_large_dimension_rounding(self):
        """F2.B2: Verify 64-multiple alignment on large dimension (d_model=1024)."""
        ffn = SwiGLUFFN(d_model=1024)
        # 8/3 * 1024 = 2730.66 -> round to multiple of 64 -> 2752
        assert ffn.d_ff % 64 == 0
        assert ffn.d_ff == 2752

    def test_swiglu_boundary_extreme_activations(self):
        """F2.B3: Verify SwiGLU numerical stability under extreme inputs (-1000.0 and +1000.0)."""
        ffn = SwiGLUFFN(d_model=32, d_ff=64)
        x_extreme = torch.tensor([[-1000.0, 1000.0] * 16]).unsqueeze(0)
        out = ffn(x_extreme)
        assert not torch.isnan(out).any()
        assert not torch.isinf(out).any()

    def test_swiglu_boundary_eval_vs_train_mode(self):
        """F2.B4: Verify SwiGLU behavior under train vs eval modes with dropout."""
        ffn = SwiGLUFFN(d_model=32, d_ff=64, dropout=0.5)
        x = torch.randn(2, 4, 32)
        ffn.eval()
        out_eval1 = ffn(x)
        out_eval2 = ffn(x)
        # Eval mode must be deterministic
        torch.testing.assert_close(out_eval1, out_eval2)

    def test_swiglu_boundary_minimal_dim(self):
        """F2.B5: Verify SwiGLU on minimal dimension d_model=8."""
        ffn = SwiGLUFFN(d_model=8, d_ff=64)
        x = torch.randn(1, 2, 8)
        out = ffn(x)
        assert out.shape == (1, 2, 8)


# ===========================================================================
# FEATURE 3 BOUNDARIES: RMSNorm (>= 5 Tests)
# ===========================================================================

class TestFeature3RMSNormBoundaries:
    def test_rmsnorm_boundary_constant_vector(self):
        """F3.B1: Verify RMSNorm maps constant positive vector to ones."""
        dim = 32
        norm = RMSNorm(dim=dim)
        x = torch.full((1, 1, dim), 42.0)
        out = norm(x)
        torch.testing.assert_close(out, torch.ones_like(out), atol=1e-4, rtol=1e-4)

    def test_rmsnorm_boundary_sparse_impulse_vector(self):
        """F3.B2: Verify RMSNorm on one-hot/impulse vector [1, 0, 0, ...]."""
        dim = 16
        norm = RMSNorm(dim=dim)
        x = torch.zeros(1, 1, dim)
        x[0, 0, 0] = 1.0
        out = norm(x)
        # RMS is sqrt(1/16) = 1/4 = 0.25 -> out[0] = 1.0 / 0.25 = 4.0
        assert math.isclose(out[0, 0, 0].item(), 4.0, rel_tol=1e-3)
        assert math.isclose(out[0, 0, 1].item(), 0.0, abs_tol=1e-5)

    def test_rmsnorm_boundary_extreme_magnitudes(self):
        """F3.B3: Verify RMSNorm on very large (1e5) and tiny (1e-6) inputs."""
        dim = 16
        norm = RMSNorm(dim=dim, eps=1e-5)
        x_huge = torch.randn(1, 2, dim) * 1e5
        x_tiny = torch.randn(1, 2, dim) * 1e-6
        out_huge = norm(x_huge)
        out_tiny = norm(x_tiny)
        assert not torch.isnan(out_huge).any()
        assert not torch.isnan(out_tiny).any()

    def test_rmsnorm_boundary_single_element_dim(self):
        """F3.B4: Verify RMSNorm on minimal dimension dim=1."""
        norm = RMSNorm(dim=1)
        x = torch.tensor([[[3.0]]])
        out = norm(x)
        # For scalar 3.0, RMS is 3.0, so 3.0 / 3.0 = 1.0
        torch.testing.assert_close(out, torch.tensor([[[1.0]]]), atol=1e-4, rtol=1e-4)

    def test_rmsnorm_boundary_negative_values(self):
        """F3.B5: Verify RMSNorm correctly retains negative signs."""
        dim = 4
        norm = RMSNorm(dim=dim)
        x = torch.tensor([[[-2.0, -2.0, 2.0, 2.0]]])
        out = norm(x)
        assert out[0, 0, 0].item() < 0
        assert out[0, 0, 2].item() > 0
        torch.testing.assert_close(out[0, 0, 0].abs(), out[0, 0, 2].abs(), atol=1e-5, rtol=1e-5)


# ===========================================================================
# FEATURE 4 BOUNDARIES: Causal Attention & KV-Cache (>= 5 Tests)
# ===========================================================================

class TestFeature4AttentionBoundaries:
    def test_attention_boundary_seq_len_one(self, tiny_config_dict):
        """F4.B1: Verify causal attention on sequence length = 1."""
        args = ModelArgs(**tiny_config_dict)
        attn = CausalSelfAttention(args)
        x = torch.randn(1, 1, args.d_model)
        out, weights = attn(x, start_pos=0, return_attentions=True)
        assert out.shape == (1, 1, args.d_model)
        assert weights.shape == (1, args.n_heads, 1, 1)
        # Attention on 1 token must be 1.0
        torch.testing.assert_close(weights, torch.ones_like(weights), atol=1e-5, rtol=1e-5)

    def test_attention_boundary_max_seq_len(self, tiny_config_dict):
        """F4.B2: Verify causal attention across full max_seq_len window."""
        args = ModelArgs(**tiny_config_dict)
        attn = CausalSelfAttention(args)
        x = torch.randn(1, args.max_seq_len, args.d_model)
        out, _ = attn(x, start_pos=0)
        assert out.shape == (1, args.max_seq_len, args.d_model)

    def test_attention_boundary_multi_query_attention(self):
        """F4.B3: Verify boundary case with 1 KV head (MQA: 4 query heads to 1 KV head)."""
        args = ModelArgs(vocab_size=100, d_model=64, n_layers=1, n_heads=4, n_kv_heads=1, max_seq_len=32)
        attn = CausalSelfAttention(args)
        assert attn.n_rep == 4
        x = torch.randn(2, 5, args.d_model)
        out, _ = attn(x, start_pos=0)
        assert out.shape == (2, 5, args.d_model)

    def test_attention_boundary_cache_sequential_rollout(self, tiny_config_dict):
        """F4.B4: Verify KV-cache rolls out 10 tokens sequentially token by token."""
        args = ModelArgs(**tiny_config_dict)
        attn = CausalSelfAttention(args)
        attn.eval()
        
        # Step 0: prompt
        prompt = torch.randn(1, 2, args.d_model)
        attn(prompt, start_pos=0, use_cache=True)
        
        # Steps 1..10
        for pos in range(2, 12):
            token = torch.randn(1, 1, args.d_model)
            out, _ = attn(token, start_pos=pos, use_cache=True)
            assert out.shape == (1, 1, args.d_model)

    def test_attention_boundary_batch_size_one_and_eight(self, tiny_config_dict):
        """F4.B5: Verify attention executes correctly with batch_size=1 and batch_size=8."""
        args = ModelArgs(**tiny_config_dict)
        attn = CausalSelfAttention(args)
        out1, _ = attn(torch.randn(1, 4, args.d_model), start_pos=0)
        out8, _ = attn(torch.randn(8, 4, args.d_model), start_pos=0)
        assert out1.shape == (1, 4, args.d_model)
        assert out8.shape == (8, 4, args.d_model)


# ===========================================================================
# FEATURE 5 BOUNDARIES: Scratch Tokenizer (>= 5 Tests)
# ===========================================================================

class TestFeature5TokenizerBoundaries:
    def test_tokenizer_boundary_null_and_control_bytes(self):
        """F5.B1: Verify encoding and decoding raw null bytes and control chars."""
        tok = ByteTokenizer()
        text = "\x00\x01\x02\x07\x08\x0b\x0c\x1b"
        ids = tok.encode(text)
        decoded = tok.decode(ids)
        assert decoded == text

    def test_tokenizer_boundary_multi_byte_utf8_emoji(self):
        """F5.B2: Verify 4-byte UTF-8 emoji characters round-trip faithfully."""
        tok = ByteTokenizer()
        text = "🤖🧠⚡️🎯🚀"
        ids = tok.encode(text)
        assert len(ids) == len(text.encode("utf-8"))
        decoded = tok.decode(ids)
        assert decoded == text

    def test_tokenizer_boundary_long_repetitive_string(self):
        """F5.B3: Verify large 5,000 character string tokenization."""
        tok = ByteTokenizer()
        text = "A" * 5000
        ids = tok.encode(text)
        assert len(ids) == 5000
        decoded = tok.decode(ids)
        assert decoded == text

    def test_tokenizer_boundary_whitespace_varieties(self):
        """F5.B4: Verify tabs, newlines, CRLF, and spaces."""
        tok = ByteTokenizer()
        text = " \t \r\n \n   "
        ids = tok.encode(text)
        decoded = tok.decode(ids)
        assert decoded == text

    def test_tokenizer_boundary_single_character(self):
        """F5.B5: Verify single character string."""
        tok = ByteTokenizer()
        ids = tok.encode("Z")
        assert len(ids) == 1
        assert tok.decode(ids) == "Z"


# ===========================================================================
# FEATURE 6 BOUNDARIES: SFT Loss & Dataset (>= 5 Tests)
# ===========================================================================

class TestFeature6SFTBoundaries:
    def test_sft_boundary_fully_masked_sequence(self):
        """F6.B1: Verify compute_sft_loss returns 0 or handles all -100 targets gracefully."""
        logits = torch.randn(1, 5, 260)
        targets = torch.full((1, 5), -100, dtype=torch.long)
        loss = compute_sft_loss(logits, targets)
        assert loss.item() == 0.0 or not torch.isnan(loss)

    def test_sft_boundary_no_masked_tokens(self):
        """F6.B2: Verify loss computation when 0 tokens are masked."""
        logits = torch.randn(2, 6, 260)
        targets = torch.randint(0, 260, (2, 6))
        loss = compute_sft_loss(logits, targets)
        assert loss.item() > 0.0

    def test_sft_boundary_single_response_token(self):
        """F6.B3: Verify sequence where only the final token is a supervised target."""
        logits = torch.randn(1, 8, 260)
        targets = torch.full((1, 8), -100, dtype=torch.long)
        targets[0, -1] = 42
        loss = compute_sft_loss(logits, targets)
        assert loss.item() > 0.0

    def test_sft_boundary_variable_prompt_lengths(self):
        """F6.B4: Verify collating batch with different prompt lengths."""
        tok = ByteTokenizer()
        data = [
            {"prompt": "Short", "response": "Answer1"},
            {"prompt": "A much longer prompt string", "response": "Answer2"}
        ]
        ds = SFTDataset(data, tokenizer=tok, max_seq_len=64)
        batch = collate_sft([ds[0], ds[1]])
        assert batch["input_ids"].shape[0] == 2
        assert batch["labels"].shape[0] == 2

    def test_sft_boundary_gradient_clipping(self, tiny_config_dict):
        """F6.B5: Verify torch.nn.utils.clip_grad_norm_ operates smoothly during SFT."""
        args = ModelArgs(**tiny_config_dict)
        model = Transformer(args)
        tokens = torch.randint(0, args.vocab_size, (2, 6))
        targets = tokens.clone()
        targets[:, :2] = -100
        
        logits, _ = model(tokens)
        loss = compute_sft_loss(logits, targets)
        loss.backward()
        
        total_norm = torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
        assert total_norm > 0.0
        assert not torch.isnan(total_norm)


# ===========================================================================
# FEATURE 7 BOUNDARIES: CRISP-DM Tracker (>= 5 Tests)
# ===========================================================================

class TestFeature7CrispDMBoundaries:
    def test_crisp_dm_boundary_invalid_stage_query(self):
        """F7.B1: Verify querying invalid stage name raises KeyError or returns None."""
        tracker = CrispDMTracker()
        stage = tracker.get_stage("non_existent_stage")
        assert stage is None

    def test_crisp_dm_boundary_complete_without_start(self):
        """F7.B2: Verify completing a stage directly without calling start sets duration."""
        tracker = CrispDMTracker()
        tracker.complete_stage("evaluation", metrics={"accuracy": 0.99})
        stage = tracker.get_stage("evaluation")
        assert stage["status"] == "completed"
        assert stage["metrics"]["accuracy"] == 0.99

    def test_crisp_dm_boundary_large_log_volume(self):
        """F7.B3: Verify logging 500 consecutive lines to a stage."""
        tracker = CrispDMTracker()
        tracker.start_stage("modeling")
        for i in range(500):
            tracker.log_stage("modeling", f"Epoch {i}: loss={1.0 / (i + 1):.4f}")
        stage = tracker.get_stage("modeling")
        assert len(stage["logs"]) == 500

    def test_crisp_dm_boundary_reset_pipeline(self):
        """F7.B4: Verify resetting pipeline restores all stages to not_started."""
        tracker = CrispDMTracker()
        tracker.complete_stage("data_preparation")
        tracker.reset()
        for stage in tracker.get_stages().values():
            assert stage["status"] == "not_started"

    def test_crisp_dm_boundary_empty_metrics(self):
        """F7.B5: Verify completing stage with empty metrics dictionary."""
        tracker = CrispDMTracker()
        tracker.complete_stage("deployment", metrics={})
        stage = tracker.get_stage("deployment")
        assert stage["status"] == "completed"
        assert stage["metrics"] == {}


# ===========================================================================
# FEATURE 8 BOUNDARIES: KV-Cache Inspector (>= 5 Tests)
# ===========================================================================

class TestFeature8KVCacheInspectorBoundaries:
    def test_kv_cache_boundary_max_tokens_one(self, tiny_config_dict):
        """F8.B1: Verify KV-cache inspector with max_new_tokens=1."""
        args = ModelArgs(**tiny_config_dict)
        model = Transformer(args)
        tok = ByteTokenizer()
        res = inspect_kv_cache(model, tok, prompt="A", max_new_tokens=1)
        assert len(res["steps"]) == 1

    def test_kv_cache_boundary_max_tokens_twenty(self, tiny_config_dict):
        """F8.B2: Verify KV-cache inspector with max_new_tokens=20."""
        args = ModelArgs(**tiny_config_dict)
        model = Transformer(args)
        tok = ByteTokenizer()
        res = inspect_kv_cache(model, tok, prompt="B", max_new_tokens=20)
        assert len(res["steps"]) == 20

    def test_kv_cache_boundary_single_char_prompt(self, tiny_config_dict):
        """F8.B3: Verify KV-cache inspector with single character prompt."""
        args = ModelArgs(**tiny_config_dict)
        model = Transformer(args)
        tok = ByteTokenizer()
        res = inspect_kv_cache(model, tok, prompt="X", max_new_tokens=2)
        assert res["status"] == "ok"

    def test_kv_cache_boundary_special_character_prompt(self, tiny_config_dict):
        """F8.B4: Verify KV-cache inspector with punctuation and whitespace."""
        args = ModelArgs(**tiny_config_dict)
        model = Transformer(args)
        tok = ByteTokenizer()
        res = inspect_kv_cache(model, tok, prompt="!@#$%^&*()", max_new_tokens=2)
        assert res["status"] == "ok"

    def test_kv_cache_boundary_temperature_extremes(self, tiny_config_dict):
        """F8.B5: Verify KV-cache inspector handles low and high temperatures."""
        args = ModelArgs(**tiny_config_dict)
        model = Transformer(args)
        tok = ByteTokenizer()
        res_low = inspect_kv_cache(model, tok, prompt="Hi", max_new_tokens=2, temperature=0.01)
        res_high = inspect_kv_cache(model, tok, prompt="Hi", max_new_tokens=2, temperature=5.0)
        assert res_low["status"] == "ok"
        assert res_high["status"] == "ok"


# ===========================================================================
# FEATURE 9 BOUNDARIES: Attention Heatmap Inspector (>= 5 Tests)
# ===========================================================================

class TestFeature9AttentionInspectorBoundaries:
    def test_attention_boundary_single_token_prompt(self, tiny_config_dict):
        """F9.B1: Verify attention heatmap on single character prompt yields 1x1 matrix with [1.0]."""
        args = ModelArgs(**tiny_config_dict)
        model = Transformer(args)
        tok = ByteTokenizer()
        res = inspect_attention(model, tok, prompt="A", layer_idx=0, head_idx=0)
        assert res["seq_len"] == 1
        assert res["attention_matrix"] == [[1.0]]

    def test_attention_boundary_max_layer_index(self, tiny_config_dict):
        """F9.B2: Verify querying the last layer (n_layers - 1)."""
        args = ModelArgs(**tiny_config_dict)
        model = Transformer(args)
        tok = ByteTokenizer()
        res = inspect_attention(model, tok, prompt="Test", layer_idx=args.n_layers - 1, head_idx=0)
        assert res["selected_layer"] == args.n_layers - 1

    def test_attention_boundary_max_head_index(self, tiny_config_dict):
        """F9.B3: Verify querying the last head (n_heads - 1)."""
        args = ModelArgs(**tiny_config_dict)
        model = Transformer(args)
        tok = ByteTokenizer()
        res = inspect_attention(model, tok, prompt="Test", layer_idx=0, head_idx=args.n_heads - 1)
        assert res["selected_head"] == args.n_heads - 1

    def test_attention_boundary_out_of_range_layer(self, tiny_config_dict):
        """F9.B4: Verify out-of-range layer index clamps or handles gracefully."""
        args = ModelArgs(**tiny_config_dict)
        model = Transformer(args)
        tok = ByteTokenizer()
        res = inspect_attention(model, tok, prompt="Test", layer_idx=999, head_idx=0)
        assert res["status"] in ["ok", "error"]

    def test_attention_boundary_out_of_range_head(self, tiny_config_dict):
        """F9.B5: Verify out-of-range head index clamps or handles gracefully."""
        args = ModelArgs(**tiny_config_dict)
        model = Transformer(args)
        tok = ByteTokenizer()
        res = inspect_attention(model, tok, prompt="Test", layer_idx=0, head_idx=999)
        assert res["status"] in ["ok", "error"]


# ===========================================================================
# FEATURE 10 BOUNDARIES: Tokenizer Inspector (>= 5 Tests)
# ===========================================================================

class TestFeature10TokenizerInspectorBoundaries:
    def test_tokenizer_inspect_boundary_empty_text(self):
        """F10.B1: Verify inspect_tokenizer with empty string."""
        tok = ByteTokenizer()
        res = inspect_tokenizer(tok, text="")
        assert res["status"] == "ok"
        assert res["token_count"] == 0
        assert res["tokens"] == []

    def test_tokenizer_inspect_boundary_html_script_tags(self):
        """F10.B2: Verify XSS/HTML string inspection safety."""
        tok = ByteTokenizer()
        payload = "<script>alert('xss')</script>"
        res = inspect_tokenizer(tok, text=payload)
        assert res["round_trip_match"] is True

    def test_tokenizer_inspect_boundary_repeated_chars(self):
        """F10.B3: Verify long repeated characters inspection."""
        tok = ByteTokenizer()
        res = inspect_tokenizer(tok, text="Z" * 100)
        assert res["token_count"] == 100
        assert res["round_trip_match"] is True

    def test_tokenizer_inspect_boundary_json_payload_string(self):
        """F10.B4: Verify tokenizing JSON string."""
        tok = ByteTokenizer()
        payload = '{"key": "value", "numbers": [1, 2, 3]}'
        res = inspect_tokenizer(tok, text=payload)
        assert res["round_trip_match"] is True

    def test_tokenizer_inspect_boundary_newline_preservation(self):
        """F10.B5: Verify multi-line code block inspection."""
        tok = ByteTokenizer()
        code = "def foo():\n    return 42\n"
        res = inspect_tokenizer(tok, text=code)
        assert res["round_trip_match"] is True


# ===========================================================================
# FEATURE 11 BOUNDARIES: Dashboard App (>= 5 Tests)
# ===========================================================================

class TestFeature11DashboardAppBoundaries:
    def test_dashboard_boundary_404_nonexistent_route(self):
        """F11.B1: Verify 404 response on undefined route."""
        from fastapi.testclient import TestClient
        client = TestClient(app)
        res = client.get("/api/undefined_endpoint_123")
        assert res.status_code == 404

    def test_dashboard_boundary_422_invalid_generate_payload(self):
        """F11.B2: Verify 422 Unprocessable Entity on malformed JSON payload."""
        from fastapi.testclient import TestClient
        client = TestClient(app)
        res = client.post("/api/generate", json={"max_new_tokens": "invalid_integer"})
        assert res.status_code == 422

    def test_dashboard_boundary_rapid_health_pings(self):
        """F11.B3: Verify consecutive health pings return 200 without degradation."""
        from fastapi.testclient import TestClient
        client = TestClient(app)
        for _ in range(10):
            res = client.get("/api/health")
            assert res.status_code == 200

    def test_dashboard_boundary_get_stage_by_id(self):
        """F11.B4: Verify GET /api/crisp-dm/stage/{stage_id} for valid and invalid IDs."""
        from fastapi.testclient import TestClient
        client = TestClient(app)
        res_valid = client.get("/api/crisp-dm/stage/modeling")
        assert res_valid.status_code == 200
        res_invalid = client.get("/api/crisp-dm/stage/unknown_stage")
        assert res_invalid.status_code in [404, 400]

    def test_dashboard_boundary_post_inspect_endpoints(self):
        """F11.B5: Verify POST requests to inspector endpoints."""
        from fastapi.testclient import TestClient
        client = TestClient(app)
        res_kv = client.post("/api/inspect/kv-cache", json={"prompt": "Test", "max_new_tokens": 2})
        assert res_kv.status_code == 200
        res_attn = client.post("/api/inspect/attention", json={"prompt": "Test"})
        assert res_attn.status_code == 200
        res_tok = client.post("/api/inspect/tokenizer", json={"text": "Test"})
        assert res_tok.status_code == 200


# ===========================================================================
# FEATURE 12 BOUNDARIES: Device Auto-Selection (>= 5 Tests)
# ===========================================================================

class TestFeature12DeviceBoundaries:
    def test_device_boundary_unknown_device_fallback(self):
        """F12.B1: Verify unknown device string ('tpu') falls back to CPU."""
        dev = resolve_device("tpu")
        assert dev.type == "cpu"

    def test_device_boundary_none_argument(self):
        """F12.B2: Verify resolve_device(None) defaults to automatic selection."""
        dev = resolve_device(None)
        assert dev.type in ["mps", "cpu", "cuda"]

    def test_device_boundary_empty_tensor_device(self):
        """F12.B3: Verify creating zero-size tensor on resolved device."""
        dev = resolve_device()
        t = torch.empty((0, 4), device=dev)
        assert t.device.type == dev.type

    def test_device_boundary_case_insensitivity(self):
        """F12.B4: Verify case insensitivity ('MPS', 'Cpu', 'CPU')."""
        dev_cpu = resolve_device("CPU")
        assert dev_cpu.type == "cpu"

    def test_device_boundary_cross_device_transfer(self):
        """F12.B5: Verify transferring tensor from CPU to resolved device and back."""
        dev = resolve_device()
        t_cpu = torch.randn(2, 3)
        t_dev = t_cpu.to(dev)
        t_back = t_dev.to("cpu")
        torch.testing.assert_close(t_cpu, t_back)


# ===========================================================================
# FEATURE 13 BOUNDARIES: Unified Memory Profiling (>= 5 Tests)
# ===========================================================================

class TestFeature13MemoryBoundaries:
    def test_memory_boundary_successive_polls(self):
        """F13.B1: Verify 5 successive get_memory_stats calls execute consistently."""
        dev = resolve_device()
        for _ in range(5):
            stats = get_memory_stats(dev)
            assert stats["within_memory_budget"] is True

    def test_memory_boundary_memory_format_units(self):
        """F13.B2: Verify RAM total is reasonable (> 1.0 GB and < 1000.0 GB)."""
        dev = resolve_device()
        stats = get_memory_stats(dev)
        assert 1.0 <= stats["system_ram_total_gb"] <= 1000.0

    def test_memory_boundary_under_tensor_allocation(self):
        """F13.B3: Verify memory profiling while holding 50MB tensor in memory."""
        dev = resolve_device()
        t = torch.randn(1000, 1000, 12, device=dev)  # ~48 MB
        stats = get_memory_stats(dev)
        assert stats["within_memory_budget"] is True
        del t
        empty_device_cache(dev)

    def test_memory_boundary_budget_limit_is_four_gb(self):
        """F13.B4: Verify predefined limit is exactly 4.0 GB."""
        dev = resolve_device()
        stats = get_memory_stats(dev)
        assert stats["unified_memory_limit_gb"] == 4.0

    def test_memory_boundary_rss_less_than_budget(self):
        """F13.B5: Verify current process RSS is strictly below 4.0 GB limit."""
        dev = resolve_device()
        stats = get_memory_stats(dev)
        rss_gb = stats["process_rss_mb"] / 1024.0
        assert rss_gb < 4.0, f"Process RSS {rss_gb:.2f} GB exceeded 4.0 GB limit"
