"""Root Mean Square Layer Normalization (RMSNorm)."""

import torch
import torch.nn as nn


class RMSNorm(nn.Module):
    """Root Mean Square Layer Normalization.

    Normalizes the input activations by their root-mean-square across the last dimension,
    followed by a learnable elementwise affine scale.

    Args:
        dim: The dimension to normalize over (e.g., d_model).
        eps: Epsilon value added to denominator for numerical stability.
    """

    def __init__(self, dim: int, eps: float = 1e-5) -> None:
        super().__init__()
        self.eps = eps
        self.weight = nn.Parameter(torch.ones(dim))

    def _norm(self, x: torch.Tensor) -> torch.Tensor:
        """Internal normalization operating in float32 for numerical stability."""
        return x * torch.rsqrt(x.pow(2).mean(-1, keepdim=True) + self.eps)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """Apply RMSNorm to input tensor x of shape (..., dim)."""
        input_dtype = x.dtype
        # Compute in float32 to prevent underflow/overflow on MPS/CUDA, then cast back
        normed = self._norm(x.float()).type_as(x)
        return normed * self.weight

    def extra_repr(self) -> str:
        return f"dim={self.weight.shape[0]}, eps={self.eps}"
