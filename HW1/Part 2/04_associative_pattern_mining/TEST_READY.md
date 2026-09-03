# TEST_READY — Associative Pattern Mining & Admin Studio Test Suite

## Overview
The 4-Tier Automated Test Suite provides complete verification for the Associative Pattern Mining CRISP-DM pipeline, automated research paper hill climbing optimizer, and Flask Data Science Admin Dashboard.

**Current status: 115 passed, 0 skipped, 0 failed** (`python3 -m pytest tests/ -q`, ~19 s).
All four tiers are green against the full M1 + M2 + M3 implementation.

---

## Test Architecture & Suite Organization

```
tests/
├── conftest.py                            # Shared fixtures (retail DF, transactions, mock artifacts, Flask client)
├── unit/                                  # Tier 1 (Feature Coverage) & Tier 2 (Boundary & Corner Cases)
│   ├── test_data_loader.py                # F1: Dataset ingestion, cleaning, cancellation filtering, one-hot encoding
│   ├── test_crisp_dm_stages.py            # F2: CRISP-DM 6-Phase stage definitions, EDA profiler, transitions
│   ├── test_mining_algorithms.py          # F3: Apriori vs FP-Growth equivalence & downward-closure property
│   ├── test_rule_metrics.py               # F4: Mathematical precision of 9 association metrics & infinite capping
│   ├── test_redundancy_pruning.py         # F5: Redundant sub-rule pruning logic and boundary conditions
│   ├── test_paper_catalog.py              # F7: Ghosh2004, Agrawal1994, Chen2012 benchmark profiles & custom configs
│   ├── test_fitness_evaluator.py          # F8: Matching MSE loss, composite quality fitness, zero-rule cliff penalty
│   ├── test_hill_climber.py               # F9, F10: 5D state space, Gaussian mutation, Rechenberg 1/5th scaling, restarts
│   └── test_dashboard_api.py              # F12, F13: REST API endpoints (/health, /api/summary, /api/rules...)
├── integration/                           # Tier 3 (Cross-Feature Integration)
│   ├── test_pipeline_artifacts.py         # F6: run_pipeline.py CLI -> artifact files & JSON schema integrity
│   ├── test_optimization_trail.py         # F11: run_optimization.py CLI -> log schema & monotonic best fitness
│   ├── test_dashboard_integration.py     # F13: ArtifactLoader -> REST APIs consistency & graceful fallback
│   ├── test_sandbox_parity.py             # F17: Live sandbox mining vs offline batch mining parity
│   └── test_recommendation_flow.py        # F13: Basket recommendation inference from discovered rules
└── e2e/                                   # Tier 4 (Real-World Workloads & Acceptance)
    ├── test_e2e_pipeline.py               # S1: Full end-to-end CRISP-DM pipeline execution on datasets
    ├── test_e2e_optimization.py           # S2: Hill climbing convergence matching research paper targets
    ├── test_e2e_dashboard_server.py       # S3: Subprocess `python app.py` startup, port binding, /health probe 200 OK
    └── test_e2e_asset_delivery.py         # S3, S4: HTML rendering, static assets (CSS/JS), and script integrity
```

---

## Test Execution Commands

### 1. Run Complete Test Suite
```bash
python3 -m pytest tests/ -v
```

### 2. Run Tier 1 & Tier 2 Unit Tests
```bash
python3 -m pytest tests/unit/ -v
```

### 3. Run Tier 3 Integration Tests
```bash
python3 -m pytest tests/integration/ -v
```

### 4. Run Tier 4 End-to-End Acceptance Tests
```bash
python3 -m pytest tests/e2e/ -v
```

### 5. Run with Coverage Report
```bash
python3 -m pytest tests/ -v --cov=src --cov-report=term-missing
```

---

## 4-Tier Test Coverage Matrix

| Feature | Description | Tier 1 (Unit) | Tier 2 (Boundary) | Tier 3 (Integration) | Tier 4 (E2E) |
|---|---|:---:|:---:|:---:|:---:|
| **F1** | Dataset Ingestion & Preprocessing | `test_data_loader.py` | `test_data_loader.py` | `test_pipeline_artifacts.py` | `test_e2e_pipeline.py` |
| **F2** | CRISP-DM 6-Phase Engine | `test_crisp_dm_stages.py` | `test_crisp_dm_stages.py` | `test_pipeline_artifacts.py` | `test_e2e_pipeline.py` |
| **F3** | Frequent Itemset Mining (Apriori/FP-Growth) | `test_mining_algorithms.py` | `test_mining_algorithms.py` | `test_sandbox_parity.py` | `test_e2e_pipeline.py` |
| **F4** | Multi-Metric Rule Generation (9 Metrics) | `test_rule_metrics.py` | `test_rule_metrics.py` | `test_pipeline_artifacts.py` | `test_e2e_pipeline.py` |
| **F5** | Evaluation & Redundancy Pruning | `test_redundancy_pruning.py` | `test_redundancy_pruning.py` | `test_pipeline_artifacts.py` | `test_e2e_pipeline.py` |
| **F6** | Pipeline CLI & Summary Artifacts | `test_crisp_dm_stages.py` | `test_crisp_dm_stages.py` | `test_pipeline_artifacts.py` | `test_e2e_pipeline.py` |
| **F7** | Research Paper Benchmark Catalog | `test_paper_catalog.py` | `test_paper_catalog.py` | `test_optimization_trail.py` | `test_e2e_optimization.py` |
| **F8** | Multi-Mode Fitness Evaluator | `test_fitness_evaluator.py` | `test_fitness_evaluator.py` | `test_optimization_trail.py` | `test_e2e_optimization.py` |
| **F9** | Adaptive Steepest-Ascent Optimizer | `test_hill_climber.py` | `test_hill_climber.py` | `test_optimization_trail.py` | `test_e2e_optimization.py` |
| **F10** | Stochastic Random Restarts | `test_hill_climber.py` | `test_hill_climber.py` | `test_optimization_trail.py` | `test_e2e_optimization.py` |
| **F11** | Optimization CLI & Progression Log | `test_hill_climber.py` | `test_hill_climber.py` | `test_optimization_trail.py` | `test_e2e_optimization.py` |
| **F12** | Dashboard Server & Health Probe | `test_dashboard_api.py` | `test_dashboard_api.py` | `test_dashboard_integration.py` | `test_e2e_dashboard_server.py` |
| **F13** | REST API Suite & Recommendation | `test_dashboard_api.py` | `test_dashboard_api.py` | `test_recommendation_flow.py` | `test_e2e_asset_delivery.py` |
| **F14** | CRISP-DM Workflow Explorer UI | `test_crisp_dm_stages.py` | `test_crisp_dm_stages.py` | `test_dashboard_integration.py` | `test_e2e_asset_delivery.py` |
| **F15** | Rule Visualizer UI (Network & 3D) | `test_dashboard_api.py` | `test_dashboard_api.py` | `test_dashboard_integration.py` | `test_e2e_asset_delivery.py` |
| **F16** | Hill Climbing Progression UI | `test_dashboard_api.py` | `test_dashboard_api.py` | `test_optimization_trail.py` | `test_e2e_asset_delivery.py` |
| **F17** | Interactive Live Mining Sandbox | `test_dashboard_api.py` | `test_dashboard_api.py` | `test_sandbox_parity.py` | `test_e2e_asset_delivery.py` |

---

## Progressive Testability & Fallback Support
- Unit and integration tests leverage pytest fixtures (`tests/conftest.py`) providing deterministic synthetic data and mock artifacts.
- Tests gracefully skip when an unbuilt module is absent, and automatically execute full verification as soon as workers finish implementation milestones.
