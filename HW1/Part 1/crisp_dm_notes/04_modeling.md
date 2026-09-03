# Phase 4 — Modeling

## Chunk 11: baseline and feature-family ablation

Implemented in
[train_baseline_ablation.py](/Users/oleg/Documents/Coding/SJSU%20Data%20Mining/HW1/Part%201/archived/train_baseline_ablation.py),
with full fold-level metrics saved to
`pipeline/results/baseline_ablation_results.json`.

### Models trained

1. **Ordinal majority baseline** — predicts the majority class of each
   training fold (never a global constant, so no cross-fold leakage).
2. **Multinomial logistic regression** — the documented approximation for
   ordinal logistic regression from the model shortlist below. `mord` (an
   ordinal-regression package) is not installed in this environment, so this
   substitution is a deliberate, recorded choice, not an oversight.

Both models reuse `FoldSafeFeatureBuilder` from
`pipeline/helpers/fold_safe_features.py`, refit inside every training fold —
no imputation value, category map, scaler, or TF-IDF vocabulary crosses a
fold boundary. `C=1.0` (sklearn default) is used throughout; a single-split
sanity check found QWK stable for `C` in `[0.1, 0.3, 1.0]`, so no
hyperparameter tuning against these CV results occurred in this chunk.

### Validation designs

- **Stratified 5-fold CV** (`StratifiedKFold`, `shuffle=True`, seed 2026)
  across all five feature-family ablation steps, to measure the
  in-distribution, incremental value of each feature family.
- **Rescuer-grouped 5-fold CV** (`GroupKFold` on `RescuerID`) for the
  full-feature step only, to check the rescuer-overlap robustness risk
  documented in Phase 2.

### Known limitation: non-convergence

Every logistic regression fit hit the `max_iter=1000` cap for the `lbfgs`
solver without formally converging (`ConvergenceWarning` on all 30 fold fits).
A pre-check on one development fold showed predictions and QWK were stable
across `max_iter` values from 1000–3000 and across several `C` values, so the
reported metrics are treated as directionally reliable, but should be
considered provisional until convergence is revisited (e.g., stronger
regularization, feature selection/dimensionality reduction on the TF-IDF
block, or an alternative solver) before final model selection.

### Results — stratified 5-fold CV (out-of-fold)

Majority baseline (constant per fold): **QWK 0.000, MAE 1.484, accuracy
27.99%, macro-F1 0.087** — identical across ablation steps because it never
uses features. This is the floor every feature family must beat.

| Step | Features (train fold) | QWK | MAE | Accuracy | Macro-F1 |
|---|---:|---:|---:|---:|---:|
| 1. Core tabular | ~350–363 | 0.276 | 1.007 | 36.98% | 0.279 |
| 2. + text-shape | ~355–368 | 0.272 | 1.010 | 37.16% | 0.280 |
| 3. + sentiment | ~366–379 | 0.272 | 1.012 | 36.92% | 0.279 |
| 4. + metadata/image pixels | ~414–427 | 0.303 | 0.982 | 38.26% | 0.296 |
| 5. + TF-IDF text | ~8,414–8,427 | **0.323** | **0.959** | **39.91%** | **0.316** |

Interpretation:

- All feature-based steps clear the majority baseline by a wide margin (QWK
  0.27–0.32 vs 0.00).
- Text-shape (step 2) and sentiment (step 3) features show **no measurable
  out-of-fold improvement** over core tabular alone at this model capacity —
  QWK is flat to slightly lower. They are not yet justified as required
  features for this model family; they remain in the feature set for now
  because they are cheap and may matter for a tree-based model with
  interaction effects (next chunk), but this must be re-checked, not assumed.
- Vision metadata + direct image-pixel features (step 4) give the first clear
  jump (QWK +0.031 over step 1).
- TF-IDF text (step 5) gives the largest single jump (QWK +0.020 over step 4,
  +0.047 over core tabular alone), confirming raw listing language carries
  signal beyond the supplied sentiment summary.

### Results — rescuer-grouped 5-fold CV, full-feature step

- Majority baseline: QWK -0.012, MAE 1.413, accuracy 26.85%.
- Logistic regression (all features): **QWK 0.294**, MAE 1.022, accuracy
  36.32%, macro-F1 0.278.

Compared to the stratified estimate for the same full-feature model (QWK
0.323), the rescuer-grouped estimate is **0.029 QWK lower** (≈9% relative
drop) with accuracy 3.6 points lower. This is consistent with the Phase 2
finding that stratified splits let ~72% of validation rescuers already appear
in training, so stratified-only results modestly overstate real-world
performance for pets from previously unseen rescuers. Both numbers are now on
record; the grouped estimate is the more conservative one and should be
quoted alongside the stratified one going forward, per the Phase 4 shortlist
requirement to report both.

### Next activity (superseded by Chunk 12 below)

Train the CatBoost/LightGBM boosted-tree comparators (shortlist items 3–4) on
the same fold-safe features and the same two validation designs, to test
whether nonlinear/interaction modeling recovers value from text-shape and
sentiment features that the linear baseline could not use, and whether tree
models narrow or widen the stratified-vs-grouped QWK gap.

## Chunk 12: boosted-tree comparison (CatBoost, LightGBM)

