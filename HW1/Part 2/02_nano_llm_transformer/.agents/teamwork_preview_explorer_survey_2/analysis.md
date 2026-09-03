# Pure PyTorch Autoregressive Transformer: Architectural & Mathematical Specification

## 1. Executive Summary & Architectural Overview

This document provides the foundational engineering specification for building a pure PyTorch autoregressive transformer neural network entirely from scratch (zero external LLM dependencies such as HuggingFace `transformers`, `flash-attn`, or `bitsandbytes`).

The model is optimized for execution on Apple Silicon (M-series unified memory via PyTorch MPS backend) and adheres to modern state-of-the-art decoder-only LLM architecture (LLaMA-3 / Mistral style):
- **Rotary Position Embeddings (RoPE)**: Applied to Query and Key projections per head.
- **SwiGLU Gated Activations**: Dimension-scaled FFN with SiLU gate and elementwise product.
- **RMSNorm**: Root Mean Square Layer Normalization with learnable scale vector and no additive bias.
- **Grouped-Query Attention (GQA) & Multi-Head Attention (MHA)**: Configurable head-to-KV ratio for memory-bandwidth efficiency.
- **Explicit KV-Cache**: First-class generation mechanism supporting both prefill and $O(1)$ single-token decode steps.
- **Attention Heatmap Extraction**: Native instrumentation yielding attention weight tensors across all layers and heads for dashboard visualization.
- **Scratch Tokenizer Engine**: Byte-level / BPE tokenizer with sub-token segmentation, inspection metadata, and vocabulary management.
- **Supervised Fine-Tuning (SFT) Engine**: Cross-entropy with prompt-masking (`ignore_index=-100`) and comprehensive gradient flow verification.

---

## 2. Rotary Position Embeddings (RoPE)

### 2.1 Mathematical Formulation
RoPE (Su et al., 2021) encodes relative position information by rotating query and key representations in the complex plane (or 2D orthogonal subspaces) rather than adding static position vectors.

For a head dimension $d_k$ (where $d_k$ is even), the frequency basis $\Theta = \{\theta_i\}$ for $i \in \{0, 1, \dots, d_k/2 - 1\}$ is defined as:
$$\theta_i = \theta_{\text{base}}^{-2i / d_k}, \quad \text{typically } \theta_{\text{base}} = 10000.0$$

For a token at position index $m \in \{0, \dots, T-1\}$, the rotation angles are:
$$\alpha_{m, i} = m \cdot \theta_i \in \mathbb{R}^{T \times (d_k/2)}$$

### 2.2 Tensor Operations (Split-Half Formulation)
Given a query or key tensor $X \in \mathbb{R}^{B \times H \times T \times d_k}$:
1. Split $X$ along the feature dimension into two equal halves:
   $$X = [X_1, X_2], \quad X_1, X_2 \in \mathbb{R}^{B \times H \times T \times (d_k/2)}$$
2. Define the orthogonal half-rotation operator:
   $$\text{rotate\_half}(X) = [-X_2, X_1]$$
3. Expand $\cos(\alpha)$ and $\sin(\alpha)$ from $(T, d_k/2)$ by duplicating across the feature dimension to shape $(1, 1, T, d_k)$:
   $$\cos\_emb = [\cos(\alpha), \cos(\alpha)], \quad \sin\_emb = [\sin(\alpha), \sin(\alpha)]$$
4. Compute the rotated tensor:
   $$\text{RoPE}(X, m) = (X \odot \cos\_emb) + (\text{rotate\_half}(X) \odot \sin\_emb)$$

### 2.3 Precomputed Cache and Slicing
To avoid recomputing trigonometric functions during every forward pass:
- Precompute $\cos\_emb$ and $\sin\_emb$ up to `max_seq_len` (e.g. 2048) during model initialization.
- Register them as non-persistent buffers in the module.
- During training / prefill ($T$ tokens starting at position 0): slice `cos_emb[:, :, :T, :]` and `sin_emb[:, :, :T, :]`.
- During autoregressive decoding (1 token at position $pos$): slice `cos_emb[:, :, pos:pos+1, :]` and `sin_emb[:, :, pos:pos+1, :]`.

---

## 3. SwiGLU Gated Activation & FeedForward Network (FFN)

### 3.1 Mathematical Formulation
Standard FFN uses a 2-matrix transformation: $\text{FFN}(x) = \text{GELU}(x W_1) W_2$.
SwiGLU (Shazeer, 2020) uses a 3-matrix gated architecture:
$$\text{SwiGLU}(x) = \left( \text{SiLU}(x W_{\text{gate}}) \odot (x W_{\text{up}}) \right) W_{\text{down}}$$
where $\text{SiLU}(z) = z \cdot \sigma(z) = \frac{z}{1 + e^{-z}}$.

