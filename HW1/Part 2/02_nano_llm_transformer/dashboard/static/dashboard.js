function switchTab(tabId) {
  document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
  document.querySelectorAll('.tab-pane').forEach(p => p.classList.remove('active'));
  
  const btn = Array.from(document.querySelectorAll('.tab-btn')).find(b => b.getAttribute('onclick').includes(tabId));
  if (btn) btn.classList.add('active');
  const pane = document.getElementById('tab-' + tabId);
  if (pane) pane.classList.add('active');

  if (tabId === 'crisp') loadCrispDM();
  if (tabId === 'hardware') loadHardwareStats();
}

async function loadHardwareStats() {
  try {
    const res = await fetch('/api/hardware/memory');
    const data = await res.json();
    document.getElementById('headDevice').innerText = data.device_type.toUpperCase();
    document.getElementById('headRss').innerText = data.process_rss_mb + ' MB';

    let html = '';
    html += `<div class="metric-badge"><span class="metric-key">Hardware Compute Device</span><span class="metric-val">${data.device}</span></div>`;
    html += `<div class="metric-badge"><span class="metric-key">Process RSS Memory</span><span class="metric-val">${data.process_rss_mb} MB (${data.process_rss_gb} GB)</span></div>`;
    html += `<div class="metric-badge"><span class="metric-key">MPS Metal Allocated</span><span class="metric-val">${data.mps_allocated_mb} MB</span></div>`;
    html += `<div class="metric-badge"><span class="metric-key">MPS Driver Resident</span><span class="metric-val">${data.mps_driver_mb} MB</span></div>`;
    html += `<div class="metric-badge"><span class="metric-key">System Total RAM</span><span class="metric-val">${data.system_ram_total_gb} GB</span></div>`;
    html += `<div class="metric-badge"><span class="metric-key">Predefined UMA Budget</span><span class="metric-val">${data.unified_memory_limit_gb} GB</span></div>`;
    html += `<div class="metric-badge"><span class="metric-key">Within Memory Budget</span><span class="metric-val" style="color: ${data.within_memory_budget ? 'var(--accent-green)' : 'var(--accent-red)'}">${data.within_memory_budget ? '✅ TRUE' : '❌ FALSE'}</span></div>`;
    document.getElementById('hwDetailedList').innerHTML = html;
  } catch (e) {
    console.error("Hardware poll failed", e);
  }
}

async function loadModelStatus() {
  try {
    const res = await fetch('/api/health');
    const m = (await res.json()).model || {};
    const el = document.getElementById('headWeights');
    const params = m.n_params ? (m.n_params / 1e6).toFixed(2) + 'M params' : '';
    if (m.trained) {
      el.style.color = 'var(--accent-green)';
      el.innerText = `trained · ${params} · val ${m.val_loss} (${m.bits_per_byte} bits/byte)`;
      el.title = `Checkpoint ${m.checkpoint} @ step ${m.step}, corpus ${m.corpus}`;
    } else {
      el.style.color = 'var(--accent-amber)';
      el.innerText = `UNTRAINED · ${params} — output is random`;
      el.title = 'Run `python3 train.py` to fit weights, then restart the dashboard.';
    }
  } catch (e) {
    console.error("Model status poll failed", e);
  }
}

async function loadCrispDM() {
  try {
    const res = await fetch('/api/crisp-dm');
    const data = await res.json();
    const grid = document.getElementById('crispStagesGrid');
    grid.innerHTML = '';
    
    for (const [key, stage] of Object.entries(data.stages)) {
      const card = document.createElement('div');
      card.className = 'stage-card';
      
      let metricsHtml = '';
      if (stage.metrics && Object.keys(stage.metrics).length > 0) {
        metricsHtml = '<div class="stage-metrics"><strong>Metrics:</strong><br>' + 
          Object.entries(stage.metrics).map(([k, v]) => `${k}: ${v}`).join('<br>') + '</div>';
      }

      card.innerHTML = `
        <div class="stage-order">Phase ${stage.order}</div>
        <div class="stage-name">${stage.name}</div>
        <span class="stage-status-badge status-${stage.status}">${stage.status.replace('_', ' ')}</span>
        <div style="font-size: 0.75rem; color: var(--text-muted);">${stage.description || ''}</div>
        ${metricsHtml}
      `;
      grid.appendChild(card);
    }
  } catch (e) {
    console.error("CRISP-DM load failed", e);
  }
}

async function profileKVCache() {
  const prompt = document.getElementById('kvPrompt').value;
  const tokens = document.getElementById('kvTokens').value;
  const temp = document.getElementById('kvTemp').value;

  try {
    const res = await fetch(`/api/inspect/kv-cache?prompt=${encodeURIComponent(prompt)}&max_new_tokens=${tokens}&temperature=${temp}`);
    const data = await res.json();

    let badges = `
      <div class="metric-badge"><span class="metric-key">Prompt</span><span class="metric-val">"${data.prompt}"</span></div>
      <div class="metric-badge"><span class="metric-key">Generated Completion</span><span class="metric-val" style="color: var(--accent-green);">"${data.generated_text}"</span></div>
      <div class="metric-badge"><span class="metric-key">Total Cached Tokens</span><span class="metric-val">${data.total_cached_tokens}</span></div>
      <div class="metric-badge"><span class="metric-key">KV Memory Footprint</span><span class="metric-val">${data.memory_footprint_formatted}</span></div>
    `;
    document.getElementById('kvSummaryBadges').innerHTML = badges;

    let logStr = "=== KV-CACHE GENERATION STEPS ===\n";
    data.steps.forEach(s => {
      logStr += `[Step ${s.step_idx}] ${s.prefill ? 'Prefill' : 'Decode'} | Token: '${s.token_str}' (ID=${s.token_id}) | Latency: ${s.step_latency_ms}ms | Shape: [${s.cache_shape_per_layer.join(', ')}]\n`;
    });
    document.getElementById('kvStepsLog').innerText = logStr;
  } catch (e) {
    console.error("KV profiling failed", e);
  }
}

