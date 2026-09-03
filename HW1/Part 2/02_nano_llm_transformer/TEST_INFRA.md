# Test Infrastructure & E2E Verification Specification

## 1. Testing Philosophy & Principles

The Nano LLM Transformer & Data Science Admin Dashboard project requires a rigorous, multi-tiered test infrastructure designed around the following foundational principles:

1. **Zero External LLM Dependencies**: All tests run against our pure PyTorch autoregressive transformer neural network built entirely from scratch without HuggingFace `transformers`, `flash-attn`, or `bitsandbytes`.
2. **Deterministic & Mathematical Rigor**: Tests verify analytical correctness of mathematical primitives—including Rotary Positional Embeddings (RoPE), SwiGLU gated activations ($d_{ff} = \text{round\_up\_64}(\lfloor \frac{8}{3} d_{model} \rfloor)$), and Root Mean Square Normalization (RMSNorm).
3. **Strict Gradient Backpropagation Auditing**: Verifies uncorrupted gradient flow across all custom layers, projections, embeddings, and normalization scales during mock Supervised Fine-Tuning (SFT) passes.
4. **Apple Silicon Unified Memory Hardware Governance**: Validates automatic device resolution prioritizing `mps` (Apple Silicon Metal Performance Shaders) when available, while strictly enforcing a $\le 4.0\text{ GB}$ peak unified memory ceiling.
5. **Interactive Dashboard & Pipeline Integrity**: Validates REST endpoints, JSON schemas, HTML rendering, and the programmatic state transitions of the 6-stage CRISP-DM data mining pipeline.
6. **4-Tier Progressive Verification Architecture**:
   - **Tier 1 (Feature Coverage)**: $\ge 5$ targeted unit/feature tests for every identified feature in the Feature Inventory.
   - **Tier 2 (Boundary & Corner Cases)**: $\ge 5$ stress/boundary tests per feature (e.g., sequence length 1, max sequence length, empty strings, zero-dropout, odd hidden dimensions, out-of-vocab bytes, extreme temperatures).
   - **Tier 3 (Cross-Feature Combinations)**: Pairwise and multi-feature interaction tests (e.g., RoPE with GQA and KV-cache, SwiGLU with RMSNorm residual streams, SFT loss masking with causal attention, MPS device execution with live attention extraction).
   - **Tier 4 (Real-World Workloads)**: End-to-end integration workflows (e.g., multi-step SFT training convergence on synthetic text, autoregressive generation with KV-cache vs. brute-force parity, full CRISP-DM lifecycle progression, complete dashboard FastAPI TestClient session).

---

## 2. Feature Inventory & Coverage Mapping

| Feature ID | Feature Name | Primary Module | Tier 1 Tests | Tier 2 Tests | Tier 3 Tests | Tier 4 Workloads |
| :--- | :--- | :--- | :---: | :---: | :---: | :---: |
| **F1** | RoPE Positional Embeddings | `nano_transformer.rope` | $\ge 5$ | $\ge 5$ | $\ge 3$ | $\ge 2$ |
| **F2** | SwiGLU Gated Activation | `nano_transformer.ffn` | $\ge 5$ | $\ge 5$ | $\ge 3$ | $\ge 2$ |
| **F3** | RMSNorm Pre-Normalization | `nano_transformer.norm` | $\ge 5$ | $\ge 5$ | $\ge 3$ | $\ge 2$ |
| **F4** | Causal Attention & KV-Cache | `nano_transformer.attention` | $\ge 5$ | $\ge 5$ | $\ge 3$ | $\ge 2$ |
| **F5** | Scratch Tokenizer & Inspector | `nano_transformer.tokenizer` | $\ge 5$ | $\ge 5$ | $\ge 3$ | $\ge 2$ |
| **F6** | Supervised Fine-Tuning (SFT) | `nano_transformer.sft` | $\ge 5$ | $\ge 5$ | $\ge 3$ | $\ge 2$ |
| **F7** | CRISP-DM Pipeline Tracker | `dashboard.crisp_dm` | $\ge 5$ | $\ge 5$ | $\ge 3$ | $\ge 2$ |
| **F8** | KV-Cache Inspection Endpoint | `dashboard.inspectors` / `app` | $\ge 5$ | $\ge 5$ | $\ge 3$ | $\ge 2$ |
| **F9** | Attention Heatmap Endpoint | `dashboard.inspectors` / `app` | $\ge 5$ | $\ge 5$ | $\ge 3$ | $\ge 2$ |
| **F10** | Tokenizer Inspection Endpoint | `dashboard.inspectors` / `app` | $\ge 5$ | $\ge 5$ | $\ge 3$ | $\ge 2$ |
| **F11** | Interactive Admin Web Dashboard | `dashboard.app` | $\ge 5$ | $\ge 5$ | $\ge 3$ | $\ge 2$ |
| **F12** | Apple Silicon (MPS) Auto-Selection | `nano_transformer.device` | $\ge 5$ | $\ge 5$ | $\ge 3$ | $\ge 2$ |
| **F13** | Unified Memory Profiling & Limit | `nano_transformer.device` / `benchmark` | $\ge 5$ | $\ge 5$ | $\ge 3$ | $\ge 2$ |

---

## 3. Test Suites Directory Structure

