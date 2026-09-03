# Milestone 2 + 3 Handoff Report

**Mission**: Implement R2 (Automated Research & Hill Climbing) and R3 (Data
Science Admin Dashboard), resuming after the previous session was cut off.
**Status**: COMPLETE — 115/115 tests passing, zero skips.
**Date**: 2026-09-02

---

## 1. Starting state

M1 (CRISP-DM pipeline) was complete. The full 4-tier test suite already existed
but M2 and M3 had no implementation, so the suite reported **65 passed, 39
skipped** — the skips being every M2/M3 test guarded by an import check.

## 2. Delivered

### M2 — `src/optimization/` + `run_optimization.py`

| File | Role |
|---|---|
| `papers.py` | Catalog of Ghosh2004 / Agrawal1994 / Chen2012 with bibliographic identity, target metrics, and a `target_basis` field documenting how each operating point was derived. Custom profiles load from JSON. |
| `state.py` | 5D `OptimizationState` + `StateBounds`, with `clip()` projecting out-of-domain proposals back into the feasible region. |
| `fitness.py` | Three modes: weighted normalised squared relative error vs the paper, intrinsic composite quality, and a hybrid blend. Empty rule sets hard-clamped to fitness 0 / loss 1000. |
| `operators.py` | Gaussian mutation scaled per-dimension by span, Rechenberg 1/5th step adaptation, uniform and Latin Hypercube restart sampling. |
| `evaluator.py` | **Mine-once / mask-many** candidate scorer (see §3). |
| `hill_climber.py` | Steepest-ascent search with LHC scouting, stagnation detection, restarts, and a global champion held outside the restart loop. |
| `logger.py` | Writes `optimization_log.json`, `optimization_history.csv`, `optimized_rules.csv`. |

**Result**: best fitness 71.3/100 (from 64.5), 64 iterations, 2 restarts, ~0.5 s.
Three of five target dimensions within 7% (avg support 0.5%, rule count 4.0%,
avg confidence 7.2%); coverage 26.6% and avg lift 141.5% over.

### M3 — `src/dashboard/` + `app.py` + `templates/` + `static/`

| File | Role |
|---|---|
| `artifact_loader.py` | Reads all pipeline/optimization artifacts with mtime-based cache invalidation and well-formed fallbacks when files are absent. |
| `live_miner.py` | Sandbox mining over the production `mine_association_rules` facade, with strict parameter validation and a lazily-loaded process-wide corpus. |
| `routes.py` | Flask app factory + 14 endpoints. |
| `app.py` | Entrypoint honouring `HOST`/`PORT` env vars, reloader disabled. |
| `templates/index.html`, `static/css`, `static/js` | Five-tab SPA console. |

Also added `generate_recommendations()` to `src/evaluation/filter.py` for
`/api/recommend`.

## 3. Key design decision: exact mine-once/mask-many scoring

Scoring one candidate naively means re-running FP-Growth (~0.5–17 s depending on
thresholds). A search evaluates hundreds of candidates, which is unworkable.

`RuleSetEvaluator` mines **once** at the loosest corner of the search domain,
then answers every candidate by masking that superset. Coverage comes from a
bit-packed itemset×transaction incidence matrix. A full search runs in ~0.5 s
after a ~16 s one-time superset build (cached to `artifacts/.cache/`).

This is **exact**, and that mattered: the first implementation disagreed with the
live engine on 5 of 801 rules. The cause was that the engine computes confidence
as a ratio-of-ratios (`42/2225 ÷ 140/2225`), which lands a few ULPs below 0.3 and
drops the rule at a 0.3 threshold, while computing `42/140` directly gives
exactly 0.3 and keeps it. The evaluator now mirrors the engine's arithmetic
deliberately — the contract it owes is that the champion configuration reproduces
this exact rule set when handed back to the miner. Verified across the domain by
`tests/integration/test_optimizer_masking_parity.py` (11 tests) and by
`verify_against_engine()`.

## 4. Defects found and fixed in prior work

1. **`is_rule_redundant` never existed.** `tests/unit/test_redundancy_pruning.py`
   imports it alongside `prune_redundant_rules`; the failing import set both to
   `None`, so all 5 F5 tests skipped silently. Redundancy pruning — which the
   pipeline actively uses to drop 170 rules — had no effective test coverage.
   Implemented it and rewrote the module around it.

2. **Contradictory `prune_redundant_rules` contract.** `test_evaluation.py`
   unpacks a 2-tuple; `test_redundancy_pruning.py` asserts
   `isinstance(result, pd.DataFrame)`. Both cannot hold for one call signature.
   Resolved in favour of the cleaner API (return the DataFrame, gate the count
   behind `return_stats=True`) and updated the single older call site in
   `test_evaluation.py` plus the pipeline caller. **This is the one test file I
   modified** — flagged because changing a test to fit an implementation is
   normally a smell; here two tests contradicted each other and one had to give.

3. **Non-existent Plotly CDN version.** `templates/index.html` pinned
   `plotly.js/2.35.2`, which 404s on cdnjs. Every chart silently failed and, worse,
   the thrown error aborted the rest of the render — the overview's rule table
   disappeared too. Fixed to 2.35.0 *and* made the chart layer degrade
   gracefully so a CDN outage can never again take down non-chart content.

## 5. Verification performed

- `python3 -m pytest tests/ -q` → **115 passed**, 0 skipped, 0 failed.
- `run_pipeline.py` and `run_optimization.py` both exit 0 and regenerate artifacts.
- All 14 endpoints exercised over HTTP against a live server (200s, correct
  shapes, 400 on invalid sandbox parameters).
- Dashboard rendered in headless Chrome and inspected visually: all five tabs,
  both themes, with and without CDN availability, with and without WebGL.
- Sandbox driven end-to-end through the UI (405 rules, 215 itemsets, 462 ms).

## 6. Caveats

- The residual paper-match gap (lift 141% over target) is a property of the
  synthetic corpus, not a search failure — a 3,000-point random sweep of the
  whole domain also tops out near fitness 65. Documented in `README.md`.
  Running against the real ~4,000-item Online Retail ledger would close most of
  it; the loader already supports `--dataset online_retail`.
- The superset cache in `artifacts/.cache/` is keyed on corpus contents and
  domain bounds, so it invalidates itself correctly, but it does grow by ~5 MB
  per distinct corpus. Delete the directory to reclaim it.
- Charts require CDN access for full fidelity; without it the console falls back
  to tables and placeholders rather than failing.
