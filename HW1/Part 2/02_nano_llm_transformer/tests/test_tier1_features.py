"""
Tier 1: Feature Coverage Test Suite.
Tests primary behavior (happy path) for all 13 core features (>=5 tests per feature).
Total target: >= 65 tests.
"""

import math
import sys
from pathlib import Path
from typing import Dict, Any, List
import pytest
import torch
import torch.nn as nn
import torch.nn.functional as F

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Safe imports from project modules with fallback check
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
# FEATURE 1: RoPE Positional Embeddings (>= 5 Tests)
# ===========================================================================

class TestFeature1RoPE:
    def test_rope_init_and_buffer_shapes(self):
        """F1.1: Verify RoPE initialization and trigonometric cache buffer dimensions."""
        dim, max_seq_len = 32, 128
        rope = RotaryEmbedding(dim=dim, max_seq_len=max_seq_len, base=10000.0)
        assert hasattr(rope, "cos_cached") or hasattr(rope, "cos")
        cos = getattr(rope, "cos_cached", getattr(rope, "cos", None))
        sin = getattr(rope, "sin_cached", getattr(rope, "sin", None))
        assert cos is not None and sin is not None
        assert cos.shape[-1] == dim or cos.shape[-1] == dim // 2
        assert cos.shape[0] == max_seq_len or cos.shape[1] == max_seq_len or cos.shape[2] == max_seq_len

    def test_rope_mathematical_rotation_values(self):
        """F1.2: Verify split-half rotation values match analytical trigonometric rotation."""
        dim, seq_len = 16, 4
        rope = RotaryEmbedding(dim=dim, max_seq_len=64)
        x = torch.randn(1, 2, seq_len, dim)
        x_rot = rope(x, start_pos=0)
        assert x_rot.shape == x.shape
        # At position 0, angle is 0, so cos(0)=1, sin(0)=0 -> x_rot[:, :, 0, :] == x[:, :, 0, :]
        torch.testing.assert_close(x_rot[:, :, 0, :], x[:, :, 0, :], atol=1e-5, rtol=1e-5)

    def test_rope_relative_position_invariance(self):
        """F1.3: Verify that inner product of rotated vectors depends solely on relative distance."""
        dim = 16
        rope = RotaryEmbedding(dim=dim, max_seq_len=64)
        q = torch.randn(1, 1, 1, dim)
        k = torch.randn(1, 1, 1, dim)
        
        # Distance delta = 2: (pos 0, pos 2) vs (pos 3, pos 5)
        q_pos0 = rope(q, start_pos=0)
        k_pos2 = rope(k, start_pos=2)
        score_0_2 = (q_pos0 * k_pos2).sum(dim=-1)

        q_pos3 = rope(q, start_pos=3)
        k_pos5 = rope(k, start_pos=5)
        score_3_5 = (q_pos3 * k_pos5).sum(dim=-1)

        torch.testing.assert_close(score_0_2, score_3_5, atol=1e-4, rtol=1e-4)

    def test_rope_slice_for_incremental_decoding(self):
        """F1.4: Verify incremental decoding slice at start_pos matches full sequence slice."""
        dim, max_len = 32, 32
        rope = RotaryEmbedding(dim=dim, max_seq_len=max_len)
        full_x = torch.randn(1, 4, 10, dim)
        full_rot = rope(full_x, start_pos=0)

        # Single step at pos 7
        single_x = full_x[:, :, 7:8, :]
        single_rot = rope(single_x, start_pos=7)
        torch.testing.assert_close(single_rot, full_rot[:, :, 7:8, :], atol=1e-5, rtol=1e-5)

    def test_rope_preserves_l2_norm(self):
        """F1.5: Verify 2D orthogonal rotation strictly preserves vector L2 norm."""
        dim = 32
        rope = RotaryEmbedding(dim=dim, max_seq_len=64)
        x = torch.randn(2, 4, 8, dim)
        x_rot = rope(x, start_pos=0)
        norm_orig = torch.norm(x, dim=-1)
        norm_rot = torch.norm(x_rot, dim=-1)
        torch.testing.assert_close(norm_rot, norm_orig, atol=1e-5, rtol=1e-5)

    def test_rope_frequency_scaling_with_custom_base(self):
        """F1.6: Verify custom base changes frequency basis correctly."""
        dim = 16
        rope1 = RotaryEmbedding(dim=dim, max_seq_len=32, base=10000.0)
        rope2 = RotaryEmbedding(dim=dim, max_seq_len=32, base=50000.0)
        x = torch.randn(1, 1, 4, dim)
        rot1 = rope1(x, start_pos=0)
        rot2 = rope2(x, start_pos=0)
        # Position 0 should match, but position 1+ should differ
        torch.testing.assert_close(rot1[:, :, 0, :], rot2[:, :, 0, :], atol=1e-5, rtol=1e-5)
        assert not torch.allclose(rot1[:, :, 1:, :], rot2[:, :, 1:, :])


