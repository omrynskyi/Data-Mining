# Explorer Survey 3: Dashboard Architecture, Live Model Inspection, & Apple Silicon MPS Hardware Optimization

## 1. Executive Summary & Problem Scope

This report provides the technical design, architectural specifications, API contracts, hardware optimization strategies, and test harness definitions for:
1. **Data Science Admin Dashboard with Interactive CRISP-DM Pipeline Tracker** (R2): Tracking the complete end-to-end data mining lifecycle across all standard phases (specifically guaranteeing at least 3 stages: *Data Preparation*, *Modeling*, and *Evaluation*) with full programmatic state inspection.
2. **Live Model Inspection Tools** (R2): Real-time interactive diagnostics including:
   - **KV-Cache Generation View**: Tracking step-by-step Key-Value cache growth, memory allocation, and token generation traces.
   - **Multi-Head Attention Heatmaps**: Extracting and rendering post-softmax causal attention matrices across model layers and heads.
   - **Tokenizer Inspector**: Visualizing subword/BPE token boundaries, token IDs, byte representations, and compression ratios.
3. **Hardware Optimization for Apple Silicon (M-series Mac) Unified Memory** (R3):
   - Leveraging Metal Performance Shaders (`mps`) with automatic fallback to `cpu`.
   - Real-time unified memory tracking via `torch.mps.current_allocated_memory()`, `torch.mps.driver_allocated_memory()`, and `psutil`.
   - Memory guardrails (strict $\le 4.0\text{ GB}$ ceiling for nano model benchmarks) and precision management (FP32/FP16/BF16).
4. **Programmatic Test Scripts & Benchmarking Harnesses**:
   - `test_model.py`: Verifying forward output tensor shapes `(B, T, V)` and end-to-end gradient flow through RoPE, SwiGLU, and RMSNorm in mock SFT.
   - `test_dashboard.py` / dashboard test suite: Programmatic HTTP verification of UI and all inspection endpoints returning HTTP 200 OK with valid structured JSON/HTML payloads.
   - `benchmark_mps.py`: Automated performance and memory benchmark asserting MPS device selection and memory limit adherence.

---

## 2. CRISP-DM Pipeline Tracker Architecture

### 2.1 CRISP-DM Phase Mapping for Nano LLM
The Cross-Industry Standard Process for Data Mining (CRISP-DM) maps directly to the Nano LLM lifecycle across 6 structured stages:

| CRISP-DM Stage | Nano LLM Mapping | Tracked State & Artifacts | Programmatic Status Values |
| :--- | :--- | :--- | :--- |
| **1. Business Understanding** | Problem Formulation & Compute Budget | Model hyperparams ($d_{\text{model}}$, $n_{\text{layers}}$, $n_{\text{heads}}$, context window $T_{\text{max}}$), target perplexity, 4GB memory ceiling | `not_started`, `running`, `completed`, `failed` |
| **2. Data Understanding** | Dataset Profiling & Distribution | Raw text corpus statistics (character count, vocabulary distribution, sequence length histogram, entropy) | `not_started`, `running`, `completed`, `failed` |
| **3. Data Preparation** | Tokenization & Batch Tensorization | BPE/subword tokenizer training, train/val/test token split, PyTorch `DataLoader` creation, context chunking | `not_started`, `running`, `completed`, `failed` |
| **4. Modeling** | Scratch Transformer & SFT Training | Model weights instantiation (RoPE, SwiGLU, RMSNorm), forward pass, SFT cross-entropy loss, optimizer step, gradient norms | `not_started`, `running`, `completed`, `failed` |
| **5. Evaluation** | Loss, Perplexity & Generation Quality | Validation loss curve, validation perplexity ($\text{PPL} = \exp(\mathcal{L})$), qualitative generation samples, KV-cache efficiency | `not_started`, `running`, `completed`, `failed` |
| **6. Deployment** | Live Inspection & API Serving | Dashboard web server startup, live KV-cache endpoint, attention heatmap inspector, MPS benchmark execution | `not_started`, `running`, `completed`, `failed` |

*Acceptance Criteria Note*: The system explicitly guarantees tracking of at least 3 stages (*Data Preparation*, *Modeling*, and *Evaluation*), while providing full 6-stage lifecycle support.

### 2.2 Programmatic State Machine Design
The CRISP-DM tracker is implemented as an in-memory state manager with atomic state updates, metric logging, and REST inspection endpoints.

