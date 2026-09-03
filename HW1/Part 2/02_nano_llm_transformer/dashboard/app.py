"""FastAPI Data Science Admin Dashboard Application with CRISP-DM & Diagnostics APIs."""

import os
from pathlib import Path
from typing import Dict, Any, Optional, List

import torch
from fastapi import FastAPI, HTTPException, Query, Body
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from nano_transformer.config import ModelArgs
from nano_transformer.model import Transformer
from nano_transformer.tokenizer import ByteTokenizer
from nano_transformer.device import resolve_device, get_memory_stats
from dashboard.crisp_dm import CrispDMTracker, StageStatus
from dashboard.inspectors import inspect_kv_cache, inspect_attention, inspect_tokenizer

# Application paths
CURRENT_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = CURRENT_DIR / "templates"
STATIC_DIR = CURRENT_DIR / "static"

app = FastAPI(
    title="Nano LLM Data Science Admin Dashboard",
    description="Interactive CRISP-DM Pipeline Tracker & Real-Time Transformer Model Visualizer",
    version="1.0.0",
)

# Serve the dashboard CSS / JS assets
if STATIC_DIR.is_dir():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# Global tracker and model instances
tracker = CrispDMTracker()

# Pre-populate sample lifecycle metrics for realistic dashboard presentation
tracker.complete_stage("business_understanding", metrics={"compute_budget_gb": 4.0, "target_ppl": 15.0})
tracker.complete_stage("data_understanding", metrics={"total_chars": 524288, "entropy": 4.82})
tracker.complete_stage("data_preparation", metrics={"total_tokens": 1048576, "vocab_size": 260, "train_split": 0.9})
tracker.start_stage("modeling")
tracker.log_stage("modeling", "Initialized Nano Transformer with RoPE, SwiGLU, and RMSNorm.")
tracker.add_artifact("modeling", "architecture", "NanoTransformer-128d-4L")

# Model and Tokenizer singletons
_device = resolve_device()
CHECKPOINT_PATH = CURRENT_DIR.parent / "checkpoints" / "nano_llm.pt"

# Architecture used when no trained checkpoint is available. An untrained model is
# mathematically valid but emits uniform-random bytes, so `train.py` writes a
# checkpoint that is loaded here in preference to random initialization.
_DEFAULT_ARGS = ModelArgs(
    vocab_size=260,
    d_model=128,
    n_layers=4,
    n_heads=4,
    n_kv_heads=2,
    d_ff=384,
    max_seq_len=256,
    dropout=0.0
)


def _load_model() -> tuple:
    """Loads the trained checkpoint when present, else falls back to random weights."""
    if CHECKPOINT_PATH.exists():
        try:
            ckpt = torch.load(CHECKPOINT_PATH, map_location=_device, weights_only=False)
            saved = dict(ckpt["model_args"])
            saved["dropout"] = 0.0  # inference only
            args = ModelArgs.from_dict(saved)
            model = Transformer(args)
            model.load_state_dict(ckpt["model_state_dict"])
            info = {
                "trained": True,
                "checkpoint": CHECKPOINT_PATH.name,
                "step": ckpt.get("step"),
                "val_loss": round(float(ckpt.get("val_loss", 0.0)), 4),
                "bits_per_byte": round(float(ckpt.get("bits_per_byte", 0.0)), 4),
                "n_params": int(ckpt.get("n_params", sum(p.numel() for p in model.parameters()))),
                "corpus": ckpt.get("corpus"),
            }
            return model.to(_device), args, info
        except Exception as exc:  # corrupt or architecture-mismatched checkpoint
            print(f"[dashboard] Could not load {CHECKPOINT_PATH}: {exc}. Using random weights.")

    model = Transformer(_DEFAULT_ARGS)
    info = {
        "trained": False,
        "checkpoint": None,
        "n_params": sum(p.numel() for p in model.parameters()),
        "note": "Untrained model — output is random. Run `python3 train.py` to fit weights.",
    }
    return model.to(_device), _DEFAULT_ARGS, info


_model, _args, _model_info = _load_model()
_model.eval()
_tokenizer = ByteTokenizer()


# ---------------------------------------------------------------------------
# Pydantic Request Models
# ---------------------------------------------------------------------------

class KVCacheRequest(BaseModel):
    prompt: str = Field(default="The quick brown fox", description="Input text prompt")
    max_new_tokens: int = Field(default=4, ge=1, le=128, description="Number of tokens to generate")
    temperature: float = Field(default=1.0, ge=0.0, le=5.0, description="Sampling temperature")


class AttentionRequest(BaseModel):
    prompt: str = Field(default="To be or not to be", description="Input text to analyze")
    layer_idx: int = Field(default=0, ge=0, description="Transformer layer index")
    head_idx: int = Field(default=0, ge=0, description="Attention head index")


class TokenizerRequest(BaseModel):
    text: str = Field(default="Hello, Apple Silicon M-series transformer!", description="Text to tokenize")


class StageTransitionRequest(BaseModel):
    status: StageStatus
    metrics: Optional[Dict[str, Any]] = None
    artifacts: Optional[Dict[str, Any]] = None
    log: Optional[str] = None


class GenerateRequest(BaseModel):
    prompt: str = Field(default="Once upon a time in Silicon Valley", description="Generation prompt")
    max_new_tokens: int = Field(default=20, ge=1, le=256, description="Max generated tokens")
    temperature: float = Field(default=0.8, ge=0.0, le=2.0)
    top_k: int = Field(default=50, ge=0)
    top_p: float = Field(default=0.9, ge=0.0, le=1.0)
    use_cache: bool = Field(default=True)


# ---------------------------------------------------------------------------
# Web UI Routes
# ---------------------------------------------------------------------------

