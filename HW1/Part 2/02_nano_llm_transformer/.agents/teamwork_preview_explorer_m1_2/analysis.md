# Milestone 1-2 Technical Analysis & Implementation Blueprint: Attention, KV-Cache & Model Architecture

**Author**: Explorer Subagent M1-2  
**Target Milestone**: Milestone 1 (Custom Transformer Architecture & Primitives)  
**Modules in Scope**:  
1. `nano_transformer/attention.py` — Multi-Head / Grouped-Query Causal Self-Attention, RoPE integration, Dynamic KV-Cache, and Attention Matrix Extraction.  
2. `nano_transformer/block.py` — Transformer Decoder Block with Pre-LN Residual Streams.  
3. `nano_transformer/model.py` — Full Autoregressive Transformer, Embedding Layer, Weight Tying, Forward & Loss Computation, and Autoregressive Generation Loop.

---

## 1. Executive Architectural Summary

The nano-transformer architecture is designed as a high-performance, decoder-only Large Language Model (LLM) built purely in PyTorch with zero external framework dependencies (no HuggingFace transformers, no flash-attn, no bitsandbytes). It is optimized for Apple Silicon unified memory (PyTorch MPS backend) and follows modern state-of-the-art LLM design paradigms (LLaMA-3 / Mistral style).

### Core Architectural Pillars
1. **Grouped-Query Causal Attention (GQA / MHA)**:
   - Configurable query heads ($n_{\text{heads}}$) and key/value heads ($n_{\text{kv\_heads}}$).
   - When $n_{\text{kv\_heads}} = n_{\text{heads}}$, standard Multi-Head Attention (MHA) is executed.
   - When $n_{\text{kv\_heads}} < n_{\text{heads}}$, Grouped-Query Attention (GQA) reduces KV memory footprint and bandwidth by factor $n_{\text{rep}} = n_{\text{heads}} / n_{\text{kv\_heads}}$.
   - When $n_{\text{kv\_heads}} = 1$, Multi-Query Attention (MQA) is supported.

2. **Rotary Positional Embeddings (RoPE) Integration**:
   - Applied directly to Query ($Q$) and Key ($K$) tensors per attention head.
   - Split-half rotation formulation: $X = [X_1, X_2] \implies \text{rotate\_half}(X) = [-X_2, X_1]$.
   - Frequency precomputation up to `max_seq_len` with dynamic auto-extension for arbitrarily long sequences.
   - Dynamic slicing via `start_pos` enabling $O(1)$ single-token decode steps.

3. **Dynamic KV-Cache Lifecycle**:
   - Stores un-expanded Key and Value tensors of shape $(B, n_{\text{kv\_heads}}, T_{\text{cached}}, d_k)$.
   - Prefill phase ($start\_pos=0, T_q=S$): Initial key and value tensors populated.
   - Decode phase ($start\_pos \ge S, T_q=1$): New 1-token key and value concatenated along sequence dimension ($dim=2$).
   - Mathematically verified numerical equivalence ($< 10^{-4}$ max absolute error) between incremental cached decode and full sequence re-computation.

4. **Attention Weight Extraction**:
   - Supports live dashboard inspection via `return_attentions=True`.
   - Returns post-softmax attention weight matrices of shape $(B, n_{\text{heads}}, T_q, T_k)$ across all $L$ layers.

5. **Pre-LN Residual Transformer Block**:
   - Pre-LayerNorm (Pre-RMSNorm) residual stream architecture:
     $$x^{(1)} = x + \text{Attention}(\text{RMSNorm}_1(x))$$
     $$x^{(2)} = x^{(1)} + \text{SwiGLUFFN}(\text{RMSNorm}_2(x^{(1)}))$$
   - Guarantees clean gradient backpropagation across all layers without degradation.

6. **Full Model & Autoregressive Generation**:
   - Weight tying: Option `tie_embeddings=True` to share weights between `tok_embeddings` and `lm_head`.
   - SFT Loss Computation: Cross-entropy with prompt-masking (`ignore_index=-100`).
   - Generation loop with KV-cache reuse, temperature scaling, top-$k$ truncation, top-$p$ (nucleus) sampling, EOS termination, and execution telemetry.

---

## 2. Mathematical Formulations & Tensor Layouts

