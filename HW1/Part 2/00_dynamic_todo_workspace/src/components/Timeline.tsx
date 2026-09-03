'use client';

import { useMemo } from 'react';
import { CalendarClock, Check } from 'lucide-react';
import type { Todo } from '@/lib/db';
import { dayKey, daysBetween, parseTags, timeLabel } from '@/lib/format';
import EmptyState from './EmptyState';

/** Agenda grouped by day, with overdue work pulled to the top. */
export default function Timeline({ todos }: { todos: Todo[] }) {
  const days = useMemo(() => {
    const map = new Map<string, Todo[]>();
    todos
      .filter((t) => t.dueDate)
      .forEach((t) => {
        const key = dayKey(t.dueDate!);
        const list = map.get(key) ?? [];
        list.push(t);
        map.set(key, list);
      });
    return Array.from(map.entries())
      .sort(([a], [b]) => a.localeCompare(b))
      .map(([key, items]) => ({
        key,
        date: new Date(`${key}T12:00:00`),
        items: items.sort((a, b) => (a.dueDate ?? '').localeCompare(b.dueDate ?? '')),
      }));
  }, [todos]);

  if (days.length === 0) {
    return (
      <div className="panel">
        <EmptyState
          icon={CalendarClock}
          title="No scheduled work"
          body="Tasks appear here once they have a due date. Add one from the list view, or type a day name straight into the task field."
        />
      </div>
    );
  }

  const now = new Date();

  return (
    <div>
      {days.map((day) => {
        const offset = daysBetween(now, day.date);
        // A past day only reads as late while something on it is unfinished.
        const settled = day.items.every((t) => t.completed === 1);
        const tone = offset < 0 && !settled ? 'overdue' : offset === 0 ? 'today' : 'later';
        const relative =
          offset < 0
            ? `${Math.abs(offset)} days ${settled ? 'ago' : 'late'}`
            : offset === 0
              ? 'Today'
              : offset === 1
                ? 'Tomorrow'
                : `In ${offset} days`;

        return (
          <section key={day.key} className="agenda-day">
            <div className="agenda-date">
              <p className="agenda-weekday">
                {day.date.toLocaleDateString(undefined, { weekday: 'long' }).toUpperCase()}
              </p>
              <p className="agenda-daynum num">
                {day.date.toLocaleDateString(undefined, { month: 'short', day: 'numeric' })}
              </p>
              <p className="agenda-rel" data-tone={tone}>
                {relative}
              </p>
            </div>

            <ul className="task-list">
              {day.items.map((todo) => {
                const isDone = todo.completed === 1;
                return (
                  <li key={todo.id} className="task-row" data-priority={isDone ? 'none' : todo.priority}>
                    <div className="task-main">
                      <span
                        className="check"
                        aria-hidden="true"
                        style={
                          isDone
                            ? { background: 'var(--accent)', borderColor: 'var(--accent)' }
                            : undefined
                        }
                      >
                        {isDone && <Check size={13} strokeWidth={3} />}
                      </span>
                      <div className="task-body">
                        <p className="task-title" data-done={isDone}>
                          {todo.title}
                        </p>
                        <div className="task-meta">
                          {timeLabel(todo.dueDate!) && (
                            <span className="meta num">{timeLabel(todo.dueDate!)}</span>
                          )}
                          {!isDone && (
                            <span className="prio" data-level={todo.priority}>
                              <span className="prio-bar" aria-hidden="true" />
                              {todo.priority}
                            </span>
                          )}
                          <span className="meta">{todo.category}</span>
                          {parseTags(todo.tags).map((tag) => (
                            <span key={tag} className="tag">
                              #{tag}
                            </span>
                          ))}
                        </div>
                      </div>
                    </div>
                  </li>
                );
              })}
            </ul>
          </section>
        );
      })}
    </div>
  );
}
