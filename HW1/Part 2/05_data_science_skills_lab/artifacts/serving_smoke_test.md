# Serving Smoke Test Transcript

Real FastAPI service (`src/p6_serve.py`), started with `uvicorn`, bound to `127.0.0.1:8321`
only, exercised with real HTTP requests via `requests`, then shut down. Raw output in
`artifacts/serving_smoke_test_raw.txt`.

## Startup

```
model loaded in 0.86s
Uvicorn running on http://127.0.0.1:8321
```
Model loaded once at process startup (verified by the single log line above appearing exactly
once across the whole test, including the 240 requests below) — not per request, per the
skill's #1 pitfall.

## Endpoint checks

| # | Case | Result |
|---|---|---|
| 1 | `GET /health` | 200 `{"status":"ok"}` |
| 2 | `GET /ready` | 200, reports `model_version` + real `threshold=0.28554...` |
| 3 | `POST /predict`, 1 real customer | 200, probability 0.6783, risk_band=high, flagged=true |
| 4 | `POST /predict`, batch of 50 real customers | 200, 50 predictions returned |
| 5 | Malformed: invalid `Contract` enum (`"Lifetime"`) | **422**, Pydantic literal_error naming the field and valid choices |
| 6 | Malformed: missing required field (`MonthlyCharges`) | **422**, Pydantic missing-field error |
| 7 | Malformed: empty `customers: []` | **422**, explicit "must not be empty" |
| 8 | Malformed: `TotalCharges="not-a-number"` | **422**, custom validator message |
| 9 | Edge case: real tenure==0 customer with blank `TotalCharges` | **200** — correctly handled, not a 422 |

Case 9 matters: a blank `TotalCharges` is *valid* (11 real customers ship this way), while
non-numeric garbage is not — the service's custom Pydantic validator distinguishes the two
correctly rather than rejecting all non-float strings.

## Load test — real measured latency, not estimated

- **220 sequential single-record requests** (random real customers, seed 42): 0 errors.
  **p50 = 50.48ms, p95 = 55.74ms, p99 = 61.42ms, mean = 50.95ms.**
- **20 batch requests of 50 customers each** (1,000 customers total): p50 = 53.29ms,
  p95 = 81.70ms, mean = 54.41ms.

**Finding worth reporting, not smoothing over**: batch-of-50 latency (mean 54ms) is barely
higher than single-record latency (mean 51ms). The cost here is dominated by fixed per-request
overhead (the sklearn `Pipeline.transform` + `CalibratedClassifierCV.predict_proba` call graph,
not the O(n) row-scoring itself, which is vectorized) rather than by payload size — meaning the
service is currently *underusing* its own `/predict` batch support. The practical implication
for the retention team's actual monthly workflow (score ~7,000 customers) is that a **single
batch call is dramatically cheaper than 7,000 single-record calls**, not the other way around:
naive back-of-envelope math from the p50s above gives ~354s (7,000 × 50.5ms) for the
single-record path vs ~7.4s (7,000/50 × 53.3ms) for batches of 50 — a lesson the client
integration should follow.

## Shutdown

Process killed after the test; `curl` to `/health` afterward confirmed connection refused —
no orphaned server left running.
