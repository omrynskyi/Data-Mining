# Phase 2 — Data Understanding

## Scope and integrity

`train/train.csv` has 14,993 labeled listings and 24 columns. `test/test.csv` has 3,972 listings and 23 columns; `AdoptionSpeed` is the sole schema difference. There are no exact duplicate train rows, duplicate train `PetID`s, or train/test `PetID` overlaps. `PetID` is a join key only, never a model feature.

Missingness: `Name` is missing for 1,265 listings (8.44%); `Description` is missing for 13 (0.09%). No other parsed CSV field is missing.

`RescuerID` has 5,595 levels; 67.6% occur once, and the largest rescuer has 459 listings. Later validation must compare stratified and rescuer-aware designs.

## Supplementary modalities (all included in scope)

| Asset | Files / coverage | Verified use |
|---|---:|---|
| `train_images/` | 58,311 JPEGs; 14,652 listings (97.73%) | Pixel-level aggregates and later pretrained embeddings. |
| `train_metadata/` | 58,311 per-photo JSONs; 14,652 listings (97.73%) | Aggregate vision labels/confidences and image-property summaries. |
| `train_sentiment/` | 14,442 per-listing JSONs (96.32%) | Sentiment, sentence, entity, and availability features. |

Use explicit `sentiment_available`, `metadata_available`, and image-availability flags. Metadata image count exactly equals `PhotoAmt`; retain `PhotoAmt`, and do not duplicate it with metadata count.

## Completed descriptive EDA

- Target mean = 2.516; median = 2.
- Cats: mean 2.40, fast (0–1) 27.6%, slow (3–4) 45.1%; dogs: mean 2.62, fast 19.7%, slow 53.7%. This is associative only.
- Class-4 listings have median age 6 months and mean 13.67 months, versus median 2–3 months for classes 0–3.
- `Fee` is zero for 84.5% of listings; use a zero-fee indicator plus a transformed positive amount later.
- Videos are sparse (96.2% zero); use `has_video` before raw count.
- More photos are not monotonically associated with faster adoption.
- Small-sample groups, including serious-injury listings (n=34), must not support definitive claims.

## Sentiment and metadata audit

For available sentiment JSON: score median 0.30 (95th percentile 0.80), magnitude median 1.60 (95th 5.70), sentence-count median 4, and entity-count median 8. Sentiment score means vary only 0.267–0.301 by target class. The `categories` field is empty in all observed records and should be excluded unless later data differ.

For available metadata: median 3 images/listing; median vision-label confidence 0.78; median 14 unique vision labels/listing. Generic repetitive visual labels (such as dog/cat/breed terms) should be filtered or downweighted later. Dominant-color count is generally capped at 10 and is not informative by itself.

## Direct-image EDA: fixed primary-photo sample

With random seed 2026, sample up to 300 listings per target class and inspect first image only. Of 1,500 selected listings, 1,464 primary images decoded, 36 had no primary image, and no present image was unreadable.

Median width/height are 400/400 pixels; median aspect ratio = 1.00; brightness = 118.39/255; colorfulness proxy = 27.65. Brightness, contrast, and colorfulness have no stable monotonic relation with outcome. Portrait photos are 52.9% of class 4 versus 45.6% of class 0. This supports considering basic visual features, but not any image-quality intervention claim.

## Data-quality decisions carried forward

1. Decode categorical identifiers for descriptive reporting; treat their values categorically in modeling.
2. Treat zero secondary breed/color codes as absence categories after checking label validity.
3. Flag extremes rather than deleting them automatically.
4. Fit clipping, imputation, encoding, scaling, and feature selection only on training folds.
5. Integrate all modalities at listing level through `PetID`; exclude the join key from predictors.

### Correction: primary-breed zero code

The original working assumption addressed zero only in secondary breed/color fields. The code audit found five `Breed1 = 0` records, and `0` is not present in the breed dictionary. Treat `Breed1 = 0` as an explicit unknown-primary-breed category, rather than an invalid value to delete or impute. `Breed2 = 0` occurs 10,762 times and `Color2`/`Color3` zero occur 4,471/10,604 times; those are absent-secondary values. This correction preserves all records.

## Cross-modal distribution and outlier audit

### Structured and text features

IQR rules are not reliable automatic anomaly rules for zero-inflated counts: their upper IQR threshold is zero for `Fee`, `VideoAmt`, and `Quantity`, which would incorrectly flag every positive value. Use quantiles and domain plausibility instead.

| Feature | Median | 95th percentile | 99th percentile | Maximum | Decision |
|---|---:|---:|---:|---:|---|
| Age (months) | 3 | 48 | 84 | 255 | Flag very old ages for review; retain them. Only 6 listings exceed 180 months. |
| Fee | 0 | 150 | 350 | 3,000 | Preserve zero mass; use `fee_is_zero` and a transformed positive amount. |
| Quantity | 1 | 4 | 7 | 20 | Retain; values above 7 occur in 147 listings (0.98%). |
| PhotoAmt | 3 | 10 | 19 | 30 | Retain; values above 19 occur in 133 listings (0.89%). |
| VideoAmt | 0 | 0 | 2 | 8 | Primarily use `has_video`; raw count may be capped/winsorized only within training folds. |
| Description length (characters) | 238 | 971 | 1,810 | 6,664 | Preserve text; derive robust length features and cap only model inputs if necessary. |

