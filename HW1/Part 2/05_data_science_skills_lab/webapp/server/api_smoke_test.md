# API Smoke Test Transcript

Real FastAPI service (`webapp/server/main.py`), started with `uvicorn`, bound to
`127.0.0.1:8005` only, exercised with real HTTP requests via `requests`, then shut down
cleanly. Also verified with a real pytest suite (`webapp/server/test_api.py`, 22 tests,
using FastAPI's `TestClient` against the real app -- real startup event, real pipelines,
no mocks).

## Startup timing

```
2026-09-02 22:15:11,522 all pipelines warmed in 39.34s -- {'titanic': 0.115,
  'house_prices': 0.805, 'fraud': 0.903, 'data_quality_audit': 36.754,
  'ecommerce': 0.681, 'telco_benchmark': 0.005, 'telco_model': 0.082}
INFO:     Application startup complete.
```

Server became ready in **42.84s** (measured wall-clock from process launch to
`Application startup complete`). Nearly all of that time (36.75s) is the real
`data-quality-audit` pipeline's column-by-column `nunique()` pass over 541,909 rows,
including two free-text `object` columns (`Description`, `StockCode`) with thousands of
distinct values -- a real, not artificial, cost. This runs **once at startup**, per the
model-serving skill's core lesson (also applied in `src/p6_serve.py`): every subsequent
`GET /api/benchmarks/*` call is served from an in-memory `functools.lru_cache`, never
retrained/recomputed per request.

## pytest suite -- 22/22 passed

```
test_api.py::test_health PASSED
test_api.py::test_skills_catalog_has_48_entries PASSED
test_api.py::test_titanic_benchmark_real_survival_rate PASSED
test_api.py::test_house_prices_benchmark PASSED
test_api.py::test_fraud_benchmark_real_rate PASSED
test_api.py::test_ecommerce_benchmark PASSED
test_api.py::test_data_quality_benchmark PASSED
test_api.py::test_telco_benchmark_real_churn_rate PASSED
test_api.py::test_telco_predict_real_customer PASSED
test_api.py::test_telco_predict_tenure_zero_blank_total_charges PASSED
test_api.py::test_telco_predict_malformed_enum_returns_422 PASSED
test_api.py::test_telco_predict_empty_list_returns_422 PASSED
test_api.py::test_ab_test_calculate PASSED
test_api.py::test_ab_test_malformed_returns_422 PASSED
test_api.py::test_skills_execute_routes_correctly[imbalanced-data-fraud] PASSED
test_api.py::test_skills_execute_routes_correctly[data-quality-audit-ecommerce] PASSED
test_api.py::test_skills_execute_routes_correctly[sklearn-pipelines-titanic] PASSED
test_api.py::test_skills_execute_routes_correctly[cohort-analysis-ecommerce] PASSED
test_api.py::test_skills_execute_routes_correctly[business-metrics-calculator-telco] PASSED
test_api.py::test_skills_execute_data_quality_audit_returns_real_quality_result PASSED
test_api.py::test_skills_execute_unknown_skill_404 PASSED
test_api.py::test_crisp_dm_report PASSED
======================= 22 passed, 2 warnings in 44.39s ========================
```

## Live HTTP endpoint checks (real requests, real server)

