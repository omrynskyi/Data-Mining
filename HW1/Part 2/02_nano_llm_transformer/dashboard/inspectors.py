"""Live Diagnostic Inspectors for KV-Cache, Attention Heatmaps, and Tokenizer."""

import math
import time
from typing import Dict, Any, List, Optional
import torch

from nano_transformer.model import Transformer
from nano_transformer.tokenizer import ByteTokenizer
from nano_transformer.attention import KVCache


def inspect_kv_cache(
    model: Transformer,
    tokenizer: ByteTokenizer,
    prompt: str = "The quick brown fox",
    max_new_tokens: int = 4,
    temperature: float = 1.0,
) -> Dict[str, Any]:
    """Inspects step-by-step KV cache tensor growth, latency, and memory footprint."""
    model.eval()
    device = next(model.parameters()).device

    prompt_str = prompt if prompt else "A"
    prompt_tokens = tokenizer.encode(prompt_str)
    if not prompt_tokens:
        prompt_tokens = [tokenizer.bos_id]

    num_layers = model.n_layers
    num_heads = model.args.n_heads
    n_kv_heads = model.args.n_kv_heads if model.args.n_kv_heads is not None else num_heads
    head_dim = model.args.head_dim if hasattr(model.args, "head_dim") else model.args.d_model // num_heads

    kv_caches = [KVCache() for _ in range(num_layers)]
    tokens_tensor = torch.tensor([prompt_tokens], dtype=torch.long, device=device)

    steps: List[Dict[str, Any]] = []
    generated_token_ids: List[int] = []

    # Prefill step
    t0 = time.perf_counter()
    with torch.no_grad():
        logits, _ = model(tokens_tensor, start_pos=0, kv_cache=kv_caches, use_cache=True)
    t1 = time.perf_counter()

    next_logits = logits[:, -1, :]
    if temperature <= 0.0 or temperature < 1e-4:
        first_token = int(torch.argmax(next_logits[0], dim=-1).item())
    else:
        probs = torch.softmax(next_logits[0] / temperature, dim=-1)
        first_token = int(torch.multinomial(probs, num_samples=1).item())

    generated_token_ids.append(first_token)
    prefill_cached_len = kv_caches[0].seq_len
    total_cache_bytes_step0 = sum(c.memory_bytes for c in kv_caches)

    steps.append({
        "step_idx": 0,
        "token_id": first_token,
        "token_str": tokenizer.decode([first_token]),
        "prefill": True,
        "cache_seq_len": prefill_cached_len,
        "cache_shape_per_layer": [1, n_kv_heads, prefill_cached_len, head_dim],
        "step_latency_ms": round((t1 - t0) * 1000.0, 3),
        "step_memory_allocated_bytes": total_cache_bytes_step0,
    })

    curr_token = torch.tensor([[first_token]], dtype=torch.long, device=device)
    S = len(prompt_tokens)

    # Subsequent decode steps
    for step_i in range(1, max_new_tokens):
        start_pos = S + step_i - 1
        t0 = time.perf_counter()
        with torch.no_grad():
            logits, _ = model(curr_token, start_pos=start_pos, kv_cache=kv_caches, use_cache=True)
        t1 = time.perf_counter()

        next_logits = logits[:, -1, :]
        if temperature <= 0.0 or temperature < 1e-4:
            next_tok = int(torch.argmax(next_logits[0], dim=-1).item())
        else:
            probs = torch.softmax(next_logits[0] / temperature, dim=-1)
            next_tok = int(torch.multinomial(probs, num_samples=1).item())

        generated_token_ids.append(next_tok)
        current_seq_len = kv_caches[0].seq_len
        total_cache_bytes = sum(c.memory_bytes for c in kv_caches)

        steps.append({
            "step_idx": step_i,
            "token_id": next_tok,
            "token_str": tokenizer.decode([next_tok]),
            "prefill": False,
            "cache_seq_len": current_seq_len,
            "cache_shape_per_layer": [1, n_kv_heads, current_seq_len, head_dim],
            "step_latency_ms": round((t1 - t0) * 1000.0, 3),
            "step_memory_allocated_bytes": total_cache_bytes,
        })
        curr_token = torch.tensor([[next_tok]], dtype=torch.long, device=device)

    total_cached = kv_caches[0].seq_len
    total_mem_bytes = sum(c.memory_bytes for c in kv_caches)
    if total_mem_bytes < 1024:
        formatted_mem = f"{total_mem_bytes} B"
    elif total_mem_bytes < 1024 * 1024:
        formatted_mem = f"{total_mem_bytes / 1024.0:.2f} KB"
    else:
        formatted_mem = f"{total_mem_bytes / (1024.0 * 1024.0):.2f} MB"

    layer_summaries = []
    for l_idx, cache in enumerate(kv_caches):
        k_norm = float(cache.k.norm().item()) if cache.k is not None else 0.0
        v_norm = float(cache.v.norm().item()) if cache.v is not None else 0.0
        layer_summaries.append({
            "layer_idx": l_idx,
            "k_norm": round(k_norm, 4),
            "v_norm": round(v_norm, 4),
            "cache_tensor_shape": [1, n_kv_heads, total_cached, head_dim],
        })

    generated_text = tokenizer.decode(generated_token_ids)

    return {
        "status": "ok",
        "prompt": prompt,
        "generated_text": generated_text,
        "num_layers": num_layers,
        "num_heads": num_heads,
        "head_dim": head_dim,
        "total_cached_tokens": total_cached,
        "memory_footprint_bytes": total_mem_bytes,
        "memory_footprint_formatted": formatted_mem,
        "steps": steps,
        "layer_summaries": layer_summaries,
    }


