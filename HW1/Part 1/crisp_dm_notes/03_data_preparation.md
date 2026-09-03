# Phase 3 — Data Preparation

## Stage 1: row-preserving structured, text, sentiment, and metadata join

`pipeline/build_stage1_feature_table.py` builds
`pipeline/data/listing_features_stage1.csv` from the raw labeled CSV plus
`train_sentiment/` and `train_metadata/`. It uses `PetID` exclusively as a
one-to-one join key and performs no target encoding, scaling, clipping,
imputation, or model fitting.

Verification after the build:

- Output shape: 14,993 rows × 43 columns.
- `PetID` remains unique (0 duplicates); every original training row is retained.
- The table adds 19 row-local or supplementary features.
- Metadata image count matches raw `PhotoAmt` for all 14,652 covered listings;
  it is retained in this audit table to validate the join but must be excluded
  from future model features to avoid duplication.

### Row-local text features

The table retains original `Name` and `Description` for later train-fold text
processing and adds `name_available`, `description_available`,
`name_char_count`, `description_char_count`, and `description_word_count`.
These features are row-local and safe to calculate before splitting.

### Sentiment features

`sentiment_available`, `sentiment_score`, `sentiment_magnitude`,
`sentiment_sentence_count`, `sentiment_token_count`, and
`sentiment_entity_count` are extracted from the per-listing JSON. The 551
unavailable records retain missing derived values and availability = 0; they
have not been globally imputed.

### Image-metadata features

`metadata_available`, `metadata_image_count`,
`vision_labels_per_image_mean`, `vision_label_score_mean`,
`vision_label_score_max`, `vision_unique_label_count`,
`vision_colors_per_image_mean`, and `vision_crop_hints_per_image_mean` are
aggregated over all available listing photos. The 341 listings without metadata
retain missing derived values and availability = 0.

## Leakage and missingness controls

1. `PetID` will be removed from every model input after joins are complete.
2. `AdoptionSpeed` is never used to compute a feature.
3. Missing modality values will be imputed inside each training fold only, with
   their availability indicators retained.
4. Raw descriptions/names will not be TF-IDF vectorized until after each split;
   vocabulary, IDF, dimensionality reduction, and feature selection must be
   fit on training partitions only.
5. Full pixel-derived features are not in the Stage 1 table yet. They will be
   computed and aggregated per listing in the next compute-limited preparation
   chunk.

## Next activity

Define the model-ready feature policy: remove redundant/identifier fields,
specify train-fold transformations, and set feature-family ablations before any
model fitting.

## Stage 2: full direct-image aggregation

`pipeline/build_image_pixel_features.py` processed all 58,311 files in
`train_images/` without using the target. Each image is resized in memory to at
most 128 × 128 pixels for descriptive measurement, then original width/height,
aspect ratio, resolution, brightness, contrast, colorfulness, and edge-variance
proxies are calculated. Per-listing mean and maximum values are aggregated
across every available photo; aspect-ratio standard deviation is also retained.

Outputs:

- `pipeline/data/image_pixel_features.csv`: 14,652 covered listings × 20 columns.
- `pipeline/data/listing_features_stage2.csv`: 14,993 listings × 62 columns.
- `pipeline/data/unreadable_train_images.csv`: data-quality log (0 unreadable files in this run).

Verification:

- Stage 2 retains all 14,993 rows with unique `PetID`s and preserves every
  Stage 1 column.
- Image-pixel coverage is 14,652 listings (97.73%); 341 retain
  `image_pixels_available = 0` and missing pixel-derived values.
- `image_pixels_count` matches `PhotoAmt` exactly for every covered listing. It
  is a join check only and must not coexist with `PhotoAmt` as a model feature.
- Across covered listings, median aggregated brightness is 119.70, contrast
  55.86, colorfulness 29.46, and edge variance 2,722.86. These are descriptive
  proxies, not validated image-quality scores.

## Direct-image feature handling rules

1. Retain the `image_pixels_available` indicator and do not drop the 341
   image-less listings.
2. Exclude `image_pixels_count` and `metadata_image_count` from model inputs;
   `PhotoAmt` is their exact duplicate.
3. Treat all pixel features as continuous candidates. Fit any clipping/scaling
   only on a training fold; preserve raw Stage 2 values in the audit artifact.
4. Do not claim that brightness, sharpness, or colorfulness are aesthetic or
   causal drivers of adoption. Their value must be established by held-out
   evaluation.

## Model-ready feature policy and fold-safe pipeline

