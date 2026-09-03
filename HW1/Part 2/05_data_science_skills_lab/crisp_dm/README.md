# CRISP-DM Walkthrough — Telco Customer Churn

This lab exercises **48 installed agent skills** against one dataset, organised by the six
phases of CRISP-DM (Cross-Industry Standard Process for Data Mining, Chapman et al. 2000).

## Dataset

| | |
|---|---|
| Source | Kaggle `blastchar/telco-customer-churn` (IBM sample: *Telco Customer Churn*) |
| Local copy | `data/Telco-Customer-Churn.csv` |
| SHA-256 | `16320c9c1ec72448db59aa0a26a0b95401046bef5d02fd3aeb906448e3055e91` |
| Shape | 7,043 rows x 21 columns |
| Grain | one row per customer, single cross-sectional snapshot |
| Target | `Churn` (Yes/No) — 26.54% positive |
| Split | stratified 80/20, seed 42 -> 5,634 train / 1,409 test |

**Why this dataset.** It is a subscription business, so it supports the analytics-pack skills
(MRR, ARPU, LTV, cohorts, segmentation, funnels, retention) *and* it is a moderately imbalanced
binary classification problem, so it supports the ML-pack skills (imbalanced-data, model
evaluation, threshold tuning, calibration, serving). One dataset, both packs.

**Known limitation, stated once and honoured throughout.** This is a *snapshot*, not an event
log. There are no timestamps, no experiment assignment, and no longitudinal panel. Any cohort,
time-series or funnel view in this lab is *reconstructed* from `tenure` under a survivorship
assumption, and any A/B comparison is *observational*. Each affected skill document says so
explicitly rather than quietly presenting the reconstruction as ground truth.

## The six phases

| Phase | What CRISP-DM asks for | Where it lives |
|---|---|---|
| 1. Business Understanding | Objectives, success criteria, project plan | `01_business_understanding/` |
| 2. Data Understanding | Collect, describe, explore, verify quality | `02_data_understanding/` |
| 3. Data Preparation | Select, clean, construct, integrate, format | `03_data_preparation/` |
| 4. Modeling | Select technique, build, assess models | `04_modeling/` |
| 5. Evaluation | Evaluate against *business* objectives, review process | `05_evaluation/` |
| 6. Deployment | Deploy, monitor, maintain, produce final report | `06_deployment/` |

CRISP-DM is iterative, not a waterfall: phases 2 and 3 loop, and phase 5 can send you back to
phase 1. The lab records where that actually happened rather than pretending it was linear.

## Reading order

Each skill has its own document named after the skill, with YAML frontmatter recording the
skill name, its source pack, the CRISP-DM phase, and the artifacts it produced. Every number in
those documents was computed by a script in `src/`; nothing is illustrative.

See `../SKILLS_INDEX.md` for the full 48-skill coverage map.