def inspect_attention(
    model: Transformer,
    tokenizer: ByteTokenizer,
    prompt: str = "Attention mechanism in Transformers",
    layer_idx: int = 0,
    head_idx: int = 0,
) -> Dict[str, Any]:
    """Extracts post-softmax multi-head causal attention matrix and diagnostics."""
    model.eval()
    device = next(model.parameters()).device

    prompt_str = prompt if prompt else "Hello"
    token_ids = tokenizer.encode(prompt_str)
    if not token_ids:
        token_ids = [tokenizer.bos_id]

    num_layers = model.n_layers
    num_heads = model.args.n_heads

    # Clamp indices to valid ranges for graceful boundary handling
    selected_layer = max(0, min(layer_idx, num_layers - 1))
    selected_head = max(0, min(head_idx, num_heads - 1))

    tokens_tensor = torch.tensor([token_ids], dtype=torch.long, device=device)

    with torch.no_grad():
        _, attentions = model(tokens_tensor, return_attentions=True)

    if attentions is None or len(attentions) <= selected_layer:
        return {
            "status": "error",
            "message": f"Layer {selected_layer} not found in model attentions output.",
        }

    # Extract layer attention matrix of shape (B, n_heads, seq_len, seq_len)
    layer_attn = attentions[selected_layer][0, selected_head].detach().cpu()
    seq_len = layer_attn.shape[0]

    # Verify causality (upper triangle is zeros)
    upper_tri = torch.triu(layer_attn, diagonal=1)
    causal_validity = bool(torch.all(torch.abs(upper_tri) <= 1e-5).item())

    # Compute diagnostic metrics
    avg_entropy = float((-layer_attn * torch.log(layer_attn.clamp(min=1e-12))).sum(dim=-1).mean().item())
    diagonal_dominance = float(torch.diagonal(layer_attn).mean().item())
    sparsity = float((layer_attn < 0.01).float().mean().item())

    # Format token pieces for display
    tokens_display = []
    for t in token_ids:
        byte_val = t - tokenizer.byte_offset
        if 32 <= byte_val <= 126 and byte_val != 92:
            tokens_display.append(chr(byte_val))
        elif t in tokenizer.inv_special_tokens:
            tokens_display.append(tokenizer.inv_special_tokens[t])
        else:
            tokens_display.append(f"\\x{byte_val:02x}")

    return {
        "status": "ok",
        "prompt": prompt,
        "tokens": tokens_display,
        "token_ids": token_ids,
        "seq_len": seq_len,
        "num_layers": num_layers,
        "num_heads": num_heads,
        "selected_layer": selected_layer,
        "selected_head": selected_head,
        "causal_validity": causal_validity,
        "attention_matrix": [[round(float(v), 5) for v in row] for row in layer_attn.tolist()],
        "head_metrics": {
            "average_entropy": round(avg_entropy, 4),
            "diagonal_dominance": round(diagonal_dominance, 4),
            "sparsity": round(sparsity, 4),
        },
    }


def inspect_tokenizer(
    tokenizer: ByteTokenizer,
    text: str = "Hello, Apple Silicon Transformer!"
) -> Dict[str, Any]:
    """Inspects subword token boundaries, token IDs, byte arrays, and compression ratio."""
    if not text:
        return {
            "status": "ok",
            "text": "",
            "vocab_size": tokenizer.vocab_size,
            "token_count": 0,
            "char_count": 0,
            "byte_count": 0,
            "compression_ratio": 0.0,
            "tokens": [],
            "round_trip_match": True,
        }

    token_ids = tokenizer.encode(text)
    raw_utf8 = text.encode("utf-8")
    byte_count = len(raw_utf8)
    token_count = len(token_ids)
    compression = round(byte_count / max(token_count, 1), 4)

    decoded_text = tokenizer.decode(token_ids)
    round_trip = decoded_text == text

    token_items = []
    for idx, t in enumerate(token_ids):
        byte_val = t - tokenizer.byte_offset
        if 32 <= byte_val <= 126 and byte_val != 92:
            token_str = chr(byte_val)
            raw_b = [byte_val]
        elif t in tokenizer.inv_special_tokens:
            token_str = tokenizer.inv_special_tokens[t]
            raw_b = list(token_str.encode("utf-8"))
        else:
            token_str = f"\\x{byte_val:02x}"
            raw_b = [byte_val]

        token_items.append({
            "index": idx,
            "token_id": t,
            "token_str": token_str,
            "raw_bytes": raw_b,
            "char_start": idx,
            "char_end": idx + 1,
        })

    return {
        "status": "ok",
        "text": text,
        "vocab_size": tokenizer.vocab_size,
        "token_count": token_count,
        "char_count": len(text),
        "byte_count": byte_count,
        "compression_ratio": compression,
        "tokens": token_items,
        "round_trip_match": round_trip,
    }
