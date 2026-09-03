'use client';

import { useEffect, useRef, useState } from 'react';
import { AnimatePresence, motion, useReducedMotion } from 'framer-motion';
import {
  Calendar, Check, ChevronRight, ListTree, Pencil, Plus, Trash2,
} from 'lucide-react';
import type { Subtask, Todo } from '@/lib/db';
import { dueMeta, parseTags, timeLabel } from '@/lib/format';

interface TodoItemProps {
  todo: Todo;
  onToggle: (id: number, completed: number) => void;
  onDelete: (id: number) => void;
  onRename: (id: number, title: string) => void;
}

export default function TodoItem({ todo, onToggle, onDelete, onRename }: TodoItemProps) {
  const isDone = todo.completed === 1;
  const [expanded, setExpanded] = useState(false);
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(todo.title);
  const [subtasks, setSubtasks] = useState<Subtask[]>(todo.subtasks ?? []);
  const [newSubtask, setNewSubtask] = useState('');
  const editRef = useRef<HTMLInputElement>(null);
  const reduceMotion = useReducedMotion();

  const tags = parseTags(todo.tags);
  const done = subtasks.filter((s) => s.completed === 1).length;
  const total = subtasks.length;
  const progress = total === 0 ? 0 : (done / total) * 100;

  useEffect(() => {
    if (editing) editRef.current?.select();
  }, [editing]);

  const commitRename = () => {
    const next = draft.trim();
    setEditing(false);
    if (!next || next === todo.title) {
      setDraft(todo.title);
      return;
    }
    onRename(todo.id, next);
  };

  const addSubtask = async (e: React.FormEvent) => {
    e.preventDefault();
    const title = newSubtask.trim();
    if (!title) return;
    setNewSubtask('');
    try {
      const res = await fetch(`/api/todos/${todo.id}/subtasks`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title }),
      });
      if (!res.ok) throw new Error(String(res.status));
      const created: Subtask = await res.json();
      setSubtasks((current) => [...current, created]);
    } catch {
      setNewSubtask(title);
    }
  };

  const toggleSubtask = async (subtaskId: number, completed: number) => {
    const snapshot = subtasks;
    setSubtasks((current) =>
      current.map((s) => (s.id === subtaskId ? { ...s, completed } : s))
    );
    try {
      const res = await fetch(`/api/subtasks/${subtaskId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ completed }),
      });
      if (!res.ok) throw new Error(String(res.status));
    } catch {
      setSubtasks(snapshot);
    }
  };

  const deleteSubtask = async (subtaskId: number) => {
    const snapshot = subtasks;
    setSubtasks((current) => current.filter((s) => s.id !== subtaskId));
    try {
      const res = await fetch(`/api/subtasks/${subtaskId}`, { method: 'DELETE' });
      if (!res.ok) throw new Error(String(res.status));
    } catch {
      setSubtasks(snapshot);
    }
  };

  return (
    <motion.li
      layout={reduceMotion ? false : 'position'}
      exit={reduceMotion ? undefined : { opacity: 0, height: 0, marginTop: 0 }}
      transition={{ duration: 0.2, ease: [0.16, 1, 0.3, 1] }}
      className="task-row"
      data-priority={isDone ? 'none' : todo.priority}
    >
      <div className="task-main">
        <button
          type="button"
          role="checkbox"
          aria-checked={isDone}
          aria-label={isDone ? `Mark "${todo.title}" as not done` : `Mark "${todo.title}" as done`}
          className="check"
          onClick={() => onToggle(todo.id, isDone ? 0 : 1)}
        >
          {isDone && <Check size={13} strokeWidth={3} />}
        </button>

        <div className="task-body">
          {editing ? (
            <input
              ref={editRef}
              className="input-bare"
              style={{ fontSize: '0.9375rem', fontWeight: 500 }}
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              onBlur={commitRename}
              onKeyDown={(e) => {
                if (e.key === 'Enter') commitRename();
                if (e.key === 'Escape') {
                  setDraft(todo.title);
                  setEditing(false);
                }
              }}
              aria-label="Task name"
            />
          ) : (
            <p
              className="task-title"
              data-done={isDone}
              onDoubleClick={() => setEditing(true)}
              title="Double-click to rename"
            >
              {todo.title}
            </p>
          )}

          <div className="task-meta">
            {!isDone && (
              <span className="prio" data-level={todo.priority}>
                <span className="prio-bar" aria-hidden="true" />
                {todo.priority}
              </span>
            )}
            <span className="meta">{todo.category}</span>

            {todo.dueDate && (
              <span
                className={`meta ${dueMeta(todo.dueDate, isDone).warn ? 'meta-warn' : ''}`}
                title={new Date(todo.dueDate).toLocaleString()}
              >
                <Calendar size={13} strokeWidth={1.75} />
                {dueMeta(todo.dueDate, isDone).label}
                {timeLabel(todo.dueDate) && (
                  <span className="num" style={{ opacity: 0.75 }}>
                    {timeLabel(todo.dueDate)}
                  </span>
                )}
              </span>
            )}

            {total > 0 && (
              <span className="meta">
                <ListTree size={13} strokeWidth={1.75} />
                <span className="num">
                  {done}/{total}
                </span>
              </span>
            )}

            {tags.map((tag) => (
              <span key={tag} className="tag">
                #{tag}
              </span>
            ))}
          </div>
        </div>

        <div className="task-actions">
          <button
            type="button"
            className="btn-icon"
            aria-label={`Rename "${todo.title}"`}
            onClick={() => setEditing(true)}
          >
            <Pencil size={15} strokeWidth={1.75} />
          </button>
          <button
            type="button"
            className="btn-icon is-danger"
            aria-label={`Delete "${todo.title}"`}
            onClick={() => onDelete(todo.id)}
          >
            <Trash2 size={15} strokeWidth={1.75} />
          </button>
          <button
            type="button"
            className="btn-icon"
            aria-expanded={expanded}
            aria-label={expanded ? 'Hide subtasks' : 'Show subtasks'}
            onClick={() => setExpanded((v) => !v)}
          >
            <motion.span
              animate={{ rotate: expanded ? 90 : 0 }}
              transition={{ duration: 0.15 }}
              style={{ display: 'inline-flex' }}
            >
              <ChevronRight size={16} strokeWidth={1.75} />
            </motion.span>
          </button>
        </div>
      </div>

      {total > 0 && !expanded && (
        <div className="progress" role="presentation">
          <motion.div
            className="progress-fill"
            initial={false}
            animate={{ width: `${progress}%` }}
            transition={{ duration: 0.3, ease: [0.16, 1, 0.3, 1] }}
          />
        </div>
      )}

      <AnimatePresence initial={false}>
        {expanded && (
          <motion.div
            initial={reduceMotion ? false : { height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={reduceMotion ? undefined : { height: 0, opacity: 0 }}
            transition={{ duration: 0.2, ease: [0.16, 1, 0.3, 1] }}
            style={{ overflow: 'hidden' }}
          >
            <ul className="subtasks">
              {subtasks.map((subtask) => (
                <li key={subtask.id} className="subtask-row">
                  <button
                    type="button"
                    role="checkbox"
                    aria-checked={subtask.completed === 1}
                    aria-label={subtask.title}
                    className="check"
                    style={{ width: 16, height: 16 }}
                    onClick={() => toggleSubtask(subtask.id, subtask.completed ? 0 : 1)}
                  >
                    {subtask.completed === 1 && <Check size={10} strokeWidth={3} />}
                  </button>
                  <span className="subtask-title" data-done={subtask.completed === 1}>
                    {subtask.title}
                  </span>
                  <button
                    type="button"
                    className="btn-icon is-danger"
                    style={{ width: 26, height: 26 }}
                    aria-label={`Delete subtask "${subtask.title}"`}
                    onClick={() => deleteSubtask(subtask.id)}
                  >
                    <Trash2 size={13} strokeWidth={1.75} />
                  </button>
                </li>
              ))}

              <li className="subtask-row">
                <Plus size={14} strokeWidth={1.75} style={{ color: 'var(--text-3)', flexShrink: 0 }} />
                <form onSubmit={addSubtask} style={{ flex: 1 }}>
                  <input
                    className="input-bare"
                    style={{ fontSize: '0.875rem' }}
                    placeholder="Add a subtask"
                    value={newSubtask}
                    onChange={(e) => setNewSubtask(e.target.value)}
                    aria-label={`Add a subtask to "${todo.title}"`}
                  />
                </form>
              </li>

              {total === 0 && (
                <li className="field-help" style={{ paddingTop: '0.25rem' }}>
                  Break this task into steps to track partial progress.
                </li>
              )}
            </ul>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.li>
  );
}
