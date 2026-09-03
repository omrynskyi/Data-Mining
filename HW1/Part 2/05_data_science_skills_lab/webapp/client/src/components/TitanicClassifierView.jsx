import React from 'react';
import { Users } from 'lucide-react';

const STAT_LABELS = {
  accuracy: 'Accuracy', precision: 'Precision', recall: 'Recall', f1: 'F1', roc_auc: 'ROC-AUC',
};

function RocCurveSvg({ points = [] }) {
  if (!points.length) return null;
  const W = 380, H = 300, PAD = 42;
  const x = (v) => PAD + v * (W - 2 * PAD);
  const y = (v) => (H - PAD) - v * (H - 2 * PAD);
  const path = points.map((p, i) => `${i === 0 ? 'M' : 'L'} ${x(p.fpr).toFixed(1)} ${y(p.tpr).toFixed(1)}`).join(' ');

  return (
    <svg viewBox={`0 0 ${W} ${H}`} style={{ width: '100%', maxWidth: 420, height: 'auto' }}>
      <line x1={PAD} y1={H - PAD} x2={W - PAD} y2={H - PAD} stroke="var(--border-subtle)" strokeWidth="1" />
      <line x1={PAD} y1={PAD} x2={PAD} y2={H - PAD} stroke="var(--border-subtle)" strokeWidth="1" />
      <line x1={x(0)} y1={y(0)} x2={x(1)} y2={y(1)} stroke="var(--text-muted)" strokeWidth="1" strokeDasharray="4 4" />
      <path d={path} fill="none" stroke="var(--accent-cyan-bright)" strokeWidth="2.5" />
      <text x={PAD} y={H - PAD + 18} fontSize="10" fill="var(--text-muted)">0</text>
      <text x={W - PAD - 8} y={H - PAD + 18} fontSize="10" fill="var(--text-muted)">1</text>
      <text x={PAD - 28} y={H - PAD + 4} fontSize="10" fill="var(--text-muted)">0</text>
      <text x={PAD - 28} y={PAD + 4} fontSize="10" fill="var(--text-muted)">1</text>
      <text x={W / 2 - 30} y={H - 8} fontSize="10" fill="var(--text-muted)">False Positive Rate</text>
      <text x={10} y={H / 2} fontSize="10" fill="var(--text-muted)" transform={`rotate(-90 10 ${H / 2})`}>True Positive Rate</text>
    </svg>
  );
}

export function TitanicClassifierView({ data = {} }) {
  const {
    dataset, model, data_quality_note, n_train, n_test, real_survival_rate,
    metrics = {}, confusion_matrix, roc_curve = [], feature_importances = [],
  } = data;

  const maxImportance = Math.max(1e-9, ...feature_importances.map((f) => f.importance));

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
      <div className="card">
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '0.6rem', marginBottom: '0.75rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
            <Users size={20} style={{ color: 'var(--accent-cyan-bright)' }} />
            <h2 style={{ fontSize: '1.15rem', fontWeight: 800 }}>Titanic Survival Classifier</h2>
          </div>
          <span className="badge-real-data">Real trained model</span>
        </div>
        <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '0.4rem' }}>{dataset}</p>
        <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginBottom: '0.75rem' }}>{model}</p>
        {data_quality_note && (
          <div style={{ background: 'var(--bg-tertiary)', border: '1px solid rgba(245, 158, 11, 0.3)', borderRadius: 'var(--radius-md)', padding: '0.7rem 0.9rem', fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
            <strong style={{ color: 'var(--accent-amber)' }}>Data quality note: </strong>{data_quality_note}
          </div>
        )}
        <div style={{ display: 'flex', gap: '1.5rem', marginTop: '0.9rem', fontSize: '0.78rem', color: 'var(--text-muted)' }}>
          <span>n_train: <strong style={{ color: 'var(--text-primary)' }}>{n_train}</strong></span>
          <span>n_test: <strong style={{ color: 'var(--text-primary)' }}>{n_test}</strong></span>
          <span>Real survival rate: <strong style={{ color: 'var(--text-primary)' }}>{real_survival_rate != null ? `${(real_survival_rate * 100).toFixed(2)}%` : '--'}</strong></span>
        </div>
      </div>

      <div className="card">
        <h3 style={{ fontSize: '0.95rem', fontWeight: 800, marginBottom: '0.9rem' }}>Model Metrics</h3>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(110px, 1fr))', gap: '0.75rem' }}>
          {Object.entries(STAT_LABELS).map(([key, label]) => (
            <div key={key} className="stat-tile">
              <div className="stat-tile-label">{label}</div>
              <div className="stat-tile-value" style={{ color: 'var(--accent-cyan-bright)' }}>
                {metrics[key] != null ? metrics[key].toFixed(4) : '--'}
              </div>
            </div>
          ))}
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'minmax(240px, 320px) 1fr', gap: '1.25rem' }}>
        <div className="card">
          <h3 style={{ fontSize: '0.95rem', fontWeight: 800, marginBottom: '0.9rem' }}>Confusion Matrix</h3>
          {confusion_matrix?.matrix ? (
            <div style={{ display: 'grid', gridTemplateColumns: 'auto 1fr 1fr', gap: '0.4rem', fontSize: '0.8rem' }}>
              <div />
              {confusion_matrix.labels.map((l) => (
                <div key={l} style={{ textAlign: 'center', color: 'var(--text-muted)', fontWeight: 700, textTransform: 'capitalize' }}>pred: {l}</div>
              ))}
              {confusion_matrix.matrix.map((row, i) => (
                <React.Fragment key={i}>
                  <div style={{ color: 'var(--text-muted)', fontWeight: 700, textTransform: 'capitalize', display: 'flex', alignItems: 'center' }}>
                    actual: {confusion_matrix.labels[i]}
                  </div>
                  {row.map((v, j) => (
                    <div key={j} style={{
                      textAlign: 'center', padding: '1rem 0.5rem', borderRadius: 'var(--radius-md)', fontWeight: 800, fontSize: '1.1rem',
                      background: i === j ? 'rgba(16, 185, 129, 0.15)' : 'rgba(244, 63, 94, 0.1)',
                      color: i === j ? 'var(--accent-emerald-bright)' : 'var(--accent-rose)',
                    }}>
                      {v}
                    </div>
                  ))}
                </React.Fragment>
              ))}
            </div>
          ) : <p style={{ color: 'var(--text-muted)', fontSize: '0.82rem' }}>Loading...</p>}
        </div>

        <div className="card">
          <h3 style={{ fontSize: '0.95rem', fontWeight: 800, marginBottom: '0.9rem' }}>ROC Curve</h3>
          <RocCurveSvg points={roc_curve} />
        </div>
      </div>

      <div className="card">
        <h3 style={{ fontSize: '0.95rem', fontWeight: 800, marginBottom: '0.9rem' }}>Feature Importance</h3>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.55rem' }}>
          {feature_importances.map((f) => (
            <div key={f.feature}>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.78rem', marginBottom: '0.2rem' }}>
                <span style={{ color: 'var(--text-secondary)', fontFamily: 'var(--font-mono)' }}>{f.feature}</span>
                <span style={{ color: 'var(--text-muted)' }}>{(f.importance * 100).toFixed(2)}%</span>
              </div>
              <div style={{ height: 8, background: 'var(--bg-tertiary)', borderRadius: 'var(--radius-full)', overflow: 'hidden' }}>
                <div style={{
                  width: `${(f.importance / maxImportance) * 100}%`, height: '100%',
                  background: 'linear-gradient(90deg, var(--accent-indigo), var(--accent-cyan))',
                }} />
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

export default TitanicClassifierView;
