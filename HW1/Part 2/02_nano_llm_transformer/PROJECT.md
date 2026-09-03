# Project: Nano LLM Transformer & Data Science Admin Dashboard

## Architecture
A modular, high-performance pure PyTorch autoregressive transformer neural network built from scratch, optimized for Apple Silicon unified memory (MPS), paired with an interactive Data Science Admin Dashboard featuring a CRISP-DM pipeline tracker and live diagnostic visualizers (KV-cache, attention heatmaps, tokenizer inspection).

### Subsystems & Data Flow
1. **Core Model Library (`nano_transformer/`)**:
   - `config.py`: `ModelArgs` configuration dataclass (vocab size, d_model, n_layers, n_heads, n_kv_heads, max_seq_len, etc.).
   - `norm.py`: `RMSNorm` pre-normalization with learnable scaling parameter.
   - `rope.py`: `RotaryEmbedding` computing split-half rotary positional embeddings with precomputed trigonometric frequencies.
   - `ffn.py`: `SwiGLUFFN` with SwiGLU gated activation and $d_{ff} = \text{round\_up\_64}(\lfloor \frac{8}{3} d_{model} \rfloor)$.
   - `attention.py`: `CausalSelfAttention` with Multi-Head / Grouped-Query Attention, dynamic KV-cache management for $O(1)$ decoding, and attention weight extraction.
   - `block.py`: `TransformerBlock` combining RMSNorm, RoPE attention, and SwiGLU FFN with residual connections.
   - `model.py`: `Transformer` autoregressive model with weight tying, prefill & KV-cached single-token decode generation.
   - `tokenizer.py`: Scratch `ByteTokenizer` (and BPE extension) with character/byte mapping and token inspection metadata.
   - `sft.py`: Supervised Fine-Tuning dataset collation, prompt target masking (`ignore_index=-100`), loss computation, and trainer.
   - `device.py`: Hardware device resolver defaulting to Apple Silicon `mps` when available, with memory profiling helpers.

2. **Data Science Admin Dashboard (`dashboard/`)**:
   - `app.py`: FastAPI application serving UI and REST APIs.
   - `crisp_dm.py`: CRISP-DM pipeline state tracker tracking all phases (Business Understanding, Data Understanding, Data Preparation, Modeling, Evaluation, Deployment) with status, duration, metrics, and logs.
   - `inspectors.py`: Handlers for KV-cache generation inspection, multi-head attention heatmap tensor extraction, and tokenizer analysis.
   - `static/` & `templates/`: Interactive, responsive admin dashboard web interface with live visualization widgets.

3. **Hardware Optimization & Benchmarks (`benchmarks/` & Root Scripts)**:
   - `test_model.py`: Acceptance test verifying model instantiation, forward pass output tensor shapes, and SFT backward gradient flow through RoPE, SwiGLU, and RMSNorm.
   - `test_dashboard.py`: Programmatic test verifying local dashboard launch, CRISP-DM state retrieval (>=3 stages), and HTTP 200 GET responses from KV-cache, attention heatmaps, and tokenizer endpoints.
   - `benchmark_mps.py`: Hardware benchmark executing generation on `mps` (if available), logging execution speed, and enforcing unified memory limits ($\le 4.0\text{ GB}$).
   - `run_tests.py`: Comprehensive test runner executing all tier test suites.

---

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| 1 | RoPE Positional Embeddings | Rotary position embeddings with split-half trigonometric rotations and $O(1)$ decoding slice support | M1 | ORIGINAL_REQUEST §R1 |
| 2 | SwiGLU Gated Activation | SwiGLU FFN with SiLU gate and $8/3 \times d_{model}$ dimension scaling | M1 | ORIGINAL_REQUEST §R1 |
| 3 | RMSNorm Pre-Normalization | Root Mean Square layer normalization with learnable scale parameter | M1 | ORIGINAL_REQUEST §R1 |
| 4 | Causal Attention & KV-Cache | Multi-Head / Grouped-Query attention with causal masking, explicit KV-cache, and attention weight extraction | M1 | ORIGINAL_REQUEST §R1, §R2 |
| 5 | Scratch Tokenizer & Inspector | Pure Python byte-level / BPE tokenizer with encode, decode, and inspection metadata | M1 | ORIGINAL_REQUEST §R1, §R2 |
| 6 | Supervised Fine-Tuning (SFT) | Prompt-masked cross entropy loss and end-to-end gradient backprop through all custom primitives | M1 | ORIGINAL_REQUEST §R1 |
| 7 | CRISP-DM Pipeline Tracker | State manager tracking $\ge 3$ stages (Data Preparation, Modeling, Evaluation, etc.) with programmatic API | M2 | ORIGINAL_REQUEST §R2 |
| 8 | KV-Cache Inspection Endpoint | HTTP GET endpoint returning step-by-step KV cache tensor dimensions, allocations, and hit metrics | M2 | ORIGINAL_REQUEST §R2 |
| 9 | Attention Heatmap Endpoint | HTTP GET endpoint returning post-softmax multi-head attention matrix heatmaps across all layers | M2 | ORIGINAL_REQUEST §R2 |
| 10 | Tokenizer Inspection Endpoint | HTTP GET endpoint returning token breakdowns, byte lengths, offsets, and compression ratio | M2 | ORIGINAL_REQUEST §R2 |
| 11 | Interactive Admin Web Dashboard | Rich interactive web interface for real-time visualization of model internals and CRISP-DM workflow | M2 | ORIGINAL_REQUEST §R2 |
| 12 | Apple Silicon (MPS) Auto-Selection | Device resolver automatically selecting `mps` when running on Apple Silicon | M3 | ORIGINAL_REQUEST §R3 |
| 13 | Unified Memory Profiling & Limit Enforcement | Telemetry tracking host RSS and Metal allocated memory with strict $\le 4.0\text{ GB}$ ceiling check | M3 | ORIGINAL_REQUEST §R3 |
| 14 | Model Verification Script (`test_model.py`) | Programmatic acceptance test for model forward pass shapes and SFT backward gradient flow | Test Track / M1 | ORIGINAL_REQUEST §Acceptance Criteria |
| 15 | Dashboard Test Script (`test_dashboard.py`) | Programmatic acceptance test for dashboard endpoints and CRISP-DM stages | Test Track / M2 | ORIGINAL_REQUEST §Acceptance Criteria |
| 16 | MPS Benchmark Script (`benchmark_mps.py`) | Programmatic benchmark verifying MPS device selection, generation throughput, and memory bounds | Test Track / M3 | ORIGINAL_REQUEST §Acceptance Criteria |
| 17 | Comprehensive Multi-Tier E2E Test Suite | Tiers 1-4 opaque-box tests (Feature, Boundary, Combinatorial, Real-World) + Tier 5 Adversarial | Test Track / M_Final | Dual Track Methodology |

