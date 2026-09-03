"""
Tier 5: Adversarial Stress-Test Harnesses and Empirical Fuzzers.

Empirical verification suite challenging:
1. RoPE position extrapolation, rotational symmetry, and L2-norm isometry.
2. KV-cache single-step incremental decoding vs full prefill equivalence.
3. SFT gradient backpropagation under extreme loss masking, varied batch sizes, and optimizer updates.
4. Tokenizer resilience against multi-byte Unicode, complex emoji ZWJ sequences, empty strings, and malformed inputs.
"""

import math
import random
import unicodedata
from typing import List, Dict, Any, Tuple
import pytest
import torch
import torch.nn as nn
import torch.nn.functional as F

from nano_transformer.config import ModelArgs
from nano_transformer.rope import RotaryEmbedding, apply_rotary_emb, rotate_half
from nano_transformer.attention import CausalSelfAttention, KVCache
from nano_transformer.model import Transformer
from nano_transformer.tokenizer import ByteTokenizer, BPETokenizer
from nano_transformer.sft import (
    SFTDataset,
    DataCollatorForSFT,
    collate_sft,
    compute_sft_loss,
    SFTTrainer,
    verify_sft_gradient_flow,
)


# ===========================================================================
# 1. RoPE Positional Extrapolation and Rotational Symmetry Challenges
# ===========================================================================

