# Technical Specification & Survey Report: Data Science Admin Dashboard (R3) & Test Infrastructure

**Document Type**: Survey & Technical Specification Report (Requirement 3 & Test Strategy)  
**Author**: Explorer Survey 3 (`8f1436b9-108c-40be-8fae-7d33ce661541`)  
**Target Audience**: Orchestrator, Sub-Orchestrators, Implementers (Workers), E2E Test Suite Writers  
**Working Directory**: `/Users/oleg/Documents/Coding/SJSU/Data Mining/HW1/Part 2/04_associative_pattern_mining/.agents/explorer_survey_3`  
**Date**: 2026-09-02  

---

## 1. Observation

### 1.1 Direct Observations from Workspace & Requirements
- **Original User Request (`ORIGINAL_REQUEST.md`)**:
  - **R3**: Data Science Admin Dashboard tailored for data scientists and AI engineers.
  - Must visualize: (1) CRISP-DM phases, (2) Discovered association rules, (3) Hill climbing optimization against target research paper.
  - Acceptance Criteria:
    - Starts cleanly via a single command: `python app.py` (serving on local port returning HTTP 200 OK).
    - Contains clear dedicated sections for CRISP-DM process, hill climbing results, and rule visualization.
- **Environment & Installed Dependencies**:
  - Python version: `3.9.6`
  - Core web frameworks installed: `Flask 3.1.3` (with `Werkzeug 3.1.6`, `Jinja2 3.1.6`), `FastAPI 0.115.6`, `uvicorn 0.34.0`, `starlette 0.41.3`.
  - Data science & visualization libraries: `pandas 2.3.3`, `numpy 1.26.4`, `plotly 7.0.0`, `networkx 2.8.8`, `scikit-learn 1.6.1`, `scipy 1.13.1`, `matplotlib 3.9.4`, `seaborn 0.13.2`.
  - Testing & automation tools: `pytest 8.3.4`, `pytest-asyncio 0.25.3`, `playwright 1.58.0`, `httpx 0.28.1`, `requests 2.32.5`.

### 1.2 Cross-Agent Alignment
- **R1 (CRISP-DM Pipeline)**: Produces pipeline summary (`artifacts/pipeline_summary.json`), exploratory data analysis stats (`artifacts/eda_summary.json`), mined frequent itemsets (`artifacts/frequent_itemsets.json`), and validated association rules (`artifacts/rules.json`).
- **R2 (Automated Research & Hill Climbing)**: Produces paper comparison benchmark metadata and step-by-step optimization logs (`artifacts/optimization_log.json`, `artifacts/optimization_history.csv`).
- **R3 (Our Focus)**: Must consume these artifacts seamlessly, provide interactive visualizers, enable dynamic on-the-fly live mining, and provide complete REST APIs backed by robust 4-Tier test coverage.

---

## 2. Logic Chain

### 2.1 Web Architecture Selection: Flask vs FastAPI vs Dash vs Streamlit
1. **Streamlit Evaluation**:
   - *Limitation*: Requires `streamlit run app.py` instead of standard `python app.py`. Full-page reruns cause UI flickering, loss of complex DOM/Canvas state in network graphs, and building standalone REST APIs (`/health`, `/api/rules`) is awkward and non-standard.
2. **Dash Evaluation**:
   - *Limitation*: Heavy React boilerplate, restrictive CSS layout customization, clunky integration of custom Vis.js physics simulations.
3. **Flask + Tailwind CSS + Modern JS Visualizers (Vis.js, Plotly.js, Chart.js)**:
   - *Rationale*:
     - Executes natively via `python app.py` with zero wrapper complexity.
     - Ultra-fast startup (< 300ms), low memory footprint (< 40MB base).
     - Modular separation: Clean REST API endpoints (`/health`, `/api/...`) + Single-Page responsive UI (`/`).
     - Unlimited UI styling freedom using Tailwind CSS with modern dark/light mode, glassmorphic cards, and responsive sidebars.
     - Best-in-class interactive visualizers: Vis.js Network for force-directed association rule graph, Plotly.js for 3D Support-Confidence-Lift scatter plots, Chart.js for smooth convergence curves and radar charts.
     - 100% testable via standard `pytest` using Flask's `test_client()` without needing a browser, plus headless browser tests via Playwright/httpx.
   - *Decision*: **Flask 3.1+ (with optional FastAPI-compatible modular route blueprint)** running via `python app.py` on default port `5000` (with port fallback / config).

