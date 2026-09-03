"""Causal Multi-Head / Grouped-Query Attention with Rotary Embeddings and KV-Cache."""

import math
from typing import Optional, Tuple
import torch
import torch.nn as nn
import torch.nn.functional as F

from nano_transformer.config import ModelArgs
from nano_transformer.rope import RotaryEmbedding


def repeat_kv(x: torch.Tensor, n_rep: int) -> torch.Tensor:
    """Expands Key/Value heads for Grouped-Query Attention (GQA).

    Transforms shape (B, n_kv_heads, T, head_dim) -> (B, n_heads, T, head_dim).
    """
    if n_rep == 1:
        return x
    B, n_kv_heads, T, head_dim = x.shape
    return (
        x[:, :, None, :, :]
        .expand(B, n_kv_heads, n_rep, T, head_dim)
        .reshape(B, n_kv_heads * n_rep, T, head_dim)
    )


class KVCache:
    """Dynamic Key-Value Cache for single-layer autoregressive generation."""

    def __init__(self) -> None:
        self.k: Optional[torch.Tensor] = None
        self.v: Optional[torch.Tensor] = None

    def update(
        self,
        k_val: torch.Tensor,
        v_val: torch.Tensor
    ) -> Tuple[torch.Tensor, torch.Tensor]:
        """Appends new key and value slices along the sequence dimension (dim=2)."""
        if self.k is None:
            self.k = k_val
            self.v = v_val
        else:
            self.k = torch.cat([self.k, k_val], dim=2)
            self.v = torch.cat([self.v, v_val], dim=2)
        return self.k, self.v

    @property
    def seq_len(self) -> int:
        return 0 if self.k is None else self.k.shape[2]

    @property
    def memory_bytes(self) -> int:
        if self.k is None or self.v is None:
            return 0
        return self.k.element_size() * (self.k.nelement() + self.v.nelement())

    def reset(self) -> None:
        self.k = None
        self.v = None


class CausalSelfAttention(nn.Module):
    """Causal Multi-Head and Grouped-Query Attention with RoPE and KV-Cache."""

    def __init__(self, args: ModelArgs) -> None:
        super().__init__()
        self.args = args
        self.d_model = args.d_model
        self.n_heads = args.n_heads
        self.n_kv_heads = args.n_kv_heads if args.n_kv_heads is not None else args.n_heads
        self.n_rep = self.n_heads // self.n_kv_heads
        self.head_dim = args.head_dim if hasattr(args, "head_dim") else args.d_model // args.n_heads

        # Linear projections (bias-free)
        self.q_proj = nn.Linear(self.d_model, self.n_heads * self.head_dim, bias=False)
        self.k_proj = nn.Linear(self.d_model, self.n_kv_heads * self.head_dim, bias=False)
        self.v_proj = nn.Linear(self.d_model, self.n_kv_heads * self.head_dim, bias=False)
        self.out_proj = nn.Linear(self.n_heads * self.head_dim, self.d_model, bias=False)

        # Aliases for interface compatibility
        self.wq = self.q_proj
        self.wk = self.k_proj
        self.wv = self.v_proj
        self.wo = self.out_proj

        # Rotary Positional Embeddings
        self.rope = RotaryEmbedding(
            dim=self.head_dim,
            max_seq_len=args.max_seq_len,
            base=args.rope_base
        )

        self.attn_dropout = nn.Dropout(args.dropout) if args.dropout > 0.0 else nn.Identity()
        self.resid_dropout = nn.Dropout(args.dropout) if args.dropout > 0.0 else nn.Identity()

        # Internal layer-level KV cache buffer for convenience
        self.cache_k: Optional[torch.Tensor] = None
        self.cache_v: Optional[torch.Tensor] = None

    def reset_cache(self) -> None:
        """Reset internal layer KV-cache tensors."""
        self.cache_k = None
        self.cache_v = None

    def forward(
        self,
        x: torch.Tensor,
        start_pos: int = 0,
        kv_cache: Optional[KVCache] = None,
        use_cache: bool = False,
        return_attentions: bool = False,
    ) -> Tuple[torch.Tensor, Optional[torch.Tensor]]:
        """Forward pass for Causal Self-Attention.

        Args:
            x: Input tensor of shape (B, T, d_model).
            start_pos: Starting sequence position for RoPE and causal alignment.
            kv_cache: Optional external KVCache instance.
            use_cache: Whether to update and use internal/external KV cache.
            return_attentions: Whether to return post-softmax attention matrices.

        Returns:
            Tuple of (output tensor of shape (B, T, d_model), optional attention weights).
        """
        B, T_q, _ = x.shape

        # Linear projections
        q = self.q_proj(x).view(B, T_q, self.n_heads, self.head_dim).transpose(1, 2)       # (B, n_heads, T_q, head_dim)
        k = self.k_proj(x).view(B, T_q, self.n_kv_heads, self.head_dim).transpose(1, 2)    # (B, n_kv_heads, T_q, head_dim)
        v = self.v_proj(x).view(B, T_q, self.n_kv_heads, self.head_dim).transpose(1, 2)    # (B, n_kv_heads, T_q, head_dim)

        # Apply Rotary Position Embeddings
        q = self.rope(q, start_pos=start_pos)
        k = self.rope(k, start_pos=start_pos)

        # KV-Cache management
        if kv_cache is not None:
            k, v = kv_cache.update(k, v)
        elif use_cache:
            if self.cache_k is None or start_pos == 0:
                self.cache_k = k
                self.cache_v = v
            else:
                self.cache_k = torch.cat([self.cache_k, k], dim=2)
                self.cache_v = torch.cat([self.cache_v, v], dim=2)
            k = self.cache_k
            v = self.cache_v

        T_k = k.shape[2]

        # Expand KV heads for GQA if needed
        k_exp = repeat_kv(k, self.n_rep)  # (B, n_heads, T_k, head_dim)
        v_exp = repeat_kv(v, self.n_rep)  # (B, n_heads, T_k, head_dim)

        # Scaled dot-product attention
        scale = 1.0 / math.sqrt(self.head_dim)
        scores = torch.matmul(q, k_exp.transpose(-2, -1)) * scale  # (B, n_heads, T_q, T_k)

        # Apply Causal Mask
        if T_q > 1 or start_pos == 0:
            q_pos = torch.arange(start_pos, start_pos + T_q, device=x.device)[:, None]
            k_pos = torch.arange(0, T_k, device=x.device)[None, :]
            mask = q_pos >= k_pos  # True where attention is valid
            scores = scores.masked_fill(~mask, float("-inf"))

        # Softmax & Dropout
        attn_weights = F.softmax(scores.float(), dim=-1).type_as(x)
        attn_weights_dropped = self.attn_dropout(attn_weights)

        # Context aggregation
        context = torch.matmul(attn_weights_dropped, v_exp)  # (B, n_heads, T_q, head_dim)
        context = context.transpose(1, 2).contiguous().view(B, T_q, self.n_heads * self.head_dim)

        output = self.resid_dropout(self.out_proj(context))

        return output, (attn_weights if return_attentions else None)