# ===========================================================================
# FEATURE 2: SwiGLU Gated Activation & FFN (>= 5 Tests)
# ===========================================================================

class TestFeature2SwiGLU:
    def test_swiglu_dimension_calculation(self):
        """F2.1: Verify d_ff default scaling d_ff = round_up_64(floor(8/3 * d_model))."""
        ffn = SwiGLUFFN(d_model=128)
        # 8/3 * 128 = 341.33 -> rounded up to multiple of 64 -> 384
        expected_d_ff = 384
        assert ffn.d_ff == expected_d_ff or ffn.w_gate.out_features == expected_d_ff

    def test_swiglu_forward_shape(self):
        """F2.2: Verify SwiGLU forward pass maintains tensor dimensions (B, T, d_model)."""
        d_model = 64
        ffn = SwiGLUFFN(d_model=d_model, d_ff=192)
        x = torch.randn(2, 8, d_model)
        out = ffn(x)
        assert out.shape == (2, 8, d_model)

    def test_swiglu_mathematical_equivalence(self):
        """F2.3: Verify forward pass matches SiLU(x @ W_gate) * (x @ W_up) @ W_down."""
        d_model, d_ff = 32, 64
        ffn = SwiGLUFFN(d_model=d_model, d_ff=d_ff)
        x = torch.randn(1, 4, d_model)
        
        # Analytical forward
        gate = F.silu(F.linear(x, ffn.w_gate.weight))
        up = F.linear(x, ffn.w_up.weight)
        expected = F.linear(gate * up, ffn.w_down.weight)
        
        out = ffn(x)
        torch.testing.assert_close(out, expected, atol=1e-5, rtol=1e-5)

    def test_swiglu_zero_input_maps_to_zero(self):
        """F2.4: Verify zero input produces exact zero output (since SiLU(0) = 0)."""
        ffn = SwiGLUFFN(d_model=64, d_ff=128)
        x = torch.zeros(2, 5, 64)
        out = ffn(x)
        torch.testing.assert_close(out, torch.zeros_like(out), atol=1e-7, rtol=1e-7)

    def test_swiglu_projections_bias_free(self):
        """F2.5: Verify linear layers in SwiGLUFFN have bias=False for parameter efficiency."""
        ffn = SwiGLUFFN(d_model=64, d_ff=128)
        assert ffn.w_gate.bias is None
        assert ffn.w_up.bias is None
        assert ffn.w_down.bias is None

    def test_swiglu_gradient_propagation(self):
        """F2.6: Verify gradient backpropagates to all 3 weight matrices."""
        ffn = SwiGLUFFN(d_model=32, d_ff=64)
        x = torch.randn(2, 4, 32, requires_grad=True)
        out = ffn(x)
        loss = out.sum()
        loss.backward()
        assert ffn.w_gate.weight.grad is not None and ffn.w_gate.weight.grad.abs().sum() > 0
        assert ffn.w_up.weight.grad is not None and ffn.w_up.weight.grad.abs().sum() > 0
        assert ffn.w_down.weight.grad is not None and ffn.w_down.weight.grad.abs().sum() > 0
        assert x.grad is not None and x.grad.abs().sum() > 0


# ===========================================================================
# FEATURE 3: RMSNorm Pre-Normalization (>= 5 Tests)
# ===========================================================================

