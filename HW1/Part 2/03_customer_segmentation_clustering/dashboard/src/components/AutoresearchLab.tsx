import {
  CartesianGrid,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { BookMarked, CheckCircle2, CircleSlash, FlaskConical } from 'lucide-react';
import type { AutoresearchOutput, ModelComparison } from '../types';
import { formatNumber, formatPercent, formatScore, formatSigned } from '../lib/format';

interface AutoresearchLabProps {
  autoresearch: AutoresearchOutput | null;
  modelComparisons: ModelComparison[];
}

const axisStyle = { stroke: '#475569', fontSize: 11 };

const tooltipStyle = {
  backgroundColor: '#0d1220',
  border: '1px solid #22304f',
  borderRadius: '0.5rem',
  fontSize: '12px',
  color: '#e2e8f0',
};

function ModelComparisonTable({ comparisons }: { comparisons: ModelComparison[] }) {
  const best = comparisons.reduce<ModelComparison | null>(
    (winner, model) =>
      winner === null || model.silhouette_score > winner.silhouette_score ? model : winner,
    null,
  );

  return (
    <section className="panel" aria-label="Model comparison">
      <header className="panel-header">
        <div>
          <h2 className="panel-title">Algorithm comparison</h2>
          <p className="panel-subtitle">Internal validation metrics from the last pipeline run</p>
        </div>
      </header>
      <div className="overflow-x-auto">
        <table className="data-table">
          <thead>
            <tr>
              <th>Algorithm</th>
              <th>k</th>
              <th>Silhouette</th>
              <th>Davies-Bouldin</th>
              <th>Calinski-Harabasz</th>
              <th>Noise</th>
              <th>Notes</th>
            </tr>
          </thead>
          <tbody>
            {comparisons.map((model) => (
              <tr
                key={model.algorithm}
                className={model === best ? 'bg-emerald-500/5' : undefined}
              >
                <td className="font-medium text-slate-100">
                  {model.algorithm}
                  {model === best ? (
                    <span className="ml-2 text-[10px] uppercase tracking-wider text-emerald-400">best</span>
                  ) : null}
                </td>
                <td className="font-mono">{model.k ?? '—'}</td>
                <td className="font-mono text-slate-100">{formatScore(model.silhouette_score)}</td>
                <td className="font-mono">{formatNumber(model.davies_bouldin_index, 4)}</td>
                <td className="font-mono">{formatNumber(model.calinski_harabasz_score, 2)}</td>
                <td className="font-mono">{model.noise_points ?? 0}</td>
                <td className="max-w-md whitespace-normal text-xs text-slate-500">{model.description}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

export default function AutoresearchLab({ autoresearch, modelComparisons }: AutoresearchLabProps) {
  if (!autoresearch) {
    return (
      <div className="space-y-6">
        <section className="panel px-5 py-8 text-center" aria-label="Autoresearch unavailable">
          <FlaskConical className="mx-auto h-6 w-6 text-slate-600" aria-hidden="true" />
          <h2 className="mt-3 text-sm font-semibold text-slate-200">No autoresearch run found</h2>
          <p className="mt-1 text-xs text-slate-500">
            Execute <code className="font-mono text-slate-400">python run_autoresearch.py</code> to generate
            the hill-climbing optimization report.
          </p>
        </section>
        <ModelComparisonTable comparisons={modelComparisons} />
      </div>
    );
  }

  const { benchmark_paper: paper, baseline_metrics: baseline, optimized_metrics: optimized } = autoresearch;
  const alignment = autoresearch.benchmark_alignment;
  const summary = autoresearch.improvement_summary;
  const target = paper.reported_metrics;

  const trajectoryData = autoresearch.trajectory.map((point) => ({
    iteration: point.iteration,
    silhouette: point.silhouette_score,
    objective: point.objective_score,
  }));

  return (
    <div className="space-y-6">
      <section className="panel" aria-label="Benchmark paper">
        <header className="panel-header">
          <div>
            <h2 className="panel-title">Benchmark paper alignment</h2>
            <p className="panel-subtitle">
              {autoresearch.metadata.optimizer_type} · {autoresearch.metadata.search_strategy}
            </p>
          </div>
          <span
            className={[
              'chip',
              alignment.paper_target_reached
                ? 'border-emerald-500/40 text-emerald-300'
                : 'border-amber-500/40 text-amber-300',
            ].join(' ')}
          >
            {alignment.paper_target_reached ? (
              <CheckCircle2 className="h-3 w-3" aria-hidden="true" />
            ) : (
              <CircleSlash className="h-3 w-3" aria-hidden="true" />
            )}
            {alignment.paper_target_reached ? 'Benchmark reached' : 'Below benchmark'}
          </span>
        </header>

        <div className="grid gap-5 p-5 lg:grid-cols-3">
          <div className="lg:col-span-2">
            <p className="flex items-center gap-2 text-[11px] font-semibold uppercase tracking-wider text-slate-500">
              <BookMarked className="h-3 w-3" aria-hidden="true" />
              Citation
            </p>
            <blockquote className="mt-2 border-l-2 border-accent/60 pl-4">
              <p className="text-sm font-semibold text-slate-100">{paper.title}</p>
              <p className="mt-1 text-xs text-slate-400">{paper.authors.join(', ')}</p>
              <p className="mt-1 text-xs italic text-slate-500">
                {paper.journal_or_conference}, {paper.year}
              </p>
              {paper.doi_or_url ? (
                <a
                  href={paper.doi_or_url}
                  target="_blank"
                  rel="noreferrer"
                  className="mt-1 inline-block break-all text-xs text-accent hover:underline"
                >
                  {paper.doi_or_url}
                </a>
              ) : null}
            </blockquote>
            <p className="mt-3 text-xs text-slate-500">Dataset: {paper.reported_dataset}</p>
          </div>

          <dl className="space-y-2 rounded-lg border border-surface-800 bg-surface-950/50 p-4 text-xs">
            <div className="flex justify-between gap-3">
              <dt className="text-slate-500">Published silhouette</dt>
              <dd className="font-mono text-slate-200">{formatScore(target.silhouette_score)}</dd>
            </div>
            <div className="flex justify-between gap-3">
              <dt className="text-slate-500">Achieved silhouette</dt>
              <dd className="font-mono text-emerald-300">{formatScore(alignment.achieved_silhouette)}</dd>
            </div>
            <div className="flex justify-between gap-3">
              <dt className="text-slate-500">Gap vs paper</dt>
              <dd className="font-mono text-slate-200">{formatSigned(alignment.silhouette_gap_vs_paper)}</dd>
            </div>
            <div className="flex justify-between gap-3">
              <dt className="text-slate-500">Relative score</dt>
              <dd className="font-mono text-slate-200">{formatPercent(alignment.relative_to_paper_pct, 2)}</dd>
            </div>
            <div className="flex justify-between gap-3">
              <dt className="text-slate-500">Cluster count</dt>
              <dd className="font-mono text-slate-200">
                k={alignment.achieved_k} {alignment.k_matches_paper ? '(match)' : `(paper k=${alignment.paper_k_target})`}
              </dd>
            </div>
          </dl>
        </div>
      </section>

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-2">
        <section className="panel" aria-label="Baseline versus optimized configuration">
          <header className="panel-header">
            <div>
              <h2 className="panel-title">Baseline vs optimized</h2>
              <p className="panel-subtitle">
                {summary.accepted_steps} accepted moves · {autoresearch.metadata.total_states_evaluated} states
                evaluated
              </p>
            </div>
          </header>
          <div className="overflow-x-auto">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Quantity</th>
                  <th>Baseline</th>
                  <th>Optimized</th>
                  <th>Δ</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td>Algorithm</td>
                  <td>{baseline.algorithm}</td>
                  <td className="text-slate-100">{optimized.algorithm}</td>
                  <td>—</td>
                </tr>
                <tr>
                  <td>Feature space</td>
                  <td>{baseline.feature_space}</td>
                  <td className="text-slate-100">{optimized.feature_space}</td>
                  <td>—</td>
                </tr>
                <tr>
                  <td>Scaler</td>
                  <td>{baseline.scaler}</td>
                  <td className="text-slate-100">{optimized.scaler}</td>
                  <td>—</td>
                </tr>
                <tr>
                  <td>Clusters (k)</td>
                  <td className="font-mono">{baseline.k}</td>
                  <td className="font-mono text-slate-100">{optimized.k}</td>
                  <td className="font-mono">{optimized.k - baseline.k >= 0 ? '+' : ''}{optimized.k - baseline.k}</td>
                </tr>
                <tr>
                  <td>Silhouette</td>
                  <td className="font-mono">{formatScore(baseline.silhouette_score)}</td>
                  <td className="font-mono text-emerald-300">{formatScore(optimized.silhouette_score)}</td>
                  <td className="font-mono">
                    {formatSigned(summary.silhouette_gain)} ({formatPercent(summary.percentage_improvement, 2)})
                  </td>
                </tr>
                <tr>
                  <td>Davies-Bouldin</td>
                  <td className="font-mono">{formatNumber(baseline.davies_bouldin_index, 4)}</td>
                  <td className="font-mono text-slate-100">{formatNumber(optimized.davies_bouldin_index, 4)}</td>
                  <td className="font-mono">{formatSigned(summary.davies_bouldin_delta)}</td>
                </tr>
                <tr>
                  <td>Calinski-Harabasz</td>
                  <td className="font-mono">{formatNumber(baseline.calinski_harabasz_index, 2)}</td>
                  <td className="font-mono text-slate-100">{formatNumber(optimized.calinski_harabasz_index, 2)}</td>
                  <td className="font-mono">{formatSigned(summary.calinski_harabasz_delta, 2)}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </section>

        <section className="panel" aria-label="Hill climbing trajectory">
          <header className="panel-header">
            <div>
              <h2 className="panel-title">Hill-climbing trajectory</h2>
              <p className="panel-subtitle">Silhouette of the incumbent state after each accepted move</p>
            </div>
          </header>
          <div className="h-72 p-4">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={trajectoryData} margin={{ top: 8, right: 16, bottom: 8, left: -18 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                <XAxis
                  dataKey="iteration"
                  tick={axisStyle}
                  tickLine={false}
                  axisLine={false}
                  label={{ value: 'Iteration', position: 'insideBottom', offset: -6, fill: '#64748b', fontSize: 11 }}
                />
                <YAxis tick={axisStyle} tickLine={false} axisLine={false} domain={['auto', 'auto']} />
                <Tooltip contentStyle={tooltipStyle} />
                <ReferenceLine
                  y={target.silhouette_score}
                  stroke="#f59e0b"
                  strokeDasharray="5 4"
                  label={{
                    value: `paper ${formatScore(target.silhouette_score)}`,
                    fill: '#f59e0b',
                    fontSize: 10,
                    position: 'insideTopRight',
                  }}
                />
                <Line
                  type="monotone"
                  dataKey="silhouette"
                  name="Silhouette"
                  stroke="#38bdf8"
                  strokeWidth={2}
                  dot={{ r: 4, fill: '#38bdf8' }}
                />
                <Line
                  type="monotone"
                  dataKey="objective"
                  name="Objective f(θ)"
                  stroke="#a78bfa"
                  strokeWidth={1.5}
                  strokeDasharray="4 3"
                  dot={{ r: 2, fill: '#a78bfa' }}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </section>
      </div>

      <section className="panel" aria-label="Hill climbing iteration log">
        <header className="panel-header">
          <div>
            <h2 className="panel-title">Search iteration log</h2>
            <p className="panel-subtitle">{autoresearch.metadata.termination_reason}</p>
          </div>
          <span className="chip">{autoresearch.iterations.length} logged steps</span>
        </header>
        <div className="max-h-[28rem] overflow-auto">
          <table className="data-table">
            <thead>
              <tr>
                <th>Iter</th>
                <th>Step type</th>
                <th>Mutation</th>
                <th>Algorithm</th>
                <th>Features</th>
                <th>Scaler</th>
                <th>Params</th>
                <th>Silhouette</th>
                <th>ΔS</th>
                <th>Objective</th>
                <th>Decision</th>
              </tr>
            </thead>
            <tbody>
              {autoresearch.iterations.map((iteration, index) => (
                <tr
                  key={`${iteration.iteration}-${index}`}
                  className={iteration.accepted ? 'bg-emerald-500/5' : undefined}
                >
                  <td className="font-mono">{iteration.iteration}</td>
                  <td className="text-xs">{iteration.step_type}</td>
                  <td className="text-xs text-slate-400">
                    {iteration.mutated_parameter}
                    {iteration.previous_value !== null && iteration.candidate_value !== null
                      ? `: ${iteration.previous_value} → ${iteration.candidate_value}`
                      : ''}
                  </td>
                  <td>{iteration.algorithm}</td>
                  <td className="text-xs">{iteration.feature_space}</td>
                  <td className="text-xs">{iteration.scaler}</td>
                  <td className="font-mono text-xs">{iteration.parameters}</td>
                  <td className="font-mono text-slate-100">{formatScore(iteration.candidate_silhouette)}</td>
                  <td
                    className={[
                      'font-mono',
                      iteration.delta_silhouette > 0 ? 'text-emerald-400' : 'text-slate-500',
                    ].join(' ')}
                  >
                    {formatSigned(iteration.delta_silhouette)}
                  </td>
                  <td className="font-mono">{formatNumber(iteration.objective_score, 4)}</td>
                  <td className="text-xs">
                    <span
                      className={
                        iteration.accepted
                          ? 'text-emerald-400'
                          : iteration.decision.includes('Initial')
                            ? 'text-slate-300'
                            : 'text-slate-500'
                      }
                    >
                      {iteration.decision}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <ModelComparisonTable comparisons={modelComparisons} />
    </div>
  );
}
