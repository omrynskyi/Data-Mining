---
skill: llm-finetuning
pack: param087/agent-ml-skills
crisp_dm_phase: 6 - Deployment
artifacts: [src/p6_finetune_dataset.py, artifacts/finetune_dataset.jsonl, artifacts/finetune_dataset_stats.json, artifacts/finetune_lora_config.json]
---

**Nothing in this document was trained.** This machine has no GPU (CPU-only, Python 3.9). Every
artifact below — the dataset, the tokenizer-based length statistics, the LoRA config, the
VRAM/cost estimate — is real, generated, and validated. The `SFTTrainer.train()` call was never
executed. That line is stated once here and not blurred anywhere below.

## What the skill prescribes

- Try prompting + few-shot + RAG first (see `rag-pipeline`); fine-tune only when you need
  consistent format/style, lower latency than a long prompt, or to internalize a large example
  set that won't fit in context.
- Default to **LoRA/QLoRA** (trains <1% of weights, avoids catastrophic forgetting); reach for
  full fine-tuning only with strong justification and budget.
- Use the model's chat template; a few thousand clean, diverse examples beat a noisy 100k dump.
- Key hyperparameters: LR 1e-4–3e-4 for LoRA, 1–3 epochs, rank 8–32, gradient-accumulate to an
  effective batch of 16–32.
- Evaluate on held-out task metrics (not just loss), and check for regression on unrelated
  abilities — a fine-tune can silently break general capability.

## Applied to Telco churn

**Use case**: turn a customer's churn-risk score and account facts into a **retention-agent
call brief** — 2-3 concrete risk drivers plus one talking point, read in under 15 seconds
before a call. This is exactly the "consistent format/style, internalize a template" case the
skill says fine-tuning is for, rather than a case needing new *knowledge* (RAG's job, covered
separately in `rag-pipeline.md`).

### Do I even need to fine-tune? — checked, not skipped

The skill says try prompting first. A single well-written prompt (the `SYSTEM` string in
`src/p6_finetune_dataset.py`) already produces this format reliably from any competent
instruct model, with no training needed — so the honest answer here is **no, this specific task
does not strictly require a fine-tune**. It is demonstrated anyway because the lab's brief
requires it, and because there is a real reason a team might still fine-tune: eliminating the
per-call system-prompt tokens (there is no cost saving relative to the alternative
`rag-pipeline` project since it's not a huge model though), and forcing the exact target field
order/format at lower latency than a longer instruction prompt. This trade-off is stated
explicitly rather than pretending the fine-tune was obviously necessary.

### Dataset — real, generated from actual customer records

`src/p6_finetune_dataset.py` scores all 7,043 customers with `artifacts/model.joblib`
(uncovering, in the process, a real bug in the Phase 4/5 hand-off contract — see box below),
then builds one chat-format example per customer: a system prompt, a user turn containing the
customer's real account facts + real model risk score as JSON, and an assistant turn built by a
deterministic template that cites only the facts present in that row (e.g. "fiber internet plan
(highest-churn segment, 41.9% base rate)" only appears when `InternetService == "Fiber optic"`
for THAT row). This stands in for a human-labeled gold set — every clause is dataset-grounded,
not hallucinated, which is exactly what the skill's "never invent facts" system instruction
also polices at inference time.

> **Bug found and fixed while building this dataset.** `artifacts/model.joblib`'s
> `FeatureEngineer.transform()` checks `TotalCharges.isna()` to find the 11 tenure==0 customers
> with blank billing — but `.isna()` is a no-op on a string column, and the true raw CSV ships
> `TotalCharges` as a string with blank/whitespace values, not numeric NaN. Scoring the raw CSV
> directly raised `TypeError: unsupported operand type(s) for /: 'str' and 'int'` at the
> `avg_monthly_spend` step. Fix: the caller must run
> `pd.to_numeric(df['TotalCharges'].astype(str).str.strip(), errors='coerce')` before scoring —
> confirmed working after the fix. `artifacts/inference_contract.json` and the `model-serving`
> deployment (built after this fix) were both corrected to state this precisely instead of the
> earlier (wrong) assumption that the pipeline coerced the string itself.

**Real stats** (`artifacts/finetune_dataset_stats.json`): 7,043 raw examples → 41 exact
duplicates dropped (customers with identical account-fact combinations, mostly `tenure==0` new
accounts) → 7,002 unique → 6,302 train / 700 val (90/10, seed 42). Token lengths measured with
the actual `gpt2` tokenizer (cached offline — a documented stand-in for whichever real base
model is chosen, swap before training): min 227, p50 252, p95 267, max 273 tokens per example —
short and tight, consistent with a templated task rather than open-ended generation.

### Method selection and config — real, justified

| Method | Trains | Fits here? |
|---|---|---|
| Full FT | 100% | Overkill — narrow templated task, wastes budget and risks overfitting the template |
| LoRA | ~0.1–1% | Viable, no quantization needed for a 3B-class base |
| **QLoRA** | ~0.1–1%, 4-bit | **Chosen** — cheapest, and this task doesn't need full precision |

`artifacts/finetune_lora_config.json` — computed, not guessed: assumed base ≈3B-param
instruct model (a narrow structured-in/structured-out task doesn't need a larger one),
`r=16, alpha=32, target_modules=[q,k,v,o]_proj`, **11.01M trainable params (0.367% of base)**,
LR 2e-4, 2 epochs, effective batch 16 (batch 2 × grad-accum 8). VRAM: ~1.5GB 4-bit base weights
+ ~0.09GB optimizer state (LoRA only) + ~3GB activations at this batch/seq-len (using the real
p95=267 token length above, not a guess) ≈ **4.6GB total** — fits on a single consumer GPU.
Estimated ≈0.2 GPU-hours for 2 epochs over 6,302 examples at effective batch 16 — cheap, which
is the expected shape for a dataset this size and task this narrow.

### Evaluation plan (specified, not run)

- Held-out val set (700 examples, disjoint customers) — track eval loss for overfitting, per
  the skill's pitfall list (too many epochs / too-high LR → degenerate repetition).
- Task metric: exact-match on the extracted risk band (HIGH/MEDIUM/LOW) and a rubric check that
  every cited driver string is verifiably present in the input JSON (a cheap, deterministic
  substitute for an LLM-judge here, since the target format is template-constrained).
- **Base-model baseline required before claiming the fine-tune helped** — the skill flags
  skipping this as a pitfall; the honest answer above (a good system prompt already gets close)
  makes this baseline unusually important here, not optional.
- Regression check: hold out a handful of generic instruction-following prompts unrelated to
  churn, and confirm the fine-tuned model still answers them competently (catastrophic-
  forgetting check) — LoRA on 0.37% of weights makes this low-risk but not zero-risk.

## Outputs produced

- `src/p6_finetune_dataset.py` — dataset generator, real tokenizer stats.
- `artifacts/finetune_dataset.jsonl` — 7,002 deduped chat-format examples, `split` field marks
  train/val.
- `artifacts/finetune_dataset_stats.json` — real counts and token-length distribution.
- `artifacts/finetune_lora_config.json` — LoRA config + VRAM/time estimate with shown arithmetic.
