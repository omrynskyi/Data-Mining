# Project: Associative Pattern Mining & Data Science Admin Dashboard

## Architecture
```
04_associative_pattern_mining/
├── run_pipeline.py                 # R1 CLI Entrypoint for CRISP-DM pipeline
├── run_optimization.py             # R2 CLI Entrypoint for Hill Climbing optimizer
├── app.py                          # R3 Flask Web Admin Dashboard Entrypoint
├── config.py                       # Global configuration & paths
├── requirements.txt                # Python package dependencies
├── data/
│   ├── raw/                        # Kaggle dataset storage (Online Retail, Groceries)
│   └── generate_synthetic.py       # Deterministic realistic retail data generator
├── src/
│   ├── data/
│   │   ├── loader.py               # Multi-dataset loader & validation
│   │   ├── preprocessor.py         # Cleaning, filtering, one-hot encoding
│   │   └── schema.py               # Data models
│   ├── eda/
│   │   └── profiler.py             # Basket size, item frequency, sparsity profiler
│   ├── mining/
│   │   ├── engine.py               # Unified mining facade
│   │   ├── apriori.py              # Apriori algorithm implementation
│   │   ├── fpgrowth.py             # FP-Growth algorithm implementation
│   │   ├── rules.py                # Association rule generator
│   │   └── metrics.py              # Support, Conf, Lift, Leverage, Conviction, Zhang, etc.
│   ├── evaluation/
│   │   ├── filter.py               # Multi-metric filtering & scoring
│   │   └── redundancy.py           # Redundant sub-rule pruning
│   ├── optimization/
│   │   ├── state.py                # 5D hyperparameter state & bounds
│   │   ├── fitness.py              # Target match MSE, composite, hybrid fitness
│   │   ├── operators.py            # Gaussian mutation, adaptive step sizing, LHC restarts
│   │   ├── papers.py               # Research paper benchmark catalog (Ghosh2004, Agrawal1994, Chen2012)
│   │   ├── evaluator.py            # Mine-once/mask-many candidate scorer (exact vs live engine)
│   │   ├── hill_climber.py         # Steepest-ascent hill climbing with restarts
│   │   └── logger.py               # JSON & CSV progression logger
│   ├── dashboard/
│   │   ├── routes.py               # REST API endpoints & HTML rendering
│   │   ├── artifact_loader.py      # Resilient artifact loader with graceful fallbacks
│   │   └── live_miner.py           # Interactive live mining handler
│   ├── deployment/
│   │   ├── exporter.py             # Summary, JSON, CSV, Markdown artifact generators
│   │   └── pipeline.py             # End-to-end CRISP-DM pipeline orchestrator
│   └── utils/
│       ├── logger.py               # Structured logging
│       └── timer.py                # Execution timing utilities
├── templates/
│   └── index.html                  # Single-Page Application Admin Dashboard Template
├── static/
│   ├── css/
│   │   └── custom.css              # Custom styling & dark mode
│   └── js/
│       ├── app.js                  # State management & tab controller
│       ├── visualizers.js          # Vis.js network graph & Plotly 3D scatter
│       └── sandbox.js              # Live mining sandbox controller
├── artifacts/                      # Generated pipeline & optimization outputs
│   ├── pipeline_summary.json       # CRISP-DM summary & top rules
│   ├── pipeline_report.md          # Human-readable markdown report
│   ├── rules.json / rules.csv      # Mined association rules
│   ├── frequent_itemsets.csv       # Discovered frequent itemsets
│   ├── optimization_log.json       # Research paper matching log & trajectory
│   ├── optimization_history.csv    # Iteration-by-iteration CSV history
│   └── optimized_rules.csv         # Optimal rule set from hill climbing
└── tests/                          # Tiers 1-4 Test Suites
    ├── conftest.py
    ├── unit/
    ├── integration/
    └── e2e/
```

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| F1 | Kaggle Dataset Ingestion & Seeding | Multi-dataset loader (Online Retail, Groceries, Bakery) + synthetic transaction generator | M1 | Survey (R1) |
| F2 | CRISP-DM 6-Phase Pipeline Engine | Business Understanding -> Data Understanding EDA -> Data Prep -> Modeling -> Eval -> Deployment | M1 | Survey (R1) |
| F3 | Dual Frequent Itemset Mining | High-performance Apriori and FP-Growth itemset discovery engines | M1 | Survey (R1) |
| F4 | Multi-Metric Rule Generation | Support, Confidence, Lift, Leverage, Conviction, Zhang's Metric, Kulczynski, Imbalance Ratio, Cosine | M1 | Survey (R1) |
| F5 | Evaluation & Redundancy Pruning | Threshold filtering, subset redundancy elimination, business clustering | M1 | Survey (R1) |
| F6 | Pipeline CLI & Summary Artifacts | `run_pipeline.py` CLI generating `pipeline_summary.json` and `pipeline_report.md` | M1 | Survey (R1) |
| F7 | Research Paper Benchmark Catalog | Formatted benchmark profiles for Ghosh & Nath (2004), Agrawal & Srikant (1994), Chen et al. (2012) | M2 | Survey (R2) |
| F8 | Multi-Mode Fitness Evaluator | Normalized MSE target matching, multi-objective Pareto composite quality, and hybrid fitness | M2 | Survey (R2) |
| F9 | Adaptive Steepest-Ascent Optimizer | 5D state space, Gaussian mutation, Rechenberg 1/5th adaptive step scaling | M2 | Survey (R2) |
| F10 | Stochastic Random-Restart Engine | Latin Hypercube / uniform restarts upon local plateau detection | M2 | Survey (R2) |
| F11 | Optimization CLI & Audit Logger | `run_optimization.py` generating `optimization_log.json`, `optimization_history.csv`, `optimized_rules.csv` | M2 | Survey (R2) |
| F12 | Dashboard Web Server & Health Probe | Flask 3.1+ server in `app.py`, resilient `ArtifactLoader`, `/health` returning HTTP 200 OK | M3 | Survey (R3) |
| F13 | Complete REST API Suite | Endpoints for summary, crisp-dm, eda, rules, network graph, export, optimization, live sandbox, recommend | M3 | Survey (R3) |
| F14 | CRISP-DM Workflow Explorer UI | Interactive 6-phase stepper cards with embedded EDA distribution charts | M3 | Survey (R3) |
| F15 | Association Rule Visualizer UI | Vis.js force-directed network graph, Plotly 3D scatter, dynamic filter sliders, sortable table, CSV/JSON export | M3 | Survey (R3) |
| F16 | Hill Climbing Progression UI | Target paper card, dual-line convergence curve, hyperparameter trajectory, radar/bar comparison, step table | M3 | Survey (R3) |
| F17 | Live Interactive Mining Sandbox | Realtime on-the-fly Apriori/FP-Growth parameter tuning, performance diagnostics, push-to-visualizer | M3 | Survey (R3) |
| F18 | Comprehensive E2E Test Suite | 4-Tier test suite (Unit, Boundary, Integration, E2E Acceptance) publishing `TEST_READY.md` | E2E Track | Survey (R3) |
| F19 | Final Integration & Adversarial Verification | 100% E2E test passing + Tier 5 adversarial stress testing & coverage hardening | M4 | Project Pattern |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M1 | CRISP-DM Pipeline & Pattern Mining | Implement F1-F6: data loader, preprocessor, EDA profiler, Apriori/FP-Growth, metrics, redundancy pruning, `run_pipeline.py`, summary artifacts | none | COMPLETE |
| M2 | Automated Research & Hill Climbing | Implement F7-F11: research paper catalog (`ghosh2004`, etc.), 5D state, fitness evaluator, steepest-ascent with restarts, `run_optimization.py`, audit logs | M1 | COMPLETE |
| M3 | Data Science Admin Dashboard | Implement F12-F17: Flask server in `app.py`, `/health`, REST APIs, CRISP-DM explorer, Vis.js network, Plotly 3D scatter, hill climbing progression UI, live sandbox | M1, M2 | COMPLETE |
| E2E | E2E Testing Suite Track | Implement F18: 4-Tier test infrastructure (Unit, Boundary, Integration, System E2E) and publish `TEST_READY.md` | none | COMPLETE |
| M4 | Final Integration & Hardening | Implement F19: Verify 100% E2E test passing (Tiers 1-4) + Tier 5 adversarial stress hardening via Challenger-Worker loop | M1, M2, M3, E2E | PLANNED |

