/* ============================================================================
   app.js -- Dashboard state, tab routing, and view rendering.

   Artifacts are fetched once into a small in-memory store and every tab renders
   from it, so switching tabs is instant and a Refresh is an explicit act rather
   than a hidden refetch on every click.
   ========================================================================= */

const App = (() => {

  const state = {
    summary: null,
    crispdm: null,
    eda: null,
    optimization: null,
    rules: [],
    activePhase: 0,
    filters: { min_support: 0, min_confidence: 0, min_lift: 0, search: '', category: '' }
  };

  const el = id => document.getElementById(id);

  /* ------------------------------ utilities ----------------------------- */

  function escapeHtml(value) {
    return String(value == null ? '' : value)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
  }

  function num(value, digits) {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed.toFixed(digits == null ? 3 : digits) : '—';
  }

  function compact(value) {
    const parsed = Number(value);
    if (!Number.isFinite(parsed)) return '—';
    return parsed.toLocaleString(undefined, { maximumFractionDigits: 0 });
  }

  function toast(message, isError) {
    const host = el('toast');
    host.textContent = message;
    host.className = 'toast' + (isError ? ' error' : '');
    host.hidden = false;
    clearTimeout(host._timer);
    host._timer = setTimeout(() => { host.hidden = true; }, 4200);
  }

  async function getJson(url) {
    const response = await fetch(url);
    if (!response.ok) throw new Error(`${url} returned ${response.status}`);
    return response.json();
  }

  /* ------------------------------ rule table ---------------------------- */

  function ruleItems(items) {
    return (items || []).map(i => `<span class="item-chip">${escapeHtml(i)}</span>`).join('');
  }

  /** Shared rule table markup, used by the visualizer and the sandbox alike. */
  function renderRuleTable(rules, metrics) {
    const columns = metrics || ['support', 'confidence', 'lift', 'leverage', 'conviction', 'zhangs_metric'];
    const header = columns.map(m =>
      `<th class="num" data-sort="${m}">${m.replace(/_/g, ' ')}</th>`).join('');

    const body = rules.map(rule => `
      <tr>
        <td class="rule-cell">${ruleItems(rule.antecedents)}<span class="arrow">&rarr;</span>${ruleItems(rule.consequents)}</td>
        ${columns.map(m => `<td class="num">${num(rule[m], m === 'support' ? 4 : 3)}</td>`).join('')}
        <td>${rule.rule_category ? `<span class="tag">${escapeHtml(rule.rule_category)}</span>` : ''}</td>
      </tr>`).join('');

    return `<table><thead><tr><th>Rule</th>${header}<th>Category</th></tr></thead><tbody>${body}</tbody></table>`;
  }

  /* ------------------------------- overview ----------------------------- */

  function renderOverview() {
    const s = state.summary;
    if (!s) return;

    const opt = s.optimization || {};
    const cards = [
      { label: 'Transactions', value: compact(s.transactions), note: `${compact(s.raw_records)} raw records` },
      { label: 'Unique items', value: compact(s.unique_items), note: `${num(s.sparsity_pct, 2)}% sparse`, cls: 'alt' },
      { label: 'Frequent itemsets', value: compact(s.frequent_itemsets), note: 'above min support', cls: 'alt2' },
      { label: 'Association rules', value: compact(s.rules_count), note: `${compact(s.redundant_rules_pruned)} redundant pruned` },
      { label: 'Average lift', value: num(s.avg_lift, 3), note: `max ${num(s.max_lift, 2)}`, cls: 'alt' },
      { label: 'Average confidence', value: num(s.avg_confidence, 3), note: `support ${num(s.avg_support, 4)}`, cls: 'alt2' },
      {
        label: 'Paper match',
        value: opt.available ? num(opt.best_fitness, 1) : '—',
        note: opt.available ? `${escapeHtml(opt.target_paper_key || '')} · from ${num(opt.initial_fitness, 1)}` : 'optimizer not run'
      },
      { label: 'Pipeline runtime', value: num(s.execution_time_seconds, 2) + 's', note: escapeHtml(s.algorithm || '—'), cls: 'alt' }
    ];

    el('kpi-grid').innerHTML = cards.map(c => `
      <div class="kpi ${c.cls || ''}">
        <div class="kpi-label">${c.label}</div>
        <div class="kpi-value">${c.value}</div>
        <div class="kpi-note">${c.note}</div>
      </div>`).join('');

    el('overview-dataset').textContent = s.dataset_name || '—';

    const params = s.parameters || {};
    const rows = [
      ['Dataset', s.dataset_name], ['Algorithm', s.algorithm], ['Framework', s.framework],
      ['Min support', params.min_support], ['Min confidence', params.min_confidence],
      ['Primary metric', params.primary_metric], ['Metric threshold', params.min_metric_val],
      ['Max itemset length', params.max_len], ['Country filter', params.country],
      ['Last run', s.run_timestamp]
    ].filter(r => r[1] !== undefined && r[1] !== null && r[1] !== '');

    el('overview-config').innerHTML = rows.length
      ? `<dl class="kv">${rows.map(([k, v]) => `<dt>${k}</dt><dd>${escapeHtml(v)}</dd>`).join('')}</dl>`
      : '<div class="empty">No pipeline run found. Run <code>python run_pipeline.py</code>.</div>';

    const categories = s.rule_categories || {};
    const labels = Object.keys(categories);
    Viz.barChart('chart-categories', labels, labels.map(k => categories[k]), {
      horizontal: true, leftMargin: 210, xTitle: 'rules',
      emptyText: 'No categorised rules yet.'
    });

    const top = (state.crispdm && state.crispdm.top_rules) || [];
    el('overview-top-rules').innerHTML = top.length
      ? renderRuleTable(top.slice(0, 15), ['support', 'confidence', 'lift', 'zhangs_metric'])
      : '<div class="empty">No rules yet. Run <code>python run_pipeline.py</code>.</div>';
  }

  /* ------------------------------- CRISP-DM ----------------------------- */

  function renderCrispDm() {
    const data = state.crispdm;
    if (!data) return;

    el('crispdm-stepper').innerHTML = data.phases.map((phase, index) => `
      <li class="step ${phase.completed ? 'done' : ''} ${index === state.activePhase ? 'is-active' : ''}"
          data-phase="${index}">
        <h3>${escapeHtml(phase.title)}</h3>
        <p>${escapeHtml(phase.description)}</p>
      </li>`).join('');

    el('crispdm-stepper').querySelectorAll('.step').forEach(node => {
      node.addEventListener('click', () => {
        state.activePhase = parseInt(node.dataset.phase, 10);
        renderCrispDm();
      });
    });

    renderPhaseDetail(data.phases[state.activePhase]);
    renderEdaCharts();

    const steps = (state.eda && state.eda.cleaning_steps_applied) || [];
    el('crispdm-cleaning').innerHTML = steps.length
      ? `<ul class="checklist">${steps.map(s => `<li>${escapeHtml(s)}</li>`).join('')}</ul>`
      : '<div class="empty">No preparation ledger recorded.</div>';
  }

  /** Flatten one phase's recorded details into a readable definition list. */
  function renderPhaseDetail(phase) {
    if (!phase) return;
    const details = phase.details || {};

    if (!Object.keys(details).length) {
      el('crispdm-detail').innerHTML =
        `<div class="empty">Phase <b>${escapeHtml(phase.title)}</b> has no recorded output yet.</div>`;
      return;
    }

    const rows = [];
    Object.entries(details).forEach(([key, value]) => {
      if (value === null || value === undefined) return;
      const label = key.replace(/_/g, ' ');

      if (Array.isArray(value)) {
        if (!value.length) return;
        const rendered = typeof value[0] === 'object'
          ? value.slice(0, 6).map(v => escapeHtml(v.item || v.name || JSON.stringify(v))).join(', ')
          : value.slice(0, 12).map(escapeHtml).join(', ');
        rows.push([label, rendered + (value.length > 12 ? ` … (${value.length} total)` : '')]);
      } else if (typeof value === 'object') {
        Object.entries(value).slice(0, 10).forEach(([k, v]) => {
          rows.push([`${label} · ${k.replace(/_/g, ' ')}`, escapeHtml(v)]);
        });
      } else {
        rows.push([label, escapeHtml(value)]);
      }
    });

    el('crispdm-detail').innerHTML = `<dl class="kv">${
      rows.map(([k, v]) => `<dt>${k}</dt><dd>${v}</dd>`).join('')}</dl>`;
  }

  function renderEdaCharts() {
    const eda = state.eda;
    if (!eda || !eda.available) {
      Viz.empty('chart-baskets', 'No EDA profile. Run <code>python run_pipeline.py</code>.');
      Viz.empty('chart-items', 'No EDA profile available.');
      return;
    }

    const distribution = eda.basket_size_distribution || [];
    Viz.barChart('chart-baskets',
      distribution.map(d => d.bin || d.basket_size || d.label),
      distribution.map(d => d.count || d.frequency || 0),
      { xTitle: 'items per basket', yTitle: 'transactions' });

    const items = (eda.top_frequent_items || []).slice(0, 14).reverse();
    Viz.barChart('chart-items',
      items.map(i => (i.item || '').length > 30 ? i.item.slice(0, 28) + '…' : i.item),
      items.map(i => i.count || 0),
      { horizontal: true, leftMargin: 230, xTitle: 'transactions containing item', color: Viz.palette().accent2 });
  }

  /* -------------------------------- rules ------------------------------- */

  function filterQuery() {
    const f = state.filters;
    const params = new URLSearchParams();
    if (f.min_support > 0) params.set('min_support', f.min_support);
    if (f.min_confidence > 0) params.set('min_confidence', f.min_confidence);
    if (f.min_lift > 0) params.set('min_lift', f.min_lift);
    if (f.search) params.set('search', f.search);
    if (f.category) params.set('category', f.category);
    return params;
  }

  async function refreshRules() {
    const params = filterQuery();
    params.set('limit', '300');

    try {
      const data = await getJson('/api/rules?' + params.toString());
      state.rules = data.rules;

      el('rules-count-label').textContent =
        `${data.filtered.toLocaleString()} of ${data.total.toLocaleString()} rules match`;
      el('rules-table').innerHTML = data.rules.length
        ? renderRuleTable(data.rules)
        : '<div class="empty">No rules match these filters.</div>';

      const select = el('f-category');
      if (select.options.length <= 1 && data.categories.length) {
        data.categories.forEach(category => {
          const option = document.createElement('option');
          option.value = category;
          option.textContent = category;
          select.appendChild(option);
        });
      }

      const exportParams = filterQuery();
      el('export-csv').href = '/api/rules/export?format=csv&' + exportParams.toString();
      el('export-json').href = '/api/rules/export?format=json&' + exportParams.toString();

      const network = await getJson('/api/rules/network?limit=120&' + params.toString());
      Viz.ruleNetwork('rule-network', network);

      const scatter = await getJson('/api/rules/scatter?limit=500&' + params.toString());
      Viz.scatter3d('rule-scatter', scatter.points);

    } catch (error) {
      toast('Could not load rules: ' + error.message, true);
    }
  }

  function bindRuleFilters() {
    const bindings = [
      ['f-support', 'val-support', 'min_support', v => Number(v).toFixed(3)],
      ['f-confidence', 'val-confidence', 'min_confidence', v => Number(v).toFixed(2)],
      ['f-lift', 'val-lift', 'min_lift', v => Number(v).toFixed(1)]
    ];

    let debounce = null;
    const schedule = () => { clearTimeout(debounce); debounce = setTimeout(refreshRules, 220); };

    bindings.forEach(([input, output, key, format]) => {
      const node = el(input);
      node.addEventListener('input', () => {
        state.filters[key] = parseFloat(node.value);
        el(output).textContent = format(node.value);
        schedule();
      });
    });

    el('f-search').addEventListener('input', e => {
      state.filters.search = e.target.value.trim();
      schedule();
    });
    el('f-category').addEventListener('change', e => {
      state.filters.category = e.target.value;
      refreshRules();
    });
    el('rules-reset').addEventListener('click', () => {
      state.filters = { min_support: 0, min_confidence: 0, min_lift: 0, search: '', category: '' };
      ['f-support', 'f-confidence', 'f-lift'].forEach(id => { el(id).value = 0; });
      el('f-search').value = '';
      el('f-category').value = '';
      el('val-support').textContent = '0.000';
      el('val-confidence').textContent = '0.00';
      el('val-lift').textContent = '0.0';
      refreshRules();
    });

    el('recommend-btn').addEventListener('click', recommend);
    el('cart-input').addEventListener('keydown', e => { if (e.key === 'Enter') recommend(); });
  }

  async function recommend() {
    const cart = el('cart-input').value.trim();
    const host = el('recommend-output');

    if (!cart) {
      host.innerHTML = '<div class="empty">Enter one or more items to get recommendations.</div>';
      return;
    }

    try {
      const data = await getJson('/api/recommend?limit=10&cart=' + encodeURIComponent(cart));
      if (!data.recommendations.length) {
        host.innerHTML = `<div class="empty">No rule fires for this basket. Every rule needs its full antecedent present, so try fewer or more common items.</div>`;
        return;
      }
      host.innerHTML = `<div class="table-wrap"><table>
        <thead><tr><th>#</th><th>Recommended item</th><th class="num">confidence</th><th class="num">lift</th><th class="num">support</th><th>Triggered by</th></tr></thead>
        <tbody>${data.recommendations.map(r => `
          <tr>
            <td class="num">${r.rank}</td>
            <td><span class="item-chip">${escapeHtml(r.item)}</span></td>
            <td class="num">${num(r.confidence, 3)}</td>
            <td class="num">${num(r.lift, 3)}</td>
            <td class="num">${num(r.support, 4)}</td>
            <td>${ruleItems(r.matched_antecedents)}</td>
          </tr>`).join('')}</tbody></table></div>`;
    } catch (error) {
      toast('Recommendation failed: ' + error.message, true);
    }
  }

  /* ----------------------------- optimization --------------------------- */

  function renderOptimization() {
    const data = state.optimization;
    if (!data) return;

    if (!data.available) {
      el('paper-card').innerHTML =
        '<div class="empty">No optimization run found. Run <code>python run_optimization.py</code>.</div>';
      ['chart-convergence', 'chart-target', 'chart-trajectory'].forEach(id =>
        Viz.empty(id, 'Awaiting an optimization run.'));
      el('best-params').innerHTML = '';
      el('optimization-table').innerHTML = '';
      return;
    }

    const paper = data.target_paper || {};
    const summary = data.summary || {};
    const comparison = data.target_vs_achieved || {};

    el('paper-card').innerHTML = `
      <div class="paper-head">
        <div>
          <div class="kpi-label">Target research paper</div>
          <h2 class="paper-title">${escapeHtml(paper.title || '—')}</h2>
          <div class="paper-meta">
            ${escapeHtml(paper.authors || '')} &middot; ${escapeHtml(paper.venue || '')}<br>
            <code>DOI ${escapeHtml(paper.doi || 'n/a')}</code> &middot; <code>key ${escapeHtml(paper.key || '')}</code>
          </div>
          ${paper.target_basis ? `<p class="paper-note">${escapeHtml(paper.target_basis)}</p>` : ''}
        </div>
        <div class="fitness-badge">
          <div class="score">${num(summary.best_fitness, 1)}</div>
          <div class="score-label">best fitness / 100</div>
          <div class="kpi-note">from ${num(summary.initial_fitness, 1)} &middot; ${compact(summary.total_iterations_run)} iterations</div>
          <div class="kpi-note">${compact(summary.restarts_triggered)} restarts &middot; loss ${num(summary.best_loss, 4)}</div>
        </div>
      </div>
      <div class="compare-grid">
        ${Object.entries(comparison).map(([metric, v]) => {
          const severity = v.error_pct <= 10 ? '' : v.error_pct <= 40 ? 'high' : 'severe';
          return `<div class="compare-cell">
            <div class="metric">${metric.replace(/_/g, ' ')}</div>
            <div class="values">
              <span class="achieved">${num(v.achieved, 4)}</span>
              <span class="target"> / ${num(v.target, 4)}</span>
            </div>
            <div class="err-bar ${severity}"><span style="width:${Math.min(100, v.error_pct)}%"></span></div>
            <div class="err-pct">${num(v.error_pct, 2)}% error</div>
          </div>`;
        }).join('')}
      </div>`;

    Viz.convergenceChart('chart-convergence', data.history);
    Viz.targetErrorChart('chart-target', comparison);
    Viz.trajectoryChart('chart-trajectory', data.history);

    const best = data.best_hyperparameters || {};
    const config = data.config || {};
    el('best-params').innerHTML = `
      <dl class="kv">
        ${Object.entries(best).map(([k, v]) =>
          `<dt>${k.replace(/_/g, ' ')}</dt><dd>${escapeHtml(v)}</dd>`).join('')}
        <dt>fitness mode</dt><dd>${escapeHtml(config.fitness_mode || '—')}</dd>
        <dt>neighbours / step</dt><dd>${escapeHtml(config.neighbors_per_step || '—')}</dd>
        <dt>scout samples</dt><dd>${escapeHtml(config.scout_samples != null ? config.scout_samples : '—')}</dd>
        <dt>seed</dt><dd>${escapeHtml(config.seed != null ? config.seed : '—')}</dd>
        <dt>termination</dt><dd>${escapeHtml(summary.termination_reason || '—')}</dd>
      </dl>`;

    const history = data.history || [];
    el('optimization-table').innerHTML = history.length ? `<table>
      <thead><tr>
        <th class="num">iter</th><th class="num">restart</th><th>step</th>
        <th class="num">support</th><th class="num">confidence</th><th class="num">lift</th>
        <th class="num">max len</th><th class="num">pruning</th>
        <th class="num">rules</th><th class="num">coverage</th>
        <th class="num">fitness</th><th class="num">best</th>
      </tr></thead>
      <tbody>${history.map(r => `
        <tr>
          <td class="num">${r.iteration}</td>
          <td class="num">${r.restart_id}</td>
          <td><span class="tag ${r.step_type === 'improvement' ? 'good' : r.step_type === 'plateau' ? '' : 'warn'}">${escapeHtml(r.step_type)}</span></td>
          <td class="num">${num(r.min_support, 4)}</td>
          <td class="num">${num(r.min_confidence, 3)}</td>
          <td class="num">${num(r.min_lift, 3)}</td>
          <td class="num">${r.max_len}</td>
          <td class="num">${num(r.pruning_factor, 3)}</td>
          <td class="num">${compact(r.rule_count)}</td>
          <td class="num">${num(r.coverage, 4)}</td>
          <td class="num">${num(r.fitness, 2)}</td>
          <td class="num">${num(r.best_fitness, 2)}</td>
        </tr>`).join('')}</tbody></table>` : '';
  }

  /* -------------------------------- shell ------------------------------- */

  const TAB_NAMES = ['overview', 'crispdm', 'rules', 'optimization', 'sandbox'];

  /**
   * Show one tab and record it in the URL fragment, so a particular view can be
   * bookmarked or shared and survives a reload.
   */
  function switchTab(name, updateHash) {
    if (!TAB_NAMES.includes(name)) name = 'overview';

    document.querySelectorAll('.tab').forEach(tab =>
      tab.classList.toggle('is-active', tab.dataset.tab === name));
    document.querySelectorAll('.panel').forEach(panel =>
      panel.classList.toggle('is-active', panel.id === 'tab-' + name));

    if (updateHash !== false && window.location.hash.slice(1) !== name) {
      history.replaceState(null, '', '#' + name);
    }

    // Plotly cannot size a chart inside a hidden container, so nudge it once
    // the panel is actually visible.
    setTimeout(() => window.dispatchEvent(new Event('resize')), 40);
  }

  async function loadAll() {
    try {
      const health = await getJson('/health');
      el('health-pill').className = 'status-pill ok';
      el('health-text').textContent = 'healthy';
      el('footer-timestamp').textContent = 'loaded ' + new Date().toLocaleTimeString();

      const missing = Object.entries(health.artifacts)
        .filter(([, present]) => !present).map(([name]) => name);
      if (missing.length) {
        toast(`Artifacts not yet generated: ${missing.join(', ')}`);
      }
    } catch (error) {
      el('health-pill').className = 'status-pill bad';
      el('health-text').textContent = 'unreachable';
    }

    const [summary, crispdm, eda, optimization] = await Promise.all([
      getJson('/api/summary').catch(() => null),
      getJson('/api/crisp-dm').catch(() => null),
      getJson('/api/eda').catch(() => null),
      getJson('/api/optimization').catch(() => null)
    ]);

    state.summary = summary;
    state.crispdm = crispdm;
    state.eda = eda;
    state.optimization = optimization;

    renderOverview();
    renderCrispDm();
    renderOptimization();
    await refreshRules();

    getJson('/api/catalog/items').then(data => {
      el('item-catalog').innerHTML = data.items
        .map(i => `<option value="${escapeHtml(i)}"></option>`).join('');
    }).catch(() => { /* autocomplete is a convenience, not a requirement */ });
  }

  function applyTheme(theme) {
    document.documentElement.setAttribute('data-theme', theme);
    el('theme-btn').textContent = theme === 'dark' ? 'Light' : 'Dark';
    try { localStorage.setItem('apm-theme', theme); } catch (e) { /* private mode */ }
    setTimeout(Viz.repaintAll, 30);
  }

  function init() {
    let stored = 'dark';
    try { stored = localStorage.getItem('apm-theme') || 'dark'; } catch (e) { /* private mode */ }
    applyTheme(stored);

    document.querySelectorAll('.tab').forEach(tab =>
      tab.addEventListener('click', () => switchTab(tab.dataset.tab)));

    switchTab(window.location.hash.slice(1) || 'overview', false);
    window.addEventListener('hashchange', () =>
      switchTab(window.location.hash.slice(1) || 'overview', false));

    el('theme-btn').addEventListener('click', () => {
      const current = document.documentElement.getAttribute('data-theme');
      applyTheme(current === 'dark' ? 'light' : 'dark');
    });

    el('refresh-btn').addEventListener('click', () => {
      toast('Reloading artifacts…');
      loadAll();
    });

    bindRuleFilters();
    Sandbox.init();
    loadAll();
  }

  document.addEventListener('DOMContentLoaded', init);

  return { renderRuleTable, switchTab, toast, escapeHtml, num };
})();
