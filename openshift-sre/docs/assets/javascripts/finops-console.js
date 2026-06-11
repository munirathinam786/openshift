/**
 * FinOps Console – React 18 single-page application.
 *
 * Architecture:
 *   • No build step required – uses global React / ReactDOM loaded via CDN.
 *   • All components use `React.createElement` (aliased as `h`) instead of JSX.
 *   • Communicates with the FastAPI backend at `/chat` and `/finops/queue`.
 *   • The FINOPS_OPERATIONS catalog defines OpenShift-native optimization
 *     workflows across platform efficiency, capacity, storage, governance,
 *     chargeback, and reporting lanes.
 *   • `buildWorkflow()` post-processes tool-call results into a structured
 *     workflow with opportunity categories, savings estimates, and action cards.
 *   • The approval queue supports persistent stage tracking:
 *     planned → approved → precheck_passed → ready_for_change_window → executed → rolled_back.
 *
 * Entry point: mounts `<FinOpsApp>` into `#finops-root` via `ReactDOM.createRoot`.
 *
 * @file finops-console.js
 * @requires React 18 (global)
 * @requires ReactDOM 18 (global)
 */
(() => {
  'use strict';

  const { createElement: h, useState, useEffect, useCallback, useRef, Fragment } = React;
  const { createRoot } = ReactDOM;

  /* ── helpers ─────────────────────────────────────────────────── */

  /**
   * Safely coerce a value to a finite number (returns 0 for NaN/Infinity/null).
   * @param {*} v - Value to coerce.
   * @returns {number}
   */
  const safeNum = (v) => { const n = Number(v); return Number.isFinite(n) ? n : 0; };
  /** Format a number with locale-aware grouping (max 2 decimal places). */
  const fmtNum = (v) => safeNum(v).toLocaleString(undefined, { maximumFractionDigits: 2 });
  /**
   * Format a value as currency using the Intl API.
   * Falls back to plain number + unit on unsupported currency codes.
   * @param {*} v   - Numeric value.
   * @param {string} [u='USD'] - ISO 4217 currency code.
   * @returns {string}
   */
  const fmtCur = (v, u = 'USD') => {
    try { return safeNum(v).toLocaleString(undefined, { style: 'currency', currency: u, maximumFractionDigits: 2 }); }
    catch { return `${fmtNum(v)} ${u}`; }
  };
  const fmtPct = (v) => `${fmtNum(v)}%`;
  /** Convert a string to a URL-safe slug (lowercase, hyphens only). */
  const slug = (s = '') => s.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/(^-|-$)/g, '');
  const escapeHtml = (value = '') => String(value)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
  const isExecutiveOperation = (operationId) => ['exec-summary', 'board-presentation', 'weekly-digest', 'savings-report', 'unit-economics', 'team-scorecard', 'forecast-scenario'].includes(operationId);
  const summarizeReport = (text = '', maxItems = 6) => {
    const cleaned = String(text || '')
      .split(/\n+/)
      .map((line) => line.replace(/^[-*•\d.\s]+/, '').trim())
      .filter((line) => line.length > 0);
    const unique = [];
    for (const line of cleaned) {
      if (!unique.includes(line)) {
        unique.push(line);
      }
      if (unique.length >= maxItems) break;
    }
    return unique;
  };
  const saveBlob = (blob, fileName) => {
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = fileName;
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
  };

  const buildPptDeck = async ({ operation, response, workflow, queue, generatedAt }) => {
    if (!window.PptxGenJS) {
      throw new Error('PowerPoint export library is not available in this session.');
    }
    const PptxGenJS = window.PptxGenJS;
    const pptx = new PptxGenJS();
    pptx.layout = 'LAYOUT_WIDE';
    pptx.author = 'GitHub Copilot';
    pptx.company = 'OpenShift SRE Local Agent';
    pptx.subject = `${operation.label} report export`;
    pptx.title = `${operation.label} – FinOps report`;
    pptx.lang = 'en-US';
    pptx.theme = {
      headFontFace: 'Aptos Display',
      bodyFontFace: 'Aptos',
      lang: 'en-US'
    };

    const summaryBullets = summarizeReport(response, 8);
    const queueItems = Array.isArray(queue?.items) ? queue.items : [];
    const topOpportunities = workflow?.opportunities?.slice(0, 5) || [];

    const addTitle = (slide, title, subtitle) => {
      slide.addText(title, { x: 0.55, y: 0.45, w: 8.9, h: 0.55, fontSize: 24, bold: true, color: 'E2E8F0' });
      slide.addText(subtitle, { x: 0.55, y: 1.02, w: 11.8, h: 0.34, fontSize: 10, color: 'B6C2D2' });
      slide.addShape(pptx.ShapeType.rect, { x: 0.4, y: 0.3, w: 12.45, h: 6.9, line: { color: '1E293B', transparency: 100 }, fill: { color: '0F172A' }, radius: 0.16 });
      slide.addShape(pptx.ShapeType.roundRect, { x: 0.55, y: 0.48, w: 0.14, h: 0.72, line: { color: '22D3EE', transparency: 100 }, fill: { color: '22D3EE' }, radius: 0.08 });
    };

    const addFooter = (slide) => {
      slide.addText(`Generated ${generatedAt.toLocaleString()} · ${operation.label}`, { x: 0.55, y: 6.72, w: 11.2, h: 0.22, fontSize: 8, color: '94A3B8', align: 'left' });
    };

    const titleSlide = pptx.addSlide();
    addTitle(titleSlide, `${operation.label}`, 'FinOps executive export');
    titleSlide.addText('OpenShift SRE Local Agent FinOps workspace export', { x: 0.78, y: 1.6, w: 5.5, h: 0.3, fontSize: 14, color: '67E8F9', bold: true });
    titleSlide.addText([
      { text: 'Generated report includes:\n', options: { bold: true, color: 'E2E8F0' } },
      { text: '• executive summary bullets\n• workflow KPIs and savings posture\n• top recommendations\n• approval queue alignment' }
    ], { x: 0.78, y: 2.02, w: 4.5, h: 1.6, fontSize: 16, color: 'E2E8F0', breakLine: false, margin: 0.02 });
    titleSlide.addShape(pptx.ShapeType.roundRect, { x: 7.05, y: 1.55, w: 5.08, h: 3.65, radius: 0.18, line: { color: '334155', transparency: 0, width: 1 }, fill: { color: '111827', transparency: 0 } });
    titleSlide.addText(`Operation\n${operation.label}`, { x: 7.4, y: 1.95, w: 2.25, h: 0.95, fontSize: 18, bold: true, color: 'F8FAFC' });
    titleSlide.addText(`Group\n${operation.group}`, { x: 9.78, y: 1.95, w: 1.8, h: 0.95, fontSize: 18, bold: true, color: '67E8F9' });
    titleSlide.addText(`Prompt length\n${String((response || '').length).toLocaleString()} chars response`, { x: 7.4, y: 3.25, w: 4.0, h: 0.75, fontSize: 13, color: 'CBD5E1' });
    addFooter(titleSlide);

    const summarySlide = pptx.addSlide();
    addTitle(summarySlide, 'Executive narrative', 'The agent answer is condensed into reusable presentation bullets.');
    if (summaryBullets.length > 0) {
      summarySlide.addText(summaryBullets.map((bullet) => ({ text: bullet, options: { bullet: { indent: 18 } } })), {
        x: 0.78,
        y: 1.6,
        w: 6.5,
        h: 4.8,
        fontSize: 16,
        color: 'E2E8F0',
        valign: 'top',
        breakLine: true,
        margin: 0.08
      });
    } else {
      summarySlide.addText('No structured report bullets were available yet. Run a FinOps reporting operation first.', { x: 0.78, y: 1.8, w: 6.4, h: 1.0, fontSize: 18, color: 'FCA5A5' });
    }
    summarySlide.addShape(pptx.ShapeType.roundRect, { x: 7.55, y: 1.55, w: 4.45, h: 4.9, radius: 0.18, line: { color: '164E63', width: 1 }, fill: { color: '082F49' } });
    summarySlide.addText('Operator note', { x: 7.88, y: 1.88, w: 2.3, h: 0.32, fontSize: 14, bold: true, color: '67E8F9' });
    summarySlide.addText('Use board-oriented operations such as Executive Cost Summary or Board-Ready Cost Presentation for the cleanest slide narrative. Optimization workflows still export, but the deck will emphasize actions over storyline.', { x: 7.88, y: 2.25, w: 3.7, h: 2.5, fontSize: 13, color: 'E2E8F0', margin: 0.04 });
    addFooter(summarySlide);

    const kpiSlide = pptx.addSlide();
    addTitle(kpiSlide, 'Workflow KPIs', 'Savings posture, exposure, and commitment context from the current report.');
    const kpis = [
      ['Estimated monthly savings', workflow ? fmtCur(workflow.totalEstimatedMonthlySavings) : '—'],
      ['Observed spend', workflow?.overview?.totalObservedSpend != null ? fmtCur(workflow.overview.totalObservedSpend) : '—'],
      ['Forecast', workflow?.overview?.forecastTotal != null ? fmtCur(workflow.overview.forecastTotal, workflow.overview.forecastUnit) : '—'],
      ['Savings Plans coverage', workflow?.overview?.savingsPlansCoverage != null ? fmtPct(workflow.overview.savingsPlansCoverage) : '—'],
      ['Rightsizing savings', workflow ? fmtCur(workflow.overview.rightsizingSavings) : '—'],
      ['Queue items', String(queueItems.length)]
    ];
    kpis.forEach(([label, value], index) => {
      const col = index % 3;
      const row = Math.floor(index / 3);
      const x = 0.8 + (col * 3.9);
      const y = 1.7 + (row * 1.85);
      kpiSlide.addShape(pptx.ShapeType.roundRect, { x, y, w: 3.35, h: 1.3, radius: 0.14, line: { color: '1E3A5F', width: 1 }, fill: { color: row === 0 ? '0B253B' : '111827' } });
      kpiSlide.addText(label, { x: x + 0.2, y: y + 0.18, w: 2.8, h: 0.22, fontSize: 10, color: '67E8F9', bold: true });
      kpiSlide.addText(value, { x: x + 0.2, y: y + 0.48, w: 2.9, h: 0.34, fontSize: 20, color: 'F8FAFC', bold: true });
    });
    if (workflow?.categorySummaries?.length) {
      kpiSlide.addText('Category savings highlights', { x: 0.82, y: 5.45, w: 3.8, h: 0.24, fontSize: 14, bold: true, color: 'E2E8F0' });
      workflow.categorySummaries.slice(0, 5).forEach((item, index) => {
        kpiSlide.addText(`${item.label}: ${fmtCur(item.estimatedMonthlySavings, item.unit)} across ${item.count} item(s)`, { x: 0.96, y: 5.78 + (index * 0.22), w: 5.8, h: 0.18, fontSize: 10, color: 'CBD5E1' });
      });
    }
    addFooter(kpiSlide);

    const actionsSlide = pptx.addSlide();
    addTitle(actionsSlide, 'Priority recommendations', 'Top opportunities to communicate and govern from the current FinOps report.');
    if (topOpportunities.length > 0) {
      topOpportunities.forEach((item, index) => {
        const y = 1.45 + (index * 1.02);
        actionsSlide.addShape(pptx.ShapeType.roundRect, { x: 0.76, y, w: 11.35, h: 0.82, radius: 0.12, line: { color: '334155', width: 1 }, fill: { color: index % 2 === 0 ? '111827' : '172033' } });
        actionsSlide.addText(item.title, { x: 0.95, y: y + 0.12, w: 3.5, h: 0.18, fontSize: 14, bold: true, color: 'F8FAFC' });
        actionsSlide.addText(`${item.category} · ${item.confidence} confidence · ${item.risk} risk`, { x: 0.95, y: y + 0.39, w: 2.7, h: 0.14, fontSize: 9, color: '67E8F9' });
        actionsSlide.addText(item.action, { x: 3.9, y: y + 0.12, w: 5.2, h: 0.42, fontSize: 11, color: 'CBD5E1', fit: 'shrink' });
        actionsSlide.addText(fmtCur(item.estimatedMonthlySavings, item.unit), { x: 9.55, y: y + 0.18, w: 1.9, h: 0.22, fontSize: 14, bold: true, color: 'A7F3D0', align: 'right' });
      });
    } else {
      actionsSlide.addText('No structured opportunities were available. The report may still be narrative-only, but you can export the response summary slide.', { x: 0.9, y: 1.8, w: 10.5, h: 0.8, fontSize: 18, color: 'FCA5A5' });
    }
    addFooter(actionsSlide);

    const queueSlide = pptx.addSlide();
    addTitle(queueSlide, 'Approval queue alignment', 'Presentation handoff includes the latest queue state so governance and execution planning stay synchronized.');
    if (queueItems.length > 0) {
      queueItems.slice(0, 6).forEach((item, index) => {
        const y = 1.5 + (index * 0.78);
        queueSlide.addShape(pptx.ShapeType.roundRect, { x: 0.82, y, w: 11.2, h: 0.58, radius: 0.1, line: { color: '1E3A5F', width: 1 }, fill: { color: '0B253B' } });
        queueSlide.addText(item.title || item.opportunity_key || 'Queue item', { x: 1.0, y: y + 0.12, w: 4.6, h: 0.16, fontSize: 12, color: 'F8FAFC', bold: true });
        queueSlide.addText(item.execution_stage || 'planned', { x: 6.15, y: y + 0.12, w: 1.7, h: 0.16, fontSize: 11, color: '67E8F9', bold: true });
        queueSlide.addText(item.action || item.action_summary || '', { x: 7.1, y: y + 0.1, w: 4.55, h: 0.22, fontSize: 10, color: 'CBD5E1', fit: 'shrink' });
      });
    } else {
      queueSlide.addText('No approval items are currently queued. Queue recommended actions from the workspace to include them in future decks.', { x: 0.9, y: 1.85, w: 10.8, h: 0.7, fontSize: 18, color: 'CBD5E1' });
    }
    addFooter(queueSlide);

    await pptx.writeFile({ fileName: `finops-${slug(operation.id || operation.label)}-${generatedAt.toISOString().replace(/[:.]/g, '-')}.pptx` });
  };

  const buildPdfReport = async ({ operation, response, workflow, queue, generatedAt }) => {
    const jsPDF = window.jspdf?.jsPDF;
    if (!jsPDF) {
      throw new Error('PDF export library is not available in this session.');
    }

    const doc = new jsPDF({ orientation: 'portrait', unit: 'pt', format: 'a4' });
    const pageWidth = doc.internal.pageSize.getWidth();
    const pageHeight = doc.internal.pageSize.getHeight();
    const margin = 48;
    const contentWidth = pageWidth - (margin * 2);
    let y = margin;

    const ensureSpace = (needed = 24) => {
      if (y + needed <= pageHeight - margin) return;
      doc.addPage();
      y = margin;
    };

    const addLine = (text, options = {}) => {
      const { size = 11, color = [31, 41, 55], weight = 'normal', gap = 16 } = options;
      doc.setFont('helvetica', weight);
      doc.setFontSize(size);
      doc.setTextColor(...color);
      const lines = doc.splitTextToSize(String(text), contentWidth);
      const needed = (lines.length * (size + 3)) + gap;
      ensureSpace(needed);
      doc.text(lines, margin, y);
      y += (lines.length * (size + 3)) + gap;
    };

    const addSection = (title) => {
      addLine(title, { size: 15, color: [15, 23, 42], weight: 'bold', gap: 12 });
    };

    addLine(operation.label, { size: 22, color: [2, 132, 199], weight: 'bold', gap: 10 });
    addLine(`FinOps report export · Generated ${generatedAt.toLocaleString()}`, { size: 10, color: [100, 116, 139], gap: 20 });
    addLine(`${operation.group} · ${isExecutiveOperation(operation.id) ? 'Executive narrative' : 'Operator workflow narrative'}`, { size: 11, color: [51, 65, 85], gap: 24 });

    addSection('Executive highlights');
    const summaryBullets = summarizeReport(response, 10);
    if (summaryBullets.length > 0) {
      summaryBullets.forEach((item) => addLine(`• ${item}`, { size: 11, color: [31, 41, 55], gap: 10 }));
    } else {
      addLine('No report highlights are available yet. Run a reporting-oriented FinOps operation first.', { color: [185, 28, 28] });
    }

    addSection('Workflow posture');
    addLine(`Estimated monthly savings: ${workflow ? fmtCur(workflow.totalEstimatedMonthlySavings) : '—'}`);
    addLine(`Observed spend: ${workflow?.overview?.totalObservedSpend != null ? fmtCur(workflow.overview.totalObservedSpend) : '—'}`);
    addLine(`Forecast: ${workflow?.overview?.forecastTotal != null ? fmtCur(workflow.overview.forecastTotal, workflow.overview.forecastUnit) : '—'}`);
    addLine(`Savings Plans coverage: ${workflow?.overview?.savingsPlansCoverage != null ? fmtPct(workflow.overview.savingsPlansCoverage) : '—'}`);
    addLine(`Approval queue items: ${Array.isArray(queue?.items) ? queue.items.length : 0}`);

    addSection('Priority recommendations');
    const topOpportunities = workflow?.opportunities?.slice(0, 6) || [];
    if (topOpportunities.length > 0) {
      topOpportunities.forEach((item, index) => {
        addLine(`${index + 1}. ${item.title} — ${fmtCur(item.estimatedMonthlySavings, item.unit)}`, { weight: 'bold', gap: 8 });
        addLine(`${item.category} · ${item.confidence} confidence · ${item.risk} risk`, { size: 10, color: [2, 132, 199], gap: 8 });
        addLine(item.action, { size: 10, gap: 8 });
        addLine(`Evidence: ${item.evidence}`, { size: 9, color: [71, 85, 105], gap: 12 });
      });
    } else {
      addLine('No structured opportunities are available yet for this report.', { color: [100, 116, 139] });
    }

    addSection('Approval queue alignment');
    const queueItems = Array.isArray(queue?.items) ? queue.items.slice(0, 8) : [];
    if (queueItems.length > 0) {
      queueItems.forEach((item, index) => {
        addLine(`${index + 1}. ${item.title || item.opportunity_key} — ${item.execution_stage || 'planned'}`, { weight: 'bold', gap: 8 });
        addLine(item.action || item.action_summary || 'No action summary recorded.', { size: 10, gap: 10 });
      });
    } else {
      addLine('No approval queue items are currently present.', { color: [100, 116, 139] });
    }

    doc.save(`finops-${slug(operation.id || operation.label)}-${generatedAt.toISOString().replace(/[:.]/g, '-')}.pdf`);
  };
  /**
   * Classify an OpenShift or platform signal into an opportunity category.
   * @param {string} s - OpenShift resource or signal label.
   * @returns {'compute'|'storage'|'network'|'governance'|'workload'|null}
   */
  const svcCat = (s = '') => {
    const l = s.toLowerCase();
    if (/node|machine|worker|cpu|memory|capacity|autoscal/i.test(l)) return 'compute';
    if (/pvc|pv|storage|volume|snapshot|image registry|image stream/i.test(l)) return 'storage';
    if (/route|ingress|service|network|egress|bandwidth|latency/i.test(l)) return 'network';
    if (/quota|policy|label|tag|scc|compliance|guardrail/i.test(l)) return 'governance';
    if (/namespace|project|pod|deployment|statefulset|daemonset|build/i.test(l)) return 'workload';
    return null;
  };

  /* ── FinOps operations catalog ──────────────────────────────── */

  /**
   * Catalog of all FinOps operations available in the dropdown.
   * Each entry has: id (unique slug), label (display name), group
   * (dropdown optgroup), and prompt (pre-filled agent prompt text).
   * Groups: Workflows, Cost Analysis, Commitment, Optimization, Governance,
   *         Chargeback & Showback, Purchasing, Reporting & Executive.
   * @type {Array<{id: string, label: string, group: string, prompt: string}>}
   */
  const FINOPS_OPERATIONS = [
    /* ── Workflows ──────────────────────────────────────────────── */
    { id: 'full-optimizer',        label: 'Full Platform Optimizer',                group: 'Workflows',              prompt: 'Act as an OpenShift FinOps and platform optimization specialist. Review node capacity, workload requests and limits, namespace density, storage lifecycle posture, route and ingress exposure, operator footprint, quotas, and cluster health signals. Produce a workflow-ready response with: 1) opportunity categories for compute, storage, network, governance, and workload hygiene, 2) proposed actions, 3) estimated savings or avoided waste, 4) operational risk, 5) rollback guidance, 6) approval-queue recommendations, and 7) the exact cluster evidence that justifies each recommendation.' },
    { id: 'quick-wins',            label: 'OpenShift Quick Wins',                   group: 'Workflows',              prompt: 'Identify immediate OpenShift optimization actions across over-provisioned namespaces, idle workloads, stale persistent storage, oversized quotas, low-value routes, and unnecessary operator subscriptions. Separate findings into quick wins, medium-risk changes, and items that need team coordination.' },
    { id: 'monthly-review',        label: 'Monthly Platform Efficiency Review',     group: 'Workflows',              prompt: 'Perform a monthly OpenShift efficiency review: summarize the biggest cost or waste drivers, highlight top platform changes, review node and workload efficiency, identify quota or storage drift, and produce a prioritized action plan for the coming month.' },
    { id: 'incident-cost',         label: 'Resource Spike Investigation',           group: 'Workflows',              prompt: 'Investigate recent resource or cost spikes in OpenShift. Correlate them with rollouts, namespace growth, node pressure, storage expansion, route traffic changes, and operator churn. Identify likely root causes, quantify impact, and recommend preventive guardrails.' },
    { id: 'well-architected-cost', label: 'OpenShift Efficiency Assessment',        group: 'Workflows',              prompt: 'Evaluate the OpenShift platform for operational efficiency: rightsizing, capacity matching, namespace governance, storage hygiene, route exposure, and continuous optimization. Provide a scored assessment with specific remediation steps.' },

    /* ── Resource Analysis ─────────────────────────────────────── */
    { id: 'capacity-baseline',     label: 'Node Capacity Baseline',                 group: 'Resource Analysis',       prompt: 'Analyze node inventory, machine sets, machine config pools, and workload placement. Highlight low-utilization worker pools, uneven packing, and opportunities to consolidate capacity safely.' },
    { id: 'namespace-density',     label: 'Namespace Density Review',               group: 'Resource Analysis',       prompt: 'Review namespace and project density. Identify lightly used namespaces, duplicated services, idle pods, and projects that should be archived, merged, or right-sized.' },
    { id: 'workload-requests',     label: 'Requests / Limits Efficiency',           group: 'Resource Analysis',       prompt: 'Inspect workload health together with resource requests and limits. Highlight over-provisioned workloads, workloads likely to starve other tenants, and opportunities to improve bin-packing.' },
    { id: 'storage-growth',        label: 'Storage Growth Review',                  group: 'Resource Analysis',       prompt: 'Inspect persistent storage usage and growth patterns. Highlight stale PVCs, oversized claims, duplicate snapshots or image artifacts, and storage classes with weak governance posture.' },
    { id: 'route-exposure',        label: 'Route & Ingress Footprint',              group: 'Resource Analysis',       prompt: 'Review routes, ingresses, and services. Identify low-value exposure, duplicate routes, insecure edge posture, and traffic patterns that create avoidable infrastructure overhead.' },
    { id: 'operator-footprint',    label: 'Operator Footprint Review',              group: 'Resource Analysis',       prompt: 'Review installed subscriptions and ClusterServiceVersions. Highlight unused operators, redundant platform add-ons, and lifecycle drift that increases platform cost or support load.' },

    /* ── Chargeback & Showback ─────────────────────────────────── */
    { id: 'chargeback-namespace',  label: 'Chargeback by Namespace',                group: 'Chargeback & Showback',  prompt: 'Produce a namespace chargeback report using project, workload, storage, and quota signals. Estimate each namespace’s share of platform cost, flag over-provisioned teams, and recommend right-sizing for fairer allocation.' },
    { id: 'chargeback-platform',   label: 'Chargeback by Platform Pattern',         group: 'Chargeback & Showback',  prompt: 'Produce a chargeback view across the platform patterns in this repository, such as ROSA, ARO, IPI, UPI, and IBM Z. Compare major cost drivers, shared services, and cluster-specific overhead.' },
    { id: 'showback-team',         label: 'Showback by Team / Owner',               group: 'Chargeback & Showback',  prompt: 'Generate a team-oriented showback report using labels, namespaces, workload ownership, and storage usage. Highlight teams with the highest month-over-month growth and the weakest resource efficiency.' },
    { id: 'shared-services',       label: 'Shared Services Allocation',             group: 'Chargeback & Showback',  prompt: 'Identify shared OpenShift platform costs such as ingress, observability, image registry, operator overhead, and cluster services. Recommend a fair allocation model for teams and environments.' },
    { id: 'untagged-spend',        label: 'Unowned Platform Spend',                 group: 'Chargeback & Showback',  prompt: 'Identify OpenShift resources and namespaces that cannot be clearly mapped to a team, owner, or project. Produce a remediation plan using labels, quotas, and namespace ownership conventions.' },
    { id: 'budget-variance',       label: 'Quota vs Usage Variance',                group: 'Chargeback & Showback',  prompt: 'Compare quota allocations with actual namespace and workload usage. Highlight teams or projects that are carrying far more reserved capacity than they consume.' },

    /* ── Capacity & Performance ────────────────────────────────── */
    { id: 'rightsizing',           label: 'Rightsizing Opportunities',              group: 'Capacity & Performance', prompt: 'Review workload health, pod density, node pressure, and machine pool posture. Recommend rightsizing actions for worker capacity, resource requests and limits, and idle non-production workloads.' },
    { id: 'burst-analysis',        label: 'Burst Capacity Review',                  group: 'Capacity & Performance', prompt: 'Analyze where bursty traffic or rollout behavior forces excess worker headroom. Identify namespaces, routes, or workloads that cause capacity spikes and propose safer scaling guardrails.' },
    { id: 'idle-resources',        label: 'Idle Resource Scan',                     group: 'Capacity & Performance', prompt: 'Identify idle and underutilized OpenShift resources such as low-traffic routes, dormant workloads, oversized quotas, stale namespaces, and worker capacity that can be reclaimed safely.' },
    { id: 'container-optimization',label: 'Pod Packing & Scheduling Efficiency',    group: 'Capacity & Performance', prompt: 'Analyze workload scheduling, node pressure, machine sets, and rollout health. Recommend better pod packing, request tuning, and worker pool adjustments to improve cost efficiency.' },
    { id: 'scheduling-automation', label: 'Non-Prod Runtime Scheduling',            group: 'Capacity & Performance', prompt: 'Identify non-production namespaces or workloads that can be scaled down outside business hours. Recommend scheduling policies and validation steps for dev, test, and sandbox environments.' },

    /* ── Storage & Data Services ───────────────────────────────── */
    { id: 'storage-optimization',  label: 'PVC & StorageClass Hygiene',             group: 'Storage & Data Services', prompt: 'Review PVCs, PVs, storage classes, and workload storage posture. Recommend cleanup, right-sizing, reclaim-policy improvements, and lifecycle actions for stale or oversized storage.' },
    { id: 'registry-cleanup',      label: 'Image Registry & Artifact Cleanup',      group: 'Storage & Data Services', prompt: 'Review image streams, builds, and related artifact sprawl. Identify stale images, redundant builds, and cleanup opportunities that reduce storage growth.' },
    { id: 'data-service-review',   label: 'Stateful Workload Efficiency',           group: 'Storage & Data Services', prompt: 'Inspect stateful workloads, PVC growth, storage-class usage, and failover posture. Highlight over-provisioning, weak resiliency settings, and data-service cleanup opportunities.' },
    { id: 'backup-retention',      label: 'Backup & Retention Review',              group: 'Storage & Data Services', prompt: 'Review backup, snapshot, and retention posture around persistent storage and build artifacts. Highlight retention that exceeds operational need and recommend safer lifecycle policies.' },

    /* ── Network & Edge ────────────────────────────────────────── */
    { id: 'network-optimization',  label: 'Route / Service Efficiency',             group: 'Network & Edge',         prompt: 'Analyze routes, services, ingresses, and network policies. Identify duplicated exposure, unused services, overly broad access, and networking posture that adds avoidable platform cost or risk.' },
    { id: 'egress-review',         label: 'Egress & Traffic Locality Review',       group: 'Network & Edge',         prompt: 'Review workload placement, route topology, and network policy posture to identify traffic patterns that create avoidable egress or cross-cluster overhead.' },
    { id: 'edge-hardening',        label: 'Edge Footprint Rationalization',         group: 'Network & Edge',         prompt: 'Inspect edge routes and ingress posture. Recommend reducing route sprawl, eliminating low-value exposure, and standardizing TLS posture to lower operational drag.' },

    /* ── Governance ────────────────────────────────────────────── */
    { id: 'tagging-governance',    label: 'Labels & Ownership Audit',               group: 'Governance',             prompt: 'Audit OpenShift namespaces, workloads, and storage for missing labels, ownership metadata, and inconsistent project taxonomy. Recommend enforcement guardrails and reporting improvements.' },
    { id: 'service-quotas',        label: 'Quota & Limit Review',                   group: 'Governance',             prompt: 'Review resource quotas, cluster resource quotas, and namespace limits. Flag quotas that are too high, too low, or no longer aligned with actual consumption.' },
    { id: 'policy-compliance',     label: 'Policy & Guardrail Compliance',          group: 'Governance',             prompt: 'Evaluate the OpenShift environment for guardrail compliance across SCCs, network policies, labels, quotas, and platform hygiene. Produce a scorecard with remediation priorities.' },
    { id: 'budget-alerts',         label: 'Efficiency Alerting Review',             group: 'Governance',             prompt: 'Review how the platform should alert on unusual namespace growth, worker pressure, PVC expansion, idle resources, and route sprawl. Recommend thresholds and ownership paths for each signal.' },
    { id: 'org-guardrails',        label: 'Organization Efficiency Guardrails',     group: 'Governance',             prompt: 'Recommend governance guardrails that prevent oversized namespaces, unnecessary operator sprawl, stale routes, weak labeling, and quota misuse across the OpenShift estate.' },

    /* ── Reporting & Executive ─────────────────────────────────── */
    { id: 'exec-summary',          label: 'Executive Platform Summary',             group: 'Reporting & Executive',  prompt: 'Produce a C-level summary of OpenShift platform efficiency: major cost and waste drivers, month-over-month changes, top optimization opportunities, operational risks, and strategic recommendations for the platform estate.' },
    { id: 'board-presentation',    label: 'Board-Ready Platform Narrative',         group: 'Reporting & Executive',  prompt: 'Generate a board-ready OpenShift platform efficiency presentation outline. Cover platform scale, key cost drivers, optimization opportunities, unit economics, governance posture, and strategic recommendations. Suggest chart types and speaker notes.' },
    { id: 'weekly-digest',         label: 'Weekly Platform Digest',                 group: 'Reporting & Executive',  prompt: 'Generate a weekly OpenShift efficiency digest: summarize resource spikes, storage growth, route and workload drift, completed actions, and the top focus items for the coming week.' },
    { id: 'savings-report',        label: 'Waste Reduction Report',                 group: 'Reporting & Executive',  prompt: 'Produce a waste-reduction report summarizing savings or avoided cost from rightsizing, cleanup, quota correction, storage hygiene, and route or operator rationalization.' },
    { id: 'unit-economics',        label: 'Unit Economics by Platform Pattern',     group: 'Reporting & Executive',  prompt: 'Estimate unit economics for the OpenShift estate by platform pattern, namespace density, and workload footprint. Compare efficiency across ROSA, ARO, IPI, UPI, and IBM Z scenarios where relevant.' },
    { id: 'team-scorecard',        label: 'Team Efficiency Scorecard',              group: 'Reporting & Executive',  prompt: 'Generate a team-by-team OpenShift efficiency scorecard covering ownership hygiene, quota alignment, storage sprawl, route sprawl, and rightsizing adoption. Rank teams and highlight the best practices of the most efficient ones.' },
    { id: 'forecast-scenario',     label: 'What-If Capacity Scenarios',             group: 'Reporting & Executive',  prompt: 'Model three OpenShift scenarios for the next planning window: baseline, optimized, and growth. For each scenario, estimate worker capacity, storage demand, route footprint, and likely cost trajectory, then recommend the best levers to pull first.' },
  ];

  const OP_GROUPS = [...new Set(FINOPS_OPERATIONS.map(o => o.group))];

  /* ── API layer ──────────────────────────────────────────────── */

  /** Base URL for the FastAPI backend (same origin as the page). */
  const API_BASE = window.location.origin;
  const llmRuntime = window.OpenShiftSreLlmRuntime || window.AwsSreLlmRuntime || {};

  /**
   * Send a prompt to the `/chat` endpoint with optional credential overrides.
   * @param {string} prompt - The user/operation prompt.
   * @param {Object} [overrides] - Optional connection settings (ollamaBaseUrl, modelName, clusterScope, etc.).
   * @returns {Promise<Object>} Parsed JSON response with `answer`, `steps`, `run_id`.
   */
  const apiChat = async (prompt, overrides = {}) => {
    const body = { prompt };
    const runtime = {
      ...(llmRuntime.buildLlmRuntime?.({
        provider: overrides.provider,
        ollamaBaseUrl: overrides.ollamaBaseUrl,
        modelName: overrides.modelName,
        externalModelName: overrides.externalModelName,
        externalBaseUrl: overrides.externalBaseUrl,
        externalApiKey: overrides.externalApiKey,
        externalApiVersion: overrides.externalApiVersion,
        externalOrganization: overrides.externalOrganization,
      }, overrides.providerCatalog) || {})
    };
    if (overrides.clusterScope) runtime.cluster_scope = overrides.clusterScope;
    if (overrides.kubeContext) runtime.kube_context_name = overrides.kubeContext;
    if (overrides.openshiftApiUrl) runtime.openshift_api_url = overrides.openshiftApiUrl;
    if (overrides.openshiftToken) runtime.openshift_token = overrides.openshiftToken;
    if (overrides.openshiftNamespace) runtime.openshift_namespace = overrides.openshiftNamespace;
    if (overrides.verifySsl !== undefined) runtime.verify_ssl = overrides.verifySsl;
    if (Object.keys(runtime).length > 0) body.runtime = runtime;
    const res = await fetch(`${API_BASE}/chat`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
    let payload = null;
    try {
      payload = await res.json();
    } catch {
      payload = null;
    }
    if (!res.ok) {
      const detail = payload?.detail || payload?.message;
      if (detail) throw new Error(detail);
      throw new Error(`Request failed with status ${res.status}`);
    }
    return payload || {};
  };

  const apiFetchModels = async (ollamaBaseUrl = '') => {
    const params = new URLSearchParams();
    if (ollamaBaseUrl) params.set('ollama_base_url', ollamaBaseUrl);
    const res = await fetch(`${API_BASE}/ollama/models${params.toString() ? `?${params}` : ''}`);
    if (!res.ok) throw new Error(`Model list request failed ${res.status}`);
    return res.json();
  };

  const apiFetchProviderCatalog = async () => llmRuntime.fetchProviderCatalog?.() || { configured_provider: 'ollama', configured_model_name: '', providers: [{ id: 'ollama', label: 'Local Ollama', default_model: '', default_base_url: 'http://localhost:11434', supports_catalog_refresh: true, suggested_models: ['gemma4:26b'] }] };

  /** Fetch all items from the FinOps approval queue. @returns {Promise<{enabled: boolean, items: Array}>} */
  const apiFetchQueue = async () => {
    const res = await fetch(`${API_BASE}/finops/queue`);
    if (!res.ok) throw new Error(`Queue fetch failed ${res.status}`);
    return res.json();
  };

  /** Create a new item in the FinOps approval queue. @param {Object} item - Queue item fields. @returns {Promise<Object>} Created item. */
  const apiCreateQueueItem = async (item) => {
    const payload = {
      opportunity_key: item.opportunity_key,
      title: item.title,
      category: item.category,
      estimated_monthly_savings: item.estimated_monthly_savings ?? item.estimated_savings ?? 0,
      unit: item.unit || 'USD',
      risk: item.risk || 'unknown',
      confidence: item.confidence || 'unknown',
      action: item.action || item.action_summary || '',
      basis: item.basis || '',
      evidence: item.evidence || '',
      execution_plan: item.execution_plan || '',
      run_id: item.run_id ?? null,
      auto_approve: Boolean(item.auto_approve),
      execution_mode: item.execution_mode || 'future-safe-execution-plan-only'
    };
    const res = await fetch(`${API_BASE}/finops/queue`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
    if (!res.ok) throw new Error(`Queue create failed ${res.status}`);
    return res.json();
  };

  /** Update the execution stage of a queue item. @param {number} id - Queue item ID. @param {string} stage - New stage name. */
  const apiUpdateQueueStage = async (id, stage) => {
    const res = await fetch(`${API_BASE}/finops/queue/${id}`, { method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ execution_stage: stage }) });
    if (!res.ok) throw new Error(`Stage update failed ${res.status}`);
    return res.json();
  };

  /** Remove a queue item by ID. @param {number} id - Queue item ID. */
  const apiDeleteQueueItem = async (id) => {
    const res = await fetch(`${API_BASE}/finops/queue/${id}`, { method: 'DELETE' });
    if (!res.ok) throw new Error(`Queue delete failed ${res.status}`);
  };

  /* ── FinOps workflow builder (mirrors agent-console.js logic) ── */

  /**
   * Set of OpenShift FinOps tool names the agent can invoke.
   * Used by `buildWorkflow()` to filter relevant tool-call steps.
   * @type {Set<string>}
   */
  const FINOPS_TOOL_NAMES = new Set([
    'list_cost_and_usage_summary', 'list_cost_by_service', 'list_cost_by_tag',
    'get_cost_forecast', 'list_savings_plans_coverage', 'list_rightsizing_recommendations',
    'list_cost_anomalies',
  ]);

  /**
   * Build a structured FinOps workflow from the agent's tool-call results.
   *
   * Processes each tool result (cost summary, forecast, rightsizing, Savings Plans,
   * cost-by-service, cost-by-tag) into categorised opportunities with savings
   * estimates, risk levels, and execution plans.
   *
   * @param {Array} items  - Array of step objects from the agent response, each
   *                         containing `tool_call` and `tool_result`.
   * @param {string|null} [runId=null] - Optional run ID for correlation.
   * @returns {Object|null} Workflow object with `opportunities`, `categorySummaries`,
   *                        `overview`, and `totalEstimatedMonthlySavings`, or null
   *                        if no FinOps tool steps are found.
   */
  const buildWorkflow = (items, runId = null) => {
    const toolSteps = (Array.isArray(items) ? items : []).filter(i => FINOPS_TOOL_NAMES.has(i.tool_call?.name));
    if (toolSteps.length === 0) return null;

    const opps = [];
    const overview = { totalObservedSpend: null, forecastTotal: null, forecastUnit: 'USD', savingsPlansCoverage: null, rightsizingSavings: 0, estimateNote: 'Estimated savings include direct recommendations and conservative heuristics.' };

    const upsert = (candidate) => {
      const idx = opps.findIndex(o => o.key === candidate.key);
      if (idx >= 0) { if (safeNum(candidate.estimatedMonthlySavings) > safeNum(opps[idx].estimatedMonthlySavings)) opps[idx] = candidate; }
      else opps.push(candidate);
    };

    for (const step of toolSteps) {
      const tn = step.tool_call?.name;
      const r = step.tool_result || {};

      if (tn === 'list_cost_and_usage_summary' && r.total_unblended_cost) overview.totalObservedSpend = safeNum(r.total_unblended_cost.amount);
      if (tn === 'get_cost_forecast' && r.forecast_total) { overview.forecastTotal = safeNum(r.forecast_total.amount); overview.forecastUnit = r.forecast_total.unit || 'USD'; }

      if (tn === 'list_rightsizing_recommendations') {
        const recs = Array.isArray(r.recommendations) ? r.recommendations : [];
        overview.rightsizingSavings = safeNum(r.estimated_total_monthly_savings?.amount);
        for (const rec of recs) {
          const sv = safeNum(rec.estimated_monthly_savings);
          const rid = rec.resource_id || rec.instance_name || 'resource';
          upsert({ key: `compute-rightsize-${slug(rid)}`, title: `Rightsize ${rid}`, category: 'compute', estimatedMonthlySavings: sv, unit: rec.currency_code || 'USD', basis: 'Direct rightsizing recommendation', confidence: 'high', risk: 'medium', action: `Validate workload for ${rid} and apply recommended instance change.`, evidence: `${rec.current_instance_type || 'Current'} → ${rec.recommended_instance_type || 'target'} saving ${fmtCur(sv)}.`, executionPlan: 'Confirm approval, compare utilization, schedule resize, verify rollback.' });
        }
      }

      if (tn === 'list_savings_plans_coverage') {
        const cov = safeNum(r.average_coverage_percentage);
        overview.savingsPlansCoverage = cov;
        const rows = Array.isArray(r.coverage_by_time) ? r.coverage_by_time : [];
        const uncov = rows.length ? rows.reduce((s, ro) => s + safeNum(ro.on_demand_cost?.amount), 0) / rows.length : 0;
        if (cov < 85 || uncov > 0) {
          upsert({ key: 'commitment-savings-plans-gap', title: `Reduce uncovered baseline spend (${fmtNum(cov)}%)`, category: 'commitment', estimatedMonthlySavings: uncov, unit: rows[0]?.on_demand_cost?.unit || 'USD', basis: 'Baseline efficiency gap', confidence: 'medium', risk: 'medium', action: 'Review steady-state platform usage and reduce uncovered waste or rebalance baseline capacity.', evidence: `Coverage ${fmtNum(cov)}%, uncovered ~${fmtCur(uncov)}.`, executionPlan: 'Validate usage, simulate scenarios, align with platform and finance owners.' });
        }
      }

      if (tn === 'list_cost_by_service') {
        for (const row of (Array.isArray(r.service_costs) ? r.service_costs.slice(0, 10) : [])) {
          const amt = safeNum(row.unblended_cost?.amount), unit = row.unblended_cost?.unit || 'USD', cat = svcCat(row.service);
          if (!cat) continue;
          const rateMap = { storage: 0.08, compute: 0.1, database: 0.12, serverless: 0.06, network: 0.07 };
          const rate = rateMap[cat] || 0.08, pot = Math.round(amt * rate * 100) / 100;
          upsert({ key: `${cat}-service-${slug(row.service)}`, title: `${row.service} optimization`, category: cat, estimatedMonthlySavings: pot, unit, basis: `Heuristic ${fmtNum(rate * 100)}% potential`, confidence: 'medium', risk: cat === 'compute' ? 'medium' : 'low', action: `Review ${row.service} utilization and reduce avoidable spend.`, evidence: `${row.service} cost: ${fmtCur(amt, unit)}.`, executionPlan: 'Capture config, validate usage, stage change, verify rollback.' });
        }
      }

      if (tn === 'list_cost_by_tag') {
        const tags = Array.isArray(r.tag_costs) ? r.tag_costs : [];
        const unalloc = tags.find(ro => ['<unallocated>', 'unallocated', 'unknown', 'untagged'].includes(String(ro.tag_value || '').toLowerCase()));
        if (unalloc) {
          const amt = safeNum(unalloc.unblended_cost?.amount), unit = unalloc.unblended_cost?.unit || 'USD';
          upsert({ key: 'idle-untagged-spend', title: 'Review unallocated spend', category: 'idle', estimatedMonthlySavings: Math.round(amt * 0.15 * 100) / 100, unit, basis: 'Heuristic from unallocated spend', confidence: 'medium', risk: 'low', action: 'Identify owners, inspect low-value resources, schedule cleanup.', evidence: `${fmtCur(amt, unit)} grouped under ${unalloc.tag_value}.`, executionPlan: 'Map owners, confirm criticality, queue cleanup, execute after approval.' });
          upsert({ key: 'chargeback-unallocated', title: 'Chargeback gap – unallocated spend', category: 'chargeback', estimatedMonthlySavings: 0, unit, basis: 'Untagged spend cannot be charged back', confidence: 'high', risk: 'low', action: 'Tag unallocated resources and assign to cost centers for accurate chargeback.', evidence: `${fmtCur(amt, unit)} unallocated across ${tags.length} tag values.`, executionPlan: 'Audit tags, enforce tagging policy, re-run chargeback report.' });
        }
        /* Create chargeback entries for each allocated tag value */
        const allocated = tags.filter(ro => !['<unallocated>', 'unallocated', 'unknown', 'untagged'].includes(String(ro.tag_value || '').toLowerCase()));
        for (const row of allocated.slice(0, 8)) {
          const amt = safeNum(row.unblended_cost?.amount), unit = row.unblended_cost?.unit || 'USD';
          if (amt > 0) {
            upsert({ key: `chargeback-tag-${slug(row.tag_value)}`, title: `Chargeback: ${row.tag_value}`, category: 'chargeback', estimatedMonthlySavings: 0, unit, basis: 'Tag-based cost allocation', confidence: 'high', risk: 'low', action: `Charge ${fmtCur(amt, unit)} to ${row.tag_value} cost center.`, evidence: `${row.tag_value}: ${fmtCur(amt, unit)} over the period.`, executionPlan: 'Validate allocation, generate invoice, distribute to finance.' });
          }
        }
      }
    }

    const catOrder = ['compute', 'storage', 'commitment', 'idle', 'chargeback', 'network', 'database', 'serverless'];
    const catLabels = { compute: 'Compute', storage: 'Storage', commitment: 'Commitment', idle: 'Idle / Unused', chargeback: 'Chargeback', network: 'Network', database: 'Database', serverless: 'Serverless' };
    const catSummaries = catOrder.map(cat => {
      const rows = opps.filter(o => o.category === cat);
      return { category: cat, label: catLabels[cat] || cat.charAt(0).toUpperCase() + cat.slice(1), count: rows.length, estimatedMonthlySavings: Math.round(rows.reduce((s, o) => s + safeNum(o.estimatedMonthlySavings), 0) * 100) / 100, unit: rows[0]?.unit || 'USD' };
    }).filter(c => c.count > 0 || ['compute', 'storage', 'commitment', 'idle'].includes(c.category));

    return { runId, opportunities: opps.sort((a, b) => safeNum(b.estimatedMonthlySavings) - safeNum(a.estimatedMonthlySavings)), categorySummaries: catSummaries, overview, totalEstimatedMonthlySavings: opps.reduce((s, o) => s + safeNum(o.estimatedMonthlySavings), 0) };
  };

  /* ── React components ───────────────────────────────────────── */

  /**
   * Toast notification that auto-dismisses after 5 seconds.
   * @param {Object} props
   * @param {string} props.message   - Notification text.
   * @param {'ok'|'error'|'info'} props.kind - Colour variant.
   * @param {Function} props.onDismiss - Called on auto/manual dismiss.
   */
  function Toast({ message, kind, onDismiss }) {
    useEffect(() => { const t = setTimeout(onDismiss, 5000); return () => clearTimeout(t); }, [message]);
    if (!message) return null;
    return h('div', { className: `finops-toast finops-toast--${kind || 'info'}`, onClick: onDismiss }, message);
  }

  /**
   * Collapsible settings panel for connection credentials (Ollama URL,
   * model name, Cluster scope/profile/keys, SSL toggle).
   * @param {Object} props
   * @param {Object} props.settings - Current settings state object.
   * @param {Function} props.onChange - Called with updated settings on any change.
   */
  function SettingsPanel({ settings, onChange, modelCatalog, modelsLoading, onRefreshModels, providerCatalog }) {
    const set = (k) => (e) => onChange({ ...settings, [k]: e.target.type === 'checkbox' ? e.target.checked : e.target.value });
    const currentProviderId = llmRuntime.normalizeProviderId?.(providerCatalog, settings.provider) || 'ollama';
    const provider = llmRuntime.getProvider?.(providerCatalog, currentProviderId) || providerCatalog?.providers?.[0] || { id: 'ollama', label: 'Local Ollama', default_model: '', default_base_url: 'http://localhost:11434' };
    const useExternal = currentProviderId !== 'ollama';
    const catalogModels = Array.isArray(modelCatalog?.models) ? modelCatalog.models : [];
    const defaultModel = settings.modelName || modelCatalog?.selected_model_name || modelCatalog?.preferred_model_name || modelCatalog?.active_model_name || modelCatalog?.configured_model_name || provider.default_model || '';
    const optionMap = new Map(catalogModels.map((model) => {
      const suffix = [model.loaded ? 'loaded' : '', model.parameter_size || ''].filter(Boolean).join(' · ');
      return [model.name, suffix ? `${model.name} · ${suffix}` : model.name];
    }));
    if (!optionMap.has(defaultModel)) {
      optionMap.set(defaultModel, defaultModel);
    }
    return h('details', { className: 'finops-settings' },
      h('summary', null, 'Connection & credentials'),
      h('div', { className: 'finops-settings__grid' },
        h('label', null,
          'LLM provider',
          h('select', { className: 'agent-console__input', value: currentProviderId, onChange: set('provider') },
            (providerCatalog?.providers || []).map((item) => h('option', { key: item.id, value: item.id }, item.label))
          )
        ),
        useExternal ? h(Fragment, null,
          h('label', null, 'External model', h('input', { className: 'agent-console__input', type: 'text', placeholder: provider.default_model || 'gpt-4.1-mini', value: settings.externalModelName, onChange: set('externalModelName') })),
          h('label', null, 'Provider base URL', h('input', { className: 'agent-console__input', type: 'url', placeholder: provider.default_base_url || 'https://api.openai.com/v1', value: settings.externalBaseUrl, onChange: set('externalBaseUrl') })),
          h('label', null, 'Provider API key', h('input', { className: 'agent-console__input', type: 'password', placeholder: 'Required for external providers', value: settings.externalApiKey, onChange: set('externalApiKey') })),
          h('label', null, 'Organization / tenant', h('input', { className: 'agent-console__input', type: 'text', placeholder: 'Optional provider org or tenant hint', value: settings.externalOrganization, onChange: set('externalOrganization') })),
          h('label', null, 'API version', h('input', { className: 'agent-console__input', type: 'text', placeholder: provider.default_api_version || 'Optional API version', value: settings.externalApiVersion, onChange: set('externalApiVersion') }))
        ) : h(Fragment, null,
          h('label', null, 'Ollama URL', h('input', { className: 'agent-console__input', type: 'url', placeholder: 'http://host.containers.internal:11434', value: settings.ollamaBaseUrl, onChange: set('ollamaBaseUrl') })),
          h('label', null,
            'Model',
            h('div', { className: 'finops-settings__model-picker' },
              h('select', { className: 'agent-console__input', value: defaultModel, onChange: set('modelName'), disabled: modelsLoading && optionMap.size === 0 },
                Array.from(optionMap.entries()).map(([value, label]) => h('option', { key: value, value }, label))
              ),
              h('button', { className: 'agent-console__example', type: 'button', onClick: onRefreshModels, disabled: modelsLoading }, modelsLoading ? 'Refreshing…' : 'Refresh')
            )
          )
        ),
        h('label', null, 'Cluster Scope', h('input', { className: 'agent-console__input', type: 'text', placeholder: 'local-cluster', value: settings.clusterScope, onChange: set('clusterScope') })),
        h('label', null, 'Kube Context', h('input', { className: 'agent-console__input', type: 'text', placeholder: 'default', value: settings.kubeContext, onChange: set('kubeContext') })),
        h('label', null, 'OpenShift API URL', h('input', { className: 'agent-console__input', type: 'text', placeholder: 'https://api...', value: settings.openshiftApiUrl, onChange: set('openshiftApiUrl') })),
        h('label', null, 'OpenShift Token', h('input', { className: 'agent-console__input', type: 'password', placeholder: 'Optional', value: settings.openshiftToken, onChange: set('openshiftToken') })),
        h('label', null, 'Namespace Scope', h('input', { className: 'agent-console__input', type: 'password', placeholder: 'Optional namespace', value: settings.openshiftNamespace, onChange: set('openshiftNamespace') })),
        h('label', { className: 'agent-console__checkbox' }, h('input', { type: 'checkbox', checked: settings.verifySsl, onChange: set('verifySsl') }), h('span', null, 'Verify SSL')),
        h('p', { className: 'agent-console__meta' }, provider.description || 'Choose the local Ollama model or an external provider like OpenAI, Azure OpenAI, Anthropic, Gemini, or OpenRouter.')
      )
    );
  }

  /**
   * Dropdown selector for FinOps operations, grouped by category.
   * Renders a `<select>` with `<optgroup>` elements for each OP_GROUP.
   * @param {Object} props
   * @param {string} props.selected - Currently selected operation ID.
   * @param {Function} props.onSelect - Called with new operation ID on change.
   */
  function OperationSelector({ selected, onSelect }) {
    return h('div', { className: 'finops-op-selector' },
      h('label', { className: 'agent-console__label', htmlFor: 'finops-op' }, 'FinOps operation'),
      h('select', { id: 'finops-op', className: 'agent-console__input finops-op-select', value: selected, onChange: (e) => onSelect(e.target.value) },
        OP_GROUPS.map(g => h('optgroup', { key: g, label: g },
          FINOPS_OPERATIONS.filter(o => o.group === g).map(o =>
            h('option', { key: o.id, value: o.id }, o.label)
          )
        ))
      )
    );
  }

  /**
   * Overview stat cards and category summaries (compute, storage, commitment, idle).
   * Shows key metrics: opportunity count, estimated savings, observed spend,
   * forecast, Savings Plans coverage, and rightsizing savings.
   * @param {Object} props
   * @param {Object|null} props.workflow - Workflow object from `buildWorkflow()`.
   */
  function OverviewCards({ workflow }) {
    if (!workflow) return h('p', { className: 'agent-console__meta' }, 'Run a FinOps operation to see the workflow overview.');
    const cards = [
      { label: 'Opportunities', value: workflow.opportunities.length },
      { label: 'Est. monthly savings', value: fmtCur(workflow.totalEstimatedMonthlySavings) },
      { label: 'Observed spend', value: workflow.overview.totalObservedSpend === null ? '—' : fmtCur(workflow.overview.totalObservedSpend) },
      { label: 'Forecast', value: workflow.overview.forecastTotal === null ? '—' : fmtCur(workflow.overview.forecastTotal, workflow.overview.forecastUnit) },
      { label: 'Efficiency coverage', value: workflow.overview.savingsPlansCoverage === null ? '—' : `${fmtNum(workflow.overview.savingsPlansCoverage)}%` },
      { label: 'Rightsizing savings', value: fmtCur(workflow.overview.rightsizingSavings) },
    ];
    return h('div', { className: 'agent-console__finops-overview' },
      h('div', { className: 'agent-console__history-card-grid' }, cards.map(c =>
        h('article', { key: c.label, className: 'agent-console__history-card' },
          h('p', { className: 'agent-console__history-card-label' }, c.label),
          h('p', { className: 'agent-console__history-card-value' }, c.value)
        )
      )),
      h('div', { className: 'finops-category-list' }, workflow.categorySummaries.map(c =>
        h('article', { key: c.category, className: 'finops-category-card' },
          h('div', { className: 'finops-category-header' },
            h('h4', null, c.label),
            h('span', { className: `finops-pill ${c.count > 0 ? 'finops-pill--active' : ''}` }, `${c.count} item(s)`)
          ),
          h('p', null, `Est. savings: ${fmtCur(c.estimatedMonthlySavings, c.unit)}`)
        )
      ))
    );
  }

  /**
   * Tabular view of all opportunities with category, title, estimated
   * monthly savings, basis, and confidence level.
   * @param {Object} props
   * @param {Object|null} props.workflow - Workflow object from `buildWorkflow()`.
   */
  function SavingsTable({ workflow }) {
    if (!workflow || workflow.opportunities.length === 0) return h('p', { className: 'agent-console__meta' }, 'Savings table will appear after a FinOps run.');
    return h('section', { className: 'agent-console__table-block' },
      h('h4', null, 'Estimated savings & impact'),
      h('table', { className: 'agent-console__table agent-console__table--wide' },
        h('thead', null, h('tr', null, ['Category', 'Opportunity', 'Est. monthly savings', 'Basis', 'Confidence'].map(c => h('th', { key: c }, c)))),
        h('tbody', null, workflow.opportunities.map(o =>
          h('tr', { key: o.key },
            h('td', null, o.category),
            h('td', null, o.title),
            h('td', null, fmtCur(o.estimatedMonthlySavings, o.unit)),
            h('td', null, o.basis),
            h('td', null, o.confidence)
          )
        ))
      )
    );
  }

  /**
   * Grid of action cards for each opportunity. Each card shows badges
   * (category, risk, confidence), savings estimate, recommended action,
   * evidence, and execution plan, with a "Queue for approval" button.
   * @param {Object} props
   * @param {Object|null} props.workflow - Workflow object from `buildWorkflow()`.
   * @param {Function} props.onQueue    - Called with a single opportunity to queue.
   * @param {Function} props.onQueueAll - Called to queue all opportunities at once.
   */
  function ActionCards({ workflow, onQueue, onQueueAll }) {
    if (!workflow || workflow.opportunities.length === 0) return h('p', { className: 'agent-console__meta' }, 'Action cards will appear after a FinOps run.');
    return h('div', { className: 'agent-console__finops-actions' },
      h('div', { className: 'finops-actions-header' },
        h('div', null,
          h('h3', null, 'Recommended actions'),
          h('p', { className: 'agent-console__meta' }, 'Generated from observed FinOps signals. Queue them for safe execution after review.')
        ),
        h('button', { className: 'agent-console__button agent-console__button--secondary', onClick: onQueueAll }, 'Queue all actions')
      ),
      h('div', { className: 'agent-console__finops-action-grid' }, workflow.opportunities.map(o =>
        h('article', { key: o.key, className: 'agent-console__module-card' },
          h('div', { className: 'agent-console__module-badge-row' },
            h('span', { className: 'agent-console__history-badge' }, o.category),
            h('span', { className: `agent-console__history-badge agent-console__history-badge--${o.risk === 'low' ? 'ok' : o.risk === 'medium' ? 'warning' : 'error'}` }, `risk: ${o.risk}`),
            h('span', { className: 'agent-console__history-badge' }, `confidence: ${o.confidence}`)
          ),
          h('h4', null, o.title),
          h('p', null, h('strong', null, 'Savings: '), fmtCur(o.estimatedMonthlySavings, o.unit)),
          h('p', null, h('strong', null, 'Action: '), o.action),
          h('p', null, h('strong', null, 'Evidence: '), o.evidence),
          h('p', null, h('strong', null, 'Plan: '), o.executionPlan),
          h('button', { className: 'agent-console__example', onClick: () => onQueue(o) }, 'Queue for approval')
        )
      ))
    );
  }

  /**
   * Ordered list of safe-execution stages for approval queue items.
   * Items progress: planned → approved → precheck_passed →
   * ready_for_change_window → executed → rolled_back.
   * @type {string[]}
   */
  const STAGES = ['planned', 'approved', 'precheck_passed', 'ready_for_change_window', 'executed', 'rolled_back'];

  /**
   * Approval queue panel showing persisted queue items with stage
   * dropdowns and remove buttons. Calls the backend to update
   * stages or delete items.
   * @param {Object} props
   * @param {Object|null} props.queue     - Queue state `{enabled, items, reason}`.
   * @param {Function}    props.onRefresh - Called after any mutation to reload queue.
   */
  function ApprovalQueue({ queue, onRefresh }) {
    if (!queue || !queue.enabled) return h('p', { className: 'agent-console__meta' }, queue?.reason || 'Queue persistence is not configured.');
    const items = Array.isArray(queue.items) ? queue.items : [];
    if (items.length === 0) return h('p', { className: 'agent-console__meta' }, 'No items in the approval queue yet.');
    return h('div', { className: 'agent-console__finops-queue' },
      items.map(item => h('article', { key: item.id, className: 'agent-console__module-card' },
        h('div', { className: 'agent-console__module-badge-row' },
          h('span', { className: 'agent-console__history-badge' }, item.category || 'finops'),
          h('span', { className: 'agent-console__history-badge agent-console__history-badge--ok' }, item.execution_stage || 'planned')
        ),
        h('h4', null, item.title || item.opportunity_key),
        h('p', null, item.action || item.action_summary || ''),
        h('div', { className: 'finops-queue-controls' },
          h('select', { className: 'agent-console__input', defaultValue: item.execution_stage || 'planned', onChange: async (e) => { await apiUpdateQueueStage(item.id, e.target.value); onRefresh(); } },
            STAGES.map(s => h('option', { key: s, value: s }, s.replace(/_/g, ' ')))
          ),
          h('button', { className: 'finops-queue-delete', onClick: async () => { await apiDeleteQueueItem(item.id); onRefresh(); } }, 'Remove')
        )
      ))
    );
  }

  /**
   * Agent response viewer with the raw answer text and an expandable
   * reasoning trace showing each tool call and its result.
   * @param {Object} props
   * @param {string|null} props.response - Agent answer text (may contain newlines).
   * @param {Array}       props.steps    - Array of reasoning steps with tool_call/tool_result.
   */
  function ResponsePanel({ response, steps }) {
    if (!response) return h('p', { className: 'agent-console__meta' }, 'Run a FinOps operation to see the agent response here.');
    return h(Fragment, null,
      h('h3', null, 'Agent response'),
      h('div', { className: 'agent-console__answer', dangerouslySetInnerHTML: { __html: response.replace(/\n/g, '<br>') } }),
      steps && steps.length > 0 ? h(Fragment, null,
        h('h3', null, 'Reasoning trace'),
        h('div', { className: 'agent-console__steps' }, steps.map((s, i) =>
          h('details', { key: i, className: 'agent-console__table-block' },
            h('summary', null, `Step ${i + 1}: ${s.tool_call?.name || 'reasoning'}`),
            s.tool_call ? h('pre', { className: 'finops-step-pre' }, JSON.stringify(s.tool_result || s.tool_call, null, 2)) : h('p', null, s.text || '')
          )
        ))
      ) : null
    );
  }

  function ReportHighlights({ operation, response, workflow, queue, onExportPpt, onExportPdf, exportBusy, exportPdfBusy }) {
    const summaryBullets = summarizeReport(response, 5);
    const queueItems = Array.isArray(queue?.items) ? queue.items : [];
    const reportReady = Boolean(response);
    return h('section', { className: 'finops-report-deck', id: 'finops-exports' },
      h('div', { className: 'finops-report-deck__header' },
        h('div', null,
          h('p', { className: 'finops-report-deck__kicker' }, isExecutiveOperation(operation.id) ? 'Executive report lane' : 'Report export lane'),
          h('h3', null, 'Presentation-ready export'),
          h('p', { className: 'agent-console__meta' }, reportReady
            ? 'The current report can be turned into a PowerPoint deck with summary, KPI, recommendation, and queue slides.'
            : 'Run a FinOps report or workflow first, then export the resulting report as a PowerPoint deck.')
        ),
        h('div', { className: 'finops-report-deck__actions' },
          h('button', { className: 'agent-console__button', type: 'button', onClick: onExportPpt, disabled: exportBusy }, exportBusy ? 'Building PPT…' : 'Export as PPT'),
          h('button', { className: 'agent-console__button agent-console__button--secondary', type: 'button', onClick: onExportPdf, disabled: exportPdfBusy }, exportPdfBusy ? 'Building PDF…' : 'Export as PDF'),
          h('span', { className: `finops-pill ${reportReady ? 'finops-pill--active' : ''}` }, reportReady ? 'Report ready' : 'Waiting for report')
        )
      ),
      h('div', { className: 'finops-report-deck__grid' },
        h('article', { className: 'finops-report-card' },
          h('h4', null, 'Report focus'),
          h('p', null, operation.label),
          h('p', { className: 'agent-console__meta' }, `${operation.group} · ${isExecutiveOperation(operation.id) ? 'Board-oriented narrative' : 'Operator workflow narrative'}`)
        ),
        h('article', { className: 'finops-report-card' },
          h('h4', null, 'Savings posture'),
          h('p', null, workflow ? fmtCur(workflow.totalEstimatedMonthlySavings) : '—'),
          h('p', { className: 'agent-console__meta' }, workflow ? `${workflow.opportunities.length} opportunities captured` : 'Run the tool to populate the workflow.' )
        ),
        h('article', { className: 'finops-report-card' },
          h('h4', null, 'Queue alignment'),
          h('p', null, String(queueItems.length)),
          h('p', { className: 'agent-console__meta' }, 'Queue items can be included as a final slide in the export deck.')
        )
      ),
      h('div', { className: 'finops-report-deck__summary' },
        h('div', { className: 'finops-report-deck__column' },
          h('h4', null, 'Report highlights'),
          summaryBullets.length > 0
            ? h('ul', { className: 'finops-report-list' }, summaryBullets.map((item) => h('li', { key: item }, item)))
            : h('p', { className: 'agent-console__meta' }, 'No report highlights yet. Run an operation to populate this summary lane.')
        ),
        h('div', { className: 'finops-report-deck__column' },
          h('h4', null, 'Export deck contents'),
          h('ul', { className: 'finops-report-list' }, [
            'Title slide with operation context',
            'Executive narrative bullets',
            'Workflow KPI and savings slide',
            'Priority recommendations',
            'Approval queue handoff',
            'PDF briefing export for offline sharing'
          ].map((item) => h('li', { key: item }, item)))
        )
      )
    );
  }

  /* ── Main app ───────────────────────────────────────────────── */

  /**
   * Root component for the FinOps Console.
   *
   * Layout: two-column grid (controls left, results right).
   *   - Left panel: operation selector dropdown, settings, prompt textarea,
   *     run button, auto-approve toggle.
   *   - Right panel: overview cards, savings table, action cards,
   *     approval queue, and agent response viewer.
   *
   * State: selectedOp, settings, customPrompt, autoApprove, running,
   *        toast, response, steps, workflow, queue.
   */
  function FinOpsApp() {
    const [selectedOp, setSelectedOp] = useState('full-optimizer');
    const [settings, setSettings] = useState({ provider: 'ollama', ollamaBaseUrl: '', modelName: '', externalModelName: '', externalBaseUrl: '', externalApiKey: '', externalApiVersion: '', externalOrganization: '', clusterScope: '', kubeContext: '', openshiftApiUrl: '', openshiftToken: '', openshiftNamespace: '', verifySsl: true });
    const [modelCatalog, setModelCatalog] = useState({ configured_model_name: '', models: [] });
    const [providerCatalog, setProviderCatalog] = useState(llmRuntime.fallbackCatalog || { configured_provider: 'ollama', configured_model_name: '', providers: [{ id: 'ollama', label: 'Local Ollama', default_model: '', default_base_url: 'http://localhost:11434', supports_catalog_refresh: true, suggested_models: ['gemma4:26b'] }] });
    const [modelsLoading, setModelsLoading] = useState(false);
    const [customPrompt, setCustomPrompt] = useState('');
    const [autoApprove, setAutoApprove] = useState(false);
    const [running, setRunning] = useState(false);
    const [toast, setToast] = useState({ message: '', kind: '' });
    const [response, setResponse] = useState(null);
    const [steps, setSteps] = useState([]);
    const [workflow, setWorkflow] = useState(null);
    const [queue, setQueue] = useState(null);
    const [exportingPpt, setExportingPpt] = useState(false);
    const [exportingPdf, setExportingPdf] = useState(false);

    const showToast = (message, kind = 'info') => setToast({ message, kind });
    const operation = FINOPS_OPERATIONS.find((item) => item.id === selectedOp) || FINOPS_OPERATIONS[0];

    const refreshQueue = useCallback(async () => {
      try { setQueue(await apiFetchQueue()); }
      catch { /* queue not available */ }
    }, []);

    useEffect(() => {
      apiFetchProviderCatalog().then((payload) => {
        setProviderCatalog(payload);
        setSettings((current) => ({
          ...current,
          provider: current.provider || payload.configured_provider || 'ollama',
          externalModelName: current.externalModelName || payload.configured_model_name || '',
        }));
      }).catch(() => undefined);
    }, []);

    const refreshModels = useCallback(async (baseUrl = settings.ollamaBaseUrl) => {
      if ((llmRuntime.normalizeProviderId?.(providerCatalog, settings.provider) || 'ollama') !== 'ollama') {
        setModelsLoading(false);
        return;
      }
      setModelsLoading(true);
      try {
        const payload = await apiFetchModels(baseUrl || '');
        setModelCatalog(payload);
        setSettings((current) => {
          const availableNames = Array.isArray(payload.models) ? payload.models.map((model) => model.name) : [];
          if (current.modelName && availableNames.includes(current.modelName)) {
            return current;
          }
          return {
            ...current,
            modelName: current.modelName || payload.selected_model_name || payload.preferred_model_name || payload.active_model_name || payload.configured_model_name || availableNames[0] || '',
          };
        });
      } catch (error) {
        showToast(error instanceof Error ? error.message : 'Unable to load model options.', 'error');
      } finally {
        setModelsLoading(false);
      }
    }, [providerCatalog, settings.ollamaBaseUrl, settings.provider]);

    useEffect(() => { refreshQueue(); }, [refreshQueue]);
    useEffect(() => {
      if ((llmRuntime.normalizeProviderId?.(providerCatalog, settings.provider) || 'ollama') === 'ollama') {
        refreshModels(settings.ollamaBaseUrl);
      }
    }, [providerCatalog, refreshModels, settings.ollamaBaseUrl, settings.provider]);

    useEffect(() => {
      const provider = llmRuntime.getProvider?.(providerCatalog, settings.provider) || providerCatalog.providers?.[0];
      if (!provider || provider.id === 'ollama') {
        return;
      }
      setSettings((current) => ({
        ...current,
        externalModelName: current.externalModelName || provider.default_model || '',
        externalBaseUrl: current.externalBaseUrl || provider.default_base_url || '',
        externalApiVersion: current.externalApiVersion || provider.default_api_version || '',
      }));
    }, [providerCatalog, settings.provider]);

    /* Update prompt when operation changes */
    useEffect(() => {
      const op = FINOPS_OPERATIONS.find(o => o.id === selectedOp);
      if (op) setCustomPrompt(op.prompt);
    }, [selectedOp]);

    const runOperation = async () => {
      if (!customPrompt.trim()) { showToast('Enter a prompt or select an operation.', 'error'); return; }
      setRunning(true);
      showToast('Running FinOps operation...', 'info');
      try {
        const data = await apiChat(customPrompt, { ...settings, providerCatalog });
        setResponse(data.answer || data.response || JSON.stringify(data));
        const items = Array.isArray(data.steps) ? data.steps : [];
        setSteps(items);
        const wf = buildWorkflow(items, data.run_id || null);
        setWorkflow(wf);
        await refreshQueue();
        showToast(wf ? `${wf.opportunities.length} opportunities found.` : 'Operation completed.', 'ok');
      } catch (err) {
        showToast(err.message || 'Operation failed.', 'error');
      } finally {
        setRunning(false);
      }
    };

    const queueItem = async (opportunity) => {
      try {
        const currentQ = await apiFetchQueue();
        if (Array.isArray(currentQ.items) && currentQ.items.some(i => i.opportunity_key === opportunity.key)) {
          showToast(`${opportunity.title} already in queue.`, 'info');
          await refreshQueue(); return;
        }
        await apiCreateQueueItem({ opportunity_key: opportunity.key, title: opportunity.title, category: opportunity.category, action: opportunity.action, estimated_monthly_savings: opportunity.estimatedMonthlySavings, unit: opportunity.unit, risk: opportunity.risk, confidence: opportunity.confidence, basis: opportunity.basis, evidence: opportunity.evidence, execution_plan: opportunity.executionPlan, auto_approve: autoApprove });
        await refreshQueue();
        showToast(autoApprove ? `${opportunity.title} auto-approved.` : `${opportunity.title} queued.`, 'ok');
      } catch (err) { showToast(err.message, 'error'); }
    };

    const queueAll = async () => {
      if (!workflow?.opportunities?.length) return;
      try {
        const currentQ = await apiFetchQueue();
        const existing = new Set((currentQ.items || []).map(i => i.opportunity_key));
        let added = 0;
        for (const o of workflow.opportunities) {
          if (existing.has(o.key)) continue;
          await apiCreateQueueItem({ opportunity_key: o.key, title: o.title, category: o.category, action: o.action, estimated_monthly_savings: o.estimatedMonthlySavings, unit: o.unit, risk: o.risk, confidence: o.confidence, basis: o.basis, evidence: o.evidence, execution_plan: o.executionPlan, auto_approve: autoApprove });
          existing.add(o.key); added++;
        }
        await refreshQueue();
        showToast(added > 0 ? `${added} action(s) queued.` : 'All actions already queued.', 'ok');
      } catch (err) { showToast(err.message, 'error'); }
    };

    const exportPpt = async () => {
      if (!response) {
        showToast('Run a FinOps report before exporting PowerPoint.', 'error');
        return;
      }
      setExportingPpt(true);
      showToast('Preparing PowerPoint export…', 'info');
      try {
        await buildPptDeck({ operation, response, workflow, queue, generatedAt: new Date() });
        showToast('PowerPoint export downloaded.', 'ok');
      } catch (error) {
        showToast(error instanceof Error ? error.message : 'Unable to export PowerPoint.', 'error');
      } finally {
        setExportingPpt(false);
      }
    };

    const exportPdf = async () => {
      if (!response) {
        showToast('Run a FinOps report before exporting PDF.', 'error');
        return;
      }
      setExportingPdf(true);
      showToast('Preparing PDF export…', 'info');
      try {
        await buildPdfReport({ operation, response, workflow, queue, generatedAt: new Date() });
        showToast('PDF export downloaded.', 'ok');
      } catch (error) {
        showToast(error instanceof Error ? error.message : 'Unable to export PDF.', 'error');
      } finally {
        setExportingPdf(false);
      }
    };

    return h('div', { className: 'agent-console' },
      h(Toast, { message: toast.message, kind: toast.kind, onDismiss: () => setToast({ message: '', kind: '' }) }),

      h('section', { className: 'finops-workspace-hero agent-console__panel agent-console__panel--full' },
        h('div', { className: 'finops-workspace-hero__copy' },
          h('p', { className: 'finops-workspace-hero__kicker' }, 'FinOps command deck'),
          h('h2', null, 'Generate, review, queue, and present FinOps outcomes from one workspace'),
          h('p', { className: 'agent-console__meta' }, 'The workspace now supports a more presentation-friendly report lane. Once a report is available, you can export it as a PowerPoint deck without leaving the tool.')
        ),
        h('div', { className: 'finops-workspace-hero__stats' },
          h('article', { className: 'finops-workspace-hero__stat' },
            h('span', null, 'Current mode'),
            h('strong', null, isExecutiveOperation(operation.id) ? 'Executive reporting' : 'Optimization workflow')
          ),
          h('article', { className: 'finops-workspace-hero__stat' },
            h('span', null, 'Workflow opportunities'),
            h('strong', null, workflow?.opportunities?.length ?? 0)
          ),
          h('article', { className: 'finops-workspace-hero__stat' },
            h('span', null, 'Queue items'),
            h('strong', null, queue?.items?.length ?? 0)
          )
        )
      ),

      /* Left column – controls */
        h('section', { className: 'agent-console__panel finops-panel finops-panel--launcher', id: 'finops-launcher' },
          h('h2', null, 'Run FinOps operation'),
          h('section', { className: 'agent-console__module-section' },
            h('div', { className: 'agent-console__module-header' },
              h('div', null,
                h('h3', null, 'FinOps operations'),
                h('p', { className: 'agent-console__meta' }, 'Select a FinOps operation from the dropdown to populate the prompt, or enter a custom prompt.')
              )
            ),
            h(OperationSelector, { selected: selectedOp, onSelect: setSelectedOp })
          ),
          h(SettingsPanel, { settings, onChange: setSettings, modelCatalog, modelsLoading, providerCatalog, onRefreshModels: () => refreshModels(settings.ollamaBaseUrl) }),
          h('label', { className: 'agent-console__label', htmlFor: 'finops-prompt' }, 'Prompt'),
          h('textarea', { id: 'finops-prompt', className: 'agent-console__textarea', value: customPrompt, onChange: (e) => setCustomPrompt(e.target.value), rows: 6, onKeyDown: (e) => { if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') runOperation(); } }),
          h('div', { className: 'agent-console__actions' },
            h('button', { className: 'agent-console__button', onClick: runOperation, disabled: running }, running ? 'Running...' : 'Run FinOps operation'),
            h('label', { className: 'agent-console__checkbox' },
              h('input', { type: 'checkbox', checked: autoApprove, onChange: (e) => setAutoApprove(e.target.checked) }),
              h('span', null, 'Auto-approve queued actions')
            )
          ),
          h('p', { className: 'agent-console__meta' }, 'Tip: Ctrl/Cmd + Enter to submit. Select an operation from the dropdown to populate the prompt.'),
          h('div', { className: 'agent-console__status', 'data-agent-status': true })
        ),

        /* Right column – results */
        h('section', { className: 'agent-console__panel finops-panel finops-panel--results', id: 'finops-results' },
          h('h2', null, 'FinOps workflow'),
          h(OverviewCards, { workflow }),
          h(ReportHighlights, { operation, response, workflow, queue, onExportPpt: exportPpt, onExportPdf: exportPdf, exportBusy: exportingPpt, exportPdfBusy: exportingPdf }),
          h(SavingsTable, { workflow }),
          h(ActionCards, { workflow, onQueue: queueItem, onQueueAll: queueAll }),
          h('div', { id: 'finops-queue' },
            h('h3', null, 'Approval queue'),
            h('p', { className: 'agent-console__meta' }, 'Queue recommendations for controlled execution through safe planning stages.'),
            h(ApprovalQueue, { queue, onRefresh: refreshQueue })
          ),
          h(ResponsePanel, { response, steps })
        )
    );
  }

  /* ── Mount ──────────────────────────────────────────────────── */

  /** Mount the React app into #finops-root if the element exists. */
  const rootEl = document.getElementById('finops-root');
  if (rootEl) {
    createRoot(rootEl).render(h(FinOpsApp));
  }
})();