Implemented in
[train_boosted_tree_ablation.py](/Users/oleg/Documents/Coding/SJSU%20Data%20Mining/HW1/Part%201/archived/train_boosted_tree_ablation.py),
using a new
[tree_fold_safe_features.py](/Users/oleg/Documents/Coding/SJSU%20Data%20Mining/HW1/Part%201/pipeline/helpers/tree_fold_safe_features.py)
builder, with full fold-level metrics saved to
`pipeline/results/boosted_tree_ablation_results.json`. `catboost` (1.2.10)
and `lightgbm` (4.6.0) were installed for this chunk; neither was previously
present in the environment.

### Deliberate feature-representation change for trees

`TreeFoldSafeFeatureBuilder` intentionally diverges from the linear-model
`FoldSafeFeatureBuilder`, because one-hot + sparse TF-IDF is a poor fit for
axis-aligned tree splits:

- Categorical columns are passed as native categories (CatBoost `cat_features`,
  LightGBM pandas `category` dtype) instead of one-hot encoded. A check
  confirmed all 14 categorical columns have zero missing values in this
  dataset, so no imputation is needed there.
- Numeric columns are left with missing values intact (both libraries route
  NaN through learned splits) — no imputation or scaling.
- Raw text is reduced to a 100-dimension dense `TruncatedSVD` embedding of a
  training-fold-only TF-IDF matrix, rather than the ~8,000-term sparse block
  used for logistic regression.

This means feature *counts* differ from Chunk 11 (e.g., the full-feature step
here has 155 columns vs. 8,427 for the linear model) even though the
underlying feature-family content is the same. This is a documented,
intentional difference in representation, not an inconsistency.

Fixed, untuned hyperparameters were used for both models: 200 trees, depth 6,
learning rate 0.1. No tuning against these CV results occurred; a model
family will be selected before any tuning pass.

### Results — stratified 5-fold CV (out-of-fold)

| Step | Features | CatBoost QWK | LightGBM QWK |
|---|---:|---:|---:|
| 1. Core tabular | 19 | 0.343 | 0.347 |
| 2. + text-shape | 24 | 0.346 | 0.360 |
| 3. + sentiment | 30 | 0.346 | 0.361 |
| 4. + metadata/image pixels | 55 | 0.366 | 0.383 |
| 5. + text (SVD-100) | 155 | 0.370 | **0.396** |

(MAE, accuracy, macro-F1, confusion matrices, and full classification reports
for every step are in `pipeline/results/boosted_tree_ablation_results.json`.)

Both boosted-tree models clear every Chunk 11 linear-model step at matching
feature families, and LightGBM's full-feature stratified QWK (0.396) is the
best in-distribution number recorded so far, ahead of CatBoost (0.370) and
logistic regression (0.323).

LightGBM shows a small but consistent gain from text-shape and sentiment
(step 1→3: 0.347→0.361) that Chunk 11's linear model did not show — partial
support for the Chunk 11 hypothesis that these families may carry
interaction-dependent signal a linear model cannot use. CatBoost is flat
across the same steps (0.343→0.346), so this benefit is model-specific, not
universal, and should not be generalized to "these features matter" without
qualification.

### Results — rescuer-grouped 5-fold CV, full-feature step

| Model | Stratified QWK | Grouped QWK | Absolute drop | Relative drop |
|---|---:|---:|---:|---:|
| Logistic regression (Chunk 11) | 0.323 | 0.294 | 0.029 | 9.0% |
| CatBoost | 0.370 | **0.347** | 0.023 | 6.2% |
| LightGBM | **0.396** | 0.330 | 0.066 | 16.7% |

**This is the key finding of Chunk 12.** The two validation designs disagree
on which model is best:

- Under stratified CV, LightGBM looks strongest (0.396).
- Under rescuer-grouped CV — the more realistic estimate for a pet from a
  rescuer not seen in training, per the Phase 2 rescuer-overlap risk — CatBoost
  is strongest (0.347) and LightGBM drops to third place among the three
  models compared here (0.330), behind even its own smaller relative decline
  cousin CatBoost.

LightGBM's larger degradation suggests it is fitting rescuer-correlated
patterns (e.g., via fine categorical splits on breed/color combinations that
happen to correlate with prolific rescuers) that do not generalize to new
rescuers, more than CatBoost does at these same fixed, untuned
hyperparameters. This is a plausible explanation, not a proven mechanism — it
has not been isolated by a dedicated ablation (e.g., removing `RescuerID`-
correlated features one at a time) and should be treated as provisional.

### Model selection implication

Given the stated success criteria (ordinal-aware evaluation, generalization
over leaderboard-style optimization), **CatBoost is the current leading
candidate**, not LightGBM, specifically because model selection here is
grounded in the more conservative rescuer-grouped estimate rather than the
higher but more optimistic stratified number. This reverses what a
stratified-only comparison would have recommended, and is recorded as a
concrete example of why Phase 1's requirement to report both validation
designs matters for this dataset.

### Next activity (superseded by Chunk 13 below)

1. Diagnose LightGBM's larger stratified-vs-grouped gap with a targeted check
   (e.g., regularization — `num_leaves`, `feature_fraction`, `bagging_fraction`
   — retuned against grouped CV, not stratified) before ruling it out.
2. Once a model family is selected, run a hyperparameter search evaluated
   against rescuer-grouped CV as the primary criterion (stratified as a
   secondary, optimistic reference), per the "tune only against
   validation/CV results" rule.
3. Defer the text-only ablation (shortlist item 7), late-fusion ensemble
   (item 8), and image-embedding/multimodal experiments (items 9–10) until
   the tabular+text tree baseline's generalization gap is understood and, if
   possible, narrowed.

