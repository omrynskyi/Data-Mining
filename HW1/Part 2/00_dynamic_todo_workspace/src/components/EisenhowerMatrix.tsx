'use client';

import { useMemo } from 'react';
import { Inbox } from 'lucide-react';
import type { Todo } from '@/lib/db';
import { dueLabel, dueTone, daysBetween } from '@/lib/format';
import EmptyState from './EmptyState';

interface Quadrant {
  id: string;
  title: string;
  hint: string;
  items: Todo[];
}

/**
 * Urgency is derived from the due date, importance from priority. Keeping the
 * two axes independent is the whole point of the matrix; the previous version
 * used priority for both, so the bottom row could never fill.
 */
export default function EisenhowerMatrix({ todos }: { todos: Todo[] }) {
  const quadrants = useMemo<Quadrant[]>(() => {
    const now = new Date();
    const isUrgent = (t: Todo) => {
      if (!t.dueDate) return false;
      return daysBetween(now, new Date(t.dueDate)) <= 2;
    };
    const isImportant = (t: Todo) => t.priority === 'High' || t.priority === 'Medium';

    return [
      {
        id: 'do',
        title: 'Do now',
        hint: 'Urgent and important',
        items: todos.filter((t) => isUrgent(t) && isImportant(t)),
      },
      {
        id: 'schedule',
        title: 'Schedule',
        hint: 'Important, not urgent',
        items: todos.filter((t) => !isUrgent(t) && isImportant(t)),
      },
      {
        id: 'delegate',
        title: 'Delegate',
        hint: 'Urgent, not important',
        items: todos.filter((t) => isUrgent(t) && !isImportant(t)),
      },
      {
        id: 'drop',
        title: 'Drop',
        hint: 'Neither urgent nor important',
        items: todos.filter((t) => !isUrgent(t) && !isImportant(t)),
      },
    ];
  }, [todos]);

  if (todos.length === 0) {
    return (
      <div className="panel">
        <EmptyState
          icon={Inbox}
          title="No open tasks"
          body="The matrix sorts unfinished work by urgency and importance. Add a task to see it placed."
        />
      </div>
    );
  }

  return (
    <div className="matrix">
      <span aria-hidden="true" />
      <div className="matrix-axis-x" aria-hidden="true">
        <span>Urgent</span>
        <span>Not urgent</span>
      </div>

      <div className="matrix-axis-y" aria-hidden="true">
        <span>Important</span>
        <span>Not important</span>
      </div>

      {quadrants.map((quad) => (
        <section key={quad.id} className="quad" aria-label={`${quad.title}, ${quad.hint}`}>
          <header className="quad-head">
            <div style={{ display: 'flex', alignItems: 'baseline', justifyContent: 'space-between', gap: '0.5rem' }}>
              <h2 className="quad-title">{quad.title}</h2>
              <span className="task-group-count num">{quad.items.length}</span>
            </div>
            <p className="quad-hint">{quad.hint}</p>
          </header>

          <div className="quad-body">
            {quad.items.map((todo) => (
              <article key={todo.id} className="card" data-priority={todo.priority} style={{ cursor: 'default' }}>
                <p className="card-title">{todo.title}</p>
                <div className="card-meta">
                  <span className="meta">{todo.category}</span>
                  {todo.dueDate && (
                    <span className={`meta ${dueTone(todo.dueDate) === 'overdue' ? 'meta-warn' : ''}`}>
                      {dueLabel(todo.dueDate)}
                    </span>
                  )}
                </div>
              </article>
            ))}

            {quad.items.length === 0 && (
              <p className="dropzone" style={{ border: 'none', color: 'var(--text-3)' }}>
                Nothing in this quadrant
              </p>
            )}
          </div>
        </section>
      ))}

    </div>
  );
}
