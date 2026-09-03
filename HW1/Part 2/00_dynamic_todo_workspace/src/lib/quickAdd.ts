/**
 * Quick-add parser.
 *
 * This runs on demand (on submit, and on a debounce for the preview strip). It
 * is deliberately a pure function: the previous version parsed inside a
 * `useEffect` keyed on the input value and wrote back to that same state, which
 * meant typing the word "today" anywhere in a title silently deleted it
 * mid-keystroke.
 */

export const CATEGORIES = ['Personal', 'Work', 'Urgent'] as const;
export const PRIORITIES = ['Low', 'Medium', 'High'] as const;

export type Category = (typeof CATEGORIES)[number];
export type Priority = (typeof PRIORITIES)[number];

export interface ParsedTask {
  title: string;
  tags: string[];
  priority: Priority | null;
  category: Category | null;
  dueDate: string | null;
  /** Human-readable list of what was recognised, for the preview strip. */
  matched: { kind: 'tag' | 'priority' | 'category' | 'due'; label: string }[];
}

const PRIORITY_TOKENS: Record<string, Priority> = {
  high: 'High',
  urgent: 'High',
  med: 'Medium',
  medium: 'Medium',
  low: 'Low',
};

const CATEGORY_TOKENS: Record<string, Category> = {
  work: 'Work',
  personal: 'Personal',
  urgent: 'Urgent',
};

const WEEKDAYS = ['sunday', 'monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday'];

/** Local-time ISO string the app stores in `dueDate` (no timezone shifting). */
function toLocalIso(date: Date, hours: number, minutes: number): string {
  const d = new Date(date);
  d.setHours(hours, minutes, 0, 0);
  const pad = (n: number) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(
    d.getMinutes()
  )}:00`;
}

export function parseQuickAdd(input: string, now: Date = new Date()): ParsedTask {
  let text = ` ${input} `;
  const matched: ParsedTask['matched'] = [];
  const tags: string[] = [];
  let priority: Priority | null = null;
  let category: Category | null = null;
  let dueDate: string | null = null;

  // #tag
  text = text.replace(/(^|\s)#([\w-]+)/g, (_m, lead: string, tag: string) => {
    if (!tags.includes(tag)) {
      tags.push(tag);
      matched.push({ kind: 'tag', label: `#${tag}` });
    }
    return lead;
  });

  // !priority
  text = text.replace(/(^|\s)!([a-z]+)/gi, (whole, lead: string, token: string) => {
    const hit = PRIORITY_TOKENS[token.toLowerCase()];
    if (!hit) return whole;
    priority = hit;
    matched.push({ kind: 'priority', label: `${hit} priority` });
    return lead;
  });

  // @category
  text = text.replace(/(^|\s)@([a-z]+)/gi, (whole, lead: string, token: string) => {
    const hit = CATEGORY_TOKENS[token.toLowerCase()];
    if (!hit) return whole;
    category = hit;
    matched.push({ kind: 'category', label: hit });
    return lead;
  });

  const setDue = (date: Date, label: string, hours = 9) => {
    if (dueDate) return;
    dueDate = toLocalIso(date, hours, 0);
    matched.push({ kind: 'due', label });
  };

  // Dates, longest phrase first so "next monday" wins over "monday".
  const dateRules: { re: RegExp; apply: () => void }[] = [
    {
      re: /(^|\s)today(\s|$)/i,
      apply: () => setDue(now, 'Due today', 17),
    },
    {
      re: /(^|\s)tomorrow(\s|$)/i,
      apply: () => {
        const d = new Date(now);
        d.setDate(d.getDate() + 1);
        setDue(d, 'Due tomorrow');
      },
    },
    {
      re: /(^|\s)next week(\s|$)/i,
      apply: () => {
        const d = new Date(now);
        d.setDate(d.getDate() + 7);
        setDue(d, 'Due next week');
      },
    },
  ];

  for (const rule of dateRules) {
    if (rule.re.test(text)) {
      rule.apply();
      text = text.replace(rule.re, '$1');
    }
  }

  if (!dueDate) {
    for (let i = 0; i < WEEKDAYS.length; i++) {
      const name = WEEKDAYS[i];
      const re = new RegExp(`(^|\\s)(next\\s+)?${name}(\\s|$)`, 'i');
      if (!re.test(text)) continue;
      const d = new Date(now);
      let delta = (i - d.getDay() + 7) % 7;
      if (delta === 0) delta = 7;
      d.setDate(d.getDate() + delta);
      setDue(d, `Due ${name[0].toUpperCase()}${name.slice(1)}`);
      text = text.replace(re, '$1');
      break;
    }
  }

  return {
    title: text.replace(/\s+/g, ' ').trim(),
    tags,
    priority,
    category,
    dueDate,
    matched,
  };
}