| # | Endpoint | Result | Real value cross-checked |
|---|---|---|---|
| 1 | `GET /api/health` | 200 (13.2ms) | `ready: true`, startup timings present |
| 2 | `GET /api/skills/catalog` | 200 (5.0ms) | `count: 48` |
| 3 | `GET /api/benchmarks/titanic` | 200 (2.8ms) | `real_survival_rate: 0.3838` (matches real 38.38%), `roc_auc: 0.8487` |
| 4 | `GET /api/benchmarks/house-prices` | 200 (2.8ms) | `real_sale_price_mean: 180796.06` (exact match to real Ames mean), `r2: 0.8812` |
| 5 | `GET /api/benchmarks/fraud` | 200 (6.5ms) | `real_full_dataset_fraud_rate_pct: 0.1727` (exact match to published ULB stat) |
| 6 | `GET /api/benchmarks/ecommerce` | 200 (2.6ms) | 13 real cohorts, 4-stage funnel, 13 months of real revenue |
| 7 | `GET /api/benchmarks/data-quality` | 200 (2.0ms) | `missing_customer_id_pct: 24.927` (matches real ~25%), `quality_score: 86.04` |
| 8 | `GET /api/benchmarks/telco` | 200 (2.5ms) | `logo_churn_rate_base_pct: 26.537`, `roc_auc: 0.8481761347490248` (exact match to `final_metrics.json`) |
| 9 | `GET /api/crisp-dm/report` | 200 (3.1ms) | `total_skills: 48`, 6 phases summing to 48 |
| 10 | `GET /api/benchmarks/titanic` (repeat, cache check) | 200 (2.7ms) | Identical payload, same latency class as first call -- confirms cache, not retraining |
| 11 | `POST /api/telco/predict` (real customer 7590-VHVEG) | 200 (58.6ms) | `probability: 0.6783`, `risk_band: high`, `flagged: true` -- matches the same live-model path proven in `artifacts/serving_smoke_test.md` |
| 12 | `POST /api/telco/predict` (bad enum `Contract: "Lifetime"`) | **422** (1.9ms) | Pydantic `literal_error` naming the field and valid choices, not a 500 |
| 13 | `POST /api/ab-test/calculate` (1000/100 vs 1000/130) | 200 (3.1ms) | `z: 2.1027`, `p: 0.035488`, `significant_at_95pct: true` -- correct two-proportion z-test math |
| 14 | `POST /api/skills/execute` `imbalanced-data` | 200 (2.1ms) | Routed to `fraud`; returned real baseline (P=0.964/R=0.870) vs balanced (P=0.519/R=0.886) comparison |
| 15 | `POST /api/skills/execute` `data-quality-audit` | 200 (1.9ms) | Routed to `ecommerce`; returned the **actual** quality-audit dict (`quality_score`, `real_issues`), not the generic ecommerce analytics payload -- see bug note below |
| 16 | `POST /api/skills/execute` `sklearn-pipelines` | 200 (2.4ms) | Routed to `titanic`; returned the real leakage-free pipeline result |
| 17 | `POST /api/skills/execute` `cohort-analysis` | 200 (2.4ms) | Routed to `ecommerce`; returned real `cohort_retention` slice only |
| 18 | `POST /api/skills/execute` `business-metrics-calculator` | 200 (2.0ms) | Routed to `telco`; returned real `business_metrics` slice only |
| 19 | `POST /api/skills/execute` (unknown `skill_id: "nope"`) | **404** (1.6ms) | `{"detail": "unknown skill_id: nope"}` |

Additional cases exercised via the pytest suite (not re-shown above): `tenure==0` with a
blank `TotalCharges` string returns **200** (a genuinely valid record per the inference
contract, distinct from actually-malformed input), and an empty `customers: []` list
returns **422**.

## Bug found and fixed during this smoke test

The first pass of `/api/skills/execute` routed by `benchmark_link` and returned whatever
that benchmark's pipeline produced verbatim. Since `data-quality-audit`'s `benchmark_link`
is `"ecommerce"` (it audits the Online Retail export), the router was calling
`run_ecommerce_analytics()` and returning the *cohort/funnel/revenue* payload for a
data-quality-audit request -- silently wrong. Fixed in `main.py`'s `_skill_highlight()` to
call `run_data_quality_audit()` directly for that skill id instead of reusing the generic
`benchmark_result`. Re-verified live (case #15 above) and covered by
`test_skills_execute_data_quality_audit_returns_real_quality_result` in the pytest suite.

## Shutdown

```
$ kill <pid>
$ lsof -ti:8005        # (no output -- port free)
$ curl -m 2 http://127.0.0.1:8005/api/health
curl: (7) Failed to connect to 127.0.0.1 port 8005 after ... Connection refused
```

Process killed after the test; port confirmed free and the health endpoint confirmed
unreachable -- no orphaned server left running.
