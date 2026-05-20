(() => {
  const root = document.getElementById('platform-root');
  if (!root || !window.React || !window.ReactDOM) {
    return;
  }

  const { createElement: h, useEffect, useMemo, useState } = window.React;
  const llmRuntime = window.OpenShiftSreLlmRuntime || {};

  const featureLabels = {
    get_cluster_identity: 'Cluster identity, API endpoint, and active context',
    list_cluster_infrastructure: 'Platform inventory / infrastructure topology',
    list_projects: 'Project / namespace inventory and phase posture',
    list_cluster_version: 'Cluster version and upgrade posture',
    list_cluster_operators: 'Cluster operator health',
    list_nodes: 'Node readiness and worker footprint',
    list_node_pressure: 'Node pressure, readiness, and kubelet conditions',
    list_pods: 'Pod phase, restart, and pending risk',
    list_machine_config_pools: 'MachineConfigPool rollout posture',
    list_machine_sets: 'MachineSet capacity posture',
    list_operator_subscriptions: 'Operator subscription health',
    list_cluster_service_versions: 'CSV install and operator lifecycle',
    list_workload_health: 'Workload rollout and readiness posture',
    list_services: 'Service exposure posture',
    list_routes: 'Route posture and ingress pathways',
    list_ingresses: 'Ingress controller posture',
    list_events: 'Recent warning and normal event patterns',
    list_persistent_storage: 'Persistent storage and claims posture',
    list_storage_classes: 'StorageClass defaults and options',
    list_security_context_constraints: 'SecurityContextConstraint privilege posture',
    list_network_policies: 'NetworkPolicy isolation and coverage posture',
    list_resource_quotas: 'ResourceQuota and ClusterResourceQuota guardrails',
    list_image_streams: 'ImageStream tags and lookup policy posture',
    list_builds: 'Build and BuildConfig delivery posture',
    list_gitops_argocds: 'OpenShift GitOps / Argo CD control planes',
    list_gitops_applications: 'Argo CD application drift and health',
    list_tekton_configs: 'TektonConfig delivery posture',
    list_tekton_pipeline_runs: 'PipelineRun delivery failures',
    list_cluster_logging: 'Cluster logging and collector posture',
    list_oadp_resources: 'OADP backup and schedule posture',
    list_acm_multicluster_hubs: 'ACM hub health',
    list_acm_managed_clusters: 'Managed cluster readiness',
    list_acm_policies: 'ACM governance and policy drift',
    list_acs_central_services: 'ACS central service posture',
    list_acs_secured_clusters: 'ACS secured cluster rollout',
    list_oauth_configuration: 'OAuth / LDAP platform access posture',
    list_virtualization_resources: 'OpenShift Virtualization / CNV posture',
    list_disaster_recovery_resources: 'DR policy, placement, and replication posture'
  };

  const platformFeatureGroups = [
    {
      title: 'Core platform and lifecycle',
      features: [
        'get_cluster_identity',
        'list_cluster_infrastructure',
        'list_projects',
        'list_cluster_version',
        'list_cluster_operators',
        'list_nodes',
        'list_node_pressure',
        'list_machine_config_pools',
        'list_machine_sets',
        'list_operator_subscriptions',
        'list_cluster_service_versions',
        'list_oauth_configuration'
      ]
    },
    {
      title: 'Workloads, traffic, and storage',
      features: [
        'list_pods',
        'list_workload_health',
        'list_services',
        'list_routes',
        'list_ingresses',
        'list_events',
        'list_persistent_storage',
        'list_storage_classes',
        'list_resource_quotas'
      ]
    },
    {
      title: 'Security and governance',
      features: [
        'list_security_context_constraints',
        'list_network_policies',
        'list_acm_multicluster_hubs',
        'list_acm_managed_clusters',
        'list_acm_policies',
        'list_acs_central_services',
        'list_acs_secured_clusters'
      ]
    },
    {
      title: 'Delivery, automation, and data services',
      features: [
        'list_image_streams',
        'list_builds',
        'list_gitops_argocds',
        'list_gitops_applications',
        'list_tekton_configs',
        'list_tekton_pipeline_runs',
        'list_cluster_logging',
        'list_oadp_resources'
      ]
    },
    {
      title: 'Virtualization, DR, and migration',
      features: [
        'list_virtualization_resources',
        'list_disaster_recovery_resources'
      ]
    }
  ];

  const orderedFeatureIds = [
    ...platformFeatureGroups.flatMap((group) => group.features),
    ...Object.keys(featureLabels).filter((featureId) => !platformFeatureGroups.some((group) => group.features.includes(featureId)))
  ];

  const allSelectableFeatures = orderedFeatureIds.filter((featureId) => featureLabels[featureId]);

  const platformProfiles = {
    lifecycle: {
      title: 'Lifecycle readiness review',
      summary: 'Assess whether the platform is ready for an upgrade or change window across version, operators, nodes, and machine pools.',
      promptLead: 'Act as an OpenShift platform lifecycle lead preparing a change window. Build a lifecycle-readiness review using the selected evidence and focus on upgrade blockers, operator risk, machine-pool rollout safety, and dependencies across baremetal, ROSA, ARO, and IBM Z platform patterns when relevant.',
      questions: [
        'What would block the next controlled upgrade or maintenance window?',
        'Which operator or machine-pool signals look most likely to elongate the change window?',
        'What should the platform team validate before approving the next step?'
      ],
      features: [
        'get_cluster_identity',
        'list_cluster_infrastructure',
        'list_projects',
        'list_cluster_version',
        'list_cluster_operators',
        'list_nodes',
        'list_node_pressure',
        'list_machine_config_pools',
        'list_machine_sets',
        'list_operator_subscriptions',
        'list_cluster_service_versions'
      ]
    },
    dr: {
      title: 'Disaster recovery and failover posture',
      summary: 'Review DR policy objects, failover intent, backup posture, and fleet dependencies before an exercise or event.',
      promptLead: 'Act as an OpenShift resiliency lead preparing for a failover, relocate, or recovery exercise. Use the selected evidence to evaluate DR readiness, backup confidence, policy drift, and cross-cluster dependencies with operator-safe recommendations.',
      questions: [
        'Which DR policy, placement, backup, or replication gaps reduce recovery confidence?',
        'Do the current signals support a controlled failover rehearsal?',
        'What should platform and app teams verify before a DR event is declared ready?'
      ],
      features: [
        'get_cluster_identity',
        'list_disaster_recovery_resources',
        'list_oadp_resources',
        'list_acm_managed_clusters',
        'list_acm_policies',
        'list_cluster_logging',
        'list_persistent_storage',
        'list_storage_classes',
        'list_events'
      ]
    },
    migration: {
      title: 'Migration factory readiness',
      summary: 'Inspect application, network, storage, and platform prerequisites before moving workloads or clusters.',
      promptLead: 'Act as an OpenShift migration architect reviewing workload migration readiness. Use the selected evidence to assess storage, routing, fleet governance, virtualization, and delivery dependencies for a migration wave or factory rollout.',
      questions: [
        'Which dependencies would put the next migration wave at risk?',
        'What application, storage, or routing constraints need attention first?',
        'How should the migration sequence be staged to reduce blast radius?'
      ],
      features: [
        'get_cluster_identity',
        'list_projects',
        'list_virtualization_resources',
        'list_pods',
        'list_workload_health',
        'list_services',
        'list_routes',
        'list_ingresses',
        'list_events',
        'list_persistent_storage',
        'list_storage_classes',
        'list_acm_managed_clusters'
      ]
    },
    virtualization: {
      title: 'Virtualization / CNV posture',
      summary: 'Evaluate KubeVirt control-plane health, HyperConverged settings, VM readiness, DataVolume imports, and live migration activity.',
      promptLead: 'Act as an OpenShift Virtualization / CNV platform engineer. Use the selected evidence to review KubeVirt readiness, HyperConverged posture, VM and DataVolume health, live migrations, storage dependencies, and node capacity signals.',
      questions: [
        'Which CNV control-plane or VM signals need action before onboarding more workloads?',
        'Are there any DataVolume or live-migration issues that threaten workload stability?',
        'What are the safest next checks for the virtualization team?'
      ],
      features: [
        'get_cluster_identity',
        'list_virtualization_resources',
        'list_nodes',
        'list_node_pressure',
        'list_pods',
        'list_machine_sets',
        'list_persistent_storage',
        'list_storage_classes',
        'list_workload_health'
      ]
    },
    fleet: {
      title: 'Fleet and platform-pattern review',
      summary: 'Compare fleet-level dependencies, governance, and security rollout signals across managed OpenShift estate patterns.',
      promptLead: 'Act as a fleet platform operations lead reviewing the health of a multi-platform OpenShift estate. Use the selected evidence to compare ACM governance, managed-cluster readiness, platform inventory, backup posture, and security rollout patterns across baremetal, ROSA, ARO, and IBM Z footprints where relevant.',
      questions: [
        'Which fleet-level gaps threaten consistency across platforms?',
        'Where should governance, backup, or security rollout be tightened first?',
        'What handoff should go to platform owners versus security or app teams?'
      ],
      features: [
        'get_cluster_identity',
        'list_cluster_infrastructure',
        'list_projects',
        'list_acm_multicluster_hubs',
        'list_acm_managed_clusters',
        'list_acm_policies',
        'list_oadp_resources',
        'list_acs_central_services',
        'list_acs_secured_clusters',
        'list_oauth_configuration',
        'list_resource_quotas'
      ]
    },
    automation: {
      title: 'Platform automation and day-2 controls',
      summary: 'Check whether GitOps, Tekton, logging, and operator lifecycle signals support safe day-2 engineering.',
      promptLead: 'Act as an OpenShift platform automation lead reviewing day-2 operational controls. Use the selected evidence to assess GitOps, Tekton, logging, backup, and operator lifecycle health before approving further automation or change work.',
      questions: [
        'Which day-2 control gaps increase operational risk?',
        'Are GitOps, delivery, logging, and backup signals aligned enough for the next change window?',
        'What should be stabilized before more automation is rolled out?'
      ],
      features: [
        'get_cluster_identity',
        'list_projects',
        'list_gitops_argocds',
        'list_gitops_applications',
        'list_image_streams',
        'list_builds',
        'list_tekton_configs',
        'list_tekton_pipeline_runs',
        'list_cluster_logging',
        'list_oadp_resources',
        'list_operator_subscriptions',
        'list_cluster_service_versions',
        'list_events'
      ]
    }
  };

  const presetOrder = ['lifecycle', 'dr', 'migration', 'virtualization', 'fleet', 'automation'];
  const defaultProfileKey = 'lifecycle';
  const defaultStatus = 'Select a platform profile, adjust the checks, and run the review.';

  const slugToTitle = (value) => value.replace(/-/g, ' ').replace(/\b\w/g, (char) => char.toUpperCase());

  const safeJsonParse = (value) => {
    if (typeof value !== 'string') {
      return value;
    }
    try {
      return JSON.parse(value);
    } catch {
      return value;
    }
  };

  const summarizeCounts = (payload) => {
    if (!payload || typeof payload !== 'object' || Array.isArray(payload)) {
      return [];
    }
    return Object.entries(payload)
      .filter(([key, value]) => typeof value === 'number' && /count|total|available|failed|degraded|running|active/i.test(key))
      .map(([key, value]) => ({ label: key.replace(/_/g, ' '), value }))
      .slice(0, 6);
  };

  const extractRows = (payload) => {
    if (!payload || typeof payload !== 'object' || Array.isArray(payload)) {
      return [];
    }
    return Object.entries(payload)
      .filter(([, value]) => Array.isArray(value) && value.length)
      .map(([key, value]) => ({ key, rows: value.slice(0, 4) }))
      .slice(0, 3);
  };

  const deriveToolName = (step = {}) => step.tool || step.tool_name || step.name || step.step || 'model-step';

  const deriveToolPayload = (step = {}) => {
    const raw = step.result ?? step.output ?? step.observation ?? step.payload ?? step.data ?? null;
    return safeJsonParse(raw);
  };

  const extractToolCards = (steps = []) => steps
    .filter((step) => deriveToolName(step) !== 'model-step')
    .map((step) => {
      const tool = deriveToolName(step);
      const payload = deriveToolPayload(step);
      const counts = summarizeCounts(payload);
      const rowGroups = extractRows(payload);
      const error = step.error || step.tool_error || null;
      return {
        tool,
        label: featureLabels[tool] || slugToTitle(tool),
        counts,
        rowGroups,
        error,
      };
    });

  const buildReviewPrompt = ({ profile, selectedFeatures, project, clusterScope, concern, recentChange, successCriteria, audience, customPrompt }) => {
    const selectedLabels = selectedFeatures.map((feature) => featureLabels[feature] || slugToTitle(feature));
    const focusNotes = [
      project ? `Primary namespace or project focus: ${project}.` : '',
      clusterScope ? `Cluster scope or estate slice: ${clusterScope}.` : '',
      concern ? `Primary platform concern: ${concern}.` : '',
      recentChange ? `Recent change or expected event: ${recentChange}.` : '',
      successCriteria ? `Success criteria for this review: ${successCriteria}.` : '',
      audience ? `Target audience for the summary: ${audience}.` : '',
      customPrompt ? `Additional operator guidance: ${customPrompt}.` : ''
    ].filter(Boolean);

    return [
      profile.promptLead,
      `Prefer these OpenShift inspection areas and tools where relevant: ${selectedLabels.join('; ')}.`,
      'Return: 1) executive summary, 2) highest-risk blockers or gaps, 3) evidence gathered, 4) blast radius or affected platform patterns, 5) recommended next safe checks, and 6) a clear handoff for the next owner.',
      ...profile.questions.map((question, index) => `${index + 1}. ${question}`),
      ...focusNotes
    ].join('\n\n');
  };

  const buildMarkdownPack = ({ prompt, answer, cards, toolCards }) => {
    const lines = [
      '# OpenShift platform review pack',
      '',
      '## Prompt',
      prompt || 'Not captured.',
      '',
      '## Executive summary',
      answer || 'No answer captured.',
      '',
      '## Summary metrics'
    ];

    if (cards.length) {
      cards.forEach((card) => {
        lines.push(`- **${card.label}:** ${card.value}`);
      });
    } else {
      lines.push('- No summary metrics extracted.');
    }

    lines.push('', '## Evidence trace');
    if (toolCards.length) {
      toolCards.forEach((card) => {
        lines.push(`### ${card.label}`);
        if (card.error) {
          lines.push(`- Error: ${card.error}`);
        }
        if (card.counts.length) {
          card.counts.forEach((entry) => lines.push(`- ${entry.label}: ${entry.value}`));
        }
        if (!card.counts.length && !card.error) {
          lines.push('- Tool ran without count-style metrics.');
        }
        lines.push('');
      });
    } else {
      lines.push('- No tool trace captured.');
    }

    return lines.join('\n');
  };

  const downloadBlob = (filename, blob) => {
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    link.click();
    setTimeout(() => URL.revokeObjectURL(url), 2500);
  };

  const exportCsv = (toolCards) => {
    const header = ['tool', 'metric', 'value'];
    const rows = [header.join(',')];
    toolCards.forEach((card) => {
      if (card.error) {
        rows.push([card.tool, 'error', JSON.stringify(card.error)].join(','));
      }
      card.counts.forEach((entry) => {
        rows.push([card.tool, JSON.stringify(entry.label), entry.value].join(','));
      });
    });
    downloadBlob('platform-review.csv', new Blob([rows.join('\n')], { type: 'text/csv;charset=utf-8' }));
  };

  const exportWord = (markdownPack) => {
    const html = `<!doctype html><html><body><pre>${markdownPack.replace(/[<&>]/g, (char) => ({ '<': '&lt;', '>': '&gt;', '&': '&amp;' }[char]))}</pre></body></html>`;
    downloadBlob('platform-review.doc', new Blob([html], { type: 'application/msword' }));
  };

  const exportPdf = (markdownPack) => {
    const jsPdf = window.jspdf?.jsPDF;
    if (!jsPdf) {
      throw new Error('PDF export is not available in this browser session.');
    }
    const doc = new jsPdf({ unit: 'pt', format: 'a4' });
    const lines = doc.splitTextToSize(markdownPack, 520);
    doc.text(lines, 40, 50);
    doc.save('platform-review.pdf');
  };

  const exportPpt = ({ answer, cards, toolCards }) => {
    const PptxGenJS = window.PptxGenJS;
    if (!PptxGenJS) {
      throw new Error('PowerPoint export is not available in this browser session.');
    }
    const pptx = new PptxGenJS();
    pptx.layout = 'LAYOUT_WIDE';
    const slide = pptx.addSlide();
    slide.addText('OpenShift platform review', { x: 0.4, y: 0.3, w: 12.2, h: 0.4, fontSize: 24, bold: true, color: '0F172A' });
    slide.addText(answer || 'No answer captured.', { x: 0.4, y: 0.85, w: 6, h: 2.8, fontSize: 14, color: '334155', margin: 0.08, valign: 'top' });
    const metricText = cards.length
      ? cards.map((card) => `${card.label}: ${card.value}`).join('\n')
      : 'No summary metrics extracted.';
    slide.addText(metricText, { x: 6.7, y: 0.85, w: 2.7, h: 2.2, fontSize: 13, color: '1D4ED8', bold: true, margin: 0.08, valign: 'top' });
    const traceText = toolCards.length
      ? toolCards.map((card) => `${card.label}\n${card.counts.map((entry) => `• ${entry.label}: ${entry.value}`).join('\n') || '• No count metrics'}`).join('\n\n')
      : 'No tool trace captured.';
    slide.addText(traceText, { x: 9.55, y: 0.85, w: 3.4, h: 5.9, fontSize: 11, color: '475569', margin: 0.08, valign: 'top' });
    pptx.writeFile({ fileName: 'platform-review.pptx' });
  };

  function PlatformConsoleApp() {
    const [providerCatalog, setProviderCatalog] = useState(llmRuntime.fallbackCatalog || { providers: [] });
    const [providerId, setProviderId] = useState('ollama');
    const [ollamaBaseUrl, setOllamaBaseUrl] = useState('');
    const [modelName, setModelName] = useState('');
    const [externalModelName, setExternalModelName] = useState('');
    const [externalBaseUrl, setExternalBaseUrl] = useState('');
    const [externalApiKey, setExternalApiKey] = useState('');
    const [externalApiVersion, setExternalApiVersion] = useState('');
    const [externalOrganization, setExternalOrganization] = useState('');
    const [clusterScope, setClusterScope] = useState('');
    const [project, setProject] = useState('');
    const [kubeContextName, setKubeContextName] = useState('');
    const [openshiftApiUrl, setOpenshiftApiUrl] = useState('');
    const [openshiftToken, setOpenshiftToken] = useState('');
    const [verifySsl, setVerifySsl] = useState(true);
    const [profileKey, setProfileKey] = useState(defaultProfileKey);
    const [selectedFeatures, setSelectedFeatures] = useState(platformProfiles[defaultProfileKey].features);
    const [concern, setConcern] = useState('');
    const [recentChange, setRecentChange] = useState('');
    const [successCriteria, setSuccessCriteria] = useState('');
    const [audience, setAudience] = useState('Change advisory board and platform engineering leads');
    const [customPrompt, setCustomPrompt] = useState('');
    const [status, setStatus] = useState(defaultStatus);
    const [statusTone, setStatusTone] = useState('');
    const [busy, setBusy] = useState(false);
    const [lastRun, setLastRun] = useState({ prompt: '', answer: '', steps: [], runId: null });

    const profile = platformProfiles[profileKey] || platformProfiles[defaultProfileKey];
    const suggestedModels = useMemo(
      () => (llmRuntime.getSuggestedModels ? llmRuntime.getSuggestedModels(providerCatalog, providerId) : []),
      [providerCatalog, providerId]
    );

    useEffect(() => {
      let cancelled = false;
      (async () => {
        const catalog = llmRuntime.fetchProviderCatalog ? await llmRuntime.fetchProviderCatalog() : { providers: [] };
        if (cancelled) {
          return;
        }
        const resolvedProviderId = llmRuntime.normalizeProviderId ? llmRuntime.normalizeProviderId(catalog, catalog.configured_provider || 'ollama') : (catalog.configured_provider || 'ollama');
        setProviderCatalog(catalog);
        setProviderId(resolvedProviderId);
        setOllamaBaseUrl(catalog.configured_base_url || '');
        setModelName(catalog.configured_model_name || '');
      })();
      return () => {
        cancelled = true;
      };
    }, []);

    const prompt = useMemo(() => buildReviewPrompt({
      profile,
      selectedFeatures,
      project,
      clusterScope,
      concern,
      recentChange,
      successCriteria,
      audience,
      customPrompt,
    }), [profile, selectedFeatures, project, clusterScope, concern, recentChange, successCriteria, audience, customPrompt]);

    const toolCards = useMemo(() => extractToolCards(lastRun.steps), [lastRun.steps]);
    const summaryCards = useMemo(() => {
      const flaggedMetrics = toolCards
        .flatMap((card) => card.counts.map((entry) => ({ card, entry })))
        .filter(({ entry }) => /failed|degraded|block|error/i.test(entry.label) && Number(entry.value) > 0);
      const runningMetrics = toolCards
        .flatMap((card) => card.counts.map((entry) => ({ card, entry })))
        .filter(({ entry }) => /available|running|active/i.test(entry.label) && Number(entry.value) > 0);
      return [
        { label: 'Profile', value: profile.title },
        { label: 'Checks selected', value: String(selectedFeatures.length) },
        { label: 'Flagged metrics', value: String(flaggedMetrics.reduce((sum, item) => sum + Number(item.entry.value || 0), 0)) },
        { label: 'Healthy signals', value: String(runningMetrics.reduce((sum, item) => sum + Number(item.entry.value || 0), 0)) }
      ];
    }, [profile.title, selectedFeatures.length, toolCards]);

    const markdownPack = useMemo(() => buildMarkdownPack({
      prompt: lastRun.prompt || prompt,
      answer: lastRun.answer,
      cards: summaryCards,
      toolCards,
    }), [lastRun.prompt, lastRun.answer, prompt, summaryCards, toolCards]);

    const onProfileChange = (event) => {
      const nextProfileKey = event.target.value;
      const nextProfile = platformProfiles[nextProfileKey] || platformProfiles[defaultProfileKey];
      setProfileKey(nextProfileKey);
      setSelectedFeatures(nextProfile.features);
      setStatus(`Loaded ${nextProfile.title}. Adjust the checks and run when ready.`);
      setStatusTone('ok');
    };

    const toggleFeature = (featureId) => {
      setSelectedFeatures((current) => {
        if (current.includes(featureId)) {
          return current.filter((entry) => entry !== featureId);
        }
        return [...current, featureId];
      });
    };

    const resetProfileFeatures = () => {
      setSelectedFeatures(profile.features);
      setStatus(`Reset checks to the ${profile.title} defaults.`);
      setStatusTone('ok');
    };

    const selectAllFeatures = () => {
      setSelectedFeatures(allSelectableFeatures);
      setStatus('Selected the full OpenShift platform check catalog for this review.');
      setStatusTone('ok');
    };

    const clearAllFeatures = () => {
      setSelectedFeatures([]);
      setStatus('Cleared the selected platform checks. Choose the exact OpenShift signals you want to inspect.');
      setStatusTone('ok');
    };

    const runPlatformReview = async () => {
      if (selectedFeatures.length === 0) {
        setStatus('Select at least one platform check before running the review.');
        setStatusTone('error');
        return;
      }

      setBusy(true);
      setStatus('Running platform review via /chat …');
      setStatusTone('');

      try {
        const runtime = {
          ...(llmRuntime.buildLlmRuntime?.({
            provider: providerId,
            ollamaBaseUrl,
            modelName,
            externalModelName,
            externalBaseUrl,
            externalApiKey,
            externalApiVersion,
            externalOrganization,
          }, providerCatalog) || {}),
          cluster_scope: clusterScope.trim() || null,
          kube_context_name: kubeContextName.trim() || null,
          openshift_api_url: openshiftApiUrl.trim() || null,
          openshift_token: openshiftToken || null,
          openshift_namespace: project.trim() || null,
          verify_ssl: verifySsl,
        };

        const response = await fetch('/chat', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ prompt, runtime })
        });
        const payload = await response.json();
        if (!response.ok) {
          throw new Error(payload.detail || `Request failed with status ${response.status}`);
        }
        setLastRun({
          prompt,
          answer: payload.answer || '',
          steps: Array.isArray(payload.steps) ? payload.steps : [],
          runId: payload.run_id || null,
        });
        setStatus(payload.run_id ? `Platform review completed and stored as run #${payload.run_id}.` : 'Platform review completed.');
        setStatusTone('ok');
      } catch (error) {
        setLastRun({ prompt, answer: '', steps: [], runId: null });
        setStatus(error instanceof Error ? error.message : 'Unexpected error while running the platform review.');
        setStatusTone('error');
      } finally {
        setBusy(false);
      }
    };

    const exportHandler = async (kind) => {
      try {
        if (kind === 'csv') {
          exportCsv(toolCards);
        } else if (kind === 'word') {
          exportWord(markdownPack);
        } else if (kind === 'pdf') {
          exportPdf(markdownPack);
        } else if (kind === 'ppt') {
          exportPpt({ answer: lastRun.answer, cards: summaryCards, toolCards });
        }
        setStatus(`Exported ${kind.toUpperCase()} platform review pack.`);
        setStatusTone('ok');
      } catch (error) {
        setStatus(error instanceof Error ? error.message : `Unable to export ${kind}.`);
        setStatusTone('error');
      }
    };

    return h('div', { className: 'platform-console' }, [
      h('section', { className: 'platform-console__hero agent-console__panel', id: 'platform-launcher', key: 'hero' }, [
        h('div', { className: 'platform-console__hero-grid', key: 'hero-grid' }, [
          h('div', { key: 'hero-copy' }, [
            h('span', { className: 'platform-console__eyebrow' }, 'Platform operations runway'),
            h('h2', null, 'Run lifecycle, DR, migration, and CNV readiness reviews from one dedicated console.'),
            h('p', null, 'This page is built for platform engineers who need repo-aligned OpenShift coverage beyond incident troubleshooting: upgrade planning, fleet consistency, DR preparedness, migration waves, and virtualization expansion.'),
            h('ul', null, [
              h('li', { key: 'hero-li-1' }, 'Profiles give you a strong starting point instead of another blank textarea.'),
              h('li', { key: 'hero-li-2' }, 'Feature selection keeps the review grounded in real OpenShift signals and actual toolkit coverage.'),
              h('li', { key: 'hero-li-3' }, 'Exports turn the latest run into a board-friendly or operator-ready handoff pack.')
            ])
          ]),
          h('div', { className: 'platform-console__hero-note', key: 'hero-note' }, [
            h('span', { className: 'platform-console__badge platform-console__badge--ok' }, 'Repo gap closed'),
            h('h3', null, profile.title),
            h('p', null, profile.summary),
            h('p', { className: 'platform-console__meta' }, `Default checks: ${profile.features.map((feature) => featureLabels[feature]).join('; ')}.`)
          ])
        ]),
        h('div', { className: 'platform-console__metrics', key: 'metrics' }, summaryCards.map((card) => h('article', { className: 'platform-console__metric', key: card.label }, [
          h('span', { className: 'platform-console__meta' }, card.label),
          h('strong', null, card.value)
        ]))),
        h('div', { className: `agent-console__status${statusTone ? ` agent-console__status--${statusTone}` : ''}`, key: 'status', role: 'status' }, status)
      ]),
      h('section', { className: 'agent-console__panel', key: 'launcher-form' }, [
        h('div', { className: 'platform-console__toolbar', key: 'toolbar' }, [
          h('label', { className: 'agent-console__label', key: 'profile' }, [
            'Platform review profile',
            h('select', { className: 'agent-console__input', value: profileKey, onChange: onProfileChange }, presetOrder.map((profileId) => h('option', { key: profileId, value: profileId }, platformProfiles[profileId].title)))
          ]),
          h('label', { className: 'agent-console__label', key: 'project' }, [
            'Namespace / project focus',
            h('input', {
              className: 'agent-console__input',
              value: project,
              onChange: (event) => setProject(event.target.value),
              placeholder: 'openshift-dr-system or app namespace'
            })
          ]),
          h('label', { className: 'agent-console__label', key: 'scope' }, [
            'Cluster or estate scope',
            h('input', {
              className: 'agent-console__input',
              value: clusterScope,
              onChange: (event) => setClusterScope(event.target.value),
              placeholder: 'prod-west fleet / aro landing zone / baremetal DR pair'
            })
          ]),
          h('div', { className: 'agent-console__actions', key: 'toolbar-actions' }, [
            h('button', { className: 'agent-console__example', type: 'button', onClick: resetProfileFeatures }, 'Reset checks'),
            h('button', { className: 'agent-console__button', type: 'button', disabled: busy, onClick: runPlatformReview }, busy ? 'Running…' : 'Run platform review')
          ])
        ]),
        h('div', { className: 'platform-console__grid', key: 'details-grid' }, [
          h('label', { className: 'agent-console__label', key: 'concern' }, [
            'Primary concern',
            h('input', {
              className: 'agent-console__input',
              value: concern,
              onChange: (event) => setConcern(event.target.value),
              placeholder: 'upgrade blockers / failover readiness / migration wave risk'
            })
          ]),
          h('label', { className: 'agent-console__label', key: 'recent-change' }, [
            'Recent change or expected event',
            h('input', {
              className: 'agent-console__input',
              value: recentChange,
              onChange: (event) => setRecentChange(event.target.value),
              placeholder: 'new MCO rollout / DR rehearsal / virtualization onboarding'
            })
          ]),
          h('label', { className: 'agent-console__label', key: 'success-criteria' }, [
            'Success criteria',
            h('input', {
              className: 'agent-console__input',
              value: successCriteria,
              onChange: (event) => setSuccessCriteria(event.target.value),
              placeholder: 'zero upgrade blockers and clean DR handoff'
            })
          ]),
          h('label', { className: 'agent-console__label', key: 'audience' }, [
            'Target audience',
            h('input', {
              className: 'agent-console__input',
              value: audience,
              onChange: (event) => setAudience(event.target.value),
              placeholder: 'platform engineering, CAB, or migration squad'
            })
          ])
        ]),
        h('section', { className: 'platform-console__card', key: 'questions' }, [
          h('div', { className: 'agent-console__queue-header' }, [
            h('div', null, [
              h('h3', null, 'Selected platform checks'),
              h('p', { className: 'platform-console__meta' }, 'Choose the exact OpenShift signals to include in this review. The generated prompt names these areas explicitly so the evidence path stays grounded across lifecycle, workloads, security, delivery, fleet, and resiliency surfaces.')
            ]),
            h('span', { className: 'platform-console__pill' }, `${selectedFeatures.length} selected`)
          ]),
          h('div', { className: 'agent-console__actions', key: 'feature-actions' }, [
            h('button', { className: 'agent-console__example', type: 'button', onClick: selectAllFeatures }, 'Select all OpenShift checks'),
            h('button', { className: 'agent-console__example', type: 'button', onClick: clearAllFeatures }, 'Clear checks'),
            h('button', { className: 'agent-console__example', type: 'button', onClick: resetProfileFeatures }, 'Restore profile defaults')
          ]),
          h('div', { className: 'platform-console__feature-group-list' }, platformFeatureGroups.map((group) => h('section', { className: 'platform-console__feature-group', key: group.title }, [
            h('div', { className: 'platform-console__feature-group-header' }, [
              h('h4', null, group.title),
              h('span', { className: 'platform-console__pill' }, `${group.features.filter((featureId) => selectedFeatures.includes(featureId)).length}/${group.features.length}`)
            ]),
            h('div', { className: 'platform-console__feature-list' }, group.features.map((featureId) => h('label', { className: 'platform-console__feature', key: featureId }, [
              h('input', {
                type: 'checkbox',
                checked: selectedFeatures.includes(featureId),
                onChange: () => toggleFeature(featureId)
              }),
              h('span', null, [
                h('span', { className: 'platform-console__feature-label' }, featureLabels[featureId] || slugToTitle(featureId)),
                h('span', { className: 'platform-console__meta' }, `Tool: ${featureId}`)
              ])
            ])))
          ])))
        ]),
        h('section', { className: 'platform-console__card', key: 'prompt-card' }, [
          h('div', { className: 'agent-console__queue-header' }, [
            h('div', null, [
              h('h3', null, 'Prompt builder'),
              h('p', { className: 'platform-console__meta' }, 'Adjust the context below if you want the agent to emphasize a specific change window, dependency set, or handoff audience.')
            ]),
            h('span', { className: 'platform-console__pill' }, 'Live /chat prompt')
          ]),
          h('div', { className: 'platform-console__question-grid' }, profile.questions.map((question) => h('div', { className: 'platform-console__hero-note', key: question }, [
            h('span', { className: 'platform-console__badge' }, 'Review question'),
            h('p', null, question)
          ]))),
          h('label', { className: 'agent-console__label', key: 'custom-prompt' }, [
            'Additional operator guidance',
            h('textarea', {
              className: 'agent-console__textarea',
              rows: 3,
              value: customPrompt,
              onChange: (event) => setCustomPrompt(event.target.value),
              placeholder: 'Optional extra instructions for this platform review.'
            })
          ]),
          h('label', { className: 'agent-console__label', key: 'prompt' }, [
            'Generated review prompt',
            h('textarea', {
              className: 'agent-console__textarea',
              rows: 11,
              value: prompt,
              readOnly: true,
              onKeyDown: (event) => {
                if ((event.metaKey || event.ctrlKey) && event.key === 'Enter') {
                  event.preventDefault();
                  runPlatformReview();
                }
              }
            })
          ])
        ]),
        h('section', { className: 'platform-console__card', key: 'runtime' }, [
          h('div', { className: 'agent-console__queue-header' }, [
            h('div', null, [
              h('h3', null, 'Runtime controls'),
              h('p', { className: 'platform-console__meta' }, 'Same backend, separate platform lane. Adjust provider or cluster overrides here when you need a different target or model.')
            ]),
            h('span', { className: 'platform-console__pill' }, 'Operator context')
          ]),
          h('div', { className: 'platform-console__runtime-grid' }, [
            h('label', { className: 'agent-console__label', key: 'provider' }, [
              'LLM provider',
              h('select', {
                className: 'agent-console__input',
                value: providerId,
                onChange: (event) => setProviderId(event.target.value)
              }, (providerCatalog.providers || []).map((provider) => h('option', { key: provider.id, value: provider.id }, provider.label || provider.id)))
            ]),
            providerId === 'ollama'
              ? h('label', { className: 'agent-console__label', key: 'ollama' }, [
                'Ollama base URL',
                h('input', {
                  className: 'agent-console__input',
                  value: ollamaBaseUrl,
                  onChange: (event) => setOllamaBaseUrl(event.target.value),
                  placeholder: 'http://host.containers.internal:11434'
                })
              ])
              : h('label', { className: 'agent-console__label', key: 'external-base' }, [
                'External base URL',
                h('input', {
                  className: 'agent-console__input',
                  value: externalBaseUrl,
                  onChange: (event) => setExternalBaseUrl(event.target.value),
                  placeholder: 'https://api.openai.com/v1'
                })
              ]),
            h('label', { className: 'agent-console__label', key: 'model' }, [
              providerId === 'ollama' ? 'Local model' : 'Hosted model',
              h('input', {
                className: 'agent-console__input',
                value: providerId === 'ollama' ? modelName : externalModelName,
                list: 'platform-suggested-models',
                onChange: (event) => providerId === 'ollama' ? setModelName(event.target.value) : setExternalModelName(event.target.value),
                placeholder: suggestedModels[0] || 'model name'
              }),
              h('datalist', { id: 'platform-suggested-models' }, suggestedModels.map((model) => h('option', { key: model, value: model })))
            ]),
            h('label', { className: 'agent-console__label', key: 'kube-context' }, [
              'Kube context name',
              h('input', {
                className: 'agent-console__input',
                value: kubeContextName,
                onChange: (event) => setKubeContextName(event.target.value),
                placeholder: 'Optional kube context override'
              })
            ]),
            h('label', { className: 'agent-console__label', key: 'api-url' }, [
              'OpenShift API URL',
              h('input', {
                className: 'agent-console__input',
                value: openshiftApiUrl,
                onChange: (event) => setOpenshiftApiUrl(event.target.value),
                placeholder: 'https://api.cluster.example:6443'
              })
            ]),
            h('label', { className: 'agent-console__label', key: 'token' }, [
              'OpenShift token',
              h('input', {
                className: 'agent-console__input',
                type: 'password',
                value: openshiftToken,
                onChange: (event) => setOpenshiftToken(event.target.value),
                placeholder: 'Optional bearer token'
              })
            ]),
            providerId !== 'ollama' ? h('label', { className: 'agent-console__label', key: 'api-key' }, [
              'Hosted API key',
              h('input', {
                className: 'agent-console__input',
                type: 'password',
                value: externalApiKey,
                onChange: (event) => setExternalApiKey(event.target.value),
                placeholder: 'Optional API key override'
              })
            ]) : null,
            providerId !== 'ollama' ? h('label', { className: 'agent-console__label', key: 'api-version' }, [
              'API version',
              h('input', {
                className: 'agent-console__input',
                value: externalApiVersion,
                onChange: (event) => setExternalApiVersion(event.target.value),
                placeholder: 'Optional API version'
              })
            ]) : null,
            providerId !== 'ollama' ? h('label', { className: 'agent-console__label', key: 'organization' }, [
              'Organization / tenant hint',
              h('input', {
                className: 'agent-console__input',
                value: externalOrganization,
                onChange: (event) => setExternalOrganization(event.target.value),
                placeholder: 'Optional organization hint'
              })
            ]) : null,
            h('label', { className: 'agent-console__label', key: 'verify-ssl' }, [
              h('span', null, 'Verify SSL'),
              h('input', {
                type: 'checkbox',
                checked: verifySsl,
                onChange: (event) => setVerifySsl(event.target.checked)
              })
            ])
          ])
        ])
      ]),
      h('section', { className: 'agent-console__panel', id: 'platform-results', key: 'results' }, [
        h('div', { className: 'agent-console__queue-header' }, [
          h('div', null, [
            h('h2', null, 'Latest platform results'),
            h('p', { className: 'platform-console__meta' }, 'See the summary first, then drill into tool-level evidence if the platform review raised concerns.')
          ]),
          lastRun.runId ? h('span', { className: 'platform-console__badge platform-console__badge--ok' }, `Run #${lastRun.runId}`) : h('span', { className: 'platform-console__badge' }, 'Awaiting first run')
        ]),
        lastRun.answer
          ? h('div', { className: 'platform-console__result-grid', key: 'result-grid' }, [
            h('article', { className: 'platform-console__summary', key: 'answer' }, [
              h('span', { className: 'platform-console__badge platform-console__badge--ok' }, 'Executive summary'),
              h('p', null, lastRun.answer)
            ]),
            h('article', { className: 'platform-console__summary', key: 'metrics-summary' }, [
              h('span', { className: 'platform-console__badge' }, 'At-a-glance'),
              h('ul', null, summaryCards.map((card) => h('li', { key: card.label }, [h('strong', null, `${card.label}: `), String(card.value)])))
            ])
          ])
          : h('div', { className: 'platform-console__empty' }, 'Run a platform review to populate the latest summary and evidence trace.'),
        toolCards.length
          ? h('div', { className: 'platform-console__grid', key: 'tool-cards' }, toolCards.map((card) => h('article', { className: 'platform-console__tool-card', key: card.tool }, [
            h('div', { className: 'agent-console__queue-header' }, [
              h('div', null, [
                h('h3', null, card.label),
                h('p', { className: 'platform-console__meta' }, `Tool: ${card.tool}`)
              ]),
              card.error
                ? h('span', { className: 'platform-console__badge platform-console__badge--warn' }, 'Needs attention')
                : h('span', { className: 'platform-console__badge platform-console__badge--ok' }, 'Evidence captured')
            ]),
            card.error ? h('p', null, card.error) : null,
            card.counts.length ? h('ul', null, card.counts.map((entry) => h('li', { key: `${card.tool}-${entry.label}` }, `${entry.label}: ${entry.value}`))) : h('p', { className: 'platform-console__meta' }, 'No count-style metrics were extracted from this tool response.'),
            card.rowGroups.map((group) => h('details', { key: `${card.tool}-${group.key}` }, [
              h('summary', null, `${group.key.replace(/_/g, ' ')} sample rows`),
              h('pre', null, JSON.stringify(group.rows, null, 2))
            ]))
          ])))
          : null
      ]),
      h('section', { className: 'agent-console__panel', id: 'platform-exports', key: 'exports' }, [
        h('div', { className: 'agent-console__queue-header' }, [
          h('div', null, [
            h('h2', null, 'Export platform handoff pack'),
            h('p', { className: 'platform-console__meta' }, 'Create a quick handoff for change review, DR rehearsal, or migration planning without retyping the summary.')
          ]),
          h('span', { className: 'platform-console__pill' }, 'CSV + PPT + PDF + Word')
        ]),
        h('div', { className: 'platform-console__exports' }, [
          h('article', { className: 'platform-console__card', key: 'export-actions' }, [
            h('h3', null, 'Export formats'),
            h('div', { className: 'agent-console__actions' }, [
              h('button', { className: 'agent-console__button', type: 'button', onClick: () => exportHandler('csv') }, 'Export CSV'),
              h('button', { className: 'agent-console__button', type: 'button', onClick: () => exportHandler('ppt') }, 'Export PPT'),
              h('button', { className: 'agent-console__button', type: 'button', onClick: () => exportHandler('pdf') }, 'Export PDF'),
              h('button', { className: 'agent-console__button', type: 'button', onClick: () => exportHandler('word') }, 'Export Word')
            ])
          ]),
          h('article', { className: 'platform-console__summary', key: 'pack-preview' }, [
            h('h3', null, 'Pack preview'),
            h('pre', null, markdownPack)
          ])
        ])
      ]),
      h('section', { className: 'agent-console__panel', id: 'platform-trace', key: 'trace' }, [
        h('div', { className: 'agent-console__queue-header' }, [
          h('div', null, [
            h('h2', null, 'Evidence trace'),
            h('p', { className: 'platform-console__meta' }, 'The raw step list stays visible so platform teams can verify which evidence sources were actually inspected.')
          ]),
          h('span', { className: 'platform-console__pill' }, `${lastRun.steps.length} steps`)
        ]),
        lastRun.steps.length
          ? h('div', { className: 'platform-console__trace' }, [
            h('table', { className: 'platform-console__step-table' }, [
              h('thead', null, h('tr', null, [
                h('th', null, 'Step'),
                h('th', null, 'Tool'),
                h('th', null, 'Status'),
                h('th', null, 'Highlights')
              ])),
              h('tbody', null, lastRun.steps.map((step, index) => {
                const payload = deriveToolPayload(step);
                const counts = summarizeCounts(payload).map((entry) => `${entry.label}: ${entry.value}`).join('; ');
                return h('tr', { key: `${deriveToolName(step)}-${index}` }, [
                  h('td', null, String(index + 1)),
                  h('td', null, deriveToolName(step)),
                  h('td', null, step.error || step.tool_error ? 'Error' : 'Completed'),
                  h('td', null, counts || (typeof payload === 'string' ? payload.slice(0, 140) : 'Model reasoning or non-count payload'))
                ]);
              }))
            ])
          ])
          : h('div', { className: 'platform-console__empty' }, 'No step trace yet. The first platform review will show each evidence hop here.')
      ])
    ]);
  }

  const reactRoot = window.ReactDOM.createRoot(root);
  reactRoot.render(h(PlatformConsoleApp));
})();
