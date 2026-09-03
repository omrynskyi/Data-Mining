/**
 * Programmatic render tests for the React data science dashboard (Acceptance Criteria R2).
 *
 * Every top-level view is mounted and asserted on: KPI cards, the 2D Recharts scatter,
 * the 3D SVG projection, distribution charts, persona cards, the autoresearch lab and
 * the customer explorer table. Charts are asserted through the rendered Recharts roots
 * and marks, so a silently empty chart fails the suite.
 */

import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import App from '../App';
import AutoresearchLab from '../components/AutoresearchLab';
import ClusterVisualizer2D from '../components/ClusterVisualizer2D';
import ClusterVisualizer3D from '../components/ClusterVisualizer3D';
import CrispDmGuide from '../components/CrispDmGuide';
import CustomerTable from '../components/CustomerTable';
import DistributionsChart from '../components/DistributionsChart';
import KpiCards from '../components/KpiCards';
import PersonaCards from '../components/PersonaCards';
import { defaultAutoresearchOutput, defaultPipelineOutput } from '../data/defaultData';

const pipeline = defaultPipelineOutput;
const autoresearch = defaultAutoresearchOutput;

/**
 * Counts the chart roots Recharts emits once a chart has actually painted.
 * `.recharts-wrapper` is one per chart (legend icons also carry `.recharts-surface`).
 */
const chartSurfaces = (container: HTMLElement): number =>
  container.querySelectorAll('.recharts-wrapper').length;

const mockFetchFailure = () => {
  vi.stubGlobal(
    'fetch',
    vi.fn(() => Promise.reject(new Error('network disabled in tests'))),
  );
};

const mockFetchSuccess = () => {
  vi.stubGlobal(
    'fetch',
    vi.fn((url: string) =>
      Promise.resolve({
        ok: true,
        status: 200,
        json: () =>
          Promise.resolve(String(url).includes('autoresearch') ? autoresearch : pipeline),
      }),
    ),
  );
};

describe('bundled data contract', () => {
  it('exposes a complete pipeline snapshot', () => {
    expect(pipeline.customers.length).toBe(pipeline.dataset_summary.total_customers);
    expect(pipeline.clusters.length).toBeGreaterThanOrEqual(2);
    expect(pipeline.model_comparisons.length).toBeGreaterThanOrEqual(3);
    expect(pipeline.diagnostics.silhouette_curve.length).toBeGreaterThan(0);
  });

  it('keeps cluster counts consistent with the customer list', () => {
    const clusterTotal = pipeline.clusters.reduce((sum, cluster) => sum + cluster.count, 0);
    expect(clusterTotal).toBe(pipeline.customers.length);
  });

  it('reports metrics inside their valid mathematical ranges', () => {
    expect(pipeline.kpis.silhouette_score).toBeGreaterThan(-1);
    expect(pipeline.kpis.silhouette_score).toBeLessThanOrEqual(1);
    expect(pipeline.kpis.davies_bouldin_index).toBeGreaterThanOrEqual(0);
    expect(pipeline.kpis.calinski_harabasz_score).toBeGreaterThanOrEqual(0);
  });
});

describe('App shell', () => {
  beforeEach(() => {
    mockFetchFailure();
  });

  it('renders the navigation with every dashboard section', async () => {
    render(<App />);

    const nav = await screen.findByRole('navigation', { name: /dashboard sections/i });
    for (const label of [
      'Overview',
      'Segments',
      'Distributions',
      'Personas',
      'Autoresearch Lab',
      'Customer Explorer',
      'CRISP-DM',
    ]) {
      expect(within(nav).getByRole('button', { name: new RegExp(label, 'i') })).toBeInTheDocument();
    }
  });

  it('mounts the overview KPIs and charts by default', async () => {
    const { container } = render(<App />);

    expect(await screen.findByTestId('kpi-silhouette')).toBeInTheDocument();
    expect(screen.getByTestId('kpi-customers')).toHaveTextContent(
      String(pipeline.dataset_summary.total_customers),
    );
    await waitFor(() => expect(chartSurfaces(container)).toBeGreaterThanOrEqual(2));
  });

  it('falls back to the bundled snapshot and surfaces a status message when artifacts are unreachable', async () => {
    render(<App />);

    const status = await screen.findByRole('status');
    expect(status).toHaveTextContent(/bundled snapshot/i);
  });

  it('navigates between views', async () => {
    const user = userEvent.setup();
    render(<App />);

    const nav = await screen.findByRole('navigation', { name: /dashboard sections/i });

    await user.click(within(nav).getByRole('button', { name: /personas/i }));
    expect(await screen.findByTestId(`persona-card-${pipeline.clusters[0].cluster_id}`)).toBeInTheDocument();

    await user.click(within(nav).getByRole('button', { name: /customer explorer/i }));
    expect(await screen.findByRole('region', { name: /customer explorer/i })).toBeInTheDocument();

    await user.click(within(nav).getByRole('button', { name: /crisp-dm/i }));
    expect(await screen.findByText(/pipeline run configuration/i)).toBeInTheDocument();
  });

  it('renders both cluster visualisers on the segments view', async () => {
    const user = userEvent.setup();
    const { container } = render(<App />);

    const nav = await screen.findByRole('navigation', { name: /dashboard sections/i });
    await user.click(within(nav).getByRole('button', { name: /segments/i }));

    expect(await screen.findByTestId('cluster-3d-canvas')).toBeInTheDocument();
    await waitFor(() => expect(chartSurfaces(container)).toBeGreaterThanOrEqual(1));
  });
});

