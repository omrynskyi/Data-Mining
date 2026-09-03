/* ============================================================================
   sandbox.js -- Live interactive mining controller.

   Drives POST /api/sandbox/mine, which re-runs the production mining engine on
   analyst-chosen thresholds. Runs are accumulated into a sweep history so the
   analyst can see how rule yield responds to the parameters they just moved --
   the thing a single point estimate cannot show.
   ========================================================================= */

const Sandbox = (() => {

  const sweepHistory = [];
  let lastRules = [];

  const el = id => document.getElementById(id);

  function readParameters() {
    return {
      algorithm:      el('s-algorithm').value,
      min_support:    parseFloat(el('s-support').value),
      min_confidence: parseFloat(el('s-confidence').value),
      min_lift:       parseFloat(el('s-lift').value),
      max_len:        parseInt(el('s-maxlen').value, 10)
    };
  }

  function bindSliderReadouts() {
    const pairs = [
      ['s-support', 's-val-support', v => Number(v).toFixed(3)],
      ['s-confidence', 's-val-confidence', v => Number(v).toFixed(2)],
      ['s-lift', 's-val-lift', v => Number(v).toFixed(1)],
      ['s-maxlen', 's-val-maxlen', v => String(v)]
    ];
    pairs.forEach(([input, output, format]) => {
      const source = el(input);
      const target = el(output);
      if (!source || !target) return;
      const sync = () => { target.textContent = format(source.value); };
      source.addEventListener('input', sync);
      sync();
    });
  }

  function renderKpis(result) {
    const cards = [
      { label: 'Rules found',   value: result.rules_count.toLocaleString(), note: result.truncated ? `showing top ${result.returned_count}` : 'all returned' },
      { label: 'Itemsets',      value: result.itemsets_count.toLocaleString(), note: 'frequent patterns', cls: 'alt' },
      { label: 'Mining time',   value: result.mining_time_ms.toFixed(1) + ' ms', note: `total ${result.execution_time_ms.toFixed(1)} ms`, cls: 'alt2' },
      { label: 'Avg lift',      value: (result.metrics.avg_lift || 0).toFixed(3), note: `max ${(result.metrics.max_lift || 0).toFixed(2)}` },
      { label: 'Avg confidence', value: (result.metrics.avg_confidence || 0).toFixed(3), note: 'across returned rules', cls: 'alt' },
      { label: 'Corpus',        value: (result.transactions || 0).toLocaleString(), note: `${result.items || 0} items`, cls: 'alt2' }
    ];

    el('sandbox-kpis').innerHTML = cards.map(c => `
      <div class="kpi ${c.cls || ''}">
        <div class="kpi-label">${c.label}</div>
        <div class="kpi-value">${c.value}</div>
        <div class="kpi-note">${c.note}</div>
      </div>`).join('');
  }

  function renderTable(rules) {
    const host = el('sandbox-table');
    if (!rules.length) {
      host.innerHTML = '<div class="empty">No rules cleared these thresholds. Try lowering support or lift.</div>';
      return;
    }
    host.innerHTML = App.renderRuleTable(rules, ['support', 'confidence', 'lift', 'leverage', 'zhangs_metric']);
  }

  function renderCharts(result) {
    const lengths = Object.keys(result.itemsets_by_length || {});
    Viz.barChart('chart-sandbox-itemsets',
      lengths,
      lengths.map(k => result.itemsets_by_length[k]),
      { yTitle: 'itemsets', emptyText: 'No itemsets at this support level.' });

    if (sweepHistory.length) {
      Viz.barChart('chart-sandbox-history',
        sweepHistory.map((r, i) => `#${i + 1} s=${r.min_support.toFixed(3)}`),
        sweepHistory.map(r => r.rules_count),
        { yTitle: 'rules discovered', color: Viz.palette().accent2 });
    }
  }

  async function run() {
    const button = el('sandbox-run');
    const status = el('sandbox-status');
    const params = readParameters();

    button.disabled = true;
    status.textContent = 'mining...';

    try {
      const response = await fetch('/api/sandbox/mine', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(params)
      });
      const result = await response.json();

      if (!response.ok || result.status !== 'success') {
        status.textContent = '';
        App.toast(result.message || 'Sandbox mining failed.', true);
        return;
      }

      lastRules = result.rules;
      sweepHistory.push({ min_support: params.min_support, rules_count: result.rules_count });
      if (sweepHistory.length > 12) sweepHistory.shift();

      renderKpis(result);
      renderTable(result.rules);
      renderCharts(result);

      el('sandbox-rule-count').textContent =
        `${result.rules_count.toLocaleString()} rules from ${result.itemsets_count.toLocaleString()} itemsets in ${result.mining_time_ms.toFixed(0)} ms`;
      if (result.dataset) {
        el('sandbox-corpus').textContent =
          `${result.dataset.dataset_name} — ${result.dataset.transactions.toLocaleString()} baskets × ${result.dataset.items} items`;
      }
      el('sandbox-push').disabled = result.rules.length === 0;
      status.textContent = `done in ${result.execution_time_ms.toFixed(0)} ms`;

    } catch (error) {
      status.textContent = '';
      App.toast('Sandbox request failed: ' + error.message, true);
    } finally {
      button.disabled = false;
    }
  }

  /** Push the sandbox's rule set into the visualizer tab's network graph. */
  function pushToVisualizer() {
    if (!lastRules.length) return;

    const degree = {};
    const edges = [];
    lastRules.slice(0, 120).forEach((rule, index) => {
      rule.antecedents.concat(rule.consequents).forEach(item => {
        degree[item] = (degree[item] || 0) + 1;
      });
      rule.antecedents.forEach(source => {
        rule.consequents.forEach(target => {
          edges.push({
            id: `s${index}-${source}-${target}`,
            from: source, to: target,
            value: rule.lift,
            title: `{${rule.antecedents.join(', ')}} → {${rule.consequents.join(', ')}}<br>confidence ${rule.confidence.toFixed(3)} | lift ${rule.lift.toFixed(3)}`
          });
        });
      });
    });

    const nodes = Object.keys(degree).map(item => ({
      id: item,
      label: item.length <= 28 ? item : item.slice(0, 25) + '...',
      title: `${item} (${degree[item]} rule participations)`,
      value: degree[item]
    }));

    App.switchTab('rules');
    Viz.ruleNetwork('rule-network', { nodes, edges });
    Viz.scatter3d('rule-scatter', lastRules.map(r => ({
      support: r.support, confidence: r.confidence, lift: r.lift,
      label: `{${r.antecedents.join(', ')}} → {${r.consequents.join(', ')}}`
    })));
    el('rules-table').innerHTML = App.renderRuleTable(lastRules,
      ['support', 'confidence', 'lift', 'leverage', 'zhangs_metric']);
    el('rules-count-label').textContent = `${lastRules.length} rules from the live sandbox`;
    App.toast(`Pushed ${lastRules.length} sandbox rules to the visualizer.`);
  }

  function init() {
    bindSliderReadouts();
    el('sandbox-run').addEventListener('click', run);
    el('sandbox-push').addEventListener('click', pushToVisualizer);

    // Say what the empty panels are waiting for, rather than showing blank boxes.
    Viz.empty('chart-sandbox-itemsets', 'Run a search to see the itemset size breakdown.');
    Viz.empty('chart-sandbox-history', 'Each run you make is added here for comparison.');
    el('sandbox-table').innerHTML =
      '<div class="empty">Choose thresholds above and press <b>Run mining</b> to search the corpus live.</div>';

    fetch('/api/sandbox/corpus')
      .then(r => r.json())
      .then(data => {
        if (data.status === 'success' && data.dataset) {
          el('sandbox-corpus').textContent =
            `${data.dataset.dataset_name} — ${data.dataset.transactions.toLocaleString()} baskets × ${data.dataset.items} items`;
        }
      })
      .catch(() => { /* corpus preview is optional; the run button still works */ });
  }

  return { init, run };
})();
