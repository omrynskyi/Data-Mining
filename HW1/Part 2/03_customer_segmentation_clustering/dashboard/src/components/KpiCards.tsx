import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { Gauge, Layers, Sparkles, TrendingDown, Users2 } from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import type { ClusterProfile, Diagnostics, ExecutiveKpis, Kpis } from '../types';
import { formatNumber, formatScore, silhouetteVerdict } from '../lib/format';

interface KpiCardsProps {
  kpis: Kpis;
  executive: ExecutiveKpis;
  clusters: ClusterProfile[];
  diagnostics: Diagnostics;
}

interface Metric {
  key: string;
  label: string;
  value: string;
  detail: string;
  icon: LucideIcon;
  tone: string;
}

const chartAxis = {
  stroke: '#475569',
  fontSize: 11,
};

const tooltipStyle = {
  backgroundColor: '#0d1220',
  border: '1px solid #22304f',
  borderRadius: '0.5rem',
  fontSize: '12px',
  color: '#e2e8f0',
};

export default function KpiCards({ kpis, executive, clusters, diagnostics }: KpiCardsProps) {
  const verdict = silhouetteVerdict(kpis.silhouette_score);
  const largest = [...clusters].sort((a, b) => b.count - a.count)[0];

  const metrics: Metric[] = [
    {
      key: 'customers',
      label: 'Customers segmented',
      value: String(executive.total_customers),
      detail: `${clusters.length} segments · ${executive.best_model_name}`,
      icon: Users2,
      tone: 'text-sky-300',
    },
    {
      key: 'silhouette',
      label: 'Silhouette score',
      value: formatScore(kpis.silhouette_score),
      detail: verdict.label,
      icon: Sparkles,
      tone: verdict.tone,
    },
    {
      key: 'davies',
      label: 'Davies-Bouldin index',
      value: formatNumber(kpis.davies_bouldin_index, 4),
      detail: 'Lower is better · compactness / separation',
      icon: TrendingDown,
      tone: 'text-violet-300',
    },
    {
      key: 'calinski',
      label: 'Calinski-Harabasz',
      value: formatNumber(kpis.calinski_harabasz_score, 2),
      detail: 'Variance ratio criterion · higher is better',
      icon: Gauge,
      tone: 'text-amber-300',
    },
    {
      key: 'optimal-k',
      label: 'Optimal k',
      value: String(kpis.optimal_k),
      detail: largest ? `Largest: ${largest.name} (${largest.count})` : 'Elbow + silhouette sweep',
      icon: Layers,
      tone: 'text-emerald-300',
    },
  ];

  const sizeData = clusters.map((cluster) => ({
    name: cluster.name,
    short: cluster.persona,
    count: cluster.count,
    color: cluster.color,
  }));

  const curveData = diagnostics.silhouette_curve.map((point, index) => ({
    k: point.k,
    silhouette: point.value,
    inertia: diagnostics.elbow_curve[index]?.value ?? null,
  }));

  return (
    <div className="space-y-6">
      <section aria-label="Executive KPIs" className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-5">
        {metrics.map((metric) => {
          const Icon = metric.icon;
          return (
            <article key={metric.key} className="panel p-4" data-testid={`kpi-${metric.key}`}>
              <div className="flex items-start justify-between">
                <p className="text-[11px] font-semibold uppercase tracking-wider text-slate-500">
                  {metric.label}
                </p>
                <Icon className={`h-4 w-4 ${metric.tone}`} aria-hidden="true" />
              </div>
              <p className="metric-value mt-3">{metric.value}</p>
              <p className="mt-1 text-xs text-slate-500">{metric.detail}</p>
            </article>
          );
        })}
      </section>

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-2">
        <section className="panel" aria-label="Segment sizes">
          <header className="panel-header">
            <div>
              <h2 className="panel-title">Segment sizes</h2>
              <p className="panel-subtitle">Customers assigned to each discovered cluster</p>
            </div>
          </header>
          <div className="h-72 p-4">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={sizeData} margin={{ top: 8, right: 12, bottom: 8, left: -18 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" vertical={false} />
                <XAxis dataKey="short" tick={chartAxis} tickLine={false} axisLine={false} />
                <YAxis tick={chartAxis} tickLine={false} axisLine={false} />
                <Tooltip contentStyle={tooltipStyle} cursor={{ fill: 'rgba(56,189,248,0.08)' }} />
                <Bar dataKey="count" name="Customers" radius={[4, 4, 0, 0]}>
                  {sizeData.map((entry) => (
                    <Cell key={entry.name} fill={entry.color} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </section>

        <section className="panel" aria-label="Model selection diagnostics">
          <header className="panel-header">
            <div>
              <h2 className="panel-title">Elbow &amp; silhouette sweep</h2>
              <p className="panel-subtitle">
                K-Means evaluated across k = {curveData[0]?.k ?? 2}–{curveData[curveData.length - 1]?.k ?? 10}
              </p>
            </div>
            <span className="chip">optimal k = {kpis.optimal_k}</span>
          </header>
          <div className="h-72 p-4">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={curveData} margin={{ top: 8, right: 12, bottom: 8, left: -18 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                <XAxis dataKey="k" tick={chartAxis} tickLine={false} axisLine={false} />
                <YAxis yAxisId="left" tick={chartAxis} tickLine={false} axisLine={false} />
                <YAxis yAxisId="right" orientation="right" tick={chartAxis} tickLine={false} axisLine={false} />
                <Tooltip contentStyle={tooltipStyle} />
                <Line
                  yAxisId="left"
                  type="monotone"
                  dataKey="silhouette"
                  name="Silhouette"
                  stroke="#38bdf8"
                  strokeWidth={2}
                  dot={{ r: 3, fill: '#38bdf8' }}
                />
                <Line
                  yAxisId="right"
                  type="monotone"
                  dataKey="inertia"
                  name="Inertia (WCSS)"
                  stroke="#f59e0b"
                  strokeWidth={2}
                  strokeDasharray="4 3"
                  dot={{ r: 2, fill: '#f59e0b' }}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </section>
      </div>
    </div>
  );
}
