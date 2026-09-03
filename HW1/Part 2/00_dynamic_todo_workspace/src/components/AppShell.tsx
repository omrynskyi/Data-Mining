'use client';

import { useEffect, useState } from 'react';
import { AnimatePresence, motion, useReducedMotion } from 'framer-motion';
import { Menu, X } from 'lucide-react';
import Sidebar from './Sidebar';
import { useMediaQuery } from '@/hooks/useMediaQuery';

/**
 * Two-column shell. At >=1024px the rail is a static column; below that it
 * becomes a drawer behind a top bar, so the app is usable on a phone (the
 * previous layout pinned a 250px rail at every width with `overflow: hidden`
 * on the body).
 */
export default function AppShell({ children }: { children: React.ReactNode }) {
  const [drawerOpen, setDrawerOpen] = useState(false);
  const isDesktop = useMediaQuery('(min-width: 1024px)', true);
  const reduceMotion = useReducedMotion();

  useEffect(() => {
    if (!drawerOpen) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setDrawerOpen(false);
    };
    document.addEventListener('keydown', onKey);
    return () => document.removeEventListener('keydown', onKey);
  }, [drawerOpen]);

  const railVisible = isDesktop || drawerOpen;

  return (
    <div className="shell">
      <AnimatePresence>
        {railVisible && (
          <motion.div
            key="rail"
            initial={isDesktop || reduceMotion ? false : { x: '-100%' }}
            animate={{ x: 0 }}
            exit={isDesktop || reduceMotion ? undefined : { x: '-100%' }}
            transition={{ duration: 0.22, ease: [0.16, 1, 0.3, 1] }}
            className="rail"
          >
            <Sidebar onNavigate={() => setDrawerOpen(false)} />
          </motion.div>
        )}
      </AnimatePresence>

      <AnimatePresence>
        {!isDesktop && drawerOpen && (
          <motion.div
            key="scrim"
            className="scrim"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.18 }}
            onClick={() => setDrawerOpen(false)}
            aria-hidden="true"
          />
        )}
      </AnimatePresence>

      <div className="main">
        <div className="topbar">
          <button
            type="button"
            className="btn-icon"
            aria-label={drawerOpen ? 'Close navigation' : 'Open navigation'}
            aria-expanded={drawerOpen}
            onClick={() => setDrawerOpen((open) => !open)}
          >
            {drawerOpen ? <X size={18} strokeWidth={1.75} /> : <Menu size={18} strokeWidth={1.75} />}
          </button>
          <span style={{ fontWeight: 600, letterSpacing: '-0.015em' }}>Zenith</span>
        </div>

        <main id="content" className="main-inner">
          {children}
        </main>
      </div>
    </div>
  );
}