## Interface Contracts

### M1 -> Downstream (Artifacts & Data Schemas)
- `artifacts/pipeline_summary.json`:
  - Contains `pipeline_metadata`, `crisp_dm_stages` (with business, data understanding stats, preparation stats, modeling stats, evaluation stats, deployment list), and `top_rules` array.
- `artifacts/rules.json`: List of rule objects:
  `{"id": int, "antecedents": [str], "consequents": [str], "support": float, "confidence": float, "lift": float, "leverage": float, "conviction": float, "zhangs_metric": float, "kulczynski": float, "imbalance_ratio": float, "cosine": float}`
- `src.data.loader.load_dataset(name)` -> Returns pandas DataFrame with transactions.
- `src.mining.engine.mine_association_rules(df, min_support, min_confidence, metric, min_metric_val, max_len, algorithm)` -> Returns `(itemsets_df, rules_df)`.

### M2 -> Downstream (Optimization Logs & State)
- `artifacts/optimization_log.json`:
  - Contains `metadata`, `target_paper` (key, title, authors, venue, doi, target_metrics), `config`, `summary` (iterations, best_fitness, best_loss, termination_reason), `target_vs_achieved` comparison, `best_hyperparameters`, `iteration_trail` array.
- `artifacts/optimization_history.csv`:
  - Columns: `iteration,restart_id,step_type,min_support,min_confidence,max_len,min_lift,pruning_factor,rule_count,avg_support,avg_confidence,avg_lift,coverage,loss,fitness,best_fitness,step_size,accepted`
