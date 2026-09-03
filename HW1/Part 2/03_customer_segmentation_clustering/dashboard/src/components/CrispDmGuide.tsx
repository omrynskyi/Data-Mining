import type { PipelineMetadata } from '../types';

interface CrispDmGuideProps {
  metadata: PipelineMetadata;
  featureNames: string[];
}

interface Phase {
  index: number;
  name: string;
  summary: string;
  module: string;
  outputs: string[];
}

const PHASES: Phase[] = [
  {
    index: 1,
    name: 'Business understanding',
    summary:
      'Frame mall retail objectives: identify actionable customer segments to prioritise marketing spend and increase revenue per visitor.',
    module: 'PROJECT.md · src/config.py',
    outputs: ['Canonical persona anchors', 'Success metric: silhouette ≥ 0.50'],
  },
  {
    index: 2,
    name: 'Data understanding',
    summary:
      'Ingest and validate the 200-record Mall Customer dataset, profile distributions, detect IQR outliers and compute the correlation structure.',
    module: 'src/data_loader.py · src/data_understanding.py',
    outputs: ['dataset_summary', 'correlation_matrix', 'outlier report'],
  },
  {
    index: 3,
    name: 'Data preparation',
    summary:
      'Encode gender, select the active feature subset and apply the configured scaler so distance-based algorithms operate on comparable units.',
    module: 'src/data_preparation.py',
    outputs: ['scaler.joblib', 'scaled feature matrix'],
  },
  {
    index: 4,
    name: 'Modeling',
    summary:
      'Fit K-Means (k-means++), Ward agglomerative clustering and DBSCAN, plus a PCA projection used by the 2D/3D visualisers.',
    module: 'src/models.py',
    outputs: ['kmeans_model.joblib', 'agglomerative_model.joblib', 'dbscan_model.joblib', 'pca_model.joblib'],
  },
  {
    index: 5,
    name: 'Evaluation',
    summary:
      'Score every candidate with silhouette, Davies-Bouldin, Calinski-Harabasz and inertia, sweep k ∈ [2, 10] and bind clusters to personas.',
    module: 'src/evaluation.py',
    outputs: ['metrics.json', 'k-sweep table', 'cluster profiles'],
  },
  {
    index: 6,
    name: 'Deployment',
    summary:
      'Serialise models and emit the JSON contracts this dashboard consumes; the autoresearch engine then hill-climbs toward the benchmark paper.',
    module: 'src/export.py · src/autoresearch.py',
    outputs: ['pipeline_output.json', 'autoresearch_output.json', 'optimization_log.md'],
  },
];

export default function CrispDmGuide({ metadata, featureNames }: CrispDmGuideProps) {
  return (
    <div className="space-y-6">
      <section className="panel px-5 py-4" aria-label="Pipeline run configuration">
        <h2 className="panel-title">Pipeline run configuration</h2>
        <dl className="mt-4 grid grid-cols-2 gap-4 text-sm md:grid-cols-4">
          {[
            ['Dataset', metadata.dataset_name],
            ['Records', String(metadata.total_records)],
            ['Feature set', metadata.feature_set],
            ['Scaler', metadata.scaler],
            ['Random state', String(metadata.random_state)],
            ['Pipeline version', metadata.pipeline_version],
            ['Current phase', metadata.crisp_dm_phase],
            ['Features', featureNames.join(', ')],
          ].map(([label, value]) => (
            <div key={label}>
              <dt className="text-[11px] uppercase tracking-wider text-slate-500">{label}</dt>
              <dd className="mt-1 text-slate-200">{value}</dd>
            </div>
          ))}
        </dl>
      </section>

      <section className="panel" aria-label="CRISP-DM phases">
        <header className="panel-header">
          <div>
            <h2 className="panel-title">CRISP-DM methodology</h2>
            <p className="panel-subtitle">How each phase maps onto the Python modules in this project</p>
          </div>
        </header>
        <ol className="divide-y divide-surface-800">
          {PHASES.map((phase) => (
            <li key={phase.index} className="flex gap-4 px-5 py-4">
              <span className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-full border border-accent/40 bg-accent/10 font-mono text-xs text-accent">
                {phase.index}
              </span>
              <div className="min-w-0">
                <h3 className="text-sm font-semibold text-slate-100">{phase.name}</h3>
                <p className="mt-1 text-sm leading-relaxed text-slate-400">{phase.summary}</p>
                <p className="mt-2 font-mono text-[11px] text-slate-500">{phase.module}</p>
                <div className="mt-2 flex flex-wrap gap-1.5">
                  {phase.outputs.map((output) => (
                    <span key={output} className="chip">
                      {output}
                    </span>
                  ))}
                </div>
              </div>
            </li>
          ))}
        </ol>
      </section>

      <section className="panel px-5 py-4" aria-label="Reproduction commands">
        <h2 className="panel-title">Reproduce this dashboard</h2>
        <pre className="mt-3 overflow-x-auto rounded-lg border border-surface-800 bg-surface-950/70 p-4 font-mono text-xs leading-relaxed text-slate-300">
{`# 1. CRISP-DM clustering pipeline -> artifacts/ + dashboard/public/data/
python run_pipeline.py --k 5 --features 2d --scaler standard

# 2. Autoresearch hill-climbing benchmark alignment -> optimization_log.md
python run_autoresearch.py --iterations 12

# 3. Dashboard production build & render tests
cd dashboard && npm run build && npm test`}
        </pre>
      </section>
    </div>
  );
}
