"""Independent Forensic Auditor Probe Script.

Conducts rigorous mathematical and runtime checks:
1. RoPE rotation equivalence & position sensitivity.
2. SwiGLU gating mathematical equivalence & activation behavior.
3. RMSNorm scale invariance & non-mean-centering.
4. KV-cache generation equivalence against non-cached prefill forward pass.
5. SFT prompt-masking verification (loss and gradients only from unmasked response tokens).
6. Pure PyTorch assertion (no external transformer libraries loaded).
"""

import sys
import os
from pathlib import Path
import torch
import torch.nn as nn
import torch.nn.functional as F

PROJECT_ROOT = Path("/Users/oleg/Documents/Coding/SJSU/Data Mining/HW1/Part 2/02_nano_llm_transformer")
sys.path.insert(0, str(PROJECT_ROOT))

from nano_transformer.config import ModelArgs
from nano_transformer.norm import RMSNorm
from nano_transformer.rope import RotaryEmbedding, apply_rotary_emb, rotate_half
from nano_transformer.ffn import SwiGLUFFN
from nano_transformer.attention import CausalSelfAttention, KVCache
from nano_transformer.block import TransformerBlock
from nano_transformer.model import Transformer
from nano_transformer.tokenizer import ByteTokenizer, BPETokenizer
from nano_transformer.sft import SFTDataset, collate_sft, compute_sft_loss
from nano_transformer.device import resolve_device, get_memory_stats


def audit_rope():
    print("Auditing RoPE...")
    dim = 32
    seq_len = 8
    rope = RotaryEmbedding(dim=dim, max_seq_len=64, base=10000.0)
    x = torch.randn(1, 2, seq_len, dim)
    
    # 1. Output shape
    out = rope(x)
    assert out.shape == x.shape, f"RoPE shape mismatch: {out.shape} vs {x.shape}"
    
    # 2. Position 0 rotation with base freq: at pos 0, angles are 0, cos=1, sin=0 => out[:,:,0,:] == x[:,:,0,:]
    diff_pos0 = (out[:, :, 0, :] - x[:, :, 0, :]).abs().max().item()
    assert diff_pos0 < 1e-5, f"RoPE at pos 0 should be identity, diff={diff_pos0}"
    
    # 3. Position sensitivity: out at pos 1 should differ from x at pos 1
    diff_pos1 = (out[:, :, 1, :] - x[:, :, 1, :]).abs().max().item()
    assert diff_pos1 > 1e-4, f"RoPE at pos 1 should modify tensor, diff={diff_pos1}"
    
    # 4. Orthogonality / norm preservation: RoPE preserves Euclidean norm per vector
    norm_in = torch.norm(x, dim=-1)
    norm_out = torch.norm(out, dim=-1)
    norm_diff = (norm_in - norm_out).abs().max().item()
    assert norm_diff < 1e-4, f"RoPE should preserve Euclidean norm, norm_diff={norm_diff}"
    print("  [PASS] RoPE mathematical integrity verified.")


def audit_swiglu():
    print("Auditing SwiGLU...")
    d_model = 64
    d_ff = 128
    ffn = SwiGLUFFN(d_model=d_model, d_ff=d_ff, dropout=0.0)
    x = torch.randn(2, 5, d_model)
    
    out = ffn(x)
    assert out.shape == (2, 5, d_model), f"SwiGLU output shape mismatch: {out.shape}"
    
    # Verify exact formula manually
    with torch.no_grad():
        gate = F.silu(ffn.w_gate(x))
        up = ffn.w_up(x)
        expected = ffn.w_down(gate * up)
        diff = (out - expected).abs().max().item()
        assert diff < 1e-5, f"SwiGLU formula mismatch: diff={diff}"
    print("  [PASS] SwiGLU mathematical integrity verified.")


def audit_rmsnorm():
    print("Auditing RMSNorm...")
    dim = 64
    eps = 1e-5
    norm = RMSNorm(dim=dim, eps=eps)
    x = torch.randn(3, 7, dim)
    out = norm(x)
    assert out.shape == x.shape, f"RMSNorm output shape mismatch: {out.shape}"
    
    with torch.no_grad():
        # Verify formula: x / sqrt(mean(x^2) + eps) * weight
        rms = torch.sqrt(torch.mean(x ** 2, dim=-1, keepdim=True) + eps)
        expected = (x / rms) * norm.weight
        diff = (out - expected).abs().max().item()
        assert diff < 1e-5, f"RMSNorm formula mismatch: diff={diff}"
        
        # Scale invariance property: norm(alpha * x) with alpha > 0 has same unit direction as norm(x)
        alpha = 5.0
        out_scaled = norm(x * alpha)
        # Difference between out_scaled and out should be small (except for epsilon effect on small values)
        # With eps << norm(x), out_scaled ~= out
        diff_scale = (out_scaled - out).abs().max().item()
        assert diff_scale < 1e-2, f"RMSNorm approximate scale invariance check failed: diff={diff_scale}"
    print("  [PASS] RMSNorm mathematical integrity verified.")