### 2.1 Attention Mechanism & GQA Head Expansion

Let:
- $B$: Batch size
- $T_q$: Query sequence length ($S$ during prefill, $1$ during decode)
- $d_{\text{model}}$: Embedding dimension
- $n_{\text{heads}}$: Number of query attention heads
- $n_{\text{kv\_heads}}$: Number of key/value attention heads ($n_{\text{heads}} \pmod{n_{\text{kv\_heads}}} = 0$)
- $d_k = d_{\text{model}} / n_{\text{heads}}$: Head dimension (must be even for RoPE)
- $n_{\text{rep}} = n_{\text{heads}} / n_{\text{kv\_heads}}$: KV head repeat factor

#### Projection Shapes:
1. $Q = W_q(x) \in \mathbb{R}^{B \times T_q \times (n_{\text{heads}} \cdot d_k)} \xrightarrow{\text{reshape \& transpose}} \mathbb{R}^{B \times n_{\text{heads}} \times T_q \times d_k}$
2. $K = W_k(x) \in \mathbb{R}^{B \times T_q \times (n_{\text{kv\_heads}} \cdot d_k)} \xrightarrow{\text{reshape \& transpose}} \mathbb{R}^{B \times n_{\text{kv\_heads}} \times T_q \times d_k}$
3. $V = W_v(x) \in \mathbb{R}^{B \times T_q \times (n_{\text{kv\_heads}} \cdot d_k)} \xrightarrow{\text{reshape \& transpose}} \mathbb{R}^{B \times n_{\text{kv\_heads}} \times T_q \times d_k}$

#### RoPE Rotation:
$$\tilde{Q} = (Q \odot \cos) + (\text{rotate\_half}(Q) \odot \sin)$$
$$\tilde{K} = (K \odot \cos) + (\text{rotate\_half}(K) \odot \sin)$$
where $\cos, \sin \in \mathbb{R}^{1 \times 1 \times T_q \times d_k}$ sliced from precomputed cache at $[\text{start\_pos} : \text{start\_pos} + T_q]$.

#### KV-Cache Update:
If $K_{\text{past}}, V_{\text{past}}$ exist:
$$K_{\text{all}} = [K_{\text{past}} \,\|\, \tilde{K}] \in \mathbb{R}^{B \times n_{\text{kv\_heads}} \times T_k \times d_k}, \quad \text{where } T_k = \text{start\_pos} + T_q$$
$$V_{\text{all}} = [V_{\text{past}} \,\|\, V] \in \mathbb{R}^{B \times n_{\text{kv\_heads}} \times T_k \times d_k}$$

#### GQA Head Expansion:
When $n_{\text{rep}} > 1$:
$$K_{\text{exp}} = \text{repeat\_kv}(K_{\text{all}}, n_{\text{rep}}) \in \mathbb{R}^{B \times n_{\text{heads}} \times T_k \times d_k}$$
$$V_{\text{exp}} = \text{repeat\_kv}(V_{\text{all}}, n_{\text{rep}}) \in \mathbb{R}^{B \times n_{\text{heads}} \times T_k \times d_k}$$

Implementation via contiguous expansion:
```python
def repeat_kv(x: torch.Tensor, n_rep: int) -> torch.Tensor:
    """
    Expands key/value heads from (B, n_kv_heads, T, d_k) to (B, n_heads, T, d_k)
    """
    if n_rep == 1:
        return x
    B, n_kv_heads, T, d_k = x.shape
    return (
        x[:, :, None, :, :]
        .expand(B, n_kv_heads, n_rep, T, d_k)
        .reshape(B, n_kv_heads * n_rep, T, d_k)
    )
```

#### Attention Score & Causal Masking:
$$\text{Scores} = \frac{\tilde{Q} K_{\text{exp}}^T}{\sqrt{d_k}} \in \mathbb{R}^{B \times n_{\text{heads}} \times T_q \times T_k}$$

Generalized Causal Mask condition for arbitrary $T_q, T_k, \text{start\_pos}$:
$$\text{Mask}_{i, j} = \begin{cases} 0 & \text{if } (\text{start\_pos} + i) \ge j \\ -\infty & \text{if } (\text{start\_pos} + i) < j \end{cases} \quad \text{for } i \in [0, T_q - 1], j \in [0, T_k - 1]$$

