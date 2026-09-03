# Nano LLM Transformer & Data Science Admin Dashboard

A pure-PyTorch autoregressive transformer built entirely from scratch — RoPE, SwiGLU, RMSNorm,
GQA attention with KV-caching, a byte-level tokenizer, and supervised fine-tuning — paired with an
interactive data science admin dashboard (CRISP-DM pipeline tracker + live model inspection),
optimized for Apple Silicon unified memory.

No `torch.nn.Transformer`, no HuggingFace. Every primitive is implemented in this repository.

## Quick start

```bash
pip install -r requirements.txt

python3 train.py                                       # pretrain the model (~30 min on M-series)
uvicorn dashboard.app:app --reload --port 8000         # then open http://127.0.0.1:8000

python3 test_model.py                                  # model forward + SFT gradient acceptance
python3 test_dashboard.py                              # dashboard endpoint acceptance
python3 benchmark_mps.py                               # Apple Silicon MPS benchmark
python3 run_tests.py                                   # full multi-tier suite (8 suites)
```

> **Run `train.py` first.** Without a checkpoint the dashboard serves a randomly-initialized
> model, which is architecturally valid but emits uniform-random bytes. The header badge reads
> `UNTRAINED` until `checkpoints/nano_llm.pt` exists.

## Training

`train.py` runs next-token prediction over a plain-text corpus and writes
`checkpoints/nano_llm.pt`, which `dashboard/app.py` loads automatically at startup.
Tiny Shakespeare (1.1 MB) is downloaded on first run.

```bash
python3 train.py                              # 4.5M params, 3000 steps, batch 32 x 256
python3 train.py --steps 6000                 # train longer for a lower loss
python3 train.py --d-model 128 --n-layers 4   # the smaller 886K-param configuration
python3 train.py --corpus data/mytext.txt     # train on your own text
```

The checkpoint stores its own `ModelArgs`, so the dashboard reconstructs whatever architecture
you trained. Loss is reported in nats and in **bits/byte**, the standard comparable metric for
byte-level models. Per-eval history is written to `training_report.json`.

To fine-tune on instruction pairs instead, `nano_transformer/sft.py` provides `SFTDataset`,
`DataCollatorForSFT`, prompt masking with `ignore_index=-100`, and `SFTTrainer`.

## What's implemented

### Core model (`nano_transformer/`)
| Module | Contents |
|--------|----------|
| `config.py` | `ModelArgs` hyperparameter dataclass |
| `norm.py` | `RMSNorm` — pre-normalization with learnable scale, no mean subtraction |
| `rope.py` | `RotaryEmbedding` — split-half rotary embeddings, precomputed cos/sin, dynamic cache extension |
| `ffn.py` | `SwiGLUFFN` — SiLU-gated FFN, `d_ff = round_up_64(8/3 · d_model)` |
| `attention.py` | `CausalSelfAttention` — MHA / GQA / MQA, causal masking, `KVCache` for O(1) decode, attention-weight extraction |
| `block.py` | Pre-LN transformer block with residual connections |
| `model.py` | `Transformer` — weight tying, prefill + KV-cached decode, top-k / top-p / temperature sampling |
| `tokenizer.py` | `ByteTokenizer` and `BPETokenizer` written from scratch, with an `inspect()` metadata API |
| `sft.py` | SFT dataset, collator, prompt masking (`ignore_index=-100`), loss and trainer |
| `device.py` | MPS auto-resolution, RSS / Metal memory profiling, 4.0 GB ceiling checks |

Default config: 886,400 parameters (`vocab=260, d_model=128, n_layers=4, n_heads=4`).

### Dashboard (`dashboard/`)
FastAPI app serving a single-page admin UI plus a REST surface:

| Route | Purpose |
|-------|---------|
| `GET /` , `GET /dashboard` | Interactive admin dashboard UI |
| `GET /api/health` | Status, active device, MPS availability, checkpoint / training metrics |
| `GET /api/crisp-dm` | All 6 CRISP-DM stages with status, metrics, logs, artifacts |
| `GET /api/crisp-dm/stage/{id}` · `POST .../transition` | Read / drive a single stage |
| `GET|POST /api/inspect/kv-cache` | Step-by-step KV-cache shapes, allocation, hit metrics |
| `GET|POST /api/inspect/attention` | Post-softmax attention matrices per layer and head |
| `GET|POST /api/inspect/tokenizer` | Token pieces, IDs, byte lengths, offsets, compression ratio |
| `GET /api/hardware/memory` | Live RSS and Metal allocation telemetry |
| `POST /api/generate` | Run generation with sampling controls |

CRISP-DM stages tracked: `business_understanding`, `data_understanding`, `data_preparation`,
`modeling`, `evaluation`, `deployment`.

### Apple Silicon optimization
`resolve_device()` selects `mps` when available and falls back to `cpu`. `benchmark_mps.py` runs a
real generation workload and enforces a 4.0 GB unified-memory ceiling.

Latest measured run: `mps`, **27.31 tokens/sec** (36.6 ms/token), **0.259 GB peak RSS** — 6.5% of
the 4.0 GB budget. Results are written to `benchmark_report.json`.

## Testing

432 tests across five tiers, all passing:

| Tier | Focus |
|------|-------|
| 1 | Feature coverage (≥5 tests per feature) |
| 2 | Boundary and corner cases |
| 3 | Combinatorial cross-feature interactions |
| 4 | Real-world end-to-end workloads |
| 5 | Adversarial: core primitives, CRISP-DM state machine, endpoint hostile inputs, sustained MPS load |

```bash
python3 -m pytest tests/ -q       # 432 passed
python3 run_tests.py              # 8/8 suites, writes test_report.json
python3 run_tests.py --tier 5     # adversarial tier only
python3 challenge_harness.py      # standalone empirical stress engine
```

`challenge_harness.py` independently verifies the model's central claims: RoPE L2-isometry over
9,800 trials and extrapolation to `seq_len=16,484`; KV-cached decode matching full prefill to
3.58e-07; SFT gradient flow under 100%-masked and single-token batches; and 6,516 Unicode/emoji
tokenizer round-trips at 100% fidelity.

## Documentation
- `PROJECT.md` — architecture, feature inventory, milestones, interface contracts
- `TEST_INFRA.md` — test suite architecture and coverage thresholds
- `TEST_READY.md` — test readiness report
- `.agents/orchestrator/GATE_STATUS.md` — review, challenge, and audit gate record
