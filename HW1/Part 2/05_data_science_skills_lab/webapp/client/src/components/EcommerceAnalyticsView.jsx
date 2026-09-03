import React, { useState } from 'react';
import { TrendingUp, FlaskConical } from 'lucide-react';
import { api } from '../utils/api';

function retentionColor(pct) {
  if (pct == null) return 'transparent';
  const clamped = Math.max(0, Math.min(100, pct));
  const alpha = 0.08 + (clamped / 100) * 0.55;
  return `rgba(6, 182, 212, ${alpha.toFixed(3)})`;
}

function RevenueChart({ monthly = [] }) {
  if (!monthly.length) return null;
  const W = 720, H = 260, PAD = 46;
  const values = monthly.map((m) => m.revenue);
  const max = Math.max(...values);
  const stepX = (W - 2 * PAD) / Math.max(1, monthly.length - 1);
  const x = (i) => PAD + i * stepX;
  const y = (v) => (H - PAD) - (v / max) * (H - 2 * PAD);
  const linePath = monthly.map((m, i) => `${i === 0 ? 'M' : 'L'} ${x(i).toFixed(1)} ${y(m.revenue).toFixed(1)}`).join(' ');
  const areaPath = `${linePath} L ${x(monthly.length - 1).toFixed(1)} ${H - PAD} L ${x(0).toFixed(1)} ${H - PAD} Z`;

  return (
    <svg viewBox={`0 0 ${W} ${H}`} style={{ width: '100%', height: 'auto' }}>
      <defs>
        <linearGradient id="revFill" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="var(--accent-cyan)" stopOpacity="0.35" />
          <stop offset="100%" stopColor="var(--accent-cyan)" stopOpacity="0" />
        </linearGradient>
      </defs>
      <line x1={PAD} y1={H - PAD} x2={W - PAD} y2={H - PAD} stroke="var(--border-subtle)" strokeWidth="1" />
      <path d={areaPath} fill="url(#revFill)" stroke="none" />
      <path d={linePath} fill="none" stroke="var(--accent-cyan-bright)" strokeWidth="2.5" />
      {monthly.map((m, i) => (
        <circle key={m.month} cx={x(i)} cy={y(m.revenue)} r="2.5" fill="var(--accent-cyan-bright)" />
      ))}
      {monthly.map((m, i) => (
        i % 2 === 0 ? (
          <text key={m.month} x={x(i)} y={H - PAD + 16} fontSize="8" fill="var(--text-muted)" textAnchor="middle">{m.month}</text>
        ) : null
      ))}
      <text x={4} y={PAD} fontSize="9" fill="var(--text-muted)">${(max / 1000).toFixed(0)}k</text>
    </svg>
  );
}

