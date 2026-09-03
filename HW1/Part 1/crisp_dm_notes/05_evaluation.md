# Phase 5 — Evaluation

## Chunk 19: refreshed error analysis for the ordinal-regression model (current)

Regenerates Chunk 17's full error analysis against the Chunk 18 model
(CatBoostRegressor, optimized-threshold decoding — grouped QWK 0.379, the
current best), using
[generate_ordinal_model_artifacts.py](/Users/oleg/Documents/Coding/SJSU%20Data%20Mining/HW1/Part%201/pipeline/generate_ordinal_model_artifacts.py)
and
[evaluate_ordinal_model.py](/Users/oleg/Documents/Coding/SJSU%20Data%20Mining/HW1/Part%201/pipeline/evaluate_ordinal_model.py)
(the latter reuses Chunk 17's analysis code directly, parameterized by file
path, so the two evaluations are computed identically). Full results in
`pipeline/results/ordinal_model_error_analysis.json`; confusion matrix at
`pipeline/figures/ordinal_model_confusion_matrix.png`. **This section is the
current reference; Chunk 17 below is retained for historical provenance
only, per this project's supersession-over-deletion convention.**

### Headline metrics vs. success criteria

| Model | Grouped QWK | Stratified QWK | Accuracy |
|---|---:|---:|---:|
| Majority-class baseline | -0.012 | 0.000 | 27.0-28.0% |
| Logistic regression (all features) | 0.294 | 0.323 | 36.3% |
| Multiclass CatBoost (Ch16) | 0.353 | 0.374 | 40.0% |
| **Ordinal regression, optimized thresholds (Ch18, current)** | **0.379** | 0.417 | 36.7% |

Note accuracy *dropped* (40.0% → 36.7%) even though QWK improved — expected
and correct: QWK rewards being ordinally closer even when the exact class is
still wrong, and the previous model's higher accuracy was partly an artifact
of over-predicting the single most common class. QWK, not accuracy, is the
metric Phase 1 designated as primary.

### Per-class performance (grouped CV, out-of-fold)

| True class | Support | Precision | Recall | F1 | Recall (Ch16 multiclass) |
|---:|---:|---:|---:|---:|---:|
| 0 (same-day) | 410 | 0.000 | **0.000** | 0.000 | 0.000 (unchanged) |
| 1 | 3,090 | 0.429 | 0.112 | 0.177 | 0.307 (worse) |
| 2 | 4,037 | 0.320 | 0.607 | 0.419 | 0.452 (better) |
| 3 | 3,259 | 0.227 | **0.187** | 0.205 | 0.090 (~2x better) |
| 4 (100+ days) | 4,197 | 0.544 | 0.500 | 0.521 | 0.700 (worse) |

Macro-F1 0.265; overall accuracy 36.7%. The QWK gain is a genuine trade: less
recall on classes 1 and 4, substantially more on classes 2 and 3 — net
positive because the new errors are ordinally closer on average (confirmed
below).

### Failure mode 1: complete collapse on class 0 (same-day adoption) — CONFIRMED UNCHANGED

**Still never predicted.** Zero of 14,993 grouped-CV predictions are class 0,
matching the multiclass model exactly. Every true class-0 listing is
misclassified — now mostly as class 2 (62%), vs. spread across 1/2/4 before
(row-normalized confusion matrix,
`pipeline/figures/ordinal_model_confusion_matrix.png`): 12% as 1, 62% as 2,
13% as 3, 14% as 4.

This confirms Chunk 18's finding was not a fluke of that chunk's specific
scoring run: the reformulation changes *how* the model errs on rare classes
(more concentrated, now mostly landing on class 2) but does not give it any
ability to *identify* class 0. The practical implication from Chunk 17 is
unchanged and still the binding constraint: **this model must not be used to
identify likely same-day adoptions**, regardless of which of the two
formulations is deployed.

### Failure mode 2: class 3 improved but still weak

