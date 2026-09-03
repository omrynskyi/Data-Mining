#!/usr/bin/env python3
"""
Pretraining loop for the Nano LLM Transformer.

The dashboard model is randomly initialized until this script produces a checkpoint,
which is why an untrained model emits uniform-random bytes. This runs next-token
prediction over a plain-text corpus and writes `checkpoints/nano_llm.pt`, which
`dashboard/app.py` loads automatically on startup.

Usage:
    python3 train.py                          # defaults: ~4.5M params, 3000 steps on MPS
    python3 train.py --steps 6000             # train longer for lower loss
    python3 train.py --d-model 128 --n-layers 4   # match the original 886K-param config
    python3 train.py --corpus data/mytext.txt     # train on your own text
"""

import argparse
import json
import math
import os
import sys
import time
import urllib.request
from pathlib import Path
from typing import Dict, Any, Tuple

import torch
import torch.nn.functional as F

PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from nano_transformer.config import ModelArgs
from nano_transformer.model import Transformer
from nano_transformer.tokenizer import ByteTokenizer
from nano_transformer.device import resolve_device, get_memory_stats, sync_device

CORPUS_URL = (
    "https://raw.githubusercontent.com/karpathy/char-rnn/master/data/"
    "tinyshakespeare/input.txt"
)
DEFAULT_CORPUS = PROJECT_ROOT / "data" / "tinyshakespeare.txt"
DEFAULT_CHECKPOINT = PROJECT_ROOT / "checkpoints" / "nano_llm.pt"


# ---------------------------------------------------------------------------
# Corpus
# ---------------------------------------------------------------------------

def ensure_corpus(path: Path) -> str:
    """Loads the training corpus, downloading the default one on first run."""
    if not path.exists():
        if path != DEFAULT_CORPUS:
            raise FileNotFoundError(f"Corpus not found: {path}")
        print(f"[data] Corpus missing — downloading Tiny Shakespeare to {path.name} ...")
        path.parent.mkdir(parents=True, exist_ok=True)
        with urllib.request.urlopen(CORPUS_URL, timeout=60) as resp:
            path.write_bytes(resp.read())
        print(f"[data] Downloaded {path.stat().st_size:,} bytes.")
    return path.read_text(encoding="utf-8")


def build_splits(
    text: str, tokenizer: ByteTokenizer, val_fraction: float
) -> Tuple[torch.Tensor, torch.Tensor]:
    """Encodes the corpus to a flat token stream and splits it into train / val."""
    ids = torch.tensor(tokenizer.encode(text), dtype=torch.long)
    split_at = int(len(ids) * (1.0 - val_fraction))
    return ids[:split_at], ids[split_at:]


def get_batch(
    data: torch.Tensor, batch_size: int, block_size: int, device: torch.device
) -> Tuple[torch.Tensor, torch.Tensor]:
    """Samples a batch of contiguous (input, next-token-target) windows."""
    starts = torch.randint(0, len(data) - block_size - 1, (batch_size,))
    x = torch.stack([data[s : s + block_size] for s in starts])
    y = torch.stack([data[s + 1 : s + 1 + block_size] for s in starts])
    return x.to(device, non_blocking=True), y.to(device, non_blocking=True)


# ---------------------------------------------------------------------------
# Training
# ---------------------------------------------------------------------------

@torch.no_grad()
def estimate_loss(
    model: Transformer,
    splits: Dict[str, torch.Tensor],
    batch_size: int,
    block_size: int,
    device: torch.device,
    iters: int = 20,
) -> Dict[str, float]:
    """Averages loss over several batches per split to smooth out sampling noise."""
    model.eval()
    out: Dict[str, float] = {}
    for name, data in splits.items():
        losses = torch.zeros(iters)
        for i in range(iters):
            x, y = get_batch(data, batch_size, block_size, device)
            logits, _ = model(x)
            losses[i] = F.cross_entropy(
                logits.reshape(-1, logits.size(-1)), y.reshape(-1)
            ).item()
        out[name] = losses.mean().item()
    model.train()
    return out


def lr_at_step(step: int, total: int, base_lr: float, warmup: int, min_lr: float) -> float:
    """Linear warmup followed by cosine decay to `min_lr`."""
    if step < warmup:
        return base_lr * (step + 1) / warmup
    progress = (step - warmup) / max(1, total - warmup)
    return min_lr + 0.5 * (base_lr - min_lr) * (1.0 + math.cos(math.pi * progress))


