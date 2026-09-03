# E2E Test Infra: Associative Pattern Mining & Admin Studio

## Test Philosophy
- **Requirement-Driven & Opaque-Box**: Tests are derived strictly from `ORIGINAL_REQUEST.md` and user acceptance criteria, exercising the pipeline, optimizer, and dashboard via public interfaces, CLI commands, and HTTP endpoints.
- **Progressive Testability**: Tier 1 tests verify fundamental data structures and metric equations in isolation; Tier 2 stresses boundaries and zero-rule edge conditions; Tier 3 asserts artifact and API cross-track consistency; Tier 4 evaluates real-world full datasets, server concurrency, and E2E browser/asset flows.

## Feature Inventory & Test Matrix
| # | Feature | Source | Tier 1 (Unit) | Tier 2 (Boundary) | Tier 3 (Integration) | Tier 4 (Real-World) |
|---|---------|--------|:-------------:|:-----------------:|:--------------------:|:-------------------:|
| F1 | Kaggle Dataset Ingestion & Seeding | R1 | 5 | 5 | ✓ | ✓ |
| F2 | CRISP-DM 6-Phase Pipeline Engine | R1 | 5 | 5 | ✓ | ✓ |
| F3 | Dual Frequent Itemset Mining (Apriori/FP-Growth) | R1 | 5 | 5 | ✓ | ✓ |
| F4 | Multi-Metric Rule Generation (9 Metrics) | R1 | 5 | 5 | ✓ | ✓ |
| F5 | Evaluation & Redundancy Pruning | R1 | 5 | 5 | ✓ | ✓ |
| F6 | Pipeline CLI & Summary Artifacts | R1 | 5 | 5 | ✓ | ✓ |
| F7 | Research Paper Benchmark Catalog (`ghosh2004`, etc.) | R2 | 5 | 5 | ✓ | ✓ |
| F8 | Multi-Mode Fitness Evaluator (MSE, Composite, Hybrid) | R2 | 5 | 5 | ✓ | ✓ |
| F9 | Adaptive Steepest-Ascent Optimizer | R2 | 5 | 5 | ✓ | ✓ |
| F10 | Stochastic Random-Restart Engine | R2 | 5 | 5 | ✓ | ✓ |
| F11 | Optimization CLI & Audit Logger | R2 | 5 | 5 | ✓ | ✓ |
| F12 | Dashboard Web Server & Health Probe (`app.py`, `/health`) | R3 | 5 | 5 | ✓ | ✓ |
| F13 | Complete REST API Suite (10 endpoints) | R3 | 5 | 5 | ✓ | ✓ |
| F14 | CRISP-DM Workflow Explorer UI | R3 | 5 | 5 | ✓ | ✓ |
| F15 | Association Rule Visualizer UI (Vis.js / Plotly 3D) | R3 | 5 | 5 | ✓ | ✓ |
| F16 | Hill Climbing Progression UI | R3 | 5 | 5 | ✓ | ✓ |
| F17 | Live Interactive Mining Sandbox | R3 | 5 | 5 | ✓ | ✓ |

## Test Architecture
```
tests/
├── conftest.py                    # Reusable pytest fixtures (sample transactions, client, mock papers)
├── unit/                          # Tier 1 & Tier 2 Unit Tests
│   ├── test_data_loader.py        # F1: Dataset ingestion, cleaning, one-hot encoding
│   ├── test_crisp_dm_stages.py    # F2: Business, Data Understanding, Prep, Modeling, Eval, Deploy
│   ├── test_mining_algorithms.py  # F3: Apriori vs FP-Growth equivalence & downward closure
│   ├── test_rule_metrics.py       # F4: Math precision of 9 association metrics & infinite handling
│   ├── test_redundancy_pruning.py # F5: Redundant sub-rules pruning logic
│   ├── test_paper_catalog.py      # F7: Paper benchmark profiles
│   ├── test_fitness_evaluator.py  # F8: MSE matching, composite quality, zero-rule penalties
│   ├── test_hill_climber.py       # F9, F10: Mutation operators, step scaling, restart triggers
│   └── test_dashboard_api.py      # F12, F13: Flask endpoints (/health, /api/rules, /api/crisp-dm...)
├── integration/                   # Tier 3 Cross-Feature Integration Tests
│   ├── test_pipeline_artifacts.py # F6: run_pipeline.py CLI -> artifact file existence & schemas
│   ├── test_optimization_trail.py # F11: run_optimization.py CLI -> log schema & trajectory
│   ├── test_dashboard_integration.py # F13: ArtifactLoader -> REST APIs consistency
│   ├── test_sandbox_parity.py     # F17: Live sandbox vs offline batch mining parity
│   └── test_recommendation_flow.py # Inference from mined rules
└── e2e/                           # Tier 4 Real-World Workload & Acceptance Tests
    ├── test_e2e_pipeline.py       # Full end-to-end dataset execution
    ├── test_e2e_optimization.py   # Full hill climbing search convergence & paper match
    ├── test_e2e_dashboard_server.py # Subprocess startup `python app.py`, port binding, /health 200 OK
    └── test_e2e_asset_delivery.py # Static assets, HTML template rendering, script tags integrity
```

## Real-World Application Scenarios (Tier 4)
| # | Scenario | Features Exercised | Expected Outcome |
|---|----------|--------------------|------------------|
| S1 | End-to-End Retail Market Basket Analysis | F1, F2, F3, F4, F5, F6 | Full pipeline executes cleanly, generating verified summary artifacts and high-lift rule clusters |
| S2 | Research Paper Metric Target Matching (`ghosh2004`) | F7, F8, F9, F10, F11 | Hill climber matches target paper profile with Best Fitness > 90% and non-decreasing trajectory |
| S3 | Clean Dashboard Server Startup & Readiness | F12, F13, F14, F15, F16, F17 | Single command `python app.py` starts in <2s, `/health` returns 200 OK, UI renders all 4 sections |
| S4 | Dynamic Live Mining Parameter Exploration | F13, F17, F15 | User adjusts support/confidence in sandbox, gets instant rule discovery, and visualizes force network |
| S5 | High-Concurrency Admin API Stress Test | F12, F13 | 50 concurrent API requests execute with zero 500 errors and mean latency <50ms |

## Coverage & Execution Thresholds
- **Tier 1 (Feature Coverage)**: >=5 test cases per feature
- **Tier 2 (Boundary & Corner Cases)**: >=5 test cases per boundary domain
- **Tier 3 (Cross-Feature Combinations)**: Complete pairwise integration coverage
- **Tier 4 (Real-World Scenarios)**: >=5 comprehensive end-to-end acceptance tests
- **Minimum Test Suite Target**: >=100 passing test cases across all tiers
- **Execution Command**: `pytest tests/ -v`