Class 3 recall roughly doubled (0.090 → 0.187) — a genuine, meaningful gain
— but precision fell (0.403 → 0.227), so the model now finds more true
class-3 cases at the cost of more false positives from neighboring classes.
Net effect on class 3's F1 (0.147 → 0.205) is a real improvement, not just a
recall/precision trade with no net gain, but class 3 remains the
second-weakest class after 0.

### Systematic directional bias: same shape, tighter spread

Mean (predicted − true) by true class, with standard deviation:

| True class | Mean error | Std (Ch16 multiclass) | Std (Ch18 ordinal) |
|---:|---:|---:|---:|
| 0 | +2.28 (unchanged) | 1.257 | **0.846** |
| 1 | +1.19 | 1.104 | **0.744** |
| 2 | +0.45 | 1.119 | **0.838** |
| 3 | -0.39 | 1.117 | **0.886** |
| 4 | -0.78 | 1.015 | **0.869** |

The mean shrinkage-toward-the-middle pattern is essentially identical in
direction and magnitude to Chunk 17's finding — this is not new. What
changed is the **standard deviation of errors is meaningfully lower for
every class** (e.g., class 0's error std fell from 1.257 to 0.846): the
ordinal model's mistakes are more consistent/concentrated (converging on a
smaller set of neighboring classes) rather than scattered across the full
range. This is consistent with, and helps explain, the QWK improvement:
QWK penalizes squared ordinal distance, so tighter, closer-average errors
score better even when the mean bias is unchanged.

### Cohort error slices (fairness and robustness) — updated

All cohorts still have n > 100. Every cohort's QWK improved with the new
model — the gain from Chunk 18 is broad-based, not concentrated in one
slice — and the *relative* ranking of easy/hard cohorts is essentially
unchanged from Chunk 17, which is reassuring: the reformulation improved the
model without shifting who it works well or poorly for.

| Cohort | n | Grouped QWK (Ch18) | Grouped QWK (Ch16) | Note |
|---|---:|---:|---:|---|
| Dogs (Type 1) | 8,132 | 0.391 | 0.353 | |
| Cats (Type 2) | 6,861 | 0.343 | 0.334 | Still modestly worse than dogs |
| Age 0-2 months | 5,986 | 0.263 | 0.256 | Still weakest age band |
| Age 3-6 months | 4,228 | 0.308 | 0.292 | |
| Age 7-12 months | 1,997 | 0.320 | 0.247 | Largest single-cohort jump |
| Age 13-60 months | 2,390 | 0.405 | 0.336 | |
| Age 60+ months | 392 | 0.411 | 0.376 | Still strongest age band |
| Has ≥1 photo | 14,652 | 0.378 | 0.352 | |
| **No photo at all** | **341** | **0.085** | 0.001 | **Still by far the weakest cohort** |
| Fee charged | 2,330 | 0.404 | 0.371 | |
| Free | 12,663 | 0.375 | 0.349 | |
| Single-listing rescuer | 3,783 | 0.351 | 0.337 | Still no cold-start collapse |
| 2-5 listings | 3,836 | 0.382 | 0.348 | |
| 6-20 listings | 3,015 | 0.365 | 0.328 | Still the weakest rescuer-size band |
| 20+ listings | 4,359 | 0.384 | 0.361 | |

The photo-less cohort moved off literal zero (QWK 0.001 → 0.085) but remains
in a different league from every other cohort (next-lowest is 0.263) — the
Chunk 17 recommendation stands: **do not treat this model's output for a
photo-less listing as informative**, and the case for recommending rescuers
add at least one photo is, if anything, reinforced by having a second model
confirm the same gap. The "younger pets are harder to predict" and "no
rescuer cold-start problem" findings both hold up unchanged in direction.

### Interpretability: feature importance by family — updated

From a Chunk 19 reference regressor (fit on 100% of data, importance only,
never scoring):