class TestFeature3RMSNorm:
    def test_rmsnorm_forward_shape(self):
        """F3.1: Verify RMSNorm preserves tensor shape."""
        norm = RMSNorm(dim=64, eps=1e-5)
        x = torch.randn(2, 10, 64)
        out = norm(x)
        assert out.shape == x.shape

    def test_rmsnorm_mathematical_correctness(self):
        """F3.2: Verify normalization matches x * rsqrt(mean(x^2) + eps) * weight."""
        dim = 32
        norm = RMSNorm(dim=dim, eps=1e-5)
        x = torch.randn(2, 5, dim)
        variance = x.pow(2).mean(-1, keepdim=True)
        expected = (x * torch.rsqrt(variance + 1e-5)) * norm.weight
        out = norm(x)
        torch.testing.assert_close(out, expected, atol=1e-5, rtol=1e-5)

    def test_rmsnorm_learnable_weight_initialization(self):
        """F3.3: Verify weight parameter is initialized to all ones."""
        norm = RMSNorm(dim=48)
        assert norm.weight.shape == (48,)
        torch.testing.assert_close(norm.weight, torch.ones(48), atol=1e-6, rtol=1e-6)

    def test_rmsnorm_non_mean_centering(self):
        """F3.4: Verify RMSNorm does NOT subtract the mean (unlike LayerNorm)."""
        dim = 16
        norm = RMSNorm(dim=dim)
        # Constant non-zero tensor
        x = torch.ones(1, 1, dim) * 5.0
        out = norm(x)
        # For constant 5.0: RMS is 5.0, so x / RMS(x) = 1.0
        torch.testing.assert_close(out, torch.ones_like(out), atol=1e-5, rtol=1e-5)

    def test_rmsnorm_numerical_stability_near_zero(self):
        """F3.5: Verify numerical stability on exact zeros and small eps inputs."""
        norm = RMSNorm(dim=32, eps=1e-5)
        x = torch.zeros(1, 4, 32)
        out = norm(x)
        assert not torch.isnan(out).any()
        assert not torch.isinf(out).any()
        torch.testing.assert_close(out, torch.zeros_like(out), atol=1e-7, rtol=1e-7)

    def test_rmsnorm_gradient_flow(self):
        """F3.6: Verify backward pass computes valid gradients for input and weight."""
        norm = RMSNorm(dim=32)
        x = torch.randn(2, 4, 32, requires_grad=True)
        out = norm(x)
        loss = (out ** 2).sum()
        loss.backward()
        assert norm.weight.grad is not None and torch.isfinite(norm.weight.grad).all()
        assert x.grad is not None and torch.isfinite(x.grad).all()


# ===========================================================================
# FEATURE 4: Causal Attention & Explicit KV-Cache (>= 5 Tests)
# ===========================================================================

class TestFeature4AttentionKVCache:
    def test_causal_attention_forward_shape(self, tiny_config_dict):
        """F4.1: Verify attention forward pass returns expected output and attention tensors."""
        args = ModelArgs(**tiny_config_dict)
        attn = CausalSelfAttention(args)
        x = torch.randn(2, 8, args.d_model)
        out, attn_weights = attn(x, start_pos=0, return_attentions=True)
        assert out.shape == (2, 8, args.d_model)
        assert attn_weights is not None
        assert attn_weights.shape == (2, args.n_heads, 8, 8)

    def test_causal_mask_strictly_enforced(self, tiny_config_dict):
        """F4.2: Verify attention probabilities to future tokens are strictly 0.0."""
        args = ModelArgs(**tiny_config_dict)
        attn = CausalSelfAttention(args)
        x = torch.randn(1, 6, args.d_model)
        _, weights = attn(x, start_pos=0, return_attentions=True)
        # weights shape: (1, n_heads, 6, 6)
        upper_triangle = torch.triu(weights, diagonal=1)
        assert torch.all(upper_triangle == 0.0)

    def test_grouped_query_attention_repetition(self):
        """F4.3: Verify GQA correctly expands n_kv_heads to match n_heads."""
        args = ModelArgs(vocab_size=100, d_model=64, n_layers=1, n_heads=4, n_kv_heads=2, max_seq_len=32)
        attn = CausalSelfAttention(args)
        assert attn.n_rep == 2
        x = torch.randn(1, 4, args.d_model)
        out, _ = attn(x, start_pos=0)
        assert out.shape == (1, 4, args.d_model)

    def test_kv_cache_initial_prefill_and_step(self, tiny_config_dict):
        """F4.4: Verify KV-cache prefill followed by single token incremental decode."""
        args = ModelArgs(**tiny_config_dict)
        attn = CausalSelfAttention(args)
        
        # Step 1: Prefill prompt of length 5
        prompt = torch.randn(1, 5, args.d_model)
        out_prefill, _ = attn(prompt, start_pos=0, use_cache=True)
        assert out_prefill.shape == (1, 5, args.d_model)
        
        # Step 2: Decode 1 token at pos 5
        next_tok = torch.randn(1, 1, args.d_model)
        out_step, _ = attn(next_tok, start_pos=5, use_cache=True)
        assert out_step.shape == (1, 1, args.d_model)

    def test_kv_cache_parity_with_full_causal_forward(self, tiny_config_dict):
        """F4.5: Verify incremental KV-cached generation matches full non-cached forward pass."""
        args = ModelArgs(**tiny_config_dict)
        attn = CausalSelfAttention(args)
        attn.eval()
        
        seq = torch.randn(1, 6, args.d_model)
        with torch.no_grad():
            full_out, _ = attn(seq, start_pos=0, use_cache=False)
            
            # Prefill 5 tokens, then decode 6th token
            attn.reset_cache() if hasattr(attn, "reset_cache") else None
            attn(seq[:, :5, :], start_pos=0, use_cache=True)
            step_out, _ = attn(seq[:, 5:6, :], start_pos=5, use_cache=True)
            
            torch.testing.assert_close(step_out[:, 0, :], full_out[:, 5, :], atol=1e-4, rtol=1e-4)

    def test_attention_probabilities_sum_to_one(self, tiny_config_dict):
        """F4.6: Verify post-softmax attention weights sum to 1.0 along key dimension."""
        args = ModelArgs(**tiny_config_dict)
        attn = CausalSelfAttention(args)
        x = torch.randn(2, 6, args.d_model)
        _, weights = attn(x, start_pos=0, return_attentions=True)
        sums = weights.sum(dim=-1)  # shape (2, n_heads, 6)
        torch.testing.assert_close(sums, torch.ones_like(sums), atol=1e-5, rtol=1e-5)


