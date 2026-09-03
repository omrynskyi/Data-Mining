# Model Card — Telco Customer Churn Risk Classifier

## Intended use

Ranks active telecom customers by probability of voluntary churn so the retention team can
prioritize a monthly outreach list under a **limited contact capacity** (this model is
threshold-tuned for ~50% capacity — see below). It is a **prioritization and triage tool**, not
an automated retention-offer dispenser: it does not decide the offer, and it should not be used
to deny service or pricing to any customer. Not validated for any use outside this telecom
churn context, and not validated on data collected after this snapshot.

## Training data

- Source: Kaggle `blastchar/telco-customer-churn` (IBM Telco Customer Churn), local copy
  `data/Telco-Customer-Churn.csv`, SHA-256 `16320c9c1ec72448db59aa0a26a0b95401046bef5d02fd3aeb906448e3055e91`.
- 7,043 customers, single cross-sectional snapshot (no event log, no timestamps).
- Stratified 80/20 split, seed 42 → 5,634 train / 1,409 test. Churn rate 26.537% (train
  26.535%, test 26.544% — stratification held to <0.01pp).
- 11 rows (all `tenure==0`, never billed) have blank `TotalCharges`; handled inside the
  pipeline, not pre-imputed.

## Features

57 features built by `src/p3_pipeline.py:build_preprocessor()` from 19 raw input columns:
median-impute+scale for numerics, most-frequent-impute+one-hot (unknown-safe) for categoricals,
plus a custom `FeatureEngineer` transformer that derives `tenure_bucket`, `avg_monthly_spend`,
`num_addon_services`, `has_internet`, `is_month_to_month`, `is_electronic_check`,
`charges_per_service`, `is_new_customer` and an out-of-fold-encoded interaction — all **inside**
the pipeline so no engineered feature is fit on data it is then scored against.
`customerID` is dropped (identifier, not a feature).

## Model

`CalibratedClassifierCV(sigmoid, cv=5)` wrapping `Pipeline(build_preprocessor() → Optuna-tuned
XGBClassifier)`. Selected over LogisticRegression (tuned and untuned), a `class_weight`-balanced
variant, an in-CV-pipeline SMOTE variant, and a PyTorch MLP — all logged as real MLflow runs
under experiment `churn-classifier` (`artifacts/mlruns/`) and compared on PR-AUC, not accuracy,
because the target is imbalanced (26.5% positive). Registered as `telco-churn-classifier` v1,
stage `Staging`, in the local MLflow model registry.

## Held-out test metrics (n=1,409, from `artifacts/final_metrics.json`)

| metric | value |
|---|---|
| ROC-AUC | 0.8482 |
| PR-AUC (average precision) | 0.6681 |
| Precision @ chosen threshold | 0.5332 |
| Recall @ chosen threshold | 0.7727 |
| F1 @ chosen threshold | 0.6310 |
| Accuracy @ chosen threshold | 0.7601 |
| Brier score (calibration) | 0.1352 |
| Lift @ top 10% | 2.81x |
| Lift @ top 20% | 2.51x |

**No numeric feature exceeds |corr|>0.95 with the target** (checked in Phase 2's leakage audit
and re-verified independently) — a ROC-AUC in the high 0.84s, not >0.90, is the expected honest
range for this dataset; a materially higher score on this data would itself be a leakage red
flag, not a win.

## Chosen threshold

**0.2856**, calibrated for ~50% retention-team contact capacity — i.e., flagging roughly the
top half of customers by risk, not the default 0.5 cutoff, because the target is imbalanced and
a 0.5 cutoff under-flags true churners (see `crisp_dm/05_evaluation/model-evaluation.md` for the
full threshold-sweep and lift/gains analysis). At this threshold: TN=782, FP=253, FN=85, TP=289.

## Business framing

LTV conflict resolved in `crisp_dm/05_evaluation/model-evaluation.md`: the hazard-based LTV
figure ($7,899.96, implying a ~122-month lifetime) is **rejected** as survivorship-biased — no
customer in this right-censored, single-snapshot dataset has been observed past 72 months, and
observed mean tenure is 32.4 months. The evaluation instead uses a bounded revenue-protected-
over-a-decision-horizon framing (details and full EV table in
`artifacts/business_expected_value.json`), with retention-offer cost ($50/contact, assumption)
and save rate (30% of contacted true churners, assumption) both explicitly labelled as
assumptions, not observed data.

## Limitations

- **Single snapshot, not a panel.** No ground truth on why any individual customer churned,
  and no way to validate predictions against a later time period from this data alone.
- **Observational, not causal.** The model predicts churn risk; it does not estimate the causal
  effect of any retention intervention (see the `ab-test-analysis` skill demonstration in
  `crisp_dm/03_data_preparation/ab-test-analysis.md` for why the Contract-type comparison in
  particular cannot be read causally).
- **Threshold is a capacity choice, not a fixed truth.** Change the retention team's real
  contact capacity and the threshold should be re-tuned — it is not a universal 0.2856.
- **No monitoring history yet.** This is a training-time snapshot; there is no production
  traffic to check for drift against (see `model-serving` doc for the drift-monitoring plan).

## Fairness / subgroup performance

From `artifacts/fairness_parity.json` (Phase 5), computed on the held-out test set:

| group | n | base churn rate | recall | precision | PR-AUC |
|---|---:|---:|---:|---:|---:|
| gender = Female | 687 | 0.281 | 0.715 | 0.585 | 0.673 |
| gender = Male | 722 | 0.251 | 0.757 | 0.548 | 0.653 |
| SeniorCitizen = 0 | 1,187 | 0.233 | 0.696 | 0.549 | 0.642 |
| SeniorCitizen = 1 | 222 | 0.441 | 0.847 | 0.610 | 0.711 |

Gender shows no meaningful disparity (recall/precision/PR-AUC all within ~4pp). SeniorCitizen
shows a real gap, but it tracks the underlying **base rate difference** (44.1% vs 23.3% churn)
rather than a spurious model artifact — the model is *more* sensitive (higher recall) for the
group with the higher true churn rate, which is the intended direction, not a fairness failure.
Recommended: monitor this gap in production rather than treat it as settled — a capacity-
constrained threshold applied uniformly could still contact senior citizens at a
disproportionate rate; if that becomes a business concern, a group-aware threshold is the fix,
not a change to the model itself.

## Reproducibility

Seed 42 throughout (`src/p4_repro.py:set_all_seeds`), dataset SHA-256 pinned, environment
frozen at `requirements.txt` (also `artifacts/env_snapshot.txt`). Loading `model.joblib`
requires `src/` on `sys.path` first — the pickled pipeline references the `FeatureEngineer`
class defined in `src/p3_pipeline.py` by module name; see `artifacts/inference_contract.json`
for the exact load and I/O contract.
