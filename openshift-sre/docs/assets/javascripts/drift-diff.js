(() => {
  const root = document.querySelector('[data-drift-diff]');
  if (!root) return;

  const leftSelect = root.querySelector('[data-diff-left]');
  const rightSelect = root.querySelector('[data-diff-right]');
  const runButton = root.querySelector('[data-diff-run]');
  const refreshButton = root.querySelector('[data-diff-refresh]');
  const status = root.querySelector('[data-diff-status]');
  const summary = root.querySelector('[data-diff-summary]');
  const metrics = root.querySelector('[data-diff-metrics]');

  function setStatus(message, tone = 'info') {
    status.textContent = message;
    status.dataset.tone = tone;
  }

  function renderOptions(runs) {
    const markup = runs.map((run) => `<option value="${run.run_id}">#${run.run_id} · ${run.model_name} · ${run.aws_region} · ${run.created_at}</option>`).join('');
    leftSelect.innerHTML = markup;
    rightSelect.innerHTML = markup;
    if (runs.length > 1) {
      leftSelect.value = String(runs[1].run_id);
      rightSelect.value = String(runs[0].run_id);
    }
  }

  function renderSummary(payload) {
    const left = payload.left || {};
    const right = payload.right || {};
    const drift = payload.summary || {};
    const tags = drift.tag_delta || {};
    return `
      <article class="agent-console__history-card agent-console__history-card--timeline">
        <div class="agent-console__history-badge-row">
          <span class="agent-console__history-badge">baseline #${left.run_id}</span>
          <span class="agent-console__history-badge">comparison #${right.run_id}</span>
        </div>
        <h3>Run drift summary</h3>
        <ul>
          <li>Duration delta: <strong>${drift.duration_delta_ms ?? '—'} ms</strong></li>
          <li>Step delta: <strong>${drift.step_delta ?? '—'}</strong></li>
          <li>Tools added: <strong>${(drift.tool_added || []).join(', ') || 'none'}</strong></li>
          <li>Tools removed: <strong>${(drift.tool_removed || []).join(', ') || 'none'}</strong></li>
          <li>Tags added: <strong>${(tags.added || []).join(', ') || 'none'}</strong></li>
          <li>Tags removed: <strong>${(tags.removed || []).join(', ') || 'none'}</strong></li>
        </ul>
      </article>
    `;
  }

  function renderMetrics(items) {
    if (!items.length) {
      return '<p class="agent-console__meta">No comparable numeric metrics were found between the selected runs.</p>';
    }
    return `
      <table>
        <thead>
          <tr>
            <th>Metric</th>
            <th>Left</th>
            <th>Right</th>
            <th>Delta</th>
          </tr>
        </thead>
        <tbody>
          ${items.map((item) => `
            <tr>
              <td><code>${item.metric_key}</code></td>
              <td>${item.left_value ?? '—'}</td>
              <td>${item.right_value ?? '—'}</td>
              <td>${item.delta ?? '—'}</td>
            </tr>
          `).join('')}
        </tbody>
      </table>
    `;
  }

  async function loadRuns() {
    setStatus('Loading recent runs…', 'pending');
    const response = await fetch('/history/overview?run_limit=20&point_limit=1&series_limit=1');
    const payload = await response.json();
    const runs = payload.recent_runs || [];
    renderOptions(runs);
    setStatus(`Loaded ${runs.length} recent run(s).`, 'ok');
  }

  async function compareRuns() {
    if (!leftSelect.value || !rightSelect.value) {
      setStatus('Select both runs before comparing.', 'warning');
      return;
    }
    setStatus('Comparing runs…', 'pending');
    runButton.disabled = true;
    try {
      const response = await fetch(`/history/compare?left_run_id=${encodeURIComponent(leftSelect.value)}&right_run_id=${encodeURIComponent(rightSelect.value)}`);
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.detail || 'Comparison failed');
      summary.innerHTML = renderSummary(payload);
      metrics.innerHTML = renderMetrics(payload.metric_deltas || []);
      setStatus('Run comparison ready.', 'ok');
    } catch (error) {
      setStatus(error.message || 'Comparison failed.', 'error');
    } finally {
      runButton.disabled = false;
    }
  }

  runButton.addEventListener('click', compareRuns);
  refreshButton.addEventListener('click', () => {
    loadRuns().catch((error) => setStatus(error.message || 'Unable to refresh runs.', 'error'));
  });

  loadRuns().catch((error) => setStatus(error.message || 'Unable to load recent runs.', 'error'));
})();
