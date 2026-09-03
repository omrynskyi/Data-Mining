---
skill: pytorch-training-loop
pack: param087/agent-ml-skills
crisp_dm_phase: 4 - Modeling
artifacts: [src/p4_mlp_torch.py, artifacts/mlp_best.pt, artifacts/mlp_vs_sklearn_comparison.json, artifacts/mlp_training_history.json, reports/figures/p4_mlp_training_curve.png]
---

# pytorch-training-loop — Telco Churn Modeling

## What the skill prescribes

A precise, non-negotiable sequence: `model.train()`/`model.eval()` toggled
correctly, `optimizer.zero_grad()` every step, `torch.no_grad()` around
validation, `BCEWithLogitsLoss` (never manual sigmoid+BCE — numerically
unstable, as [[ml-debugging]] bug (c) demonstrated in this same phase),
gradient clipping, deterministic seeding, explicit device selection, and
checkpointing the *best* validated weights rather than the last epoch.

## Applied to Telco churn

`ChurnMLP` — a 57→64→32→1 MLP with ReLU + Dropout(0.3), trained on
`p3_pipeline.build_preprocessor()`'s output — implements every rule:

| Rule | Implementation |
|---|---|
| Deterministic seeding | `set_all_seeds(42)` from [[reproducible-ml]], plus a seeded `torch.Generator` for the shuffling `DataLoader` |
| Device selection | `select_device()`: CUDA → MPS → CPU; ran on **MPS** (Apple Silicon) this session |
| `model.train()`/`model.eval()` | Explicit before the train loop and before the validation loop each epoch |
| `optimizer.zero_grad()` | `set_to_none=True`, every step, before `backward()` |
| `torch.no_grad()` | Wraps the entire validation loop |
| `BCEWithLogitsLoss` | Used throughout — never separate `sigmoid()` + `BCELoss` (see [[ml-debugging]] bug (c) for why that pairing is numerically fragile) |
| `pos_weight` for imbalance | `pos_weight = n_neg/n_pos = 2.7671` computed from the **train split only** (not val/test) |
| Gradient clipping | `clip_grad_norm_(max_norm=1.0)` every step |
| Early stopping | Patience=10 epochs on val loss; training stopped at **epoch 11** (best was epoch 1) |
| Checkpointing best weights | `torch.save` fires only when val loss improves by >1e-4; evaluation reloads that checkpoint, not the final-epoch weights |
| Leakage-safe preprocessing | `build_preprocessor()` fit on the **train split only**, applied (not refit) to val and test |

Train/val split: 85/15 stratified from `train.csv` (n=4,788 train / 846 val),
test = the untouched `test.csv` (n=1,409).

### Training curve

Loss decreases for 2 epochs then val loss starts drifting up while train loss
keeps falling — classic early overfitting on a small (4,788-row) tabular
set with a 57→64→32→1 capacity. Early stopping caught it at epoch 11 and
checkpointed the epoch-1 weights (val_loss=0.7286), exactly the case the
skill's checkpointing rule exists for — training 100 epochs and taking the
last one would have used a measurably worse model.
See `reports/figures/p4_mlp_training_curve.png`.

### Held-out TEST metrics (best checkpoint, epoch 1)

| Metric | Value |
|---|---|
| ROC-AUC | 0.8435 |
| PR-AUC | 0.6532 |
| Accuracy @ 0.5 | 0.7410 |
| Recall @ 0.5 | 0.7861 |
| Brier score | 0.1698 |

### Honest comparison vs the sklearn baselines (same held-out test set)

| Model | Test PR-AUC | Test ROC-AUC |
|---|---|---|
| LogisticRegression (`class_weight="balanced"`) | 0.6590 | -- |
| **XGBoost (Optuna-tuned, from [[hyperparameter-tuning]])** | **0.6621** | -- |
| MLP (this script, best checkpoint) | 0.6532 | 0.8435 |

**Verdict: the MLP does NOT beat the sklearn baselines** — XGBoost's tuned
PR-AUC (0.6621) and even the untuned class-weighted LogisticRegression
(0.6590) both edge out the MLP (0.6532) on held-out test. This is the
expected, correct finding for a dataset this size (a few thousand rows, 57
engineered/encoded features): gradient-boosted trees and even plain
logistic regression are well known to match or beat small MLPs on
small/medium tabular data, where there isn't enough data for a neural net's
extra capacity to pay for itself and regularize away overfitting. The MLP is
reported honestly here rather than tuned further to force a win — its value
in this lab is demonstrating a *correct* loop, not winning the model
selection, and it is **not** the model carried forward to
[[model-evaluation]] / the Phase 6 hand-off.

## Outputs produced

- `src/p4_mlp_torch.py` — the full correct loop.
- `artifacts/mlp_best.pt` — best checkpoint (state dict + epoch + val_loss).
- `artifacts/mlp_training_history.json` — per-epoch train/val loss + val PR-AUC.
- `artifacts/mlp_vs_sklearn_comparison.json` — the three-way test-set comparison above.
- `reports/figures/p4_mlp_training_curve.png` — loss curves + val PR-AUC per epoch, best-checkpoint epoch marked.
