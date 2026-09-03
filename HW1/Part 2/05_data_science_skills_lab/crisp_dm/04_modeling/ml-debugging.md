---
skill: ml-debugging
pack: param087/agent-ml-skills
crisp_dm_phase: 4 - Modeling
artifacts: [src/p4_debugging.py, artifacts/ml_debugging_cases.json, reports/figures/p4_debug_nan_divergence.png]
---

# ml-debugging — Telco Churn Modeling

## What the skill prescribes

Isolate which layer is broken — data, optimization, or generalization —
with the cheapest possible experiment, starting with "can it overfit one
batch?" Use the symptom -> cause decision tree (NaN loss -> LR too high;
implausibly high metric -> leakage; stuck at chance -> label/LR/scaling
bug) and the leakage-hunt checklist (feature |corr|≈1.0 to target,
preprocessing fit before split, entity/time leakage across folds).

## Applied to Telco churn

Three real failure modes were **deliberately induced** — not hypothetical —
each diagnosed with the skill's own tools and fixed with measured
before/after numbers.

### Bug (a): target leakage

A synthetic `retention_flag_leaked` column was injected — modeled on a
realistic real-world mistake (joining in a downstream "retention system"
field that is only populated *after* a customer has already been flagged as
churned, i.e. it encodes the outcome): `y + N(0, 0.05)` noise.

| | PR-AUC (5-fold CV) |
|---|---|
| Honest (no leaked feature) | 0.6617 ± 0.0165 |
| **With leaked feature** | **1.0000 ± 0.0000** |

A perfect 1.0 PR-AUC with zero variance across folds is the textbook
"implausibly high" signal from the decision tree. **Diagnosis**: leakage-hunt
checklist item 1 ("any feature with |corr|≈1.0 to target?") immediately flags
it — measured `|corr(retention_flag_leaked, Churn)| = 0.9937`. **Fix**: drop
the column; score returns to the honest 0.6617 baseline.

### Bug (b): unlearning model (unscaled inputs + aggressive LR)

`SGDClassifier(loss="log_loss", learning_rate="constant", eta0=10.0)` trained
on a deliberately broken preprocessor that imputes but does **not** scale
numeric columns — so `TotalCharges` (range ≈0-8,684) sits next to 0/1
one-hot dummies. Evaluated with the same out-of-fold `cross_val_predict` used
throughout Phase 4:

| | Predicted class split | Accuracy | PR-AUC |
|---|---|---|---|
| Broken (unscaled + eta0=10.0) | {0: 4993, 1: 641} — 88.6% one class | 0.7547 | 0.3468 |
| Fixed (StandardScaler + `learning_rate="optimal"`) | {0: 3499, 1: 2135} | 0.7348 | **0.5852** |

**Diagnosis**: this is the "stuck at chance" row of the decision tree —
accuracy (0.7547) looks fine on its own (close to the 73.46% no-skill base
rate from [[imbalanced-data]]'s accuracy-trap demo) and would mislead anyone
checking only accuracy; PR-AUC exposes it immediately (0.3468 is barely above
the 0.2654 no-skill floor, i.e. the model has learned almost nothing
discriminative). Cause: the large-magnitude `TotalCharges` column dominates
the gradient step under a fixed aggressive `eta0`, so the decision boundary
collapses toward one class. **Fix**: restore `StandardScaler` (the real
`build_preprocessor()`) and use `learning_rate="optimal"` — PR-AUC nearly
doubles (0.3468 → 0.5852). It doesn't reach the tuned baseline's 0.66 because
`SGDClassifier` with a generic schedule still isn't a tuned model — that gap
is expected and is exactly what [[hyperparameter-tuning]] closes.

### Bug (c): loss instability under unscaled inputs + high LR (torch)

The skill's frontmatter explicitly includes "training is unstable" as a
trigger, not only literal NaN — reproduced here with the same
unscaled-preprocessor construction as bug (b), fed into a single
`nn.Linear` unit (`BCEWithLogitsLoss`) and the "can it overfit one batch?"
sanity check (skill's first move) at `lr=10.0`:

```
losses: [6.2, 4344668.5, 4275272.0, 3384569.5, 2493866.5, 1603163.8, 712460.9,
         937214.5, 4862466.0, 3971763.8, 3081060.5, 2190358.0, 1299655.0,
         411864.6, 2506418.5]
```

Loss swings **~5.9 orders of magnitude** (6.2 → 4.86M and back) across 15
steps on a single 64-row batch and never converges — it fails the one-batch
test outright. **Diagnosis**: decision-tree lookup for NaN/unstable loss →
LR too high, compounded here by unscaled inputs (the same root cause as bug
b, now shown in the torch loop). **Fix**: scale inputs
(`build_preprocessor()`'s `StandardScaler`), drop LR to 0.05, add gradient
clipping (`max_norm=1.0`):

```
losses: [0.7527, 0.7054, 0.6687, 0.6403, 0.6178, 0.5995, 0.5844, 0.5717,
         0.5606, 0.5509, 0.5422, 0.5344, 0.5272, 0.5205, 0.5143]
```

Monotonic decrease, no oscillation — the one-batch test now passes as
expected, confirming the fix rather than just asserting it. This result
directly informs the real MLP built for [[pytorch-training-loop]], which
uses scaled inputs, a conservative LR, and gradient clipping from the start.

## Outputs produced

- `src/p4_debugging.py` — all three induced-bug/diagnose/fix cycles, one script.
- `artifacts/ml_debugging_cases.json` — every metric, correlation, and loss trace above.
- `reports/figures/p4_debug_nan_divergence.png` — bug (c)'s broken (log-scale, oscillating) vs fixed (monotone) loss curves, side by side.
