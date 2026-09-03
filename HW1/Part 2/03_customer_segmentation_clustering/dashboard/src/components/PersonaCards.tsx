import { Megaphone, Target, TrendingUp, Users } from 'lucide-react';
import type { ClusterProfile } from '../types';
import { formatCurrencyK, formatNumber, formatPercent, hexToRgba } from '../lib/format';

interface PersonaCardsProps {
  clusters: ClusterProfile[];
  totalCustomers: number;
}

export default function PersonaCards({ clusters, totalCustomers }: PersonaCardsProps) {
  return (
    <div className="space-y-6">
      <section className="panel px-5 py-4" aria-label="Persona summary">
        <h2 className="panel-title">Segment personas &amp; activation plan</h2>
        <p className="panel-subtitle">
          {clusters.length} personas derived from {totalCustomers} customer records. Cluster centroids are
          matched to canonical mall-retail archetypes via Hungarian assignment on the income/spending plane.
        </p>
      </section>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2 2xl:grid-cols-3">
        {clusters.map((cluster) => {
          const details = cluster.persona_details;
          return (
            <article
              key={cluster.cluster_id}
              className="panel flex flex-col overflow-hidden"
              data-testid={`persona-card-${cluster.cluster_id}`}
            >
              <div
                className="border-b border-surface-800 px-5 py-4"
                style={{ background: `linear-gradient(135deg, ${hexToRgba(cluster.color, 0.18)}, transparent 70%)` }}
              >
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <p className="text-[11px] font-semibold uppercase tracking-widest text-slate-500">
                      Cluster {cluster.cluster_id}
                    </p>
                    <h3 className="mt-1 text-lg font-semibold text-slate-50">
                      {details?.title ?? cluster.name}
                    </h3>
                    <p className="text-xs text-slate-400">{cluster.name}</p>
                  </div>
                  <span
                    className="mt-1 h-3 w-3 shrink-0 rounded-full ring-4"
                    style={{
                      backgroundColor: cluster.color,
                      boxShadow: `0 0 0 4px ${hexToRgba(cluster.color, 0.15)}`,
                    }}
                    aria-hidden="true"
                  />
                </div>

                <div className="mt-3 flex flex-wrap gap-2">
                  <span className="chip">
                    <Users className="h-3 w-3" aria-hidden="true" />
                    {cluster.count} customers ({formatPercent(cluster.percentage)})
                  </span>
                  {details ? <span className="chip">{details.priority_tier}</span> : null}
                  {details ? (
                    <span className="chip">
                      <TrendingUp className="h-3 w-3" aria-hidden="true" />
                      {details.spending_power} spend power
                    </span>
                  ) : null}
                </div>
              </div>

              <div className="grid grid-cols-3 gap-px border-b border-surface-800 bg-surface-800">
                {[
                  { label: 'Avg age', value: formatNumber(cluster.avg_age, 1) },
                  { label: 'Avg income', value: formatCurrencyK(cluster.avg_income) },
                  { label: 'Avg spend', value: formatNumber(cluster.avg_spending, 1) },
                ].map((stat) => (
                  <div key={stat.label} className="bg-surface-900 px-4 py-3">
                    <p className="text-[10px] uppercase tracking-wider text-slate-500">{stat.label}</p>
                    <p className="mt-1 font-mono text-base text-slate-100">{stat.value}</p>
                  </div>
                ))}
              </div>

              <div className="flex flex-1 flex-col gap-4 px-5 py-4">
                {details ? (
                  <p className="text-sm leading-relaxed text-slate-400">{details.description}</p>
                ) : null}

                <div>
                  <p className="mb-2 flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-wider text-slate-500">
                    <Target className="h-3 w-3" aria-hidden="true" />
                    Key traits
                  </p>
                  <div className="flex flex-wrap gap-1.5">
                    {cluster.key_traits.map((trait) => (
                      <span key={trait} className="chip">
                        {trait}
                      </span>
                    ))}
                  </div>
                </div>

                {details && details.recommended_strategies.length > 0 ? (
                  <div>
                    <p className="mb-2 text-[11px] font-semibold uppercase tracking-wider text-slate-500">
                      Recommended plays
                    </p>
                    <ul className="space-y-1.5 text-sm text-slate-400">
                      {details.recommended_strategies.map((strategy) => (
                        <li key={strategy} className="flex gap-2">
                          <span className="mt-1.5 h-1 w-1 shrink-0 rounded-full bg-accent" aria-hidden="true" />
                          {strategy}
                        </li>
                      ))}
                    </ul>
                  </div>
                ) : null}

                {details && details.marketing_channels.length > 0 ? (
                  <div>
                    <p className="mb-2 flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-wider text-slate-500">
                      <Megaphone className="h-3 w-3" aria-hidden="true" />
                      Channels
                    </p>
                    <div className="flex flex-wrap gap-1.5">
                      {details.marketing_channels.map((channel) => (
                        <span key={channel} className="chip">
                          {channel}
                        </span>
                      ))}
                    </div>
                  </div>
                ) : null}

                <p className="mt-auto rounded-lg border border-surface-800 bg-surface-950/60 px-3 py-2.5 text-xs leading-relaxed text-slate-400">
                  <span className="font-semibold text-slate-300">Recommendation · </span>
                  {cluster.business_recommendation}
                </p>
              </div>
            </article>
          );
        })}
      </div>
    </div>
  );
}