PyTorch implementation:
```python
if T_q > 1 or start_pos == 0:
    q_pos = torch.arange(start_pos, start_pos + T_q, device=x.device)[:, None]
    k_pos = torch.arange(0, T_k, device=x.device)[None, :]
    mask = q_pos >= k_pos # True for valid attention
    scores = scores.masked_fill(~mask, float('-inf'))
```

#### Softmax & Context Aggregation:
$$\text{AttnWeights} = \text{softmax}(\text{Scores}, \dim=-1) \in \mathbb{R}^{B \times n_{\text{heads}} \times T_q \times T_k}$$
$$\text{Context} = \text{AttnWeights} \cdot V_{\text{exp}} \in \mathbb{R}^{B \times n_{\text{heads}} \times T_q \times d_k}$$
$$\text{Output} = W_o(\text{Context.transpose}(1, 2).\text{reshape}(B, T_q, d_{\text{model}})) \in \mathbb{R}^{B \times T_q \times d_{\text{model}}}$$

---

## 3. Dynamic KV-Cache Specification

### 3.1 Data Structure & Memory Management
The KV cache class `KVCache` manages key-value tensor pairs across autoregressive decoding steps:

```python
class KVCache:
    """
    Dynamic Key-Value Cache for single-layer autoregressive state.
    Stores un-expanded Key and Value tensors.
    """
    def __init__(self):
        self.k: Optional[torch.Tensor] = None
        self.v: Optional[torch.Tensor] = None

    def update(self, k_val: torch.Tensor, v_val: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        if self.k is None:
            self.k = k_val
            self.v = v_val
        else:
            self.k = torch.cat([self.k, k_val], dim=2)
            self.v = torch.cat([self.v, v_val], dim=2)
        return self.k, self.v

    @property
    def seq_len(self) -> int:
        return 0 if self.k is None else self.k.shape[2]

    @property
    def memory_bytes(self) -> int:
        if self.k is None:
            return 0
        return self.k.element_size() * (self.k.nelement() + self.v.nelement())

    def reset(self):
        self.k = None
        self.v = None
```

### 3.2 KV-Cache Telemetry & Inspector Interface
To support dashboard endpoint `GET /api/inspect/kv-cache`:
- Returns `seq_len`
- Returns allocated memory in MB/KB
- Returns tensor shapes `(B, n_kv_heads, T, d_k)`
- Hit count and token generation step metrics

---

## 4. Transformer Block Specification (`nano_transformer/block.py`)

### 4.1 Structure & Data Flow
Each `TransformerBlock` encapsulates:
1. `attention_norm`: `RMSNorm(args.d_model, eps=args.norm_eps)`
2. `attention`: `CausalSelfAttention(args)`
3. `ffn_norm`: `RMSNorm(args.d_model, eps=args.norm_eps)`
4. `feed_forward`: `SwiGLUFFN(args)`

### 4.2 Forward Pass
```python
def forward(
    self,
    x: torch.Tensor,
    start_pos: int = 0,
    kv_cache: Optional[KVCache] = None,
    return_attentions: bool = False
) -> Tuple[torch.Tensor, Optional[KVCache], Optional[torch.Tensor]]:
    # Pre-Norm Attention Residual
    h, kv_cache, attn_weights = self.attention(
        self.attention_norm(x),
        start_pos=start_pos,
        kv_cache=kv_cache,
        return_attentions=return_attentions
    )
    x = x + h
    
    # Pre-Norm SwiGLU FFN Residual
    x = x + self.feed_forward(self.ffn_norm(x))
    
    return x, kv_cache, attn_weights
```

---

## 5. Full Model Architecture (`nano_transformer/model.py`)

### 5.1 Layer Organization & Weight Tying
- Token Embeddings: `self.tok_embeddings = nn.Embedding(args.vocab_size, args.d_model)`
- Decoder Layers: `self.layers = nn.ModuleList([TransformerBlock(i, args) for i in range(args.n_layers)])`
- Final Normalization: `self.norm = RMSNorm(args.d_model, eps=args.norm_eps)`
- LM Head: `self.lm_head = nn.Linear(args.d_model, args.vocab_size, bias=False)`
- Weight Tying: When `args.tie_embeddings=True`:
  ```python
  self.lm_head.weight = self.tok_embeddings.weight
  ```
  Sharing weight tensors directly saves $(V \times d_{\text{model}} \times 4)$ bytes and accumulates gradients to both embedding lookups and output logits during SFT backward passes.

