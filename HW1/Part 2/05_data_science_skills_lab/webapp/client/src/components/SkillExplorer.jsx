import React, { useMemo, useState } from 'react';
import { Search, Play, ArrowRight, X, AlertTriangle, Sigma } from 'lucide-react';
import { api } from '../utils/api';

function SkillModal({ skill, result, loading, error, onClose }) {
  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-card" style={{ maxWidth: '780px' }} onClick={(e) => e.stopPropagation()}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '1.1rem 1.4rem', borderBottom: '1px solid var(--border-subtle)' }}>
          <div>
            <div style={{ fontSize: '0.7rem', color: 'var(--accent-cyan-bright)', fontWeight: 800, textTransform: 'uppercase' }}>
              Live Execute Result
            </div>
            <h3 style={{ fontSize: '1.05rem', fontWeight: 800 }}>{skill.name}</h3>
          </div>
          <button onClick={onClose} style={{ background: 'transparent', border: 'none', color: 'var(--text-muted)', cursor: 'pointer' }}>
            <X size={20} />
          </button>
        </div>
        <div style={{ padding: '1.4rem', maxHeight: '65vh', overflowY: 'auto' }}>
          {loading && (
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', color: 'var(--text-muted)' }}>
              <span className="spinner" /> Calling POST /api/skills/execute...
            </div>
          )}
          {error && (
            <div style={{ color: 'var(--accent-rose)', fontSize: '0.85rem' }}>{error}</div>
          )}
          {!loading && !error && result && (
            <pre style={{
              background: 'var(--bg-tertiary)', padding: '1rem', borderRadius: 'var(--radius-md)',
              fontFamily: 'var(--font-mono)', fontSize: '0.75rem', color: 'var(--text-secondary)',
              whiteSpace: 'pre-wrap', wordBreak: 'break-word', overflowX: 'auto',
            }}>
              {JSON.stringify(result, null, 2)}
            </pre>
          )}
        </div>
      </div>
    </div>
  );
}

