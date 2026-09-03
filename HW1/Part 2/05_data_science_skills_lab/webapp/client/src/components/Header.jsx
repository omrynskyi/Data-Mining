import React from 'react';
import { BookOpen, ShieldCheck, FileText, Layers, TrendingUp, DollarSign, Users, AlertTriangle, PhoneCall } from 'lucide-react';

const TABS = [
  { key: 'skills', label: '48 Skills Catalog', icon: Layers },
  { key: 'titanic', label: 'Titanic (Classification)', icon: Users },
  { key: 'house', label: 'House Prices (Regression)', icon: DollarSign },
  { key: 'fraud', label: 'Fraud (Imbalanced ML)', icon: AlertTriangle },
  { key: 'ecommerce', label: 'E-Commerce Analytics', icon: TrendingUp },
  { key: 'quality', label: 'Data Quality Audit', icon: ShieldCheck },
  { key: 'telco', label: 'Telco Churn (CRISP-DM)', icon: PhoneCall },
];

export const Header = ({ activeTab, setActiveTab, onOpenCrispDm, totalSkills = 48 }) => {
  return (
    <header className="header">
      <div className="brand-container">
        <div className="logo-icon">
          <BookOpen size={20} />
        </div>
        <div>
          <div className="brand-title">Data Science Skills Mastery Lab</div>
          <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
            <span style={{ display: 'inline-block', width: 6, height: 6, borderRadius: '50%', background: '#22d3ee' }}></span>
            <span>param087 Agent ML Skills • nimrodfisher Analytics Skills • real datasets only</span>
          </div>
        </div>
      </div>

      <nav className="nav-tabs">
        {TABS.map(({ key, label, icon: Icon }) => (
          <button
            key={key}
            className={`nav-tab-btn ${activeTab === key ? 'active' : ''}`}
            onClick={() => setActiveTab(key)}
            id={`tab-${key}`}
          >
            <Icon size={15} />
            <span>{label}</span>
          </button>
        ))}
      </nav>

      <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
        <button
          className="btn-secondary"
          onClick={onOpenCrispDm}
          id="btn-crisp-dm-lab"
          style={{ borderColor: 'var(--accent-indigo)', color: 'var(--accent-indigo-bright)' }}
        >
          <FileText size={14} />
          <span>CRISP-DM Report</span>
        </button>

        <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', background: 'rgba(99, 102, 241, 0.12)', padding: '0.35rem 0.75rem', borderRadius: 'var(--radius-full)', border: '1px solid var(--border-active)', fontSize: '0.74rem', color: 'var(--accent-cyan-bright)', fontWeight: 800 }}>
          <ShieldCheck size={14} />
          <span>{totalSkills} Skills Installed</span>
        </div>
      </div>
    </header>
  );
};
