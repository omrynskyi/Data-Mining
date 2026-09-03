// REST API client for the Data Science & Analytics Skills Lab backend
// (webapp/server/main.py, FastAPI on :8005, proxied at /api by Vite in dev).
//
// NOTE on response shape: unlike many reference implementations of this app,
// this real backend returns FLAT JSON from every endpoint -- no
// {"success": true, "data": {...}} envelope. E.g. GET /api/benchmarks/titanic
// returns {dataset, model, metrics, confusion_matrix, roc_curve, ...} directly.
// The one exception is /api/skills/catalog, which wraps as {count, skills}.
// Verified live against the real running server -- see webapp/server/api_smoke_test.md.

const BASE_URL = '/api';

async function getJSON(path) {
  const res = await fetch(`${BASE_URL}${path}`);
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    const err = new Error(body.detail ? JSON.stringify(body.detail) : `${res.status} ${path}`);
    err.status = res.status;
    throw err;
  }
  return res.json();
}

async function postJSON(path, body) {
  const res = await fetch(`${BASE_URL}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const err = new Error(data.detail ? JSON.stringify(data.detail) : `${res.status} ${path}`);
    err.status = res.status;
    err.body = data;
    throw err;
  }
  return data;
}

export const api = {
  getHealth: () => getJSON('/health'),
  // { count, skills: [...] }
  getSkillsCatalog: () => getJSON('/skills/catalog'),
  // -> { skill_id, skill_name, benchmark_link, result }
  executeSkill: (skillId) => postJSON('/skills/execute', { skill_id: skillId }),

  // Every benchmark getter below returns its payload directly (flat, no wrapper).
  getTitanicBenchmark: () => getJSON('/benchmarks/titanic'),
  getHousePricesBenchmark: () => getJSON('/benchmarks/house-prices'),
  getFraudBenchmark: () => getJSON('/benchmarks/fraud'),
  getEcommerceBenchmark: () => getJSON('/benchmarks/ecommerce'),
  getDataQualityBenchmark: () => getJSON('/benchmarks/data-quality'),
  getTelcoBenchmark: () => getJSON('/benchmarks/telco'),

  // -> two-proportion z-test result object, directly
  calculateAbTest: (params) => postJSON('/ab-test/calculate', params),
  // body: { customers: [ {..raw Telco columns.., TotalCharges: "29.85"} ] }
  // -> { model_version, threshold, latency_ms, predictions: [{customerID, probability, risk_band, flagged}] }
  predictTelcoChurn: (customers) => postJSON('/telco/predict', { customers }),

  // -> { project, total_skills, phases: [{phase, skill_count, skills:[...]}] }
  getCrispDmReport: () => getJSON('/crisp-dm/report'),
};
