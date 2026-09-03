"""
Tier 5 Adversarial Test Suite: Apple Silicon MPS Memory Management & Generation Loop Stress.

Adversarial Objectives:
1. Sustained autoregressive token generation loops on MPS (50 consecutive passes, >1,000 tokens generated).
2. Dynamic KV-cache expansion memory audits and leak detection across cycles.
3. Strict enforcement of Apple Silicon unified memory ceiling (<= 4.0 GB).
4. Long-context generation stress up to maximum sequence length limit (256 tokens).
5. Device synchronization robustness and empty_device_cache memory reclamation.
6. Resolver fallback behavior under invalid or forced device inputs.
"""

import time
import math
from typing import Dict, Any, List
import pytest
import torch

from nano_transformer.config import ModelArgs
from nano_transformer.model import Transformer
from nano_transformer.tokenizer import ByteTokenizer
from nano_transformer.attention import KVCache
from nano_transformer.device import (
    resolve_device,
    get_memory_stats,
    check_memory_limit,
    empty_device_cache,
    sync_device,
)


@pytest.fixture
def benchmark_model(device: torch.device) -> Transformer:
    """Instantiates a benchmark Transformer model placed on the active compute device."""
    args = ModelArgs(
        vocab_size=260,
        d_model=128,
        n_layers=4,
        n_heads=4,
        n_kv_heads=2,
        d_ff=384,
        max_seq_len=256,
        dropout=0.0,
    )
    model = Transformer(args).to(device)
    model.eval()
    return model


@pytest.fixture
def tokenizer() -> ByteTokenizer:
    return ByteTokenizer()


# ===========================================================================
# 1. Sustained Generation Loop & Memory Leak Auditing (50 passes, >1,000 tokens)
# ===========================================================================

def test_adversarial_sustained_mps_generation_loops(
    benchmark_model: Transformer,
    tokenizer: ByteTokenizer,
    device: torch.device
):
    """
    Stress-test: Runs 50 consecutive autoregressive generation passes (20 new tokens each = 1,000 tokens).
    Measures baseline RSS vs final RSS to confirm zero unbounded linear memory leak.
    """
    prompt = "Apple Silicon Metal Performance Shaders transformer evaluation loop."
    prompt_tokens = tokenizer.encode(prompt)

    empty_device_cache(device)
    sync_device(device)
    initial_stats = get_memory_stats(device)
    initial_rss_mb = initial_stats["process_rss_mb"]

    total_tokens_generated = 0
    rss_checkpoints = []

    for iteration in range(50):
        gen_tokens, metrics = benchmark_model.generate(
            prompt_tokens,
            max_new_tokens=20,
            temperature=0.7,
            device=device,
            return_metrics=True,
            use_cache=True,
            eos_id=None,  # disable early stopping so every pass generates the full 20 tokens
        )
        sync_device(device)
        total_tokens_generated += metrics["tokens_generated"]

        if (iteration + 1) % 10 == 0:
            current_stats = get_memory_stats(device)
            rss_checkpoints.append(current_stats["process_rss_mb"])

    final_stats = get_memory_stats(device)
    final_rss_mb = final_stats["process_rss_mb"]

    # Verify generation volume
    assert total_tokens_generated >= 1000, f"Expected >= 1000 tokens generated, got {total_tokens_generated}"

    # Verify strict memory ceiling (<= 4.0 GB)
    assert final_stats["within_memory_budget"] is True
    assert final_stats["process_rss_gb"] <= 4.0, (
        f"Memory exceeded 4.0 GB limit: {final_stats['process_rss_gb']:.3f} GB"
    )

    # Memory growth between checkpoint 1 (iter 10) and checkpoint 5 (iter 50) must be sub-linear / bounded (< 50MB delta)
    rss_delta_mb = final_rss_mb - rss_checkpoints[0]
    assert rss_delta_mb < 50.0, (
        f"Potential memory leak detected: RSS grew by {rss_delta_mb:.2f} MB across iterations 10->50."
    )


# ===========================================================================
# 2. Long Sequence Generation (Near Max Sequence Length)
# ===========================================================================

