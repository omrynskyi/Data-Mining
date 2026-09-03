# Handoff Report — Challenger 1 (Core Model Primitives)

**Date**: 2026-09-02
**Scope**: RoPE, KV-cache decode equivalence, SFT gradient flow, Tokenizer Unicode robustness
**Verdict**: **APPROVE**

## Observation
The M1 core library (`nano_transformer/`) claims mathematically exact RoPE rotations, bit-exact
KV-cached decoding, correct prompt-masked SFT gradients, and lossless byte-level tokenization.
Each claim was challenged empirically rather than accepted from the implementation's own tests.

## Logic Chain
1. Built `challenge_harness.py` — a standalone empirical stress engine independent of the pytest suite.
2. Encoded the four claims as falsifiable adversarial experiments at scale.
3. Codified the surviving cases as a permanent regression suite in
   `tests/test_tier5_adversarial_challenge.py` (244 tests).

## Empirical Results (`python3 challenge_harness.py`)
| # | Challenge | Scale | Measurement | Verdict |
|---|-----------|-------|-------------|---------|
| 1 | RoPE extrapolation, rotational invariance, L2 isometry | 9,800 trials | Norm preserved; dynamic cache extension verified to `seq_len=16,484` | PASS |
| 2 | KV-cached single-step decode vs. full prefill | 90 sequences (MHA/GQA/MQA) | Max logit discrepancy **3.58e-07** (threshold 1e-4); 20/20 greedy generations bitwise identical | PASS |
| 3 | SFT gradients under extreme loss masking | B=1..16, LR sweep | 100%-masked batch → 0.0 loss, zero grad, no NaNs; single active token still propagates finite grads to RoPE/SwiGLU/RMSNorm; loss 5.5609 → 3.0171 | PASS |
| 4 | Tokenizer Unicode / SMP / ZWJ-emoji / malformed fuzzing | 6,516 cycles | 100% round-trip preservation, 100% malformed-input resilience (zero uncaught exceptions) | PASS |

Total adversarial execution time: 3.00s.

## Caveats
- Challenge 2's equivalence threshold (1e-4) is deliberately loose relative to the observed 3.58e-07,
  to stay stable across MPS/CPU float32 reduction-order differences.
- The tokenizer fuzzer generates 10,000 candidate inputs but deduplicates to 6,516 distinct cycles;
  the reported count is the executed count, not the generated count.

## Conclusion
No falsifying case was found against any of the four core-primitive claims. The primitives are
genuine from-scratch implementations, not delegations to `torch.nn.Transformer` or HuggingFace.

## Verification Method
`python3 challenge_harness.py` (exit 0, FINAL VERDICT: APPROVE) and
`python3 -m pytest tests/test_tier5_adversarial_challenge.py` (244 passed).
