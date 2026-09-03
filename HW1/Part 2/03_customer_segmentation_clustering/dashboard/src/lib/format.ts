/** Shared number / label formatting helpers used across dashboard views. */

export const formatNumber = (value: number | null | undefined, digits = 2): string =>
  value === null || value === undefined || Number.isNaN(value) ? '—' : value.toFixed(digits);

export const formatScore = (value: number | null | undefined): string => formatNumber(value, 4);

export const formatCompact = (value: number | null | undefined): string =>
  value === null || value === undefined || Number.isNaN(value)
    ? '—'
    : new Intl.NumberFormat('en-US', { notation: 'compact', maximumFractionDigits: 1 }).format(value);

export const formatCurrencyK = (value: number | null | undefined): string =>
  value === null || value === undefined || Number.isNaN(value) ? '—' : `$${value.toFixed(1)}k`;

export const formatPercent = (value: number | null | undefined, digits = 1): string =>
  value === null || value === undefined || Number.isNaN(value) ? '—' : `${value.toFixed(digits)}%`;

export const formatSigned = (value: number | null | undefined, digits = 4): string => {
  if (value === null || value === undefined || Number.isNaN(value)) return '—';
  return `${value >= 0 ? '+' : ''}${value.toFixed(digits)}`;
};

/** Grades a silhouette score using Rousseeuw's (1987) interpretation thresholds. */
export const silhouetteVerdict = (score: number): { label: string; tone: string } => {
  if (score >= 0.7) return { label: 'Strong structure', tone: 'text-emerald-400' };
  if (score >= 0.5) return { label: 'Reasonable structure', tone: 'text-emerald-400' };
  if (score >= 0.25) return { label: 'Weak structure', tone: 'text-amber-400' };
  return { label: 'No substantial structure', tone: 'text-rose-400' };
};

export const hexToRgba = (hex: string, alpha: number): string => {
  const clean = hex.replace('#', '');
  const value = clean.length === 3 ? clean.split('').map((c) => c + c).join('') : clean;
  const num = parseInt(value, 16);
  if (Number.isNaN(num)) return `rgba(148, 163, 184, ${alpha})`;
  const r = (num >> 16) & 255;
  const g = (num >> 8) & 255;
  const b = num & 255;
  return `rgba(${r}, ${g}, ${b}, ${alpha})`;
};
