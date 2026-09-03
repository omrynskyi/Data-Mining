'use client';

import { useState } from 'react';
import { motion, useReducedMotion } from 'framer-motion';
import { ArrowLeft, ArrowRight, Calendar, ListTree } from 'lucide-react';
import type { Todo } from '@/lib/db';
import { useTodoStore } from '@/hooks/useTodoStore';
import { dueMeta, parseTags } from '@/lib/format';
import ErrorToast from './ErrorToast';

const COLUMNS = ['To Do', 'In Progress', 'Done'] as const;
type Column = (typeof COLUMNS)[number];

function columnOf(todo: Todo): Column {
  if (todo.completed === 1) return 'Done';
  const status = todo.status as Column;
  return COLUMNS.includes(status) ? status : 'To Do';
}

/**
 * Board with pointer drag and drop plus arrow buttons, so the same move is
 * available to keyboard and touch users. The old board used a `<select>`
 * labelled "Move to X" whose displayed value was the column the card was
 * already in, which read as a status field that lied about the status.
 */
export default function KanbanBoard({ initialTodos }: { initialTodos: Todo[] }) {
  const { todos, error, dismissError, setStatus, remove } = useTodoStore(initialTodos);
  const [dragId, setDragId] = useState<number | null>(null);
  const [overColumn, setOverColumn] = useState<Column | null>(null);
  const reduceMotion = useReducedMotion();

  const move = (todo: Todo, delta: number) => {
    const index = COLUMNS.indexOf(columnOf(todo));
    const next = COLUMNS[index + delta];
    if (next) setStatus(todo.id, next);
  };

  return (
    <>
      <div className="board">
        {COLUMNS.map((column) => {
          const items = todos.filter((t) => columnOf(t) === column);
          return (
            <section
              key={column}
              className="column"
              data-over={overColumn === column && dragId !== null}
              aria-label={`${column}, ${items.length} tasks`}
              onDragOver={(e) => {
                e.preventDefault();
                setOverColumn(column);
              }}
              onDragLeave={() => setOverColumn((c) => (c === column ? null : c))}
              onDrop={(e) => {
                e.preventDefault();
                setOverColumn(null);
                if (dragId === null) return;
                const todo = todos.find((t) => t.id === dragId);
                if (todo && columnOf(todo) !== column) setStatus(dragId, column);
                setDragId(null);
              }}
            >
              <header className="column-head">
                <h2 className="column-title">{column}</h2>
                <span className="column-count num">{items.length}</span>
              </header>

              <div className="column-body">
                {items.map((todo) => {
                  const due = todo.dueDate ? dueMeta(todo.dueDate, column === 'Done') : null;
                  const subtasks = todo.subtasks ?? [];
                  const doneCount = subtasks.filter((s) => s.completed === 1).length;
                  const index = COLUMNS.indexOf(column);
                  return (
                    <motion.article
                      key={todo.id}
                      layout={reduceMotion ? false : true}
                      transition={{ duration: 0.2, ease: [0.16, 1, 0.3, 1] }}
                      className="card"
                      data-priority={column === 'Done' ? 'none' : todo.priority}
                      data-dragging={dragId === todo.id}
                      draggable
                      onDragStart={() => setDragId(todo.id)}
                      onDragEnd={() => {
                        setDragId(null);
                        setOverColumn(null);
                      }}
                    >
                      <p
                        className="card-title"
                        style={
                          column === 'Done'
                            ? { color: 'var(--text-3)', textDecoration: 'line-through' }
                            : undefined
                        }
                      >
                        {todo.title}
                      </p>

                      <div className="card-meta">
                        <span className="meta">{todo.category}</span>
                        {due && (
                          <span className={`meta ${due.warn ? 'meta-warn' : ''}`}>
                            <Calendar size={12} strokeWidth={1.75} />
                            {due.label}
                          </span>
                        )}
                        {subtasks.length > 0 && (
                          <span className="meta">
                            <ListTree size={12} strokeWidth={1.75} />
                            <span className="num">
                              {doneCount}/{subtasks.length}
                            </span>
                          </span>
                        )}
                        {parseTags(todo.tags).map((tag) => (
                          <span key={tag} className="tag">
                            #{tag}
                          </span>
                        ))}
                      </div>

                      <div
                        style={{
                          display: 'flex', alignItems: 'center', gap: '0.125rem',
                          marginTop: '0.5rem', marginLeft: '-0.25rem',
                        }}
                      >
                        <button
                          type="button"
                          className="btn-icon"
                          style={{ width: 26, height: 26 }}
                          disabled={index === 0}
                          aria-label={`Move "${todo.title}" to ${COLUMNS[index - 1] ?? ''}`}
                          onClick={() => move(todo, -1)}
                        >
                          <ArrowLeft size={14} strokeWidth={1.75} />
                        </button>
                        <button
                          type="button"
                          className="btn-icon"
                          style={{ width: 26, height: 26 }}
                          disabled={index === COLUMNS.length - 1}
                          aria-label={`Move "${todo.title}" to ${COLUMNS[index + 1] ?? ''}`}
                          onClick={() => move(todo, 1)}
                        >
                          <ArrowRight size={14} strokeWidth={1.75} />
                        </button>
                        <button
                          type="button"
                          className="btn btn-ghost btn-sm"
                          style={{ marginLeft: 'auto', color: 'var(--text-3)' }}
                          onClick={() => remove(todo.id)}
                        >
                          Delete
                        </button>
                      </div>
                    </motion.article>
                  );
                })}

                {items.length === 0 && (
                  <p className="dropzone">
                    {dragId !== null ? `Release to move here` : `Nothing in ${column}`}
                  </p>
                )}
              </div>
            </section>
          );
        })}
      </div>

      <ErrorToast message={error} onDismiss={dismissError} />
    </>
  );
}
