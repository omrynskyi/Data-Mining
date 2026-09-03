'use client';

import { useSyncExternalStore } from 'react';
import { Moon, Sun } from 'lucide-react';

type Theme = 'light' | 'dark';

/** Watches the attribute the inline script in `layout.tsx` already set. */
function subscribe(onChange: () => void) {
  const observer = new MutationObserver(onChange);
  observer.observe(document.documentElement, {
    attributes: true,
    attributeFilter: ['data-theme'],
  });
  return () => observer.disconnect();
}

const readTheme = (): Theme =>
  document.documentElement.getAttribute('data-theme') === 'dark' ? 'dark' : 'light';

export default function ThemeToggle() {
  // useSyncExternalStore hydrates with the server snapshot and swaps to the
  // real value without a mismatch warning, so the label is never wrong.
  const theme = useSyncExternalStore<Theme>(subscribe, readTheme, () => 'light');

  const toggle = () => {
    const next: Theme = theme === 'dark' ? 'light' : 'dark';
    document.documentElement.setAttribute('data-theme', next);
    try {
      localStorage.setItem('zenith-theme', next);
    } catch {
      // Storage is unavailable in some private windows; the attribute still applies.
    }
  };

  return (
    <button
      type="button"
      className="btn btn-ghost btn-sm"
      onClick={toggle}
      aria-label={`Switch to ${theme === 'dark' ? 'light' : 'dark'} mode`}
      style={{ justifyContent: 'flex-start', gap: '0.625rem', padding: '0.5rem 0.625rem' }}
    >
      {theme === 'dark' ? <Moon size={16} strokeWidth={1.75} /> : <Sun size={16} strokeWidth={1.75} />}
      <span>{theme === 'dark' ? 'Dark mode' : 'Light mode'}</span>
    </button>
  );
}