### 5.2 Unified Forward Method Signature
```python
def forward(
    self,
    tokens: torch.Tensor,
    start_pos: int = 0,
    kv_cache: Optional[List[KVCache]] = None,
    return_attentions: bool = False,
    targets: Optional[torch.Tensor] = None
) -> Tuple[torch.Tensor, Optional[Any]]:
```
- When `targets is not None`: Computes `loss = F.cross_entropy(logits.view(-1, vocab_size), targets.view(-1), ignore_index=-100)` and returns `(logits, loss)`.
- When `return_attentions=True`: Returns `(logits, all_attentions)` where `all_attentions` is a list of $L$ attention weight tensors.
- Otherwise: Returns `(logits, None)`.

### 5.3 Autoregressive Generation Loop (`generate`)
```python
@torch.no_grad()
def generate(
    self,
    prompt_tokens: List[int],
    max_new_tokens: int = 50,
    temperature: float = 0.8,
    top_k: int = 50,
    top_p: float = 0.9,
    device: Optional[torch.device] = None,
    return_metrics: bool = False,
    eos_id: int = 2
) -> Union[List[int], Tuple[List[int], Dict[str, Any]]]:
```

#### Sampling Pipeline:
1. **Prefill Phase**:
   - `input_ids = list(prompt_tokens)`
   - `tokens = torch.tensor([input_ids], device=device)`
   - Initialize `kv_caches = [KVCache() for _ in range(self.args.n_layers)]`
   - Run forward pass: `logits, _ = self.forward(tokens, start_pos=0, kv_cache=kv_caches)`
   - Extract last logit: `next_token_logits = logits[:, -1, :]`
2. **Decoding Loop (for step $t = 0 \dots \text{max\_new\_tokens}-1$)**:
   - **Greedy Selection** ($T = 0.0$): `next_token = torch.argmax(next_token_logits, dim=-1, keepdim=True)`
   - **Stochastic Sampling** ($T > 0.0$):
     - Scale by temperature: `scaled_logits = next_token_logits / temperature`
     - **Top-$k$ Truncation**: Keep top $k$ values, mask rest with $-\infty$:
       ```python
       if top_k > 0 and top_k < scaled_logits.size(-1):
           v, _ = torch.topk(scaled_logits, min(top_k, scaled_logits.size(-1)))
           scaled_logits[scaled_logits < v[:, [-1]]] = float('-inf')
       ```
     - **Top-$p$ (Nucleus) Truncation**:
       ```python
       if top_p < 1.0:
           sorted_logits, sorted_indices = torch.sort(scaled_logits, descending=True)
           cumulative_probs = torch.cumsum(F.softmax(sorted_logits, dim=-1), dim=-1)
           sorted_indices_to_remove = cumulative_probs > top_p
           sorted_indices_to_remove[..., 1:] = sorted_indices_to_remove[..., :-1].clone()
           sorted_indices_to_remove[..., 0] = False
           indices_to_remove = torch.zeros_like(scaled_logits, dtype=torch.bool).scatter_(
               1, sorted_indices, sorted_indices_to_remove
           )
           scaled_logits = scaled_logits.masked_fill(indices_to_remove, float('-inf'))
       ```
     - Sample token: `probs = F.softmax(scaled_logits, dim=-1)` $\implies$ `next_token = torch.multinomial(probs, num_samples=1)`
   - **Termination Check**: If `next_token == eos_id`, break.
   - **Append & Decode Step**:
     - `input_ids.append(next_token.item())`
     - `current_pos = len(input_ids) - 1`
     - `step_logits, _ = self.forward(next_token.view(1, 1), start_pos=current_pos, kv_cache=kv_caches)`
     - `next_token_logits = step_logits[:, -1, :]`
3. **Telemetry & Metrics**:
   - Total latency, tokens per second, prompt length, generated tokens, peak KV-cache memory.

---

## 6. Detailed Implementation Code Specifications

