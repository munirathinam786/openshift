(() => {
  const root = document.querySelector('[data-llm-utilization]');
  if (!root) {
    return;
  }

  const statusNode = root.querySelector('[data-llm-status]');
  const summaryNode = root.querySelector('[data-llm-summary]');
  const modelsNode = root.querySelector('[data-llm-models]');
  const processesNode = root.querySelector('[data-llm-processes]');
  const commandsNode = root.querySelector('[data-llm-commands]');
  const refreshButton = root.querySelector('[data-llm-refresh]');
  const themeToggleButton = root.querySelector('[data-llm-theme-toggle]');
  const reportExportButtons = root.querySelectorAll('[data-llm-export-report]');
  const reportStatusNode = root.querySelector('[data-llm-report-status]');
  const themeStorageKey = 'openshift-sre-history-theme';
  let lastPayload = null;

  function escapeHtml(value) {
    return String(value ?? '')
      .replaceAll('&', '&amp;')
      .replaceAll('<', '&lt;')
      .replaceAll('>', '&gt;')
      .replaceAll('"', '&quot;')
      .replaceAll("'", '&#39;');
  }

  function getFriendlyMessage(message) {
    const raw = String(message ?? '').trim();
    if (!raw) {
      return 'No data is available yet.';
    }

    if (raw.toLowerCase() === 'failed to fetch') {
      return 'Live model data is unavailable in static preview. Open this page through the running app on http://127.0.0.1:8000/ or start the local stack to enable API-backed panels.';
    }

    return raw;
  }

  function setStatus(message, kind = '') {
    statusNode.textContent = getFriendlyMessage(message);
    statusNode.className = 'agent-console__status';
    if (kind) {
      statusNode.classList.add(`agent-console__status--${kind}`);
    }
  }

  function setReportStatus(message, kind = '') {
    if (!reportStatusNode) {
      return;
    }
    reportStatusNode.textContent = getFriendlyMessage(message);
    reportStatusNode.className = 'agent-console__status';
    if (kind) {
      reportStatusNode.classList.add(`agent-console__status--${kind}`);
    }
  }

  function renderMessage(node, message) {
    const friendlyMessage = getFriendlyMessage(message);
    const isWarning = /failed to fetch|unavailable|unable|disabled/i.test(friendlyMessage);
    const title = isWarning ? 'Live data unavailable' : 'Nothing to show yet';
    node.innerHTML = `
      <div class="agent-console__state ${isWarning ? 'agent-console__state--warning' : ''}">
        <p class="agent-console__state-title">${escapeHtml(title)}</p>
        <p class="agent-console__state-copy">${escapeHtml(friendlyMessage)}</p>
      </div>
    `;
  }

  function formatNumber(value) {
    const numeric = Number(value);
    if (!Number.isFinite(numeric)) {
      return String(value ?? '');
    }
    return new Intl.NumberFormat(undefined, { maximumFractionDigits: 2 }).format(numeric);
  }

  function formatTimestamp(value) {
    return value ? new Date(value).toLocaleString() : '—';
  }

  function createTimestampSlug() {
    return new Date().toISOString().replace(/[:.]/g, '-');
  }

  function toCsv(rows = []) {
    return rows.map((row = []) => row.map((value) => {
      const text = String(value ?? '');
      if (text.includes(',') || text.includes('"') || text.includes('\n')) {
        return `"${text.replaceAll('"', '""')}"`;
      }
      return text;
    }).join(',')).join('\n');
  }

  function downloadBlob(filename, blob) {
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
  }

  function applyTheme(theme) {
    document.body.dataset.theme = theme === 'dark' ? 'dark' : 'light';
    window.localStorage.setItem(themeStorageKey, document.body.dataset.theme);
    themeToggleButton.textContent = document.body.dataset.theme === 'dark' ? 'Light mode' : 'Dark mode';
  }

  function initializeTheme() {
    const savedTheme = window.localStorage.getItem(themeStorageKey);
    applyTheme(savedTheme === 'dark' ? 'dark' : 'light');
  }

  function renderSummary(payload) {
    const models = Array.isArray(payload.loaded_models) ? payload.loaded_models : [];
    const primary = models[0] || null;
    summaryNode.innerHTML = `
      <div class="agent-console__history-card-grid">
        <article class="agent-console__history-card">
          <p class="agent-console__history-card-label">Configured model</p>
          <p class="agent-console__history-card-value agent-console__history-card-value--small">${escapeHtml(payload.configured_model_name || '—')}</p>
        </article>
        <article class="agent-console__history-card">
          <p class="agent-console__history-card-label">Loaded model count</p>
          <p class="agent-console__history-card-value">${formatNumber(payload.active_model_count ?? 0)}</p>
        </article>
        <article class="agent-console__history-card">
          <p class="agent-console__history-card-label">Current loaded model</p>
          <p class="agent-console__history-card-value agent-console__history-card-value--small">${escapeHtml(primary?.name || 'No model loaded')}</p>
        </article>
        <article class="agent-console__history-card">
          <p class="agent-console__history-card-label">VRAM footprint</p>
          <p class="agent-console__history-card-value">${primary?.size_vram_gib == null ? '—' : `${formatNumber(primary.size_vram_gib)} GiB`}</p>
        </article>
        <article class="agent-console__history-card">
          <p class="agent-console__history-card-label">Context length</p>
          <p class="agent-console__history-card-value">${primary?.context_length == null ? '—' : formatNumber(primary.context_length)}</p>
        </article>
        <article class="agent-console__history-card">
          <p class="agent-console__history-card-label">Ollama base URL</p>
          <p class="agent-console__history-card-value agent-console__history-card-value--small">${escapeHtml(payload.ollama_base_url || '—')}</p>
        </article>
        <article class="agent-console__history-card">
          <p class="agent-console__history-card-label">API reachability</p>
          <p class="agent-console__history-card-value">${payload.api_reachable ? 'Reachable' : 'Unavailable'}</p>
        </article>
        <article class="agent-console__history-card">
          <p class="agent-console__history-card-label">Checked at</p>
          <p class="agent-console__history-card-value agent-console__history-card-value--small">${escapeHtml(formatTimestamp(payload.checked_at))}</p>
        </article>
      </div>
      <div class="agent-console__history-badges">
        <span class="agent-console__history-badge ${payload.api_reachable ? 'agent-console__history-badge--ok' : 'agent-console__history-badge--error'}">${payload.api_reachable ? 'ollama api reachable' : 'ollama api unavailable'}</span>
        <span class="agent-console__history-badge">${payload.running_in_container ? 'running in container' : 'running on host'}</span>
        ${primary?.processor_hint ? `<span class="agent-console__history-badge">${escapeHtml(primary.processor_hint)}</span>` : ''}
      </div>
      ${payload.api_error ? `<p class="agent-console__meta"><strong>API error:</strong> ${escapeHtml(payload.api_error)}</p>` : ''}
    `;
  }

  function renderModels(payload) {
    const models = Array.isArray(payload.loaded_models) ? payload.loaded_models : [];
    if (models.length === 0) {
      renderMessage(modelsNode, payload.api_reachable ? 'No Ollama model is currently loaded.' : 'No model data is available because the Ollama API could not be reached.');
      return;
    }

    modelsNode.innerHTML = `
      <section class="agent-console__table-block">
        <table class="agent-console__table">
          <thead>
            <tr>
              <th>Model</th>
              <th>Parameters</th>
              <th>Quantization</th>
              <th>VRAM</th>
              <th>Context</th>
              <th>Expires</th>
            </tr>
          </thead>
          <tbody>
            ${models.map((model) => `
              <tr>
                <td>${escapeHtml(model.name || '—')}</td>
                <td>${escapeHtml(model.parameter_size || '—')}</td>
                <td>${escapeHtml(model.quantization_level || '—')}</td>
                <td>${model.size_vram_gib == null ? '—' : `${formatNumber(model.size_vram_gib)} GiB`}</td>
                <td>${model.context_length == null ? '—' : formatNumber(model.context_length)}</td>
                <td>${escapeHtml(formatTimestamp(model.expires_at))}</td>
              </tr>
            `).join('')}
          </tbody>
        </table>
      </section>
    `;
  }

  function renderProcesses(payload) {
    const processMetrics = payload.host_process_metrics || {};
    const processes = Array.isArray(processMetrics.processes) ? processMetrics.processes : [];

    processesNode.innerHTML = `
      <section class="agent-console__table-block">
        <h4>Process inspection scope</h4>
        <p class="agent-console__meta">${escapeHtml(processMetrics.note || 'No additional process notes available.')}</p>
        <p><strong>Scope:</strong> ${escapeHtml(processMetrics.scope || 'unknown')}</p>
        <p><strong>Available:</strong> ${processMetrics.available ? 'Yes' : 'No'}</p>
      </section>
      <section class="agent-console__table-block">
        <h4>Observed Ollama-related processes</h4>
        ${processes.length > 0 ? `
          <table class="agent-console__table">
            <thead>
              <tr>
                <th>PID</th>
                <th>CPU %</th>
                <th>Mem %</th>
                <th>RSS</th>
                <th>VSZ</th>
                <th>Elapsed</th>
                <th>Command</th>
              </tr>
            </thead>
            <tbody>
              ${processes.map((process) => `
                <tr>
                  <td>${formatNumber(process.pid)}</td>
                  <td>${formatNumber(process.cpu_percent)}</td>
                  <td>${formatNumber(process.mem_percent)}</td>
                  <td>${formatNumber(process.rss_mb)} MB</td>
                  <td>${formatNumber(process.vsz_mb)} MB</td>
                  <td>${escapeHtml(process.elapsed || '—')}</td>
                  <td>${escapeHtml(process.command || '—')}</td>
                </tr>
              `).join('')}
            </tbody>
          </table>
        ` : '<p class="agent-console__meta">No local process rows are available from this runtime. Use the host-side commands below for direct laptop inspection.</p>'}
      </section>
    `;
  }

  function renderCommands(payload) {
    const commands = Array.isArray(payload.recommended_host_commands) ? payload.recommended_host_commands : [];
    commandsNode.innerHTML = `
      <section class="agent-console__table-block">
        <h4>Recommended laptop commands</h4>
        <p class="agent-console__meta">These are the commands to run directly on your Mac when you want the same Ollama model identity plus host CPU/RAM snapshots.</p>
        <div class="agent-console__metric-records">
          ${commands.map((command, index) => `
            <article class="agent-console__detail-card">
              <h3>Command ${index + 1}</h3>
              <pre>${escapeHtml(command)}</pre>
            </article>
          `).join('')}
        </div>
      </section>
    `;
  }

  function buildReportContext(reportType) {
    const payload = lastPayload || {};
    const models = Array.isArray(payload.loaded_models) ? payload.loaded_models : [];
    const processMetrics = payload.host_process_metrics || {};
    const processes = Array.isArray(processMetrics.processes) ? processMetrics.processes : [];
    const commands = Array.isArray(payload.recommended_host_commands) ? payload.recommended_host_commands : [];
    const primary = models[0] || null;
    return {
      reportType,
      reportLabel: reportType === 'model-inventory' ? 'Model Inventory Pack' : 'Capacity Snapshot',
      generatedAt: new Date(),
      configuredModelName: payload.configured_model_name || '—',
      ollamaBaseUrl: payload.ollama_base_url || '—',
      apiReachable: payload.api_reachable ? 'Reachable' : 'Unavailable',
      checkedAt: formatTimestamp(payload.checked_at),
      primary,
      models,
      processMetrics,
      processes,
      commands,
      apiError: payload.api_error || ''
    };
  }

  function exportLlmCsv(context) {
    const rows = [
      ['Section', 'Field', 'Value'],
      ['summary', 'report_type', context.reportLabel],
      ['summary', 'generated_at', context.generatedAt.toISOString()],
      ['summary', 'configured_model_name', context.configuredModelName],
      ['summary', 'ollama_base_url', context.ollamaBaseUrl],
      ['summary', 'api_reachable', context.apiReachable],
      ['summary', 'checked_at', context.checkedAt],
      ['summary', 'api_error', context.apiError],
      [],
      ['loaded_models', 'name', 'parameter_size', 'quantization_level', 'size_vram_gib', 'context_length', 'expires_at'],
      ...context.models.map((model) => ['loaded_models', model.name || '', model.parameter_size || '', model.quantization_level || '', model.size_vram_gib ?? '', model.context_length ?? '', model.expires_at || '']),
      [],
      ['processes', 'pid', 'cpu_percent', 'mem_percent', 'rss_mb', 'vsz_mb', 'elapsed', 'command'],
      ...context.processes.map((process) => ['processes', process.pid ?? '', process.cpu_percent ?? '', process.mem_percent ?? '', process.rss_mb ?? '', process.vsz_mb ?? '', process.elapsed || '', process.command || '']),
      [],
      ['recommended_host_commands', 'command'],
      ...context.commands.map((command) => ['recommended_host_commands', command])
    ];
    downloadBlob(`openshift-sre-llm-${context.reportType}-${createTimestampSlug()}.csv`, new Blob([toCsv(rows)], { type: 'text/csv;charset=utf-8' }));
  }

  async function exportLlmPpt(context) {
    const PptxGenJS = window.PptxGenJS;
    if (!PptxGenJS) {
      throw new Error('PowerPoint export library is not available on this page right now.');
    }
    const pptx = new PptxGenJS();
    pptx.layout = 'LAYOUT_WIDE';
    pptx.author = 'GitHub Copilot';
    pptx.company = 'OpenShift SRE Local Agent';
    pptx.subject = context.reportLabel;
    pptx.title = `${context.reportLabel} - ${context.configuredModelName}`;

    const titleSlide = pptx.addSlide();
    titleSlide.background = { color: 'F8FAFC' };
    titleSlide.addText(context.reportLabel, { x: 0.5, y: 0.5, w: 6.4, h: 0.5, fontSize: 24, bold: true, color: '0F172A' });
    titleSlide.addText(`${context.configuredModelName} • ${context.generatedAt.toLocaleString()}`, { x: 0.5, y: 1.1, w: 7.0, h: 0.3, fontSize: 14, color: '2563EB' });
    titleSlide.addText(`Ollama base URL: ${context.ollamaBaseUrl}\nAPI reachability: ${context.apiReachable}\nChecked at: ${context.checkedAt}`, { x: 0.5, y: 1.7, w: 5.6, h: 1.8, fontSize: 13, color: '334155', breakLine: true });
    titleSlide.addText(context.primary ? `Loaded model: ${context.primary.name}\nVRAM: ${context.primary.size_vram_gib == null ? '—' : `${formatNumber(context.primary.size_vram_gib)} GiB`}\nContext length: ${context.primary.context_length == null ? '—' : formatNumber(context.primary.context_length)}` : 'No model was loaded at export time.', { x: 6.8, y: 1.4, w: 5.2, h: 2.0, fontSize: 13, color: '0F172A', margin: 0.12, fill: { color: 'DBEAFE' }, line: { color: '93C5FD' } });

    const inventorySlide = pptx.addSlide();
    inventorySlide.addText('Loaded model inventory', { x: 0.5, y: 0.4, w: 6.2, h: 0.4, fontSize: 20, bold: true, color: '0F172A' });
    inventorySlide.addText((context.models.length > 0 ? context.models : [{ name: 'No models loaded', parameter_size: '—', quantization_level: '—', size_vram_gib: '—', context_length: '—' }]).map((model) => `• ${model.name} — ${model.parameter_size || '—'} · ${model.quantization_level || '—'} · VRAM ${model.size_vram_gib == null ? '—' : `${formatNumber(model.size_vram_gib)} GiB`} · Context ${model.context_length == null ? '—' : formatNumber(model.context_length)}`).join('\n'), { x: 0.5, y: 1.0, w: 5.8, h: 4.8, fontSize: 12, color: '0F172A', margin: 0.12, fill: { color: 'FFFFFF' }, line: { color: 'CBD5E1' } });
    inventorySlide.addText((context.commands.length > 0 ? context.commands : ['No host commands were returned.']).map((command) => `• ${command}`).join('\n'), { x: 6.7, y: 1.0, w: 5.4, h: 4.8, fontSize: 11, color: '0F172A', margin: 0.12, fill: { color: 'FFFFFF' }, line: { color: 'CBD5E1' } });

    await pptx.writeFile({ fileName: `openshift-sre-llm-${context.reportType}-${createTimestampSlug()}.pptx` });
  }

  async function exportLlmPdf(context) {
    const jsPDF = window.jspdf?.jsPDF;
    if (!jsPDF) {
      throw new Error('PDF export library is not available on this page right now.');
    }
    const doc = new jsPDF({ unit: 'pt', format: 'a4' });
    const pageWidth = doc.internal.pageSize.getWidth();
    let cursorY = 56;
    const addBlock = (title, lines = []) => {
      const filtered = lines.filter(Boolean);
      if (filtered.length === 0) {
        return;
      }
      if (cursorY > 720) {
        doc.addPage();
        cursorY = 56;
      }
      doc.setFont('helvetica', 'bold');
      doc.setFontSize(13);
      doc.text(title, 48, cursorY);
      cursorY += 18;
      doc.setFont('helvetica', 'normal');
      doc.setFontSize(11);
      const wrapped = doc.splitTextToSize(filtered.map((line) => `• ${line}`).join('\n'), pageWidth - 96);
      doc.text(wrapped, 48, cursorY);
      cursorY += wrapped.length * 14 + 18;
    };
    doc.setFont('helvetica', 'bold');
    doc.setFontSize(22);
    doc.text(context.reportLabel, 48, cursorY);
    cursorY += 22;
    doc.setFontSize(12);
    doc.setFont('helvetica', 'normal');
    doc.text(`${context.configuredModelName} • ${context.generatedAt.toLocaleString()}`, 48, cursorY);
    cursorY += 24;
    addBlock('Runtime summary', [
      `Ollama base URL: ${context.ollamaBaseUrl}`,
      `API reachability: ${context.apiReachable}`,
      `Checked at: ${context.checkedAt}`,
      context.apiError ? `API error: ${context.apiError}` : ''
    ]);
    addBlock('Loaded models', context.models.length > 0 ? context.models.map((model) => `${model.name} — ${model.parameter_size || '—'} · ${model.quantization_level || '—'} · VRAM ${model.size_vram_gib == null ? '—' : `${formatNumber(model.size_vram_gib)} GiB`} · Context ${model.context_length == null ? '—' : formatNumber(model.context_length)}`) : ['No models were loaded.']);
    addBlock('Process visibility', [
      `Scope: ${context.processMetrics.scope || 'unknown'}`,
      `Available: ${context.processMetrics.available ? 'Yes' : 'No'}`,
      context.processMetrics.note || ''
    ]);
    addBlock('Host inspection commands', context.commands.length > 0 ? context.commands : ['No host commands were returned.']);
    doc.save(`openshift-sre-llm-${context.reportType}-${createTimestampSlug()}.pdf`);
  }

  async function exportLlmWord(context) {
    const html = `<!doctype html>
<html>
  <head>
    <meta charset="utf-8">
    <title>${escapeHtml(context.reportLabel)}</title>
    <style>
      body { font-family: Arial, sans-serif; color: #0f172a; margin: 32px; }
      h1, h2 { color: #0f172a; }
      .meta { color: #475569; margin-bottom: 18px; }
      .section { margin-top: 22px; }
      ul { margin: 8px 0 0 20px; }
      li { margin: 4px 0; }
      .chip { display: inline-block; margin-right: 8px; margin-bottom: 8px; padding: 4px 10px; border-radius: 999px; background: #dbeafe; color: #1d4ed8; font-size: 12px; }
    </style>
  </head>
  <body>
    <h1>${escapeHtml(context.reportLabel)}</h1>
    <p class="meta">${escapeHtml(context.configuredModelName)} · ${escapeHtml(context.generatedAt.toLocaleString())}</p>
    <div>
      <span class="chip">API: ${escapeHtml(context.apiReachable)}</span>
      <span class="chip">Loaded models: ${escapeHtml(context.models.length)}</span>
      <span class="chip">Checked: ${escapeHtml(context.checkedAt)}</span>
    </div>
    <div class="section">
      <h2>Loaded models</h2>
      <ul>${(context.models.length > 0 ? context.models.map((model) => `${model.name} — ${model.parameter_size || '—'} · ${model.quantization_level || '—'} · VRAM ${model.size_vram_gib == null ? '—' : `${formatNumber(model.size_vram_gib)} GiB`} · Context ${model.context_length == null ? '—' : formatNumber(model.context_length)}`) : ['No models were loaded.']).map((line) => `<li>${escapeHtml(line)}</li>`).join('')}</ul>
    </div>
    <div class="section">
      <h2>Process visibility</h2>
      <ul>
        <li>Scope: ${escapeHtml(context.processMetrics.scope || 'unknown')}</li>
        <li>Available: ${escapeHtml(context.processMetrics.available ? 'Yes' : 'No')}</li>
        <li>${escapeHtml(context.processMetrics.note || 'No additional process note was returned.')}</li>
      </ul>
    </div>
    <div class="section">
      <h2>Host inspection commands</h2>
      <ul>${(context.commands.length > 0 ? context.commands : ['No host commands were returned.']).map((line) => `<li>${escapeHtml(line)}</li>`).join('')}</ul>
    </div>
  </body>
</html>`;
    downloadBlob(`openshift-sre-llm-${context.reportType}-${createTimestampSlug()}.doc`, new Blob([html], { type: 'application/msword' }));
  }

  function updateReportExportState() {
    const hasPayload = Boolean(lastPayload);
    reportExportButtons.forEach((button) => {
      const isExporting = button.dataset.llmExporting === 'true';
      button.disabled = !hasPayload || isExporting;
    });
    if (!hasPayload) {
      setReportStatus('Refresh utilization to unlock LLM runtime report exports.');
    }
  }

  async function handleReportExport(button) {
    if (!button || !lastPayload) {
      setReportStatus('Refresh utilization first so there is live runtime content to export.', 'error');
      return;
    }
    const reportType = button.dataset.llmExportReport || 'capacity-snapshot';
    const format = button.dataset.llmExportFormat || 'word';
    const context = buildReportContext(reportType);
    const originalLabel = button.textContent;
    button.dataset.llmExporting = 'true';
    button.textContent = `Preparing ${format.toUpperCase()}…`;
    updateReportExportState();
    setReportStatus(`Building ${context.reportLabel} as ${format.toUpperCase()}…`, 'ok');
    try {
      if (format === 'csv') {
        exportLlmCsv(context);
      } else if (format === 'ppt') {
        await exportLlmPpt(context);
      } else if (format === 'pdf') {
        await exportLlmPdf(context);
      } else {
        await exportLlmWord(context);
      }
      setReportStatus(`${context.reportLabel} exported as ${format.toUpperCase()}.`, 'ok');
    } catch (error) {
      setReportStatus(error instanceof Error ? error.message : `Unable to export ${context.reportLabel}.`, 'error');
    } finally {
      button.dataset.llmExporting = 'false';
      button.textContent = originalLabel;
      updateReportExportState();
    }
  }

  async function loadUtilization() {
    refreshButton.disabled = true;
    setStatus('Loading Ollama utilization…');
    try {
      const response = await fetch('/ollama/utilization');
      const payload = await response.json();
      if (!response.ok) {
        throw new Error(payload.detail || `Utilization request failed with status ${response.status}`);
      }
      lastPayload = payload;
      renderSummary(payload);
      renderModels(payload);
      renderProcesses(payload);
      renderCommands(payload);
      updateReportExportState();
      setStatus('LLM utilization refreshed.', 'ok');
    } catch (error) {
      lastPayload = null;
      const message = error instanceof Error ? error.message : 'Unable to load Ollama utilization.';
      setStatus(message, 'error');
      [summaryNode, modelsNode, processesNode, commandsNode].forEach((node) => renderMessage(node, message));
      updateReportExportState();
    } finally {
      refreshButton.disabled = false;
    }
  }

  refreshButton.addEventListener('click', loadUtilization);
  themeToggleButton.addEventListener('click', () => applyTheme(document.body.dataset.theme === 'dark' ? 'light' : 'dark'));
  reportExportButtons.forEach((button) => button.addEventListener('click', () => handleReportExport(button)));

  initializeTheme();
  updateReportExportState();
  loadUtilization();
})();
