(() => {
  const root = document.querySelector('[data-openshift-builder]');
  if (!root) return;

  const ARCHITECT_STORAGE_KEY = 'openshift-sre-architect-latest';
  const PROMPT_TEMPLATES = [
    {
      id: 'builder-openshift-implementation',
      group: 'Delivery',
      label: 'OpenShift implementation handoff',
      description: 'Use the latest Architect design to select reusable OpenShift pipelines and generate only confirmed gaps.',
      prompt: 'Act as a Principal Red Hat OpenShift Architect and platform delivery lead. Implement the latest Architect design using reusable catalog pipeline wrappers first. Map each IPI, UPI, ACM, GitOps, DR, ODF, CNV, MTC, ARO, ROSA, IBM Z, disconnected, security, networking, and day-2 requirement to an existing pipeline or template where possible. If a required pipeline is missing, report the gap with rationale, dependencies, security impact, and expected YAML files before generating anything. Only generate missing implementation YAML after explicit confirmation.',
      skills: ['openshift-architecture', 'ipi-upi-delivery', 'acm-gitops-governance', 'review-checklist'],
    },
    {
      id: 'builder-lld-delivery-pack',
      group: 'Architecture handoff',
      label: 'LLD engineering handoff to YAML',
      description: 'Translate implementation-ready LLD details into selected/generated pipeline files.',
      prompt: 'Act as a Principal OpenShift platform engineering reviewer. Translate the latest LLD Architect design into implementation YAML. Preserve cluster names, network CIDRs, VLANs, ingress/egress paths, pull secret and mirror registry assumptions, ACM policies, GitOps apps, ODF or external storage, CNV and migration details, validation steps, and operational handoff notes. Select existing catalog files first, then list any missing YAML with exact file names, dependencies, and validation criteria before generation.',
      skills: ['openshift-lld', 'terraform-delivery', 'azure-pipelines', 'validation-runbook'],
    },
    {
      id: 'builder-disconnected-platform',
      group: 'Disconnected',
      label: 'Disconnected and air-gapped implementation',
      description: 'Focus implementation on mirror registry, pull secrets, release payloads, disconnected operators, and evidence handoff.',
      prompt: 'Act as a Principal OpenShift disconnected-platform architect. Build the implementation plan for the latest disconnected or air-gapped Architect design. Cover mirror registry, ImageContentSourcePolicy or ImageDigestMirrorSet, catalog sources, pull secrets, release image mirroring, proxy/no-proxy, trust bundles, GitOps bootstrap, compliance evidence, day-2 operator lifecycle, and validation gates. Match each control to reusable pipeline assets and report missing controls before generating new YAML.',
      skills: ['disconnected-openshift', 'mirror-registry', 'operator-catalogs', 'security-review'],
    },
    {
      id: 'builder-dr-migration-virtualization',
      group: 'Migration and DR',
      label: 'DR, migration, and virtualization implementation',
      description: 'Focus implementation on ACM DR, ODF/Ceph, MTC, VM migration, and OpenShift Virtualization / CNV.',
      prompt: 'Act as a Principal OpenShift resilience and migration architect. Build the implementation plan for disaster recovery, migration, and virtualization in the latest Architect design. Cover ACM hub/spoke policy, DR placement, ODF or Ceph replication, OADP backups, MTC migration waves, CNV/OpenShift Virtualization, VM import, storage classes, network mappings, validation checkpoints, rollback, and cutover criteria. Select existing catalog pipelines first and identify missing migration or DR modules before generation.',
      skills: ['acm-dr', 'oadp', 'mtc', 'openshift-virtualization'],
    },
  ];

  const llmRuntime = window.AwsSreLlmRuntime || {};
  const $ = (selector) => root.querySelector(selector);
  const $$ = (selector) => root.querySelectorAll(selector);
  const nodes = {
    heroPipelines: $('[data-builder-hero-pipelines]'),
    heroDesign: $('[data-builder-hero-design]'),
    heroLane: $('[data-builder-hero-lane]'),
    provider: $('[data-builder-llm-provider]'),
    providerNote: $('[data-builder-provider-note]'),
    ollamaFields: $$('[data-builder-ollama-field]'),
    externalFields: $$('[data-builder-external-field]'),
    ollamaBaseUrl: $('[data-builder-ollama-base-url]'),
    modelName: $('[data-builder-model-name]'),
    externalModelName: $('[data-builder-external-model-name]'),
    externalBaseUrl: $('[data-builder-external-base-url]'),
    externalApiKey: $('[data-builder-external-api-key]'),
    externalOrganization: $('[data-builder-external-organization]'),
    externalApiVersion: $('[data-builder-external-api-version]'),
    promptTemplate: $('[data-builder-prompt-template]'),
    promptDescription: $('[data-builder-prompt-description]'),
    skillChips: $('[data-builder-skill-chips]'),
    clusterScope: $('[data-builder-cluster-scope]'),
    prompt: $('[data-builder-prompt]'),
    pipelineSelect: $('[data-builder-pipeline-select]'),
    pushToAdo: $('[data-builder-push-to-ado]'),
    status: $('[data-builder-status]'),
    catalogSummary: $('[data-builder-catalog-summary]'),
    designSummary: $('[data-builder-design-summary]'),
    planOutput: $('[data-builder-plan-output]'),
    adoSummary: $('[data-builder-ado-summary]'),
    implementationSummary: $('[data-builder-implementation-summary]'),
    implementationOutput: $('[data-builder-implementation-output]'),
    adoOrgUrl: $('[data-builder-ado-org-url]'),
    adoProject: $('[data-builder-ado-project]'),
    adoRepo: $('[data-builder-ado-repo]'),
    adoBranch: $('[data-builder-ado-branch]'),
    adoTargetDirectory: $('[data-builder-ado-target-directory]'),
    adoPat: $('[data-builder-ado-pat]'),
    confirm: $('[data-builder-confirm]'),
  };

  let providerCatalog = llmRuntime.fallbackCatalog || {
    configured_provider: 'ollama',
    configured_model_name: 'gpt-oss:20b',
    providers: [{ id: 'ollama', label: 'Local Ollama', default_model: 'gpt-oss:20b', default_base_url: 'http://host.containers.internal:11434', description: 'Use the local Ollama runtime already supported by the stack.' }],
  };
  let architectSnapshot = null;

  const escapeHtml = (value = '') => String(value).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#39;');
  const formatNumber = (value) => Number.isFinite(Number(value)) ? new Intl.NumberFormat().format(Number(value)) : '0';
  const selectedPipelineIds = () => Array.from(nodes.pipelineSelect.selectedOptions || []).map((option) => option.value);

  const setStatus = (message, kind = '') => {
    nodes.status.textContent = message;
    nodes.status.className = 'agent-console__status';
    if (kind) nodes.status.classList.add(`agent-console__status--${kind}`);
  };

  const renderMessage = (node, message) => {
    const warning = /unable|failed|error|missing|not found|unavailable/i.test(String(message));
    node.innerHTML = `<div class="agent-console__state${warning ? ' agent-console__state--warning' : ''}"><p class="agent-console__state-title">${warning ? 'Attention needed' : 'Nothing to show yet'}</p><p class="agent-console__state-copy">${escapeHtml(message)}</p></div>`;
  };

  const fetchJson = async (url, options = {}) => {
    const response = await fetch(url, options);
    const payload = await response.json().catch(() => null);
    if (!response.ok) {
      const detail = payload?.detail || payload?.message || `Request failed with status ${response.status}`;
      throw new Error(typeof detail === 'string' ? detail : JSON.stringify(detail));
    }
    return payload;
  };

  const currentProviderId = () => llmRuntime.normalizeProviderId?.(providerCatalog, nodes.provider?.value) || providerCatalog.configured_provider || 'ollama';
  const currentProvider = () => llmRuntime.getProvider?.(providerCatalog, currentProviderId()) || providerCatalog.providers?.[0] || providerCatalog.providers[0];

  const syncProviderVisibility = () => {
    const provider = currentProvider();
    const useExternal = provider.id !== 'ollama';
    nodes.ollamaFields.forEach((node) => { node.hidden = useExternal; });
    nodes.externalFields.forEach((node) => { node.hidden = !useExternal; });
    nodes.providerNote.textContent = provider.description || 'OpenShift Builder can use the same local Ollama runtime or external providers supported by the Architect workspace.';
    if (!useExternal) {
      if (!nodes.ollamaBaseUrl.value.trim()) nodes.ollamaBaseUrl.value = provider.default_base_url || providerCatalog.configured_base_url || 'http://host.containers.internal:11434';
      if (!nodes.modelName.value.trim()) nodes.modelName.value = provider.default_model || providerCatalog.configured_model_name || 'gpt-oss:20b';
    } else {
      if (!nodes.externalModelName.value.trim() && provider.default_model) nodes.externalModelName.value = provider.default_model;
      if (!nodes.externalBaseUrl.value.trim() && provider.default_base_url) nodes.externalBaseUrl.value = provider.default_base_url;
      if (!nodes.externalApiVersion.value.trim() && provider.default_api_version) nodes.externalApiVersion.value = provider.default_api_version;
    }
  };

  const buildRuntimePayload = () => {
    const runtime = llmRuntime.buildLlmRuntime?.({
      provider: currentProviderId(),
      ollamaBaseUrl: nodes.ollamaBaseUrl.value,
      modelName: nodes.modelName.value,
      externalModelName: nodes.externalModelName.value,
      externalBaseUrl: nodes.externalBaseUrl.value,
      externalApiKey: nodes.externalApiKey.value,
      externalOrganization: nodes.externalOrganization.value,
      externalApiVersion: nodes.externalApiVersion.value,
      ollamaValidationMode: currentProviderId() === 'ollama' ? 'required' : 'optional',
    }, providerCatalog) || { llm_provider: currentProviderId() };
    if (nodes.clusterScope.value.trim()) {
      runtime.openshift_cluster = nodes.clusterScope.value.trim();
      runtime.cluster_scope = nodes.clusterScope.value.trim();
    }
    return runtime;
  };

  const buildAdoPayload = () => ({
    organization_url: nodes.adoOrgUrl.value.trim(),
    project: nodes.adoProject.value.trim(),
    repository: nodes.adoRepo.value.trim(),
    branch: nodes.adoBranch.value.trim() || 'develop',
    target_directory: nodes.adoTargetDirectory.value.trim() || '/pipelines/generated/openshift',
    pat: nodes.adoPat.value,
  });
  const hasAdoCredentials = () => Boolean(nodes.adoOrgUrl.value.trim() && nodes.adoProject.value.trim() && nodes.adoPat.value.trim());

  const applyPromptTemplate = (templateId = nodes.promptTemplate.value) => {
    const template = PROMPT_TEMPLATES.find((item) => item.id === templateId) || PROMPT_TEMPLATES[0];
    nodes.promptTemplate.value = template.id;
    nodes.prompt.value = template.prompt;
    nodes.promptDescription.textContent = template.description;
    nodes.heroLane.textContent = template.label;
    nodes.skillChips.innerHTML = template.skills.map((skill) => `<span class="agent-console__history-badge">${escapeHtml(skill)}</span>`).join('');
  };

  const renderPromptTemplateOptions = () => {
    const groups = [...new Set(PROMPT_TEMPLATES.map((template) => template.group))];
    nodes.promptTemplate.innerHTML = groups.map((group) => `<optgroup label="${escapeHtml(group)}">${PROMPT_TEMPLATES.filter((template) => template.group === group).map((template) => `<option value="${escapeHtml(template.id)}">${escapeHtml(template.label)}</option>`).join('')}</optgroup>`).join('');
  };

  const applyUiDefaults = (payload) => {
    const defaults = payload?.defaults || {};
    const ado = defaults.ado || {};
    if (!nodes.clusterScope.value.trim() && (defaults.openshift_cluster || defaults.cluster_scope)) nodes.clusterScope.value = defaults.openshift_cluster || defaults.cluster_scope;
    if (!nodes.adoOrgUrl.value.trim() && ado.organization_url) nodes.adoOrgUrl.value = ado.organization_url;
    if (!nodes.adoProject.value.trim() && ado.project) nodes.adoProject.value = ado.project;
    if (!nodes.adoRepo.value.trim() && ado.repository) nodes.adoRepo.value = ado.repository;
    if (!nodes.adoBranch.value.trim() && ado.branch) nodes.adoBranch.value = ado.branch;
    if (!nodes.adoTargetDirectory.value.trim() && ado.target_directory) nodes.adoTargetDirectory.value = ado.target_directory;
  };

  const renderCatalog = (payload) => {
    const pipelines = Array.isArray(payload?.pipelines) ? payload.pipelines : [];
    nodes.pipelineSelect.innerHTML = pipelines.map((item) => `<option value="${escapeHtml(item.id)}">${escapeHtml(item.title)} — ${escapeHtml(item.relative_path)}${item.source_root ? ` (${escapeHtml(item.source_root)})` : ''}</option>`).join('');
    nodes.heroPipelines.textContent = formatNumber(pipelines.length);
    applyUiDefaults(payload);
    nodes.catalogSummary.innerHTML = `<section class="agent-console__table-block"><div class="agent-console__history-card-grid"><article class="agent-console__history-card"><p class="agent-console__history-card-label">Pipelines</p><p class="agent-console__history-card-value">${escapeHtml(formatNumber(payload?.counts?.pipeline_count || 0))}</p></article><article class="agent-console__history-card"><p class="agent-console__history-card-label">Templates</p><p class="agent-console__history-card-value">${escapeHtml(formatNumber(payload?.counts?.template_count || 0))}</p></article><article class="agent-console__history-card"><p class="agent-console__history-card-label">Variable files</p><p class="agent-console__history-card-value">${escapeHtml(formatNumber(payload?.counts?.variable_file_count || 0))}</p></article><article class="agent-console__history-card"><p class="agent-console__history-card-label">Source roots</p><p class="agent-console__history-card-value">${escapeHtml(formatNumber((payload?.source_roots || []).length))}</p></article></div><p class="agent-console__meta">Source roots: ${(payload?.source_roots || []).map((rootPath) => `<code>${escapeHtml(rootPath)}</code>`).join(', ') || 'none discovered'}.</p></section>`;
    if (!pipelines.length) renderMessage(nodes.planOutput, 'No OpenShift delivery pipelines were discovered. Set OPENSHIFT_BUILDER_SOURCE_PATHS or keep pipeline YAML under this repository.');
  };

  const renderArchitectSummary = () => {
    if (!architectSnapshot) {
      nodes.heroDesign.textContent = 'Not loaded';
      renderMessage(nodes.designSummary, 'No Architect design loaded yet. Generate a diagram in Architect first, then load it here.');
      return;
    }
    const planning = architectSnapshot.planning || {};
    const diagram = architectSnapshot.diagram || {};
    nodes.heroDesign.textContent = planning.pattern_label || planning.pattern_id || 'Loaded';
    nodes.designSummary.innerHTML = `<section class="agent-console__table-block"><div class="agent-console__history-card-grid"><article class="agent-console__history-card"><p class="agent-console__history-card-label">Pattern</p><p class="agent-console__history-card-value">${escapeHtml(planning.pattern_label || planning.pattern_id || 'Custom OpenShift architecture')}</p></article><article class="agent-console__history-card"><p class="agent-console__history-card-label">Cluster</p><p class="agent-console__history-card-value">${escapeHtml(architectSnapshot.cluster_scope || '—')}</p></article><article class="agent-console__history-card"><p class="agent-console__history-card-label">Nodes</p><p class="agent-console__history-card-value">${escapeHtml(formatNumber((diagram.nodes || []).length))}</p></article><article class="agent-console__history-card"><p class="agent-console__history-card-label">Edges</p><p class="agent-console__history-card-value">${escapeHtml(formatNumber((diagram.edges || []).length))}</p></article></div><p class="agent-console__meta">${escapeHtml(planning.reasoning_summary || architectSnapshot.prompt || 'Loaded the latest Architect snapshot from browser storage.')}</p></section>`;
  };

  const renderPlan = (payload) => {
    const recommended = Array.isArray(payload?.recommended_pipeline_ids) ? payload.recommended_pipeline_ids : [];
    const missing = Array.isArray(payload?.missing_requirements) ? payload.missing_requirements : [];
    recommended.forEach((itemId) => {
      const option = nodes.pipelineSelect.querySelector(`option[value="${CSS.escape(itemId)}"]`);
      if (option) option.selected = true;
    });
    nodes.planOutput.innerHTML = `<section class="agent-console__table-block"><div class="agent-console__history-card-grid"><article class="agent-console__history-card"><p class="agent-console__history-card-label">Recommendation source</p><p class="agent-console__history-card-value">${escapeHtml(payload?.recommendation_source || 'heuristic')}</p></article><article class="agent-console__history-card"><p class="agent-console__history-card-label">Recommended pipelines</p><p class="agent-console__history-card-value">${escapeHtml(formatNumber(recommended.length))}</p></article><article class="agent-console__history-card"><p class="agent-console__history-card-label">Missing requirements</p><p class="agent-console__history-card-value">${escapeHtml(formatNumber(missing.length))}</p></article><article class="agent-console__history-card"><p class="agent-console__history-card-label">History run</p><p class="agent-console__history-card-value">${payload?.run_id ? `#${escapeHtml(String(payload.run_id))}` : 'not stored'}</p></article></div><p class="agent-console__meta">${escapeHtml(payload?.reasoning_summary || 'Builder analyzed the latest design and catalog inventory.')}</p></section><section class="agent-console__table-block"><div class="agent-console__cards"><article class="agent-console__card agent-console__card--ok"><h3>Recommended pipeline ids</h3><pre>${escapeHtml(recommended.join('\n') || 'No matching catalog pipelines were recommended.')}</pre></article><article class="agent-console__card ${missing.length ? 'agent-console__card--warn' : 'agent-console__card--neutral'}"><h3>Missing requirements</h3><pre>${escapeHtml(missing.join('\n') || 'No missing pipeline requirements detected.')}</pre></article></div></section>`;
  };

  const renderAdoSummary = (payload) => {
    const repositories = Array.isArray(payload?.repositories) ? payload.repositories : [];
    const pipelineCount = Number(payload?.pipeline_count ?? payload?.catalog?.counts?.pipeline_count ?? 0);
    nodes.adoSummary.innerHTML = `<section class="agent-console__table-block"><div class="agent-console__history-card-grid"><article class="agent-console__history-card"><p class="agent-console__history-card-label">Organization</p><p class="agent-console__history-card-value">${escapeHtml(payload?.organization_url || '—')}</p></article><article class="agent-console__history-card"><p class="agent-console__history-card-label">Project</p><p class="agent-console__history-card-value">${escapeHtml(payload?.project || '—')}</p></article><article class="agent-console__history-card"><p class="agent-console__history-card-label">Repositories</p><p class="agent-console__history-card-value">${escapeHtml(formatNumber(payload?.repository_count || 0))}</p></article><article class="agent-console__history-card"><p class="agent-console__history-card-label">Branch</p><p class="agent-console__history-card-value">${escapeHtml(payload?.branch || 'develop')}</p></article><article class="agent-console__history-card"><p class="agent-console__history-card-label">ADO pipelines loaded</p><p class="agent-console__history-card-value">${escapeHtml(formatNumber(pipelineCount))}</p></article></div><p class="agent-console__meta">${repositories.length ? `Visible repositories: ${repositories.map((repo) => escapeHtml(repo.name || repo.id || 'repo')).join(', ')}.` : 'Authentication succeeded, but no repositories were returned.'}</p></section>`;
  };

  const renderImplementation = (payload) => {
    const selectedPipelines = Array.isArray(payload?.selected_pipelines) ? payload.selected_pipelines : [];
    const generatedFiles = Array.isArray(payload?.generated_files || payload?.generation_preview) ? (payload.generated_files || payload.generation_preview) : [];
    const pushFiles = Array.isArray(payload?.ado_push?.files) ? payload.ado_push.files : [];
    const missing = Array.isArray(payload?.missing_requirements) ? payload.missing_requirements : [];
    nodes.implementationSummary.innerHTML = `<section class="agent-console__table-block"><div class="agent-console__history-card-grid"><article class="agent-console__history-card"><p class="agent-console__history-card-label">Selected pipelines</p><p class="agent-console__history-card-value">${escapeHtml(formatNumber(selectedPipelines.length))}</p></article><article class="agent-console__history-card"><p class="agent-console__history-card-label">Generated files</p><p class="agent-console__history-card-value">${escapeHtml(formatNumber(generatedFiles.length))}</p></article><article class="agent-console__history-card"><p class="agent-console__history-card-label">ADO push</p><p class="agent-console__history-card-value">${escapeHtml(payload?.ado_push?.performed ? 'Requested' : 'Skipped')}</p></article><article class="agent-console__history-card"><p class="agent-console__history-card-label">History run</p><p class="agent-console__history-card-value">${payload?.run_id ? `#${escapeHtml(String(payload.run_id))}` : 'not stored'}</p></article></div><p class="agent-console__meta">${escapeHtml(payload?.message || 'Builder prepared the implementation payload.')}</p></section>`;
    nodes.implementationOutput.innerHTML = `<div class="agent-console__cards">${selectedPipelines.map((item) => `<article class="agent-console__card agent-console__card--neutral"><h3>${escapeHtml(item.title || item.id)}</h3><p class="agent-console__meta">${escapeHtml(item.relative_path || '')}</p><pre>${escapeHtml(item.content || item.content_preview || '')}</pre></article>`).join('')}${generatedFiles.map((item) => `<article class="agent-console__card agent-console__card--ok"><h3>${escapeHtml(item.path || 'generated-file.yml')}</h3><p class="agent-console__meta">${escapeHtml(item.requirement || item.kind || 'generated')}</p><pre>${escapeHtml(item.content || '')}</pre></article>`).join('')}</div>${missing.length ? `<section class="agent-console__table-block"><h4>Missing requirements</h4><pre>${escapeHtml(missing.join('\n'))}</pre></section>` : ''}${pushFiles.length ? `<section class="agent-console__table-block"><h4>Azure DevOps push result</h4><table class="agent-console__table"><thead><tr><th>Path</th><th>Repository</th><th>Branch</th><th>Push ID</th></tr></thead><tbody>${pushFiles.map((item) => `<tr><td>${escapeHtml(item.path || '—')}</td><td>${escapeHtml(item.repository || '—')}</td><td>${escapeHtml(item.branch || '—')}</td><td>${escapeHtml(String(item.push_id || '—'))}</td></tr>`).join('')}</tbody></table></section>` : ''}`;
  };

  const loadProviderCatalog = async () => {
    providerCatalog = await (llmRuntime.fetchProviderCatalog?.() || Promise.resolve(providerCatalog));
    nodes.provider.innerHTML = (providerCatalog.providers || []).map((provider) => `<option value="${escapeHtml(provider.id)}">${escapeHtml(provider.label)}</option>`).join('');
    nodes.provider.value = currentProviderId();
    syncProviderVisibility();
  };

  const loadCatalog = async ({ silent = false } = {}) => {
    try {
      if (!silent) setStatus('Refreshing the OpenShift delivery catalog…');
      const payload = await fetchJson('/builder/catalog');
      renderCatalog(payload);
      if (!silent) setStatus('OpenShift delivery catalog refreshed.', 'ok');
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Unable to load the OpenShift delivery catalog.';
      renderMessage(nodes.catalogSummary, message);
      setStatus(message, 'error');
    }
  };

  const loadArchitectDesign = () => {
    try {
      const raw = window.localStorage.getItem(ARCHITECT_STORAGE_KEY);
      const parsed = raw ? JSON.parse(raw) : null;
      architectSnapshot = parsed?.diagramPayload || parsed;
    } catch {
      architectSnapshot = null;
    }
    renderArchitectSummary();
    setStatus(architectSnapshot ? 'Loaded the latest Architect design snapshot into OpenShift Builder.' : 'No Architect snapshot is available yet. Generate a diagram in Architect first.', architectSnapshot ? 'ok' : 'error');
  };

  const analyzeDesign = async () => {
    try {
      setStatus('Matching the latest design to the discovered OpenShift delivery pipelines…');
      const payload = await fetchJson('/builder/design/plan', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ prompt: nodes.prompt.value.trim(), runtime: buildRuntimePayload(), design_snapshot: architectSnapshot, selected_pipeline_ids: selectedPipelineIds(), ado: hasAdoCredentials() ? buildAdoPayload() : null }) });
      renderPlan(payload);
      setStatus('OpenShift Builder recommended the best matching pipelines for the current design.', 'ok');
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Unable to analyze the latest design.';
      renderMessage(nodes.planOutput, message);
      setStatus(message, 'error');
    }
  };

  const authenticateAdo = async () => {
    try {
      setStatus('Validating Azure DevOps access…');
      const payload = await fetchJson('/builder/ado/auth', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(buildAdoPayload()) });
      renderAdoSummary(payload);
      if (payload.catalog) renderCatalog(payload.catalog);
      const pipelineCount = Number(payload?.pipeline_count ?? payload?.catalog?.counts?.pipeline_count ?? 0);
      setStatus(`Azure DevOps authentication succeeded${pipelineCount ? ` and loaded ${formatNumber(pipelineCount)} pipeline(s)` : ', but no YAML-backed pipelines were returned'}.`, 'ok');
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Unable to validate Azure DevOps access.';
      renderMessage(nodes.adoSummary, message);
      setStatus(message, 'error');
    }
  };

  const executeImplementation = async ({ confirmGenerateMissing = false } = {}) => {
    try {
      const request = { prompt: nodes.prompt.value.trim(), runtime: buildRuntimePayload(), design_snapshot: architectSnapshot, selected_pipeline_ids: selectedPipelineIds(), ado: hasAdoCredentials() ? buildAdoPayload() : null, push_to_ado: nodes.pushToAdo.checked, confirm_generate_missing: confirmGenerateMissing };
      setStatus(confirmGenerateMissing ? 'Generating the missing pipeline files and continuing implementation…' : 'Implementing the selected OpenShift delivery pipelines…');
      const payload = await fetchJson('/builder/implement', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(request) });
      renderImplementation(payload);
      nodes.confirm.hidden = !payload.confirmation_required;
      setStatus(payload.confirmation_required ? 'Builder found missing pipeline requirements. Review and confirm generation if you want Builder to create YAML.' : 'OpenShift Builder completed the implementation flow.', payload.confirmation_required ? 'error' : 'ok');
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Unable to implement the selected OpenShift delivery pipelines.';
      renderMessage(nodes.implementationSummary, message);
      renderMessage(nodes.implementationOutput, message);
      nodes.confirm.hidden = true;
      setStatus(message, 'error');
    }
  };

  nodes.provider?.addEventListener('change', syncProviderVisibility);
  nodes.promptTemplate?.addEventListener('change', () => applyPromptTemplate());
  $('[data-builder-refresh-catalog]')?.addEventListener('click', () => loadCatalog());
  $('[data-builder-load-architect]')?.addEventListener('click', loadArchitectDesign);
  $('[data-builder-analyze]')?.addEventListener('click', analyzeDesign);
  $('[data-builder-authenticate]')?.addEventListener('click', authenticateAdo);
  $('[data-builder-implement]')?.addEventListener('click', () => executeImplementation());
  nodes.confirm?.addEventListener('click', () => executeImplementation({ confirmGenerateMissing: true }));

  renderPromptTemplateOptions();
  applyPromptTemplate('builder-openshift-implementation');
  renderMessage(nodes.planOutput, 'Pipeline recommendations will appear here after analysis.');
  renderMessage(nodes.adoSummary, 'No Azure DevOps validation has been performed yet.');
  renderMessage(nodes.implementationOutput, 'Selected pipeline content, generated YAML, and Azure DevOps push details will appear here.');
  renderArchitectSummary();
  loadProviderCatalog();
  loadCatalog({ silent: true });
})();
