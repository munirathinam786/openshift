(() => {
  const root = document.querySelector('[data-watchlists]');
  if (!root) return;

  const llmRuntime = window.OpenShiftSreLlmRuntime || window.AwsSreLlmRuntime || {};

  const investigationName = root.querySelector('[data-investigation-name]');
  const investigationCategory = root.querySelector('[data-investigation-category]');
  const investigationRegions = root.querySelector('[data-investigation-regions]');
  const investigationTags = root.querySelector('[data-investigation-tags]');
  const investigationPrompt = root.querySelector('[data-investigation-prompt]');
  const investigationSave = root.querySelector('[data-investigation-save]');
  const investigationStatus = root.querySelector('[data-investigation-status]');
  const investigationList = root.querySelector('[data-investigation-list]');
  const investigationSelect = root.querySelector('[data-watchlist-investigation]');

  const watchlistName = root.querySelector('[data-watchlist-name]');
  const watchlistRegions = root.querySelector('[data-watchlist-regions]');
  const watchlistRoles = root.querySelector('[data-watchlist-roles]');
  const watchlistNotes = root.querySelector('[data-watchlist-notes]');
  const watchlistSave = root.querySelector('[data-watchlist-save]');
  const watchlistStatus = root.querySelector('[data-watchlist-status]');
  const watchlistList = root.querySelector('[data-watchlist-list]');
  const watchlistResults = root.querySelector('[data-watchlist-results]');
  const llmProviderInput = root.querySelector('[data-watchlist-llm-provider]');
  const ollamaBaseUrlInput = root.querySelector('[data-watchlist-ollama-base-url]');
  const modelNameInput = root.querySelector('[data-watchlist-model-name]');
  const externalModelNameInput = root.querySelector('[data-watchlist-external-model-name]');
  const externalBaseUrlInput = root.querySelector('[data-watchlist-external-base-url]');
  const externalApiKeyInput = root.querySelector('[data-watchlist-external-api-key]');
  const externalApiVersionInput = root.querySelector('[data-watchlist-external-api-version]');
  const externalOrganizationInput = root.querySelector('[data-watchlist-external-organization]');
  const kubeContextInput = root.querySelector('[data-watchlist-kube-context]');
  const openshiftApiUrlInput = root.querySelector('[data-watchlist-openshift-api-url]');
  const openshiftTokenInput = root.querySelector('[data-watchlist-openshift-token]');
  const openshiftNamespaceInput = root.querySelector('[data-watchlist-openshift-namespace]');
  const verifySslInput = root.querySelector('[data-watchlist-verify-ssl]');
  const providerNote = root.querySelector('[data-watchlist-llm-provider-note]');
  const ollamaFields = root.querySelectorAll('[data-watchlist-ollama-field]');
  const externalFields = root.querySelectorAll('[data-watchlist-external-llm-field]');
  let providerCatalog = llmRuntime.fallbackCatalog || {
    configured_provider: 'ollama',
    configured_model_name: 'gpt-oss:20b',
    providers: [{ id: 'ollama', label: 'Local Ollama', default_model: 'gpt-oss:20b', default_base_url: 'http://localhost:11434', description: 'Use the local Ollama runtime already supported by the stack.', supports_catalog_refresh: true, suggested_models: ['gpt-oss:20b'] }]
  };

  function parseCsv(value) {
    return value.split(',').map((item) => item.trim()).filter(Boolean);
  }

  function parseLines(value) {
    return value.split('\n').map((item) => item.trim()).filter(Boolean);
  }

  function setMessage(element, message, tone = 'info') {
    element.textContent = message;
    element.dataset.tone = tone;
  }

  function currentProviderId() {
    return llmRuntime.normalizeProviderId?.(providerCatalog, llmProviderInput?.value) || 'ollama';
  }

  function currentProvider() {
    return llmRuntime.getProvider?.(providerCatalog, currentProviderId()) || providerCatalog.providers?.[0] || { id: 'ollama', label: 'Local Ollama', default_model: 'gpt-oss:20b', default_base_url: 'http://localhost:11434' };
  }

  function renderProviderOptions() {
    if (!llmProviderInput) return;
    llmProviderInput.innerHTML = (providerCatalog.providers || []).map((provider) => `<option value="${provider.id}">${provider.label}</option>`).join('');
    llmProviderInput.value = currentProviderId();
  }

  function renderModelOptions(catalog = null) {
    if (!modelNameInput) return;
    const currentValue = modelNameInput.value || currentProvider().default_model || providerCatalog.configured_model_name || 'gpt-oss:20b';
    const options = new Map();
    for (const model of (catalog?.models || [])) {
      const name = model?.name || model?.model;
      if (name) {
        options.set(name, name);
      }
    }
    options.set(currentValue, currentValue);
    modelNameInput.innerHTML = Array.from(options.entries()).map(([value, label]) => `<option value="${value}">${label}</option>`).join('');
    modelNameInput.value = currentValue;
  }

  function syncProviderFields() {
    const provider = currentProvider();
    const useExternal = provider.id !== 'ollama';
    ollamaFields.forEach((node) => { node.hidden = useExternal; });
    externalFields.forEach((node) => { node.hidden = !useExternal; });
    if (providerNote) {
      providerNote.textContent = provider.description || 'Manual watchlist runs can use the local Ollama model or a supported external provider.';
    }
    if (useExternal) {
      if (externalModelNameInput && !externalModelNameInput.value.trim()) {
        externalModelNameInput.value = provider.default_model || '';
      }
      if (externalBaseUrlInput && !externalBaseUrlInput.value.trim() && provider.default_base_url) {
        externalBaseUrlInput.value = provider.default_base_url;
      }
      if (externalApiVersionInput && !externalApiVersionInput.value.trim() && provider.default_api_version) {
        externalApiVersionInput.value = provider.default_api_version;
      }
    }
  }

  async function loadProviderCatalog() {
    providerCatalog = await (llmRuntime.fetchProviderCatalog?.() || Promise.resolve(providerCatalog));
    renderProviderOptions();
    syncProviderFields();
  }

  async function loadOllamaModels(silent = true) {
    if (!modelNameInput || currentProviderId() !== 'ollama') {
      return;
    }
    try {
      const params = new URLSearchParams();
      if (ollamaBaseUrlInput?.value.trim()) {
        params.set('ollama_base_url', ollamaBaseUrlInput.value.trim());
      }
      const response = await fetch(`/ollama/models${params.toString() ? `?${params}` : ''}`);
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.detail || 'Unable to load Ollama models');
      renderModelOptions(payload);
      if (!silent) setMessage(watchlistStatus, `Loaded ${payload.model_count || 0} Ollama model option(s).`, 'ok');
    } catch (error) {
      renderModelOptions();
      if (!silent) setMessage(watchlistStatus, error.message || 'Unable to load Ollama models.', 'error');
    }
  }

  function buildRuntime() {
    return {
      ...(llmRuntime.buildLlmRuntime?.({
        provider: currentProviderId(),
        ollamaBaseUrl: ollamaBaseUrlInput?.value.trim() || '',
        modelName: modelNameInput?.value.trim() || '',
        externalModelName: externalModelNameInput?.value.trim() || '',
        externalBaseUrl: externalBaseUrlInput?.value.trim() || '',
        externalApiKey: externalApiKeyInput?.value || '',
        externalApiVersion: externalApiVersionInput?.value.trim() || '',
        externalOrganization: externalOrganizationInput?.value.trim() || '',
      }, providerCatalog) || {}),
      ...(kubeContextInput?.value.trim() ? { kube_context_name: kubeContextInput.value.trim() } : {}),
      ...(openshiftApiUrlInput?.value.trim() ? { openshift_api_url: openshiftApiUrlInput.value.trim() } : {}),
      ...(openshiftTokenInput?.value ? { openshift_token: openshiftTokenInput.value } : {}),
      ...(openshiftNamespaceInput?.value ? { openshift_namespace: openshiftNamespaceInput.value } : {}),
      ...(verifySslInput ? { verify_ssl: verifySslInput.checked } : {}),
    };
  }

  function optionMarkup(investigation) {
    return `<option value="${investigation.id}">${investigation.name} · ${investigation.category}</option>`;
  }

  function investigationCard(investigation) {
    return `
      <article class="agent-console__history-card">
        <div class="agent-console__history-badge-row">
          <span class="agent-console__history-badge">${investigation.category}</span>
          <span class="agent-console__history-badge">${(investigation.default_regions || []).join(', ') || 'default scope'}</span>
        </div>
        <h3>${investigation.name}</h3>
        <p>${investigation.description || 'No description provided yet.'}</p>
        <p class="agent-console__meta">Tags: ${(investigation.default_tags || []).join(', ') || 'none'}</p>
        <details>
          <summary>Prompt</summary>
          <pre>${investigation.prompt}</pre>
        </details>
      </article>
    `;
  }

  function watchlistCard(watchlist) {
    const investigation = watchlist.investigation || {};
    return `
      <article class="agent-console__history-card agent-console__history-card--timeline">
        <div class="agent-console__history-badge-row">
          <span class="agent-console__history-badge">${watchlist.enabled ? 'enabled' : 'disabled'}</span>
          <span class="agent-console__history-badge">${watchlist.schedule_hint || 'manual'}</span>
        </div>
        <h3>${watchlist.name}</h3>
        <p>${investigation.name || 'No saved investigation linked.'}</p>
        <p class="agent-console__meta">Cluster scopes: ${(watchlist.regions || []).join(', ') || 'inherit from investigation / runtime'}</p>
        <p class="agent-console__meta">Execution contexts: ${(watchlist.role_arns || []).length || 0} configured</p>
        <p class="agent-console__meta">Last run: ${watchlist.last_run_at || 'never'}</p>
        <div class="agent-console__actions">
          <button class="agent-console__button agent-console__button--secondary" type="button" data-watchlist-run-id="${watchlist.id}">Run now</button>
        </div>
      </article>
    `;
  }

  function runResultMarkup(result) {
    return `
      <details class="agent-console__history-card agent-console__history-card--detail">
        <summary>${result.region} · ${result.role_arn || 'current execution context'} · run ${result.run_id || 'n/a'}</summary>
        <p class="agent-console__meta">Confidence: ${result.confidence ?? '—'}</p>
        <pre>${result.answer || 'No answer returned.'}</pre>
      </details>
    `;
  }

  async function loadInvestigations() {
    const response = await fetch('/investigations');
    const payload = await response.json();
    const items = payload.items || [];
    investigationList.innerHTML = items.length
      ? items.map(investigationCard).join('')
      : '<p class="agent-console__meta">No saved investigations yet.</p>';
    investigationSelect.innerHTML = items.length
      ? items.map(optionMarkup).join('')
      : '<option value="">No saved investigations yet</option>';
    return items;
  }

  async function loadWatchlists() {
    const response = await fetch('/watchlists');
    const payload = await response.json();
    const items = payload.items || [];
    watchlistList.innerHTML = items.length
      ? items.map(watchlistCard).join('')
      : '<p class="agent-console__meta">No watchlists yet.</p>';
  }

  async function refreshAll() {
    await loadInvestigations();
    await loadWatchlists();
  }

  investigationSave.addEventListener('click', async () => {
    setMessage(investigationStatus, 'Saving investigation…', 'pending');
    try {
      const response = await fetch('/investigations', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: investigationName.value.trim(),
          category: investigationCategory.value.trim() || 'general',
          prompt: investigationPrompt.value.trim(),
          default_regions: parseCsv(investigationRegions.value),
          default_tags: parseCsv(investigationTags.value)
        })
      });
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.detail || 'Unable to save investigation');
      setMessage(investigationStatus, `Saved investigation “${payload.name}”.`, 'ok');
      await refreshAll();
    } catch (error) {
      setMessage(investigationStatus, error.message || 'Unable to save investigation.', 'error');
    }
  });

  watchlistSave.addEventListener('click', async () => {
    setMessage(watchlistStatus, 'Saving watchlist…', 'pending');
    try {
      const response = await fetch('/watchlists', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: watchlistName.value.trim(),
          investigation_id: Number(investigationSelect.value),
          regions: parseCsv(watchlistRegions.value),
          role_arns: parseLines(watchlistRoles.value),
          notes: watchlistNotes.value.trim()
        })
      });
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.detail || 'Unable to save watchlist');
      setMessage(watchlistStatus, `Saved watchlist “${payload.name}”.`, 'ok');
      await loadWatchlists();
    } catch (error) {
      setMessage(watchlistStatus, error.message || 'Unable to save watchlist.', 'error');
    }
  });

  root.querySelectorAll('[data-investigation-example]').forEach((button) => {
    button.addEventListener('click', () => {
      if (button.dataset.investigationExample === 'network') {
        investigationName.value = 'Cluster edge hygiene review';
        investigationCategory.value = 'platform';
        investigationRegions.value = 'local-cluster,aro-prod';
        investigationTags.value = 'network,governance';
        investigationPrompt.value = 'Review routes, services, ingresses, and network policies. Highlight public exposure, stale routes, missing isolation, and cross-cluster drift.';
      } else {
        investigationName.value = 'Storage governance review';
        investigationCategory.value = 'storage';
        investigationRegions.value = 'local-cluster,ibmz-prod';
        investigationTags.value = 'storage,governance';
        investigationPrompt.value = 'Inspect persistent volumes, persistent volume claims, storage classes, image streams, and builds. Highlight stale storage, weak reclaim posture, and artifact sprawl.';
      }
    });
  });

  watchlistList.addEventListener('click', async (event) => {
    const button = event.target.closest('[data-watchlist-run-id]');
    if (!button) return;
    setMessage(watchlistStatus, 'Running watchlist…', 'pending');
    try {
      const response = await fetch(`/watchlists/${button.dataset.watchlistRunId}/run`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ runtime: buildRuntime() })
      });
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.detail || 'Unable to run watchlist');
      watchlistResults.innerHTML = (payload.results || []).map(runResultMarkup).join('') || '<p class="agent-console__meta">No results were returned.</p>';
      setMessage(watchlistStatus, `Completed ${payload.count || 0} watchlist target run(s).`, 'ok');
      await loadWatchlists();
    } catch (error) {
      setMessage(watchlistStatus, error.message || 'Unable to run watchlist.', 'error');
    }
  });

  refreshAll().catch((error) => {
    setMessage(investigationStatus, error.message || 'Unable to load saved investigations.', 'error');
    setMessage(watchlistStatus, error.message || 'Unable to load watchlists.', 'error');
  });

  loadProviderCatalog().then(() => loadOllamaModels(true));
  llmProviderInput?.addEventListener('change', () => {
    syncProviderFields();
    if (currentProviderId() === 'ollama') {
      loadOllamaModels(true);
      setMessage(watchlistStatus, 'Switched to Local Ollama runtime for manual watchlist runs.', 'ok');
      return;
    }
    setMessage(watchlistStatus, `Switched to ${currentProvider().label}. Provide the required external credentials before running the watchlist.`, 'ok');
  });
  ollamaBaseUrlInput?.addEventListener('change', () => loadOllamaModels(false));
})();
