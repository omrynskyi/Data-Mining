"""Model configuration dataclass for Nano LLM Transformer."""

from dataclasses import dataclass, asdict
from typing import Optional, Dict, Any


@dataclass
class ModelArgs:
    """Hyperparameters configuration for Nano Transformer architecture."""
    vocab_size: int = 260
    d_model: int = 128
    n_layers: int = 4
    n_heads: int = 4
    n_kv_heads: Optional[int] = None
    d_ff: Optional[int] = None
    multiple_of: int = 64
    max_seq_len: int = 512
    dropout: float = 0.0
    norm_eps: float = 1e-5
    rope_base: float = 10000.0
    tie_embeddings: bool = True

    def __post_init__(self) -> None:
        if self.d_model <= 0 or self.n_heads <= 0:
            raise ValueError(
                f"d_model ({self.d_model}) and n_heads ({self.n_heads}) must be positive integers"
            )
        if self.d_model % self.n_heads != 0:
            raise ValueError(
                f"d_model ({self.d_model}) must be divisible by n_heads ({self.n_heads})"
            )
        
        # Default n_kv_heads to n_heads (Standard Multi-Head Attention)
        if self.n_kv_heads is None:
            self.n_kv_heads = self.n_heads
        elif self.n_kv_heads <= 0 or self.n_heads % self.n_kv_heads != 0:
            raise ValueError(
                f"n_heads ({self.n_heads}) must be divisible by n_kv_heads ({self.n_kv_heads})"
            )

        self.head_dim = self.d_model // self.n_heads
        if self.head_dim % 2 != 0:
            raise ValueError(
                f"head_dim ({self.head_dim}) must be an even integer for rotary embeddings"
            )

        # SwiGLU 8/3 dimension calculation with multiple_of alignment
        if self.d_ff is None:
            raw_d_ff = int(8 * self.d_model / 3)
            self.d_ff = self.multiple_of * ((raw_d_ff + self.multiple_of - 1) // self.multiple_of)

        if self.norm_eps <= 0:
            raise ValueError(f"norm_eps ({self.norm_eps}) must be strictly positive")
        if not (0.0 <= self.dropout < 1.0):
            raise ValueError(f"dropout ({self.dropout}) must be in range [0.0, 1.0)")
        if self.vocab_size <= 0:
            raise ValueError(f"vocab_size ({self.vocab_size}) must be positive")
        if self.max_seq_len <= 0:
            raise ValueError(f"max_seq_len ({self.max_seq_len}) must be positive")

    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "ModelArgs":
        """Instantiate ModelArgs from dictionary, filtering unknown keys."""
        valid_keys = {f for f in cls.__dataclass_fields__}
        filtered = {k: v for k, v in d.items() if k in valid_keys}
        return cls(**filtered)