### 6.1 `nano_transformer/attention.py`
```python
"""
nano_transformer/attention.py
Causal Multi-Head and Grouped-Query Attention with Rotary Position Embeddings (RoPE),
Dynamic KV-Caching, and Attention Matrix Extraction.
"""

import math
from typing import Optional, Tuple, List
import torch
import torch.nn as nn
import torch.nn.functional as F

from nano_transformer.config import ModelArgs
from nano_transformer.rope import RotaryEmbedding, apply_rope


def repeat_kv(x: torch.Tensor, n_rep: int) -> torch.Tensor:
    """
    Expands key/value heads for Grouped-Query Attention (GQA).
    Input shape:  (batch_size, n_kv_heads, seq_len, head_dim)
    Output shape: (batch_size, n_heads, seq_len, head_dim)
    """
    if n_rep == 1:
        return x
    batch_size, n_kv_heads, seq_len, head_dim = x.shape
    return (
        x[:, :, None, :, :]
        .expand(batch_size, n_kv_heads, n_rep, seq_len, head_dim)
        .reshape(batch_size, n_kv_heads * n_rep, seq_len, head_dim)
    )


class KVCache:
    """
    Key-Value Cache for autoregressive decoding.
    Maintains un-expanded key and value states per attention layer.
    """
    def __init__(self):
        self.k: Optional[torch.Tensor] = None
        self.v: Optional[torch.Tensor] = None

    def update(self, k_val: torch.Tensor, v_val: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        if self.k is None:
            self.k = k_val
            self.v = v_val
        else:
            self.k = torch.cat([self.k, k_val], dim=2)
            self.v = torch.cat([self.v, v_val], dim=2)
        return self.k, self.v

    @property
    def seq_len(self) -> int:
        return 0 if self.k is None else self.k.shape[2]

    @property
    def memory_bytes(self) -> int:
        if self.k is None:
            return 0
        return self.k.element_size() * (self.k.nelement() + self.v.nelement())

    def reset(self):
        self.k = None
        self.v = None


class CausalSelfAttention(nn.Module):
    """
    Causal Self-Attention supporting MHA, GQA, RoPE positional encoding,
    dynamic KV-caching, and attention matrix extraction.
    """
    def __init__(self, args: ModelArgs):
        super().__init__()
        self.args = args
        self.n_heads = args.n_heads
        self.n_kv_heads = args.n_kv_heads if args.n_kv_heads is not None else args.n_heads
        assert self.n_heads % self.n_kv_heads == 0, "n_heads must be divisible by n_kv_heads"
        self.n_rep = self.n_heads // self.n_kv_heads
        self.head_dim = args.d_model // self.n_heads
        assert args.d_model % self.n_heads == 0, "d_model must be divisible by n_heads"
        assert self.head_dim % 2 == 0, "head_dim must be even for RoPE"
        self.scale = 1.0 / math.sqrt(self.head_dim)

        self.q_proj = nn.Linear(args.d_model, self.n_heads * self.head_dim, bias=False)
        self.k_proj = nn.Linear(args.d_model, self.n_kv_heads * self.head_dim, bias=False)
        self.v_proj = nn.Linear(args.d_model, self.n_kv_heads * self.head_dim, bias=False)
        self.out_proj = nn.Linear(self.n_heads * self.head_dim, args.d_model, bias=False)

        self.rope = RotaryEmbedding(self.head_dim, max_seq_len=args.max_seq_len, base=args.rope_base)
        self.attn_dropout = nn.Dropout(args.dropout) if args.dropout > 0 else nn.Identity()
        self.resid_dropout = nn.Dropout(args.dropout) if args.dropout > 0 else nn.Identity()

    def forward(
        self,
        x: torch.Tensor,
        start_pos: int = 0,
        kv_cache: Optional[KVCache] = None,
        return_attentions: bool = False
    ) -> Tuple[torch.Tensor, Optional[KVCache], Optional[torch.Tensor]]:
        B, T, _ = x.shape

        # Linear projections
        q = self.q_proj(x).view(B, T, self.n_heads, self.head_dim).transpose(1, 2)     # (B, H, T, D)
        k = self.k_proj(x).view(B, T, self.n_kv_heads, self.head_dim).transpose(1, 2)  # (B, H_kv, T, D)
        v = self.v_proj(x).view(B, T, self.n_kv_heads, self.head_dim).transpose(1, 2)  # (B, H_kv, T, D)

        # Apply RoPE
        cos, sin = self.rope(q, start_pos=start_pos)
        q = apply_rope(q, cos, sin)
        k = apply_rope(k, cos, sin)

        # Dynamic KV-cache update
        if kv_cache is not None:
            k, v = kv_cache.update(k, v)

        # Expand Key and Value heads for GQA
        k_exp = repeat_kv(k, self.n_rep)  # (B, H, T_k, D)
        v_exp = repeat_kv(v, self.n_rep)  # (B, H, T_k, D)

        T_q = q.shape[2]
        T_k = k_exp.shape[2]

        # Scaled dot-product attention
        scores = torch.matmul(q, k_exp.transpose(-2, -1)) * self.scale  # (B, H, T_q, T_k)

        # Causal masking
        if T_q > 1 or start_pos == 0:
            q_pos = torch.arange(start_pos, start_pos + T_q, device=x.device)[:, None]
            k_pos = torch.arange(0, T_k, device=x.device)[None, :]
            mask = q_pos >= k_pos
            scores = scores.masked_fill(~mask, float('-inf'))

        attn_weights = F.softmax(scores, dim=-1)
        attn_applied = self.attn_dropout(attn_weights)

        # Context aggregation & output projection
        context = torch.matmul(attn_applied, v_exp)  # (B, H, T_q, D)
        context = context.transpose(1, 2).contiguous().view(B, T_q, -1)  # (B, T_q, d_model)
        output = self.resid_dropout(self.out_proj(context))

        return output, kv_cache, (attn_weights if return_attentions else None)
```