The executable policy is implemented in `pipeline/helpers/fold_safe_features.py`
and checked by `archived/validate_fold_safe_features.py`. The checker
uses one fixed `StratifiedShuffleSplit` (20% validation; seed 2026) only to
verify transformations; it does not train or evaluate a predictive model.

### Excluded from model inputs

- `AdoptionSpeed`: target only.
- `PetID`: join identifier only.
- `RescuerID`: excluded from initial models because of high cardinality and the
  observed rescuer-overlap validation risk. It may be considered later only in
  a separately reported grouped-validation experiment.
- `metadata_image_count` and `image_pixels_count`: exact duplicates of
  `PhotoAmt`.

### Feature families

| Family | Initial contents | Processing |
|---|---|---|
| Core categorical | pet type, breed/color codes, sex, size, fur, care status, health, state | Most-frequent imputation plus one-hot encoding; unknown validation categories ignored. |
| Core numeric | age, quantity, fee, photo/video count | Median imputation with missing indicators; robust scaling for linear models. |
| Text shape | availability and name/description length/count features | Same numeric pipeline. |
| Sentiment | availability, score/magnitude, sentence/token/entity counts | Same numeric pipeline. |
| Vision metadata | availability and label/confidence/label-diversity/crop summaries | Same numeric pipeline. |
| Direct image pixels | availability and aggregated geometry/brightness/contrast/color/detail measures | Same numeric pipeline. |
| Raw text | `Name` and `Description` | Training-fold TF-IDF word/bi-gram vocabulary (max 8,000 terms; `min_df=2`; sublinear term frequency). |

The resulting tabular and text sparse matrices are concatenated only after both
components have been fit on the same training partition. The test transform
produced 8,424 features for 11,994 training and 2,999 validation rows, with an
8,000-term training-only TF-IDF vocabulary. All rows are preserved.

### Feature-family ablation plan

Evaluate in this order using the same cross-validation folds:

1. Core categorical + core numeric.
2. Add text-shape features.
3. Add supplied sentiment features.
4. Add metadata and direct-image-pixel features.
5. Add raw-text TF-IDF.
6. Later, add frozen image embeddings as a separate visual feature family.

Each step must demonstrate an out-of-fold improvement before it remains in the
recommended model. The definitive comparison protocol will use stratified and
rescuer-grouped cross-validation, not this single development split.

## Stage 3: frozen ResNet18 image embeddings (Chunk 14)

`pipeline/build_image_embedding_features.py` extracts a frozen,
ImageNet-pretrained ResNet18 penultimate-layer embedding (512-dim,
average-pooled) for up to the first three photos per listing, using
`torch`/`torchvision` (installed for this chunk; not previously present) with
Apple Silicon MPS acceleration. The network is frozen — not fine-tuned on
this dataset or its labels — so the embeddings are computed once globally,
the same treatment as the Stage 2 pixel features, not per CV fold.

Two pooling variants come from a single pass over the same up-to-three
images per listing:

- `primary`: the first available photo's embedding only.
- `capped3_mean`: the mean-pooled embedding across whichever of the first
  three photos are actually present.

Verification after the build:

- 35,288 images embedded (capped at 3/listing) across all 14,993 listings;
  0 unreadable files.
- Coverage: 14,652 listings (97.73%) — identical to the Stage 2
  `image_pixels_available` coverage, as expected (both derive from the same
  underlying photo availability). The remaining 341 listings have no
  embedding and are not dropped.
- Every covered listing's primary-image embedding was available (no case of
  image 1 missing while images 2-3 exist).

Storage: raw embeddings are saved as `pipeline/data/image_embeddings_resnet18.npz`
(54.1 MB, float32) rather than merged as CSV columns into a Stage 3 table —
14,652 x 512 x 2 variants as CSV text would be roughly 200 MB, whereas the
binary array format holds both variants at a fraction of that. A small
`pipeline/data/image_embedding_meta.csv` records per-listing availability
and image count for inspection without loading the full array. This is a
deliberate departure from the Stage 1/2 CSV-merge convention for this one
high-dimensional feature family, not an oversight.

`pipeline/helpers/image_embedding_features.py` loads the store once and
returns a raw (n_rows, 512) array aligned to a frame's `PetID`s, NaN (never
zero) for uncovered listings. `pipeline/helpers/tree_fold_safe_features.py`
was extended to consume this: PCA reduction of the raw embeddings to a
compact dense block is a *learned* transform and is fit inside each training
fold only (mean-imputed, then PCA to 50 components by default), exactly like
the existing text TF-IDF-to-SVD block. See Chunk 14 in
`crisp_dm_notes/04_modeling.md` for whether this feature family earned its
place.