---

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M_TEST | E2E Testing Suite & Infrastructure | Test infrastructure, test runner (`run_tests.py`), test cases for Tiers 1-4, `test_model.py`, `test_dashboard.py`, `benchmark_mps.py`, `TEST_INFRA.md`, `TEST_READY.md` | none | COMPLETE |
| M1 | Custom Transformer Architecture & Primitives | Implement `nano_transformer/` (RoPE, SwiGLU, RMSNorm, Attention, KV-Cache, Model, Tokenizer, SFT, Device) and unit tests | none | COMPLETE |
| M2 | Data Science Admin Dashboard & CRISP-DM Tracker | Implement `dashboard/` (FastAPI app, CRISP-DM tracker, KV-cache / attention / tokenizer inspection endpoints, web UI) | M1 | COMPLETE |
| M3 | Hardware Optimization & MPS Profiling | Implement memory profiling, device resolver, benchmark optimizations, and `benchmark_mps.py` execution validation | M1 | COMPLETE |
| M_FINAL | Full E2E Verification & Adversarial Coverage Hardening | Execute 100% of E2E test suite (Tiers 1-4), then run Phase 2 Tier 5 Adversarial Coverage Hardening (Challenger stress tests + Forensic Auditor) | M_TEST, M1, M2, M3 | COMPLETE |

---

## Interface Contracts

### 1. `nano_transformer.config.ModelArgs`
```python
@dataclass
class ModelArgs:
    vocab_size: int = 260
    d_model: int = 128
    n_layers: int = 4
    n_heads: int = 4
    n_kv_heads: Optional[int] = None
    d_ff: Optional[int] = None
    max_seq_len: int = 512
    dropout: float = 0.0
    norm_eps: float = 1e-5
    rope_base: float = 10000.0
    tie_embeddings: bool = True
```

### 2. `nano_transformer.model.Transformer`
```python
class Transformer(nn.Module):
    def __init__(self, args: ModelArgs): ...
    def forward(
        self,
        tokens: torch.Tensor,               # shape: (B, T)
        start_pos: int = 0,
        kv_cache: Optional[List[KVCache]] = None,
        return_attentions: bool = False
    ) -> Tuple[torch.Tensor, Optional[List[torch.Tensor]]]:
        # returns: (logits: (B, T, vocab_size), Optional[List[attn_weights]])
        ...
    def generate(
        self,
        prompt_tokens: List[int],
        max_new_tokens: int = 50,
        temperature: float = 0.8,
        top_k: int = 50,
        device: Optional[torch.device] = None,
        return_metrics: bool = False
    ) -> Union[List[int], Tuple[List[int], Dict[str, Any]]]: ...
```

### 3. `nano_transformer.tokenizer.ByteTokenizer`
```python
class ByteTokenizer:
    def encode(self, text: str) -> List[int]: ...
    def decode(self, tokens: List[int]) -> str: ...
    def inspect(self, text: str) -> Dict[str, Any]:
        # returns: {"tokens": [...], "token_ids": [...], "byte_lengths": [...], "offsets": [...], "compression_ratio": float}
        ...
```