### 2.2 Server Reliability & Graceful Startup
- **Problem**: When starting a dashboard before `run_pipeline.py` or `run_optimization.py` has completed, a naive server that assumes files exist will crash on startup or throw 500 Internal Server Errors.
- **Solution**:
  - Implement a robust Artifact Manager (`ArtifactLoader`) in `app.py`.
  - If artifacts are missing, load embedded fallback sample data and show a non-blocking banner: *"Pipeline artifacts not found. Showing demo dataset. Run `python run_pipeline.py` to populate live data."*
  - Ensure `/health` endpoint responds with 200 OK immediately with artifact readiness flags.
  - Implement automatic port binding with fallback (`5000` -> `8050` -> `5001`) if the target port is in use.

---

## 3. Caveats & Assumptions

1. **Static Asset Loading & CDN Resilience**:
   - *Assumption*: Web interface uses modern JS visualization libraries (Vis.js, Plotly.js, Chart.js, Tailwind CSS, Lucide Icons).
   - *Mitigation*: Include robust CDN links (unpkg / cdnjs) with local offline fallback scripts or bundled static JS files so the dashboard functions reliably even in air-gapped or restricted network environments.
2. **Rule Volume in Network Visualizer**:
   - *Caveat*: Rendering 5,000+ rule edges in a force-directed canvas simultaneously will degrade browser FPS.
   - *Mitigation*: Implement dynamic client/server-side top-$K$ filtering (default top 50–100 highest-lift rules) with a slider allowing user expansion.
3. **Live Mining Sandbox Execution Time**:
   - *Caveat*: Running Apriori with very low support (e.g., 0.0001) on 500k transactions in a single HTTP request could block the main Flask thread.
   - *Mitigation*: Limit sample size or max candidates in live sandbox requests, or run asynchronously with a 5-second timeout guard.

---

## 4. Conclusion & Technical Specifications

```
+----------------------------------------------------------------------------------------------------+
|                                    ASSOCMINING STUDIO ADMIN UI                                     |
+----------------------------------------------------------------------------------------------------+
| [Sidebar]       | [Top Bar: Dataset: Online Retail II | Rules: 142 | Lift: 12.4 | Status: Ready]   |
| - CRISP-DM      +----------------------------------------------------------------------------------+
| - Rule Visualizer | 📊 EXECUTIVE KPI CARDS: Total Transactions | Unique Items | Max Lift | Fitness |
| - Hill Climbing +----------------------------------------------------------------------------------+
| - Live Sandbox  | [TAB 1: CRISP-DM WORKFLOW EXPLORER]                                              |
| - API & Health  |  Phase 1 -> Phase 2 (EDA) -> Phase 3 (Prep) -> Phase 4 -> Phase 5 -> Phase 6     |
|                 +----------------------------------------------------------------------------------+
|                 | [TAB 2: ASSOCIATION RULE VISUALIZER]                                             |
|                 |  +-----------------------------+  +--------------------------------------------+ |
|                 |  | Force-Directed Network Graph|  | 3D Scatter: Support x Confidence x Lift    | |
|                 |  | (Nodes=Items, Edges=Rules)  |  | (Plotly.js 3D rotatable point cloud)       | |
|                 |  +-----------------------------+  +--------------------------------------------+ |
|                 |  [Dynamic Filter Sliders: Min Supp (0.01) | Min Conf (0.50) | Min Lift (2.0)]    |
|                 |  [Searchable Rule Data Table + CSV/JSON Export Buttons]                          |
|                 +----------------------------------------------------------------------------------+
|                 | [TAB 3: AUTOMATED RESEARCH & HILL CLIMBING DASHBOARD]                            |
|                 |  Target Paper: Agrawal et al. / Benchmark Target Match                           |
|                 |  - Fitness vs Iteration Convergence Curve (Best vs Current)                      |
|                 |  - Hyperparameter Trajectory Plot (Supp / Conf / MaxLen / Threshold)             |
|                 |  - Paper vs Discovered Metrics Radar / Bar Comparison Chart                      |
|                 |  - Iteration History Step Table                                                  |
|                 +----------------------------------------------------------------------------------+
|                 | [TAB 4: INTERACTIVE LIVE MINING SANDBOX]                                         |
|                 |  [Algorithm: FP-Growth/Apriori] [Supp: 0.02] [Conf: 0.4] [Mine Now 🚀]           |
|                 |  Realtime Execution Diagnostics (ms) + Instant Rule Output                       |
+----------------------------------------------------------------------------------------------------+
```

