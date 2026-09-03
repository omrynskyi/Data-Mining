'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import { AnimatePresence, motion, useReducedMotion } from 'framer-motion';
import { Pause, Play, RotateCcw, Timer, X } from 'lucide-react';

const DURATIONS = { Focus: 25 * 60, Break: 5 * 60 } as const;
type Mode = keyof typeof DURATIONS;

const RADIUS = 34;
const CIRCUMFERENCE = 2 * Math.PI * RADIUS;

/** Short two-tone chime, synthesised so the app carries no external audio. */
function chime() {
  try {
    const Ctor =
      window.AudioContext ??
      (window as unknown as { webkitAudioContext?: typeof AudioContext }).webkitAudioContext;
    if (!Ctor) return;
    const ctx = new Ctor();
    [0, 0.18].forEach((offset, i) => {
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.type = 'sine';
      osc.frequency.value = i === 0 ? 660 : 880;
      gain.gain.setValueAtTime(0.0001, ctx.currentTime + offset);
      gain.gain.exponentialRampToValueAtTime(0.14, ctx.currentTime + offset + 0.02);
      gain.gain.exponentialRampToValueAtTime(0.0001, ctx.currentTime + offset + 0.16);
      osc.connect(gain).connect(ctx.destination);
      osc.start(ctx.currentTime + offset);
      osc.stop(ctx.currentTime + offset + 0.18);
    });
    setTimeout(() => ctx.close(), 800);
  } catch {
    // Audio is a nicety; a blocked context must not break the timer.
  }
}

export default function PomodoroTimer() {
  const [isOpen, setIsOpen] = useState(false);
  const [mode, setMode] = useState<Mode>('Focus');
  const [remaining, setRemaining] = useState<number>(DURATIONS.Focus);
  const [running, setRunning] = useState(false);
  const deadlineRef = useRef<number | null>(null);
  const reduceMotion = useReducedMotion();

  const switchMode = useCallback((next: Mode) => {
    setMode(next);
    setRunning(false);
    deadlineRef.current = null;
    setRemaining(DURATIONS[next]);
  }, []);

  // Counting against a wall-clock deadline keeps the timer honest while the
  // tab is backgrounded and browsers throttle intervals.
  useEffect(() => {
    if (!running || deadlineRef.current === null) return;

    const tick = () => {
      const left = Math.max(0, Math.round((deadlineRef.current! - Date.now()) / 1000));
      setRemaining(left);
      if (left === 0) {
        setRunning(false);
        deadlineRef.current = null;
        chime();
        const next: Mode = mode === 'Focus' ? 'Break' : 'Focus';
        setMode(next);
        setRemaining(DURATIONS[next]);
      }
    };

    const id = setInterval(tick, 250);
    return () => clearInterval(id);
  }, [running, mode]);

  const toggleRun = () => {
    if (running) {
      deadlineRef.current = null;
      setRunning(false);
    } else {
      deadlineRef.current = Date.now() + remaining * 1000;
      setRunning(true);
    }
  };

  const reset = () => {
    deadlineRef.current = null;
    setRunning(false);
    setRemaining(DURATIONS[mode]);
  };

  const minutes = String(Math.floor(remaining / 60)).padStart(2, '0');
  const seconds = String(remaining % 60).padStart(2, '0');
  const elapsed = 1 - remaining / DURATIONS[mode];

  return (
    <div className="dock">
      <AnimatePresence mode="wait">
        {isOpen ? (
          <motion.div
            key="panel"
            className="dock-panel"
            role="group"
            aria-label="Pomodoro timer"
            initial={reduceMotion ? false : { opacity: 0, y: 8, scale: 0.97 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={reduceMotion ? undefined : { opacity: 0, y: 8, scale: 0.97 }}
            transition={{ duration: 0.18, ease: [0.16, 1, 0.3, 1] }}
          >
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.875rem' }}>
              <span style={{ fontSize: '0.8125rem', fontWeight: 600, color: 'var(--text-2)' }}>
                {mode === 'Focus' ? 'Focus session' : 'Short break'}
              </span>
              <button type="button" className="btn-icon" aria-label="Close timer" onClick={() => setIsOpen(false)}>
                <X size={15} strokeWidth={1.75} />
              </button>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', marginBottom: '1rem' }}>
              <svg width="80" height="80" viewBox="0 0 80 80" aria-hidden="true" style={{ flexShrink: 0 }}>
                <circle cx="40" cy="40" r={RADIUS} fill="none" stroke="var(--surface-3)" strokeWidth="5" />
                <circle
                  cx="40"
                  cy="40"
                  r={RADIUS}
                  fill="none"
                  stroke="var(--accent)"
                  strokeWidth="5"
                  strokeLinecap="round"
                  strokeDasharray={CIRCUMFERENCE}
                  strokeDashoffset={CIRCUMFERENCE * (1 - elapsed)}
                  transform="rotate(-90 40 40)"
                  style={{ transition: 'stroke-dashoffset 0.3s linear' }}
                />
              </svg>
              <div>
                <p className="dock-time num" role="timer" aria-live="off">
                  {minutes}:{seconds}
                </p>
                <p className="field-help" style={{ marginTop: '0.35rem' }}>
                  {running ? 'Running' : 'Paused'}
                </p>
              </div>
            </div>

            <div className="dock-modes" style={{ marginBottom: '0.75rem' }}>
              {(Object.keys(DURATIONS) as Mode[]).map((m) => (
                <button
                  key={m}
                  type="button"
                  className="dock-mode"
                  aria-pressed={mode === m}
                  onClick={() => switchMode(m)}
                >
                  {m}
                </button>
              ))}
            </div>

            <div style={{ display: 'flex', gap: '0.5rem' }}>
              <button type="button" className="btn btn-primary btn-sm" style={{ flex: 1 }} onClick={toggleRun}>
                {running ? <Pause size={14} strokeWidth={2} /> : <Play size={14} strokeWidth={2} />}
                {running ? 'Pause' : 'Start'}
              </button>
              <button type="button" className="btn btn-secondary btn-sm" onClick={reset} aria-label="Reset timer">
                <RotateCcw size={14} strokeWidth={1.75} />
              </button>
            </div>
          </motion.div>
        ) : (
          <motion.button
            key="toggle"
            type="button"
            className="dock-toggle"
            onClick={() => setIsOpen(true)}
            initial={reduceMotion ? false : { opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={reduceMotion ? undefined : { opacity: 0, scale: 0.9 }}
            transition={{ duration: 0.16, ease: [0.16, 1, 0.3, 1] }}
          >
            <Timer size={16} strokeWidth={1.75} style={{ color: running ? 'var(--accent)' : 'var(--text-3)' }} />
            <span className="num">
              {minutes}:{seconds}
            </span>
          </motion.button>
        )}
      </AnimatePresence>
    </div>
  );
}
