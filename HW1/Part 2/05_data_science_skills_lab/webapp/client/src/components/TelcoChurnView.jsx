import React, { useState } from 'react';
import { PhoneCall, Zap } from 'lucide-react';
import { api } from '../utils/api';

const SELECT_FIELDS = {
  gender: ['Female', 'Male'],
  Partner: ['No', 'Yes'],
  Dependents: ['No', 'Yes'],
  PhoneService: ['No', 'Yes'],
  MultipleLines: ['No', 'No phone service', 'Yes'],
  InternetService: ['DSL', 'Fiber optic', 'No'],
  OnlineSecurity: ['No', 'No internet service', 'Yes'],
  OnlineBackup: ['No', 'No internet service', 'Yes'],
  DeviceProtection: ['No', 'No internet service', 'Yes'],
  TechSupport: ['No', 'No internet service', 'Yes'],
  StreamingTV: ['No', 'No internet service', 'Yes'],
  StreamingMovies: ['No', 'No internet service', 'Yes'],
  Contract: ['Month-to-month', 'One year', 'Two year'],
  PaperlessBilling: ['No', 'Yes'],
  PaymentMethod: ['Bank transfer (automatic)', 'Credit card (automatic)', 'Electronic check', 'Mailed check'],
  SeniorCitizen: ['0', '1'],
};

const DEFAULT_CUSTOMER = {
  customerID: '7590-VHVEG',
  gender: 'Female', SeniorCitizen: '0', Partner: 'Yes', Dependents: 'No', tenure: 1,
  PhoneService: 'No', MultipleLines: 'No phone service', InternetService: 'DSL',
  OnlineSecurity: 'No', OnlineBackup: 'Yes', DeviceProtection: 'No', TechSupport: 'No',
  StreamingTV: 'No', StreamingMovies: 'No', Contract: 'Month-to-month',
  PaperlessBilling: 'Yes', PaymentMethod: 'Electronic check', MonthlyCharges: 29.85,
  TotalCharges: '29.85',
};

function fmtUsd(v, digits = 0) {
  if (v == null) return '--';
  return `$${v.toLocaleString('en-US', { maximumFractionDigits: digits })}`;
}