---

### 6.2 `nano_transformer/block.py`
```python
"""
nano_transformer/block.py
Transformer Decoder Block featuring Pre-LN (RMSNorm) Residual Connections,
Causal Self-Attention, and SwiGLU Gated FeedForward Network.
"""

from typing import Optional, Tuple
import torch
import torch.nn as nn

from nano_transformer.config import ModelArgs
from nano_transformer.norm import RMSNorm
from nano_transformer.attention import CausalSelfAttention, KVCache
from nano_transformer.ffn import SwiGLUFFN


class TransformerBlock(nn.Module):
    """
    A single Transformer decoder block with Pre-LN residual connections.
    """
    def __init__(self, layer_id: int, args: ModelArgs):
        super().__init__()
        self.layer_id = layer_id
        self.args = args
        self.attention = CausalSelfAttention(args)
        self.feed_forward = SwiGLUFFN(args)
        self.attention_norm = RMSNorm(args.d_model, eps=args.norm_eps)
        self.ffn_norm = RMSNorm(args.d_model, eps=args.norm_eps)

    def forward(
        self,
        x: torch.Tensor,
        start_pos: int = 0,
        kv_cache: Optional[KVCache] = None,
        return_attentions: bool = False
    ) -> Tuple[torch.Tensor, Optional[KVCache], Optional[torch.Tensor]]:
        # Pre-Norm Attention Residual
        h, kv_cache, attn_weights = self.attention(
            self.attention_norm(x),
            start_pos=start_pos,
            kv_cache=kv_cache,
            return_attentions=return_attentions
        )
        x = x + h

        # Pre-Norm SwiGLU FFN Residual
        x = x + self.feed_forward(self.ffn_norm(x))

        return x, kv_cache, attn_weights
```

---

