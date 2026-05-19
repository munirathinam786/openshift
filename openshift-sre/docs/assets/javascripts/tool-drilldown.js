(() => {
  const root = document.querySelector('[data-tool-drilldown]');
  if (!root) {
    return;
  }

  const statusNode = root.querySelector('[data-tool-status]');
  const summaryNode = root.querySelector('[data-tool-summary]');
  const latestNode = root.querySelector('[data-tool-latest]');
  const trendsNode = root.querySelector('[data-tool-trends]');
  const invocationsNode = root.querySelector('[data-tool-invocations]');
  const refreshButton = document.querySelector('[data-tool-refresh]');
  const themeToggleButton = document.querySelector('[data-tool-theme-toggle]');
  const toolSelect = document.querySelector('[data-tool-name]');
  const rangeSelect = document.querySelector('[data-tool-range]');
  const modelSelect = document.querySelector('[data-tool-models]');
  const regionSelect = document.querySelector('[data-tool-regions]');
  const activeToolNode = document.querySelector('[data-tool-active-name]');
  const activeModelNode = document.querySelector('[data-tool-active-models]');
  const activeRegionNode = document.querySelector('[data-tool-active-regions]');
  const lastRefreshNode = document.querySelector('[data-tool-last-refresh]');
  const reportExportButtons = document.querySelectorAll('[data-tool-export-report]');
  const reportStatusNode = document.querySelector('[data-tool-report-status]');
  const themeStorageKey = 'aws-sre-history-theme';
  const params = new URLSearchParams(window.location.search);
  let lastToolPayload = null;

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
      return 'Live drilldown data is unavailable in static preview. Open this page through the running app on http://127.0.0.1:8000/ or start the local stack to enable API-backed panels.';
    }

    return raw;
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

  function formatNumber(value) {
    const numeric = Number(value);
    if (!Number.isFinite(numeric)) {
      return String(value ?? '');
    }
    return new Intl.NumberFormat(undefined, { maximumFractionDigits: 2 }).format(numeric);
  }

  function formatMetricValue(value, unit) {
    return unit ? `${formatNumber(value)} ${unit}` : formatNumber(value);
  }

  function formatTimestamp(value) {
    return value ? new Date(value).toLocaleString() : '—';
  }

  function formatDuration(value) {
    return `${formatNumber(value)} ms`;
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

  function getSelectedValues(selectNode) {
    return Array.from(selectNode.selectedOptions).map((option) => option.value).filter(Boolean);
  }

  function setSelectedValues(selectNode, values) {
    const selected = new Set(values || []);
    Array.from(selectNode.options).forEach((option) => {
      option.selected = selected.has(option.value);
    });
  }

  function updateOptions(selectNode, values, keepSelected = true) {
    const previous = keepSelected ? getSelectedValues(selectNode) : [];
    const normalized = Array.from(new Set((values || []).filter(Boolean)));
    selectNode.innerHTML = normalized.map((value) => `<option value="${escapeHtml(value)}">${escapeHtml(value)}</option>`).join('');
    setSelectedValues(selectNode, previous.filter((value) => normalized.includes(value)));
  }

  function formatSelectionLabel(values, emptyLabel) {
    if (!values || values.length === 0) return emptyLabel;
    if (values.length <= 2) return values.join(', ');
    return `${values.length} selected`;
  }

  function applyTheme(theme) {
    document.body.dataset.theme = theme === 'dark' ? 'dark' : 'light';
    window.localStorage.setItem(themeStorageKey, document.body.dataset.theme);
    themeToggleButton.textContent = document.body.dataset.theme === 'dark' ? 'Light mode' : 'Dark mode';
  }

  function initializeTheme() {
    applyTheme(window.localStorage.getItem(themeStorageKey) === 'dark' ? 'dark' : 'light');
  }

  function updateActiveLabels() {
    activeToolNode.textContent = toolSelect.value || '—';
    activeModelNode.textContent = formatSelectionLabel(getSelectedValues(modelSelect), 'All models');
    activeRegionNode.textContent = formatSelectionLabel(getSelectedValues(regionSelect), 'All regions');
    lastRefreshNode.textContent = new Date().toLocaleTimeString();
  }

  function createSparkline(points) {
    if (!Array.isArray(points) || points.length === 0) {
      return '';
    }
    const width = 280;
    const height = 110;
    const padding = 14;
    const values = points.map((point) => Number(point.metric_value ?? 0));
    const min = Math.min(...values);
    const max = Math.max(...values);
    const range = max - min || 1;
    const stepX = points.length > 1 ? (width - padding * 2) / (points.length - 1) : 0;
    const line = points.map((point, index) => {
      const x = padding + (stepX * index);
      const y = height - padding - (((Number(point.metric_value ?? 0) - min) / range) * (height - padding * 2));
      return `${x},${y}`;
    }).join(' ');
    return `
      <svg viewBox="0 0 ${width} ${height}" class="agent-console__sparkline" role="img" aria-label="tool metric trend">
        <line x1="${padding}" y1="${height - padding}" x2="${width - padding}" y2="${height - padding}" class="agent-console__sparkline-axis"></line>
        <polyline fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round" points="${line}"></polyline>
      </svg>
    `;
  }

  async function loadToolOptions() {
    const response = await fetch('/history/overview?time_range=all&run_limit=1&point_limit=1&series_limit=1');
    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload.detail || 'Unable to load tool options.');
    }
    updateOptions(toolSelect, payload.filter_options?.tools || [], false);
    if (!toolSelect.value) {
      const fromQuery = params.get('tool');
      if (fromQuery && Array.from(toolSelect.options).some((option) => option.value === fromQuery)) {
        toolSelect.value = fromQuery;
      } else if (toolSelect.options.length > 0) {
        toolSelect.value = toolSelect.options[0].value;
      }
    }
  }

  function renderSummary(payload) {
    const summary = payload.summary || {};
    summaryNode.innerHTML = `
      <div class="agent-console__history-card-grid">
        <article class="agent-console__history-card"><p class="agent-console__history-card-label">Invocations</p><p class="agent-console__history-card-value">${formatNumber(summary.invocation_count ?? 0)}</p></article>
        <article class="agent-console__history-card"><p class="agent-console__history-card-label">Distinct runs</p><p class="agent-console__history-card-value">${formatNumber(summary.distinct_runs ?? 0)}</p></article>
        <article class="agent-console__history-card"><p class="agent-console__history-card-label">Failed invocations</p><p class="agent-console__history-card-value">${formatNumber(summary.failed_invocations ?? 0)}</p></article>
        <article class="agent-console__history-card"><p class="agent-console__history-card-label">Average duration</p><p class="agent-console__history-card-value">${summary.average_duration_ms == null ? '—' : formatDuration(summary.average_duration_ms)}</p></article>
        <article class="agent-console__history-card"><p class="agent-console__history-card-label">Last invoked</p><p class="agent-console__history-card-value agent-console__history-card-value--small">${formatTimestamp(summary.last_invoked_at)}</p></article>
      </div>
    `;
  }

  function renderLatestMetrics(payload) {
    const latestMetrics = payload.latest_metrics || [];
    if (latestMetrics.length === 0) {
      renderMessage(latestNode, 'No numeric metrics are stored for this tool yet.');
      return;
    }
    latestNode.innerHTML = `
      <section class="agent-console__table-block">
        <table class="agent-console__table">
          <thead><tr><th>Metric</th><th>Latest value</th><th>Recorded at</th></tr></thead>
          <tbody>
            ${latestMetrics.map((metric) => `
              <tr>
                <td>${escapeHtml(metric.metric_label)}</td>
                <td>${formatMetricValue(metric.metric_value, metric.unit)}</td>
                <td>${formatTimestamp(metric.recorded_at)}</td>
              </tr>
            `).join('')}
          </tbody>
        </table>
      </section>
    `;
  }

  function renderTrends(payload) {
    const series = payload.metric_series || [];
    if (series.length === 0) {
      renderMessage(trendsNode, 'No metric trend lines are available for this tool.');
      return;
    }
    trendsNode.innerHTML = series.map((seriesItem) => {
      const latest = seriesItem.points?.[seriesItem.points.length - 1];
      return `
        <article class="agent-console__trend-card">
          <div class="agent-console__trend-header">
            <div>
              <h4>${escapeHtml(seriesItem.metric_label)}</h4>
              <p class="agent-console__meta">${escapeHtml(payload.tool_label)}</p>
            </div>
            <p class="agent-console__trend-value">${latest ? formatMetricValue(latest.metric_value, seriesItem.unit) : '—'}</p>
          </div>
          ${createSparkline(seriesItem.points || [])}
        </article>
      `;
    }).join('');
  }

  function renderInvocations(payload) {
    const invocations = payload.recent_invocations || [];
    if (invocations.length === 0) {
      renderMessage(invocationsNode, 'No invocations were found for this tool and filter combination.');
      return;
    }
    invocationsNode.innerHTML = `
      <section class="agent-console__table-block">
        <table class="agent-console__table">
          <thead>
            <tr>
              <th>When</th>
              <th>Status</th>
              <th>Model</th>
              <th>Region</th>
              <th>Prompt</th>
              <th>Details</th>
            </tr>
          </thead>
          <tbody>
            ${invocations.map((row) => `
              <tr>
                <td>${formatTimestamp(row.created_at)}</td>
                <td>${escapeHtml(row.status)}</td>
                <td>${escapeHtml(row.model_name)}</td>
                <td>${escapeHtml(row.aws_region)}</td>
                <td>${escapeHtml(row.prompt_excerpt || '—')}</td>
                <td>
                  <details class="agent-console__step">
                    <summary>Open</summary>
                    <div class="agent-console__step-body">
                      <p><strong>Thought:</strong> ${escapeHtml(row.thought || '—')}</p>
                      <p><strong>Arguments:</strong></p>
                      <pre>${escapeHtml(JSON.stringify(row.tool_arguments ?? {}, null, 2))}</pre>
                      <p><strong>Result:</strong></p>
                      <pre>${escapeHtml(JSON.stringify(row.tool_result ?? {}, null, 2))}</pre>
                      ${row.tool_error ? `<p><strong>Error:</strong> ${escapeHtml(row.tool_error)}</p>` : ''}
                      <p><a class="agent-console__inline-link" href="history.html">Open run ${row.run_id} in historical dashboard</a></p>
                    </div>
                  </details>
                </td>
              </tr>
            `).join('')}
          </tbody>
        </table>
      </section>
    `;
  }

  function buildReportContext(reportType) {
    const payload = lastToolPayload || { summary: {} };
    const summary = payload.summary || {};
    const latestMetrics = Array.isArray(payload.latest_metrics) ? payload.latest_metrics.slice(0, 8) : [];
    const metricSeries = Array.isArray(payload.metric_series) ? payload.metric_series.slice(0, 8) : [];
    const invocations = Array.isArray(payload.recent_invocations) ? payload.recent_invocations.slice(0, 8) : [];
    return {
      reportType,
      reportLabel: reportType === 'invocation-evidence' ? 'Invocation Evidence Pack' : 'Tool Performance Report',
      generatedAt: new Date(),
      toolLabel: payload.tool_label || toolSelect.value || 'Selected tool',
      toolName: payload.tool_name || toolSelect.value || '',
      summary,
      latestMetrics,
      metricSeries,
      invocations,
      filters: payload.filters || {}
    };
  }

  function exportToolCsv(context) {
    const rows = [
      ['Section', 'Field', 'Value'],
      ['summary', 'report_type', context.reportLabel],
      ['summary', 'generated_at', context.generatedAt.toISOString()],
      ['summary', 'tool_name', context.toolName],
      ['summary', 'tool_label', context.toolLabel],
      ['summary', 'time_range', context.filters.time_range || rangeSelect.value],
      ['summary', 'model_names', (context.filters.model_names || []).join('|')],
      ['summary', 'aws_regions', (context.filters.aws_regions || []).join('|')],
      ['summary', 'invocation_count', context.summary.invocation_count ?? 0],
      ['summary', 'distinct_runs', context.summary.distinct_runs ?? 0],
      ['summary', 'failed_invocations', context.summary.failed_invocations ?? 0],
      ['summary', 'average_duration_ms', context.summary.average_duration_ms ?? ''],
      [],
      ['latest_metrics', 'metric_label', 'metric_value', 'unit', 'recorded_at'],
      ...context.latestMetrics.map((metric) => ['latest_metrics', metric.metric_label, metric.metric_value, metric.unit || '', metric.recorded_at || '']),
      [],
      ['invocations', 'created_at', 'status', 'model_name', 'aws_region', 'prompt_excerpt', 'thought', 'tool_error'],
      ...context.invocations.map((row) => ['invocations', row.created_at || '', row.status || '', row.model_name || '', row.aws_region || '', row.prompt_excerpt || '', row.thought || '', row.tool_error || ''])
    ];
    downloadBlob(`aws-sre-tool-${context.toolName || 'selected'}-${context.reportType}-${createTimestampSlug()}.csv`, new Blob([toCsv(rows)], { type: 'text/csv;charset=utf-8' }));
  }

  async function exportToolPpt(context) {
    const PptxGenJS = window.PptxGenJS;
    if (!PptxGenJS) {
      throw new Error('PowerPoint export library is not available on this page right now.');
    }
    const pptx = new PptxGenJS();
    pptx.layout = 'LAYOUT_WIDE';
    pptx.author = 'GitHub Copilot';
    pptx.company = 'AWS SRE Local Agent';
    pptx.subject = context.reportLabel;
    pptx.title = `${context.reportLabel} - ${context.toolLabel}`;

    const titleSlide = pptx.addSlide();
    titleSlide.background = { color: 'F8FAFC' };
    titleSlide.addText(context.reportLabel, { x: 0.5, y: 0.5, w: 6.6, h: 0.5, fontSize: 24, bold: true, color: '0F172A' });
    titleSlide.addText(`${context.toolLabel} • ${context.generatedAt.toLocaleString()}`, { x: 0.5, y: 1.1, w: 7.4, h: 0.3, fontSize: 14, color: '2563EB' });
    titleSlide.addText(`Invocations: ${formatNumber(context.summary.invocation_count ?? 0)}\nDistinct runs: ${formatNumber(context.summary.distinct_runs ?? 0)}\nFailed invocations: ${formatNumber(context.summary.failed_invocations ?? 0)}\nAverage duration: ${context.summary.average_duration_ms == null ? '—' : formatDuration(context.summary.average_duration_ms)}`, { x: 0.5, y: 1.7, w: 5.8, h: 2.2, fontSize: 13, color: '334155', breakLine: true });
    titleSlide.addText((context.latestMetrics.length > 0 ? context.latestMetrics.map((metric) => `${metric.metric_label}: ${formatMetricValue(metric.metric_value, metric.unit)}`) : ['No latest metrics were available.']).map((line) => `• ${line}`).join('\n'), { x: 6.8, y: 1.5, w: 5.2, h: 2.8, fontSize: 12, color: '0F172A', margin: 0.12, fill: { color: 'DBEAFE' }, line: { color: '93C5FD' } });

    const metricsSlide = pptx.addSlide();
    metricsSlide.addText('Metric trends and latest signals', { x: 0.5, y: 0.4, w: 6.4, h: 0.4, fontSize: 20, bold: true, color: '0F172A' });
    metricsSlide.addText((context.metricSeries.length > 0 ? context.metricSeries.map((seriesItem) => `${seriesItem.metric_label}: ${seriesItem.points?.length || 0} samples`) : ['No trend series were available.']).map((line) => `• ${line}`).join('\n'), { x: 0.5, y: 1.0, w: 5.8, h: 4.8, fontSize: 12, color: '0F172A', margin: 0.12, fill: { color: 'FFFFFF' }, line: { color: 'CBD5E1' } });
    metricsSlide.addText((context.invocations.length > 0 ? context.invocations.map((row) => `${formatTimestamp(row.created_at)} · ${row.status} · ${row.model_name} · ${row.aws_region}`) : ['No invocation evidence was available.']).map((line) => `• ${line}`).join('\n'), { x: 6.7, y: 1.0, w: 5.4, h: 4.8, fontSize: 11, color: '0F172A', margin: 0.12, fill: { color: 'FFFFFF' }, line: { color: 'CBD5E1' } });

    await pptx.writeFile({ fileName: `aws-sre-tool-${context.toolName || 'selected'}-${context.reportType}-${createTimestampSlug()}.pptx` });
  }

  async function exportToolPdf(context) {
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
    doc.text(`${context.toolLabel} • ${context.generatedAt.toLocaleString()}`, 48, cursorY);
    cursorY += 24;
    addBlock('Tool summary', [
      `Invocations: ${formatNumber(context.summary.invocation_count ?? 0)}`,
      `Distinct runs: ${formatNumber(context.summary.distinct_runs ?? 0)}`,
      `Failed invocations: ${formatNumber(context.summary.failed_invocations ?? 0)}`,
      `Average duration: ${context.summary.average_duration_ms == null ? '—' : formatDuration(context.summary.average_duration_ms)}`
    ]);
    addBlock('Latest metrics', context.latestMetrics.length > 0 ? context.latestMetrics.map((metric) => `${metric.metric_label}: ${formatMetricValue(metric.metric_value, metric.unit)}`) : ['No latest metrics were available.']);
    addBlock('Recent invocations', context.invocations.length > 0 ? context.invocations.map((row) => `${formatTimestamp(row.created_at)} · ${row.status} · ${row.model_name} · ${row.aws_region} · ${row.prompt_excerpt || 'No prompt excerpt'}`) : ['No invocation evidence was available.']);
    doc.save(`aws-sre-tool-${context.toolName || 'selected'}-${context.reportType}-${createTimestampSlug()}.pdf`);
  }

  async function exportToolWord(context) {
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
    <p class="meta">${escapeHtml(context.toolLabel)} · ${escapeHtml(context.generatedAt.toLocaleString())}</p>
    <div>
      <span class="chip">Invocations: ${escapeHtml(formatNumber(context.summary.invocation_count ?? 0))}</span>
      <span class="chip">Failed: ${escapeHtml(formatNumber(context.summary.failed_invocations ?? 0))}</span>
      <span class="chip">Avg duration: ${escapeHtml(context.summary.average_duration_ms == null ? '—' : formatDuration(context.summary.average_duration_ms))}</span>
    </div>
    <div class="section">
      <h2>Latest metrics</h2>
      <ul>${(context.latestMetrics.length > 0 ? context.latestMetrics.map((metric) => `${metric.metric_label}: ${formatMetricValue(metric.metric_value, metric.unit)}`) : ['No latest metrics were available.']).map((line) => `<li>${escapeHtml(line)}</li>`).join('')}</ul>
    </div>
    <div class="section">
      <h2>Recent invocations</h2>
      <ul>${(context.invocations.length > 0 ? context.invocations.map((row) => `${formatTimestamp(row.created_at)} · ${row.status} · ${row.model_name} · ${row.aws_region} · ${row.prompt_excerpt || 'No prompt excerpt'}`) : ['No invocation evidence was available.']).map((line) => `<li>${escapeHtml(line)}</li>`).join('')}</ul>
    </div>
  </body>
</html>`;
    downloadBlob(`aws-sre-tool-${context.toolName || 'selected'}-${context.reportType}-${createTimestampSlug()}.doc`, new Blob([html], { type: 'application/msword' }));
  }

  function updateReportExportState() {
    const hasPayload = Boolean(lastToolPayload);
    reportExportButtons.forEach((button) => {
      const isExporting = button.dataset.toolExporting === 'true';
      button.disabled = !hasPayload || isExporting;
    });
    if (!hasPayload) {
      setReportStatus('Refresh the tool drilldown to unlock report exports.');
    }
  }

  async function handleReportExport(button) {
    if (!button || !lastToolPayload) {
      setReportStatus('Refresh the tool drilldown first so there is live data to export.', 'error');
      return;
    }
    const reportType = button.dataset.toolExportReport || 'tool-performance';
    const format = button.dataset.toolExportFormat || 'word';
    const context = buildReportContext(reportType);
    const originalLabel = button.textContent;
    button.dataset.toolExporting = 'true';
    button.textContent = `Preparing ${format.toUpperCase()}…`;
    updateReportExportState();
    setReportStatus(`Building ${context.reportLabel} as ${format.toUpperCase()}…`, 'ok');
    try {
      if (format === 'csv') {
        exportToolCsv(context);
      } else if (format === 'ppt') {
        await exportToolPpt(context);
      } else if (format === 'pdf') {
        await exportToolPdf(context);
      } else {
        await exportToolWord(context);
      }
      setReportStatus(`${context.reportLabel} exported as ${format.toUpperCase()}.`, 'ok');
    } catch (error) {
      setReportStatus(error instanceof Error ? error.message : `Unable to export ${context.reportLabel}.`, 'error');
    } finally {
      button.dataset.toolExporting = 'false';
      button.textContent = originalLabel;
      updateReportExportState();
    }
  }

  async function loadToolDetail() {
    refreshButton.disabled = true;
    setStatus('Loading tool drilldown…');
    try {
      if (toolSelect.options.length === 0) {
        await loadToolOptions();
      }
      if (!toolSelect.value) {
        throw new Error('No recorded tools are available yet.');
      }
      const query = new URLSearchParams({
        time_range: rangeSelect.value,
        run_limit: '25',
        point_limit: '24',
      });
      const modelNames = getSelectedValues(modelSelect);
      const regionNames = getSelectedValues(regionSelect);
      if (modelNames.length > 0) query.set('model_names', modelNames.join(','));
      if (regionNames.length > 0) query.set('aws_regions', regionNames.join(','));
      const response = await fetch(`/history/tools/${encodeURIComponent(toolSelect.value)}?${query.toString()}`);
      const payload = await response.json();
      if (!response.ok) {
        throw new Error(payload.detail || `Tool drilldown request failed with status ${response.status}`);
      }
      lastToolPayload = payload;
      updateOptions(modelSelect, payload.filter_options?.models || []);
      updateOptions(regionSelect, payload.filter_options?.regions || []);
      setSelectedValues(modelSelect, payload.filters?.model_names || getSelectedValues(modelSelect));
      setSelectedValues(regionSelect, payload.filters?.aws_regions || getSelectedValues(regionSelect));
      renderSummary(payload);
      renderLatestMetrics(payload);
      renderTrends(payload);
      renderInvocations(payload);
      updateReportExportState();
      updateActiveLabels();
      setStatus(`Showing drilldown for ${payload.tool_label}.`, 'ok');
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Unable to load tool drilldown.';
      setStatus(message, 'error');
      [summaryNode, latestNode, trendsNode, invocationsNode].forEach((node) => renderMessage(node, message));
      lastToolPayload = null;
      updateReportExportState();
    } finally {
      refreshButton.disabled = false;
    }
  }

  refreshButton.addEventListener('click', loadToolDetail);
  toolSelect.addEventListener('change', () => {
    params.set('tool', toolSelect.value);
    window.history.replaceState({}, '', `?${params.toString()}`);
    loadToolDetail();
  });
  rangeSelect.addEventListener('change', loadToolDetail);
  modelSelect.addEventListener('change', loadToolDetail);
  regionSelect.addEventListener('change', loadToolDetail);
  themeToggleButton.addEventListener('click', () => applyTheme(document.body.dataset.theme === 'dark' ? 'light' : 'dark'));
  reportExportButtons.forEach((button) => button.addEventListener('click', () => handleReportExport(button)));

  initializeTheme();
  updateReportExportState();
  loadToolOptions().then(loadToolDetail).catch((error) => {
    const message = error instanceof Error ? error.message : 'Unable to initialize the tool drilldown page.';
    setStatus(message, 'error');
    [summaryNode, latestNode, trendsNode, invocationsNode].forEach((node) => renderMessage(node, message));
  });
})();