#### State Data Model (`CrispDMState`):
```python
from enum import Enum
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
import time

class StageStatus(str, Enum):
    NOT_STARTED = "not_started"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"

class StageInfo(BaseModel):
    id: str
    name: str
    order: int
    status: StageStatus = StageStatus.NOT_STARTED
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    duration_seconds: Optional[float] = None
    metrics: Dict[str, Any] = Field(default_factory=dict)
    artifacts: Dict[str, Any] = Field(default_factory=dict)
    logs: List[str] = Field(default_factory=list)

class CrispDMTrackerState(BaseModel):
    current_stage: str
    active_pipeline: bool
    stages: Dict[str, StageInfo]
    updated_at: float
```

#### CRISP-DM REST API Endpoints:
1. `GET /api/crisp-dm`
   - **Description**: Returns the full state of the CRISP-DM pipeline, including all stages, current active stage, statuses, metrics, and timestamps.
   - **Response Code**: `200 OK`
   - **JSON Response Format**:
     ```json
     {
       "status": "ok",
       "current_stage": "modeling",
       "active_pipeline": true,
       "stages": {
         "data_preparation": {
           "id": "data_preparation",
           "name": "Data Preparation",
           "order": 3,
           "status": "completed",
           "duration_seconds": 1.42,
           "metrics": {
             "total_tokens": 1048576,
             "vocab_size": 1024,
             "train_split_ratio": 0.9,
             "batch_size": 16,
             "block_size": 256
           },
           "artifacts": {
             "tokenizer_type": "bpe",
             "train_tokens_count": 943718,
             "val_tokens_count": 104858
           },
           "logs": ["Tokenizer trained", "Dataloaders initialized"]
         },
         "modeling": {
           "id": "modeling",
           "name": "Modeling (Transformer + SFT)",
           "order": 4,
           "status": "running",
           "duration_seconds": 12.8,
           "metrics": {
             "step": 200,
             "train_loss": 2.145,
             "learning_rate": 0.0003,
             "grad_norm": 0.82,
             "params_count": 12450816
           },
           "artifacts": {
             "architecture": "CustomTransformer(RoPE, SwiGLU, RMSNorm)"
           },
           "logs": ["Step 100: loss=2.45", "Step 200: loss=2.145"]
         },
         "evaluation": {
           "id": "evaluation",
           "name": "Evaluation",
           "order": 5,
           "status": "not_started",
           "duration_seconds": null,
           "metrics": {},
           "artifacts": {},
           "logs": []
         }
       },
       "updated_at": 1772644935.12
     }
     ```

2. `POST /api/crisp-dm/stage/{stage_id}/transition`
   - **Description**: Programmatically transitions a stage status (e.g., from `not_started` to `running`, or `running` to `completed`) and records metrics/artifacts.
   - **Request Body**: `{"status": "completed", "metrics": {"val_loss": 1.95, "perplexity": 7.03}}`
   - **Response Code**: `200 OK`

---

## 3. Live Model Inspection Tools & Endpoints

### 3.1 KV-Cache Live Generation Inspector

#### Theoretical Foundation:
In standard autoregressive decoding without KV-cache, generating token $t+1$ given prompt of length $T$ requires computing attention over all $t$ tokens at each step, yielding $O(T^2)$ time complexity.
With Key-Value Caching:
- Keys and Values for past tokens are cached in GPU/MPS memory:
  $$\mathbf{K}_{\text{cached}} \in \mathbb{R}^{B \times H_{\text{kv}} \times t \times d_{\text{head}}}, \quad \mathbf{V}_{\text{cached}} \in \mathbb{R}^{B \times H_{\text{kv}} \times t \times d_{\text{head}}}$$
- At decode step $t+1$, only the query for the new token $\mathbf{q}_{t+1}$ is projected, and new key/value $\mathbf{k}_{t+1}, \mathbf{v}_{t+1}$ are appended to the cache:
  $$\mathbf{K}_{\text{new}} = [\mathbf{K}_{\text{cached}}; \mathbf{k}_{t+1}], \quad \mathbf{V}_{\text{new}} = [\mathbf{V}_{\text{cached}}; \mathbf{v}_{t+1}]$$
- Time complexity per step drops from $O(t)$ to $O(1)$ computation per layer.
- Memory consumption of KV-cache:
  $$\text{Memory}_{\text{bytes}} = 2 \times n_{\text{layers}} \times B \times n_{\text{heads\_kv}} \times T_{\text{cache}} \times d_{\text{head}} \times \text{sizeof(dtype)}$$

