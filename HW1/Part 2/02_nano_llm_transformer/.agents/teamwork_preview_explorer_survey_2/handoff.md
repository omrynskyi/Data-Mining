# Handoff Report: Model Architecture & Primitives (Explorer Survey 2)

## 1. Observation

Directly observed technical requirements from `.agents/ORIGINAL_REQUEST.md`:
- Line 7: *"A rigorous evaluation setup for experimenting with local LLMs, optimized for Apple Silicon (M-series). It features a pure PyTorch autoregressive transformer neural network built entirely from scratch (featuring RoPE, SwiGLU, RMSNorm, SFT)."*
- Line 14-15: *"R1. Custom Transformer Model: Build a pure PyTorch autoregressive transformer from scratch utilizing state-of-the-art primitives including Rotary Position Embeddings (RoPE), SwiGLU gated activations, and RMSNorm. It must support Supervised Fine-Tuning (SFT)."*
- Line 18: *"The dashboard must provide live inspection tools for the model, including KV-cache generation views, attention heatmaps, and tokenizer inspection."*
- Lines 25-27: *"Acceptance Criteria: A programmatic test script (`test_model.py`) runs successfully, initializing the model and verifying that a forward pass produces expected output tensor shapes. The test script verifies that gradients flow through all custom components (RoPE, SwiGLU, RMSNorm) during a mock SFT backward pass."*

## 2. Logic Chain

From the observed requirements, we derive the structural and algorithmic implementation specifics:

1. **Rotary Position Embedding (RoPE)**:
   - **Observation**: Relative positioning must be injected per head without additive positional parameters.
   - **Derivation**: Split head dimension $d_k$ into two halves $(d_k/2)$. Precompute base frequencies $\theta_i = 10000^{-2i/d_k}$. Form rotation angles $\alpha_{pos, i} = pos \cdot \theta_i$. Apply vector rotation:
     $$\text{RoPE}(X) = X \odot \cos(\alpha) + \text{rotate\_half}(X) \odot \sin(\alpha)$$
     where $\text{rotate\_half}([-X_2, X_1])$. This is $100\%$ differentiable and supports single-token step slicing $pos:pos+1$ for KV-cache decoding.

2. **SwiGLU Gated FeedForward Network**:
   - **Observation**: Modern LLMs (LLaMA-3) replace standard GELU FFNs with SwiGLU for enhanced capacity per parameter.
   - **Derivation**: Compute hidden dimension $d_{ff} = \text{round\_up\_64}(\lfloor \frac{8}{3} d_{model} \rfloor)$.
     Compute $\text{FFN}(x) = (\text{SiLU}(x W_{gate}) \odot (x W_{up})) W_{down}$. Setting `bias=False` ensures zero dead weight overhead and optimal MPS tensor execution.

3. **RMSNorm Pre-Normalization**:
   - **Observation**: Stable gradient dynamics without mean-centering overhead.
   - **Derivation**: Normalize each hidden vector by $x / \sqrt{\text{mean}(x^2) + \epsilon}$ and multiply by learnable 1D parameter $\gamma$ (shape: $d_{model}$). Apply in Pre-LN configuration before Attention and FFN, followed by a final RMSNorm before the LM unembedding head.

4. **Multi-Head / Grouped-Query Attention & Explicit KV-Cache**:
   - **Observation**: Must support both full-context parallel forward pass (training/prefill) and $O(1)$ single-token decode steps with live attention weight tensor capture.
   - **Derivation**:
     - *Prefill pass*: Projects $Q, K, V \in (B, n_{heads}, T, d_k)$, applies RoPE across positions $0 \dots T-1$, computes attention scores with causal mask $M \in \{0, -\infty\}$, caches $K, V$.
     - *Generation step*: Inputs $x_{new} \in (B, 1, d_{model})$, projects new $K_{new}, V_{new}$, applies RoPE at position $pos = S$, concatenates to existing cached $K_{cache}, V_{cache}$, performs unmasked cross-attention against the concatenated cache $(B, n_{heads}, 1, S+1)$, and outputs next token logits.
     - *Attention Weights Capture*: Compute `attn_weights = softmax(scores, dim=-1)` with shape $(B, n_{heads}, T_q, T_k)$ and return when `return_attentions=True`.

