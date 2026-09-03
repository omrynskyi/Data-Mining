'use client';

import { useMemo, useState } from 'react';
import { AnimatePresence } from 'framer-motion';
import { CheckCircle2, ListTodo, Search, SearchX } from 'lucide-react';
import type { Todo } from '@/lib/db';
import { useTodoStore } from '@/hooks/useTodoStore';
import { daysBetween, parseTags, plural } from '@/lib/format';
import TodoItem from './TodoItem';
import TodoInput from './TodoInput';
import CustomDropdown from './CustomDropdown';
import EmptyState from './EmptyState';
import ErrorToast from './ErrorToast';

const SORTS = ['Due date', 'Priority', 'Recently added'] as const;
const PRIORITY_RANK: Record<string, number> = { High: 0, Medium: 1, Low: 2 };

/** Buckets used when sorting by due date, in display order. */
const BUCKETS = ['Overdue', 'Today', 'Tomorrow', 'This week', 'Later', 'No due date'] as const;

function bucketOf(todo: Todo): (typeof BUCKETS)[number] {
  if (!todo.dueDate) return 'No due date';
  const diff = daysBetween(new Date(), new Date(todo.dueDate));
  if (diff < 0) return 'Overdue';
  if (diff === 0) return 'Today';
  if (diff === 1) return 'Tomorrow';
  if (diff <= 7) return 'This week';
  return 'Later';
}