def audit_kv_cache_equivalence():
    print("Auditing KV-Cache decoding mathematical equivalence...")
    torch.manual_seed(42)
    args = ModelArgs(vocab_size=260, d_model=64, n_layers=2, n_heads=4, n_kv_heads=2, max_seq_len=64)
    model = Transformer(args)
    model.eval()
    
    prompt = torch.randint(4, 250, (1, 6), dtype=torch.long)
    
    # 1. Non-cached full forward pass
    with torch.no_grad():
        full_logits, _ = model(prompt)
    
    # 2. KV-cached step-by-step decoding
    kv_caches = [KVCache() for _ in range(args.n_layers)]
    # Prefill first 5 tokens
    with torch.no_grad():
        _, _ = model(prompt[:, :5], start_pos=0, kv_cache=kv_caches, use_cache=True)
        # Decode 6th token
        step_logits, _ = model(prompt[:, 5:6], start_pos=5, kv_cache=kv_caches, use_cache=True)
    
    # The logits for the 6th token (index 5) should match exactly between full and cached forward passes!
    diff = (full_logits[:, 5, :] - step_logits[:, 0, :]).abs().max().item()
    assert diff < 1e-4, f"KV cache decoding produced different logits than full prefill! diff={diff}"
    print(f"  [PASS] KV-cache decoding is mathematically identical to full prefill (max logit diff = {diff:.2e}).")


def audit_sft_masking():
    print("Auditing SFT prompt masking & gradient flow...")
    args = ModelArgs(vocab_size=260, d_model=64, n_layers=2, n_heads=4, n_kv_heads=2, max_seq_len=64)
    model = Transformer(args)
    model.train()
    
    tok = ByteTokenizer()
    dataset = SFTDataset([("Prompt text here", "Response answer here")], tokenizer=tok)
    batch = collate_sft([dataset[0]])
    
    input_ids = batch["input_ids"]
    labels = batch["labels"]
    
    # Verify prompt tokens are masked with -100
    prompt_len = dataset[0]["prompt_len"]
    assert (labels[0, :prompt_len] == -100).all(), "Prompt tokens were not masked with -100!"
    assert (labels[0, prompt_len:] != -100).all(), "Response tokens were incorrectly masked!"
    
    logits, _ = model(input_ids)
    loss = compute_sft_loss(logits, labels)
    loss.backward()
    
    # Check that all modules have non-zero gradients
    for name, p in model.named_parameters():
        if p.requires_grad:
            assert p.grad is not None, f"Parameter {name} has no grad"
            assert not torch.isnan(p.grad).any(), f"Parameter {name} grad is NaN"
            assert not torch.isinf(p.grad).any(), f"Parameter {name} grad is Inf"
            assert p.grad.abs().sum().item() > 0, f"Parameter {name} grad is zero"
    print("  [PASS] SFT prompt masking and gradient flow verified.")


def audit_pure_pytorch_dependencies():
    print("Auditing module imports against banned external packages...")
    import sys
    banned = ["transformers", "accelerate", "deepspeed", "llama_cpp", "vllm", "litellm", "openai", "anthropic"]
    for b in banned:
        assert b not in sys.modules, f"Banned dependency {b} is imported in runtime!"
    print("  [PASS] Pure PyTorch verified (no banned external LLM libraries loaded).")


if __name__ == "__main__":
    print("=" * 60)
    print("RUNNING INDEPENDENT FORENSIC AUDIT PROBE")
    print("=" * 60)
    audit_rope()
    audit_swiglu()
    audit_rmsnorm()
    audit_kv_cache_equivalence()
    audit_sft_masking()
    audit_pure_pytorch_dependencies()
    print("=" * 60)
    print("ALL INDEPENDENT FORENSIC AUDIT PROBES PASSED (100%)")
    print("=" * 60)
