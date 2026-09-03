"""Transformer Decoder Block with Pre-LN RMSNorm, Causal Attention, and SwiGLU FFN."""

from typing import Optional, Tuple, Any
import torch
import torch.nn as nn

from nano_transformer.config import ModelArgs
from nano_transformer.norm import RMSNorm
from nano_transformer.attention import CausalSelfAttention, KVCache
from nano_transformer.ffn import SwiGLUFFN


class TransformerBlock(nn.Module):
    """Transformer Decoder Block with Pre-LN Residual connections.

    Structure:
        x1 = x + Attention(RMSNorm(x))
        x2 = x1 + SwiGLUFFN(RMSNorm(x1))
    """

    def __init__(
        self,
        args_or_idx: Any = None,
        layer_idx_or_args: Any = None,
        args: Optional[ModelArgs] = None,
        layer_idx: int = 0
    ) -> None:
        super().__init__()
        # Flexible argument parsing supporting (args, layer_idx) or (layer_idx, args)
        if isinstance(args_or_idx, ModelArgs):
            resolved_args = args_or_idx
            resolved_idx = layer_idx if layer_idx_or_args is None else (
                layer_idx_or_args if isinstance(layer_idx_or_args, int) else 0
            )
        elif isinstance(layer_idx_or_args, ModelArgs):
            resolved_args = layer_idx_or_args
            resolved_idx = args_or_idx if isinstance(args_or_idx, int) else 0
        elif args is not None:
            resolved_args = args
            resolved_idx = layer_idx
        else:
            raise ValueError("ModelArgs must be provided to instantiate TransformerBlock")

        self.layer_idx = resolved_idx
        self.args = resolved_args

        self.attention_norm = RMSNorm(resolved_args.d_model, eps=resolved_args.norm_eps)
        self.attention = CausalSelfAttention(resolved_args)
        self.ffn_norm = RMSNorm(resolved_args.d_model, eps=resolved_args.norm_eps)
        self.ffn = SwiGLUFFN(
            d_model=resolved_args.d_model,
            d_ff=resolved_args.d_ff,
            multiple_of=resolved_args.multiple_of,
            dropout=resolved_args.dropout
        )
        self.feed_forward = self.ffn

    def forward(
        self,
        x: torch.Tensor,
        start_pos: int = 0,
        kv_cache: Optional[KVCache] = None,
        use_cache: bool = False,
        return_attentions: bool = False,
    ) -> Tuple[torch.Tensor, Optional[torch.Tensor]]:
        """Forward pass for TransformerBlock.

        Args:
            x: Input tensor of shape (B, T, d_model).
            start_pos: Starting sequence position for RoPE.
            kv_cache: Optional layer KV-cache.
            use_cache: Whether to use KV-caching.
            return_attentions: Whether to return attention weights.

        Returns:
            Tuple of (output tensor of shape (B, T, d_model), optional attention weights).
        """
        # Pre-LN Attention Branch
        normed_x = self.attention_norm(x)
        attn_out, attn_weights = self.attention(
            normed_x,
            start_pos=start_pos,
            kv_cache=kv_cache,
            use_cache=use_cache,
            return_attentions=return_attentions,
        )
        x = x + attn_out

        # Pre-LN SwiGLU FFN Branch
        x = x + self.feed_forward(self.ffn_norm(x))

        return x, attn_weights