class TestRoPEAdversarialChallenges:
    """Adversarial stress-tests challenging RoPE mathematical properties."""

    @pytest.mark.parametrize("head_dim", [2, 4, 8, 16, 32, 64, 128])
    @pytest.mark.parametrize("base", [100.0, 10000.0, 500000.0])
    @pytest.mark.parametrize("shift", [1, 7, 42, 128, 1000])
    def test_rope_rotational_symmetry_inner_product_invariance(self, head_dim: int, base: float, shift: int):
        """
        Mathematical Oracle: The inner product of RoPE-rotated vectors at positions m and n
        must depend ONLY on relative distance (m - n), i.e.:
            <R_m q, R_n k> == <R_{m+shift} q, R_{n+shift} k>
        """
        torch.manual_seed(42 + head_dim + int(base) % 100 + shift)
        rope = RotaryEmbedding(dim=head_dim, max_seq_len=2048, base=base)

        m = 15
        n = 8
        q = torch.randn(1, head_dim, dtype=torch.float32)
        k = torch.randn(1, head_dim, dtype=torch.float32)

        # Unshifted rotations
        cos_m, sin_m = rope.get_cos_sin(1, start_pos=m)
        cos_n, sin_n = rope.get_cos_sin(1, start_pos=n)
        q_rot_m = apply_rotary_emb(q, cos_m, sin_m)
        k_rot_n = apply_rotary_emb(k, cos_n, sin_n)
        dot_original = torch.sum(q_rot_m * k_rot_n).item()

        # Shifted rotations
        cos_ms, sin_ms = rope.get_cos_sin(1, start_pos=m + shift)
        cos_ns, sin_ns = rope.get_cos_sin(1, start_pos=n + shift)
        q_rot_ms = apply_rotary_emb(q, cos_ms, sin_ms)
        k_rot_ns = apply_rotary_emb(k, cos_ns, sin_ns)
        dot_shifted = torch.sum(q_rot_ms * k_rot_ns).item()

        assert math.isclose(dot_original, dot_shifted, rel_tol=1e-4, abs_tol=1e-5), (
            f"RoPE rotational symmetry failed for dim={head_dim}, base={base}, shift={shift}: "
            f"Original={dot_original:.6f}, Shifted={dot_shifted:.6f}, Diff={abs(dot_original - dot_shifted):.6e}"
        )

    @pytest.mark.parametrize("head_dim", [4, 16, 64])
    @pytest.mark.parametrize("pos", [0, 1, 99, 1024, 15000])
    def test_rope_l2_norm_preservation_isometry(self, head_dim: int, pos: int):
        """
        RoPE represents orthogonal rotations in 2D subspaces.
        The Euclidean L2 norm of any vector must be strictly preserved: ||R_m x||_2 == ||x||_2.
        """
        torch.manual_seed(100 + head_dim + pos)
        rope = RotaryEmbedding(dim=head_dim, max_seq_len=128)

        x = torch.randn(5, 3, head_dim, dtype=torch.float32)
        original_norms = torch.norm(x, p=2, dim=-1)

        cos, sin = rope.get_cos_sin(1, start_pos=pos)
        rotated_x = apply_rotary_emb(x, cos, sin)
        rotated_norms = torch.norm(rotated_x, p=2, dim=-1)

        max_norm_diff = torch.max(torch.abs(original_norms - rotated_norms)).item()
        assert max_norm_diff < 1e-4, f"RoPE failed L2 norm preservation at pos={pos}, max diff: {max_norm_diff}"

    def test_rope_dynamic_cache_extrapolation_growth(self):
        """
        Challenge: Initialize RoPE with tiny max_seq_len=8, then query sequence positions
        up to 2048 to force dynamic table reallocation. Verify no crashes, no NaN,
        and that previously computed slices remain strictly identical.
        """
        rope = RotaryEmbedding(dim=32, max_seq_len=8)
        assert rope.cos_cached.shape[0] == 8

        cos_initial_4, sin_initial_4 = rope.get_cos_sin(4, start_pos=0)
        cos_initial_copy = cos_initial_4.clone()

        # Query far beyond initial table
        cos_large, sin_large = rope.get_cos_sin(128, start_pos=1000)
        assert rope.cos_cached.shape[0] >= 1128
        assert not torch.isnan(cos_large).any()
        assert not torch.isnan(sin_large).any()

        # Check that [0:4] has not been corrupted by dynamic cache reallocation
        cos_after, sin_after = rope.get_cos_sin(4, start_pos=0)
        assert torch.allclose(cos_initial_copy, cos_after, atol=1e-7)

    def test_rope_odd_dimension_exception(self):
        """RoPE requires pairs of dimensions; odd dim must raise ValueError."""
        with pytest.raises(ValueError, match="RoPE dimension must be even"):
            _ = RotaryEmbedding(dim=33)

    def test_rope_inverse_rotation(self):
        """
        Rotating a vector by position m, and then rotating with negated sin
        must exactly invert the rotation and yield the original vector.
        """
        rope = RotaryEmbedding(dim=16, max_seq_len=64)
        x = torch.randn(2, 4, 16)
        cos, sin = rope.get_cos_sin(4, start_pos=10)

        rotated = apply_rotary_emb(x, cos, sin)
        inverted = apply_rotary_emb(rotated, cos, -sin)

        assert torch.allclose(x, inverted, atol=1e-5), "Inverse RoPE rotation failed to reconstruct original vector"


# ===========================================================================
# 2. KV-Cache Single-Step vs Full Prefill Equivalence Challenges
# ===========================================================================

