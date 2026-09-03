'use client';

import { useEffect, useMemo, useRef, useState } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { CalendarDays, ChevronLeft, ChevronRight, X } from 'lucide-react';
import { dayKey } from '@/lib/format';

interface DateTimePickerProps {
  value: string;
  onChange: (val: string) => void;
  label?: string;
}

const DOW = ['Mo', 'Tu', 'We', 'Th', 'Fr', 'Sa', 'Su'];
const MONTHS = [
  'January', 'February', 'March', 'April', 'May', 'June',
  'July', 'August', 'September', 'October', 'November', 'December',
];

const pad = (n: number) => String(n).padStart(2, '0');

/** Builds the local-time ISO string the API stores, without UTC drift. */
function composeIso(date: Date, time: string): string {
  const [h, m] = time.split(':');
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${h}:${m}:00`;
}

export default function DateTimePicker({ value, onChange, label = 'Due date' }: DateTimePickerProps) {
  const [isOpen, setIsOpen] = useState(false);
  const wrapRef = useRef<HTMLDivElement>(null);
  const triggerRef = useRef<HTMLButtonElement>(null);
  const gridRef = useRef<HTMLDivElement>(null);

  const selected = value ? new Date(value) : null;
  const isValid = selected !== null && !Number.isNaN(selected.getTime());

  const [cursor, setCursor] = useState(() => (isValid ? new Date(selected) : new Date()));
  // The time is derived from the value whenever there is one; the draft only
  // holds the choice made before a date has been picked.
  const [draftTime, setDraftTime] = useState('09:00');
  const time = isValid ? `${pad(selected.getHours())}:${pad(selected.getMinutes())}` : draftTime;

  useEffect(() => {
    if (!isOpen) return;
    const onPointerDown = (e: MouseEvent) => {
      if (wrapRef.current && !wrapRef.current.contains(e.target as Node)) setIsOpen(false);
    };
    document.addEventListener('mousedown', onPointerDown);
    return () => document.removeEventListener('mousedown', onPointerDown);
  }, [isOpen]);

  // Monday-first grid, with leading blanks so weekdays line up.
  const cells = useMemo(() => {
    const year = cursor.getFullYear();
    const month = cursor.getMonth();
    const first = new Date(year, month, 1);
    const lead = (first.getDay() + 6) % 7;
    const daysInMonth = new Date(year, month + 1, 0).getDate();
    return [
      ...Array.from({ length: lead }, () => null),
      ...Array.from({ length: daysInMonth }, (_, i) => new Date(year, month, i + 1)),
    ];
  }, [cursor]);

  const shiftMonth = (delta: number) =>
    setCursor((c) => new Date(c.getFullYear(), c.getMonth() + delta, 1));

  const pick = (date: Date) => onChange(composeIso(date, time));

  const onGridKeyDown = (e: React.KeyboardEvent) => {
    const deltas: Record<string, number> = {
      ArrowLeft: -1, ArrowRight: 1, ArrowUp: -7, ArrowDown: 7,
    };
    if (e.key in deltas) {
      e.preventDefault();
      setCursor((c) => {
        const next = new Date(c);
        next.setDate(next.getDate() + deltas[e.key]);
        return next;
      });
      return;
    }
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      pick(cursor);
      setIsOpen(false);
      triggerRef.current?.focus();
    }
    if (e.key === 'Escape') {
      e.preventDefault();
      setIsOpen(false);
      triggerRef.current?.focus();
    }
  };

  const todayKey = dayKey(new Date());
  const selectedKey = isValid ? dayKey(selected) : null;
  const cursorKey = dayKey(cursor);

  const triggerText = isValid
    ? selected.toLocaleString(undefined, {
        month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit',
      })
    : 'No date';

  return (
    <div className="field" ref={wrapRef} style={{ position: 'relative' }}>
      <span className="field-label">{label}</span>
      <button
        ref={triggerRef}
        type="button"
        className="select-trigger"
        aria-haspopup="dialog"
        aria-expanded={isOpen}
        onClick={() => {
          if (!isOpen) setCursor(isValid ? new Date(selected) : new Date());
          setIsOpen((open) => !open);
        }}
      >
        <span
          style={{ display: 'inline-flex', alignItems: 'center', gap: '0.45rem' }}
          className={isValid ? undefined : 'select-placeholder'}
        >
          <CalendarDays size={15} strokeWidth={1.75} />
          {triggerText}
        </span>
        {isValid && (
          <span
            role="button"
            tabIndex={0}
            aria-label="Clear due date"
            className="btn-icon"
            style={{ width: 22, height: 22 }}
            onClick={(e) => {
              e.stopPropagation();
              onChange('');
            }}
            onKeyDown={(e) => {
              if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                e.stopPropagation();
                onChange('');
              }
            }}
          >
            <X size={13} strokeWidth={2} />
          </span>
        )}
      </button>

      <AnimatePresence>
        {isOpen && (
          <motion.div
            role="dialog"
            aria-label="Choose a due date"
            className="popover"
            style={{ width: 268, right: 0, left: 'auto' }}
            initial={{ opacity: 0, y: -4 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -4 }}
            transition={{ duration: 0.13, ease: [0.16, 1, 0.3, 1] }}
          >
            <div
              style={{
                display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                gap: '0.5rem', padding: '0.25rem 0.25rem 0.5rem',
              }}
            >
              <button type="button" className="btn-icon" aria-label="Previous month" onClick={() => shiftMonth(-1)}>
                <ChevronLeft size={16} strokeWidth={1.75} />
              </button>
              <span style={{ fontWeight: 600, fontSize: '0.875rem' }} aria-live="polite">
                {MONTHS[cursor.getMonth()]} {cursor.getFullYear()}
              </span>
              <button type="button" className="btn-icon" aria-label="Next month" onClick={() => shiftMonth(1)}>
                <ChevronRight size={16} strokeWidth={1.75} />
              </button>
            </div>

            <div className="cal-grid" aria-hidden="true">
              {DOW.map((d) => (
                <span key={d} className="cal-dow">{d}</span>
              ))}
            </div>

            <div
              ref={gridRef}
              className="cal-grid"
              role="grid"
              tabIndex={0}
              onKeyDown={onGridKeyDown}
              style={{ outline: 'none' }}
            >
              {cells.map((date, i) => {
                if (!date) return <span key={`blank-${i}`} />;
                const key = dayKey(date);
                return (
                  <button
                    key={key}
                    type="button"
                    role="gridcell"
                    className="cal-day"
                    aria-selected={key === selectedKey}
                    data-today={key === todayKey}
                    style={
                      key === cursorKey && key !== selectedKey
                        ? { borderColor: 'var(--line-strong)' }
                        : undefined
                    }
                    onClick={() => {
                      pick(date);
                      setIsOpen(false);
                    }}
                  >
                    {date.getDate()}
                  </button>
                );
              })}
            </div>

            <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'flex-end', marginTop: '0.625rem' }}>
              <label className="field" style={{ flex: 1 }}>
                <span className="field-label">Time</span>
                <input
                  type="time"
                  className="input"
                  value={time}
                  onChange={(e) => {
                    if (isValid) onChange(composeIso(selected, e.target.value));
                    else setDraftTime(e.target.value);
                  }}
                />
              </label>
              <button
                type="button"
                className="btn btn-secondary btn-sm"
                onClick={() => {
                  const today = new Date();
                  setCursor(today);
                  pick(today);
                  setIsOpen(false);
                }}
              >
                Today
              </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