#### Endpoint Specification:
- **Route**: `GET /api/inspect/kv-cache` and `POST /api/inspect/kv-cache`
- **Query / Body Parameters**:
  - `prompt` (string, default: `"The quick brown fox"`): Input text prompt.
  - `max_new_tokens` (int, default: `10`): Number of autoregressive steps to roll out.
  - `temperature` (float, default: `1.0`): Sampling temperature.
- **Response Status**: `200 OK`
- **Response JSON Schema**:
  ```json
  {
    "status": "ok",
    "prompt": "The quick brown fox",
    "generated_text": " jumps over the lazy dog in the field",
    "num_layers": 6,
    "num_heads": 6,
    "head_dim": 64,
    "total_cached_tokens": 15,
    "memory_footprint_bytes": 46080,
    "memory_footprint_formatted": "45.00 KB",
    "steps": [
      {
        "step_idx": 0,
        "token_id": 542,
        "token_str": " jumps",
        "prefill": true,
        "cache_seq_len": 5,
        "cache_shape_per_layer": [1, 6, 5, 64],
        "step_latency_ms": 1.82,
        "step_memory_allocated_bytes": 15360
      },
      {
        "step_idx": 1,
        "token_id": 918,
        "token_str": " over",
        "prefill": false,
        "cache_seq_len": 6,
        "cache_shape_per_layer": [1, 6, 6, 64],
        "step_latency_ms": 0.41,
        "step_memory_allocated_bytes": 18432
      }
    ],
    "layer_summaries": [
      {
        "layer_idx": 0,
        "k_norm": 1.024,
        "v_norm": 0.982,
        "cache_tensor_shape": [1, 6, 15, 64]
      }
    ]
  }
  ```

---

### 3.2 Attention Heatmaps Inspector

#### Theoretical Foundation:
For an input sequence $\mathbf{X} = (x_1, \dots, x_T)$, Multi-Head Causal Self-Attention computes:
$$\mathbf{S}_{l, h} = \frac{\mathbf{Q}_{l, h} \mathbf{K}_{l, h}^T}{\sqrt{d_{\text{head}}}} + \mathbf{M}$$
$$\mathbf{A}_{l, h} = \text{softmax}(\mathbf{S}_{l, h}, \text{dim}=-1) \in [0, 1]^{T \times T}$$
where $\mathbf{M}_{i, j} = 0 \text{ if } i \ge j \text{ else } -\infty$ (strictly causal / lower triangular).

#### Endpoint Specification:
- **Route**: `GET /api/inspect/attention` and `POST /api/inspect/attention`
- **Query / Body Parameters**:
  - `prompt` (string, default: `"To be or not to be"`): Sequence to analyze.
  - `layer_idx` (int, default: `0`): Layer index to inspect ($0 \le l < n_{\text{layers}}$).
  - `head_idx` (int, default: `0`): Attention head index ($0 \le h < n_{\text{heads}}$).
- **Response Status**: `200 OK`
- **Response JSON Schema**:
  ```json
  {
    "status": "ok",
    "prompt": "To be or not to be",
    "tokens": ["To", " be", " or", " not", " to", " be"],
    "token_ids": [45, 120, 89, 214, 110, 120],
    "seq_len": 6,
    "num_layers": 6,
    "num_heads": 6,
    "selected_layer": 0,
    "selected_head": 0,
    "causal_validity": true,
    "attention_matrix": [
      [1.0, 0.0, 0.0, 0.0, 0.0, 0.0],
      [0.62, 0.38, 0.0, 0.0, 0.0, 0.0],
      [0.31, 0.24, 0.45, 0.0, 0.0, 0.0],
      [0.21, 0.19, 0.15, 0.45, 0.0, 0.0],
      [0.48, 0.12, 0.08, 0.11, 0.21, 0.0],
      [0.18, 0.52, 0.05, 0.07, 0.09, 0.09]
    ],
    "head_metrics": {
      "average_entropy": 1.28,
      "diagonal_dominance": 0.35,
      "sparsity": 0.50
    }
  }
  ```

---

### 3.3 Tokenizer Inspector

