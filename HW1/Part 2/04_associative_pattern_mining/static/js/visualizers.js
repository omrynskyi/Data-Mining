/* ============================================================================
   visualizers.js -- Vis.js network graph and Plotly chart renderers.

   Every renderer reads its colours from the live CSS custom properties rather
   than hard-coded hex, so a theme toggle repaints the charts consistently with
   the rest of the console instead of leaving dark plots on a light page.
   ========================================================================= */

const Viz = (() => {

  function cssVar(name, fallback) {
    const value = getComputedStyle(document.documentElement).getPropertyValue(name);
    return (value && value.trim()) || fallback;
  }

  function palette() {
    return {
      accent:  cssVar('--accent', '#4fd1c5'),
      accent2: cssVar('--accent-2', '#f6ad55'),
      accent3: cssVar('--accent-3', '#9f7aea'),
      danger:  cssVar('--danger', '#fc8181'),
      text:    cssVar('--text', '#e6ebf2'),
      dim:     cssVar('--text-dim', '#9aa7b8'),
      faint:   cssVar('--text-faint', '#64707f'),
      grid:    cssVar('--border', '#232a34'),
      surface: cssVar('--bg-sunken', '#0a0d11')
    };
  }

  /** Shared Plotly layout so every chart in the console reads as one system. */
  function baseLayout(overrides) {
    const c = palette();
    return Object.assign({
      paper_bgcolor: 'rgba(0,0,0,0)',
      plot_bgcolor: 'rgba(0,0,0,0)',
      font: { family: '"IBM Plex Sans", system-ui, sans-serif', size: 11, color: c.dim },
      margin: { l: 52, r: 18, t: 16, b: 44 },
      xaxis: { gridcolor: c.grid, zerolinecolor: c.grid, linecolor: c.grid, tickfont: { color: c.faint } },
      yaxis: { gridcolor: c.grid, zerolinecolor: c.grid, linecolor: c.grid, tickfont: { color: c.faint } },
      hoverlabel: { bgcolor: c.surface, bordercolor: c.grid, font: { color: c.text, size: 11 } },
      showlegend: false
    }, overrides || {});
  }

  const CONFIG = { displayModeBar: false, responsive: true };

  function empty(elementId, message) {
    const host = document.getElementById(elementId);
    if (host) host.innerHTML = `<div class="empty">${message}</div>`;
  }

  /*
   * Plotly and Vis.js load from a CDN, which is exactly the dependency most
   * likely to be unavailable when this console is demoed offline or behind a
   * restrictive proxy. Charts are the only part of the dashboard that need
   * them, so a missing library degrades to a placeholder in that one panel
   * rather than throwing and taking every table on the tab down with it.
   */
  const MISSING_LIB_MESSAGE =
    'Charting library unavailable (offline?). Tables and metrics below are unaffected.';

  function hasPlotly() { return typeof Plotly !== 'undefined'; }
  function hasVis() { return typeof vis !== 'undefined'; }

  /*
   * Plotly's 3D traces require WebGL, which is missing on some VMs, locked-down
   * corporate builds and headless browsers. Probing once and falling back to a
   * 2D projection keeps the rule-space view useful everywhere rather than
   * leaving Plotly's raw "visit get.webgl.org" notice spilling over the card.
   */
  let webglSupport = null;
  function hasWebGL() {
    if (webglSupport !== null) return webglSupport;
    try {
      const canvas = document.createElement('canvas');
      webglSupport = !!(window.WebGLRenderingContext &&
        (canvas.getContext('webgl') || canvas.getContext('experimental-webgl')));
    } catch (error) {
      webglSupport = false;
    }
    return webglSupport;
  }

  /** Run a chart renderer, degrading to a placeholder on any failure. */
  function guard(elementId, hasLibrary, render) {
    if (!hasLibrary()) return empty(elementId, MISSING_LIB_MESSAGE);
    try {
      // Plotly draws over whatever is in the host without clearing it, so an
      // earlier placeholder would otherwise show through behind the chart.
      const host = document.getElementById(elementId);
      if (host && host.querySelector('.empty')) host.innerHTML = '';
      render();
    } catch (error) {
      console.error(`Chart "${elementId}" failed to render:`, error);
      empty(elementId, 'This chart could not be rendered.');
    }
  }

  /* ------------------------------- charts ------------------------------- */

  function barChart(elementId, labels, values, opts) {
    const options = opts || {};
    if (!labels || !labels.length) return empty(elementId, options.emptyText || 'No data available.');
    const c = palette();

    guard(elementId, hasPlotly, () => Plotly.newPlot(elementId, [{
      type: 'bar',
      x: options.horizontal ? values : labels,
      y: options.horizontal ? labels : values,
      orientation: options.horizontal ? 'h' : 'v',
      marker: { color: options.color || c.accent, line: { width: 0 } },
      hovertemplate: (options.hoverLabel || '%{label}') + ': <b>%{value}</b><extra></extra>'
    }], baseLayout({
      margin: options.horizontal
        ? { l: Math.min(230, options.leftMargin || 190), r: 18, t: 12, b: 36 }
        : { l: 52, r: 18, t: 12, b: 46 },
      xaxis: Object.assign(baseLayout().xaxis, { title: options.xTitle || '', automargin: true }),
      yaxis: Object.assign(baseLayout().yaxis, { title: options.yTitle || '', automargin: true })
    }), CONFIG));
  }

  /**
   * Convergence: per-iteration fitness against the running champion.
   * The champion line is a step function by construction, so the gap between
   * the two lines is exactly the search's wasted exploration -- which is the
   * point of showing them together.
   */
  function convergenceChart(elementId, history) {
    if (!history || !history.length) {
      return empty(elementId, 'No optimization history. Run <code>python run_optimization.py</code>.');
    }
    const c = palette();
    const iterations = history.map(r => r.iteration);
    const restartAt = history.filter(r => r.restart_id > 0 && r.step_type === 'initial').map(r => r.iteration);

    const shapes = restartAt.map(x => ({
      type: 'line', x0: x, x1: x, yref: 'paper', y0: 0, y1: 1,
      line: { color: c.accent3, width: 1, dash: 'dot' }
    }));

    guard(elementId, hasPlotly, () => Plotly.newPlot(elementId, [
      {
        type: 'scatter', mode: 'lines+markers', name: 'candidate fitness',
        x: iterations, y: history.map(r => r.fitness),
        line: { color: c.faint, width: 1.2 },
        marker: { size: 4, color: c.dim },
        hovertemplate: 'iter %{x}<br>fitness <b>%{y:.2f}</b><extra></extra>'
      },
      {
        type: 'scatter', mode: 'lines', name: 'champion',
        x: iterations, y: history.map(r => r.best_fitness),
        line: { color: c.accent, width: 2.4, shape: 'hv' },
        hovertemplate: 'iter %{x}<br>best <b>%{y:.2f}</b><extra></extra>'
      }
    ], baseLayout({
      shapes: shapes,
      showlegend: true,
      legend: { orientation: 'h', y: -0.22, font: { size: 10.5 } },
      margin: { l: 52, r: 18, t: 10, b: 54 },
      xaxis: Object.assign(baseLayout().xaxis, { title: 'iteration' }),
      yaxis: Object.assign(baseLayout().yaxis, { title: 'fitness / 100' })
    }), CONFIG));
  }

  /** Percentage error per target dimension, worst first. */
  function targetErrorChart(elementId, comparison) {
    const entries = Object.entries(comparison || {});
    if (!entries.length) return empty(elementId, 'No target comparison available.');
    const c = palette();

    entries.sort((a, b) => b[1].error_pct - a[1].error_pct);
    const labels = entries.map(e => e[0].replace(/_/g, ' '));
    const errors = entries.map(e => e[1].error_pct);

    guard(elementId, hasPlotly, () => Plotly.newPlot(elementId, [{
      type: 'bar', orientation: 'h',
      x: errors, y: labels,
      marker: { color: errors.map(e => (e <= 10 ? c.accent : e <= 40 ? c.accent2 : c.danger)) },
      text: errors.map(e => e.toFixed(1) + '%'),
      textposition: 'auto',
      textfont: { size: 10.5, family: '"IBM Plex Mono", monospace' },
      hovertemplate: '%{y}: <b>%{x:.2f}%</b> error<extra></extra>'
    }], baseLayout({
      // Explicit left margin, not `automargin`: Plotly recomputes the margin
      // from tick width and clips these labels, so the gutter is reserved here.
      margin: { l: 132, r: 46, t: 10, b: 44 },
      xaxis: Object.assign(baseLayout().xaxis, { title: 'absolute error vs paper (%)' }),
      yaxis: Object.assign(baseLayout().yaxis, { ticklabelposition: 'outside' })
    }), CONFIG));
  }

  /**
   * Hyperparameter trajectory. The five dimensions live on incomparable scales,
   * so each is min-max normalised into [0,1] against its own search bounds --
   * the shape of the movement is what matters here, not the raw magnitude.
   */
  function trajectoryChart(elementId, history) {
    if (!history || !history.length) return empty(elementId, 'No trajectory recorded.');
    const c = palette();

    const dims = [
      { key: 'min_support',    label: 'min support',    lo: 0.002, hi: 0.150, color: c.accent },
      { key: 'min_confidence', label: 'min confidence', lo: 0.100, hi: 0.950, color: c.accent2 },
      { key: 'min_lift',       label: 'min lift',       lo: 1.000, hi: 10.00, color: c.accent3 },
      { key: 'pruning_factor', label: 'pruning factor', lo: 0.000, hi: 1.000, color: c.danger }
    ];

    const traces = dims.map(d => ({
      type: 'scatter', mode: 'lines', name: d.label,
      x: history.map(r => r.iteration),
      y: history.map(r => {
        const v = Number(r[d.key]);
        return Number.isFinite(v) ? (v - d.lo) / (d.hi - d.lo) : null;
      }),
      line: { color: d.color, width: 1.8 },
      hovertemplate: d.label + '<br>iter %{x}: <b>%{y:.3f}</b> of range<extra></extra>'
    }));

    guard(elementId, hasPlotly, () => Plotly.newPlot(elementId, traces, baseLayout({
      showlegend: true,
      legend: { orientation: 'h', y: -0.22, font: { size: 10.5 } },
      margin: { l: 52, r: 18, t: 10, b: 54 },
      xaxis: Object.assign(baseLayout().xaxis, { title: 'iteration' }),
      yaxis: Object.assign(baseLayout().yaxis, { title: 'normalised position', range: [-0.04, 1.04] })
    }), CONFIG));
  }

  /** Rules in support x confidence x lift space, coloured by lift. */
  function scatter3d(elementId, points) {
    if (!points || !points.length) {
      return empty(elementId, 'No rules to plot. Adjust the filters or run the pipeline.');
    }
    if (!hasWebGL()) return scatter2dFallback(elementId, points);

    const c = palette();
    const axis = {
      gridcolor: c.grid, zerolinecolor: c.grid,
      backgroundcolor: 'rgba(0,0,0,0)', showbackground: false,
      tickfont: { size: 9, color: c.faint },
      titlefont: { size: 10.5, color: c.dim }
    };

    guard(elementId, hasPlotly, () => Plotly.newPlot(elementId, [{
      type: 'scatter3d', mode: 'markers',
      x: points.map(p => p.support),
      y: points.map(p => p.confidence),
      z: points.map(p => p.lift),
      text: points.map(p => p.label),
      marker: {
        size: 4,
        color: points.map(p => p.lift),
        colorscale: [[0, c.grid], [0.45, c.accent], [1, c.accent2]],
        opacity: 0.85,
        line: { width: 0 }
      },
      hovertemplate: '%{text}<br>support %{x:.4f}<br>confidence %{y:.3f}<br>lift <b>%{z:.3f}</b><extra></extra>'
    }], baseLayout({
      margin: { l: 0, r: 0, t: 0, b: 0 },
      scene: {
        xaxis: Object.assign({ title: 'support' }, axis),
        yaxis: Object.assign({ title: 'confidence' }, axis),
        zaxis: Object.assign({ title: 'lift' }, axis),
        camera: { eye: { x: 1.6, y: 1.5, z: 0.85 } }
      }
    }), CONFIG));
  }

  /**
   * WebGL-free stand-in for the 3D rule-space plot: support against confidence,
   * with lift carried by marker colour and size. Two of the three dimensions
   * stay on real axes and the third stays legible, which is the most faithful
   * projection available without a 3D context.
   */
  function scatter2dFallback(elementId, points) {
    const c = palette();
    const lifts = points.map(p => p.lift);
    const maxLift = Math.max.apply(null, lifts.concat([1]));

    guard(elementId, hasPlotly, () => Plotly.newPlot(elementId, [{
      type: 'scatter', mode: 'markers',
      x: points.map(p => p.support),
      y: points.map(p => p.confidence),
      text: points.map(p => `${p.label}<br>lift ${p.lift.toFixed(3)}`),
      marker: {
        size: lifts.map(l => 5 + 11 * (l / maxLift)),
        color: lifts,
        colorscale: [[0, c.grid], [0.45, c.accent], [1, c.accent2]],
        opacity: 0.8,
        line: { width: 0 }
      },
      hovertemplate: '%{text}<br>support %{x:.4f}<br>confidence %{y:.3f}<extra></extra>'
    }], baseLayout({
      margin: { l: 58, r: 18, t: 28, b: 48 },
      title: {
        text: '3D view needs WebGL — showing support × confidence, sized by lift',
        font: { size: 10.5, color: c.faint }, x: 0, xanchor: 'left', y: 0.99
      },
      xaxis: Object.assign(baseLayout().xaxis, { title: 'support' }),
      yaxis: Object.assign(baseLayout().yaxis, { title: 'confidence' })
    }), CONFIG));
  }

  /* ------------------------------- network ------------------------------ */

  let network = null;

  /**
   * Force-directed item graph. Node size encodes how many rules an item takes
   * part in, so hub products surface immediately; edge width encodes lift.
   */
  function ruleNetwork(elementId, data) {
    const host = document.getElementById(elementId);
    if (!host) return;

    if (!data || !data.nodes || !data.nodes.length) {
      host.innerHTML = '<div class="empty">No rules match the current filters.</div>';
      if (network) { network.destroy(); network = null; }
      return;
    }
    if (!hasVis()) {
      host.innerHTML = `<div class="empty">${MISSING_LIB_MESSAGE}</div>`;
      return;
    }
    host.innerHTML = '';

    const c = palette();
    const maxLift = Math.max.apply(null, data.edges.map(e => e.value).concat([1]));

    const nodes = new vis.DataSet(data.nodes.map(n => ({
      id: n.id,
      label: n.label,
      title: n.title,
      value: n.value,
      shape: 'dot',
      font: { color: c.dim, size: 11, face: 'IBM Plex Sans' },
      color: {
        background: c.surface,
        border: c.accent,
        highlight: { background: c.accent, border: c.accent },
        hover: { background: c.accent, border: c.accent }
      }
    })));

    const edges = new vis.DataSet(data.edges.map(e => ({
      id: e.id,
      from: e.from,
      to: e.to,
      title: e.title,
      width: 0.6 + 3.2 * (e.value / maxLift),
      color: { color: c.faint, opacity: 0.55, highlight: c.accent2, hover: c.accent2 },
      arrows: { to: { enabled: true, scaleFactor: 0.42 } },
      smooth: { type: 'continuous', roundness: 0.22 }
    })));

    if (network) network.destroy();
    try {
      network = buildNetwork(host, nodes, edges);
    } catch (error) {
      console.error('Rule network failed to render:', error);
      host.innerHTML = '<div class="empty">The network graph could not be rendered.</div>';
    }
  }

  function buildNetwork(host, nodes, edges) {
    return new vis.Network(host, { nodes, edges }, {
      autoResize: true,
      interaction: { hover: true, tooltipDelay: 130, navigationButtons: false },
      nodes: { scaling: { min: 8, max: 34, label: { enabled: true, min: 10, max: 15 } } },
      edges: { selectionWidth: 2 },
      physics: {
        solver: 'forceAtlas2Based',
        forceAtlas2Based: { gravitationalConstant: -46, springLength: 118, springConstant: 0.07, avoidOverlap: 0.3 },
        stabilization: { iterations: 180, updateInterval: 30 }
      }
    });
  }

  /** Repaint every rendered chart after a theme change. */
  function repaintAll() {
    if (!hasPlotly()) return;
    document.querySelectorAll('.plot').forEach(el => {
      if (el.data) Plotly.react(el, el.data, Object.assign({}, el.layout, baseLayout()), CONFIG);
    });
  }

  return {
    barChart, convergenceChart, targetErrorChart, trajectoryChart,
    scatter3d, ruleNetwork, empty, palette, repaintAll
  };
})();
