---
skill: sklearn-pipelines
pack: param087/agent-ml-skills
crisp_dm_phase: 3 - Data Preparation
artifacts:
  - src/p3_pipeline.py
  - artifacts/preprocessor.joblib
  - artifacts/prepared_feature_manifest.json
  - artifacts/pipeline_leakage_proof.md
---

# sklearn-pipelines

## What the skill prescribes

Chain preprocessing and the estimator into one `Pipeline`/`ColumnTransformer` object so every
fit happens on training folds only, making leakage structurally impossible and the model
trivially serializable. Custom transformers subclass `BaseEstimator, TransformerMixin`. Combine
with `cross_val_score`/`StratifiedKFold` so preprocessing is refit inside every fold.

## Applied to Telco churn — THE deliverable other phases depend on

`src/p3_pipeline.py` exposes:
- **`FeatureEngineer`** — a custom `BaseEstimator, TransformerMixin` that runs the SAME cleaning
  (tenure==0 → TotalCharges=0, sentinel collapse) and engineering (all 9 features from the
  feature-engineering step) as fit/transform logic, so it executes inside cross-validation and
  inside the saved artifact — this is the skill's anti-leakage point applied literally: no
  statistic or encoding is ever computed on data the model will later be scored on.
- **`build_preprocessor()`** → unfitted `Pipeline([("engineer", FeatureEngineer()), ("prep",
  ColumnTransformer(...))])`. Numeric branch: median impute + `StandardScaler`. Categorical
  branch: most-frequent impute + `OneHotEncoder(handle_unknown="ignore")`. `customerID` is
  excluded by construction (never selected by the ColumnTransformer).
- **`FEATURE_SPEC`** — dict of raw/engineered numeric and categorical column roles.

Fitted on `train_clean.csv` (5,634 × 19 raw columns) → **57 output features**
(`artifacts/prepared_feature_manifest.json`).

### Leakage proof (`src/p3_sklearn_pipelines_demo.py`)

**Mechanism** — fold-statistic drift: the naive approach freezes numeric medians from all 5,634
train rows once; proper CV refits on each fold's ~4,507-row portion. Largest drift: TotalCharges
median differs by up to 9.7 (full-data median 1394.9, feature std ≈2,300) between a fold and the
full set.

**Cross-validated ROC AUC, proper (preprocessing refit every fold) vs naive (preprocessing fit
once on all of train, then CV'd on the frozen matrix)**, `LogisticRegression`, `StratifiedKFold(5)`:

| | Mean AUC | Std |
|---|---|---|
| Proper (leakage-safe) | **0.84761** | 0.01138 |
| Naive (fit-on-all) | **0.84759** | 0.01136 |
| Difference (naive − proper) | **−0.00002** | within CV noise |

The gap is statistically indistinguishable from zero **for this dataset's numeric/categorical
columns** — there's no rare-category or heavy-tailed column here for the leakage to bite on. This
null result is cross-referenced against the feature-engineering step's target-encoding demo
(`artifacts/target_encoding_leakage_demo.json`), where the identical naive-vs-proper mechanism
inflates AUC by 0.0075 on the real target and manufactures 0.02 AUC of pure noise on a shuffled
target — same mechanism, different magnitude, because target encoding's per-category statistic
overfits far more easily than a global median/OHE vocabulary. This is why the skill's rule is
structural (always fit inside Pipeline/CV) rather than a case-by-case judgment call.

## Outputs produced

- `src/p3_pipeline.py` — importable `build_preprocessor()` + `FEATURE_SPEC` for downstream phases.
- `artifacts/preprocessor.joblib` — fitted-on-train preprocessing pipeline.
- `artifacts/prepared_feature_manifest.json` — 57 final feature names.
- `artifacts/pipeline_leakage_proof.md` — fold-drift table + proper-vs-naive AUC comparison.