| Family | Share (Ch18 ordinal) | Share (Ch16 multiclass) |
|---|---:|---:|
| Text (TF-IDF → SVD) | 31.1% | 30.6% |
| Frozen image embeddings | **22.8%** | 16.2% |
| Categorical | 17.8% | 23.8% |
| Core numeric | 13.7% | 12.5% |
| Direct image pixels | 6.6% | 8.7% |
| Vision metadata | 6.4% | 5.6% |
| Sentiment | 1.0% | 2.0% |
| Text-shape | 0.6% | 0.6% |

Frozen image embeddings gained a substantially larger importance share under
the regression formulation (16.2% → 22.8%), with categorical fields giving
up roughly the same amount — plausibly because a smooth regression target
lets continuous embedding dimensions contribute gradually across many trees,
whereas the multiclass classifier's discrete decision boundaries leaned more
on categorical splits. Text's importance share is essentially unchanged
(30.6% → 31.1%), so **Chunk 15's rescuer-confound caveat applies with equal
force to this new model**: do not read text's high importance as
content-quality guidance without controlling for rescuer identity. Sentiment
and text-shape remain negligible, consistent with every prior chunk.

### Robustness: stratified vs. grouped agreement — updated

The ordinal model's gap is 9.1% relative (0.417 → 0.379) for the optimized
decoding — slightly wider than Chunk 16's multiclass model (6.5%) but still
well within this project's normal 6-9% band for combined-feature models, and
far below the 16.7-30.5% seen for known-overfit configurations (untuned
LightGBM, text-only). Naive rounding's gap was a 15.2% outlier (Chunk 18) —
one more reason the optimized-threshold decoding is the adopted one, not
naive rounding.

### Limitations (consolidated, current)

1. **Cannot detect same-day adoptions at all** (0% recall on class 0) under
   either model formulation tried. This is the most important unresolved
   limitation in the project and needs a dedicated fix (class reweighting,
   resampling, or a separate same-day-vs-not binary classifier) — none tried
   yet.
2. **Class 3 detection improved but remains weak** (19% recall) — the
   ordinal reformulation is a partial, not complete, fix for rare/awkward
   class detection.
3. **QWK ≈ 0.38 (grouped) is fair-to-moderate agreement, not high-precision
   prediction.** Suitable for decision support and triage prioritization,
   not an automated or high-stakes determination about an individual animal.
4. **Photo-less listings are nearly unscored** (QWK 0.085 vs. 0.38 overall,
   2.3% of data).
5. **Text importance is confounded with rescuer identity** in both model
   formulations tested; do not treat feature importance as content-quality
   guidance without controlling for that.
6. **Predictions are associational, not causal.**
7. **No independent held-out test set was reserved** — all estimates are
   from stratified/rescuer-grouped CV on the labeled training data (see
   `crisp_dm_notes/03_data_preparation.md`).

### Next activity

Two live options, not mutually exclusive: (a) move to Phase 6 and write the
deployment recommendation around this model's real capabilities and blind
spots, framing the class 0/3 and photo-less limitations as human-review
triggers; or (b) attempt the still-unresolved class 0 fix (reweighting,
resampling, or a dedicated binary classifier) before finalizing Phase 6,
since "cannot detect the business's most time-sensitive outcome at all" is a
significant enough gap that a deployment recommendation should probably say
which of these was tried, not just that it wasn't.

## Chunk 21: SHAP-based direction analysis (what did the model learn?)

Chunks 16/19's feature importance (CatBoost `PredictionValuesChange`) ranks
features by *how much* they matter but says nothing about *direction*.
Implemented in
[analyze_model_shap.py](/Users/oleg/Documents/Coding/SJSU%20Data%20Mining/HW1/Part%201/pipeline/analyze_model_shap.py),
using CatBoost's built-in SHAP values (Shapley additive explanations) on a
reference model fit on 100% of labeled data (iterations=329, the mean Chunk
18 grouped per-fold count; interpretability only, never used for scoring).
SHAP's top-feature ranking matches `PredictionValuesChange`'s closely (Age,
Breed1, Sterilized top 3 in both), which cross-validates the two importance
measures. Categorical codes are decoded via the official PetFinder data
dictionaries (`breed_labels.csv`, `color_labels.csv`, `state_labels.csv`)
and the standard Kaggle competition code dictionary for
Gender/MaturitySize/FurLength/Vaccinated/Dewormed/Sterilized/Health —
cross-checked first against this dataset's actually observed value sets
(all matched the documented cardinalities exactly, no surprises). Full
per-feature detail in `pipeline/results/model_shap_analysis.json`.