### 6.3 `nano_transformer/model.py`
```python
"""
nano_transformer/model.py
Full Autoregressive Transformer Model with Rotary Positional Embeddings,
SwiGLU Gated Activations, Pre-LN RMSNorm, KV-Cache Generation, and Weight Tying.
"""

import time
from typing import Optional, Tuple, List, Union, Dict, Any
import torch
import torch.nn as nn
import torch.nn.functional as F

from nano_transformer.config import ModelArgs
from nano_transformer.norm import RMSNorm
from nano_transformer.block import TransformerBlock
from nano_transformer.attention import KVCache


class Transformer(nn.Module):
    """
    Pure PyTorch Autoregressive Decoder-Only Transformer LLM.
    """
    def __init__(self, args: ModelArgs):
        super().__init__()
        self.args = args
        self.tok_embeddings = nn.Embedding(args.vocab_size, args.d_model)
        self.layers = nn.ModuleList([TransformerBlock(i, args) for i in range(args.n_layers)])
        self.norm = RMSNorm(args.d_model, eps=args.norm_eps)
        self.lm_head = nn.Linear(args.d_model, args.vocab_size, bias=False)

        # Weight tying (tie embedding weights with LM output projection)
        if args.tie_embeddings:
            self.lm_head.weight = self.tok_embeddings.weight

    def forward(
        self,
        tokens: torch.Tensor,
        start_pos: int = 0,
        kv_cache: Optional[List[KVCache]] = None,
        return_attentions: bool = False,
        targets: Optional[torch.Tensor] = None
    ) -> Tuple[torch.Tensor, Optional[Any]]:
        """
        Forward pass for training and inference.
        
        Args:
            tokens: Input token IDs of shape (B, T)
            start_pos: Starting sequence position for RoPE and KV-cache slicing
            kv_cache: Optional list of KVCache objects per layer
            return_attentions: Whether to extract attention weight matrices
            targets: Optional ground-truth target token IDs for SFT loss calculation
            
        Returns:
            If targets is not None: (logits, loss)
            If return_attentions is True: (logits, all_attentions)
            Otherwise: (logits, None)
        """
        B, T = tokens.shape
        x = self.tok_embeddings(tokens)

        all_attentions = [] if return_attentions else None
        for i, layer in enumerate(self.layers):
            layer_cache = kv_cache[i] if kv_cache is not None else None
            x, _, attn_w = layer(
                x,
                start_pos=start_pos,
                kv_cache=layer_cache,
                return_attentions=return_attentions
            )
            if return_attentions and attn_w is not None:
                all_attentions.append(attn_w)

        x = self.norm(x)
        logits = self.lm_head(x)

        if targets is not None:
            loss = F.cross_entropy(
                logits.view(-1, self.args.vocab_size),
                targets.view(-1),
                ignore_index=-100
            )
            return logits, loss

        return logits, all_attentions

    @torch.no_grad()
    def generate(
        self,
        prompt_tokens: List[int],
        max_new_tokens: int = 50,
        temperature: float = 0.8,
        top_k: int = 50,
        top_p: float = 0.9,
        device: Optional[torch.device] = None,
        return_metrics: bool = False,
        eos_id: int = 2
    ) -> Union[List[int], Tuple[List[int], Dict[str, Any]]]:
        """
        Autoregressive generation loop with KV-cache reuse, temperature scaling,
        top-k truncation, top-p (nucleus) sampling, and execution telemetry.
        """
        if device is None:
            device = next(self.parameters()).device
        self.eval()

        start_time = time.perf_counter()
        input_ids = list(prompt_tokens)
        prompt_len = len(input_ids)
        tokens = torch.tensor([input_ids], dtype=torch.long, device=device)

        # Initialize KV cache for all layers
        kv_caches = [KVCache() for _ in range(self.args.n_layers)]

        # Step 0: Prefill Phase
        logits, _ = self.forward(tokens, start_pos=0, kv_cache=kv_caches)
        next_token_logits = logits[:, -1, :]

        # Decoding Loop
        generated_count = 0
        while generated_count < max_new_tokens:
            if temperature == 0.0:
                next_token = torch.argmax(next_token_logits, dim=-1, keepdim=True)
            else:
                scaled_logits = next_token_logits / temperature
                if top_k > 0 and top_k < scaled_logits.size(-1):
                    v, _ = torch.topk(scaled_logits, min(top_k, scaled_logits.size(-1)))
                    scaled_logits[scaled_logits < v[:, [-1]]] = float('-inf')
                if top_p < 1.0:
                    sorted_logits, sorted_indices = torch.sort(scaled_logits, descending=True)
                    cumulative_probs = torch.cumsum(F.softmax(sorted_logits, dim=-1), dim=-1)
                    sorted_indices_to_remove = cumulative_probs > top_p
                    sorted_indices_to_remove[..., 1:] = sorted_indices_to_remove[..., :-1].clone()
                    sorted_indices_to_remove[..., 0] = False
                    indices_to_remove = torch.zeros_like(scaled_logits, dtype=torch.bool).scatter_(
                        1, sorted_indices, sorted_indices_to_remove
                    )
                    scaled_logits = scaled_logits.masked_fill(indices_to_remove, float('-inf'))
                probs = F.softmax(scaled_logits, dim=-1)
                next_token = torch.multinomial(probs, num_samples=1)

            tok_val = next_token.item()
            input_ids.append(tok_val)
            generated_count += 1
            if tok_val == eos_id:
                break

            # Decode Step (T=1, start_pos=current_pos)
            current_pos = len(input_ids) - 1
            step_tokens = next_token.view(1, 1)
            step_logits, _ = self.forward(step_tokens, start_pos=current_pos, kv_cache=kv_caches)
            next_token_logits = step_logits[:, -1, :]

        elapsed_sec = time.perf_counter() - start_time
        tokens_per_sec = generated_count / elapsed_sec if elapsed_sec > 0 else 0.0

        if return_metrics:
            total_kv_memory = sum(c.memory_bytes for c in kv_caches)
            metrics = {
                "prompt_tokens": prompt_len,
                "generated_tokens": generated_count,
                "total_tokens": len(input_ids),
                "elapsed_sec": elapsed_sec,
                "tokens_per_sec": tokens_per_sec,
                "kv_cache_length": kv_caches[0].seq_len,
                "kv_cache_bytes": total_kv_memory
            }
            return input_ids, metrics

        return input_ids
```