class TestKVCacheEquivalenceChallenges:
    """Adversarial stress-tests challenging KV-cache single-step decoding vs full forward pass."""

    @pytest.mark.parametrize("seq_len", [5, 13, 31, 64])
    @pytest.mark.parametrize("split_idx", [1, 2, 4])
    @pytest.mark.parametrize("n_kv_heads", [1, 2, 4])  # Tests MQA, GQA, MHA
    def test_kv_cache_exact_logits_equivalence(self, seq_len: int, split_idx: int, n_kv_heads: int):
        """
        Oracle: For any sequence of tokens, autoregressive generation with KV-cache
        must produce logits identical to full prefill forward pass on the entire sequence.
        """
        if split_idx >= seq_len:
            pytest.skip("split_idx exceeds seq_len")

        torch.manual_seed(42 + seq_len + n_kv_heads)
        args = ModelArgs(
            vocab_size=260,
            d_model=64,
            n_layers=2,
            n_heads=4,
            n_kv_heads=n_kv_heads,
            d_ff=128,
            max_seq_len=128,
            dropout=0.0
        )
        model = Transformer(args)
        model.eval()

        tokens = torch.randint(4, 250, (1, seq_len), dtype=torch.long)

        # 1. Full prefill forward pass (Gold standard)
        with torch.no_grad():
            full_logits, _ = model(tokens, start_pos=0, use_cache=False)
            expected_final_logits = full_logits[:, -1, :]

        # 2. Incremental step-by-step KV cache decoding
        kv_caches = [KVCache() for _ in range(args.n_layers)]
        
        # Step A: Prefill first split_idx tokens
        prefix_tokens = tokens[:, :split_idx]
        with torch.no_grad():
            _ = model(prefix_tokens, start_pos=0, kv_cache=kv_caches, use_cache=True)

        # Step B: Step through remaining tokens one-by-one
        step_logits = None
        for step in range(split_idx, seq_len):
            curr_token = tokens[:, step:step+1]
            with torch.no_grad():
                step_logits, _ = model(curr_token, start_pos=step, kv_cache=kv_caches, use_cache=True)

        cached_final_logits = step_logits[:, -1, :]

        # Measure max absolute error
        max_diff = torch.max(torch.abs(expected_final_logits - cached_final_logits)).item()
        assert max_diff < 1e-4, (
            f"KV-cache equivalence violation for seq_len={seq_len}, split={split_idx}, n_kv_heads={n_kv_heads}: "
            f"Max absolute diff = {max_diff:.6e} (tolerance 1e-4)"
        )

    @pytest.mark.parametrize("prompt_len", [3, 8, 17])
    @pytest.mark.parametrize("max_new_tokens", [5, 12])
    def test_kv_cache_greedy_generation_token_identity(self, prompt_len: int, max_new_tokens: int):
        """
        At temperature=0.0 (greedy decoding), KV-cached generation MUST produce
        the exact same token sequence as non-cached full-context generation.
        """
        torch.manual_seed(999)
        args = ModelArgs(
            vocab_size=260,
            d_model=64,
            n_layers=2,
            n_heads=4,
            n_kv_heads=2,
            d_ff=128,
            max_seq_len=128,
            dropout=0.0
        )
        model = Transformer(args)
        model.eval()

        prompt = torch.randint(4, 250, (prompt_len,), dtype=torch.long).tolist()

        gen_cached = model.generate(
            prompt,
            max_new_tokens=max_new_tokens,
            temperature=0.0,
            use_cache=True
        )

        gen_uncached = model.generate(
            prompt,
            max_new_tokens=max_new_tokens,
            temperature=0.0,
            use_cache=False
        )

        assert gen_cached == gen_uncached, (
            f"Greedy generation mismatch between cached and uncached:\n"
            f"Cached  : {gen_cached}\n"
            f"Uncached: {gen_uncached}"
        )

    def test_kv_cache_reset_and_isolation(self):
        """Verify that sequential calls do not leak cache state across requests."""
        args = ModelArgs(vocab_size=260, d_model=64, n_layers=2, n_heads=4, n_kv_heads=2, d_ff=128)
        model = Transformer(args)
        model.eval()

        cache = KVCache()
        k_sample = torch.randn(1, 2, 4, 16)
        v_sample = torch.randn(1, 2, 4, 16)
        cache.update(k_sample, v_sample)
        assert cache.seq_len == 4
        assert cache.memory_bytes > 0

        cache.reset()
        assert cache.seq_len == 0
        assert cache.memory_bytes == 0
        assert cache.k is None and cache.v is None

    @pytest.mark.parametrize("temp", [0.01, 0.5, 1.0, 2.0])
    @pytest.mark.parametrize("top_k", [1, 5, 50, 100])
    @pytest.mark.parametrize("top_p", [0.2, 0.8, 1.0])
    def test_kv_cache_sampling_stability(self, temp: float, top_k: int, top_p: float):
        """Fuzz generation across diverse sampling parameters without crashing or NaNs."""
        args = ModelArgs(vocab_size=260, d_model=32, n_layers=1, n_heads=2, n_kv_heads=2, d_ff=64)
        model = Transformer(args)
        prompt = [4, 5, 6, 7]
        output, metrics = model.generate(
            prompt,
            max_new_tokens=6,
            temperature=temp,
            top_k=top_k,
            top_p=top_p,
            return_metrics=True
        )
        assert len(output) == len(prompt) + 6
        assert metrics["tokens_generated"] == 6
        assert all(isinstance(t, int) for t in output)