- `src.optimization.hill_climber.HillClimber.run(transactions_df)` -> Returns `OptimizationResult`.

### M3 Web Admin Dashboard Interfaces
- Server entrypoint: `python app.py` (serves on `http://0.0.0.0:5000` or configurable port).
- `GET /health` -> `{"status": "healthy", "timestamp": str, "version": "1.0.0", "artifacts": {"eda": bool, "pipeline": bool, "rules": bool, "optimization": bool}}`
- `GET /api/summary` -> High-level KPI metrics dictionary.
- `GET /api/crisp-dm` -> Full 6-phase metadata structure.
- `GET /api/eda` -> Item distributions and basket stats.
- `GET /api/rules` -> Filtered and paginated rule list.
- `GET /api/rules/network` -> Nodes and edges for Vis.js force graph.
- `GET /api/optimization` -> Target paper benchmark details and iteration history.
- `POST /api/sandbox/mine` -> Interactive live rule mining on user parameters.

## Code Layout
- `src/data/`: Data loading, synthetic generation, transaction encoding.
- `src/eda/`: Exploratory data analysis profiling.
- `src/mining/`: Apriori, FP-Growth, rule generation, interest metrics.
- `src/evaluation/`: Redundancy pruning, rule filtering.
- `src/optimization/`: Hill climbing optimizer, research papers, fitness functions, operators.
- `src/dashboard/`: Flask app, routes, live miner, artifact loader.
- `src/deployment/`: Exporters, summary builders, pipeline runners.
- `src/utils/`: Logger, timers.
- `templates/`: HTML Jinja templates.
- `static/`: CSS and JavaScript files.
- `tests/`: Unit, integration, and E2E test suites.
