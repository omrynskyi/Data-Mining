/**
 * TypeScript contracts for the artifacts produced by the Python CRISP-DM pipeline
 * (`run_pipeline.py` -> pipeline_output.json) and the autoresearch engine
 * (`run_autoresearch.py` -> autoresearch_output.json).
 */

export interface FeatureStats {
  mean: number;
  min: number;
  max: number;
  std: number;
  median?: number;
  q1?: number;
  q3?: number;
}

export interface Quartiles {
  min: number;
  q1: number;
  median: number;
  q3: number;
  max: number;
  mean: number;
  std: number;
}

export interface DatasetSummary {
  total_customers: number;
  features: string[];
  age_stats: FeatureStats;
  income_stats: FeatureStats;
  spending_stats: FeatureStats;
  gender_counts: { Male: number; Female: number };
  female_ratio?: number;
}

export interface Kpis {
  optimal_k: number;
  silhouette_score: number;
  davies_bouldin_index: number;
  calinski_harabasz_score: number;
  inertia: number | null;
  best_algorithm: string;
}

export interface ExecutiveKpis {
  total_customers: number;
  optimal_k: number;
  best_model_name: string;
  silhouette_score: number;
  davies_bouldin_index: number;
  calinski_harabasz_index: number;
  mean_income_k: number;
  mean_spending_score: number;
  female_ratio: number;
}

export interface Customer {
  customer_id: number;
  gender: 'Male' | 'Female';
  age: number;
  annual_income: number;
  annual_income_k?: number;
  spending_score: number;
  cluster_id: number;
  cluster_name: string;
  persona_name?: string;
  pca_x: number;
  pca_y: number;
  pca_z?: number;
  distance_to_centroid?: number;
}

export interface PersonaDetails {
  title: string;
  subtitle: string;
  description: string;
  demographic_summary: string;
  behavioral_traits: string[];
  recommended_strategies: string[];
  marketing_channels: string[];
  priority_tier: string;
  spending_power: string;
}

export interface ClusterProfile {
  cluster_id: number;
  name: string;
  persona: string;
  color: string;
  count: number;
  percentage: number;
  avg_age: number;
  avg_income: number;
  avg_spending: number;
  male_count?: number;
  female_count?: number;
  female_percentage?: number;
  gender_distribution: { Male: number; Female: number };
  centroid?: { age: number; annual_income: number; spending_score: number };
  business_recommendation: string;
  key_traits: string[];
  persona_details?: PersonaDetails;
}

export interface ModelComparison {
  algorithm: string;
  k?: number;
  silhouette_score: number;
  davies_bouldin_index: number;
  calinski_harabasz_score: number;
  inertia?: number | null;
  noise_points?: number;
  description: string;
  is_benchmark?: boolean;
}

export interface CurvePoint {
  k: number;
  value: number;
}

export interface Diagnostics {
  elbow_curve: CurvePoint[];
  silhouette_curve: CurvePoint[];
}

export interface FeatureDistribution {
  feature_name: string;
  by_cluster: Record<string, Quartiles>;
  overall: Quartiles;
}

export interface CorrelationMatrix {
  features: string[];
  matrix: number[][];
}

export interface PipelineMetadata {
  generated_at: string;
  dataset_name: string;
  total_records: number;
  crisp_dm_phase: string;
  pipeline_version: string;
  random_state: number;
  feature_set: string;
  scaler: string;
}

export interface PipelineOutput {
  timestamp: string;
  metadata: PipelineMetadata;
  dataset_summary: DatasetSummary;
  kpis: Kpis;
  executive_kpis: ExecutiveKpis;
  clusters: ClusterProfile[];
  customers: Customer[];
  model_comparisons: ModelComparison[];
  diagnostics: Diagnostics;
  distributions: FeatureDistribution[];
  correlation_matrix: CorrelationMatrix;
}

/* ------------------------------------------------------------------ */
/* Autoresearch contracts                                              */
/* ------------------------------------------------------------------ */

export interface PaperCitation {
  title: string;
  authors: string[];
  journal_or_conference: string;
  year: number;
  doi_or_url?: string;
  reported_dataset: string;
  reported_metrics: {
    algorithm: string;
    k: number;
    features_used: string[];
    silhouette_score: number;
    davies_bouldin_index?: number;
    calinski_harabasz_index?: number;
  };
  supporting_references?: string[];
}

export interface HillClimbingIteration {
  iteration: number;
  step_type: string;
  description: string;
  mutated_parameter: string;
  previous_value: string | number | null;
  candidate_value: string | number | null;
  algorithm: string;
  feature_space: string;
  scaler: string;
  parameters: string;
  n_clusters: number;
  candidate_silhouette: number;
  candidate_davies_bouldin: number;
  candidate_calinski_harabasz: number;
  noise_points: number;
  objective_score: number;
  delta_silhouette: number;
  delta_objective: number;
  accepted: boolean;
  decision: string;
  notes?: string;
  timestamp: string;
}

export interface ConfigMetrics {
  algorithm: string;
  k: number;
  features: string[];
  feature_space: string;
  scaler: string;
  hyperparameters: Record<string, string | number>;
  silhouette_score: number;
  davies_bouldin_index: number;
  calinski_harabasz_index: number;
  inertia?: number | null;
  noise_points?: number;
  objective_score: number;
}

export interface BenchmarkAlignment {
  paper_silhouette_target: number;
  paper_k_target: number;
  paper_davies_bouldin_target: number;
  achieved_silhouette: number;
  achieved_k: number;
  silhouette_gap_vs_paper: number;
  relative_to_paper_pct: number;
  k_matches_paper: boolean;
  paper_target_reached: boolean;
}

export interface AutoresearchMetadata {
  executed_at: string;
  total_iterations: number;
  total_states_evaluated: number;
  logged_steps: number;
  accepted_steps: number;
  optimizer_type: string;
  search_strategy: string;
  optimization_objective: string;
  random_state: number;
  step_size: number;
  iteration_budget: number;
  converged: boolean;
  termination_reason: string;
}

export interface TrajectoryPoint {
  iteration: number;
  config: {
    algorithm: string;
    feature_space_label: string;
    scaler: string;
    hyperparameters: Record<string, string | number>;
  };
  silhouette_score: number;
  davies_bouldin_index: number;
  objective_score: number;
}

export interface AutoresearchOutput {
  metadata: AutoresearchMetadata;
  benchmark_paper: PaperCitation;
  baseline_metrics: ConfigMetrics;
  optimized_metrics: ConfigMetrics;
  final_metrics: ConfigMetrics;
  improvement_summary: {
    silhouette_gain: number;
    percentage_improvement: number;
    davies_bouldin_delta: number;
    calinski_harabasz_delta: number;
    paper_target_reached: boolean;
    accepted_steps: number;
  };
  benchmark_alignment: BenchmarkAlignment;
  trajectory: TrajectoryPoint[];
  iterations: HillClimbingIteration[];
}

export type ViewId =
  | 'overview'
  | 'segments'
  | 'distributions'
  | 'personas'
  | 'autoresearch'
  | 'explorer'
  | 'methodology';

export interface DashboardData {
  pipeline: PipelineOutput;
  autoresearch: AutoresearchOutput | null;
  /** True when the live artifacts could not be fetched and the bundled snapshot is in use. */
  usingFallback: boolean;
  loading: boolean;
  error: string | null;
}