#### Theoretical Foundation:
Byte-level Byte-Pair Encoding (BPE) compresses variable-length UTF-8 character sequences into an integer vocabulary:
$$\text{Input String} \xrightarrow{\text{UTF-8 bytes}} [b_1, b_2, \dots] \xrightarrow{\text{Iterative Merge}} [t_1, t_2, \dots, t_K]$$
Compression ratio:
$$\rho_{\text{compression}} = \frac{\text{len(raw UTF-8 bytes)}}{K_{\text{tokens}}}$$

#### Endpoint Specification:
- **Route**: `GET /api/inspect/tokenizer` and `POST /api/inspect/tokenizer`
- **Query / Body Parameters**:
  - `text` (string, default: `"Hello, Apple Silicon M-series transformer!"`): Input text.
- **Response Status**: `200 OK`
- **Response JSON Schema**:
  ```json
  {
    "status": "ok",
    "text": "Hello, Apple Silicon M-series transformer!",
    "vocab_size": 1024,
    "token_count": 8,
    "char_count": 42,
    "byte_count": 42,
    "compression_ratio": 5.25,
    "tokens": [
      {
        "index": 0,
        "token_id": 1542,
        "token_str": "Hello",
        "raw_bytes": [72, 101, 108, 108, 111],
        "char_start": 0,
        "char_end": 5
      },
      {
        "index": 1,
        "token_id": 44,
        "token_str": ",",
        "raw_bytes": [44],
        "char_start": 5,
        "char_end": 6
      }
    ],
    "round_trip_match": true
  }
  ```

---

## 4. Hardware Optimization for Apple Silicon (M-series Mac)

### 4.1 Unified Memory Architecture (UMA) on Apple Silicon
Apple Silicon (M1/M2/M3/M4) features Unified Memory Architecture (UMA):
- **Physical Shared Bus**: CPU, GPU (Apple Metal cores), and Neural Engine share high-bandwidth LPDDR5/LPDDR5X memory (e.g. 100GB/s to 800GB/s).
- **Metal Performance Shaders (MPS)**: PyTorch maps tensor operations onto Metal compute kernels.
- **MPS Memory Allocator**: PyTorch maintains an internal caching allocator on top of the Metal device heap.

### 4.2 PyTorch MPS Management & Fallback APIs
1. **Device Selection & Detection**:
   ```python
   import torch

   def resolve_device(requested: str = "mps") -> torch.device:
       """
       Resolves device with Apple Silicon MPS priority and automatic CPU fallback.
       """
       if requested.lower() == "mps":
           if torch.backends.mps.is_available() and torch.backends.mps.is_built():
               return torch.device("mps")
           return torch.device("cpu")
       elif requested.lower() == "cuda" and torch.cuda.is_available():
           return torch.device("cuda")
       return torch.device("cpu")
   ```

2. **Memory Footprint Tracking APIs**:
   - `torch.mps.current_allocated_memory()`: Returns current memory allocated by PyTorch MPS in bytes.
   - `torch.mps.driver_allocated_memory()`: Returns total memory allocated by the Metal driver heap.
   - `torch.mps.empty_cache()`: Explicitly releases unused caching blocks back to the OS.
   - `torch.mps.synchronize()`: Blocks until all submitted MPS kernels complete (mandatory for high-precision latency profiling).
   - `psutil.Process().memory_info().rss`: Current OS Resident Set Size (RSS).
   - `psutil.virtual_memory()`: System-wide RAM metrics (`total`, `available`, `percent`).

### 4.3 Hardware Memory Telemetry Endpoint:
- **Route**: `GET /api/hardware/memory`
- **Response Status**: `200 OK`
- **Response JSON Schema**:
  ```json
  {
    "status": "ok",
    "device_type": "mps",
    "mps_available": true,
    "mps_built": true,
    "platform": "macOS-26.3.1-arm64",
    "mps_allocated_bytes": 12582912,
    "mps_allocated_mb": 12.0,
    "mps_driver_bytes": 25165824,
    "mps_driver_mb": 24.0,
    "process_rss_bytes": 205520896,
    "process_rss_mb": 196.0,
    "system_ram_total_gb": 32.0,
    "system_ram_available_gb": 8.3,
    "unified_memory_limit_gb": 4.0,
    "within_memory_budget": true
  }
  ```

### 4.4 Precision & Memory Budget Considerations
- **FP32 vs FP16 vs BF16**:
  - `torch.float32`: 4 bytes/element. Baseline stability, full MPS kernel coverage.
  - `torch.float16`: 2 bytes/element. 50% memory reduction for model weights and KV-cache; accelerated via Apple Silicon FP16 ALUs.
  - `torch.bfloat16`: Supported on newer macOS/PyTorch versions with wider dynamic range.