```
02_nano_llm_transformer/
├── tests/
│   ├── __init__.py
│   ├── conftest.py                  # Shared fixtures, test configs, mock generators
│   ├── test_tier1_features.py       # Tier 1: Isolated feature coverage (>=65 tests)
│   ├── test_tier2_boundaries.py     # Tier 2: Boundaries, edge cases & extremes (>=65 tests)
│   ├── test_tier3_combinations.py   # Tier 3: Combinatorial & cross-subsystem interactions
│   └── test_tier4_workloads.py      # Tier 4: Real-world workloads & full pipeline simulations
├── test_model.py                    # Acceptance Criterion 1: Shape & SFT gradient verification
├── test_dashboard.py                # Acceptance Criterion 2: FastAPI TestClient & CRISP-DM verification
├── benchmark_mps.py                 # Acceptance Criterion 3: MPS throughput & memory bound verification
├── run_tests.py                     # Master test runner & summary generator
├── TEST_INFRA.md                    # Test infrastructure specification (this document)
└── TEST_READY.md                    # Test readiness publication and feature checklist
```

---

## 4. Acceptance Scripts Specification

### 4.1 `test_model.py` (Acceptance Criterion 1)
- **Objective**: Programmatically instantiate the custom transformer model, execute a forward pass to assert shape conformity `(Batch, SeqLen, VocabSize)`, and execute a mock SFT backward pass asserting finite, non-zero gradient flow across all RoPE, SwiGLU, and RMSNorm parameters.
- **Pass Criteria**:
  1. Forward pass produces output logits tensor matching shape `(B, T, vocab_size)`.
  2. Attention extraction produces attention weights matching shape `(B, n_heads, T, T)`.
  3. Backward pass computes non-None, finite, non-zero gradients for every trainable parameter (`norm.weight`, `q_proj.weight`, `k_proj.weight`, `v_proj.weight`, `out_proj.weight`, `gate_proj.weight`, `up_proj.weight`, `down_proj.weight`, `tok_embeddings.weight`, `lm_head.weight`).
  4. Exit code 0 on complete pass.

### 4.2 `test_dashboard.py` (Acceptance Criterion 2)
- **Objective**: Programmatically launch the dashboard API via `fastapi.testclient.TestClient`, issue HTTP requests to inspection and CRISP-DM endpoints, and verify response status codes and schema structures.
- **Pass Criteria**:
  1. `GET /` and `GET /dashboard` return HTTP 200 OK with valid HTML containing title and navigation elements.
  2. `GET /api/crisp-dm` returns HTTP 200 OK with $\ge 3$ distinct stages (specifically `data_preparation`, `modeling`, `evaluation`) with status, metrics, and duration.
  3. `GET /api/inspect/kv-cache` (and `POST /api/inspect/kv-cache`) returns HTTP 200 OK with step-by-step tensor shapes and byte footprints.
  4. `GET /api/inspect/attention` (and `POST /api/inspect/attention`) returns HTTP 200 OK with square attention matrices and causal validity.
  5. `GET /api/inspect/tokenizer` (and `POST /api/inspect/tokenizer`) returns HTTP 200 OK with token pieces, token IDs, and positive compression ratio.
  6. `GET /api/health` and `GET /api/hardware/memory` return HTTP 200 OK.
  7. Exit code 0 on complete pass.

### 4.3 `benchmark_mps.py` (Acceptance Criterion 3)
- **Objective**: Execute an autoregressive text generation benchmark prioritizing Apple Silicon Metal (`mps`) device if available (falling back to `cpu`), profile memory utilization (PyTorch MPS allocated and host RSS), and enforce that memory does not exceed the predefined 4.0 GB limit.
- **Pass Criteria**:
  1. Auto-selects `mps` device when `torch.backends.mps.is_available() == True`, otherwise logs CPU fallback.
  2. Executes multi-token generation with KV-caching.
  3. Profiles and outputs latency metrics (TTFT, Inter-Token Latency, Tokens/Sec).
  4. Asserts that peak memory usage $\le 4.0\text{ GB}$.
  5. Outputs formatted ASCII table and JSON telemetry summary.
  6. Exit code 0 on complete pass.

---

## 5. Master Test Runner (`run_tests.py`)

The `run_tests.py` script provides a unified CLI orchestrator:
- **Usage**:
  ```bash
  python run_tests.py                 # Run all 4 tiers + acceptance scripts
  python run_tests.py --tier 1        # Run Tier 1 Feature Coverage tests
  python run_tests.py --tier 2        # Run Tier 2 Boundary & Edge Case tests
  python run_tests.py --tier 3        # Run Tier 3 Combinations tests
  python run_tests.py --tier 4        # Run Tier 4 Workloads tests
  python run_tests.py --acceptance    # Run test_model.py, test_dashboard.py, benchmark_mps.py
  python run_tests.py --json-report   # Export machine-readable JSON results
  ```
- **Exit Code**: `0` if all tests pass; `1` if any test fails.

---

## 6. Execution & Pass Criteria Matrix

| Test Suite / Script | Command | Expected Pass Count | Exit Code |
| :--- | :--- | :---: | :---: |
| Tier 1 Features | `pytest tests/test_tier1_features.py -v` | $\ge 65$ | 0 |
| Tier 2 Boundaries | `pytest tests/test_tier2_boundaries.py -v` | $\ge 65$ | 0 |
| Tier 3 Combinations | `pytest tests/test_tier3_combinations.py -v` | $\ge 20$ | 0 |
| Tier 4 Workloads | `pytest tests/test_tier4_workloads.py -v` | $\ge 15$ | 0 |
| Model Acceptance | `python test_model.py` | 1 suite (all checks pass) | 0 |
| Dashboard Acceptance | `python test_dashboard.py` | 1 suite (all endpoints 200) | 0 |
| MPS Benchmark | `python benchmark_mps.py` | 1 benchmark ($\le 4.0\text{ GB}$) | 0 |
| Full Master Suite | `python run_tests.py` | 100% pass | 0 |