def main() -> int:
    p = argparse.ArgumentParser(description="Pretrain the Nano LLM Transformer.")
    p.add_argument("--corpus", type=Path, default=DEFAULT_CORPUS)
    p.add_argument("--out", type=Path, default=DEFAULT_CHECKPOINT)
    p.add_argument("--steps", type=int, default=3000)
    p.add_argument("--batch-size", type=int, default=32)
    p.add_argument("--block-size", type=int, default=256, help="Training context length")
    p.add_argument("--d-model", type=int, default=256)
    p.add_argument("--n-layers", type=int, default=6)
    p.add_argument("--n-heads", type=int, default=8)
    p.add_argument("--n-kv-heads", type=int, default=4)
    p.add_argument("--dropout", type=float, default=0.1)
    p.add_argument("--lr", type=float, default=3e-4)
    p.add_argument("--min-lr", type=float, default=3e-5)
    p.add_argument("--warmup", type=int, default=100)
    p.add_argument("--weight-decay", type=float, default=0.1)
    p.add_argument("--grad-clip", type=float, default=1.0)
    p.add_argument("--eval-every", type=int, default=250)
    p.add_argument("--val-fraction", type=float, default=0.1)
    p.add_argument("--device", type=str, default=None, help="mps | cpu | cuda")
    p.add_argument("--seed", type=int, default=1337)
    args = p.parse_args()

    torch.manual_seed(args.seed)
    device = resolve_device(args.device)
    tokenizer = ByteTokenizer()

    print("=" * 78)
    print(" NANO LLM TRANSFORMER — PRETRAINING")
    print("=" * 78)

    text = ensure_corpus(args.corpus)
    train_data, val_data = build_splits(text, tokenizer, args.val_fraction)
    splits = {"train": train_data, "val": val_data}

    model_args = ModelArgs(
        vocab_size=tokenizer.vocab_size,
        d_model=args.d_model,
        n_layers=args.n_layers,
        n_heads=args.n_heads,
        n_kv_heads=args.n_kv_heads,
        max_seq_len=max(args.block_size, 256),
        dropout=args.dropout,
    )
    model = Transformer(model_args).to(device)
    n_params = sum(p.numel() for p in model.parameters())

    print(f"[setup] Device          : {device}")
    print(f"[setup] Corpus          : {args.corpus.name} ({len(text):,} chars)")
    print(f"[setup] Train / val     : {len(train_data):,} / {len(val_data):,} tokens")
    print(f"[setup] Parameters      : {n_params:,}")
    print(f"[setup] Architecture    : d_model={args.d_model}, n_layers={args.n_layers}, "
          f"n_heads={args.n_heads}, n_kv_heads={args.n_kv_heads}")
    print(f"[setup] Steps           : {args.steps} @ batch {args.batch_size} x {args.block_size}")
    print("-" * 78)

    # Weight decay applies to matmul weights only, not to norms / biases / embeddings.
    decay, no_decay = [], []
    for name, param in model.named_parameters():
        if not param.requires_grad:
            continue
        (decay if param.dim() >= 2 else no_decay).append(param)
    optimizer = torch.optim.AdamW(
        [
            {"params": decay, "weight_decay": args.weight_decay},
            {"params": no_decay, "weight_decay": 0.0},
        ],
        lr=args.lr,
        betas=(0.9, 0.95),
    )

    history = []
    best_val = float("inf")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    model.train()
    t_start = time.perf_counter()

    for step in range(args.steps):
        lr = lr_at_step(step, args.steps, args.lr, args.warmup, args.min_lr)
        for group in optimizer.param_groups:
            group["lr"] = lr

        x, y = get_batch(train_data, args.batch_size, args.block_size, device)
        logits, _ = model(x)
        loss = F.cross_entropy(logits.reshape(-1, logits.size(-1)), y.reshape(-1))

        optimizer.zero_grad(set_to_none=True)
        loss.backward()
        grad_norm = torch.nn.utils.clip_grad_norm_(model.parameters(), args.grad_clip)
        optimizer.step()

        if step % args.eval_every == 0 or step == args.steps - 1:
            sync_device(device)
            ev = estimate_loss(model, splits, args.batch_size, args.block_size, device)
            elapsed = time.perf_counter() - t_start
            bpc = ev["val"] / math.log(2)  # byte-level loss in bits per byte
            print(
                f"step {step:>5} | train {ev['train']:.4f} | val {ev['val']:.4f} "
                f"| bits/byte {bpc:.3f} | lr {lr:.2e} | grad {grad_norm:.2f} | {elapsed:6.1f}s"
            )
            history.append(
                {
                    "step": step,
                    "train_loss": round(ev["train"], 4),
                    "val_loss": round(ev["val"], 4),
                    "bits_per_byte": round(bpc, 4),
                    "lr": lr,
                    "elapsed_seconds": round(elapsed, 2),
                }
            )
            if ev["val"] < best_val:
                best_val = ev["val"]
                torch.save(
                    {
                        "model_state_dict": model.state_dict(),
                        "model_args": model_args.to_dict(),
                        "step": step,
                        "train_loss": ev["train"],
                        "val_loss": ev["val"],
                        "bits_per_byte": bpc,
                        "n_params": n_params,
                        "corpus": args.corpus.name,
                        "corpus_chars": len(text),
                        "tokenizer": "ByteTokenizer",
                    },
                    args.out,
                )

    total_time = time.perf_counter() - t_start
    mem = get_memory_stats(device)

    print("-" * 78)
    print(f"[done] Best val loss    : {best_val:.4f} ({best_val / math.log(2):.3f} bits/byte)")
    print(f"[done] Training time    : {total_time:.1f}s")
    print(f"[done] Peak process RSS : {mem['process_rss_mb'] / 1024:.3f} GB")
    print(f"[done] Checkpoint       : {args.out}")

    # Sample from the best checkpoint so the printed text reflects what gets served.
    ckpt = torch.load(args.out, map_location=device, weights_only=False)
    model.load_state_dict(ckpt["model_state_dict"])
    model.eval()
    prompt = "Once upon a time in Silicon Valley"
    out_ids = model.generate(
        tokenizer.encode(prompt),
        max_new_tokens=200,
        temperature=0.8,
        top_k=50,
        device=device,
        eos_id=None,
    )
    print("-" * 78)
    print("[sample] " + tokenizer.decode(out_ids).replace("\n", "\n         "))
    print("=" * 78)

    report = {
        "checkpoint": str(args.out),
        "n_params": n_params,
        "steps": args.steps,
        "best_val_loss": round(best_val, 4),
        "best_bits_per_byte": round(best_val / math.log(2), 4),
        "training_seconds": round(total_time, 2),
        "device": str(device),
        "peak_rss_gb": round(mem["process_rss_mb"] / 1024, 4),
        "history": history,
    }
    report_path = PROJECT_ROOT / "training_report.json"
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"[report] Written to {report_path.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
