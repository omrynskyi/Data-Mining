'use client';

import { useEffect, useMemo, useRef, useState } from 'react';
import { AnimatePresence, motion, useReducedMotion } from 'framer-motion';
import { AlertCircle, Loader2, Plus } from 'lucide-react';
import CustomDropdown from './CustomDropdown';
import DateTimePicker from './DateTimePicker';
import { CATEGORIES, PRIORITIES, parseQuickAdd } from '@/lib/quickAdd';
import type { Category, Priority } from '@/lib/quickAdd';
import type { Todo } from '@/lib/db';

interface TodoInputProps {
  onAdd: (todo: Todo) => void;
}

export default function TodoInput({ onAdd }: TodoInputProps) {
  const [raw, setRaw] = useState('');
  const [category, setCategory] = useState<Category>('Personal');
  const [priority, setPriority] = useState<Priority>('Medium');
  const [dueDate, setDueDate] = useState('');
  const [expanded, setExpanded] = useState(false);
  const [status, setStatus] = useState<'idle' | 'saving'>('idle');
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const reduceMotion = useReducedMotion();

  // Parsing is derived, never written back into the field. The old version
  // rewrote the input from a `useEffect`, which ate characters as you typed.
  const parsed = useMemo(() => parseQuickAdd(raw), [raw]);

  const effectivePriority = parsed.priority ?? priority;
  const effectiveCategory = parsed.category ?? category;
  const effectiveDue = parsed.dueDate ?? dueDate;
  const canSubmit = parsed.title.length > 0 && status === 'idle';

  // "n" focuses the composer from anywhere, the way task apps behave.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const target = e.target as HTMLElement | null;
      const typing =
        target &&
        (target.tagName === 'INPUT' ||
          target.tagName === 'TEXTAREA' ||
          target.isContentEditable);
      if (e.key === 'n' && !typing && !e.metaKey && !e.ctrlKey && !e.altKey) {
        e.preventDefault();
        inputRef.current?.focus();
      }
    };
    document.addEventListener('keydown', onKey);
    return () => document.removeEventListener('keydown', onKey);
  }, []);

  const reset = () => {
    setRaw('');
    setDueDate('');
    setPriority('Medium');
    setCategory('Personal');
    setError(null);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!canSubmit) {
      setError('Give the task a name first.');
      return;
    }

    setStatus('saving');
    setError(null);
    try {
      const res = await fetch('/api/todos', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          title: parsed.title,
          category: effectiveCategory,
          priority: effectivePriority,
          dueDate: effectiveDue || null,
          tags: parsed.tags,
        }),
      });
      if (!res.ok) throw new Error(String(res.status));
      onAdd(await res.json());
      reset();
      inputRef.current?.focus();
    } catch {
      setError('Could not save the task. Check your connection and try again.');
    } finally {
      setStatus('idle');
    }
  };

  const showDetails = expanded || raw.length > 0;

  return (
    <form onSubmit={handleSubmit} className="panel" style={{ marginBottom: '1.5rem' }}>
      <div className="panel-pad" style={{ paddingBottom: showDetails ? '1rem' : '1.25rem' }}>
        <label className="sr-only" htmlFor="quick-add">
          Task name
        </label>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <Plus size={18} strokeWidth={1.75} style={{ color: 'var(--text-3)', flexShrink: 0 }} />
          <input
            id="quick-add"
            ref={inputRef}
            type="text"
            className={`input-bare ${error ? 'input-invalid' : ''}`}
            style={{ fontSize: '1rem' }}
            placeholder="Add a task, for example: Draft the Q3 brief @work !high tomorrow"
            value={raw}
            onChange={(e) => {
              setRaw(e.target.value);
              if (error) setError(null);
            }}
            onFocus={() => setExpanded(true)}
            aria-describedby="quick-add-help"
            aria-invalid={error ? true : undefined}
          />
        </div>

        <AnimatePresence initial={false}>
          {parsed.matched.length > 0 && (
            <motion.div
              initial={reduceMotion ? false : { opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              exit={reduceMotion ? undefined : { opacity: 0, height: 0 }}
              transition={{ duration: 0.16, ease: [0.16, 1, 0.3, 1] }}
              style={{ overflow: 'hidden' }}
            >
              <div
                style={{
                  display: 'flex', flexWrap: 'wrap', gap: '0.375rem',
                  alignItems: 'center', paddingTop: '0.75rem', marginLeft: '1.75rem',
                }}
              >
                <span className="field-help">Detected</span>
                {parsed.matched.map((m) => (
                  <span key={`${m.kind}-${m.label}`} className="tag">
                    {m.label}
                  </span>
                ))}
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      <AnimatePresence initial={false}>
        {showDetails && (
          <motion.div
            initial={reduceMotion ? false : { opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={reduceMotion ? undefined : { opacity: 0, height: 0 }}
            transition={{ duration: 0.2, ease: [0.16, 1, 0.3, 1] }}
            style={{ overflow: 'visible' }}
          >
            <div
              style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))',
                gap: '0.75rem',
                padding: '1rem 1.25rem',
                borderTop: '1px solid var(--line)',
              }}
            >
              <CustomDropdown
                label="Category"
                options={CATEGORIES}
                value={effectiveCategory}
                onChange={(v) => setCategory(v as Category)}
              />
              <CustomDropdown
                label="Priority"
                options={PRIORITIES}
                value={effectivePriority}
                onChange={(v) => setPriority(v as Priority)}
                renderOption={(option) => (
                  <span className="prio" data-level={option}>
                    <span className="prio-bar" aria-hidden="true" />
                    {option}
                  </span>
                )}
              />
              <DateTimePicker value={effectiveDue} onChange={setDueDate} />
            </div>

            <div
              style={{
                display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                gap: '1rem', flexWrap: 'wrap',
                padding: '0 1.25rem 1.25rem',
              }}
            >
              <p className="field-help" id="quick-add-help" style={{ margin: 0 }}>
                Shortcuts: <strong>!high</strong>, <strong>@work</strong>, <strong>#tag</strong>,{' '}
                <strong>tomorrow</strong>
              </p>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                {raw.length > 0 && (
                  <button type="button" className="btn btn-ghost btn-sm" onClick={reset}>
                    Clear
                  </button>
                )}
                <button type="submit" className="btn btn-primary" disabled={!canSubmit}>
                  {status === 'saving' ? (
                    <>
                      <Loader2 size={15} strokeWidth={2} className="spin" />
                      Saving
                    </>
                  ) : (
                    'Add task'
                  )}
                </button>
              </div>
            </div>

            {error && (
              <p className="field-error" style={{ padding: '0 1.25rem 1.25rem', margin: 0 }} role="alert">
                <AlertCircle size={14} strokeWidth={1.75} />
                {error}
              </p>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </form>
  );
}