@app.get("/", response_class=HTMLResponse)
@app.get("/dashboard", response_class=HTMLResponse)
async def serve_dashboard():
    """Serves the interactive Data Science Admin Dashboard Single Page Application."""
    index_path = TEMPLATES_DIR / "index.html"
    if index_path.exists():
        with open(index_path, "r", encoding="utf-8") as f:
            html_content = f.read()
    else:
        html_content = (
            "<!DOCTYPE html><html><head><title>Nano LLM Dashboard</title></head>"
            "<body><h1>Nano LLM Transformer Data Science Dashboard</h1>"
            "<p>Dashboard templates initialized.</p></body></html>"
        )
    return HTMLResponse(content=html_content, status_code=200)


# ---------------------------------------------------------------------------
# REST API Endpoints
# ---------------------------------------------------------------------------

@app.get("/api/health")
async def health_check():
    """Returns application health status and compute device hardware info."""
    mem = get_memory_stats(_device)
    return {
        "status": "healthy",
        "device": str(_device),
        "device_type": _device.type,
        "mps_available": mem.get("mps_available", False),
        "mps_built": mem.get("mps_built", False),
        "platform": mem.get("platform", ""),
        "model": _model_info,
    }


@app.get("/api/crisp-dm")
async def get_crisp_dm_state():
    """Returns the complete CRISP-DM 6-stage pipeline tracker state."""
    return tracker.export_state()


@app.get("/api/crisp-dm/stage/{stage_id}")
async def get_crisp_dm_stage(stage_id: str):
    """Returns state and metrics for a specific CRISP-DM stage."""
    stage = tracker.get_stage(stage_id)
    if stage is None:
        raise HTTPException(status_code=404, detail=f"Stage '{stage_id}' not found in pipeline.")
    return stage


@app.post("/api/crisp-dm/stage/{stage_id}/transition")
async def transition_crisp_dm_stage(stage_id: str, payload: StageTransitionRequest):
    """Transitions a CRISP-DM stage status and records metrics/artifacts."""
    if stage_id not in tracker.stages:
        raise HTTPException(status_code=404, detail=f"Stage '{stage_id}' not found.")
    
    if payload.status == StageStatus.RUNNING:
        tracker.start_stage(stage_id)
    elif payload.status == StageStatus.COMPLETED:
        tracker.complete_stage(stage_id, metrics=payload.metrics, artifacts=payload.artifacts)
    elif payload.status == StageStatus.FAILED:
        tracker.fail_stage(stage_id, error=payload.log or "Unknown failure")
    
    if payload.log:
        tracker.log_stage(stage_id, payload.log)

    return tracker.get_stage(stage_id)


@app.get("/api/inspect/kv-cache")
async def inspect_kv_cache_get(
    prompt: str = Query(default="The quick brown fox"),
    max_new_tokens: int = Query(default=4, ge=1, le=128),
    temperature: float = Query(default=1.0, ge=0.0, le=5.0),
):
    """Inspects step-by-step KV cache tensor growth via HTTP GET."""
    return inspect_kv_cache(_model, _tokenizer, prompt, max_new_tokens, temperature)


@app.post("/api/inspect/kv-cache")
async def inspect_kv_cache_post(payload: KVCacheRequest):
    """Inspects step-by-step KV cache tensor growth via HTTP POST."""
    return inspect_kv_cache(
        _model, _tokenizer, payload.prompt, payload.max_new_tokens, payload.temperature
    )


@app.get("/api/inspect/attention")
async def inspect_attention_get(
    prompt: str = Query(default="To be or not to be"),
    layer_idx: int = Query(default=0, ge=0),
    head_idx: int = Query(default=0, ge=0),
):
    """Extracts post-softmax attention matrix heatmap via HTTP GET."""
    return inspect_attention(_model, _tokenizer, prompt, layer_idx, head_idx)


@app.post("/api/inspect/attention")
async def inspect_attention_post(payload: AttentionRequest):
    """Extracts post-softmax attention matrix heatmap via HTTP POST."""
    return inspect_attention(
        _model, _tokenizer, payload.prompt, payload.layer_idx, payload.head_idx
    )


@app.get("/api/inspect/tokenizer")
async def inspect_tokenizer_get(
    text: str = Query(default="Hello, Apple Silicon M-series transformer!"),
):
    """Inspects token breakdown, byte values, and compression metrics via HTTP GET."""
    return inspect_tokenizer(_tokenizer, text)


@app.post("/api/inspect/tokenizer")
async def inspect_tokenizer_post(payload: TokenizerRequest):
    """Inspects token breakdown, byte values, and compression metrics via HTTP POST."""
    return inspect_tokenizer(_tokenizer, payload.text)


@app.get("/api/hardware/memory")
async def get_hardware_memory():
    """Returns Apple Silicon MPS unified memory and process RSS telemetry."""
    return get_memory_stats(_device)


@app.post("/api/generate")
async def generate_text(payload: GenerateRequest):
    """Executes autoregressive text generation with optional KV caching."""
    prompt_tokens = _tokenizer.encode(payload.prompt)
    gen_tokens, metrics = _model.generate(
        prompt_tokens,
        max_new_tokens=payload.max_new_tokens,
        temperature=payload.temperature,
        top_k=payload.top_k,
        top_p=payload.top_p,
        device=_device,
        return_metrics=True,
        use_cache=payload.use_cache
    )
    generated_text = _tokenizer.decode(gen_tokens)
    return {
        "status": "ok",
        "prompt": payload.prompt,
        "generated_text": generated_text,
        "token_ids": gen_tokens,
        "tokens_count": len(gen_tokens),
        "metrics": metrics,
    }
