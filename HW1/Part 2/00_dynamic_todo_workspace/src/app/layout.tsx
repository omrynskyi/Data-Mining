import type { Metadata, Viewport } from 'next';
import { Geist, Geist_Mono } from 'next/font/google';
import './globals.css';
import AppShell from '@/components/AppShell';
import PomodoroTimer from '@/components/PomodoroTimer';

const geist = Geist({ subsets: ['latin'], variable: '--font-geist', display: 'swap' });
const geistMono = Geist_Mono({ subsets: ['latin'], variable: '--font-geist-mono', display: 'swap' });

export const metadata: Metadata = {
  title: 'Zenith',
  description: 'A task workspace with list, board, timeline, matrix, and analytics views.',
};

export const viewport: Viewport = {
  themeColor: [
    { media: '(prefers-color-scheme: light)', color: '#f6f5f3' },
    { media: '(prefers-color-scheme: dark)', color: '#131211' },
  ],
};

/**
 * Resolves the theme before first paint so the page never flashes the wrong
 * mode. Kept inline and tiny on purpose.
 */
const themeScript = `
(function () {
  try {
    var stored = localStorage.getItem('zenith-theme');
    var prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    var theme = stored === 'light' || stored === 'dark' ? stored : (prefersDark ? 'dark' : 'light');
    document.documentElement.setAttribute('data-theme', theme);
  } catch (e) {
    document.documentElement.setAttribute('data-theme', 'light');
  }
})();
`;

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" className={`${geist.variable} ${geistMono.variable}`} suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: themeScript }} />
      </head>
      <body>
        <a className="skip-link" href="#content">
          Skip to content
        </a>
        <AppShell>{children}</AppShell>
        <PomodoroTimer />
      </body>
    </html>
  );
}
