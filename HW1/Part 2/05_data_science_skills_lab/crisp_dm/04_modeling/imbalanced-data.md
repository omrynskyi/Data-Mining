---
skill: imbalanced-data
pack: param087/agent-ml-skills
crisp_dm_phase: 4 - Modeling
artifacts: [src/p4_imbalanced.py, artifacts/imbalanced_data_comparison.json, reports/figures/p4_imbalanced_data_comparison.png]
---

# imbalanced-data — Telco Churn Modeling

## What the skill prescribes

Rare-positive problems mislead at three levels: **metric** (accuracy hides
failure on the minority class), **algorithm** (class weights first, resampling
only if needed), and **threshold** (0.5 is rarely right). It specifically
warns to resample *inside* cross-validation via `imblearn.pipeline.Pipeline`,
never before the train/test split, and lists SMOTE-before-split as the
central leakage trap and accuracy-on-imbalanced-data as the central metric trap.

## Applied to Telco churn

Churn is **26.54% positive** — moderate imbalance, not extreme (fraud/disease
problems the skill targets are typically 1-5%). Per the skill's own guidance
("26.54% positive is moderate ... do not over-apply SMOTE reflexively"), all
five strategies below are compared on the **same `StratifiedKFold(5,
shuffle=True, random_state=42)`** folds over `data/processed/train.csv`
(n=5,634), scored through `p3_pipeline.build_preprocessor()` so preprocessing
also re-fits per fold (no leakage from that direction either).

### (a)-(c) Strategy comparison, same folds

| Strategy | PR-AUC | ROC-AUC | Recall | Accuracy |
|---|---|---|---|---|
| (a) Baseline LogisticRegression | 0.6631 ± 0.0166 | 0.8476 | 0.5371 | 0.8069 |
| (b) `class_weight="balanced"` | 0.6617 ± 0.0165 | 0.8475 | **0.7980** | 0.7508 |
| (c) SMOTE inside CV (honest) | 0.6579 ± 0.0192 | 0.8450 | 0.7866 | 0.7551 |

PR-AUC is essentially flat across all three (0.658-0.663) — consistent with
the skill's warning not to expect SMOTE to beat class weights on moderate
imbalance; here it doesn't even match (b). `class_weight="balanced"` is the
cheapest, leak-free first move the skill recommends, and it wins: it nearly
matches SMOTE's recall (0.798 vs 0.787) with no synthetic data and no extra
pipeline step. **Verdict: `class_weight="balanced"` is the imbalance strategy
carried forward**, confirmed later against the model-evaluation held-out test.

### (e) The resampling-leakage trap, demonstrated

`SMOTE` was deliberately fit on the **full transformed train set before**
any CV split (mirroring how someone tempted to "resample first" would code
it), then the identical `StratifiedKFold(5)` folds were run on top of that
already-resampled data:

| | PR-AUC | ROC-AUC |
|---|---|---|
| (c) SMOTE inside CV (honest, leak-free) | 0.6579 | 0.8450 |
| (e) SMOTE before split (**leaky**) | **0.8355** | 0.8517 |
| **Leakage inflation** | **+0.1777 PR-AUC** | +0.0067 ROC-AUC |

The leaky version's synthetic minority points have real nearest-neighbor
donors sitting in what CV calls the "validation" fold, so the model is
partially validated on points it effectively memorized — PR-AUC jumps
17.8 points and its std shrinks 3x (0.0192 → 0.0061), the fingerprint of a
score that no longer reflects out-of-sample difficulty. ROC-AUC barely moves
(+0.0067) because ROC-AUC is threshold/rank-based over the whole space and
is much less sensitive to this local leakage than PR-AUC, which is exactly
why the skill prefers PR-AUC for imbalanced problems — it is also the metric
most vulnerable to being fooled by this leak, so leak-checking must use it,
not ROC-AUC, as the tripwire.

### (d) Threshold tuning on the baseline

Using out-of-fold probabilities (`cross_val_predict`, same 5 folds) from the
baseline model:

| Threshold | Recall | Precision constraint |
|---|---|---|
| default 0.5 | 0.5371 | (whatever precision falls out) |
| tuned 0.234 | **0.8308** | smallest threshold with precision ≥ 0.50 |

Lowering the threshold from 0.5 to 0.234 raises recall from 54% to 83% of
churners caught, while holding precision at the stated 50% floor — this is
the mechanism the business evaluation (model-evaluation, Phase 5) uses under
a retention-capacity constraint, tuned there on validation, never on test.

### (f) The accuracy trap, demonstrated

| | Accuracy | Recall | PR-AUC |
|---|---|---|---|
| Dummy majority-class predictor ("no one churns") | **73.46%** | **0.0000** | 0.2654 (= base rate) |
| Baseline LogisticRegression | 80.69% | 0.5371 | 0.6631 |

73.46% accuracy sounds respectable and is only ~7 points behind the real
model — but the dummy classifier catches **zero** churners. Accuracy alone
would make a useless model look nearly as good as a working one; PR-AUC
(0.2654 vs 0.6631, a 2.5x gap) exposes the real difference immediately. This
is the exact trap the skill names as the central metric mistake on imbalanced
data.

## Outputs produced

- `src/p4_imbalanced.py` — all five comparisons, one script, shared CV folds.
- `artifacts/imbalanced_data_comparison.json` — every metric above, machine-readable.
- `reports/figures/p4_imbalanced_data_comparison.png` — PR-AUC bar comparison
  (leaky SMOTE flagged in red) + the baseline PR curve with both thresholds marked.
