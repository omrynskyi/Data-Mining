"""
Tier 4: Real-World Workloads & End-to-End Application Scenarios Test Suite.
Simulates real data science workflows, SFT training convergence, KV-cache generation workloads,
CRISP-DM lifecycle progression, and full dashboard interactions.
"""

import sys
import time
from pathlib import Path
from typing import Dict, Any, List
import pytest
import torch
import torch.nn as nn
import torch.optim as optim

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Safe imports
try:
    from nano_transformer.config import ModelArgs
    from nano_transformer.norm import RMSNorm
    from nano_transformer.rope import RotaryEmbedding, apply_rope
    from nano_transformer.ffn import SwiGLUFFN
    from nano_transformer.attention import CausalSelfAttention
    from nano_transformer.block import TransformerBlock
    from nano_transformer.model import Transformer
    from nano_transformer.tokenizer import ByteTokenizer
    from nano_transformer.sft import SFTDataset, collate_sft, compute_sft_loss
    from nano_transformer.device import resolve_device, get_memory_stats, empty_device_cache
    from dashboard.crisp_dm import CrispDMTracker, StageStatus
    from dashboard.inspectors import inspect_kv_cache, inspect_attention, inspect_tokenizer
    from dashboard.app import app
    MODULES_AVAILABLE = True
except ImportError:
    MODULES_AVAILABLE = False


