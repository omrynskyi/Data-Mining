# Associative Pattern Mining Studio

Market-basket association rule mining built end-to-end on the CRISP-DM framework,
with an automated hill-climbing search that tunes the miner to reproduce a
published research paper's reported operating point, and an admin dashboard for
inspecting all of it.

Three deliverables, three entrypoints:

| Requirement | Entrypoint | What it does |
|---|---|---|
| **R1** CRISP-DM pipeline | `python run_pipeline.py` | Six CRISP-DM phases from ingestion to artifact export |
| **R2** Automated research matching | `python run_optimization.py` | Hill-climbs 5 mining hyperparameters toward a paper's metrics |
| **R3** Admin dashboard | `python app.py` | Flask console over every artifact the other two produce |

---

## Quick start

```bash
pip install -r requirements.txt

python run_pipeline.py          # writes artifacts/pipeline_summary.json, rules.*, report
python run_optimization.py      # writes artifacts/optimization_log.json, history, rules
python app.py                   # dashboard on http://localhost:5000
```

Run the pipeline before the optimizer, and both before the dashboard — though the
dashboard degrades gracefully and will tell you which artifacts are missing
rather than rendering empty charts.

```bash
python3 -m pytest tests/ -v     # 115 tests across 4 tiers
```

The dashboard reads `PORT` and `HOST` from the environment, so
`PORT=8080 python app.py` works without editing anything.

---

## R1 — CRISP-DM pipeline

`run_pipeline.py` walks the six phases in order and records what each one did.

**Dataset.** The default corpus is a deterministic synthetic retail ledger
(`data/generate_synthetic.py`, seed 42) modelled on the UCI/Kaggle *Online
Retail* schema, with seven planted affinity clusters (breakfast, coffee, Italian
dinner, bakery, desk/tech, garden, vintage decor) plus realistic noise:
cancellations, administrative stock codes, null descriptions and negative
prices. The loader also accepts `--dataset online_retail|groceries|bakery` or any
CSV path; it falls back to the synthetic generator when a raw file is absent, so
the pipeline runs offline with zero configuration.

**Result on the default corpus:**

| | |
|---|---|
| Raw records → cleaned baskets | 10,370 → 2,225 |
| Unique items | 55 (91.99% sparse matrix) |
| Frequent itemsets | 244 |
| Actionable rules | 626 (170 redundant rules pruned) |
| Runtime | ~0.8 s |

Every rule carries nine interest metrics — support, confidence, lift, leverage,
conviction, Zhang's metric, Kulczynski, imbalance ratio, cosine — and a business
category (high-confidence cross-sell, high-lift affinity pair, emerging niche
bundle, strong symmetric association).

The seven planted clusters are recovered cleanly: the top rules are all
within-cluster (garden tools imply garden tools, desk peripherals imply desk
peripherals) at lift ≈ 6.8–7.0.

---

## R2 — Automated research matching

**Target paper:** Ghosh & Nath, *Multi-objective rule mining using genetic
algorithms*, Information Sciences 163 (2004) 123–133, DOI
`10.1016/j.ins.2003.03.021`. Two more are registered in the catalog
(`--list-papers`): Agrawal & Srikant (VLDB 1994) and Chen, Sain & Guo (2012) —
the last being the case study that donated the Online Retail dataset.

**Search space (5D).** `min_support`, `min_confidence`, `min_lift`, `max_len`,
and `pruning_factor` — the last being the minimum *relative* confidence
improvement a specialised rule must show over its most confident generalisation
to survive redundancy pruning.

**Method.** Steepest-ascent hill climbing: each iteration samples a Gaussian
neighbourhood, evaluates all of it, and moves to the best neighbour if it
improves. Step size adapts by Rechenberg's 1/5th rule. Stalled segments relaunch
from Latin Hypercube restart points, and the global champion is held outside the
restart loop so `best_fitness` is monotonically non-decreasing.

**Fitness.** Hybrid by default: 70% weighted normalised squared relative error
against the paper's five reported metrics, 30% intrinsic rule-set quality
(confidence, lift, coverage, parsimony), with an empty rule set hard-clamped
to zero.

### Result

Best fitness **71.3 / 100**, up from 64.5 at the scouted start, in ~0.5 s of
search over 64 iterations and 2 restarts.

| Metric | Paper target | Achieved | Error |
|---|---|---|---|
| avg support | 0.0250 | 0.0249 | **0.5%** |
| rule count | 50 | 52 | **4.0%** |
| avg confidence | 0.720 | 0.668 | **7.2%** |
| coverage | 0.180 | 0.228 | 26.6% |
| avg lift | 2.450 | 5.916 | **141.5%** |

Champion configuration: `min_support=0.0212`, `min_confidence=0.629`,
`min_lift=3.733`, `max_len=5`, `pruning_factor=0.026`.

### Reading this result honestly

