# PetFinder Adoption Speed Prediction

A personal, reproducible CRISP-DM case study on PetFinder.my's Kaggle adoption
dataset: given a shelter/rescue listing's attributes, photos, and description,
predict how quickly the pet will be adopted (`AdoptionSpeed`, 0 = same day
through 4 = not adopted within 100 days). Built as a decision-support and
learning exercise, not an automated determination tool — see
[Limitations](#limitations) before drawing conclusions from it.

**Current best result: Quadratic Weighted Kappa 0.379 (rescuer-grouped CV)** —
roughly 30x better than chance and meaningfully ahead of every simpler
baseline tried. See [Results at a glance](#results-at-a-glance) for the full
model-progression table, and [Limitations](#limitations) for what this model
still cannot do (it never predicts the rarest class).

## Contents

- [Repository map](#repository-map)
- [Setup](#setup)
- [Demo: inspect results without re-running anything](#demo-inspect-results-without-re-running-anything)
- [Walkthrough: full pipeline, in order](#walkthrough-full-pipeline-in-order)
- [Archived: the exploratory and superseded work](#archived-the-exploratory-and-superseded-work)
- [Results at a glance](#results-at-a-glance)
- [Key findings](#key-findings)
- [Limitations](#limitations)
- [Reproducibility notes](#reproducibility-notes)

## Repository map

```
Data Mining/
├── README.md                        ← you are here
├── requirements.txt                 ← pinned Python environment
├── AGENTS.md                        ← methodology/process guidance this project follows
├── Findings.md                      ← standalone narrative write-up (course-report style)
├── crisp_dm_notes/                  ← the full evidence record, one file per CRISP-DM phase
│   ├── README.md                    ← phase index
│   ├── 01_business_understanding.md
│   ├── 02_data_understanding.md
│   ├── 03_data_preparation.md
│   ├── 04_modeling.md               ← every model/experiment tried, in order, with results
│   ├── 05_evaluation.md             ← final model's error analysis, SHAP findings, limitations
│   └── 06_deployment.md
├── pipeline/                         ← only what the current final model needs — start here
│   ├── run_pipeline.py              ← runs the whole thing end-to-end
│   ├── *.py                         ← 10 essential scripts — see the Walkthrough below
│   ├── helpers/                     ← shared library modules — never run directly, only imported
│   ├── data/                        ← intermediate feature tables + image embeddings
│   ├── results/                     ← JSON/CSV results from every experiment (essential + archived)
│   ├── figures/                     ← every chart, including ones archived scripts generate
│   └── logs/                        ← captured stdout from each run
├── archived/                        ← ablations/tuning/comparisons NOT on the final model's
│                                       path, kept for the research record — see below
├── petfinder-adoption-prediction/   ← raw Kaggle dataset (not tracked in git — see .gitignore)
└── transcripts/                     ← full session transcripts (part1 = Codex, part2 = Claude Code)
```

`crisp_dm_notes/` is the authoritative narrative — it explains *why* each
decision was made, in chronological "chunks." This README is a map and quick
reference, not a replacement for it.

## Setup

```bash
python3 -m venv .venv && source .venv/bin/activate   # optional but recommended
pip install -r requirements.txt
```

The raw dataset must be present at `petfinder-adoption-prediction/` (train/test
CSVs, `train_images/`, `train_metadata/`, `train_sentiment/`, and the
breed/color/state label dictionaries) — it's the original Kaggle competition
download, ~2.7GB, and is git-ignored rather than committed.

Every script assumes it's run **from inside `pipeline/`** (its imports of
`helpers/` depend on that):

```bash
cd pipeline
python3 <script>.py
```

Frozen-embedding extraction (`build_image_embedding_features*.py`) uses Apple
Silicon MPS acceleration automatically if available, else falls back to CPU
(slower but correct).

Scripts in `archived/` (see [Archived](#archived-the-exploratory-and-superseded-work) below)
are run the same way but from the repo root, since they no longer live
inside `pipeline/`: `python3 archived/<script>.py`. They still read/write
`pipeline/data/`, `pipeline/results/`, and `pipeline/figures/` — only the
scripts themselves moved, not the data.

## Demo: inspect results without re-running anything

Every result and figure in this repo is already computed and committed. For a
live demo, the fastest path is to open these directly rather than re-running
multi-minute training scripts:

| What to show | Where |
|---|---|
| Final model performance vs. every baseline tried | [Results at a glance](#results-at-a-glance) below, or `crisp_dm_notes/04_modeling.md` Chunks 18-19 |
| Confusion matrix (shows the class-0 blind spot visually) | `pipeline/figures/ordinal_model_confusion_matrix.png` |
| What the model learned (SHAP direction charts) | `pipeline/figures/shap_chart_1_overall_importance.png` through `_5_state_effects.png` |
| Full error/fairness analysis | `crisp_dm_notes/05_evaluation.md` Chunk 19 |
| Raw EDA (class imbalance, rescuer concentration) | `pipeline/figures/outlier_boxplots.png`, `relationship_eda.png` |
| The complete decision trail, chunk by chunk | `crisp_dm_notes/04_modeling.md` and `05_evaluation.md` (read top-to-bottom) |

If you do want to demo a *script* live, the cheapest ones that finish in
seconds and read already-computed inputs are `evaluate_ordinal_model.py` and
`create_shap_charts.py` (see runtimes in the table below). To regenerate
everything from scratch instead of inspecting existing results, see
[Running it all at once](#running-it-all-at-once) below.

## Walkthrough: full pipeline, in order

All commands assume `cd pipeline` first. Runtime is approximate, on
Apple Silicon with MPS; CPU-only will be slower for the embedding-extraction
steps. "Reads" / "Produces" are relative to `pipeline/`.

### Running it all at once

`run_pipeline.py` runs every script in `pipeline/` in order, streaming each
step's output to the console and saving it to `logs/<script>.log`. It stops
at the first failure (every later step assumes earlier ones succeeded).
Takes roughly 10-15 minutes.

```bash
cd pipeline
python3 run_pipeline.py --dry-run     # see the plan first, run nothing
python3 run_pipeline.py               # everything in pipeline/, in order
```

Add `--phase 3` (repeatable, phases 3/4/5) to restrict to specific phases, or
`--from <script.py>` to resume a run that stopped partway. Run
`python3 run_pipeline.py --help` for the full option list; `--dry-run`
combined with any filter shows exactly which scripts and in what order
without executing anything. It only knows about `pipeline/`'s 11 scripts —
`archived/` scripts are run individually (see
[Archived](#archived-the-exploratory-and-superseded-work) below).

Phase 2 (EDA) has no scripts left in `pipeline/` — both of its scripts turned
out not to be on the final model's dependency path and moved to `archived/`
(see [below](#archived-the-exploratory-and-superseded-work)); their output
figures are still used throughout the notes and `Findings.md`.

### Phase 3 — Data preparation

| Script | Runtime | Produces |
|---|---|---|
| `build_stage1_feature_table.py` | ~30s | `data/listing_features_stage1.csv` (joins structured + text + sentiment + metadata) |
| `build_image_pixel_features.py` | ~1-3 min | `data/image_pixel_features.csv`, `data/listing_features_stage2.csv`, `data/unreadable_train_images.csv` |
| `build_image_embedding_features.py` | ~2 min (MPS) | `data/image_embeddings_resnet18.npz`, `data/image_embedding_meta.csv` — frozen ResNet18 embeddings, the backbone the final model actually uses |

`helpers/fold_safe_features.py`, `helpers/tree_fold_safe_features.py`,
`helpers/image_embedding_features.py`, and `helpers/error_analysis.py` are
**library modules, not run directly** — every modeling/evaluation script
below (and several in `archived/`) imports from them, which is why they're
split into their own `helpers/` folder. They implement the leakage-safe
policy: all imputation/encoding/scaling/TF-IDF/PCA is fit inside each
training fold only.

### Phase 4 — Modeling

| Script | Runtime | Produces | What it answers |
|---|---|---|---|
| `train_ordinal_regression.py` | ~2-3 min | `results/ordinal_regression_results.json` | **The winning reformulation** — regression + optimized-threshold decoding |
| `generate_ordinal_model_artifacts.py` | ~1-2 min | `results/ordinal_model_oof_predictions.csv`, `results/ordinal_model_feature_importance.csv` | Out-of-fold predictions + feature importances for the **current final model** |

Everything that led *to* this reformulation — the baseline, the CatBoost vs.
LightGBM comparison, hyperparameter tuning, the image-backbone comparison,
the text-only ablation, and the superseded multiclass model — is real,
documented work; it's just not needed to *regenerate* the final model, so
it lives in `archived/` (below) rather than here.

### Phase 5 — Evaluation

| Script | Runtime | Produces |
|---|---|---|
| `evaluate_ordinal_model.py` | <10s | `results/ordinal_model_error_analysis.json` — confusion matrix, cohort slices, feature importance by family |
| `analyze_model_shap.py` | ~30-60s | `results/model_shap_analysis.json` — SHAP direction analysis, with breed/color/state decoded |
| `create_shap_charts.py` | <10s | `figures/shap_chart_1..5*.png` |
| `create_model_comparison_table.py` | <5s | `figures/model_comparison_table.png` — summary table used in `Findings.md` |
| `create_class_recall_table.py` | <5s | `figures/class_recall_table.png` — summary table used in `Findings.md` |

## Archived: the exploratory and superseded work

`archived/` holds every script that was part of the real research process
but isn't on the dependency path to the current final model — nothing here
was deleted, and nothing here is "wrong," it's just not needed to regenerate
today's numbers. Each script still runs (`python3 archived/<script>.py` from
the repo root — see [Setup](#setup)); each adds `pipeline/` to its own
`sys.path` so its `helpers/` imports keep resolving. Full reasoning for why
each was tried and what it found: `crisp_dm_notes/04_modeling.md`.

| Script | Chunk | What it was for |
|---|---|---|
| `create_outlier_boxplot.py` | Phase 2 | EDA: outlier/distribution review |
| `create_relationship_eda.py` | Phase 2 | EDA: adoption speed vs. age/type/state |
| `validate_fold_safe_features.py` | Ch10 | Sanity-checks the fold-safe pipeline; trains nothing |
| `train_baseline_ablation.py` | Ch11 | Majority baseline + logistic regression, feature-family ablation |
| `train_boosted_tree_ablation.py` | Ch12 | CatBoost vs. LightGBM on the same features |
| `tune_boosted_trees.py` | Ch13 | Hyperparameter search, selected against grouped CV |
| `refit_tuned_winners_full_data.py` | Ch13 | Corrects a data-efficiency confound in the tuning search |
| `build_image_embedding_features_clip.py` | Ch20 | Frozen CLIP embeddings, for the backbone comparison below only — **not used by the final model** |
| `evaluate_image_embeddings.py` | Ch14/20 | Does adding frozen image embeddings help? ResNet18 vs. CLIP vs. none |
| `text_only_ablation.py` | Ch15 | Standalone value of listing text (isolates a rescuer-writing-style confound) |
| `train_final_model.py` | Ch16 | Full-data refit of the *multiclass* model — superseded by the ordinal reformulation |
| `evaluate_final_model.py` | Ch17 | Error analysis for the superseded multiclass model |

`tune_boosted_trees.py` (~10-15 min) and `evaluate_image_embeddings.py`
(~15-25 min) are the two slow ones; everything else here finishes in
seconds to a few minutes.

## Results at a glance

| Model | Grouped QWK | Stratified QWK | Accuracy |
|---|---:|---:|---:|
| Majority-class baseline | -0.012 | 0.000 | ~27% |
| Logistic regression (all features) | 0.294 | 0.323 | 36.3% |
| CatBoost, untuned | 0.347 | 0.370 | — |
| CatBoost, tuned | 0.340 | 0.370 | — |
| CatBoost + frozen image embeddings (multiclass, full refit) | 0.353 | 0.374 | 40.0% |
| **CatBoost ordinal regression + optimized thresholds (final)** | **0.379** | **0.417** | 36.7% |

Grouped (rescuer-held-out) CV is the primary, more conservative estimate
throughout this project — stratified CV lets ~72% of validation rescuers
already appear in training, which modestly inflates its numbers. The single
largest lever across every experiment was adding a new modality (frozen
image embeddings), followed by reformulating the problem as ordinal
regression instead of multiclass classification — both beat every
hyperparameter-tuning attempt by a wide margin.

Full model-by-model reasoning: `crisp_dm_notes/04_modeling.md`.

## Key findings

- **Older pets, listings with more animals, and higher adoption fees all
  predict slower adoption** — clean, monotonic, and intuitive
  (`figures/shap_chart_2_numeric_trends.png`).
- **Photo-less listings (2.3% of data) are barely predictable at all**
  (QWK ≈ 0.08 vs. ≈0.38 overall) — a concrete, evidence-based reason to
  recommend rescuers always include a photo.
- **A counterintuitive one**: sterilized/vaccinated pets predict *slower*
  adoption. Read as an age/tenure confound (longer-stay pets are more likely
  already sterilized), not a reason to avoid sterilizing shelter animals —
  see `crisp_dm_notes/05_evaluation.md` Chunk 21 for the full reasoning.
- **No rescuer cold-start problem**: pets from rescuers never seen in
  training score close to the overall average, validating the whole
  grouped-CV protocol this project relies on.
- Swapping the frozen image backbone (ResNet18 → CLIP) made no meaningful
  difference — evidence the bottleneck is the noisy, listing-level label
  itself, not embedding quality.

## Limitations

1. **The model never predicts class 0 (same-day adoption)** — 0% recall,
   under every formulation tried. It must not be used to flag likely
   same-day adoptions; that needs a dedicated fix (class reweighting,
   resampling, or a separate binary classifier) not yet attempted.
2. QWK ≈ 0.38 is fair-to-moderate agreement — useful for decision support and
   triage prioritization, not a precise or high-stakes automated
   determination about an individual animal.
3. Photo-less listings are effectively unscored (see above).
4. Feature-importance findings for listing text and sterilization status
   carry real confounds (rescuer writing style; age/tenure) — see
   `crisp_dm_notes/05_evaluation.md` before treating either as actionable
   advice.
5. All results are associational; nothing here establishes that changing a
   listing's photos, fee, or description *causes* faster adoption.
6. No independent held-out test set was reserved — every number is from
   stratified/rescuer-grouped cross-validation on the labeled training data.

## Reproducibility notes

- Fixed random seed (`2026`) throughout every split, model fit, and search.
- All learned transformations (imputers, encoders, scalers, TF-IDF
  vocabulary, PCA/SVD components) are fit inside each training fold only —
  never on validation data. See `helpers/fold_safe_features.py` and
  `helpers/tree_fold_safe_features.py`.
- Two validation designs are reported everywhere that matters: stratified
  5-fold CV (optimistic, in-distribution) and rescuer-grouped 5-fold CV
  (conservative, matches deployment reality) — see `crisp_dm_notes/02_data_understanding.md`
  for why the two disagree on this dataset.
- Package versions are pinned in `requirements.txt`; exact figures in this
  README were produced with those versions on Python 3.9.6.
