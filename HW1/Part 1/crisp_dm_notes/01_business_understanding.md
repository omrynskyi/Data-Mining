# Phase 1 — Business Understanding

## Purpose

Develop a personal, reproducible analysis of pet-adoption timing. Each row is a PetFinder pet listing; the target, `AdoptionSpeed`, is an ordinal five-level outcome, where lower values mean faster adoption.

This is an analytical and decision-support study, not a competition-submission workflow. Predictions and findings must support human judgment and never determine an animal's worthiness for promotion or adoption.

## Success criteria and safeguards

- Use ordinal-aware evaluation, initially Quadratic Weighted Kappa, alongside class-level errors and cohort analyses.
- Establish interpretable baselines before complex models.
- Treat results as predictive associations, not causal effects.
- Preserve raw data and record all processing/validation decisions.

## Target distribution

| AdoptionSpeed | Listings | Share |
|---:|---:|---:|
| 0 | 410 | 2.73% |
| 1 | 3,090 | 20.61% |
| 2 | 4,037 | 26.93% |
| 3 | 3,259 | 21.74% |
| 4 | 4,197 | 27.99% |

The same-day class is rare; accuracy alone is inadequate.