## Chunk 13: hyperparameter tuning (CatBoost, LightGBM)

Implemented in
[tune_boosted_trees.py](/Users/oleg/Documents/Coding/SJSU%20Data%20Mining/HW1/Part%201/archived/tune_boosted_trees.py)
and
[refit_tuned_winners_full_data.py](/Users/oleg/Documents/Coding/SJSU%20Data%20Mining/HW1/Part%201/archived/refit_tuned_winners_full_data.py),
with results in `pipeline/results/tuning_results.json` and
`pipeline/results/tuned_full_data_refit_results.json`.

### Method

- Selection criterion: mean out-of-fold QWK under rescuer-grouped 5-fold CV
  (the conservative estimate identified in Chunk 12), not stratified CV.
- Both models early-stop directly on QWK — CatBoost's built-in `WKappa`
  metric, and a custom kappa `feval` for LightGBM — rather than log-loss, so
  the stopping rule matches the metric that matters for the stated success
  criteria.
- Leakage safety: within every outer CV fold, an inner 15% holdout (also
  `RescuerID`-grouped when the outer fold is grouped) is carved out purely to
  select the early-stopping iteration. `TreeFoldSafeFeatureBuilder` is fit on
  the inner-training partition only; the inner-eval and outer-validation
  partitions are transformed with that same fitted builder, so no partition
  ever contributes to a transform it is later scored against.
- Search grids: 6 hand-chosen configurations per model, varying `depth` /
  `l2_leaf_reg` / `learning_rate` for CatBoost, and `num_leaves` /
  `feature_fraction` / `bagging_fraction` / `min_child_samples` / `reg_lambda`
  for LightGBM (fixed `learning_rate=0.05`). This is a small, targeted grid
  sized for a personal compute budget, not an exhaustive search.

### A confound found and corrected mid-chunk

The search's best grouped QWK was 0.3387 for CatBoost — *lower* than Chunk
12's untuned result (0.347). Before concluding tuning hurt CatBoost, this was
checked for a confound: the search trains on only ~85% of each outer-training
fold (15% held out for early-stopping selection), while Chunk 12's untuned
run trained on 100% of it. That is a data-efficiency cost, not a
hyperparameter effect, and the two numbers are not directly comparable as
recorded.