async function loadAttentionHeatmap() {
  const prompt = document.getElementById('attnPrompt').value;
  const layer = document.getElementById('attnLayer').value;
  const head = document.getElementById('attnHead').value;

  try {
    const res = await fetch(`/api/inspect/attention?prompt=${encodeURIComponent(prompt)}&layer_idx=${layer}&head_idx=${head}`);
    const data = await res.json();

    // Render chips
    const chipsContainer = document.getElementById('heatmapTokens');
    chipsContainer.innerHTML = data.tokens.map((t, idx) => 
      `<span class="token-chip"><span class="tok-id">${idx}</span> "${t}"</span>`
    ).join('');

    // Render metrics
    const m = data.head_metrics;
    document.getElementById('attnMetricsBox').innerHTML = `
      <div class="metric-badge"><span class="metric-key">Causal Validity</span><span class="metric-val" style="color: var(--accent-green);">${data.causal_validity ? '✅ STRICTLY CAUSAL' : '❌ NON-CAUSAL'}</span></div>
      <div class="metric-badge"><span class="metric-key">Average Entropy</span><span class="metric-val">${m.average_entropy}</span></div>
      <div class="metric-badge"><span class="metric-key">Diagonal Dominance</span><span class="metric-val">${m.diagonal_dominance}</span></div>
      <div class="metric-badge"><span class="metric-key">Sparsity (<0.01)</span><span class="metric-val">${(m.sparsity * 100).toFixed(1)}%</span></div>
    `;

    // Render grid heatmap
    const container = document.getElementById('heatmapContainer');
    const matrix = data.attention_matrix;
    const N = matrix.length;
    
    let gridHtml = `<div class="heatmap-grid" style="grid-template-columns: repeat(${N}, 32px);">`;
    for (let i = 0; i < N; i++) {
      for (let j = 0; j < N; j++) {
        const val = matrix[i][j];
        // Blue heat gradient
        const alpha = Math.min(1.0, Math.max(0.05, val));
        const bg = `rgba(56, 189, 248, ${alpha})`;
        gridHtml += `<div class="heatmap-cell" style="background: ${bg};" title="Q[${i}] '${data.tokens[i]}' -> K[${j}] '${data.tokens[j]}': ${val.toFixed(3)}">${val >= 0.1 ? val.toFixed(2).replace('0.', '.') : ''}</div>`;
      }
    }
    gridHtml += '</div>';
    container.innerHTML = gridHtml;
  } catch (e) {
    console.error("Attention extraction failed", e);
  }
}

async function inspectTokenizerText() {
  const text = document.getElementById('tokInput').value;
  try {
    const res = await fetch(`/api/inspect/tokenizer?text=${encodeURIComponent(text)}`);
    const data = await res.json();

    document.getElementById('tokStatsGrid').innerHTML = `
      <div class="metric-badge"><span class="metric-key">Tokens Count</span><span class="metric-val">${data.token_count}</span></div>
      <div class="metric-badge"><span class="metric-key">Raw UTF-8 Bytes</span><span class="metric-val">${data.byte_count}</span></div>
      <div class="metric-badge"><span class="metric-key">Compression Ratio</span><span class="metric-val">${data.compression_ratio} bytes/tok</span></div>
    `;

    const chips = data.tokens.map(t => 
      `<span class="token-chip"><span class="tok-id">#${t.token_id}</span> '${t.token_str}'</span>`
    ).join('');
    document.getElementById('tokChipsContainer').innerHTML = chips;
  } catch (e) {
    console.error("Tokenizer inspection failed", e);
  }
}

async function generateText() {
  const prompt = document.getElementById('genPrompt').value;
  const max_tokens = parseInt(document.getElementById('genMaxTokens').value);
  const temp = parseFloat(document.getElementById('genTemp').value);
  const top_k = parseInt(document.getElementById('genTopK').value);
  const top_p = parseFloat(document.getElementById('genTopP').value);

  document.getElementById('genOutputText').innerText = "Generating...";
  try {
    const res = await fetch('/api/generate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        prompt: prompt,
        max_new_tokens: max_tokens,
        temperature: temp,
        top_k: top_k,
        top_p: top_p,
        use_cache: true
      })
    });
    const data = await res.json();
    document.getElementById('genOutputText').innerText = data.generated_text;
    const m = data.metrics;
    if (m) {
      document.getElementById('genMetricsFooter').innerText = `⚡️ Generated ${m.tokens_generated} tokens in ${m.elapsed_seconds}s (${m.tokens_per_second} tok/s | ${m.ms_per_token} ms/tok)`;
    }
  } catch (e) {
    console.error("Generation failed", e);
    document.getElementById('genOutputText').innerText = "Error: " + e;
  }
}

// Initial load
window.addEventListener('DOMContentLoaded', () => {
  loadHardwareStats();
  loadModelStatus();
  loadCrispDM();
});