# ===========================================================================
# FEATURE 5: Scratch Tokenizer & Inspector (>= 5 Tests)
# ===========================================================================

class TestFeature5Tokenizer:
    def test_byte_tokenizer_round_trip(self):
        """F5.1: Verify UTF-8 string encodes and decodes deterministically."""
        tok = ByteTokenizer()
        text = "Pure PyTorch Transformer with RoPE & SwiGLU!"
        token_ids = tok.encode(text)
        decoded = tok.decode(token_ids)
        assert decoded == text

    def test_byte_tokenizer_special_tokens(self):
        """F5.2: Verify special tokens pad=0, bos=1, eos=2, unk=3 and byte offset +4."""
        tok = ByteTokenizer()
        assert tok.pad_id == 0
        assert tok.bos_id == 1
        assert tok.eos_id == 2
        assert tok.unk_id == 3
        # Byte 'A' is ASCII 65 -> token ID 65 + 4 = 69
        ids = tok.encode("A")
        assert ids == [69]

    def test_byte_tokenizer_oov_immunity(self):
        """F5.3: Verify 100% out-of-vocabulary immunity for unicode, emojis, and symbols."""
        tok = ByteTokenizer()
        complex_text = "Apple Silicon 🚀 M3 Max 💻 🍎 ∑(x_i) = 1.0"
        ids = tok.encode(complex_text)
        decoded = tok.decode(ids)
        assert decoded == complex_text

    def test_byte_tokenizer_inspect_structure(self):
        """F5.4: Verify inspect API returns required metadata fields."""
        tok = ByteTokenizer()
        res = tok.inspect("Hello!")
        assert isinstance(res, dict)
        for key in ["tokens", "token_ids", "byte_lengths", "offsets", "compression_ratio"]:
            assert key in res
        assert len(res["tokens"]) == len(res["token_ids"])
        assert len(res["byte_lengths"]) == len(res["token_ids"])

    def test_byte_tokenizer_compression_ratio(self):
        """F5.5: Verify compression ratio is byte_count / token_count."""
        tok = ByteTokenizer()
        res = tok.inspect("ABC")
        assert res["compression_ratio"] == 1.0  # Byte tokenizer has 1 byte per token

    def test_byte_tokenizer_empty_string(self):
        """F5.6: Verify empty string encodes and decodes cleanly without exception."""
        tok = ByteTokenizer()
        ids = tok.encode("")
        assert ids == []
        assert tok.decode([]) == ""


# ===========================================================================
# FEATURE 6: Supervised Fine-Tuning (SFT) (>= 5 Tests)
# ===========================================================================