function PredictWidget({ threshold }) {
  const [form, setForm] = useState(DEFAULT_CUSTOMER);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  function update(field, value) {
    setForm((f) => ({ ...f, [field]: value }));
  }

  async function predict() {
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const payload = { ...form, SeniorCitizen: Number(form.SeniorCitizen), tenure: Number(form.tenure), MonthlyCharges: Number(form.MonthlyCharges) };
      const res = await api.predictTelcoChurn([payload]);
      setResult(res.predictions?.[0]);
    } catch (err) {
      setError(err.message || 'Prediction failed.');
    } finally {
      setLoading(false);
    }
  }

  const riskColor = { low: 'var(--accent-emerald-bright)', medium: 'var(--accent-amber)', high: 'var(--accent-rose)' };

  return (
    <div className="card">
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.3rem' }}>
        <Zap size={18} style={{ color: 'var(--accent-cyan-bright)' }} />
        <h3 style={{ fontSize: '0.95rem', fontWeight: 800 }}>Live Churn Prediction</h3>
      </div>
      <p style={{ fontSize: '0.76rem', color: 'var(--text-muted)', marginBottom: '1rem' }}>
        Calls the real serving pipeline (POST /api/telco/predict). Pre-filled with real customer 7590-VHVEG.
      </p>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))', gap: '0.65rem', marginBottom: '1rem' }}>
        {Object.entries(SELECT_FIELDS).map(([field, options]) => (
          <label key={field} style={{ fontSize: '0.68rem', color: 'var(--text-muted)' }}>
            {field}
            <select
              value={form[field]}
              onChange={(e) => update(field, e.target.value)}
              style={{
                display: 'block', width: '100%', marginTop: '0.25rem', padding: '0.45rem 0.5rem',
                borderRadius: 'var(--radius-md)', border: '1px solid var(--border-subtle)',
                background: 'var(--bg-tertiary)', color: 'var(--text-primary)', fontSize: '0.8rem',
              }}
            >
              {options.map((o) => <option key={o} value={o}>{o}</option>)}
            </select>
          </label>
        ))}
        <label style={{ fontSize: '0.68rem', color: 'var(--text-muted)' }}>
          tenure (months)
          <input type="number" min="0" max="72" value={form.tenure} onChange={(e) => update('tenure', e.target.value)}
            style={{ display: 'block', width: '100%', marginTop: '0.25rem', padding: '0.45rem 0.5rem', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-subtle)', background: 'var(--bg-tertiary)', color: 'var(--text-primary)', fontSize: '0.8rem' }} />
        </label>
        <label style={{ fontSize: '0.68rem', color: 'var(--text-muted)' }}>
          MonthlyCharges
          <input type="number" step="0.01" min="18.25" max="118.75" value={form.MonthlyCharges} onChange={(e) => update('MonthlyCharges', e.target.value)}
            style={{ display: 'block', width: '100%', marginTop: '0.25rem', padding: '0.45rem 0.5rem', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-subtle)', background: 'var(--bg-tertiary)', color: 'var(--text-primary)', fontSize: '0.8rem' }} />
        </label>
        <label style={{ fontSize: '0.68rem', color: 'var(--text-muted)' }}>
          TotalCharges (string, blank ok for tenure=0)
          <input type="text" value={form.TotalCharges} onChange={(e) => update('TotalCharges', e.target.value)}
            style={{ display: 'block', width: '100%', marginTop: '0.25rem', padding: '0.45rem 0.5rem', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-subtle)', background: 'var(--bg-tertiary)', color: 'var(--text-primary)', fontSize: '0.8rem' }} />
        </label>
      </div>

      <button className="btn-primary" onClick={predict} disabled={loading}>
        {loading ? <span className="spinner" /> : 'Predict'}
      </button>
      {error && <p style={{ color: 'var(--accent-rose)', fontSize: '0.8rem', marginTop: '0.6rem' }}>{error}</p>}
      {result && (
        <div style={{ marginTop: '1rem', display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))', gap: '0.75rem' }}>
          <div className="stat-tile">
            <div className="stat-tile-label">Churn Probability</div>
            <div className="stat-tile-value" style={{ color: 'var(--accent-cyan-bright)' }}>{(result.probability * 100).toFixed(2)}%</div>
          </div>
          <div className="stat-tile">
            <div className="stat-tile-label">Risk Band</div>
            <div className="stat-tile-value" style={{ color: riskColor[result.risk_band], textTransform: 'uppercase' }}>{result.risk_band}</div>
          </div>
          <div className="stat-tile">
            <div className="stat-tile-label">Flagged (&ge; threshold)</div>
            <div className="stat-tile-value" style={{ color: result.flagged ? 'var(--accent-rose)' : 'var(--accent-emerald-bright)' }}>{result.flagged ? 'Yes' : 'No'}</div>
          </div>
          <div className="stat-tile">
            <div className="stat-tile-label">Decision Threshold</div>
            <div className="stat-tile-value">{threshold != null ? threshold.toFixed(4) : '--'}</div>
          </div>
        </div>
      )}
    </div>
  );
}

export function TelcoChurnView({ data = {} }) {
  const { dataset, business_metrics = {}, model_metrics = {}, segment_profiles = [], campaign_expected_value = {} } = data;
  const { population = {}, revenue = {}, churn = {}, ltv = {} } = business_metrics;
  const evTable = campaign_expected_value.ev_table || [];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
      <div className="card">
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '0.6rem', marginBottom: '0.5rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
            <PhoneCall size={20} style={{ color: 'var(--accent-cyan-bright)' }} />
            <h2 style={{ fontSize: '1.15rem', fontWeight: 800 }}>Telco Customer Churn -- Full CRISP-DM Lab</h2>
          </div>
          <span className="badge-real-data">Real business + model + serving layer</span>
        </div>
        <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>{dataset}</p>
      </div>

      <div className="card">
        <h3 style={{ fontSize: '0.95rem', fontWeight: 800, marginBottom: '0.9rem' }}>Real Business Metrics</h3>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))', gap: '0.75rem' }}>
          <div className="stat-tile">
            <div className="stat-tile-label">Customers</div>
            <div className="stat-tile-value">{population.n_customers?.toLocaleString()}</div>
          </div>
          <div className="stat-tile">
            <div className="stat-tile-label">MRR (all)</div>
            <div className="stat-tile-value" style={{ color: 'var(--accent-emerald-bright)' }}>{fmtUsd(revenue.mrr_all_customers)}</div>
          </div>
          <div className="stat-tile">
            <div className="stat-tile-label">ARPU</div>
            <div className="stat-tile-value">{fmtUsd(revenue.arpu_all_customers, 2)}</div>
          </div>
          <div className="stat-tile">
            <div className="stat-tile-label">Logo Churn Rate</div>
            <div className="stat-tile-value" style={{ color: 'var(--accent-rose)' }}>{churn.logo_churn_rate_base_pct}%</div>
          </div>
          <div className="stat-tile">
            <div className="stat-tile-label">Revenue Churn Rate</div>
            <div className="stat-tile-value" style={{ color: 'var(--accent-rose)' }}>{churn.revenue_churn_rate_base_pct}%</div>
          </div>
          <div className="stat-tile">
            <div className="stat-tile-label">Realized Churned MRR</div>
            <div className="stat-tile-value" style={{ color: 'var(--accent-amber)' }}>{fmtUsd(business_metrics.revenue_at_risk?.realized_churned_mrr)}</div>
          </div>
        </div>
        {ltv.ltv_tenure_based_formula && (
          <p style={{ fontSize: '0.74rem', color: 'var(--text-muted)', marginTop: '0.9rem', lineHeight: 1.5 }}>
            Tenure-based empirical LTV (used for campaign ROI, not the survivorship-biased hazard figure): {fmtUsd(ltv.ltv_tenure_based_empirical, 2)}.
          </p>
        )}
      </div>

      <div className="card">
        <h3 style={{ fontSize: '0.95rem', fontWeight: 800, marginBottom: '0.9rem' }}>Real Model Metrics</h3>
        <p style={{ fontSize: '0.76rem', color: 'var(--text-muted)', marginBottom: '0.75rem' }}>{model_metrics.model}</p>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(120px, 1fr))', gap: '0.75rem' }}>
          {['roc_auc', 'pr_auc', 'precision', 'recall', 'f1', 'accuracy'].map((k) => (
            <div key={k} className="stat-tile">
              <div className="stat-tile-label">{k.replace('_', '-').toUpperCase()}</div>
              <div className="stat-tile-value" style={{ color: 'var(--accent-cyan-bright)' }}>{model_metrics[k] != null ? model_metrics[k].toFixed(4) : '--'}</div>
            </div>
          ))}
        </div>
        <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)', marginTop: '0.9rem' }}>
          Chosen threshold: <strong style={{ color: 'var(--text-primary)' }}>{model_metrics.chosen_threshold?.toFixed(4)}</strong> (calibrated for {model_metrics.chosen_threshold_capacity_pct}% retention-team contact capacity)
        </div>
      </div>

      {segment_profiles.length > 0 && (
        <div className="card">
          <h3 style={{ fontSize: '0.95rem', fontWeight: 800, marginBottom: '0.9rem' }}>Customer Segments</h3>
          <div className="data-table-container" style={{ padding: '0.5rem' }}>
            <table className="data-table">
              <thead>
                <tr>
                  <th>Segment</th>
                  <th>Share</th>
                  <th>Churn Rate</th>
                  <th>ARPU</th>
                  <th>Avg Tenure</th>
                  <th>MRR at Risk</th>
                </tr>
              </thead>
              <tbody>
                {segment_profiles.map((s) => (
                  <tr key={s.cluster}>
                    <td>{s.label}</td>
                    <td>{s.share_pct}%</td>
                    <td style={{ color: s.churn_rate_pct > 30 ? 'var(--accent-rose)' : 'var(--text-secondary)' }}>{s.churn_rate_pct}%</td>
                    <td>{fmtUsd(s.arpu, 2)}</td>
                    <td>{s.avg_tenure?.toFixed(1)} mo</td>
                    <td>{fmtUsd(s.mrr_at_risk)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {evTable.length > 0 && (
        <div className="card">
          <h3 style={{ fontSize: '0.95rem', fontWeight: 800, marginBottom: '0.3rem' }}>Retention Campaign Expected Value</h3>
          <p style={{ fontSize: '0.74rem', color: 'var(--text-muted)', marginBottom: '0.9rem' }}>
            Recommended contact capacity: <strong style={{ color: 'var(--text-primary)' }}>{campaign_expected_value.recommended_capacity_pct}%</strong> of the base
            (net EV {fmtUsd(campaign_expected_value.recommended_capacity_net_ev_usd)}).
          </p>
          <div className="data-table-container" style={{ padding: '0.5rem' }}>
            <table className="data-table">
              <thead>
                <tr>
                  <th>Capacity</th>
                  <th>Contacted</th>
                  <th>Precision@k</th>
                  <th>Expected Saves</th>
                  <th>Campaign Cost</th>
                  <th>Net EV</th>
                </tr>
              </thead>
              <tbody>
                {evTable.map((row) => (
                  <tr key={row.capacity_pct} style={row.capacity_pct === campaign_expected_value.recommended_capacity_pct ? { background: 'rgba(6, 182, 212, 0.08)' } : undefined}>
                    <td>{row.capacity_pct}%</td>
                    <td>{row.n_contacted}</td>
                    <td>{(row.precision_at_k * 100).toFixed(1)}%</td>
                    <td>{row.expected_saves}</td>
                    <td>{fmtUsd(row.campaign_cost)}</td>
                    <td style={{ color: 'var(--accent-emerald-bright)', fontWeight: 700 }}>{fmtUsd(row.net_ev_primary_12mo_arpu)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      <PredictWidget threshold={model_metrics.chosen_threshold} />
    </div>
  );
}

export default TelcoChurnView;
