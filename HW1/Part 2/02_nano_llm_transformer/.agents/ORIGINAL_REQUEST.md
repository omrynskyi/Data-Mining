# Original User Request

## 2026-09-02T17:21:23Z

# Teamwork Project Prompt

A rigorous evaluation setup for experimenting with local LLMs, optimized for Apple Silicon (M-series). It features a pure PyTorch autoregressive transformer neural network built entirely from scratch (featuring RoPE, SwiGLU, RMSNorm, SFT). The project includes a data science admin dashboard with an interactive CRISP-DM pipeline tracker and live visualizations of KV-cache, attention heatmaps, and tokenizer inspection.

Working directory: /Users/oleg/Documents/Coding/SJSU/Data Mining/HW1/Part 2/02_nano_llm_transformer
Integrity mode: benchmark

## Requirements

### R1. Custom Transformer Model
Build a pure PyTorch autoregressive transformer from scratch utilizing state-of-the-art primitives including Rotary Position Embeddings (RoPE), SwiGLU gated activations, and RMSNorm. It must support Supervised Fine-Tuning (SFT).

### R2. Data Science Admin Dashboard
Create an interactive data science dashboard that features a CRISP-DM pipeline tracker. The dashboard must provide live inspection tools for the model, including KV-cache generation views, attention heatmaps, and tokenizer inspection.

### R3. Hardware Optimization
The implementation must be explicitly optimized to run efficiently within Apple Silicon (M-series Mac) unified memory constraints.

## Acceptance Criteria

### Model Architecture Verification
- [ ] A programmatic test script (`test_model.py`) runs successfully, initializing the model and verifying that a forward pass produces expected output tensor shapes.
- [ ] The test script verifies that gradients flow through all custom components (RoPE, SwiGLU, RMSNorm) during a mock SFT backward pass.

### Dashboard Verification
- [ ] A programmatic test script launches the dashboard locally and verifies that HTTP GET requests to the KV-cache, attention heatmaps, and tokenizer endpoints return HTTP 200 OK.
- [ ] The CRISP-DM pipeline tracker state can be read programmatically, confirming it tracks at least 3 stages (e.g., Data Preparation, Modeling, Evaluation).

### Hardware Optimization Verification
- [ ] A programmatic benchmark script (`benchmark_mps.py`) runs a text generation task and verifies that it defaults to the `mps` device (Apple Metal Performance Shaders) if available.
- [ ] The benchmark logs memory usage and confirms it does not exceed a predefined unified memory limit (e.g., 4GB for a tiny model).
