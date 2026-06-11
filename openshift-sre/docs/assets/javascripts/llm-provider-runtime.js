(() => {
  const FALLBACK_PROVIDER_CATALOG = {
    configured_provider: 'ollama',
    configured_model_name: '',
    configured_base_url: 'http://localhost:11434',
    providers: [
      {
        id: 'ollama',
        label: 'Local Ollama',
        category: 'local',
        description: 'Use the local Ollama runtime already supported by the stack.',
        default_base_url: 'http://localhost:11434',
        default_model: '',
        default_api_version: '',
        supports_catalog_refresh: true,
        suggested_models: ['gemma4:26b', 'qwen3:8b', 'llama3.1:8b'],
        credential_fields: []
      }
    ]
  };

  const normalizeProviderId = (catalog, providerId) => {
    const requested = String(providerId || '').trim().toLowerCase();
    const providers = Array.isArray(catalog?.providers) ? catalog.providers : [];
    if (requested && providers.some((provider) => provider.id === requested)) {
      return requested;
    }
    return catalog?.configured_provider || providers[0]?.id || 'ollama';
  };

  const getProvider = (catalog, providerId) => {
    const resolvedId = normalizeProviderId(catalog, providerId);
    return (Array.isArray(catalog?.providers) ? catalog.providers : []).find((provider) => provider.id === resolvedId)
      || FALLBACK_PROVIDER_CATALOG.providers[0];
  };

  const getSuggestedModels = (catalog, providerId, ollamaCatalog = null) => {
    const provider = getProvider(catalog, providerId);
    const providerModels = Array.isArray(provider?.suggested_models) ? provider.suggested_models : [];
    if (provider.id === 'ollama') {
      const ollamaModels = Array.isArray(ollamaCatalog?.models)
        ? ollamaCatalog.models.map((model) => model?.name || model?.model).filter(Boolean)
        : [];
      return Array.from(new Set([...ollamaModels, ...providerModels, provider.default_model || catalog?.configured_model_name || ''].filter(Boolean)));
    }
    return Array.from(new Set([...providerModels, provider.default_model || catalog?.configured_model_name || ''])).filter(Boolean);
  };

  const buildLlmRuntime = (settings = {}, catalog = FALLBACK_PROVIDER_CATALOG) => {
    const providerId = normalizeProviderId(catalog, settings.provider || settings.llmProvider);
    const runtime = { llm_provider: providerId };
    if (providerId === 'ollama') {
      if (settings.ollamaBaseUrl?.trim()) runtime.ollama_base_url = settings.ollamaBaseUrl.trim();
      if (settings.modelName?.trim()) runtime.local_model_name = settings.modelName.trim();
      return runtime;
    }
    if (settings.externalModelName?.trim()) runtime.llm_model_name = settings.externalModelName.trim();
    if (settings.externalBaseUrl?.trim()) runtime.llm_base_url = settings.externalBaseUrl.trim();
    if (settings.externalApiKey?.trim()) runtime.llm_api_key = settings.externalApiKey.trim();
    if (settings.externalApiVersion?.trim()) runtime.llm_api_version = settings.externalApiVersion.trim();
    if (settings.externalOrganization?.trim()) runtime.llm_organization = settings.externalOrganization.trim();
    return runtime;
  };

  const fetchProviderCatalog = async () => {
    try {
      const response = await fetch('/llm/providers');
      const payload = await response.json();
      if (!response.ok) {
        throw new Error(payload.detail || `Provider catalog request failed with status ${response.status}`);
      }
      return payload;
    } catch {
      return FALLBACK_PROVIDER_CATALOG;
    }
  };

  const runtimeApi = {
    fallbackCatalog: FALLBACK_PROVIDER_CATALOG,
    normalizeProviderId,
    getProvider,
    getSuggestedModels,
    buildLlmRuntime,
    fetchProviderCatalog,
  };

  window.OpenShiftSreLlmRuntime = runtimeApi;
  window.AwsSreLlmRuntime = runtimeApi;
})();
