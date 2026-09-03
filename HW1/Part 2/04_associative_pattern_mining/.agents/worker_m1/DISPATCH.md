## 2026-09-02T17:30:16Z
You are the Worker for Milestone 1 (M1) — CRISP-DM Pipeline & Pattern Mining Engine.
Your Working Directory: /Users/oleg/Documents/Coding/SJSU/Data Mining/HW1/Part 2/04_associative_pattern_mining/.agents/worker_m1
Project Root: /Users/oleg/Documents/Coding/SJSU/Data Mining/HW1/Part 2/04_associative_pattern_mining
Original Request: /Users/oleg/Documents/Coding/SJSU/Data Mining/HW1/Part 2/04_associative_pattern_mining/ORIGINAL_REQUEST.md
Project Spec: /Users/oleg/Documents/Coding/SJSU/Data Mining/HW1/Part 2/04_associative_pattern_mining/PROJECT.md
Explorer 1 Report: /Users/oleg/Documents/Coding/SJSU/Data Mining/HW1/Part 2/04_associative_pattern_mining/.agents/explorer_survey_1/handoff.md

Read ORIGINAL_REQUEST.md, PROJECT.md, and Explorer 1's report first.

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Your exclusive write ownership:
- `requirements.txt`
- `config.py`
- `data/generate_synthetic.py`
- `src/__init__.py`
- `src/data/*` (`loader.py`, `preprocessor.py`, `schema.py`)
- `src/eda/*` (`profiler.py`)
- `src/mining/*` (`engine.py`, `apriori.py`, `fpgrowth.py`, `rules.py`, `metrics.py`)
- `src/evaluation/*` (`filter.py`, `redundancy.py`)
- `src/deployment/*` (`exporter.py`, `pipeline.py`)
- `src/utils/*` (`logger.py`, `timer.py`)
- `run_pipeline.py`

Your mission:
Implement Requirement 1 (R1) end-to-end:
1. `requirements.txt`: specify required libraries (pandas, numpy, scipy, mlxtend, matplotlib, seaborn, etc.).
2. Data Layer:
   - `data/generate_synthetic.py`: Deterministic realistic retail transaction generator with planted affinities (e.g. bread+butter+jam, coffee+sugar, wine+cheese, tech items) for offline testability.
   - `src/data/loader.py`: Multi-dataset loader supporting 'online_retail', 'groceries', 'bakery', 'synthetic', and custom CSV file paths.
   - `src/data/preprocessor.py`: Cleaning (whitespace trimming, drop null descriptions, filter cancellations 'C...', remove zero/negative unit prices, filter single-item baskets) and sparse/one-hot transaction encoding.
3. EDA Profiler:
   - `src/eda/profiler.py`: Profile basket sizes, item frequencies, Pareto/Zipf distributions, sparsity, temporal distributions.
4. Mining Engine:
   - `src/mining/apriori.py`: Robust Apriori implementation with downward-closure candidate generation.
   - `src/mining/fpgrowth.py`: FP-Growth implementation with FP-Tree construction and conditional FP-Tree growth (can use mlxtend or pure Python/NumPy dual fallback).
   - `src/mining/rules.py`: Association rule extraction from frequent itemsets ($A \to C$).
   - `src/mining/metrics.py`: 9 mathematical metrics (Support, Confidence, Lift, Leverage, Conviction with $\infty$ capping, Zhang's Metric, Kulczynski, Imbalance Ratio, Cosine).
5. Evaluation Layer:
   - `src/evaluation/filter.py`: Multi-metric threshold filtering and composite score ranking.
   - `src/evaluation/redundancy.py`: Redundant sub-rule pruning ($A \subset A' \land conf(A') \le conf(A)$).
6. Deployment & Pipeline Runner:
   - `src/deployment/exporter.py`: Generate `artifacts/pipeline_summary.json`, `artifacts/pipeline_report.md`, `artifacts/rules.csv`, `artifacts/rules.json`, `artifacts/frequent_itemsets.csv`.
   - `src/deployment/pipeline.py`: Full CRISP-DM 6-phase pipeline runner.
   - `run_pipeline.py`: Top-level CLI with flags (--dataset, --algorithm, --min-support, --min-confidence, --metric, --min-metric-val, --max-len, --output-dir, etc.) executing end-to-end without manual intervention.

Verification:
1. Execute `python run_pipeline.py --dataset synthetic --output-dir artifacts` to ensure successful completion with exit code 0.
2. Verify artifacts created: `artifacts/pipeline_summary.json` and `artifacts/pipeline_report.md`.
3. Verify top rules are generated and all metrics calculated accurately.
