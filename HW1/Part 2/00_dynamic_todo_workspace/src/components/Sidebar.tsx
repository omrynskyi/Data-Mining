'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { motion } from 'framer-motion';
import { BarChart3, CalendarDays, Columns3, Grid2x2, ListTodo, CheckCheck } from 'lucide-react';
import ThemeToggle from './ThemeToggle';

const LINKS = [
  { name: 'List', href: '/', icon: ListTodo },
  { name: 'Board', href: '/kanban', icon: Columns3 },
  { name: 'Timeline', href: '/timeline', icon: CalendarDays },
  { name: 'Matrix', href: '/matrix', icon: Grid2x2 },
  { name: 'Analytics', href: '/analytics', icon: BarChart3 },
];

export default function Sidebar({ onNavigate }: { onNavigate?: () => void }) {
  const pathname = usePathname();

  return (
    <>
      <Link href="/" className="rail-brand" onClick={onNavigate}>
        <span className="rail-mark" aria-hidden="true">
          <CheckCheck size={17} strokeWidth={2} />
        </span>
        <span className="rail-wordmark">Zenith</span>
      </Link>

      <nav className="rail-nav" aria-label="Views">
        {LINKS.map((link) => {
          const isActive = pathname === link.href;
          return (
            <Link
              key={link.href}
              href={link.href}
              className="rail-link"
              aria-current={isActive ? 'page' : undefined}
              onClick={onNavigate}
            >
              {/* Shared element so the active marker slides between items. */}
              {isActive && (
                <motion.span
                  layoutId="rail-active"
                  className="rail-link-bg"
                  transition={{ type: 'spring', stiffness: 380, damping: 32 }}
                />
              )}
              <link.icon size={17} strokeWidth={isActive ? 2 : 1.75} />
              {link.name}
            </Link>
          );
        })}
      </nav>

      <div className="rail-foot">
        <p className="rail-hint">
          Type <kbd>!high</kbd>, <kbd>@work</kbd>, <kbd>#tag</kbd>, or <kbd>tomorrow</kbd> straight into
          the task field and Zenith fills the rest in.
        </p>
        <ThemeToggle />
      </div>
    </>
  );
}