5. **Pure Python/PyTorch Scratch Tokenizer**:
   - **Observation**: Zero external dependencies, fully inspectable.
   - **Derivation**: Implement a dual-mode tokenizer:
     - Byte-level base tokenizer mapping UTF-8 bytes ($0 \dots 255$) + 4 special tokens (`<pad>=0`, `<bos>=1`, `<eos>=2`, `<unk>=3`) to vocabulary size 260.
     - Optional BPE pair-merging extension to vocabulary size 512 / 1024.
     - Inspection API returning token pieces, IDs, byte lengths, and string offsets for dashboard rendering.

6. **SFT Loss & Gradient Flow Verification**:
   - **Observation**: SFT requires prompt-masked loss and test verification of gradient propagation across all custom components.
   - **Derivation**: Shift logits $Z[:, :-1, :]$ against targets $Y[:, 1:]$. Mask prompt token target indices with $-100$. Compute `F.cross_entropy(..., ignore_index=-100)`. Run `.backward()` and verify $\|p.grad\|_2 > 0$ for all weights in RoPE projections, SwiGLU matrices, RMSNorm scales, and embeddings.

## 3. Caveats

1. **MPS float32 vs float16 precision**: PyTorch MPS handles both float32 and float16/bfloat16. For nano training and gradient checks, float32 is recommended for exact numerical gradient stability and zero underflow in attention softmax.
2. **Attention heatmap tensor retention**: Storing full attention matrices across all layers during training consumes $O(L \cdot H \cdot T^2)$ memory. The `return_attentions=True` flag should only be activated during diagnostic/dashboard inspection passes, not standard high-throughput training.
3. **KV-Cache maximum sequence length**: The precomputed RoPE tables should support at least `max_seq_len` (e.g., 512 or 2048). If generation exceeds this, dynamic frequency computation or RoPE interpolation can be added.

## 4. Conclusion

The model architecture is fully specified as a modular, pure PyTorch library (`nano_transformer/`) with exact mathematical formulations, shape contracts, and zero external dependencies:
- **`nano_transformer/config.py`**: ModelArgs dataclass with preset hyperparameter configurations.
- **`nano_transformer/norm.py`**: `RMSNorm` module.
- **`nano_transformer/rope.py`**: `RotaryEmbedding` helper and `apply_rope` operator.
- **`nano_transformer/ffn.py`**: `SwiGLUFFN` module with 8/3 dimension scaling.
- **`nano_transformer/attention.py`**: `CausalSelfAttention` supporting MHA, GQA, KV-cache, and attention weights extraction.
- **`nano_transformer/block.py`**: `TransformerBlock` with Pre-LN residual streams.
- **`nano_transformer/model.py`**: Full `Transformer` model with generation loop, KV-cache management, and weight tying option.
- **`nano_transformer/tokenizer.py`**: `ByteTokenizer` & `BPETokenizer` with inspection API.
- **`nano_transformer/sft.py`**: SFT dataset formatting, prompt-masking collation, and loss calculation.

## 5. Verification Method

To independently verify the architecture:
1. **Module Unit Tests**: Execute `python -m pytest tests/test_primitives.py` verifying:
   - RoPE rotational symmetry: $\langle \text{RoPE}(q, m), \text{RoPE}(k, n) \rangle = f(m - n)$.
   - SwiGLU forward pass with correct intermediate hidden dimensions.
   - RMSNorm invariance to positive scalar input scaling.
2. **Full Model & Gradient Flow Test**: Run `python test_model.py` to confirm:
   - Forward pass shapes match $(B, T, V)$.
   - Single-step KV-cache generation yields identical logits to full sequence prefill.
   - SFT backward pass produces non-zero gradients across all custom components: `tok_embeddings`, `norm`, `q_proj`, `k_proj`, `v_proj`, `out_proj`, `gate_proj`, `up_proj`, `down_proj`, and `lm_head`.
3. **Tokenizer Round-Trip Test**: Verify `decode(encode(text)) == text` for arbitrary Unicode strings.
