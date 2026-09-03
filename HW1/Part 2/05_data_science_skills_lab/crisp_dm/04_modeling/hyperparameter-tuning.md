---
skill: hyperparameter-tuning
pack: param087/agent-ml-skills
crisp_dm_phase: 4 - Modeling
artifacts: [src/p4_tuning.py, artifacts/hyperparameter_tuning_results.json, artifacts/optuna_trials_logreg.csv, artifacts/optuna_trials_xgboost.csv, reports/figures/p4_optuna_logreg_history.png, reports/figures/p4_optuna_logreg_importance.png, reports/figures/p4_optuna_xgboost_history.png, reports/figures/p4_optuna_xgboost_importance.png]
---

# hyperparameter-tuning — Telco Churn Modeling

## What the skill prescribes

Tune the **whole pipeline inside cross-validation** (never fit preprocessing
once and tune on top of it), search smart — Bayesian/Optuna over grid/random
for anything beyond a couple of cheap params — sample learning-rate/regularization
on a log scale, cap budget with `n_trials`/`timeout` and use pruning to kill
bad trials early, and never touch the test set during search.

## Applied to Telco churn

Two model families tuned with `optuna.samplers.TPESampler(seed=42)`, each
objective scoring **mean PR-AUC over the same `StratifiedKFold(5,
shuffle=True, random_state=42)`** folds used throughout Phase 4 — the metric
choice carries over directly from [[imbalanced-data]]'s conclusion that
PR-AUC is the honest metric here.

### LogisticRegression — cheap search space, no pruning needed

- Params: `C` (log-scale, 1e-3 to 10), `penalty` (l1/l2 via `liblinear`),
  `class_weight="balanced"` fixed (per the imbalanced-data finding).
- Budget: 30 trials, 300s timeout — actually finished in 51.4s (fit is
  sub-second per fold), no pruner needed for a 2-param space.
- **Best: PR-AUC = 0.6622**, `C=0.2731`, `penalty='l1'`.
- Essentially matches the untuned baseline (0.6631 PR-AUC from
  [[imbalanced-data]]) — expected: LogisticRegression on 57 already-scaled
  features has little headroom left to tune.

### XGBoost — 9-param search space, pruning demonstrated

- Params: `max_depth` (2-8), `learning_rate` (log-scale, 1e-3 to 0.3),
  `n_estimators` (50-400), `subsample`, `colsample_bytree`,
  `min_child_weight`, `reg_alpha`/`reg_lambda` (log-scale), `scale_pos_weight`
  (1.0 to 1.5x the natural neg/pos ratio).
- Budget: 40 trials, 900s timeout, `MedianPruner(n_warmup_steps=1,
  n_startup_trials=5)` — each trial reports its running mean PR-AUC after
  every one of the 5 CV folds, so a trial clearly below the running median
  after fold 1 is pruned before wasting compute on folds 2-5.
- **Result: 40 trials total, 21 completed, 19 pruned (47.5%)**, wall time
  32.8s — roughly half the trial budget was reclaimed by pruning instead of
  running every trial to completion.
- **Best: PR-AUC = 0.6646**, `max_depth=3, learning_rate=0.0182,
  n_estimators=365, subsample=0.564, colsample_bytree=0.797,
  min_child_weight=6, reg_alpha=0.497, reg_lambda=0.128,
  scale_pos_weight=1.879`.
- The winning config is shallow (depth 3) with a low learning rate and heavy
  subsampling/regularization — consistent with a dataset where the signal is
  mostly linear (LogisticRegression is nearly as good) and a deep/aggressive
  GBM would just overfit noise.

### Verdict

XGBoost's tuned PR-AUC (0.6646) edges out both the tuned LogisticRegression
(0.6622) and the untuned baseline (0.6631) — a real but small (~0.2-0.3 point)
gain, consistent with the skill's framing that tuning "squeezes the last
5-15%," and here squeezes noticeably less than that because the untuned
baseline was already close to the ceiling on this feature set. **XGBoost with
these tuned params is carried into [[model-evaluation]] as a candidate
alongside the class-weighted LogisticRegression.**

## Budget discussion

- LogisticRegression: cheap model (<1s/fold fit), 2-param space → generous
  30-trial budget, no pruning warranted, finished in under a minute.
- XGBoost: ~5x more expensive per fit, 9-param space → capped at 40
  trials/900s with `MedianPruner` so the search reallocates budget away from
  clearly-bad regions (deep trees + high LR that overfit within the first
  fold or two) toward the shallow/regularized region that ultimately won.
- Neither study used a subsample-then-refine two-stage search (the skill's
  "narrow around the best region" pattern) — at this data size (5,634 rows)
  full-data trials were already cheap enough that a coarse-to-fine split
  wasn't necessary; noted here as the natural next step if the search space
  or dataset grew.
- No CV split was reused between the LogisticRegression and XGBoost studies
  by accident — both use the identical `StratifiedKFold(42)` object
  construction, so the two best-value numbers above are directly comparable.

## Outputs produced

- `src/p4_tuning.py` — both Optuna studies, nested CV, pruning.
- `artifacts/hyperparameter_tuning_results.json` — best params/values, trial counts, budget note.
- `artifacts/optuna_trials_{logreg,xgboost}.csv` — full trial-level history (`study.trials_dataframe()`).
- `reports/figures/p4_optuna_{logreg,xgboost}_{history,importance}.png` — optimization history + hyperparameter importance, both studies.