# ===========================================================================
# 3. SFT Gradient Backpropagation Challenges under Extreme Masking
# ===========================================================================

class TestSFTGradientChallenges:
    """Adversarial stress-tests challenging SFT loss computation and gradient backpropagation."""

    def test_sft_100_percent_masked_zero_grad_no_nan(self):
        """
        Extreme Case: When 100% of labels are -100 (entire sequence is prompt, zero target),
        compute_sft_loss must return 0.0 without throwing errors, dividing by zero, or producing NaNs.
        """
        B, T, V = 2, 8, 260
        logits = torch.randn(B, T, V, requires_grad=True)
        labels = torch.full((B, T), -100, dtype=torch.long)

        loss, metrics = compute_sft_loss(logits, labels, return_metrics=True)
        assert loss.item() == 0.0
        assert metrics["num_active_tokens"] == 0

        loss.backward()
        assert logits.grad is not None
        assert not torch.isnan(logits.grad).any()
        assert (logits.grad == 0.0).all()

    def test_sft_0_percent_masked_full_gradient_flow(self):
        """
        Extreme Case: When 0% of labels are masked (every token is a target),
        gradients must flow through every model component.
        """
        args = ModelArgs(vocab_size=260, d_model=64, n_layers=2, n_heads=4, n_kv_heads=2, d_ff=128)
        model = Transformer(args)
        model.train()

        tokens = torch.randint(4, 250, (2, 8), dtype=torch.long)
        labels = tokens.clone()  # No -100 masking

        logits, _ = model(tokens)
        loss = compute_sft_loss(logits, labels)
        loss.backward()

        for name, p in model.named_parameters():
            if p.requires_grad:
                assert p.grad is not None, f"Parameter {name} did not receive gradients"
                assert not torch.isnan(p.grad).any(), f"NaN in gradients for {name}"
                assert not torch.isinf(p.grad).any(), f"Inf in gradients for {name}"
                assert p.grad.norm().item() > 0.0, f"Zero gradient norm for {name}"

    def test_sft_single_active_token_gradient_propagation(self):
        """
        Boundary Case: Only 1 token in the sequence is unmasked (the last one).
        Gradients must cleanly backpropagate through all layers without numerical underflow.
        """
        args = ModelArgs(vocab_size=260, d_model=64, n_layers=2, n_heads=4, n_kv_heads=2, d_ff=128)
        model = Transformer(args)
        model.train()

        tokens = torch.randint(4, 250, (1, 16), dtype=torch.long)
        labels = torch.full((1, 16), -100, dtype=torch.long)
        labels[0, -1] = 42  # Exactly 1 target token

        logits, _ = model(tokens)
        loss, metrics = compute_sft_loss(logits, labels, return_metrics=True)
        assert metrics["num_active_tokens"] == 1
        assert loss.item() > 0.0

        loss.backward()
        # Verify gradients reached embeddings and projections
        assert model.tok_embeddings.weight.grad is not None
        assert model.tok_embeddings.weight.grad.norm().item() > 0.0
        assert model.layers[0].attention.q_proj.weight.grad.norm().item() > 0.0
        assert model.layers[0].ffn.w_gate.weight.grad.norm().item() > 0.0
        assert model.norm.weight.grad.norm().item() > 0.0

    @pytest.mark.parametrize("batch_size", [1, 2, 4, 8])
    def test_sft_batch_replicated_loss_invariance(self, batch_size: int):
        """
        Batch scaling oracle: Loss on batch size B=1 replicated B times must equal loss on B=B.
        """
        torch.manual_seed(42)
        logits_single = torch.randn(1, 10, 260)
        labels_single = torch.randint(4, 250, (1, 10))
        labels_single[:, :4] = -100

        loss_single = compute_sft_loss(logits_single, labels_single)

        logits_batched = logits_single.repeat(batch_size, 1, 1)
        labels_batched = labels_single.repeat(batch_size, 1)
        loss_batched = compute_sft_loss(logits_batched, labels_batched)

        assert math.isclose(loss_single.item(), loss_batched.item(), rel_tol=1e-5), (
            f"Batch invariance failed for B={batch_size}: single={loss_single.item()}, batched={loss_batched.item()}"
        )

    def test_sft_optimization_step_loss_decrease(self):
        """Verify that multiple training steps with AdamW decrease loss on a fixed batch."""
        torch.manual_seed(42)
        args = ModelArgs(vocab_size=260, d_model=32, n_layers=1, n_heads=2, n_kv_heads=2, d_ff=64)
        model = Transformer(args)
        optimizer = torch.optim.AdamW(model.parameters(), lr=0.01)

        tokens = torch.randint(4, 250, (2, 8), dtype=torch.long)
        labels = tokens.clone()
        labels[:, :3] = -100

        losses = []
        for _ in range(5):
            model.train()
            optimizer.zero_grad()
            logits, _ = model(tokens)
            loss = compute_sft_loss(logits, labels)
            loss.backward()
            optimizer.step()
            losses.append(loss.item())

        assert losses[-1] < losses[0], f"Loss did not decrease over training steps: {losses}"


