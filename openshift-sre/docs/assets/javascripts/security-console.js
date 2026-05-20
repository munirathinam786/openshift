(() => {
  'use strict';

  const { createElement: h, useState, useMemo, useEffect, useCallback, Fragment } = React;
  const { createRoot } = ReactDOM;

  const themeStorageKey = 'openshift-sre-shell-theme';
  const API_BASE = window.location.origin;
  const llmRuntime = window.AwsSreLlmRuntime || {};

  const featureLabels = {
    list_cluster_infrastructure: 'Cluster infrastructure and platform pattern',
    list_cluster_version: 'Cluster version posture',
    list_cluster_operators: 'Cluster operator health',
    list_acm_multicluster_hubs: 'ACM MultiClusterHub health',
    list_acm_managed_clusters: 'ACM managed cluster fleet',
    list_acm_policies: 'ACM governance policies',
    list_acs_central_services: 'ACS central services',
    list_acs_secured_clusters: 'ACS secured-cluster coverage',
    list_security_context_constraints: 'SecurityContextConstraints posture',
    list_network_policies: 'NetworkPolicy coverage',
    list_resource_quotas: 'ResourceQuota posture',
    list_operator_subscriptions: 'Operator subscription health',
    list_cluster_service_versions: 'ClusterServiceVersion posture',
    list_workload_health: 'Workload health posture',
    list_routes: 'Route exposure posture',
    list_ingresses: 'Ingress exposure posture',
    list_services: 'Service exposure posture',
    list_persistent_storage: 'Persistent storage posture',
    list_storage_classes: 'StorageClass posture',
    list_machine_config_pools: 'MachineConfigPool posture',
    list_machine_sets: 'MachineSet posture',
    list_nodes: 'Node inventory',
    list_node_pressure: 'Node pressure and readiness',
    list_gitops_argocds: 'OpenShift GitOps / Argo CD control-plane posture',
    list_gitops_applications: 'Argo CD application sync posture',
    list_tekton_configs: 'OpenShift Pipelines / Tekton configuration posture',
    list_tekton_pipeline_runs: 'Tekton PipelineRun delivery posture',
    list_cluster_logging: 'Cluster Logging posture',
    list_oadp_resources: 'OADP / Velero backup posture',
    list_oauth_configuration: 'OAuth / LDAP identity-provider posture',
    run_read_only_oc_cli: 'Read-only oc validation'
  };

  const auditProfiles = {
    sox: {
      label: 'SOX evidence and control readiness',
      narrative: 'Focus on OpenShift controls that support change traceability, operator governance, namespace guardrails, and platform evidence collection for regulated environments.',
      features: [
        'list_cluster_infrastructure',
        'list_cluster_version',
        'list_cluster_operators',
        'list_security_context_constraints',
        'list_network_policies',
        'list_resource_quotas',
        'list_operator_subscriptions',
        'list_cluster_service_versions'
      ]
    },
    cis: {
      label: 'CIS-style cluster hardening review',
      narrative: 'Focus on baseline platform hardening, network segmentation, namespace guardrails, operator health, and control-plane posture.',
      features: [
        'list_cluster_infrastructure',
        'list_cluster_version',
        'list_cluster_operators',
        'list_security_context_constraints',
        'list_network_policies',
        'list_nodes',
        'list_node_pressure'
      ]
    },
    pci: {
      label: 'PCI-oriented platform posture review',
      narrative: 'Emphasize workload exposure, namespace isolation, operator health, and storage posture for regulated application paths.',
      features: [
        'list_cluster_infrastructure',
        'list_routes',
        'list_ingresses',
        'list_services',
        'list_network_policies',
        'list_persistent_storage',
        'list_storage_classes',
        'list_workload_health'
      ]
    },
    hipaa: {
      label: 'HIPAA safeguard and evidence readiness',
      narrative: 'Focus on workload isolation, storage posture, operator stability, and evidence needed to support security safeguard reviews.',
      features: [
        'list_cluster_infrastructure',
        'list_cluster_operators',
        'list_security_context_constraints',
        'list_network_policies',
        'list_resource_quotas',
        'list_persistent_storage',
        'list_storage_classes',
        'list_workload_health'
      ]
    },
    soc2: {
      label: 'SOC 2 security and change controls',
      narrative: 'Review platform operator health, change-sensitive cluster posture, and namespace guardrails that support SOC 2 narratives.',
      features: [
        'list_cluster_infrastructure',
        'list_cluster_version',
        'list_cluster_operators',
        'list_operator_subscriptions',
        'list_cluster_service_versions',
        'list_security_context_constraints',
        'list_network_policies'
      ]
    },
    iso27001: {
      label: 'ISO 27001 platform control mapping',
      narrative: 'Focus on governance, workload exposure, security boundaries, and operator lifecycle posture across the selected cluster domains.',
      features: [
        'list_cluster_infrastructure',
        'list_cluster_operators',
        'list_routes',
        'list_ingresses',
        'list_security_context_constraints',
        'list_network_policies',
        'list_operator_subscriptions'
      ]
    },
    nist: {
      label: 'NIST CSF operational review',
      narrative: 'Frame the review around identify, protect, detect, respond, and recover themes using OpenShift security posture and operator health signals.',
      features: [
        'list_cluster_infrastructure',
        'list_cluster_operators',
        'list_node_pressure',
        'list_workload_health',
        'list_routes',
        'list_network_policies',
        'list_persistent_storage'
      ]
    },
    'iam-encryption': {
      label: 'Namespace guardrails and workload privilege hygiene',
      narrative: 'Prioritize SCC posture, service exposure, workload security boundaries, and namespace-level governance signals.',
      features: [
        'list_cluster_infrastructure',
        'list_security_context_constraints',
        'list_network_policies',
        'list_resource_quotas',
        'list_routes',
        'list_services'
      ]
    },
    'resilience-governance': {
      label: 'Operator resilience and cluster governance',
      narrative: 'Review operator lifecycle stability, node pool posture, machine configuration state, and storage readiness across the platform.',
      features: [
        'list_cluster_infrastructure',
        'list_cluster_operators',
        'list_operator_subscriptions',
        'list_cluster_service_versions',
        'list_machine_config_pools',
        'list_machine_sets',
        'list_persistent_storage',
        'list_storage_classes'
      ]
    },
    acm: {
      label: 'ACM fleet governance and policy posture',
      narrative: 'Review MultiClusterHub health, managed-cluster availability, cluster-set distribution, and governance-policy drift across the repo-wide OpenShift estate.',
      features: [
        'list_cluster_infrastructure',
        'list_acm_multicluster_hubs',
        'list_acm_managed_clusters',
        'list_acm_policies',
        'list_cluster_operators'
      ]
    },
    acs: {
      label: 'ACS central and secured-cluster coverage',
      narrative: 'Review ACS central health, secured-cluster rollout, network segmentation, and workload posture so protection gaps are obvious before they become audit surprises.',
      features: [
        'list_cluster_infrastructure',
        'list_acs_central_services',
        'list_acs_secured_clusters',
        'list_network_policies',
        'list_workload_health',
        'list_cluster_operators'
      ]
    },
    'gitops-delivery': {
      label: 'GitOps and delivery security posture',
      narrative: 'Review Argo CD, Tekton, build and workload delivery posture so software-supply and promotion drift becomes visible before it becomes an incident.',
      features: [
        'list_cluster_infrastructure',
        'list_gitops_argocds',
        'list_gitops_applications',
        'list_tekton_configs',
        'list_tekton_pipeline_runs',
        'list_workload_health',
        'list_operator_subscriptions'
      ]
    },
    'day2-services': {
      label: 'Day-2 services hardening and resilience',
      narrative: 'Review cluster logging, backup posture, operator lifecycle, storage dependencies, and recovery-readiness signals across the OpenShift estate.',
      features: [
        'list_cluster_infrastructure',
        'list_cluster_logging',
        'list_oadp_resources',
        'list_persistent_storage',
        'list_storage_classes',
        'list_cluster_operators',
        'list_operator_subscriptions'
      ]
    },
    'identity-access': {
      label: 'OAuth / LDAP and guardrail posture',
      narrative: 'Review cluster identity providers, SCC posture, namespace guardrails, and network boundaries so access drift is separated from workload-side breakage.',
      features: [
        'list_cluster_infrastructure',
        'list_oauth_configuration',
        'list_security_context_constraints',
        'list_network_policies',
        'list_resource_quotas',
        'list_cluster_operators'
      ]
    },
    'platform-patterns': {
      label: 'Baremetal / ROSA / ARO / IBM Z platform-pattern coverage',
      narrative: 'Compare infrastructure pattern, fleet membership, operator health, identity posture, and node posture across baremetal, ROSA, ARO, and IBM Z-aligned estates so pattern-specific gaps stand out quickly.',
      features: [
        'list_cluster_infrastructure',
        'list_nodes',
        'list_cluster_operators',
        'list_acm_managed_clusters',
        'list_oauth_configuration',
        'list_resource_quotas'
      ]
    }
  };

  const presetProfiles = {
    sox: 'sox',
    hipaa: 'hipaa',
    findings: 'nist',
    governance: 'resilience-governance',
    'iam-encryption': 'iam-encryption',
    acm: 'acm',
    acs: 'acs',
    gitops: 'gitops-delivery',
    day2: 'day2-services',
    identity: 'identity-access',
    platform: 'platform-patterns'
  };

  function escapeHtml(value) {
    return String(value ?? '')
      .replaceAll('&', '&amp;')
      .replaceAll('<', '&lt;')
      .replaceAll('>', '&gt;')
      .replaceAll('"', '&quot;')
      .replaceAll("'", '&#39;');
  }

  function getFriendlyMessage(message) {
    return String(message || 'No update available yet.');
  }

  function formatPercent(value) {
    const numeric = Number(value);
    return Number.isFinite(numeric) ? `${Math.round(numeric * 100)}%` : '—';
  }

  function formatNumber(value) {
    const numeric = Number(value);
    return Number.isFinite(numeric) ? numeric.toLocaleString() : '—';
  }

  function formatTimestamp(value) {
    return value ? new Date(value).toLocaleString() : '—';
  }

  function createTimestampSlug() {
    return new Date().toISOString().replace(/[:.]/g, '-');
  }

  function toCsv(rows = []) {
    return rows
      .map((row = []) => row.map((value) => {
        const text = String(value ?? '');
        if (text.includes(',') || text.includes('"') || text.includes('\n')) {
          return `"${text.replaceAll('"', '""')}"`;
        }
        return text;
      }).join(','))
      .join('\n');
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

  function summarizeNarrativeLines(answer, limit = 8) {
    return String(answer || '')
      .split(/\n+/)
      .map((line) => line.replace(/^[-*\d.\s]+/, '').trim())
      .filter(Boolean)
      .slice(0, limit);
  }

  function collectNextActions(answer, steps) {
    const explicit = String(answer || '')
      .split(/\n+/)
      .map((line) => line.trim())
      .filter((line) => /^(-|\*|\d+\.)\s+/.test(line))
      .map((line) => line.replace(/^(-|\*|\d+\.)\s+/, ''));
    if (explicit.length > 0) {
      return explicit.slice(0, 6);
    }
    const fallback = [];
    for (const step of steps || []) {
      const toolName = step.tool_call?.name;
      if (step.tool_error && toolName) {
        fallback.push(`Retry ${featureLabels[toolName] || toolName} and review the returned platform error before closing the audit.`);
      }
      if (fallback.length >= 6) {
        break;
      }
    }
    return fallback.length > 0 ? fallback : ['Review the selected controls with the control owner and confirm remediation or accepted-risk decisions.'];
  }

  function buildPrompt(profileKey, focusLabel, region, features, notes) {
    const profile = auditProfiles[profileKey] || auditProfiles.sox;
    const featureNames = features.map((feature) => featureLabels[feature] || feature);
    const toolList = features.join(', ');
    const instructions = [
      `Perform an OpenShift security review using the audit profile "${profile.label}".`,
      profile.narrative,
      `Primary cluster or scope: ${region}.`,
      `Review focus: ${focusLabel}.`,
      `Selected OpenShift security features: ${featureNames.join(', ')}.`,
      `Prefer these OpenShift inspection tools where appropriate: ${toolList}.`,
      'Return an executive summary, the highest-priority findings, what is healthy, what is missing or disabled, and recommended next steps for operators and auditors.',
      'If a service is unavailable, not enabled, or returns a platform error, say so explicitly instead of assuming a healthy posture.'
    ];
    if (notes) {
      instructions.push(`Operator notes: ${notes}`);
    }
    return instructions.join(' ');
  }

  function buildSummaryCards(context) {
    const steps = context?.steps || [];
    const successfulSteps = steps.filter((step) => step.tool_call?.name && step.tool_result && !step.tool_error).length;
    const failedSteps = steps.filter((step) => step.tool_error).length;
    return [
      { label: 'Audit profile', value: context.profileLabel, detail: context.focusLabel },
      { label: 'Selected controls', value: `${context.selectedFeatures.length}`, detail: context.selectedFeatures.map((feature) => featureLabels[feature] || feature).slice(0, 4).join(', ') || 'No controls selected' },
      { label: 'Successful tool calls', value: `${successfulSteps}`, detail: failedSteps > 0 ? `${failedSteps} tool errors captured` : 'No tool errors captured' },
      { label: 'Run confidence', value: formatPercent(context.confidence), detail: `Run #${context.runId || '—'} • ${context.region}` }
    ];
  }

  function buildFindingCards(context) {
    const coverage = context.selectedFeatures.map((feature) => {
      const matchingStep = (context.steps || []).find((step) => step.tool_call?.name === feature);
      return {
        label: featureLabels[feature] || feature,
        status: matchingStep?.tool_error ? 'Error' : matchingStep?.tool_result ? 'Reviewed' : 'Requested',
        detail: matchingStep?.tool_error || matchingStep?.thought || 'Awaiting or inferred through the final summary.'
      };
    });
    const highlights = summarizeNarrativeLines(context.answer, 4).map((line) => ({
      label: 'Finding highlight',
      status: 'Narrative',
      detail: line
    }));
    const cards = [...coverage.slice(0, 6), ...highlights].slice(0, 8);
    return cards;
  }

  function buildReportContext(context, reportType) {
    const highlights = summarizeNarrativeLines(context.answer, 8);
    const nextActions = collectNextActions(context.answer, context.steps);
    return {
      reportType,
      reportLabel: reportType === 'compliance-handoff' ? 'Compliance Handoff' : 'Audit Posture Pack',
      generatedAt: new Date(),
      profileLabel: context.profileLabel,
      focusLabel: context.focusLabel,
      region: context.region,
      runId: context.runId,
      confidence: context.confidence,
      selectedFeatures: context.selectedFeatures,
      answer: context.answer,
      steps: context.steps,
      highlights,
      nextActions
    };
  }

  function exportReportCsv(context) {
    const rows = [
      ['Section', 'Field', 'Value'],
      ['summary', 'report_type', context.reportLabel],
      ['summary', 'generated_at', context.generatedAt.toISOString()],
      ['summary', 'audit_profile', context.profileLabel],
      ['summary', 'focus', context.focusLabel],
      ['summary', 'region', context.region],
      ['summary', 'run_id', context.runId ?? ''],
      ['summary', 'confidence', context.confidence ?? ''],
      ['summary', 'selected_features', context.selectedFeatures.map((feature) => featureLabels[feature] || feature).join('|')],
      [],
      ['highlights', 'line'],
      ...context.highlights.map((line) => ['highlights', line]),
      [],
      ['next_actions', 'line'],
      ...context.nextActions.map((line) => ['next_actions', line]),
      [],
      ['steps', 'step', 'tool', 'thought', 'tool_error'],
      ...context.steps.map((step) => [
        'steps',
        step.step ?? '',
        featureLabels[step.tool_call?.name] || step.tool_call?.name || '',
        step.thought || '',
        step.tool_error || ''
      ])
    ];
    downloadBlob(`openshift-sre-security-${context.reportType}-${createTimestampSlug()}.csv`, new Blob([toCsv(rows)], { type: 'text/csv;charset=utf-8' }));
  }

  async function exportReportPpt(context) {
    const PptxGenJS = window.PptxGenJS;
    if (!PptxGenJS) {
      throw new Error('PowerPoint export library is not available on this page right now.');
    }
    const pptx = new PptxGenJS();
    pptx.layout = 'LAYOUT_WIDE';
    pptx.author = 'GitHub Copilot';
    pptx.company = 'OpenShift SRE Local Agent';
    pptx.subject = context.reportLabel;
    pptx.title = `${context.reportLabel} - ${context.profileLabel}`;

    const titleSlide = pptx.addSlide();
    titleSlide.background = { color: 'F8FAFC' };
    titleSlide.addText(context.reportLabel, { x: 0.5, y: 0.5, w: 6.2, h: 0.5, fontSize: 24, bold: true, color: '0F172A' });
    titleSlide.addText(`${context.profileLabel} • ${context.region} • ${context.generatedAt.toLocaleString()}`, { x: 0.5, y: 1.1, w: 8.0, h: 0.3, fontSize: 14, color: '2563EB' });
    titleSlide.addText(`Focus: ${context.focusLabel}\nRun: ${context.runId || '—'}\nConfidence: ${formatPercent(context.confidence)}`, { x: 0.5, y: 1.7, w: 5.6, h: 1.7, fontSize: 13, color: '334155', breakLine: true });
    titleSlide.addText(context.highlights.length > 0 ? context.highlights.map((line) => `• ${line}`).join('\n') : '• No highlights were returned.', { x: 6.7, y: 1.3, w: 5.4, h: 3.0, fontSize: 12, color: '0F172A', margin: 0.12, fill: { color: 'DBEAFE' }, line: { color: '93C5FD' } });

    const controlsSlide = pptx.addSlide();
    controlsSlide.addText('Selected controls and next actions', { x: 0.5, y: 0.4, w: 6.6, h: 0.4, fontSize: 20, bold: true, color: '0F172A' });
    controlsSlide.addText(context.selectedFeatures.map((feature) => `• ${featureLabels[feature] || feature}`).join('\n'), { x: 0.5, y: 1.0, w: 5.8, h: 4.8, fontSize: 12, color: '0F172A', margin: 0.12, fill: { color: 'FFFFFF' }, line: { color: 'CBD5E1' } });
    controlsSlide.addText(context.nextActions.map((line) => `• ${line}`).join('\n'), { x: 6.7, y: 1.0, w: 5.4, h: 4.8, fontSize: 12, color: '0F172A', margin: 0.12, fill: { color: 'FFFFFF' }, line: { color: 'CBD5E1' } });

    await pptx.writeFile({ fileName: `openshift-sre-security-${context.reportType}-${createTimestampSlug()}.pptx` });
  }

  async function exportReportPdf(context) {
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
    doc.setFont('helvetica', 'normal');
    doc.setFontSize(12);
    doc.text(`${context.profileLabel} • ${context.region} • ${context.generatedAt.toLocaleString()}`, 48, cursorY);
    cursorY += 24;
    addBlock('Review focus', [`Focus: ${context.focusLabel}`, `Run: ${context.runId || '—'}`, `Confidence: ${formatPercent(context.confidence)}`]);
    addBlock('Selected controls', context.selectedFeatures.map((feature) => featureLabels[feature] || feature));
    addBlock('Highlights', context.highlights.length > 0 ? context.highlights : ['No highlights were returned.']);
    addBlock('Next actions', context.nextActions);
    doc.save(`openshift-sre-security-${context.reportType}-${createTimestampSlug()}.pdf`);
  }

  async function exportReportWord(context) {
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
    <p class="meta">${escapeHtml(context.profileLabel)} · ${escapeHtml(context.region)} · ${escapeHtml(context.generatedAt.toLocaleString())}</p>
    <div>
      <span class="chip">Focus: ${escapeHtml(context.focusLabel)}</span>
      <span class="chip">Run: ${escapeHtml(context.runId || '—')}</span>
      <span class="chip">Confidence: ${escapeHtml(formatPercent(context.confidence))}</span>
    </div>
    <div class="section">
      <h2>Selected controls</h2>
      <ul>${context.selectedFeatures.map((feature) => `<li>${escapeHtml(featureLabels[feature] || feature)}</li>`).join('')}</ul>
    </div>
    <div class="section">
      <h2>Highlights</h2>
      <ul>${(context.highlights.length > 0 ? context.highlights : ['No highlights were returned.']).map((line) => `<li>${escapeHtml(line)}</li>`).join('')}</ul>
    </div>
    <div class="section">
      <h2>Next actions</h2>
      <ul>${context.nextActions.map((line) => `<li>${escapeHtml(line)}</li>`).join('')}</ul>
    </div>
  </body>
</html>`;
    downloadBlob(`openshift-sre-security-${context.reportType}-${createTimestampSlug()}.doc`, new Blob([html], { type: 'application/msword' }));
  }

  function applyTheme(theme) {
    document.body.dataset.theme = theme === 'dark' ? 'dark' : 'light';
    window.localStorage.setItem(themeStorageKey, document.body.dataset.theme);
  }

  function initializeTheme() {
    const stored = window.localStorage.getItem(themeStorageKey);
    applyTheme(stored || document.body.dataset.theme || 'light');
  }

  async function apiFetchModels(ollamaBaseUrl = '') {
    const params = new URLSearchParams();
    if (ollamaBaseUrl) {
      params.set('ollama_base_url', ollamaBaseUrl);
    }
    const response = await fetch(`${API_BASE}/ollama/models${params.toString() ? `?${params}` : ''}`);
    if (!response.ok) {
      throw new Error(`Model list request failed ${response.status}`);
    }
    return response.json();
  }

  async function apiFetchProviderCatalog() {
    return llmRuntime.fetchProviderCatalog?.() || { configured_provider: 'ollama', configured_model_name: 'gpt-oss:20b', providers: [{ id: 'ollama', label: 'Local Ollama', default_model: 'gpt-oss:20b', default_base_url: 'http://localhost:11434', supports_catalog_refresh: true, suggested_models: ['gpt-oss:20b'] }] };
  }

  function Toast({ toast, onDismiss }) {
    useEffect(() => {
      if (!toast?.message) {
        return undefined;
      }
      const timeout = window.setTimeout(onDismiss, 5000);
      return () => window.clearTimeout(timeout);
    }, [toast, onDismiss]);

    if (!toast?.message) {
      return null;
    }

    return h('div', { className: `finops-toast finops-toast--${toast.kind || 'info'}`, onClick: onDismiss }, toast.message);
  }

  function SettingsPanel({ settings, onChange, modelCatalog, modelsLoading, onRefreshModels, providerCatalog }) {
    const set = (key) => (event) => onChange({
      ...settings,
      [key]: event.target.type === 'checkbox' ? event.target.checked : event.target.value
    });
    const currentProviderId = llmRuntime.normalizeProviderId?.(providerCatalog, settings.provider) || 'ollama';
    const provider = llmRuntime.getProvider?.(providerCatalog, currentProviderId) || providerCatalog?.providers?.[0] || { id: 'ollama', label: 'Local Ollama', default_model: 'gpt-oss:20b', default_base_url: 'http://localhost:11434' };
    const useExternal = currentProviderId !== 'ollama';
    const catalogModels = Array.isArray(modelCatalog?.models) ? modelCatalog.models : [];
    const defaultModel = settings.modelName || modelCatalog?.configured_model_name || provider.default_model || 'gpt-oss:20b';
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
          h('select', {
            className: 'agent-console__input',
            value: currentProviderId,
            onChange: set('provider')
          }, (providerCatalog?.providers || []).map((item) => h('option', { key: item.id, value: item.id }, item.label)))
        ),
        useExternal ? h(Fragment, null,
          h('label', null,
            'External model',
            h('input', {
              className: 'agent-console__input',
              type: 'text',
              placeholder: provider.default_model || 'gpt-4.1-mini',
              value: settings.externalModelName,
              onChange: set('externalModelName')
            })
          ),
          h('label', null,
            'Provider base URL',
            h('input', {
              className: 'agent-console__input',
              type: 'url',
              placeholder: provider.default_base_url || 'https://api.openai.com/v1',
              value: settings.externalBaseUrl,
              onChange: set('externalBaseUrl')
            })
          ),
          h('label', null,
            'Provider API key',
            h('input', {
              className: 'agent-console__input',
              type: 'password',
              placeholder: 'Required for external providers',
              value: settings.externalApiKey,
              onChange: set('externalApiKey')
            })
          ),
          h('label', null,
            'Organization / tenant',
            h('input', {
              className: 'agent-console__input',
              type: 'text',
              placeholder: 'Optional provider org or tenant hint',
              value: settings.externalOrganization,
              onChange: set('externalOrganization')
            })
          ),
          h('label', null,
            'API version',
            h('input', {
              className: 'agent-console__input',
              type: 'text',
              placeholder: provider.default_api_version || 'Optional API version',
              value: settings.externalApiVersion,
              onChange: set('externalApiVersion')
            })
          )
        ) : h(Fragment, null,
          h('label', null,
            'Ollama URL',
            h('input', {
              className: 'agent-console__input',
              type: 'url',
              placeholder: 'http://host.containers.internal:11434',
              value: settings.ollamaBaseUrl,
              onChange: set('ollamaBaseUrl')
            })
          ),
          h('label', null,
            'Model',
            h('div', { className: 'finops-settings__model-picker' },
              h('select', {
                className: 'agent-console__input',
                value: defaultModel,
                onChange: set('modelName'),
                disabled: modelsLoading && optionMap.size === 0
              }, Array.from(optionMap.entries()).map(([value, label]) => h('option', { key: value, value }, label))),
              h('button', {
                className: 'agent-console__example',
                type: 'button',
                onClick: onRefreshModels,
                disabled: modelsLoading
              }, modelsLoading ? 'Refreshing…' : 'Refresh')
            )
          )
        ),
        h('label', null,
          'Cluster name / scope label',
          h('input', { className: 'agent-console__input', type: 'text', placeholder: 'prod-cluster', value: settings.openshiftCluster, onChange: set('openshiftCluster') })
        ),
        h('label', null,
          'Kube context',
          h('input', { className: 'agent-console__input', type: 'text', placeholder: 'default', value: settings.kubeContext, onChange: set('kubeContext') })
        ),
        h('label', null,
          'API server URL',
          h('input', { className: 'agent-console__input', type: 'text', placeholder: 'https://api.cluster.example.com:6443', value: settings.openshiftApiUrl, onChange: set('openshiftApiUrl') })
        ),
        h('label', null,
          'API token',
          h('input', { className: 'agent-console__input', type: 'password', placeholder: 'Optional', value: settings.openshiftToken, onChange: set('openshiftToken') })
        ),
        h('label', null,
          'Namespace / project',
          h('input', { className: 'agent-console__input', type: 'text', placeholder: 'openshift-operators', value: settings.openshiftNamespace, onChange: set('openshiftNamespace') })
        ),
        h('label', null,
          'Kubeconfig path',
          h('input', { className: 'agent-console__input', type: 'text', placeholder: '~/.kube/config', value: settings.kubeconfigPath, onChange: set('kubeconfigPath') })
        ),
        h('label', { className: 'agent-console__checkbox' },
          h('input', { type: 'checkbox', checked: settings.openshiftVerifySsl, onChange: set('openshiftVerifySsl') }),
          h('span', null, 'Verify cluster API certificates')
        ),
          h('p', { className: 'agent-console__meta' }, provider.description || 'Choose the local Ollama model or an external provider like OpenAI, Azure OpenAI, Anthropic, Gemini, or OpenRouter.')
      )
    );
  }

  function SummaryCards({ context }) {
    if (!context) {
      return h('p', { className: 'agent-console__meta' }, 'Run a security review to populate summary cards.');
    }
    return h('div', { className: 'security-summary-grid' }, buildSummaryCards(context).map((card) =>
      h('article', { key: card.label, className: 'agent-console__history-card agent-console__history-card--timeline' },
        h('h3', null, card.label),
        h('p', null, h('strong', null, card.value)),
        h('p', { className: 'agent-console__meta' }, card.detail)
      )
    ));
  }

  function FindingsGrid({ context }) {
    const cards = context ? buildFindingCards(context) : [];
    if (!cards.length) {
      return h('p', { className: 'agent-console__meta' }, 'Coverage cards will call out the controls and findings captured by the latest run.');
    }
    return h('div', { className: 'finops-category-list security-findings-grid' }, cards.map((card, index) =>
      h('article', { key: `${card.label}-${index}`, className: 'finops-category-card' },
        h('div', { className: 'finops-category-header' },
          h('h4', null, card.label),
          h('span', { className: `finops-pill${card.status && card.status !== 'Review area' ? ' finops-pill--active' : ''}` }, card.status)
        ),
        h('p', { className: 'agent-console__meta' }, card.detail)
      )
    ));
  }

  function TraceTable({ context }) {
    if (!context?.steps?.length) {
      return h('p', { className: 'agent-console__meta' }, 'Reasoning steps and tool evidence will appear here after the first run.');
    }
    return h('div', { className: 'security-trace-table' },
      h('table', { className: 'agent-console__table' },
        h('thead', null,
          h('tr', null,
            ['Step', 'Tool / control', 'Status', 'Reasoning / evidence'].map((label) => h('th', { key: label }, label))
          )
        ),
        h('tbody', null, context.steps.map((step, index) => {
          const toolName = step.tool_call?.name || '—';
          const status = step.tool_error ? 'error' : step.tool_result ? 'ok' : step.final_answer ? 'answer' : 'pending';
          const detail = step.tool_error || step.thought || step.final_answer || 'No additional detail recorded.';
          return h('tr', { key: `${toolName}-${index}` },
            h('td', null, step.step ?? '—'),
            h('td', null, featureLabels[toolName] || toolName),
            h('td', null, status),
            h('td', null, detail)
          );
        }))
      )
    );
  }

  function ReportDeck({ context, statusMessage, statusKind, onExport, exporting }) {
    const highlights = context ? summarizeNarrativeLines(context.answer, 5) : [];
    return h('section', { className: 'finops-report-deck', id: 'security-exports' },
      h('div', { className: 'finops-report-deck__header' },
        h('div', null,
          h('p', { className: 'finops-report-deck__kicker' }, 'Audit export lane'),
          h('h3', null, 'Presentation-ready security export'),
          h('p', { className: 'agent-console__meta' }, context
            ? 'Export the latest audit review as a handoff pack without leaving the React workspace.'
            : 'Run a security review first, then export the resulting audit pack in the format you need.')
        ),
        h('div', { className: 'finops-report-deck__actions' },
          ['csv', 'ppt', 'pdf', 'word'].map((format) => h('button', {
            key: format,
            className: `agent-console__button${format === 'pdf' ? ' agent-console__button--secondary' : ''}`,
            type: 'button',
            onClick: () => onExport('audit-pack', format),
            disabled: Boolean(exporting)
          }, exporting === format ? `Preparing ${format.toUpperCase()}…` : `Export ${format.toUpperCase()}`)),
          h('span', { className: `finops-pill ${context ? 'finops-pill--active' : ''}` }, context ? 'Report ready' : 'Waiting for review')
        )
      ),
      h('div', { className: 'finops-report-deck__grid' },
        h('article', { className: 'finops-report-card' },
          h('h4', null, 'Audit profile'),
          h('p', null, context?.profileLabel || '—'),
          h('p', { className: 'agent-console__meta' }, context?.focusLabel || 'Choose a review focus and run the agent.')
        ),
        h('article', { className: 'finops-report-card' },
          h('h4', null, 'Selected controls'),
          h('p', null, context ? String(context.selectedFeatures.length) : '0'),
          h('p', { className: 'agent-console__meta' }, context ? `Run #${context.runId || '—'} • ${context.region}` : 'No live run yet.')
        ),
        h('article', { className: 'finops-report-card' },
          h('h4', null, 'Confidence'),
          h('p', null, context ? formatPercent(context.confidence) : '—'),
          h('p', { className: 'agent-console__meta' }, 'Export includes highlights, evidence trace, and next actions.')
        )
      ),
      h('div', { className: 'finops-report-deck__summary' },
        h('article', { className: 'finops-report-deck__column' },
          h('h4', null, 'Highlights'),
          highlights.length
            ? h('ul', { className: 'finops-report-list' }, highlights.map((item) => h('li', { key: item }, item)))
            : h('p', { className: 'agent-console__meta' }, 'No highlights available yet.')
        ),
        h('article', { className: 'finops-report-deck__column' },
          h('h4', null, 'Export status'),
          h('p', { className: 'agent-console__meta' }, statusMessage || 'Run a security review to unlock exports.'),
          statusKind ? h('span', { className: `agent-console__history-badge agent-console__history-badge--${statusKind === 'error' ? 'error' : 'ok'}` }, statusKind) : null
        )
      )
    );
  }

  function SecurityApp() {
    const [profileKey, setProfileKey] = useState('sox');
    const [focusKey, setFocusKey] = useState('executive');
    const [region, setRegion] = useState('prod-cluster');
    const [settings, setSettings] = useState({
      provider: 'ollama',
      ollamaBaseUrl: '',
      modelName: '',
      externalModelName: '',
      externalBaseUrl: '',
      externalApiKey: '',
      externalApiVersion: '',
      externalOrganization: '',
      openshiftCluster: 'prod-cluster',
      kubeContext: '',
      openshiftApiUrl: '',
      openshiftToken: '',
      openshiftNamespace: '',
      kubeconfigPath: '',
      openshiftVerifySsl: true
    });
    const [modelCatalog, setModelCatalog] = useState({ configured_model_name: 'gpt-oss:20b', models: [] });
    const [providerCatalog, setProviderCatalog] = useState(llmRuntime.fallbackCatalog || { configured_provider: 'ollama', configured_model_name: 'gpt-oss:20b', providers: [{ id: 'ollama', label: 'Local Ollama', default_model: 'gpt-oss:20b', default_base_url: 'http://localhost:11434', supports_catalog_refresh: true, suggested_models: ['gpt-oss:20b'] }] });
    const [modelsLoading, setModelsLoading] = useState(false);
    const [selectedFeatures, setSelectedFeatures] = useState(auditProfiles.sox.features);
    const [notes, setNotes] = useState('');
    const [status, setStatus] = useState({ message: 'Pick an audit profile and feature set, then run the review.', kind: '' });
    const [reportStatus, setReportStatus] = useState({ message: 'Run a security review to unlock exports.', kind: '' });
    const [toast, setToast] = useState({ message: '', kind: '' });
    const [context, setContext] = useState(null);
    const [running, setRunning] = useState(false);
    const [exporting, setExporting] = useState('');

    useEffect(() => {
      initializeTheme();
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
            modelName: current.modelName || payload.configured_model_name || availableNames[0] || 'gpt-oss:20b'
          };
        });
      } catch (error) {
        setToast({ message: error instanceof Error ? error.message : 'Unable to load model options.', kind: 'error' });
      } finally {
        setModelsLoading(false);
      }
    }, [providerCatalog, settings.ollamaBaseUrl, settings.provider]);

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

    const currentProfile = auditProfiles[profileKey] || auditProfiles.sox;
    const focusLabel = useMemo(() => ({
      executive: 'Executive summary + priority findings',
      controls: 'Control-by-control gap analysis',
      findings: 'Threat and findings triage',
      handoff: 'Audit handoff and evidence notes'
    }[focusKey] || focusKey), [focusKey]);

    const applyPreset = (presetKey) => {
      const mapped = presetProfiles[presetKey] || 'sox';
      const preset = auditProfiles[mapped] || auditProfiles.sox;
      setProfileKey(mapped);
      setSelectedFeatures(preset.features);
      setStatus({ message: `Loaded the ${preset.label} preset.`, kind: 'ok' });
      setToast({ message: `Loaded ${preset.label}.`, kind: 'ok' });
    };

    const runReview = async () => {
      if (!selectedFeatures.length) {
        setStatus({ message: 'Choose at least one OpenShift security feature before running the review.', kind: 'error' });
        return;
      }

      const normalizedRegion = region.trim() || 'prod-cluster';
      const runtimeRegion = settings.openshiftCluster.trim() || normalizedRegion;
      setRunning(true);
      setStatus({ message: `Running ${currentProfile.label} review for ${normalizedRegion}…`, kind: 'ok' });
      setToast({ message: 'Running security review…', kind: 'info' });

      try {
        const response = await fetch('/security/audit', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            profile_key: profileKey,
            profile_label: currentProfile.label,
            focus_label: focusLabel,
            selected_features: selectedFeatures,
            operator_notes: notes.trim(),
            runtime: {
              openshift_cluster: runtimeRegion,
              agent_max_steps: 20,
              ...(llmRuntime.buildLlmRuntime?.({
                provider: settings.provider,
                ollamaBaseUrl: settings.ollamaBaseUrl,
                modelName: settings.modelName,
                externalModelName: settings.externalModelName,
                externalBaseUrl: settings.externalBaseUrl,
                externalApiKey: settings.externalApiKey,
                externalApiVersion: settings.externalApiVersion,
                externalOrganization: settings.externalOrganization,
              }, providerCatalog) || {}),
              ...(settings.kubeContext.trim() ? { kube_context: settings.kubeContext.trim() } : {}),
              ...(settings.openshiftApiUrl.trim() ? { openshift_api_url: settings.openshiftApiUrl.trim() } : {}),
              ...(settings.openshiftToken.trim() ? { openshift_token: settings.openshiftToken.trim() } : {}),
              ...(settings.openshiftNamespace.trim() ? { openshift_namespace: settings.openshiftNamespace.trim() } : {}),
              ...(settings.kubeconfigPath.trim() ? { kubeconfig_path: settings.kubeconfigPath.trim() } : {}),
              openshift_verify_ssl: settings.openshiftVerifySsl
            },
            tags: ['security-console', profileKey]
          })
        });
        const payload = await response.json();
        if (!response.ok) {
          throw new Error(payload.detail || `Security review failed with status ${response.status}`);
        }

        const nextContext = {
          answer: payload.answer || '',
          steps: Array.isArray(payload.steps) ? payload.steps : [],
          runId: payload.run_id,
          confidence: payload.confidence,
          profileKey,
          profileLabel: currentProfile.label,
          focusLabel,
          region: runtimeRegion,
          selectedFeatures
        };
        setContext(nextContext);
        setStatus({ message: `Security review complete. Run #${payload.run_id || '—'} is ready for export.`, kind: 'ok' });
        setReportStatus({ message: 'Audit review ready for export.', kind: 'ok' });
        setToast({ message: 'Security review complete.', kind: 'ok' });
      } catch (error) {
        const message = error instanceof Error ? error.message : 'Unable to run the security review.';
        setContext(null);
        setStatus({ message, kind: 'error' });
        setReportStatus({ message: 'Run a security review to unlock exports.', kind: '' });
        setToast({ message, kind: 'error' });
      } finally {
        setRunning(false);
      }
    };

    const handleExport = async (reportType, format) => {
      if (!context?.answer) {
        setReportStatus({ message: 'Run a security review first so there is live content to export.', kind: 'error' });
        return;
      }

      const reportContext = buildReportContext(context, reportType);
      setExporting(format);
      setReportStatus({ message: `Building ${reportContext.reportLabel} as ${format.toUpperCase()}…`, kind: 'ok' });

    try {
      if (format === 'csv') {
          exportReportCsv(reportContext);
      } else if (format === 'ppt') {
          await exportReportPpt(reportContext);
      } else if (format === 'pdf') {
          await exportReportPdf(reportContext);
      } else {
          await exportReportWord(reportContext);
      }
        setReportStatus({ message: `${reportContext.reportLabel} exported as ${format.toUpperCase()}.`, kind: 'ok' });
        setToast({ message: `${reportContext.reportLabel} exported as ${format.toUpperCase()}.`, kind: 'ok' });
    } catch (error) {
        setReportStatus({ message: error instanceof Error ? error.message : `Unable to export ${reportContext.reportLabel}.`, kind: 'error' });
        setToast({ message: error instanceof Error ? error.message : 'Export failed.', kind: 'error' });
    } finally {
        setExporting('');
      }
    };

    return h('div', { className: 'agent-console' },
      h(Toast, { toast, onDismiss: () => setToast({ message: '', kind: '' }) }),
      h('section', { className: 'finops-workspace-hero agent-console__panel agent-console__panel--full', id: 'security-workspace-hero' },
        h('div', { className: 'finops-workspace-hero__copy' },
          h('p', { className: 'finops-workspace-hero__kicker' }, 'Security command deck'),
          h('h2', null, 'Audit, threat, and governance reviews in a proper React workspace'),
          h('p', { className: 'agent-console__meta' }, 'The Security Console now matches the operator-shell pattern used by the React-powered pages, with a richer launch surface, themed result lanes, and exportable OpenShift audit handoffs.')
        ),
        h('div', { className: 'finops-workspace-hero__stats' },
          h('article', { className: 'finops-workspace-hero__stat' }, h('span', null, 'Current profile'), h('strong', null, currentProfile.label)),
          h('article', { className: 'finops-workspace-hero__stat' }, h('span', null, 'Selected controls'), h('strong', null, String(selectedFeatures.length))),
          h('article', { className: 'finops-workspace-hero__stat' }, h('span', null, 'Export formats'), h('strong', null, 'CSV · PPT · PDF · Word'))
        )
      ),
      h('section', { className: 'agent-console__panel finops-panel', id: 'security-launcher' },
        h('h2', null, 'Launch a security review'),
        h('p', { className: 'agent-console__meta' }, 'Choose the audit lens, then select the OpenShift security and governance features you want inspected. Cmd/Ctrl + Enter also runs the review.'),
        h(SettingsPanel, {
          settings,
          onChange: setSettings,
          modelCatalog,
          modelsLoading,
          providerCatalog,
          onRefreshModels: () => refreshModels(settings.ollamaBaseUrl)
        }),
        h('div', { className: 'security-control-grid' },
          h('label', null, 'Audit profile', h('select', { className: 'agent-console__input', value: profileKey, onChange: (event) => setProfileKey(event.target.value) }, Object.entries(auditProfiles).map(([key, profile]) => h('option', { key, value: key }, profile.label)))),
          h('label', null, 'Review focus', h('select', { className: 'agent-console__input', value: focusKey, onChange: (event) => setFocusKey(event.target.value) },
            h('option', { value: 'executive' }, 'Executive summary + priority findings'),
            h('option', { value: 'controls' }, 'Control-by-control gap analysis'),
            h('option', { value: 'findings' }, 'Threat and findings triage'),
            h('option', { value: 'handoff' }, 'Audit handoff and evidence notes')
          )),
          h('label', null, 'Primary cluster / environment', h('input', { className: 'agent-console__input', type: 'text', value: region, onChange: (event) => setRegion(event.target.value), placeholder: 'prod-cluster' })),
          h('div', { className: 'security-field' },
            h('label', { htmlFor: 'security-features-react' }, 'OpenShift security and governance features'),
            h('select', {
              id: 'security-features-react',
              className: 'agent-console__input security-features-select',
              multiple: true,
              size: 18,
              value: selectedFeatures,
              onChange: (event) => setSelectedFeatures(Array.from(event.target.selectedOptions).map((option) => option.value))
            }, Object.entries(featureLabels).map(([value, label]) => h('option', { key: value, value }, label)))
          )
        ),
        h('label', { className: 'agent-console__label', htmlFor: 'security-notes-react' }, 'Operator notes'),
        h('textarea', {
          id: 'security-notes-react',
          className: 'agent-console__textarea',
          value: notes,
          onChange: (event) => setNotes(event.target.value),
          placeholder: 'Add scope notes, control-owner asks, incident context, or evidence expectations.',
          onKeyDown: (event) => {
            if ((event.metaKey || event.ctrlKey) && event.key === 'Enter') {
              event.preventDefault();
              runReview();
            }
          }
        }),
        h('div', { className: 'security-preset-row' },
          h('button', { className: 'agent-console__button', type: 'button', onClick: runReview, disabled: running }, running ? 'Running…' : 'Run security review'),
          h('button', { className: 'agent-console__example', type: 'button', onClick: () => applyPreset('sox') }, 'SOX preset'),
          h('button', { className: 'agent-console__example', type: 'button', onClick: () => applyPreset('hipaa') }, 'HIPAA preset'),
          h('button', { className: 'agent-console__example', type: 'button', onClick: () => applyPreset('findings') }, 'Findings triage'),
          h('button', { className: 'agent-console__example', type: 'button', onClick: () => applyPreset('governance') }, 'Governance depth'),
          h('button', { className: 'agent-console__example', type: 'button', onClick: () => applyPreset('iam-encryption') }, 'SCC + guardrails'),
          h('button', { className: 'agent-console__example', type: 'button', onClick: () => applyPreset('acm') }, 'ACM fleet'),
          h('button', { className: 'agent-console__example', type: 'button', onClick: () => applyPreset('acs') }, 'ACS coverage'),
          h('button', { className: 'agent-console__example', type: 'button', onClick: () => applyPreset('gitops') }, 'GitOps / Tekton'),
          h('button', { className: 'agent-console__example', type: 'button', onClick: () => applyPreset('day2') }, 'Logging / OADP'),
          h('button', { className: 'agent-console__example', type: 'button', onClick: () => applyPreset('identity') }, 'OAuth / LDAP'),
          h('button', { className: 'agent-console__example', type: 'button', onClick: () => applyPreset('platform') }, 'Baremetal / ROSA / ARO / IBM Z')
        ),
        h('div', { className: `agent-console__status${status.kind ? ` agent-console__status--${status.kind}` : ''}` }, status.message)
      ),
      h('section', { className: 'agent-console__panel finops-panel', id: 'security-results' },
        h('div', { className: 'agent-console__queue-header' },
          h('div', null,
            h('h2', null, 'Latest security review'),
            h('p', { className: 'agent-console__meta' }, 'See the latest executive summary, selected controls, and run posture from the dedicated security workspace.')
          ),
          h('span', { className: 'agent-console__history-badge agent-console__history-badge--neutral' }, 'Run-backed')
        ),
        h(SummaryCards, { context }),
        h('h3', null, 'Security narrative'),
        context?.answer
          ? h('div', { className: 'agent-console__answer', dangerouslySetInnerHTML: { __html: context.answer.split(/\n{2,}/).map((paragraph) => `<p>${escapeHtml(paragraph).replace(/\n/g, '<br>')}</p>`).join('') } })
          : h('div', { className: 'agent-console__answer' }, 'Security findings and recommendations will appear here after the first run.'),
        h('h3', null, 'Coverage highlights'),
        h(FindingsGrid, { context })
      ),
      h(ReportDeck, { context, statusMessage: reportStatus.message, statusKind: reportStatus.kind, onExport: handleExport, exporting }),
      h('section', { className: 'agent-console__panel finops-panel', id: 'security-trace' },
        h('h2', null, 'Evidence trace'),
        h(TraceTable, { context })
      )
    );
  }

  const rootElement = document.getElementById('security-root');
  if (rootElement) {
    createRoot(rootElement).render(h(SecurityApp));
  }
})();