### 4. `dashboard.app` REST Endpoints
- `GET /api/crisp-dm` -> Returns JSON containing stages `{"data_preparation": {...}, "modeling": {...}, "evaluation": {...}, ...}` with statuses, metrics, logs.
- `GET /api/inspect/kv-cache` (or `POST /api/inspect/kv-cache`) -> Returns JSON with step-by-step KV-cache shapes, allocated memory, and hit rate.
- `GET /api/inspect/attention` (or `POST /api/inspect/attention`) -> Returns JSON with attention matrices per layer and head, tokens, and heatmap arrays.
- `GET /api/inspect/tokenizer` -> Returns JSON with token pieces, token IDs, lengths, and compression metrics for sample/input text.
- `GET /api/health` -> `{"status": "healthy", "device": "mps"|"cpu", "mps_available": bool}`
- `GET /` -> Serves the interactive HTML Admin Dashboard.

### 5. `nano_transformer.device`
```python
def resolve_device(preferred: Optional[str] = None) -> torch.device: ...
def get_memory_stats(device: torch.device) -> Dict[str, float]:
    # returns: {"ram_used_gb": float, "ram_total_gb": float, "mps_allocated_gb": float, "mps_driver_gb": float}
    ...
```

---

## Code Layout
```
02_nano_llm_transformer/
├── nano_transformer/           # Core Pure PyTorch Transformer Library
│   ├── __init__.py
│   ├── config.py               # Model hyperparameters dataclass
│   ├── norm.py                 # RMSNorm implementation
│   ├── rope.py                 # Rotary Position Embeddings
│   ├── ffn.py                  # SwiGLU Gated FeedForward Network
│   ├── attention.py            # Causal MHA/GQA with KV-cache & attention extraction
│   ├── block.py                # Transformer Block with Pre-LN residuals
│   ├── model.py                # Full Transformer Autoregressive Model
│   ├── tokenizer.py            # Scratch Byte / BPE Tokenizer with inspection API
│   ├── sft.py                  # SFT dataset collation, prompt masking, and training loop
│   └── device.py               # Apple Silicon MPS device resolver and memory profiler
├── dashboard/                  # Data Science Admin Dashboard
│   ├── __init__.py
│   ├── app.py                  # FastAPI web application & REST routes
│   ├── crisp_dm.py             # CRISP-DM 6-phase pipeline state tracker
│   ├── inspectors.py           # Model inspection service (KV-cache, attention, tokenizer)
│   ├── templates/              # Dashboard HTML templates
│   │   └── index.html          # Interactive CRISP-DM & model visualization UI
│   └── static/                 # Static assets mounted at /static
│       ├── dashboard.css       # Dashboard stylesheet
│       └── dashboard.js        # Dashboard client logic (tabs, polling, heatmaps)
├── tests/                      # Multi-Tier Test Suite
│   ├── test_tier1_features.py  # Tier 1: Feature Coverage (>=5 per feature)
│   ├── test_tier2_boundaries.py# Tier 2: Boundary & Corner Cases (>=5 per feature)
│   ├── test_tier3_combinations.py # Tier 3: Cross-Feature Interactions
│   ├── test_tier4_workloads.py # Tier 4: Real-World Scenarios
│   ├── test_tier5_adversarial_challenge.py    # Tier 5: Core primitive adversarial stress
│   ├── test_tier5_adversarial_crisp_dm.py     # Tier 5: CRISP-DM state machine adversarial
│   ├── test_tier5_adversarial_dashboard.py    # Tier 5: Endpoint hostile-input & concurrency
│   ├── test_tier5_adversarial_mps_memory.py   # Tier 5: Sustained MPS load & memory ceiling
│   └── conftest.py             # Shared fixtures
├── challenge_harness.py        # Standalone empirical adversarial stress engine
├── test_model.py               # Acceptance script: forward shape & SFT gradient backprop
├── test_dashboard.py           # Acceptance script: FastAPI test client endpoint verification
├── benchmark_mps.py            # Acceptance script: MPS generation benchmark & unified memory ceiling
├── run_tests.py                # Comprehensive test runner across all test suites
├── TEST_INFRA.md               # E2E Test Suite Architecture & Coverage Thresholds
├── TEST_READY.md               # Generated once E2E test suite is complete
└── PROJECT.md                  # Project specification & living status document
```

---

## Final Status — 2026-09-02

**All milestones COMPLETE. All acceptance criteria met.**

| Verification | Command | Result |
|--------------|---------|--------|
| Full test suite | `python3 -m pytest tests/ -q` | 432 passed, 0 failed |
| Multi-tier runner | `python3 run_tests.py` | 8/8 suites PASS |
| Model acceptance | `python3 test_model.py` | PASS |
| Dashboard acceptance | `python3 test_dashboard.py` | PASS |
| MPS benchmark | `python3 benchmark_mps.py` | PASS — `mps`, 27.31 tok/s, 0.259 GB peak ≤ 4.0 GB |
| Adversarial harness | `python3 challenge_harness.py` | APPROVE (4/4 challenges) |

Test distribution: Tier 1 (features) · Tier 2 (boundaries) · Tier 3 (combinatorial) ·
Tier 4 (real-world workloads) · Tier 5 (adversarial: 244 core-primitive + 38 subsystem tests).

See `.agents/orchestrator/GATE_STATUS.md` for the full review/challenge/audit gate record.
