# Nano LLM Transformer Orchestration Plan

## Objective
Build and verify a pure PyTorch autoregressive transformer neural network built from scratch (RoPE, SwiGLU, RMSNorm, SFT), an interactive Data Science Admin Dashboard (CRISP-DM tracker, live KV-cache, attention heatmaps, tokenizer inspection), and Apple Silicon (MPS) unified memory optimization.

## Workflow Phases
1. **Phase 0: Survey & Scope Discovery (3 Parallel Explorers)**
   - Explorer 1: Inspect environment, python packages, hardware (Apple Silicon / MPS), directory layout.
   - Explorer 2: Analyze transformer architecture components (RoPE, SwiGLU, RMSNorm, SFT, KV-cache, attention extraction, tokenizer).
   - Explorer 3: Analyze dashboard requirements (web framework, CRISP-DM tracker, endpoints) and hardware memory benchmarking.
   - Merge findings into `PROJECT.md` Feature Inventory & Architecture.

2. **Phase 1: Dual Track Launch**
   - **Track A (E2E Testing Track)**: Design and build independent verification suite (Tiers 1-4 tests, runner, test_model.py, test_dashboard.py, benchmark_mps.py) -> generate `TEST_READY.md`.
   - **Track B (Implementation Track)**:
     - Milestone 1: Custom Transformer Model & Architecture (RoPE, SwiGLU, RMSNorm, Multi-Head / Grouped Attention with KV-cache, SFT support, tokenizer).
     - Milestone 2: Data Science Admin Dashboard & CRISP-DM Tracker (Interactive web UI, API endpoints for KV-cache, attention heatmaps, tokenizer, CRISP-DM pipeline tracker).
     - Milestone 3: Hardware Optimization & MPS Memory Profiling (MPS device selection, unified memory management, benchmark_mps.py integration).

3. **Phase 2: Final Verification & Integration Gate**
   - Run 100% E2E test suite across all milestones.
   - Independent Reviewer review + Challenger stress testing + Forensic Integrity Audit (teamwork_preview_auditor).
   - Phase 2 Tier 5 Adversarial Coverage Hardening.

4. **Phase 3: Victory Audit & Handover**
   - Confirm all acceptance criteria met cleanly.
   - Notify parent/user of project completion.
