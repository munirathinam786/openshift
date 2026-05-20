(async () => {
  const root = document.querySelector('[data-agent-console]');
  if (!root) {
    return;
  }

  const promptInput = root.querySelector('textarea[data-agent-prompt]');
  const runButton = root.querySelector('[data-agent-run]');
  const status = root.querySelector('[data-agent-status]');
  const answer = root.querySelector('[data-agent-answer]');
  const approvalPanel = root.querySelector('[data-agent-approval-panel]');
  const approvalOptions = root.querySelector('[data-agent-approval-options]');
  const approvalApplyButton = root.querySelector('[data-agent-approval-apply]');
  const cards = root.querySelector('[data-agent-cards]');
  const tables = root.querySelector('[data-agent-tables]');
  const finopsOverview = root.querySelector('[data-agent-finops-overview]');
  const finopsSavings = root.querySelector('[data-agent-finops-savings]');
  const finopsActions = root.querySelector('[data-agent-finops-actions]');
  const finopsQueue = root.querySelector('[data-agent-finops-queue]');
  const finopsAutoApproveInput = root.querySelector('[data-agent-finops-auto-approve]');
  const runtimeSummary = root.querySelector('[data-agent-runtime-summary]');
  const runtimeContainers = root.querySelector('[data-agent-runtime-containers]');
  const runtimeDatabase = root.querySelector('[data-agent-runtime-database]');
  const historySummary = root.querySelector('[data-agent-history-summary]');
  const historyTrends = root.querySelector('[data-agent-history-trends]');
  const historyRuns = root.querySelector('[data-agent-history-runs]');
  const steps = root.querySelector('[data-agent-steps]');
  const promptButtons = root.querySelectorAll('button[data-agent-prompt], button[data-agent-example]');
  const llmRuntime = window.OpenShiftSreLlmRuntime || window.AwsSreLlmRuntime || {};
  const llmProviderInput = root.querySelector('[data-agent-llm-provider]');
  const ollamaBaseUrlInput = root.querySelector('[data-agent-ollama-base-url]');
  const modelNameInput = root.querySelector('[data-agent-model-name]');
  const externalModelNameInput = root.querySelector('[data-agent-external-model-name]');
  const externalBaseUrlInput = root.querySelector('[data-agent-external-base-url]');
  const externalApiKeyInput = root.querySelector('[data-agent-external-api-key]');
  const externalApiVersionInput = root.querySelector('[data-agent-external-api-version]');
  const externalOrganizationInput = root.querySelector('[data-agent-external-organization]');
  const llmProviderNote = root.querySelector('[data-agent-llm-provider-note]');
  const ollamaFieldGroups = root.querySelectorAll('[data-agent-ollama-field]');
  const externalLlmFieldGroups = root.querySelectorAll('[data-agent-external-llm-field]');
  const clusterScopeInput = root.querySelector('[data-agent-cluster-scope]');
  const kubeContextInput = root.querySelector('[data-agent-kube-context]');
  const openshiftApiUrlInput = root.querySelector('[data-agent-openshift-api-url]');
  const openshiftTokenInput = root.querySelector('[data-agent-openshift-token]');
  const openshiftNamespaceInput = root.querySelector('[data-agent-openshift-namespace]');
  const verifySslInput = root.querySelector('[data-agent-verify-ssl]');
  let modelRefreshHandle = null;
  let providerCatalog = llmRuntime.fallbackCatalog || {
    configured_provider: 'ollama',
    configured_model_name: 'gpt-oss:20b',
    providers: [{ id: 'ollama', label: 'Local Ollama', default_model: 'gpt-oss:20b', default_base_url: 'http://localhost:11434', description: 'Use the local Ollama runtime already supported by the stack.', supports_catalog_refresh: true, suggested_models: ['gpt-oss:20b'] }]
  };
  const troubleshootingSelect = root.querySelector('[data-agent-troubleshooting-scenario]');
  const troubleshootingDetails = root.querySelector('[data-agent-troubleshooting-details]');
  const loadTroubleshootingButton = root.querySelector('[data-agent-load-troubleshooting]');
  const autoLoadTroubleshooting = root.dataset.agentAutoLoadTroubleshooting === 'true';
  const serviceFilterInput = root.querySelector('[data-agent-service-filter]');
  const symptomInput = root.querySelector('[data-agent-symptom]');
  const severityInput = root.querySelector('[data-agent-severity]');
  const environmentInput = root.querySelector('[data-agent-environment]');
  const blastRadiusInput = root.querySelector('[data-agent-blast-radius]');
  const timeWindowInput = root.querySelector('[data-agent-time-window]');
  const issueStartInput = root.querySelector('[data-agent-issue-start]');
  const lastHealthyInput = root.querySelector('[data-agent-last-healthy]');
  const recentChangeInput = root.querySelector('[data-agent-recent-change]');
  const primaryResourceInput = root.querySelector('[data-agent-primary-resource]');
  const affectedScopeInput = root.querySelector('[data-agent-affected-scope]');
  const healthyResourceInput = root.querySelector('[data-agent-healthy-resource]');
  const unhealthyResourceInput = root.querySelector('[data-agent-unhealthy-resource]');
  const resourceIdsInput = root.querySelector('[data-agent-resource-ids]');
  const issueNotesInput = root.querySelector('[data-agent-issue-notes]');
  const evidenceChecklist = root.querySelector('[data-agent-evidence-checklist]');
  const commandHints = root.querySelector('[data-agent-command-hints]');
  const runbooks = root.querySelector('[data-agent-runbooks]');
  const rootCauseCards = root.querySelector('[data-agent-root-causes]');
  const nextActionCards = root.querySelector('[data-agent-next-actions]');
  const presetNameInput = root.querySelector('[data-agent-preset-name]');
  const presetSelect = root.querySelector('[data-agent-preset-select]');
  const presetSaveButton = root.querySelector('[data-agent-preset-save]');
  const presetLoadButton = root.querySelector('[data-agent-preset-load]');
  const presetDeleteButton = root.querySelector('[data-agent-preset-delete]');
  const refreshWorkflowButton = root.querySelector('[data-agent-refresh-workflow]');
  const managementTabButtons = root.querySelectorAll('[data-agent-management-tab]');
  const managementPanels = root.querySelectorAll('[data-agent-management-panel]');
  const incidentPhaseInput = root.querySelector('[data-agent-incident-phase]');
  const incidentTypeInput = root.querySelector('[data-agent-incident-type]');
  const communicationsStatusInput = root.querySelector('[data-agent-communications-status]');
  const stakeholderAudienceInput = root.querySelector('[data-agent-stakeholder-audience]');
  const restorationStatusInput = root.querySelector('[data-agent-restoration-status]');
  const incidentOwnerInput = root.querySelector('[data-agent-incident-owner]');
  const customerImpactInput = root.querySelector('[data-agent-customer-impact]');
  const businessImpactInput = root.querySelector('[data-agent-business-impact]');
  const changeTypeInput = root.querySelector('[data-agent-change-type]');
  const changeRiskInput = root.querySelector('[data-agent-change-risk]');
  const changeApprovalInput = root.querySelector('[data-agent-change-approval]');
  const changeImplementationInput = root.querySelector('[data-agent-change-implementation]');
  const rollbackReadinessInput = root.querySelector('[data-agent-rollback-readiness]');
  const changeWindowInput = root.querySelector('[data-agent-change-window]');
  const changeSummaryInput = root.querySelector('[data-agent-change-summary]');
  const problemRecordInput = root.querySelector('[data-agent-problem-record]');
  const problemRecurrenceInput = root.querySelector('[data-agent-problem-recurrence]');
  const rcaMethodInput = root.querySelector('[data-agent-rca-method]');
  const rootCauseDomainInput = root.querySelector('[data-agent-root-cause-domain]');
  const knownErrorStatusInput = root.querySelector('[data-agent-known-error-status]');
  const correctiveOwnerInput = root.querySelector('[data-agent-corrective-owner]');
  const problemNotesInput = root.querySelector('[data-agent-problem-notes]');
  const reportExportButtons = root.querySelectorAll('[data-agent-export-report]');
  const reportStatus = root.querySelector('[data-agent-report-status]');
  const consoleReportExportButtons = root.querySelectorAll('[data-agent-console-export-report]');
  const consoleReportStatus = root.querySelector('[data-agent-console-report-status]');
  const FINOPS_TOOL_NAMES = new Set([
    'list_cost_and_usage_summary',
    'list_cost_by_service',
    'list_cost_by_tag',
    'get_cost_forecast',
    'list_savings_plans_coverage',
    'list_rightsizing_recommendations'
  ]);
  const TROUBLESHOOTING_SCENARIOS = [
    {
      id: 'general-incident-triage',
      category: 'Core triage',
      label: 'General incident triage',
      summary: 'Start broad when the symptom is real but the failing OpenShift domain is still fuzzy.',
      symptoms: ['Customer impact is reported but the owning team is not yet sure whether the issue is control plane, worker, ingress, storage, or workload related.', 'Multiple alerts or dashboards look noisy and you need the shortest path to a likely failure domain.'],
      evidenceSources: ['Cluster operator health and warning events', 'Recent rollout, upgrade, or configuration changes', 'Top-level dependencies across nodes, workloads, routes, storage, and operator lifecycle'],
      checks: ['Confirm the first bad timestamp and blast radius.', 'Compare healthy versus unhealthy nodes, namespaces, routes, or worker pools.', 'List the next safe validation steps if the first hypothesis is wrong.'],
      prompt: 'Act as an OpenShift incident commander for read-only troubleshooting. Investigate the operator issue by gathering evidence from cluster operators, warning events, rollout changes, node state, and major upstream or downstream dependencies. Return: 1) likely root cause, 2) evidence collected, 3) blast radius, 4) immediate next safe checks, and 5) deeper follow-up checks if the first hypothesis is wrong.'
    },
    {
      id: 'route-ingress-connectivity',
      category: 'Networking',
      label: 'Route / ingress / service connectivity',
      summary: 'Investigate north-south or service exposure failures across routes, ingresses, and services.',
      symptoms: ['Routes return 503, TLS handshakes fail, or only some applications are unreachable from outside the cluster.', 'Services appear present but traffic does not reach the expected workload endpoints.'],
      evidenceSources: ['Route admitted status, TLS posture, and wildcard policy', 'Ingress definitions, service selectors, and endpoint exposure posture', 'Recent warning events from routers, backing workloads, or target namespaces'],
      checks: ['Compare healthy versus failing routes, hosts, and namespaces.', 'Validate service selectors, endpoint availability, and route admission state.', 'Correlate recent events with ingress, service, or backing workload changes.'],
      prompt: 'Act as an OpenShift network troubleshooting specialist. Investigate route, ingress, or service connectivity issues by checking route admission state, TLS posture, ingress definitions, service selectors, backing workload readiness, and recent warning events. Return: 1) likely failure path, 2) exact evidence found, 3) blast radius, 4) immediate safe remediation steps for operators, and 5) alternate hypotheses if the first theory does not hold.'
    },
    {
      id: 'operator-degradation',
      category: 'Platform',
      label: 'Cluster operator degradation',
      summary: 'Use when one or more cluster operators are degraded, progressing too long, or blocking upgrades.',
      symptoms: ['Cluster operators report Degraded=True or Progressing=True for an unusual length of time.', 'A recent upgrade, configuration change, or rollout preceded broader cluster instability.'],
      evidenceSources: ['ClusterOperator conditions and messages', 'ClusterVersion desired state and conditions', 'Related warning events and impacted platform namespaces'],
      checks: ['Identify the first degraded or stuck operator and its message.', 'Compare ClusterVersion state with operator progress and failure signals.', 'Determine whether the issue is isolated to one operator or impacts multiple platform areas.'],
      prompt: 'Act as an OpenShift platform troubleshooting specialist. Investigate degraded or stuck cluster operators by checking ClusterOperator conditions, ClusterVersion status, related warning events, and platform namespace health. Return the likely root cause, evidence, blast radius, and safe next steps.'
    },
    {
      id: 'node-pressure-readiness',
      category: 'Workloads',
      label: 'Node readiness / pressure / scheduling issues',
      summary: 'Focus on Ready=False nodes, memory or disk pressure, and scheduling side effects.',
      symptoms: ['Pods stay Pending, workloads evict unexpectedly, or nodes drop from Ready state.', 'Cluster symptoms align to one worker pool, machine set, or specific availability domain.'],
      evidenceSources: ['Node Ready and pressure conditions', 'MachineConfigPool and MachineSet state', 'Recent events tied to node health or workload scheduling'],
      checks: ['Confirm which nodes are NotReady or under pressure.', 'Check whether the issue aligns to one machine set or worker pool.', 'Correlate pending pods and rollout failures with node or machine API signals.'],
      prompt: 'Act as an OpenShift node troubleshooting specialist. Investigate node readiness, pressure, or scheduling issues by checking node conditions, machine config pools, machine sets, workload rollout health, and recent warning events. Return the likely root cause, evidence, blast radius, and safe next steps.'
    },
    {
      id: 'workload-rollout-failures',
      category: 'Workloads',
      label: 'Deployment / StatefulSet / DaemonSet rollout failures',
      summary: 'Trace failing rollouts, CrashLoopBackOff pods, and readiness gaps in managed workloads.',
      symptoms: ['Deployments never become available, stateful workloads stall, or daemonsets are partially ready.', 'Pods restart frequently or remain Pending in one namespace or environment.'],
      evidenceSources: ['Workload desired/available/ready counts', 'Pod phases and restart counts', 'Recent warning events in the impacted namespace'],
      checks: ['Compare desired versus available replica counts.', 'Identify pods with repeated restarts or Pending state.', 'Correlate rollout failures with recent changes, quotas, or node readiness issues.'],
      prompt: 'Act as an OpenShift workload troubleshooting specialist. Investigate rollout failures by checking deployments, statefulsets, daemonsets, jobs, pods, and recent warning events. Return the likely root cause, evidence, blast radius, and safe next steps.'
    },
    {
      id: 'storage-binding-capacity',
      category: 'Storage',
      label: 'Persistent volume binding / storage capacity issues',
      summary: 'Use for Pending PVCs, storage class misalignment, or volume lifecycle risks.',
      symptoms: ['PVCs remain Pending, workloads cannot mount storage, or storage classes behave unexpectedly.', 'Capacity or access-mode mismatches appear during rollout or recovery.'],
      evidenceSources: ['PV and PVC phase, capacity, and access modes', 'StorageClass defaults, provisioners, and expansion support', 'Recent warning events from workloads using storage'],
      checks: ['Identify the first Pending or failed PVC.', 'Compare requested storage and access modes with the selected storage class.', 'Correlate mount or binding problems with workload rollout and node events.'],
      prompt: 'Act as an OpenShift storage troubleshooting specialist. Investigate storage binding or capacity issues by checking PVs, PVCs, storage classes, and recent events tied to affected workloads. Return the likely root cause, evidence, blast radius, and safe next steps.'
    },
    {
      id: 'security-guardrail-review',
      category: 'Security & governance',
      label: 'SCC / network policy / quota guardrail issues',
      summary: 'Use when namespace guardrails, SCC posture, or network isolation may be causing failures or drift.',
      symptoms: ['Workloads fail admission, namespaces lack isolation, or quota pressure blocks deployments.', 'Recent security or governance changes align with rollout or runtime impact.'],
      evidenceSources: ['SecurityContextConstraints privilege posture', 'NetworkPolicy coverage across target namespaces', 'ResourceQuota and ClusterResourceQuota state'],
      checks: ['Identify whether the primary symptom is admission, isolation, or quota exhaustion.', 'Compare protected and unprotected namespaces.', 'Correlate policy or quota pressure with recent workload and operator changes.'],
      prompt: 'Act as an OpenShift security troubleshooting specialist. Investigate guardrail-related failures by checking SecurityContextConstraints, NetworkPolicies, ResourceQuotas, affected workloads, and recent warning events. Return the likely root cause, evidence, blast radius, and safe next steps.'
    },
    {
      id: 'olm-csv-subscription-failures',
      category: 'Operators',
      label: 'OLM subscription / CSV failures',
      summary: 'Use when operators fail to install, upgrade, or reconcile through OLM.',
      symptoms: ['Subscriptions stay unhealthy, CSVs remain Pending or Failed, or operator upgrades stall.', 'Only operator-managed namespaces or platforms are affected after a catalog or channel change.'],
      evidenceSources: ['Subscription state, source, package, and installed CSV', 'CSV phase and display name', 'Related platform symptoms and recent warning events'],
      checks: ['Identify the first unhealthy subscription or failed CSV.', 'Check channel and source alignment for the affected operator.', 'Determine whether the failure is isolated or blocks broader platform functionality.'],
      prompt: 'Act as an OpenShift operator lifecycle troubleshooting specialist. Investigate OLM subscription or CSV failures by checking subscription state, installed CSVs, operator phase, related warning events, and impacted namespaces. Return the likely root cause, evidence, blast radius, and safe next steps.'
    },
    {
      id: 'acm-fleet-governance',
      category: 'Fleet governance',
      label: 'ACM hub / managed cluster / policy drift',
      summary: 'Use when the repository-wide multi-cluster estate looks inconsistent across hub health, managed cluster join state, or governance policy compliance.',
      symptoms: ['Managed clusters stop reporting to the hub, fleet health differs across platform patterns, or governance policy status drifts between clusters.', 'The investigation needs ACM visibility instead of a single-cluster only view.'],
      evidenceSources: ['MultiClusterHub phase, version, and availability', 'ManagedCluster joined / available posture and cluster-set distribution', 'ACM policy remediation action, disabled policies, and compliance state'],
      checks: ['Confirm whether the hub itself is healthy before blaming managed clusters.', 'Compare managed-cluster availability and platform-pattern distribution across ROSA, ARO, IPI, UPI, and IBM Z targets.', 'Identify whether policy drift is caused by disabled policies, noncompliant policy state, or unreachable managed clusters.'],
      prompt: 'Act as an OpenShift fleet governance specialist. Investigate ACM hub, managed-cluster, and governance-policy issues by checking MultiClusterHub availability, ManagedCluster join and available state, cluster infrastructure patterns, and ACM policy compliance or remediation posture. Return the likely root cause, evidence, blast radius, and safe next steps.'
    },
    {
      id: 'acs-security-coverage',
      category: 'Security & compliance',
      label: 'ACS central / secured cluster coverage gaps',
      summary: 'Use when Red Hat Advanced Cluster Security coverage, central health, or secured-cluster protection looks incomplete.',
      symptoms: ['ACS central is degraded, secured clusters are not protected evenly, or workload security expectations differ between clusters.', 'Security review needs to correlate ACS installation health with OpenShift network and workload posture.'],
      evidenceSources: ['ACS Central service availability and phase', 'ACS SecuredCluster availability and central endpoint linkage', 'OpenShift network policy and workload health for protected namespaces'],
      checks: ['Confirm whether ACS central is healthy before investigating secured-cluster drift.', 'Identify which clusters or namespaces are missing secured-cluster coverage.', 'Correlate ACS posture gaps with workload, policy, or platform issues instead of treating them as isolated security symptoms.'],
      prompt: 'Act as an OpenShift and ACS security specialist. Investigate ACS central and secured-cluster coverage by checking Central service health, SecuredCluster availability, network-policy posture, workload health, and related operator signals. Return the likely root cause, evidence, blast radius, and safe next steps.'
    },
    {
      id: 'rosa-platform-posture',
      category: 'Platform patterns',
      label: 'ROSA platform posture and managed-service dependencies',
      summary: 'Use when AWS-hosted OpenShift fleet behavior needs to be understood in a ROSA-aware way rather than as generic cluster drift.',
      symptoms: ['ROSA clusters behave differently from the rest of the estate after a fleet change, upgrade wave, or policy rollout.', 'Operators need a ROSA-specific view of infrastructure pattern, managed-cluster posture, and cluster health.'],
      evidenceSources: ['Cluster infrastructure platform type and inferred platform pattern', 'ManagedCluster fleet posture for ROSA-labelled targets', 'Cluster operators, nodes, and workload stability for the impacted ROSA scopes'],
      checks: ['Confirm the cluster infrastructure resolves to an AWS / ROSA pattern before pursuing ROSA-specific hypotheses.', 'Compare healthy and unhealthy ROSA clusters against ARO, IPI, UPI, or IBM Z peers where useful.', 'Separate provider-managed dependency issues from in-cluster operator or workload faults.'],
      prompt: 'Act as a ROSA platform operations specialist. Investigate ROSA fleet posture by checking cluster infrastructure, ACM managed-cluster state, cluster operators, node readiness, and workload stability. Return the likely root cause, evidence, blast radius, and safe next steps.'
    },
    {
      id: 'aro-platform-posture',
      category: 'Platform patterns',
      label: 'ARO platform posture and Azure landing-zone dependencies',
      summary: 'Use when Azure-hosted OpenShift fleet behavior needs an ARO-aware investigation path instead of generic single-cluster checks.',
      symptoms: ['ARO clusters drift from the rest of the estate, governance posture differs by Azure footprint, or upgrades impact only Azure-hosted clusters.', 'Operators need to compare ARO health against the broader fleet without losing OpenShift evidence depth.'],
      evidenceSources: ['Cluster infrastructure platform type and inferred platform pattern', 'ManagedCluster fleet posture for ARO-labelled targets', 'Cluster operators, nodes, and workload stability for impacted ARO scopes'],
      checks: ['Confirm the cluster infrastructure resolves to an Azure / ARO pattern before pursuing ARO-specific hypotheses.', 'Compare healthy and unhealthy ARO clusters against ROSA, IPI, UPI, or IBM Z peers where useful.', 'Separate landing-zone or provider-aligned drift from in-cluster operator and workload faults.'],
      prompt: 'Act as an ARO platform operations specialist. Investigate ARO fleet posture by checking cluster infrastructure, ACM managed-cluster state, cluster operators, node readiness, and workload stability. Return the likely root cause, evidence, blast radius, and safe next steps.'
    },
    {
      id: 'ibmz-architecture-posture',
      category: 'Platform patterns',
      label: 'IBM Z architecture and capacity posture',
      summary: 'Use when s390x / IBM Z clusters need an architecture-aware operational review instead of a generic x86-centric investigation.',
      symptoms: ['IBM Z clusters show different rollout, capacity, or governance behavior than the rest of the fleet.', 'Operators need to validate that architecture-specific posture, node distribution, and policy coverage are still aligned.'],
      evidenceSources: ['Cluster infrastructure pattern and node architectures', 'ManagedCluster fleet posture for IBM Z targets', 'Cluster operators, node readiness, workload health, and quota posture'],
      checks: ['Confirm the cluster exposes an IBM Z / s390x architecture signal before pursuing architecture-specific hypotheses.', 'Compare IBM Z targets against ROSA, ARO, IPI, or UPI peers only after architecture and quota posture are clear.', 'Identify whether the issue is architecture-specific, policy-related, or simply another cluster-level operator failure.'],
      prompt: 'Act as an IBM Z OpenShift platform specialist. Investigate IBM Z architecture posture by checking cluster infrastructure, node architectures, ACM managed-cluster state, cluster operators, quota posture, and workload stability. Return the likely root cause, evidence, blast radius, and safe next steps.'
    }
  ];
  const TROUBLESHOOTING_PRESET_KEY = 'openshift-sre-troubleshooting-presets-v1';
  const MANAGEMENT_TAB_LABELS = {
    'incident-management': 'Incident management',
    'change-management': 'Change management',
    'problem-management': 'Problem management'
  };
  const uniqueStrings = (values = []) => Array.from(new Set(values.filter(Boolean)));
  const TROUBLESHOOTING_SYMPTOM_LABELS = {
    operator_degraded: 'Cluster operator degraded',
    rollout_stuck: 'Rollout stuck or partially available',
    route_failure: 'Route or ingress failure',
    node_not_ready: 'Node NotReady or pressured',
    pod_crashloop: 'Pod CrashLoopBackOff or restarts',
    quota_pressure: 'Quota pressure or admission block',
    pvc_pending: 'PVC Pending or mount failure',
    policy_block: 'Policy or SCC block',
    olm_failed: 'Subscription or CSV failed',
    warning_events: 'Warning events spike',
    acm_policy_drift: 'ACM policy drift or noncompliance',
    acm_cluster_unavailable: 'Managed cluster unavailable or not joined',
    acs_sensor_gap: 'ACS coverage gap or central issue',
    managed_service_drift: 'Managed service platform drift',
    architecture_mismatch: 'Architecture or platform pattern mismatch'
  };
  const CATEGORY_WORKFLOW_DEFAULTS = {
    'Core triage': {
      services: ['Cluster operators', 'Nodes', 'Workloads', 'Routes'],
      symptomOptions: ['operator_degraded', 'warning_events', 'rollout_stuck'],
      checklist: ['Confirm the first bad timestamp and blast radius.', 'Check top-level operator health, warning events, and recent change windows.', 'Compare a healthy namespace, node, or route with the unhealthy path.', 'Note the first strong hypothesis and the next fallback hypothesis.'],
      commandHints: ['oc get clusterversion', 'oc get clusteroperators', 'oc get events -A --field-selector type=Warning', 'oc get nodes'],
      runbooks: [{ title: 'Operations guide', href: 'operations/' }, { title: 'Architecture reference', href: 'architecture/' }],
      rootCauses: [{ title: 'Recent platform change regression', detail: 'An upgrade, operator change, or rollout aligns with the issue start.', confidence: 'medium', keywords: ['upgrade', 'operator', 'rollout', 'change'] }, { title: 'Infrastructure dependency issue', detail: 'A node, machine pool, route, or storage dependency is degraded and amplifying failure.', confidence: 'medium', keywords: ['node', 'machine', 'route', 'storage', 'degraded'] }, { title: 'Observability blind spot', detail: 'The primary issue may be real, but warning events or surface telemetry are incomplete.', confidence: 'low', keywords: ['warning', 'events', 'missing', 'visibility'] }],
      nextActions: ['Validate the timeline against recent platform changes.', 'Compare healthy and unhealthy namespaces or nodes side-by-side.', 'Escalate only after the first failure domain is narrowed.']
    },
    Platform: {
      services: ['Cluster operators', 'OLM', 'Machine API'],
      symptomOptions: ['operator_degraded', 'olm_failed', 'warning_events'],
      checklist: ['Inspect cluster version, cluster operators, and operator messages.', 'Check whether failures are isolated to one operator or cascade across the platform.', 'Correlate platform issues with recent upgrades or configuration changes.'],
      commandHints: ['oc get clusterversion', 'oc get clusteroperators', 'oc get subscriptions -A', 'oc get csv -A'],
      runbooks: [{ title: 'Operations guide', href: 'operations/' }, { title: 'Service coverage', href: 'service-coverage/' }],
      rootCauses: [{ title: 'Operator reconciliation failure', detail: 'A platform operator cannot reconcile desired state.', confidence: 'high', keywords: ['operator', 'degraded', 'progressing', 'reconcile'] }, { title: 'Upgrade drift', detail: 'Cluster version and operator versions are out of sync or blocked.', confidence: 'medium', keywords: ['upgrade', 'version', 'channel', 'csv'] }, { title: 'Machine API dependency issue', detail: 'Machine sets or machine config pools are preventing recovery.', confidence: 'medium', keywords: ['machine', 'mcp', 'pool', 'machineset'] }],
      nextActions: ['Identify the first degraded operator and capture its message.', 'Verify whether ClusterVersion is blocked or failing.', 'Check machine API health before changing workloads.']
    },
    Networking: {
      services: ['Routes', 'Services', 'Ingresses'],
      symptomOptions: ['route_failure', 'warning_events'],
      checklist: ['Inspect the full client-to-route-to-service path.', 'Check route admitted state, service selectors, and backing pod readiness.', 'Correlate network evidence with application error timestamps.'],
      commandHints: ['oc get routes -A', 'oc get ingress -A', 'oc get svc -A', 'oc get endpoints -A'],
      runbooks: [{ title: 'Operations guide', href: 'operations/' }, { title: 'Architecture reference', href: 'architecture/' }],
      rootCauses: [{ title: 'Route or ingress admission issue', detail: 'The ingress path is defined but not admitted or not wired to a healthy service.', confidence: 'high', keywords: ['route', 'ingress', 'admitted', 'tls'] }, { title: 'Service selector mismatch', detail: 'The route resolves to a service that does not target healthy pods.', confidence: 'high', keywords: ['selector', 'service', 'endpoints'] }, { title: 'Backing workload health issue', detail: 'The network path exists, but the workload behind it is degraded.', confidence: 'medium', keywords: ['pod', 'deployment', 'unavailable', 'restart'] }],
      nextActions: ['Compare healthy and failing routes.', 'Validate selectors and endpoint populations before changing ingress.', 'Check warning events in the affected namespace.']
    },
    Workloads: {
      services: ['Nodes', 'Workloads'],
      symptomOptions: ['node_not_ready', 'rollout_stuck', 'pod_crashloop'],
      checklist: ['Check node readiness, taints, and pressure posture.', 'Compare desired versus ready replicas for impacted workloads.', 'Capture pods with repeated restarts or Pending state.'],
      commandHints: ['oc get nodes', 'oc get pods -A', 'oc get deploy -A', 'oc get statefulset -A', 'oc get daemonset -A'],
      runbooks: [{ title: 'Operations guide', href: 'operations/' }, { title: 'Architecture reference', href: 'architecture/' }],
      rootCauses: [{ title: 'Node readiness or pressure issue', detail: 'Nodes are NotReady or under resource pressure, impacting placement and stability.', confidence: 'high', keywords: ['notready', 'pressure', 'memory', 'disk'] }, { title: 'Rollout regression', detail: 'A recent deployment or configuration change introduced readiness problems.', confidence: 'medium', keywords: ['rollout', 'deployment', 'statefulset', 'daemonset'] }, { title: 'Crash loop or configuration error', detail: 'Pods are starting but failing rapidly due to app or config issues.', confidence: 'medium', keywords: ['crashloop', 'restart', 'pending'] }],
      nextActions: ['Identify whether the issue starts at node or pod level.', 'Compare healthy and unhealthy workloads in the same namespace.', 'Review recent warning events before restarting anything.']
    },
    Storage: {
      services: ['Storage'],
      symptomOptions: ['pvc_pending', 'warning_events'],
      checklist: ['Inspect PV/PVC phase, requested capacity, and access modes.', 'Check storage class defaults and provisioner capabilities.', 'Correlate storage problems with workload rollout or node changes.'],
      commandHints: ['oc get pvc -A', 'oc get pv', 'oc get storageclass'],
      runbooks: [{ title: 'Operations guide', href: 'operations/' }, { title: 'Architecture reference', href: 'architecture/' }],
      rootCauses: [{ title: 'PVC binding mismatch', detail: 'Requested access mode or storage class does not map to an available volume.', confidence: 'high', keywords: ['pvc', 'pending', 'storageclass', 'bound'] }, { title: 'Provisioner or class issue', detail: 'The selected storage class or provisioner is misconfigured or unavailable.', confidence: 'medium', keywords: ['provisioner', 'storageclass', 'default'] }, { title: 'Downstream workload dependency', detail: 'Workloads remain unhealthy because storage is not attached or mounted correctly.', confidence: 'medium', keywords: ['mount', 'volume', 'pod'] }],
      nextActions: ['Find the first Pending PVC.', 'Compare the requested class with the available defaults.', 'Inspect recent events from affected workloads.']
    },
    'Security & governance': {
      services: ['SCCs', 'Network policies', 'Resource quotas'],
      symptomOptions: ['policy_block', 'quota_pressure', 'warning_events'],
      checklist: ['Check SCC privilege posture, network policy isolation, and resource quotas.', 'Determine whether workloads are blocked by admission, isolation, or quotas.', 'Compare expected and actual guardrail posture in the impacted namespace.'],
      commandHints: ['oc get scc', 'oc get networkpolicy -A', 'oc get quota -A'],
      runbooks: [{ title: 'Operations guide', href: 'operations/' }, { title: 'Architecture reference', href: 'architecture/' }],
      rootCauses: [{ title: 'Admission guardrail block', detail: 'Security context or policy requirements are blocking workload startup.', confidence: 'high', keywords: ['scc', 'admission', 'forbidden'] }, { title: 'Namespace isolation gap', detail: 'Network policy posture is missing or changed in the affected namespace.', confidence: 'medium', keywords: ['networkpolicy', 'isolation', 'egress', 'ingress'] }, { title: 'Quota exhaustion', detail: 'Resource quotas are preventing new pods or storage claims.', confidence: 'medium', keywords: ['quota', 'exceeded', 'limit'] }],
      nextActions: ['Identify whether admission, policy, or quotas are the first failure.', 'Compare the affected namespace with a healthy peer.', 'Review recent changes to SCCs, policies, and quotas.']
    },
    Operators: {
      services: ['OLM'],
      symptomOptions: ['olm_failed', 'warning_events'],
      checklist: ['Inspect Subscription state and installed CSVs.', 'Check whether the issue is tied to one package, source, or channel.', 'Determine whether the failure blocks workload or platform services.'],
      commandHints: ['oc get subscriptions -A', 'oc get csv -A'],
      runbooks: [{ title: 'Operations guide', href: 'operations/' }, { title: 'Architecture reference', href: 'architecture/' }],
      rootCauses: [{ title: 'Subscription channel or source issue', detail: 'The Subscription references a bad channel or source.', confidence: 'high', keywords: ['subscription', 'channel', 'source'] }, { title: 'CSV phase failure', detail: 'The installed CSV is not progressing to Succeeded.', confidence: 'medium', keywords: ['csv', 'failed', 'pending'] }, { title: 'Platform dependency problem', detail: 'An operator lifecycle issue is caused by an underlying platform fault.', confidence: 'medium', keywords: ['operator', 'platform', 'degraded'] }],
      nextActions: ['Identify the first unhealthy subscription.', 'Check CSV phase and operator namespace events.', 'Confirm whether the operator issue is isolated or cascading.']
    },
    'Fleet governance': {
      services: ['ACM', 'Cluster infrastructure', 'ROSA', 'ARO', 'IBM Z'],
      symptomOptions: ['acm_cluster_unavailable', 'acm_policy_drift', 'managed_service_drift'],
      checklist: ['Check MultiClusterHub availability and phase first.', 'Compare ManagedCluster joined and available posture across the affected fleet segment.', 'Review ACM policy compliance and disabled-policy state before assuming a transport issue.'],
      commandHints: ['oc get multiclusterhubs -A', 'oc get managedclusters', 'oc get policies -A', 'oc get infrastructure cluster -o yaml'],
      runbooks: [{ title: 'Operations guide', href: 'operations/' }, { title: 'Service coverage', href: 'service-coverage/' }],
      rootCauses: [{ title: 'Hub control-plane issue', detail: 'The ACM hub is degraded or unavailable, so managed-cluster health looks worse than it really is.', confidence: 'high', keywords: ['multiclusterhub', 'hub', 'available', 'phase'] }, { title: 'Managed-cluster connectivity or join drift', detail: 'One or more managed clusters stopped joining or reporting cleanly to ACM.', confidence: 'high', keywords: ['managedcluster', 'joined', 'available', 'fleet'] }, { title: 'Governance policy drift', detail: 'Policies are disabled, noncompliant, or unevenly remediated across the fleet.', confidence: 'medium', keywords: ['policy', 'compliance', 'remediation', 'disabled'] }],
      nextActions: ['Verify whether the ACM hub is healthy before escalating to cluster owners.', 'Compare affected managed clusters by platform pattern and cluster set.', 'Review noncompliant or disabled policies that align with the issue start.']
    },
    'Security & compliance': {
      services: ['ACS', 'Network policies', 'Workloads'],
      symptomOptions: ['acs_sensor_gap', 'policy_block', 'warning_events'],
      checklist: ['Check ACS central service health before reviewing secured-cluster coverage.', 'Identify whether coverage gaps are fleet-wide or isolated to one secured cluster.', 'Correlate ACS symptoms with network-policy posture and workload health.'],
      commandHints: ['oc get centralservices -A', 'oc get securedclusters -A', 'oc get networkpolicy -A', 'oc get pods -A'],
      runbooks: [{ title: 'Operations guide', href: 'operations/' }, { title: 'Architecture reference', href: 'architecture/' }],
      rootCauses: [{ title: 'ACS central degradation', detail: 'Central is unhealthy, so downstream coverage or compliance signals are incomplete.', confidence: 'high', keywords: ['central', 'acs', 'stackrox', 'degraded'] }, { title: 'Secured-cluster rollout gap', detail: 'SecuredCluster coverage is missing or uneven across target clusters.', confidence: 'high', keywords: ['securedcluster', 'sensor', 'coverage', 'cluster'] }, { title: 'Underlying OpenShift policy or workload fault', detail: 'ACS is reporting a real gap caused by network, workload, or operator posture.', confidence: 'medium', keywords: ['networkpolicy', 'workload', 'operator', 'policy'] }],
      nextActions: ['Confirm ACS central health and namespace placement.', 'Compare protected and unprotected clusters or namespaces.', 'Validate whether the gap is an ACS deployment issue or an OpenShift posture issue.']
    },
    'Platform patterns': {
      services: ['Cluster infrastructure', 'ROSA', 'ARO', 'IBM Z', 'Nodes', 'ACM'],
      symptomOptions: ['managed_service_drift', 'architecture_mismatch', 'node_not_ready'],
      checklist: ['Inspect cluster infrastructure and inferred platform pattern first.', 'Check node readiness and architecture signals for the impacted pattern.', 'Compare the affected pattern against a healthy peer pattern before assuming cluster-local fault.'],
      commandHints: ['oc get infrastructure cluster -o yaml', 'oc get nodes -o wide', 'oc get clusterversion', 'oc get clusteroperators', 'oc get managedclusters'],
      runbooks: [{ title: 'Architecture reference', href: 'architecture/' }, { title: 'Service coverage', href: 'service-coverage/' }],
      rootCauses: [{ title: 'Managed service dependency drift', detail: 'A provider-aligned or landing-zone-aligned dependency changed for one platform pattern.', confidence: 'medium', keywords: ['rosa', 'aro', 'managed', 'platform'] }, { title: 'Cluster infrastructure mismatch', detail: 'The cluster reports a different platform pattern or topology than expected, changing how the issue should be investigated.', confidence: 'medium', keywords: ['infrastructure', 'platform', 'topology', 'pattern'] }, { title: 'Architecture-specific capacity or scheduling issue', detail: 'Node architecture, quota, or worker availability differs from the rest of the fleet.', confidence: 'medium', keywords: ['s390x', 'ibm', 'capacity', 'architecture', 'quota'] }],
      nextActions: ['Confirm the cluster platform pattern from infrastructure signals.', 'Compare the affected pattern with a healthy peer cluster.', 'Separate provider-managed drift from in-cluster operator, node, or workload failures.']
    }
  };
  const SCENARIO_WORKFLOW_OVERRIDES = {
    'route-ingress-connectivity': {
      services: ['Routes', 'Services', 'Ingresses'],
      symptomOptions: ['route_failure', 'warning_events']
    },
    'operator-degradation': {
      services: ['Cluster operators', 'OLM'],
      symptomOptions: ['operator_degraded', 'warning_events']
    },
    'node-pressure-readiness': {
      services: ['Nodes', 'Machine API'],
      symptomOptions: ['node_not_ready', 'rollout_stuck']
    },
    'workload-rollout-failures': {
      services: ['Workloads', 'Nodes'],
      symptomOptions: ['rollout_stuck', 'pod_crashloop']
    },
    'storage-binding-capacity': {
      services: ['Storage'],
      symptomOptions: ['pvc_pending', 'warning_events']
    },
    'security-guardrail-review': {
      services: ['SCCs', 'Network policies', 'Resource quotas'],
      symptomOptions: ['policy_block', 'quota_pressure']
    },
    'olm-csv-subscription-failures': {
      services: ['OLM'],
      symptomOptions: ['olm_failed', 'warning_events']
    },
    'acm-fleet-governance': {
      services: ['ACM', 'Cluster infrastructure', 'ROSA', 'ARO', 'IBM Z'],
      symptomOptions: ['acm_cluster_unavailable', 'acm_policy_drift', 'managed_service_drift']
    },
    'acs-security-coverage': {
      services: ['ACS', 'Network policies', 'Workloads'],
      symptomOptions: ['acs_sensor_gap', 'policy_block']
    },
    'rosa-platform-posture': {
      services: ['ROSA', 'Cluster infrastructure', 'ACM', 'Nodes'],
      symptomOptions: ['managed_service_drift', 'node_not_ready']
    },
    'aro-platform-posture': {
      services: ['ARO', 'Cluster infrastructure', 'ACM', 'Nodes'],
      symptomOptions: ['managed_service_drift', 'node_not_ready']
    },
    'ibmz-architecture-posture': {
      services: ['IBM Z', 'Cluster infrastructure', 'Nodes', 'ACM'],
      symptomOptions: ['architecture_mismatch', 'node_not_ready']
    }
  };
  const ENRICHED_TROUBLESHOOTING_SCENARIOS = TROUBLESHOOTING_SCENARIOS.map((scenario) => {
    const defaults = CATEGORY_WORKFLOW_DEFAULTS[scenario.category] || {};
    const override = SCENARIO_WORKFLOW_OVERRIDES[scenario.id] || {};
    return {
      ...scenario,
      services: uniqueStrings([...(defaults.services || []), ...(override.services || [])]),
      symptomOptions: uniqueStrings([...(override.symptomOptions || []), ...(defaults.symptomOptions || [])]),
      checklist: uniqueStrings([...(override.checklist || []), ...(defaults.checklist || []), ...scenario.checks]),
      commandHints: uniqueStrings([...(override.commandHints || []), ...(defaults.commandHints || [])]),
      runbooks: [ ...(override.runbooks || []), ...(defaults.runbooks || []) ],
      rootCauses: override.rootCauses || defaults.rootCauses || [],
      nextActions: override.nextActions || defaults.nextActions || []
    };
  });
  let currentFinopsWorkflow = null;
  let lastRunContext = null;

  const clearGuidedSelection = () => {
    for (const card of root.querySelectorAll('.agent-console__module-card')) {
      card.classList.remove('agent-console__module-card--selected');
    }
    for (const button of root.querySelectorAll('.agent-console__module-card [data-agent-prompt], .agent-console__module-card [data-agent-load-troubleshooting]')) {
      button.classList.remove('agent-console__example--selected');
      button.removeAttribute('aria-pressed');
    }
  };

  const applyGuidedSelection = (button) => {
    clearGuidedSelection();
    button.classList.add('agent-console__example--selected');
    button.setAttribute('aria-pressed', 'true');
    button.closest('.agent-console__module-card')?.classList.add('agent-console__module-card--selected');
  };

  const loadPromptTemplate = (button, statusMessage) => {
    promptInput.value = button.dataset.agentPrompt || button.dataset.agentExample || '';
    applyGuidedSelection(button);
    promptInput.focus();
    promptInput.setSelectionRange(0, promptInput.value.length);
    promptInput.scrollIntoView({ behavior: 'smooth', block: 'center' });
    setStatus(statusMessage, 'ok');
  };

  const getFilteredTroubleshootingScenarios = () => {
    const selectedService = serviceFilterInput?.value || 'all';
    const filtered = selectedService === 'all'
      ? ENRICHED_TROUBLESHOOTING_SCENARIOS
      : ENRICHED_TROUBLESHOOTING_SCENARIOS.filter((scenario) => scenario.services.includes(selectedService));
    return filtered.length > 0 ? filtered : ENRICHED_TROUBLESHOOTING_SCENARIOS;
  };

  const getTroubleshootingScenario = () => {
    const filtered = getFilteredTroubleshootingScenarios();
    return filtered.find((scenario) => scenario.id === troubleshootingSelect?.value)
      || ENRICHED_TROUBLESHOOTING_SCENARIOS.find((scenario) => scenario.id === troubleshootingSelect?.value)
      || filtered[0]
      || ENRICHED_TROUBLESHOOTING_SCENARIOS[0];
  };

  const getSelectedOptionLabel = (node) => node?.selectedOptions?.[0]?.textContent?.trim() || '';

  const getActiveManagementTab = () => root.querySelector('[data-agent-management-tab][aria-selected="true"]')?.dataset.agentManagementTab || 'incident-management';

  const collectFieldLines = (pairs = []) => pairs.map(([label, node]) => {
    const value = node?.tagName === 'SELECT'
      ? getSelectedOptionLabel(node)
      : node?.value?.trim();
    return value ? `${label}: ${value}` : '';
  }).filter(Boolean);

  const getIncidentManagementLines = () => collectFieldLines([
    ['Incident phase', incidentPhaseInput],
    ['Incident type', incidentTypeInput],
    ['Communications status', communicationsStatusInput],
    ['Stakeholder audience', stakeholderAudienceInput],
    ['Restoration status', restorationStatusInput],
    ['Incident owner / commander', incidentOwnerInput],
    ['Customer impact statement', customerImpactInput],
    ['Business impact / decisions needed', businessImpactInput]
  ]);

  const getChangeManagementLines = () => collectFieldLines([
    ['Change type', changeTypeInput],
    ['Change risk', changeRiskInput],
    ['Approval state', changeApprovalInput],
    ['Implementation status', changeImplementationInput],
    ['Rollback readiness', rollbackReadinessInput],
    ['Change window', changeWindowInput],
    ['Change summary', changeSummaryInput]
  ]);

  const getProblemManagementLines = () => collectFieldLines([
    ['Problem record status', problemRecordInput],
    ['Recurrence pattern', problemRecurrenceInput],
    ['RCA method', rcaMethodInput],
    ['Root cause domain', rootCauseDomainInput],
    ['Known error status', knownErrorStatusInput],
    ['Corrective action owner', correctiveOwnerInput],
    ['RCA notes / preventive actions', problemNotesInput]
  ]);

  const getManagementContextSections = () => {
    const incidentLines = getIncidentManagementLines();
    const changeLines = getChangeManagementLines();
    const problemLines = getProblemManagementLines();
    const sections = [];
    if (incidentLines.length > 0) {
      sections.push({ title: 'Incident management context', lines: incidentLines });
    }
    if (changeLines.length > 0) {
      sections.push({ title: 'Change management context', lines: changeLines });
    }
    if (problemLines.length > 0) {
      sections.push({ title: 'Problem management context', lines: problemLines });
    }
    return {
      activeTab: getActiveManagementTab(),
      activeTabLabel: MANAGEMENT_TAB_LABELS[getActiveManagementTab()] || 'Incident management',
      sections,
      incidentLines,
      changeLines,
      problemLines
    };
  };

  const setActiveManagementTab = (tabId, { announce = false } = {}) => {
    managementTabButtons.forEach((button) => {
      const isActive = button.dataset.agentManagementTab === tabId;
      button.classList.toggle('is-active', isActive);
      button.setAttribute('aria-selected', isActive ? 'true' : 'false');
    });
    managementPanels.forEach((panel) => {
      const isActive = panel.dataset.agentManagementPanel === tabId;
      panel.hidden = !isActive;
      panel.classList.toggle('is-active', isActive);
    });
    if (announce) {
      setStatus(`${MANAGEMENT_TAB_LABELS[tabId] || 'Management'} tab is now active.`, 'ok');
    }
  };

  const populateTroubleshootingScenarios = (preferredScenarioId = troubleshootingSelect?.value) => {
    if (!troubleshootingSelect) {
      return;
    }

    const availableScenarios = getFilteredTroubleshootingScenarios();
    const categories = availableScenarios.reduce((map, scenario) => {
      if (!map.has(scenario.category)) {
        map.set(scenario.category, []);
      }
      map.get(scenario.category).push(scenario);
      return map;
    }, new Map());

    troubleshootingSelect.innerHTML = Array.from(categories.entries()).map(([category, scenarios]) => `
      <optgroup label="${escapeHtml(category)}">
        ${scenarios.map((scenario) => `<option value="${escapeHtml(scenario.id)}">${escapeHtml(scenario.label)}</option>`).join('')}
      </optgroup>
    `).join('');

    const selectedScenario = availableScenarios.find((scenario) => scenario.id === preferredScenarioId) || availableScenarios[0];
    troubleshootingSelect.value = selectedScenario?.id || '';
  };

  const populateSymptomOptions = (preferredSymptom = symptomInput?.value || 'auto') => {
    if (!symptomInput) {
      return;
    }

    const scenario = getTroubleshootingScenario();
    const options = ['auto', ...(scenario?.symptomOptions || [])];
    symptomInput.innerHTML = options.map((option) => {
      const label = option === 'auto' ? 'Auto from scenario' : (TROUBLESHOOTING_SYMPTOM_LABELS[option] || option);
      return `<option value="${escapeHtml(option)}">${escapeHtml(label)}</option>`;
    }).join('');
    symptomInput.value = options.includes(preferredSymptom) ? preferredSymptom : 'auto';
  };

  const getCheckedEvidenceItems = () => Array.from(evidenceChecklist?.querySelectorAll('input:checked') || []).map((input) => input.value);

  const renderEvidenceChecklist = (preservedChecks = getCheckedEvidenceItems()) => {
    if (!evidenceChecklist) {
      return;
    }

    const scenario = getTroubleshootingScenario();
    evidenceChecklist.innerHTML = (scenario?.checklist || []).map((item) => {
      const value = item.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/(^-|-$)/g, '');
      return `
        <label class="agent-console__checklist-item">
          <input type="checkbox" value="${escapeHtml(value)}" ${preservedChecks.includes(value) ? 'checked' : ''}>
          <span>${escapeHtml(item)}</span>
        </label>
      `;
    }).join('');
  };

  const renderCommandHints = () => {
    if (!commandHints) {
      return;
    }

    const scenario = getTroubleshootingScenario();
    const items = scenario?.commandHints || [];
    if (items.length === 0) {
      renderMessage(commandHints, 'No recommended read-only checks are configured for this scenario yet.');
      return;
    }

    commandHints.innerHTML = items.map((item) => `
      <article class="agent-console__workflow-item">
        <div>
          <h6>Read-only validation</h6>
          <code>${escapeHtml(item)}</code>
        </div>
      </article>
    `).join('');
  };

  const renderRunbooks = () => {
    if (!runbooks) {
      return;
    }

    const scenario = getTroubleshootingScenario();
    const items = scenario?.runbooks || [];
    if (items.length === 0) {
      renderMessage(runbooks, 'No runbook references are configured for this scenario yet.');
      return;
    }

    runbooks.innerHTML = items.map((item) => `
      <article class="agent-console__runbook-item">
        <div>
          <h6>${escapeHtml(item.title)}</h6>
          <p><a class="agent-console__inline-link" href="${escapeHtml(item.href)}">Open reference</a></p>
        </div>
      </article>
    `).join('');
  };

  const scoreRootCauseCards = (answer = '', rootCauses = []) => {
    const lowered = String(answer || '').toLowerCase();
    return rootCauses
      .map((item) => ({
        ...item,
        score: (item.keywords || []).reduce((sum, keyword) => sum + (lowered.includes(String(keyword).toLowerCase()) ? 1 : 0), 0)
      }))
      .sort((left, right) => right.score - left.score || (left.confidence > right.confidence ? -1 : 1));
  };

  const renderRootCauseCards = (answer = '') => {
    if (!rootCauseCards) {
      return;
    }

    const scenario = getTroubleshootingScenario();
    const ranked = scoreRootCauseCards(answer, scenario?.rootCauses || []).slice(0, 3);
    if (ranked.length === 0) {
      renderMessage(rootCauseCards, 'Likely root cause categories will appear here when this scenario defines them.');
      return;
    }

    rootCauseCards.innerHTML = ranked.map((item) => `
      <article class="agent-console__card agent-console__card--${item.score > 0 ? 'warning' : 'neutral'} agent-console__insight-card">
        <div class="agent-console__module-badge-row">
          <span class="agent-console__history-badge">confidence: ${escapeHtml(item.confidence || 'medium')}</span>
          ${item.score > 0 ? `<span class="agent-console__history-badge agent-console__history-badge--ok">matched in answer</span>` : '<span class="agent-console__history-badge agent-console__history-badge--neutral">scenario preview</span>'}
        </div>
        <h4>${escapeHtml(item.title)}</h4>
        <p>${escapeHtml(item.detail || '')}</p>
      </article>
    `).join('');
  };

  const extractActionLinesFromAnswer = (answer = '') => {
    const lines = String(answer || '').split(/\r?\n/);
    const startIndex = lines.findIndex((line) => /^What I can do next:/i.test(line.trim()));
    if (startIndex === -1) {
      return [];
    }

    const items = [];
    for (const line of lines.slice(startIndex + 1)) {
      const trimmed = line.trim();
      if (!trimmed) {
        if (items.length > 0) {
          break;
        }
        continue;
      }
      if (/^[A-Z][A-Za-z\s]+:$/.test(trimmed)) {
        break;
      }
      if (/^[-*]\s+/.test(trimmed) || /^\d+[.)]\s+/.test(trimmed)) {
        items.push(trimmed.replace(/^[-*]\s+/, '').replace(/^\d+[.)]\s+/, ''));
      }
    }
    return items;
  };

  const renderNextActionCards = (answer = '') => {
    if (!nextActionCards) {
      return;
    }

    const scenario = getTroubleshootingScenario();
    const answerActions = extractActionLinesFromAnswer(answer);
    const actions = answerActions.length > 0 ? answerActions : (scenario?.nextActions || []);
    if (actions.length === 0) {
      renderMessage(nextActionCards, 'Recommended next actions will appear here after you select a workflow or run the agent.');
      return;
    }

    nextActionCards.innerHTML = actions.slice(0, 4).map((item, index) => `
      <article class="agent-console__card agent-console__card--ok agent-console__insight-card">
        <div class="agent-console__module-badge-row">
          <span class="agent-console__history-badge agent-console__history-badge--ok">next action ${index + 1}</span>
          ${answerActions.length > 0 ? '<span class="agent-console__history-badge">from latest run</span>' : '<span class="agent-console__history-badge agent-console__history-badge--neutral">scenario guidance</span>'}
        </div>
        <h4>${escapeHtml(item)}</h4>
        <p>${answerActions.length > 0 ? 'Pulled from the latest agent answer so operators can act on the freshest guidance.' : 'Seeded from the selected troubleshooting workflow as a suggested safe next step.'}</p>
      </article>
    `).join('');
  };

  const formatTimelineValue = (value) => {
    if (!value) {
      return '';
    }
    const date = new Date(value);
    return Number.isNaN(date.getTime()) ? value : date.toISOString();
  };

  const buildTroubleshootingPrompt = () => {
    const scenario = getTroubleshootingScenario();
    if (!scenario) {
      return promptInput.value;
    }

    const managementContext = getManagementContextSections();

    const contextLines = [
      `Severity: ${getSelectedOptionLabel(severityInput) || 'Unspecified'}`,
      `Environment: ${getSelectedOptionLabel(environmentInput) || 'Unspecified'}`,
      `Blast radius: ${getSelectedOptionLabel(blastRadiusInput) || 'Unspecified'}`,
      `Time window: ${getSelectedOptionLabel(timeWindowInput) || 'Unspecified'}`,
      `Management workflow focus: ${managementContext.activeTabLabel}`,
      serviceFilterInput?.value && serviceFilterInput.value !== 'all' ? `Service focus: ${serviceFilterInput.value}` : '',
      symptomInput?.value && symptomInput.value !== 'auto' ? `Primary symptom: ${getSelectedOptionLabel(symptomInput)}` : '',
      primaryResourceInput?.value?.trim() ? `Primary resource or workload: ${primaryResourceInput.value.trim()}` : '',
      affectedScopeInput?.value?.trim() ? `Affected scope/account/service: ${affectedScopeInput.value.trim()}` : '',
      issueStartInput?.value ? `Issue started at: ${formatTimelineValue(issueStartInput.value)}` : '',
      lastHealthyInput?.value ? `Last known healthy: ${formatTimelineValue(lastHealthyInput.value)}` : '',
      recentChangeInput?.value ? `Recent change time: ${formatTimelineValue(recentChangeInput.value)}` : '',
      healthyResourceInput?.value?.trim() ? `Healthy comparison reference: ${healthyResourceInput.value.trim()}` : '',
      unhealthyResourceInput?.value?.trim() ? `Unhealthy comparison reference: ${unhealthyResourceInput.value.trim()}` : '',
      resourceIdsInput?.value?.trim() ? `Specific IDs / ARNs / endpoints:\n${resourceIdsInput.value.trim()}` : ''
    ].filter(Boolean);

    const checkedEvidence = Array.from(evidenceChecklist?.querySelectorAll('input:checked') || []).map((input) => input.nextElementSibling?.textContent?.trim() || input.value).filter(Boolean);
    const notes = issueNotesInput?.value?.trim();
    const rootCauseFocus = (scenario.rootCauses || []).slice(0, 3).map((item) => item.title).join('; ');

    return [
      scenario.prompt,
      contextLines.length > 0 ? `Operator incident context:\n- ${contextLines.join('\n- ')}` : '',
      ...managementContext.sections.map((section) => `${section.title}:\n- ${section.lines.join('\n- ')}`),
      checkedEvidence.length > 0 ? `Evidence already validated:\n- ${checkedEvidence.join('\n- ')}` : '',
      rootCauseFocus ? `Prioritize these likely failure categories first: ${rootCauseFocus}.` : '',
      notes ? `Pasted logs, errors, or operator notes:\n${notes}` : '',
      'Keep the investigation read-only. Explicitly call out what is already validated versus what still needs confirmation.'
    ].filter(Boolean).join('\n\n');
  };

  const updateTroubleshootingPrompt = (statusMessage = '') => {
    if (!promptInput || !troubleshootingSelect) {
      return;
    }
    promptInput.value = buildTroubleshootingPrompt();
    if (statusMessage) {
      setStatus(statusMessage, 'ok');
    }
  };

  const renderTroubleshootingScenario = () => {
    if (!troubleshootingDetails) {
      return;
    }

    const scenario = getTroubleshootingScenario();
    if (!scenario) {
      renderMessage(troubleshootingDetails, 'No troubleshooting workflows are configured yet.');
      return;
    }

    troubleshootingDetails.innerHTML = `
      <div class="agent-console__troubleshooting-header">
        <div class="agent-console__module-badge-row">
          <span class="agent-console__history-badge">${escapeHtml(scenario.category)}</span>
          <span class="agent-console__history-badge agent-console__history-badge--ok">guided workflow</span>
          ${scenario.services.slice(0, 3).map((service) => `<span class="agent-console__history-badge agent-console__history-badge--neutral">${escapeHtml(service)}</span>`).join('')}
        </div>
        <h5>${escapeHtml(scenario.label)}</h5>
        <p class="agent-console__meta">${escapeHtml(scenario.summary)}</p>
      </div>
      <div class="agent-console__troubleshooting-grid">
        <section class="agent-console__troubleshooting-block">
          <h6>Typical symptoms</h6>
          <ul>${scenario.symptoms.map((item) => `<li>${escapeHtml(item)}</li>`).join('')}</ul>
        </section>
        <section class="agent-console__troubleshooting-block">
          <h6>OpenShift evidence sources</h6>
          <ul>${scenario.evidenceSources.map((item) => `<li>${escapeHtml(item)}</li>`).join('')}</ul>
        </section>
        <section class="agent-console__troubleshooting-block">
          <h6>Investigation steps</h6>
          <ul>${scenario.checks.map((item) => `<li>${escapeHtml(item)}</li>`).join('')}</ul>
        </section>
      </div>
      <section class="agent-console__troubleshooting-block">
        <h6>Generated investigation prompt</h6>
        <p class="agent-console__troubleshooting-prompt">${escapeHtml(buildTroubleshootingPrompt())}</p>
      </section>
    `;
  };

  const syncTroubleshootingWorkflow = ({ preferredScenarioId = troubleshootingSelect?.value, preferredSymptom = symptomInput?.value || 'auto', preservedChecks = getCheckedEvidenceItems(), updatePrompt = true } = {}) => {
    if (!troubleshootingSelect) {
      return;
    }
    populateTroubleshootingScenarios(preferredScenarioId);
    populateSymptomOptions(preferredSymptom);
    renderEvidenceChecklist(preservedChecks);
    if (evidenceChecklist) {
      for (const checkbox of evidenceChecklist.querySelectorAll('input[type="checkbox"]')) {
        checkbox.addEventListener('change', () => {
          renderTroubleshootingScenario();
          updateTroubleshootingPrompt();
        });
      }
    }
    renderCommandHints();
    renderRunbooks();
    renderTroubleshootingScenario();
    renderRootCauseCards('');
    renderNextActionCards('');
    if (updatePrompt) {
      updateTroubleshootingPrompt();
    }
  };

  const loadSelectedTroubleshootingScenario = () => {
    const scenario = getTroubleshootingScenario();
    if (!scenario || !loadTroubleshootingButton) {
      return;
    }

    updateTroubleshootingPrompt();
    clearGuidedSelection();
    loadTroubleshootingButton.classList.add('agent-console__example--selected');
    loadTroubleshootingButton.setAttribute('aria-pressed', 'true');
    loadTroubleshootingButton.closest('.agent-console__module-card')?.classList.add('agent-console__module-card--selected');
    promptInput.focus();
    promptInput.setSelectionRange(0, promptInput.value.length);
    promptInput.scrollIntoView({ behavior: 'smooth', block: 'center' });
    setStatus(`${scenario.label} troubleshooting workflow loaded. Review the prompt and run when ready.`, 'ok');
  };

  const getStoredTroubleshootingPresets = () => {
    try {
      return JSON.parse(localStorage.getItem(TROUBLESHOOTING_PRESET_KEY) || '[]');
    } catch {
      return [];
    }
  };

  const setStoredTroubleshootingPresets = (presets) => {
    try {
      localStorage.setItem(TROUBLESHOOTING_PRESET_KEY, JSON.stringify(presets));
    } catch {
      // Ignore storage failures; the console still works without presets.
    }
  };

  const collectTroubleshootingWorkflowState = () => ({
    scenarioId: troubleshootingSelect?.value || '',
    serviceFilter: serviceFilterInput?.value || 'all',
    symptom: symptomInput?.value || 'auto',
    managementTab: getActiveManagementTab(),
    severity: severityInput?.value || '',
    environment: environmentInput?.value || '',
    blastRadius: blastRadiusInput?.value || '',
    timeWindow: timeWindowInput?.value || '',
    issueStart: issueStartInput?.value || '',
    lastHealthy: lastHealthyInput?.value || '',
    recentChange: recentChangeInput?.value || '',
    primaryResource: primaryResourceInput?.value || '',
    affectedScope: affectedScopeInput?.value || '',
    healthyResource: healthyResourceInput?.value || '',
    unhealthyResource: unhealthyResourceInput?.value || '',
    resourceIds: resourceIdsInput?.value || '',
    issueNotes: issueNotesInput?.value || '',
    incidentPhase: incidentPhaseInput?.value || '',
    incidentType: incidentTypeInput?.value || '',
    communicationsStatus: communicationsStatusInput?.value || '',
    stakeholderAudience: stakeholderAudienceInput?.value || '',
    restorationStatus: restorationStatusInput?.value || '',
    incidentOwner: incidentOwnerInput?.value || '',
    customerImpact: customerImpactInput?.value || '',
    businessImpact: businessImpactInput?.value || '',
    changeType: changeTypeInput?.value || '',
    changeRisk: changeRiskInput?.value || '',
    changeApproval: changeApprovalInput?.value || '',
    changeImplementation: changeImplementationInput?.value || '',
    rollbackReadiness: rollbackReadinessInput?.value || '',
    changeWindow: changeWindowInput?.value || '',
    changeSummary: changeSummaryInput?.value || '',
    problemRecord: problemRecordInput?.value || '',
    problemRecurrence: problemRecurrenceInput?.value || '',
    rcaMethod: rcaMethodInput?.value || '',
    rootCauseDomain: rootCauseDomainInput?.value || '',
    knownErrorStatus: knownErrorStatusInput?.value || '',
    correctiveOwner: correctiveOwnerInput?.value || '',
    problemNotes: problemNotesInput?.value || '',
    checkedEvidence: getCheckedEvidenceItems()
  });

  const refreshPresetOptions = () => {
    if (!presetSelect) {
      return;
    }
    const presets = getStoredTroubleshootingPresets();
    presetSelect.innerHTML = presets.length > 0
      ? ['<option value="">Select a saved preset</option>', ...presets.map((preset) => `<option value="${escapeHtml(preset.name)}">${escapeHtml(preset.name)}</option>`)].join('')
      : '<option value="">No saved presets</option>';
  };

  const applyTroubleshootingWorkflowState = (state) => {
    if (!state) {
      return;
    }
    if (serviceFilterInput) {
      serviceFilterInput.value = state.serviceFilter || 'all';
    }
    if (severityInput) {
      severityInput.value = state.severity || severityInput.value;
    }
    if (environmentInput) {
      environmentInput.value = state.environment || environmentInput.value;
    }
    if (blastRadiusInput) {
      blastRadiusInput.value = state.blastRadius || blastRadiusInput.value;
    }
    if (timeWindowInput) {
      timeWindowInput.value = state.timeWindow || timeWindowInput.value;
    }
    if (issueStartInput) {
      issueStartInput.value = state.issueStart || '';
    }
    if (lastHealthyInput) {
      lastHealthyInput.value = state.lastHealthy || '';
    }
    if (recentChangeInput) {
      recentChangeInput.value = state.recentChange || '';
    }
    if (primaryResourceInput) {
      primaryResourceInput.value = state.primaryResource || '';
    }
    if (affectedScopeInput) {
      affectedScopeInput.value = state.affectedScope || '';
    }
    if (healthyResourceInput) {
      healthyResourceInput.value = state.healthyResource || '';
    }
    if (unhealthyResourceInput) {
      unhealthyResourceInput.value = state.unhealthyResource || '';
    }
    if (resourceIdsInput) {
      resourceIdsInput.value = state.resourceIds || '';
    }
    if (issueNotesInput) {
      issueNotesInput.value = state.issueNotes || '';
    }
    if (incidentPhaseInput && state.incidentPhase) {
      incidentPhaseInput.value = state.incidentPhase;
    }
    if (incidentTypeInput && state.incidentType) {
      incidentTypeInput.value = state.incidentType;
    }
    if (communicationsStatusInput && state.communicationsStatus) {
      communicationsStatusInput.value = state.communicationsStatus;
    }
    if (stakeholderAudienceInput && state.stakeholderAudience) {
      stakeholderAudienceInput.value = state.stakeholderAudience;
    }
    if (restorationStatusInput && state.restorationStatus) {
      restorationStatusInput.value = state.restorationStatus;
    }
    if (incidentOwnerInput) {
      incidentOwnerInput.value = state.incidentOwner || '';
    }
    if (customerImpactInput) {
      customerImpactInput.value = state.customerImpact || '';
    }
    if (businessImpactInput) {
      businessImpactInput.value = state.businessImpact || '';
    }
    if (changeTypeInput && state.changeType) {
      changeTypeInput.value = state.changeType;
    }
    if (changeRiskInput && state.changeRisk) {
      changeRiskInput.value = state.changeRisk;
    }
    if (changeApprovalInput && state.changeApproval) {
      changeApprovalInput.value = state.changeApproval;
    }
    if (changeImplementationInput && state.changeImplementation) {
      changeImplementationInput.value = state.changeImplementation;
    }
    if (rollbackReadinessInput && state.rollbackReadiness) {
      rollbackReadinessInput.value = state.rollbackReadiness;
    }
    if (changeWindowInput && state.changeWindow) {
      changeWindowInput.value = state.changeWindow;
    }
    if (changeSummaryInput) {
      changeSummaryInput.value = state.changeSummary || '';
    }
    if (problemRecordInput && state.problemRecord) {
      problemRecordInput.value = state.problemRecord;
    }
    if (problemRecurrenceInput && state.problemRecurrence) {
      problemRecurrenceInput.value = state.problemRecurrence;
    }
    if (rcaMethodInput && state.rcaMethod) {
      rcaMethodInput.value = state.rcaMethod;
    }
    if (rootCauseDomainInput && state.rootCauseDomain) {
      rootCauseDomainInput.value = state.rootCauseDomain;
    }
    if (knownErrorStatusInput && state.knownErrorStatus) {
      knownErrorStatusInput.value = state.knownErrorStatus;
    }
    if (correctiveOwnerInput) {
      correctiveOwnerInput.value = state.correctiveOwner || '';
    }
    if (problemNotesInput) {
      problemNotesInput.value = state.problemNotes || '';
    }
    setActiveManagementTab(state.managementTab || 'incident-management');
    syncTroubleshootingWorkflow({ preferredScenarioId: state.scenarioId, preferredSymptom: state.symptom, preservedChecks: state.checkedEvidence || [], updatePrompt: true });
  };

  const escapeHtml = (value = '') => String(value)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');

  const currentProviderId = () => llmRuntime.normalizeProviderId?.(providerCatalog, llmProviderInput?.value) || 'ollama';

  const currentProvider = () => llmRuntime.getProvider?.(providerCatalog, currentProviderId()) || providerCatalog.providers?.[0] || { id: 'ollama', label: 'Local Ollama', default_model: 'gpt-oss:20b', default_base_url: 'http://localhost:11434' };

  const renderProviderOptions = () => {
    if (!llmProviderInput) {
      return;
    }
    const selected = currentProviderId();
    const options = Array.isArray(providerCatalog?.providers) ? providerCatalog.providers : [];
    llmProviderInput.innerHTML = options.map((provider) => `<option value="${escapeHtml(provider.id)}">${escapeHtml(provider.label)}</option>`).join('');
    llmProviderInput.value = selected;
  };

  const syncProviderVisibility = () => {
    const provider = currentProvider();
    const useExternal = provider.id !== 'ollama';
    ollamaFieldGroups.forEach((node) => { node.hidden = useExternal; });
    externalLlmFieldGroups.forEach((node) => { node.hidden = !useExternal; });
    if (llmProviderNote) {
      llmProviderNote.textContent = provider.description || 'Choose between the local Ollama runtime and supported external providers.';
    }
    if (useExternal) {
      if (externalModelNameInput && !externalModelNameInput.value.trim()) {
        externalModelNameInput.value = provider.default_model || providerCatalog.configured_model_name || '';
      }
      if (externalBaseUrlInput && !externalBaseUrlInput.value.trim() && provider.default_base_url) {
        externalBaseUrlInput.value = provider.default_base_url;
      }
      if (externalApiVersionInput && !externalApiVersionInput.value.trim() && provider.default_api_version) {
        externalApiVersionInput.value = provider.default_api_version;
      }
      if (externalModelNameInput && provider.default_model) {
        externalModelNameInput.placeholder = provider.default_model;
      }
      if (externalBaseUrlInput && provider.default_base_url) {
        externalBaseUrlInput.placeholder = provider.default_base_url;
      }
    }
  };

  const loadProviderCatalog = async () => {
    providerCatalog = await (llmRuntime.fetchProviderCatalog?.() || Promise.resolve(providerCatalog));
    renderProviderOptions();
    syncProviderVisibility();
  };

  const getFriendlyMessage = (message) => {
    const raw = String(message ?? '').trim();
    if (!raw) {
      return 'No data is available yet.';
    }

    if (raw.toLowerCase() === 'failed to fetch') {
      return 'Live data is unavailable in static preview. Open this page through the running app on http://127.0.0.1:8000/ or start the local stack to enable API-backed panels.';
    }

    return raw;
  };

  const renderMessage = (node, message) => {
    const friendlyMessage = getFriendlyMessage(message);
    const isWarning = /failed to fetch|unavailable|unable|disabled/i.test(friendlyMessage);
    const title = isWarning ? 'Live data unavailable' : 'Nothing to show yet';
    node.innerHTML = `
      <div class="agent-console__state ${isWarning ? 'agent-console__state--warning' : ''}">
        <p class="agent-console__state-title">${escapeHtml(title)}</p>
        <p class="agent-console__state-copy">${escapeHtml(friendlyMessage)}</p>
      </div>
    `;
  };

  const parseApprovalOptions = (text = '') => {
    const lines = String(text).split(/\r?\n/);
    const approvalHeaderIndex = lines.findIndex((line) => line.trim() === 'Approval options:');
    if (approvalHeaderIndex === -1) {
      return { displayText: text, options: [] };
    }

    const before = lines.slice(0, approvalHeaderIndex).join('\n').trim();
    const after = lines.slice(approvalHeaderIndex + 1);
    const optionLines = [];
    const trailingLines = [];
    let collectingOptions = true;

    for (const line of after) {
      const trimmed = line.trim();
      if (collectingOptions && trimmed.startsWith('- ')) {
        optionLines.push(trimmed);
        continue;
      }
      if (!trimmed && collectingOptions && optionLines.length > 0) {
        continue;
      }
      collectingOptions = false;
      trailingLines.push(line);
    }

    const options = optionLines.map((line, index) => {
      const match = line.match(/^- Reply with `([^`]+)` and (.+)$/);
      if (match) {
        return {
          id: `approval-option-${index + 1}`,
          command: match[1],
          description: match[2].replace(/\.$/, ''),
        };
      }

      return {
        id: `approval-option-${index + 1}`,
        command: line.replace(/^-\s*/, ''),
        description: '',
      };
    });

    const trailing = trailingLines.join('\n').trim();
    const displayText = [before, trailing].filter(Boolean).join('\n\n').trim();
    return { displayText, options };
  };

  const renderAnswerText = (text = '') => {
    const normalized = String(text || '').trim();
    if (!normalized) {
      answer.textContent = '(No answer returned)';
      return;
    }

    const blocks = normalized.split(/\n{2,}/).map((block) => block.trim()).filter(Boolean);
    answer.innerHTML = blocks.map((block) => {
      if (block.startsWith('Observed service states:')) {
        const lines = block.split(/\n/);
        const title = escapeHtml(lines[0]);
        const items = lines.slice(1).map((line) => `<li>${escapeHtml(line.replace(/^-\s*/, ''))}</li>`).join('');
        return `<section class="agent-console__answer-section"><h3>${title}</h3><ul>${items}</ul></section>`;
      }
      if (block.startsWith('What I can do next:')) {
        const lines = block.split(/\n/);
        const title = escapeHtml(lines[0]);
        const items = lines.slice(1).map((line) => `<li>${escapeHtml(line.replace(/^-\s*/, ''))}</li>`).join('');
        return `<section class="agent-console__answer-section"><h3>${title}</h3><ul>${items}</ul></section>`;
      }
      if (block.startsWith('Note:')) {
        return `<p class="agent-console__meta">${escapeHtml(block)}</p>`;
      }
      return `<p>${escapeHtml(block)}</p>`;
    }).join('');
  };

  const clearApprovalOptions = () => {
    approvalOptions.innerHTML = '';
    approvalPanel.hidden = true;
  };

  const buildApprovalPrompt = (option) => {
    const previousPrompt = lastRunContext?.prompt?.trim() || promptInput.value.trim();
    const previousAnswer = lastRunContext?.answer?.trim() || '';
    const optionDescription = option.description ? `Approved option details: ${option.description}.` : '';
    return [
      `Original operator request: ${previousPrompt}`,
      previousAnswer ? `Previous agent answer:\n${previousAnswer}` : '',
      `Operator approval decision: ${option.command}.`,
      optionDescription,
      'Continue with the approved next step now. Re-run or extend the investigation as needed, then return an updated operator-ready answer.',
    ].filter(Boolean).join('\n\n');
  };

  const renderApprovalOptions = (options = []) => {
    approvalOptions.innerHTML = '';
    if (!Array.isArray(options) || options.length === 0) {
      approvalPanel.hidden = true;
      return;
    }

    approvalPanel.hidden = false;
    approvalOptions.innerHTML = options.map((option, index) => `
      <label class="agent-console__approval-option">
        <input type="radio" name="agent-approval-option" value="${escapeHtml(option.command)}" ${index === 0 ? 'checked' : ''}>
        <span class="agent-console__approval-option-body">
          <span class="agent-console__approval-option-title">${escapeHtml(option.command)}</span>
          <span class="agent-console__approval-option-description">${escapeHtml(option.description || 'Use this approval path for the next guided follow-up run.')}</span>
        </span>
      </label>
    `).join('');
  };

  const setStatus = (message, kind = '') => {
    status.textContent = message;
    status.className = 'agent-console__status';
    if (kind) {
      status.classList.add(`agent-console__status--${kind}`);
    }
  };

  const setReportStatus = (message, kind = '') => {
    if (!reportStatus) {
      return;
    }
    reportStatus.textContent = message;
    reportStatus.className = 'agent-console__status';
    if (kind) {
      reportStatus.classList.add(`agent-console__status--${kind}`);
    }
  };

  const summarizeNarrativeLines = (text = '', maxItems = 6) => String(text || '')
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter((line) => line && !/^Approval options:?$/i.test(line))
    .map((line) => line.replace(/^[-*]\s+/, '').replace(/^\d+[.)]\s+/, ''))
    .slice(0, maxItems);

  const formatReportTypeLabel = (reportType) => reportType === 'rca' ? 'Root Cause Analysis' : 'Incident Report';

  const buildTroubleshootingReportContext = (reportType) => {
    const scenario = getTroubleshootingScenario();
    const managementContext = getManagementContextSections();
    const checkedEvidence = Array.from(evidenceChecklist?.querySelectorAll('input:checked') || [])
      .map((input) => input.nextElementSibling?.textContent?.trim() || input.value)
      .filter(Boolean);
    const rootCauses = scoreRootCauseCards(lastRunContext?.answer || '', scenario?.rootCauses || []).slice(0, 4);
    const nextActions = extractActionLinesFromAnswer(lastRunContext?.answer || '');
    const answerHighlights = summarizeNarrativeLines(lastRunContext?.answer || '', 8);
    return {
      reportType,
      reportLabel: formatReportTypeLabel(reportType),
      generatedAt: new Date(),
      prompt: lastRunContext?.prompt || promptInput?.value || '',
      answer: lastRunContext?.answer || '',
      scenarioLabel: scenario?.label || 'Troubleshooting workflow',
      scenarioSummary: scenario?.summary || '',
      severity: getSelectedOptionLabel(severityInput) || 'Unspecified',
      environment: getSelectedOptionLabel(environmentInput) || 'Unspecified',
      blastRadius: getSelectedOptionLabel(blastRadiusInput) || 'Unspecified',
      timeWindow: getSelectedOptionLabel(timeWindowInput) || 'Unspecified',
      symptom: symptomInput?.value && symptomInput.value !== 'auto' ? getSelectedOptionLabel(symptomInput) : 'Auto from scenario',
      issueStart: formatTimelineValue(issueStartInput?.value || '') || 'Unspecified',
      lastHealthy: formatTimelineValue(lastHealthyInput?.value || '') || 'Unspecified',
      recentChange: formatTimelineValue(recentChangeInput?.value || '') || 'Unspecified',
      primaryResource: primaryResourceInput?.value?.trim() || 'Unspecified',
      affectedScope: affectedScopeInput?.value?.trim() || 'Unspecified',
      notes: issueNotesInput?.value?.trim() || '',
      checkedEvidence,
      rootCauses,
      nextActions: nextActions.length > 0 ? nextActions : (scenario?.nextActions || []).slice(0, 5),
      answerHighlights,
      managementContext
    };
  };

  const createTimestampSlug = () => new Date().toISOString().replace(/[:.]/g, '-');

  const downloadBlob = (filename, blob) => {
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
  };

  const toCsvText = (rows = []) => rows.map((row = []) => row.map((value) => {
    const text = String(value ?? '');
    if (text.includes(',') || text.includes('"') || text.includes('\n')) {
      return `"${text.replaceAll('"', '""')}"`;
    }
    return text;
  }).join(',')).join('\n');

  const buildReportSectionText = (title, lines = []) => {
    const filtered = lines.filter(Boolean);
    if (filtered.length === 0) {
      return '';
    }
    return `${title}\n${filtered.map((line) => `• ${line}`).join('\n')}`;
  };

  const exportTroubleshootingPpt = async (context) => {
    const PptxGenJS = window.PptxGenJS;
    if (!PptxGenJS) {
      throw new Error('PowerPoint export library is not available on this page right now.');
    }

    const pptx = new PptxGenJS();
    pptx.layout = 'LAYOUT_WIDE';
    pptx.author = 'GitHub Copilot';
    pptx.company = 'OpenShift SRE Local Agent';
    pptx.subject = context.reportLabel;
    pptx.title = `${context.reportLabel} - ${context.scenarioLabel}`;

    const titleSlide = pptx.addSlide();
    titleSlide.background = { color: 'F8FAFC' };
    titleSlide.addText(context.reportLabel, { x: 0.5, y: 0.5, w: 6.2, h: 0.5, fontSize: 24, bold: true, color: '0F172A' });
    titleSlide.addText(context.scenarioLabel, { x: 0.5, y: 1.1, w: 7.2, h: 0.35, fontSize: 15, color: '2563EB' });
    titleSlide.addText([
      { text: `Severity: ${context.severity}` },
      { text: `Environment: ${context.environment}` },
      { text: `Blast radius: ${context.blastRadius}` },
      { text: `Generated: ${context.generatedAt.toLocaleString()}` }
    ], { x: 0.5, y: 1.7, w: 5.8, h: 1.2, fontSize: 13, breakLine: true, color: '334155' });
    titleSlide.addText((context.answerHighlights.slice(0, 4).join('\n• ')) ? `• ${context.answerHighlights.slice(0, 4).join('\n• ')}` : '• Run summary unavailable', { x: 6.8, y: 0.9, w: 5.8, h: 2.8, fontSize: 13, color: '0F172A', margin: 0.12, fill: { color: 'DBEAFE' }, line: { color: '93C5FD' }, radius: 0.16 });

    const detailSlide = pptx.addSlide();
    detailSlide.addText(`${context.reportLabel} overview`, { x: 0.5, y: 0.4, w: 5.6, h: 0.4, fontSize: 20, bold: true, color: '0F172A' });
    detailSlide.addText(buildReportSectionText('Incident context', [
      `Time window: ${context.timeWindow}`,
      `Primary symptom: ${context.symptom}`,
      `Issue start: ${context.issueStart}`,
      `Last healthy: ${context.lastHealthy}`,
      `Recent change: ${context.recentChange}`,
      `Primary resource: ${context.primaryResource}`,
      `Affected scope: ${context.affectedScope}`
    ]), { x: 0.5, y: 1.0, w: 5.8, h: 2.8, fontSize: 12, color: '0F172A', margin: 0.12, fill: { color: 'FFFFFF' }, line: { color: 'CBD5E1' } });
    detailSlide.addText(buildReportSectionText(context.reportType === 'rca' ? 'Likely root causes' : 'Response highlights', context.reportType === 'rca'
      ? context.rootCauses.map((item) => `${item.title} (${item.confidence || 'medium'} confidence) — ${item.detail || ''}`)
      : context.answerHighlights.slice(0, 6)), { x: 6.7, y: 1.0, w: 5.8, h: 2.8, fontSize: 12, color: '0F172A', margin: 0.12, fill: { color: 'FFFFFF' }, line: { color: 'CBD5E1' } });

    const actionSlide = pptx.addSlide();
    actionSlide.addText('Evidence, actions, and management context', { x: 0.5, y: 0.4, w: 7.2, h: 0.4, fontSize: 20, bold: true, color: '0F172A' });
    actionSlide.addText(buildReportSectionText('Evidence captured', context.checkedEvidence.length > 0 ? context.checkedEvidence : ['No evidence checklist items were marked complete.']), { x: 0.5, y: 1.0, w: 4.0, h: 3.4, fontSize: 12, color: '0F172A', margin: 0.12, fill: { color: 'FFFFFF' }, line: { color: 'CBD5E1' } });
    actionSlide.addText(buildReportSectionText(context.reportType === 'rca' ? 'Corrective and preventive actions' : 'Immediate next actions', context.nextActions.length > 0 ? context.nextActions : ['No next actions were extracted from the latest run.']), { x: 4.75, y: 1.0, w: 3.7, h: 3.4, fontSize: 12, color: '0F172A', margin: 0.12, fill: { color: 'FFFFFF' }, line: { color: 'CBD5E1' } });
    actionSlide.addText(buildReportSectionText(`${context.managementContext.activeTabLabel} details`, (context.managementContext.sections.find((section) => section.title.includes(context.managementContext.activeTabLabel.split(' ')[0]))?.lines) || context.managementContext.sections.flatMap((section) => section.lines).slice(0, 6)), { x: 8.7, y: 1.0, w: 3.6, h: 3.4, fontSize: 12, color: '0F172A', margin: 0.12, fill: { color: 'FFFFFF' }, line: { color: 'CBD5E1' } });

    await pptx.writeFile({ fileName: `openshift-sre-${context.reportType}-${createTimestampSlug()}.pptx` });
  };

  const exportTroubleshootingPdf = async (context) => {
    const jsPDF = window.jspdf?.jsPDF;
    if (!jsPDF) {
      throw new Error('PDF export library is not available on this page right now.');
    }

    const doc = new jsPDF({ unit: 'pt', format: 'a4' });
    const pageWidth = doc.internal.pageSize.getWidth();
    let cursorY = 56;
    const addWrappedBlock = (title, lines = []) => {
      const filtered = lines.filter(Boolean);
      if (filtered.length === 0) {
        return;
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
      if (cursorY > 740) {
        doc.addPage();
        cursorY = 56;
      }
    };

    doc.setFont('helvetica', 'bold');
    doc.setFontSize(22);
    doc.text(context.reportLabel, 48, cursorY);
    cursorY += 22;
    doc.setFontSize(12);
    doc.setFont('helvetica', 'normal');
    doc.text(`${context.scenarioLabel} • ${context.generatedAt.toLocaleString()}`, 48, cursorY);
    cursorY += 24;

    addWrappedBlock('Overview', [
      `Severity: ${context.severity}`,
      `Environment: ${context.environment}`,
      `Blast radius: ${context.blastRadius}`,
      `Time window: ${context.timeWindow}`,
      `Primary resource: ${context.primaryResource}`,
      `Affected scope: ${context.affectedScope}`
    ]);
    addWrappedBlock(context.reportType === 'rca' ? 'Likely root causes' : 'Response highlights', context.reportType === 'rca'
      ? context.rootCauses.map((item) => `${item.title} (${item.confidence || 'medium'} confidence) — ${item.detail || ''}`)
      : context.answerHighlights.slice(0, 8));
    addWrappedBlock('Evidence captured', context.checkedEvidence.length > 0 ? context.checkedEvidence : ['No evidence checklist items were marked complete.']);
    addWrappedBlock(context.reportType === 'rca' ? 'Corrective / preventive actions' : 'Immediate next actions', context.nextActions.length > 0 ? context.nextActions : ['No next actions were extracted from the latest run.']);
    addWrappedBlock('Management context', context.managementContext.sections.flatMap((section) => [`${section.title}`, ...section.lines]));
    if (context.notes) {
      addWrappedBlock('Operator notes', [context.notes]);
    }

    doc.save(`openshift-sre-${context.reportType}-${createTimestampSlug()}.pdf`);
  };

  const exportTroubleshootingWord = async (context) => {
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
    <p class="meta">${escapeHtml(context.scenarioLabel)} · ${escapeHtml(context.generatedAt.toLocaleString())}</p>
    <div>
      <span class="chip">Severity: ${escapeHtml(context.severity)}</span>
      <span class="chip">Environment: ${escapeHtml(context.environment)}</span>
      <span class="chip">Blast radius: ${escapeHtml(context.blastRadius)}</span>
      <span class="chip">Workflow: ${escapeHtml(context.managementContext.activeTabLabel)}</span>
    </div>
    <div class="section">
      <h2>Overview</h2>
      <ul>
        <li>Time window: ${escapeHtml(context.timeWindow)}</li>
        <li>Primary symptom: ${escapeHtml(context.symptom)}</li>
        <li>Issue start: ${escapeHtml(context.issueStart)}</li>
        <li>Last healthy: ${escapeHtml(context.lastHealthy)}</li>
        <li>Recent change: ${escapeHtml(context.recentChange)}</li>
        <li>Primary resource: ${escapeHtml(context.primaryResource)}</li>
        <li>Affected scope: ${escapeHtml(context.affectedScope)}</li>
      </ul>
    </div>
    <div class="section">
      <h2>${escapeHtml(context.reportType === 'rca' ? 'Likely root causes' : 'Response highlights')}</h2>
      <ul>
        ${(context.reportType === 'rca'
          ? context.rootCauses.map((item) => `${item.title} (${item.confidence || 'medium'} confidence) — ${item.detail || ''}`)
          : context.answerHighlights.slice(0, 8)
        ).map((line) => `<li>${escapeHtml(line)}</li>`).join('')}
      </ul>
    </div>
    <div class="section">
      <h2>Evidence captured</h2>
      <ul>
        ${(context.checkedEvidence.length > 0 ? context.checkedEvidence : ['No evidence checklist items were marked complete.']).map((line) => `<li>${escapeHtml(line)}</li>`).join('')}
      </ul>
    </div>
    <div class="section">
      <h2>${escapeHtml(context.reportType === 'rca' ? 'Corrective and preventive actions' : 'Immediate next actions')}</h2>
      <ul>
        ${(context.nextActions.length > 0 ? context.nextActions : ['No next actions were extracted from the latest run.']).map((line) => `<li>${escapeHtml(line)}</li>`).join('')}
      </ul>
    </div>
    <div class="section">
      <h2>Management context</h2>
      ${context.managementContext.sections.map((section) => `
        <h3>${escapeHtml(section.title)}</h3>
        <ul>${section.lines.map((line) => `<li>${escapeHtml(line)}</li>`).join('')}</ul>
      `).join('')}
    </div>
    ${context.notes ? `<div class="section"><h2>Operator notes</h2><p>${escapeHtml(context.notes).replace(/\n/g, '<br>')}</p></div>` : ''}
  </body>
</html>`;
    downloadBlob(`openshift-sre-${context.reportType}-${createTimestampSlug()}.doc`, new Blob([html], { type: 'application/msword' }));
  };

  const updateReportExportState = () => {
    const hasAnswer = Boolean(lastRunContext?.answer);
    reportExportButtons.forEach((button) => {
      const isExporting = button.dataset.agentExporting === 'true';
      button.disabled = !hasAnswer || isExporting;
    });
    if (!hasAnswer) {
      setReportStatus('Run a troubleshooting scenario to unlock incident report and RCA exports.');
    }
  };

  const handleReportExport = async (button) => {
    if (!button || !lastRunContext?.answer) {
      setReportStatus('Run a troubleshooting scenario first so there is live content to export.', 'error');
      return;
    }

    const reportType = button.dataset.agentExportReport || 'incident-report';
    const format = button.dataset.agentExportFormat || 'word';
    const context = buildTroubleshootingReportContext(reportType);
    const originalLabel = button.textContent;
    button.dataset.agentExporting = 'true';
    button.textContent = `Preparing ${format.toUpperCase()}…`;
    updateReportExportState();
    setReportStatus(`Building ${context.reportLabel} as ${format.toUpperCase()}…`, 'ok');

    try {
      if (format === 'ppt') {
        await exportTroubleshootingPpt(context);
      } else if (format === 'pdf') {
        await exportTroubleshootingPdf(context);
      } else {
        await exportTroubleshootingWord(context);
      }
      setReportStatus(`${context.reportLabel} exported as ${format.toUpperCase()}.`, 'ok');
      if (typeof showToast === 'function') {
        showToast(`${context.reportLabel} exported as ${format.toUpperCase()}.`, 'success');
      }
    } catch (error) {
      const message = error instanceof Error ? error.message : `Unable to export ${context.reportLabel}.`;
      setReportStatus(message, 'error');
      if (typeof showToast === 'function') {
        showToast(message, 'error');
      }
    } finally {
      button.dataset.agentExporting = 'false';
      button.textContent = originalLabel;
      updateReportExportState();
    }
  };

  const setConsoleReportStatus = (message, kind = '') => {
    if (!consoleReportStatus) {
      return;
    }
    consoleReportStatus.textContent = message;
    consoleReportStatus.className = 'agent-console__status';
    if (kind) {
      consoleReportStatus.classList.add(`agent-console__status--${kind}`);
    }
  };

  const buildConsoleReportContext = (reportType) => {
    const steps = Array.isArray(lastRunContext?.steps) ? lastRunContext.steps : [];
    const toolSummaries = steps.filter((item) => item.tool_call?.name).map((item) => summarizeStep(item)).slice(0, 8);
    const answerHighlights = summarizeNarrativeLines(lastRunContext?.answer || '', 8);
    const nextActions = extractActionLinesFromAnswer(lastRunContext?.answer || '');
    return {
      reportType,
      reportLabel: reportType === 'investigation-handoff' ? 'Investigation Handoff' : 'Operator Response Report',
      generatedAt: new Date(),
      runId: lastRunContext?.runId || '—',
      prompt: lastRunContext?.prompt || promptInput?.value || '',
      answer: lastRunContext?.answer || '',
      answerHighlights,
      nextActions: nextActions.length > 0 ? nextActions : ['No next actions were extracted from the latest answer.'],
      toolSummaries,
      steps
    };
  };

  const exportConsoleCsv = async (context) => {
    const rows = [
      ['Section', 'Field', 'Value'],
      ['summary', 'report_type', context.reportLabel],
      ['summary', 'generated_at', context.generatedAt.toISOString()],
      ['summary', 'run_id', context.runId],
      ['summary', 'prompt', context.prompt],
      ['summary', 'answer', context.answer],
      [],
      ['highlights', 'line'],
      ...context.answerHighlights.map((line) => ['highlights', line]),
      [],
      ['next_actions', 'line'],
      ...context.nextActions.map((line) => ['next_actions', line]),
      [],
      ['tool_summaries', 'title', 'summary', 'detail', 'kind'],
      ...context.toolSummaries.map((item) => ['tool_summaries', item.title, item.summary, item.detail, item.kind]),
      [],
      ['steps', 'step', 'tool', 'thought', 'tool_error'],
      ...context.steps.map((item) => [
        'steps',
        item.step ?? '',
        item.tool_call?.name || '',
        item.thought || '',
        item.tool_error || item.tool_result?.error || ''
      ])
    ];
    downloadBlob(`openshift-sre-console-${context.reportType}-${createTimestampSlug()}.csv`, new Blob([toCsvText(rows)], { type: 'text/csv;charset=utf-8' }));
  };

  const exportConsolePpt = async (context) => {
    const PptxGenJS = window.PptxGenJS;
    if (!PptxGenJS) {
      throw new Error('PowerPoint export library is not available on this page right now.');
    }
    const pptx = new PptxGenJS();
    pptx.layout = 'LAYOUT_WIDE';
    pptx.author = 'GitHub Copilot';
    pptx.company = 'OpenShift SRE Local Agent';
    pptx.subject = context.reportLabel;
    pptx.title = `${context.reportLabel} - Run ${context.runId}`;

    const titleSlide = pptx.addSlide();
    titleSlide.background = { color: 'F8FAFC' };
    titleSlide.addText(context.reportLabel, { x: 0.5, y: 0.5, w: 6.4, h: 0.5, fontSize: 24, bold: true, color: '0F172A' });
    titleSlide.addText(`Run ${context.runId} • ${context.generatedAt.toLocaleString()}`, { x: 0.5, y: 1.1, w: 6.8, h: 0.3, fontSize: 14, color: '2563EB' });
    titleSlide.addText(`Prompt:\n${context.prompt}`, { x: 0.5, y: 1.7, w: 5.8, h: 2.2, fontSize: 11, color: '334155', margin: 0.08, fill: { color: 'FFFFFF' }, line: { color: 'CBD5E1' } });
    titleSlide.addText(context.answerHighlights.length > 0 ? `• ${context.answerHighlights.slice(0, 5).join('\n• ')}` : '• No answer highlights were available.', { x: 6.7, y: 1.2, w: 5.5, h: 2.8, fontSize: 13, color: '0F172A', margin: 0.12, fill: { color: 'DBEAFE' }, line: { color: '93C5FD' } });

    const servicesSlide = pptx.addSlide();
    servicesSlide.addText('Service state overview', { x: 0.5, y: 0.4, w: 5.5, h: 0.4, fontSize: 20, bold: true, color: '0F172A' });
    servicesSlide.addText(buildReportSectionText('Top service findings', context.toolSummaries.length > 0
      ? context.toolSummaries.map((item) => `${item.title}: ${item.summary} — ${item.detail}`)
      : ['No tool-backed service findings were available.']), { x: 0.5, y: 1.0, w: 5.8, h: 4.8, fontSize: 12, color: '0F172A', margin: 0.12, fill: { color: 'FFFFFF' }, line: { color: 'CBD5E1' } });
    servicesSlide.addText(buildReportSectionText('Next actions', context.nextActions), { x: 6.7, y: 1.0, w: 5.4, h: 4.8, fontSize: 12, color: '0F172A', margin: 0.12, fill: { color: 'FFFFFF' }, line: { color: 'CBD5E1' } });

    const traceSlide = pptx.addSlide();
    traceSlide.addText('Investigation trace', { x: 0.5, y: 0.4, w: 5.5, h: 0.4, fontSize: 20, bold: true, color: '0F172A' });
    traceSlide.addText(buildReportSectionText('Reasoning steps', context.steps.slice(0, 8).map((item) => `Step ${item.step ?? '?'}${item.tool_call?.name ? ` (${item.tool_call.name})` : ''}: ${item.thought || 'No thought recorded.'}`)), { x: 0.5, y: 1.0, w: 11.6, h: 5.2, fontSize: 12, color: '0F172A', margin: 0.12, fill: { color: 'FFFFFF' }, line: { color: 'CBD5E1' } });

    await pptx.writeFile({ fileName: `openshift-sre-console-${context.reportType}-${createTimestampSlug()}.pptx` });
  };

  const exportConsolePdf = async (context) => {
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
    doc.text(`Run ${context.runId} • ${context.generatedAt.toLocaleString()}`, 48, cursorY);
    cursorY += 24;
    addBlock('Prompt', [context.prompt]);
    addBlock('Answer highlights', context.answerHighlights.length > 0 ? context.answerHighlights : ['No answer highlights were available.']);
    addBlock('Service state overview', context.toolSummaries.length > 0 ? context.toolSummaries.map((item) => `${item.title}: ${item.summary} — ${item.detail}`) : ['No tool-backed service findings were available.']);
    addBlock('Next actions', context.nextActions);
    addBlock('Reasoning trace', context.steps.slice(0, 8).map((item) => `Step ${item.step ?? '?'}${item.tool_call?.name ? ` (${item.tool_call.name})` : ''}: ${item.thought || 'No thought recorded.'}`));
    doc.save(`openshift-sre-console-${context.reportType}-${createTimestampSlug()}.pdf`);
  };

  const exportConsoleWord = async (context) => {
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
    <p class="meta">Run ${escapeHtml(context.runId)} · ${escapeHtml(context.generatedAt.toLocaleString())}</p>
    <div>
      <span class="chip">Steps: ${escapeHtml(context.steps.length)}</span>
      <span class="chip">Findings: ${escapeHtml(context.toolSummaries.length)}</span>
    </div>
    <div class="section">
      <h2>Prompt</h2>
      <p>${escapeHtml(context.prompt).replace(/\n/g, '<br>')}</p>
    </div>
    <div class="section">
      <h2>Answer highlights</h2>
      <ul>${(context.answerHighlights.length > 0 ? context.answerHighlights : ['No answer highlights were available.']).map((line) => `<li>${escapeHtml(line)}</li>`).join('')}</ul>
    </div>
    <div class="section">
      <h2>Service state overview</h2>
      <ul>${(context.toolSummaries.length > 0 ? context.toolSummaries.map((item) => `${item.title}: ${item.summary} — ${item.detail}`) : ['No tool-backed service findings were available.']).map((line) => `<li>${escapeHtml(line)}</li>`).join('')}</ul>
    </div>
    <div class="section">
      <h2>Next actions</h2>
      <ul>${context.nextActions.map((line) => `<li>${escapeHtml(line)}</li>`).join('')}</ul>
    </div>
    <div class="section">
      <h2>Reasoning trace</h2>
      <ul>${context.steps.slice(0, 8).map((item) => `<li>${escapeHtml(`Step ${item.step ?? '?'}${item.tool_call?.name ? ` (${item.tool_call.name})` : ''}: ${item.thought || 'No thought recorded.'}`)}</li>`).join('')}</ul>
    </div>
  </body>
</html>`;
    downloadBlob(`openshift-sre-console-${context.reportType}-${createTimestampSlug()}.doc`, new Blob([html], { type: 'application/msword' }));
  };

  const updateConsoleReportExportState = () => {
    const hasAnswer = Boolean(lastRunContext?.answer);
    consoleReportExportButtons.forEach((button) => {
      const isExporting = button.dataset.agentConsoleExporting === 'true';
      button.disabled = !hasAnswer || isExporting;
    });
    if (!hasAnswer) {
      setConsoleReportStatus('Run the agent to unlock console response exports.');
    }
  };

  const handleConsoleReportExport = async (button) => {
    if (!button || !lastRunContext?.answer) {
      setConsoleReportStatus('Run the agent first so there is live content to export.', 'error');
      return;
    }
    const reportType = button.dataset.agentConsoleExportReport || 'operator-response';
    const format = button.dataset.agentConsoleExportFormat || 'word';
    const context = buildConsoleReportContext(reportType);
    const originalLabel = button.textContent;
    button.dataset.agentConsoleExporting = 'true';
    button.textContent = `Preparing ${format.toUpperCase()}…`;
    updateConsoleReportExportState();
    setConsoleReportStatus(`Building ${context.reportLabel} as ${format.toUpperCase()}…`, 'ok');
    try {
      if (format === 'csv') {
        await exportConsoleCsv(context);
      } else if (format === 'ppt') {
        await exportConsolePpt(context);
      } else if (format === 'pdf') {
        await exportConsolePdf(context);
      } else {
        await exportConsoleWord(context);
      }
      setConsoleReportStatus(`${context.reportLabel} exported as ${format.toUpperCase()}.`, 'ok');
      if (typeof showToast === 'function') {
        showToast(`${context.reportLabel} exported as ${format.toUpperCase()}.`, 'success');
      }
    } catch (error) {
      const message = error instanceof Error ? error.message : `Unable to export ${context.reportLabel}.`;
      setConsoleReportStatus(message, 'error');
      if (typeof showToast === 'function') {
        showToast(message, 'error');
      }
    } finally {
      button.dataset.agentConsoleExporting = 'false';
      button.textContent = originalLabel;
      updateConsoleReportExportState();
    }
  };

  const renderModelOptions = (catalog = null, preferredValue = '') => {
    if (!modelNameInput) {
      return;
    }

    const defaultModel = currentProvider().default_model || modelNameInput.dataset.agentDefaultModel || 'gpt-oss:20b';
    const currentValue = preferredValue || modelNameInput.value || defaultModel;
    const catalogModels = Array.isArray(catalog?.models) ? catalog.models : [];
    const optionMap = new Map();

    for (const model of catalogModels) {
      const name = model?.name || model?.model;
      if (!name) {
        continue;
      }
      const suffix = [model.loaded ? 'loaded' : '', model.parameter_size || ''].filter(Boolean).join(' · ');
      optionMap.set(name, suffix ? `${name} · ${suffix}` : name);
    }

    if (!optionMap.has(currentValue)) {
      optionMap.set(currentValue, currentValue);
    }
    if (!optionMap.has(defaultModel)) {
      optionMap.set(defaultModel, defaultModel);
    }

    modelNameInput.innerHTML = Array.from(optionMap.entries()).map(([value, label]) => `
      <option value="${escapeHtml(value)}">${escapeHtml(label)}</option>
    `).join('');
    modelNameInput.value = currentValue;
    modelNameInput.disabled = false;
  };

  const loadAvailableModels = async ({ baseUrl = '', silent = false } = {}) => {
    if (!modelNameInput) {
      return;
    }
    if (currentProviderId() !== 'ollama') {
      modelNameInput.disabled = true;
      renderModelOptions(null, modelNameInput.value || currentProvider().default_model || providerCatalog.configured_model_name || 'gpt-oss:20b');
      return;
    }

    const currentValue = modelNameInput.value || modelNameInput.dataset.agentDefaultModel || 'gpt-oss:20b';
    modelNameInput.disabled = true;
    modelNameInput.innerHTML = `<option value="${escapeHtml(currentValue)}">Loading models…</option>`;
    modelNameInput.value = currentValue;

    const query = new URLSearchParams();
    if (baseUrl) {
      query.set('ollama_base_url', baseUrl);
    }

    try {
      const response = await fetch(`/ollama/models${query.toString() ? `?${query}` : ''}`);
      const payload = await response.json();
      if (!response.ok) {
        throw new Error(payload.detail || `Model list request failed with status ${response.status}`);
      }
      renderModelOptions(payload, currentValue || payload.configured_model_name || 'gpt-oss:20b');
      if (!silent) {
        setStatus(`Loaded ${payload.model_count ?? 0} model option(s) from Ollama.`, 'ok');
      }
    } catch (error) {
      renderModelOptions(null, currentValue);
      if (!silent) {
        setStatus(error instanceof Error ? error.message : 'Unable to load available Ollama models.', 'error');
      }
    }
  };

  const scheduleModelRefresh = ({ silent = true } = {}) => {
    window.clearTimeout(modelRefreshHandle);
    modelRefreshHandle = window.setTimeout(() => {
      loadAvailableModels({ baseUrl: ollamaBaseUrlInput?.value.trim() || '', silent });
    }, 250);
  };

  const renderSteps = (items) => {
    steps.innerHTML = '';
    if (!Array.isArray(items) || items.length === 0) {
      steps.innerHTML = '<p class="agent-console__meta">No reasoning steps were returned.</p>';
      return;
    }

    for (const item of items) {
      const details = document.createElement('details');
      details.className = 'agent-console__step';

      const summary = document.createElement('summary');
      summary.textContent = `Step ${item.step ?? '?'}${item.tool_call?.name ? ` · ${item.tool_call.name}` : ''}`;
      details.appendChild(summary);

      const pre = document.createElement('pre');
      pre.textContent = JSON.stringify(item, null, 2);
      details.appendChild(pre);
      steps.appendChild(details);
    }
  };

  const humanizeToolName = (name = '') => name
    .replace(/^list_/, '')
    .replace(/^get_/, '')
    .replace(/^run_/, '')
    .split('_')
    .map((part) => ({ oc: 'oc', pvc: 'PVC', pv: 'PV', scc: 'SCC', olm: 'OLM', csv: 'CSV', mcp: 'MCP', api: 'API' }[part] || `${part.charAt(0).toUpperCase()}${part.slice(1)}`))
    .join(' ');

  const classifyError = (message = '') => {
    const lowered = message.toLowerCase();
    if (lowered.includes('not subscribed') || lowered.includes('not enabled') || lowered.includes('invalidaccessexception')) {
      return { kind: 'warning', summary: 'Service not enabled or unsubscribed' };
    }
    if (
      lowered.includes('unrecognizedclientexception')
      || lowered.includes('invalidclienttokenid')
      || lowered.includes('expiredtoken')
      || lowered.includes('security token included in the request is invalid')
      || lowered.includes('invalid security token')
      || lowered.includes('signaturedoesnotmatch')
    ) {
      return { kind: 'error', summary: 'Credentials or security token invalid' };
    }
    if (lowered.includes('accessdenied') || lowered.includes('unauthorized')) {
      return { kind: 'error', summary: 'Access denied' };
    }
    if (lowered.includes('unsupported') || lowered.includes('unknown service')) {
      return { kind: 'warning', summary: 'Unsupported or unavailable service' };
    }
    return { kind: 'error', summary: 'Service returned an error' };
  };

  const summarizeStep = (item) => {
    const toolName = item.tool_call?.name;
    const label = humanizeToolName(toolName || 'step');
    const result = item.tool_result || {};
    const errorMessage = result.error || item.tool_error;


    if (errorMessage) {
      const classified = classifyError(String(errorMessage));
      return {
        title: label,
        kind: classified.kind,
        summary: classified.summary,
        detail: classified.summary === 'Credentials or security token invalid'
          ? 'The active cluster or provider credentials were rejected for this request. Refresh the credentials or scope overrides and retry.'
          : String(errorMessage)
      };
    }

    const severityCounts = result.severity_counts;
    if (severityCounts && Object.keys(severityCounts).length > 0) {
      return {
        title: label,
        kind: 'ok',
        summary: 'Findings returned',
        detail: Object.entries(severityCounts).map(([key, value]) => `${key}: ${value}`).join(' · ')
      };
    }


    const complianceCounts = result.compliance_type_counts;
    if (complianceCounts && Object.keys(complianceCounts).length > 0) {
      return {
        title: label,

        kind: 'ok',
        summary: 'Compliance summary returned',
        detail: Object.entries(complianceCounts).map(([key, value]) => `${key}: ${value}`).join(' · ')
      };
    }

    const count = Number.isFinite(Number(result.count)) ? Number(result.count) : null;
    if (count === 0 && ['list_securityhub_findings', 'list_guardduty_findings', 'list_inspector_findings'].includes(toolName)) {
      return {

        title: label,
        kind: 'ok',
        summary: 'Healthy / no sampled findings',
        detail: 'The service responded, but no findings were returned in the current sample.'
      };
    }
    if (count === 0) {
      return {
        title: label,

        kind: 'neutral',
        summary: 'No rows returned',
        detail: 'The service responded, but no resources or rows were returned for this query.'
      };
    }
    if (count && count > 0) {
      return {
        title: label,
        kind: 'ok',

        summary: `${count} item(s) returned`,
        detail: 'The service returned live inventory or findings for this step.'
      };
    }

    return {
      title: label,
      kind: 'neutral',
      summary: 'Step completed',
      detail: 'The step completed without a count-based summary.'
    };
  };

  const renderCards = (items) => {
    cards.innerHTML = '';
    const toolSteps = (Array.isArray(items) ? items : []).filter((item) => item.tool_call?.name);
    if (toolSteps.length === 0) {
      cards.innerHTML = '<p class="agent-console__meta">No service-state cards were produced.</p>';
      return;
    }

    for (const item of toolSteps) {
      const summary = summarizeStep(item);
      const card = document.createElement('article');
      card.className = `agent-console__card agent-console__card--${summary.kind}`;


      const title = document.createElement('h4');
      title.textContent = summary.title;
      card.appendChild(title);

      const statusLine = document.createElement('p');
      statusLine.className = 'agent-console__card-summary';

      statusLine.textContent = summary.summary;
      card.appendChild(statusLine);

      const detail = document.createElement('p');
      detail.className = 'agent-console__card-detail';
      detail.textContent = summary.detail;
      card.appendChild(detail);


      cards.appendChild(card);
    }
  };


  const createKeyValueTable = (titleText, values) => {
    const wrapper = document.createElement('section');

    wrapper.className = 'agent-console__table-block';

    const title = document.createElement('h4');
    title.textContent = titleText;

    wrapper.appendChild(title);

    const table = document.createElement('table');
    table.className = 'agent-console__table';


    const tbody = document.createElement('tbody');
    for (const [key, value] of Object.entries(values)) {

      const row = document.createElement('tr');
      const keyCell = document.createElement('th');
      keyCell.textContent = key;

      const valueCell = document.createElement('td');
      valueCell.textContent = String(value);
      row.appendChild(keyCell);

      row.appendChild(valueCell);
      tbody.appendChild(row);

    }
    table.appendChild(tbody);
    wrapper.appendChild(table);
    return wrapper;
  };

  const createDatasetTable = (titleText, rows) => {
    if (!Array.isArray(rows) || rows.length === 0) {
      return null;
    }

    const normalizedRows = rows.slice(0, 10).map((row) => {
      const normalized = {};
      for (const [key, value] of Object.entries(row || {})) {
        if (value && typeof value === 'object' && 'amount' in value && 'unit' in value) {
          normalized[key] = `${value.amount} ${value.unit}`;
        } else if (Array.isArray(value)) {
          normalized[key] = value.join(', ');
        } else {
          normalized[key] = value ?? '';
        }
      }
      return normalized;
    });

    const columns = Array.from(new Set(normalizedRows.flatMap((row) => Object.keys(row))));
    const wrapper = document.createElement('section');
    wrapper.className = 'agent-console__table-block';

    const title = document.createElement('h4');
    title.textContent = titleText;
    wrapper.appendChild(title);

    const table = document.createElement('table');
    table.className = 'agent-console__table';

    const thead = document.createElement('thead');
    const headRow = document.createElement('tr');
    for (const column of columns) {
      const th = document.createElement('th');
      th.textContent = column.replace(/_/g, ' ');
      headRow.appendChild(th);
    }
    thead.appendChild(headRow);
    table.appendChild(thead);

    const tbody = document.createElement('tbody');
    for (const row of normalizedRows) {
      const tr = document.createElement('tr');
      for (const column of columns) {
        const td = document.createElement('td');
        td.textContent = String(row[column] ?? '');
        tr.appendChild(td);
      }
      tbody.appendChild(tr);
    }
    table.appendChild(tbody);
    wrapper.appendChild(table);
    return wrapper;
  };

  const renderTables = (items) => {
    tables.innerHTML = '';
    const toolSteps = (Array.isArray(items) ? items : []).filter((item) => item.tool_call?.name);
    let rendered = 0;

    for (const item of toolSteps) {
      const label = humanizeToolName(item.tool_call?.name || 'Step');
      const result = item.tool_result || {};
      if (result.severity_counts && Object.keys(result.severity_counts).length > 0) {
        tables.appendChild(createKeyValueTable(`${label} severity summary`, result.severity_counts));
        rendered += 1;
      }
      if (result.compliance_type_counts && Object.keys(result.compliance_type_counts).length > 0) {
        tables.appendChild(createKeyValueTable(`${label} compliance summary`, result.compliance_type_counts));
        rendered += 1;
      }
      if (result.total_unblended_cost && typeof result.total_unblended_cost === 'object') {
        tables.appendChild(createKeyValueTable(`${label} cost summary`, {
          total: `${result.total_unblended_cost.amount} ${result.total_unblended_cost.unit}`,
          days: result.days ?? '',
          granularity: result.granularity ?? ''
        }));
        rendered += 1;
      }
      if (Array.isArray(result.service_costs) && result.service_costs.length > 0) {
        const table = createDatasetTable(`${label} service drilldown`, result.service_costs);
        if (table) {
          tables.appendChild(table);
          rendered += 1;
        }
      }
      if (Array.isArray(result.tag_costs) && result.tag_costs.length > 0) {
        const table = createDatasetTable(`${label} tag drilldown`, result.tag_costs);
        if (table) {
          tables.appendChild(table);
          rendered += 1;
        }
      }
      if (result.forecast_total && typeof result.forecast_total === 'object') {
        tables.appendChild(createKeyValueTable(`${label} forecast summary`, {
          forecast_total: `${result.forecast_total.amount} ${result.forecast_total.unit}`,
          mean_value: `${result.mean_value?.amount ?? ''} ${result.mean_value?.unit ?? ''}`,
          lower_bound: `${result.prediction_interval_lower?.amount ?? ''} ${result.prediction_interval_lower?.unit ?? ''}`,
          upper_bound: `${result.prediction_interval_upper?.amount ?? ''} ${result.prediction_interval_upper?.unit ?? ''}`,
          months: result.months ?? ''
        }));
        rendered += 1;
      }
      if (Array.isArray(result.coverage_by_time) && result.coverage_by_time.length > 0) {
        tables.appendChild(createKeyValueTable(`${label} coverage summary`, {
          average_coverage_percentage: `${result.average_coverage_percentage ?? 0}%`,
          days: result.days ?? '',
          granularity: result.granularity ?? ''
        }));
        const table = createDatasetTable(`${label} coverage drilldown`, result.coverage_by_time);
        if (table) {
          tables.appendChild(table);
        }
        rendered += 2;
      }
      if (Array.isArray(result.recommendations) && result.recommendations.length > 0) {
        tables.appendChild(createKeyValueTable(`${label} recommendation summary`, {
          recommendation_count: result.count ?? 0,
          estimated_total_monthly_savings: `${result.estimated_total_monthly_savings?.amount ?? 0} ${result.estimated_total_monthly_savings?.unit ?? 'USD'}`,
          lookback_period: result.lookback_period ?? '',
          service: result.service ?? ''
        }));
        const table = createDatasetTable(`${label} recommendation drilldown`, result.recommendations);
        if (table) {
          tables.appendChild(table);
        }
        rendered += 2;
      }
    }

    if (rendered === 0) {
      tables.innerHTML = '<p class="agent-console__meta">No severity, compliance, or FinOps summary tables were returned for this run.</p>';
    }
  };

  const formatNumber = (value) => {
    const numeric = Number(value);
    if (!Number.isFinite(numeric)) {
      return String(value ?? '');
    }
    return new Intl.NumberFormat(undefined, { maximumFractionDigits: 2 }).format(numeric);
  };

  const formatMetricValue = (value, unit) => unit ? `${formatNumber(value)} ${unit}` : formatNumber(value);

  const formatBytes = (value) => {
    const numeric = Number(value);
    if (!Number.isFinite(numeric) || numeric <= 0) {
      return '—';
    }
    const units = ['B', 'KiB', 'MiB', 'GiB', 'TiB'];
    let size = numeric;
    let index = 0;
    while (size >= 1024 && index < units.length - 1) {
      size /= 1024;
      index += 1;
    }
    return `${formatNumber(size)} ${units[index]}`;
  };

  const formatPercent = (value) => {
    const numeric = Number(value);
    return Number.isFinite(numeric) ? `${formatNumber(numeric)}%` : '—';
  };

  const formatCurrency = (value, unit = 'USD') => {
    const numeric = Number(value);
    if (!Number.isFinite(numeric)) {
      return '—';
    }
    return `${new Intl.NumberFormat(undefined, { style: 'currency', currency: unit, maximumFractionDigits: 2 }).format(numeric)}`;
  };

  const safeNumber = (value) => {
    const numeric = Number(value);
    return Number.isFinite(numeric) ? numeric : 0;
  };

  const slugify = (value = '') => value.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/(^-|-$)/g, '');

  const isFinopsTool = (toolName = '') => FINOPS_TOOL_NAMES.has(toolName);

  const serviceCategory = (service = '') => {
    const normalized = String(service).toLowerCase();
    if (/(node|machine|worker|capacity|cpu|memory|autoscal)/.test(normalized)) {
      return 'compute';
    }
    if (/(storage|volume|pvc|pv|image|registry|build|artifact)/.test(normalized)) {
      return 'storage';
    }
    return null;
  };

  const upsertOpportunity = (opportunities, candidate) => {
    const existing = opportunities.find((item) => item.key === candidate.key);
    if (!existing) {
      opportunities.push(candidate);
      return;
    }
    if ((candidate.estimatedMonthlySavings || 0) > (existing.estimatedMonthlySavings || 0)) {
      Object.assign(existing, candidate);
    }
  };

  const createQueueEntryFromOpportunity = (opportunity, autoApprove) => ({
    opportunityKey: opportunity.key,
    title: opportunity.title,
    category: opportunity.category,
    estimatedMonthlySavings: opportunity.estimatedMonthlySavings,
    unit: opportunity.unit || 'USD',
    risk: opportunity.risk,
    confidence: opportunity.confidence,
    action: opportunity.action,
    basis: opportunity.basis,
    evidence: opportunity.evidence,
    executionPlan: opportunity.executionPlan,
    autoApproved: Boolean(autoApprove),
    executionMode: 'future-safe-execution-plan-only'
  });

  const fetchFinopsQueue = async () => {
    const response = await fetch('/finops/queue');
    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload.detail || `Queue request failed with status ${response.status}`);
    }
    return payload;
  };

  const createFinopsQueueItem = async (opportunity) => {
    const response = await fetch('/finops/queue', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        opportunity_key: opportunity.opportunityKey,
        title: opportunity.title,
        category: opportunity.category,
        estimated_monthly_savings: opportunity.estimatedMonthlySavings,
        unit: opportunity.unit,
        risk: opportunity.risk,
        confidence: opportunity.confidence,
        action: opportunity.action,
        basis: opportunity.basis,
        evidence: opportunity.evidence,
        execution_plan: opportunity.executionPlan,
        run_id: currentFinopsWorkflow?.runId || null,
        auto_approve: Boolean(finopsAutoApproveInput?.checked),
        execution_mode: opportunity.executionMode,
      })
    });
    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload.detail || `Queue create failed with status ${response.status}`);
    }
    return payload;
  };

  const updateFinopsQueueItemStage = async (itemId, executionStage) => {
    const response = await fetch(`/finops/queue/${itemId}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ execution_stage: executionStage })
    });
    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload.detail || `Queue update failed with status ${response.status}`);
    }
    return payload;
  };

  const deleteFinopsQueueItem = async (itemId) => {
    const response = await fetch(`/finops/queue/${itemId}`, { method: 'DELETE' });
    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload.detail || `Queue delete failed with status ${response.status}`);
    }
    return payload;
  };

  const buildFinopsWorkflow = (items, runId = null) => {
    const toolSteps = (Array.isArray(items) ? items : []).filter((item) => isFinopsTool(item.tool_call?.name));
    if (toolSteps.length === 0) {
      return null;
    }

    const opportunities = [];
    const overview = {
      totalObservedSpend: null,
      forecastTotal: null,
      forecastUnit: 'USD',
      savingsPlansCoverage: null,
      rightsizingSavings: 0,
      estimateNote: 'Estimated savings include both direct recommendations and conservative heuristics based on observed spend signals.'
    };

    for (const step of toolSteps) {
      const toolName = step.tool_call?.name;
      const result = step.tool_result || {};

      if (toolName === 'list_cost_and_usage_summary' && result.total_unblended_cost) {
        overview.totalObservedSpend = safeNumber(result.total_unblended_cost.amount);
      }

      if (toolName === 'get_cost_forecast' && result.forecast_total) {
        overview.forecastTotal = safeNumber(result.forecast_total.amount);
        overview.forecastUnit = result.forecast_total.unit || 'USD';
      }

      if (toolName === 'list_rightsizing_recommendations') {
        const recommendations = Array.isArray(result.recommendations) ? result.recommendations : [];
        overview.rightsizingSavings = safeNumber(result.estimated_total_monthly_savings?.amount);
        for (const recommendation of recommendations) {
          const savings = safeNumber(recommendation.estimated_monthly_savings);
          const resourceId = recommendation.resource_id || recommendation.instance_name || 'resource';
          upsertOpportunity(opportunities, {
            key: `compute-rightsize-${slugify(resourceId)}`,
            title: `Rightsize ${resourceId}`,
            category: 'compute',
            estimatedMonthlySavings: savings,
            unit: recommendation.currency_code || result.estimated_total_monthly_savings?.unit || 'USD',
            basis: 'Direct rightsizing recommendation',
            confidence: 'high',
            risk: 'medium',
            action: `Validate workload performance headroom for ${resourceId} and apply the recommended instance-size change during a maintenance window.`,
            evidence: `${recommendation.current_instance_type || 'Current instance'} → ${recommendation.recommended_instance_type || 'recommended target'} with projected savings ${formatCurrency(savings, recommendation.currency_code || 'USD')}.`,
            executionPlan: `Future safe execution plan: confirm owner approval, compare CloudWatch utilization trends, schedule the resize/change, and verify rollback criteria before applying the instance-size update.`
          });
        }
      }

      if (toolName === 'list_savings_plans_coverage') {
        const coverage = safeNumber(result.average_coverage_percentage);
        overview.savingsPlansCoverage = coverage;
        const rows = Array.isArray(result.coverage_by_time) ? result.coverage_by_time : [];
        const uncoveredAverage = rows.length
          ? rows.reduce((sum, row) => sum + safeNumber(row.on_demand_cost?.amount), 0) / rows.length
          : 0;
        if (coverage < 85 || uncoveredAverage > 0) {
          upsertOpportunity(opportunities, {
            key: 'commitment-savings-plans-gap',
            title: `Reduce uncovered baseline spend (${formatNumber(coverage)}%)`,
            category: 'commitment',
            estimatedMonthlySavings: uncoveredAverage,
            unit: rows[0]?.on_demand_cost?.unit || 'USD',
            basis: 'Observed uncovered on-demand spend',
            confidence: 'medium',
            risk: 'medium',
            action: 'Review steady-state platform usage and reduce uncovered waste or rebalance baseline capacity for the consistently uncovered portion of spend.',
            evidence: `Average coverage is ${formatNumber(coverage)}% with about ${formatCurrency(uncoveredAverage, rows[0]?.on_demand_cost?.unit || 'USD')} of uncovered on-demand cost per sampled period.`,
            executionPlan: 'Future safe execution plan: validate steady-state compute usage, simulate commitment scenarios, obtain finance approval, and then place the commitment purchase through controlled automation.'
          });
        }
      }

      if (toolName === 'list_cost_by_service') {
        const serviceCosts = Array.isArray(result.service_costs) ? result.service_costs.slice(0, 6) : [];
        for (const row of serviceCosts) {
          const amount = safeNumber(row.unblended_cost?.amount);
          const unit = row.unblended_cost?.unit || 'USD';
          const category = serviceCategory(row.service);
          if (!category) {
            continue;
          }
          const heuristicRate = category === 'storage' ? 0.08 : 0.1;
          const potential = Math.round(amount * heuristicRate * 100) / 100;
          upsertOpportunity(opportunities, {
            key: `${category}-service-${slugify(row.service)}`,
            title: `${row.service} cost optimization`,
            category,
            estimatedMonthlySavings: potential,
            unit,
            basis: `Heuristic ${formatNumber(heuristicRate * 100)}% optimization potential from observed spend`,
            confidence: 'medium',
            risk: category === 'compute' ? 'medium' : 'low',
            action: category === 'compute'
              ? `Review ${row.service} utilization, rightsizing posture, schedules, and scale settings to reduce avoidable spend.`
              : `Review ${row.service} lifecycle, tiering, retention, and snapshot policies to reduce storage cost.`,
            evidence: `${row.service} accounts for ${formatCurrency(amount, unit)} of observed spend in the selected window.`,
            executionPlan: `Future safe execution plan: capture current configuration, validate utilization/retention patterns, stage the optimization change, and verify rollback and business-owner approval before execution.`
          });
        }
      }

      if (toolName === 'list_cost_by_tag') {
        const tagCosts = Array.isArray(result.tag_costs) ? result.tag_costs : [];
        const unallocated = tagCosts.find((row) => ['<unallocated>', 'unallocated', 'unknown', 'untagged'].includes(String(row.tag_value || '').toLowerCase()));
        if (unallocated) {
          const amount = safeNumber(unallocated.unblended_cost?.amount);
          const unit = unallocated.unblended_cost?.unit || 'USD';
          upsertOpportunity(opportunities, {
            key: 'idle-untagged-or-unallocated-spend',
            title: 'Review unallocated or weakly-governed spend',
            category: 'idle',
            estimatedMonthlySavings: Math.round(amount * 0.15 * 100) / 100,
            unit,
            basis: 'Heuristic reduction potential from unallocated spend',
            confidence: 'medium',
            risk: 'low',
            action: 'Identify owners for unallocated spend, inspect low-value resources, and schedule cleanup for idle or forgotten assets.',
            evidence: `${formatCurrency(amount, unit)} is currently grouped under ${unallocated.tag_value}.`,
            executionPlan: 'Future safe execution plan: map owners, confirm business criticality, queue idle-resource cleanup, and execute only after approval and rollback checks.'
          });
        }
      }
    }

    const categoryOrder = ['compute', 'storage', 'commitment', 'idle'];
    const categorySummaries = categoryOrder.map((category) => {
      const rows = opportunities.filter((item) => item.category === category);
      const estimatedMonthlySavings = rows.reduce((sum, item) => sum + safeNumber(item.estimatedMonthlySavings), 0);
      return {
        category,
        label: `${category.charAt(0).toUpperCase()}${category.slice(1)}`,
        count: rows.length,
        estimatedMonthlySavings: Math.round(estimatedMonthlySavings * 100) / 100,
        unit: rows[0]?.unit || 'USD'
      };
    });

    return {
      runId,
      opportunities: opportunities.sort((left, right) => safeNumber(right.estimatedMonthlySavings) - safeNumber(left.estimatedMonthlySavings)),
      categorySummaries,
      overview,
      totalEstimatedMonthlySavings: opportunities.reduce((sum, item) => sum + safeNumber(item.estimatedMonthlySavings), 0)
    };
  };

  const renderFinopsOverview = (workflow) => {
    if (!workflow) {
      renderMessage(finopsOverview, 'Run the FinOps module to see compute, storage, commitment, and idle opportunities grouped into a workflow.');
      return;
    }

    const summaryCards = [
      { label: 'Opportunities', value: workflow.opportunities.length },
      { label: 'Estimated monthly savings', value: formatCurrency(workflow.totalEstimatedMonthlySavings, 'USD') },
      { label: 'Observed spend', value: workflow.overview.totalObservedSpend === null ? '—' : formatCurrency(workflow.overview.totalObservedSpend, 'USD') },
      { label: 'Forecast', value: workflow.overview.forecastTotal === null ? '—' : formatCurrency(workflow.overview.forecastTotal, workflow.overview.forecastUnit) },
      { label: 'Efficiency coverage', value: workflow.overview.savingsPlansCoverage === null ? '—' : `${formatNumber(workflow.overview.savingsPlansCoverage)}%` },
      { label: 'Direct rightsizing savings', value: formatCurrency(workflow.overview.rightsizingSavings, 'USD') }
    ].map((item) => `
      <article class="agent-console__history-card">
        <p class="agent-console__history-card-label">${item.label}</p>
        <p class="agent-console__history-card-value agent-console__history-card-value--small">${item.value}</p>
      </article>
    `).join('');

    const categoryRows = workflow.categorySummaries.map((item) => `
      <article class="agent-console__comparison-card">
        <div class="agent-console__comparison-header">
          <h5>${item.label}</h5>
          <span class="agent-console__status-pill ${item.count > 0 ? 'agent-console__status-pill--ok' : 'agent-console__status-pill--neutral'}">${item.count} item(s)</span>
        </div>
        <div class="agent-console__comparison-grid">
          <p>Estimated monthly savings</p>
          <p>${formatCurrency(item.estimatedMonthlySavings, item.unit)}</p>
        </div>
      </article>
    `).join('');

    finopsOverview.innerHTML = `
      <div class="agent-console__history-card-grid">${summaryCards}</div>
      <section class="agent-console__table-block">
        <h4>Opportunity categories</h4>
        <p class="agent-console__meta">${workflow.overview.estimateNote}</p>
        <div class="agent-console__comparison-list">${categoryRows}</div>
      </section>
    `;
  };

  const renderFinopsSavings = (workflow) => {
    if (!workflow || workflow.opportunities.length === 0) {
      renderMessage(finopsSavings, 'Estimated savings tables will appear here after a FinOps run.');
      return;
    }

    finopsSavings.innerHTML = `
      <section class="agent-console__table-block">
        <h4>Estimated savings and impact table</h4>
        <table class="agent-console__table agent-console__table--wide">
          <thead>
            <tr>
              <th>Category</th>
              <th>Opportunity</th>
              <th>Estimated monthly savings</th>
              <th>Basis</th>
              <th>Confidence</th>
            </tr>
          </thead>
          <tbody>
            ${workflow.opportunities.map((item) => `
              <tr>
                <td>${item.category}</td>
                <td>${item.title}</td>
                <td>${formatCurrency(item.estimatedMonthlySavings, item.unit)}</td>
                <td>${item.basis}</td>
                <td>${item.confidence}</td>
              </tr>
            `).join('')}
          </tbody>
        </table>
      </section>
    `;
  };

  const queueOpportunity = async (opportunity) => {
    try {
      const currentQueue = await fetchFinopsQueue();
      if (Array.isArray(currentQueue.items) && currentQueue.items.some((item) => item.opportunity_key === opportunity.key)) {
        setStatus(`Approval queue already contains ${opportunity.title}.`, 'ok');
        await renderFinopsQueue();
        return;
      }
      await createFinopsQueueItem(createQueueEntryFromOpportunity(opportunity, Boolean(finopsAutoApproveInput?.checked)));
      await renderFinopsQueue();
      setStatus(Boolean(finopsAutoApproveInput?.checked)
        ? `${opportunity.title} was auto-approved for future safe execution planning.`
        : `${opportunity.title} added to the approval queue.`, 'ok');
    } catch (error) {
      setStatus(error instanceof Error ? error.message : 'Unable to queue the FinOps action.', 'error');
    }
  };

  const queueAllOpportunities = async () => {
    if (!currentFinopsWorkflow?.opportunities?.length) {
      return;
    }
    try {
      const currentQueue = await fetchFinopsQueue();
      const existingKeys = new Set((currentQueue.items || []).map((item) => item.opportunity_key));
      let added = 0;
      for (const opportunity of currentFinopsWorkflow.opportunities) {
        if (existingKeys.has(opportunity.key)) {
          continue;
        }
        await createFinopsQueueItem(createQueueEntryFromOpportunity(opportunity, Boolean(finopsAutoApproveInput?.checked)));
        existingKeys.add(opportunity.key);
        added += 1;
      }
      await renderFinopsQueue();
      setStatus(added > 0
        ? `${added} FinOps action(s) added to the approval queue${Boolean(finopsAutoApproveInput?.checked) ? ' and auto-approved' : ''}.`
        : 'All current FinOps actions are already present in the approval queue.', 'ok');
    } catch (error) {
      setStatus(error instanceof Error ? error.message : 'Unable to queue FinOps actions.', 'error');
    }
  };

  const renderFinopsActions = (workflow) => {
    if (!workflow || workflow.opportunities.length === 0) {
      renderMessage(finopsActions, 'Recommended action cards will appear here after a FinOps run.');
      return;
    }

    finopsActions.innerHTML = `
      <section class="agent-console__table-block">
        <div class="agent-console__queue-header">
          <div>
            <h4>Recommended actions</h4>
            <p class="agent-console__meta">These cards are generated from observed FinOps signals. Queue them for future safe execution after review.</p>
          </div>
          <button class="agent-console__button agent-console__button--secondary" type="button" data-agent-finops-queue-all>Queue all actions</button>
        </div>
        <div class="agent-console__finops-action-grid">
          ${workflow.opportunities.map((item) => `
            <article class="agent-console__detail-card agent-console__finops-action-card">
              <div class="agent-console__module-badge-row">
                <span class="agent-console__history-badge">${item.category}</span>
                <span class="agent-console__history-badge agent-console__history-badge--${item.risk === 'low' ? 'ok' : item.risk === 'medium' ? 'warning' : 'error'}">risk: ${item.risk}</span>
                <span class="agent-console__history-badge">confidence: ${item.confidence}</span>
              </div>
              <h4>${item.title}</h4>
              <p><strong>Estimated monthly savings:</strong> ${formatCurrency(item.estimatedMonthlySavings, item.unit)}</p>
              <p><strong>Action:</strong> ${item.action}</p>
              <p><strong>Evidence:</strong> ${item.evidence}</p>
              <p><strong>Execution plan:</strong> ${item.executionPlan}</p>
              <div class="agent-console__actions">
                <button class="agent-console__example" type="button" data-agent-finops-queue-opportunity="${item.key}">Queue for approval</button>
              </div>
            </article>
          `).join('')}
        </div>
      </section>
    `;

    for (const button of finopsActions.querySelectorAll('[data-agent-finops-queue-opportunity]')) {
      button.addEventListener('click', async () => {
        const key = button.getAttribute('data-agent-finops-queue-opportunity');
        const opportunity = workflow.opportunities.find((item) => item.key === key);
        if (opportunity) {
          await queueOpportunity(opportunity);
        }
      });
    }

    finopsActions.querySelector('[data-agent-finops-queue-all]')?.addEventListener('click', async () => {
      await queueAllOpportunities();
    });
  };

  const renderFinopsQueue = async () => {
    try {
      const payload = await fetchFinopsQueue();
      if (!payload?.enabled) {
        renderMessage(finopsQueue, payload?.reason || 'Queue persistence is not configured.');
        return;
      }
      const queue = Array.isArray(payload.items) ? payload.items : [];
      if (queue.length === 0) {
        renderMessage(finopsQueue, 'Queued approval items will appear here after you add a recommendation.');
        return;
      }

      const stageCounts = Object.entries(payload.stage_counts || {}).map(([stage, count]) => `<span class="agent-console__history-badge">${stage.replace(/_/g, ' ')}: ${count}</span>`).join('');
      finopsQueue.innerHTML = `
      <div class="agent-console__history-badges">${stageCounts}</div>
      <div class="agent-console__metric-records">
        ${queue.map((item) => `
          <article class="agent-console__detail-card agent-console__queue-card">
            <div class="agent-console__queue-card-header">
              <div>
                <h4>${item.title}</h4>
                <p class="agent-console__meta">Queued ${new Date(item.created_at).toLocaleString()} · Updated ${new Date(item.updated_at).toLocaleString()}</p>
              </div>
              <span class="agent-console__status-pill ${item.execution_stage === 'approved' || item.execution_stage === 'executed' ? 'agent-console__status-pill--ok' : item.execution_stage === 'rolled_back' || item.execution_stage === 'deferred' ? 'agent-console__status-pill--error' : 'agent-console__status-pill--neutral'}">${item.execution_stage.replace(/_/g, ' ')}</span>
            </div>
            <p><strong>Category:</strong> ${item.category}</p>
            <p><strong>Estimated monthly savings:</strong> ${formatCurrency(item.estimated_monthly_savings, item.unit)}</p>
            <p><strong>Future safe execution mode:</strong> ${item.execution_mode}</p>
            <p><strong>Planned action:</strong> ${item.action}</p>
            <p><strong>Execution plan:</strong> ${item.execution_plan}</p>
            <div class="agent-console__actions">
              <button class="agent-console__example" type="button" data-agent-finops-queue-stage="planned" data-agent-finops-queue-id="${item.id}">Planned</button>
              <button class="agent-console__example" type="button" data-agent-finops-queue-stage="approved" data-agent-finops-queue-id="${item.id}">Approve</button>
              <button class="agent-console__example" type="button" data-agent-finops-queue-stage="precheck_passed" data-agent-finops-queue-id="${item.id}">Precheck passed</button>
              <button class="agent-console__example" type="button" data-agent-finops-queue-stage="ready_for_change_window" data-agent-finops-queue-id="${item.id}">Ready for change window</button>
              <button class="agent-console__example" type="button" data-agent-finops-queue-stage="executed" data-agent-finops-queue-id="${item.id}">Executed</button>
              <button class="agent-console__example" type="button" data-agent-finops-queue-stage="rolled_back" data-agent-finops-queue-id="${item.id}">Rolled back</button>
              <button class="agent-console__example" type="button" data-agent-finops-queue-stage="deferred" data-agent-finops-queue-id="${item.id}">Deferred</button>
              <button class="agent-console__example" type="button" data-agent-finops-queue-remove="${item.id}">Remove</button>
            </div>
          </article>
        `).join('')}
      </div>
    `;

      for (const button of finopsQueue.querySelectorAll('[data-agent-finops-queue-stage]')) {
        button.addEventListener('click', async () => {
          const id = button.getAttribute('data-agent-finops-queue-id');
          const executionStage = button.getAttribute('data-agent-finops-queue-stage');
          try {
            await updateFinopsQueueItemStage(id, executionStage);
            await renderFinopsQueue();
            setStatus(`Queue item moved to ${executionStage?.replace(/_/g, ' ')}.`, 'ok');
          } catch (error) {
            setStatus(error instanceof Error ? error.message : 'Unable to update the queue item.', 'error');
          }
        });
      }

      for (const button of finopsQueue.querySelectorAll('[data-agent-finops-queue-remove]')) {
        button.addEventListener('click', async () => {
          const id = button.getAttribute('data-agent-finops-queue-remove');
          try {
            await deleteFinopsQueueItem(id);
            await renderFinopsQueue();
            setStatus('Queue item removed.', 'ok');
          } catch (error) {
            setStatus(error instanceof Error ? error.message : 'Unable to remove the queue item.', 'error');
          }
        });
      }
    } catch (error) {
      renderMessage(finopsQueue, error instanceof Error ? error.message : 'Unable to load the FinOps queue.');
    }
  };

  const renderFinopsWorkflow = async (items, runId = null) => {
    currentFinopsWorkflow = buildFinopsWorkflow(items, runId);
    renderFinopsOverview(currentFinopsWorkflow);
    renderFinopsSavings(currentFinopsWorkflow);
    renderFinopsActions(currentFinopsWorkflow);
    await renderFinopsQueue();
  };

  const createSparkline = (points) => {
    if (!Array.isArray(points) || points.length === 0) {
      return '';
    }

    const width = 260;
    const height = 96;
    const padding = 12;
    const values = points.map((point) => Number(point.metric_value ?? 0));
    const min = Math.min(...values);
    const max = Math.max(...values);
    const range = max - min || 1;
    const stepX = points.length > 1 ? (width - padding * 2) / (points.length - 1) : 0;
    const polyline = points.map((point, index) => {
      const x = padding + (stepX * index);
      const y = height - padding - (((Number(point.metric_value ?? 0) - min) / range) * (height - padding * 2));
      return `${x},${y}`;
    }).join(' ');

    return `
      <svg viewBox="0 0 ${width} ${height}" class="agent-console__sparkline" role="img" aria-label="Metric trend">
        <line x1="${padding}" y1="${height - padding}" x2="${width - padding}" y2="${height - padding}" class="agent-console__sparkline-axis"></line>
        <polyline fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round" points="${polyline}"></polyline>
      </svg>
    `;
  };

  const renderHistorySummary = (payload) => {
    historySummary.innerHTML = '';
    if (!payload?.enabled) {
      renderMessage(historySummary, payload?.reason || 'Historical storage is disabled.');
      return;
    }

    const summary = payload.summary || {};
    const cardsMarkup = [
      { label: 'Stored runs', value: summary.total_runs ?? 0 },
      { label: 'Failed runs', value: summary.failed_runs ?? 0 },
      { label: 'Metrics recorded', value: summary.metrics_recorded ?? 0 },
      { label: 'Last run', value: summary.last_run_at ? new Date(summary.last_run_at).toLocaleString() : '—' },
    ].map((item) => `
      <article class="agent-console__history-card">
        <p class="agent-console__history-card-label">${item.label}</p>
        <p class="agent-console__history-card-value">${item.value}</p>
      </article>
    `).join('');

    const toolUsageMarkup = Array.isArray(payload.tool_usage) && payload.tool_usage.length > 0
      ? `<table class="agent-console__table"><thead><tr><th>Tool</th><th>Runs</th></tr></thead><tbody>${payload.tool_usage.slice(0, 8).map((row) => `<tr><td>${row.label}</td><td>${row.count}</td></tr>`).join('')}</tbody></table>`
      : '<p class="agent-console__meta">Tool usage will appear after persisted runs include tool calls.</p>';

    historySummary.innerHTML = `
      <div class="agent-console__history-card-grid">${cardsMarkup}</div>
      <section class="agent-console__table-block">
        <h4>Tool usage</h4>
        ${toolUsageMarkup}
      </section>
    `;
  };

  const renderHistoryTrends = (payload) => {
    historyTrends.innerHTML = '';
    if (!payload?.enabled) {
      renderMessage(historyTrends, payload?.reason || 'Historical storage is disabled.');
      return;
    }

    const series = Array.isArray(payload.metric_series) ? payload.metric_series : [];
    if (series.length === 0) {
      renderMessage(historyTrends, 'No persisted metric series are available yet. Run a few prompts that return metrics and refresh.');
      return;
    }

    historyTrends.innerHTML = series.map((seriesItem) => {
      const points = Array.isArray(seriesItem.points) ? seriesItem.points : [];
      const latest = points[points.length - 1];
      const dimensionBadge = latest?.dimensions
        ? Object.entries(latest.dimensions).map(([key, value]) => `<span class="agent-console__history-badge">${key}: ${value}</span>`).join('')
        : '';
      return `
        <article class="agent-console__trend-card">
          <div class="agent-console__trend-header">
            <div>
              <h4>${seriesItem.metric_label}</h4>
              <p class="agent-console__meta">${humanizeToolName(seriesItem.tool_name || 'metric')}</p>
            </div>
            <p class="agent-console__trend-value">${latest ? formatMetricValue(latest.metric_value, seriesItem.unit) : '—'}</p>
          </div>
          ${createSparkline(points)}
          <div class="agent-console__history-badges">${dimensionBadge}</div>
        </article>
      `;
    }).join('');
  };

  const renderHistoryRuns = (payload) => {
    historyRuns.innerHTML = '';
    if (!payload?.enabled) {
      renderMessage(historyRuns, payload?.reason || 'Historical storage is disabled.');
      return;
    }
    const recentRuns = Array.isArray(payload.recent_runs) ? payload.recent_runs : [];
    if (recentRuns.length === 0) {
      renderMessage(historyRuns, 'No persisted runs are available yet.');
      return;
    }

    historyRuns.innerHTML = `
      <section class="agent-console__table-block">
        <h4>Recent runs</h4>
        <table class="agent-console__table">
          <thead>
            <tr>
              <th>When</th>
              <th>Model</th>
              <th>Prompt</th>
              <th>Status</th>
              <th>Steps</th>
              <th>Duration</th>
            </tr>
          </thead>
          <tbody>
            ${recentRuns.map((run) => `
              <tr>
                <td>${new Date(run.created_at).toLocaleString()}</td>
                <td>${run.model_name}</td>
                <td>${run.prompt_excerpt || '—'}</td>
                <td>${run.status}</td>
                <td>${run.step_count}</td>
                <td>${formatNumber(run.duration_ms)} ms</td>
              </tr>
            `).join('')}
          </tbody>
        </table>
      </section>
    `;
  };

  const renderRuntimeSummaryPanel = (payload) => {
    if (!runtimeSummary) {
      return;
    }
    runtimeSummary.innerHTML = '';
    const containerPayload = payload?.containers || {};
    const databasePayload = payload?.database || {};
    if (!databasePayload?.enabled && (!Array.isArray(containerPayload.containers) || containerPayload.containers.length === 0)) {
      renderMessage(runtimeSummary, containerPayload.note || databasePayload.reason || 'Runtime telemetry is unavailable.');
      return;
    }

    const cardsMarkup = [
      { label: 'Telemetry checked', value: payload?.checked_at ? new Date(payload.checked_at).toLocaleString() : '—' },
      { label: 'Container runtime', value: containerPayload.runtime || 'unavailable' },
      { label: 'Containers tracked', value: containerPayload.containers?.length ?? 0 },
      { label: 'Database engine', value: databasePayload.dialect || 'disabled' },
      { label: 'Database size', value: formatBytes(databasePayload.utilization?.database_size_bytes) },
      { label: 'Tables tracked', value: databasePayload.utilization?.table_count ?? 0 }
    ].map((item) => `
      <article class="agent-console__history-card">
        <p class="agent-console__history-card-label">${item.label}</p>
        <p class="agent-console__history-card-value agent-console__history-card-value--small">${item.value}</p>
      </article>
    `).join('');

    runtimeSummary.innerHTML = `
      <div class="agent-console__history-card-grid">${cardsMarkup}</div>
      <section class="agent-console__table-block">
        <h4>Observability notes</h4>
        <p class="agent-console__meta">${containerPayload.note || 'Container CLI visibility is active.'}</p>
      </section>
    `;
  };

  const renderRuntimeContainersPanel = (payload) => {
    if (!runtimeContainers) {
      return;
    }
    runtimeContainers.innerHTML = '';
    const containerPayload = payload?.containers || {};
    const containers = Array.isArray(containerPayload.containers) ? containerPayload.containers : [];
    if (containers.length === 0) {
      renderMessage(runtimeContainers, containerPayload.note || 'No container telemetry is available right now.');
      return;
    }

    runtimeContainers.innerHTML = `
      <section class="agent-console__table-block">
        <div class="agent-console__queue-header">
          <div>
            <h4>Containers used by the local stack</h4>
            <p class="agent-console__meta">CPU, memory, size, and GPU values come from the local container runtime when available. Fallback rows stay visible so the console still explains what is running.</p>
          </div>
          <span class="agent-console__history-badge agent-console__history-badge--neutral">source: ${containerPayload.source || 'fallback'}</span>
        </div>
        <table class="agent-console__table agent-console__table--wide">
          <thead>
            <tr>
              <th>Container</th>
              <th>Image</th>
              <th>Status</th>
              <th>Size</th>
              <th>CPU</th>
              <th>Memory</th>
              <th>GPU</th>
              <th>Notes</th>
            </tr>
          </thead>
          <tbody>
            ${containers.map((container) => `
              <tr>
                <td>${container.name || '—'}</td>
                <td>${container.image || '—'}</td>
                <td>${container.status || container.state || '—'}</td>
                <td>${container.size || '—'}</td>
                <td>${formatPercent(container.cpu_percent)}</td>
                <td>${container.memory_usage || formatBytes(container.memory_usage_bytes)}${container.memory_limit ? ` / ${container.memory_limit}` : ''}${container.memory_percent != null ? ` (${formatPercent(container.memory_percent)})` : ''}</td>
                <td>${container.gpu_usage || 'Not exposed'}</td>
                <td>${container.note || container.gpu_note || '—'}</td>
              </tr>
            `).join('')}
          </tbody>
        </table>
      </section>
    `;
  };

  const renderRuntimeDatabasePanel = (payload) => {
    if (!runtimeDatabase) {
      return;
    }
    runtimeDatabase.innerHTML = '';
    const databasePayload = payload?.database || {};
    if (!databasePayload?.enabled) {
      renderMessage(runtimeDatabase, databasePayload.reason || 'Database telemetry is unavailable.');
      return;
    }

    const utilization = databasePayload.utilization || {};
    const runtimeStats = utilization.runtime_stats || {};
    const tables = Array.isArray(databasePayload.tables) ? databasePayload.tables : [];
    const summaryCards = [
      { label: 'Database', value: databasePayload.database_name || '—' },
      { label: 'Version', value: databasePayload.version || '—' },
      { label: 'Tracked runs', value: utilization.tracked_run_count ?? 0 },
      { label: 'Free space', value: formatBytes(utilization.free_bytes) },
    ].map((item) => `
      <article class="agent-console__history-card">
        <p class="agent-console__history-card-label">${item.label}</p>
        <p class="agent-console__history-card-value agent-console__history-card-value--small">${item.value}</p>
      </article>
    `).join('');

    const statRows = Object.entries(runtimeStats).length > 0
      ? `<table class="agent-console__table"><thead><tr><th>Runtime stat</th><th>Value</th></tr></thead><tbody>${Object.entries(runtimeStats).map(([key, value]) => `<tr><td>${key}</td><td>${value}</td></tr>`).join('')}</tbody></table>`
      : '<p class="agent-console__meta">No live database runtime stats were exposed by the current database engine.</p>';

    const tableRows = tables.length > 0
      ? `<table class="agent-console__table agent-console__table--wide"><thead><tr><th>Table</th><th>Rows</th><th>Size</th><th>Indexes</th><th>Primary key</th></tr></thead><tbody>${tables.map((table) => `<tr><td>${table.table_name}</td><td>${formatNumber(table.row_count ?? 0)}</td><td>${formatBytes(table.size_bytes)}</td><td>${table.indexes?.length ?? 0}</td><td>${(table.primary_key || []).join(', ') || '—'}</td></tr>`).join('')}</tbody></table>`
      : '<p class="agent-console__meta">No application tables were detected yet.</p>';

    const tableDetails = tables.map((table) => `
      <details class="agent-console__step">
        <summary>${table.table_name} · ${formatNumber(table.row_count ?? 0)} row(s) · ${formatBytes(table.size_bytes)}</summary>
        <div class="agent-console__table-block">
          <p class="agent-console__meta">Engine: ${table.engine || databasePayload.dialect || '—'} · Data size: ${formatBytes(table.data_size_bytes)} · Index size: ${formatBytes(table.index_size_bytes)} · Free: ${formatBytes(table.free_bytes)}</p>
          <table class="agent-console__table agent-console__table--wide">
            <thead>
              <tr>
                <th>Column</th>
                <th>Type</th>
                <th>Nullable</th>
                <th>Default</th>
              </tr>
            </thead>
            <tbody>
              ${(table.columns || []).map((column) => `<tr><td>${column.name}</td><td>${column.type}</td><td>${column.nullable ? 'yes' : 'no'}</td><td>${column.default || '—'}</td></tr>`).join('')}
            </tbody>
          </table>
        </div>
      </details>
    `).join('');

    runtimeDatabase.innerHTML = `
      <section class="agent-console__table-block">
        <h4>Database utilization</h4>
        <div class="agent-console__history-card-grid">${summaryCards}</div>
      </section>
      <section class="agent-console__table-block">
        <h4>Live database stats</h4>
        ${statRows}
      </section>
      <section class="agent-console__table-block">
        <h4>Table inventory</h4>
        ${tableRows}
      </section>
      <section class="agent-console__table-block">
        <h4>Table details dropdown</h4>
        ${tableDetails || '<p class="agent-console__meta">Table-level details will appear here after the database exposes schema metadata.</p>'}
      </section>
    `;
  };

  const loadRuntimeObservability = async () => {
    try {
      const response = await fetch('/runtime/observability');
      const payload = await response.json();
      if (!response.ok) {
        throw new Error(payload.detail || `Runtime telemetry request failed with status ${response.status}`);
      }
      renderRuntimeSummaryPanel(payload);
      renderRuntimeContainersPanel(payload);
      renderRuntimeDatabasePanel(payload);
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Unable to load runtime telemetry.';
      renderMessage(runtimeSummary, message);
      renderMessage(runtimeContainers, message);
      renderMessage(runtimeDatabase, message);
    }
  };

  const loadHistory = async () => {
    try {
      const response = await fetch('/history/overview');
      const payload = await response.json();
      if (!response.ok) {
        throw new Error(payload.detail || `History request failed with status ${response.status}`);
      }
      renderHistorySummary(payload);
      renderHistoryTrends(payload);
      renderHistoryRuns(payload);
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Unable to load historical metrics.';
      renderMessage(historySummary, message);
      renderMessage(historyTrends, message);
      renderMessage(historyRuns, message);
    }
  };

  const setBusy = (busy) => {
    runButton.disabled = busy;
    if (approvalApplyButton) {
      approvalApplyButton.disabled = busy;
    }

    runButton.textContent = busy ? 'Running…' : 'Run agent';
  };

  const runAgent = async () => {
    const prompt = promptInput.value.trim();
    if (prompt.length < 5) {
      setStatus('Please enter a more specific SRE prompt.', 'error');
      promptInput.focus();
      return;
    }

    setBusy(true);
    setStatus('Calling /chat …', '');
    answer.textContent = '';
    clearApprovalOptions();
    cards.innerHTML = '';
    tables.innerHTML = '';
    steps.innerHTML = '';

    try {
      const runtime = {
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
        cluster_scope: clusterScopeInput?.value.trim() || null,
        kube_context_name: kubeContextInput?.value.trim() || null,
        openshift_api_url: openshiftApiUrlInput?.value.trim() || null,
        openshift_token: openshiftTokenInput?.value || null,
        openshift_namespace: openshiftNamespaceInput?.value || null,
        verify_ssl: verifySslInput ? verifySslInput.checked : null
      };

      const response = await fetch('/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ prompt, runtime })
      });

      const payload = await response.json();
      if (!response.ok) {
        throw new Error(payload.detail || `Request failed with status ${response.status}`);
      }

      lastRunContext = {
        prompt,
        answer: payload.answer || '',
        steps: Array.isArray(payload.steps) ? payload.steps : [],
        runId: payload.run_id || null,
      };
      const parsedAnswer = parseApprovalOptions(payload.answer || '');
      renderAnswerText(parsedAnswer.displayText || '(No answer returned)');
      renderApprovalOptions(parsedAnswer.options);
      renderRootCauseCards(payload.answer || '');
      renderNextActionCards(payload.answer || '');
      renderCards(payload.steps);
      renderTables(payload.steps);
      await renderFinopsWorkflow(payload.steps, payload.run_id || null);
      renderSteps(payload.steps);
      await loadHistory();
      await loadRuntimeObservability();
      setStatus(payload.run_id ? `Agent run completed and stored as run #${payload.run_id}.` : 'Agent run completed.', 'ok');
    } catch (error) {
      answer.textContent = '';
      clearApprovalOptions();
      cards.innerHTML = '<p class="agent-console__meta">No service-state cards were produced because the request failed.</p>';
      tables.innerHTML = '<p class="agent-console__meta">No tables were produced because the request failed.</p>';
      renderRootCauseCards('');
      renderNextActionCards('');
      await renderFinopsWorkflow([], null);
      steps.innerHTML = '';
      setStatus(error instanceof Error ? error.message : 'Unexpected error while running the agent.', 'error');
    } finally {
      setBusy(false);
    }
  };

  runButton.addEventListener('click', runAgent);
  promptInput.addEventListener('keydown', (event) => {
    if ((event.metaKey || event.ctrlKey) && event.key === 'Enter') {
      event.preventDefault();
      runAgent();
    }
  });

  for (const button of promptButtons) {
    button.addEventListener('click', () => {
      const statusMessage = button.dataset.agentModule
        ? (button.dataset.agentModule === 'finops-advanced-optimizer'
          ? 'FinOps optimizer module template loaded. Review the prompt and run when ready.'
          : 'Technical troubleshooting module template loaded. Review the prompt and run when ready.')
        : button.closest('.agent-console__module-card')
          ? 'Guided module prompt loaded. Review the prompt and run when ready.'
          : 'Example prompt loaded. Review the prompt and run when ready.';
      loadPromptTemplate(button, statusMessage);
    });
  }

  syncTroubleshootingWorkflow({ updatePrompt: false });
  setActiveManagementTab(getActiveManagementTab());
  troubleshootingSelect?.addEventListener('change', () => {
    syncTroubleshootingWorkflow({ preferredScenarioId: troubleshootingSelect.value, preferredSymptom: 'auto', preservedChecks: [], updatePrompt: true });
  });
  serviceFilterInput?.addEventListener('change', () => {
    syncTroubleshootingWorkflow({ preferredScenarioId: troubleshootingSelect?.value, preferredSymptom: symptomInput?.value || 'auto', preservedChecks: getCheckedEvidenceItems(), updatePrompt: true });
    setStatus(`Filtered troubleshooting workflows for ${getSelectedOptionLabel(serviceFilterInput)}.`, 'ok');
  });
  symptomInput?.addEventListener('change', () => {
    renderTroubleshootingScenario();
    updateTroubleshootingPrompt();
  });
  [severityInput, environmentInput, blastRadiusInput, timeWindowInput, issueStartInput, lastHealthyInput, recentChangeInput, primaryResourceInput, affectedScopeInput, healthyResourceInput, unhealthyResourceInput, resourceIdsInput].forEach((node) => {
    node?.addEventListener('change', () => {
      renderTroubleshootingScenario();
      updateTroubleshootingPrompt();
    });
  });
  managementTabButtons.forEach((button) => {
    button.addEventListener('click', () => {
      setActiveManagementTab(button.dataset.agentManagementTab, { announce: true });
      renderTroubleshootingScenario();
      updateTroubleshootingPrompt();
      renderTroubleshootingProgress();
    });
  });
  [
    incidentPhaseInput,
    incidentTypeInput,
    communicationsStatusInput,
    stakeholderAudienceInput,
    restorationStatusInput,
    incidentOwnerInput,
    customerImpactInput,
    businessImpactInput,
    changeTypeInput,
    changeRiskInput,
    changeApprovalInput,
    changeImplementationInput,
    rollbackReadinessInput,
    changeWindowInput,
    changeSummaryInput,
    problemRecordInput,
    problemRecurrenceInput,
    rcaMethodInput,
    rootCauseDomainInput,
    knownErrorStatusInput,
    correctiveOwnerInput,
    problemNotesInput
  ].forEach((node) => {
    const eventName = node?.tagName === 'TEXTAREA' || node?.tagName === 'INPUT' ? 'input' : 'change';
    node?.addEventListener(eventName, () => {
      renderTroubleshootingScenario();
      updateTroubleshootingPrompt();
      renderTroubleshootingProgress();
    });
  });
  issueNotesInput?.addEventListener('blur', () => {
    renderTroubleshootingScenario();
    updateTroubleshootingPrompt('Prompt refreshed with the latest pasted notes.');
  });
  loadTroubleshootingButton?.addEventListener('click', loadSelectedTroubleshootingScenario);
  refreshWorkflowButton?.addEventListener('click', () => {
    renderTroubleshootingScenario();
    updateTroubleshootingPrompt('Prompt regenerated from the workflow context.');
  });
  presetSaveButton?.addEventListener('click', () => {
    const name = presetNameInput?.value?.trim();
    if (!name) {
      setStatus('Enter a preset name before saving.', 'error');
      presetNameInput?.focus();
      return;
    }
    const presets = getStoredTroubleshootingPresets().filter((preset) => preset.name !== name);
    presets.push({ name, state: collectTroubleshootingWorkflowState() });
    presets.sort((left, right) => left.name.localeCompare(right.name));
    setStoredTroubleshootingPresets(presets);
    refreshPresetOptions();
    if (presetSelect) {
      presetSelect.value = name;
    }
    setStatus(`Saved troubleshooting preset ${name}.`, 'ok');
  });
  presetLoadButton?.addEventListener('click', () => {
    const name = presetSelect?.value;
    const preset = getStoredTroubleshootingPresets().find((item) => item.name === name);
    if (!preset) {
      setStatus('Choose a saved preset to load.', 'error');
      return;
    }
    applyTroubleshootingWorkflowState(preset.state);
    if (presetNameInput) {
      presetNameInput.value = preset.name;
    }
    setStatus(`Loaded troubleshooting preset ${preset.name}.`, 'ok');
  });
  presetDeleteButton?.addEventListener('click', () => {
    const name = presetSelect?.value || presetNameInput?.value?.trim();
    if (!name) {
      setStatus('Choose a preset to delete.', 'error');
      return;
    }
    const presets = getStoredTroubleshootingPresets().filter((preset) => preset.name !== name);
    setStoredTroubleshootingPresets(presets);
    refreshPresetOptions();
    if (presetNameInput && presetNameInput.value === name) {
      presetNameInput.value = '';
    }
    setStatus(`Deleted troubleshooting preset ${name}.`, 'ok');
  });
  if (autoLoadTroubleshooting) {
    loadSelectedTroubleshootingScenario();
  }

  approvalApplyButton?.addEventListener('click', () => {
    const selected = approvalOptions.querySelector('input[name="agent-approval-option"]:checked');
    if (!selected) {
      setStatus('Choose an approval action before continuing.', 'error');
      return;
    }
    const selectedOption = parseApprovalOptions(lastRunContext?.answer || '').options.find((option) => option.command === selected.value);
    if (!selectedOption) {
      setStatus('Unable to resolve the selected approval option. Run the previous request again if needed.', 'error');
      return;
    }
    promptInput.value = buildApprovalPrompt(selectedOption);
    promptInput.focus();
    promptInput.setSelectionRange(0, promptInput.value.length);
    promptInput.scrollIntoView({ behavior: 'smooth', block: 'center' });
    setStatus(`Prepared ${selectedOption.command} as the next guided input. Review it or run it now.`, 'ok');
  });

  finopsAutoApproveInput?.addEventListener('change', () => {
    setStatus(finopsAutoApproveInput.checked
      ? 'Auto approve enabled for newly queued FinOps actions.'
      : 'Auto approve disabled. Newly queued FinOps actions will wait for review.', 'ok');
  });

  refreshPresetOptions();
  await loadProviderCatalog();
  renderModelOptions(null, modelNameInput?.dataset.agentDefaultModel || 'gpt-oss:20b');
  scheduleModelRefresh({ silent: true });
  llmProviderInput?.addEventListener('change', () => {
    syncProviderVisibility();
    if (currentProviderId() === 'ollama') {
      scheduleModelRefresh({ silent: true });
      setStatus('Switched to Local Ollama runtime.', 'ok');
    } else {
      loadAvailableModels({ silent: true });
      setStatus(`Switched to ${currentProvider().label}. Provide the required external credentials before running the agent.`, 'ok');
    }
  });
  ollamaBaseUrlInput?.addEventListener('change', () => scheduleModelRefresh({ silent: false }));
  ollamaBaseUrlInput?.addEventListener('blur', () => scheduleModelRefresh({ silent: true }));
  await renderFinopsWorkflow([], null);
  loadHistory();
  loadRuntimeObservability();

  // ---------------------------------------------------------------------------
  // v0.3.0 — Toast notification system
  // ---------------------------------------------------------------------------
  const toastContainer = document.createElement('div');
  toastContainer.className = 'agent-console__toast-container';
  toastContainer.setAttribute('aria-live', 'polite');
  document.body.appendChild(toastContainer);

  function showToast(message, kind = 'info', durationMs = 4000) {
    const toast = document.createElement('div');
    toast.className = `agent-console__toast agent-console__toast--${kind}`;
    toast.textContent = message;
    toastContainer.appendChild(toast);
    requestAnimationFrame(() => toast.classList.add('agent-console__toast--visible'));
    setTimeout(() => {
      toast.classList.remove('agent-console__toast--visible');
      toast.addEventListener('transitionend', () => toast.remove());
    }, durationMs);
  }

  // ---------------------------------------------------------------------------
  // v0.3.0 — Prompt history (localStorage)
  // ---------------------------------------------------------------------------
  const PROMPT_HISTORY_KEY = 'openshift-sre-prompt-history-v1';
  const MAX_HISTORY = 50;

  function getPromptHistory() {
    try { return JSON.parse(localStorage.getItem(PROMPT_HISTORY_KEY) || '[]'); } catch { return []; }
  }

  function savePromptToHistory(prompt) {
    const trimmed = prompt.trim();
    if (!trimmed || trimmed.length < 5) return;
    const history = getPromptHistory().filter(p => p !== trimmed);
    history.unshift(trimmed);
    localStorage.setItem(PROMPT_HISTORY_KEY, JSON.stringify(history.slice(0, MAX_HISTORY)));
  }

  // Autocomplete dropdown
  let historyDropdown = null;
  promptInput?.addEventListener('focus', () => {
    const history = getPromptHistory();
    if (!history.length) return;
    if (historyDropdown) historyDropdown.remove();
    historyDropdown = document.createElement('div');
    historyDropdown.className = 'agent-console__history-dropdown';
    history.slice(0, 8).forEach(entry => {
      const item = document.createElement('button');
      item.type = 'button';
      item.className = 'agent-console__history-item';
      item.textContent = entry.length > 100 ? entry.slice(0, 97) + '…' : entry;
      item.addEventListener('click', () => {
        promptInput.value = entry;
        historyDropdown.remove();
        historyDropdown = null;
        promptInput.focus();
      });
      historyDropdown.appendChild(item);
    });
    promptInput.parentElement?.appendChild(historyDropdown);
  });

  document.addEventListener('click', (e) => {
    if (historyDropdown && !historyDropdown.contains(e.target) && e.target !== promptInput) {
      historyDropdown.remove();
      historyDropdown = null;
    }
  });

  // Save prompt on submit
  const originalRunAgent = runAgent;
  const wrappedRunAgent = async () => {
    savePromptToHistory(promptInput.value);
    await originalRunAgent();
  };
  runButton.removeEventListener('click', runAgent);
  runButton.addEventListener('click', wrappedRunAgent);

  // ---------------------------------------------------------------------------
  // v0.3.0 — Keyboard shortcuts
  // ---------------------------------------------------------------------------
  document.addEventListener('keydown', (e) => {
    // Escape to stop / clear
    if (e.key === 'Escape' && !runButton.disabled) {
      promptInput.value = '';
      promptInput.focus();
      setStatus('Prompt cleared.', 'ok');
    }
    // Ctrl+/ to focus prompt
    if ((e.ctrlKey || e.metaKey) && e.key === '/') {
      e.preventDefault();
      promptInput?.focus();
    }
  });

  // ---------------------------------------------------------------------------
  // v0.3.0 — WebSocket toast notifications
  // ---------------------------------------------------------------------------
  try {
    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${wsProtocol}//${window.location.host}/ws/events`;
    const ws = new WebSocket(wsUrl);
    ws.addEventListener('message', (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === 'run_completed') {
          showToast(`Run #${data.run_id} completed (${data.duration_ms}ms)`, 'success');
        }
      } catch { /* ignore parse errors */ }
    });
    ws.addEventListener('error', () => { /* silent — WS is optional */ });
  } catch { /* WebSocket not available */ }

  // ---------------------------------------------------------------------------
  // v0.4.0 — Drafts, toolbars, session insights, and troubleshooting progress
  // ---------------------------------------------------------------------------
  const DRAFT_STORAGE_KEY = `openshift-sre-draft:${window.location.pathname}`;
  const SESSION_STORAGE_KEY = `openshift-sre-session:${window.location.pathname}`;
  let draftSaveTimer = null;

  const readStoredJson = (key, fallback) => {
    try {
      return JSON.parse(localStorage.getItem(key) || JSON.stringify(fallback));
    } catch {
      return fallback;
    }
  };

  const writeStoredJson = (key, value) => {
    try {
      localStorage.setItem(key, JSON.stringify(value));
    } catch {
      // Ignore localStorage failures in restricted preview contexts.
    }
  };

  const getDraftPayload = () => ({
    prompt: promptInput?.value || '',
    issueNotes: issueNotesInput?.value || '',
    scenarioId: troubleshootingSelect?.value || '',
    workflowState: collectTroubleshootingWorkflowState(),
    updatedAt: new Date().toISOString()
  });

  const getSessionPayload = () => readStoredJson(SESSION_STORAGE_KEY, {
    runCount: 0,
    successCount: 0,
    failureCount: 0,
    lastRunId: null,
    lastPrompt: '',
    lastUpdatedAt: null
  });

  const saveDraft = (manual = false) => {
    writeStoredJson(DRAFT_STORAGE_KEY, getDraftPayload());
    renderPromptToolbar();
    if (manual) {
      showToast('Prompt draft saved locally.', 'success');
    }
  };

  const restoreDraft = () => {
    const draft = readStoredJson(DRAFT_STORAGE_KEY, null);
    if (!draft || (!draft.prompt && !draft.issueNotes)) {
      showToast('No saved draft is available for this page yet.', 'info');
      return;
    }
    if (promptInput) {
      promptInput.value = draft.prompt || '';
    }
    if (issueNotesInput) {
      issueNotesInput.value = draft.issueNotes || '';
    }
    if (draft.workflowState) {
      applyTroubleshootingWorkflowState(draft.workflowState);
    } else if (troubleshootingSelect && draft.scenarioId) {
      troubleshootingSelect.value = draft.scenarioId;
      syncTroubleshootingWorkflow({ preferredScenarioId: draft.scenarioId, preferredSymptom: symptomInput?.value || 'auto', preservedChecks: getCheckedEvidenceItems(), updatePrompt: false });
    }
    renderPromptToolbar();
    renderTroubleshootingProgress();
    setStatus('Restored the latest saved draft for this page.', 'ok');
    showToast('Draft restored.', 'success');
  };

  const clearDraft = () => {
    try {
      localStorage.removeItem(DRAFT_STORAGE_KEY);
    } catch {
      // Ignore storage failures.
    }
    renderPromptToolbar();
    showToast('Saved draft cleared for this page.', 'info');
  };

  const updateSessionStats = ({ success, prompt, runId }) => {
    const current = getSessionPayload();
    const next = {
      runCount: current.runCount + 1,
      successCount: current.successCount + (success ? 1 : 0),
      failureCount: current.failureCount + (success ? 0 : 1),
      lastRunId: runId || current.lastRunId || null,
      lastPrompt: prompt,
      lastUpdatedAt: new Date().toISOString()
    };
    writeStoredJson(SESSION_STORAGE_KEY, next);
    renderSessionRail();
  };

  const copyToClipboard = async (value, successMessage) => {
    try {
      await navigator.clipboard.writeText(value);
      showToast(successMessage, 'success');
    } catch {
      showToast('Clipboard access was not available. You can still select and copy manually.', 'error');
    }
  };

  const downloadTextFile = (filename, text) => {
    const blob = new Blob([text], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
  };

  const promptToolbar = document.createElement('section');
  promptToolbar.className = 'agent-console__toolbar';
  promptInput?.insertAdjacentElement('afterend', promptToolbar);

  const sessionRail = document.createElement('section');
  sessionRail.className = 'agent-console__session-rail';
  answer.parentElement?.insertBefore(sessionRail, answer);

  let troubleshootingProgress = null;
  if (troubleshootingDetails?.parentElement) {
    troubleshootingProgress = document.createElement('section');
    troubleshootingProgress.className = 'agent-console__scenario-status';
    troubleshootingDetails.insertAdjacentElement('afterend', troubleshootingProgress);
  }

  const answerToolbar = document.createElement('div');
  answerToolbar.className = 'agent-console__toolbar';
  answer.insertAdjacentElement('beforebegin', answerToolbar);

  function renderPromptToolbar() {
    const draft = readStoredJson(DRAFT_STORAGE_KEY, null);
    const recentPrompts = getPromptHistory().slice(0, 5);
    const hasDraft = Boolean(draft?.prompt || draft?.issueNotes);
    promptToolbar.innerHTML = `
      <div class="agent-console__toolbar-actions">
        <button class="agent-console__example" type="button" data-agent-draft-save>Save draft</button>
        <button class="agent-console__example" type="button" data-agent-draft-restore ${hasDraft ? '' : 'disabled'}>Restore draft</button>
        <button class="agent-console__example" type="button" data-agent-draft-clear ${hasDraft ? '' : 'disabled'}>Clear draft</button>
        <button class="agent-console__example" type="button" data-agent-copy-prompt>Copy prompt</button>
      </div>
      <div class="agent-console__toolbar-history">
        ${hasDraft ? `<span class="agent-console__draft-chip">Draft updated ${new Date(draft.updatedAt).toLocaleString()}</span>` : '<span class="agent-console__draft-chip">No local draft saved yet</span>'}
        ${recentPrompts.map((entry, index) => `<button class="agent-console__history-chip" type="button" data-agent-recent-prompt="${index}">${escapeHtml(entry.length > 64 ? `${entry.slice(0, 61)}…` : entry)}</button>`).join('')}
      </div>
    `;

    promptToolbar.querySelector('[data-agent-draft-save]')?.addEventListener('click', () => saveDraft(true));
    promptToolbar.querySelector('[data-agent-draft-restore]')?.addEventListener('click', restoreDraft);
    promptToolbar.querySelector('[data-agent-draft-clear]')?.addEventListener('click', clearDraft);
    promptToolbar.querySelector('[data-agent-copy-prompt]')?.addEventListener('click', () => copyToClipboard(promptInput?.value || '', 'Prompt copied to clipboard.'));
    for (const button of promptToolbar.querySelectorAll('[data-agent-recent-prompt]')) {
      button.addEventListener('click', () => {
        const selectedPrompt = recentPrompts[Number(button.getAttribute('data-agent-recent-prompt'))];
        if (selectedPrompt && promptInput) {
          promptInput.value = selectedPrompt;
          promptInput.focus();
          showToast('Loaded a recent prompt into the editor.', 'success');
        }
      });
    }
  }

  function renderAnswerToolbar() {
    const hasAnswer = Boolean(lastRunContext?.answer);
    answerToolbar.innerHTML = `
      <div class="agent-console__toolbar-actions">
        <button class="agent-console__example" type="button" data-agent-copy-answer ${hasAnswer ? '' : 'disabled'}>Copy answer</button>
        <button class="agent-console__example" type="button" data-agent-export-answer ${hasAnswer ? '' : 'disabled'}>Export answer</button>
        <button class="agent-console__example" type="button" data-agent-export-trace ${hasAnswer ? '' : 'disabled'}>Export trace JSON</button>
      </div>
    `;

    answerToolbar.querySelector('[data-agent-copy-answer]')?.addEventListener('click', () => copyToClipboard(lastRunContext?.answer || '', 'Answer copied to clipboard.'));
    answerToolbar.querySelector('[data-agent-export-answer]')?.addEventListener('click', () => {
      const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
      const content = `# OpenShift SRE Agent Response\n\n## Prompt\n\n${lastRunContext?.prompt || ''}\n\n## Answer\n\n${lastRunContext?.answer || ''}\n`;
      downloadTextFile(`openshift-sre-answer-${timestamp}.md`, content);
      showToast('Answer exported as Markdown.', 'success');
    });
    answerToolbar.querySelector('[data-agent-export-trace]')?.addEventListener('click', () => {
      const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
      downloadTextFile(`openshift-sre-trace-${timestamp}.json`, JSON.stringify(lastRunContext || {}, null, 2));
      showToast('Trace exported as JSON.', 'success');
    });
    updateReportExportState();
    updateConsoleReportExportState();
  }

  function renderSessionRail() {
    const session = getSessionPayload();
    const successRate = session.runCount > 0 ? Math.round((session.successCount / session.runCount) * 100) : 0;
    sessionRail.innerHTML = `
      <div class="agent-console__session-grid">
        <article class="agent-console__session-card">
          <p class="agent-console__session-label">Runs this browser session</p>
          <p class="agent-console__session-value">${session.runCount}</p>
        </article>
        <article class="agent-console__session-card">
          <p class="agent-console__session-label">Success rate</p>
          <p class="agent-console__session-value">${successRate}%</p>
        </article>
        <article class="agent-console__session-card">
          <p class="agent-console__session-label">Last run ID</p>
          <p class="agent-console__session-value">${session.lastRunId ?? '—'}</p>
        </article>
        <article class="agent-console__session-card">
          <p class="agent-console__session-label">Last activity</p>
          <p class="agent-console__session-value">${session.lastUpdatedAt ? new Date(session.lastUpdatedAt).toLocaleTimeString() : 'Waiting…'}</p>
        </article>
      </div>
    `;
  }

  function renderTroubleshootingProgress() {
    if (!troubleshootingProgress || !troubleshootingSelect) {
      return;
    }
    const scenario = getTroubleshootingScenario();
    const totalChecks = evidenceChecklist?.querySelectorAll('input').length || 0;
    const completedChecks = evidenceChecklist?.querySelectorAll('input:checked').length || 0;
    const progress = totalChecks > 0 ? Math.round((completedChecks / totalChecks) * 100) : 0;
    troubleshootingProgress.innerHTML = `
      <section class="agent-console__table-block">
        <div class="agent-console__queue-header">
          <div>
            <h4>Scenario progress</h4>
            <p class="agent-console__meta">Measure how complete the investigation context is before running the agent.</p>
          </div>
          <span class="agent-console__history-badge ${progress >= 75 ? 'agent-console__history-badge--ok' : progress >= 40 ? 'agent-console__history-badge--warning' : 'agent-console__history-badge--neutral'}">${progress}% evidence captured</span>
        </div>
        <div class="agent-console__scenario-progress" aria-hidden="true">
          <div class="agent-console__scenario-progress-fill" style="width:${progress}%"></div>
        </div>
        <div class="agent-console__scenario-grid">
          <article class="agent-console__scenario-card">
            <h4>Scenario</h4>
            <p>${escapeHtml(scenario?.label || 'No scenario selected')}</p>
          </article>
          <article class="agent-console__scenario-card">
            <h4>Severity &amp; scope</h4>
            <p>${escapeHtml(getSelectedOptionLabel(severityInput) || 'Unspecified')} · ${escapeHtml(getSelectedOptionLabel(blastRadiusInput) || 'Unspecified')}</p>
          </article>
          <article class="agent-console__scenario-card">
            <h4>Management workflow</h4>
            <p>${escapeHtml(MANAGEMENT_TAB_LABELS[getActiveManagementTab()] || 'Incident management')}</p>
          </article>
          <article class="agent-console__scenario-card">
            <h4>Evidence checklist</h4>
            <p>${completedChecks}/${totalChecks} items checked</p>
          </article>
        </div>
      </section>
    `;
  }

  const autoSaveDraft = () => {
    window.clearTimeout(draftSaveTimer);
    draftSaveTimer = window.setTimeout(() => saveDraft(false), 350);
  };

  promptInput?.addEventListener('input', autoSaveDraft);
  issueNotesInput?.addEventListener('input', autoSaveDraft);
  [
    incidentOwnerInput,
    customerImpactInput,
    businessImpactInput,
    changeSummaryInput,
    problemNotesInput,
    changeTypeInput,
    changeRiskInput,
    changeApprovalInput,
    changeImplementationInput,
    rollbackReadinessInput,
    changeWindowInput,
    incidentPhaseInput,
    incidentTypeInput,
    communicationsStatusInput,
    stakeholderAudienceInput,
    restorationStatusInput,
    problemRecordInput,
    problemRecurrenceInput,
    rcaMethodInput,
    rootCauseDomainInput,
    knownErrorStatusInput,
    correctiveOwnerInput
  ].forEach((node) => node?.addEventListener(node.tagName === 'SELECT' ? 'change' : 'input', autoSaveDraft));

  const enhancedRunAgent = async () => {
    const promptBeforeRun = promptInput?.value || '';
    savePromptToHistory(promptBeforeRun);
    await originalRunAgent();
    const succeeded = status.classList.contains('agent-console__status--ok');
    updateSessionStats({ success: succeeded, prompt: promptBeforeRun, runId: lastRunContext?.runId || null });
    renderAnswerToolbar();
    renderPromptToolbar();
    renderTroubleshootingProgress();
    updateReportExportState();
  };

  runButton.removeEventListener('click', wrappedRunAgent);
  runButton.addEventListener('click', enhancedRunAgent);

  promptInput?.addEventListener('keydown', (event) => {
    if ((event.metaKey || event.ctrlKey) && event.key === 'Enter') {
      event.preventDefault();
      event.stopImmediatePropagation();
      enhancedRunAgent();
    }
  }, true);

  troubleshootingSelect?.addEventListener('change', renderTroubleshootingProgress);
  evidenceChecklist?.addEventListener('change', renderTroubleshootingProgress);
  [severityInput, blastRadiusInput, environmentInput, timeWindowInput].forEach((node) => node?.addEventListener('change', renderTroubleshootingProgress));
  reportExportButtons.forEach((button) => button.addEventListener('click', () => handleReportExport(button)));
  consoleReportExportButtons.forEach((button) => button.addEventListener('click', () => handleConsoleReportExport(button)));

  renderPromptToolbar();
  renderAnswerToolbar();
  renderSessionRail();
  renderTroubleshootingProgress();
  updateReportExportState();
  updateConsoleReportExportState();

})();