export default function TodoList({ initialTodos }: { initialTodos: Todo[] }) {
  const { todos, error, dismissError, add, toggle, rename, remove } = useTodoStore(initialTodos);
  const [query, setQuery] = useState('');
  const [filter, setFilter] = useState('Active');
  const [sort, setSort] = useState<(typeof SORTS)[number]>('Due date');

  const tags = useMemo(() => {
    const set = new Set<string>();
    todos.forEach((t) => parseTags(t.tags).forEach((tag) => set.add(tag)));
    return Array.from(set).sort();
  }, [todos]);

  const counts = useMemo(
    () => ({
      All: todos.length,
      Active: todos.filter((t) => t.completed === 0).length,
      Done: todos.filter((t) => t.completed === 1).length,
    }),
    [todos]
  );

  const visible = useMemo(() => {
    const needle = query.trim().toLowerCase();

    const matchesFilter = (t: Todo) => {
      if (filter === 'All') return true;
      if (filter === 'Active') return t.completed === 0;
      if (filter === 'Done') return t.completed === 1;
      if (filter.startsWith('#')) return parseTags(t.tags).includes(filter.slice(1));
      return t.category === filter;
    };

    const matchesQuery = (t: Todo) => {
      if (!needle) return true;
      return (
        t.title.toLowerCase().includes(needle) ||
        t.category.toLowerCase().includes(needle) ||
        parseTags(t.tags).some((tag) => tag.toLowerCase().includes(needle))
      );
    };

    const result = todos.filter((t) => matchesFilter(t) && matchesQuery(t));

    return result.sort((a, b) => {
      // Finished work always sinks, whatever the sort.
      if (a.completed !== b.completed) return a.completed - b.completed;
      if (sort === 'Priority') {
        const delta = PRIORITY_RANK[a.priority] - PRIORITY_RANK[b.priority];
        if (delta !== 0) return delta;
      }
      if (sort === 'Due date') {
        if (a.dueDate && b.dueDate) return a.dueDate.localeCompare(b.dueDate);
        if (a.dueDate) return -1;
        if (b.dueDate) return 1;
      }
      return b.createdAt.localeCompare(a.createdAt);
    });
  }, [todos, filter, query, sort]);

  // Only the due-date sort groups; the others read better as one flat list.
  const groups = useMemo(() => {
    if (sort !== 'Due date') return [{ label: null as string | null, items: visible }];
    const open = visible.filter((t) => t.completed === 0);
    const closed = visible.filter((t) => t.completed === 1);
    const bucketed: { label: string | null; items: Todo[] }[] = BUCKETS.map((label) => ({
      label: label as string | null,
      items: open.filter((t) => bucketOf(t) === label),
    })).filter((g) => g.items.length > 0);
    if (closed.length > 0) bucketed.push({ label: 'Completed', items: closed });
    return bucketed;
  }, [visible, sort]);

  const clearCompleted = () => {
    todos.filter((t) => t.completed === 1).forEach((t) => remove(t.id));
  };

  const filterChips = ['Active', 'All', 'Done', 'Work', 'Personal', 'Urgent', ...tags.map((t) => `#${t}`)];

  return (
    <>
      <TodoInput onAdd={add} />

      <div
        style={{
          display: 'flex', alignItems: 'flex-end', gap: '0.75rem',
          flexWrap: 'wrap', marginBottom: '1rem',
        }}
      >
        <div className="field" style={{ flex: '1 1 260px', position: 'relative' }}>
          <label className="sr-only" htmlFor="task-search">
            Search tasks
          </label>
          <Search
            size={15}
            strokeWidth={1.75}
            aria-hidden="true"
            style={{
              position: 'absolute', left: '0.7rem', top: '50%',
              transform: 'translateY(-50%)', color: 'var(--text-3)', pointerEvents: 'none',
            }}
          />
          <input
            id="task-search"
            type="search"
            className="input"
            style={{ paddingLeft: '2rem' }}
            placeholder="Search tasks and tags"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
        </div>

        <div style={{ flex: '0 1 172px', minWidth: 140 }}>
          <CustomDropdown
            label="Sort by"
            options={SORTS}
            value={sort}
            onChange={(v) => setSort(v as (typeof SORTS)[number])}
          />
        </div>

        {counts.Done > 0 && (
          <button type="button" className="btn btn-secondary" onClick={clearCompleted}>
            Clear {plural(counts.Done, 'completed task')}
          </button>
        )}
      </div>

      <div
        role="group"
        aria-label="Filter tasks"
        style={{
          display: 'flex', gap: '0.375rem', flexWrap: 'wrap',
          alignItems: 'center', marginBottom: '1.25rem',
        }}
      >
        {filterChips.map((chip) => (
          <button
            key={chip}
            type="button"
            className="chip"
            aria-pressed={filter === chip}
            onClick={() => setFilter(chip)}
          >
            {chip}
            {chip in counts && (
              <span className="chip-count num">{counts[chip as keyof typeof counts]}</span>
            )}
          </button>
        ))}
      </div>

      {todos.length === 0 ? (
        <div className="panel">
          <EmptyState
            icon={ListTodo}
            title="Nothing here yet"
            body="Add your first task above. Press N from anywhere to jump to the field."
          />
        </div>
      ) : visible.length === 0 ? (
        <div className="panel">
          <EmptyState
            icon={query ? SearchX : CheckCircle2}
            title={query ? 'No matches' : 'All clear'}
            body={
              query
                ? `Nothing matches "${query.trim()}". Try a different word or clear the filter.`
                : 'Every task in this filter is done. Switch to All to see the archive.'
            }
            action={
              <button
                type="button"
                className="btn btn-secondary btn-sm"
                style={{ marginTop: '0.5rem' }}
                onClick={() => {
                  setQuery('');
                  setFilter('All');
                }}
              >
                Reset filters
              </button>
            }
          />
        </div>
      ) : (
        groups.map((group) => (
          <section className="task-group" key={group.label ?? 'all'}>
            {group.label && (
              <header className="task-group-head">
                <h2 className="task-group-title">{group.label}</h2>
                <span className="task-group-count num">{group.items.length}</span>
              </header>
            )}
            <ul className="task-list">
              <AnimatePresence initial={false}>
                {group.items.map((todo) => (
                  <TodoItem
                    key={todo.id}
                    todo={todo}
                    onToggle={toggle}
                    onDelete={remove}
                    onRename={rename}
                  />
                ))}
              </AnimatePresence>
            </ul>
          </section>
        ))
      )}

      <ErrorToast message={error} onDismiss={dismissError} />
    </>
  );
}
