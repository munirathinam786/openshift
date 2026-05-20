(() => {
  const root = document.querySelector('[data-history-dashboard]');
  if (!root) {
    return;
  }

  const statusNode = root.querySelector('[data-history-status]');
  const badgesNode = root.querySelector('[data-history-badges]');
  const summaryNode = root.querySelector('[data-history-summary]');
  const benchmarkBoardNode = root.querySelector('[data-history-benchmarks]');
  const boardBriefNode = root.querySelector('[data-history-board-brief]');
  const storytellingNode = root.querySelector('[data-history-storytelling]');
  const percentilesNode = root.querySelector('[data-history-percentiles]');
  const exceptionsNode = root.querySelector('[data-history-exceptions]');
  const llmSummaryNode = root.querySelector('[data-history-llm-summary]');
  const statusChartNode = root.querySelector('[data-history-status-chart]');
  const durationChartNode = root.querySelector('[data-history-duration-chart]');
  const toolUsageNode = root.querySelector('[data-history-tool-usage]');
  const statusTimelineNode = root.querySelector('[data-history-status-timeline]');
  const modelComparisonNode = root.querySelector('[data-history-model-comparison]');
  const regionComparisonNode = root.querySelector('[data-history-region-comparison]');
  const trendsNode = root.querySelector('[data-history-trends]');
  const latestNode = root.querySelector('[data-history-latest]');
  const metricDetailNode = root.querySelector('[data-history-metric-detail]');
  const runsNode = root.querySelector('[data-history-runs]');
  const runDetailNode = root.querySelector('[data-history-run-detail]');
  const refreshButton = document.querySelector('[data-history-refresh]');
  const themeToggleButton = document.querySelector('[data-history-theme-toggle]');
  const exportCsvButton = document.querySelector('[data-history-export-csv]');
  const exportMetricCsvButton = document.querySelector('[data-history-export-metric-csv]');
  const exportPngButton = document.querySelector('[data-history-export-png]');
  const exportWeeklyReviewButton = document.querySelector('[data-history-export-weekly-review]');
  const reportExportButtons = document.querySelectorAll('[data-history-export-report]');
  const reportStatusNode = document.querySelector('[data-history-report-status]');
  const rangeSelect = document.querySelector('[data-history-range]');
  const modelSelect = document.querySelector('[data-history-model]');
  const regionSelect = document.querySelector('[data-history-region]');
  const toolSelect = document.querySelector('[data-history-tools]');
  const autoRefreshSelect = document.querySelector('[data-history-auto-refresh]');
  const slaSuccessInput = document.querySelector('[data-history-sla-success]');
  const slaDurationInput = document.querySelector('[data-history-sla-duration]');
  const exportLayoutSelect = document.querySelector('[data-history-export-layout]');
  const activeRangeNode = document.querySelector('[data-history-active-range]');
  const activeModelNode = document.querySelector('[data-history-active-model]');
  const activeRegionNode = document.querySelector('[data-history-active-region]');
  const activeToolNode = document.querySelector('[data-history-active-tool]');
  const activeSlaNode = document.querySelector('[data-history-active-sla]');
  const activeLayoutNode = document.querySelector('[data-history-active-layout]');
  const activeComparisonNode = document.querySelector('[data-history-active-comparison]');
  const lastRefreshNode = document.querySelector('[data-history-last-refresh]');

  let autoRefreshTimer = null;
  let lastPayload = null;
  let selectedMetricDetail = null;
  let selectedMetricKey = null;
  let selectedRunId = null;
  let sparklineSequence = 0;
  const themeStorageKey = 'openshift-sre-history-theme';

  const rangeLabels = {
    '24h': 'Last 24 hours',
    '7d': 'Last 7 days',
    '30d': 'Last 30 days',
    '90d': 'Last 90 days',
    all: 'All history',
  };

  const exportLayoutLabels = {
    standard: 'Standard dashboard',
    board: 'Board review',
    appendix: 'Appendix / dense detail',
  };

  const tooltipIcon = (message) => `<span class="agent-console__tooltip" tabindex="0" data-tooltip="${escapeHtml(message)}">ⓘ</span>`;

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
      return 'Live data is unavailable in static preview. Open this page through the running app on http://127.0.0.1:8000/ or start the local stack to enable API-backed panels.';
    }

    return raw;
  }

  function renderMessage(node, message) {
    const friendlyMessage = getFriendlyMessage(message);
    const isWarning = /failed to fetch|unavailable|unable|disabled/i.test(friendlyMessage);
    const title = isWarning ? 'Live data unavailable' : 'Nothing to show yet';
    const badge = isWarning ? 'Preview mode' : 'Waiting for signal';
    const hint = isWarning
      ? 'Open the running stack to unlock API-backed analytics, exports, and deeper drilldowns.'
      : 'Run a few prompts so the dashboard can build trends, comparisons, and executive summaries.';
    node.innerHTML = `
      <div class="agent-console__state ${isWarning ? 'agent-console__state--warning' : ''}">
        <div class="agent-console__state-badge"><span class="agent-console__state-orb" aria-hidden="true"></span>${escapeHtml(badge)}</div>
        <p class="agent-console__state-title">${escapeHtml(title)}</p>
        <p class="agent-console__state-copy">${escapeHtml(friendlyMessage)}</p>
        <p class="agent-console__state-hint">${escapeHtml(hint)}</p>
      </div>
    `;
  }

  function setMetricExportState(enabled) {
    exportMetricCsvButton.disabled = !enabled;
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

  function formatPercent(value) {
    return `${formatNumber(value)}%`;
  }

  function clamp(value, min, max) {
    return Math.min(max, Math.max(min, value));
  }

  function median(values) {
    if (!Array.isArray(values) || values.length === 0) {
      return null;
    }
    const ordered = values.filter((value) => Number.isFinite(value)).slice().sort((left, right) => left - right);
    if (ordered.length === 0) {
      return null;
    }
    const midpoint = Math.floor(ordered.length / 2);
    if (ordered.length % 2 === 0) {
      return (ordered[midpoint - 1] + ordered[midpoint]) / 2;
    }
    return ordered[midpoint];
  }

  function getSlaSettings() {
    const successTarget = clamp(Number(slaSuccessInput?.value || 99), 0, 100);
    const durationTargetMs = Math.max(1, Number(slaDurationInput?.value || 90000));
    return { successTarget, durationTargetMs };
  }

  function getSelectedExportLayout() {
    return exportLayoutSelect?.value || 'standard';
  }

  function formatSignedVariance(value, formatter, positiveIsGood = true) {
    if (!Number.isFinite(value) || value === 0) {
      return { text: 'On target', kind: 'neutral' };
    }
    const improved = positiveIsGood ? value > 0 : value < 0;
    return {
      text: `${value > 0 ? '+' : '−'}${formatter(Math.abs(value))} vs benchmark`,
      kind: improved ? 'positive' : 'negative',
    };
  }

  function formatDirectionalDelta(value, formatter, positiveIsGood = true, neutralText = 'Flat week over week') {
    if (!Number.isFinite(value) || value === 0) {
      return { text: neutralText, kind: 'neutral' };
    }
    const improved = positiveIsGood ? value > 0 : value < 0;
    return {
      text: `${value > 0 ? '+' : '−'}${formatter(Math.abs(value))} vs last week`,
      kind: improved ? 'positive' : 'negative',
    };
  }

  function computeOverviewStats(payload) {
    const summary = payload.summary || {};
    const totalRuns = Number(summary.total_runs ?? 0);
    const failedRuns = Number(summary.failed_runs ?? 0);
    const completedRuns = Math.max(0, totalRuns - failedRuns);
    const successRate = totalRuns ? (completedRuns / totalRuns) * 100 : 0;
    const averageDuration = Number(summary.average_duration_ms ?? 0);
    return { totalRuns, failedRuns, completedRuns, successRate, averageDuration };
  }

  function computeExecutiveSignals(payload) {
    const stats = computeOverviewStats(payload);
    const modelRows = Array.isArray(payload.model_breakdown) ? payload.model_breakdown : [];
    const regionRows = Array.isArray(payload.region_breakdown) ? payload.region_breakdown : [];
    const latestMetrics = Array.isArray(payload.latest_metrics) ? payload.latest_metrics : [];
    const recentRuns = Array.isArray(payload.recent_runs) ? payload.recent_runs : [];
    const breakdownRows = [...modelRows, ...regionRows];
    const benchmarkSuccess = breakdownRows.length > 0
      ? Math.max(...breakdownRows.map((row) => Number(row.success_rate ?? 0)), stats.successRate)
      : stats.successRate;
    const benchmarkDuration = median([
      ...breakdownRows.map((row) => Number(row.average_duration_ms)).filter((value) => Number.isFinite(value) && value > 0),
      ...recentRuns.map((row) => Number(row.duration_ms)).filter((value) => Number.isFinite(value) && value > 0),
      stats.averageDuration > 0 ? stats.averageDuration : null,
    ].filter((value) => Number.isFinite(value) && value > 0));
    const metricDeltas = latestMetrics
      .map((metric) => Number(metric.delta_from_previous))
      .filter((value) => Number.isFinite(value));
    const avgMetricVariance = metricDeltas.length > 0
      ? metricDeltas.reduce((sum, value) => sum + Math.abs(value), 0) / metricDeltas.length
      : null;
    return {
      ...stats,
      benchmarkSuccess,
      benchmarkDuration,
      avgMetricVariance,
      modelRows,
      regionRows,
      latestMetrics,
      recentRuns,
    };
  }

  function stringifyCompactJson(value) {
    if (value == null) {
      return '';
    }
    try {
      return JSON.stringify(value);
    } catch {
      return String(value);
    }
  }

  function updateLastRefresh() {
    lastRefreshNode.textContent = new Date().toLocaleTimeString();
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

  function getSelectedValues(selectNode) {
    return Array.from(selectNode.selectedOptions).map((option) => option.value).filter(Boolean);
  }

  function setSelectedValues(selectNode, values) {
    const selected = new Set(values || []);
    Array.from(selectNode.options).forEach((option) => {
      option.selected = selected.has(option.value);
    });
  }

  function updateMultiSelectOptions(selectNode, values) {
    const selected = getSelectedValues(selectNode);
    const normalizedValues = Array.from(new Set((values || []).filter(Boolean)));
    selectNode.innerHTML = normalizedValues
      .map((value) => `<option value="${escapeHtml(value)}">${escapeHtml(value)}</option>`)
      .join('');
    const nextSelected = selected.filter((value) => normalizedValues.includes(value));
    setSelectedValues(selectNode, nextSelected);
  }

  function formatSelectionLabel(values, emptyLabel) {
    if (!values || values.length === 0) {
      return emptyLabel;
    }
    if (values.length <= 2) {
      return values.join(', ');
    }
    return `${values.length} selected`;
  }

  function updateActiveLabels() {
    activeRangeNode.textContent = rangeLabels[rangeSelect.value] || rangeSelect.value;
    activeModelNode.textContent = formatSelectionLabel(getSelectedValues(modelSelect), 'All models');
    activeRegionNode.textContent = formatSelectionLabel(getSelectedValues(regionSelect), 'All regions');
    activeToolNode.textContent = formatSelectionLabel(getSelectedValues(toolSelect), 'All tools');
    const sla = getSlaSettings();
    activeSlaNode.textContent = `${formatPercent(sla.successTarget)} success · ${formatDuration(sla.durationTargetMs)} avg duration`;
    activeLayoutNode.textContent = exportLayoutLabels[getSelectedExportLayout()] || getSelectedExportLayout();
    if (activeComparisonNode) {
      activeComparisonNode.textContent = 'This week vs last week';
    }
    document.body.dataset.historyLayout = getSelectedExportLayout();
  }

  function createSparkline(points, valueKey = 'metric_value', options = {}) {
    if (!Array.isArray(points) || points.length === 0) {
      return '';
    }
    const width = 280;
    const height = 110;
    const padding = 14;
    const values = points.map((point) => Number(point[valueKey] ?? 0));
    const min = Math.min(...values);
    const max = Math.max(...values);
    const range = max - min || 1;
    const stepX = points.length > 1 ? (width - padding * 2) / (points.length - 1) : 0;
    const linePoints = points.map((point, index) => {
      const x = padding + (stepX * index);
      const y = height - padding - (((Number(point[valueKey] ?? 0) - min) / range) * (height - padding * 2));
      return { x, y };
    });
    const line = linePoints.map((point) => `${point.x},${point.y}`).join(' ');
    const fill = `${padding},${height - padding} ${line} ${width - padding},${height - padding}`;
    const sparklineId = `sparkline-${sparklineSequence += 1}`;
    const targetValue = Number(options.target);
    const hasTarget = Number.isFinite(targetValue);
    const targetY = hasTarget
      ? height - padding - (((targetValue - min) / range) * (height - padding * 2))
      : null;
    return `
      <svg viewBox="0 0 ${width} ${height}" class="agent-console__sparkline" role="img" aria-label="trend chart">
        <defs>
          <linearGradient id="${sparklineId}-line" x1="0" y1="0" x2="1" y2="0">
            <stop offset="0%" stop-color="currentColor" stop-opacity="0.98"></stop>
            <stop offset="100%" stop-color="currentColor" stop-opacity="0.45"></stop>
          </linearGradient>
          <linearGradient id="${sparklineId}-fill" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stop-color="currentColor" stop-opacity="0.24"></stop>
            <stop offset="100%" stop-color="currentColor" stop-opacity="0"></stop>
          </linearGradient>
        </defs>
        <line x1="${padding}" y1="${height - padding}" x2="${width - padding}" y2="${height - padding}" class="agent-console__sparkline-axis"></line>
        ${hasTarget ? `<line x1="${padding}" y1="${clamp(targetY, padding, height - padding)}" x2="${width - padding}" y2="${clamp(targetY, padding, height - padding)}" class="agent-console__sparkline-target"></line>` : ''}
        ${hasTarget ? `<text x="${width - padding}" y="${clamp(targetY, padding + 10, height - padding - 4)}" class="agent-console__sparkline-target-label" text-anchor="end">${escapeHtml(options.targetLabel || 'Target')}</text>` : ''}
        <polygon class="agent-console__sparkline-fill" fill="url(#${sparklineId}-fill)" points="${fill}"></polygon>
        <polyline fill="none" stroke="url(#${sparklineId}-line)" stroke-width="3" stroke-linecap="round" stroke-linejoin="round" points="${line}"></polyline>
        ${linePoints.length ? `<circle class="agent-console__sparkline-point" cx="${linePoints[linePoints.length - 1].x}" cy="${linePoints[linePoints.length - 1].y}" r="4.5"></circle>` : ''}
      </svg>
    `;
  }

  function renderBenchmarkBoard(payload) {
    if (!benchmarkBoardNode || !boardBriefNode) {
      return;
    }
    if (!payload?.enabled) {
      renderMessage(benchmarkBoardNode, payload?.reason || 'Historical storage is disabled.');
      renderMessage(boardBriefNode, payload?.reason || 'Historical storage is disabled.');
      return;
    }

    const signals = computeExecutiveSignals(payload);
    const sla = getSlaSettings();
    const layout = getSelectedExportLayout();
    const successVariance = formatSignedVariance(signals.successRate - signals.benchmarkSuccess, formatPercent);
    const durationBaseline = signals.benchmarkDuration || signals.averageDuration || sla.durationTargetMs;
    const durationVariance = formatSignedVariance(signals.averageDuration - durationBaseline, formatDuration, false);
    const slaSuccessVariance = formatSignedVariance(signals.successRate - sla.successTarget, formatPercent);
    const slaDurationVariance = formatSignedVariance(signals.averageDuration - sla.durationTargetMs, formatDuration, false);
    const totalRunsForRibbon = Math.max(signals.totalRuns, 1);
    const failedWidth = Math.min(100, (signals.failedRuns / totalRunsForRibbon) * 100);
    const successWidth = 100 - failedWidth;
    const durationScale = Math.max(sla.durationTargetMs * 1.4, signals.averageDuration || 1, durationBaseline || 1);

    benchmarkBoardNode.innerHTML = `
      <div class="agent-console__benchmark-grid">
        <article class="agent-console__benchmark-card">
          <div class="agent-console__benchmark-header">
            <div>
              <p class="agent-console__benchmark-kicker">Benchmark ribbon</p>
              <h3>Success rate versus best visible cohort</h3>
            </div>
            <span class="agent-console__variance agent-console__variance--${successVariance.kind}">${escapeHtml(successVariance.text)}</span>
          </div>
          <div class="agent-console__benchmark-ribbon">
            <div class="agent-console__benchmark-track">
              <div class="agent-console__benchmark-fill" style="width:${clamp(signals.successRate, 0, 100)}%"></div>
              <div class="agent-console__benchmark-marker" style="left:${clamp(signals.benchmarkSuccess, 0, 100)}%"></div>
              <div class="agent-console__benchmark-marker agent-console__benchmark-marker--sla" style="left:${clamp(sla.successTarget, 0, 100)}%"></div>
            </div>
            <div class="agent-console__benchmark-meta">
              <p><strong>Current:</strong> ${formatPercent(signals.successRate)}</p>
              <p><strong>Benchmark:</strong> ${formatPercent(signals.benchmarkSuccess)}</p>
              <p><strong>SLA:</strong> ${formatPercent(sla.successTarget)}</p>
            </div>
          </div>
        </article>
        <article class="agent-console__benchmark-card">
          <div class="agent-console__benchmark-header">
            <div>
              <p class="agent-console__benchmark-kicker">Variance indicator</p>
              <h3>Average duration against operating baseline</h3>
            </div>
            <span class="agent-console__variance agent-console__variance--${durationVariance.kind}">${escapeHtml(durationVariance.text)}</span>
          </div>
          <div class="agent-console__benchmark-ribbon agent-console__benchmark-ribbon--duration">
            <div class="agent-console__benchmark-track">
              <div class="agent-console__benchmark-fill" style="width:${clamp((signals.averageDuration / durationScale) * 100, 0, 100)}%"></div>
              <div class="agent-console__benchmark-marker" style="left:${clamp((durationBaseline / durationScale) * 100, 0, 100)}%"></div>
              <div class="agent-console__benchmark-marker agent-console__benchmark-marker--sla" style="left:${clamp((sla.durationTargetMs / durationScale) * 100, 0, 100)}%"></div>
            </div>
            <div class="agent-console__benchmark-meta">
              <p><strong>Current:</strong> ${signals.averageDuration > 0 ? formatDuration(signals.averageDuration) : 'Awaiting samples'}</p>
              <p><strong>Baseline:</strong> ${durationBaseline ? formatDuration(durationBaseline) : 'Awaiting samples'}</p>
              <p><strong>SLA:</strong> ${formatDuration(sla.durationTargetMs)}</p>
            </div>
          </div>
        </article>
        <article class="agent-console__benchmark-card">
          <div class="agent-console__benchmark-header">
            <div>
              <p class="agent-console__benchmark-kicker">Run mix</p>
              <h3>Failure pressure and confidence band</h3>
            </div>
            <span class="agent-console__variance agent-console__variance--${signals.failedRuns > 0 ? 'negative' : 'positive'}">${signals.failedRuns > 0 ? `${formatNumber(signals.failedRuns)} failed runs` : 'No failures in window'}</span>
          </div>
          <div class="agent-console__mix-ribbon" aria-hidden="true">
            <div class="agent-console__mix-ribbon-success" style="width:${successWidth}%"></div>
            <div class="agent-console__mix-ribbon-failure" style="width:${failedWidth}%"></div>
          </div>
          <div class="agent-console__benchmark-meta">
            <p><strong>Completed:</strong> ${formatNumber(signals.completedRuns)}</p>
            <p><strong>Failed:</strong> ${formatNumber(signals.failedRuns)}</p>
            <p><strong>Avg metric variance:</strong> ${signals.avgMetricVariance == null ? 'No deltas yet' : formatNumber(signals.avgMetricVariance)}</p>
          </div>
        </article>
      </div>
    `;

    const leadingModel = signals.modelRows[0];
    const leadingRegion = signals.regionRows[0];
    const layoutCopy = layout === 'board'
      ? 'Board review preset trims the export to headline KPIs, benchmark ribbons, and priority commentary.'
      : layout === 'appendix'
        ? 'Appendix preset preserves a denser operational snapshot with more comparative detail for follow-up packets.'
        : 'Standard preset balances KPI framing with enough supporting context for staff reviews.';
    boardBriefNode.innerHTML = `
      <div class="agent-console__board-brief-grid">
        <article class="agent-console__board-brief-card agent-console__board-brief-card--hero">
          <p class="agent-console__benchmark-kicker">Board brief</p>
          <h3>Executive readout for the selected window</h3>
          <p>${signals.successRate >= sla.successTarget ? 'Reliability is meeting the configured SLA threshold.' : 'Reliability is below the configured SLA threshold and should be called out in the next executive review.'}</p>
          <ul>
            <li>Success-rate variance: <strong>${escapeHtml(slaSuccessVariance.text)}</strong></li>
            <li>Latency variance: <strong>${escapeHtml(slaDurationVariance.text)}</strong></li>
            <li>Export preset: <strong>${escapeHtml(exportLayoutLabels[layout] || layout)}</strong></li>
          </ul>
        </article>
        <article class="agent-console__board-brief-card">
          <p class="agent-console__benchmark-kicker">Leading cohort</p>
          <h3>${escapeHtml(leadingModel?.label || 'No dominant model yet')}</h3>
          <p>${leadingModel ? `${formatPercent(leadingModel.success_rate)} success across ${formatNumber(leadingModel.total_runs)} runs.` : 'Visible data will identify the strongest model cohort here.'}</p>
        </article>
        <article class="agent-console__board-brief-card">
          <p class="agent-console__benchmark-kicker">Operational lane</p>
          <h3>${escapeHtml(leadingRegion?.label || 'No dominant region yet')}</h3>
          <p>${leadingRegion ? `${leadingRegion.average_duration_ms == null ? 'Average duration unavailable' : formatDuration(leadingRegion.average_duration_ms)} average duration in the busiest visible region.` : 'Visible data will identify the strongest region cohort here.'}</p>
        </article>
        <article class="agent-console__board-brief-card agent-console__board-brief-card--wide">
          <p class="agent-console__benchmark-kicker">Export note</p>
          <h3>Snapshot packaging</h3>
          <p>${escapeHtml(layoutCopy)}</p>
        </article>
      </div>
    `;
  }

  function renderStorytelling(payload) {
    if (!storytellingNode) {
      return;
    }
    const comparison = payload?.time_window_comparison;
    if (!payload?.enabled || !comparison) {
      renderMessage(storytellingNode, payload?.reason || 'Time-window comparison is unavailable.');
      return;
    }

    const current = comparison.current || {};
    const previous = comparison.previous || {};
    const delta = comparison.delta || {};
    const runDelta = formatDirectionalDelta(Number(delta.total_runs), formatNumber, true, 'Flat run volume week over week');
    const successDelta = formatDirectionalDelta(Number(delta.success_rate), formatPercent, true);
    const durationDelta = formatDirectionalDelta(Number(delta.average_duration_ms), formatDuration, false);
    const p95Delta = formatDirectionalDelta(Number(delta.p95_duration_ms), formatDuration, false, 'Flat p95 latency week over week');

    storytellingNode.innerHTML = `
      <div class="agent-console__storytelling-grid">
        <article class="agent-console__storytelling-card agent-console__storytelling-card--wide">
          <div class="agent-console__storytelling-header">
            <div>
              <p class="agent-console__benchmark-kicker">Time-window comparison</p>
              <h3>${escapeHtml(comparison.mode === 'this_week_vs_last_week' ? 'This week vs last week' : 'Selected comparison')}</h3>
            </div>
            <span class="agent-console__variance agent-console__variance--${successDelta.kind}">${escapeHtml(successDelta.text)}</span>
          </div>
          <div class="agent-console__storytelling-stats">
            <div>
              <p class="agent-console__history-card-label">This week</p>
              <p class="agent-console__story-value">${formatNumber(current.total_runs ?? 0)} runs</p>
              <p class="agent-console__story-copy">${formatPercent(current.success_rate ?? 0)} success · ${current.average_duration_ms == null ? '—' : formatDuration(current.average_duration_ms)}</p>
            </div>
            <div>
              <p class="agent-console__history-card-label">Last week</p>
              <p class="agent-console__story-value">${formatNumber(previous.total_runs ?? 0)} runs</p>
              <p class="agent-console__story-copy">${formatPercent(previous.success_rate ?? 0)} success · ${previous.average_duration_ms == null ? '—' : formatDuration(previous.average_duration_ms)}</p>
            </div>
          </div>
        </article>
        <article class="agent-console__storytelling-card">
          <p class="agent-console__benchmark-kicker">Volume</p>
          <h3>${escapeHtml(runDelta.text)}</h3>
          <p class="agent-console__story-copy">Current week captured ${formatNumber(current.total_runs ?? 0)} runs from ${formatTimestamp(current.start)} to now.</p>
        </article>
        <article class="agent-console__storytelling-card">
          <p class="agent-console__benchmark-kicker">Latency</p>
          <h3>${escapeHtml(durationDelta.text)}</h3>
          <p class="agent-console__story-copy">p95 moved ${escapeHtml(p95Delta.text.toLowerCase())} while average duration changed ${escapeHtml(durationDelta.text.toLowerCase())}.</p>
        </article>
      </div>
    `;
  }

  function renderPercentiles(payload) {
    if (!percentilesNode) {
      return;
    }
    const percentiles = payload?.summary?.latency_percentiles_ms;
    if (!payload?.enabled || !percentiles) {
      renderMessage(percentilesNode, payload?.reason || 'Latency percentile bands are unavailable.');
      return;
    }

    const entries = [
      { key: 'p50', label: 'p50 median' },
      { key: 'p90', label: 'p90' },
      { key: 'p95', label: 'p95' },
      { key: 'p99', label: 'p99' },
    ];
    const maxValue = Math.max(...entries.map((entry) => Number(percentiles[entry.key] ?? 0)), 1);
    const currentWeekPercentiles = payload.time_window_comparison?.current?.latency_percentiles_ms || {};
    const previousWeekPercentiles = payload.time_window_comparison?.previous?.latency_percentiles_ms || {};

    percentilesNode.innerHTML = `
      <section class="agent-console__percentile-panel">
        <div class="agent-console__history-topbar">
          <div>
            <h3>Percentile latency bands</h3>
            <p class="agent-console__meta">Use these bands to see whether the long-tail experience is widening even when average duration still looks calm.</p>
          </div>
        </div>
        <div class="agent-console__percentile-list">
          ${entries.map((entry) => {
            const value = Number(percentiles[entry.key]);
            const currentWeekValue = Number(currentWeekPercentiles[entry.key]);
            const previousWeekValue = Number(previousWeekPercentiles[entry.key]);
            const delta = formatDirectionalDelta(currentWeekValue - previousWeekValue, formatDuration, false, 'Flat week over week');
            return `
              <article class="agent-console__percentile-card">
                <div class="agent-console__percentile-header">
                  <div>
                    <p class="agent-console__benchmark-kicker">Latency band</p>
                    <h4>${escapeHtml(entry.label)}</h4>
                  </div>
                  <span class="agent-console__variance agent-console__variance--${delta.kind}">${escapeHtml(delta.text)}</span>
                </div>
                <div class="agent-console__percentile-track" aria-hidden="true">
                  <div class="agent-console__percentile-fill" style="width:${clamp((value / maxValue) * 100, 0, 100)}%"></div>
                </div>
                <div class="agent-console__benchmark-meta">
                  <p><strong>Selected window:</strong> ${Number.isFinite(value) ? formatDuration(value) : '—'}</p>
                  <p><strong>This week:</strong> ${Number.isFinite(currentWeekValue) ? formatDuration(currentWeekValue) : '—'}</p>
                  <p><strong>Last week:</strong> ${Number.isFinite(previousWeekValue) ? formatDuration(previousWeekValue) : '—'}</p>
                </div>
              </article>
            `;
          }).join('')}
        </div>
      </section>
    `;
  }

  function renderExceptions(payload) {
    if (!exceptionsNode) {
      return;
    }
    const exceptions = Array.isArray(payload?.executive_exception_rollup) ? payload.executive_exception_rollup : [];
    if (!payload?.enabled || exceptions.length === 0) {
      renderMessage(exceptionsNode, payload?.reason || 'Executive exception rollups are unavailable.');
      return;
    }

    exceptionsNode.innerHTML = `
      <section class="agent-console__exceptions-panel">
        <div class="agent-console__history-topbar">
          <div>
            <h3>Executive exception rollup</h3>
            <p class="agent-console__meta">These callouts summarize the items most likely to deserve a mention in the weekly operator review.</p>
          </div>
        </div>
        <div class="agent-console__exceptions-grid">
          ${exceptions.map((item) => `
            <article class="agent-console__exception-card agent-console__exception-card--${escapeHtml(item.severity || 'neutral')}">
              <div class="agent-console__exception-header">
                <p class="agent-console__benchmark-kicker">${escapeHtml(item.severity || 'notice')}</p>
                <span class="agent-console__status-pill agent-console__status-pill--${item.severity === 'critical' ? 'error' : item.severity === 'ok' ? 'ok' : 'neutral'}">${escapeHtml(item.severity || 'neutral')}</span>
              </div>
              <h4>${escapeHtml(item.title || 'Exception')}</h4>
              <p>${escapeHtml(item.summary || 'No summary available.')}</p>
              <p class="agent-console__meta">${escapeHtml(item.detail || '')}</p>
            </article>
          `).join('')}
        </div>
      </section>
    `;
  }

  function buildExecutiveStories(payload) {
    const summary = payload.summary || {};
    const toolUsage = Array.isArray(payload.tool_usage) ? payload.tool_usage : [];
    const topTool = toolUsage[0];
    const totalRuns = Number(summary.total_runs ?? 0);
    const failedRuns = Number(summary.failed_runs ?? 0);
    const completedRuns = Math.max(0, totalRuns - failedRuns);
    const failureRate = totalRuns ? (failedRuns / totalRuns) * 100 : 0;
    const successRate = totalRuns ? (completedRuns / totalRuns) * 100 : 0;
    const averageDuration = Number(summary.average_duration_ms ?? 0);

    return [
      {
        kicker: 'Reliability posture',
        value: totalRuns ? `${formatNumber(successRate)}% success` : 'No runs yet',
        copy: totalRuns
          ? `Failed runs account for ${formatNumber(failureRate)}% of captured executions in the current view.`
          : 'Run prompts to establish a baseline for success and failure rates.',
      },
      {
        kicker: 'Throughput signal',
        value: averageDuration > 0 ? formatDuration(averageDuration) : 'Awaiting samples',
        copy: averageDuration > 0
          ? 'Average duration across the filtered run set, useful for spotting latency drift.'
          : 'Duration analytics appear after the first persisted prompt runs complete.',
      },
      {
        kicker: 'Top workload lane',
        value: topTool ? topTool.label : 'No tool data',
        copy: topTool
          ? `${formatNumber(topTool.count)} recorded invocations currently dominate the visible workload.`
          : 'Tool usage breakdowns will appear once persisted steps are available.',
      },
    ];
  }

  function createStatusTimeline(runs) {
    if (!Array.isArray(runs) || runs.length === 0) {
      return '<p class="agent-console__meta">No status history is available for the selected time range.</p>';
    }
    const grouped = new Map();
    runs.slice().reverse().forEach((run) => {
      const dayKey = (run.created_at || '').slice(0, 10) || 'unknown';
      const bucket = grouped.get(dayKey) || { completed: 0, failed: 0 };
      if (run.status === 'completed') {
        bucket.completed += 1;
      } else {
        bucket.failed += 1;
      }
      grouped.set(dayKey, bucket);
    });
    return `
      <div class="agent-console__timeline-list">
        ${Array.from(grouped.entries()).map(([dayKey, bucket]) => {
          const total = Math.max(1, bucket.completed + bucket.failed);
          const successWidth = (bucket.completed / total) * 100;
          const failureWidth = 100 - successWidth;
          return `
            <div class="agent-console__timeline-row">
              <div class="agent-console__bar-head">
                <span>${escapeHtml(dayKey)}</span>
                <strong>${formatNumber(total)} run(s)</strong>
              </div>
              <div class="agent-console__timeline-track" title="Completed ${formatNumber(bucket.completed)} · Failed ${formatNumber(bucket.failed)}">
                <div class="agent-console__timeline-segment agent-console__timeline-segment--success" style="width:${successWidth}%"></div>
                <div class="agent-console__timeline-segment agent-console__timeline-segment--failure" style="width:${failureWidth}%"></div>
              </div>
              <p class="agent-console__meta">Completed ${formatNumber(bucket.completed)} · Failed ${formatNumber(bucket.failed)}</p>
            </div>
          `;
        }).join('')}
      </div>
    `;
  }

  function createDonut(completed, failed) {
    const total = Math.max(1, completed + failed);
    const radius = 54;
    const circumference = 2 * Math.PI * radius;
    const completedOffset = circumference * (1 - (completed / total));
    return `
      <svg viewBox="0 0 160 160" class="agent-console__donut" role="img" aria-label="success and failure distribution">
        <title>Completed ${completed}; Failed ${failed}</title>
        <circle cx="80" cy="80" r="54" class="agent-console__donut-track"></circle>
        <circle cx="80" cy="80" r="54" class="agent-console__donut-success" stroke-dasharray="${circumference}" stroke-dashoffset="${completedOffset}"></circle>
        <text x="80" y="76" class="agent-console__donut-value">${completed + failed}</text>
        <text x="80" y="96" class="agent-console__donut-label">runs</text>
      </svg>
    `;
  }

  function createHorizontalBars(items, renderLabel, valueKey = 'count') {
    if (!Array.isArray(items) || items.length === 0) {
      return '<p class="agent-console__meta">No chart data is available for the selected time range.</p>';
    }
    const max = Math.max(...items.map((item) => Number(item[valueKey] ?? 0)), 1);
    return `
      <div class="agent-console__bar-list">
        ${items.map((item) => {
          const value = Number(item[valueKey] ?? 0);
          const width = Math.max(8, (value / max) * 100);
          return `
            <div class="agent-console__bar-row">
              <div class="agent-console__bar-head">
                <span>${renderLabel(item)}</span>
                <strong>${formatNumber(value)}</strong>
              </div>
              <div class="agent-console__bar-track" title="${formatNumber(value)}">
                <div class="agent-console__bar-fill" style="width:${width}%"></div>
              </div>
            </div>
          `;
        }).join('')}
      </div>
    `;
  }

  function buildDashboardSvg(payload) {
    const layout = getSelectedExportLayout();
    const signals = computeExecutiveSignals(payload);
    const sla = getSlaSettings();
    const width = 1400;
    const height = 980;
    const summary = payload.summary || {};
    const recentRuns = Array.isArray(payload.recent_runs) ? payload.recent_runs.slice(0, 6) : [];
    const toolUsage = Array.isArray(payload.tool_usage) ? payload.tool_usage.slice(0, 6) : [];
    const durations = recentRuns.slice().reverse().map((run, index) => ({ label: `Run ${index + 1}`, duration_ms: Number(run.duration_ms ?? 0) }));
    const totalRuns = Number(summary.total_runs ?? 0);
    const failedRuns = Number(summary.failed_runs ?? 0);
    const completedRuns = Math.max(0, totalRuns - failedRuns);
    const averageDuration = Number(summary.average_duration_ms ?? 0);
    const successRate = totalRuns ? `${formatNumber((completedRuns / totalRuns) * 100)}%` : '0%';
    const cards = layout === 'board'
      ? [
        ['Stored runs', formatNumber(totalRuns)],
        ['Success rate', successRate],
        ['Avg duration', averageDuration > 0 ? formatDuration(averageDuration) : '—'],
        ['SLA target', `${formatPercent(sla.successTarget)} / ${formatDuration(sla.durationTargetMs)}`],
        ['Top model cohort', payload.model_breakdown?.[0]?.label || '—'],
        ['Top region cohort', payload.region_breakdown?.[0]?.label || '—'],
      ]
      : [
        ['Stored runs', formatNumber(totalRuns)],
        ['Completed runs', formatNumber(completedRuns)],
        ['Failed runs', formatNumber(failedRuns)],
        ['Metrics recorded', formatNumber(summary.metrics_recorded ?? 0)],
        ['Success rate', successRate],
        ['Last run', formatTimestamp(summary.last_run_at)],
      ];
    const cardMarkup = cards.map(([label, value], index) => {
      const column = index % 3;
      const row = Math.floor(index / 3);
      const x = 40 + (column * 440);
      const y = 110 + (row * 112);
      return `
        <rect x="${x}" y="${y}" width="400" height="88" rx="20" fill="#ffffff" stroke="#dbe4f0" />
        <text x="${x + 24}" y="${y + 34}" font-size="20" fill="#475569">${escapeHtml(label)}</text>
        <text x="${x + 24}" y="${y + 64}" font-size="30" font-weight="700" fill="#0f172a">${escapeHtml(value)}</text>
      `;
    }).join('');
    const maxToolCount = Math.max(...toolUsage.map((item) => Number(item.count ?? 0)), 1);
    const toolMarkup = toolUsage.length > 0
      ? toolUsage.map((item, index) => {
          const barX = 80;
          const rowY = 410 + (index * 52);
          const widthPct = (Number(item.count ?? 0) / maxToolCount) * 340;
          return `
            <text x="${barX}" y="${rowY}" font-size="18" fill="#0f172a">${escapeHtml(item.label)}</text>
            <text x="${barX + 360}" y="${rowY}" text-anchor="end" font-size="18" font-weight="700" fill="#0f172a">${escapeHtml(formatNumber(item.count))}</text>
            <rect x="${barX}" y="${rowY + 10}" width="340" height="16" rx="999" fill="#dbeafe" />
            <rect x="${barX}" y="${rowY + 10}" width="${Math.max(16, widthPct)}" height="16" rx="999" fill="#2563eb" />
          `;
        }).join('')
      : '<text x="80" y="438" font-size="18" fill="#64748b">No tool usage rows are available for the selected window.</text>';
    const polyline = (() => {
      if (durations.length === 0) return '';
      const values = durations.map((point) => point.duration_ms);
      const min = Math.min(...values);
      const max = Math.max(...values);
      const range = max - min || 1;
      const stepX = durations.length > 1 ? 520 / (durations.length - 1) : 0;
      return durations.map((point, index) => `${760 + (stepX * index)},${460 + 180 - (((point.duration_ms - min) / range) * 180)}`).join(' ');
    })();
    const durationMarkup = durations.length > 0
      ? `
        <line x1="760" y1="640" x2="1280" y2="640" stroke="#cbd5e1" stroke-width="2" />
        <polyline points="${polyline}" fill="none" stroke="#0ea5e9" stroke-width="5" stroke-linecap="round" stroke-linejoin="round" />
        <text x="760" y="680" font-size="18" fill="#64748b">Latest: ${escapeHtml(formatDuration(durations[durations.length - 1].duration_ms))}</text>
      `
      : '<text x="760" y="470" font-size="18" fill="#64748b">No duration history is available for the selected window.</text>';
    const boardBrief = `
      <rect x="40" y="710" width="1320" height="220" rx="24" fill="#ffffff" stroke="#dbe4f0" />
      <text x="60" y="750" font-size="24" font-weight="700" fill="#0f172a">Executive brief</text>
      <text x="60" y="790" font-size="18" fill="#475569">Current success rate ${escapeHtml(formatPercent(signals.successRate))} against SLA ${escapeHtml(formatPercent(sla.successTarget))}.</text>
      <text x="60" y="820" font-size="18" fill="#475569">Average duration ${escapeHtml(signals.averageDuration > 0 ? formatDuration(signals.averageDuration) : 'Awaiting samples')} against SLA ${escapeHtml(formatDuration(sla.durationTargetMs))}.</text>
      <text x="60" y="850" font-size="18" fill="#475569">Visible benchmark success rate ${escapeHtml(formatPercent(signals.benchmarkSuccess))}${signals.benchmarkDuration ? ` · baseline duration ${escapeHtml(formatDuration(signals.benchmarkDuration))}` : ''}.</text>
      <text x="60" y="890" font-size="18" fill="#475569">Export preset: ${escapeHtml(exportLayoutLabels[layout] || layout)}.</text>
    `;
    return `
      <svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}" viewBox="0 0 ${width} ${height}">
        <rect width="${width}" height="${height}" fill="#f8fafc" />
        <text x="40" y="54" font-size="34" font-weight="700" fill="#0f172a">OpenShift SRE Historical Dashboard</text>
        <text x="40" y="84" font-size="18" fill="#475569">Range: ${escapeHtml(rangeLabels[rangeSelect.value] || rangeSelect.value)} · Layout: ${escapeHtml(exportLayoutLabels[layout] || layout)} · Exported ${escapeHtml(new Date().toLocaleString())}</text>
        ${cardMarkup}
        <rect x="40" y="350" width="620" height="320" rx="24" fill="#ffffff" stroke="#dbe4f0" />
        <text x="60" y="390" font-size="24" font-weight="700" fill="#0f172a">Tool usage</text>
        ${toolMarkup}
        <rect x="700" y="350" width="660" height="320" rx="24" fill="#ffffff" stroke="#dbe4f0" />
        <text x="720" y="390" font-size="24" font-weight="700" fill="#0f172a">Recent run durations</text>
        ${durationMarkup}
        ${layout === 'board' || layout === 'appendix' ? boardBrief : ''}
      </svg>
    `;
  }

  function createTimestampSlug() {
    return new Date().toISOString().replace(/[:.]/g, '-');
  }

  function buildHistoryReportContext(reportType) {
    const payload = lastPayload || { summary: {} };
    const summary = payload.summary || {};
    const comparison = payload.time_window_comparison || {};
    const signals = computeExecutiveSignals(payload);
    const topTools = Array.isArray(payload.tool_usage) ? payload.tool_usage.slice(0, 8) : [];
    const exceptions = Array.isArray(payload.executive_exception_rollup) ? payload.executive_exception_rollup.slice(0, 6) : [];
    const latestMetrics = Array.isArray(payload.latest_metrics) ? payload.latest_metrics.slice(0, 8) : [];
    const recentRuns = Array.isArray(payload.recent_runs) ? payload.recent_runs.slice(0, 8) : [];
    const rangeLabel = rangeLabels[rangeSelect.value] || rangeSelect.value;
    return {
      reportType,
      reportLabel: reportType === 'operations-review' ? 'Operations Review Pack' : 'Executive Portfolio Report',
      generatedAt: new Date(),
      rangeLabel,
      filters: payload.filters || {},
      summary,
      comparison,
      signals,
      topTools,
      exceptions,
      latestMetrics,
      recentRuns,
      layoutLabel: exportLayoutLabels[getSelectedExportLayout()] || getSelectedExportLayout()
    };
  }

  function buildHistorySectionText(title, lines = []) {
    const filtered = lines.filter(Boolean);
    if (filtered.length === 0) {
      return '';
    }
    return `${title}\n${filtered.map((line) => `• ${line}`).join('\n')}`;
  }

  function exportHistoryCsvReport(context) {
    const rows = [
      ['Section', 'Field', 'Value'],
      ['summary', 'report_type', context.reportLabel],
      ['summary', 'generated_at', context.generatedAt.toISOString()],
      ['summary', 'time_range', context.rangeLabel],
      ['summary', 'layout', context.layoutLabel],
      ['summary', 'model_names', (context.filters.model_names || []).join('|')],
      ['summary', 'cluster_scopes', (context.filters.cluster_scopes || []).join('|')],
      ['summary', 'tool_names', (context.filters.tool_names || []).join('|')],
      ['summary', 'total_runs', context.summary.total_runs ?? 0],
      ['summary', 'failed_runs', context.summary.failed_runs ?? 0],
      ['summary', 'metrics_recorded', context.summary.metrics_recorded ?? 0],
      ['summary', 'average_duration_ms', context.summary.average_duration_ms ?? ''],
      ['summary', 'p95_duration_ms', context.summary.latency_percentiles_ms?.p95 ?? ''],
      [],
      ['comparison', 'current_runs', context.comparison.current?.total_runs ?? 0],
      ['comparison', 'current_success_rate', context.comparison.current?.success_rate ?? ''],
      ['comparison', 'previous_runs', context.comparison.previous?.total_runs ?? 0],
      ['comparison', 'previous_success_rate', context.comparison.previous?.success_rate ?? ''],
      ['comparison', 'delta_runs', context.comparison.delta?.total_runs ?? ''],
      ['comparison', 'delta_success_rate', context.comparison.delta?.success_rate ?? ''],
      [],
      ['top_tools', 'label', 'count'],
      ...context.topTools.map((item) => ['top_tools', item.label, item.count]),
      [],
      ['latest_metrics', 'metric', 'value', 'delta', 'recorded_at'],
      ...context.latestMetrics.map((metric) => ['latest_metrics', metric.metric_label, metric.metric_value, metric.delta_from_previous ?? '', metric.recorded_at]),
      [],
      ['exceptions', 'severity', 'title', 'summary', 'detail'],
      ...context.exceptions.map((item) => ['exceptions', item.severity || '', item.title || '', item.summary || '', item.detail || '']),
      [],
      ['recent_runs', 'created_at', 'status', 'model_name', 'cluster_scope', 'duration_ms', 'prompt_excerpt'],
      ...context.recentRuns.map((run) => ['recent_runs', run.created_at || '', run.status || '', run.model_name || '', run.cluster_scope || '', run.duration_ms ?? '', run.prompt_excerpt || ''])
    ];
    downloadBlob(`openshift-sre-history-${context.reportType}-${createTimestampSlug()}.csv`, new Blob([toCsv(rows)], { type: 'text/csv;charset=utf-8' }));
  }

  async function exportHistoryPpt(context) {
    const PptxGenJS = window.PptxGenJS;
    if (!PptxGenJS) {
      throw new Error('PowerPoint export library is not available on this page right now.');
    }
    const pptx = new PptxGenJS();
    pptx.layout = 'LAYOUT_WIDE';
    pptx.author = 'GitHub Copilot';
    pptx.company = 'OpenShift SRE Local Agent';
    pptx.subject = context.reportLabel;
    pptx.title = `${context.reportLabel} - ${context.rangeLabel}`;

    const titleSlide = pptx.addSlide();
    titleSlide.background = { color: 'F8FAFC' };
    titleSlide.addText(context.reportLabel, { x: 0.5, y: 0.5, w: 6.6, h: 0.5, fontSize: 24, bold: true, color: '0F172A' });
    titleSlide.addText(`${context.rangeLabel} • ${context.layoutLabel} • ${context.generatedAt.toLocaleString()}`, { x: 0.5, y: 1.1, w: 7.6, h: 0.3, fontSize: 14, color: '2563EB' });
    titleSlide.addText(buildHistorySectionText('Headline metrics', [
      `Stored runs: ${formatNumber(context.summary.total_runs ?? 0)}`,
      `Failed runs: ${formatNumber(context.summary.failed_runs ?? 0)}`,
      `Average duration: ${context.summary.average_duration_ms == null ? '—' : formatDuration(context.summary.average_duration_ms)}`,
      `p95 duration: ${context.summary.latency_percentiles_ms?.p95 == null ? '—' : formatDuration(context.summary.latency_percentiles_ms.p95)}`
    ]), { x: 0.5, y: 1.7, w: 5.8, h: 2.4, fontSize: 12, color: '0F172A', margin: 0.12, fill: { color: 'FFFFFF' }, line: { color: 'CBD5E1' } });
    titleSlide.addText(buildHistorySectionText('Portfolio posture', [
      `Success rate: ${formatPercent(context.signals.successRate)}`,
      `Benchmark success: ${formatPercent(context.signals.benchmarkSuccess)}`,
      `Top model cohort: ${context.signals.modelRows[0]?.label || '—'}`,
      `Top region cohort: ${context.signals.regionRows[0]?.label || '—'}`
    ]), { x: 6.8, y: 1.7, w: 5.4, h: 2.4, fontSize: 12, color: '0F172A', margin: 0.12, fill: { color: 'DBEAFE' }, line: { color: '93C5FD' } });

    const activitySlide = pptx.addSlide();
    activitySlide.addText('Operational activity', { x: 0.5, y: 0.4, w: 6.0, h: 0.4, fontSize: 20, bold: true, color: '0F172A' });
    activitySlide.addText(buildHistorySectionText('Top tools', context.topTools.length > 0 ? context.topTools.map((item) => `${item.label}: ${formatNumber(item.count)} invocations`) : ['No tool activity was available.']), { x: 0.5, y: 1.0, w: 5.8, h: 4.8, fontSize: 12, color: '0F172A', margin: 0.12, fill: { color: 'FFFFFF' }, line: { color: 'CBD5E1' } });
    activitySlide.addText(buildHistorySectionText('Latest metrics', context.latestMetrics.length > 0 ? context.latestMetrics.map((metric) => `${metric.metric_label}: ${formatMetricValue(metric.metric_value, metric.unit)}${metric.delta_from_previous == null ? '' : ` (Δ ${formatMetricValue(metric.delta_from_previous, metric.unit)})`}`) : ['No latest metrics were available.']), { x: 6.7, y: 1.0, w: 5.4, h: 4.8, fontSize: 12, color: '0F172A', margin: 0.12, fill: { color: 'FFFFFF' }, line: { color: 'CBD5E1' } });

    const reviewSlide = pptx.addSlide();
    reviewSlide.addText('Exceptions and recent runs', { x: 0.5, y: 0.4, w: 6.8, h: 0.4, fontSize: 20, bold: true, color: '0F172A' });
    reviewSlide.addText(buildHistorySectionText('Executive exceptions', context.exceptions.length > 0 ? context.exceptions.map((item) => `${item.title}: ${item.summary}${item.detail ? ` — ${item.detail}` : ''}`) : ['No exception rollups were available.']), { x: 0.5, y: 1.0, w: 5.8, h: 4.8, fontSize: 12, color: '0F172A', margin: 0.12, fill: { color: 'FFFFFF' }, line: { color: 'CBD5E1' } });
    reviewSlide.addText(buildHistorySectionText('Recent runs', context.recentRuns.length > 0 ? context.recentRuns.map((run) => `${formatTimestamp(run.created_at)} · ${run.status} · ${run.model_name} · ${formatDuration(run.duration_ms)}`) : ['No recent runs were available.']), { x: 6.7, y: 1.0, w: 5.4, h: 4.8, fontSize: 12, color: '0F172A', margin: 0.12, fill: { color: 'FFFFFF' }, line: { color: 'CBD5E1' } });

    await pptx.writeFile({ fileName: `openshift-sre-history-${context.reportType}-${createTimestampSlug()}.pptx` });
  }

  async function exportHistoryPdf(context) {
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
    doc.text(`${context.rangeLabel} • ${context.layoutLabel} • ${context.generatedAt.toLocaleString()}`, 48, cursorY);
    cursorY += 24;
    addBlock('Headline metrics', [
      `Stored runs: ${formatNumber(context.summary.total_runs ?? 0)}`,
      `Failed runs: ${formatNumber(context.summary.failed_runs ?? 0)}`,
      `Average duration: ${context.summary.average_duration_ms == null ? '—' : formatDuration(context.summary.average_duration_ms)}`,
      `p95 duration: ${context.summary.latency_percentiles_ms?.p95 == null ? '—' : formatDuration(context.summary.latency_percentiles_ms.p95)}`
    ]);
    addBlock('Time-window comparison', [
      `Current runs: ${formatNumber(context.comparison.current?.total_runs ?? 0)}`,
      `Current success rate: ${formatPercent(context.comparison.current?.success_rate ?? 0)}`,
      `Previous runs: ${formatNumber(context.comparison.previous?.total_runs ?? 0)}`,
      `Previous success rate: ${formatPercent(context.comparison.previous?.success_rate ?? 0)}`,
      `Run delta: ${formatNumber(context.comparison.delta?.total_runs ?? 0)}`,
      `Success-rate delta: ${formatPercent(context.comparison.delta?.success_rate ?? 0)}`
    ]);
    addBlock('Top tools', context.topTools.length > 0 ? context.topTools.map((item) => `${item.label}: ${formatNumber(item.count)} invocations`) : ['No tool activity was available.']);
    addBlock('Latest metrics', context.latestMetrics.length > 0 ? context.latestMetrics.map((metric) => `${metric.metric_label}: ${formatMetricValue(metric.metric_value, metric.unit)}`) : ['No latest metrics were available.']);
    addBlock('Executive exceptions', context.exceptions.length > 0 ? context.exceptions.map((item) => `${item.title}: ${item.summary}${item.detail ? ` — ${item.detail}` : ''}`) : ['No exception rollups were available.']);
    doc.save(`openshift-sre-history-${context.reportType}-${createTimestampSlug()}.pdf`);
  }

  async function exportHistoryWord(context) {
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
    <p class="meta">${escapeHtml(context.rangeLabel)} · ${escapeHtml(context.layoutLabel)} · ${escapeHtml(context.generatedAt.toLocaleString())}</p>
    <div>
      <span class="chip">Runs: ${escapeHtml(formatNumber(context.summary.total_runs ?? 0))}</span>
      <span class="chip">Failed: ${escapeHtml(formatNumber(context.summary.failed_runs ?? 0))}</span>
      <span class="chip">Success: ${escapeHtml(formatPercent(context.signals.successRate))}</span>
    </div>
    <div class="section">
      <h2>Headline metrics</h2>
      <ul>
        <li>Average duration: ${escapeHtml(context.summary.average_duration_ms == null ? '—' : formatDuration(context.summary.average_duration_ms))}</li>
        <li>p95 duration: ${escapeHtml(context.summary.latency_percentiles_ms?.p95 == null ? '—' : formatDuration(context.summary.latency_percentiles_ms.p95))}</li>
        <li>Benchmark success: ${escapeHtml(formatPercent(context.signals.benchmarkSuccess))}</li>
        <li>Top model cohort: ${escapeHtml(context.signals.modelRows[0]?.label || '—')}</li>
      </ul>
    </div>
    <div class="section">
      <h2>Top tools</h2>
      <ul>${(context.topTools.length > 0 ? context.topTools.map((item) => `${item.label}: ${formatNumber(item.count)} invocations`) : ['No tool activity was available.']).map((line) => `<li>${escapeHtml(line)}</li>`).join('')}</ul>
    </div>
    <div class="section">
      <h2>Latest metrics</h2>
      <ul>${(context.latestMetrics.length > 0 ? context.latestMetrics.map((metric) => `${metric.metric_label}: ${formatMetricValue(metric.metric_value, metric.unit)}`) : ['No latest metrics were available.']).map((line) => `<li>${escapeHtml(line)}</li>`).join('')}</ul>
    </div>
    <div class="section">
      <h2>Executive exceptions</h2>
      <ul>${(context.exceptions.length > 0 ? context.exceptions.map((item) => `${item.title}: ${item.summary}${item.detail ? ` — ${item.detail}` : ''}`) : ['No exception rollups were available.']).map((line) => `<li>${escapeHtml(line)}</li>`).join('')}</ul>
    </div>
  </body>
</html>`;
    downloadBlob(`openshift-sre-history-${context.reportType}-${createTimestampSlug()}.doc`, new Blob([html], { type: 'application/msword' }));
  }

  function updateHistoryReportState() {
    const hasPayload = Boolean(lastPayload?.enabled);
    reportExportButtons.forEach((button) => {
      const isExporting = button.dataset.historyExporting === 'true';
      button.disabled = !hasPayload || isExporting;
    });
    if (!hasPayload) {
      setReportStatus('Refresh the dashboard to unlock history report exports.');
    }
  }

  async function handleHistoryReportExport(button) {
    if (!button || !lastPayload?.enabled) {
      setReportStatus('Refresh the dashboard first so there is live history content to export.', 'error');
      return;
    }
    const reportType = button.dataset.historyExportReport || 'executive-portfolio';
    const format = button.dataset.historyExportFormat || 'word';
    const context = buildHistoryReportContext(reportType);
    const originalLabel = button.textContent;
    button.dataset.historyExporting = 'true';
    button.textContent = `Preparing ${format.toUpperCase()}…`;
    updateHistoryReportState();
    setReportStatus(`Building ${context.reportLabel} as ${format.toUpperCase()}…`, 'ok');
    try {
      if (format === 'csv') {
        exportHistoryCsvReport(context);
      } else if (format === 'ppt') {
        await exportHistoryPpt(context);
      } else if (format === 'pdf') {
        await exportHistoryPdf(context);
      } else {
        await exportHistoryWord(context);
      }
      setReportStatus(`${context.reportLabel} exported as ${format.toUpperCase()}.`, 'ok');
    } catch (error) {
      setReportStatus(error instanceof Error ? error.message : `Unable to export ${context.reportLabel}.`, 'error');
    } finally {
      button.dataset.historyExporting = 'false';
      button.textContent = originalLabel;
      updateHistoryReportState();
    }
  }

  function renderBadges(payload) {
    const summary = payload.summary || {};
    const totalRuns = Number(summary.total_runs ?? 0);
    const failedRuns = Number(summary.failed_runs ?? 0);
    const averageDuration = Number(summary.average_duration_ms ?? 0);
    const badges = [];
    if (totalRuns === 0) {
      badges.push({ label: 'No runs captured yet', kind: 'neutral' });
    } else if (failedRuns === 0) {
      badges.push({ label: 'Healthy run history', kind: 'ok' });
    } else if (failedRuns === totalRuns) {
      badges.push({ label: 'Attention required', kind: 'error' });
    } else {
      badges.push({ label: 'Mixed outcomes', kind: 'warning' });
    }
    if (summary.metrics_recorded > 0) {
      badges.push({ label: `${formatNumber(summary.metrics_recorded)} numeric metrics captured`, kind: 'ok' });
    } else {
      badges.push({ label: 'No numeric metrics yet', kind: 'neutral' });
    }
    if (averageDuration >= 120000) {
      badges.push({ label: 'Average duration is high', kind: 'warning' });
    } else if (averageDuration > 0) {
      badges.push({ label: `Average duration ${formatDuration(averageDuration)}`, kind: 'neutral' });
    }
    const sla = getSlaSettings();
    badges.push({ label: `SLA ${formatPercent(sla.successTarget)} / ${formatDuration(sla.durationTargetMs)}`, kind: 'neutral' });
    badges.push({ label: exportLayoutLabels[getSelectedExportLayout()] || getSelectedExportLayout(), kind: 'neutral' });
    const modelNames = payload.filters?.model_names || [];
    const regions = payload.filters?.cluster_scopes || [];
    const tools = payload.filters?.tool_names || [];
    if (modelNames.length > 0) {
      badges.push({ label: formatSelectionLabel(modelNames, ''), kind: 'neutral' });
    }
    if (regions.length > 0) {
      badges.push({ label: formatSelectionLabel(regions, ''), kind: 'neutral' });
    }
    if (tools.length > 0) {
      badges.push({ label: formatSelectionLabel(tools, ''), kind: 'neutral' });
    }
    badgesNode.innerHTML = badges.map((badge) => `<span class="agent-console__history-badge agent-console__history-badge--${badge.kind}">${escapeHtml(badge.label)}</span>`).join('');
  }

  function renderSummary(payload) {
    summaryNode.innerHTML = '';
    if (!payload?.enabled) {
      renderMessage(summaryNode, payload?.reason || 'Historical storage is disabled.');
      return;
    }
    const summary = payload.summary || {};
    const { totalRuns, failedRuns, completedRuns, successRate, averageDuration } = computeOverviewStats(payload);
    const stories = buildExecutiveStories(payload);
    const signals = computeExecutiveSignals(payload);
    const sla = getSlaSettings();
    const successRibbonWidth = clamp(signals.successRate, 0, 100);
    const successBenchmarkWidth = clamp(signals.benchmarkSuccess, 0, 100);
    const durationScale = Math.max(sla.durationTargetMs * 1.4, averageDuration || 1, signals.benchmarkDuration || 1);
    const durationRibbonWidth = clamp((averageDuration / durationScale) * 100, 0, 100);
    const durationBenchmarkWidth = clamp(((signals.benchmarkDuration || 0) / durationScale) * 100, 0, 100);
    summaryNode.innerHTML = `
      <div class="agent-console__story-grid">
        ${stories.map((story) => `
          <article class="agent-console__story-card">
            <p class="agent-console__story-kicker">${escapeHtml(story.kicker)}</p>
            <p class="agent-console__story-value">${escapeHtml(story.value)}</p>
            <p class="agent-console__story-copy">${escapeHtml(story.copy)}</p>
          </article>
        `).join('')}
      </div>
      <div class="agent-console__history-card-grid">
        <article class="agent-console__history-card">
          <p class="agent-console__history-card-label">Stored runs</p>
          <p class="agent-console__history-card-value">${formatNumber(totalRuns)}</p>
        </article>
        <article class="agent-console__history-card">
          <p class="agent-console__history-card-label">Completed runs</p>
          <p class="agent-console__history-card-value">${formatNumber(completedRuns)}</p>
        </article>
        <article class="agent-console__history-card">
          <p class="agent-console__history-card-label">Failed runs</p>
          <p class="agent-console__history-card-value">${formatNumber(failedRuns)}</p>
        </article>
        <article class="agent-console__history-card">
          <p class="agent-console__history-card-label">Metrics recorded</p>
          <p class="agent-console__history-card-value">${formatNumber(summary.metrics_recorded ?? 0)}</p>
        </article>
        <article class="agent-console__history-card">
          <p class="agent-console__history-card-label">Average duration</p>
          <p class="agent-console__history-card-value">${summary.average_duration_ms == null ? '—' : formatDuration(summary.average_duration_ms)}</p>
          <div class="agent-console__mini-ribbon agent-console__mini-ribbon--duration">
            <div class="agent-console__mini-ribbon-fill" style="width:${durationRibbonWidth}%"></div>
            <div class="agent-console__mini-ribbon-marker" style="left:${durationBenchmarkWidth}%"></div>
            <div class="agent-console__mini-ribbon-marker agent-console__mini-ribbon-marker--sla" style="left:${clamp((sla.durationTargetMs / durationScale) * 100, 0, 100)}%"></div>
          </div>
        </article>
        <article class="agent-console__history-card">
          <p class="agent-console__history-card-label">Success rate</p>
          <p class="agent-console__history-card-value">${totalRuns ? formatNumber(successRate) : '0'}%</p>
          <div class="agent-console__mini-ribbon">
            <div class="agent-console__mini-ribbon-fill" style="width:${successRibbonWidth}%"></div>
            <div class="agent-console__mini-ribbon-marker" style="left:${successBenchmarkWidth}%"></div>
            <div class="agent-console__mini-ribbon-marker agent-console__mini-ribbon-marker--sla" style="left:${clamp(sla.successTarget, 0, 100)}%"></div>
          </div>
        </article>
        <article class="agent-console__history-card">
          <p class="agent-console__history-card-label">Last run</p>
          <p class="agent-console__history-card-value agent-console__history-card-value--small">${summary.last_run_at ? formatTimestamp(summary.last_run_at) : '—'}</p>
        </article>
      </div>
    `;
  }

  function renderLlmSummary(payload) {
    if (!llmSummaryNode) {
      return;
    }
    const models = Array.isArray(payload.loaded_models) ? payload.loaded_models : [];
    const primary = models[0] || null;
    llmSummaryNode.innerHTML = `
      <div class="agent-console__history-card-grid">
        <article class="agent-console__history-card">
          <p class="agent-console__history-card-label">Configured model</p>
          <p class="agent-console__history-card-value agent-console__history-card-value--small">${escapeHtml(payload.configured_model_name || '—')}</p>
        </article>
        <article class="agent-console__history-card">
          <p class="agent-console__history-card-label">Loaded model</p>
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
      </div>
      <div class="agent-console__history-badges">
        <span class="agent-console__history-badge ${payload.api_reachable ? 'agent-console__history-badge--ok' : 'agent-console__history-badge--error'}">${payload.api_reachable ? 'ollama api reachable' : 'ollama api unavailable'}</span>
        <span class="agent-console__history-badge">${payload.running_in_container ? 'running in container' : 'running on host'}</span>
        ${primary?.processor_hint ? `<span class="agent-console__history-badge">${escapeHtml(primary.processor_hint)}</span>` : ''}
      </div>
      ${payload.host_process_metrics?.note ? `<p class="agent-console__meta">${escapeHtml(payload.host_process_metrics.note)}</p>` : ''}
    `;
  }

  async function loadLlmSummary({ silent = false } = {}) {
    if (!llmSummaryNode) {
      return;
    }
    if (!silent) {
      llmSummaryNode.innerHTML = '<p class="agent-console__meta">Loading live Ollama utilization…</p>';
    }
    try {
      const response = await fetch('/ollama/utilization');
      const payload = await response.json();
      if (!response.ok) {
        throw new Error(payload.detail || `LLM utilization request failed with status ${response.status}`);
      }
      renderLlmSummary(payload);
    } catch (error) {
      renderMessage(llmSummaryNode, error instanceof Error ? error.message : 'Unable to load LLM utilization.');
    }
  }

  function renderRunHealthCharts(payload) {
    const summary = payload.summary || {};
    const recentRuns = Array.isArray(payload.recent_runs) ? payload.recent_runs : [];
    const totalRuns = Number(summary.total_runs ?? 0);
    const failedRuns = Number(summary.failed_runs ?? 0);
    const completedRuns = Math.max(0, totalRuns - failedRuns);
    const sla = getSlaSettings();
    const successRate = totalRuns ? (completedRuns / totalRuns) * 100 : 0;
    statusChartNode.innerHTML = `
      <section class="agent-console__table-block agent-console__table-block--chart">
        <h4>Success vs failure ${tooltipIcon('Green indicates completed runs. Red indicates failed runs for the current filter set. The note also compares the current window to the configured success SLA.')}</h4>
        <div class="agent-console__chart-row">
          ${createDonut(completedRuns, failedRuns)}
          <div class="agent-console__chart-legend">
            <p title="Completed runs returned a final answer without raising an exception."><span class="agent-console__legend-swatch agent-console__legend-swatch--success"></span>Completed: ${formatNumber(completedRuns)}</p>
            <p title="Failed runs ended with an exception, tool error, or timeout."><span class="agent-console__legend-swatch agent-console__legend-swatch--failure"></span>Failed: ${formatNumber(failedRuns)}</p>
            <p title="Configured SLA target for success rate."><span class="agent-console__legend-swatch agent-console__legend-swatch--target"></span>SLA target: ${formatPercent(sla.successTarget)} · Current: ${formatPercent(successRate)}</p>
          </div>
        </div>
      </section>
    `;
    if (recentRuns.length === 0) {
      renderMessage(durationChartNode, 'Run a few prompts to render duration history.');
      return;
    }
    const durationPoints = recentRuns.slice().reverse().map((run, index) => ({ label: `Run ${index + 1}`, duration_ms: Number(run.duration_ms ?? 0) }));
    durationChartNode.innerHTML = `
      <section class="agent-console__table-block agent-console__table-block--chart">
        <h4>Recent run durations ${tooltipIcon('This sparkline charts run duration in milliseconds for the visible recent runs and overlays the configured average-duration SLA target.')}</h4>
        ${createSparkline(durationPoints, 'duration_ms', { target: sla.durationTargetMs, targetLabel: `SLA ${formatDuration(sla.durationTargetMs)}` })}
        <div class="agent-console__chart-caption">Latest: ${formatDuration(durationPoints[durationPoints.length - 1].duration_ms)} · SLA overlay: ${formatDuration(sla.durationTargetMs)}</div>
      </section>
    `;
  }

  function renderUsageCharts(payload) {
    const toolUsage = Array.isArray(payload.tool_usage) ? payload.tool_usage.slice(0, 8) : [];
    const recentRuns = Array.isArray(payload.recent_runs) ? payload.recent_runs : [];
    toolUsageNode.innerHTML = `
      <section class="agent-console__table-block agent-console__table-block--chart">
        <h4>Most used tools ${tooltipIcon('Each bar shows how many recorded steps invoked a tool within the current filter set. Click a tool name to open its drilldown page.')}</h4>
        ${createHorizontalBars(toolUsage, (item) => `<a class="agent-console__inline-link" href="tool-drilldown.html?tool=${encodeURIComponent(item.tool_name)}">${escapeHtml(item.label)}</a>`)}
      </section>
    `;
    statusTimelineNode.innerHTML = `
      <section class="agent-console__table-block agent-console__table-block--chart">
        <h4>Status timeline ${tooltipIcon('Each day is split by completed and failed runs for the selected filters.')}</h4>
        ${createStatusTimeline(recentRuns)}
      </section>
    `;
  }

  function renderComparisonBreakdown(node, title, items, keyLabel, tooltipText) {
    if (!Array.isArray(items) || items.length === 0) {
      renderMessage(node, `No ${title.toLowerCase()} data is available for the selected filters.`);
      return;
    }
    const overall = computeExecutiveSignals(lastPayload || { summary: {} });
    const sla = getSlaSettings();
    node.innerHTML = `
      <section class="agent-console__table-block agent-console__table-block--chart">
        <h4>${title} ${tooltipIcon(tooltipText)}</h4>
        <div class="agent-console__comparison-list">
          ${items.map((item) => {
            const successVariance = formatSignedVariance(Number(item.success_rate ?? 0) - overall.successRate, formatPercent);
            const durationVariance = formatSignedVariance(Number(item.average_duration_ms ?? 0) - (overall.averageDuration || 0), formatDuration, false);
            const meetsSla = Number(item.success_rate ?? 0) >= sla.successTarget && (item.average_duration_ms == null || Number(item.average_duration_ms) <= sla.durationTargetMs);
            return `
            <article class="agent-console__comparison-card">
              <div class="agent-console__comparison-header">
                <h5>${escapeHtml(item.label || item[keyLabel] || 'Unknown')}</h5>
                <span class="agent-console__status-pill agent-console__status-pill--${meetsSla ? 'ok' : 'error'}" title="SLA posture for this grouping">${meetsSla ? 'SLA aligned' : 'SLA watch'}</span>
              </div>
              <div class="agent-console__comparison-meter" aria-hidden="true">
                <div class="agent-console__comparison-meter-fill" style="width:${Math.max(8, Number(item.success_rate ?? 0))}%"></div>
              </div>
              <div class="agent-console__comparison-variance-row">
                <span class="agent-console__variance agent-console__variance--${successVariance.kind}">${escapeHtml(successVariance.text)}</span>
                <span class="agent-console__variance agent-console__variance--${durationVariance.kind}">${escapeHtml(durationVariance.text)}</span>
              </div>
              <div class="agent-console__comparison-grid">
                <p><strong>${formatNumber(item.total_runs)}</strong> runs</p>
                <p><strong>${formatNumber(item.completed_runs)}</strong> completed</p>
                <p><strong>${formatNumber(item.failed_runs)}</strong> failed</p>
                <p><strong>${item.average_duration_ms == null ? '—' : formatDuration(item.average_duration_ms)}</strong> avg duration</p>
              </div>
            </article>
          `;
          }).join('')}
        </div>
      </section>
    `;
  }

  function renderTrends(payload) {
    trendsNode.innerHTML = '';
    const series = Array.isArray(payload.metric_series) ? payload.metric_series : [];
    if (series.length === 0) {
      renderMessage(trendsNode, 'No metric series are stored yet. Metric charts will appear after successful prompts return numeric results.');
      return;
    }
    trendsNode.innerHTML = series.map((seriesItem) => {
      const points = Array.isArray(seriesItem.points) ? seriesItem.points : [];
      const latest = points[points.length - 1];
      return `
        <article class="agent-console__trend-card agent-console__metric-clickable${selectedMetricKey === seriesItem.metric_key ? ' agent-console__metric-clickable--selected' : ''}" data-metric-key="${escapeHtml(seriesItem.metric_key)}" role="button" tabindex="0">
          <div class="agent-console__trend-header">
            <div>
              <h4>${escapeHtml(seriesItem.metric_label)}</h4>
              <p class="agent-console__meta">${escapeHtml(seriesItem.tool_name || 'metric series')}</p>
            </div>
            <p class="agent-console__trend-value">${latest ? formatMetricValue(latest.metric_value, seriesItem.unit) : '—'}</p>
          </div>
          ${createSparkline(points)}
        </article>
      `;
    }).join('');
  }

  function renderLatestMetrics(payload) {
    latestNode.innerHTML = '';
    const latestMetrics = Array.isArray(payload.latest_metrics) ? payload.latest_metrics : [];
    if (latestMetrics.length === 0) {
      renderMessage(latestNode, 'No latest metrics are available yet. Successful prompt runs with numeric output will populate this table.');
      return;
    }
    latestNode.innerHTML = `
      <section class="agent-console__table-block">
        <table class="agent-console__table">
          <thead>
            <tr>
              <th>Metric</th>
              <th>Tool</th>
              <th>Latest value</th>
              <th>Delta</th>
              <th>Recorded at</th>
            </tr>
          </thead>
          <tbody>
            ${latestMetrics.map((metric) => `
              <tr class="agent-console__clickable-row${selectedMetricKey === metric.metric_key ? ' agent-console__clickable-row--selected' : ''}" data-metric-key="${escapeHtml(metric.metric_key)}">
                <td>${escapeHtml(metric.metric_label)}</td>
                <td>${escapeHtml(metric.tool_name || '—')}</td>
                <td>${formatMetricValue(metric.metric_value, metric.unit)}</td>
                <td>${metric.delta_from_previous == null ? '—' : `<span class="agent-console__variance agent-console__variance--${metric.delta_from_previous > 0 ? 'positive' : metric.delta_from_previous < 0 ? 'negative' : 'neutral'}">${escapeHtml(formatMetricValue(metric.delta_from_previous, metric.unit))}</span>`}</td>
                <td>${formatTimestamp(metric.recorded_at)}</td>
              </tr>
            `).join('')}
          </tbody>
        </table>
      </section>
    `;
  }

  function renderMetricDetail(detail) {
    selectedMetricDetail = detail;
    setMetricExportState(Boolean(detail));
    if (!detail) {
      metricDetailNode.innerHTML = '<p class="agent-console__meta">Select a metric to inspect the detailed collected payload behind it.</p>';
      return;
    }

    metricDetailNode.innerHTML = `
      <div class="agent-console__detail-grid">
        <article class="agent-console__detail-card">
          <h3>${escapeHtml(detail.metric_label)}</h3>
          <p><strong>Metric key:</strong> ${escapeHtml(detail.metric_key)}</p>
          <p><strong>Tool:</strong> ${detail.tool_name ? `<a class="agent-console__inline-link" href="tool-drilldown.html?tool=${encodeURIComponent(detail.tool_name)}">${escapeHtml(detail.tool_label || detail.tool_name)}</a>` : '—'}</p>
          <p><strong>Samples:</strong> ${formatNumber(detail.summary.sample_count)}</p>
          <p><strong>Distinct runs:</strong> ${formatNumber(detail.summary.distinct_runs)}</p>
          <p><strong>Latest recorded:</strong> ${formatTimestamp(detail.summary.latest_recorded_at)}</p>
        </article>
        <article class="agent-console__detail-card">
          <h3>Value range</h3>
          <p><strong>Latest:</strong> ${formatMetricValue(detail.summary.latest_value, detail.unit)}</p>
          <p><strong>Average:</strong> ${detail.summary.average_value == null ? '—' : formatMetricValue(detail.summary.average_value, detail.unit)}</p>
          <p><strong>Min:</strong> ${formatMetricValue(detail.summary.min_value, detail.unit)}</p>
          <p><strong>Max:</strong> ${formatMetricValue(detail.summary.max_value, detail.unit)}</p>
        </article>
        <article class="agent-console__detail-card agent-console__detail-card--span-2">
          <h3>Metric trend</h3>
          ${createSparkline(detail.points || [])}
        </article>
      </div>
      <section class="agent-console__table-block">
        <h3>Observed metric records</h3>
        <table class="agent-console__table">
          <thead>
            <tr>
              <th>Recorded at</th>
              <th>Value</th>
              <th>Dimensions</th>
              <th>Model</th>
              <th>Region</th>
              <th>Run</th>
            </tr>
          </thead>
          <tbody>
            ${detail.records.map((record) => `
              <tr>
                <td>${formatTimestamp(record.recorded_at)}</td>
                <td>${formatMetricValue(record.metric_value, detail.unit)}</td>
                <td>${escapeHtml(stringifyCompactJson(record.dimensions) || '—')}</td>
                <td>${escapeHtml(record.model_name)}</td>
                <td>${escapeHtml(record.cluster_scope)}</td>
                <td><button class="agent-console__link-button" type="button" data-metric-run-id="${record.run_id}">Open run ${record.run_id}</button></td>
              </tr>
            `).join('')}
          </tbody>
        </table>
      </section>
      <div class="agent-console__metric-records">
        ${detail.records.map((record, index) => `
          <details class="agent-console__step" ${index === 0 ? 'open' : ''}>
            <summary>${escapeHtml(formatTimestamp(record.recorded_at))} · ${formatMetricValue(record.metric_value, detail.unit)} · Run ${record.run_id}</summary>
            <div class="agent-console__step-body">
              <p><strong>Prompt excerpt:</strong> ${escapeHtml(record.prompt_excerpt || '—')}</p>
              <p><strong>Thought:</strong> ${escapeHtml(record.thought || '—')}</p>
              <p><strong>Arguments:</strong></p>
              <pre>${escapeHtml(JSON.stringify(record.tool_arguments ?? {}, null, 2))}</pre>
              <p><strong>Collected result:</strong></p>
              <pre>${escapeHtml(JSON.stringify(record.tool_result ?? {}, null, 2))}</pre>
              ${record.tool_error ? `<p><strong>Tool error:</strong> ${escapeHtml(record.tool_error)}</p>` : ''}
            </div>
          </details>
        `).join('')}
      </div>
    `;
  }

  async function loadMetricDetail(metricKey, { scroll = true, silent = false } = {}) {
    selectedMetricKey = metricKey;
    renderLatestMetrics(lastPayload || { latest_metrics: [] });
    renderTrends(lastPayload || { metric_series: [] });
    metricDetailNode.innerHTML = '<p class="agent-console__meta">Loading metric detail…</p>';
    try {
      const query = new URLSearchParams({
        time_range: rangeSelect.value,
        record_limit: '25',
      });
      const modelNames = getSelectedValues(modelSelect);
      const regionNames = getSelectedValues(regionSelect);
      if (modelNames.length > 0) query.set('model_names', modelNames.join(','));
      if (regionNames.length > 0) query.set('cluster_scopes', regionNames.join(','));
      const response = await fetch(`/history/metrics/${encodeURIComponent(metricKey)}?${query.toString()}`);
      const payload = await response.json();
      if (!response.ok) {
        throw new Error(payload.detail || `Metric detail request failed with status ${response.status}`);
      }
      renderMetricDetail(payload);
      if (!silent) {
        setStatus(`Loaded metric detail for ${payload.metric_label}.`, 'ok');
      }
      if (scroll) {
        metricDetailNode.closest('.agent-console__panel')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }
    } catch (error) {
      selectedMetricKey = null;
      selectedMetricDetail = null;
      renderLatestMetrics(lastPayload || { latest_metrics: [] });
      renderTrends(lastPayload || { metric_series: [] });
      renderMetricDetail(null);
      const message = error instanceof Error ? error.message : 'Unable to load metric detail.';
      if (!silent) {
        setStatus(message, 'error');
      }
    }
  }

  function syncFilterOptions(payload) {
    updateMultiSelectOptions(modelSelect, payload.filter_options?.models || []);
    updateMultiSelectOptions(regionSelect, payload.filter_options?.regions || []);
    updateMultiSelectOptions(toolSelect, payload.filter_options?.tools || []);
    setSelectedValues(modelSelect, payload.filters?.model_names || getSelectedValues(modelSelect));
    setSelectedValues(regionSelect, payload.filters?.cluster_scopes || getSelectedValues(regionSelect));
    setSelectedValues(toolSelect, payload.filters?.tool_names || getSelectedValues(toolSelect));
    updateActiveLabels();
  }

  function renderRuns(payload) {
    runsNode.innerHTML = '';
    const recentRuns = Array.isArray(payload.recent_runs) ? payload.recent_runs : [];
    if (recentRuns.length === 0) {
      renderMessage(runsNode, 'No persisted runs are available yet.');
      return;
    }
    runsNode.innerHTML = `
      <section class="agent-console__table-block">
        <table class="agent-console__table">
          <thead>
            <tr>
              <th>When</th>
              <th>Status</th>
              <th>Model</th>
              <th>Region</th>
              <th>Prompt</th>
              <th>Duration</th>
              <th>Error</th>
            </tr>
          </thead>
          <tbody>
            ${recentRuns.map((run) => `
              <tr class="agent-console__clickable-row${selectedRunId === run.run_id ? ' agent-console__clickable-row--selected' : ''}" data-run-id="${run.run_id}">
                <td><button class="agent-console__link-button" type="button">${escapeHtml(formatTimestamp(run.created_at))}</button></td>
                <td><span class="agent-console__status-pill agent-console__status-pill--${run.status === 'completed' ? 'ok' : 'error'}">${escapeHtml(run.status)}</span></td>
                <td>${escapeHtml(run.model_name)}</td>
                <td>${escapeHtml(run.cluster_scope)}</td>
                <td>${escapeHtml(run.prompt_excerpt || '—')}</td>
                <td>${formatDuration(run.duration_ms)}</td>
                <td>${escapeHtml(run.error_message || '—')}</td>
              </tr>
            `).join('')}
          </tbody>
        </table>
      </section>
    `;
  }

  function renderRunDetail(detail) {
    if (!detail) {
      runDetailNode.innerHTML = '<p class="agent-console__meta">Select a run above to inspect its full trace.</p>';
      return;
    }
    runDetailNode.innerHTML = `
      <div class="agent-console__detail-grid">
        <article class="agent-console__detail-card">
          <h3>Run summary</h3>
          <p><strong>Status:</strong> ${escapeHtml(detail.status)}</p>
          <p><strong>Model:</strong> ${escapeHtml(detail.model_name)}</p>
          <p><strong>Region:</strong> ${escapeHtml(detail.cluster_scope)}</p>
          <p><strong>Duration:</strong> ${formatDuration(detail.duration_ms)}</p>
          <p><strong>Steps:</strong> ${formatNumber(detail.step_count)}</p>
          <p><strong>Created:</strong> ${formatTimestamp(detail.created_at)}</p>
        </article>
        <article class="agent-console__detail-card agent-console__detail-card--span-2">
          <h3>Prompt</h3>
          <pre>${escapeHtml(detail.prompt || '')}</pre>
        </article>
        <article class="agent-console__detail-card agent-console__detail-card--span-2">
          <h3>Answer</h3>
          <pre>${escapeHtml(detail.answer || detail.error_message || '—')}</pre>
        </article>
      </div>
      <div class="agent-console__steps">
        ${detail.steps.map((step) => `
          <details class="agent-console__step" ${step.step_number === 1 ? 'open' : ''}>
            <summary>Step ${formatNumber(step.step_number)}${step.tool_name ? ` · ${escapeHtml(step.tool_label || step.tool_name)}` : ''}</summary>
            <div class="agent-console__step-body">
              <p><strong>Thought:</strong> ${escapeHtml(step.thought || '—')}</p>
              ${step.tool_name ? `<p><strong>Tool:</strong> <a class="agent-console__inline-link" href="tool-drilldown.html?tool=${encodeURIComponent(step.tool_name)}">${escapeHtml(step.tool_label || step.tool_name)}</a></p>` : ''}
              <p><strong>Arguments:</strong></p>
              <pre>${escapeHtml(JSON.stringify(step.tool_arguments ?? {}, null, 2))}</pre>
              <p><strong>Result:</strong></p>
              <pre>${escapeHtml(JSON.stringify(step.tool_result ?? {}, null, 2))}</pre>
              ${step.tool_error ? `<p><strong>Error:</strong> ${escapeHtml(step.tool_error)}</p>` : ''}
              ${step.final_answer ? `<p><strong>Final answer fragment:</strong> ${escapeHtml(step.final_answer)}</p>` : ''}
            </div>
          </details>
        `).join('')}
      </div>
      <section class="agent-console__table-block">
        <h3>Extracted metrics</h3>
        ${detail.metrics.length === 0 ? '<p class="agent-console__meta">No numeric metrics were captured for this run.</p>' : `
          <table class="agent-console__table">
            <thead>
              <tr>
                <th>Metric</th>
                <th>Tool</th>
                <th>Value</th>
                <th>Recorded at</th>
              </tr>
            </thead>
            <tbody>
              ${detail.metrics.map((metric) => `
                <tr>
                  <td>${escapeHtml(metric.metric_label)}</td>
                  <td>${escapeHtml(metric.tool_name || '—')}</td>
                  <td>${formatMetricValue(metric.metric_value, metric.unit)}</td>
                  <td>${formatTimestamp(metric.recorded_at)}</td>
                </tr>
              `).join('')}
            </tbody>
          </table>
        `}
      </section>
    `;
  }

  async function loadRunDetail(runId) {
    selectedRunId = runId;
    renderRuns(lastPayload || { recent_runs: [] });
    runDetailNode.innerHTML = '<p class="agent-console__meta">Loading run details…</p>';
    try {
      const response = await fetch(`/history/runs/${runId}`);
      const payload = await response.json();
      if (!response.ok) {
        throw new Error(payload.detail || `Run detail request failed with status ${response.status}`);
      }
      renderRunDetail(payload);
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Unable to load run details.';
      renderMessage(runDetailNode, message);
      setStatus(message, 'error');
    }
  }

  function toCsv(rows) {
    return rows.map((row) => row.map((value) => {
      const text = String(value ?? '');
      if (text.includes(',') || text.includes('"') || text.includes('\n')) {
        return `"${text.replaceAll('"', '""')}"`;
      }
      return text;
    }).join(',')).join('\n');
  }

  function downloadBlob(filename, blob) {
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = filename;
    document.body.append(anchor);
    anchor.click();
    anchor.remove();
    URL.revokeObjectURL(url);
  }

  function exportCsv() {
    if (!lastPayload) {
      setStatus('Load the dashboard before exporting CSV.', 'error');
      return;
    }
    const summary = lastPayload.summary || {};
    const comparison = lastPayload.time_window_comparison || {};
    const currentWeek = comparison.current || {};
    const previousWeek = comparison.previous || {};
    const exceptions = Array.isArray(lastPayload.executive_exception_rollup) ? lastPayload.executive_exception_rollup : [];
    const rows = [
      ['Section', 'Field', 'Value'],
      ['summary', 'time_range', lastPayload.filters?.time_range || rangeSelect.value],
      ['summary', 'model_names', (lastPayload.filters?.model_names || []).join('|')],
      ['summary', 'cluster_scopes', (lastPayload.filters?.cluster_scopes || []).join('|')],
      ['summary', 'tool_names', (lastPayload.filters?.tool_names || []).join('|')],
      ['summary', 'total_runs', summary.total_runs ?? 0],
      ['summary', 'failed_runs', summary.failed_runs ?? 0],
      ['summary', 'metrics_recorded', summary.metrics_recorded ?? 0],
      ['summary', 'p50_duration_ms', summary.latency_percentiles_ms?.p50 ?? ''],
      ['summary', 'p90_duration_ms', summary.latency_percentiles_ms?.p90 ?? ''],
      ['summary', 'p95_duration_ms', summary.latency_percentiles_ms?.p95 ?? ''],
      ['summary', 'p99_duration_ms', summary.latency_percentiles_ms?.p99 ?? ''],
      ['summary', 'last_run_at', summary.last_run_at || ''],
      [],
      ['time_window_comparison', 'current_week_runs', currentWeek.total_runs ?? 0],
      ['time_window_comparison', 'current_week_success_rate', currentWeek.success_rate ?? 0],
      ['time_window_comparison', 'current_week_average_duration_ms', currentWeek.average_duration_ms ?? ''],
      ['time_window_comparison', 'previous_week_runs', previousWeek.total_runs ?? 0],
      ['time_window_comparison', 'previous_week_success_rate', previousWeek.success_rate ?? 0],
      ['time_window_comparison', 'previous_week_average_duration_ms', previousWeek.average_duration_ms ?? ''],
      ['time_window_comparison', 'delta_runs', comparison.delta?.total_runs ?? ''],
      ['time_window_comparison', 'delta_success_rate', comparison.delta?.success_rate ?? ''],
      ['time_window_comparison', 'delta_average_duration_ms', comparison.delta?.average_duration_ms ?? ''],
      [],
      ['tool_usage', 'label', 'count'],
      ...((lastPayload.tool_usage || []).map((row) => ['tool_usage', row.label, row.count])),
      [],
      ['executive_exception_rollup', 'severity', 'title', 'summary', 'detail'],
      ...(exceptions.map((item) => ['executive_exception_rollup', item.severity || '', item.title || '', item.summary || '', item.detail || ''])),
      [],
      ['recent_runs', 'created_at', 'status', 'model_name', 'cluster_scope', 'duration_ms', 'prompt_excerpt', 'error_message'],
      ...((lastPayload.recent_runs || []).map((run) => [
        'recent_runs',
        run.created_at || '',
        run.status,
        run.model_name,
        run.cluster_scope,
        run.duration_ms,
        run.prompt_excerpt || '',
        run.error_message || '',
      ])),
    ];
    downloadBlob(`openshift-sre-history-${rangeSelect.value}.csv`, new Blob([toCsv(rows)], { type: 'text/csv;charset=utf-8' }));
    setStatus('CSV export downloaded.', 'ok');
  }

  function exportWeeklyOpsReview() {
    if (!lastPayload) {
      setStatus('Load the dashboard before exporting the weekly ops review.', 'error');
      return;
    }

    const summary = lastPayload.summary || {};
    const comparison = lastPayload.time_window_comparison || {};
    const current = comparison.current || {};
    const previous = comparison.previous || {};
    const delta = comparison.delta || {};
    const exceptions = Array.isArray(lastPayload.executive_exception_rollup) ? lastPayload.executive_exception_rollup : [];
    const filters = lastPayload.filters || {};
    const html = `<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <title>OpenShift SRE Weekly Ops Review</title>
    <style>
      body { font-family: Inter, Arial, sans-serif; margin: 0; padding: 32px; background: #f8fafc; color: #0f172a; }
      .sheet { max-width: 1100px; margin: 0 auto; }
      .hero, .panel { background: #fff; border: 1px solid #dbe4f0; border-radius: 20px; box-shadow: 0 14px 34px rgba(15, 23, 42, 0.08); }
      .hero { padding: 28px; margin-bottom: 20px; }
      .kicker { text-transform: uppercase; letter-spacing: 0.08em; font-size: 12px; font-weight: 700; color: #6366f1; margin: 0 0 8px; }
      h1, h2, h3, h4, p { margin-top: 0; }
      .meta { color: #475569; line-height: 1.6; }
      .grid { display: grid; gap: 16px; }
      .grid-4 { grid-template-columns: repeat(4, minmax(0, 1fr)); }
      .grid-2 { grid-template-columns: repeat(2, minmax(0, 1fr)); }
      .panel { padding: 20px; margin-bottom: 18px; }
      .metric { padding: 16px; border-radius: 16px; background: linear-gradient(180deg, rgba(99, 102, 241, 0.08), #fff); border: 1px solid rgba(99, 102, 241, 0.14); }
      .metric-label { font-size: 12px; text-transform: uppercase; letter-spacing: 0.08em; color: #475569; }
      .metric-value { font-size: 28px; font-weight: 700; margin: 6px 0; }
      .delta { display: inline-flex; padding: 4px 10px; border-radius: 999px; font-size: 12px; font-weight: 700; }
      .delta.pos { background: rgba(22,163,74,0.12); color: #166534; }
      .delta.neg { background: rgba(239,68,68,0.12); color: #b91c1c; }
      .delta.neu { background: rgba(148,163,184,0.16); color: #334155; }
      ul { padding-left: 18px; }
      .exception { padding: 16px; border-radius: 16px; border: 1px solid #e2e8f0; background: #fff; }
      .exception.critical { border-color: rgba(239,68,68,0.28); background: rgba(254,226,226,0.42); }
      .exception.warning { border-color: rgba(245,158,11,0.28); background: rgba(254,243,199,0.48); }
      .exception.ok { border-color: rgba(22,163,74,0.24); background: rgba(220,252,231,0.48); }
      table { width: 100%; border-collapse: collapse; }
      th, td { text-align: left; padding: 10px 12px; border-top: 1px solid #e2e8f0; }
      th { color: #475569; font-size: 12px; text-transform: uppercase; letter-spacing: 0.08em; }
      @media print { body { padding: 0; background: #fff; } .panel, .hero { box-shadow: none; break-inside: avoid; } }
    </style>
  </head>
  <body>
    <div class="sheet">
      <section class="hero">
        <p class="kicker">Weekly ops review</p>
        <h1>OpenShift SRE operator storytelling packet</h1>
        <p class="meta">Exported ${escapeHtml(new Date().toLocaleString())}. Filters: range ${escapeHtml(rangeLabels[rangeSelect.value] || rangeSelect.value)}, models ${escapeHtml((filters.model_names || []).join(', ') || 'All models')}, regions ${escapeHtml((filters.cluster_scopes || []).join(', ') || 'All regions')}, tools ${escapeHtml((filters.tool_names || []).join(', ') || 'All tools')}.</p>
      </section>
      <section class="panel">
        <p class="kicker">Headline metrics</p>
        <div class="grid grid-4">
          <article class="metric"><p class="metric-label">Stored runs</p><p class="metric-value">${escapeHtml(formatNumber(summary.total_runs ?? 0))}</p></article>
          <article class="metric"><p class="metric-label">Failed runs</p><p class="metric-value">${escapeHtml(formatNumber(summary.failed_runs ?? 0))}</p></article>
          <article class="metric"><p class="metric-label">Average duration</p><p class="metric-value">${escapeHtml(summary.average_duration_ms == null ? '—' : formatDuration(summary.average_duration_ms))}</p></article>
          <article class="metric"><p class="metric-label">p95 duration</p><p class="metric-value">${escapeHtml(summary.latency_percentiles_ms?.p95 == null ? '—' : formatDuration(summary.latency_percentiles_ms.p95))}</p></article>
        </div>
      </section>
      <section class="panel">
        <p class="kicker">This week vs last week</p>
        <div class="grid grid-2">
          <article>
            <h3>This week</h3>
            <ul>
              <li>Runs: <strong>${escapeHtml(formatNumber(current.total_runs ?? 0))}</strong></li>
              <li>Success rate: <strong>${escapeHtml(formatPercent(current.success_rate ?? 0))}</strong></li>
              <li>Average duration: <strong>${escapeHtml(current.average_duration_ms == null ? '—' : formatDuration(current.average_duration_ms))}</strong></li>
              <li>p95 latency: <strong>${escapeHtml(current.latency_percentiles_ms?.p95 == null ? '—' : formatDuration(current.latency_percentiles_ms.p95))}</strong></li>
            </ul>
          </article>
          <article>
            <h3>Last week</h3>
            <ul>
              <li>Runs: <strong>${escapeHtml(formatNumber(previous.total_runs ?? 0))}</strong></li>
              <li>Success rate: <strong>${escapeHtml(formatPercent(previous.success_rate ?? 0))}</strong></li>
              <li>Average duration: <strong>${escapeHtml(previous.average_duration_ms == null ? '—' : formatDuration(previous.average_duration_ms))}</strong></li>
              <li>p95 latency: <strong>${escapeHtml(previous.latency_percentiles_ms?.p95 == null ? '—' : formatDuration(previous.latency_percentiles_ms.p95))}</strong></li>
            </ul>
          </article>
        </div>
        <div class="grid grid-4" style="margin-top:16px;">
          <article class="metric"><p class="metric-label">Run delta</p><p class="metric-value">${escapeHtml(formatNumber(delta.total_runs ?? 0))}</p></article>
          <article class="metric"><p class="metric-label">Success delta</p><p class="metric-value">${escapeHtml(formatPercent(delta.success_rate ?? 0))}</p></article>
          <article class="metric"><p class="metric-label">Avg duration delta</p><p class="metric-value">${escapeHtml(delta.average_duration_ms == null ? '—' : formatDuration(delta.average_duration_ms))}</p></article>
          <article class="metric"><p class="metric-label">p95 delta</p><p class="metric-value">${escapeHtml(delta.p95_duration_ms == null ? '—' : formatDuration(delta.p95_duration_ms))}</p></article>
        </div>
      </section>
      <section class="panel">
        <p class="kicker">Latency percentiles</p>
        <table>
          <thead><tr><th>Band</th><th>Selected window</th><th>This week</th><th>Last week</th></tr></thead>
          <tbody>
            ${['p50', 'p90', 'p95', 'p99'].map((key) => `<tr><td>${escapeHtml(key.toUpperCase())}</td><td>${escapeHtml(summary.latency_percentiles_ms?.[key] == null ? '—' : formatDuration(summary.latency_percentiles_ms[key]))}</td><td>${escapeHtml(current.latency_percentiles_ms?.[key] == null ? '—' : formatDuration(current.latency_percentiles_ms[key]))}</td><td>${escapeHtml(previous.latency_percentiles_ms?.[key] == null ? '—' : formatDuration(previous.latency_percentiles_ms[key]))}</td></tr>`).join('')}
          </tbody>
        </table>
      </section>
      <section class="panel">
        <p class="kicker">Executive exception rollup</p>
        <div class="grid grid-2">
          ${exceptions.map((item) => `<article class="exception ${escapeHtml(item.severity || 'neutral')}"><h3>${escapeHtml(item.title || 'Exception')}</h3><p>${escapeHtml(item.summary || '')}</p><p class="meta">${escapeHtml(item.detail || '')}</p></article>`).join('') || '<p class="meta">No exceptions were returned for this window.</p>'}
        </div>
      </section>
    </div>
  </body>
</html>`;

    downloadBlob(
      `openshift-sre-weekly-ops-review-${new Date().toISOString().slice(0, 10)}.html`,
      new Blob([html], { type: 'text/html;charset=utf-8' }),
    );
    setStatus('Weekly ops review export downloaded.', 'ok');
  }

  function exportMetricCsv() {
    if (!selectedMetricDetail) {
      setStatus('Select a metric before exporting metric CSV.', 'error');
      return;
    }
    const rows = [
      ['Section', 'Field', 'Value'],
      ['summary', 'metric_key', selectedMetricDetail.metric_key],
      ['summary', 'metric_label', selectedMetricDetail.metric_label],
      ['summary', 'tool_name', selectedMetricDetail.tool_name || ''],
      ['summary', 'time_range', selectedMetricDetail.filters?.time_range || rangeSelect.value],
      ['summary', 'model_names', (selectedMetricDetail.filters?.model_names || []).join('|')],
      ['summary', 'cluster_scopes', (selectedMetricDetail.filters?.cluster_scopes || []).join('|')],
      ['summary', 'sample_count', selectedMetricDetail.summary?.sample_count ?? 0],
      ['summary', 'distinct_runs', selectedMetricDetail.summary?.distinct_runs ?? 0],
      ['summary', 'latest_value', selectedMetricDetail.summary?.latest_value ?? ''],
      ['summary', 'latest_recorded_at', selectedMetricDetail.summary?.latest_recorded_at || ''],
      [],
      ['records', 'run_id', 'step_number', 'recorded_at', 'metric_value', 'dimensions', 'model_name', 'cluster_scope', 'status', 'prompt_excerpt', 'tool_arguments', 'tool_result', 'tool_error'],
      ...((selectedMetricDetail.records || []).map((record) => [
        'records',
        record.run_id,
        record.step_number ?? '',
        record.recorded_at || '',
        record.metric_value,
        stringifyCompactJson(record.dimensions),
        record.model_name || '',
        record.cluster_scope || '',
        record.status || '',
        record.prompt_excerpt || '',
        stringifyCompactJson(record.tool_arguments),
        stringifyCompactJson(record.tool_result),
        record.tool_error || '',
      ])),
    ];
    const safeMetricKey = selectedMetricDetail.metric_key.replace(/[^a-z0-9._-]+/gi, '-');
    downloadBlob(`openshift-sre-metric-${safeMetricKey}.csv`, new Blob([toCsv(rows)], { type: 'text/csv;charset=utf-8' }));
    setStatus(`Metric CSV exported for ${selectedMetricDetail.metric_label}.`, 'ok');
  }

  async function exportPng() {
    if (!lastPayload) {
      setStatus('Load the dashboard before exporting PNG.', 'error');
      return;
    }
    setStatus('Preparing PNG export…');
    const svg = buildDashboardSvg(lastPayload);
    const blob = new Blob([svg], { type: 'image/svg+xml;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const image = new Image();
    await new Promise((resolve, reject) => {
      image.onload = resolve;
      image.onerror = reject;
      image.src = url;
    });
    const canvas = document.createElement('canvas');
    canvas.width = 1400 * 2;
    canvas.height = 980 * 2;
    const context = canvas.getContext('2d');
    if (!context) {
      URL.revokeObjectURL(url);
      throw new Error('Canvas rendering is unavailable in this browser.');
    }
    context.scale(2, 2);
    context.fillStyle = '#f8fafc';
    context.fillRect(0, 0, 1400, 980);
    context.drawImage(image, 0, 0, 1400, 980);
    URL.revokeObjectURL(url);
    canvas.toBlob((pngBlob) => {
      if (!pngBlob) {
        setStatus('Unable to generate PNG export.', 'error');
        return;
      }
      downloadBlob(`openshift-sre-history-${rangeSelect.value}.png`, pngBlob);
      setStatus('PNG export downloaded.', 'ok');
    }, 'image/png');
  }

  function configureAutoRefresh() {
    if (autoRefreshTimer) {
      window.clearInterval(autoRefreshTimer);
      autoRefreshTimer = null;
    }
    const seconds = Number(autoRefreshSelect.value || 0);
    if (seconds > 0) {
      autoRefreshTimer = window.setInterval(() => {
        loadDashboard({ silent: true });
      }, seconds * 1000);
    }
  }

  async function loadDashboard({ silent = false } = {}) {
    refreshButton.disabled = true;
    if (!silent) {
      setStatus('Loading historical dashboard…');
    }
    try {
      updateActiveLabels();
      const query = new URLSearchParams({
        time_range: rangeSelect.value,
        run_limit: '100',
        point_limit: '24',
        series_limit: '12',
      });
      const modelNames = getSelectedValues(modelSelect);
      const regionNames = getSelectedValues(regionSelect);
      const toolNames = getSelectedValues(toolSelect);
      if (modelNames.length > 0) query.set('model_names', modelNames.join(','));
      if (regionNames.length > 0) query.set('cluster_scopes', regionNames.join(','));
      if (toolNames.length > 0) query.set('tool_names', toolNames.join(','));
      const response = await fetch(`/history/overview?${query.toString()}`);
      const payload = await response.json();
      if (!response.ok) {
        throw new Error(payload.detail || `Dashboard request failed with status ${response.status}`);
      }
      lastPayload = payload;
      syncFilterOptions(payload);
      renderBadges(payload);
      renderSummary(payload);
      renderBenchmarkBoard(payload);
      renderStorytelling(payload);
      renderPercentiles(payload);
      renderExceptions(payload);
      await loadLlmSummary({ silent: true });
      renderRunHealthCharts(payload);
      renderUsageCharts(payload);
      renderComparisonBreakdown(modelComparisonNode, 'Model comparison', payload.model_breakdown || [], 'model_name', 'Compare how each visible model performs across success rate, run volume, and average duration.');
      renderComparisonBreakdown(regionComparisonNode, 'Region comparison', payload.region_breakdown || [], 'cluster_scope', 'Compare run outcomes across regions for the currently selected tools and models.');
      renderTrends(payload);
      renderLatestMetrics(payload);
      renderRuns(payload);
      if (selectedMetricKey) {
        await loadMetricDetail(selectedMetricKey, { scroll: false, silent: true });
      } else {
        renderMetricDetail(null);
      }
      if (selectedRunId && !payload.recent_runs.some((run) => run.run_id === selectedRunId)) {
        selectedRunId = null;
        renderRunDetail(null);
      }
      updateHistoryReportState();
      updateLastRefresh();
      setStatus('Dashboard refreshed.', 'ok');
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Unable to load historical dashboard.';
      setStatus(message, 'error');
      badgesNode.innerHTML = '';
      [summaryNode, benchmarkBoardNode, boardBriefNode, storytellingNode, percentilesNode, exceptionsNode, statusChartNode, durationChartNode, toolUsageNode, statusTimelineNode, modelComparisonNode, regionComparisonNode, trendsNode, latestNode, runsNode, runDetailNode].forEach((node) => renderMessage(node, message));
      updateHistoryReportState();
    } finally {
      refreshButton.disabled = false;
    }
  }

  runsNode.addEventListener('click', (event) => {
    const target = event.target.closest('[data-run-id]');
    if (!target) return;
    loadRunDetail(Number(target.dataset.runId));
  });
  latestNode.addEventListener('click', (event) => {
    const target = event.target.closest('[data-metric-key]');
    if (!target) return;
    loadMetricDetail(target.dataset.metricKey);
  });
  trendsNode.addEventListener('click', (event) => {
    const target = event.target.closest('[data-metric-key]');
    if (!target) return;
    loadMetricDetail(target.dataset.metricKey);
  });
  trendsNode.addEventListener('keydown', (event) => {
    const target = event.target.closest('[data-metric-key]');
    if (!target) return;
    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault();
      loadMetricDetail(target.dataset.metricKey);
    }
  });
  metricDetailNode.addEventListener('click', (event) => {
    const target = event.target.closest('[data-metric-run-id]');
    if (!target) return;
    loadRunDetail(Number(target.dataset.metricRunId));
    runDetailNode.closest('.agent-console__panel')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  });
  refreshButton.addEventListener('click', () => loadDashboard());
  rangeSelect.addEventListener('change', () => loadDashboard());
  modelSelect.addEventListener('change', () => loadDashboard());
  regionSelect.addEventListener('change', () => loadDashboard());
  toolSelect.addEventListener('change', () => loadDashboard());
  autoRefreshSelect.addEventListener('change', configureAutoRefresh);
  slaSuccessInput.addEventListener('change', () => {
    updateActiveLabels();
    if (lastPayload) {
      renderBadges(lastPayload);
      renderSummary(lastPayload);
      renderBenchmarkBoard(lastPayload);
      renderRunHealthCharts(lastPayload);
      renderComparisonBreakdown(modelComparisonNode, 'Model comparison', lastPayload.model_breakdown || [], 'model_name', 'Compare how each visible model performs across success rate, run volume, and average duration.');
      renderComparisonBreakdown(regionComparisonNode, 'Region comparison', lastPayload.region_breakdown || [], 'cluster_scope', 'Compare run outcomes across regions for the currently selected tools and models.');
    }
  });
  slaDurationInput.addEventListener('change', () => {
    updateActiveLabels();
    if (lastPayload) {
      renderBadges(lastPayload);
      renderSummary(lastPayload);
      renderBenchmarkBoard(lastPayload);
      renderRunHealthCharts(lastPayload);
      renderComparisonBreakdown(modelComparisonNode, 'Model comparison', lastPayload.model_breakdown || [], 'model_name', 'Compare how each visible model performs across success rate, run volume, and average duration.');
      renderComparisonBreakdown(regionComparisonNode, 'Region comparison', lastPayload.region_breakdown || [], 'cluster_scope', 'Compare run outcomes across regions for the currently selected tools and models.');
    }
  });
  exportLayoutSelect.addEventListener('change', () => {
    updateActiveLabels();
    if (lastPayload) {
      renderBadges(lastPayload);
      renderBenchmarkBoard(lastPayload);
    }
  });
  themeToggleButton.addEventListener('click', () => applyTheme(document.body.dataset.theme === 'dark' ? 'light' : 'dark'));
  exportCsvButton.addEventListener('click', exportCsv);
  exportMetricCsvButton.addEventListener('click', exportMetricCsv);
  exportWeeklyReviewButton.addEventListener('click', exportWeeklyOpsReview);
  reportExportButtons.forEach((button) => button.addEventListener('click', () => handleHistoryReportExport(button)));
  exportPngButton.addEventListener('click', () => {
    exportPng().catch((error) => {
      const message = error instanceof Error ? error.message : 'Unable to export PNG.';
      setStatus(message, 'error');
    });
  });

  // --- WebSocket live updates ---
  function connectWebSocket() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws/events`;
    let ws;
    try {
      ws = new WebSocket(wsUrl);
    } catch {
      return; // static preview — no WS available
    }
    ws.addEventListener('message', (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === 'run_completed') {
          loadDashboard({ silent: true });
        }
      } catch { /* ignore malformed frames */ }
    });
    ws.addEventListener('close', () => {
      setTimeout(connectWebSocket, 5000);
    });
  }

  // --- Accessibility: add ARIA attributes ---
  function applyA11yAttributes() {
    root.setAttribute('role', 'region');
    root.setAttribute('aria-label', 'Historical Dashboard');
    refreshButton?.setAttribute('aria-label', 'Refresh dashboard data');
    themeToggleButton?.setAttribute('aria-label', 'Toggle dark mode');
    exportCsvButton?.setAttribute('aria-label', 'Export run data as CSV');
    exportPngButton?.setAttribute('aria-label', 'Export dashboard as PNG');
    exportWeeklyReviewButton?.setAttribute('aria-label', 'Export weekly ops review');
    rangeSelect?.setAttribute('aria-label', 'Select time range');
    modelSelect?.setAttribute('aria-label', 'Filter by model');
    regionSelect?.setAttribute('aria-label', 'Filter by region');
    toolSelect?.setAttribute('aria-label', 'Filter by tool');
    autoRefreshSelect?.setAttribute('aria-label', 'Auto-refresh interval');
    slaSuccessInput?.setAttribute('aria-label', 'SLA success target percentage');
    slaDurationInput?.setAttribute('aria-label', 'SLA duration target in milliseconds');
    document.querySelectorAll('.agent-console__panel').forEach((panel) => {
      panel.setAttribute('role', 'article');
    });
    document.querySelectorAll('.agent-console__bar').forEach((bar) => {
      bar.setAttribute('role', 'img');
      bar.setAttribute('aria-label', `Bar segment: ${bar.style.width || '0%'}`);
    });
  }

  // --- Tool → run drillthrough helper ---
  toolUsageNode?.addEventListener('click', (event) => {
    const target = event.target.closest('[data-tool-name]');
    if (!target) return;
    const toolName = target.dataset.toolName;
    if (toolName) {
      window.location.href = `/guide/tool-drilldown.html?tool=${encodeURIComponent(toolName)}`;
    }
  });
  toolUsageNode?.addEventListener('keydown', (event) => {
    const target = event.target.closest('[data-tool-name]');
    if (!target) return;
    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault();
      const toolName = target.dataset.toolName;
      if (toolName) {
        window.location.href = `/guide/tool-drilldown.html?tool=${encodeURIComponent(toolName)}`;
      }
    }
  });

  initializeTheme();
  applyA11yAttributes();
  updateActiveLabels();
  configureAutoRefresh();
  renderMetricDetail(null);
  renderRunDetail(null);
  updateHistoryReportState();
  connectWebSocket();
  loadDashboard();

  // ---------------------------------------------------------------------------
  // v0.3.0 — Shareable URL state via query params
  // ---------------------------------------------------------------------------
  function syncFiltersToUrl() {
    const params = new URLSearchParams();
    if (rangeSelect?.value) params.set('range', rangeSelect.value);
    if (modelSelect?.value) params.set('model', modelSelect.value);
    if (regionSelect?.value) params.set('region', regionSelect.value);
    if (toolSelect?.value) params.set('tool', toolSelect.value);
    const url = `${window.location.pathname}?${params.toString()}`;
    window.history.replaceState(null, '', url);
  }

  function restoreFiltersFromUrl() {
    const params = new URLSearchParams(window.location.search);
    if (params.get('range') && rangeSelect) rangeSelect.value = params.get('range');
    if (params.get('model') && modelSelect) modelSelect.value = params.get('model');
    if (params.get('region') && regionSelect) regionSelect.value = params.get('region');
    if (params.get('tool') && toolSelect) toolSelect.value = params.get('tool');
  }

  restoreFiltersFromUrl();
  [rangeSelect, modelSelect, regionSelect, toolSelect].forEach(el => {
    el?.addEventListener('change', () => { syncFiltersToUrl(); });
  });

  // ---------------------------------------------------------------------------
  // v0.3.0 — Run comparison view
  // ---------------------------------------------------------------------------
  const comparedRunIds = new Set();

  function toggleRunComparison(runId) {
    if (comparedRunIds.has(runId)) {
      comparedRunIds.delete(runId);
    } else if (comparedRunIds.size < 4) {
      comparedRunIds.add(runId);
    }
    renderComparisonPanel();
  }

  function renderComparisonPanel() {
    let panel = root.querySelector('.agent-console__comparison-panel');
    if (!comparedRunIds.size) {
      panel?.remove();
      return;
    }
    if (!panel) {
      panel = document.createElement('div');
      panel.className = 'agent-console__comparison-panel';
      root.appendChild(panel);
    }
    panel.innerHTML = `<h3>Comparing ${comparedRunIds.size} runs</h3>` +
      Array.from(comparedRunIds).map(id => `<span class="agent-console__comparison-tag">#${id} <button data-remove-compare="${id}">&times;</button></span>`).join(' ');
    panel.querySelectorAll('[data-remove-compare]').forEach(btn => {
      btn.addEventListener('click', () => {
        comparedRunIds.delete(btn.dataset.removeCompare);
        renderComparisonPanel();
      });
    });
  }

  // Expose for external use
  root.toggleRunComparison = toggleRunComparison;
})();
