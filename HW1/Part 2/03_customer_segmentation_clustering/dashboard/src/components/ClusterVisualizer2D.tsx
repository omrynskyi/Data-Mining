import { useMemo, useState } from 'react';
import {
  CartesianGrid,
  Legend,
  Scatter,
  ScatterChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
  ZAxis,
} from 'recharts';
import type { ClusterProfile, Customer } from '../types';

type Projection = 'feature' | 'pca';

interface ClusterVisualizer2DProps {
  customers: Customer[];
  clusters: ClusterProfile[];
}

const axisStyle = { stroke: '#475569', fontSize: 11 };

const tooltipStyle = {
  backgroundColor: '#0d1220',
  border: '1px solid #22304f',
  borderRadius: '0.5rem',
  fontSize: '12px',
  color: '#e2e8f0',
};

export default function ClusterVisualizer2D({ customers, clusters }: ClusterVisualizer2DProps) {
  const [projection, setProjection] = useState<Projection>('feature');
  const [hidden, setHidden] = useState<number[]>([]);

  const series = useMemo(
    () =>
      clusters.map((cluster) => ({
        cluster,
        points: customers
          .filter((customer) => customer.cluster_id === cluster.cluster_id)
          .map((customer) => ({
            x: projection === 'feature' ? customer.annual_income : customer.pca_x,
            y: projection === 'feature' ? customer.spending_score : customer.pca_y,
            id: customer.customer_id,
            age: customer.age,
            gender: customer.gender,
            segment: cluster.name,
          })),
      })),
    [clusters, customers, projection],
  );

  const toggle = (clusterId: number) =>
    setHidden((current) =>
      current.includes(clusterId) ? current.filter((id) => id !== clusterId) : [...current, clusterId],
    );

  const axisLabels =
    projection === 'feature'
      ? { x: 'Annual income (k$)', y: 'Spending score (1–100)' }
      : { x: 'Principal component 1', y: 'Principal component 2' };

  return (
    <section className="panel" aria-label="Two dimensional cluster scatter plot">
      <header className="panel-header">
        <div>
          <h2 className="panel-title">Cluster scatter — 2D</h2>
          <p className="panel-subtitle">
            {customers.length} customers across {clusters.length} segments · {axisLabels.x} vs {axisLabels.y}
          </p>
        </div>
        <div className="flex shrink-0 rounded-lg border border-surface-700 bg-surface-850 p-0.5" role="group">
          {(
            [
              ['feature', 'Feature space'],
              ['pca', 'PCA space'],
            ] as const
          ).map(([value, label]) => (
            <button
              key={value}
              type="button"
              onClick={() => setProjection(value)}
              aria-pressed={projection === value}
              className={[
                'rounded-md px-3 py-1.5 text-xs font-medium transition',
                projection === value ? 'bg-accent/20 text-accent' : 'text-slate-400 hover:text-slate-200',
              ].join(' ')}
            >
              {label}
            </button>
          ))}
        </div>
      </header>

      <div className="h-[26rem] p-4">
        <ResponsiveContainer width="100%" height="100%">
          <ScatterChart margin={{ top: 12, right: 16, bottom: 16, left: -8 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
            <XAxis
              type="number"
              dataKey="x"
              name={axisLabels.x}
              tick={axisStyle}
              tickLine={false}
              axisLine={false}
              label={{ value: axisLabels.x, position: 'insideBottom', offset: -8, fill: '#64748b', fontSize: 11 }}
            />
            <YAxis
              type="number"
              dataKey="y"
              name={axisLabels.y}
              tick={axisStyle}
              tickLine={false}
              axisLine={false}
            />
            <ZAxis range={[42, 42]} />
            <Tooltip contentStyle={tooltipStyle} cursor={{ strokeDasharray: '3 3', stroke: '#334155' }} />
            <Legend
              verticalAlign="bottom"
              wrapperStyle={{ fontSize: 11, color: '#94a3b8', paddingTop: 12 }}
            />
            {series
              .filter(({ cluster }) => !hidden.includes(cluster.cluster_id))
              .map(({ cluster, points }) => (
                <Scatter
                  key={cluster.cluster_id}
                  name={cluster.name}
                  data={points}
                  fill={cluster.color}
                  fillOpacity={0.85}
                />
              ))}
          </ScatterChart>
        </ResponsiveContainer>
      </div>

      <footer className="flex flex-wrap gap-2 border-t border-surface-800 px-5 py-4">
        {clusters.map((cluster) => {
          const isHidden = hidden.includes(cluster.cluster_id);
          return (
            <button
              key={cluster.cluster_id}
              type="button"
              onClick={() => toggle(cluster.cluster_id)}
              aria-pressed={!isHidden}
              className={[
                'chip transition',
                isHidden ? 'opacity-40' : 'hover:border-surface-600',
              ].join(' ')}
            >
              <span
                className="h-2 w-2 rounded-full"
                style={{ backgroundColor: cluster.color }}
                aria-hidden="true"
              />
              {cluster.name} · {cluster.count}
            </button>
          );
        })}
      </footer>
    </section>
  );
}