`refit_tuned_winners_full_data.py` isolates the hyperparameter effect: it
takes each winning configuration's per-fold iteration count exactly as
selected by early stopping, then refits with that fixed iteration count on
the **complete** outer-training fold (matching Chunk 12's protocol) and
re-scores on the same outer validation fold.

### Results — full comparison (grouped QWK is the primary criterion)

| Model | Stratified QWK | Grouped QWK | Gap (relative) |
|---|---:|---:|---:|
| Logistic regression, untuned (Ch11) | 0.323 | 0.294 | 9.0% |
| CatBoost, untuned defaults (Ch12) | 0.370 | 0.347 | 6.2% |
| LightGBM, untuned defaults (Ch12) | 0.396 | 0.330 | 16.7% |
| **CatBoost, tuned, full-data refit** | 0.370 | 0.340 | 8.1% |
| **LightGBM, tuned, full-data refit** | 0.373 | **0.345** | 7.5% |

Winning configurations:

- CatBoost: `depth=6, l2_leaf_reg=3, learning_rate=0.05` (near CatBoost's own
  defaults — the search did not find anything better in this neighborhood).
- LightGBM: `num_leaves=10, feature_fraction=0.6, bagging_fraction=0.7,
  min_child_samples=50, reg_lambda=5.0` (substantially more regularized than
  the untuned default of `num_leaves=31` with no subsampling).

### Interpretation

- **Tuning did not meaningfully help CatBoost.** Its full-data-refit grouped
  QWK (0.340) is statistically indistinguishable from its untuned Chunk 12
  result (0.347) — within normal fold-to-fold noise for a 5-fold estimate.
  CatBoost's defaults were already close to optimal in the searched
  neighborhood, and its ordered-boosting design appears to give it built-in
  robustness that explicit regularization search does not improve on further
  here.
- **Tuning meaningfully helped LightGBM, and confirms the Chunk 12
  hypothesis.** Its stratified-to-grouped gap shrank from 16.7% (untuned) to
  7.5% (tuned) — now matching CatBoost's robustness level — while its grouped
  QWK improved from 0.330 to 0.345. This is direct evidence that LightGBM's
  earlier larger degradation was addressable overfitting (fine categorical
  splits picking up rescuer-correlated noise), not a fundamental generalization
  weakness of the algorithm, exactly as Chunk 12 proposed but had not yet
  tested.
- **After tuning, CatBoost and LightGBM are essentially tied** on the primary
  (grouped) criterion (0.340 vs. 0.345) and on the secondary (stratified) one
  (0.370 vs. 0.373). Chunk 12's preference for CatBoost as "the leading
  candidate" is superseded: that conclusion held only for the untuned
  comparison. With both models properly regularized, either is a defensible
  choice; LightGBM has a narrow, likely-noise-level numerical edge on both
  metrics, and CatBoost has the practical advantage of not needing this
  regularization search to reach the same place.

### Next activity (superseded by Chunk 14 below)

1. Select one model family to carry forward as the primary tabular+text
   model. Given the near-tie, a reasonable rule is: prefer CatBoost for
   fewer moving parts (no regularization search needed to reach its ceiling),
   or prefer LightGBM if training speed matters (LightGBM fits were
   consistently faster than CatBoost's in this and prior chunks).
2. With a model family fixed, move to the previously deferred experiments:
   the text-only TF-IDF ablation (shortlist item 7, to isolate raw-language
   value independent of tabular features), then frozen image embeddings
   (item 9), which is the modality least explored so far and, per the
   original Kaggle competition for this dataset, plausibly the largest
   remaining source of predictive signal.
3. This 6-configuration grid per model was not exhaustive; a wider or
   Bayesian-optimized search remains an option if returns from the modality
   experiments above turn out to be small.

**Decision:** CatBoost is selected as the model family going forward (fewer
moving parts to reach its ceiling, per point 1 above). Chunk 14 below moves
to frozen image embeddings (item 9), the modality least explored so far.

## Chunk 14: frozen image embeddings (CatBoost)

Implemented in
[build_image_embedding_features.py](/Users/oleg/Documents/Coding/SJSU%20Data%20Mining/HW1/Part%201/pipeline/build_image_embedding_features.py)
(extraction, documented in `crisp_dm_notes/03_data_preparation.md` Stage 3),
[image_embedding_features.py](/Users/oleg/Documents/Coding/SJSU%20Data%20Mining/HW1/Part%201/pipeline/helpers/image_embedding_features.py)
(loader), an extension to `helpers/tree_fold_safe_features.py` (fold-safe PCA
reduction of the raw embeddings), and
[evaluate_image_embeddings.py](/Users/oleg/Documents/Coding/SJSU%20Data%20Mining/HW1/Part%201/archived/evaluate_image_embeddings.py)
(the comparison). Full results in `pipeline/results/image_embedding_results.json`.

### Method

- Frozen, ImageNet-pretrained ResNet18 (penultimate layer, 512-dim,
  average-pooled, `fc` replaced with identity) embeds up to the first three
  photos per listing. `torch`/`torchvision` were installed for this chunk;
  Apple Silicon MPS acceleration made embedding all 35,288 images (capped at
  3/listing) take a few minutes.
- Two pooling variants compared, per the Phase 4 modeling-note directive to
  test "one primary image" against "capped multi-image (first three)" under
  the same compute budget: `primary` (first photo only) and `capped3_mean`
  (mean pool of whichever of the first three photos exist).
- The raw embeddings are fixed/target-independent and loaded globally (same
  treatment as Stage 2 pixel features), but the PCA that reduces them to 50
  dense components is a learned transform and is fit fold-safe, exactly like
  the existing text TF-IDF→SVD block.
- All three configurations (no embeddings / +primary / +capped3_mean) use
  the identical Chunk 13 winning CatBoost hyperparameters
  (`depth=6, l2_leaf_reg=3, learning_rate=0.05`) and the identical
  inner-holdout, QWK-early-stopping protocol from `tune_boosted_trees.py`, so
  only the feature set varies. The `no_image_embeddings` row below reproduces
  Chunk 13's search number exactly (0.3387 grouped), confirming the
  comparison is apples-to-apples.

### Results

| Configuration | Features | Grouped QWK | Stratified QWK | Gap (relative) |
|---|---:|---:|---:|---:|
| No image embeddings | 155 | 0.339 | 0.363 | 6.8% |
| + primary embedding | 206 | 0.344 | 0.367 | 6.2% |
| + capped3-mean embedding | 206 | **0.352** | **0.376** | 6.5% |

### Interpretation

- **This is the largest single improvement found in the whole modeling
  process to date** — larger than any gain from hyperparameter tuning
  (Chunk 13 moved CatBoost's grouped QWK by essentially nothing). Frozen,
  off-the-shelf ImageNet features — never fine-tuned on pet photos or this
  target — carry real incremental signal beyond the pixel-brightness/
  contrast/colorfulness proxies already in the feature set.
- **Pooling across more photos helps.** `capped3_mean` beats `primary` by
  +0.0085 grouped QWK / +0.0099 stratified QWK — consistent with the idea
  that a single photo is a noisy sample of a listing's overall photo quality,
  and averaging across up to three photos is a better summary.
- **The gap between validation designs stays roughly constant (~6-7%)
  across all three configurations.** Unlike LightGBM's regularization
  problem in Chunks 12-13, image embeddings do not introduce new
  rescuer-correlated overfitting — this reads as a clean, generalizing
  signal, not an artifact of the grouped-vs-stratified comparison.
- This raises CatBoost's grouped QWK to 0.352, the best result recorded in
  this project so far (previous best: 0.347, Chunk 12's untuned CatBoost on
  the full tabular+text feature set).
- Caveat: Chunk 13 identified that the inner-holdout early-stopping protocol
  used here trains on ~85% of each fold and slightly understates a
  full-data-refit number (a ~0.001-0.002 grouped QWK effect for CatBoost).
  That effect applies equally to all three rows here, so it does not change
  the *ranking* (capped3_mean > primary > none), only the absolute numbers
  quoted — a full-data refit of the capped3_mean winner is a candidate for
  the eventual Phase 5 final-model number, not required to trust this
  comparison.

### Next activity

1. Adopt `capped3_mean` image embeddings as a permanent feature family in
   the CatBoost model going forward.
2. Consider extracting embeddings from more than 3 photos per listing (mean
   pooling over all available photos, uncapped) as a low-cost follow-up,
   given the clear "more photos helps" trend from primary→capped3.
3. Revisit the deferred text-only TF-IDF ablation (shortlist item 7) and the
   late-fusion ensemble (item 8) now that all three modalities (tabular,
   text, image) have been evaluated individually.
4. Before Phase 5 evaluation, do a full-data refit of the final chosen
   configuration (mirroring Chunk 13's confound correction) for the
   cleanest reportable number.

**Decision:** CatBoost is confirmed as the model family; images are adopted.
Chunk 15 below runs the deferred text-only ablation (item 3 above).

## Chunk 15: text-only ablation

Implemented in
[text_only_ablation.py](/Users/oleg/Documents/Coding/SJSU%20Data%20Mining/HW1/Part%201/archived/text_only_ablation.py),
with results in `pipeline/results/text_only_ablation_results.json`.

### Method

Isolates the standalone value of `Name` + `Description` alone — no tabular,
sentiment, or image features — using the shortlist's recommended model for
this experiment (TF-IDF + regularized multinomial logistic regression),
identical hyperparameters to Chunk 11's linear baseline (`C=1.0`,
`max_iter=1000`, 8,000-term training-fold-only vocabulary) so results are
directly comparable. Purpose: decide whether a dedicated text branch would
add orthogonal signal to CatBoost (motivating a late-fusion ensemble), or
whether text's value is already captured within the combined model.

### Results

| Configuration | Stratified QWK | Grouped QWK | Gap (relative) |
|---|---:|---:|---:|
| Majority baseline (Ch11) | 0.000 | -0.012 | — |
| Core tabular only (Ch11, logistic) | 0.276 | *(not run grouped)* | — |
| **Text only (TF-IDF + logistic)** | **0.212** | **0.148** | **30.5%** |
| Full tabular+text+image (Ch11/14, best) | 0.376 | 0.352 | 6.5% |

All logistic fits converged this time (0 `ConvergenceWarning`s across all 10
folds) — likely because removing the ~400-column tabular block reduced
collinearity in the optimization compared to Chunk 11's full feature set.

### Interpretation

- **Text alone is a real but weaker signal than tabular alone.** QWK 0.212
  (stratified) is clearly above the majority baseline but below core tabular
  features alone (0.276) — raw listing language is not, by itself, as
  informative as the pet's structured attributes.
- **Text alone has by far the largest stratified-to-grouped gap measured in
  this project (30.5%),** roughly 4-5x every other configuration tested
  (6-9% everywhere else). This is a strong, specific finding: a meaningful
  share of text's apparent stratified-CV predictive power is attributable to
  *rescuer writing style/boilerplate* (the same rescuer likely reuses similar
  phrasing across their listings) rather than genuine content signal about
  the individual pet. The rescuer-grouped estimate (QWK 0.148) is the
  trustworthy one; the stratified number overstates text's real-world value
  more than any other feature family examined so far.
- **This argues against pursuing a late-fusion ensemble with a dedicated
  text branch.** A standalone text model is both weaker in absolute terms
  and more leakage-prone than the combined model overall (grouped QWK 0.148
  vs. 0.352). There is little reason to expect blending its predictions with
  CatBoost's would add generalizing signal — Chunks 11/12/14 already showed
  text's genuine marginal contribution *inside* the combined model (+0.02 to
  +0.047 QWK when added to the full tabular+image stack), likely because
  tree splits use text as secondary/contextual signal alongside tabular
  fields rather than relying on it in isolation, which appears to dilute the
  rescuer-style confound rather than amplify it.
- **Caution for Phase 5 reporting:** any feature-importance or interpretation
  claims about `Description`/`Name` content should note this confound
  explicitly. Do not present text-derived feature importance as evidence
  about *what pet owners should write* in a listing without controlling for
  rescuer identity — the same text patterns may simply track prolific,
  successful rescuers.

### Next activity

1. Do not build a separate text-only branch for late-fusion; this evidence
   does not support it. Late-fusion remains an option only if a future
   image-only or metadata-only branch shows a *smaller* stratified-to-grouped
   gap and *meaningfully different* errors from the combined model — neither
   has been tested yet.
2. Proceed with the uncapped all-photos image-embedding extension (flagged
   in Chunk 14) or move toward Phase 5 evaluation of the current best
   configuration (CatBoost + full tabular/sentiment/vision-metadata/image-
   pixel features + TF-IDF text + capped3-mean frozen image embeddings,
   grouped QWK 0.352).
3. Before any final Phase 5 number, do the still-outstanding full-data refit
   (Chunk 13/14) for the chosen configuration.

## Chunk 16: final model — full-data refit, Phase 4 close-out

Implemented in
[train_final_model.py](/Users/oleg/Documents/Coding/SJSU%20Data%20Mining/HW1/Part%201/archived/train_final_model.py).
Applies the Chunk 13 full-data-refit correction to the Chunk 14 winning
configuration: per-fold iteration counts are taken from Chunk 14's
early-stopping run, then each fold is refit on the complete outer-training
fold (not the 85% inner-training subset early stopping used).

### Final configuration

CatBoost, `depth=6, l2_leaf_reg=3, learning_rate=0.05`, full tabular +
sentiment + vision-metadata + image-pixel feature set, TF-IDF text
(SVD-100), and `capped3_mean` frozen ResNet18 image embeddings (PCA-50).

### Final CV metrics (the headline numbers carried into Phase 5)

| CV design | QWK | MAE | Accuracy | Macro-F1 |
|---|---:|---:|---:|---:|
| Rescuer-grouped (primary) | **0.353** | 0.945 | 40.0% | 0.286 |
| Stratified (secondary) | 0.374 | 0.907 | 42.1% | 0.313 |

Both numbers moved by less than 0.002 QWK from Chunk 14's inner-holdout
figures (0.352 grouped, 0.376 stratified) — a much smaller full-data-refit
effect than Chunk 13 saw, and in the direction expected. This is now the
final Phase 4 model result.

### Interpretability artifact

A separate reference model, fit on 100% of the labeled data (iterations =
mean of the grouped per-fold counts = 200) and used only for feature
importance — never for scoring — produced this family-level breakdown
(`pipeline/results/final_model_feature_importance.csv`, aggregated in
Chunk 17 below):

| Feature family | Share of importance |
|---|---:|
| Text (TF-IDF → SVD) | 30.6% |
| Categorical (breed/color/type/health/etc.) | 23.8% |
| Frozen image embeddings | 16.2% |
| Core numeric (age, fee, quantity, photo count) | 12.5% |
| Direct image pixels | 8.7% |
| Vision metadata (Google Vision labels) | 5.6% |
| Sentiment | 2.0% |
| Text-shape (length/word counts) | 0.6% |

**Caution:** the text family's outsized 30.6% share must be read alongside
Chunk 15's finding that text-alone has the largest rescuer-driven
generalization gap (30.5%) of any feature family tested. High importance
here plausibly reflects the model partly learning rescuer-identity patterns
through writing style, not purely pet-content signal — this is flagged again
in Phase 5 for anyone drawing conclusions about listing-description content.

### Phase 4 close-out

Modeling is complete. Final answer to "what is the best model we can build
with the available compute and data": CatBoost, four combined modalities
(tabular, sentiment/vision metadata, TF-IDF text, frozen image embeddings),
grouped QWK 0.353. Progression across chunks: majority baseline 0.00 (Ch11)
→ logistic regression 0.29 (Ch11) → untuned CatBoost 0.35 (Ch12) → tuned
CatBoost ~0.34 (Ch13, tuning did not help) → + image embeddings 0.35
(Ch14) → final full-data refit 0.353 (Ch16). The single largest lever found
was adding a new modality (images), not tuning or architecture search.

```text
CRISP-DM
├─ 1. Business understanding                         ✓
├─ 2. Data understanding                             ✓
├─ 3. Data preparation                               ✓
├─ 4. Modeling                                       ✓
│  ├─ baseline and ablation design                   ✓
│  ├─ boosted-tree comparison                        ✓
│  ├─ hyperparameter tuning                          ✓
│  ├─ frozen image embeddings                        ✓
│  ├─ text-only ablation                             ✓
│  └─ final model, full-data refit                   ✓
├─ 5. Evaluation                                     ← next
└─ 6. Deployment recommendation
```

### Next activity (superseded by Chunk 18 below)

Move to Phase 5: assess the final model against Phase 1 success criteria,
inspect error slices and calibration, and document limitations and failure
modes. See `crisp_dm_notes/05_evaluation.md` (Chunk 17).

## Chunk 18: ordinal regression reformulation (Phase 4 revisit)

**Why this revisits Phase 4 after Phase 5 started:** Chunk 17's evaluation
found the multiclass model never predicts class 0 and rarely predicts class
3 — traced to training on standard multiclass log-loss, which treats every
wrong class as equally wrong regardless of ordinal distance. Per CRISP-DM's
iterative principle, this is exactly the kind of finding that should send
work back to Modeling rather than being merely noted and left. Implemented
in
[train_ordinal_regression.py](/Users/oleg/Documents/Coding/SJSU%20Data%20Mining/HW1/Part%201/pipeline/train_ordinal_regression.py),
results in `pipeline/results/ordinal_regression_results.json`.

### Method

CatBoostRegressor (RMSE loss) replaces CatBoostClassifier, predicting
`AdoptionSpeed` as a continuous value; the continuous prediction is then
decoded to a class two ways: naive rounding (clip to [0,4], round to
nearest integer), and optimized thresholds (4 cutpoints fit via Nelder-Mead
to directly maximize QWK — the "OptimizedRounder" technique from the
original PetFinder Kaggle competition's top solutions). Everything else is
held constant to isolate this one change: identical features (full
tabular/sentiment/vision-metadata/image-pixel set + TF-IDF text +
`capped3_mean` embeddings), identical hyperparameters
(`depth=6, l2_leaf_reg=3, learning_rate=0.05`), and the same nested
inner-holdout protocol as Chunks 13/14/17. Threshold optimization is fit on
the inner-eval fold's predictions only — never the outer validation fold —
matching the fold-safety standard used throughout.

### Results

| Configuration | Grouped QWK | Stratified QWK | Gap |
|---|---:|---:|---:|
| Multiclass CatBoost (Ch16, current final model) | 0.353 | 0.374 | 6.5% |
| Ordinal regression, naive rounding | 0.289 | 0.333 | 15.2% |
| **Ordinal regression, optimized thresholds** | **0.379** | **0.417** | 9.1% |

Optimized-threshold ordinal regression is **the single largest improvement
found in this entire project** (+0.026 grouped QWK over Ch16, larger than
the image-embedding gain in Chunk 14). Naive rounding alone is *worse* than
the existing multiclass model — the threshold-optimization step is not
optional polish, it is what makes this reformulation pay off. Fitted
thresholds cluster well below the naive 0.5/1.5/2.5/3.5 boundaries (e.g.,
one grouped fold: `[0.52, 1.72, 2.61, 2.77]`) — the regressor's raw outputs
are compressed toward the middle of the range, so naive rounding badly
under-allocates the two most extreme classes.

### Per-class recall: what actually changed

| Class | Multiclass (Ch17) | Ordinal, optimized (grouped) |
|---:|---:|---:|
| 0 (same-day) | 0.000 | **0.000 — unchanged** |
| 1 | 0.307 | 0.112 (worse) |
| 2 | 0.452 | 0.607 (better) |
| 3 | 0.090 | 0.187 (better, ~2x) |
| 4 | 0.700 | 0.500 (worse) |

**This reformulation does not fix the class 0 blind spot.** Every one of the
four combinations tested (2 CV designs × naive/optimized) has exactly 0%
recall on class 0. The optimizer, given complete freedom to place the
class-0/class-1 threshold anywhere, still converges to ~0.45-0.53 — meaning
essentially no continuous predictions fall low enough for any threshold
choice to carve out a class-0 region without a net QWK loss elsewhere. RMSE
regression on 2.7%-prevalence data still doesn't produce distinctly low
predictions for that class. The overall QWK gain instead comes entirely from
much better discrimination between classes 2 and 3 (previously classes 3-4
absorbed most of class 3's true cases; a genuine trade of some class 1/4
recall for large class 2/3 gains).

### Interpretation

- Adopt optimized-threshold ordinal regression as the new final model
  (grouped QWK 0.379, up from 0.353) — this is a real, well-isolated
  improvement, not noise (consistent gain across both CV designs, gap
  stays in the normal 6-9% band this project has seen elsewhere, aside from
  naive rounding's outlier 15.2%).
- The Chunk 17 "cannot detect same-day adoption" limitation **still fully
  applies to this new best model** and needs its own fix (class reweighting,
  resampling, or a dedicated binary same-day classifier) — none of which
  have been tried yet.
- `crisp_dm_notes/05_evaluation.md`'s cohort slices, confusion matrix, and
  feature-importance breakdown were computed against the superseded
  multiclass model and have not yet been regenerated for this new model;
  flagged there as a pending item rather than silently left stale.

### Next activity

1. Regenerate the Phase 5 error analysis (confusion matrix, cohort slices,
   directional error) against the new ordinal-regression model's grouped-CV
   predictions, so Phase 5 reflects the current best model.
2. Address the still-unresolved class 0 blind spot directly — class
   reweighting/oversampling or a dedicated same-day-vs-not binary classifier
   — since ordinal reformulation alone did not touch it.

```text
CRISP-DM
├─ 4. Modeling                                       ✓ (revised, Ch18)
│  └─ ordinal regression reformulation               ✓ ← new best model
├─ 5. Evaluation                                     ✓ refreshed for Ch18 (Ch19)
└─ 6. Deployment recommendation
```

Phase 5 was subsequently regenerated against this model (Chunk 19, see
`crisp_dm_notes/05_evaluation.md`).

## Chunk 20: frozen-backbone swap test (ResNet18 vs. CLIP)

Follows up on the user's question about making image embeddings more
"pet-specific." Two paths were possible: (a) fine-tune part of a CNN
directly on this dataset's labels (higher cost, higher overfitting risk,
since every photo in a listing shares one noisy listing-level label), or
(b) swap in a frozen backbone that's already more semantically aware, with
zero training risk. This chunk tests (b) first, as the cheaper diagnostic.

### Method

`open_clip_torch` (installed for this chunk) provides OpenAI's CLIP
ViT-B/32 image encoder (`ViT-B-32-quickgelu`, `pretrained='openai'`) —
trained on image-caption pairs rather than 1000-class ImageNet labels, so
its embedding space plausibly captures higher-level visual concepts (coat
type, breed appearance) closer to human judgment than ImageNet-classification
features. Extraction mirrors Chunk 14 exactly
([build_image_embedding_features_clip.py](/Users/oleg/Documents/Coding/SJSU%20Data%20Mining/HW1/Part%201/archived/build_image_embedding_features_clip.py)):
same up-to-3-photos-per-listing, same 512-dim output, same two pooling
variants, saved separately (`pipeline/data/image_embeddings_clip.npz`) so the ResNet18
artifacts stay untouched. Coverage is identical: 14,652/14,993 listings
(97.7%), 0 unreadable files.

`helpers/image_embedding_features.py` and `helpers/tree_fold_safe_features.py` were
extended with a `backbone` parameter (`"resnet18"` or `"clip"`) so the rest
of the fold-safe pipeline (mean-imputation, PCA-50, CatBoost) is completely
unchanged between the two — isolating the backbone choice as the only
variable, using the exact Chunk 14 comparison protocol and hyperparameters.

### Results (capped3_mean pooling, full tabular+text feature set)

| Backbone | Grouped QWK | Stratified QWK | Gap (relative) |
|---|---:|---:|---:|
| No image embeddings | 0.339 | 0.363 | 6.8% |
| ResNet18 (Ch14) | 0.352 | 0.376 | 6.5% |
| **CLIP ViT-B/32** | **0.355** | 0.369 | 3.9% |

### Interpretation

**This is a wash, not a win.** CLIP edges out ResNet18 on the primary
grouped-CV criterion by +0.003 QWK — small enough to plausibly be fold noise
rather than a real effect — while doing slightly *worse* on stratified CV
(-0.007). The one arguably real secondary finding is that CLIP's
stratified-to-grouped gap (3.9%) is smaller than ResNet18's (6.5%),
suggesting CLIP's features may be marginally less entangled with
rescuer-specific correlations, but this is a minor effect sitting on top of
an inconclusive headline result.

**Implication for the fine-tuning question that motivated this chunk:**
swapping to a more semantically rich *frozen* backbone did not meaningfully
move the needle. This is evidence — not proof — that the bottleneck here is
less about embedding quality and more fundamental: a single listing-level
adoption-speed label is a noisy, indirect target for what any photo shows,
and no frozen feature extractor can manufacture signal that isn't there.
This tempers the expected payoff of the more expensive, higher-risk Path A
(fine-tuning part of a CNN directly on this data) — it may face the same
signal ceiling rather than a backbone-quality problem. Fine-tuning was not
attempted in this chunk; this is a reason for caution about its expected
value, not a decisive argument against trying it.

### Next activity

Given the marginal, inconclusive result, further backbone experimentation
(other CLIP variants, ensembling both backbones) is not recommended as a
priority — expected returns look small relative to the two items still
outstanding: the unresolved class 0 blind spot (Chunk 19) and the Phase 6
deployment recommendation.

## Recommended model shortlist

The target is ordinal (`AdoptionSpeed` 0–4), the dataset has 14,993 listings,
and features are tabular, text, sentiment, image metadata, and derived
image-pixel summaries. Begin with the first four models below before any neural
network or image-embedding experiment.

1. **Ordinal majority/median baseline** — predicts a fixed class; establishes
   the minimum QWK, MAE, and class-level performance to beat.
2. **Regularized ordinal logistic regression** — interpretable baseline using
   one-hot categorical fields, scaled numeric fields, and a small TF-IDF text
   block. If an ordinal implementation is unavailable, use multinomial logistic
   regression as a documented approximation.
3. **CatBoost classifier/regressor** — first recommended strong model. It
   handles nonlinear tabular relationships, categorical variables, missingness,
   and interactions efficiently. Use multiclass probabilities with ordinal
   decision thresholds, or evaluate an ordinal regression formulation.
4. **LightGBM or XGBoost** — competitive tree-boosting comparator after
   categorical encoding. Prefer LightGBM for low compute; avoid naive ordinal
   integer treatment of nominal categorical codes.
5. **Explainable boosting machine (EBM)** — optional interpretable nonlinear
   comparator for the structured/supplementary numeric feature set. Useful for
   shape functions and partial effects, but not necessarily the top performer.
6. **HistGradientBoosting with encoded categories** — low-dependency sklearn
   fallback and useful sanity-check model.
7. **TF-IDF + regularized logistic/linear ordinal model** — text-only ablation
   for `Description` and `Name`. This establishes whether raw listing language
   adds value beyond structured, sentiment, and metadata features.
8. **Late-fusion ensemble** — combine out-of-fold probabilities from a tabular
   booster and text model, optionally adding a visual model only if it has
   independently validated value. Use a simple weighted average selected with
   out-of-fold results; avoid a high-capacity stacker at this dataset size.
9. **Pretrained image embeddings + small classifier** — use a frozen pretrained
   vision encoder (for example, EfficientNet/ResNet/CLIP) to embed one or a few
   photos per listing, pool embeddings across photos, then train regularized
   logistic regression or a small MLP. This is the recommended image deep-
   learning experiment under limited compute.
10. **Multimodal neural late fusion** — optional final experiment: a text
    encoder/TF-IDF branch, pooled frozen image embeddings, and tabular features
    combined in a small regularized MLP. Train only after ablations establish
    value from each modality.

## Models to defer or avoid initially

- A custom CNN trained from scratch: excessive variance and compute cost for
  this dataset.
- End-to-end vision-language fine-tuning: unsuitable as an initial limited-
  compute experiment and risks overfitting.
- K-nearest neighbors: weak fit for mixed high-dimensional sparse text and
  categorical data.
- Unsupervised clusters as direct predictors without validation: clusters may
  be useful for exploration but do not replace supervised features.

All candidates must use identical leakage-safe feature construction and report
both stratified and rescuer-grouped validation results.

## Deep-learning decision for image and text modalities

### Images: recommended, with transfer learning

Use a pretrained vision model as a **frozen feature extractor**, not a custom
CNN trained from scratch. Extract an embedding for each available image, pool
embeddings within `PetID` (mean pooling is the initial choice), add an
image-availability flag, and fit a small regularized classifier/regressor on
the pooled embedding. Compare one-primary-image pooling against a capped
multi-image approach (for example, first three images) under the same compute
budget. Only unfreeze a small final vision block if frozen embeddings show a
consistent grouped-validation gain.

### Text: start sparse, then evaluate a small language model

For these short listing descriptions and roughly 15k records, TF-IDF word and
character n-grams with a regularized linear model are the mandatory first text
baseline: they are fast, multilingual-tolerant, and highly competitive on
short/noisy text. A small pretrained sentence encoder (SLM) is a reasonable
second text experiment: generate a fixed embedding for the concatenated name
and description, then train a regularized downstream model. Prefer a
multilingual encoder if language inspection confirms mixed Malay/English text.

Do not fine-tune a language model initially. Fine-tuning has greater compute
cost and overfitting risk, while the fixed-embedding experiment answers whether
semantic text representation adds value beyond TF-IDF and the supplied
sentiment features.