describe('App with live artifacts', () => {
  beforeEach(() => {
    mockFetchSuccess();
  });

  it('consumes the fetched pipeline artifacts and reports live status', async () => {
    render(<App />);

    const nav = await screen.findByRole('navigation', { name: /dashboard sections/i });
    await waitFor(() =>
      expect(within(nav).getByText(/live pipeline artifacts/i)).toBeInTheDocument(),
    );
    expect(screen.queryByRole('status')).not.toBeInTheDocument();
  });
});

describe('KpiCards', () => {
  it('renders all five executive metrics and two charts', async () => {
    const { container } = render(
      <KpiCards
        kpis={pipeline.kpis}
        executive={pipeline.executive_kpis}
        clusters={pipeline.clusters}
        diagnostics={pipeline.diagnostics}
      />,
    );

    for (const key of ['customers', 'silhouette', 'davies', 'calinski', 'optimal-k']) {
      expect(screen.getByTestId(`kpi-${key}`)).toBeInTheDocument();
    }
    expect(screen.getByTestId('kpi-silhouette')).toHaveTextContent(
      pipeline.kpis.silhouette_score.toFixed(4),
    );
    await waitFor(() => expect(chartSurfaces(container)).toBe(2));
  });
});

describe('ClusterVisualizer2D', () => {
  it('renders a scatter point for every customer and switches projection', async () => {
    const user = userEvent.setup();
    const { container } = render(
      <ClusterVisualizer2D customers={pipeline.customers} clusters={pipeline.clusters} />,
    );

    await waitFor(() => expect(chartSurfaces(container)).toBe(1));
    await waitFor(() =>
      expect(container.querySelectorAll('.recharts-scatter-symbol').length).toBe(
        pipeline.customers.length,
      ),
    );

    const pcaButton = screen.getByRole('button', { name: /pca space/i });
    await user.click(pcaButton);
    expect(pcaButton).toHaveAttribute('aria-pressed', 'true');
    expect(screen.getAllByText(/principal component 1/i).length).toBeGreaterThan(0);
  });

  it('hides a segment when its legend chip is toggled off', async () => {
    const user = userEvent.setup();
    const first = pipeline.clusters[0];
    const { container } = render(
      <ClusterVisualizer2D customers={pipeline.customers} clusters={pipeline.clusters} />,
    );

    await waitFor(() =>
      expect(container.querySelectorAll('.recharts-scatter-symbol').length).toBe(
        pipeline.customers.length,
      ),
    );

    await user.click(screen.getByRole('button', { name: new RegExp(`${first.name} · ${first.count}`) }));

    await waitFor(() =>
      expect(container.querySelectorAll('.recharts-scatter-symbol').length).toBe(
        pipeline.customers.length - first.count,
      ),
    );
  });
});

describe('ClusterVisualizer3D', () => {
  it('projects every customer into the SVG scene', () => {
    render(<ClusterVisualizer3D customers={pipeline.customers} clusters={pipeline.clusters} />);

    const canvas = screen.getByTestId('cluster-3d-canvas');
    expect(canvas.querySelectorAll('circle').length).toBe(pipeline.customers.length);
    expect(screen.getByLabelText(/rotate horizontally/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/rotate vertically/i)).toBeInTheDocument();
  });

  it('re-projects the scene when the yaw control changes', async () => {
    render(<ClusterVisualizer3D customers={pipeline.customers} clusters={pipeline.clusters} />);

    const canvas = screen.getByTestId('cluster-3d-canvas');
    const before = canvas.querySelector('circle')?.getAttribute('cx');

    const yaw = screen.getByLabelText(/rotate horizontally/i) as HTMLInputElement;
    fireEvent.change(yaw, { target: { value: '-90' } });

    await waitFor(() => {
      const after = screen.getByTestId('cluster-3d-canvas').querySelector('circle')?.getAttribute('cx');
      expect(after).not.toBe(before);
    });
  });
});