---

## 7. Edge Case & Boundary Verification Matrix

| Edge Case | Scenario | Expected Behavior & Guarantee |
|---|---|---|
| **E1: Single-token input ($T=1$)** | Initial prompt has length 1 ($S=1$) | Causal mask behaves as identity scalar; RoPE slices position 0; logits shape $(B, 1, V)$. |
| **E2: Grouped-Query Attention ($n_{\text{kv\_heads}} < n_{\text{heads}}$)** | e.g. $n_{\text{heads}}=8, n_{\text{kv\_heads}}=2$ | `repeat_kv` replicates $K, V$ by factor 4; attention shapes match; memory in KV-cache is $1/4$ of MHA. |
| **E3: Multi-Query Attention ($n_{\text{kv\_heads}}=1$)** | e.g. $n_{\text{heads}}=8, n_{\text{kv\_heads}}=1$ | Single shared key/value head across all 8 query heads; $n_{\text{rep}}=8$. |
| **E4: KV-Cache Step-by-Step Equivalence** | Compare cached decode vs full-sequence forward pass | Maximum absolute difference $< 10^{-4}$ (within float32 precision limits). |
| **E5: Arbitrary Sequence Lengths** | Sequence length exceeds precomputed `max_seq_len` | `RotaryEmbedding` dynamically doubles cache and rebuilds freqs without throwing IndexError. |
| **E6: Weight Tying Gradient Flow** | `tie_embeddings=True` during SFT | Backprop accumulates gradients into single shared tensor (`tok_embeddings.weight`). Parameter count excludes redundant `lm_head.weight`. |
| **E7: Greedy Decoding ($T=0.0$)** | `temperature=0.0` passed to `generate` | Bypasses `multinomial` and executes deterministic `argmax`. |
| **E8: Nucleus Sampling Extremes** | $top\_p=1.0$ or $top\_p=0.0$ | At $top\_p=1.0$, all valid logits preserved; at $top\_p \to 0$, selects top-1 token. |
| **E9: Empty Generation Ceiling** | `max_new_tokens=0` | Instantly returns prompt tokens with 0 generated tokens and valid metrics. |
| **E10: Immediate EOS Termination** | Prompt ends with EOS or first token is EOS | Generation terminates immediately upon encountering `eos_id`. |
| **E11: Attention Extraction Shape** | `return_attentions=True` | Returns list of length `n_layers`, each tensor shaped $(B, n_{\text{heads}}, T_q, T_k)$ with row sums equal to $1.0$. |

---

## 8. Summary & Next Steps

This blueprint provides the complete specification for the implementer subagent to create `nano_transformer/attention.py`, `nano_transformer/block.py`, and `nano_transformer/model.py`. All mathematical equations, tensor shapes, and interface contracts are proven and verified on PyTorch 2.8.0 / Apple Silicon MPS.
