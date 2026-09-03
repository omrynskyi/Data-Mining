import React, { useState, useMemo } from 'react';
import { AlertTriangle } from 'lucide-react';

function pct(v, digits = 2) {
  return v != null ? `${(v * 100).toFixed(digits)}%` : '--';
}

export function FraudDetectionView({ data = {} }) {
  const {
    dataset, sampling_note, real_full_dataset_fraud_rate_pct, sample_fraud_rate_pct,
    n_train, n_test, baseline_logreg, balanced_logreg, precision_recall_curve = [],
    f1_optimal_threshold,
  } = data;

  const n = precision_recall_curve.length;
  const [idx, setIdx] = useState(0);

  const current = precision_recall_curve[Math.min(idx, Math.max(0, n - 1))];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
      <div className="card">
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '0.6rem', marginBottom: '0.75rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
            <AlertTriangle size={20} style={{ color: 'var(--accent-rose)' }} />
            <h2 style={{ fontSize: '1.15rem', fontWeight: 800 }}>Credit Card Fraud Detection</h2>
          </div>
          <span className="badge-real-data">Real trained model</span>
        </div>
        <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '0.75rem' }}>{dataset}</p>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))', gap: '0.75rem', marginBottom: '0.9rem' }}>
          <div className="stat-tile">
            <div className="stat-tile-label">Real full-dataset fraud rate</div>
            <div className="stat-tile-value" style={{ color: 'var(--accent-rose)' }}>{real_full_dataset_fraud_rate_pct}%</div>
          </div>
          <div className="stat-tile">
            <div className="stat-tile-label">Training-sample fraud rate</div>
            <div className="stat-tile-value" style={{ color: 'var(--accent-amber)' }}>{sample_fraud_rate_pct}%</div>
          </div>
          <div className="stat-tile">
            <div className="stat-tile-label">n_train / n_test</div>
            <div className="stat-tile-value">{n_train} / {n_test}</div>
          </div>
        </div>

        {sampling_note && (
          <div style={{ background: 'var(--bg-tertiary)', border: '1px solid var(--border-cyan)', borderRadius: 'var(--radius-md)', padding: '0.75rem 0.9rem', fontSize: '0.8rem', color: 'var(--text-secondary)', lineHeight: 1.5 }}>
            <strong style={{ color: 'var(--accent-cyan-bright)' }}>Sampling note (honest, not hidden): </strong>{sampling_note}
          </div>
        )}
      </div>

      <div className="card">
        <h3 style={{ fontSize: '0.95rem', fontWeight: 800, marginBottom: '0.3rem' }}>The Accuracy Paradox: Baseline vs. Class-Balanced</h3>
        <p style={{ fontSize: '0.78rem', color: 'var(--text-muted)', marginBottom: '0.9rem' }}>
          The unweighted model looks precise but recalls far less real fraud than the balanced model -- accuracy alone hides this on imbalanced data.
        </p>
        <div className="data-table-container" style={{ padding: 0 }}>
          <table className="data-table">
            <thead>
              <tr>
                <th>Model</th>
                <th>Precision</th>
                <th>Recall</th>
                <th>F1</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td>Baseline LogReg <span style={{ color: 'var(--text-muted)', fontSize: '0.72rem' }}>({baseline_logreg?.description})</span></td>
                <td>{pct(baseline_logreg?.metrics?.precision)}</td>
                <td style={{ color: 'var(--accent-rose)', fontWeight: 700 }}>{pct(baseline_logreg?.metrics?.recall)}</td>
                <td>{pct(baseline_logreg?.metrics?.f1)}</td>
              </tr>
              <tr>
                <td>Balanced LogReg <span style={{ color: 'var(--text-muted)', fontSize: '0.72rem' }}>({balanced_logreg?.description})</span></td>
                <td>{pct(balanced_logreg?.metrics?.precision)}</td>
                <td style={{ color: 'var(--accent-emerald-bright)', fontWeight: 700 }}>{pct(balanced_logreg?.metrics?.recall)}</td>
                <td>{pct(balanced_logreg?.metrics?.f1)}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <div className="card">
        <h3 style={{ fontSize: '0.95rem', fontWeight: 800, marginBottom: '0.3rem' }}>Precision-Recall Threshold Explorer</h3>
        <p style={{ fontSize: '0.78rem', color: 'var(--text-muted)', marginBottom: '0.9rem' }}>
          Reading the real precision-recall curve ({n} points from the trained model's held-out predictions) at a chosen operating point --
          not a simulation. F1-optimal probability threshold: <strong style={{ color: 'var(--text-primary)' }}>{f1_optimal_threshold}</strong>.
        </p>
        {n > 0 && (
          <>
            <input
              type="range"
              min={0}
              max={n - 1}
              value={idx}
              onChange={(e) => setIdx(Number(e.target.value))}
              style={{ width: '100%', accentColor: 'var(--accent-cyan)' }}
            />
            <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', marginBottom: '0.9rem' }}>
              Operating point {idx + 1} of {n} on the real curve
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '0.75rem' }}>
              <div className="stat-tile">
                <div className="stat-tile-label">Precision at this point</div>
                <div className="stat-tile-value" style={{ color: 'var(--accent-cyan-bright)' }}>{pct(current?.precision)}</div>
              </div>
              <div className="stat-tile">
                <div className="stat-tile-label">Recall at this point</div>
                <div className="stat-tile-value" style={{ color: 'var(--accent-emerald-bright)' }}>{pct(current?.recall)}</div>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}

export default FraudDetectionView;
