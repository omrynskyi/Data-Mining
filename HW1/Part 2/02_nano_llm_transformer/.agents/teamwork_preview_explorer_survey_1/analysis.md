# Environment & Workspace Technical Survey Analysis

**Date**: 2026-09-02  
**Target Workspace**: `/Users/oleg/Documents/Coding/SJSU/Data Mining/HW1/Part 2/02_nano_llm_transformer`  
**Explorer**: Explorer Survey 1 (Environment & Workspace)

---

## 1. Executive Summary

This survey establishes the complete runtime and hardware environment for building the **Nano LLM Transformer** project. All essential machine learning, web server, and testing dependencies are already installed and fully operational. PyTorch 2.8.0 has verified Apple Silicon Metal Performance Shaders (MPS) hardware acceleration, and the system possesses 32GB of unified memory with Apple M1 Pro silicon.

---

## 2. Hardware and Operating System Specifications

| Parameter | Value | Verification Source |
|---|---|---|
| **SoC / Chip** | Apple M1 Pro | `machdep.cpu.brand_string` |
| **CPU Cores** | 10 physical / 10 logical cores | `psutil.cpu_count()` |
| **Unified Memory** | 32.00 GB (34,359,738,368 bytes) | `sysctl hw.memsize` / `psutil` |
| **Available RAM** | ~8.40 GB | `psutil.virtual_memory().available` |
| **Operating System** | macOS 26.3.1 (Build 25D2128) | `sw_vers` |
| **GPU / Acceleration** | Apple Metal Performance Shaders (`mps:0`) | `torch.backends.mps.is_available()` |

---

## 3. Python Runtime & Package Inventory

The active default Python environment invoked by `python3` is `/usr/bin/python3` (Python 3.9.6) with user-site packages located at `/Users/oleg/Library/Python/3.9/lib/python/site-packages`.

### Package Status Matrix

| Category | Package | Version | Status | Notes |
|---|---|---|---|---|
| **Deep Learning** | `torch` | `2.8.0` | ✅ Installed & Verified | MPS backend built and available; tensor allocation tested |
| **Vision / DL Utils** | `torchvision` | `0.23.0` | ✅ Installed | Available |
| **Numerical / Data** | `numpy` | `1.26.4` | ✅ Installed | Core tensor/array operations |
| **Scientific Computing**| `scipy` | `1.13.1` | ✅ Installed | Math/statistical routines |
| **DataFrames** | `pandas` | `2.3.3` | ✅ Installed | Tabular data manipulation |
| **Testing** | `pytest` | `8.3.4` | ✅ Installed | `python3 -m pytest` ready |
| **Web Framework** | `fastapi` | `0.115.6` | ✅ Installed | Primary framework for admin dashboard |
| **ASGI Server** | `uvicorn` | `0.34.0` | ✅ Installed | High-performance server for FastAPI |
| **ASGI Toolkit** | `starlette` | `0.41.3` | ✅ Installed | Used under FastAPI |
| **Alternative Web** | `flask` | `3.1.3` | ✅ Installed | WSGI alternative |
| **Validation / Schemas**| `pydantic` | `2.10.4` | ✅ Installed | Request/response data models |
| **Plotting / Graphics** | `matplotlib` | `3.9.4` | ✅ Installed | Heatmap / chart rendering |
| **System Profiling** | `psutil` | `7.2.2` | ✅ Installed | RSS & CPU memory tracking |
| **HTTP Clients** | `httpx` | `0.28.1` | ✅ Installed | ASGI TestClient support / async requests |
| **HTTP Clients** | `requests` | `2.32.5` | ✅ Installed | Synchronous test client requests |
| **Templating** | `jinja2` | `3.1.6` | ✅ Installed | HTML dashboard template rendering |
| **Tokenization** | `tiktoken` | `0.12.0` | ✅ Installed | Fast BPE tokenizer library |
| **Tokenization** | `tokenizers` | `0.22.2` | ✅ Installed | HuggingFace tokenizers |
| **Transformers** | `transformers` | `4.57.6` | ✅ Installed | HuggingFace transformers |
| **Progress / CLI** | `tqdm` | `4.67.3` | ✅ Installed | Training and generation progress bars |

---

## 4. PyTorch & Apple Silicon MPS Capabilities

PyTorch 2.8.0 includes native support for Apple Silicon Metal acceleration:
- `torch.backends.mps.is_built()`: **`True`**
- `torch.backends.mps.is_available()`: **`True`**
- Memory tracking APIs verified:
  - `torch.mps.current_allocated_memory()`
  - `torch.mps.driver_allocated_memory()`
  - `torch.mps.empty_cache()`
  - `torch.mps.synchronize()`