# ===========================================================================
# 4. Tokenizer Fuzzing (Unicode, Emojis, Empty Strings, Malformed)
# ===========================================================================

class TestTokenizerFuzzingChallenges:
    """Adversarial stress-tests challenging Tokenizer against complex Unicode, emojis, and malformed inputs."""

    @pytest.fixture
    def tokenizer(self) -> ByteTokenizer:
        return ByteTokenizer()

    @pytest.mark.parametrize("unicode_sample", [
        "Привет, мир! 12345",                    # Cyrillic
        "你好世界，深度学习与大语言模型",        # CJK Chinese
        "こんにちは世界、トランスフォーマー",    # CJK Japanese Katakana/Hiragana
        "مرحبا بالعالم! التعلم العميق",          # Arabic RTL
        "שלום עולם, רשתות נוירונים",            # Hebrew RTL
        "Γειά σου κόσμε! Νευρωνικά δίκτυα",     # Greek
        "∑_{i=1}^N \\int_{-\\infty}^\\infty f(x)dx \\approx \\mathbb{E}[X]", # Math TeX
        "e\u0301 (combining acute)",            # Combining diacritic
        "𓀀 𓀁 𓀂 𓀃 (Ancient Egyptian)",           # 4-byte SMP Ancient Hieroglyphics
        "᚛᚛ᚑᚌᚐᚋ᚜ (Ogham)",                      # Ogham Celtic Script
        "Special accents: é, è, ê, ë, à, ù, ç, ñ, ø, å, ß",
    ])
    def test_tokenizer_multibyte_unicode_fuzzing(self, tokenizer: ByteTokenizer, unicode_sample: str):
        """Asserts 100% exact round-trip preservation on diverse multi-byte Unicode strings."""
        encoded = tokenizer.encode(unicode_sample)
        decoded = tokenizer.decode(encoded)
        assert decoded == unicode_sample, f"Unicode mismatch:\nOriginal: {unicode_sample}\nDecoded : {decoded}"

        # Test inspection API
        info = tokenizer.inspect(unicode_sample)
        assert info["total_bytes"] == len(unicode_sample.encode("utf-8"))
        assert info["total_tokens"] == len(encoded)
        assert info["compression_ratio"] == 1.0

    @pytest.mark.parametrize("emoji_sample", [
        "🚀🔥🤖🧠💡",                           # Single codepoint emojis
        "👨‍👩‍👧‍👦",                                # Family ZWJ sequence (multiple codepoints joined by U+200D)
        "👩🏽‍💻",                                # Technologist + Fitzpatrick skin tone + ZWJ + Laptop
        "🏳️‍🌈",                                # Rainbow flag (White flag + ZWJ + Rainbow)
        "🏳️‍⚧️",                                # Transgender flag
        "🧑🏿‍🦰",                                # Person + dark skin tone + ZWJ + red hair
        "❤️ 💔 💖 ✨ 🎉 🥑 🍕 🍺",            # Miscellaneous symbols & pictographs
    ])
    def test_tokenizer_complex_emoji_sequences(self, tokenizer: ByteTokenizer, emoji_sample: str):
        """Asserts exact round-trip decode of complex multi-codepoint and ZWJ emoji sequences."""
        encoded = tokenizer.encode(emoji_sample)
        decoded = tokenizer.decode(encoded)
        assert decoded == emoji_sample, f"Emoji round-trip mismatch:\nExpected: {emoji_sample}\nGot: {decoded}"

    def test_tokenizer_empty_and_control_characters(self, tokenizer: ByteTokenizer):
        """Test boundary conditions: empty string, control bytes, NULL characters."""
        # Empty string
        assert tokenizer.encode("") == []
        assert tokenizer.decode([]) == ""
        assert tokenizer.inspect("")["total_tokens"] == 0

        # String with special tokens flags
        assert tokenizer.encode("", add_bos=True, add_eos=True) == [tokenizer.bos_id, tokenizer.eos_id]

        # NULL characters and control bytes
        null_str = "\x00\x01\x02\x03\x1f\x7f\t\n\r"
        enc = tokenizer.encode(null_str)
        dec = tokenizer.decode(enc)
        assert dec == null_str

    def test_tokenizer_raw_byte_permutations_fuzzing(self, tokenizer: ByteTokenizer):
        """Fuzz all 256 byte values 0x00..0xFF in arbitrary combinations."""
        all_bytes = bytes(range(256))
        # Direct token translation
        token_ids = [b + tokenizer.byte_offset for b in all_bytes]
        # Decode should not crash even on non-UTF8 combinations due to errors='replace'
        decoded = tokenizer.decode(token_ids)
        assert isinstance(decoded, str)

    def test_tokenizer_malformed_token_ids_resilience(self, tokenizer: ByteTokenizer):
        """Passing out-of-bounds or negative token IDs must degrade gracefully without uncaught exceptions."""
        malformed_ids = [-100, -1, 99999, 1000000]
        # Should decode gracefully without crashing
        res_skip = tokenizer.decode(malformed_ids, skip_special_tokens=True)
        assert res_skip == ""

        res_unk = tokenizer.decode(malformed_ids, skip_special_tokens=False)
        assert "<unk>" in res_unk

    def test_bpe_tokenizer_fuzzing_and_training(self):
        """Stress-test BPE tokenizer merges, training, inspection, and unseen Unicode encoding."""
        corpus = [
            "The quick brown fox jumps over the lazy dog.",
            "Transformer models are powerful architectures for deep learning.",
            "Attention is all you need for sequence modeling.",
            "PyTorch and Apple Silicon MPS unified memory."
        ]
        bpe = BPETokenizer(vocab_size=300)
        bpe.train(corpus, target_vocab_size=300)
        assert bpe.vocab_size <= 300

        test_phrase = "Transformer models are powerful! 🚀"
        encoded = bpe.encode(test_phrase)
        decoded = bpe.decode(encoded)
        assert decoded == test_phrase

        info = bpe.inspect(test_phrase)
        assert info["total_tokens"] == len(encoded)
        assert info["total_bytes"] == len(test_phrase.encode("utf-8"))
        assert len(info["offsets"]) == len(encoded)
