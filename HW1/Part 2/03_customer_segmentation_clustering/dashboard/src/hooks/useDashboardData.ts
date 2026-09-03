import { useEffect, useState } from 'react';
import { defaultAutoresearchOutput, defaultPipelineOutput } from '../data/defaultData';
import type { AutoresearchOutput, DashboardData, PipelineOutput } from '../types';

const PIPELINE_URL = 'data/pipeline_output.json';
const AUTORESEARCH_URL = 'data/autoresearch_output.json';

/** Minimal structural check so a truncated or foreign JSON never reaches the charts. */
const isPipelinePayload = (value: unknown): value is PipelineOutput => {
  if (!value || typeof value !== 'object') return false;
  const candidate = value as Partial<PipelineOutput>;
  return (
    Array.isArray(candidate.customers) &&
    candidate.customers.length > 0 &&
    Array.isArray(candidate.clusters) &&
    candidate.clusters.length > 0 &&
    typeof candidate.kpis === 'object' &&
    candidate.kpis !== null
  );
};

const isAutoresearchPayload = (value: unknown): value is AutoresearchOutput => {
  if (!value || typeof value !== 'object') return false;
  const candidate = value as Partial<AutoresearchOutput>;
  return Array.isArray(candidate.iterations) && typeof candidate.benchmark_paper === 'object';
};

async function fetchJson(url: string): Promise<unknown> {
  if (typeof fetch !== 'function') throw new Error('fetch unavailable');
  const response = await fetch(url, { cache: 'no-store' });
  if (!response.ok) throw new Error(`${url} responded ${response.status}`);
  return response.json();
}

/**
 * Loads the pipeline and autoresearch artifacts written by the Python pipeline,
 * falling back to the bundled snapshot whenever they are unreachable or malformed.
 */
export function useDashboardData(): DashboardData {
  const [state, setState] = useState<DashboardData>({
    pipeline: defaultPipelineOutput,
    autoresearch: defaultAutoresearchOutput,
    usingFallback: true,
    loading: true,
    error: null,
  });

  useEffect(() => {
    let cancelled = false;

    (async () => {
      let pipeline: PipelineOutput = defaultPipelineOutput;
      let autoresearch: AutoresearchOutput | null = defaultAutoresearchOutput;
      let usingFallback = true;
      let error: string | null = null;

      try {
        const raw = await fetchJson(PIPELINE_URL);
        if (isPipelinePayload(raw)) {
          pipeline = raw;
          usingFallback = false;
        } else {
          error = 'Live pipeline_output.json failed validation — showing bundled snapshot.';
        }
      } catch (err) {
        error = `Could not load live pipeline artifacts (${
          err instanceof Error ? err.message : 'unknown error'
        }) — showing bundled snapshot.`;
      }

      try {
        const raw = await fetchJson(AUTORESEARCH_URL);
        if (isAutoresearchPayload(raw)) autoresearch = raw;
      } catch {
        /* autoresearch is optional: the bundled snapshot (or null) stands in */
      }

      if (!cancelled) {
        setState({ pipeline, autoresearch, usingFallback, loading: false, error });
      }
    })();

    return () => {
      cancelled = true;
    };
  }, []);

  return state;
}