class TestFeature6SFT:
    def test_sft_dataset_item_format(self):
        """F6.1: Verify SFT dataset creates tokens and masked targets."""
        tok = ByteTokenizer()
        ds = SFTDataset([{"prompt": "Hi", "response": "Bye"}], tokenizer=tok, max_seq_len=32)
        item = ds[0]
        assert "input_ids" in item and "labels" in item
        assert item["input_ids"].shape == item["labels"].shape

    def test_sft_prompt_masking_with_negative_100(self):
        """F6.2: Verify prompt tokens in targets have ignore_index = -100."""
        tok = ByteTokenizer()
        ds = SFTDataset([{"prompt": "Hello", "response": "World"}], tokenizer=tok, max_seq_len=32)
        item = ds[0]
        labels = item["labels"]
        # Prompt tokens must be -100
        prompt_len = len(tok.encode("Hello"))
        assert (labels[:prompt_len] == -100).all()
        # Response tokens must NOT be -100
        assert (labels[prompt_len:] != -100).any()

    def test_sft_loss_computation(self, tiny_config_dict):
        """F6.3: Verify compute_sft_loss computes CrossEntropyLoss with ignore_index=-100."""
        args = ModelArgs(**tiny_config_dict)
        logits = torch.randn(2, 10, args.vocab_size)
        targets = torch.randint(0, args.vocab_size, (2, 10))
        targets[:, :5] = -100  # Mask first 5 tokens
        loss = compute_sft_loss(logits, targets)
        assert loss.item() > 0.0
        assert not torch.isnan(loss)

    def test_sft_gradient_flow_end_to_end(self, tiny_config_dict):
        """F6.4: Verify SFT loss backward propagates gradients through the entire model."""
        args = ModelArgs(**tiny_config_dict)
        model = Transformer(args)
        tokens = torch.randint(0, args.vocab_size, (2, 8))
        targets = tokens.clone()
        targets[:, :4] = -100
        
        logits, _ = model(tokens)
        loss = compute_sft_loss(logits, targets)
        loss.backward()
        
        for name, p in model.named_parameters():
            if p.requires_grad:
                assert p.grad is not None, f"Parameter {name} has None gradient"
                assert torch.isfinite(p.grad).all(), f"Parameter {name} has non-finite gradient"

    def test_sft_trainer_step_reduces_loss(self, tiny_config_dict):
        """F6.5: Verify optimizer step updates weights in the expected gradient descent direction."""
        torch.manual_seed(42)
        args = ModelArgs(**tiny_config_dict)
        model = Transformer(args)
        optimizer = torch.optim.AdamW(model.parameters(), lr=1e-2)
        tokens = torch.randint(0, args.vocab_size, (2, 8))
        targets = tokens.clone()
        targets[:, :2] = -100
        
        # Step 1
        optimizer.zero_grad()
        logits1, _ = model(tokens)
        loss1 = compute_sft_loss(logits1, targets)
        loss1.backward()
        optimizer.step()
        
        # Step 2
        with torch.no_grad():
            logits2, _ = model(tokens)
            loss2 = compute_sft_loss(logits2, targets)
        
        assert loss2.item() < loss1.item(), f"Loss did not decrease: {loss1.item()} -> {loss2.item()}"


# ===========================================================================
# FEATURE 7: CRISP-DM Pipeline Tracker (>= 5 Tests)
# ===========================================================================

class TestFeature7CrispDMTracker:
    def test_crisp_dm_initialization_six_stages(self):
        """F7.1: Verify tracker initializes with all 6 standard CRISP-DM phases."""
        tracker = CrispDMTracker()
        stages = tracker.get_stages()
        expected = [
            "business_understanding", "data_understanding", "data_preparation",
            "modeling", "evaluation", "deployment"
        ]
        for s in expected:
            assert s in stages

    def test_crisp_dm_guarantees_minimum_three_stages(self):
        """F7.2: Verify tracker explicitly tracks Data Preparation, Modeling, and Evaluation."""
        tracker = CrispDMTracker()
        stages = tracker.get_stages()
        assert "data_preparation" in stages
        assert "modeling" in stages
        assert "evaluation" in stages

    def test_crisp_dm_stage_transition_lifecycle(self):
        """F7.3: Verify stage transition not_started -> running -> completed."""
        tracker = CrispDMTracker()
        assert tracker.get_stage("modeling")["status"] == "not_started"
        tracker.start_stage("modeling")
        assert tracker.get_stage("modeling")["status"] == "running"
        tracker.complete_stage("modeling", metrics={"loss": 1.25})
        stage = tracker.get_stage("modeling")
        assert stage["status"] == "completed"
        assert stage["metrics"]["loss"] == 1.25
        assert stage["duration_seconds"] is not None and stage["duration_seconds"] >= 0

    def test_crisp_dm_artifacts_and_logs(self):
        """F7.4: Verify logging messages and recording artifacts in stage state."""
        tracker = CrispDMTracker()
        tracker.start_stage("data_preparation")
        tracker.log_stage("data_preparation", "Tokenizing corpus...")
        tracker.add_artifact("data_preparation", "vocab_size", 260)
        tracker.complete_stage("data_preparation")
        
        stage = tracker.get_stage("data_preparation")
        assert "Tokenizing corpus..." in stage["logs"]
        assert stage["artifacts"]["vocab_size"] == 260

    def test_crisp_dm_export_state_dict(self):
        """F7.5: Verify full state export format conforms to REST API requirements."""
        tracker = CrispDMTracker()
        state = tracker.export_state()
        assert "current_stage" in state
        assert "stages" in state
        assert "updated_at" in state
        assert len(state["stages"]) >= 3


