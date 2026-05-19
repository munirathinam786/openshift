(() => {
  const root = document.querySelector('[data-posture-radar]');
  if (!root) return;

  const toolsSelect = root.querySelector('[data-radar-tools]');
  const regionsInput = root.querySelector('[data-radar-regions]');
  const rolesInput = root.querySelector('[data-radar-roles]');
  const awsProfileInput = root.querySelector('[data-radar-aws-profile]');
  const awsAccessKeyIdInput = root.querySelector('[data-radar-aws-access-key-id]');
  const awsSecretAccessKeyInput = root.querySelector('[data-radar-aws-secret-access-key]');
  const awsSessionTokenInput = root.querySelector('[data-radar-aws-session-token]');
  const awsVerifySslInput = root.querySelector('[data-radar-aws-verify-ssl]');
  const runButton = root.querySelector('[data-radar-run]');
  const status = root.querySelector('[data-radar-status]');
  const reportStatus = root.querySelector('[data-radar-report-status]');
  const exportButtons = root.querySelectorAll('[data-radar-export-format]');
  const cards = root.querySelector('[data-radar-cards]');
  const raw = root.querySelector('[data-radar-raw]');
  let lastSweepPayload = null;

  const presetTools = {
    network: ['get_caller_identity', 'list_security_groups', 'list_route_tables', 'list_nat_gateways', 'list_vpc_endpoints'],
    storage: ['get_caller_identity', 'list_s3_bucket_posture', 'list_rds_failover_posture', 'list_rds_event_subscriptions'],
    identity: ['get_caller_identity', 'list_enabled_regions', 'list_iam_roles', 'list_lambda_operational_posture']
  };

  function selectedTools() {
    return Array.from(toolsSelect.selectedOptions).map((option) => option.value);
  }

  function parseLines(value) {
    return value
      .split('\n')
      .map((item) => item.trim())
      .filter(Boolean);
  }

  function parseCsv(value) {
    return value
      .split(',')
      .map((item) => item.trim())
      .filter(Boolean);
  }

  function buildRuntime() {
    const runtime = {};
    if (awsProfileInput?.value.trim()) runtime.aws_profile = awsProfileInput.value.trim();
    if (awsAccessKeyIdInput?.value.trim()) runtime.aws_access_key_id = awsAccessKeyIdInput.value.trim();
    if (awsSecretAccessKeyInput?.value.trim()) runtime.aws_secret_access_key = awsSecretAccessKeyInput.value.trim();
    if (awsSessionTokenInput?.value.trim()) runtime.aws_session_token = awsSessionTokenInput.value.trim();
    if (awsVerifySslInput) runtime.aws_verify_ssl = Boolean(awsVerifySslInput.checked);
    return Object.keys(runtime).length ? runtime : undefined;
  }

  function setStatus(message, tone = 'info') {
    status.textContent = message;
    status.dataset.tone = tone;
  }

  function setReportStatus(message, tone = 'info') {
    if (!reportStatus) return;
    reportStatus.textContent = message;
    reportStatus.dataset.tone = tone;
  }

  function escapeHtml(value = '') {
    return String(value)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  function formatNumber(value) {
    const number = Number(value);
    if (!Number.isFinite(number)) return '—';
    return new Intl.NumberFormat('en-US', { maximumFractionDigits: 2 }).format(number);
  }

  function createTimestampSlug() {
    return new Date().toISOString().replace(/[:.]/g, '-');
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

  function toCsv(rows = []) {
    return rows.map((row = []) => row.map((value) => {
      const text = String(value ?? '');
      if (text.includes(',') || text.includes('"') || text.includes('\n')) {
        return `"${text.replaceAll('"', '""')}"`;
      }
      return text;
    }).join(',')).join('\n');
  }

  function summarizeTarget(target) {
    const toolResults = target.tool_results || {};
    const securityGroups = toolResults.list_security_groups || {};
    const routeTables = toolResults.list_route_tables || {};
    const s3 = toolResults.list_s3_bucket_posture || {};
    const budgets = toolResults.list_budgets || {};
    const costByAccount = toolResults.list_cost_by_account || {};
    return {
      region: target.region || 'unknown-region',
      roleArn: target.role_arn || 'current trust context',
      account: target.caller_identity?.account || 'unknown account',
      arn: target.caller_identity?.arn || 'Caller identity unavailable',
      riskyGroups: securityGroups.risky_group_count ?? '—',
      blackholeRoutes: routeTables.blackhole_route_count ?? '—',
      bucketRisk: s3.public_or_unencrypted_count ?? '—',
      budgets: budgets.count ?? '—',
      spend: moneyBlock(costByAccount.total_unblended_cost)
    };
  }

  function buildReportContext() {
    const payload = lastSweepPayload || {};
    const results = Array.isArray(payload.results) ? payload.results : [];
    const summaries = results.map(summarizeTarget);
    return {
      reportLabel: 'Posture Radar Sweep Report',
      generatedAt: new Date(),
      toolNames: Array.isArray(payload.request?.tool_names) ? payload.request.tool_names : selectedTools(),
      regions: Array.isArray(payload.request?.regions) ? payload.request.regions : parseCsv(regionsInput.value),
      roleArns: Array.isArray(payload.request?.role_arns) ? payload.request.role_arns : parseLines(rolesInput.value),
      count: payload.count || results.length,
      summaries,
      results
    };
  }

  function updateExportState() {
    const hasResults = Boolean(lastSweepPayload && Array.isArray(lastSweepPayload.results) && lastSweepPayload.results.length);
    exportButtons.forEach((button) => {
      const exporting = button.dataset.radarExporting === 'true';
      button.disabled = !hasResults || exporting;
    });
    if (!hasResults) {
      setReportStatus('Run the posture radar to unlock exports.');
    }
  }

  function exportRadarCsv(context) {
    const rows = [
      ['Section', 'Field', 'Value'],
      ['summary', 'report_type', context.reportLabel],
      ['summary', 'generated_at', context.generatedAt.toISOString()],
      ['summary', 'target_count', context.count],
      ['summary', 'regions', context.regions.join(', ')],
      ['summary', 'role_arns', context.roleArns.join(', ')],
      ['summary', 'tool_names', context.toolNames.join(', ')],
      [],
      ['targets', 'region', 'role_arn', 'account', 'arn', 'risky_groups', 'blackhole_routes', 'bucket_risk', 'budgets', 'spend'],
      ...context.summaries.map((item) => ['targets', item.region, item.roleArn, item.account, item.arn, item.riskyGroups, item.blackholeRoutes, item.bucketRisk, item.budgets, item.spend]),
      [],
      ['raw_tool_results', 'region', 'role_arn', 'tool_name', 'payload'],
      ...context.results.flatMap((target) => Object.entries(target.tool_results || {}).map(([toolName, payload]) => ['raw_tool_results', target.region || '', target.role_arn || '', toolName, JSON.stringify(payload)]))
    ];
    downloadBlob(`aws-sre-posture-radar-${createTimestampSlug()}.csv`, new Blob([toCsv(rows)], { type: 'text/csv;charset=utf-8' }));
  }

  async function exportRadarPpt(context) {
    const PptxGenJS = window.PptxGenJS;
    if (!PptxGenJS) throw new Error('PowerPoint export library is not available on this page right now.');
    const pptx = new PptxGenJS();
    pptx.layout = 'LAYOUT_WIDE';
    pptx.author = 'GitHub Copilot';
    pptx.company = 'AWS SRE Local Agent';
    pptx.subject = context.reportLabel;
    pptx.title = context.reportLabel;

    const titleSlide = pptx.addSlide();
    titleSlide.background = { color: 'F8FAFC' };
    titleSlide.addText(context.reportLabel, { x: 0.5, y: 0.5, w: 6.5, h: 0.5, fontSize: 24, bold: true, color: '0F172A' });
    titleSlide.addText(`Generated ${context.generatedAt.toLocaleString()}`, { x: 0.5, y: 1.1, w: 4.5, h: 0.3, fontSize: 14, color: '2563EB' });
    titleSlide.addText(`Targets: ${context.count}\nRegions: ${context.regions.join(', ') || '—'}\nRoles: ${context.roleArns.join(', ') || 'Current trust context'}\nTools: ${context.toolNames.join(', ') || '—'}`, { x: 0.5, y: 1.7, w: 5.8, h: 2.2, fontSize: 12, color: '334155', breakLine: true });
    titleSlide.addText((context.summaries.slice(0, 4).map((item) => `• ${item.account} @ ${item.region} — SG risk ${item.riskyGroups}, blackholes ${item.blackholeRoutes}, bucket risk ${item.bucketRisk}, spend ${item.spend}`).join('\n')) || '• No sweep targets were returned.', { x: 6.7, y: 1.4, w: 5.2, h: 3.0, fontSize: 12, color: '0F172A', margin: 0.12, fill: { color: 'DBEAFE' }, line: { color: '93C5FD' } });

    const detailSlide = pptx.addSlide();
    detailSlide.addText('Target summary', { x: 0.5, y: 0.4, w: 6.0, h: 0.4, fontSize: 20, bold: true, color: '0F172A' });
    detailSlide.addText((context.summaries.length ? context.summaries : [{ account: 'No targets', region: '—', riskyGroups: '—', blackholeRoutes: '—', bucketRisk: '—', budgets: '—', spend: '—' }]).map((item) => `• ${item.account} (${item.region})\n  Role: ${item.roleArn}\n  Risky SGs: ${item.riskyGroups} · Blackhole routes: ${item.blackholeRoutes} · Bucket risk: ${item.bucketRisk} · Budgets: ${item.budgets} · Spend: ${item.spend}`).join('\n'), { x: 0.5, y: 1.0, w: 11.4, h: 5.6, fontSize: 11, color: '0F172A', margin: 0.12, fill: { color: 'FFFFFF' }, line: { color: 'CBD5E1' } });

    await pptx.writeFile({ fileName: `aws-sre-posture-radar-${createTimestampSlug()}.pptx` });
  }

  async function exportRadarPdf(context) {
    const jsPDF = window.jspdf?.jsPDF;
    if (!jsPDF) throw new Error('PDF export library is not available on this page right now.');
    const doc = new jsPDF({ unit: 'pt', format: 'a4' });
    const pageWidth = doc.internal.pageSize.getWidth();
    let cursorY = 56;
    const addBlock = (title, lines = []) => {
      const filtered = lines.filter(Boolean);
      if (!filtered.length) return;
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
    doc.setFont('helvetica', 'normal');
    doc.setFontSize(12);
    doc.text(context.generatedAt.toLocaleString(), 48, cursorY);
    cursorY += 24;
    addBlock('Sweep scope', [
      `Targets: ${context.count}`,
      `Regions: ${context.regions.join(', ') || '—'}`,
      `Roles: ${context.roleArns.join(', ') || 'Current trust context'}`,
      `Tools: ${context.toolNames.join(', ') || '—'}`
    ]);
    addBlock('Target summary', context.summaries.length ? context.summaries.map((item) => `${item.account} (${item.region}) — Role: ${item.roleArn}; Risky SGs: ${item.riskyGroups}; Blackhole routes: ${item.blackholeRoutes}; Bucket risk: ${item.bucketRisk}; Budgets: ${item.budgets}; Spend: ${item.spend}`) : ['No sweep targets were returned.']);
    doc.save(`aws-sre-posture-radar-${createTimestampSlug()}.pdf`);
  }

  async function exportRadarWord(context) {
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
    <p class="meta">${escapeHtml(context.generatedAt.toLocaleString())}</p>
    <div>
      <span class="chip">Targets: ${escapeHtml(context.count)}</span>
      <span class="chip">Regions: ${escapeHtml(context.regions.join(', ') || '—')}</span>
      <span class="chip">Tools: ${escapeHtml(context.toolNames.join(', ') || '—')}</span>
    </div>
    <div class="section">
      <h2>Target summary</h2>
      <ul>${(context.summaries.length ? context.summaries : [{ account: 'No targets', region: '—', roleArn: '—', riskyGroups: '—', blackholeRoutes: '—', bucketRisk: '—', budgets: '—', spend: '—' }]).map((item) => `<li>${escapeHtml(`${item.account} (${item.region}) — Role: ${item.roleArn}; Risky SGs: ${item.riskyGroups}; Blackhole routes: ${item.blackholeRoutes}; Bucket risk: ${item.bucketRisk}; Budgets: ${item.budgets}; Spend: ${item.spend}`)}</li>`).join('')}</ul>
    </div>
  </body>
</html>`;
    downloadBlob(`aws-sre-posture-radar-${createTimestampSlug()}.doc`, new Blob([html], { type: 'application/msword' }));
  }

  async function handleExport(button) {
    if (!button || !lastSweepPayload || !Array.isArray(lastSweepPayload.results) || !lastSweepPayload.results.length) {
      setReportStatus('Run the posture radar first so there is sweep evidence to export.', 'error');
      return;
    }
    const format = button.dataset.radarExportFormat || 'word';
    const context = buildReportContext();
    const originalLabel = button.textContent;
    button.dataset.radarExporting = 'true';
    button.textContent = `Preparing ${format.toUpperCase()}…`;
    updateExportState();
    setReportStatus(`Building ${context.reportLabel} as ${format.toUpperCase()}…`, 'ok');
    try {
      if (format === 'csv') {
        exportRadarCsv(context);
      } else if (format === 'ppt') {
        await exportRadarPpt(context);
      } else if (format === 'pdf') {
        await exportRadarPdf(context);
      } else {
        await exportRadarWord(context);
      }
      setReportStatus(`${context.reportLabel} exported as ${format.toUpperCase()}.`, 'ok');
    } catch (error) {
      setReportStatus(error instanceof Error ? error.message : `Unable to export ${context.reportLabel}.`, 'error');
    } finally {
      button.dataset.radarExporting = 'false';
      button.textContent = originalLabel;
      updateExportState();
    }
  }

  function moneyBlock(value) {
    if (!value || typeof value.amount !== 'number') return '—';
    return `${value.amount.toFixed(2)} ${value.unit || 'USD'}`;
  }

  function renderTarget(target) {
    const identity = target.caller_identity || {};
    const toolResults = target.tool_results || {};
    const securityGroups = toolResults.list_security_groups || {};
    const routeTables = toolResults.list_route_tables || {};
    const s3 = toolResults.list_s3_bucket_posture || {};
    const budgets = toolResults.list_budgets || {};
    const costByAccount = toolResults.list_cost_by_account || {};
    return `
      <article class="agent-console__history-card agent-console__history-card--timeline">
        <div class="agent-console__history-badge-row">
          <span class="agent-console__history-badge">${target.region}</span>
          <span class="agent-console__history-badge">${target.role_arn || 'current trust context'}</span>
        </div>
        <h3>${identity.account || 'unknown account'}</h3>
        <p class="agent-console__meta">${identity.arn || 'Caller identity unavailable'}</p>
        <ul>
          <li>Security groups with internet ingress: <strong>${securityGroups.risky_group_count ?? '—'}</strong></li>
          <li>Blackhole routes: <strong>${routeTables.blackhole_route_count ?? '—'}</strong></li>
          <li>Public or unencrypted buckets: <strong>${s3.public_or_unencrypted_count ?? '—'}</strong></li>
          <li>Budgets returned: <strong>${budgets.count ?? '—'}</strong></li>
          <li>Account-level spend: <strong>${moneyBlock(costByAccount.total_unblended_cost)}</strong></li>
        </ul>
      </article>
    `;
  }

  function renderRaw(target) {
    return `
      <details class="agent-console__history-card agent-console__history-card--detail">
        <summary>${target.region} · ${target.caller_identity?.account || 'unknown account'} · raw evidence</summary>
        <pre>${JSON.stringify(target.tool_results || {}, null, 2)}</pre>
      </details>
    `;
  }

  async function runSweep() {
    const toolNames = selectedTools();
    const regions = parseCsv(regionsInput.value);
    const roleArns = parseLines(rolesInput.value);
    if (!toolNames.length) {
      setStatus('Pick at least one tool before running the posture radar.', 'warning');
      return;
    }
    setStatus('Running posture radar across the selected targets…', 'pending');
    runButton.disabled = true;
    try {
      const runtime = buildRuntime();
      const response = await fetch('/platform/sweep', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          tool_names: toolNames,
          regions,
          role_arns: roleArns.length ? roleArns : undefined,
          runtime
        })
      });
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.detail || 'Sweep failed');
      const results = payload.results || [];
      lastSweepPayload = {
        ...payload,
        request: {
          tool_names: toolNames,
          regions,
          role_arns: roleArns.length ? roleArns : [],
          runtime
        }
      };
      cards.innerHTML = results.length
        ? results.map(renderTarget).join('')
        : '<p class="agent-console__meta">No sweep results were returned.</p>';
      raw.innerHTML = results.length
        ? results.map(renderRaw).join('')
        : '<p class="agent-console__meta">No raw evidence was returned.</p>';
      updateExportState();
      setStatus(`Completed ${payload.count || results.length} sweep target(s).`, 'ok');
    } catch (error) {
      lastSweepPayload = null;
      updateExportState();
      setStatus(error.message || 'Sweep failed.', 'error');
    } finally {
      runButton.disabled = false;
    }
  }

  root.querySelectorAll('[data-radar-preset]').forEach((button) => {
    button.addEventListener('click', () => {
      const preset = presetTools[button.dataset.radarPreset] || [];
      Array.from(toolsSelect.options).forEach((option) => {
        option.selected = preset.includes(option.value);
      });
      setStatus(`Loaded the ${button.dataset.radarPreset} tool pack.`, 'info');
    });
  });

  runButton.addEventListener('click', runSweep);
  exportButtons.forEach((button) => button.addEventListener('click', () => handleExport(button)));
  root.addEventListener('keydown', (event) => {
    if ((event.metaKey || event.ctrlKey) && event.key === 'Enter') {
      event.preventDefault();
      runSweep();
    }
  });

  updateExportState();
})();