export function SkillExplorer({ skills = [], onNavigateToBenchmark }) {
  const [query, setQuery] = useState('');
  const [activeCategory, setActiveCategory] = useState('All');
  const [modalSkill, setModalSkill] = useState(null);
  const [modalResult, setModalResult] = useState(null);
  const [modalLoading, setModalLoading] = useState(false);
  const [modalError, setModalError] = useState(null);

  const categories = useMemo(() => {
    const set = new Set(skills.map((s) => s.category).filter(Boolean));
    return ['All', ...Array.from(set).sort()];
  }, [skills]);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    return skills.filter((s) => {
      const matchesCategory = activeCategory === 'All' || s.category === activeCategory;
      if (!matchesCategory) return false;
      if (!q) return true;
      return (
        s.name?.toLowerCase().includes(q) ||
        s.purpose?.toLowerCase().includes(q) ||
        s.id?.toLowerCase().includes(q) ||
        s.origin?.toLowerCase().includes(q)
      );
    });
  }, [skills, query, activeCategory]);

  async function handleExecute(skill) {
    setModalSkill(skill);
    setModalResult(null);
    setModalError(null);
    setModalLoading(true);
    try {
      const res = await api.executeSkill(skill.id);
      setModalResult(res);
    } catch (err) {
      setModalError(err.message || 'Failed to execute skill.');
    } finally {
      setModalLoading(false);
    }
  }

  return (
    <div>
      <div className="card" style={{ marginBottom: '1.25rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '0.75rem', marginBottom: '1rem' }}>
          <div>
            <h2 style={{ fontSize: '1.15rem', fontWeight: 800 }}>48 Skills Catalog</h2>
            <p style={{ fontSize: '0.82rem', color: 'var(--text-muted)', marginTop: '0.2rem' }}>
              param087 Agent ML Skills + nimrodfisher Analytics Skills, each executable live against a real dataset.
            </p>
          </div>
          <span className="badge-real-data">Real skill definitions</span>
        </div>

        <div style={{ position: 'relative', marginBottom: '0.9rem' }}>
          <Search size={16} style={{ position: 'absolute', left: '0.85rem', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search skills by name, purpose, or origin..."
            style={{
              width: '100%', padding: '0.65rem 0.9rem 0.65rem 2.4rem', borderRadius: 'var(--radius-md)',
              border: '1px solid var(--border-subtle)', background: 'var(--bg-tertiary)', color: 'var(--text-primary)',
              fontSize: '0.85rem', fontFamily: 'var(--font-sans)',
            }}
          />
        </div>

        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.4rem' }}>
          {categories.map((cat) => (
            <button
              key={cat}
              onClick={() => setActiveCategory(cat)}
              className="btn-secondary"
              style={activeCategory === cat ? {
                background: 'linear-gradient(135deg, rgba(99, 102, 241, 0.25), rgba(6, 182, 212, 0.25))',
                color: 'var(--accent-cyan-bright)', border: '1px solid var(--border-active)',
              } : undefined}
            >
              {cat}
            </button>
          ))}
        </div>
      </div>

      <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)', marginBottom: '0.75rem' }}>
        Showing {filtered.length} of {skills.length} skills
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(340px, 1fr))', gap: '1rem' }}>
        {filtered.map((skill) => (
          <div key={skill.id} className="card" style={{ display: 'flex', flexDirection: 'column', gap: '0.6rem' }}>
            <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: '0.5rem' }}>
              <span style={{
                fontSize: '0.65rem', fontWeight: 800, textTransform: 'uppercase', color: 'var(--accent-indigo-bright)',
                background: 'rgba(99, 102, 241, 0.12)', padding: '0.15rem 0.5rem', borderRadius: 'var(--radius-full)',
              }}>
                {skill.category}
              </span>
            </div>
            <div style={{ fontFamily: 'var(--font-mono)', fontSize: '0.68rem', color: 'var(--text-muted)' }}>
              {skill.origin}
            </div>
            <h3 style={{ fontSize: '1rem', fontWeight: 800 }}>{skill.name}</h3>
            <p style={{ fontSize: '0.82rem', color: 'var(--text-secondary)', lineHeight: 1.5 }}>{skill.purpose}</p>

            {skill.math_intuition ? (
              <div style={{
                background: 'var(--bg-tertiary)', border: '1px solid var(--border-cyan)', borderRadius: 'var(--radius-md)',
                padding: '0.65rem 0.75rem', display: 'flex', gap: '0.5rem', alignItems: 'flex-start',
              }}>
                <Sigma size={14} style={{ color: 'var(--accent-cyan-bright)', flexShrink: 0, marginTop: '0.15rem' }} />
                <div>
                  <div style={{ fontSize: '0.62rem', fontWeight: 800, textTransform: 'uppercase', color: 'var(--accent-cyan-bright)', marginBottom: '0.2rem' }}>
                    Statistical & Mathematical Intuition
                  </div>
                  <div style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', lineHeight: 1.45 }}>{skill.math_intuition}</div>
                </div>
              </div>
            ) : null}

            {Array.isArray(skill.pitfalls) && skill.pitfalls.length > 0 && (
              <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', fontSize: '0.68rem', fontWeight: 800, textTransform: 'uppercase', color: 'var(--accent-amber)', marginBottom: '0.3rem' }}>
                  <AlertTriangle size={12} /> Pitfalls
                </div>
                <ul style={{ paddingLeft: '1.1rem', display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
                  {skill.pitfalls.map((p, i) => (
                    <li key={i} style={{ fontSize: '0.76rem', color: 'var(--text-muted)', lineHeight: 1.4 }}>{p}</li>
                  ))}
                </ul>
              </div>
            )}

            <div style={{ display: 'flex', gap: '0.5rem', marginTop: 'auto', paddingTop: '0.5rem' }}>
              <button className="btn-primary" onClick={() => handleExecute(skill)} style={{ flex: 1, justifyContent: 'center' }}>
                <Play size={14} /> Live Execute Skill
              </button>
              {skill.benchmark_link && onNavigateToBenchmark && (
                <button
                  className="btn-secondary"
                  onClick={() => onNavigateToBenchmark(skill.benchmark_link)}
                  title={`View the ${skill.benchmark_link} benchmark`}
                >
                  <ArrowRight size={14} />
                </button>
              )}
            </div>
          </div>
        ))}
      </div>

      {modalSkill && (
        <SkillModal
          skill={modalSkill}
          result={modalResult}
          loading={modalLoading}
          error={modalError}
          onClose={() => setModalSkill(null)}
        />
      )}
    </div>
  );
}

export default SkillExplorer;
