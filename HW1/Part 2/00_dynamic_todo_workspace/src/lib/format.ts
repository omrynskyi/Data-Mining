/** Date and text helpers shared across the views. */

export function startOfDay(date: Date): Date {
  const d = new Date(date);
  d.setHours(0, 0, 0, 0);
  return d;
}

export function dayKey(value: string | Date): string {
  const d = typeof value === 'string' ? new Date(value) : value;
  const pad = (n: number) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
}

export function daysBetween(from: Date, to: Date): number {
  return Math.round((startOfDay(to).getTime() - startOfDay(from).getTime()) / 86_400_000);
}

export type DueTone = 'overdue' | 'today' | 'soon' | 'later' | 'none';

export function dueTone(dueDate: string | null | undefined, now = new Date()): DueTone {
  if (!dueDate) return 'none';
  const diff = daysBetween(now, new Date(dueDate));
  if (diff < 0) return 'overdue';
  if (diff === 0) return 'today';
  if (diff <= 2) return 'soon';
  return 'later';
}

/** Short label for a due date: "Overdue by 3d", "Today", "Tomorrow", "Mar 14". */
export function dueLabel(dueDate: string, now = new Date()): string {
  const diff = daysBetween(now, new Date(dueDate));
  if (diff === 0) return 'Today';
  if (diff === 1) return 'Tomorrow';
  if (diff === -1) return 'Yesterday';
  if (diff < 0) return `${Math.abs(diff)} days late`;
  if (diff <= 6) {
    return new Date(dueDate).toLocaleDateString(undefined, { weekday: 'long' });
  }
  return new Date(dueDate).toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
}

/**
 * Label plus warning flag for a task's due date. Finished work never reads as
 * late: the board's Done column was rendering "5 days late" in red on tasks
 * that were already completed.
 */
export function dueMeta(
  dueDate: string,
  completed: boolean,
  now = new Date()
): { label: string; warn: boolean } {
  if (completed) {
    return {
      label: new Date(dueDate).toLocaleDateString(undefined, {
        month: 'short',
        day: 'numeric',
      }),
      warn: false,
    };
  }
  return { label: dueLabel(dueDate, now), warn: dueTone(dueDate, now) === 'overdue' };
}

export function timeLabel(dueDate: string): string {
  const d = new Date(dueDate);
  if (d.getHours() === 0 && d.getMinutes() === 0) return '';
  return d.toLocaleTimeString(undefined, { hour: 'numeric', minute: '2-digit' });
}

export function parseTags(raw: string | null | undefined): string[] {
  if (!raw || raw === '[]') return [];
  try {
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed.filter((t): t is string => typeof t === 'string') : [];
  } catch {
    return [];
  }
}

export function plural(count: number, one: string, many = `${one}s`): string {
  return `${count} ${count === 1 ? one : many}`;
}
