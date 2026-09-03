import {
  Activity,
  BookOpen,
  FlaskConical,
  LayoutDashboard,
  ScatterChart,
  Table2,
  Users,
} from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import type { ViewId } from '../types';

export interface NavItem {
  id: ViewId;
  label: string;
  hint: string;
  icon: LucideIcon;
}

export const NAV_ITEMS: NavItem[] = [
  { id: 'overview', label: 'Overview', hint: 'Executive KPIs', icon: LayoutDashboard },
  { id: 'segments', label: 'Segments', hint: '2D & 3D clusters', icon: ScatterChart },
  { id: 'distributions', label: 'Distributions', hint: 'Features & demographics', icon: Activity },
  { id: 'personas', label: 'Personas', hint: 'Business actions', icon: Users },
  { id: 'autoresearch', label: 'Autoresearch Lab', hint: 'Hill-climbing & models', icon: FlaskConical },
  { id: 'explorer', label: 'Customer Explorer', hint: 'Record-level table', icon: Table2 },
  { id: 'methodology', label: 'CRISP-DM', hint: 'Process reference', icon: BookOpen },
];

interface NavbarProps {
  activeView: ViewId;
  onSelect: (view: ViewId) => void;
  datasetName: string;
  generatedAt: string;
  usingFallback: boolean;
}

export default function Navbar({
  activeView,
  onSelect,
  datasetName,
  generatedAt,
  usingFallback,
}: NavbarProps) {
  const generatedLabel = (() => {
    const parsed = new Date(generatedAt);
    return Number.isNaN(parsed.getTime()) ? generatedAt : parsed.toUTCString();
  })();

  return (
    <nav
      aria-label="Dashboard sections"
      className="flex h-full w-full flex-col border-r border-surface-800 bg-surface-900/70"
    >
      <div className="border-b border-surface-800 px-5 py-5">
        <div className="flex items-center gap-2.5">
          <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-accent/15 text-accent">
            <ScatterChart className="h-5 w-5" aria-hidden="true" />
          </span>
          <div>
            <h1 className="text-sm font-semibold leading-tight text-slate-100">
              Segmentation Console
            </h1>
            <p className="text-[11px] leading-tight text-slate-500">CRISP-DM · Unsupervised ML</p>
          </div>
        </div>
      </div>

      <ul className="flex flex-1 flex-col gap-1 overflow-y-auto p-3">
        {NAV_ITEMS.map((item) => {
          const Icon = item.icon;
          const isActive = item.id === activeView;
          return (
            <li key={item.id}>
              <button
                type="button"
                onClick={() => onSelect(item.id)}
                aria-current={isActive ? 'page' : undefined}
                className={[
                  'group flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-left transition',
                  isActive
                    ? 'bg-accent/15 text-accent'
                    : 'text-slate-400 hover:bg-surface-850 hover:text-slate-200',
                ].join(' ')}
              >
                <Icon className="h-4 w-4 shrink-0" aria-hidden="true" />
                <span className="min-w-0">
                  <span className="block truncate text-sm font-medium">{item.label}</span>
                  <span className="block truncate text-[11px] text-slate-500">{item.hint}</span>
                </span>
              </button>
            </li>
          );
        })}
      </ul>

      <div className="border-t border-surface-800 px-5 py-4 text-[11px] leading-relaxed text-slate-500">
        <p className="font-medium text-slate-400">{datasetName}</p>
        <p>Artifacts generated {generatedLabel}</p>
        <p className="mt-2">
          <span
            className={[
              'chip',
              usingFallback ? 'border-amber-500/40 text-amber-300' : 'border-emerald-500/40 text-emerald-300',
            ].join(' ')}
          >
            {usingFallback ? 'Bundled snapshot' : 'Live pipeline artifacts'}
          </span>
        </p>
      </div>
    </nav>
  );
}
