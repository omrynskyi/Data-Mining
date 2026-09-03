import { useState } from 'react';
import {
  Bar,
  CartesianGrid,
  Cell,
  ComposedChart,
  Legend,
  Pie,
  PieChart,
  ResponsiveContainer,
  Scatter,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import type {
  ClusterProfile,
  CorrelationMatrix,
  DatasetSummary,
  FeatureDistribution,
} from '../types';
import { formatNumber } from '../lib/format';

interface DistributionsChartProps {
  distributions: FeatureDistribution[];
  clusters: ClusterProfile[];
  summary: DatasetSummary;
  correlation: CorrelationMatrix;
}

const FEATURE_LABELS: Record<string, string> = {
  age: 'Age (years)',
  annual_income_k: 'Annual income (k$)',
  spending_score: 'Spending score (1–100)',
};

const axisStyle = { stroke: '#475569', fontSize: 11 };

const tooltipStyle = {
  backgroundColor: '#0d1220',
  border: '1px solid #22304f',
  borderRadius: '0.5rem',
  fontSize: '12px',
  color: '#e2e8f0',
};

const correlationColor = (value: number): string => {
  const magnitude = Math.min(Math.abs(value), 1);
  const channel = value >= 0 ? '56, 189, 248' : '244, 114, 182';
  return `rgba(${channel}, ${0.12 + magnitude * 0.7})`;
};

export default function DistributionsChart({
  distributions,
  clusters,
  summary,
  correlation,
}: DistributionsChartProps) {
  const [activeFeature, setActiveFeature] = useState(distributions[0]?.feature_name ?? 'age');
  const distribution =
    distributions.find((item) => item.feature_name === activeFeature) ?? distributions[0];

  const boxData = distribution
    ? clusters.map((cluster) => {
        const stats = distribution.by_cluster[String(cluster.cluster_id)];
        return {
          name: cluster.persona,
          fullName: cluster.name,
          color: cluster.color,
          base: stats?.q1 ?? 0,
          box: stats ? Math.max(stats.q3 - stats.q1, 0.4) : 0,
          median: stats?.median ?? 0,
          min: stats?.min ?? 0,
          max: stats?.max ?? 0,
          mean: stats?.mean ?? 0,
        };
      })
    : [];

  const genderData = [
    { name: 'Female', value: summary.gender_counts.Female, fill: '#f472b6' },
    { name: 'Male', value: summary.gender_counts.Male, fill: '#38bdf8' },
  ];

  const genderByCluster = clusters.map((cluster) => ({
    name: cluster.persona,
    Female: cluster.gender_distribution.Female,
    Male: cluster.gender_distribution.Male,
  }));

  return (
    <div className="space-y-6">
      <section className="panel" aria-label="Feature distribution by cluster">
        <header className="panel-header">
          <div>
            <h2 className="panel-title">Feature distribution by segment</h2>
            <p className="panel-subtitle">
              Interquartile range (Q1–Q3) with median marker · {FEATURE_LABELS[activeFeature] ?? activeFeature}
            </p>
          </div>
          <div className="flex shrink-0 flex-wrap gap-1 rounded-lg border border-surface-700 bg-surface-850 p-0.5">
            {distributions.map((item) => (
              <button
                key={item.feature_name}
                type="button"
                onClick={() => setActiveFeature(item.feature_name)}
                aria-pressed={activeFeature === item.feature_name}
                className={[
                  'rounded-md px-3 py-1.5 text-xs font-medium transition',
                  activeFeature === item.feature_name
                    ? 'bg-accent/20 text-accent'
                    : 'text-slate-400 hover:text-slate-200',
                ].join(' ')}
              >
                {FEATURE_LABELS[item.feature_name] ?? item.feature_name}
              </button>
            ))}
          </div>
        </header>

        <div className="h-80 p-4">
          <ResponsiveContainer width="100%" height="100%">
            <ComposedChart data={boxData} margin={{ top: 12, right: 16, bottom: 8, left: -18 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" vertical={false} />
              <XAxis dataKey="name" tick={axisStyle} tickLine={false} axisLine={false} />
              <YAxis tick={axisStyle} tickLine={false} axisLine={false} />
              <Tooltip contentStyle={tooltipStyle} cursor={{ fill: 'rgba(56,189,248,0.06)' }} />
              <Bar dataKey="base" stackId="box" fill="transparent" isAnimationActive={false} />
              <Bar dataKey="box" stackId="box" name="Q1–Q3" radius={[3, 3, 0, 0]} isAnimationActive={false}>
                {boxData.map((entry) => (
                  <Cell key={entry.fullName} fill={entry.color} fillOpacity={0.65} />
                ))}
              </Bar>
              <Scatter dataKey="median" name="Median" fill="#f8fafc" shape="cross" />
            </ComposedChart>
          </ResponsiveContainer>
        </div>

        {distribution ? (
          <div className="overflow-x-auto border-t border-surface-800">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Segment</th>
                  <th>Min</th>
                  <th>Q1</th>
                  <th>Median</th>
                  <th>Q3</th>
                  <th>Max</th>
                  <th>Mean</th>
                  <th>Std</th>
                </tr>
              </thead>
              <tbody>
                {clusters.map((cluster) => {
                  const stats = distribution.by_cluster[String(cluster.cluster_id)];
                  if (!stats) return null;
                  return (
                    <tr key={cluster.cluster_id}>
                      <td>
                        <span className="flex items-center gap-2">
                          <span
                            className="h-2 w-2 rounded-full"
                            style={{ backgroundColor: cluster.color }}
                            aria-hidden="true"
                          />
                          {cluster.name}
                        </span>
                      </td>
                      <td className="font-mono">{formatNumber(stats.min, 1)}</td>
                      <td className="font-mono">{formatNumber(stats.q1, 1)}</td>
                      <td className="font-mono">{formatNumber(stats.median, 1)}</td>
                      <td className="font-mono">{formatNumber(stats.q3, 1)}</td>
                      <td className="font-mono">{formatNumber(stats.max, 1)}</td>
                      <td className="font-mono">{formatNumber(stats.mean, 1)}</td>
                      <td className="font-mono">{formatNumber(stats.std, 1)}</td>
                    </tr>
                  );
                })}
                <tr className="bg-surface-850/60">
                  <td className="font-semibold text-slate-200">Overall</td>
                  <td className="font-mono">{formatNumber(distribution.overall.min, 1)}</td>
                  <td className="font-mono">{formatNumber(distribution.overall.q1, 1)}</td>
                  <td className="font-mono">{formatNumber(distribution.overall.median, 1)}</td>
                  <td className="font-mono">{formatNumber(distribution.overall.q3, 1)}</td>
                  <td className="font-mono">{formatNumber(distribution.overall.max, 1)}</td>
                  <td className="font-mono">{formatNumber(distribution.overall.mean, 1)}</td>
                  <td className="font-mono">{formatNumber(distribution.overall.std, 1)}</td>
                </tr>
              </tbody>
            </table>
          </div>
        ) : null}
      </section>

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-3">
        <section className="panel xl:col-span-1" aria-label="Gender split">
          <header className="panel-header">
            <div>
              <h2 className="panel-title">Gender split</h2>
              <p className="panel-subtitle">{summary.total_customers} customers</p>
            </div>
          </header>
          <div className="h-64 p-4">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={genderData}
                  dataKey="value"
                  nameKey="name"
                  innerRadius="55%"
                  outerRadius="80%"
                  paddingAngle={3}
                  stroke="none"
                >
                  {genderData.map((entry) => (
                    <Cell key={entry.name} fill={entry.fill} />
                  ))}
                </Pie>
                <Tooltip contentStyle={tooltipStyle} />
                <Legend wrapperStyle={{ fontSize: 11, color: '#94a3b8' }} />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </section>

        <section className="panel xl:col-span-2" aria-label="Gender composition per segment">
          <header className="panel-header">
            <div>
              <h2 className="panel-title">Gender composition per segment</h2>
              <p className="panel-subtitle">Absolute customer counts</p>
            </div>
          </header>
          <div className="h-64 p-4">
            <ResponsiveContainer width="100%" height="100%">
              <ComposedChart data={genderByCluster} margin={{ top: 12, right: 16, bottom: 8, left: -18 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" vertical={false} />
                <XAxis dataKey="name" tick={axisStyle} tickLine={false} axisLine={false} />
                <YAxis tick={axisStyle} tickLine={false} axisLine={false} />
                <Tooltip contentStyle={tooltipStyle} cursor={{ fill: 'rgba(56,189,248,0.06)' }} />
                <Legend wrapperStyle={{ fontSize: 11, color: '#94a3b8' }} />
                <Bar dataKey="Female" stackId="gender" fill="#f472b6" radius={[0, 0, 0, 0]} />
                <Bar dataKey="Male" stackId="gender" fill="#38bdf8" radius={[3, 3, 0, 0]} />
              </ComposedChart>
            </ResponsiveContainer>
          </div>
        </section>
      </div>

      <section className="panel" aria-label="Feature correlation matrix">
        <header className="panel-header">
          <div>
            <h2 className="panel-title">Feature correlation matrix</h2>
            <p className="panel-subtitle">Pearson correlation across numeric attributes</p>
          </div>
        </header>
        <div className="overflow-x-auto p-4">
          <table className="min-w-[28rem] border-collapse text-sm">
            <thead>
              <tr>
                <th className="px-3 py-2 text-left text-[11px] uppercase tracking-wider text-slate-500" />
                {correlation.features.map((feature) => (
                  <th
                    key={feature}
                    className="px-3 py-2 text-center text-[11px] uppercase tracking-wider text-slate-500"
                  >
                    {feature.replace(/_/g, ' ')}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {correlation.matrix.map((row, rowIndex) => (
                <tr key={correlation.features[rowIndex]}>
                  <th className="px-3 py-2 text-left text-[11px] uppercase tracking-wider text-slate-500">
                    {correlation.features[rowIndex]?.replace(/_/g, ' ')}
                  </th>
                  {row.map((value, columnIndex) => (
                    <td
                      key={`${rowIndex}-${columnIndex}`}
                      className="px-3 py-2 text-center font-mono text-xs text-slate-200"
                      style={{ backgroundColor: correlationColor(value) }}
                    >
                      {formatNumber(value, 3)}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