The six listings older than 15 years are all in target classes 3–4; this is plausible rather than proof of error. Listings above the 99th percentile of fee have mean speed 2.22 (n=148), while high quantity listings have mean 2.87 (n=147). These small groups are descriptive only and must be evaluated in a multivariable setting.

The full-data boxplot is available at `pipeline/figures/outlier_boxplots.png`; its reproducible generation script is `archived/create_outlier_boxplot.py`. It shows that apparent outliers are primarily expected right tails or zero-inflated counts, not data points to discard.

### Coded-field validity and semantic consistency

- `Color1`, `Color2`, `Color3`, and `State` all use values permitted by their dictionaries (with zero accepted as no secondary color).
- `Breed1` has five zero codes; `Breed2` has no invalid code when zero is accepted as no secondary breed.
- Among nonzero breed assignments, 12 of 14,988 primary breeds (0.08%) and 3 of 4,231 secondary breeds (0.07%) have a dictionary pet-type mismatch. Keep them, add no inferred correction, and retain a possible mismatch flag for later sensitivity analysis.
- All observed codes for type, gender, maturity size, fur length, vaccination, deworming, sterilization, and health are within their expected observed value sets.

### Modality availability is informative but not independent

| Sentiment / metadata / primary image available | Listings | Mean adoption speed | Interpretation |
|---|---:|---:|---|
| Yes / yes / yes | 14,111 | 2.51 | Fully covered majority. |
| No / yes / yes | 541 | 2.39 | Missing sentiment only. |
| Yes / no / no | 331 | 3.09 | Typically no listing image/metadata; likely overlaps with the existing zero-photo signal. |
| No / no / no | 10 | 3.80 | Too small for inference. |

Do not create redundant availability/count variables: metadata and primary-image availability are largely manifestations of `PhotoAmt`. Use availability flags to support safe joins and conditional imputation, then test whether they add value beyond `PhotoAmt` in validation. Keep sentiment availability as a separate candidate feature.

### Missing-modality retention decision

**Do not churn (drop) listings solely because an image, metadata file, or sentiment file is unavailable.** There are 882 rows missing at least one supplementary modality, including 10 with neither metadata/image nor sentiment. Dropping them would reduce the training sample, disproportionately remove image-less listings, and introduce selection bias because missingness is associated with the outcome. Every row retains complete core structured data other than the previously documented name/description missingness.

Preparation policy: retain all listings; add modality-availability indicators; impute derived numeric modality features using training-fold statistics (with a missingness flag); and define image-based aggregate features only where images exist. Evaluate whether availability flags add incremental value beyond `PhotoAmt` and description-derived features.

## Next activity

Relationship-focused visual EDA: compare adoption outcome across age, pet type, and listing/media characteristics with sample-size-aware charts; then inspect rescuer and state group structure before preparation.

## Next activity

Relationship-focused visual EDA and group-structure review are complete; the next activity is to define the preparation plan and leakage-safe validation protocol.

## Relationship-focused EDA and group structure

The reproducible visualization is `pipeline/figures/relationship_eda.png`, generated by `archived/create_relationship_eda.py`. It presents descriptive associations only and labels state estimates with their listing counts.

### Age and pet type

| Age band | Listings | Mean speed | Fast (0–1) | Slow (3–4) |
|---|---:|---:|---:|---:|
| 0–2 months | 5,986 | 2.24 | 29.0% | 38.9% |
| 3–6 months | 4,228 | 2.58 | 21.1% | 52.3% |
| 7–12 months | 1,997 | 2.87 | 15.7% | 62.6% |
| 13–60 months | 2,390 | 2.77 | 20.8% | 60.1% |
| >60 months | 392 | 2.73 | 15.1% | 58.2% |

Adoption speed worsens sharply beyond two months, then does not increase monotonically at older ages. Cats have lower mean speed than dogs in the first three bands (for example 2.06 vs. 2.38 at 0–2 months); the difference reverses slightly at 13–60 months (2.83 vs. 2.75). This pattern indicates that nonlinear age and type-by-age interaction candidates deserve validation, not causal interpretation.

### State context

Selangor (n=8,714) and Kuala Lumpur (n=3,845) dominate the dataset. Estimates for states with small n—especially Labuan (n=3), Sarawak (n=13), and Kelantan (n=15)—are too unstable for standalone recommendations. Encode state categorically and consider pooling rare states; never rank location performance by unadjusted mean alone.

### Rescuer concentration and validation risk

- The top 10 rescuers contribute 1,907 listings (12.72%); the top 100 contribute 4,749 (31.67%).
- 3,783 rescuers have one listing; only 79 have more than 20.
- In one fixed 5-fold stratified split (seed 2026), 72.09% of validation listings have a rescuer that also appears in training. A rescuer-derived feature could therefore produce optimistic results.
- A 5-fold `GroupKFold` by `RescuerID` eliminates rescuer overlap. Its class proportions differ from training by up to 2.59 percentage points in the examined fold, so group-aware performance must be reported with class-distribution context.

Later modeling will use stratified cross-validation for an in-distribution estimate and a rescuer-grouped cross-validation robustness estimate. Rescuer target encodings, if used, must be created out-of-fold and never from validation labels.
