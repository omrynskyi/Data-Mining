"""Rotary Position Embeddings (RoPE) with split-half rotation and trigonometric caching."""

import torch
import torch.nn as nn
from typing import Tuple, Optional


def rotate_half(x: torch.Tensor) -> torch.Tensor:
    """Rotates half the hidden dimensions of the input tensor.

    Splits the last dimension in half: [x1, x2] -> [-x2, x1].
    """
    half_dim = x.shape[-1] // 2
    x1 = x[..., :half_dim]
    x2 = x[..., half_dim:]
    return torch.cat([-x2, x1], dim=-1)


def apply_rotary_emb(
    x: torch.Tensor,
    cos: torch.Tensor,
    sin: torch.Tensor
) -> torch.Tensor:
    """Applies Rotary Position Embedding to input tensor x.

    Args:
        x: Input tensor of shape (..., head_dim).
        cos: Precomputed cosine tensor, broadcastable to x.
        sin: Precomputed sine tensor, broadcastable to x.

    Returns:
        Rotated tensor with same shape and dtype as x.
    """
    return (x * cos.type_as(x)) + (rotate_half(x) * sin.type_as(x))


# Alias for backward compatibility across test suites
apply_rope = apply_rotary_emb


def apply_rotary_pos_emb(
    q: torch.Tensor,
    k: torch.Tensor,
    cos: torch.Tensor,
    sin: torch.Tensor
) -> Tuple[torch.Tensor, torch.Tensor]:
    """Applies RoPE simultaneously to both query and key tensors."""
    q_rot = apply_rotary_emb(q, cos, sin)
    k_rot = apply_rotary_emb(k, cos, sin)
    return q_rot, k_rot


class RotaryEmbedding(nn.Module):
    """Precomputes and caches cos/sin frequencies for Rotary Position Embeddings (RoPE).

    Args:
        dim: Dimension of each attention head (head_dim, must be even).
        max_seq_len: Initial maximum sequence length for precomputed table.
        base: The base frequency theta (default 10000.0).
    """

    def __init__(self, dim: int, max_seq_len: int = 512, base: float = 10000.0) -> None:
        super().__init__()
        if dim % 2 != 0:
            raise ValueError(f"RoPE dimension must be even, got dim={dim}")
        self.dim = dim
        self.max_seq_len = max_seq_len
        self.base = base
        self._build_cache(max_seq_len)

    def _build_cache(self, seq_len: int) -> None:
        """Precomputes cos and sin tables for seq_len positions."""
        inv_freq = 1.0 / (self.base ** (torch.arange(0, self.dim, 2, dtype=torch.float32) / self.dim))
        t = torch.arange(seq_len, dtype=torch.float32)
        # Outer product: (seq_len, dim // 2)
        freqs = torch.outer(t, inv_freq)
        # Split-half concatenation: duplicate freqs for both halves: (seq_len, dim)
        freqs = torch.cat([freqs, freqs], dim=-1)
        self.register_buffer("cos_cached", freqs.cos(), persistent=False)
        self.register_buffer("sin_cached", freqs.sin(), persistent=False)

    @property
    def cos(self) -> torch.Tensor:
        return self.cos_cached

    @property
    def sin(self) -> torch.Tensor:
        return self.sin_cached

    def get_cos_sin(
        self,
        seq_len: int,
        start_pos: int = 0,
        device: Optional[torch.device] = None
    ) -> Tuple[torch.Tensor, torch.Tensor]:
        """Retrieves or expands precomputed cos and sin slices for [start_pos : start_pos + seq_len]."""
        end_pos = start_pos + seq_len
        if end_pos > self.cos_cached.shape[0]:
            new_len = max(end_pos, self.cos_cached.shape[0] * 2)
            self._build_cache(new_len)
            if device is not None:
                self.cos_cached = self.cos_cached.to(device)
                self.sin_cached = self.sin_cached.to(device)

        cos = self.cos_cached[start_pos:end_pos]
        sin = self.sin_cached[start_pos:end_pos]
        if device is not None and cos.device != device:
            cos = cos.to(device)
            sin = sin.to(device)
        return cos, sin

    def forward(
        self,
        x: torch.Tensor,
        start_pos: int = 0
    ) -> torch.Tensor:
        """Applies RoPE to tensor x.

        Supports shapes:
        - 4D: (B, H, T, D) -> cos reshaped to (1, 1, T, D)
        - 3D: (B, T, D)    -> cos reshaped to (1, T, D)
        - 2D: (T, D)       -> cos reshaped to (T, D)
        """
        dim = x.shape[-1]
        if x.dim() == 4:
            seq_len = x.shape[2]
            cos, sin = self.get_cos_sin(seq_len, start_pos, device=x.device)
            cos = cos.view(1, 1, seq_len, dim)
            sin = sin.view(1, 1, seq_len, dim)
        elif x.dim() == 3:
            seq_len = x.shape[1]
            cos, sin = self.get_cos_sin(seq_len, start_pos, device=x.device)
            cos = cos.view(1, seq_len, dim)
            sin = sin.view(1, seq_len, dim)
        elif x.dim() == 2:
            seq_len = x.shape[0]
            cos, sin = self.get_cos_sin(seq_len, start_pos, device=x.device)
            cos = cos.view(seq_len, dim)
            sin = sin.view(seq_len, dim)
        else:
            raise ValueError(f"Expected 2D, 3D, or 4D tensor for RoPE, got shape {x.shape}")

        return apply_rotary_emb(x, cos, sin)
