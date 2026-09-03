"""SwiGLU Gated Feed-Forward Network."""

import torch
import torch.nn as nn
import torch.nn.functional as F
from typing import Optional


class SwiGLUFFN(nn.Module):
    """SwiGLU Feed-Forward Network with SiLU gated activation.

    Computes: (SiLU(x @ W_gate) * (x @ W_up)) @ W_down

    Args:
        d_model: Input and output embedding dimension.
        d_ff: Hidden dimension. If None, derived as 8/3 * d_model rounded to multiple_of.
        multiple_of: Alignment multiple for d_ff (default 64).
        dropout: Dropout probability applied to intermediate activations.
        bias: Whether to include bias in linear projections (default False).
    """

    def __init__(
        self,
        d_model: int,
        d_ff: Optional[int] = None,
        multiple_of: int = 64,
        dropout: float = 0.0,
        bias: bool = False
    ) -> None:
        super().__init__()
        if d_ff is None:
            raw_d_ff = int(8 * d_model / 3)
            d_ff = multiple_of * ((raw_d_ff + multiple_of - 1) // multiple_of)
        
        self.d_model = d_model
        self.d_ff = d_ff
        self.multiple_of = multiple_of
        self.w_gate = nn.Linear(d_model, d_ff, bias=bias)
        self.w_up = nn.Linear(d_model, d_ff, bias=bias)
        self.w_down = nn.Linear(d_ff, d_model, bias=bias)
        
        # Aliases for compatibility
        self.gate_proj = self.w_gate
        self.up_proj = self.w_up
        self.down_proj = self.w_down

        self.dropout = nn.Dropout(dropout) if dropout > 0.0 else nn.Identity()

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """Forward pass for SwiGLU FFN.

        Args:
            x: Input tensor of shape (..., d_model).

        Returns:
            Output tensor of shape (..., d_model).
        """
        gate = F.silu(self.w_gate(x))
        up = self.w_up(x)
        intermediate = gate * up
        intermediate = self.dropout(intermediate)
        return self.w_down(intermediate)

    def extra_repr(self) -> str:
        return f"d_model={self.d_model}, d_ff={self.d_ff}"