### 4.1 Web Architecture & Entrypoint (`app.py`)

#### Code Structure
```
04_associative_pattern_mining/
├── app.py                      # Flask Application Entrypoint
├── config.py                   # Configuration & Port Settings
├── src/
│   ├── dashboard/
│   │   ├── __init__.py
│   │   ├── routes.py           # REST API & Page Routes
│   │   ├── artifact_loader.py  # Safe JSON/CSV Artifact Reader & Fallbacks
│   │   └── live_miner.py       # Sandbox Mining Handler
│   ├── pipeline/               # CRISP-DM Core Engine (from R1)
│   └── optimization/           # Hill Climbing Optimizer (from R2)
├── templates/
│   └── index.html              # Main Modern Admin Dashboard SPA Template
├── static/
│   ├── css/
│   │   └── custom.css          # Custom Dark Mode & Styling
│   └── js/
│       ├── app.js              # Dashboard Orchestration & State Management
│       ├── visualizers.js      # Vis.js Network & Plotly 3D Charts
│       └── sandbox.js          # Interactive Live Mining Sandbox Client
├── artifacts/                  # Generated by R1 and R2
│   ├── eda_summary.json
│   ├── pipeline_summary.json
│   ├── rules.json
│   ├── optimization_log.json
│   └── optimization_history.csv
└── tests/                      # Tiers 1-4 Test Suites
```

#### Entrypoint Interface (`app.py`)
```python
# app.py specification
import os
import sys
from flask import Flask, render_template, jsonify, request, send_file
from src.dashboard.routes import register_blueprints

def create_app(config_override=None):
    app = Flask(__name__, template_folder="templates", static_folder="static")
    app.config["JSON_SORT_KEYS"] = False
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "assocmining-secret-key")
    
    if config_override:
        app.config.update(config_override)
        
    register_blueprints(app)
    return app

app = create_app()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    host = os.environ.get("HOST", "0.0.0.0")
    debug = os.environ.get("DEBUG", "False").lower() in ("true", "1")
    print(f"🚀 Starting Data Science Admin Dashboard on http://{host}:{port}")
    app.run(host=host, port=port, debug=debug)
```

---

### 4.2 REST API Endpoints Specification