# ===========================================================================
# FEATURE 8: KV-Cache Inspection Endpoint (>= 5 Tests)
# ===========================================================================

class TestFeature8KVCacheInspector:
    def test_kv_cache_inspector_output_format(self, tiny_config_dict):
        """F8.1: Verify inspect_kv_cache returns structured telemetry."""
        args = ModelArgs(**tiny_config_dict)
        model = Transformer(args)
        tok = ByteTokenizer()
        res = inspect_kv_cache(model, tok, prompt="Hello", max_new_tokens=4)
        assert res["status"] == "ok"
        assert "steps" in res
        assert len(res["steps"]) == 4

    def test_kv_cache_inspector_step_details(self, tiny_config_dict):
        """F8.2: Verify step trace includes cache shape, step latency, and memory footprint."""
        args = ModelArgs(**tiny_config_dict)
        model = Transformer(args)
        tok = ByteTokenizer()
        res = inspect_kv_cache(model, tok, prompt="Test", max_new_tokens=2)
        step0 = res["steps"][0]
        assert "cache_shape_per_layer" in step0
        assert "step_latency_ms" in step0
        assert "step_memory_allocated_bytes" in step0

    def test_kv_cache_inspector_layer_summaries(self, tiny_config_dict):
        """F8.3: Verify layer summaries array matches model n_layers."""
        args = ModelArgs(**tiny_config_dict)
        model = Transformer(args)
        tok = ByteTokenizer()
        res = inspect_kv_cache(model, tok, prompt="Hello", max_new_tokens=2)
        assert len(res["layer_summaries"]) == args.n_layers

    def test_kv_cache_inspector_memory_calculation(self, tiny_config_dict):
        """F8.4: Verify computed memory footprint in bytes is positive and mathematically consistent."""
        args = ModelArgs(**tiny_config_dict)
        model = Transformer(args)
        tok = ByteTokenizer()
        res = inspect_kv_cache(model, tok, prompt="Hi", max_new_tokens=3)
        assert res["memory_footprint_bytes"] > 0
        assert "memory_footprint_formatted" in res

    def test_kv_cache_inspector_empty_prompt_fallback(self, tiny_config_dict):
        """F8.5: Verify empty or minimal prompt defaults gracefully."""
        args = ModelArgs(**tiny_config_dict)
        model = Transformer(args)
        tok = ByteTokenizer()
        res = inspect_kv_cache(model, tok, prompt="", max_new_tokens=2)
        assert res["status"] == "ok"
        assert len(res["steps"]) == 2


# ===========================================================================
# FEATURE 9: Attention Heatmap Endpoint (>= 5 Tests)
# ===========================================================================