Five charts render these findings visually
([create_shap_charts.py](/Users/oleg/Documents/Coding/SJSU%20Data%20Mining/HW1/Part%201/pipeline/create_shap_charts.py),
`pipeline/figures/shap_chart_1_overall_importance.png` through `_5_state_effects.png`),
using a validated diverging blue/red palette (blue = pushes prediction toward
faster adoption, red = toward slower; `node validate_palette.js` all-checks-pass).

Recall this model predicts a continuous ordinal value where **higher means
slower adoption** — so a positive SHAP contribution pushes a prediction
toward *slower*, and negative pushes toward *faster*.

### Clear, well-supported directional findings

- **Age (strongest numeric driver, Pearson r=0.57 between age and its SHAP
  contribution):** older pets are predicted to adopt slower, monotonically
  across quartiles (mean SHAP -0.22 → -0.07 → +0.19 → +0.26 from youngest to
  oldest quartile). Consistent with the Phase 2 EDA finding that adoption
  speed worsens with age.
- **Quantity (very strong, r=0.89):** listings with more pets (litters/
  groups) are predicted to adopt much slower than single-pet listings —
  intuitive; harder to place multiple animals as a unit.
- **Fee (strong, r=0.70):** higher adoption fees predict slower adoption.
- **Breed1:** the two most common breed codes in the dataset — "Mixed
  Breed" (n=5,923) and "Domestic Short Hair" (n=3,634) — both push toward
  slower predicted adoption, plausibly because they're the least
  distinctive, most competed-against listings. The breeds with the fastest
  predicted adoption are small popular companion breeds (Pug, Yorkshire
  Terrier, Papillon, Cocker Spaniel...), but **every one of these has n
  between 2 and 21** — per the Phase 1/2 small-sample caution, these
  specific breed rankings are not reliable individually and must not be
  read as "get a Pug to adopt faster." The large-sample findings (Mixed
  Breed, Domestic Short Hair being slower) are the trustworthy part of this
  feature's story.

### A counterintuitive, likely-confounded finding

**`Sterilized=Yes` predicts *slower* adoption (mean SHAP +0.149, n=3,101),
and `Sterilized=No` predicts *faster* (mean SHAP -0.070, n=10,077).**
`Vaccinated` shows the same weaker pattern (Yes +0.014, No -0.022). This
runs against the intuition that sterilization/vaccination are adopter-
reassuring positives. The far more plausible explanation, consistent with
everything else this model learned: **sterilization is more common among
pets that have already spent longer in a shelter's care** (shelters often
sterilize during an extended stay, and older pets — already shown to
predict slower adoption — are more likely arrive already sterilized or get
sterilized while waiting). This reads as **an age/tenure confound, not a
causal effect of sterilization status on adoption speed**, and is exactly
the kind of association Phase 1 warned must not be overstated as causal.
**Do not use this finding to argue against sterilizing shelter animals** —
nothing here establishes sterilization slows adoption; it more likely marks
pets that were already going to take longer for other reasons.

### Weaker, secondary directional findings

- **Gender:** male pets predicted modestly faster (mean SHAP -0.041) than
  female (+0.022) or mixed groups (+0.031) — a real but small effect.
- **State:** the states with the highest "slower" mean SHAP include several
  with very thin samples (Sarawak n=13, Terengganu n=26) that Phase 2
  already flagged as too small for standalone claims; only Perak (n=420),
  Pulau Pinang (n=843), and Negeri Sembilan (n=253) have enough listings to
  treat their direction as more than noise, and even those are associational
  regional effects, not necessarily policy-actionable ones.