| Method | Endpoint | Description | Query / Body Parameters | Response Schema | Status Codes |
|---|---|---|---|---|---|
| `GET` | `/health` | Liveness & Readiness probe | None | `{"status": "healthy", "timestamp": str, "version": str, "artifacts": {"eda": bool, "pipeline": bool, "rules": bool, "optimization": bool}}` | `200` |
| `GET` | `/api/summary` | Executive Overview KPIs | None | `{"total_transactions": int, "unique_items": int, "total_rules": int, "max_lift": float, "mean_confidence": float, "best_fitness": float, "dataset_name": str}` | `200` |
| `GET` | `/api/crisp-dm` | CRISP-DM 6-Phase Status & Metadata | None | `{"phases": [{"phase_id": 1..6, "name": str, "status": "completed"\|"pending", "description": str, "artifacts": list, "metrics": dict}]}` | `200` |
| `GET` | `/api/eda` | Exploratory Data Analysis distributions | None | `{"top_items": [{"item": str, "count": int, "support": float}], "tx_length_distribution": dict, "temporal_patterns": dict, "summary_stats": dict}` | `200` |
| `GET` | `/api/rules` | Filtered Association Rules list | `min_support` (float), `min_confidence` (float), `min_lift` (float), `search` (str), `sort_by` (str), `order` (asc/desc), `limit` (int), `offset` (int) | `{"total_rules": int, "filtered_count": int, "rules": [{"id": int, "antecedents": list, "consequents": list, "support": float, "confidence": float, "lift": float, "leverage": float, "conviction": float, "zhang_metric": float}]}` | `200`, `400` |
| `GET` | `/api/rules/network` | Vis.js Graph Nodes & Edges | `min_lift` (float), `min_confidence` (float), `max_nodes` (int), `max_edges` (int) | `{"nodes": [{"id": str, "label": str, "value": float, "group": str, "title": str}], "edges": [{"from": str, "to": str, "value": float, "title": str, "color": str, "arrows": "to"}]}` | `200` |
| `GET` | `/api/rules/export` | Download rules as CSV or JSON | `format` (`csv` or `json`), `min_lift`, `min_confidence` | File attachment (`association_rules.csv` or `association_rules.json`) | `200`, `400` |
| `GET` | `/api/optimization` | Hill Climbing Paper Benchmarks & Convergence | None | `{"target_paper": {"title": str, "authors": str, "year": int, "citation": str, "benchmark_metrics": dict}, "optimization_summary": {"iterations": int, "best_fitness": float, "convergence_iteration": int, "elapsed_sec": float}, "radar_comparison": dict, "history": list}` | `200` |
| `POST` | `/api/sandbox/mine` | Run Interactive Live Mining | `{"algorithm": "fpgrowth"\|"apriori", "min_support": float, "min_confidence": float, "min_lift": float, "max_len": int, "sample_size": int}` | `{"status": "success", "execution_time_ms": float, "frequent_itemsets_count": int, "rules_count": int, "rules": list, "memory_mb": float}` | `200`, `400`, `500` |
| `GET` | `/api/recommend` | Basket Recommendation Inference | `cart` (comma-separated items, e.g. `?cart=WHITE HANGING HEART,RED BUNTING`) | `{"cart": list, "recommendations": [{"item": str, "confidence": float, "lift": float, "rule_source": str}]}` | `200` |

---

### 4.3 UI & UX Layout Specifications

#### 1. Header & Navigation
- **Left Sidebar**:
  - Logo & Title with pulsating green online badge.
  - Active navigation indicator across 5 tabs:
    - `01. CRISP-DM Workflow`
    - `02. Rule Visualizer`
    - `03. Hill Climbing & Paper`
    - `04. Live Sandbox`
    - `05. Health & API Explorer`
  - Bottom panel: Memory usage, dataset size, engine version (`v1.0.0`).
- **Top Utility Bar**:
  - Dark / Light Mode switcher with localStorage persistence.
  - Quick refresh button to reload artifacts.
  - "Run Full Pipeline" quick trigger.

