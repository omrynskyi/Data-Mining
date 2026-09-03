import React from 'react';
import { X, FileText } from 'lucide-react';

const PHASES = [
  {
    color: 'var(--accent-cyan-bright)',
    title: 'Phase 1: Business Understanding',
    body: (
      <>
        A telecom subscription business losing 26.5% of customers and 30.5% of MRR to voluntary
        churn. Real business metrics computed from the raw data: MRR $456,116.60/mo, ARPU
        $64.76, revenue at risk $139,131/mo realized + $136,447/mo forward-looking. The
        hazard-based vs. tenure-based LTV figures disagreed by 3.5x -- resolved in Phase 5 as a
        survivorship-bias artifact, not left unqualified.
      </>
    ),
  },
  {
    color: 'var(--accent-indigo-bright)',
    title: 'Phase 2: Data Understanding',
    body: (
      <>
        Profiled all 21 columns of 7,043 real Telco customers (Kaggle{' '}
        <code>blastchar/telco-customer-churn</code>, SHA-256 pinned). Verified{' '}
        <code>TotalCharges &asymp; tenure &times; MonthlyCharges</code> (r=0.9996) is redundancy,
        not target leakage -- no feature exceeds 0.95 correlation with churn. Strongest real
        driver: Contract type (Cramer's V=0.41). Two plausible hypotheses ruled out: gender and
        phone service have no measurable association with churn.
      </>
    ),
  },
  {
    color: 'var(--accent-emerald-bright)',
    title: 'Phase 3: Data Preparation',
    body: (
      <>
        Built a leakage-free <code>sklearn Pipeline</code> with a custom{' '}
        <code>FeatureEngineer</code> transformer (cleaning + 9 engineered features run inside
        fit/transform, never fit on data it's later scored against). Proved the leakage-safety
        empirically: proper CV-refit vs. naive fit-once ROC-AUC differed by 0.00002, while the
        same mechanism applied to out-of-fold target encoding manufactured +0.030 AUC of pure
        noise on a shuffled target -- shown side by side, not just asserted.
      </>
    ),
  },
  {
    color: 'var(--accent-amber)',
    title: 'Phase 4: Modeling',
    body: (
      <>
        Compared 7 real, MLflow-tracked runs: baseline/balanced/SMOTE-in-CV logistic regression,
        Optuna-tuned logistic regression and XGBoost, a PyTorch MLP, and the final calibrated
        model. Demonstrated the SMOTE-before-split leakage trap on this data explicitly (inflated
        vs. honest CV score), not just described it.
      </>
    ),
  },
  {
    color: 'var(--accent-rose)',
    title: 'Phase 5: Evaluation',
    body: (
      <>
        Final model: <code>CalibratedClassifierCV</code> wrapping a tuned XGBoost pipeline.
        Held-out test set (n=1,409): ROC-AUC 0.8482, PR-AUC 0.6681 -- in the honest range for
        this dataset (a score above ~0.90 here would itself be a leakage red flag, verified it
        isn't). Threshold 0.2856 chosen for a real capacity-bounded retention campaign: 705
        customers contacted, 46.5% precision, ~$43K net expected value per cycle.
      </>
    ),
  },
  {
    color: 'var(--accent-cyan-bright)',
    title: 'Phase 6: Deployment',
    body: (
      <>
        Real FastAPI serving layer, load-tested at p50=50ms over 240 live requests with 0
        errors. A real bug was found and fixed in the hand-off contract along the way: the
        pipeline silently required pre-coerced numeric <code>TotalCharges</code>, not the raw
        string column -- caught by building the live predict endpoint, not left latent. This
        webapp's "Telco Churn" tab and its live predict widget call that same serving layer.
      </>
    ),
  },
];

export const CrispDmReportModal = ({ isOpen, onClose }) => {
  if (!isOpen) return null;

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-card" style={{ maxWidth: '840px' }} onClick={(e) => e.stopPropagation()}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '1.25rem 1.5rem', borderBottom: '1px solid var(--border-subtle)', background: 'linear-gradient(135deg, rgba(99, 102, 241, 0.12), rgba(6, 182, 212, 0.12))' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
            <FileText size={20} style={{ color: 'var(--accent-indigo-bright)' }} />
            <div>
              <span style={{ fontSize: '0.7rem', color: 'var(--accent-cyan-bright)', fontWeight: 800, textTransform: 'uppercase' }}>
                Telco Customer Churn -- 48 Skills, One Real Dataset
              </span>
              <h2 style={{ fontSize: '1.2rem', fontWeight: 800, color: '#fff' }}>CRISP-DM Report</h2>
            </div>
          </div>
          <button onClick={onClose} style={{ background: 'transparent', border: 'none', color: 'var(--text-muted)', cursor: 'pointer' }}>
            <X size={20} />
          </button>
        </div>

        <div style={{ padding: '1.5rem', maxHeight: '72vh', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '1.25rem', fontSize: '0.82rem', color: 'var(--text-secondary)', lineHeight: 1.6 }}>
          {PHASES.map((p) => (
            <div key={p.title} style={{ background: 'var(--bg-tertiary)', padding: '1rem', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-subtle)' }}>
              <h3 style={{ color: p.color, fontWeight: 800, fontSize: '0.95rem', marginBottom: '0.4rem' }}>{p.title}</h3>
              <p>{p.body}</p>
            </div>
          ))}
          <p style={{ fontSize: '0.72rem', color: 'var(--text-muted)', fontStyle: 'italic' }}>
            Full per-skill write-ups for all 48 demonstrations live in{' '}
            <code>crisp_dm/01_business_understanding/</code> through{' '}
            <code>crisp_dm/06_deployment/</code> in the project repository, each traceable to
            executed code -- this modal is a summary, not the source of record.
          </p>
        </div>

        <div style={{ display: 'flex', justifyContent: 'flex-end', padding: '1rem 1.5rem', borderTop: '1px solid var(--border-subtle)', background: 'var(--bg-tertiary)' }}>
          <button className="btn-primary" onClick={onClose}>Close Report</button>
        </div>
      </div>
    </div>
  );
};