### 3.2 Dimension Scaling
Because SwiGLU uses three weight matrices instead of two, to maintain parameter parity with standard transformer FFNs ($d_{ff} = 4 d_{model}$), the hidden dimension is scaled by $\frac{2}{3}$:
$$d_{ff} = \text{round\_up\_to\_multiple}\left(\left\lfloor \frac{8}{3} d_{model} \right\rfloor, 64\right)$$

**Concrete Calculation**:
```python
def find_multiple(n: int, multiple: int = 64) -> int:
    return ((n + multiple - 1) // multiple) * multiple

hidden_dim = int(2 * (4 * d_model) / 3)
d_ff = find_multiple(hidden_dim, 64)
```

### 3.3 Tensor Dimensions
- Input $x$: $(B, T, d_{model})$
- Gate projection $W_{\text{gate}}$: $(d_{model}, d_{ff}) \to (B, T, d_{ff})$
- Up projection $W_{\text{up}}$: $(d_{model}, d_{ff}) \to (B, T, d_{ff})$
- Gated state: $\text{SiLU}(\text{Gate}) \odot \text{Up} \to (B, T, d_{ff})$
- Down projection $W_{\text{down}}$: $(d_{ff}, d_{model}) \to (B, T, d_{model})$
- Biases: `bias=False` across all linear layers for modern parameter efficiency.

---

## 4. RMSNorm (Root Mean Square Layer Normalization)

### 4.1 Mathematical Formulation
RMSNorm (Zhang & Sennrich, 2019) normalizes activations strictly by their root mean square statistic without subtracting the mean:
$$\text{RMS}(x) = \sqrt{\frac{1}{d_{model}} \sum_{i=1}^{d_{model}} x_i^2 + \epsilon}$$
$$y_i = \frac{x_i}{\text{RMS}(x)} \cdot \gamma_i$$
where $\gamma \in \mathbb{R}^{d_{model}}$ is a learnable gain vector initialized to $\mathbf{1}$, and $\epsilon = 10^{-5}$ is the numerical stabilization epsilon.

### 4.2 PyTorch Tensor Implementation
```python
class RMSNorm(nn.Module):
    def __init__(self, dim: int, eps: float = 1e-5):
        super().__init__()
        self.eps = eps
        self.weight = nn.Parameter(torch.ones(dim))

    def _norm(self, x: torch.Tensor) -> torch.Tensor:
        return x * torch.rsqrt(x.pow(2).mean(-1, keepdim=True) + self.eps)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        output = self._norm(x.float()).type_as(x)
        return output * self.weight
```

### 4.3 Pre-Norm Architecture
Modern decoder blocks apply RMSNorm before each sub-layer (Pre-LN formulation) to ensure clean residual gradient propagation:
$$x^{(1)} = x + \text{Attention}(\text{RMSNorm}_1(x))$$
$$x^{(2)} = x^{(1)} + \text{FeedForward}(\text{RMSNorm}_2(x^{(1)}))$$
A final $\text{RMSNorm}_{\text{final}}$ is applied to the output of the last transformer block prior to projection into vocabulary logits.

---

## 5. Attention Mechanism & Explicit KV-Cache Mechanics

### 5.1 Multi-Head (MHA) & Grouped-Query Attention (GQA)
- Number of Query heads: $n_{\text{heads}}$
- Number of Key/Value heads: $n_{\text{kv\_heads}}$ ($n_{\text{kv\_heads}} \le n_{\text{heads}}$ and $n_{\text{heads}} \pmod{n_{\text{kv\_heads}}} = 0$)
- Head dimension: $d_k = d_{model} / n_{\text{heads}}$
- KV repeat factor: $n_{\text{rep}} = n_{\text{heads}} / n_{\text{kv\_heads}}$

If $n_{\text{rep}} > 1$, Keys and Values are expanded across heads before computing attention:
```python
def repeat_kv(x: torch.Tensor, n_rep: int) -> torch.Tensor:
    """(B, n_kv_heads, T, d_k) -> (B, n_heads, T, d_k)"""
    if n_rep == 1:
        return x
    B, n_kv_heads, T, d_k = x.shape
    return (
        x[:, :, None, :, :]
        .expand(B, n_kv_heads, n_rep, T, d_k)
        .reshape(B, n_kv_heads * n_rep, T, d_k)
    )
```

### 5.2 Explicit KV-Cache Lifecycle
The KV-cache stores computed Key and Value tensors across generation steps to eliminate redundant computations:

