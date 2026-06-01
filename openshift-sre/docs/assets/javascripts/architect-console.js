(() => {
  const root = document.getElementById('architect-root');
  if (!root || !window.React || !window.ReactDOM) {
    return;
  }

  const { createElement: h, useEffect, useMemo, useState } = window.React;
  const llmRuntime = window.OpenShiftSreLlmRuntime || {};
  const safeJson = (value) => {
    if (!value) return null;
    try {
      return JSON.parse(value);
    } catch {
      return null;
    }
  };
  const parseLines = (value) => String(value || '').split('\n').map((item) => item.trim()).filter(Boolean);
  const formatDate = (value) => {
    if (!value) return '—';
    const date = new Date(value);
    return Number.isNaN(date.getTime()) ? String(value) : date.toLocaleString();
  };
  const stripHtml = (value) => String(value || '').replace(/<[^>]+>/g, '');

  async function fetchJson(url, options) {
    const response = await fetch(url, options);
    const text = await response.text();
    let payload = {};
    try {
      payload = text ? JSON.parse(text) : {};
    } catch {
      payload = { detail: text };
    }
    if (!response.ok) {
      throw new Error(payload.detail || `Request failed with status ${response.status}`);
    }
    return payload;
  }

  function downloadBlob(filename, blob) {
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    link.click();
    setTimeout(() => URL.revokeObjectURL(url), 2500);
  }

  function StatusMessage({ state }) {
    if (!state?.message) return null;
    return h('div', { className: `agent-console__status${state.tone ? ` agent-console__status--${state.tone}` : ''}` }, state.message);
  }

  function ArchitectApp() {
    const [catalog, setCatalog] = useState({ templates: [], supported_assessment_scopes: [] });
    const [knowledgeStatus, setKnowledgeStatus] = useState(null);
    const [knowledgeSources, setKnowledgeSources] = useState([]);
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
    const [templateId, setTemplateId] = useState('custom');
    const [prompt, setPrompt] = useState('');
    const [researchLinks, setResearchLinks] = useState('');
    const [includeLiveState, setIncludeLiveState] = useState(true);
    const [includeKnowledge, setIncludeKnowledge] = useState(true);
    const [ollamaRequirement, setOllamaRequirement] = useState('optional');
    const [assessmentScope, setAssessmentScope] = useState('architecture-readiness');
    const [knowledgeUrl, setKnowledgeUrl] = useState('');
    const [knowledgeQuery, setKnowledgeQuery] = useState('');
    const [knowledgeSearch, setKnowledgeSearch] = useState(null);
    const [knowledgeFiles, setKnowledgeFiles] = useState([]);
    const [status, setStatus] = useState({ message: 'Load a template, add your architecture brief, and generate an OpenShift design pack.', tone: '' });
    const [knowledgeMessage, setKnowledgeMessage] = useState({ message: '', tone: '' });
    const [busy, setBusy] = useState(false);
    const [clarifyResult, setClarifyResult] = useState(null);
    const [assessmentResult, setAssessmentResult] = useState(null);
    const [diagramResult, setDiagramResult] = useState(null);
    const [activeDocument, setActiveDocument] = useState('hld');
    const [liveState, setLiveState] = useState(null);
    const [suggestedTemplateApplied, setSuggestedTemplateApplied] = useState(false);

    const selectedTemplate = useMemo(() => (catalog.templates || []).find((item) => item.id === templateId) || (catalog.templates || [])[0] || null, [catalog.templates, templateId]);
    const suggestedModels = useMemo(() => (llmRuntime.getSuggestedModels ? llmRuntime.getSuggestedModels(providerCatalog, providerId) : []), [providerCatalog, providerId]);
    const documentPack = useMemo(() => diagramResult?.documents?.[activeDocument] || assessmentResult?.assessment || null, [diagramResult, assessmentResult, activeDocument]);

    const runtime = useMemo(() => ({
      ...(llmRuntime.buildLlmRuntime?.({ provider: providerId, ollamaBaseUrl, modelName, externalModelName, externalBaseUrl, externalApiKey, externalApiVersion, externalOrganization }, providerCatalog) || {}),
      cluster_scope: clusterScope.trim() || null,
      openshift_namespace: project.trim() || null,
      kube_context_name: kubeContextName.trim() || null,
      openshift_api_url: openshiftApiUrl.trim() || null,
      openshift_token: openshiftToken || null,
      verify_ssl: verifySsl,
    }), [providerId, ollamaBaseUrl, modelName, externalModelName, externalBaseUrl, externalApiKey, externalApiVersion, externalOrganization, providerCatalog, clusterScope, project, kubeContextName, openshiftApiUrl, openshiftToken, verifySsl]);

    const loadCatalog = async () => {
      const [templates, statusPayload, sources] = await Promise.all([
        fetchJson('/architect/templates'),
        fetchJson('/architect/knowledge'),
        fetchJson('/architect/knowledge/sources')
      ]);
      setCatalog(templates);
      setKnowledgeStatus(statusPayload);
      setKnowledgeSources(sources.sources || []);
      setTemplateId(templates.default_template_id || 'custom');
      setAssessmentScope((templates.supported_assessment_scopes || [])[0]?.id || 'architecture-readiness');
      return templates;
    };

    const refreshKnowledge = async (message) => {
      const [statusPayload, sources] = await Promise.all([
        fetchJson('/architect/knowledge'),
        fetchJson('/architect/knowledge/sources')
      ]);
      setKnowledgeStatus(statusPayload);
      setKnowledgeSources(sources.sources || []);
      if (message) {
        setKnowledgeMessage({ message, tone: 'ok' });
      }
    };

    useEffect(() => {
      let cancelled = false;
      (async () => {
        try {
          const catalogPayload = llmRuntime.fetchProviderCatalog ? await llmRuntime.fetchProviderCatalog() : { providers: [] };
          if (cancelled) return;
          const resolvedProviderId = llmRuntime.normalizeProviderId ? llmRuntime.normalizeProviderId(catalogPayload, catalogPayload.configured_provider || 'ollama') : (catalogPayload.configured_provider || 'ollama');
          setProviderCatalog(catalogPayload);
          setProviderId(resolvedProviderId);
          setOllamaBaseUrl(catalogPayload.configured_base_url || '');
          setModelName(catalogPayload.configured_model_name || '');
          await loadCatalog();
        } catch (error) {
          if (!cancelled) {
            setStatus({ message: error instanceof Error ? error.message : 'Unable to load the architect workspace.', tone: 'error' });
          }
        }
      })();
      return () => {
        cancelled = true;
      };
    }, []);

    useEffect(() => {
      if (!selectedTemplate || suggestedTemplateApplied) return;
      setPrompt((current) => current || selectedTemplate.prompt || '');
    }, [selectedTemplate, suggestedTemplateApplied]);

    const applyTemplate = () => {
      if (!selectedTemplate) return;
      setPrompt(selectedTemplate.prompt || '');
      setSuggestedTemplateApplied(true);
      setStatus({ message: `Loaded the ${selectedTemplate.label} template into the prompt editor.`, tone: 'ok' });
    };

    const loadLiveState = async () => {
      setBusy(true);
      setStatus({ message: 'Collecting live OpenShift architecture state…', tone: '' });
      try {
        const payload = await fetchJson('/architect/openshift-state', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ runtime }) });
        setLiveState(payload);
        setStatus({ message: 'Captured live OpenShift architecture state.', tone: 'ok' });
      } catch (error) {
        setStatus({ message: error instanceof Error ? error.message : 'Unable to capture live OpenShift state.', tone: 'error' });
      } finally {
        setBusy(false);
      }
    };

    const runClarification = async () => {
      setBusy(true);
      setStatus({ message: 'Generating clarification questions…', tone: '' });
      try {
        const payload = await fetchJson('/architect/clarify', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ prompt, runtime, include_live_openshift_state: includeLiveState, openshift_state: liveState }) });
        setClarifyResult(payload);
        setStatus({ message: payload.needs_clarification ? 'Clarification questions ready.' : 'Prompt already has enough detail to proceed.', tone: 'ok' });
      } catch (error) {
        setStatus({ message: error instanceof Error ? error.message : 'Unable to generate clarification questions.', tone: 'error' });
      } finally {
        setBusy(false);
      }
    };

    const runAssessment = async () => {
      setBusy(true);
      setStatus({ message: 'Building architecture assessment pack…', tone: '' });
      try {
        const payload = await fetchJson('/architect/assessment', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            prompt,
            runtime,
            include_live_openshift_state: includeLiveState,
            include_trained_knowledge: includeKnowledge,
            openshift_state: liveState,
            scope_id: assessmentScope,
            research_links: parseLines(researchLinks),
          })
        });
        setAssessmentResult(payload);
        setActiveDocument('assessment');
        setStatus({ message: 'Architecture assessment ready.', tone: 'ok' });
      } catch (error) {
        setStatus({ message: error instanceof Error ? error.message : 'Unable to build the architecture assessment.', tone: 'error' });
      } finally {
        setBusy(false);
      }
    };

    const generateDiagram = async () => {
      setBusy(true);
      setStatus({ message: 'Generating the OpenShift architecture diagram and document pack…', tone: '' });
      try {
        const payload = await fetchJson('/architect/diagram', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            prompt,
            runtime,
            include_live_openshift_state: includeLiveState,
            include_trained_knowledge: includeKnowledge,
            ollama_requirement: ollamaRequirement,
            openshift_state: liveState,
            research_links: parseLines(researchLinks),
          })
        });
        setDiagramResult(payload);
        setAssessmentResult(null);
        setActiveDocument('hld');
        setLiveState(payload.openshift_state || liveState);
        setStatus({ message: 'Architecture pack generated successfully.', tone: 'ok' });
        refreshKnowledge();
      } catch (error) {
        setStatus({ message: error instanceof Error ? error.message : 'Unable to generate the architecture pack.', tone: 'error' });
      } finally {
        setBusy(false);
      }
    };

    const trainLink = async () => {
      if (!knowledgeUrl.trim()) {
        setKnowledgeMessage({ message: 'Paste a documentation URL before training the knowledge base.', tone: 'error' });
        return;
      }
      setBusy(true);
      setKnowledgeMessage({ message: 'Training the knowledge base from the supplied link…', tone: '' });
      try {
        await fetchJson('/architect/knowledge/train-link', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ url: knowledgeUrl.trim(), runtime }) });
        setKnowledgeUrl('');
        await refreshKnowledge('Research link trained successfully.');
      } catch (error) {
        setKnowledgeMessage({ message: error instanceof Error ? error.message : 'Unable to train the knowledge base from that link.', tone: 'error' });
      } finally {
        setBusy(false);
      }
    };

    const trainFiles = async () => {
      if (!knowledgeFiles.length) {
        setKnowledgeMessage({ message: 'Choose at least one file to train the knowledge base.', tone: 'error' });
        return;
      }
      setBusy(true);
      setKnowledgeMessage({ message: 'Uploading and training knowledge files…', tone: '' });
      try {
        const form = new FormData();
        knowledgeFiles.slice(0, 8).forEach((file) => form.append('files', file, file.name));
        form.append('runtime', JSON.stringify(runtime));
        const response = await fetch('/architect/knowledge/train-files', { method: 'POST', body: form });
        const text = await response.text();
        let payload = {};
        try {
          payload = text ? JSON.parse(text) : {};
        } catch {
          payload = { detail: text };
        }
        if (!response.ok) {
          throw new Error(payload.detail || `Request failed with status ${response.status}`);
        }
        setKnowledgeFiles([]);
        await refreshKnowledge(`Trained ${payload.trained_count || 0} knowledge file(s).`);
      } catch (error) {
        setKnowledgeMessage({ message: error instanceof Error ? error.message : 'Unable to train the knowledge base from the uploaded files.', tone: 'error' });
      } finally {
        setBusy(false);
      }
    };

    const searchKnowledge = async () => {
      if (!knowledgeQuery.trim()) {
        setKnowledgeMessage({ message: 'Type a search phrase before previewing knowledge retrieval.', tone: 'error' });
        return;
      }
      setBusy(true);
      setKnowledgeMessage({ message: 'Searching the architect knowledge base…', tone: '' });
      try {
        const payload = await fetchJson('/architect/knowledge/search', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ query: knowledgeQuery.trim(), top_k: 5, runtime }) });
        setKnowledgeSearch(payload);
        setKnowledgeMessage({ message: `Returned ${payload.items?.length || 0} knowledge result(s).`, tone: 'ok' });
      } catch (error) {
        setKnowledgeMessage({ message: error instanceof Error ? error.message : 'Unable to search the knowledge base.', tone: 'error' });
      } finally {
        setBusy(false);
      }
    };

    const clearKnowledge = async () => {
      setBusy(true);
      setKnowledgeMessage({ message: 'Clearing the architect knowledge base…', tone: '' });
      try {
        await fetchJson('/architect/knowledge/clear', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ clear_all: true, runtime }) });
        setKnowledgeSearch(null);
        await refreshKnowledge('Architect knowledge base cleared.');
      } catch (error) {
        setKnowledgeMessage({ message: error instanceof Error ? error.message : 'Unable to clear the architect knowledge base.', tone: 'error' });
      } finally {
        setBusy(false);
      }
    };

    const exportDocument = (kind) => {
      const pack = documentPack;
      if (!pack) {
        setStatus({ message: 'Generate a document pack first before exporting.', tone: 'error' });
        return;
      }
      const markdown = [
        `# ${pack.title || 'OpenShift architecture pack'}`,
        '',
        ...(pack.sections || []).flatMap((section) => [`## ${section.title}`, '', ...(section.body || []), ''])
      ].join('\n');
      try {
        if (kind === 'md') {
          downloadBlob(`${activeDocument}.md`, new Blob([markdown], { type: 'text/markdown;charset=utf-8' }));
        } else if (kind === 'doc') {
          downloadBlob(`${activeDocument}.doc`, new Blob([`<!doctype html><html><body><pre>${markdown.replace(/[<&>]/g, (char) => ({ '<': '&lt;', '>': '&gt;', '&': '&amp;' }[char]))}</pre></body></html>`], { type: 'application/msword' }));
        } else if (kind === 'pdf') {
          const jsPdf = window.jspdf?.jsPDF;
          if (!jsPdf) throw new Error('PDF export is not available in this browser session.');
          const doc = new jsPdf({ unit: 'pt', format: 'a4' });
          doc.text(doc.splitTextToSize(markdown, 520), 40, 50);
          doc.save(`${activeDocument}.pdf`);
        } else if (kind === 'ppt') {
          const PptxGenJS = window.PptxGenJS;
          if (!PptxGenJS) throw new Error('PowerPoint export is not available in this browser session.');
          const pptx = new PptxGenJS();
          pptx.layout = 'LAYOUT_WIDE';
          const slide = pptx.addSlide();
          slide.addText(pack.title || 'OpenShift architecture pack', { x: 0.4, y: 0.3, w: 12.2, h: 0.4, fontSize: 24, bold: true, color: '0F172A' });
          slide.addText(markdown, { x: 0.4, y: 0.85, w: 12.2, h: 6.0, fontSize: 10.5, color: '334155', margin: 0.08, valign: 'top' });
          pptx.writeFile({ fileName: `${activeDocument}.pptx` });
        }
        setStatus({ message: `Exported the ${activeDocument.toUpperCase()} pack as ${kind.toUpperCase()}.`, tone: 'ok' });
      } catch (error) {
        setStatus({ message: error instanceof Error ? error.message : 'Unable to export the document pack.', tone: 'error' });
      }
    };

    const exportArtifact = (kind) => {
      if (!diagramResult?.artifacts) {
        setStatus({ message: 'Generate a diagram first before exporting artifacts.', tone: 'error' });
        return;
      }
      const artifacts = diagramResult.artifacts;
      try {
        if (kind === 'drawio') {
          downloadBlob(artifacts.filenames?.drawio || 'openshift-architecture.drawio', new Blob([artifacts.drawio_xml || ''], { type: 'application/xml;charset=utf-8' }));
        } else if (kind === 'svg') {
          downloadBlob(artifacts.filenames?.svg || 'openshift-architecture.svg', new Blob([artifacts.svg || artifacts.svg_preview || ''], { type: 'image/svg+xml;charset=utf-8' }));
        } else if (kind === 'png') {
          if (!artifacts.png_base64) throw new Error('PNG export is not available in this result.');
          const binary = atob(artifacts.png_base64);
          const bytes = Uint8Array.from(binary, (char) => char.charCodeAt(0));
          downloadBlob(artifacts.filenames?.png || 'openshift-architecture.png', new Blob([bytes], { type: 'image/png' }));
        }
        setStatus({ message: `Exported the ${kind.toUpperCase()} artifact.`, tone: 'ok' });
      } catch (error) {
        setStatus({ message: error instanceof Error ? error.message : 'Unable to export the diagram artifact.', tone: 'error' });
      }
    };

    return h('div', { className: 'architect-console' }, [
      h('section', { className: 'architect-console__hero agent-console__panel', id: 'architect-launcher' }, [
        h('div', { className: 'architect-console__hero-grid' }, [
          h('div', null, [
            h('span', { className: 'architect-console__eyebrow' }, 'OpenShift-native architect lane'),
            h('h2', null, 'Create original OpenShift HLD and LLD packs with live-state grounding, research-link ingestion, and editable draw.io output.'),
            h('p', null, 'This workspace is intentionally OpenShift-first. It understands multicluster fleets, GitOps delivery, disconnected environments, CNV, DR, security, and migration patterns—and it can pull in Red Hat or internal documentation before it generates the final architecture pack.'),
            h('div', { className: 'architect-console__metrics' }, [
              h('article', { className: 'architect-console__metric' }, [h('span', { className: 'architect-console__meta' }, 'Pattern library'), h('strong', null, `${catalog.templates?.length || 0} templates`)]),
              h('article', { className: 'architect-console__metric' }, [h('span', { className: 'architect-console__meta' }, 'Knowledge sources'), h('strong', null, `${knowledgeSources.length}`)]),
              h('article', { className: 'architect-console__metric' }, [h('span', { className: 'architect-console__meta' }, 'Knowledge health'), h('strong', null, knowledgeStatus?.healthy ? 'Ready' : (knowledgeStatus?.enabled ? 'Configured' : 'Disabled'))])
            ])
          ]),
          h('div', { className: 'architect-console__summary' }, [
            h('span', { className: `architect-console__badge ${diagramResult ? 'architect-console__badge--ok' : ''}` }, diagramResult ? 'Latest pack ready' : 'Awaiting first generation'),
            h('h3', null, selectedTemplate?.label || 'Custom OpenShift architecture'),
            h('p', { className: 'architect-console__meta' }, selectedTemplate?.description || 'Choose a template or write your own OpenShift architecture brief.'),
            h('ul', null, [
              h('li', { key: 'state' }, includeLiveState ? 'Live OpenShift state grounding enabled.' : 'Prompt-only generation enabled.'),
              h('li', { key: 'knowledge' }, includeKnowledge ? 'Trained knowledge will be used when available.' : 'Knowledge retrieval disabled for this run.'),
              h('li', { key: 'research' }, parseLines(researchLinks).length ? `${parseLines(researchLinks).length} research link(s) queued for ingestion.` : 'No research links queued.'),
              h('li', { key: 'scope' }, `Assessment scope: ${assessmentScope}`)
            ])
          ])
        ]),
        h(StatusMessage, { state: status })
      ]),

      h('section', { className: 'agent-console__panel' }, [
        h('div', { className: 'architect-console__grid' }, [
          h('article', { className: 'architect-console__card' }, [
            h('div', { className: 'agent-console__queue-header' }, [
              h('div', null, [h('h3', null, 'Template and prompt'), h('p', { className: 'architect-console__meta' }, 'Choose a named OpenShift pattern or keep the workspace fully custom.')]),
              h('button', { className: 'agent-console__example', type: 'button', onClick: applyTemplate }, 'Apply template')
            ]),
            h('label', { className: 'agent-console__label' }, ['Template', h('select', { className: 'agent-console__input', value: templateId, onChange: (event) => setTemplateId(event.target.value) }, (catalog.templates || []).map((item) => h('option', { key: item.id, value: item.id }, `${item.label} · ${item.category}`)))]),
            h('div', { className: 'architect-console__template-grid' }, (catalog.templates || []).slice(0, 6).map((item) => h('article', { className: `architect-console__template-card ${item.id === templateId ? 'is-active' : ''}`, key: item.id }, [h('strong', null, item.label), h('p', { className: 'architect-console__meta' }, item.description), h('span', { className: 'architect-console__pill' }, item.mode || 'prompt-only')]))),
            h('label', { className: 'agent-console__label' }, ['Architecture brief', h('textarea', { className: 'agent-console__textarea', rows: 10, value: prompt, onChange: (event) => { setPrompt(event.target.value); setSuggestedTemplateApplied(true); }, onKeyDown: (event) => { if ((event.metaKey || event.ctrlKey) && event.key === 'Enter') { event.preventDefault(); generateDiagram(); } }, placeholder: 'Describe the OpenShift architecture you want, including platform pattern, ingress, security, GitOps, DR, migration, or application concerns.' })]),
            h('label', { className: 'agent-console__label' }, ['Research links (one per line)', h('textarea', { className: 'agent-console__textarea', rows: 4, value: researchLinks, onChange: (event) => setResearchLinks(event.target.value), placeholder: 'https://docs.redhat.com/...\nhttps://internal/wiki/openshift-patterns' })]),
            h('p', { className: 'architect-console__helper' }, 'Paste Red Hat or internal URLs here if you want the architect lane to ingest them before generation. The workspace can ground the design on those sources whenever the pgvector knowledge store is enabled.')
          ]),
          h('article', { className: 'architect-console__card' }, [
            h('div', { className: 'agent-console__queue-header' }, [h('div', null, [h('h3', null, 'Generation controls'), h('p', { className: 'architect-console__meta' }, 'Choose whether to ground on live cluster state, trained knowledge, and optional Ollama-only rendering.')])]),
            h('div', { className: 'architect-console__grid' }, [
              h('label', { className: 'agent-console__label' }, ['Cluster scope', h('input', { className: 'agent-console__input', value: clusterScope, onChange: (event) => setClusterScope(event.target.value), placeholder: 'prod-west / acm-hub / edge-factory' })]),
              h('label', { className: 'agent-console__label' }, ['Namespace focus', h('input', { className: 'agent-console__input', value: project, onChange: (event) => setProject(event.target.value), placeholder: 'openshift-gitops or app namespace' })]),
              h('label', { className: 'agent-console__label' }, ['Assessment scope', h('select', { className: 'agent-console__input', value: assessmentScope, onChange: (event) => setAssessmentScope(event.target.value) }, (catalog.supported_assessment_scopes || []).map((item) => h('option', { key: item.id, value: item.id }, item.label)))]),
              h('label', { className: 'agent-console__label' }, ['Ollama requirement', h('select', { className: 'agent-console__input', value: ollamaRequirement, onChange: (event) => setOllamaRequirement(event.target.value) }, [h('option', { value: 'optional' }, 'Optional'), h('option', { value: 'required' }, 'Required')])]),
              h('label', { className: 'agent-console__label' }, [h('span', null, 'Include live OpenShift state'), h('input', { type: 'checkbox', checked: includeLiveState, onChange: (event) => setIncludeLiveState(event.target.checked) })]),
              h('label', { className: 'agent-console__label' }, [h('span', null, 'Include trained knowledge'), h('input', { type: 'checkbox', checked: includeKnowledge, onChange: (event) => setIncludeKnowledge(event.target.checked) })])
            ]),
            h('div', { className: 'agent-console__actions' }, [
              h('button', { className: 'agent-console__example', type: 'button', disabled: busy, onClick: loadLiveState }, busy ? 'Working…' : 'Load live state'),
              h('button', { className: 'agent-console__example', type: 'button', disabled: busy, onClick: runClarification }, busy ? 'Working…' : 'Clarify prompt'),
              h('button', { className: 'agent-console__example', type: 'button', disabled: busy, onClick: runAssessment }, busy ? 'Working…' : 'Run assessment'),
              h('button', { className: 'agent-console__button', type: 'button', disabled: busy, onClick: generateDiagram }, busy ? 'Generating…' : 'Generate HLD / LLD')
            ]),
            h('details', null, [
              h('summary', null, 'Runtime overrides'),
              h('div', { className: 'architect-console__grid' }, [
                h('label', { className: 'agent-console__label' }, ['LLM provider', h('select', { className: 'agent-console__input', value: providerId, onChange: (event) => setProviderId(event.target.value) }, (providerCatalog.providers || []).map((provider) => h('option', { key: provider.id, value: provider.id }, provider.label || provider.id)))]),
                providerId === 'ollama'
                  ? h('label', { className: 'agent-console__label' }, ['Ollama base URL', h('input', { className: 'agent-console__input', value: ollamaBaseUrl, onChange: (event) => setOllamaBaseUrl(event.target.value), placeholder: 'http://host.containers.internal:11434' })])
                  : h('label', { className: 'agent-console__label' }, ['Hosted base URL', h('input', { className: 'agent-console__input', value: externalBaseUrl, onChange: (event) => setExternalBaseUrl(event.target.value), placeholder: 'https://api.openai.com/v1' })]),
                h('label', { className: 'agent-console__label' }, [(providerId === 'ollama' ? 'Local model' : 'Hosted model'), h('input', { className: 'agent-console__input', value: providerId === 'ollama' ? modelName : externalModelName, list: 'architect-suggested-models', onChange: (event) => providerId === 'ollama' ? setModelName(event.target.value) : setExternalModelName(event.target.value), placeholder: suggestedModels[0] || 'model name' }), h('datalist', { id: 'architect-suggested-models' }, suggestedModels.map((model) => h('option', { key: model, value: model }))) ]),
                h('label', { className: 'agent-console__label' }, ['Kube context name', h('input', { className: 'agent-console__input', value: kubeContextName, onChange: (event) => setKubeContextName(event.target.value), placeholder: 'Optional kube context override' })]),
                h('label', { className: 'agent-console__label' }, ['OpenShift API URL', h('input', { className: 'agent-console__input', value: openshiftApiUrl, onChange: (event) => setOpenshiftApiUrl(event.target.value), placeholder: 'https://api.cluster.example:6443' })]),
                h('label', { className: 'agent-console__label' }, ['OpenShift token', h('input', { className: 'agent-console__input', type: 'password', value: openshiftToken, onChange: (event) => setOpenshiftToken(event.target.value), placeholder: 'Optional bearer token' })]),
                providerId !== 'ollama' ? h('label', { className: 'agent-console__label' }, ['Hosted API key', h('input', { className: 'agent-console__input', type: 'password', value: externalApiKey, onChange: (event) => setExternalApiKey(event.target.value), placeholder: 'Optional API key override' })]) : null,
                providerId !== 'ollama' ? h('label', { className: 'agent-console__label' }, ['API version', h('input', { className: 'agent-console__input', value: externalApiVersion, onChange: (event) => setExternalApiVersion(event.target.value), placeholder: 'Optional API version' })]) : null,
                providerId !== 'ollama' ? h('label', { className: 'agent-console__label' }, ['Organization / tenant hint', h('input', { className: 'agent-console__input', value: externalOrganization, onChange: (event) => setExternalOrganization(event.target.value), placeholder: 'Optional organization hint' })]) : null,
                h('label', { className: 'agent-console__label' }, [h('span', null, 'Verify SSL'), h('input', { type: 'checkbox', checked: verifySsl, onChange: (event) => setVerifySsl(event.target.checked) })])
              ])
            ])
          ])
        ])
      ]),

      h('section', { className: 'agent-console__panel', id: 'architect-knowledge' }, [
        h('div', { className: 'agent-console__queue-header' }, [h('div', null, [h('h2', null, 'Knowledge and web research lane'), h('p', { className: 'architect-console__meta' }, 'Train the architect store from direct documentation links or uploaded files, then preview the retrieved context before generation.')]), h('span', { className: `architect-console__badge ${knowledgeStatus?.healthy ? 'architect-console__badge--ok' : knowledgeStatus?.enabled ? 'architect-console__badge--warn' : ''}` }, knowledgeStatus?.healthy ? 'Knowledge ready' : knowledgeStatus?.enabled ? 'Configured but unhealthy' : 'Knowledge disabled')]),
        h(StatusMessage, { state: knowledgeMessage }),
        h('div', { className: 'architect-console__knowledge-grid' }, [
          h('article', { className: 'architect-console__knowledge-card' }, [
            h('h3', null, 'Train from link'),
            h('label', { className: 'agent-console__label' }, ['Documentation URL', h('input', { className: 'agent-console__input', value: knowledgeUrl, onChange: (event) => setKnowledgeUrl(event.target.value), placeholder: 'https://docs.redhat.com/...' })]),
            h('div', { className: 'agent-console__actions' }, [h('button', { className: 'agent-console__button', type: 'button', disabled: busy, onClick: trainLink }, 'Train link')]),
            h('p', { className: 'architect-console__helper' }, 'Use this for Red Hat documentation, internal design standards, reference architectures, or approved engineering guidance.')
          ]),
          h('article', { className: 'architect-console__knowledge-card' }, [
            h('h3', null, 'Train from files'),
            h('label', { className: 'agent-console__label' }, ['Upload design files', h('input', { className: 'agent-console__input', type: 'file', multiple: true, onChange: (event) => setKnowledgeFiles(Array.from(event.target.files || [])) })]),
            h('div', { className: 'agent-console__actions' }, [h('button', { className: 'agent-console__button', type: 'button', disabled: busy, onClick: trainFiles }, 'Train files')]),
            h('p', { className: 'architect-console__helper' }, knowledgeFiles.length ? `${knowledgeFiles.length} file(s) selected.` : 'Supported inputs include text, markdown, JSON, HTML, SVG, draw.io, and PDF documents.')
          ]),
          h('article', { className: 'architect-console__knowledge-card' }, [
            h('h3', null, 'Search knowledge base'),
            h('label', { className: 'agent-console__label' }, ['Search phrase', h('input', { className: 'agent-console__input', value: knowledgeQuery, onChange: (event) => setKnowledgeQuery(event.target.value), placeholder: 'OpenShift disconnected registry design' })]),
            h('div', { className: 'agent-console__actions' }, [h('button', { className: 'agent-console__button', type: 'button', disabled: busy, onClick: searchKnowledge }, 'Search knowledge'), h('button', { className: 'agent-console__example', type: 'button', disabled: busy, onClick: clearKnowledge }, 'Clear knowledge')]),
            h('p', { className: 'architect-console__helper' }, 'The search preview shows the exact snippets that will ground the next architecture run.')
          ])
        ]),
        h('div', { className: 'architect-console__knowledge-grid' }, [
          h('article', { className: 'architect-console__knowledge-card' }, [
            h('h3', null, 'Knowledge status'),
            knowledgeStatus ? h('ul', null, [
              h('li', { key: 'enabled' }, `Enabled: ${knowledgeStatus.enabled ? 'yes' : 'no'}`),
              h('li', { key: 'healthy' }, `Healthy: ${knowledgeStatus.healthy ? 'yes' : 'no'}`),
              h('li', { key: 'model' }, `Embedding model: ${knowledgeStatus.embedding_model || 'n/a'}`),
              h('li', { key: 'chunks' }, `Chunks: ${knowledgeStatus.stats?.chunk_count || 0}`),
              h('li', { key: 'documents' }, `Documents: ${knowledgeStatus.stats?.document_count || 0}`),
              h('li', { key: 'last' }, `Last trained: ${formatDate(knowledgeStatus.stats?.last_trained_at)}`)
            ]) : h('div', { className: 'architect-console__empty' }, 'Knowledge status not loaded yet.')
          ]),
          h('article', { className: 'architect-console__knowledge-card' }, [
            h('h3', null, 'Indexed sources'),
            knowledgeSources.length ? h('div', { className: 'architect-console__sources' }, knowledgeSources.map((source) => h('div', { className: 'architect-console__source', key: source.source_uri }, [h('strong', null, source.title || source.source_uri), h('div', { className: 'architect-console__meta' }, `${source.source_type} · ${source.chunk_count} chunk(s) · ${formatDate(source.last_trained_at)}`), h('div', { className: 'architect-console__meta' }, source.source_uri)]))) : h('div', { className: 'architect-console__empty' }, 'No knowledge sources have been trained yet.')
          ]),
          h('article', { className: 'architect-console__knowledge-card' }, [
            h('h3', null, 'Search preview'),
            knowledgeSearch?.items?.length ? h('div', { className: 'architect-console__sources' }, knowledgeSearch.items.map((item, index) => h('div', { className: 'architect-console__source', key: `${item.source_uri}-${index}` }, [h('strong', null, item.title), h('div', { className: 'architect-console__meta' }, `${item.source_type} · score ${item.score}`), h('p', null, item.excerpt)]))) : h('div', { className: 'architect-console__empty' }, 'Search the knowledge base to preview retrieved context.')
          ])
        ])
      ]),

      h('section', { className: 'agent-console__panel', id: 'architect-results' }, [
        h('div', { className: 'agent-console__queue-header' }, [h('div', null, [h('h2', null, 'Results and diagram'), h('p', { className: 'architect-console__meta' }, 'The generated diagram stays editable as draw.io XML and previewable as SVG or PNG.')]), diagramResult?.rendering?.quality_scorecard ? h('span', { className: 'architect-console__badge architect-console__badge--ok' }, `${diagramResult.rendering.quality_scorecard.overall_score}/${diagramResult.rendering.quality_scorecard.max_score}`) : null]),
        h('div', { className: 'architect-console__result-grid' }, [
          h('article', { className: 'architect-console__summary' }, [
            h('h3', null, 'Planning summary'),
            diagramResult?.planning ? h('ul', null, [
              h('li', { key: 'pattern' }, `Pattern: ${diagramResult.planning.pattern_label}`),
              h('li', { key: 'confidence' }, `Confidence: ${diagramResult.planning.confidence}`),
              h('li', { key: 'reasoning' }, diagramResult.planning.reasoning_summary),
              h('li', { key: 'state' }, `Live state included: ${diagramResult.openshift_state_included ? 'yes' : 'no'}`)
            ]) : h('div', { className: 'architect-console__empty' }, 'Generate a diagram to see the planning summary.')
          ]),
          h('article', { className: 'architect-console__summary' }, [
            h('h3', null, 'Clarification questions'),
            clarifyResult?.questions?.length ? h('div', { className: 'architect-console__question-grid' }, clarifyResult.questions.map((question) => h('article', { className: 'architect-console__question', key: question.question_id }, [h('strong', null, question.title), h('p', null, question.question), question.rationale ? h('p', { className: 'architect-console__meta' }, question.rationale) : null]))) : h('div', { className: 'architect-console__empty' }, 'Use “Clarify prompt” if you want the workspace to ask for missing OpenShift design inputs before generation.')
          ]),
          h('article', { className: 'architect-console__summary' }, [
            h('h3', null, 'Assessment summary'),
            assessmentResult?.assessment ? h('div', null, [h('p', null, assessmentResult.assessment.summary || 'Architecture assessment ready.'), h('ul', null, (assessmentResult.assessment.assessment_dimensions || []).map((item) => h('li', { key: item.id }, `${item.label}: ${item.assessment}`)))]) : h('div', { className: 'architect-console__empty' }, 'Run the assessment lane to review architecture readiness by scope.')
          ])
        ]),
        h('div', { className: 'architect-console__diagram' }, diagramResult?.artifacts?.svg ? h('div', { dangerouslySetInnerHTML: { __html: diagramResult.artifacts.svg } }) : h('div', { className: 'architect-console__empty' }, 'Generate a diagram to see the architecture preview here.'))
      ]),

      h('section', { className: 'agent-console__panel', id: 'architect-documents' }, [
        h('div', { className: 'agent-console__queue-header' }, [h('div', null, [h('h2', null, 'HLD, LLD, and assessment packs'), h('p', { className: 'architect-console__meta' }, 'Switch between document packs and export them as markdown, Word-compatible output, PDF, or PowerPoint.')]), h('div', { className: 'architect-console__tabs' }, [h('button', { type: 'button', className: `architect-console__tab ${activeDocument === 'hld' ? 'is-active' : ''}`, onClick: () => setActiveDocument('hld') }, 'HLD'), h('button', { type: 'button', className: `architect-console__tab ${activeDocument === 'lld' ? 'is-active' : ''}`, onClick: () => setActiveDocument('lld') }, 'LLD'), h('button', { type: 'button', className: `architect-console__tab ${activeDocument === 'assessment' ? 'is-active' : ''}`, onClick: () => setActiveDocument('assessment') }, 'Assessment')])]),
        h('div', { className: 'architect-console__document-grid' }, [
          h('article', { className: 'architect-console__document' }, [
            h('div', { className: 'agent-console__queue-header' }, [h('div', null, [h('h3', null, documentPack?.title || 'Document preview'), h('p', { className: 'architect-console__meta' }, documentPack?.summary || 'Generate a document pack to preview the sections here.')]), h('div', { className: 'architect-console__artifact-actions' }, [h('button', { className: 'agent-console__example', type: 'button', onClick: () => exportDocument('md') }, 'Markdown'), h('button', { className: 'agent-console__example', type: 'button', onClick: () => exportDocument('doc') }, 'Word'), h('button', { className: 'agent-console__example', type: 'button', onClick: () => exportDocument('pdf') }, 'PDF'), h('button', { className: 'agent-console__example', type: 'button', onClick: () => exportDocument('ppt') }, 'PPT')])]),
            documentPack?.sections?.length ? h('div', { className: 'architect-console__sources' }, documentPack.sections.map((section) => h('div', { className: 'architect-console__source', key: section.title }, [h('strong', null, section.title), h('ul', null, (section.body || []).map((line, index) => h('li', { key: `${section.title}-${index}` }, stripHtml(line))))]))) : h('div', { className: 'architect-console__empty' }, 'No document sections yet.')
          ]),
          h('article', { className: 'architect-console__document' }, [
            h('h3', null, 'Quality scorecard'),
            diagramResult?.rendering?.quality_scorecard ? h('ul', null, [
              h('li', { key: 'score' }, `Overall score: ${diagramResult.rendering.quality_scorecard.overall_score}/${diagramResult.rendering.quality_scorecard.max_score}`),
              h('li', { key: 'band' }, `Quality band: ${diagramResult.rendering.quality_scorecard.quality_band}`),
              h('li', { key: 'summary' }, diagramResult.rendering.quality_scorecard.summary)
            ].concat((diagramResult.rendering.quality_scorecard.top_gaps || []).map((item, index) => h('li', { key: `gap-${index}` }, item)))) : h('div', { className: 'architect-console__empty' }, 'Generate a diagram to compute the quality scorecard.'),
            h('h3', null, 'Live state snapshot'),
            liveState ? h('pre', { className: 'architect-console__json' }, JSON.stringify(liveState, null, 2)) : h('div', { className: 'architect-console__empty' }, 'Load or generate live OpenShift state to inspect it here.')
          ])
        ])
      ]),

      h('section', { className: 'agent-console__panel', id: 'architect-artifacts' }, [
        h('div', { className: 'agent-console__queue-header' }, [h('div', null, [h('h2', null, 'Artifacts and exports'), h('p', { className: 'architect-console__meta' }, 'Download editable draw.io source, browser-friendly SVG, or a portable PNG from the generated result.')])]),
        h('div', { className: 'architect-console__artifact-grid' }, [
          h('article', { className: 'architect-console__artifact' }, [
            h('h3', null, 'Diagram artifacts'),
            h('div', { className: 'architect-console__artifact-actions' }, [
              h('button', { className: 'agent-console__button', type: 'button', onClick: () => exportArtifact('drawio') }, 'Export draw.io'),
              h('button', { className: 'agent-console__button', type: 'button', onClick: () => exportArtifact('svg') }, 'Export SVG'),
              h('button', { className: 'agent-console__button', type: 'button', onClick: () => exportArtifact('png') }, 'Export PNG')
            ]),
            h('p', { className: 'architect-console__helper' }, 'The container now installs draw.io plus Xvfb and related GUI libraries so server-side diagram export works in the Podman stack instead of relying on a host-side desktop install.')
          ]),
          h('article', { className: 'architect-console__artifact' }, [
            h('h3', null, 'Research training results'),
            diagramResult?.research_training?.length ? h('div', { className: 'architect-console__sources' }, diagramResult.research_training.map((item, index) => h('div', { className: 'architect-console__source', key: `${item.url}-${index}` }, [h('strong', null, item.url), h('div', { className: 'architect-console__meta' }, item.trained ? 'Trained successfully' : `Skipped / failed: ${item.reason || 'unknown reason'}`)]))) : h('div', { className: 'architect-console__empty' }, 'No research-link ingestion has been attempted for the latest run.'),
            h('h3', null, 'Knowledge context used'),
            diagramResult?.knowledge?.items?.length ? h('div', { className: 'architect-console__sources' }, diagramResult.knowledge.items.map((item, index) => h('div', { className: 'architect-console__source', key: `${item.source_uri}-${index}` }, [h('strong', null, item.title), h('div', { className: 'architect-console__meta' }, `${item.source_type} · score ${item.score}`), h('p', null, item.excerpt)]))) : h('div', { className: 'architect-console__empty' }, 'No knowledge context was used in the latest generation run.')
          ])
        ])
      ]),

      h('section', { className: 'agent-console__panel', id: 'architect-trace' }, [
        h('div', { className: 'agent-console__queue-header' }, [h('div', null, [h('h2', null, 'Generation trace'), h('p', { className: 'architect-console__meta' }, 'Inspect the raw result envelopes when you want the exact planning, assessment, or artifact payloads instead of the curated view.')])]),
        h('div', { className: 'architect-console__grid' }, [
          h('article', { className: 'architect-console__card' }, [h('h3', null, 'Latest diagram payload'), diagramResult ? h('pre', { className: 'architect-console__json' }, JSON.stringify(diagramResult, null, 2)) : h('div', { className: 'architect-console__empty' }, 'No diagram payload yet.')]),
          h('article', { className: 'architect-console__card' }, [h('h3', null, 'Latest assessment payload'), assessmentResult ? h('pre', { className: 'architect-console__json' }, JSON.stringify(assessmentResult, null, 2)) : h('div', { className: 'architect-console__empty' }, 'No assessment payload yet.')]),
          h('article', { className: 'architect-console__card' }, [h('h3', null, 'Latest clarification payload'), clarifyResult ? h('pre', { className: 'architect-console__json' }, JSON.stringify(clarifyResult, null, 2)) : h('div', { className: 'architect-console__empty' }, 'No clarification payload yet.')])
        ])
      ])
    ]);
  }

  const reactRoot = window.ReactDOM.createRoot(root);
  reactRoot.render(h(ArchitectApp));
})();