### Verified MPS Code Snippet
```python
import torch

device = torch.device("mps" if torch.backends.mps.is_available() else "cpu")
x = torch.randn(1000, 1000, device=device)
y = x @ x
torch.mps.synchronize()
allocated = torch.mps.current_allocated_memory()  # returns allocated bytes
```

---

## 5. Network & Port Allocation

- **Port 8000**: In use by another system process.
- **Port 8080**: Available (recommended default for dashboard).
- **Port 8008 / 8501 / 8888**: Available.
- **Recommendation**: Configure dashboard to default to `8080` (or allow environment variable `PORT` / dynamic port binding in pytest test suites).

---

## 6. Workspace Layout & Existing Files

- Current directory `/Users/oleg/Documents/Coding/SJSU/Data Mining/HW1/Part 2/02_nano_llm_transformer` contains only `.agents/`.
- Clean slate ready for module layout.

---

## 7. Recommended Architectural Blueprint for Nano LLM Project

Based on the requirements in `ORIGINAL_REQUEST.md`:

```
02_nano_llm_transformer/
├── model/
│   ├── __init__.py
│   ├── config.py             # Model dataclass config (d_model, n_heads, n_layers, vocab_size, max_seq_len, etc.)
│   ├── rmsnorm.py            # Custom RMSNorm implementation from scratch
│   ├── rope.py               # Custom Rotary Position Embedding (RoPE) implementation
│   ├── swiglu.py             # Custom SwiGLU feed-forward gated activation block
│   ├── attention.py          # Multi-Head Causal Self-Attention with KV-cache & RoPE integration
│   ├── transformer_block.py  # Transformer Decoder block combining RMSNorm, Attention, SwiGLU
│   ├── nano_transformer.py   # Full Autoregressive Transformer with SFT loss computation
│   └── tokenizer.py          # Character-level / BPE / Byte tokenizer with inspection metadata
├── sft/
│   ├── __init__.py
│   ├── dataset.py            # SFT dataset formatter with prompt masking and target labels
│   └── trainer.py            # Supervised Fine-Tuning trainer loop with gradient tracking
├── dashboard/
│   ├── __init__.py
│   ├── app.py                # FastAPI dashboard backend
│   ├── crisp_dm.py           # CRISP-DM 6-stage pipeline tracker state manager
│   ├── inspector.py          # KV-cache, Attention heatmap, Tokenizer inspector service
│   ├── templates/            # Interactive HTML dashboard with charts and live widgets
│   └── static/               # CSS/JS styling and visualization scripts
├── hardware/
│   ├── __init__.py
│   ├── memory_tracker.py     # MPS unified memory monitor & profiler (psutil + torch.mps)
│   └── device_utils.py       # Device resolution (MPS/CPU) and allocation helpers
├── tests/
│   ├── __init__.py
│   ├── test_model.py         # R1 acceptance: forward shapes & gradient flow across RoPE, SwiGLU, RMSNorm
│   ├── test_dashboard.py     # R2 acceptance: HTTP GET 200 OK for kv-cache, attention, tokenizer, CRISP-DM
│   └── test_hardware.py      # R3 acceptance: MPS device defaults & memory limit validation
├── benchmark_mps.py          # Programmatic benchmark script measuring tokens/sec, latency, memory limit
├── run_dashboard.py          # CLI runner for launching interactive admin dashboard
├── requirements.txt          # Minimal requirements listing pre-installed packages
└── README.md                 # Documentation, architectural guide, and usage instructions
```

---

## 8. Requirements Traceability

1. **R1 (Custom Transformer Model)**:
   - Built with pure PyTorch in `model/`.
   - Explicit modules for `RoPE`, `SwiGLU`, `RMSNorm`.
   - Full SFT loss computation masking prompts and backpropagating target tokens.
   - Verified via `test_model.py` and `pytest tests/test_model.py`.

2. **R2 (Data Science Admin Dashboard)**:
   - FastAPI + Uvicorn backend with rich interactive HTML/JS UI.
   - Endpoints `/api/kv-cache`, `/api/attention-heatmaps`, `/api/tokenizer`, `/api/crisp-dm`.
   - CRISP-DM tracker maintaining 6 standard stages (Business Understanding, Data Understanding, Data Preparation, Modeling, Evaluation, Deployment).
   - Verified via programmatic test script `tests/test_dashboard.py`.

3. **R3 (Hardware Optimization)**:
   - Default to `mps` device when available with CPU fallback.
   - KV-cache reuse during autoregressive generation to avoid redundant computation.
   - Memory tracking with assertions (< 4GB unified memory limit).
   - Programmatic benchmark in `benchmark_mps.py` and `tests/test_hardware.py`.