- **Abstract components** (`img_emb_pca_*`, `text_svd_*`): these are linear
  combinations of 512/8,000 underlying dimensions and have no direct
  real-world interpretation — SHAP confirms several carry real signal
  (`img_emb_pca_2` and `img_emb_pca_4` are the 4th- and 5th-most important
  features overall) but "what visual or textual concept do they represent"
  cannot be answered without extra work (e.g., inspecting which images score
  highest/lowest on that component) that has not been done here.

### Next activity

This deep-dive is complete and ready to inform Phase 6's deployment
recommendation (e.g., the sterilization confound should be called out
explicitly so nobody downstream misreads it as advice). The two items from
Chunk 19 remain open: the class 0 fix, and writing Phase 6 itself.

---

## Chunk 17: final model evaluation (historical — superseded by Chunk 19 above)

Evaluates the Chunk 16 final model (CatBoost; tabular + sentiment +
vision-metadata + image-pixel features + TF-IDF text + `capped3_mean` frozen
image embeddings) against the Phase 1 success criteria, using the
rescuer-grouped 5-fold out-of-fold predictions saved in
`pipeline/results/final_model_oof_predictions.csv` — the more conservative,
deployment-realistic estimate established across Phases 2-4. All analysis
here is read-only (`archived/evaluate_final_model.py`); no model is
retrained or tuned in this phase.

### Headline metrics vs. success criteria

Phase 1 named Quadratic Weighted Kappa (QWK) as the primary ordinal-aware
metric, with class-level error and cohort analysis required because the
same-day class is rare (2.73% of listings).

| Model | Grouped QWK | Stratified QWK | Accuracy |
|---|---:|---:|---:|
| Majority-class baseline | -0.012 | 0.000 | 27.0-28.0% |
| Logistic regression (all features) | 0.294 | 0.323 | 36.3% |
| CatBoost, untuned (Ch12) | 0.347 | 0.370 | — |
| CatBoost, tuned (Ch13) | 0.340 | 0.370 | — |
| **Final model (Ch16)** | **0.353** | 0.374 | **40.0%** |

The final model roughly triples the majority baseline's QWK and clears the
strongest linear baseline by 0.06 QWK. In absolute terms, QWK 0.35 indicates
fair-to-moderate ordinal agreement — a genuinely useful decision-support
signal, not a precise predictor, consistent with Phase 1's framing of this as
an analytical/decision-support tool rather than an automated determination.

### Per-class performance (grouped CV, out-of-fold)

| True class | Support | Precision | Recall | F1 |
|---:|---:|---:|---:|---:|
| 0 (same-day) | 410 | 0.000 | **0.000** | 0.000 |
| 1 | 3,090 | 0.370 | 0.307 | 0.336 |
| 2 | 4,037 | 0.338 | 0.452 | 0.387 |
| 3 | 3,259 | 0.403 | **0.090** | 0.147 |
| 4 (100+ days) | 4,197 | 0.466 | 0.700 | 0.560 |

Macro-F1 0.286; weighted-F1 0.362; overall accuracy 40.0%.

### Failure mode 1: complete collapse on class 0 (same-day adoption)

**The model never predicts class 0.** Across all 14,993 grouped-CV
out-of-fold predictions, `predicted_class == 0` occurs zero times, and the
single highest predicted probability assigned to class 0 anywhere in the
dataset is 0.17 (mean predicted probability 0.028). Every one of the 410
true same-day listings is misclassified, mostly as class 1 or 2 (row-
normalized confusion matrix, `pipeline/figures/final_model_confusion_matrix.png`):
38% predicted as 1, 29% as 2, 31% as 4, 0% as 3.

This is a direct, verified consequence of two compounding factors already on
record: class 0's 2.73% prevalence (Phase 1), and training on standard
multiclass log-loss rather than an ordinal-aware objective (flagged as a
limitation before this evaluation ran). The model has no incentive to ever
select the rarest class over a more common neighbor, because doing so
essentially never reduces the training loss.

