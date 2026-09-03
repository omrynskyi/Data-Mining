---
skill: model-serving
pack: param087/agent-ml-skills
crisp_dm_phase: 6 - Deployment
artifacts: [src/p6_serve.py, artifacts/serving_smoke_test.md, artifacts/serving_smoke_test_raw.txt, artifacts/inference_contract.json]
---

## What the skill prescribes

- Serving shifts the concern from accuracy to **latency, throughput, robustness,
  observability**. The model artifact and its preprocessing must travel together — ship the
  pipeline, not just the estimator.
- Load the model once at startup, not per request. Validate inputs with Pydantic, return 422 on
  bad payloads. Health *and* readiness endpoints. Version the model in the response. Batch
  where possible. Monitor operationally (latency/error-rate) and ML-specifically (drift).
- Named pitfalls: training/serving skew, per-request loading, no input validation, loading
  untrusted pickles, no monitoring.

## Applied to Telco churn

`src/p6_serve.py` is a real FastAPI service for `artifacts/model.joblib`, generated against
`artifacts/inference_contract.json` (the Phase 4/5 hand-off contract) — not a hand-rolled schema
that happens to resemble it. Started with `uvicorn`, exercised with live HTTP requests, load
tested, and shut down; full transcript and numbers in `artifacts/serving_smoke_test.md`.

**Model + preprocessing ship together**, per the skill's core requirement: `model.joblib` is
the full `CalibratedClassifierCV(Pipeline(FeatureEngineer → ColumnTransformer → XGBClassifier))`
object produced by Phase 4/5 — the service never re-implements cleaning or feature construction,
it just calls `.predict_proba()` on the raw-schema DataFrame.

**Loaded once at startup**: an `@app.on_event("startup")` handler loads the model; verified in
the smoke test by the single "model loaded in 0.86s" log line appearing exactly once across the
full 240-request test.

**Input validation, and where it caught a real contract error**: a `pydantic.BaseModel` with
`Literal[...]` enums for every categorical column (values pulled from the actual data, not
guessed) rejects any out-of-vocabulary category with a 422 naming the field and the valid
choices (smoke test case 5). Building this validator is what surfaced the `TotalCharges` bug
documented in `llm-finetuning.md` and corrected in `inference_contract.json`: the raw column
ships as a string, sometimes blank (11 real tenure==0 customers) — the service accepts
`TotalCharges: str` with a custom validator that allows blank/whitespace OR a numeric string,
rejects anything else (smoke test case 6), and the request handler runs the exact
`pd.to_numeric(...str.strip()...)` coercion the pipeline silently requires (smoke test case 9
confirms the real blank-TotalCharges edge case scores correctly, not as an error).

**Health vs readiness, distinguished on purpose**: `/health` is a pure liveness probe (process
is up); `/ready` additionally reports `model_version` and the real `chosen_threshold`
(0.28554...) and 503s if the model hasn't finished loading — the distinction orchestrators like
k8s actually need (a container can be alive but not yet able to serve).

**Batching supported and its real effect measured**, not assumed: the load test moved 1,000
customers through in ~1.07s of measured request time via 20 batches of 50, vs a projected ~354s
extrapolated from the single-record p50 for the same volume sent one at a time — see the "worth
reporting" finding in `serving_smoke_test.md` for the actual per-request-overhead-dominated
latency profile behind that gap.

**Model versioning in the response**: every `/predict` response carries `model_version:
"telco-churn-classifier-v1"`, matching the MLflow registry version registered in
`experiment-tracking.md` — a caller can trace any prediction back to the exact registered run.

### ONNX / quantization — considered, not applied

The skill's speed section suggests ONNX + quantization for 2-4x CPU speedup. Measured p50
latency here is already ~50ms per request with **0 errors over 220 sequential + 1,000 batched
requests** and the bottleneck is fixed per-request overhead, not raw compute — so ONNX export is
not justified for this model/workload today. Documented as a considered-and-declined
optimization rather than silently skipped: it would matter if p50 needed to drop below ~10ms for
a real-time (not monthly-batch) use case.

### Monitoring plan (specified, since there is no production traffic yet to monitor)

- **Operational**: request latency p50/p95/p99 and error rate, already instrumented via the
  `request_id` + `latency_ms` fields on every response and the `log.info` line — the smoke test
  numbers above are what a real dashboard would track from day one.
- **Input drift** — the features that matter here, from the Phase 2 association ranking: watch
  the distribution of `Contract`, `InternetService`, `PaymentMethod`, `MonthlyCharges`, and
  `tenure` category shares against the training distribution (e.g. population stability index
  per feature); these are the top Cramér's-V / point-biserial drivers, so drift in them is what
  would most plausibly silently degrade the model.
- **Prediction drift**: the mean predicted probability and the `flagged` rate should track
  training-time expectations (~26.5% base rate, ~50% flagged at this capacity-tuned threshold);
  a sustained shift in either without a matching shift in true churn is the standard silent-
  degradation signal the skill warns about.
- **Label drift (when labels arrive)**: this is a monthly-cadence business process — actual
  churn outcomes become known roughly a month after a risk list is acted on. Re-validate
  `roc_auc`/`pr_auc` against realized outcomes every cycle; alert if PR-AUC drops meaningfully
  below the 0.6681 test baseline. **Note the honest limitation**: no production traffic exists
  yet to backtest this plan against, since this is a training-time hand-off, not a running
  service — the plan is specified and instrumented for, not yet exercised on real drift.
- **Only load artifacts this project produced**: `model.joblib` is loaded from the local
  `artifacts/` directory this lab wrote; the skill's untrusted-pickle pitfall doesn't apply here
  but the service does not load any path from user input, so it can't be redirected to one.

## Outputs produced

- `src/p6_serve.py` — the FastAPI service.
- `artifacts/serving_smoke_test.md` + `_raw.txt` — full live-request transcript, 9 endpoint
  cases, 240-request load test with real p50/p95/p99.
- `artifacts/inference_contract.json` — corrected during this work (see the `TotalCharges` note
  above) to state the true I/O contract the service and any other caller must follow.
