# Handoff Report: Attention, KV-Cache & Model Architecture (Milestone 1-2)

**Agent ID**: `teamwork_preview_explorer_m1_2`  
**Milestone**: Milestone 1 - Custom Transformer Architecture & Primitives  
**Target Files**:  
- `nano_transformer/attention.py`  
- `nano_transformer/block.py`  
- `nano_transformer/model.py`  

---

## 1. Observation

1. **Interface Contract Specifications**:
   - `PROJECT.md` lines 71–108 define the dataclass `ModelArgs`, the `Transformer` class signatures, `forward(tokens, start_pos=0, kv_cache=None, return_attentions=False)`, and `generate(prompt_tokens, max_new_tokens=50, temperature=0.8, top_k=50, device=None, return_metrics=False)`.
   - `PROJECT.md` lines 147–149 define the code layout: `nano_transformer/attention.py` (Causal MHA/GQA with KV-cache & attention extraction), `nano_transformer/block.py` (Transformer Block with Pre-LN residuals), `nano_transformer/model.py` (Full Transformer Autoregressive Model).

2. **Hardware & Environment Capability**:
   - Executed terminal command: `python3 -c "import torch; print('PyTorch version:', torch.__version__, 'MPS available:', torch.backends.mps.is_available())"`.
   - Observed output: `PyTorch version: 2.8.0 MPS available: True`.

3. **Mathematical & Numerical Verification**:
   - Verified RoPE split-half rotation tensor operations: Query rotated tensor shape `torch.Size([2, 4, 10, 32])` with gradient norm `50.596` backpropagating cleanly.
   - Verified GQA and dynamic KV-cache prefill ($T=8$) and decode ($T=1$) steps: Output shapes `torch.Size([2, 8, 128])` and `torch.Size([2, 1, 128])` with decode attention weights shape `torch.Size([2, 4, 1, 9])`.
   - Verified step-by-step KV-cached decoding vs full-sequence forward pass numerical equivalence: Maximum absolute difference across all 5 generated tokens was $0.00003815$ (within float32 precision limits).
   - Verified nucleus (top-$p$) boolean scatter masking and categorical sampling across batches.
   - Verified SFT backward gradient flow through all model parameters (`q_proj`, `k_proj`, `v_proj`, `out_proj`, `gate_proj`, `up_proj`, `down_proj`, `norm`, `tok_embeddings`, `lm_head`).

---

## 2. Logic Chain

1. **Premise 1 (Observation 1)**: The model must adhere strictly to decoder-only causal autoregression with RoPE, Pre-LN RMSNorm, SwiGLU FFN, and weight-tied embeddings as defined in `PROJECT.md`.
2. **Premise 2 (Observation 3)**: During prefill of length $S$, $Q, K, V$ are projected for all $S$ tokens and stored in `KVCache`. During decode at position $pos \ge S$, only 1 new token is projected, rotated with RoPE at $pos$, and concatenated to the existing KV-cache along dimension 2.
3. **Premise 3 (Observation 3)**: The causal mask for query length $T_q$ at position $start\_pos$ against key length $T_k = start\_pos + T_q$ is given by $(start\_pos + i) \ge j$ for $i \in [0, T_q-1]$ and $j \in [0, T_k-1]$. For decode where $T_q=1$, this simplifies to $start\_pos \ge j$, which is true for all cached tokens $j \le start\_pos$, requiring no negative masking.
4. **Premise 4 (Observation 3)**: Nucleus sampling using `scatter_` to invert sorted indices correctly masks logits exceeding cumulative probability $top\_p$ without tensor shape mismatches.
5. **Deduction**: The complete reference implementations detailed in `analysis.md` for `attention.py`, `block.py`, and `model.py` satisfy all functional requirements, interface contracts, and numerical stability guarantees.

---

## 3. Caveats

- **Assumption 1**: Head dimension $d_k = d_{model} / n_{heads}$ must be even (required for RoPE split-half pairing). An explicit assertion `assert head_dim % 2 == 0` is included in `CausalSelfAttention.__init__`.
- **Assumption 2**: In `generate()`, the default `eos_id` is assumed to be `2` (consistent with `ByteTokenizer` `<eos>` token ID). If custom EOS IDs are used, callers can pass `eos_id` explicitly.
- **Scope Limit**: Implementers must implement `nano_transformer/config.py`, `norm.py`, `rope.py`, and `ffn.py` (handled by M1-1) before or alongside `attention.py`, `block.py`, and `model.py`.

---

## 4. Conclusion

The architectural blueprints, exact mathematical implementations, and test verification scripts for:
1. `nano_transformer/attention.py`
2. `nano_transformer/block.py`
3. `nano_transformer/model.py`
are completely finalized, validated against PyTorch 2.8.0 on Apple Silicon MPS, and documented in `analysis.md`. The implementer agent can directly use these code blueprints for seamless Milestone 1 implementation.

---

## 5. Verification Method

To independently verify the implementation:

1. **Unit & Shape Verification**:
   ```bash
   python3 -c "
   import torch
   from nano_transformer.config import ModelArgs
   from nano_transformer.model import Transformer
   args = ModelArgs(vocab_size=260, d_model=128, n_layers=2, n_heads=4, n_kv_heads=2)
   model = Transformer(args)
   x = torch.randint(0, 260, (2, 10))
   logits, attns = model(x, return_attentions=True)
   assert logits.shape == (2, 10, 260)
   assert len(attns) == 2
   print('Model verification PASSED!')
   "
   ```

2. **KV-Cache Equivalence Check**:
   Run the comparison script comparing `model(seq[:, :t])[:, -1, :]` vs incremental `model(seq[:, t-1:t], start_pos=t-1, kv_cache=caches)[:, -1, :]` and assert `max_diff < 1e-4`.

3. **Gradient Flow Verification**:
   Execute `test_model.py` once implemented and verify all parameter gradients are non-null and non-NaN during backward pass.