**Practical implication:** this model must not be used, as-is, to identify
which pets are likely to be adopted the same day. Any deployment use case
that depends on flagging class 0 requires either a rebalancing strategy
(class weights, oversampling, a decision threshold below pure argmax) or a
dedicated binary "same-day vs. not" model — this has not been built or
evaluated.

### Failure mode 2: near-collapse on class 3

Class 3 recall is 0.090 — the model predicts class 3 for only 724 of 14,993
listings (4.8% of predictions, vs. 21.7% true prevalence), overwhelmingly
routing class-3 cases to class 2 or class 4 instead (39% and 38% of true
class-3 listings respectively, per the confusion matrix). Class 3's
precision when it is predicted (0.403) is comparable to classes 1-2, so the
model is not "guessing badly" when it does choose class 3 — it is simply
choosing it far too rarely.

### Systematic directional bias (regression toward the middle classes)

Mean (predicted − true) by true class:

| True class | Mean error | Interpretation |
|---:|---:|---|
| 0 | **+2.28** | Predicts far slower than actual |
| 1 | +1.18 | Predicts slower than actual |
| 2 | +0.51 | Mild over-prediction of speed-class |
| 3 | -0.29 | Mild under-prediction |
| 4 | -0.63 | Predicts somewhat faster than actual |

This is a textbook shrinkage pattern: predictions for extreme classes (0 and
4) are pulled toward the interior of the scale. Combined with the two
collapse failures above, the model's effective behavior is closer to a
3-way classifier over {1, 2, 4} than a genuine 5-class ordinal model. This
should be stated plainly in any summary of what the model can and cannot do.

### Cohort error slices (fairness and robustness)

All cohorts below have n > 100 (Phase 2's small-sample caution does not
apply to any of them) unless noted.

| Cohort | n | Grouped QWK | Accuracy | Note |
|---|---:|---:|---:|---|
| Dogs (Type 1) | 8,132 | 0.353 | 41.3% | — |
| Cats (Type 2) | 6,861 | 0.334 | 38.6% | Modestly worse for cats |
| Age 0-2 months | 5,986 | 0.256 | 37.8% | Weakest age band |
| Age 3-6 months | 4,228 | 0.292 | 37.3% | |
| Age 7-12 months | 1,997 | 0.247 | 45.5% | Weakest QWK overall |
| Age 13-60 months | 2,390 | 0.336 | 45.9% | |
| Age 60+ months | 392 | 0.376 | 40.6% | Strongest age band |
| Has ≥1 photo | 14,652 | 0.352 | 39.5% | Matches overall (97.7% of data) |
| **No photo at all** | **341** | **0.001** | 62.5% | **Near-zero skill; see below** |
| Fee charged | 2,330 | 0.371 | 40.9% | |
| Free | 12,663 | 0.349 | 39.9% | |
| Single-listing rescuer | 3,783 | 0.337 | 44.6% | No cold-start collapse |
| 2-5 listings | 3,836 | 0.348 | 39.9% | |
| 6-20 listings | 3,015 | 0.328 | 36.3% | Weakest rescuer-size band |
| 20+ listings | 4,359 | 0.361 | 38.8% | Strongest rescuer-size band |

Findings worth acting on:

- **Photo-less listings (n=341, 2.3% of data) get essentially no predictive
  skill from this model (QWK 0.001).** The high accuracy (62.5%) alongside
  near-zero QWK is the classic sign of a model defaulting to one dominant
  class for this subgroup rather than genuinely discriminating — unsurprising,
  since every image-derived feature family (pixels, vision metadata, frozen
  embeddings) is unavailable for these listings and Chunk 15 already showed
  text and tabular data alone are comparatively weak. This is directly
  actionable: **a listing with no photos should not be scored by this model
  as if it were informative**, and it supports a concrete, evidence-based
  recommendation (for Phase 6) that rescuers add at least one photo.