describe('DistributionsChart', () => {
  it('renders quartile, gender and correlation views', async () => {
    const { container } = render(
      <DistributionsChart
        distributions={pipeline.distributions}
        clusters={pipeline.clusters}
        summary={pipeline.dataset_summary}
        correlation={pipeline.correlation_matrix}
      />,
    );

    await waitFor(() => expect(chartSurfaces(container)).toBe(3));
    expect(screen.getByRole('region', { name: /feature correlation matrix/i })).toBeInTheDocument();
    expect(screen.getByText(/overall/i)).toBeInTheDocument();
  });

  it('switches the active feature', async () => {
    const user = userEvent.setup();
    render(
      <DistributionsChart
        distributions={pipeline.distributions}
        clusters={pipeline.clusters}
        summary={pipeline.dataset_summary}
        correlation={pipeline.correlation_matrix}
      />,
    );

    const incomeButton = screen.getByRole('button', { name: /annual income/i });
    await user.click(incomeButton);
    expect(incomeButton).toHaveAttribute('aria-pressed', 'true');
  });
});

describe('PersonaCards', () => {
  it('renders one card per cluster with its business recommendation', () => {
    render(
      <PersonaCards
        clusters={pipeline.clusters}
        totalCustomers={pipeline.dataset_summary.total_customers}
      />,
    );

    for (const cluster of pipeline.clusters) {
      const card = screen.getByTestId(`persona-card-${cluster.cluster_id}`);
      expect(card).toHaveTextContent(cluster.name);
      expect(card).toHaveTextContent(cluster.business_recommendation.slice(0, 32));
    }
  });
});

describe('AutoresearchLab', () => {
  it('cites the benchmark paper and logs the hill-climbing iterations', async () => {
    if (!autoresearch) throw new Error('autoresearch snapshot missing');
    const { container } = render(
      <AutoresearchLab autoresearch={autoresearch} modelComparisons={pipeline.model_comparisons} />,
    );

    expect(screen.getByText(autoresearch.benchmark_paper.title)).toBeInTheDocument();
    expect(screen.getByText(autoresearch.benchmark_paper.authors.join(', '))).toBeInTheDocument();
    expect(
      screen.getByText(new RegExp(String(autoresearch.benchmark_paper.year) + '$')),
    ).toBeInTheDocument();
    expect(screen.getByText(`${autoresearch.iterations.length} logged steps`)).toBeInTheDocument();
    await waitFor(() => expect(chartSurfaces(container)).toBe(1));
  });

  it('renders the algorithm comparison table', () => {
    render(
      <AutoresearchLab autoresearch={autoresearch} modelComparisons={pipeline.model_comparisons} />,
    );

    const table = screen.getByRole('region', { name: /model comparison/i });
    for (const model of pipeline.model_comparisons) {
      expect(within(table).getAllByText(new RegExp(model.algorithm, 'i')).length).toBeGreaterThan(0);
    }
  });

  it('degrades gracefully when no autoresearch run exists', () => {
    render(<AutoresearchLab autoresearch={null} modelComparisons={pipeline.model_comparisons} />);
    expect(screen.getByText(/no autoresearch run found/i)).toBeInTheDocument();
    expect(screen.getByRole('region', { name: /model comparison/i })).toBeInTheDocument();
  });
});

describe('CustomerTable', () => {
  it('paginates, filters and sorts the customer records', async () => {
    const user = userEvent.setup();
    render(<CustomerTable customers={pipeline.customers} clusters={pipeline.clusters} />);

    expect(screen.getByText(`${pipeline.customers.length} of ${pipeline.customers.length} records`))
      .toBeInTheDocument();
    expect(screen.getAllByRole('row').length).toBe(26); // header + 25 rows

    await user.click(screen.getByRole('button', { name: /next/i }));
    expect(screen.getByText(/page 2 of/i)).toBeInTheDocument();

    const target = pipeline.clusters[0];
    await user.selectOptions(screen.getByLabelText(/filter by segment/i), String(target.cluster_id));
    expect(
      screen.getByText(`${target.count} of ${pipeline.customers.length} records`),
    ).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: /^age/i }));
    const firstAge = screen.getAllByRole('row')[1].querySelectorAll('td')[2].textContent;
    await user.click(screen.getByRole('button', { name: /^age/i }));
    const reversedAge = screen.getAllByRole('row')[1].querySelectorAll('td')[2].textContent;
    expect(Number(reversedAge)).toBeGreaterThanOrEqual(Number(firstAge));
  });

  it('shows an empty state when the search matches nothing', async () => {
    const user = userEvent.setup();
    render(<CustomerTable customers={pipeline.customers} clusters={pipeline.clusters} />);

    await user.type(screen.getByLabelText(/search customers/i), 'zzzzz-no-match');
    expect(screen.getByText(/no customers match the current filters/i)).toBeInTheDocument();
  });
});

describe('CrispDmGuide', () => {
  it('documents all six CRISP-DM phases and the run configuration', () => {
    render(
      <CrispDmGuide
        metadata={pipeline.metadata}
        featureNames={pipeline.dataset_summary.features}
      />,
    );

    for (const phase of [
      'Business understanding',
      'Data understanding',
      'Data preparation',
      'Modeling',
      'Evaluation',
      'Deployment',
    ]) {
      expect(screen.getByText(phase)).toBeInTheDocument();
    }
    expect(screen.getByText(pipeline.metadata.pipeline_version)).toBeInTheDocument();
  });
});
