---
skill: experiment-tracking
pack: param087/agent-ml-skills
crisp_dm_phase: 4 - Modeling
artifacts: [src/p4_tracking.py, artifacts/mlruns/, artifacts/mlflow_runs_comparison.csv, artifacts/mlflow_runs_comparison.md]
---

## What the skill prescribes

- Untracked experiments are unreproducible: if you cannot answer "which data + code +
  hyperparameters produced this metric?", you have a number, not a result.
- Always log **params** (hyperparameters, architecture, seed, data version/hash), **metrics**
  (per-epoch and final), **artifacts** (model, plots, confusion matrix), **code state** (commit
  SHA / dirty flag), and **environment** (Python/CUDA version, hardware).
- Use `mlflow.set_experiment(...)`, one `mlflow.start_run()` per configuration, and query the
  tracking store afterward with `mlflow.search_runs` rather than eyeballing a UI.
- Cover model-registry basics: register the promotion candidate, transition it through stages.

## Applied to Telco churn

Used a **local, file-backed** MLflow tracking store — `tracking_uri = file:artifacts/mlruns`,
no server, no network — under experiment `churn-classifier`. `src/p4_tracking.py` logs every
model variant produced across Phase 4 as one real run each, sourced from the JSON/artifact
outputs those steps already wrote (`imbalanced_data_comparison.json`,
`hyperparameter_tuning_results.json`, `mlp_vs_sklearn_comparison.json`, `final_metrics.json`,
`mlp_best.pt`), so nothing here is re-fabricated — it is the same numbers already reported
elsewhere in this lab, now captured as reproducible runs.

**7 runs logged**, one per model configuration built this phase:

| run | what it is | key metric |
|---|---|---|
| `baseline_logreg` | LogisticRegression, no imbalance handling | CV PR-AUC 0.6631 |
| `logreg_class_weight_balanced` | + `class_weight='balanced'` | CV PR-AUC 0.6617 |
| `smote_honest_logreg` | SMOTE **inside** the CV pipeline (imblearn) | CV PR-AUC 0.6579 |
| `logreg_optuna_tuned` | Optuna-tuned LogisticRegression | CV PR-AUC 0.6622, test PR-AUC 0.6610, test ROC-AUC 0.8470 |
| `xgboost_optuna_tuned` | Optuna-tuned XGBoost | CV PR-AUC 0.6646, test PR-AUC 0.6621, test ROC-AUC 0.8465 |
| `mlp_torch` | PyTorch MLP on the 57 preprocessed features | test PR-AUC 0.6532, test ROC-AUC 0.8435 |
| `final_calibrated_xgboost` | **final model**: `CalibratedClassifierCV` wrapping the tuned XGBoost pipeline | test PR-AUC 0.6681, test ROC-AUC 0.8482 |

Each run logs params (model type, seed=42, dataset SHA-256, relevant hyperparameters), the
metrics above, tags (`git_sha` unavailable — this project is not a git repo, tagged
`git_sha=not-a-git-repo` instead of silently omitting it), the fitted estimator via
`mlflow.sklearn.log_model`, and the relevant figure (e.g. `p4_mlp_training_curve.png`) as an
artifact. `smote_honest_logreg` additionally carries a `leakage_comparison` tag pointing at the
`imbalanced-data` skill's naive-vs-honest SMOTE finding, so the two skill demonstrations are
cross-referenced rather than siloed.

Calibration and PR-AUC (not accuracy) are the comparison axis throughout, consistent with the
`imbalanced-data` and `model-evaluation` skills applied earlier this lab — a 26.5%-positive
target makes accuracy misleading, and PR-AUC together with the calibration/Brier numbers is what
the retention-campaign business case in Phase 5 actually depends on.

**Run comparison, re-derived by querying the store** (not hand-copied) via
`mlflow.search_runs(experiment_names=["churn-classifier"])` → `artifacts/mlflow_runs_comparison.{csv,md}`:
the final calibrated XGBoost run is the best on every metric that is comparable across runs
(test PR-AUC 0.6681 vs 0.6532–0.6621 for the alternatives), confirming the Phase 5 model choice
independently from inside the tracking store rather than only from the one-off script that
produced it.

**Model registry**: registered `telco-churn-classifier`, version 1, sourced from the
`final_calibrated_xgboost` run's logged model artifact, transitioned `None → Staging`. Verified
by re-querying `mlflow.search_model_versions(filter_string="name='telco-churn-classifier'")`
after the script exited — returns exactly one version, stage `Staging`, confirming the
transition persisted to the file-backed store rather than only existing in-process.

**Limitation, stated plainly**: this project isn't a git repository, so the code-state axis of
the skill (commit SHA, dirty flag) is tagged `not-a-git-repo` rather than fabricated. The
`dataset_sha256` param is logged on every run instead, which is the reproducibility anchor that
actually applies here.

## Outputs produced

- `src/p4_tracking.py` — logs all 7 runs, registers + promotes the final model, exports the
  comparison table by querying the store.
- `artifacts/mlruns/` — the real MLflow file store (7 runs, 1 registered model).
- `artifacts/mlflow_runs_comparison.{csv,md}` — run comparison, produced by `mlflow.search_runs`,
  not hand-assembled.