- **Younger pets (0-12 months) are harder to predict than older ones**
  (QWK 0.25-0.29 vs. 0.34-0.38 for 13+ months), the opposite of what "cute
  puppies/kittens get adopted fast and predictably" intuition might suggest.
  This is plausibly explained by higher-variance, less-observable demand
  effects for young animals (litters flooding the market, breed trends) that
  aren't captured by any available feature — an honest limitation, not a
  fixable modeling error.
- **Cats are modestly harder to predict than dogs** (QWK 0.334 vs. 0.353).
  Worth monitoring but not a severe disparity at this sample size.
- **No rescuer-size cold-start problem.** Single-listing (previously-unseen)
  rescuers score close to the overall average (QWK 0.337 vs. 0.353 overall),
  confirming the grouped-CV protocol's core promise: the model generalizes
  reasonably to genuinely new rescuers, not just prolific ones already seen
  in a similar form during training.

### Interpretability: feature importance by family

From the Chunk 16 reference model (fit on 100% of data, used only for
importance, never for scoring):

| Family | Share |
|---|---:|
| Text (TF-IDF → SVD) | 30.6% |
| Categorical (breed/color/type/health/etc.) | 23.8% |
| Frozen image embeddings | 16.2% |
| Core numeric (age, fee, quantity, photo count) | 12.5% |
| Direct image pixels | 8.7% |
| Vision metadata | 5.6% |
| Sentiment | 2.0% |
| Text-shape | 0.6% |

**This must be read together with Chunk 15**, which found text-alone has the
largest rescuer-driven generalization gap (30.5% stratified-to-grouped drop)
of any feature family tested. Text's outsized importance share here plausibly
reflects the model partly learning rescuer-identity/writing-style patterns
alongside genuine content signal. Do not present this importance ranking as
"write better descriptions to get faster adoptions" without that caveat —
the evidence does not cleanly support a content-quality causal claim.
Sentiment and text-shape's near-zero importance (2.0%, 0.6%) is consistent
with their measured lack of out-of-fold benefit since Chunk 11.

### Robustness: stratified vs. grouped agreement

The final model's stratified-to-grouped gap is 6.5% relative (0.374 → 0.353)
— in the normal range established across every combined-feature
configuration in this project (6-9%), and far from the 16.7% seen for
untuned LightGBM (Ch12) or the 30.5% seen for text-only (Ch15). This
particular final configuration does not show evidence of unusual
rescuer-specific overfitting.

### Limitations (consolidated)

1. **Cannot detect same-day adoptions at all** (0% recall on class 0) and
   substantially under-detects class 3 (9% recall). Effective behavior is
   closer to a 3-way {1,2,4} classifier than a 5-class ordinal model.
2. **QWK ≈ 0.35 is fair-to-moderate agreement, not high-precision
   prediction.** Appropriate for decision support and triage prioritization,
   not for an automated or high-stakes determination about an individual
   animal — consistent with the Phase 1 non-causal, decision-support framing.
3. **Photo-less listings are effectively unscored** (QWK ≈ 0, 2.3% of data).
4. **Text importance is confounded with rescuer identity**; do not treat
   feature importance as content-quality guidance without controlling for
   that.
5. **Predictions are associational, not causal.** Nothing here establishes
   that changing a listing's photos, fee, or description *causes* faster
   adoption — only that these features correlate with historical outcomes.
6. **Training objective does not match the evaluation metric.** Standard
   multiclass loss was used throughout; an ordinal-aware loss or class
   reweighting was not tried and is the most direct lever for the class 0/3
   collapse specifically.
7. All CV estimates are on the labeled training data only; no independent
   held-out test set was reserved (see `crisp_dm_notes/03_data_preparation.md`
   for why: this project reused stratified/grouped CV throughout rather than
   introducing a holdout mid-project, which would have made only the final
   chunks' numbers directly comparable to a benchmark the earlier chunks
   never had).

### Next activity

Move to Phase 6: translate these findings into a deployment recommendation —
specifically, how the model should (and should not) be used given the class
0/3 collapse and the photo-less-listing blind spot, what human-review
safeguards are needed, and what a retraining trigger would look like.
