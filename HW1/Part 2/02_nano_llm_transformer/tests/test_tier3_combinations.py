"""
Tier 3: Combinatorial & Cross-Feature Pairwise Interaction Test Suite.
Tests non-trivial interactions between model primitives, tokenizer, SFT, dashboard, and hardware resolver.
"""

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


class TestTier3Combinations:
    def test_comb_rope_with_gqa_attention(self, tiny_config_dict):
        """Comb 1: RoPE rotations integrated into Grouped-Query Causal Attention."""
        args = ModelArgs(**tiny_config_dict)
        attn = CausalSelfAttention(args)
        x = torch.randn(2, 12, args.d_model)
        out, weights = attn(x, start_pos=0, return_attentions=True)
        assert out.shape == (2, 12, args.d_model)
        assert weights.shape == (2, args.n_heads, 12, 12)
        # Verify upper triangle of attention matrix is strictly 0 (causality)
        upper_tri = torch.triu(weights, diagonal=1)
        assert torch.all(upper_tri == 0.0)

    def test_comb_rmsnorm_swiglu_residual_block(self, tiny_config_dict):
        """Comb 2: RMSNorm pre-normalization + SwiGLU FFN + Residual connection in TransformerBlock."""
        args = ModelArgs(**tiny_config_dict)
        block = TransformerBlock(args, layer_idx=0)
        x = torch.randn(2, 8, args.d_model)
        out, _ = block(x, start_pos=0)
        assert out.shape == x.shape
        # Verify residual connection: output should not be zero even if sublayers are zeroed
        assert not torch.allclose(out, torch.zeros_like(out))

    def test_comb_full_model_forward_and_logits(self, small_config_dict):
        """Comb 3: Full Transformer stack with RoPE, SwiGLU, RMSNorm, and weight-tied LM head."""
        args = ModelArgs(**small_config_dict)
        model = Transformer(args)
        tokens = torch.randint(0, args.vocab_size, (2, 16))
        logits, attentions = model(tokens, return_attentions=True)
        assert logits.shape == (2, 16, args.vocab_size)
        assert len(attentions) == args.n_layers
        assert attentions[0].shape == (2, args.n_heads, 16, 16)

    def test_comb_sft_gradient_backprop_through_all_primitives(self, tiny_config_dict):
        """Comb 4: Mock SFT loss backpropagation computes clean gradients across all custom primitives."""
        args = ModelArgs(**tiny_config_dict)
        model = Transformer(args)
        tokens = torch.randint(0, args.vocab_size, (2, 10))
        targets = tokens.clone()
        targets[:, :4] = -100  # Mask prompt tokens
        
        logits, _ = model(tokens)
        loss = compute_sft_loss(logits, targets)
        loss.backward()
        
        # Verify gradients exist and are non-zero for all components
        for name, param in model.named_parameters():
            if param.requires_grad:
                assert param.grad is not None, f"No gradient for {name}"
                assert torch.isfinite(param.grad).all(), f"NaN/Inf gradient in {name}"
                assert param.grad.abs().sum() > 0, f"Zero gradient in {name}"

    def test_comb_tokenizer_with_model_generate(self, tiny_config_dict):
        """Comb 5: ByteTokenizer encoding into Transformer autoregressive generation and decoding."""
        args = ModelArgs(**tiny_config_dict)
        model = Transformer(args)
        tok = ByteTokenizer()
        
        prompt = "Hello"
        prompt_ids = tok.encode(prompt)
        gen_ids = model.generate(prompt_ids, max_new_tokens=6, temperature=0.8)
        assert len(gen_ids) == len(prompt_ids) + 6
        output_text = tok.decode(gen_ids)
        assert output_text.startswith("Hello")

    def test_comb_kv_cache_generation_vs_full_forward(self, tiny_config_dict):
        """Comb 6: Verification that KV-cached token-by-token rollout matches brute-force forward pass."""
        args = ModelArgs(**tiny_config_dict)
        model = Transformer(args)
        model.eval()
        
        torch.manual_seed(42)
        prompt_tokens = [10, 25, 45, 60]
        max_new = 4
        
        with torch.no_grad():
            gen_cached = model.generate(prompt_tokens, max_new_tokens=max_new, temperature=0.0)
            
            # Step by step full forward
            current = list(prompt_tokens)
            for _ in range(max_new):
                inp = torch.tensor([current], dtype=torch.long)
                logits, _ = model(inp)
                next_tok = int(torch.argmax(logits[:, -1, :], dim=-1).item())
                current.append(next_tok)
            
            assert gen_cached == current

    def test_comb_crisp_dm_with_training_telemetry(self):
        """Comb 7: CRISP-DM tracker state management integrating live training metrics."""
        tracker = CrispDMTracker()
        tracker.start_stage("data_preparation")
        tracker.complete_stage("data_preparation", metrics={"vocab_size": 260, "tokens": 10000})
        
        tracker.start_stage("modeling")
        for step in range(3):
            tracker.log_stage("modeling", f"Step {step}: loss = {2.5 - step * 0.3:.3f}")
        tracker.complete_stage("modeling", metrics={"final_loss": 1.9, "perplexity": 6.68})
        
        state = tracker.export_state()
        assert state["stages"]["data_preparation"]["status"] == "completed"
        assert state["stages"]["modeling"]["status"] == "completed"
        assert state["stages"]["modeling"]["metrics"]["final_loss"] == 1.9

    def test_comb_attention_inspector_with_tokenizer_offsets(self, tiny_config_dict):
        """Comb 8: Attention heatmap inspector paired with tokenizer character offsets."""
        args = ModelArgs(**tiny_config_dict)
        model = Transformer(args)
        tok = ByteTokenizer()
        
        prompt = "Attention mechanism"
        attn_res = inspect_attention(model, tok, prompt=prompt, layer_idx=0, head_idx=0)
        tok_res = inspect_tokenizer(tok, text=prompt)
        
        assert attn_res["status"] == "ok"
        assert tok_res["status"] == "ok"
        assert len(attn_res["tokens"]) == tok_res["token_count"]

    def test_comb_device_resolution_and_model_execution(self, tiny_config_dict):
        """Comb 9: Device resolver auto-selection paired with model training step."""
        dev = resolve_device()
        args = ModelArgs(**tiny_config_dict)
        model = Transformer(args).to(dev)
        
        tokens = torch.randint(0, args.vocab_size, (2, 8), device=dev)
        targets = tokens.clone()
        targets[:, :2] = -100
        
        logits, _ = model(tokens)
        assert logits.device.type == dev.type
        loss = compute_sft_loss(logits, targets)
        loss.backward()
        assert model.tok_embeddings.weight.grad is not None

    def test_comb_fastapi_e2e_inspection_pipeline(self):
        """Comb 10: Complete FastAPI client interaction across all inspection routes."""
        from fastapi.testclient import TestClient
        client = TestClient(app)
        
        # 1. Health
        h = client.get("/api/health")
        assert h.status_code == 200
        
        # 2. CRISP-DM
        c = client.get("/api/crisp-dm")
        assert c.status_code == 200
        
        # 3. Tokenizer inspect
        t = client.post("/api/inspect/tokenizer", json={"text": "E2E testing"})
        assert t.status_code == 200
        assert t.json()["round_trip_match"] is True
        
        # 4. Attention inspect
        a = client.post("/api/inspect/attention", json={"prompt": "E2E testing"})
        assert a.status_code == 200
        assert a.json()["causal_validity"] is True
        
        # 5. KV-Cache inspect
        k = client.post("/api/inspect/kv-cache", json={"prompt": "E2E", "max_new_tokens": 3})
        assert k.status_code == 200
        assert len(k.json()["steps"]) == 3
        
        # 6. Hardware memory
        m = client.get("/api/hardware/memory")
        assert m.status_code == 200
        assert m.json()["within_memory_budget"] is True
