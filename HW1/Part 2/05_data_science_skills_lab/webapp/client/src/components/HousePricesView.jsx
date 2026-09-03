import React from 'react';
import { DollarSign } from 'lucide-react';

function fmtUsd(v) {
  if (v == null) return '--';
  return `$${v.toLocaleString('en-US', { maximumFractionDigits: 0 })}`;
}

function ScatterSvg({ points = [] }) {
  if (!points.length) return null;
  const W = 520, H = 380, PAD = 56;
  const allVals = points.flatMap((p) => [p.actual, p.predicted]);
  const min = Math.min(...allVals), max = Math.max(...allVals);
  const scale = (v) => PAD + ((v - min) / (max - min)) * (W - 2 * PAD);
  const yScale = (v) => (H - PAD) - ((v - min) / (max - min)) * (H - 2 * PAD);

  return (
    <svg viewBox={`0 0 ${W} ${H}`} style={{ width: '100%', height: 'auto' }}>
      <line x1={PAD} y1={H - PAD} x2={W - PAD} y2={H - PAD} stroke="var(--border-subtle)" strokeWidth="1" />
      <line x1={PAD} y1={PAD} x2={PAD} y2={H - PAD} stroke="var(--border-subtle)" strokeWidth="1" />
      <line x1={scale(min)} y1={yScale(min)} x2={scale(max)} y2={yScale(max)} stroke="var(--text-muted)" strokeWidth="1" strokeDasharray="4 4" />
      {points.map((p, i) => (
        <circle key={i} cx={scale(p.actual)} cy={yScale(p.predicted)} r="3" fill="var(--accent-cyan-bright)" fillOpacity="0.55" />
      ))}
      <text x={PAD} y={H - PAD + 20} fontSize="10" fill="var(--text-muted)">{fmtUsd(min)}</text>
      <text x={W - PAD - 60} y={H - PAD + 20} fontSize="10" fill="var(--text-muted)">{fmtUsd(max)}</text>
      <text x={W / 2 - 60} y={H - 10} fontSize="10" fill="var(--text-muted)">Actual Sale Price</text>
      <text x={12} y={H / 2} fontSize="10" fill="var(--text-muted)" transform={`rotate(-90 12 ${H / 2})`}>Predicted Sale Price</text>
    </svg>
  );
}

export function HousePricesView({ data = {} }) {
  const {
    dataset, model, data_quality_note, n_train, n_test, real_sale_price_mean,
    metrics = {}, feature_importances = [], actual_vs_predicted_sample = [],
  } = data;

  const maxImportance = Math.max(1e-9, ...feature_importances.map((f) => f.importance));

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
      <div className="card">
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '0.6rem', marginBottom: '0.75rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
            <DollarSign size={20} style={{ color: 'var(--accent-emerald-bright)' }} />
            <h2 style={{ fontSize: '1.15rem', fontWeight: 800 }}>Ames House Price Regressor</h2>
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
          <span>Real mean sale price: <strong style={{ color: 'var(--text-primary)' }}>{fmtUsd(real_sale_price_mean)}</strong></span>
        </div>
      </div>

      <div className="card">
        <h3 style={{ fontSize: '0.95rem', fontWeight: 800, marginBottom: '0.9rem' }}>Model Metrics</h3>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))', gap: '0.75rem' }}>
          <div className="stat-tile">
            <div className="stat-tile-label">RMSE</div>
            <div className="stat-tile-value" style={{ color: 'var(--accent-emerald-bright)' }}>{fmtUsd(metrics.rmse)}</div>
          </div>
          <div className="stat-tile">
            <div className="stat-tile-label">MAE</div>
            <div className="stat-tile-value" style={{ color: 'var(--accent-emerald-bright)' }}>{fmtUsd(metrics.mae)}</div>
          </div>
          <div className="stat-tile">
            <div className="stat-tile-label">R&sup2;</div>
            <div className="stat-tile-value" style={{ color: 'var(--accent-emerald-bright)' }}>{metrics.r2 != null ? metrics.r2.toFixed(4) : '--'}</div>
          </div>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'minmax(260px, 380px) 1fr', gap: '1.25rem' }}>
        <div className="card">
          <h3 style={{ fontSize: '0.95rem', fontWeight: 800, marginBottom: '0.9rem' }}>Feature Importance</h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.55rem' }}>
            {feature_importances.map((f) => (
              <div key={f.feature}>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.76rem', marginBottom: '0.2rem' }}>
                  <span style={{ color: 'var(--text-secondary)', fontFamily: 'var(--font-mono)' }}>{f.feature}</span>
                  <span style={{ color: 'var(--text-muted)' }}>{(f.importance * 100).toFixed(2)}%</span>
                </div>
                <div style={{ height: 8, background: 'var(--bg-tertiary)', borderRadius: 'var(--radius-full)', overflow: 'hidden' }}>
                  <div style={{
                    width: `${(f.importance / maxImportance) * 100}%`, height: '100%',
                    background: 'linear-gradient(90deg, var(--accent-indigo), var(--accent-emerald))',
                  }} />
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="card">
          <h3 style={{ fontSize: '0.95rem', fontWeight: 800, marginBottom: '0.3rem' }}>Actual vs. Predicted</h3>
          <p style={{ fontSize: '0.74rem', color: 'var(--text-muted)', marginBottom: '0.6rem' }}>
            {actual_vs_predicted_sample.length} real test-set points. Points near the diagonal are accurate predictions.
          </p>
          <ScatterSvg points={actual_vs_predicted_sample} />
        </div>
      </div>
    </div>
  );
}

export default HousePricesView;