function AbTestCalculator() {
  const [form, setForm] = useState({ n_control: 1000, x_control: 100, n_treatment: 1000, x_treatment: 130 });
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  function update(field, value) {
    setForm((f) => ({ ...f, [field]: Number(value) }));
  }

  async function calculate() {
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const res = await api.calculateAbTest(form);
      setResult(res);
    } catch (err) {
      setError(err.message || 'Failed to calculate.');
    } finally {
      setLoading(false);
    }
  }

  const fields = [
    { key: 'n_control', label: 'Control visitors' },
    { key: 'x_control', label: 'Control conversions' },
    { key: 'n_treatment', label: 'Treatment visitors' },
    { key: 'x_treatment', label: 'Treatment conversions' },
  ];

  return (
    <div className="card">
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.4rem' }}>
        <FlaskConical size={18} style={{ color: 'var(--accent-violet)' }} />
        <h3 style={{ fontSize: '0.95rem', fontWeight: 800 }}>A/B Test Calculator</h3>
      </div>
      <p style={{ fontSize: '0.76rem', color: 'var(--text-muted)', marginBottom: '0.9rem' }}>
        Live two-proportion z-test computed by the backend on every click -- a real calculation, not a lookup.
      </p>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))', gap: '0.75rem', marginBottom: '0.9rem' }}>
        {fields.map((f) => (
          <label key={f.key} style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>
            {f.label}
            <input
              type="number"
              min="0"
              value={form[f.key]}
              onChange={(e) => update(f.key, e.target.value)}
              style={{
                display: 'block', width: '100%', marginTop: '0.25rem', padding: '0.5rem 0.6rem',
                borderRadius: 'var(--radius-md)', border: '1px solid var(--border-subtle)',
                background: 'var(--bg-tertiary)', color: 'var(--text-primary)', fontSize: '0.85rem',
              }}
            />
          </label>
        ))}
      </div>
      <button className="btn-primary" onClick={calculate} disabled={loading}>
        {loading ? <span className="spinner" /> : 'Calculate'}
      </button>
      {error && <p style={{ color: 'var(--accent-rose)', fontSize: '0.8rem', marginTop: '0.6rem' }}>{error}</p>}
      {result && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))', gap: '0.75rem', marginTop: '1rem' }}>
          <div className="stat-tile">
            <div className="stat-tile-label">Relative lift</div>
            <div className="stat-tile-value" style={{ color: 'var(--accent-emerald-bright)' }}>{result.relative_lift_pct}%</div>
          </div>
          <div className="stat-tile">
            <div className="stat-tile-label">z-statistic</div>
            <div className="stat-tile-value">{result.z_statistic}</div>
          </div>
          <div className="stat-tile">
            <div className="stat-tile-label">p-value</div>
            <div className="stat-tile-value">{result.p_value}</div>
          </div>
          <div className="stat-tile">
            <div className="stat-tile-label">Significant (95%)</div>
            <div className="stat-tile-value" style={{ color: result.significant_at_95pct ? 'var(--accent-emerald-bright)' : 'var(--accent-rose)' }}>
              {result.significant_at_95pct ? 'Yes' : 'No'}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export function EcommerceAnalyticsView({ data = {} }) {
  const { dataset, cohort_retention, engagement_funnel, revenue_time_series } = data;
  const cohorts = cohort_retention?.matrix || [];
  const monthKeys = ['month_0', 'month_1', 'month_2', 'month_3', 'month_4', 'month_5', 'month_6'];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
      <div className="card">
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '0.6rem', marginBottom: '0.5rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
            <TrendingUp size={20} style={{ color: 'var(--accent-cyan-bright)' }} />
            <h2 style={{ fontSize: '1.15rem', fontWeight: 800 }}>E-Commerce Analytics</h2>
          </div>
          <span className="badge-real-data">Real transaction data</span>
        </div>
        <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>{dataset}</p>
      </div>

      <div className="card">
        <h3 style={{ fontSize: '0.95rem', fontWeight: 800, marginBottom: '0.3rem' }}>Cohort Retention</h3>
        {cohort_retention?.note && (
          <p style={{ fontSize: '0.74rem', color: 'var(--text-muted)', marginBottom: '0.9rem', lineHeight: 1.5 }}>{cohort_retention.note}</p>
        )}
        <div className="data-table-container" style={{ padding: '0.5rem' }}>
          <table className="data-table">
            <thead>
              <tr>
                <th>Cohort</th>
                <th>Size</th>
                {monthKeys.map((m) => <th key={m}>{m.replace('month_', 'M+')}</th>)}
              </tr>
            </thead>
            <tbody>
              {cohorts.map((c) => (
                <tr key={c.cohort}>
                  <td>{c.cohort}</td>
                  <td>{c.cohort_size}</td>
                  {monthKeys.map((m) => (
                    <td key={m} style={{ background: retentionColor(c[m]), textAlign: 'center' }}>
                      {c[m] != null ? `${c[m].toFixed(1)}%` : '--'}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <div className="card">
        <h3 style={{ fontSize: '0.95rem', fontWeight: 800, marginBottom: '0.3rem' }}>Engagement Funnel <span style={{ fontWeight: 600, fontSize: '0.7rem', color: 'var(--text-muted)', textTransform: 'none' }}>(derived from real repeat-purchase behavior, not literal browse events)</span></h3>
        {engagement_funnel?.note && (
          <p style={{ fontSize: '0.74rem', color: 'var(--text-muted)', marginBottom: '0.9rem', lineHeight: 1.5 }}>{engagement_funnel.note}</p>
        )}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.6rem' }}>
          {(engagement_funnel?.stages || []).map((s, i) => (
            <div key={s.stage}>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.78rem', marginBottom: '0.2rem' }}>
                <span style={{ color: 'var(--text-secondary)' }}>{s.stage}</span>
                <span style={{ color: 'var(--text-muted)' }}>{s.count.toLocaleString()} ({s.conversion_from_start_pct}% of start)</span>
              </div>
              <div style={{ height: 14, background: 'var(--bg-tertiary)', borderRadius: 'var(--radius-full)', overflow: 'hidden' }}>
                <div style={{
                  width: `${s.conversion_from_start_pct}%`, height: '100%',
                  background: 'linear-gradient(90deg, var(--accent-indigo), var(--accent-cyan))',
                }} />
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="card">
        <h3 style={{ fontSize: '0.95rem', fontWeight: 800, marginBottom: '0.3rem' }}>Monthly Revenue</h3>
        {revenue_time_series?.note && (
          <p style={{ fontSize: '0.74rem', color: 'var(--text-muted)', marginBottom: '0.9rem', lineHeight: 1.5 }}>{revenue_time_series.note}</p>
        )}
        <RevenueChart monthly={revenue_time_series?.monthly || []} />
      </div>

      <AbTestCalculator />
    </div>
  );
}

export default EcommerceAnalyticsView;
