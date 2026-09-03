"""Nano LLM Transformer Package."""

from nano_transformer.config import ModelArgs
from nano_transformer.norm import RMSNorm
from nano_transformer.rope import RotaryEmbedding, apply_rotary_emb, apply_rope, rotate_half
from nano_transformer.ffn import SwiGLUFFN
from nano_transformer.attention import CausalSelfAttention, KVCache, repeat_kv
from nano_transformer.block import TransformerBlock
from nano_transformer.model import Transformer
from nano_transformer.tokenizer import ByteTokenizer, BPETokenizer
from nano_transformer.sft import (
    SFTDataset,
    collate_sft,
    DataCollatorForSFT,
    compute_sft_loss,
    SFTTrainer,
    verify_sft_gradient_flow,
)
from nano_transformer.device import (
    resolve_device,
    get_memory_stats,
    check_memory_limit,
    empty_device_cache,
    sync_device,
)

__all__ = [
    "ModelArgs",
    "RMSNorm",
    "RotaryEmbedding",
    "apply_rotary_emb",
    "apply_rope",
    "rotate_half",
    "SwiGLUFFN",
    "CausalSelfAttention",
    "KVCache",
    "repeat_kv",
    "TransformerBlock",
    "Transformer",
    "ByteTokenizer",
    "BPETokenizer",
    "SFTDataset",
    "collate_sft",
    "DataCollatorForSFT",
    "compute_sft_loss",
    "SFTTrainer",
    "verify_sft_gradient_flow",
    "resolve_device",
    "get_memory_stats",
    "check_memory_limit",
    "empty_device_cache",
    "sync_device",
]
