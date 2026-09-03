import React from 'react';
import { ShieldCheck } from 'lucide-react';

const ISSUE_LABELS = {
  missing_customer_id: 'Missing Customer ID',
  duplicate_rows: 'Duplicate Rows',
  cancelled_invoice: 'Cancelled Invoices',
  negative_quantity: 'Negative Quantity',
  zero_or_negative_unit_price: 'Zero/Negative Unit Price',
};

function issueRows(real_issues = {}) {
  const rowKeys = Object.keys(ISSUE_LABELS);
  return rowKeys
    .filter((key) => `${key}_rows` in real_issues)
    .map((key) => ({
      label: ISSUE_LABELS[key],
      rows: real_issues[`${key}_rows`],
      pct: real_issues[`${key}_pct`],
    }));
}

export function DataQualityAuditView({ data = {} }) {
  const {
    dataset, n_rows, n_columns, columns_audit = [], real_issues = {},
    completeness_score, quality_score, scoring_note,
  } = data;

  const issues = issueRows(real_issues);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
      <div className="card">
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '0.6rem', marginBottom: '0.5rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
            <ShieldCheck size={20} style={{ color: 'var(--accent-emerald-bright)' }} />
            <h2 style={{ fontSize: '1.15rem', fontWeight: 800 }}>Data Quality Audit</h2>
          </div>
          <span className="badge-real-data">Real audit, real dataset</span>
        </div>
        <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '0.75rem' }}>{dataset}</p>
        <div style={{ display: 'flex', gap: '1.5rem', fontSize: '0.78rem', color: 'var(--text-muted)' }}>
          <span>Rows: <strong style={{ color: 'var(--text-primary)' }}>{n_rows?.toLocaleString()}</strong></span>
          <span>Columns: <strong style={{ color: 'var(--text-primary)' }}>{n_columns}</strong></span>
        </div>
      </div>

      <div className="card">
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '1.5rem', alignItems: 'center', marginBottom: '0.9rem' }}>
          <div className="stat-tile" style={{ minWidth: 180 }}>
            <div className="stat-tile-label">Quality Score</div>
            <div className="stat-tile-value" style={{ fontSize: '2rem', color: 'var(--accent-emerald-bright)' }}>{quality_score}</div>
          </div>
          <div className="stat-tile" style={{ minWidth: 180 }}>
            <div className="stat-tile-label">Completeness Score</div>
            <div className="stat-tile-value" style={{ color: 'var(--accent-cyan-bright)' }}>{completeness_score}</div>
          </div>
        </div>
        {scoring_note && (
          <div style={{ background: 'var(--bg-tertiary)', border: '1px solid var(--border-cyan)', borderRadius: 'var(--radius-md)', padding: '0.75rem 0.9rem', fontSize: '0.8rem', color: 'var(--text-secondary)', lineHeight: 1.5 }}>
            <strong style={{ color: 'var(--accent-cyan-bright)' }}>How this score is computed: </strong>{scoring_note}
          </div>
        )}
      </div>

      <div className="card">
        <h3 style={{ fontSize: '0.95rem', fontWeight: 800, marginBottom: '0.9rem' }}>Real Data Issues Found</h3>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(170px, 1fr))', gap: '0.75rem' }}>
          {issues.map((issue) => (
            <div key={issue.label} className="stat-tile">
              <div className="stat-tile-label">{issue.label}</div>
              <div className="stat-tile-value" style={{ color: 'var(--accent-amber)' }}>{issue.pct}%</div>
              <div style={{ fontSize: '0.68rem', color: 'var(--text-muted)', marginTop: '0.15rem' }}>{issue.rows?.toLocaleString()} rows</div>
            </div>
          ))}
        </div>
      </div>

      <div className="card">
        <h3 style={{ fontSize: '0.95rem', fontWeight: 800, marginBottom: '0.9rem' }}>Per-Column Audit</h3>
        <div className="data-table-container" style={{ padding: '0.5rem' }}>
          <table className="data-table">
            <thead>
              <tr>
                <th>Column</th>
                <th>Dtype</th>
                <th>Null Count</th>
                <th>Null %</th>
                <th>Unique Values</th>
              </tr>
            </thead>
            <tbody>
              {columns_audit.map((c) => (
                <tr key={c.column}>
                  <td style={{ fontFamily: 'var(--font-mono)' }}>{c.column}</td>
                  <td style={{ color: 'var(--text-muted)' }}>{c.dtype}</td>
                  <td>{c.null_count?.toLocaleString()}</td>
                  <td style={{ color: c.null_pct > 0 ? 'var(--accent-amber)' : 'var(--text-muted)' }}>{c.null_pct}%</td>
                  <td>{c.unique_count?.toLocaleString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

export default DataQualityAuditView;
