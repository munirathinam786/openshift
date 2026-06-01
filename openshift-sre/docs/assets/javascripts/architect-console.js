(() => {
  const root = document.getElementById('architect-root');
  if (!root || !window.React || !window.ReactDOM) {
    return;
  }

  const { createElement: h, useEffect, useMemo, useRef, useState } = window.React;
  const llmRuntime = window.OpenShiftSreLlmRuntime || {};
  const DRAWIO_EMBED_ORIGIN = 'https://embed.diagrams.net';
  const DRAWIO_EMBED_URL = `${DRAWIO_EMBED_ORIGIN}/?embed=1&ui=min&spin=Loading+native+draw.io+preview...&proto=json&saveAndExit=0&noSaveBtn=1&noExitBtn=1&modified=0&libraries=0`;
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
  const pickPreferredOllamaModel = (payload) => {
    const models = Array.isArray(payload?.models) ? payload.models : [];
    const names = models.map((model) => model?.name || model?.model).filter(Boolean);
    if (!names.length) {
      return '';
    }
    const configured = String(payload?.configured_model_name || '').trim();
    if (configured && names.includes(configured)) {
      return configured;
    }
    const loaded = models.find((model) => model?.loaded && (model?.name || model?.model));
    if (loaded) {
      return loaded.name || loaded.model;
    }
    const firstGenerative = models.find((model) => {
      const name = String(model?.name || model?.model || '').toLowerCase();
      return name && !name.includes('embed');
    });
    if (firstGenerative) {
      return firstGenerative.name || firstGenerative.model;
    }
    return names[0];
  };

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

  async function fetchOllamaModels(ollamaBaseUrl = '') {
    const params = new URLSearchParams();
    if (ollamaBaseUrl) {
      params.set('ollama_base_url', ollamaBaseUrl);
    }
    const response = await fetch(`/ollama/models${params.toString() ? `?${params}` : ''}`);
    const text = await response.text();
    let payload = {};
    try {
      payload = text ? JSON.parse(text) : {};
    } catch {
      payload = { detail: text };
    }
    if (!response.ok) {
      throw new Error(payload.detail || `Model list request failed with status ${response.status}`);
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

  const createTimestampSlug = () => new Date().toISOString().replace(/[:.]/g, '-');
  const slugify = (value, fallback = 'architect-pack') => String(value || '')
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '') || fallback;
  const escapeHtmlValue = (value) => String(value || '').replace(/[<&>]/g, (char) => ({ '<': '&lt;', '>': '&gt;', '&': '&amp;' }[char]));
  const diagramFilename = (pageName, extension) => `${slugify(pageName || `diagram-page-${extension}`)}.${extension}`;

  async function svgMarkupToPngDataUrl(svgMarkup) {
    if (!svgMarkup) {
      throw new Error('No SVG markup is available for this preview page.');
    }
    return new Promise((resolve, reject) => {
      const blob = new Blob([svgMarkup], { type: 'image/svg+xml;charset=utf-8' });
      const url = URL.createObjectURL(blob);
      const image = new Image();
      image.onload = () => {
        try {
          const canvas = document.createElement('canvas');
          canvas.width = Math.max(image.naturalWidth || 1600, 1200);
          canvas.height = Math.max(image.naturalHeight || 900, 900);
          const context = canvas.getContext('2d');
          if (!context) {
            throw new Error('Canvas rendering is not available for SVG conversion.');
          }
          context.fillStyle = '#ffffff';
          context.fillRect(0, 0, canvas.width, canvas.height);
          context.drawImage(image, 0, 0, canvas.width, canvas.height);
          resolve(canvas.toDataURL('image/png'));
        } catch (error) {
          reject(error);
        } finally {
          URL.revokeObjectURL(url);
        }
      };
      image.onerror = () => {
        URL.revokeObjectURL(url);
        reject(new Error('Unable to convert the SVG preview into a PNG image.'));
      };
      image.src = url;
    });
  }

  function dataUrlToBlob(dataUrl) {
    const [header, payload] = String(dataUrl || '').split(',');
    if (!header || !payload) {
      throw new Error('The generated image payload is invalid.');
    }
    const mime = /data:(.*?);base64/.exec(header)?.[1] || 'application/octet-stream';
    const binary = atob(payload);
    const bytes = Uint8Array.from(binary, (char) => char.charCodeAt(0));
    return new Blob([bytes], { type: mime });
  }

  async function getPreviewImageData(preview) {
    const pngBase64 = String(preview?.png_base64 || '').trim();
    if (pngBase64) {
      return `data:image/png;base64,${pngBase64}`;
    }
    return svgMarkupToPngDataUrl(preview?.svg || '');
  }

  async function buildArchitectPdf({ pack, diagramResult, activeDocument, generatedAt }) {
    const jsPdf = window.jspdf?.jsPDF;
    if (!jsPdf) {
      throw new Error('PDF export is not available in this browser session.');
    }
    const doc = new jsPdf({ unit: 'pt', format: 'a4' });
    const pageWidth = doc.internal.pageSize.getWidth();
    const pageHeight = doc.internal.pageSize.getHeight();
    const margin = 42;
    const contentWidth = pageWidth - (margin * 2);
    const footerY = pageHeight - 24;
    const pagePreviews = Array.isArray(diagramResult?.artifacts?.page_previews) ? diagramResult.artifacts.page_previews : [];
    const documentLabel = activeDocument.toUpperCase();

    const paintHeader = (sectionTitle, sectionSubtitle = '') => {
      doc.setFillColor(8, 47, 73);
      doc.rect(0, 0, pageWidth, 58, 'F');
      doc.setFillColor(34, 211, 238);
      doc.rect(0, 58, pageWidth, 6, 'F');
      doc.setTextColor(255, 255, 255);
      doc.setFont('helvetica', 'bold');
      doc.setFontSize(18);
      doc.text(pack.title || 'OpenShift architecture pack', margin, 28);
      doc.setFont('helvetica', 'normal');
      doc.setFontSize(9.5);
      doc.text(`${documentLabel} · Senior Red Hat OpenShift architect`, margin, 45);
      doc.setTextColor(15, 23, 42);
      if (sectionTitle) {
        doc.setFont('helvetica', 'bold');
        doc.setFontSize(15);
        doc.text(sectionTitle, margin, 88);
      }
      if (sectionSubtitle) {
        doc.setFont('helvetica', 'normal');
        doc.setFontSize(10.5);
        const lines = doc.splitTextToSize(sectionSubtitle, contentWidth);
        doc.text(lines, margin, 106);
      }
    };

    const paintFooter = (pageNumber, totalPages) => {
      doc.setDrawColor(203, 213, 225);
      doc.line(margin, footerY - 10, pageWidth - margin, footerY - 10);
      doc.setFont('helvetica', 'normal');
      doc.setFontSize(9);
      doc.setTextColor(71, 85, 105);
      doc.text(`Generated ${generatedAt.toLocaleString()} · ${documentLabel} pack`, margin, footerY);
      doc.text(`Page ${pageNumber} of ${totalPages}`, pageWidth - margin, footerY, { align: 'right' });
    };

    let cursorY = 130;
    const resetPage = (title, subtitle = '') => {
      paintHeader(title, subtitle);
      cursorY = subtitle ? 136 + (doc.splitTextToSize(subtitle, contentWidth).length * 12) : 130;
    };
    const ensureSpace = (height, continuationTitle = '') => {
      if (cursorY + height <= pageHeight - 48) {
        return;
      }
      doc.addPage();
      resetPage(continuationTitle || 'Continued architecture narrative');
    };
    const addParagraph = (text, { fontSize = 11.5, leading = 16, indent = 0, bullet = false } = {}) => {
      const clean = stripHtml(text);
      if (!clean) return;
      doc.setFont('helvetica', bullet ? 'normal' : 'normal');
      doc.setFontSize(fontSize);
      doc.setTextColor(15, 23, 42);
      const wrapped = doc.splitTextToSize(clean, contentWidth - indent - (bullet ? 14 : 0));
      ensureSpace((wrapped.length * leading) + 10, 'Continued architecture narrative');
      if (bullet) {
        doc.text('•', margin + indent, cursorY);
      }
      doc.text(wrapped, margin + indent + (bullet ? 12 : 0), cursorY);
      cursorY += (wrapped.length * leading) + 8;
    };
    const addSectionTitle = (title) => {
      ensureSpace(40, 'Continued architecture narrative');
      doc.setFillColor(239, 246, 255);
      doc.roundedRect(margin, cursorY - 18, contentWidth, 28, 10, 10, 'F');
      doc.setTextColor(30, 64, 175);
      doc.setFont('helvetica', 'bold');
      doc.setFontSize(13);
      doc.text(title, margin + 12, cursorY);
      cursorY += 24;
    };

    doc.setFillColor(8, 47, 73);
    doc.rect(0, 0, pageWidth, pageHeight, 'F');
    doc.setFillColor(34, 211, 238);
    doc.circle(pageWidth - 72, 72, 86, 'F');
    doc.setTextColor(255, 255, 255);
    doc.setFont('helvetica', 'bold');
    doc.setFontSize(26);
    doc.text(pack.title || 'OpenShift architecture pack', margin, 88, { maxWidth: contentWidth - 80 });
    doc.setFont('helvetica', 'normal');
    doc.setFontSize(13);
    doc.text(pack.summary || 'Enterprise OpenShift architecture handoff pack.', margin, 128, { maxWidth: contentWidth - 80 });
    doc.setFillColor(255, 255, 255);
    doc.roundedRect(margin, 174, contentWidth, 124, 18, 18, 'F');
    doc.setTextColor(15, 23, 42);
    doc.setFont('helvetica', 'bold');
    doc.setFontSize(14);
    doc.text('Pack metadata', margin + 16, 198);
    doc.setFont('helvetica', 'normal');
    doc.setFontSize(11.5);
    [
      `Document type: ${documentLabel}`,
      `Pattern: ${diagramResult?.planning?.pattern_label || 'OpenShift architecture'}`,
      `Architect profile: ${diagramResult?.planning?.architect_profile || 'Senior Red Hat OpenShift architect'}`,
      `Version baseline: ${diagramResult?.planning?.version_baseline || 'OpenShift 4.20+'}`,
      `Estimated pages: ${pack.estimated_page_count || 'n/a'} (target ${pack.target_page_count || 'n/a'})`,
      `Diagram pages: ${pagePreviews.length || 0}`,
    ].forEach((line, index) => doc.text(line, margin + 16, 224 + (index * 16), { maxWidth: contentWidth - 32 }));

    if (pagePreviews[0]?.svg || pagePreviews[0]?.png_base64) {
      try {
        const coverImage = await getPreviewImageData(pagePreviews[0]);
        doc.addImage(coverImage, 'PNG', margin, 330, contentWidth, 270, undefined, 'FAST');
      } catch {
        // ignore cover image conversion failures and still export the pack
      }
    }
    doc.setFont('helvetica', 'italic');
    doc.setFontSize(10);
    doc.text('Holistic architecture preview on cover; detailed page atlas follows.', margin, 620);

    doc.addPage();
    resetPage('Diagram atlas', 'The architecture pack is intentionally multi-page so reviewers can move from holistic view to explanation, component view, perimeter, service placement, infrastructure, and resilience lenses.');
    for (const preview of pagePreviews) {
      doc.addPage();
      resetPage(`${preview.page_number}. ${preview.page_name}`, preview.summary || preview.title || 'Architecture page preview');
      doc.setFillColor(248, 250, 252);
      doc.roundedRect(margin, cursorY, contentWidth, 430, 18, 18, 'F');
      try {
        const imageData = await getPreviewImageData(preview);
        doc.addImage(imageData, 'PNG', margin + 12, cursorY + 12, contentWidth - 24, 406, undefined, 'FAST');
      } catch {
        doc.setTextColor(71, 85, 105);
        doc.setFont('helvetica', 'normal');
        doc.setFontSize(11);
        doc.text('Preview image could not be rendered in-browser for this page, but the draw.io pack still contains the editable source.', margin + 16, cursorY + 24, { maxWidth: contentWidth - 32 });
      }
      cursorY += 454;
      addParagraph(`Layout mode: ${preview.layout_mode || 'grouped'}.`, { fontSize: 10.5, leading: 14 });
    }

    doc.addPage();
    resetPage('Document outline', 'Major sections included in this generated handoff pack.');
    (pack.sections || []).slice(0, 24).forEach((section, index) => addParagraph(`${index + 1}. ${section.title}`, { fontSize: 11, leading: 14, bullet: false }));

    doc.addPage();
    resetPage('Design summary and decision frame', 'High-level context used to structure the shared architecture pack and the separate HLD / LLD narratives.');
    addSectionTitle('Assumptions');
    (pack.assumptions || []).forEach((line) => addParagraph(line, { bullet: true }));
    addSectionTitle('Architectural decisions');
    (pack.decision_rows || []).forEach((row) => {
      addParagraph(`${row.title}: ${row.decision}`, { bullet: true });
      addParagraph(`Rationale: ${row.rationale}`, { fontSize: 10.5, leading: 14, indent: 14 });
      addParagraph(`Consequence: ${row.consequences}`, { fontSize: 10.5, leading: 14, indent: 14 });
    });
    addSectionTitle('State views');
    (pack.state_views || []).forEach((view) => {
      addParagraph(`${view.title}: ${view.summary}`, { bullet: true });
      (view.bullets || []).forEach((line) => addParagraph(line, { fontSize: 10.5, leading: 14, indent: 14, bullet: true }));
    });

    for (const section of (pack.sections || [])) {
      doc.addPage();
      resetPage(section.title, pack.summary || 'Generated architecture narrative');
      (section.body || []).forEach((line) => addParagraph(line, { bullet: /^[-•]/.test(String(line).trim()) }));
    }

    const totalPages = doc.getNumberOfPages();
    for (let page = 1; page <= totalPages; page += 1) {
      doc.setPage(page);
      paintFooter(page, totalPages);
    }

    doc.save(`${slugify(pack.title || activeDocument, activeDocument)}-${activeDocument}-${createTimestampSlug()}.pdf`);
  }

  function StatusMessage({ state }) {
    if (!state?.message) return null;
    return h('div', { className: `agent-console__status${state.tone ? ` agent-console__status--${state.tone}` : ''}` }, state.message);
  }

  function ArchitectApp() {
    const viewerFrameRef = useRef(null);
    const viewerInitializedRef = useRef(false);
    const latestDrawioXmlRef = useRef('');
    const [catalog, setCatalog] = useState({ templates: [], supported_assessment_scopes: [] });
    const [knowledgeStatus, setKnowledgeStatus] = useState(null);
    const [knowledgeSources, setKnowledgeSources] = useState([]);
    const [providerCatalog, setProviderCatalog] = useState(llmRuntime.fallbackCatalog || { providers: [] });
    const [modelCatalog, setModelCatalog] = useState({ configured_model_name: '', models: [] });
    const [modelsLoading, setModelsLoading] = useState(false);
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
    const [activeDiagramPage, setActiveDiagramPage] = useState(0);
    const [liveState, setLiveState] = useState(null);
    const [suggestedTemplateApplied, setSuggestedTemplateApplied] = useState(false);
    const [viewerLoaded, setViewerLoaded] = useState(false);
    const [viewerStatus, setViewerStatus] = useState('Generate a diagram to render the editable draw.io preview directly in the browser.');

    const selectedTemplate = useMemo(() => (catalog.templates || []).find((item) => item.id === templateId) || (catalog.templates || [])[0] || null, [catalog.templates, templateId]);
    const suggestedModels = useMemo(() => (llmRuntime.getSuggestedModels ? llmRuntime.getSuggestedModels(providerCatalog, providerId, modelCatalog) : []), [providerCatalog, providerId, modelCatalog]);
    const documentPack = useMemo(() => diagramResult?.documents?.[activeDocument] || assessmentResult?.assessment || null, [diagramResult, assessmentResult, activeDocument]);
    const diagramPagePreviews = useMemo(() => {
      const previews = Array.isArray(diagramResult?.artifacts?.page_previews) ? diagramResult.artifacts.page_previews : [];
      if (previews.length) return previews;
      if (diagramResult?.artifacts?.svg || diagramResult?.artifacts?.svg_preview) {
        return [{
          page_number: 1,
          page_name: diagramResult?.artifacts?.preview_page_name || 'Architecture preview',
          layout_mode: 'grouped',
          title: diagramResult?.diagram?.title || 'Architecture preview',
          summary: diagramResult?.diagram?.summary || '',
          svg: diagramResult?.artifacts?.svg || diagramResult?.artifacts?.svg_preview || '',
        }];
      }
      return [];
    }, [diagramResult]);
    const activeDiagramPreview = useMemo(() => diagramPagePreviews[activeDiagramPage] || diagramPagePreviews[0] || null, [diagramPagePreviews, activeDiagramPage]);
    const ollamaOptionMap = useMemo(() => {
      const options = new Map();
      const catalogModels = Array.isArray(modelCatalog?.models) ? modelCatalog.models : [];
      catalogModels.forEach((model) => {
        const name = model?.name || model?.model;
        if (!name) return;
        const suffix = [model.loaded ? 'loaded' : '', model.parameter_size || ''].filter(Boolean).join(' · ');
        options.set(name, suffix ? `${name} · ${suffix}` : name);
      });
      suggestedModels.forEach((name) => {
        if (name && !options.has(name)) {
          options.set(name, name);
        }
      });
      const fallbackModel = modelName || modelCatalog?.configured_model_name || providerCatalog?.configured_model_name || '';
      if (fallbackModel && !options.has(fallbackModel)) {
        options.set(fallbackModel, fallbackModel);
      }
      return options;
    }, [modelCatalog, suggestedModels, modelName, providerCatalog]);
    const preferredOllamaModel = useMemo(() => pickPreferredOllamaModel(modelCatalog), [modelCatalog]);
    const selectedOllamaModel = useMemo(() => {
      if (modelName && ollamaOptionMap.has(modelName)) {
        return modelName;
      }
      return preferredOllamaModel || '';
    }, [modelName, ollamaOptionMap, preferredOllamaModel]);

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
          setModelName(resolvedProviderId === 'ollama' ? '' : (catalogPayload.configured_model_name || ''));
          setExternalModelName(catalogPayload.configured_model_name || '');
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

    const refreshModels = async (baseUrl = ollamaBaseUrl) => {
      if ((llmRuntime.normalizeProviderId?.(providerCatalog, providerId) || 'ollama') !== 'ollama') {
        setModelsLoading(false);
        return;
      }
      setModelsLoading(true);
      try {
        const payload = await fetchOllamaModels(baseUrl || '');
        setModelCatalog(payload);
        setModelName((current) => {
          const availableNames = Array.isArray(payload.models) ? payload.models.map((model) => model?.name || model?.model).filter(Boolean) : [];
          if (current && availableNames.includes(current)) {
            return current;
          }
          return pickPreferredOllamaModel(payload) || current || '';
        });
      } catch (error) {
        setStatus({ message: error instanceof Error ? error.message : 'Unable to load available Ollama models.', tone: 'error' });
      } finally {
        setModelsLoading(false);
      }
    };

    useEffect(() => {
      if ((llmRuntime.normalizeProviderId?.(providerCatalog, providerId) || 'ollama') === 'ollama') {
        refreshModels(ollamaBaseUrl);
      }
    }, [providerCatalog, providerId, ollamaBaseUrl]);

    useEffect(() => {
      if ((llmRuntime.normalizeProviderId?.(providerCatalog, providerId) || 'ollama') !== 'ollama') {
        return;
      }
      if (selectedOllamaModel && selectedOllamaModel !== modelName) {
        setModelName(selectedOllamaModel);
      }
    }, [providerCatalog, providerId, selectedOllamaModel, modelName]);

    useEffect(() => {
      const provider = llmRuntime.getProvider?.(providerCatalog, providerId) || providerCatalog?.providers?.[0];
      if (!provider || provider.id === 'ollama') {
        return;
      }
      setExternalModelName((current) => current || provider.default_model || providerCatalog?.configured_model_name || '');
      setExternalBaseUrl((current) => current || provider.default_base_url || '');
      setExternalApiVersion((current) => current || provider.default_api_version || '');
    }, [providerCatalog, providerId]);

    useEffect(() => {
      if (!selectedTemplate || suggestedTemplateApplied) return;
      setPrompt((current) => current || selectedTemplate.prompt || '');
    }, [selectedTemplate, suggestedTemplateApplied]);

    useEffect(() => {
      setActiveDiagramPage(0);
    }, [diagramResult]);

    const loadEmbeddedViewer = (drawioXml) => {
      const targetWindow = viewerFrameRef.current?.contentWindow;
      if (!viewerInitializedRef.current || !targetWindow || !drawioXml) {
        return false;
      }

      setViewerLoaded(false);
      setViewerStatus('Rendering the editable draw.io preview from the generated architecture pack…');
      targetWindow.postMessage(JSON.stringify({
        action: 'load',
        xml: drawioXml,
        autosave: 0,
        saveAndExit: 0,
        noSaveBtn: 1,
        noExitBtn: 1,
        modified: 0,
        title: 'OpenShift architecture draw.io preview',
        border: 24,
        background: '#ffffff',
      }), DRAWIO_EMBED_ORIGIN);
      return true;
    };

    useEffect(() => {
      const onMessage = (event) => {
        if (event.origin !== DRAWIO_EMBED_ORIGIN) {
          return;
        }

        let payload = event.data;
        if (typeof payload === 'string') {
          try {
            payload = JSON.parse(payload);
          } catch {
            return;
          }
        }
        if (!payload || typeof payload !== 'object') {
          return;
        }

        if (payload.event === 'init' || payload.event === 'ready') {
          viewerInitializedRef.current = true;
          if (!latestDrawioXmlRef.current) {
            setViewerStatus('Generate a diagram to render the editable draw.io preview directly in the browser.');
            return;
          }
          loadEmbeddedViewer(latestDrawioXmlRef.current);
          return;
        }

        if (payload.event === 'load') {
          setViewerLoaded(true);
          setViewerStatus('Editable draw.io preview rendered successfully from the generated architecture pack.');
          return;
        }

        if (payload.error) {
          setViewerLoaded(false);
          setViewerStatus('The embedded draw.io preview is unavailable in this session. The SVG page preview remains available below.');
        }
      };

      window.addEventListener('message', onMessage);
      return () => window.removeEventListener('message', onMessage);
    }, []);

    useEffect(() => {
      const drawioXml = diagramResult?.artifacts?.drawio_xml || '';
      latestDrawioXmlRef.current = drawioXml;
      if (!drawioXml) {
        setViewerLoaded(false);
        setViewerStatus('Generate a diagram to render the editable draw.io preview directly in the browser.');
        return;
      }
      loadEmbeddedViewer(drawioXml);
    }, [diagramResult]);

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
      setStatus({ message: 'Generating the shared OpenShift architecture pack plus separate HLD and LLD documents…', tone: '' });
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
        setActiveDiagramPage(0);
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

    const exportDocument = async (kind) => {
      const pack = documentPack;
      if (!pack) {
        setStatus({ message: 'Generate a document pack first before exporting.', tone: 'error' });
        return;
      }
      const generatedAt = new Date();
      const markdown = [
        `# ${pack.title || 'OpenShift architecture pack'}`,
        '',
        ...(pack.sections || []).flatMap((section) => [`## ${section.title}`, '', ...(section.body || []), ''])
      ].join('\n');
      const baseFilename = `${slugify(pack.title || activeDocument, activeDocument)}-${createTimestampSlug()}`;
      try {
        if (kind === 'md') {
          downloadBlob(`${baseFilename}.md`, new Blob([markdown], { type: 'text/markdown;charset=utf-8' }));
        } else if (kind === 'doc') {
          const html = [
            '<!doctype html><html><body style="font-family:Segoe UI,Arial,sans-serif;padding:32px;color:#0f172a;">',
            `<h1>${escapeHtmlValue(pack.title || 'OpenShift architecture pack')}</h1>`,
            `<p>${escapeHtmlValue(pack.summary || '')}</p>`,
            ...(pack.sections || []).flatMap((section) => [
              `<h2>${escapeHtmlValue(section.title)}</h2>`,
              ...(section.body || []).map((line) => `<p>${escapeHtmlValue(stripHtml(line))}</p>`),
            ]),
            '</body></html>'
          ].join('');
          downloadBlob(`${baseFilename}.doc`, new Blob([html], { type: 'application/msword' }));
        } else if (kind === 'pdf') {
          await buildArchitectPdf({ pack, diagramResult, activeDocument, generatedAt });
        } else if (kind === 'ppt') {
          const PptxGenJS = window.PptxGenJS;
          if (!PptxGenJS) throw new Error('PowerPoint export is not available in this browser session.');
          const pptx = new PptxGenJS();
          pptx.layout = 'LAYOUT_WIDE';
          const slide = pptx.addSlide();
          slide.addText(pack.title || 'OpenShift architecture pack', { x: 0.4, y: 0.3, w: 12.2, h: 0.4, fontSize: 24, bold: true, color: '0F172A' });
          slide.addText(markdown, { x: 0.4, y: 0.85, w: 12.2, h: 6.0, fontSize: 10.5, color: '334155', margin: 0.08, valign: 'top' });
          if (activeDiagramPreview?.svg) {
            try {
              const pngDataUrl = await svgMarkupToPngDataUrl(activeDiagramPreview.svg);
              slide.addImage({ data: pngDataUrl, x: 7.75, y: 0.55, w: 4.55, h: 2.7 });
            } catch {
              // keep PowerPoint export resilient even when browser rasterization is unavailable
            }
          }
          pptx.writeFile({ fileName: `${baseFilename}.pptx` });
        }
        setStatus({ message: `Exported the ${activeDocument.toUpperCase()} pack as ${kind.toUpperCase()}.`, tone: 'ok' });
      } catch (error) {
        setStatus({ message: error instanceof Error ? error.message : 'Unable to export the document pack.', tone: 'error' });
      }
    };

    const exportArtifact = async (kind) => {
      if (!diagramResult?.artifacts) {
        setStatus({ message: 'Generate a diagram first before exporting artifacts.', tone: 'error' });
        return;
      }
      const artifacts = diagramResult.artifacts;
      try {
        if (kind === 'drawio') {
          downloadBlob(artifacts.filenames?.drawio || 'openshift-architecture.drawio', new Blob([artifacts.drawio_xml || ''], { type: 'application/xml;charset=utf-8' }));
        } else if (kind === 'svg') {
          downloadBlob(
            activeDiagramPreview ? diagramFilename(activeDiagramPreview.page_name, 'svg') : (artifacts.filenames?.svg || 'openshift-architecture.svg'),
            new Blob([activeDiagramPreview?.svg || artifacts.svg || artifacts.svg_preview || ''], { type: 'image/svg+xml;charset=utf-8' })
          );
        } else if (kind === 'png') {
          if (activeDiagramPreview?.svg) {
            const dataUrl = await svgMarkupToPngDataUrl(activeDiagramPreview.svg);
            downloadBlob(diagramFilename(activeDiagramPreview.page_name, 'png'), dataUrlToBlob(dataUrl));
          } else if (artifacts.png_base64) {
            const binary = atob(artifacts.png_base64);
            const bytes = Uint8Array.from(binary, (char) => char.charCodeAt(0));
            downloadBlob(artifacts.filenames?.png || 'openshift-architecture.png', new Blob([bytes], { type: 'image/png' }));
          } else {
            throw new Error('PNG export is not available in this result.');
          }
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
            h('h2', null, 'Create a shared OpenShift architecture pack with separate HLD and LLD outputs, live-state grounding, research-link ingestion, and editable draw.io output.'),
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
              h('button', { className: 'agent-console__button', type: 'button', disabled: busy, onClick: generateDiagram }, busy ? 'Generating…' : 'Generate architecture pack')
            ]),
            h('details', null, [
              h('summary', null, 'Runtime overrides'),
              h('div', { className: 'architect-console__grid' }, [
                h('label', { className: 'agent-console__label' }, ['LLM provider', h('select', { className: 'agent-console__input', value: providerId, onChange: (event) => setProviderId(event.target.value) }, (providerCatalog.providers || []).map((provider) => h('option', { key: provider.id, value: provider.id }, provider.label || provider.id)))]),
                providerId === 'ollama'
                  ? h('label', { className: 'agent-console__label' }, ['Ollama base URL', h('input', { className: 'agent-console__input', value: ollamaBaseUrl, onChange: (event) => setOllamaBaseUrl(event.target.value), placeholder: 'http://host.containers.internal:11434' })])
                  : h('label', { className: 'agent-console__label' }, ['Hosted base URL', h('input', { className: 'agent-console__input', value: externalBaseUrl, onChange: (event) => setExternalBaseUrl(event.target.value), placeholder: 'https://api.openai.com/v1' })]),
                providerId === 'ollama'
                  ? h('label', { className: 'agent-console__label' }, ['Local model', h('div', { className: 'finops-settings__model-picker' }, [
                      h('select', { className: 'agent-console__input', value: selectedOllamaModel, onChange: (event) => setModelName(event.target.value), disabled: modelsLoading && ollamaOptionMap.size === 0 }, Array.from(ollamaOptionMap.entries()).map(([value, label]) => h('option', { key: value, value }, label))),
                      h('button', { className: 'agent-console__example', type: 'button', onClick: () => refreshModels(ollamaBaseUrl), disabled: modelsLoading }, modelsLoading ? 'Refreshing…' : 'Refresh')
                    ])])
                  : h('label', { className: 'agent-console__label' }, ['Hosted model', h('input', { className: 'agent-console__input', value: externalModelName, list: 'architect-suggested-models', onChange: (event) => setExternalModelName(event.target.value), placeholder: suggestedModels[0] || 'model name' }), h('datalist', { id: 'architect-suggested-models' }, suggestedModels.map((model) => h('option', { key: model, value: model }))) ]),
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
        h('article', { className: 'architect-console__page-preview' }, [
          h('div', { className: 'agent-console__queue-header' }, [
            h('div', null, [
              h('h3', null, 'Embedded draw.io preview'),
              h('p', { className: 'architect-console__meta' }, viewerStatus)
            ]),
            h('div', { className: 'architect-console__artifact-actions' }, [
              h('span', { className: 'architect-console__artifact-pill' }, 'Source: generated draw.io XML'),
              h('span', { className: 'architect-console__artifact-pill' }, viewerLoaded ? 'Viewer rendered' : 'Viewer waiting / fallback active')
            ])
          ]),
          diagramResult?.artifacts?.drawio_xml
            ? h('div', { className: 'architect-console__viewer-shell' }, [
                h('iframe', {
                  ref: viewerFrameRef,
                  className: 'architect-console__viewer-frame',
                  src: DRAWIO_EMBED_URL,
                  title: 'OpenShift architecture draw.io preview',
                  loading: 'lazy',
                  referrerPolicy: 'no-referrer',
                })
              ])
            : h('div', { className: 'architect-console__empty' }, 'Generate a diagram to render the editable draw.io preview directly in the browser.'),
          diagramResult?.artifacts?.drawio_xml
            ? h('details', { className: 'architect-console__card' }, [
                h('summary', null, 'Show draw.io XML'),
                h('pre', { className: 'architect-console__json' }, diagramResult.artifacts.drawio_xml || '')
              ])
            : null
        ]),
        h('div', { className: 'architect-console__diagram-shell' }, [
          h('aside', { className: 'architect-console__page-rail' }, diagramPagePreviews.length ? diagramPagePreviews.map((page, index) => h('button', {
            key: `${page.page_number}-${page.page_name}`,
            type: 'button',
            className: `architect-console__page-button ${index === activeDiagramPage ? 'is-active' : ''}`,
            onClick: () => setActiveDiagramPage(index)
          }, [
            h('span', { className: 'architect-console__page-index' }, `Page ${page.page_number}`),
            h('strong', null, page.page_name),
            h('span', { className: 'architect-console__meta' }, page.layout_mode || 'diagram')
          ])) : h('div', { className: 'architect-console__empty' }, 'Generate a diagram to browse the full multi-page draw.io-style architecture pack.')),
          h('div', { className: 'architect-console__page-preview' }, activeDiagramPreview ? [
            h('div', { className: 'agent-console__queue-header' }, [
              h('div', null, [
                h('h3', null, activeDiagramPreview.page_name),
                h('p', { className: 'architect-console__meta' }, activeDiagramPreview.summary || activeDiagramPreview.title || 'Selected architecture page preview.')
              ]),
              h('div', { className: 'architect-console__artifact-actions' }, [
                h('span', { className: 'architect-console__badge architect-console__badge--ok' }, `${diagramPagePreviews.length} pages`),
                h('span', { className: 'architect-console__artifact-pill' }, 'SVG fallback / page rail preview')
              ])
            ]),
            h('div', { className: 'architect-console__diagram' }, h('div', { dangerouslySetInnerHTML: { __html: activeDiagramPreview.svg } }))
          ] : h('div', { className: 'architect-console__empty' }, 'Generate a diagram to see the architecture preview here.'))
        ])
      ]),

      h('section', { className: 'agent-console__panel', id: 'architect-documents' }, [
        h('div', { className: 'agent-console__queue-header' }, [h('div', null, [h('h2', null, 'Architecture documents and assessment packs'), h('p', { className: 'architect-console__meta' }, 'Review the shared architecture pack context, then switch between the separate HLD, LLD, and assessment outputs for export as markdown, Word-compatible output, PDF, or PowerPoint.')]), h('div', { className: 'architect-console__tabs' }, [h('button', { type: 'button', className: `architect-console__tab ${activeDocument === 'hld' ? 'is-active' : ''}`, onClick: () => setActiveDocument('hld') }, 'HLD'), h('button', { type: 'button', className: `architect-console__tab ${activeDocument === 'lld' ? 'is-active' : ''}`, onClick: () => setActiveDocument('lld') }, 'LLD'), h('button', { type: 'button', className: `architect-console__tab ${activeDocument === 'assessment' ? 'is-active' : ''}`, onClick: () => setActiveDocument('assessment') }, 'Assessment')])]),
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
            h('p', { className: 'architect-console__helper' }, activeDiagramPreview ? `Exports will use the currently selected page: ${activeDiagramPreview.page_name}.` : 'Generate a diagram to export the currently selected preview page as SVG or PNG, or download the full editable draw.io pack.')
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