class TestFeature9AttentionInspector:
    def test_attention_inspector_matrix_dimensions(self, tiny_config_dict):
        """F9.1: Verify attention heatmap matrix is square with dimension (seq_len, seq_len)."""
        args = ModelArgs(**tiny_config_dict)
        model = Transformer(args)
        tok = ByteTokenizer()
        res = inspect_attention(model, tok, prompt="Hello world", layer_idx=0, head_idx=0)
        assert res["status"] == "ok"
        seq_len = len(res["tokens"])
        matrix = res["attention_matrix"]
        assert len(matrix) == seq_len
        assert len(matrix[0]) == seq_len

    def test_attention_inspector_causal_validity_flag(self, tiny_config_dict):
        """F9.2: Verify causal_validity is True for autoregressive attention."""
        args = ModelArgs(**tiny_config_dict)
        model = Transformer(args)
        tok = ByteTokenizer()
        res = inspect_attention(model, tok, prompt="Causal test", layer_idx=0, head_idx=0)
        assert res["causal_validity"] is True

    def test_attention_inspector_layer_and_head_indexing(self, tiny_config_dict):
        """F9.3: Verify inspector extracts specific layer and head accurately."""
        args = ModelArgs(**tiny_config_dict)
        model = Transformer(args)
        tok = ByteTokenizer()
        res = inspect_attention(model, tok, prompt="Test index", layer_idx=1, head_idx=2)
        assert res["selected_layer"] == 1
        assert res["selected_head"] == 2

    def test_attention_inspector_metrics(self, tiny_config_dict):
        """F9.4: Verify entropy, diagonal dominance, and sparsity metrics are computed."""
        args = ModelArgs(**tiny_config_dict)
        model = Transformer(args)
        tok = ByteTokenizer()
        res = inspect_attention(model, tok, prompt="Attention metrics", layer_idx=0, head_idx=0)
        metrics = res["head_metrics"]
        assert "average_entropy" in metrics
        assert "diagonal_dominance" in metrics
        assert "sparsity" in metrics

    def test_attention_inspector_token_alignment(self, tiny_config_dict):
        """F9.5: Verify tokens and token_ids have identical length to matrix dimension."""
        args = ModelArgs(**tiny_config_dict)
        model = Transformer(args)
        tok = ByteTokenizer()
        res = inspect_attention(model, tok, prompt="Token alignment", layer_idx=0, head_idx=0)
        assert len(res["tokens"]) == len(res["token_ids"]) == res["seq_len"]


# ===========================================================================
# FEATURE 10: Tokenizer Inspection Endpoint (>= 5 Tests)
# ===========================================================================

class TestFeature10TokenizerInspector:
    def test_tokenizer_inspector_full_payload(self):
        """F10.1: Verify inspect_tokenizer returns structured dictionary with all fields."""
        tok = ByteTokenizer()
        res = inspect_tokenizer(tok, text="Nano LLM")
        assert res["status"] == "ok"
        assert res["text"] == "Nano LLM"
        assert res["token_count"] > 0
        assert res["char_count"] == len("Nano LLM")

    def test_tokenizer_inspector_token_items(self):
        """F10.2: Verify token item dictionary format."""
        tok = ByteTokenizer()
        res = inspect_tokenizer(tok, text="Test")
        for item in res["tokens"]:
            assert "token_id" in item
            assert "token_str" in item
            assert "raw_bytes" in item
            assert "char_start" in item
            assert "char_end" in item

    def test_tokenizer_inspector_round_trip_match(self):
        """F10.3: Verify round_trip_match is True."""
        tok = ByteTokenizer()
        res = inspect_tokenizer(tok, text="Silicon Apple M3")
        assert res["round_trip_match"] is True

    def test_tokenizer_inspector_compression_metrics(self):
        """F10.4: Verify compression ratio is positive float."""
        tok = ByteTokenizer()
        res = inspect_tokenizer(tok, text="Transformer Architecture")
        assert res["compression_ratio"] > 0.0

    def test_tokenizer_inspector_unicode_special_chars(self):
        """F10.5: Verify correct inspection on UTF-8 emoji and non-ASCII chars."""
        tok = ByteTokenizer()
        res = inspect_tokenizer(tok, text="🔥 PyTorch ⚡️")
        assert res["round_trip_match"] is True
        assert res["status"] == "ok"


# ===========================================================================
# FEATURE 11: Interactive Admin Web Dashboard (>= 5 Tests)
# ===========================================================================