#### 2. Section A: CRISP-DM Workflow Explorer
- **Interactive Phase Stepper**:
  - 6 interactive cards with visual checkmarks and execution metadata.
  - **Phase 1: Business Understanding**: Problem formulation, ROI potential, market basket optimization goals.
  - **Phase 2: Data Understanding**: Embedded interactive EDA charts (Chart.js):
    - Top 20 Most Frequent Items horizontal bar chart.
    - Transaction Size (basket depth) distribution histogram.
    - Daily & hourly transaction intensity heatmap.
  - **Phase 3: Data Preparation**: Data hygiene visualizer (missing value drop count, negative quantity cancellation removal, one-hot encoding matrix dimension reduction).
  - **Phase 4: Modeling**: Algorithm comparison table (Apriori vs FP-Growth: candidate generation time vs FP-tree growth time, memory footprint).
  - **Phase 5: Evaluation**: Multi-metric evaluation radar and correlation matrix (Support vs Confidence vs Lift vs Conviction vs Zhang's metric).
  - **Phase 6: Deployment**: REST API schema viewer, export triggers, production inference endpoint.

#### 3. Section B: Association Rule Visualizer
- **Dual Visualizer Layout**:
  - **Left / Upper**: Interactive Force-Directed Network Graph (Vis.js Network):
    - Node size scaled by individual item support.
    - Node color grouped by community / product category.
    - Directed arrows representing antecedent $\to$ consequent implications.
    - Edge color mapped to Lift (Viridis scale: Low Lift = Blue, High Lift = Crimson Red).
    - Edge thickness mapped to Confidence ($0.1 - 1.0$).
    - Dynamic physics stabilization: smooth panning, zooming, node pinning, hover tooltips showing `Rule: A -> B | Conf: 85.4% | Lift: 4.82`.
  - **Right / Lower**: 3D Scatter Plot (Plotly.js):
    - X-axis: Support ($0.001 - 0.10$).
    - Y-axis: Confidence ($0.10 - 1.00$).
    - Z-axis: Lift ($1.0 - 15.0+$).
    - Marker color: Lift (plasma palette); Marker size: Rule Length (antecedent + consequent count).
    - Interactive 3D rotation, lasso select, cross-filter sync with data table.
- **Dynamic Control Sliders**:
  - Minimum Support Slider (range `0.001` - `0.10`, step `0.001`).
  - Minimum Confidence Slider (range `0.10` - `1.00`, step `0.05`).
  - Minimum Lift Slider (range `1.0` - `10.0`, step `0.2`).
  - Search input for antecedent / consequent items.
- **Searchable & Sortable Data Table**:
  - Pagination, ascending/descending sorting on all columns (Support, Confidence, Lift, Leverage, Conviction).
  - Action buttons: "Copy Rule JSON", "Export CSV", "Export JSON".

#### 4. Section C: Automated Research & Hill Climbing Progression
- **Target Research Paper Benchmark Card**:
  - Paper Title, Authors, Venue, Citation, Abstract.
  - Reported Paper Benchmarks vs Discovered Results target comparison.
- **Interactive Convergence Curve**:
  - Dual-line Chart.js plot: Iteration (1 to $N$) on X-axis vs Fitness Score on Y-axis.
  - Blue line: `Best Fitness So Far` (strictly non-decreasing).
  - Dotted orange line: `Candidate Fitness` at iteration $i$.
  - Step Type Annotations: Green dots for `Improvement`, Yellow dots for `Plateau / Neutral`, Purple triangles for `Stochastic Restart`.
- **Hyperparameter Trajectory Chart**:
  - 4-axis line chart tracking hyperparameter exploration over iterations (`min_support`, `min_confidence`, `max_len`, `metric_threshold`).
- **Target Paper vs Algorithm Comparison Radar & Bar Chart**:
  - Radar Chart (Spider Plot) measuring normalized metric alignment across 6 dimensions:
    1. Rule Quality / Lift Accuracy
    2. Confidence Alignment
    3. Coverage / Item Diversity
    4. Non-redundancy Score
    5. Rule Length Parsimony
    6. Runtime Efficiency
  - Bar chart showing absolute Paper Value vs Discovered Value vs Delta Error (%).
- **Iteration Step Log Table**:
  - Searchable table containing every iteration step: `Iteration #`, `Hyperparameters`, `Fitness`, `Step Type`, `Decision` (Accepted/Rejected), `Execution Time (ms)`.

#### 5. Section D: Interactive Live Mining Sandbox
- **Parameter Controls Panel**:
  - Algorithm Selector: `FP-Growth` (default, fast) vs `Apriori`.
  - Slider: Min Support (`0.005` - `0.10`).
  - Slider: Min Confidence (`0.10` - `1.00`).
  - Slider: Min Lift (`1.0` - `10.0`).
  - Max Itemset Length: `2`, `3`, `4`, `5`.
  - Sample Size Selector: `1,000 tx`, `10,000 tx`, `Full Dataset`.
  - Button: `🚀 Mine Association Rules` with live spinner and async cancellation support.
- **Realtime Diagnostics & Results Display**:
  - Diagnostic Pills: `Execution Time: 114ms`, `Itemsets Generated: 94`, `Rules Discovered: 32`, `Peak RAM: 42 MB`.
  - Live Rule Cards with instant visual badges for Support, Confidence, and Lift.
  - "Push to Visualizer" button that immediately updates the Network Graph and 3D Scatter with the sandbox rules.

---

### 4.4 System & E2E Testing Strategy (Tiers 1-4)

To ensure the entire system has zero regressions, high reliability, and thorough validation, we define a 4-Tier Test Suite architecture to be detailed in `TEST_INFRA.md`.

```
========================================================================================
                                4-TIER TEST MATRIX
========================================================================================
[ Tier 1: Feature Coverage ]
  - Pipeline Unit Tests (Data cleaning, one-hot encoding, Apriori, FP-Growth, Rule metrics)
  - Optimization Unit Tests (Fitness function, perturbation operators, restart logic)
  - Dashboard API Unit Tests (/health, /api/crisp-dm, /api/rules, /api/optimization, /api/sandbox)

[ Tier 2: Boundary & Edge Cases ]
  - Empty dataset, single item dataset, disjoint itemsets
  - Extreme hyperparameter boundaries (min_support=1.0, min_support=0.00001, min_conf=1.0)
  - Zero-rules scenario handling & graceful fallback
  - Invalid API inputs, missing parameters, out-of-range types (400 responses)

[ Tier 3: Cross-Feature Integration ]
  - Pipeline Execution -> Artifact Creation -> Dashboard API consumption consistency
  - Optimization Execution -> Log Creation -> Dashboard Convergence visualization sync
  - Live Sandbox Mining output parity with Offline Batch Pipeline output
  - Recommendation endpoint accuracy based on mined rule base

[ Tier 4: Real-World Workloads & E2E Acceptance ]
  - End-to-end user workflow: CLI execution -> Dashboard launch -> UI asset delivery -> Rule exploration
  - Full-scale dataset stress test (500,000+ transactions)
  - Server concurrent requests & port binding resilience (< 50ms /health response)
========================================================================================
```

#### Detailed Test Scenarios by Tier

#### Tier 1: Feature Coverage (Unit Tests)
- `test_pipeline_data_cleaning()`: Verifies null customer ID handling, invoice cancellation filtering (e.g. `C` prefixes), and description whitespace trimming.
- `test_one_hot_encoding()`: Verifies binary transaction matrix generation matches ground truth transaction items.
- `test_frequent_itemsets_apriori()`: Verifies frequent itemset discovery satisfies anti-monotonicity (downward-closure property).
- `test_frequent_itemsets_fpgrowth()`: Verifies FP-Growth produces identical frequent itemsets to Apriori.
- `test_association_rules_metrics()`: Verifies mathematical precision of Support, Confidence, Lift, Leverage, Conviction, and Zhang's metric.
- `test_hill_climbing_fitness_function()`: Verifies fitness calculation correctly penalizes deviations from target research paper metrics.
- `test_hill_climbing_mutation_step()`: Verifies state perturbation respects boundary constraints ($0 < \text{min\_support} \le 1.0$).
- `test_api_health_endpoint()`: Asserts `GET /health` returns HTTP 200 with `status == "healthy"`.
- `test_api_rules_filtering()`: Asserts `GET /api/rules?min_lift=2.0` returns only rules with `lift >= 2.0`.
- `test_api_crisp_dm_phases()`: Asserts `GET /api/crisp-dm` returns all 6 phases with valid metadata.

#### Tier 2: Boundary & Edge Cases
- `test_boundary_empty_dataset()`: Ensures pipeline and live sandbox raise clear descriptive errors rather than unhandled index errors when given 0 transactions.
- `test_boundary_single_transaction()`: Validates behavior when dataset contains only 1 transaction (no rules exceeding confidence threshold possible or trivial 1.0 confidence).
- `test_boundary_zero_rules_found()`: Tests dashboard response when filters result in 0 rules (returns empty list with HTTP 200 and total_rules=0, no 500 crash).
- `test_boundary_high_support_threshold()`: Validates behavior when `min_support=1.0` (returns only universal items or empty set).
- `test_boundary_invalid_api_parameters()`: Asserts `POST /api/sandbox/mine` with negative support or invalid algorithm name returns HTTP 400 Bad Request with helpful error message.
- `test_boundary_missing_artifacts()`: Starts dashboard without running pipeline first; asserts `/health` returns 200 OK and dashboard loads sample fallback state without throwing exceptions.

#### Tier 3: Cross-Feature Integration
- `test_integration_pipeline_to_dashboard()`:
  1. Runs `run_pipeline.py --output artifacts/`.
  2. Asserts artifact files exist on disk (`pipeline_summary.json`, `rules.json`).
  3. Queries `GET /api/rules` via Flask test client and asserts returned rules match `artifacts/rules.json`.
- `test_integration_optimization_to_dashboard()`:
  1. Runs `run_optimization.py --iterations 10 --output artifacts/`.
  2. Asserts `artifacts/optimization_log.json` exists.
  3. Queries `GET /api/optimization` and asserts convergence history length matches iterations.
- `test_integration_sandbox_vs_batch_parity()`:
  - Invokes `POST /api/sandbox/mine` with fixed support/confidence and compares output rules against offline pipeline output on identical transaction sample, asserting exact rule equivalence.
- `test_integration_recommendation_flow()`:
  - Queries `GET /api/recommend?cart=ITEM_A` and verifies recommended `ITEM_B` originates from a valid high-lift rule `ITEM_A => ITEM_B`.

#### Tier 4: Real-World Workloads & E2E Acceptance
- `test_e2e_full_scale_dataset_mining()`: Executes pipeline against full Kaggle dataset (e.g. 500,000+ rows) and measures execution time and memory peak.
- `test_e2e_dashboard_startup_and_health()`: Spawns `python app.py` as a subprocess, polls `GET http://localhost:5000/health`, verifies HTTP 200 OK in < 2 seconds, and terminates gracefully with SIGINT.
- `test_e2e_concurrent_api_requests()`: Fires 50 concurrent HTTP requests to `/api/rules` and `/api/eda` to verify server thread-safety and zero 500 errors.
- `test_e2e_static_asset_integrity()`: Validates that all HTML, CSS, and JS script tags in `templates/index.html` resolve properly without 404 broken links.

---

### 4.5 `TEST_INFRA.md` Structure & CI Requirements

The test infrastructure specification file (`TEST_INFRA.md`) will define:
1. **Directory Structure**:
   ```
   tests/
   ├── conftest.py                # Shared pytest fixtures (mock datasets, test client)
   ├── unit/
   │   ├── test_pipeline.py       # Data cleaning & rule mining unit tests
   │   ├── test_optimizer.py      # Hill climbing & fitness unit tests
   │   └── test_api.py            # Flask REST API unit tests
   ├── integration/
   │   ├── test_pipeline_api.py   # Artifact-to-API integration tests
   │   └── test_sandbox_live.py   # Live mining parity tests
   └── e2e/
       ├── test_dashboard_e2e.py  # Server startup, port binding, and health check
       └── test_full_pipeline.py  # Full-scale dataset execution
   ```
2. **Pytest Configuration (`pytest.ini` / `pyproject.toml`)**:
   - Custom test markers: `@pytest.mark.unit`, `@pytest.mark.integration`, `@pytest.mark.e2e`, `@pytest.mark.slow`.
   - Coverage thresholds: Minimum 85% line coverage on `src/`.
3. **Execution Commands**:
   - Fast Unit Tests: `pytest tests/unit/ -v`
   - Integration Tests: `pytest tests/integration/ -v`
   - Full Test Suite: `pytest tests/ -v --cov=src`
   - End-to-End Dashboard Check: `pytest tests/e2e/test_dashboard_e2e.py -v`

---

## 5. Verification Method

To independently verify all specifications in this report:

1. **Verify Web Framework & Core Imports**:
   ```bash
   python3 -c "import flask, jinja2, werkzeug, plotly, pandas, pytest; print('All core dependencies present.')"
   ```
2. **Verify Server Startup & Health Check**:
   ```bash
   # In terminal 1:
   python3 app.py
   # In terminal 2:
   curl -i http://localhost:5000/health
   # Expected: HTTP/1.1 200 OK, {"status": "healthy", ...}
   ```
3. **Verify Test Suite Runner**:
   ```bash
   pytest tests/ -v
   ```
4. **Inspect Specification Artifact**:
   - Inspect `/Users/oleg/Documents/Coding/SJSU/Data Mining/HW1/Part 2/04_associative_pattern_mining/.agents/explorer_survey_3/handoff.md` for complete architectural blueprints and REST API schemas.