- **Predefined Memory Ceiling**:
  - For tiny / nano LLMs ($10\text{M} - 50\text{M}$ parameters), total model weights + KV-cache + activations consume $< 500\text{ MB}$.
  - The benchmark and dashboard enforce a hard ceiling of **$\le 4.0\text{ GB}$**, preventing accidental runaway memory leaks or driver crashes.

---

## 5. Dashboard Web Application Architecture

### 5.1 Technology Stack
- **Backend**: FastAPI (`fastapi==0.115.6`, `uvicorn==0.34.0`, `pydantic>=2.0`)
- **Frontend**: Responsive Single-Page Application (SPA) with modern CSS grid, dark theme, interactive SVG/HTML5 canvas charts, dynamic stage inspection, live KV-cache step explorer, and attention heatmap visualizer.
- **Client/Testing**: `fastapi.testclient.TestClient` / `requests` / `httpx`.

### 5.2 Complete Dashboard Route Map
| Route | Method | Payload / Query | Output | Purpose |
| :--- | :--- | :--- | :--- | :--- |
| `/` | `GET` | None | HTML (text/html) | Interactive Data Science Admin Dashboard UI |
| `/dashboard` | `GET` | None | HTML (text/html) | Alias to root UI |
| `/api/health` | `GET` | None | JSON | Health check & uptime |
| `/api/crisp-dm` | `GET` | None | JSON | Full CRISP-DM 6-stage tracker state |
| `/api/crisp-dm/stage/{stage_id}` | `GET` | `stage_id` | JSON | Single stage state & detailed metrics/artifacts |
| `/api/crisp-dm/stage/{stage_id}/transition` | `POST` | JSON body | JSON | Transition stage status & append logs/metrics |
| `/api/inspect/kv-cache` | `GET`, `POST` | `prompt`, `max_new_tokens` | JSON | Live KV-cache generation step inspector |
| `/api/inspect/attention` | `GET`, `POST` | `prompt`, `layer_idx`, `head_idx` | JSON | Multi-head attention matrix inspector |
| `/api/inspect/tokenizer` | `GET`, `POST` | `text` | JSON | Tokenizer breakdown & compression inspector |
| `/api/hardware/memory` | `GET` | None | JSON | Apple Silicon MPS & UMA memory telemetry |
| `/api/generate` | `POST` | `prompt`, `max_tokens`, `use_cache` | JSON | Autoregressive text generation endpoint |

---

## 6. Programmatic Test Scripts & Benchmark Specifications

### 6.1 `test_model.py` Specification
`test_model.py` must be a standalone executable script (`python test_model.py`) as well as fully compatible with `pytest test_model.py`.

#### Required Verification Checks:
1. **Architecture Initialization**:
   - Initializes `NanoLLMTransformer` with RoPE, SwiGLU, RMSNorm.
   - Verifies layer counts, attention heads, embedding dimension.
2. **Forward Pass Shape Verification**:
   - Forward pass with input tensor of shape `(batch_size, seq_len)` returns logits tensor of shape `(batch_size, seq_len, vocab_size)`.
   - Forward pass with `return_attention=True` returns attention weights matching `(batch_size, n_layers, n_heads, seq_len, seq_len)`.
3. **KV-Cache Generation Verification**:
   - Verifies that incremental autoregressive generation using KV-cache matches forward pass outputs and adheres to step-by-step tensor cache growth.
4. **Gradient Flow Verification (Mock SFT Backward Pass)**:
   - Sets up mock input tokens and target labels.
   - Computes Cross-Entropy loss.
   - Executes `loss.backward()`.
   - Asserts that all trainable parameters have non-None, finite gradients (`param.grad is not None` and `torch.isfinite(param.grad).all()`).
   - Specifically checks:
     - Embedding weights
     - RoPE frequency projections / Q, K, V linear projections
     - SwiGLU `w1` (gate), `w2` (up), `w3` (down) projections
     - RMSNorm gamma parameters
     - Final LM head weights

---

### 6.2 Dashboard Test Script (`tests/test_dashboard.py`) Specification
A programmatic test script launching the dashboard via `TestClient` or local server socket to verify all endpoints return HTTP 200 OK.