```
Step 0 (Prefill with Prompt of length S):
  Input: x_0:S -> Q (S, d_k), K (S, d_k), V (S, d_k)
  Store in cache: K_cache = K, V_cache = V  [Shape: (B, n_kv_heads, S, d_k)]
  Mask: Causal Lower-Triangular Mask (S x S)
  Output: logits for token S

Step 1 (Generate 1 token at pos S):
  Input: x_new (1, d_model) -> Q_new (1, d_k), K_new (1, d_k), V_new (1, d_k)
  RoPE applied to Q_new, K_new at pos=S
  Update Cache: K_cache = cat([K_cache, K_new], dim=2) -> (B, n_kv_heads, S+1, d_k)
                V_cache = cat([V_cache, V_new], dim=2) -> (B, n_kv_heads, S+1, d_k)
  Mask: None (Q at pos S can attend to all tokens 0..S)
  Scores: (Q_new @ K_cache.T) / sqrt(d_k) -> Shape (B, n_heads, 1, S+1)
  Output: logits for token S+1
```

### 5.3 Attention Weights Extraction for Inspection
To support live attention heatmaps on the dashboard:
- Attention layer computes:
  $$\text{attn\_weights} = \text{softmax}\left(\frac{Q K^T}{\sqrt{d_k}} + \text{mask}, \dim=-1\right)$$
- Shape: $(B, n_{\text{heads}}, T_q, T_k)$
- When `return_attention_weights=True`, the layer returns `(output, past_kv, attn_weights)`.
- The parent model aggregates attention weights into a tuple across all $N_{\text{layers}}$:
  $$\text{all\_attentions} = (\text{weights}_0, \text{weights}_1, \dots, \text{weights}_{N-1})$$

---

## 6. Tokenizer from Scratch

### 6.1 Dual Tokenizer Design (Byte-Level & Simple BPE)
To ensure 100% pure Python/PyTorch execution with zero external tokenizer libraries:

1. **Byte-Level Tokenizer (Base Engine)**:
   - Maps raw UTF-8 bytes ($0 \dots 255$) directly to token IDs.
   - Special Tokens:
     - `<pad>`: ID 0
     - `<bos>`: ID 1
     - `<eos>`: ID 2
     - `<unk>`: ID 3
   - Byte IDs: $b \to b + 4$ (IDs $4 \dots 259$).
   - Total base vocabulary size: $V_{\text{base}} = 260$.
   - **Properties**: 100% out-of-vocabulary immunity, deterministic round-trip encoding/decoding, transparent byte inspection.

2. **Byte-Pair Encoding (BPE) Extension**:
   - Trains from byte vocabulary by scanning text corpus and iteratively merging the most frequent adjacent pair:
     $$(t_a, t_b) \to t_{\text{new}} \quad (\text{ID } \ge 260)$$
   - Target vocabulary size: e.g. $512, 1024, \text{ or } 2048$.
   - Serialized to JSON (`vocab.json` and `merges.json` / `tokenizer.json`).

### 6.2 Tokenizer Inspection API for Dashboard
The tokenizer provides detailed inspection metadata for the frontend:
```python
class TokenizerInspectionResult:
    tokens: list[str]       # Display representation (e.g. ['<bos>', 'H', 'e', 'l', 'l', 'o'])
    token_ids: list[int]    # Numeric IDs [1, 76, 105, 112, 112, 115]
    byte_lengths: list[int] # Length in bytes of each token
    offsets: list[tuple[int, int]] # Character span (start, end) in original string
```

---

## 7. Supervised Fine-Tuning (SFT) & Loss Calculation

### 7.1 Causal Shift & Target Masking
In autoregressive modeling, the prediction for position $t$ is the token at position $t+1$.
In SFT, the prompt tokens must not contribute to the loss gradient.

Given an input sequence $X = [p_0, p_1, \dots, p_{k-1}, r_0, r_1, \dots, r_{m-1}]$:
- Input to model: $X_{input} = X[:-1]$ (tokens $0 \dots k+m-2$)
- Target labels: $Y_{target} = X[1:]$ (tokens $1 \dots k+m-1$)
- Label masking:
  $$Y_{\text{masked}}[t] = \begin{cases} -100 & \text{if } t < k - 1 \quad (\text{prompt tokens}) \\ X[t+1] & \text{if } t \ge k - 1 \quad (\text{response tokens}) \end{cases}$$