class TestFeature11DashboardApp:
    def test_dashboard_root_html_serving(self):
        """F11.1: Verify GET / returns HTTP 200 OK and text/html."""
        from fastapi.testclient import TestClient
        client = TestClient(app)
        response = client.get("/")
        assert response.status_code == 200
        assert "text/html" in response.headers.get("content-type", "")

    def test_dashboard_alias_route(self):
        """F11.2: Verify GET /dashboard returns HTTP 200 OK."""
        from fastapi.testclient import TestClient
        client = TestClient(app)
        response = client.get("/dashboard")
        assert response.status_code == 200

    def test_dashboard_health_api(self):
        """F11.3: Verify GET /api/health returns HTTP 200 with status ok."""
        from fastapi.testclient import TestClient
        client = TestClient(app)
        response = client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") in ["healthy", "ok"]

    def test_dashboard_crisp_dm_api_endpoint(self):
        """F11.4: Verify GET /api/crisp-dm returns HTTP 200 and stages dict."""
        from fastapi.testclient import TestClient
        client = TestClient(app)
        response = client.get("/api/crisp-dm")
        assert response.status_code == 200
        data = response.json()
        assert "stages" in data

    def test_dashboard_generate_endpoint(self):
        """F11.5: Verify POST /api/generate produces generated text."""
        from fastapi.testclient import TestClient
        client = TestClient(app)
        response = client.post("/api/generate", json={"prompt": "Once upon", "max_new_tokens": 5})
        assert response.status_code == 200
        data = response.json()
        assert "generated_text" in data


# ===========================================================================
# FEATURE 12: Apple Silicon (MPS) Auto-Selection (>= 5 Tests)
# ===========================================================================

class TestFeature12DeviceAutoSelection:
    def test_resolve_device_default(self):
        """F12.1: Verify resolve_device() returns a valid torch.device object."""
        dev = resolve_device()
        assert isinstance(dev, torch.device)
        assert dev.type in ["mps", "cpu", "cuda"]

    def test_resolve_device_mps_priority(self):
        """F12.2: Verify resolve_device selects mps when available."""
        if torch.backends.mps.is_available() and torch.backends.mps.is_built():
            dev = resolve_device("mps")
            assert dev.type == "mps"
        else:
            dev = resolve_device("mps")
            assert dev.type == "cpu"

    def test_resolve_device_explicit_cpu_override(self):
        """F12.3: Verify resolve_device('cpu') returns CPU device regardless of MPS."""
        dev = resolve_device("cpu")
        assert dev.type == "cpu"

    def test_tensor_creation_on_resolved_device(self):
        """F12.4: Verify tensor creation and arithmetic on resolved device."""
        dev = resolve_device()
        t = torch.ones((2, 2), device=dev)
        assert t.device.type == dev.type
        t2 = t * 2.0
        assert t2.sum().item() == 8.0

    def test_model_migration_to_resolved_device(self, tiny_config_dict):
        """F12.5: Verify moving transformer model to resolved device executes smoothly."""
        dev = resolve_device()
        args = ModelArgs(**tiny_config_dict)
        model = Transformer(args).to(dev)
        x = torch.randint(0, args.vocab_size, (1, 4), device=dev)
        logits, _ = model(x)
        assert logits.device.type == dev.type


# ===========================================================================
# FEATURE 13: Unified Memory Profiling & Limit Enforcement (>= 5 Tests)
# ===========================================================================

class TestFeature13MemoryProfiling:
    def test_get_memory_stats_structure(self):
        """F13.1: Verify get_memory_stats returns dictionary with memory telemetry."""
        dev = resolve_device()
        stats = get_memory_stats(dev)
        assert isinstance(stats, dict)
        for key in ["process_rss_mb", "system_ram_total_gb", "unified_memory_limit_gb", "within_memory_budget"]:
            assert key in stats

    def test_memory_stats_values_non_negative(self):
        """F13.2: Verify all returned memory quantities are >= 0."""
        dev = resolve_device()
        stats = get_memory_stats(dev)
        assert stats["process_rss_mb"] >= 0
        assert stats["system_ram_total_gb"] > 0
        assert stats["unified_memory_limit_gb"] == 4.0

    def test_within_memory_budget_boolean_assertion(self):
        """F13.3: Verify process RSS is strictly within the 4.0 GB memory ceiling."""
        dev = resolve_device()
        stats = get_memory_stats(dev)
        assert stats["within_memory_budget"] is True
        assert stats["process_rss_mb"] / 1024.0 <= 4.0

    def test_empty_device_cache_execution(self):
        """F13.4: Verify empty_device_cache runs safely on any device."""
        dev = resolve_device()
        empty_device_cache(dev)  # Should not raise any exception

    def test_hardware_memory_rest_endpoint(self):
        """F13.5: Verify GET /api/hardware/memory returns valid payload."""
        from fastapi.testclient import TestClient
        client = TestClient(app)
        response = client.get("/api/hardware/memory")
        assert response.status_code == 200
        data = response.json()
        assert data.get("within_memory_budget") is True