#### Required Verification Checks:
1. `test_ui_endpoint()`: `GET /` returns status 200 and `text/html` containing dashboard title and tabs.
2. `test_crisp_dm_pipeline_state()`: `GET /api/crisp-dm` returns status 200, contains at least 3 stages (`data_preparation`, `modeling`, `evaluation`), each with status, metrics, and duration.
3. `test_kv_cache_endpoint()`: `GET /api/inspect/kv-cache` and `POST /api/inspect/kv-cache` return status 200, valid JSON with `steps`, `layer_summaries`, and `memory_footprint_bytes`.
4. `test_attention_endpoint()`: `GET /api/inspect/attention` and `POST /api/inspect/attention` return status 200, valid JSON with `tokens`, `attention_matrix` (2D square array matching sequence length), and `causal_validity == True`.
5. `test_tokenizer_endpoint()`: `GET /api/inspect/tokenizer` and `POST /api/inspect/tokenizer` return status 200, valid JSON with `tokens`, `token_ids`, and `compression_ratio > 0`.
6. `test_hardware_memory_endpoint()`: `GET /api/hardware/memory` returns status 200, reports `mps_available`, `process_rss_mb`, and `within_memory_budget == True`.

---

### 6.3 `benchmark_mps.py` Specification
A standalone CLI benchmarking script (`python benchmark_mps.py`) executing text generation benchmarks and memory validation.

#### Benchmark Protocol:
1. **Device Selection**:
   - Detects `torch.backends.mps.is_available()`.
   - Automatically selects `mps` if available, defaults gracefully to `cpu`.
   - Logs device name and Metal capabilities.
2. **Warm-up Phase**:
   - Runs 3 warmup generation passes to initialize Metal shader pipelines.
3. **Generation Benchmark**:
   - Runs text generation with KV-cache for $N$ tokens (e.g. 50 tokens, batch size 1).
   - Runs text generation without KV-cache for comparison.
   - Measures:
     - Time to First Token (TTFT, ms)
     - Inter-Token Latency (ITL, ms/token)
     - Generation Throughput (tokens/second)
     - Speedup ratio ($\text{Throughput}_{\text{KV}} / \text{Throughput}_{\text{NoKV}}$)
4. **Memory Profiling & Limit Assertion**:
   - Measures initial memory, peak allocated memory (`torch.mps.current_allocated_memory()`), and process RSS.
   - **Hard Assertion**:
     ```python
     peak_memory_gb = peak_allocated_bytes / (1024 ** 3)
     assert peak_memory_gb <= 4.0, f"Memory exceeded limit: {peak_memory_gb:.2f}GB > 4.0GB"
     ```
5. **Output**:
   - Formatted terminal summary table.
   - JSON report export (e.g. `benchmark_report.json`).

---

## 7. Recommended Directory Structure

```
/Users/oleg/Documents/Coding/SJSU/Data Mining/HW1/Part 2/02_nano_llm_transformer/
├── src/
│   ├── __init__.py
│   ├── model/
│   │   ├── __init__.py
│   │   ├── transformer.py       # Custom Transformer (RoPE, SwiGLU, RMSNorm, KV-Cache)
│   │   ├── components.py        # RoPE, SwiGLU, RMSNorm modular implementations
│   │   ├── tokenizer.py         # BPE / Subword Tokenizer
│   │   └── sft.py               # Supervised Fine-Tuning trainer & dataset
│   ├── dashboard/
│   │   ├── __init__.py
│   │   ├── app.py               # FastAPI Admin Dashboard Application
│   │   ├── crisp_dm.py          # CRISP-DM Pipeline Tracker & State Manager
│   │   ├── inspectors.py        # KV-Cache, Attention, Tokenizer live extractors
│   │   ├── hardware.py          # Apple Silicon MPS & Unified Memory profiler
│   │   ├── static/              # CSS, JS assets
│   │   └── templates/           # Jinja2 HTML templates
│   └── hardware/
│       ├── __init__.py
│       └── mps_utils.py         # Device selection, memory tracking, synchronization
├── tests/
│   ├── __init__.py
│   ├── test_model_arch.py       # Detailed unit tests for components
│   ├── test_dashboard_api.py    # Detailed API endpoint tests
│   └── test_hardware_mps.py     # Hardware memory assertions
├── test_model.py                # Root verification script for Acceptance Criteria 1
├── test_dashboard.py            # Root verification script for Acceptance Criteria 2
├── benchmark_mps.py             # Root benchmark script for Acceptance Criteria 3
├── run_dashboard.py             # CLI runner for launching dashboard locally
└── README.md
```
