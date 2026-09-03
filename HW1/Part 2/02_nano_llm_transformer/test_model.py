#!/usr/bin/env python3
"""
Acceptance Test Script: Model Architecture & SFT Gradient Flow Verification.

Requirements:
1. Programmatically initializes NanoLLMTransformer.
2. Verifies forward pass tensor shapes: (B, T, vocab_size) and attention weights.
3. Verifies gradient backpropagation through RoPE, SwiGLU, and RMSNorm during mock SFT pass.

Usage:
    python test_model.py
    pytest test_model.py -v
"""

import sys
import os
from pathlib import Path
import torch
import torch.nn as nn
import torch.nn.functional as F

# Ensure project root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def run_model_verification():
    print("=" * 70)
    print(" ACCEPTANCE CRITERIA 1: MODEL ARCHITECTURE & GRADIENT VERIFICATION")
    print("=" * 70)

    try:
        from nano_transformer.config import ModelArgs
        from nano_transformer.model import Transformer
        from nano_transformer.norm import RMSNorm
        from nano_transformer.rope import RotaryEmbedding
        from nano_transformer.ffn import SwiGLUFFN
        from nano_transformer.attention import CausalSelfAttention
        from nano_transformer.sft import compute_sft_loss
    except ImportError as e:
        print(f"[-] Import failed: {e}")
        print("[-] Ensure nano_transformer package is implemented per PROJECT.md interface contracts.")
        return False

    # 1. Model Initialization
    print("[1/3] Initializing Transformer model configuration...")
    vocab_size = 260
    d_model = 128
    n_layers = 4
    n_heads = 4
    n_kv_heads = 2
    max_seq_len = 256
    
    args = ModelArgs(
        vocab_size=vocab_size,
        d_model=d_model,
        n_layers=n_layers,
        n_heads=n_heads,
        n_kv_heads=n_kv_heads,
        max_seq_len=max_seq_len,
        dropout=0.0,
        norm_eps=1e-5,
        rope_base=10000.0,
        tie_embeddings=True
    )
    model = Transformer(args)
    model.train()
    total_params = sum(p.numel() for p in model.parameters())
    print(f"    [+] Model successfully initialized with {total_params:,} parameters.")
    print(f"    [+] Architecture: {n_layers} layers, {n_heads} Q-heads, {n_kv_heads} KV-heads, d_model={d_model}.")

    # 2. Forward Pass Tensor Shape Verification
    print("\n[2/3] Verifying Forward Pass Tensor Shapes...")
    batch_size = 2
    seq_len = 16
    torch.manual_seed(42)
    mock_input_tokens = torch.randint(4, vocab_size, (batch_size, seq_len), dtype=torch.long)
    
    logits, attentions = model(mock_input_tokens, return_attentions=True)
    
    expected_logits_shape = (batch_size, seq_len, vocab_size)
    assert logits.shape == expected_logits_shape, (
        f"Logits shape mismatch: expected {expected_logits_shape}, got {logits.shape}"
    )
    print(f"    [+] Logits shape verified: {logits.shape} == (Batch={batch_size}, SeqLen={seq_len}, Vocab={vocab_size})")

    assert attentions is not None and len(attentions) == n_layers, (
        f"Attentions count mismatch: expected {n_layers} layers, got {len(attentions) if attentions else 0}"
    )
    expected_attn_shape = (batch_size, n_heads, seq_len, seq_len)
    assert attentions[0].shape == expected_attn_shape, (
        f"Attention matrix shape mismatch: expected {expected_attn_shape}, got {attentions[0].shape}"
    )
    print(f"    [+] Attention heatmaps shape verified: {len(attentions)} layers of {attentions[0].shape}")

    # 3. SFT Mock Backward Pass & Gradient Flow Verification
    print("\n[3/3] Verifying SFT Loss & Gradient Flow through RoPE, SwiGLU, RMSNorm...")
    mock_targets = mock_input_tokens.clone()
    prompt_len = 6
    mock_targets[:, :prompt_len] = -100  # Mask prompt tokens with ignore_index=-100
    
    loss = compute_sft_loss(logits, mock_targets)
    assert not torch.isnan(loss), "SFT loss is NaN"
    assert not torch.isinf(loss), "SFT loss is Inf"
    assert loss.item() > 0.0, f"SFT loss non-positive: {loss.item()}"
    print(f"    [+] SFT Cross-Entropy Loss computed: {loss.item():.4f} (prompt tokens masked)")

    # Execute backward pass
    loss.backward()

    # Audit specific component gradients
    audited_components = {
        "Token Embeddings": model.tok_embeddings.weight,
        "Final RMSNorm": model.norm.weight,
    }

    # Add layer 0 components
    layer0 = model.layers[0]
    audited_components.update({
        "Layer 0 Attention RMSNorm": layer0.attention_norm.weight,
        "Layer 0 Q-Projection (RoPE Input)": layer0.attention.q_proj.weight,
        "Layer 0 K-Projection (RoPE Input)": layer0.attention.k_proj.weight,
        "Layer 0 V-Projection": layer0.attention.v_proj.weight,
        "Layer 0 Out-Projection": layer0.attention.out_proj.weight,
        "Layer 0 FFN RMSNorm": layer0.ffn_norm.weight,
        "Layer 0 SwiGLU Gate Proj (w1)": layer0.ffn.w_gate.weight,
        "Layer 0 SwiGLU Up Proj (w2)": layer0.ffn.w_up.weight,
        "Layer 0 SwiGLU Down Proj (w3)": layer0.ffn.w_down.weight,
    })

    for name, param in audited_components.items():
        assert param.grad is not None, f"Gradient missing for {name}"
        assert torch.isfinite(param.grad).all(), f"Gradient contains NaN/Inf for {name}"
        grad_norm = param.grad.abs().sum().item()
        assert grad_norm > 0.0, f"Gradient is all zeros for {name}"
        print(f"    [+] {name:<35} | Grad Norm: {grad_norm:.6f} (PASS)")

    # Comprehensive check across all model parameters
    for p_name, p in model.named_parameters():
        if p.requires_grad:
            assert p.grad is not None, f"Param {p_name} has None grad"
            assert torch.isfinite(p.grad).all(), f"Param {p_name} has non-finite grad"

    print("\n" + "=" * 70)
    print(" ALL MODEL ARCHITECTURE & SFT GRADIENT CHECKS PASSED (100%)")
    print("=" * 70)
    return True


# Pytest test function wrapper
def test_model_acceptance():
    assert run_model_verification() is True


if __name__ == "__main__":
    success = run_model_verification()
    sys.exit(0 if success else 1)