def test_adversarial_long_sequence_generation_bounds(
    benchmark_model: Transformer,
    tokenizer: ByteTokenizer,
    device: torch.device
):
    """
    Stress-test: Generates long token sequences (150 new tokens) approaching max_seq_len (256).
    Verifies KV cache allocation integrity, output validity, and memory limits.
    """
    prompt = "Deep learning transformers on unified memory:"
    prompt_tokens = tokenizer.encode(prompt)

    empty_device_cache(device)
    gen_tokens, metrics = benchmark_model.generate(
        prompt_tokens,
        max_new_tokens=150,
        temperature=0.5,
        device=device,
        return_metrics=True,
        use_cache=True,
    )
    sync_device(device)

    assert len(gen_tokens) == len(prompt_tokens) + 150
    assert metrics["tokens_generated"] == 150
    assert all(0 <= tok < benchmark_model.vocab_size for tok in gen_tokens)

    # Verify memory within budget
    stats = get_memory_stats(device)
    assert stats["within_memory_budget"] is True
    assert stats["process_rss_gb"] < 2.0


# ===========================================================================
# 3. Dynamic KV-Cache Memory Calculation & Repeated Deallocation
# ===========================================================================

def test_adversarial_kv_cache_exact_memory_and_reclamation(device: torch.device):
    """
    Empirical oracle test: Audits KVCache memory_bytes calculation against theoretical formula.
    Stress-tests 200 allocations and deallocations with empty_device_cache.
    """
    batch_size = 1
    n_kv_heads = 2
    head_dim = 32
    seq_len = 64

    cache = KVCache()
    dummy_k = torch.randn(batch_size, n_kv_heads, seq_len, head_dim, device=device)
    dummy_v = torch.randn(batch_size, n_kv_heads, seq_len, head_dim, device=device)
    cache.update(dummy_k, dummy_v)

    # Theoretical size: 2 * (1 * 2 * 64 * 32) * 4 bytes (float32) = 2 * 4096 * 4 = 32,768 bytes
    expected_bytes = 2 * (batch_size * n_kv_heads * seq_len * head_dim) * 4
    assert cache.memory_bytes == expected_bytes, (
        f"KVCache memory_bytes mismatch: {cache.memory_bytes} vs expected {expected_bytes}"
    )

    # Stress repeated allocation and clearing
    for _ in range(200):
        c = KVCache()
        c.update(dummy_k, dummy_v)
        c.reset()

    empty_device_cache(device)
    sync_device(device)
    stats = get_memory_stats(device)
    assert stats["within_memory_budget"] is True


# ===========================================================================
# 4. Check Memory Limit Oracle & Failure Triggering
# ===========================================================================

def test_adversarial_check_memory_limit_oracle(device: torch.device):
    """
    Tests check_memory_limit function:
    1. Standard 4.0 GB limit must return within_limit = True.
    2. Deliberately tiny limit (0.00001 GB) must return within_limit = False.
    """
    within_4gb, usage_4gb, stats_4gb = check_memory_limit(max_limit_gb=4.0, device=device)
    assert within_4gb is True
    assert usage_4gb <= 4.0
    assert "process_rss_gb" in stats_4gb

    within_tiny, usage_tiny, _ = check_memory_limit(max_limit_gb=0.00001, device=device)
    assert within_tiny is False
    assert usage_tiny > 0.00001


# ===========================================================================
# 5. Device Resolver Fuzzing & Fallback Robustness
# ===========================================================================

@pytest.mark.parametrize("dev_input, expected_type", [
    (None, ["mps", "cpu", "cuda"]),
    ("auto", ["mps", "cpu", "cuda"]),
    ("cpu", ["cpu"]),
    ("mps", ["mps", "cpu"]),  # Falls back to cpu if mps is not built
    ("cuda", ["cuda", "cpu"]),
    ("tpu", ["cpu"]),
    ("unknown_device_xyz", ["cpu"]),
    (torch.device("cpu"), ["cpu"]),
])
def test_adversarial_device_resolver_robustness(dev_input: Any, expected_type: List[str]):
    """Tests device resolver resilience against arbitrary valid, invalid, and fallback inputs."""
    resolved = resolve_device(dev_input)
    assert isinstance(resolved, torch.device)
    assert resolved.type in expected_type
