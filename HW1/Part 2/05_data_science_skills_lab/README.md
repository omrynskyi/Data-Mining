# Data Science Skills Lab — CRISP-DM on Telco Customer Churn

48 agent skills — 15 from [`param087/agent-ml-skills`](https://github.com/param087/agent-ml-skills),
33 from [`nimrodfisher/data-analytics-skills`](https://github.com/nimrodfisher/data-analytics-skills)
— installed into `.claude/skills/` and demonstrated end-to-end against one dataset:
[Kaggle `blastchar/telco-customer-churn`](https://www.kaggle.com/datasets/blastchar/telco-customer-churn)
(IBM Telco Customer Churn, 7,043 customers), organized by the six phases of CRISP-DM.

## Start here

- **`SKILLS_INDEX.md`** — the 48-skill coverage map, generated (not hand-maintained) by
  `src/build_skills_index.py`, which reconciles installed skills against demonstration docs
  actually present on disk.
- **`crisp_dm/README.md`** — the CRISP-DM walkthrough and phase-by-phase reading order.
- **`artifacts/executive_summary.md`** — the one-page, decision-ready business summary.
- **`src/verify_claims.py`** — an independent, 26-check harness that recomputes headline
  numbers straight from the raw CSV without importing any of this lab's own code, to verify
  nothing here drifted from the source data. Run it yourself: `python3 src/verify_claims.py`.

## Layout

```
crisp_dm/            one .md per skill demonstration, organized by CRISP-DM phase 1-6
src/                 all executable scripts (p1_/p2_/p3_/p4_/p6_ prefixes = phase)
artifacts/           every computed output: JSON/CSV results, the fitted model, the local
                      MLflow store, the SQLite DB, the RAG index, sign-off docs
reports/figures/     every chart, PNG dpi=130
data/                the raw Kaggle CSV + the stratified train/test split
requirements.txt     pinned environment
```

## Reproduce

```bash
pip3 install -r requirements.txt
python3 src/00_foundation.py        # builds data/processed/{train,test}.csv
python3 src/verify_claims.py        # 26 independent checks against the raw CSV
python3 src/build_skills_index.py   # regenerates SKILLS_INDEX.md
```

Individual phase scripts (`src/p1_*.py` … `src/p6_*.py`) can be run standalone; each writes its
outputs to `artifacts/` and `reports/figures/`.