Three of five dimensions land within 7% — the rule-set size and the support
regime are reproduced closely. **The lift gap is structural, not a search
failure.** A 3,000-point random sweep of the entire domain tops out at fitness
≈ 65, and the climber beats that; there is no configuration of these five
parameters that reaches the paper's numbers on this corpus.

The reason is the corpus, not the optimiser. Ghosh & Nath report over a corpus
whose interesting rules sit at lift ≈ 2.5; our synthetic ledger has only 55 items
in seven tightly planted affinity clusters, so any rule strong enough to clear a
confidence floor of 0.6 is *also* a within-cluster rule with lift near 6. Support
and lift are not independently steerable here — pushing lift down to 2.5 means
admitting weak cross-cluster rules, which collapses confidence and rule count
together. The optimiser correctly finds the best available compromise and the
report shows exactly where it is forced to give ground.

Running against a larger, longer-tailed catalogue (the real Online Retail ledger,
~4,000 items) would close most of the lift gap. That is the natural next step,
and the loader already supports it via `--dataset online_retail`.

### Performance note

Scoring one candidate configuration naively means re-running FP-Growth — seconds
per candidate, hundreds of candidates per search. `src/optimization/evaluator.py`
instead mines **once** at the loosest corner of the search domain and answers
every candidate by masking that superset, with coverage answered from a
bit-packed itemset/transaction incidence matrix. A full search drops from minutes
to ~0.5 s.

This is exact, not approximate: the masked rule set is byte-for-byte what a fresh
mining run at those thresholds returns, including the engine's own floating-point
tie behaviour. `tests/integration/test_optimizer_masking_parity.py` pins that
equivalence across the domain, and `RuleSetEvaluator.verify_against_engine()`
re-checks it against a live mining run on demand.

---

## R3 — Admin dashboard

`python app.py` serves a five-tab single-page console. Tabs are deep-linkable
(`/#rules`, `/#optimization`, …).

- **Overview** — KPI strip, pipeline configuration, rule categories, top rules.
- **CRISP-DM Workflow** — clickable six-phase stepper showing what each phase
  recorded, plus basket-size distribution, item frequency, and the full data
  preparation ledger.
- **Rule Visualizer** — force-directed item network (Vis.js), support × confidence
  × lift 3D scatter (Plotly), live filter sliders, sortable table, CSV/JSON
  export, and a basket recommender.
- **Hill Climbing** — target paper card with per-dimension target-vs-achieved
  bars, convergence curve (candidate fitness against the running champion, with
  restarts marked), normalised hyperparameter trajectory, and the full iteration
  log.
- **Live Sandbox** — re-mine the corpus on demand at your own thresholds against
  the *production* engine, with timing diagnostics, a sweep history across your
  runs, and a push-to-visualizer handoff.

### REST API

```
GET  /health              GET  /api/rules            GET  /api/optimization
GET  /api/summary         GET  /api/rules/network    POST /api/sandbox/mine
GET  /api/crisp-dm        GET  /api/rules/scatter    GET  /api/sandbox/corpus
GET  /api/eda             GET  /api/rules/export     GET  /api/recommend?cart=a,b
GET  /api/itemsets        GET  /api/catalog/items
```

### Robustness

The console is built to stay useful when things are missing:

- **No artifacts yet** — every endpoint returns a well-formed empty structure and
  `/health` reports which artifact families exist, so the UI says "run
  `run_pipeline.py`" instead of rendering zeros.
- **CDN unreachable** — Plotly and Vis.js load from a CDN; if either is missing,
  the affected chart shows a placeholder and every table and metric on the page
  still renders.
- **No WebGL** — the 3D rule-space plot falls back to a 2D support × confidence
  projection with lift carried by marker colour and size.
- **Artifacts rewritten while running** — the loader caches on modification time,
  so re-running the pipeline is picked up on the next request without a restart.

---

## Testing

115 tests across four tiers, all passing, no skips:

```
tests/unit/          Tier 1 & 2  feature coverage + boundary/corner cases
tests/integration/   Tier 3      cross-feature: CLI → artifacts → API consistency
tests/e2e/           Tier 4      subprocess server startup, /health probe, full runs
```

```bash
python3 -m pytest tests/ -v
python3 -m pytest tests/ -q --cov=src --cov-report=term-missing
```

---

## Layout

```
run_pipeline.py       run_optimization.py       app.py        config.py
src/
  data/         loader, preprocessor, schema
  eda/          basket/frequency/sparsity profiler
  mining/       apriori, fpgrowth, rules, 9 interest metrics, engine facade
  evaluation/   multi-metric filtering, redundancy pruning, recommendations
  optimization/ papers, state, fitness, operators, evaluator, hill_climber, logger
  dashboard/    routes, artifact_loader, live_miner
  deployment/   exporter, pipeline orchestrator
templates/  static/  artifacts/  tests/
```
