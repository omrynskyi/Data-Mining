'use client';

import { useMemo } from 'react';
import { CheckCircle2, Flame, Target, Timer } from 'lucide-react';
import type { Todo } from '@/lib/db';
import { dayKey, plural } from '@/lib/format';

const HEATMAP_DAYS = 30;

export default function AnalyticsDashboard({ todos }: { todos: Todo[] }) {
  const stats = useMemo(() => {
    const completed = todos.filter((t) => t.completed === 1 && t.completedAt);

    const byDay = new Map<string, number>();
    completed.forEach((t) => {
      const key = dayKey(t.completedAt!);
      byDay.set(key, (byDay.get(key) ?? 0) + 1);
    });

    // Walk back from today; today being empty does not break a streak yet.
    let streak = 0;
    const cursor = new Date();
    for (let i = 0; i < 365; i++) {
      const key = dayKey(cursor);
      if (byDay.has(key)) streak++;
      else if (i !== 0) break;
      cursor.setDate(cursor.getDate() - 1);
    }

    const days = Array.from({ length: HEATMAP_DAYS }, (_, i) => {
      const d = new Date();
      d.setDate(d.getDate() - (HEATMAP_DAYS - 1 - i));
      const key = dayKey(d);
      return { key, date: d, count: byDay.get(key) ?? 0 };
    });

    const byCategory = new Map<string, { total: number; done: number }>();
    todos.forEach((t) => {
      const entry = byCategory.get(t.category) ?? { total: 0, done: 0 };
      entry.total += 1;
      if (t.completed === 1) entry.done += 1;
      byCategory.set(t.category, entry);
    });

    const last7 = days.slice(-7).reduce((sum, d) => sum + d.count, 0);

    return {
      completedCount: completed.length,
      openCount: todos.filter((t) => t.completed === 0).length,
      rate: todos.length === 0 ? 0 : Math.round((completed.length / todos.length) * 100),
      streak,
      days,
      last7,
      categories: Array.from(byCategory.entries())
        .map(([name, v]) => ({ name, ...v }))
        .sort((a, b) => b.total - a.total),
    };
  }, [todos]);

  const busiest = Math.max(1, ...stats.days.map((d) => d.count));
  const level = (count: number) => {
    if (count === 0) return '0';
    if (count / busiest <= 0.34) return '1';
    if (count / busiest <= 0.67) return '2';
    return '3';
  };

  const cards = [
    {
      icon: Flame,
      label: 'Current streak',
      value: stats.streak,
      note:
        stats.streak === 0
          ? 'Finish a task today to start one'
          : 'Consecutive days finishing a task',
    },
    {
      icon: CheckCircle2,
      label: 'Completed',
      value: stats.completedCount,
      note: `${plural(stats.last7, 'task')} in the last 7 days`,
    },
    {
      icon: Timer,
      label: 'Still open',
      value: stats.openCount,
      note: stats.openCount === 0 ? 'Inbox is clear' : 'Across every view',
    },
    {
      icon: Target,
      label: 'Completion rate',
      value: `${stats.rate}%`,
      note: `${stats.completedCount} of ${todos.length} tasks`,
    },
  ];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
      <div className="stat-grid">
        {cards.map((card) => (
          <div key={card.label} className="stat">
            <p className="stat-label">
              <card.icon size={14} strokeWidth={1.75} />
              {card.label}
            </p>
            <p className="stat-value num">{card.value}</p>
            <p className="stat-note">{card.note}</p>
          </div>
        ))}
      </div>

      <section className="panel">
        <header className="panel-head">
          <h2 className="panel-title">Completions, last 30 days</h2>
          <span className="field-help num">{stats.completedCount} total</span>
        </header>
        <div className="panel-pad">
          <div className="heatmap">
            {stats.days.map((day) => (
              <span
                key={day.key}
                className="heat-cell"
                data-level={level(day.count)}
                title={`${day.date.toLocaleDateString(undefined, {
                  month: 'short',
                  day: 'numeric',
                })}: ${plural(day.count, 'task')}`}
              />
            ))}
          </div>
          <p className="heat-legend">
            Quieter
            <span className="heat-cell" data-level="0" />
            <span className="heat-cell" data-level="1" />
            <span className="heat-cell" data-level="2" />
            <span className="heat-cell" data-level="3" />
            Busier
          </p>
        </div>
      </section>

      <section className="panel">
        <header className="panel-head">
          <h2 className="panel-title">Progress by category</h2>
        </header>
        <div className="panel-pad">
          {stats.categories.length === 0 ? (
            <p className="field-help">No tasks recorded yet.</p>
          ) : (
            stats.categories.map((cat) => {
              const pct = cat.total === 0 ? 0 : Math.round((cat.done / cat.total) * 100);
              return (
                <div className="bar-row" key={cat.name}>
                  <span style={{ fontSize: '0.875rem' }}>{cat.name}</span>
                  <span className="bar-track">
                    <span className="bar-fill" style={{ display: 'block', width: `${pct}%` }} />
                  </span>
                  <span className="num" style={{ fontSize: '0.8125rem', color: 'var(--text-2)', textAlign: 'right' }}>
                    {pct}%
                  </span>
                </div>
              );
            })
          )}
        </div>
      </section>
    </div>
  );
}
