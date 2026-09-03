import { useEffect, useState } from 'react';
import { AlertTriangle, Menu, X } from 'lucide-react';
import AutoresearchLab from './components/AutoresearchLab';
import ClusterVisualizer2D from './components/ClusterVisualizer2D';
import ClusterVisualizer3D from './components/ClusterVisualizer3D';
import CrispDmGuide from './components/CrispDmGuide';
import CustomerTable from './components/CustomerTable';
import DistributionsChart from './components/DistributionsChart';
import KpiCards from './components/KpiCards';
import Navbar, { NAV_ITEMS } from './components/Navbar';
import PersonaCards from './components/PersonaCards';
import { useDashboardData } from './hooks/useDashboardData';
import type { ViewId } from './types';
import { formatScore } from './lib/format';

/** Resolves the view encoded in the URL hash (e.g. `#/personas`), defaulting to overview. */
const viewFromHash = (): ViewId => {
  if (typeof window === 'undefined') return 'overview';
  const id = window.location.hash.replace(/^#\/?/, '');
  return NAV_ITEMS.some((item) => item.id === id) ? (id as ViewId) : 'overview';
};

export default function App() {
  const [activeView, setActiveView] = useState<ViewId>(viewFromHash);
  const [navOpen, setNavOpen] = useState(false);
  const { pipeline, autoresearch, usingFallback, error } = useDashboardData();

  // Keep the view in sync with the hash so sections are deep-linkable and the
  // browser's back button moves between them.
  useEffect(() => {
    const onHashChange = () => setActiveView(viewFromHash());
    window.addEventListener('hashchange', onHashChange);
    return () => window.removeEventListener('hashchange', onHashChange);
  }, []);

  const active = NAV_ITEMS.find((item) => item.id === activeView) ?? NAV_ITEMS[0];

  const selectView = (view: ViewId) => {
    setActiveView(view);
    setNavOpen(false);
    if (typeof window !== 'undefined') window.location.hash = `/${view}`;
  };

  return (
    <div className="flex h-full min-h-screen bg-surface-950">
      <aside className="hidden w-64 shrink-0 lg:block">
        <Navbar
          activeView={activeView}
          onSelect={selectView}
          datasetName={pipeline.metadata.dataset_name}
          generatedAt={pipeline.metadata.generated_at}
          usingFallback={usingFallback}
        />
      </aside>

      {navOpen ? (
        <div className="fixed inset-0 z-40 flex lg:hidden">
          <div
            className="absolute inset-0 bg-black/60"
            onClick={() => setNavOpen(false)}
            aria-hidden="true"
          />
          <div className="relative z-50 w-64">
            <Navbar
              activeView={activeView}
              onSelect={selectView}
              datasetName={pipeline.metadata.dataset_name}
              generatedAt={pipeline.metadata.generated_at}
              usingFallback={usingFallback}
            />
          </div>
        </div>
      ) : null}

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="sticky top-0 z-30 flex items-center gap-4 border-b border-surface-800 bg-surface-950/90 px-5 py-4 backdrop-blur">
          <button
            type="button"
            onClick={() => setNavOpen((open) => !open)}
            aria-label={navOpen ? 'Close navigation' : 'Open navigation'}
            className="rounded-lg border border-surface-700 bg-surface-850 p-2 text-slate-300 lg:hidden"
          >
            {navOpen ? <X className="h-4 w-4" /> : <Menu className="h-4 w-4" />}
          </button>

          <div className="min-w-0 flex-1">
            <h1 className="truncate text-base font-semibold text-slate-100">{active.label}</h1>
            <p className="truncate text-xs text-slate-500">
              Mall customer segmentation · {pipeline.dataset_summary.total_customers} records ·{' '}
              {pipeline.clusters.length} segments
            </p>
          </div>

          <div className="hidden shrink-0 items-center gap-2 sm:flex">
            <span className="chip">{pipeline.executive_kpis.best_model_name}</span>
            <span className="chip">silhouette {formatScore(pipeline.kpis.silhouette_score)}</span>
          </div>
        </header>

        {error ? (
          <div
            role="status"
            className="flex items-start gap-2 border-b border-amber-500/30 bg-amber-500/10 px-5 py-2.5 text-xs text-amber-200"
          >
            <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0" aria-hidden="true" />
            <span>{error}</span>
          </div>
        ) : null}

        <main className="flex-1 overflow-y-auto p-5">
          {activeView === 'overview' ? (
            <KpiCards
              kpis={pipeline.kpis}
              executive={pipeline.executive_kpis}
              clusters={pipeline.clusters}
              diagnostics={pipeline.diagnostics}
            />
          ) : null}

          {activeView === 'segments' ? (
            <div className="space-y-6">
              <ClusterVisualizer2D customers={pipeline.customers} clusters={pipeline.clusters} />
              <ClusterVisualizer3D customers={pipeline.customers} clusters={pipeline.clusters} />
            </div>
          ) : null}

          {activeView === 'distributions' ? (
            <DistributionsChart
              distributions={pipeline.distributions}
              clusters={pipeline.clusters}
              summary={pipeline.dataset_summary}
              correlation={pipeline.correlation_matrix}
            />
          ) : null}

          {activeView === 'personas' ? (
            <PersonaCards
              clusters={pipeline.clusters}
              totalCustomers={pipeline.dataset_summary.total_customers}
            />
          ) : null}

          {activeView === 'autoresearch' ? (
            <AutoresearchLab
              autoresearch={autoresearch}
              modelComparisons={pipeline.model_comparisons}
            />
          ) : null}

          {activeView === 'explorer' ? (
            <CustomerTable customers={pipeline.customers} clusters={pipeline.clusters} />
          ) : null}

          {activeView === 'methodology' ? (
            <CrispDmGuide
              metadata={pipeline.metadata}
              featureNames={pipeline.dataset_summary.features}
            />
          ) : null}
        </main>
      </div>
    </div>
  );
}
