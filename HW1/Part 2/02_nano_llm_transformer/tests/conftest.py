"""
Shared Pytest Fixtures and Test Utilities for Nano LLM Transformer and Admin Dashboard.
"""

import sys
import os
from pathlib import Path
from typing import Dict, Any, Tuple, Optional, List
import pytest
import torch
import torch.nn as nn
import torch.nn.functional as F

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


# ---------------------------------------------------------------------------
# Reference / Fallback Implementations for Strict Mathematical Oracles
# ---------------------------------------------------------------------------

def reference_rmsnorm(x: torch.Tensor, weight: torch.Tensor, eps: float = 1e-5) -> torch.Tensor:
    """Authoritative mathematical reference for RMSNorm."""
    variance = x.pow(2).mean(-1, keepdim=True)
    normed = x * torch.rsqrt(variance + eps)
    return normed * weight


def reference_swiglu(x: torch.Tensor, w_gate: torch.Tensor, w_up: torch.Tensor, w_down: torch.Tensor) -> torch.Tensor:
    """Authoritative mathematical reference for SwiGLU FFN."""
    gate = F.silu(F.linear(x, w_gate))
    up = F.linear(x, w_up)
    gated = gate * up
    return F.linear(gated, w_down)


def reference_rope_freqs(dim: int, max_seq_len: int, base: float = 10000.0) -> Tuple[torch.Tensor, torch.Tensor]:
    """Authoritative mathematical reference for RoPE frequencies."""
    theta = 1.0 / (base ** (torch.arange(0, dim, 2).float() / dim))
    m = torch.arange(max_seq_len).float()
    freqs = torch.outer(m, theta)  # (max_seq_len, dim/2)
    freqs_cis = torch.polar(torch.ones_like(freqs), freqs)  # complex
    cos = torch.cos(freqs)
    sin = torch.sin(freqs)
    # duplicate for full dim
    cos_full = torch.cat([cos, cos], dim=-1)
    sin_full = torch.cat([sin, sin], dim=-1)
    return cos_full, sin_full


def verify_gradient_flow(model: nn.Module, loss: torch.Tensor) -> Dict[str, bool]:
    """
    Executes loss.backward() and audits every parameter for valid, finite, non-zero gradients.
    """
    loss.backward()
    grad_status = {}
    for name, param in model.named_parameters():
        if param.requires_grad:
            has_grad = param.grad is not None
            is_finite = bool(torch.isfinite(param.grad).all().item()) if has_grad else False
            is_nonzero = bool((param.grad.abs().sum() > 0).item()) if has_grad else False
            grad_status[name] = has_grad and is_finite and is_nonzero
    return grad_status


def verify_causal_mask_structure(attn_matrix: torch.Tensor, atol: float = 1e-5) -> bool:
    """
    Verifies that the attention matrix is causal (upper-triangle above main diagonal is 0.0).
    Shape: (..., T, T)
    """
    T = attn_matrix.shape[-1]
    upper_tri = torch.triu(attn_matrix, diagonal=1)
    return bool(torch.all(torch.abs(upper_tri) <= atol).item())


# ---------------------------------------------------------------------------
# Pytest Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def project_root() -> Path:
    return PROJECT_ROOT


@pytest.fixture
def tiny_config_dict() -> Dict[str, Any]:
    return {
        "vocab_size": 260,
        "d_model": 64,
        "n_layers": 2,
        "n_heads": 4,
        "n_kv_heads": 2,
        "d_ff": 192,
        "max_seq_len": 128,
        "dropout": 0.0,
        "norm_eps": 1e-5,
        "rope_base": 10000.0,
        "tie_embeddings": True
    }


@pytest.fixture
def small_config_dict() -> Dict[str, Any]:
    return {
        "vocab_size": 512,
        "d_model": 128,
        "n_layers": 4,
        "n_heads": 4,
        "n_kv_heads": 2,
        "d_ff": 384,
        "max_seq_len": 256,
        "dropout": 0.1,
        "norm_eps": 1e-5,
        "rope_base": 10000.0,
        "tie_embeddings": True
    }


@pytest.fixture
def sample_input_tokens() -> torch.Tensor:
    """Batch of 2 sequences of length 16 with token IDs in range [4, 250]."""
    torch.manual_seed(42)
    return torch.randint(4, 250, (2, 16), dtype=torch.long)


@pytest.fixture
def sample_sft_batch() -> Tuple[torch.Tensor, torch.Tensor]:
    """
    Returns (tokens, targets) where targets contain prompt-masking (-100)
    for the first 6 tokens.
    """
    torch.manual_seed(42)
    B, T = 2, 16
    tokens = torch.randint(4, 250, (B, T), dtype=torch.long)
    targets = tokens.clone()
    targets[:, :6] = -100  # prompt masked
    return tokens, targets


@pytest.fixture
def sample_prompt_text() -> str:
    return "The quick brown fox jumps over the lazy dog."


@pytest.fixture
def device() -> torch.device:
    """Default device for tests: mps if available, else cpu."""
    if torch.backends.mps.is_available() and torch.backends.mps.is_built():
        return torch.device("mps")
    return torch.device("cpu")