### 7.2 Loss Formulation
$$\mathcal{L}_{\text{SFT}}(\theta) = -\frac{1}{\sum_{t} \mathbb{I}(Y_t \neq -100)} \sum_{t: Y_t \neq -100} \log P_\theta(Y_t \mid X_{\le t})$$
Implemented via:
```python
loss = F.cross_entropy(
    logits.view(-1, vocab_size),
    targets.view(-1),
    ignore_index=-100
)
```

### 7.3 Gradient Flow Verification Plan
The test suite (`test_model.py`) executes a synthetic SFT step and asserts:
1. `loss.backward()` computes gradients for all parameters.
2. $\forall p \in \text{model.parameters()}$, $p.\text{grad}$ is NOT None and $\neg \text{isnan}(p.\text{grad}.\text{sum}())$ and $\|p.\text{grad}\|_2 > 0$.
3. Specific checks on:
   - RoPE input projections (`q_proj.weight`, `k_proj.weight`)
   - SwiGLU projections (`gate_proj.weight`, `up_proj.weight`, `down_proj.weight`)
   - RMSNorm gain vectors (`norm.weight`)
   - Token embedding table (`tok_embeddings.weight`)
   - Language model head (`lm_head.weight`)

---

## 8. Model Configuration & Memory Budget (Apple Silicon MPS)

### 8.1 Nano-LLM Hyperparameter Preset
| Parameter | Value | Rationale |
|---|---|---|
| `vocab_size` | 512 (or 260 for pure byte) | Lightweight, fast convergence |
| `dim` ($d_{model}$) | 256 | High representational capacity for nano model |
| `n_layers` | 6 | Sufficient depth for non-trivial causal reasoning |
| `n_heads` | 8 | Head dimension $d_k = 256 / 8 = 32$ |
| `n_kv_heads` | 4 (GQA) or 8 (MHA) | 2:1 GQA grouping or 1:1 MHA |
| `d_ff` (SwiGLU) | 682 $\to$ 704 (rounded to 64) | $\approx \frac{8}{3} \times 256 = 682.6$ |
| `max_seq_len` | 512 | Context window for homework & benchmark tasks |
| `norm_eps` | $10^{-5}$ | RMSNorm numerical stability |
| `rope_base` | $10000.0$ | RoPE frequency base |

### 8.2 Parameter Count & Memory Estimation
- Embedding: $512 \times 256 = 131,072$ params
- Per Layer:
  - Attention: $W_q(256 \times 256) + W_k(256 \times 128) + W_v(256 \times 128) + W_o(256 \times 256) = 196,608$ params
  - SwiGLU FFN: $W_{\text{gate}}(256 \times 704) + W_{\text{up}}(256 \times 704) + W_{\text{down}}(704 \times 256) = 540,672$ params
  - RMSNorms: $2 \times 256 = 512$ params
  - Layer Total: $737,792$ params
- 6 Layers Total: $4,426,752$ params
- Final Norm + LM Head: $256 + 256 \times 512 = 131,328$ params
- **Total Model Parameters**: $\approx 4.69 \text{ Million}$ params
- **Memory Footprint (FP32)**: $\approx 18.8 \text{ MB}$
- **Peak Training Memory (Batch 8, Seq 256)**: $< 250 \text{ MB}$ (well under the 4GB MPS constraint)

---

## 9. Modular Interface Contracts

### 9.1 Model Module Hierarchy
```
nano_transformer/
├── __init__.py
├── config.py             # ModelArgs dataclass
├── tokenizer.py          # ByteTokenizer & SimpleBPETokenizer
├── norm.py               # RMSNorm
├── rope.py               # RotaryEmbedding & apply_rope
├── ffn.py                # SwiGLUFFN
├── attention.py          # CausalSelfAttention (MHA/GQA + KV-Cache)
├── block.py              # TransformerBlock (Pre-Norm Pre-SwiGLU)
├── model.py              # Transformer (Decoder-only LLM + generation)
└── sft.py                # SFTDataset, collate_sft, train_sft_step
```

### 9.2 Forward Signature
```python
def forward(
    self,
    tokens: torch.Tensor,                # (B, T)
    targets: Optional[torch.Tensor] = None, # (B, T)
    kv_cache: Optional[list[tuple[torch.Tensor, torch.Tensor]]] = None,
    start_pos: int = 0,
    return_attentions: bool = False
) -> tuple[torch.Tensor, Optional[torch.Tensor], Optional[list], Optional[list]]:
    """
    Returns:
        logits: (B, T, vocab_size)
        loss: Optional scalar cross-entropy loss
        new_kv_cache: Optional list of (key, value) per layer
        all_attentions: Optional list of (B, n_heads, T_q, T_k) per layer
    """
```