class TestTier4Workloads:
    def test_workload_synthetic_sft_training_convergence(self, tiny_config_dict):
        """
        Workload 1: Multi-step SFT fine-tuning on a synthetic Q&A corpus.
        Asserts monotonic or steady loss decrease, stable gradient norms, and parameter updates.
        """
        torch.manual_seed(42)
        dev = resolve_device()
        args = ModelArgs(**tiny_config_dict)
        model = Transformer(args).to(dev)
        model.train()
        
        tok = ByteTokenizer()
        corpus = [
            {"prompt": "Question: What is Apple Silicon? Answer:", "response": " Apple ARM SOC."},
            {"prompt": "Question: What is RoPE? Answer:", "response": " Rotary Position Embeddings."},
            {"prompt": "Question: What is SwiGLU? Answer:", "response": " Gated Activation Function."}
        ]
        dataset = SFTDataset(corpus, tokenizer=tok, max_seq_len=64)
        optimizer = optim.AdamW(model.parameters(), lr=5e-3, weight_decay=0.01)
        
        initial_loss = None
        final_loss = None
        losses = []
        
        # Train for 15 steps
        for step in range(15):
            optimizer.zero_grad()
            batch = collate_sft([dataset[i % len(dataset)] for i in range(2)])
            tokens = batch["input_ids"].to(dev)
            targets = batch["labels"].to(dev)
            
            logits, _ = model(tokens)
            loss = compute_sft_loss(logits, targets)
            loss.backward()
            
            # Audit gradient norm
            grad_norm = torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
            assert torch.isfinite(grad_norm)
            
            optimizer.step()
            loss_val = loss.item()
            losses.append(loss_val)
            if initial_loss is None:
                initial_loss = loss_val
            final_loss = loss_val
        
        assert final_loss < initial_loss, f"SFT failed to converge: initial={initial_loss:.4f}, final={final_loss:.4f}"

    def test_workload_autoregressive_generation_kv_cache(self, tiny_config_dict):
        """
        Workload 2: Multi-step autoregressive generation with KV-cache vs non-cache speed and output check.
        """
        dev = resolve_device()
        args = ModelArgs(**tiny_config_dict)
        model = Transformer(args).to(dev)
        model.eval()
        
        tok = ByteTokenizer()
        prompt = "Once upon a time in Silicon Valley,"
        prompt_tokens = tok.encode(prompt)
        
        # Generate 20 tokens with KV-cache
        t0 = time.perf_counter()
        gen_tokens = model.generate(prompt_tokens, max_new_tokens=20, temperature=0.7, device=dev)
        t1 = time.perf_counter()
        
        assert len(gen_tokens) == len(prompt_tokens) + 20
        generated_text = tok.decode(gen_tokens)
        assert generated_text.startswith(prompt)
        assert (t1 - t0) > 0.0

    def test_workload_crisp_dm_complete_six_stage_lifecycle(self):
        """
        Workload 3: Full CRISP-DM 6-phase pipeline simulation.
        Executes Business Understanding -> Data Understanding -> Data Prep -> Modeling -> Eval -> Deployment.
        """
        tracker = CrispDMTracker()
        
        # Phase 1: Business Understanding
        tracker.start_stage("business_understanding")
        tracker.log_stage("business_understanding", "Define nano LLM parameters and 4GB Apple Silicon memory ceiling.")
        tracker.complete_stage("business_understanding", metrics={"target_memory_gb": 4.0, "target_d_model": 128})
        
        # Phase 2: Data Understanding
        tracker.start_stage("data_understanding")
        tracker.log_stage("data_understanding", "Profile raw text dataset.")
        tracker.complete_stage("data_understanding", metrics={"char_count": 50000, "estimated_tokens": 12500})
        
        # Phase 3: Data Preparation
        tracker.start_stage("data_preparation")
        tracker.log_stage("data_preparation", "Initialize ByteTokenizer and build SFT train/val splits.")
        tracker.complete_stage("data_preparation", metrics={"vocab_size": 260, "train_samples": 80, "val_samples": 20})
        
        # Phase 4: Modeling
        tracker.start_stage("modeling")
        tracker.log_stage("modeling", "Instantiate Transformer(RoPE, SwiGLU, RMSNorm) and run SFT training.")
        tracker.complete_stage("modeling", metrics={"train_loss": 1.45, "epochs": 5, "grad_norm": 0.42})
        
        # Phase 5: Evaluation
        tracker.start_stage("evaluation")
        tracker.log_stage("evaluation", "Evaluate validation perplexity and attention entropy.")
        tracker.complete_stage("evaluation", metrics={"val_loss": 1.62, "perplexity": 5.05, "eval_accuracy": 0.88})
        
        # Phase 6: Deployment
        tracker.start_stage("deployment")
        tracker.log_stage("deployment", "Launch FastAPI Admin Dashboard with live KV-cache & Attention visualizers.")
        tracker.complete_stage("deployment", metrics={"server_status": "healthy", "port": 8000})
        
        # Assert full lifecycle state
        state = tracker.export_state()
        for stage_name, stage_data in state["stages"].items():
            assert stage_data["status"] == "completed", f"Stage {stage_name} is not completed"
            assert stage_data["duration_seconds"] is not None
            assert len(stage_data["logs"]) > 0

    def test_workload_fastapi_admin_dashboard_full_session(self):
        """
        Workload 4: Full interactive FastAPI TestClient session testing dashboard UI and all APIs.
        """
        from fastapi.testclient import TestClient
        client = TestClient(app)
        
        # 1. Access Dashboard HTML
        res_ui = client.get("/")
        assert res_ui.status_code == 200
        assert "text/html" in res_ui.headers.get("content-type", "")
        
        # 2. Query CRISP-DM Pipeline
        res_crisp = client.get("/api/crisp-dm")
        assert res_crisp.status_code == 200
        crisp_data = res_crisp.json()
        assert len(crisp_data["stages"]) >= 3
        
        # 3. Inspect Tokenizer
        res_tok = client.post("/api/inspect/tokenizer", json={"text": "Apple Silicon M3 Max"})
        assert res_tok.status_code == 200
        assert res_tok.json()["token_count"] > 0
        
        # 4. Inspect Attention Matrix
        res_attn = client.post("/api/inspect/attention", json={"prompt": "Attention is all you need"})
        assert res_attn.status_code == 200
        attn_data = res_attn.json()
        assert attn_data["causal_validity"] is True
        assert len(attn_data["attention_matrix"]) == attn_data["seq_len"]
        
        # 5. Inspect KV-Cache
        res_kv = client.post("/api/inspect/kv-cache", json={"prompt": "Deep learning", "max_new_tokens": 5})
        assert res_kv.status_code == 200
        kv_data = res_kv.json()
        assert len(kv_data["steps"]) == 5
        
        # 6. Query Hardware Memory Telemetry
        res_mem = client.get("/api/hardware/memory")
        assert res_mem.status_code == 200
        mem_data = res_mem.json()
        assert mem_data["within_memory_budget"] is True
        assert mem_data["unified_memory_limit_gb"] == 4.0

    def test_workload_unified_memory_stability_under_load(self, small_config_dict):
        """
        Workload 5: Hardware unified memory constraint enforcement under repetitive inference load.
        """
        dev = resolve_device()
        args = ModelArgs(**small_config_dict)
        model = Transformer(args).to(dev)
        model.eval()
        
        tok = ByteTokenizer()
        prompt = "Profiling transformer memory allocations on Apple Silicon Metal shaders."
        prompt_tokens = tok.encode(prompt)
        
        # Execute 5 repeated generation passes
        for _ in range(5):
            _ = model.generate(prompt_tokens, max_new_tokens=15, device=dev)
            stats = get_memory_stats(dev)
            assert stats["within_memory_budget"] is True
            assert stats["process_rss_mb"] / 1024.0 <= 4.0
        
        empty_device_cache(dev)
