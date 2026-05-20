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
		list_cluster_network_config: 'Cluster network configuration and CIDR posture',
		list_ingress_controllers: 'IngressController domains, publishing, and replica posture',
		list_cluster_proxy_config: 'Cluster proxy egress posture and trusted CA wiring',
		list_cluster_dns_config: 'DNS operator resolver, zone, and node-placement posture',
		list_feature_gate_config: 'FeatureGate set and custom no-upgrade feature posture',
		list_scheduler_config: 'Scheduler profiles and control-plane placement posture',
		list_nodes: 'Node readiness and worker footprint',
		list_node_pressure: 'Node pressure, readiness, and kubelet conditions',
		list_pods: 'Pod phase, restart, and pending risk',
		list_machine_config_pools: 'MachineConfigPool rollout posture',
		list_machine_sets: 'MachineSet capacity posture',
		list_machine_health_checks: 'MachineHealthCheck remediation and max-unhealthy posture',
		list_cluster_autoscaling: 'ClusterAutoscaler and MachineAutoscaler capacity posture',
		list_operator_subscriptions: 'Operator subscription health',
		list_cluster_service_versions: 'CSV install and operator lifecycle',
		list_monitoring_alert_posture: 'Monitoring stack, Alertmanager, and PrometheusRule posture',
		list_control_plane_certificates: 'Control-plane certificate expiry and trust-bundle review',
		list_operator_extension_readiness: 'Operator dependency and extension readiness scoring',
		list_api_service_health: 'Aggregated APIService availability and extension health',
		list_certificatesigning_requests: 'CSR approval backlog and certificate issuance posture',
		list_workload_health: 'Workload rollout and readiness posture',
		list_services: 'Service exposure posture',
		list_routes: 'Route posture and ingress pathways',
		list_ingresses: 'Ingress controller posture',
		list_events: 'Recent warning and normal event patterns',
		list_persistent_storage: 'Persistent storage and claims posture',
		list_horizontal_pod_autoscalers: 'HorizontalPodAutoscaler scaling posture',
		list_pod_disruption_budgets: 'PodDisruptionBudget maintenance safety posture',
		list_cronjobs: 'CronJob schedule and suspend posture',
		list_volume_snapshots: 'VolumeSnapshot readiness and class coverage',
		list_storage_classes: 'StorageClass defaults and options',
		list_security_context_constraints: 'SecurityContextConstraint privilege posture',
		list_admission_webhook_configurations: 'Admission webhook failure policy and CA-bundle posture',
		list_rbac_bindings: 'RBAC bindings and elevated-access posture',
		list_service_accounts: 'ServiceAccount token and pull-secret posture',
		list_limit_ranges: 'LimitRange defaults and governance guardrails',
		list_network_policies: 'NetworkPolicy isolation and coverage posture',
		list_resource_quotas: 'ResourceQuota and ClusterResourceQuota guardrails',
		list_image_streams: 'ImageStream tags and lookup policy posture',
		list_builds: 'Build and BuildConfig delivery posture',
		list_build_configs: 'BuildConfig trigger and source posture',
		list_deployment_configs: 'DeploymentConfig rollout and trigger posture',
		list_gitops_argocds: 'OpenShift GitOps / Argo CD control planes',
		list_gitops_applications: 'Argo CD application drift and health',
		list_knative_services: 'Knative / Serverless service readiness',
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
		list_virtual_machine_snapshots: 'Virtual machine snapshot readiness',
		list_migration_toolkit_resources: 'Migration Toolkit for Containers plan and execution posture',
		list_disaster_recovery_resources: 'DR policy, placement, and replication posture'
	};

	const featureDescriptions = {
		list_cluster_version: 'Tracks update posture, conditional risk, and upgradeability so preflight reviews can make a go/no-go recommendation with evidence instead of optimism.',
		list_cluster_operators: 'Surfaces degraded or progressing operators that can expand upgrade blast radius across ingress, storage, auth, and workload paths.',
		list_cluster_network_config: 'Checks cluster/service CIDRs, network type, and exposed network ranges before change windows.',
		list_ingress_controllers: 'Surfaces domain, publishing strategy, and replica drift on cluster ingress control planes.',
		list_cluster_proxy_config: 'Shows whether egress proxy settings, trusted CA wiring, and readiness endpoints are aligned before upgrades or disconnected-path changes.',
		list_cluster_dns_config: 'Highlights DNS forwarding, zone configuration, and placement details that often break upgrades in subtle and deeply annoying ways.',
		list_feature_gate_config: 'Flags non-default feature sets and custom no-upgrade features that should be explicitly reviewed before lifecycle changes.',
		list_scheduler_config: 'Summarizes scheduler profiles, default selectors, and master schedulability so capacity assumptions are not based on vibes alone.',
		list_pods: 'Highlights restart-heavy, pending, or crashlooping pods that often show where reliability and error-budget burn will surface first.',
		list_workload_health: 'Captures rollout health across core workloads so SLO posture and operator-impact reviews are grounded in workload reality.',
		list_horizontal_pod_autoscalers: 'Shows whether autoscaled workloads are pinned at min/max bounds or scaling normally.',
		list_pod_disruption_budgets: 'Highlights workloads that may block draining, upgrades, or planned maintenance.',
		list_cronjobs: 'Flags suspended or stale scheduled jobs that often get forgotten until a release weekend.',
		list_volume_snapshots: 'Summarizes protection coverage and readiness of storage snapshots and snapshot classes.',
		list_machine_health_checks: 'Shows machine remediation safety rails and whether node-health automation is actually armed for the fleet.',
		list_cluster_autoscaling: 'Adds cluster-wide and machine-set scaling guardrails so lifecycle reviews can spot brittle capacity envelopes early.',
		list_monitoring_alert_posture: 'Summarizes Prometheus, Alertmanager, and PrometheusRule coverage so monitoring blind spots and alerting readiness show up before a change window.',
		list_control_plane_certificates: 'Reviews serving certificates and trust bundles across key control-plane namespaces to flag expiry and trust-chain risk before it bites the API path.',
		list_operator_extension_readiness: 'Derives a fast readiness score from cluster operators, subscriptions, CSVs, APIService health, and webhook posture so extension drift is visible in one place.',
		list_api_service_health: 'Surfaces unavailable aggregated APIs and fragile extension registrations that can quietly break operators, consoles, and upgrade workflows.',
		list_certificatesigning_requests: 'Highlights pending or denied CSRs so node joins, kubelet rotation, and certificate approval bottlenecks stop being surprise outage lore.',
		list_events: 'Pulls warning and recovery signals that help correlate live alerts with the most likely operational runbook or owning team.',
		list_cluster_logging: 'Shows whether cluster logging and collection posture can support alert triage, evidence capture, and handoff quality during incidents.',
		list_oauth_configuration: 'Summarizes cluster identity providers, LDAP posture, and authentication entry points used for platform access.',
		list_admission_webhook_configurations: 'Shows mutating and validating webhook risk, including fail-open behavior and missing CA bundles that can destabilize admission paths.',
		list_rbac_bindings: 'Surfaces cluster-admin, admin, and other elevated bindings that influence governance posture.',
		list_service_accounts: 'Shows token-mount behavior and pull-secret usage across service identities.',
		list_limit_ranges: 'Captures namespace defaults and max/min envelopes for resource-governance reviews.',
		list_resource_quotas: 'Shows namespace and cluster quota guardrails that shape multi-tenant governance and resource fairness.',
		list_acm_multicluster_hubs: 'Adds ACM hub control-plane posture for fleet-wide governance orchestration and policy distribution.',
		list_acm_managed_clusters: 'Surfaces fleet join, availability, and clusterset posture across managed OpenShift estates.',
		list_acm_policies: 'Tracks ACM governance policy compliance, remediation mode, and disabled-policy drift.',
		list_acs_central_services: 'Shows ACS control-plane readiness for security governance and policy management.',
		list_acs_secured_clusters: 'Highlights secured-cluster rollout coverage and protection reach across the fleet.',
		list_build_configs: 'Summarizes source strategy and trigger coverage for build pipelines, not just individual runs.',
		list_deployment_configs: 'Tracks OpenShift-native rollout posture and trigger coverage for DeploymentConfigs.',
		list_knative_services: 'Adds serverless readiness signals when OpenShift Serverless is installed.',
		list_virtual_machine_snapshots: 'Surfaces VM snapshot readiness for virtualization backup and restore confidence.',
		list_migration_toolkit_resources: 'Adds MTC migration clusters, plans, and recent execution posture to migration reviews.'
	};

	const groupDescriptions = {
		'Core platform and lifecycle': 'Version, operators, platform config, networking, ingress, capacity, and machine-fleet readiness for change windows.',
		'Workloads, traffic, and storage': 'Application rollout, disruption safety, autoscaling, exposure paths, and storage protection posture.',
		'Security and governance': 'Identity, privilege, segmentation, quota guardrails, and fleet governance controls that shape operational risk.',
		'Delivery, automation, and data services': 'Build, rollout, GitOps, Tekton, logging, and serverless delivery surfaces.',
		'Virtualization, DR, and migration': 'CNV, VM protection, MTC, failover policy, and recovery/mobility execution posture.'
	};

	const featureGroups = [
		{ title: 'Core platform and lifecycle', features: ['get_cluster_identity', 'list_cluster_infrastructure', 'list_projects', 'list_cluster_version', 'list_cluster_operators', 'list_cluster_network_config', 'list_ingress_controllers', 'list_cluster_proxy_config', 'list_cluster_dns_config', 'list_feature_gate_config', 'list_scheduler_config', 'list_nodes', 'list_node_pressure', 'list_machine_config_pools', 'list_machine_sets', 'list_machine_health_checks', 'list_cluster_autoscaling', 'list_operator_subscriptions', 'list_cluster_service_versions', 'list_monitoring_alert_posture', 'list_control_plane_certificates', 'list_operator_extension_readiness', 'list_api_service_health', 'list_certificatesigning_requests'] },
		{ title: 'Workloads, traffic, and storage', features: ['list_pods', 'list_workload_health', 'list_horizontal_pod_autoscalers', 'list_pod_disruption_budgets', 'list_cronjobs', 'list_services', 'list_routes', 'list_ingresses', 'list_events', 'list_persistent_storage', 'list_volume_snapshots', 'list_storage_classes'] },
		{ title: 'Security and governance', features: ['list_security_context_constraints', 'list_admission_webhook_configurations', 'list_oauth_configuration', 'list_rbac_bindings', 'list_service_accounts', 'list_limit_ranges', 'list_network_policies', 'list_resource_quotas', 'list_acm_multicluster_hubs', 'list_acm_managed_clusters', 'list_acm_policies', 'list_acs_central_services', 'list_acs_secured_clusters'] },
		{ title: 'Delivery, automation, and data services', features: ['list_image_streams', 'list_builds', 'list_build_configs', 'list_deployment_configs', 'list_gitops_argocds', 'list_gitops_applications', 'list_knative_services', 'list_tekton_configs', 'list_tekton_pipeline_runs', 'list_cluster_logging', 'list_oadp_resources'] },
		{ title: 'Virtualization, DR, and migration', features: ['list_virtualization_resources', 'list_virtual_machine_snapshots', 'list_migration_toolkit_resources', 'list_disaster_recovery_resources'] }
	];

	const allSelectableFeatures = [...new Set(featureGroups.flatMap((group) => group.features))];
	const maxSweepTools = 12;

	const platformProfiles = {
		lifecycle: {
			title: 'Lifecycle readiness review',
			summary: 'Assess whether the platform is ready for an upgrade or change window across version, operators, nodes, and machine pools.',
			promptLead: 'Act as an OpenShift platform lifecycle lead preparing a change window. Build a lifecycle-readiness review using the selected evidence and focus on upgrade blockers, operator risk, machine-pool rollout safety, and dependencies across baremetal, ROSA, ARO, and IBM Z patterns when relevant.',
			questions: ['What would block the next controlled upgrade or maintenance window?', 'Which operator or machine-pool signals look most likely to elongate the change window?', 'What should the platform team validate before approving the next step?'],
			expectedOutputs: ['Lifecycle readiness score with go/no-go tone', 'Upgrade blockers and machine-pool dependencies', 'Affected platform patterns and next owner handoff'],
			features: ['get_cluster_identity', 'list_cluster_infrastructure', 'list_projects', 'list_cluster_version', 'list_cluster_operators', 'list_cluster_network_config', 'list_ingress_controllers', 'list_cluster_proxy_config', 'list_cluster_dns_config', 'list_feature_gate_config', 'list_scheduler_config', 'list_nodes', 'list_node_pressure', 'list_machine_config_pools', 'list_machine_sets', 'list_machine_health_checks', 'list_cluster_autoscaling', 'list_operator_subscriptions', 'list_cluster_service_versions', 'list_monitoring_alert_posture', 'list_control_plane_certificates', 'list_operator_extension_readiness', 'list_api_service_health', 'list_certificatesigning_requests']
		},
		upgrade: {
			title: 'Upgrade preflight scoring',
			summary: 'Compute a preflight-style score for the next OpenShift upgrade window using lifecycle, alerting, and disruption-safety evidence.',
			promptLead: 'Act as an OpenShift upgrade approval lead preparing a formal preflight review. Use the selected evidence to calculate an evidence-backed preflight score, identify blockers, map affected operator and workload surfaces, and recommend a go / hold / no-go posture for the next controlled upgrade window.',
			questions: ['What is the current upgrade preflight score and what weighted factors are lowering it most?', 'Which operators, machine pools, admission paths, or disruption controls expand the blast radius if the upgrade proceeds now?', 'What exact remediation steps would move the score into a safe approval band?'],
			expectedOutputs: ['Upgrade preflight score from 0-100 with go / hold / no-go guidance', 'Weighted blocker list covering operators, machine pools, alerts, and disruption controls', 'Blast-radius map showing which platform domains are most exposed'],
			features: ['get_cluster_identity', 'list_cluster_infrastructure', 'list_projects', 'list_cluster_version', 'list_cluster_operators', 'list_cluster_network_config', 'list_ingress_controllers', 'list_cluster_proxy_config', 'list_cluster_dns_config', 'list_feature_gate_config', 'list_scheduler_config', 'list_nodes', 'list_node_pressure', 'list_machine_config_pools', 'list_machine_sets', 'list_machine_health_checks', 'list_cluster_autoscaling', 'list_operator_subscriptions', 'list_cluster_service_versions', 'list_monitoring_alert_posture', 'list_control_plane_certificates', 'list_operator_extension_readiness', 'list_api_service_health', 'list_certificatesigning_requests', 'list_workload_health', 'list_horizontal_pod_autoscalers', 'list_pod_disruption_budgets', 'list_events']
		},
		observability: {
			title: 'Observability and extension advisory lane',
			summary: 'Run a fast pre-change advisory across monitoring, alert posture, certificate trust, and extension readiness without waiting on the full LLM loop.',
			promptLead: 'Act as an OpenShift observability and control-plane readiness lead. Use the selected evidence to assess monitoring stack health, alert coverage, control-plane certificate expiry, trust-bundle posture, operator dependencies, and extension API readiness before a maintenance window.',
			questions: ['Which monitoring or extension signals are the best early-warning indicators for the next maintenance window?', 'Do certificate expiry or trust-bundle issues threaten control-plane or operator continuity?', 'What should platform engineering stabilize first before approving the next change?'],
			expectedOutputs: ['Observability readiness summary', 'Early-warning indicator shortlist', 'Next stabilization actions for the platform team'],
			features: ['get_cluster_identity', 'list_cluster_operators', 'list_operator_subscriptions', 'list_cluster_service_versions', 'list_monitoring_alert_posture', 'list_control_plane_certificates', 'list_operator_extension_readiness', 'list_api_service_health', 'list_certificatesigning_requests', 'list_admission_webhook_configurations']
		},
		reliability: {
			title: 'SLO / error-budget posture',
			summary: 'Review service reliability signals, alerting gaps, and rollout pressure to estimate whether the platform is burning error budget too fast.',
			promptLead: 'Act as an OpenShift SRE reliability lead reviewing service posture before approving more change. Use the selected evidence to estimate SLO pressure, infer where error budget is being consumed, and identify the workload, traffic, and platform signals most likely to degrade customer outcomes.',
			questions: ['Which signals suggest the platform or key services are burning error budget faster than intended?', 'Where do alerts, events, rollout health, or scaling posture imply latent SLO risk even if there is no declared incident?', 'What short-term protections should SREs apply before accepting more change on the estate?'],
			expectedOutputs: ['SLO / error-budget posture with low / moderate / high burn-risk guidance', 'Top workload, alerting, and exposure signals shaping reliability risk', 'Suggested protections to preserve reliability before the next change window'],
			features: ['get_cluster_identity', 'list_projects', 'list_cluster_operators', 'list_monitoring_alert_posture', 'list_cluster_logging', 'list_nodes', 'list_node_pressure', 'list_pods', 'list_workload_health', 'list_horizontal_pod_autoscalers', 'list_pod_disruption_budgets', 'list_services', 'list_routes', 'list_ingresses', 'list_events', 'list_persistent_storage', 'list_resource_quotas']
		},
		dr: {
			title: 'Disaster recovery and failover posture',
			summary: 'Review DR policy objects, failover intent, backup posture, and fleet dependencies before an exercise or event.',
			promptLead: 'Act as an OpenShift resiliency lead preparing for a failover, relocate, or recovery exercise. Use the selected evidence to evaluate DR readiness, backup confidence, policy drift, and cross-cluster dependencies with operator-safe recommendations.',
			questions: ['Which DR policy, placement, backup, or replication gaps reduce recovery confidence?', 'Do the current signals support a controlled failover rehearsal?', 'What should platform and app teams verify before a DR event is declared ready?'],
			expectedOutputs: ['DR readiness summary', 'Recovery-confidence gaps', 'Shared platform/app handoff before rehearsal or event'],
			features: ['get_cluster_identity', 'list_disaster_recovery_resources', 'list_oadp_resources', 'list_volume_snapshots', 'list_acm_managed_clusters', 'list_acm_policies', 'list_cluster_logging', 'list_persistent_storage', 'list_storage_classes', 'list_events']
		},
		migration: {
			title: 'Migration factory readiness',
			summary: 'Inspect application, network, storage, and platform prerequisites before moving workloads or clusters.',
			promptLead: 'Act as an OpenShift migration architect reviewing workload migration readiness. Use the selected evidence to assess storage, routing, fleet governance, virtualization, and delivery dependencies for a migration wave or factory rollout.',
			questions: ['Which dependencies would put the next migration wave at risk?', 'What application, storage, or routing constraints need attention first?', 'How should the migration sequence be staged to reduce blast radius?'],
			expectedOutputs: ['Migration readiness summary', 'Highest-risk dependencies by wave', 'Blast-radius-aware staging guidance'],
			features: ['get_cluster_identity', 'list_projects', 'list_virtualization_resources', 'list_virtual_machine_snapshots', 'list_migration_toolkit_resources', 'list_pods', 'list_workload_health', 'list_pod_disruption_budgets', 'list_services', 'list_routes', 'list_ingresses', 'list_events', 'list_persistent_storage', 'list_volume_snapshots', 'list_storage_classes', 'list_acm_managed_clusters']
		},
		virtualization: {
			title: 'Virtualization / CNV posture',
			summary: 'Evaluate KubeVirt control-plane health, HyperConverged settings, VM readiness, DataVolume imports, and live migration activity.',
			promptLead: 'Act as an OpenShift Virtualization / CNV platform engineer. Use the selected evidence to review KubeVirt readiness, HyperConverged posture, VM and DataVolume health, live migrations, storage dependencies, and node capacity signals.',
			questions: ['Which CNV control-plane or VM signals need action before onboarding more workloads?', 'Are there any DataVolume or live-migration issues that threaten workload stability?', 'What are the safest next checks for the virtualization team?'],
			expectedOutputs: ['CNV readiness summary', 'Control-plane and VM risk hotspots', 'Safest next checks for the virtualization team'],
			features: ['get_cluster_identity', 'list_virtualization_resources', 'list_virtual_machine_snapshots', 'list_nodes', 'list_node_pressure', 'list_pods', 'list_machine_sets', 'list_persistent_storage', 'list_volume_snapshots', 'list_storage_classes', 'list_workload_health']
		},
		blastRadius: {
			title: 'Operator upgrade blast-radius mapping',
			summary: 'Map which platform surfaces are most likely to be affected when degraded operators, APIs, or webhooks collide with an upgrade.',
			promptLead: 'Act as an OpenShift platform risk analyst preparing an operator-focused upgrade blast-radius map. Use the selected evidence to identify which operators, APIs, auth paths, ingress surfaces, workload controllers, and storage dependencies would be affected if upgrade-related operator issues worsened or spread.',
			questions: ['Which operators or extension components have the broadest potential impact on the next upgrade window?', 'How would failures propagate across auth, ingress, workloads, storage, delivery, or fleet governance surfaces?', 'What sequencing or isolation steps would shrink the blast radius before proceeding?'],
			expectedOutputs: ['Operator-centric blast-radius map across platform domains', 'Highest-risk dependencies and propagation paths', 'Sequencing steps to reduce exposure before change approval'],
			features: ['get_cluster_identity', 'list_cluster_version', 'list_cluster_operators', 'list_operator_subscriptions', 'list_cluster_service_versions', 'list_operator_extension_readiness', 'list_api_service_health', 'list_admission_webhook_configurations', 'list_oauth_configuration', 'list_ingress_controllers', 'list_routes', 'list_persistent_storage', 'list_cluster_logging', 'list_gitops_applications', 'list_tekton_pipeline_runs', 'list_acm_managed_clusters', 'list_acm_policies', 'list_events', 'list_workload_health']
		},
		fleet: {
			title: 'Fleet and platform-pattern review',
			summary: 'Compare fleet-level dependencies, governance, and security rollout signals across managed OpenShift estate patterns.',
			promptLead: 'Act as a fleet platform operations lead reviewing the health of a multi-platform OpenShift estate. Use the selected evidence to compare ACM governance, managed-cluster readiness, platform inventory, backup posture, and security rollout patterns across baremetal, ROSA, ARO, and IBM Z footprints where relevant.',
			questions: ['Which fleet-level gaps threaten consistency across platforms?', 'Where should governance, backup, or security rollout be tightened first?', 'What handoff should go to platform owners versus security or app teams?'],
			expectedOutputs: ['Fleet consistency summary', 'Cross-platform control gaps', 'Ownership handoff by team and platform pattern'],
			features: ['get_cluster_identity', 'list_cluster_infrastructure', 'list_projects', 'list_api_service_health', 'list_certificatesigning_requests', 'list_admission_webhook_configurations', 'list_oauth_configuration', 'list_rbac_bindings', 'list_service_accounts', 'list_limit_ranges', 'list_network_policies', 'list_resource_quotas', 'list_acm_multicluster_hubs', 'list_acm_managed_clusters', 'list_acm_policies', 'list_oadp_resources', 'list_acs_central_services', 'list_acs_secured_clusters']
		},
		automation: {
			title: 'Platform automation and day-2 controls',
			summary: 'Check whether GitOps, Tekton, logging, and operator lifecycle signals support safe day-2 engineering.',
			promptLead: 'Act as an OpenShift platform automation lead reviewing day-2 operational controls. Use the selected evidence to assess GitOps, Tekton, logging, backup, and operator lifecycle health before approving further automation or change work.',
			questions: ['Which day-2 control gaps increase operational risk?', 'Are GitOps, delivery, logging, and backup signals aligned enough for the next change window?', 'What should be stabilized before more automation is rolled out?'],
			expectedOutputs: ['Day-2 control summary', 'Operational control gaps', 'Stabilization checklist before further automation'],
			features: ['get_cluster_identity', 'list_projects', 'list_gitops_argocds', 'list_gitops_applications', 'list_image_streams', 'list_builds', 'list_build_configs', 'list_deployment_configs', 'list_knative_services', 'list_tekton_configs', 'list_tekton_pipeline_runs', 'list_cluster_logging', 'list_oadp_resources', 'list_operator_subscriptions', 'list_cluster_service_versions', 'list_events']
		},
		runbook: {
			title: 'Alert-to-runbook correlation',
			summary: 'Correlate alert posture, warning events, and platform symptoms to the most relevant operational playbook and next owner handoff.',
			promptLead: 'Act as an OpenShift incident command reviewer building an alert-to-runbook handoff. Use the selected evidence to correlate alert posture, warning events, rollout symptoms, and platform dependencies with the most relevant operational runbooks, then identify who should own the next action.',
			questions: ['Which active alerting or event patterns most clearly map to an existing operational runbook?', 'Where do the current signals suggest missing, stale, or ambiguous runbook coverage?', 'What owner handoff should happen next so alerts become action instead of noise?'],
			expectedOutputs: ['Alert-to-runbook correlation summary', 'Likely runbook destinations and coverage gaps', 'Clear next-owner handoff for the hottest alerts or symptoms'],
			features: ['get_cluster_identity', 'list_cluster_operators', 'list_monitoring_alert_posture', 'list_cluster_logging', 'list_events', 'list_pods', 'list_workload_health', 'list_services', 'list_routes', 'list_ingresses', 'list_persistent_storage', 'list_disaster_recovery_resources', 'list_oadp_resources', 'list_migration_toolkit_resources']
		}
	};

	const presetOrder = ['lifecycle', 'upgrade', 'observability', 'reliability', 'dr', 'migration', 'virtualization', 'blastRadius', 'fleet', 'automation', 'runbook'];
	const defaultProfileKey = 'lifecycle';
	const defaultStatus = 'Select a platform profile, adjust the checks, and run the review.';
	const parseCsv = (value) => String(value || '').split(',').map((item) => item.trim()).filter(Boolean);
	const parseLines = (value) => String(value || '').split('\n').map((item) => item.trim()).filter(Boolean);
	const clamp = (value, min, max) => Math.max(min, Math.min(max, value));
	const slugToTitle = (value) => String(value || '').replace(/[-_]/g, ' ').replace(/\b\w/g, (char) => char.toUpperCase());
	const formatDateTime = (value) => {
		if (!value) return '—';
		const date = new Date(value);
		return Number.isNaN(date.getTime()) ? String(value) : date.toLocaleString();
	};

	const safeJsonParse = (value) => {
		if (typeof value !== 'string') return value;
		try {
			return JSON.parse(value);
		} catch {
			return value;
		}
	};

	const deriveToolName = (step = {}) => step.tool_call?.name || step.tool || step.tool_name || step.name || null;
	const deriveToolPayload = (step = {}) => safeJsonParse(step.tool_result ?? step.result ?? step.output ?? step.payload ?? step.data ?? step.observation ?? null);
	const summarizeCounts = (payload) => {
		if (!payload || typeof payload !== 'object' || Array.isArray(payload)) return [];
		return Object.entries(payload)
			.filter(([key, value]) => typeof value === 'number' && /count|total|available|failed|degraded|running|active|warning|pending|error|ready|blocked/i.test(key))
			.map(([key, value]) => ({ label: key.replace(/_/g, ' '), value: Number(value) }))
			.slice(0, 8);
	};
	const extractRows = (payload) => {
		if (!payload || typeof payload !== 'object' || Array.isArray(payload)) return [];
		return Object.entries(payload)
			.filter(([, value]) => Array.isArray(value) && value.length)
			.map(([key, value]) => ({ key, rows: value.slice(0, 4) }))
			.slice(0, 3);
	};
	const countFlaggedEntries = (card) => card.counts.filter((entry) => /failed|degraded|block|error|warn|pending/i.test(entry.label) && entry.value > 0).reduce((sum, entry) => sum + entry.value, 0);
	const countHealthyEntries = (card) => card.counts.filter((entry) => /available|running|active|ready|healthy/i.test(entry.label) && entry.value > 0).reduce((sum, entry) => sum + entry.value, 0);
	const extractToolCards = (steps = []) => steps.map((step) => {
		const tool = deriveToolName(step);
		if (!tool) return null;
		const payload = deriveToolPayload(step);
		return { tool, label: featureLabels[tool] || slugToTitle(tool), counts: summarizeCounts(payload), rowGroups: extractRows(payload), error: step.error || step.tool_error || null };
	}).filter(Boolean);

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
			...(profile.expectedOutputs || []).map((item, index) => `Required output ${index + 1}: ${item}.`),
			...profile.questions.map((question, index) => `${index + 1}. ${question}`),
			...focusNotes
		].join('\n\n');
	};

	const runbookCatalog = [
		{ title: 'Platform & Automation', location: 'playbook-platform-automation.md', tools: ['list_cluster_version', 'list_cluster_operators', 'list_machine_config_pools', 'list_machine_sets', 'list_operator_subscriptions', 'list_cluster_service_versions', 'list_monitoring_alert_posture', 'list_operator_extension_readiness', 'list_api_service_health', 'list_gitops_argocds', 'list_gitops_applications', 'list_tekton_configs', 'list_tekton_pipeline_runs', 'list_cluster_logging', 'list_oadp_resources', 'list_disaster_recovery_resources'] },
		{ title: 'Capacity & Optimization', location: 'playbook-finops.md', tools: ['list_nodes', 'list_node_pressure', 'list_projects', 'list_horizontal_pod_autoscalers', 'list_pod_disruption_budgets', 'list_resource_quotas', 'list_machine_sets', 'list_cluster_autoscaling'] },
		{ title: 'Storage & Governance', location: 'playbook-storage-governance.md', tools: ['list_persistent_storage', 'list_storage_classes', 'list_volume_snapshots', 'list_resource_quotas'] },
		{ title: 'Advanced Security & Governance', location: 'playbook-advanced-security-governance.md', tools: ['list_oauth_configuration', 'list_admission_webhook_configurations', 'list_rbac_bindings', 'list_service_accounts', 'list_limit_ranges', 'list_network_policies', 'list_acm_multicluster_hubs', 'list_acm_managed_clusters', 'list_acm_policies', 'list_acs_central_services', 'list_acs_secured_clusters'] },
		{ title: 'Audit & Security', location: 'playbook-audit-security.md', tools: ['list_security_context_constraints', 'list_routes', 'list_cluster_operators', 'list_events'] }
	];

	const deriveImpactMap = ({ selectedFeatures, toolCards }) => {
		const cardMap = new Map(toolCards.map((card) => [card.tool, card]));
		return featureGroups.map((group) => {
			const impactedCards = group.features
				.filter((featureId) => selectedFeatures.includes(featureId))
				.map((featureId) => cardMap.get(featureId))
				.filter((card) => card && (card.error || countFlaggedEntries(card) > 0));
			if (!impactedCards.length) return null;
			return { domain: group.title, count: impactedCards.length, tools: impactedCards.map((card) => card.label).slice(0, 4) };
		}).filter(Boolean);
	};

	const deriveRunbookCorrelations = (toolCards) => runbookCatalog.map((runbook) => {
		const matchedTools = toolCards.filter((card) => runbook.tools.includes(card.tool) && (card.error || countFlaggedEntries(card) > 0));
		if (!matchedTools.length) return null;
		return { title: runbook.title, location: runbook.location, count: matchedTools.length, tools: matchedTools.map((card) => card.label).slice(0, 4) };
	}).filter(Boolean);

	const deriveProfileInsight = ({ profileKey, selectedFeatures, toolCards, scoreDetails }) => {
		const impactMap = deriveImpactMap({ selectedFeatures, toolCards });
		const runbookMatches = deriveRunbookCorrelations(toolCards);
		const cardMap = new Map(toolCards.map((card) => [card.tool, card]));
		const hasIssue = (tool) => {
			const card = cardMap.get(tool);
			return Boolean(card && (card.error || countFlaggedEntries(card) > 0));
		};
		if (profileKey === 'upgrade') {
			const blockers = ['list_cluster_version', 'list_cluster_operators', 'list_machine_config_pools', 'list_machine_sets', 'list_monitoring_alert_posture', 'list_pod_disruption_budgets'].filter(hasIssue).length;
			const goNoGo = scoreDetails.overall === null ? 'Awaiting run' : (scoreDetails.overall >= 85 ? 'GO' : scoreDetails.overall >= 70 ? 'HOLD' : 'NO-GO');
			return { label: 'Upgrade preflight', value: scoreDetails.overall === null ? 'Awaiting run' : `${scoreDetails.overall}/100 · ${goNoGo}`, details: [`${blockers} core preflight blocker lane(s) detected`, `${impactMap.length} impacted platform domain(s)`] };
		}
		if (profileKey === 'reliability') {
			const burnSignals = ['list_monitoring_alert_posture', 'list_events', 'list_workload_health', 'list_routes', 'list_ingresses', 'list_horizontal_pod_autoscalers', 'list_pod_disruption_budgets'].filter(hasIssue).length;
			const posture = scoreDetails.overall === null ? 'Awaiting run' : (burnSignals >= 4 || scoreDetails.overall < 70 ? 'High burn risk' : burnSignals >= 2 || scoreDetails.overall < 85 ? 'Moderate burn risk' : 'Low burn risk');
			return { label: 'Error-budget posture', value: posture, details: [`${burnSignals} reliability signal group(s) under pressure`, `${runbookMatches.length} likely playbook destination(s)`] };
		}
		if (profileKey === 'blastRadius') {
			const topDomain = impactMap[0]?.domain || 'No impacted domain yet';
			return { label: 'Blast radius', value: impactMap.length ? `${impactMap.length} impacted domain(s)` : 'Awaiting run', details: [`Top affected domain: ${topDomain}`, `${runbookMatches.length} runbook correlation(s)`] };
		}
		if (profileKey === 'runbook') {
			return { label: 'Runbook matches', value: runbookMatches.length ? `${runbookMatches.length} correlated playbook(s)` : 'Awaiting run', details: [runbookMatches[0] ? `Top runbook: ${runbookMatches[0].title}` : 'Run a review to correlate alerts with playbooks', `${impactMap.length} impacted domain(s) in current evidence`] };
		}
		return { label: 'Blast radius', value: impactMap.length ? `${impactMap.length} impacted domain(s)` : 'Awaiting run', details: [runbookMatches[0] ? `Top runbook: ${runbookMatches[0].title}` : 'Run a review to derive playbook handoffs', `${scoreDetails.flagged || 0} flagged metric(s)`] };
	};

	const buildMarkdownPack = ({ prompt, answer, cards, toolCards, recommendations }) => {
		const lines = ['# OpenShift platform review pack', '', '## Prompt', prompt || 'Not captured.', '', '## Executive summary', answer || 'No answer captured.', '', '## Summary metrics'];
		(cards.length ? cards : [{ label: 'Status', value: 'No summary metrics extracted.' }]).forEach((card) => lines.push(`- **${card.label}:** ${card.value}`));
		lines.push('', '## Recommended next actions');
		(recommendations.length ? recommendations : ['No follow-up recommendations were derived.']).forEach((item) => lines.push(`- ${item}`));
		lines.push('', '## Evidence trace');
		if (toolCards.length) {
			toolCards.forEach((card) => {
				lines.push(`### ${card.label}`);
				if (card.error) lines.push(`- Error: ${card.error}`);
				if (card.counts.length) card.counts.forEach((entry) => lines.push(`- ${entry.label}: ${entry.value}`));
				if (!card.error && !card.counts.length) lines.push('- Tool ran without count-style metrics.');
				lines.push('');
			});
		} else {
			lines.push('- No tool trace captured.');
		}
		return lines.join('\n');
	};

	const renderStatus = (state) => state?.message ? h('div', { className: `agent-console__status${state.tone ? ` agent-console__status--${state.tone}` : ''}`, role: 'status' }, state.message) : null;
	const downloadBlob = (filename, blob) => {
		const url = URL.createObjectURL(blob);
		const link = document.createElement('a');
		link.href = url;
		link.download = filename;
		link.click();
		setTimeout(() => URL.revokeObjectURL(url), 2000);
	};
	const exportCsv = (toolCards) => {
		const rows = [['tool', 'metric', 'value']];
		toolCards.forEach((card) => {
			if (card.error) rows.push([card.tool, 'error', JSON.stringify(card.error)]);
			card.counts.forEach((entry) => rows.push([card.tool, entry.label, entry.value]));
		});
		downloadBlob('platform-review.csv', new Blob([rows.map((row) => row.join(',')).join('\n')], { type: 'text/csv;charset=utf-8' }));
	};
	const exportWord = (markdownPack) => downloadBlob('platform-review.doc', new Blob([`<!doctype html><html><body><pre>${markdownPack.replace(/[<&>]/g, (char) => ({ '<': '&lt;', '>': '&gt;', '&': '&amp;' }[char]))}</pre></body></html>`], { type: 'application/msword' }));
	const exportPdf = (markdownPack) => {
		const jsPdf = window.jspdf?.jsPDF;
		if (!jsPdf) throw new Error('PDF export is not available in this browser session.');
		const doc = new jsPdf({ unit: 'pt', format: 'a4' });
		doc.text(doc.splitTextToSize(markdownPack, 520), 40, 50);
		doc.save('platform-review.pdf');
	};
	const exportPpt = ({ answer, cards, toolCards, recommendations }) => {
		const PptxGenJS = window.PptxGenJS;
		if (!PptxGenJS) throw new Error('PowerPoint export is not available in this browser session.');
		const pptx = new PptxGenJS();
		pptx.layout = 'LAYOUT_WIDE';
		const slide = pptx.addSlide();
		slide.addText('OpenShift platform review', { x: 0.4, y: 0.3, w: 12.2, h: 0.4, fontSize: 24, bold: true, color: '0F172A' });
		slide.addText(answer || 'No answer captured.', { x: 0.4, y: 0.85, w: 5.6, h: 2.8, fontSize: 14, color: '334155', margin: 0.08, valign: 'top' });
		slide.addText((cards.length ? cards : [{ label: 'Status', value: 'No summary metrics' }]).map((card) => `${card.label}: ${card.value}`).join('\n'), { x: 6.2, y: 0.85, w: 2.4, h: 2.2, fontSize: 12.5, color: '1D4ED8', bold: true, margin: 0.08, valign: 'top' });
		slide.addText((recommendations.length ? recommendations : ['No recommendations derived.']).map((item) => `• ${item}`).join('\n'), { x: 8.8, y: 0.85, w: 4.0, h: 2.4, fontSize: 10.5, color: '475569', margin: 0.08, valign: 'top' });
		slide.addText((toolCards.length ? toolCards : [{ label: 'No tool trace captured.', counts: [] }]).map((card) => `${card.label}\n${card.counts.map((entry) => `• ${entry.label}: ${entry.value}`).join('\n') || '• No count metrics'}`).join('\n\n'), { x: 0.4, y: 3.9, w: 12.2, h: 3.0, fontSize: 10.5, color: '475569', margin: 0.08, valign: 'top' });
		pptx.writeFile({ fileName: 'platform-review.pptx' });
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
		if (!response.ok) throw new Error(payload.detail || `Request failed with status ${response.status}`);
		return payload;
	}

	const computeScoreDetails = ({ selectedFeatures, toolCards }) => {
		const cardMap = new Map(toolCards.map((card) => [card.tool, card]));
		const categoryScores = featureGroups.map((group) => {
			const scoped = group.features.filter((featureId) => selectedFeatures.includes(featureId));
			if (!scoped.length) return null;
			const cards = scoped.map((featureId) => cardMap.get(featureId)).filter(Boolean);
			const errors = cards.filter((card) => card.error).length;
			const flagged = cards.reduce((sum, card) => sum + countFlaggedEntries(card), 0);
			const healthy = cards.reduce((sum, card) => sum + countHealthyEntries(card), 0);
			const score = clamp(100 - (errors * 28) - (Math.min(flagged, 8) * 5) + Math.min(healthy, 10), 0, 100);
			return { title: group.title, score, errors, flagged, healthy, selectedCount: scoped.length, tone: score >= 85 ? 'ok' : score >= 65 ? 'warn' : 'error' };
		}).filter(Boolean);
		if (!toolCards.length) return { overall: null, errors: 0, flagged: 0, healthy: 0, tone: 'info', categoryScores };
		const overallBase = categoryScores.length ? Math.round(categoryScores.reduce((sum, item) => sum + item.score, 0) / categoryScores.length) : 100;
		const errors = toolCards.filter((card) => card.error).length;
		const flagged = toolCards.reduce((sum, card) => sum + countFlaggedEntries(card), 0);
		const healthy = toolCards.reduce((sum, card) => sum + countHealthyEntries(card), 0);
		const overall = clamp(overallBase - (errors * 4), 0, 100);
		return { overall, errors, flagged, healthy, tone: overall >= 85 ? 'ok' : overall >= 65 ? 'warn' : 'error', categoryScores };
	};

	const buildRecommendations = ({ profileKey, selectedFeatures, toolCards, scoreDetails }) => {
		if (!toolCards.length) {
			return [
				'Run the first platform review so the console can calculate readiness, find hotspots, and suggest targeted follow-up work.',
				'Save the review as a reusable template once the signal mix matches your operating pattern.',
				'Use a watchlist when you want the same platform review rerun before every planned change window.'
			];
		}
		const cardMap = new Map(toolCards.map((card) => [card.tool, card]));
		const hasIssue = (tool) => {
			const card = cardMap.get(tool);
			return Boolean(card && (card.error || countFlaggedEntries(card) > 0));
		};
		const items = [];
		if (scoreDetails.errors > 0) items.push('Re-run the checks that returned tool errors with the cluster override and kube context fields verified first so the evidence set is complete before the handoff leaves the room.');
		if (profileKey === 'lifecycle' && (hasIssue('list_cluster_version') || hasIssue('list_cluster_operators') || hasIssue('list_machine_config_pools'))) items.push('Before the next upgrade window, validate cluster version posture, degraded operators, and MachineConfigPool rollout health together so upgrade blockers are not reviewed in isolation.');
		if (profileKey === 'upgrade' && (hasIssue('list_cluster_version') || hasIssue('list_cluster_operators') || hasIssue('list_machine_config_pools') || hasIssue('list_monitoring_alert_posture') || hasIssue('list_pod_disruption_budgets'))) items.push('Treat this as an upgrade preflight gate: hold the window until version, operator, alert posture, and disruption-control signals can defend a clean go/no-go review.');
		if (profileKey === 'reliability' && (hasIssue('list_monitoring_alert_posture') || hasIssue('list_events') || hasIssue('list_workload_health') || hasIssue('list_routes'))) items.push('Protect the error budget first: tighten noisy alert ownership, confirm rollout health, and reduce exposure-path instability before accepting more platform change.');
		if (profileKey === 'dr' && (hasIssue('list_disaster_recovery_resources') || hasIssue('list_oadp_resources'))) items.push('Treat DR policy and OADP backup posture as a paired gate: confirm restore confidence and policy placement before approving a failover rehearsal.');
		if ((profileKey === 'migration' || profileKey === 'virtualization') && (hasIssue('list_virtualization_resources') || hasIssue('list_persistent_storage') || hasIssue('list_storage_classes'))) items.push('Stabilize virtualization and storage dependencies before the next migration or CNV onboarding wave so DataVolume and storage-class assumptions do not break late in the sequence.');
		if (profileKey === 'blastRadius' && (hasIssue('list_cluster_operators') || hasIssue('list_operator_extension_readiness') || hasIssue('list_api_service_health') || hasIssue('list_admission_webhook_configurations'))) items.push('Map operator issues to affected auth, ingress, workload, and storage surfaces before sequencing the upgrade so the team knows exactly where the blast radius could spread.');
		if (profileKey === 'runbook' && (hasIssue('list_monitoring_alert_posture') || hasIssue('list_events') || hasIssue('list_cluster_logging'))) items.push('Turn the hot alerts into owner-ready action: correlate alert posture, events, and logging coverage with the closest playbook, then document where runbook coverage is stale or missing.');
		if (selectedFeatures.includes('list_gitops_applications') && hasIssue('list_gitops_applications')) items.push('Review GitOps application drift alongside Tekton or build failures to separate control-plane drift from delivery-pipeline regressions.');
		if (selectedFeatures.includes('list_network_policies') && hasIssue('list_network_policies')) items.push('Where network policy coverage is noisy, pair the route/service checks with namespace isolation posture so exposure risk and workload reachability are evaluated together.');
		if (scoreDetails.overall !== null && scoreDetails.overall < 70) items.push('Use the compare lane against the previous successful run before approving the next change window, so the team can prove whether the platform is improving or regressing.');
		if (!items.length) {
			items.push('The current signal mix looks steady; save it as a reusable template and schedule it as a watchlist so the same posture can be checked before each planned change window.');
			items.push('Use the multi-cluster sweep lane to compare the same checks across the estate and catch drift before it becomes a late-stage platform surprise.');
			items.push('Export the current handoff pack so CAB, platform engineering, and service owners all see the same evidence path.');
		}
		return items.slice(0, 4);
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
		const [streamMode, setStreamMode] = useState(true);
		const [toolFilter, setToolFilter] = useState('all');
		const [featureSearch, setFeatureSearch] = useState('');
		const [showSelectedOnly, setShowSelectedOnly] = useState(false);
		const [status, setStatus] = useState(defaultStatus);
		const [statusTone, setStatusTone] = useState('');
		const [busy, setBusy] = useState(false);
		const [lastRun, setLastRun] = useState({ prompt: '', answer: '', steps: [], runId: null });

		const [templateName, setTemplateName] = useState('');
		const [templateDescription, setTemplateDescription] = useState('');
		const [templateCategory, setTemplateCategory] = useState('platform');
		const [templateStatus, setTemplateStatus] = useState({ message: '', tone: '' });
		const [savedTemplates, setSavedTemplates] = useState([]);

		const [watchlistName, setWatchlistName] = useState('');
		const [watchlistRegions, setWatchlistRegions] = useState('');
		const [watchlistNotes, setWatchlistNotes] = useState('');
		const [selectedTemplateId, setSelectedTemplateId] = useState('');
		const [watchlistStatus, setWatchlistStatus] = useState({ message: '', tone: '' });
		const [watchlists, setWatchlists] = useState([]);
		const [watchlistResults, setWatchlistResults] = useState([]);

		const [overviewStatus, setOverviewStatus] = useState({ message: '', tone: '' });
		const [overview, setOverview] = useState({ summary: {}, recent_runs: [], latest_metrics: [] });
		const [compareLeft, setCompareLeft] = useState('');
		const [compareRight, setCompareRight] = useState('');
		const [comparePayload, setComparePayload] = useState(null);

		const [sweepRegions, setSweepRegions] = useState('');
		const [sweepRoles, setSweepRoles] = useState('');
		const [sweepStatus, setSweepStatus] = useState({ message: '', tone: '' });
		const [sweepPayload, setSweepPayload] = useState({ results: [], count: 0 });

		const profile = platformProfiles[profileKey] || platformProfiles[defaultProfileKey];
		const suggestedModels = useMemo(() => (llmRuntime.getSuggestedModels ? llmRuntime.getSuggestedModels(providerCatalog, providerId) : []), [providerCatalog, providerId]);

		const prompt = useMemo(() => buildReviewPrompt({ profile, selectedFeatures, project, clusterScope, concern, recentChange, successCriteria, audience, customPrompt }), [profile, selectedFeatures, project, clusterScope, concern, recentChange, successCriteria, audience, customPrompt]);
		const toolCards = useMemo(() => extractToolCards(lastRun.steps), [lastRun.steps]);
		const filteredToolCards = useMemo(() => toolCards.filter((card) => toolFilter === 'all' || (toolFilter === 'attention' ? card.error || countFlaggedEntries(card) > 0 : !card.error && countFlaggedEntries(card) === 0)), [toolCards, toolFilter]);
		const scoreDetails = useMemo(() => computeScoreDetails({ selectedFeatures, toolCards }), [selectedFeatures, toolCards]);
		const profileInsight = useMemo(() => deriveProfileInsight({ profileKey, selectedFeatures, toolCards, scoreDetails }), [profileKey, selectedFeatures, toolCards, scoreDetails]);
		const runbookCorrelations = useMemo(() => deriveRunbookCorrelations(toolCards), [toolCards]);
		const impactMap = useMemo(() => deriveImpactMap({ selectedFeatures, toolCards }), [selectedFeatures, toolCards]);
		const recommendations = useMemo(() => buildRecommendations({ profileKey, selectedFeatures, toolCards, scoreDetails }), [profileKey, selectedFeatures, toolCards, scoreDetails]);
		const normalizedFeatureSearch = featureSearch.trim().toLowerCase();
		const visibleFeatureGroups = useMemo(() => featureGroups.map((group) => ({
			...group,
			visibleFeatures: group.features.filter((featureId) => {
				const label = (featureLabels[featureId] || slugToTitle(featureId)).toLowerCase();
				const description = (featureDescriptions[featureId] || '').toLowerCase();
				const matchesSearch = !normalizedFeatureSearch || label.includes(normalizedFeatureSearch) || description.includes(normalizedFeatureSearch) || featureId.toLowerCase().includes(normalizedFeatureSearch);
				const matchesSelection = !showSelectedOnly || selectedFeatures.includes(featureId);
				return matchesSearch && matchesSelection;
			})
		})).filter((group) => group.visibleFeatures.length), [normalizedFeatureSearch, showSelectedOnly, selectedFeatures]);
		const visibleFeatureCount = useMemo(() => visibleFeatureGroups.reduce((sum, group) => sum + group.visibleFeatures.length, 0), [visibleFeatureGroups]);
		const summaryCards = useMemo(() => [
			{ label: 'Profile', value: profile.title },
			{ label: 'Checks selected', value: String(selectedFeatures.length) },
			{ label: profileInsight.label, value: profileInsight.value },
			{ label: 'Flagged metrics', value: String(scoreDetails.flagged || 0) },
			{ label: 'Healthy signals', value: String(scoreDetails.healthy || 0) },
			{ label: 'Tool errors', value: String(scoreDetails.errors || 0) }
		], [profile.title, selectedFeatures.length, scoreDetails, profileInsight]);
		const markdownPack = useMemo(() => buildMarkdownPack({ prompt: lastRun.prompt || prompt, answer: lastRun.answer, cards: summaryCards, toolCards, recommendations }), [lastRun.prompt, prompt, lastRun.answer, summaryCards, toolCards, recommendations]);
		const selectedSweepTools = selectedFeatures.slice(0, maxSweepTools);

		const buildRuntime = () => ({
			...(llmRuntime.buildLlmRuntime?.({ provider: providerId, ollamaBaseUrl, modelName, externalModelName, externalBaseUrl, externalApiKey, externalApiVersion, externalOrganization }, providerCatalog) || {}),
			cluster_scope: clusterScope.trim() || null,
			kube_context_name: kubeContextName.trim() || null,
			openshift_api_url: openshiftApiUrl.trim() || null,
			openshift_token: openshiftToken || null,
			openshift_namespace: project.trim() || null,
			verify_ssl: verifySsl,
		});

		const loadTemplates = async () => {
			const payload = await fetchJson('/investigations');
			const items = payload.items || [];
			setSavedTemplates(items);
			setSelectedTemplateId((current) => current && items.some((item) => String(item.id) === String(current)) ? current : (items[0] ? String(items[0].id) : ''));
			return items;
		};
		const loadWatchlists = async () => {
			const payload = await fetchJson('/watchlists');
			setWatchlists(payload.items || []);
			return payload.items || [];
		};
		const loadOverview = async () => {
			setOverviewStatus({ message: 'Loading recent run history…', tone: '' });
			const payload = await fetchJson('/history/overview?run_limit=12&point_limit=6&series_limit=6');
			setOverview(payload);
			const runs = payload.recent_runs || [];
			setCompareLeft((current) => current || (runs[1] ? String(runs[1].run_id) : ''));
			setCompareRight((current) => current || (runs[0] ? String(runs[0].run_id) : ''));
			setOverviewStatus({ message: `Loaded ${runs.length} recent run(s) for scoring and compare analysis.`, tone: 'ok' });
			return payload;
		};

		useEffect(() => {
			let cancelled = false;
			(async () => {
				const catalog = llmRuntime.fetchProviderCatalog ? await llmRuntime.fetchProviderCatalog() : { providers: [] };
				if (cancelled) return;
				const resolvedProviderId = llmRuntime.normalizeProviderId ? llmRuntime.normalizeProviderId(catalog, catalog.configured_provider || 'ollama') : (catalog.configured_provider || 'ollama');
				setProviderCatalog(catalog);
				setProviderId(resolvedProviderId);
				setOllamaBaseUrl(catalog.configured_base_url || '');
				setModelName(catalog.configured_model_name || '');
			})();
			return () => { cancelled = true; };
		}, []);

		useEffect(() => {
			Promise.all([loadTemplates(), loadWatchlists(), loadOverview()]).catch((error) => {
				const message = error instanceof Error ? error.message : 'Unable to load the platform library.';
				setTemplateStatus({ message, tone: 'error' });
				setWatchlistStatus({ message, tone: 'error' });
				setOverviewStatus({ message, tone: 'error' });
			});
		}, []);

		useEffect(() => {
			if (!templateName) setTemplateName(`${profile.title} template`);
			if (!watchlistName) setWatchlistName(`${profile.title} watchlist`);
		}, [profile.title, templateName, watchlistName]);

		const onProfileChange = (event) => {
			const nextProfileKey = event.target.value;
			const nextProfile = platformProfiles[nextProfileKey] || platformProfiles[defaultProfileKey];
			setProfileKey(nextProfileKey);
			setSelectedFeatures(nextProfile.features);
			setTemplateName(`${nextProfile.title} template`);
			setWatchlistName(`${nextProfile.title} watchlist`);
			setStatus(`Loaded ${nextProfile.title}. Adjust the checks and run when ready.`);
			setStatusTone('ok');
		};
		const toggleFeature = (featureId) => setSelectedFeatures((current) => current.includes(featureId) ? current.filter((item) => item !== featureId) : [...current, featureId]);
		const resetProfileFeatures = () => { setSelectedFeatures(profile.features); setStatus(`Reset checks to the ${profile.title} defaults.`); setStatusTone('ok'); };
		const selectAllFeatures = () => { setSelectedFeatures(allSelectableFeatures); setStatus('Selected the full OpenShift platform check catalog for this review.'); setStatusTone('ok'); };
		const clearAllFeatures = () => { setSelectedFeatures([]); setStatus('Cleared the selected platform checks. Choose the exact OpenShift signals you want to inspect.'); setStatusTone('ok'); };

		const saveTemplate = async () => {
			const payload = {
				name: templateName.trim(),
				description: templateDescription.trim() || `Saved from Platform Console (${profile.title}).`,
				category: templateCategory.trim() || 'platform',
				prompt,
				default_regions: clusterScope.trim() ? [clusterScope.trim()] : [],
				default_tags: ['platform-console', profileKey],
				default_tools: selectedFeatures,
			};
			if (!payload.name) {
				setTemplateStatus({ message: 'Name the template before saving it.', tone: 'error' });
				return null;
			}
			setTemplateStatus({ message: 'Saving the current review as a reusable template…', tone: '' });
			try {
				const created = await fetchJson('/investigations', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
				await loadTemplates();
				setSelectedTemplateId(String(created.id));
				setTemplateStatus({ message: `Saved template “${created.name}”.`, tone: 'ok' });
				return created;
			} catch (error) {
				setTemplateStatus({ message: error instanceof Error ? error.message : 'Unable to save the template.', tone: 'error' });
				return null;
			}
		};

		const loadTemplateIntoReview = (item) => {
			if (Array.isArray(item.default_tools) && item.default_tools.length) setSelectedFeatures(item.default_tools.filter((tool) => featureLabels[tool]));
			if (Array.isArray(item.default_regions) && item.default_regions[0]) setClusterScope(item.default_regions[0]);
			setTemplateName(item.name || `${profile.title} template`);
			setTemplateDescription(item.description || '');
			setTemplateCategory(item.category || 'platform');
			setSelectedTemplateId(String(item.id));
			setCustomPrompt(`Loaded saved template “${item.name}”. Keep or replace this note before running the review.`);
			setStatus(`Loaded saved template “${item.name}”. Review the selected checks and run when ready.`);
			setStatusTone('ok');
		};

		const createWatchlist = async (fromCurrent = false) => {
			setWatchlistStatus({ message: 'Preparing the platform watchlist…', tone: '' });
			try {
				let templateId = selectedTemplateId;
				if (fromCurrent || !templateId) {
					const created = await saveTemplate();
					if (!created?.id) throw new Error('Save a reusable template first so the watchlist has a stable prompt definition.');
					templateId = String(created.id);
				}
				if (!watchlistName.trim()) throw new Error('Name the watchlist before saving it.');
				const payload = await fetchJson('/watchlists', {
					method: 'POST',
					headers: { 'Content-Type': 'application/json' },
					body: JSON.stringify({ name: watchlistName.trim(), investigation_id: Number(templateId), regions: parseCsv(watchlistRegions), notes: watchlistNotes.trim() })
				});
				await loadWatchlists();
				setWatchlistStatus({ message: `Saved watchlist “${payload.name}”.`, tone: 'ok' });
			} catch (error) {
				setWatchlistStatus({ message: error instanceof Error ? error.message : 'Unable to create the watchlist.', tone: 'error' });
			}
		};

		const runWatchlistNow = async (watchlistId) => {
			setWatchlistStatus({ message: 'Running the selected watchlist…', tone: '' });
			try {
				const payload = await fetchJson(`/watchlists/${watchlistId}/run`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ runtime: buildRuntime() }) });
				setWatchlistResults(payload.results || []);
				await loadWatchlists();
				await loadOverview();
				setWatchlistStatus({ message: `Completed ${payload.count || 0} watchlist target run(s).`, tone: 'ok' });
			} catch (error) {
				setWatchlistStatus({ message: error instanceof Error ? error.message : 'Unable to run the watchlist.', tone: 'error' });
			}
		};

		const compareRuns = async () => {
			if (!compareLeft || !compareRight) {
				setOverviewStatus({ message: 'Choose two runs before comparing them.', tone: 'error' });
				return;
			}
			setOverviewStatus({ message: 'Comparing the selected historical runs…', tone: '' });
			try {
				const payload = await fetchJson(`/history/compare?left_run_id=${encodeURIComponent(compareLeft)}&right_run_id=${encodeURIComponent(compareRight)}`);
				setComparePayload(payload);
				setOverviewStatus({ message: 'Run comparison ready.', tone: 'ok' });
			} catch (error) {
				setOverviewStatus({ message: error instanceof Error ? error.message : 'Unable to compare runs.', tone: 'error' });
			}
		};

		const runPlatformReview = async () => {
			if (!selectedFeatures.length) {
				setStatus('Select at least one platform check before running the review.');
				setStatusTone('error');
				return;
			}
			setBusy(true);
			setLastRun({ prompt, answer: '', steps: [], runId: null });
			setStatus(streamMode ? 'Streaming platform review via /chat/stream …' : 'Running platform review via /chat …');
			setStatusTone('');
			const runtime = buildRuntime();
			const tags = ['platform-console', profileKey];
			try {
				if (streamMode) {
					const response = await fetch('/chat/stream', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ prompt, runtime, tags }) });
					if (!response.ok || !response.body) throw new Error(`Streaming request failed with status ${response.status}`);
					const reader = response.body.getReader();
					const decoder = new TextDecoder();
					let buffer = '';
					const liveSteps = [];
					const handleEvent = (rawEvent) => {
						const line = rawEvent.split('\n').find((entry) => entry.startsWith('data: '));
						if (!line) return;
						const payload = JSON.parse(line.slice(6));
						if (payload.type === 'step' && payload.step) {
							liveSteps.push(payload.step);
							setLastRun({ prompt, answer: '', steps: [...liveSteps], runId: null });
							setStatus(`Captured streaming evidence step ${payload.index + 1}.`);
						} else if (payload.type === 'done') {
							setLastRun({ prompt, answer: payload.answer || '', steps: [...liveSteps], runId: payload.run_id || null });
							setStatus(payload.run_id ? `Platform review completed and stored as run #${payload.run_id}.` : 'Platform review completed.');
							setStatusTone('ok');
						} else if (payload.type === 'error') {
							throw new Error(payload.detail || 'Unexpected streaming error while running the platform review.');
						}
					};
					while (true) {
						const { done, value } = await reader.read();
						buffer += decoder.decode(value || new Uint8Array(), { stream: !done });
						let boundaryIndex = buffer.indexOf('\n\n');
						while (boundaryIndex !== -1) {
							const eventBlock = buffer.slice(0, boundaryIndex).trim();
							buffer = buffer.slice(boundaryIndex + 2);
							if (eventBlock) handleEvent(eventBlock);
							boundaryIndex = buffer.indexOf('\n\n');
						}
						if (done) break;
					}
				} else {
					const payload = await fetchJson('/chat', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ prompt, runtime, tags }) });
					setLastRun({ prompt, answer: payload.answer || '', steps: Array.isArray(payload.steps) ? payload.steps : [], runId: payload.run_id || null });
					setStatus(payload.run_id ? `Platform review completed and stored as run #${payload.run_id}.` : 'Platform review completed.');
					setStatusTone('ok');
				}
				await loadOverview();
			} catch (error) {
				setLastRun({ prompt, answer: '', steps: [], runId: null });
				setStatus(error instanceof Error ? error.message : 'Unexpected error while running the platform review.');
				setStatusTone('error');
			} finally {
				setBusy(false);
			}
		};

		const runFastAdvisory = async () => {
			if (!selectedFeatures.length) {
				setStatus('Select at least one platform check before running the advisory pack.');
				setStatusTone('error');
				return;
			}
			setBusy(true);
			setLastRun({ prompt, answer: '', steps: [], runId: null });
			setStatus('Running the fast non-LLM platform advisory pack …');
			setStatusTone('');
			try {
				const payload = await fetchJson('/platform/advisory', {
					method: 'POST',
					headers: { 'Content-Type': 'application/json' },
					body: JSON.stringify({
						lane_key: profileKey,
						lane_label: profile.title,
						focus_label: 'Fast non-LLM advisory pack',
						selected_features: selectedFeatures,
						operator_notes: [concern, recentChange, successCriteria, customPrompt].filter(Boolean).join(' · '),
						runtime: buildRuntime(),
						tags: ['platform-console', profileKey, 'fast-advisory']
					})
				});
				setLastRun({ prompt, answer: payload.answer || '', steps: Array.isArray(payload.steps) ? payload.steps : [], runId: payload.run_id || null });
				setStatus(payload.run_id ? `Fast advisory completed and stored as run #${payload.run_id}.` : 'Fast advisory completed.');
				setStatusTone('ok');
				await loadOverview();
			} catch (error) {
				setLastRun({ prompt, answer: '', steps: [], runId: null });
				setStatus(error instanceof Error ? error.message : 'Unexpected error while running the fast advisory pack.');
				setStatusTone('error');
			} finally {
				setBusy(false);
			}
		};

		const runSweep = async () => {
			if (!selectedSweepTools.length) {
				setSweepStatus({ message: 'Pick at least one selected platform check before running the sweep.', tone: 'error' });
				return;
			}
			setSweepStatus({ message: 'Running the multi-cluster platform sweep…', tone: '' });
			try {
				const payload = await fetchJson('/platform/sweep', {
					method: 'POST',
					headers: { 'Content-Type': 'application/json' },
					body: JSON.stringify({ tool_names: selectedSweepTools, regions: parseCsv(sweepRegions), role_arns: parseLines(sweepRoles), runtime: buildRuntime() })
				});
				setSweepPayload(payload);
				setSweepStatus({ message: selectedFeatures.length > maxSweepTools ? `Completed ${payload.count || 0} sweep target(s). The sweep used the first ${maxSweepTools} selected checks because the backend caps each request at 12 tools.` : `Completed ${payload.count || 0} sweep target(s).`, tone: 'ok' });
			} catch (error) {
				setSweepPayload({ results: [], count: 0 });
				setSweepStatus({ message: error instanceof Error ? error.message : 'Unable to run the platform sweep.', tone: 'error' });
			}
		};

		const exportHandler = async (kind) => {
			try {
				if (kind === 'csv') exportCsv(toolCards);
				else if (kind === 'word') exportWord(markdownPack);
				else if (kind === 'pdf') exportPdf(markdownPack);
				else if (kind === 'ppt') exportPpt({ answer: lastRun.answer, cards: summaryCards, toolCards, recommendations });
				setStatus(`Exported ${kind.toUpperCase()} platform review pack.`);
				setStatusTone('ok');
			} catch (error) {
				setStatus(error instanceof Error ? error.message : `Unable to export ${kind}.`);
				setStatusTone('error');
			}
		};

		const renderTemplateCard = (item) => h('article', { className: 'platform-console__library-card', key: item.id }, [
			h('div', { className: 'agent-console__queue-header' }, [
				h('div', null, [h('h3', null, item.name), h('p', { className: 'platform-console__meta' }, item.description || 'No description provided yet.')]),
				h('span', { className: 'platform-console__pill' }, item.category || 'platform')
			]),
			h('p', { className: 'platform-console__meta' }, `Default tools: ${(item.default_tools || []).map((tool) => featureLabels[tool] || tool).join('; ') || 'prompt only'}`),
			h('div', { className: 'agent-console__actions' }, [
				h('button', { className: 'agent-console__example', type: 'button', onClick: () => loadTemplateIntoReview(item) }, 'Load into review'),
				h('button', { className: 'agent-console__example', type: 'button', onClick: () => setSelectedTemplateId(String(item.id)) }, 'Use for watchlist')
			])
		]);

		const renderWatchlistCard = (item) => h('article', { className: 'platform-console__library-card', key: item.id }, [
			h('div', { className: 'agent-console__queue-header' }, [
				h('div', null, [h('h3', null, item.name), h('p', { className: 'platform-console__meta' }, item.investigation?.name || 'No saved template linked.')]),
				h('span', { className: `platform-console__badge ${item.enabled ? 'platform-console__badge--ok' : 'platform-console__badge--warn'}` }, item.enabled ? 'Enabled' : 'Disabled')
			]),
			h('ul', null, [
				h('li', { key: 'scopes' }, `Cluster scopes: ${(item.regions || []).join(', ') || 'inherit from runtime'}`),
				h('li', { key: 'last' }, `Last run: ${item.last_run_at ? formatDateTime(item.last_run_at) : 'never'}`),
				h('li', { key: 'notes' }, `Notes: ${item.notes || 'none'}`)
			]),
			h('div', { className: 'agent-console__actions' }, [
				h('button', { className: 'agent-console__button', type: 'button', onClick: () => runWatchlistNow(item.id) }, 'Run now')
			])
		]);

		const renderSweepCard = (target, index) => {
			const toolResults = target.tool_results || {};
			const identity = toolResults.get_cluster_identity || target.caller_identity || {};
			const clusterName = identity.cluster_name || identity.infrastructure_name || identity.name || target.region || `cluster-${index + 1}`;
			return h('article', { className: 'platform-console__tool-card', key: `${clusterName}-${index}` }, [
				h('div', { className: 'agent-console__queue-header' }, [
					h('div', null, [h('h3', null, clusterName), h('p', { className: 'platform-console__meta' }, `${target.region || 'current scope'} · ${target.role_arn || 'current execution context'}`)]),
					h('span', { className: 'platform-console__pill' }, `${selectedSweepTools.length} checks`)
				]),
				h('ul', null, selectedSweepTools.map((toolName) => {
					const payload = toolResults[toolName] || {};
					const counts = summarizeCounts(payload);
					return h('li', { key: `${clusterName}-${toolName}` }, [
						h('strong', null, `${featureLabels[toolName] || toolName}: `),
						payload.error ? `error — ${payload.error}` : (counts.length ? counts.map((entry) => `${entry.label}: ${entry.value}`).join('; ') : 'evidence captured')
					]);
				})),
				h('details', null, [h('summary', null, 'Raw sweep evidence'), h('pre', null, JSON.stringify(toolResults, null, 2))])
			]);
		};

		return h('div', { className: 'platform-console' }, [
			h('section', { className: 'platform-console__hero agent-console__panel', id: 'platform-launcher', key: 'hero' }, [
				h('div', { className: 'platform-console__hero-grid' }, [
					h('div', null, [
						h('span', { className: 'platform-console__eyebrow' }, 'Platform operations runway'),
						h('h2', null, 'Run lifecycle, upgrade, reliability, runbook, DR, migration, CNV, comparison, and estate sweeps from one dedicated console.'),
						h('p', null, 'This page now covers planned OpenShift readiness work end-to-end: upgrade preflight scoring, SLO / error-budget posture, operator blast-radius mapping, alert-to-runbook correlation, reusable templates, historical comparison, streaming evidence, and multi-cluster sweeps.'),
						h('ul', null, [h('li', { key: 'a' }, 'Profiles give you a strong starting point instead of another blank textarea.'), h('li', { key: 'b' }, 'Upgrade, reliability, blast-radius, and runbook lanes make planned SRE work much easier to structure.'), h('li', { key: 'c' }, 'Saved templates, streaming mode, and estate sweeps keep the evidence path visible while you work.')])
					]),
					h('div', { className: 'platform-console__hero-note' }, [
						h('span', { className: 'platform-console__badge platform-console__badge--ok' }, 'Expanded platform cockpit'),
						h('h3', null, profile.title),
						h('p', null, profile.summary),
						h('p', { className: 'platform-console__meta' }, scoreDetails.overall === null ? 'Run the first review to compute profile scoring, blast-radius hints, and recommendations.' : `${profileInsight.label}: ${profileInsight.value} · Current tone: ${scoreDetails.tone.toUpperCase()}.`),
						profileInsight.details?.length ? h('ul', null, profileInsight.details.map((item) => h('li', { key: item }, item))) : null
					])
				]),
				h('div', { className: 'platform-console__metrics' }, summaryCards.map((card) => h('article', { className: 'platform-console__metric', key: card.label }, [h('span', { className: 'platform-console__meta' }, card.label), h('strong', null, card.value)]))),
				h('div', { className: 'platform-console__link-bar' }, [h('a', { href: 'history.html', className: 'platform-console__pill' }, 'Open full history'), h('a', { href: 'watchlists.html', className: 'platform-console__pill' }, 'Open watchlists'), h('a', { href: 'drift-diff.html', className: 'platform-console__pill' }, 'Open drift diff'), h('a', { href: 'posture-radar.html', className: 'platform-console__pill' }, 'Open posture radar')]),
				h('div', { className: `agent-console__status${statusTone ? ` agent-console__status--${statusTone}` : ''}`, role: 'status' }, status)
			]),

			h('section', { className: 'agent-console__panel', key: 'launcher-form' }, [
				h('div', { className: 'platform-console__toolbar' }, [
					h('label', { className: 'agent-console__label' }, ['Platform review profile', h('select', { className: 'agent-console__input', value: profileKey, onChange: onProfileChange }, presetOrder.map((profileId) => h('option', { key: profileId, value: profileId }, platformProfiles[profileId].title)))]),
					h('label', { className: 'agent-console__label' }, ['Namespace / project focus', h('input', { className: 'agent-console__input', value: project, onChange: (event) => setProject(event.target.value), placeholder: 'openshift-dr-system or app namespace' })]),
					h('label', { className: 'agent-console__label' }, ['Cluster or estate scope', h('input', { className: 'agent-console__input', value: clusterScope, onChange: (event) => setClusterScope(event.target.value), placeholder: 'prod-west fleet / aro landing zone / baremetal DR pair' })]),
					h('label', { className: 'agent-console__label' }, [h('span', null, 'Streaming execution'), h('input', { type: 'checkbox', checked: streamMode, onChange: (event) => setStreamMode(event.target.checked) })]),
					h('div', { className: 'agent-console__actions' }, [h('button', { className: 'agent-console__example', type: 'button', onClick: resetProfileFeatures }, 'Reset checks'), h('button', { className: 'agent-console__example', type: 'button', disabled: busy, onClick: runFastAdvisory }, busy ? 'Running…' : 'Run fast advisory'), h('button', { className: 'agent-console__button', type: 'button', disabled: busy, onClick: runPlatformReview }, busy ? 'Running…' : (streamMode ? 'Stream platform review' : 'Run platform review'))])
				]),
				h('div', { className: 'platform-console__grid' }, [
					h('label', { className: 'agent-console__label' }, ['Primary concern', h('input', { className: 'agent-console__input', value: concern, onChange: (event) => setConcern(event.target.value), placeholder: 'upgrade blockers / failover readiness / migration wave risk' })]),
					h('label', { className: 'agent-console__label' }, ['Recent change or expected event', h('input', { className: 'agent-console__input', value: recentChange, onChange: (event) => setRecentChange(event.target.value), placeholder: 'new MCO rollout / DR rehearsal / virtualization onboarding' })]),
					h('label', { className: 'agent-console__label' }, ['Success criteria', h('input', { className: 'agent-console__input', value: successCriteria, onChange: (event) => setSuccessCriteria(event.target.value), placeholder: 'zero upgrade blockers and clean DR handoff' })]),
					h('label', { className: 'agent-console__label' }, ['Target audience', h('input', { className: 'agent-console__input', value: audience, onChange: (event) => setAudience(event.target.value), placeholder: 'platform engineering, CAB, or migration squad' })])
				]),
				h('section', { className: 'platform-console__card' }, [
					h('div', { className: 'agent-console__queue-header' }, [h('div', null, [h('h3', null, 'Selected platform checks'), h('p', { className: 'platform-console__meta' }, 'Choose the exact OpenShift signals to include in this review. The generated prompt names these areas explicitly so the evidence path stays grounded across lifecycle, workloads, security, delivery, fleet, and resiliency surfaces.')]), h('span', { className: 'platform-console__pill' }, `${selectedFeatures.length} selected`)]),
					h('div', { className: 'platform-console__filter-bar' }, [
						h('label', { className: 'agent-console__label' }, ['Find checks', h('input', { className: 'agent-console__input', value: featureSearch, onChange: (event) => setFeatureSearch(event.target.value), placeholder: 'Search lifecycle, autoscaler, migration, ingress…' })]),
						h('label', { className: 'agent-console__label' }, [h('span', null, 'Show selected only'), h('input', { type: 'checkbox', checked: showSelectedOnly, onChange: (event) => setShowSelectedOnly(event.target.checked) })]),
						h('div', { className: 'platform-console__selection-summary' }, [
							h('span', { className: 'platform-console__pill' }, `${visibleFeatureCount} visible`),
							h('span', { className: 'platform-console__meta' }, showSelectedOnly ? 'Filtering to selected checks only.' : 'Showing the full category catalog.')
						])
					]),
					h('div', { className: 'platform-console__category-strip' }, featureGroups.map((group) => h('article', { className: 'platform-console__category-chip', key: `${group.title}-chip` }, [
						h('strong', null, group.title),
						h('span', { className: 'platform-console__meta' }, groupDescriptions[group.title] || ''),
						h('span', { className: 'platform-console__pill' }, `${group.features.filter((featureId) => selectedFeatures.includes(featureId)).length}/${group.features.length}`)
					]))),
					h('div', { className: 'agent-console__actions' }, [h('button', { className: 'agent-console__example', type: 'button', onClick: selectAllFeatures }, 'Select all OpenShift checks'), h('button', { className: 'agent-console__example', type: 'button', onClick: clearAllFeatures }, 'Clear checks'), h('button', { className: 'agent-console__example', type: 'button', onClick: resetProfileFeatures }, 'Restore profile defaults')]),
					h(
						'div',
						{ className: 'platform-console__feature-group-list' },
						visibleFeatureGroups.length
							? visibleFeatureGroups.map((group) => h('section', { className: 'platform-console__feature-group', key: group.title }, [
								h('div', { className: 'platform-console__feature-group-header' }, [
									h('div', null, [
										h('h4', null, group.title),
										h('p', { className: 'platform-console__meta' }, groupDescriptions[group.title] || '')
									]),
									h('span', { className: 'platform-console__pill' }, `${group.features.filter((featureId) => selectedFeatures.includes(featureId)).length}/${group.features.length}`)
								]),
								h('div', { className: 'platform-console__feature-list' }, group.visibleFeatures.map((featureId) => h('label', { className: 'platform-console__feature', key: featureId }, [
									h('input', { type: 'checkbox', checked: selectedFeatures.includes(featureId), onChange: () => toggleFeature(featureId) }),
									h('span', null, [
										h('span', { className: 'platform-console__feature-label' }, featureLabels[featureId] || slugToTitle(featureId)),
										featureDescriptions[featureId] ? h('span', { className: 'platform-console__feature-note' }, featureDescriptions[featureId]) : null,
										h('span', { className: 'platform-console__meta' }, `Tool: ${featureId}`)
									])
								]))),
							]))
							: h('div', { className: 'platform-console__empty' }, 'No platform checks match the current selector filters. Clear the search or show all checks to continue.')
					)
				]),
				h('section', { className: 'platform-console__card' }, [
					h('div', { className: 'agent-console__queue-header' }, [h('div', null, [h('h3', null, 'Prompt builder'), h('p', { className: 'platform-console__meta' }, 'Adjust the context below if you want the agent to emphasize a specific change window, dependency set, or handoff audience.')]), h('span', { className: 'platform-console__pill' }, streamMode ? 'Live /chat/stream prompt' : 'Live /chat prompt')]),
					h('div', { className: 'platform-console__question-grid' }, profile.questions.map((question) => h('div', { className: 'platform-console__hero-note', key: question }, [h('span', { className: 'platform-console__badge' }, 'Review question'), h('p', null, question)]))),
					(profile.expectedOutputs || []).length ? h('div', { className: 'platform-console__question-grid' }, profile.expectedOutputs.map((item) => h('div', { className: 'platform-console__hero-note', key: item }, [h('span', { className: 'platform-console__badge platform-console__badge--ok' }, 'Expected output'), h('p', null, item)]))) : null,
					h('label', { className: 'agent-console__label' }, ['Additional operator guidance', h('textarea', { className: 'agent-console__textarea', rows: 3, value: customPrompt, onChange: (event) => setCustomPrompt(event.target.value), placeholder: 'Optional extra instructions for this platform review.' })]),
					h('label', { className: 'agent-console__label' }, ['Generated review prompt', h('textarea', { className: 'agent-console__textarea', rows: 11, value: prompt, readOnly: true, onKeyDown: (event) => { if ((event.metaKey || event.ctrlKey) && event.key === 'Enter') { event.preventDefault(); runPlatformReview(); } } })])
				]),
				h('section', { className: 'platform-console__card' }, [
					h('div', { className: 'agent-console__queue-header' }, [h('div', null, [h('h3', null, 'Runtime controls'), h('p', { className: 'platform-console__meta' }, 'Same backend, separate platform lane. Adjust provider or cluster overrides here when you need a different target or model.')]), h('span', { className: 'platform-console__pill' }, 'Operator context')]),
					h('div', { className: 'platform-console__runtime-grid' }, [
						h('label', { className: 'agent-console__label' }, ['LLM provider', h('select', { className: 'agent-console__input', value: providerId, onChange: (event) => setProviderId(event.target.value) }, (providerCatalog.providers || []).map((provider) => h('option', { key: provider.id, value: provider.id }, provider.label || provider.id)))]),
						providerId === 'ollama'
							? h('label', { className: 'agent-console__label' }, ['Ollama base URL', h('input', { className: 'agent-console__input', value: ollamaBaseUrl, onChange: (event) => setOllamaBaseUrl(event.target.value), placeholder: 'http://host.containers.internal:11434' })])
							: h('label', { className: 'agent-console__label' }, ['External base URL', h('input', { className: 'agent-console__input', value: externalBaseUrl, onChange: (event) => setExternalBaseUrl(event.target.value), placeholder: 'https://api.openai.com/v1' })]),
						h('label', { className: 'agent-console__label' }, [(providerId === 'ollama' ? 'Local model' : 'Hosted model'), h('input', { className: 'agent-console__input', value: providerId === 'ollama' ? modelName : externalModelName, list: 'platform-suggested-models', onChange: (event) => providerId === 'ollama' ? setModelName(event.target.value) : setExternalModelName(event.target.value), placeholder: suggestedModels[0] || 'model name' }), h('datalist', { id: 'platform-suggested-models' }, suggestedModels.map((model) => h('option', { key: model, value: model })))]),
						h('label', { className: 'agent-console__label' }, ['Kube context name', h('input', { className: 'agent-console__input', value: kubeContextName, onChange: (event) => setKubeContextName(event.target.value), placeholder: 'Optional kube context override' })]),
						h('label', { className: 'agent-console__label' }, ['OpenShift API URL', h('input', { className: 'agent-console__input', value: openshiftApiUrl, onChange: (event) => setOpenshiftApiUrl(event.target.value), placeholder: 'https://api.cluster.example:6443' })]),
						h('label', { className: 'agent-console__label' }, ['OpenShift token', h('input', { className: 'agent-console__input', type: 'password', value: openshiftToken, onChange: (event) => setOpenshiftToken(event.target.value), placeholder: 'Optional bearer token' })]),
						providerId !== 'ollama' ? h('label', { className: 'agent-console__label' }, ['Hosted API key', h('input', { className: 'agent-console__input', type: 'password', value: externalApiKey, onChange: (event) => setExternalApiKey(event.target.value), placeholder: 'Optional API key override' })]) : null,
						providerId !== 'ollama' ? h('label', { className: 'agent-console__label' }, ['API version', h('input', { className: 'agent-console__input', value: externalApiVersion, onChange: (event) => setExternalApiVersion(event.target.value), placeholder: 'Optional API version' })]) : null,
						providerId !== 'ollama' ? h('label', { className: 'agent-console__label' }, ['Organization / tenant hint', h('input', { className: 'agent-console__input', value: externalOrganization, onChange: (event) => setExternalOrganization(event.target.value), placeholder: 'Optional organization hint' })]) : null,
						h('label', { className: 'agent-console__label' }, [h('span', null, 'Verify SSL'), h('input', { type: 'checkbox', checked: verifySsl, onChange: (event) => setVerifySsl(event.target.checked) })])
					])
				])
			]),

			h('section', { className: 'agent-console__panel', id: 'platform-library', key: 'library' }, [
				h('div', { className: 'agent-console__queue-header' }, [h('div', null, [h('h2', null, 'Templates and watchlists'), h('p', { className: 'platform-console__meta' }, 'Turn one solid platform review into a reusable operating motion: save the prompt, reload it later, or schedule it as a watchlist-ready run definition.')]), h('span', { className: 'platform-console__pill' }, `${savedTemplates.length} templates · ${watchlists.length} watchlists`)]),
				h('div', { className: 'platform-console__grid' }, [
					h('article', { className: 'platform-console__card' }, [
						h('h3', null, 'Save current review as template'),
						h('div', { className: 'platform-console__grid' }, [
							h('label', { className: 'agent-console__label' }, ['Template name', h('input', { className: 'agent-console__input', value: templateName, onChange: (event) => setTemplateName(event.target.value), placeholder: 'Lifecycle readiness template' })]),
							h('label', { className: 'agent-console__label' }, ['Template category', h('input', { className: 'agent-console__input', value: templateCategory, onChange: (event) => setTemplateCategory(event.target.value), placeholder: 'platform' })])
						]),
						h('label', { className: 'agent-console__label' }, ['Description', h('textarea', { className: 'agent-console__textarea', rows: 3, value: templateDescription, onChange: (event) => setTemplateDescription(event.target.value), placeholder: 'Describe when this platform template should be reused.' })]),
						h('div', { className: 'agent-console__actions' }, [h('button', { className: 'agent-console__button', type: 'button', onClick: saveTemplate }, 'Save template'), h('button', { className: 'agent-console__example', type: 'button', onClick: () => loadTemplates().then(() => setTemplateStatus({ message: 'Refreshed the saved template library.', tone: 'ok' })).catch((error) => setTemplateStatus({ message: error.message, tone: 'error' })) }, 'Refresh library')]),
						renderStatus(templateStatus),
						h('div', { className: 'platform-console__library-list' }, savedTemplates.length ? savedTemplates.map(renderTemplateCard) : [h('div', { className: 'platform-console__empty', key: 'no-templates' }, 'No saved templates yet. Save the current review to seed the reusable library.')])
					]),
					h('article', { className: 'platform-console__card' }, [
						h('h3', null, 'Watchlist manager'),
						h('div', { className: 'platform-console__grid' }, [
							h('label', { className: 'agent-console__label' }, ['Watchlist name', h('input', { className: 'agent-console__input', value: watchlistName, onChange: (event) => setWatchlistName(event.target.value), placeholder: 'Weekly lifecycle readiness watchlist' })]),
							h('label', { className: 'agent-console__label' }, ['Saved template', h('select', { className: 'agent-console__input', value: selectedTemplateId, onChange: (event) => setSelectedTemplateId(event.target.value) }, [h('option', { key: 'empty', value: '' }, savedTemplates.length ? 'Choose a template' : 'No templates saved yet'), ...savedTemplates.map((item) => h('option', { key: item.id, value: String(item.id) }, `${item.name} · ${item.category}`))])]),
							h('label', { className: 'agent-console__label' }, ['Cluster scopes (CSV)', h('input', { className: 'agent-console__input', value: watchlistRegions, onChange: (event) => setWatchlistRegions(event.target.value), placeholder: 'aro-prod,rosa-stage,baremetal-dr' })]),
							h('label', { className: 'agent-console__label' }, ['Operator notes', h('input', { className: 'agent-console__input', value: watchlistNotes, onChange: (event) => setWatchlistNotes(event.target.value), placeholder: 'Run before the weekly CAB checkpoint' })])
						]),
						h('div', { className: 'agent-console__actions' }, [h('button', { className: 'agent-console__button', type: 'button', onClick: () => createWatchlist(false) }, 'Create watchlist'), h('button', { className: 'agent-console__example', type: 'button', onClick: () => createWatchlist(true) }, 'Create from current review'), h('button', { className: 'agent-console__example', type: 'button', onClick: () => loadWatchlists().then(() => setWatchlistStatus({ message: 'Refreshed the watchlist catalog.', tone: 'ok' })).catch((error) => setWatchlistStatus({ message: error.message, tone: 'error' })) }, 'Refresh watchlists')]),
						renderStatus(watchlistStatus),
						h('div', { className: 'platform-console__library-list' }, watchlists.length ? watchlists.map(renderWatchlistCard) : [h('div', { className: 'platform-console__empty', key: 'no-watchlists' }, 'No watchlists yet. Save a template or create a watchlist directly from the current review.')]),
						watchlistResults.length ? h('div', { className: 'platform-console__watchlist-results' }, [h('h4', null, 'Latest watchlist results'), ...watchlistResults.map((result, index) => h('details', { className: 'platform-console__library-card', key: `${result.run_id || index}-${index}` }, [h('summary', null, `${result.region} · ${result.role_arn || 'current execution context'} · run ${result.run_id || 'n/a'}`), h('p', { className: 'platform-console__meta' }, `Confidence: ${result.confidence ?? '—'}`), h('pre', null, result.answer || 'No answer returned.')]))]) : null
					])
				])
			]),

			h('section', { className: 'agent-console__panel', id: 'platform-intelligence', key: 'intelligence' }, [
				h('div', { className: 'agent-console__queue-header' }, [h('div', null, [h('h2', null, 'Scoring, trends, and run comparison'), h('p', { className: 'platform-console__meta' }, 'Use the readiness scorecard for the latest run, then compare it against recent history to prove whether the platform is moving toward or away from a safe change window.')]), h('span', { className: `platform-console__badge ${scoreDetails.tone === 'ok' ? 'platform-console__badge--ok' : 'platform-console__badge--warn'}` }, scoreDetails.overall === null ? 'Awaiting first run' : `Readiness ${scoreDetails.overall}/100`)]),
				renderStatus(overviewStatus),
				h('div', { className: 'platform-console__grid' }, [
					h('article', { className: 'platform-console__card' }, [
							h('h3', null, `${profileInsight.label} scorecard`),
						scoreDetails.overall === null
								? h('div', { className: 'platform-console__empty' }, 'Run a platform review to compute the score, profile insight, and category breakdown.')
							: h('div', { className: 'platform-console__score-grid' }, [
									h('article', { className: `platform-console__score-card platform-console__score-card--${scoreDetails.tone}` }, [h('span', { className: 'platform-console__meta' }, profileInsight.label), h('strong', { className: 'platform-console__score-value' }, `${scoreDetails.overall}/100`), h('p', { className: 'platform-console__meta' }, `${scoreDetails.flagged} flagged metrics · ${scoreDetails.errors} tool errors · ${scoreDetails.healthy} healthy signals`)]),
								...scoreDetails.categoryScores.map((item) => h('article', { className: `platform-console__score-card platform-console__score-card--${item.tone}`, key: item.title }, [h('span', { className: 'platform-console__meta' }, item.title), h('strong', { className: 'platform-console__score-value' }, String(item.score)), h('p', { className: 'platform-console__meta' }, `${item.selectedCount} checks · ${item.errors} errors · ${item.flagged} flagged · ${item.healthy} healthy`)]))
							]),
							h('div', { className: 'platform-console__recommendations' }, [h('h4', null, 'Suggested next actions'), h('ul', null, recommendations.map((item, index) => h('li', { key: `${index}-${item}` }, item)))]),
							h('div', { className: 'platform-console__recommendations' }, [h('h4', null, 'Blast radius and runbook signals'), h('ul', null, [(impactMap[0] ? `Top impacted domain: ${impactMap[0].domain} (${impactMap[0].count} hot checks)` : 'Run a review to derive impacted domains.'), (runbookCorrelations[0] ? `Top correlated playbook: ${runbookCorrelations[0].title}` : 'Run a review to derive playbook correlation.'), ...(profileInsight.details || [])].map((item, index) => h('li', { key: `insight-${index}-${item}` }, item)))])
					]),
					h('article', { className: 'platform-console__card' }, [
						h('div', { className: 'agent-console__queue-header' }, [h('div', null, [h('h3', null, 'Recent platform run history'), h('p', { className: 'platform-console__meta' }, 'Quick access to recent runs and the latest numeric metrics extracted from persisted tool traces.')]), h('button', { className: 'agent-console__example', type: 'button', onClick: () => loadOverview().catch((error) => setOverviewStatus({ message: error.message, tone: 'error' })) }, 'Refresh history')]),
						h('ul', null, [h('li', { key: 'runs' }, [h('strong', null, 'Total runs: '), String(overview.summary?.total_runs ?? 0)]), h('li', { key: 'failed' }, [h('strong', null, 'Failed runs: '), String(overview.summary?.failed_runs ?? 0)]), h('li', { key: 'avg' }, [h('strong', null, 'Average duration: '), `${overview.summary?.average_duration_ms ?? '—'} ms`]), h('li', { key: 'last' }, [h('strong', null, 'Last run: '), formatDateTime(overview.summary?.last_run_at)])]),
						overview.recent_runs?.length ? h('div', { className: 'platform-console__table-wrap' }, [h('table', { className: 'platform-console__step-table' }, [h('thead', null, h('tr', null, [h('th', null, 'Run'), h('th', null, 'Scope'), h('th', null, 'When'), h('th', null, 'Status')])), h('tbody', null, overview.recent_runs.slice(0, 6).map((run) => h('tr', { key: run.run_id }, [h('td', null, `#${run.run_id}`), h('td', null, run.cluster_scope || '—'), h('td', null, formatDateTime(run.created_at)), h('td', null, run.status || 'completed')])) )])]) : h('div', { className: 'platform-console__empty' }, 'No historical runs have been recorded yet.'),
						overview.latest_metrics?.length ? h('div', { className: 'platform-console__mini-list' }, overview.latest_metrics.slice(0, 6).map((metric) => h('div', { className: 'platform-console__mini-item', key: metric.metric_key }, [h('strong', null, metric.metric_label), h('span', { className: 'platform-console__meta' }, `${metric.metric_value}${metric.unit ? ` ${metric.unit}` : ''} · ${metric.tool_name || 'metric'}`)]))) : null
					])
				]),
				h('article', { className: 'platform-console__card' }, [
					h('div', { className: 'agent-console__queue-header' }, [h('div', null, [h('h3', null, 'Compare two historical runs'), h('p', { className: 'platform-console__meta' }, 'Spot drift in duration, tool usage, and numeric metrics without leaving the Platform Console.')]), h('div', { className: 'agent-console__actions' }, [h('button', { className: 'agent-console__example', type: 'button', onClick: () => { if (overview.recent_runs?.[1] && overview.recent_runs?.[0]) { setCompareLeft(String(overview.recent_runs[1].run_id)); setCompareRight(String(overview.recent_runs[0].run_id)); } } }, 'Latest vs previous'), h('button', { className: 'agent-console__button', type: 'button', onClick: compareRuns }, 'Compare runs')])]),
					h('div', { className: 'platform-console__compare-grid' }, [
						h('label', { className: 'agent-console__label' }, ['Baseline run', h('select', { className: 'agent-console__input', value: compareLeft, onChange: (event) => setCompareLeft(event.target.value) }, [h('option', { key: 'baseline-empty', value: '' }, overview.recent_runs?.length ? 'Choose baseline run' : 'No runs available'), ...(overview.recent_runs || []).map((run) => h('option', { key: `baseline-${run.run_id}`, value: String(run.run_id) }, `#${run.run_id} · ${run.cluster_scope || 'scope'} · ${formatDateTime(run.created_at)}`))])]),
						h('label', { className: 'agent-console__label' }, ['Comparison run', h('select', { className: 'agent-console__input', value: compareRight, onChange: (event) => setCompareRight(event.target.value) }, [h('option', { key: 'compare-empty', value: '' }, overview.recent_runs?.length ? 'Choose comparison run' : 'No runs available'), ...(overview.recent_runs || []).map((run) => h('option', { key: `compare-${run.run_id}`, value: String(run.run_id) }, `#${run.run_id} · ${run.cluster_scope || 'scope'} · ${formatDateTime(run.created_at)}`))])])
					]),
					comparePayload
						? h('div', { className: 'platform-console__compare-grid' }, [
							h('article', { className: 'platform-console__summary' }, [h('span', { className: 'platform-console__badge platform-console__badge--ok' }, 'Run drift summary'), h('ul', null, [h('li', { key: 'left' }, `Baseline: #${comparePayload.left?.run_id} · ${comparePayload.left?.cluster_scope || 'unknown scope'} · ${formatDateTime(comparePayload.left?.created_at)}`), h('li', { key: 'right' }, `Comparison: #${comparePayload.right?.run_id} · ${comparePayload.right?.cluster_scope || 'unknown scope'} · ${formatDateTime(comparePayload.right?.created_at)}`), h('li', { key: 'duration' }, [h('strong', null, 'Duration delta: '), `${comparePayload.summary?.duration_delta_ms ?? '—'} ms`]), h('li', { key: 'step' }, [h('strong', null, 'Step delta: '), String(comparePayload.summary?.step_delta ?? '—')]), h('li', { key: 'added' }, [h('strong', null, 'Tools added: '), (comparePayload.summary?.tool_added || []).join(', ') || 'none']), h('li', { key: 'removed' }, [h('strong', null, 'Tools removed: '), (comparePayload.summary?.tool_removed || []).join(', ') || 'none'])])]),
							h('article', { className: 'platform-console__summary' }, [h('span', { className: 'platform-console__badge' }, 'Metric deltas'), comparePayload.metric_deltas?.length ? h('div', { className: 'platform-console__table-wrap' }, [h('table', { className: 'platform-console__step-table' }, [h('thead', null, h('tr', null, [h('th', null, 'Metric'), h('th', null, 'Left'), h('th', null, 'Right'), h('th', null, 'Delta')])), h('tbody', null, comparePayload.metric_deltas.slice(0, 12).map((item) => h('tr', { key: item.metric_key }, [h('td', null, item.metric_key), h('td', null, item.left_value ?? '—'), h('td', null, item.right_value ?? '—'), h('td', null, item.delta ?? '—')])) )])]) : h('p', { className: 'platform-console__meta' }, 'No comparable numeric metrics were found between the selected runs.')])
						])
						: h('div', { className: 'platform-console__empty' }, 'Pick two runs and compare them to see drift in tool usage, duration, and numeric metrics.')
				])
			]),

			h('section', { className: 'agent-console__panel', id: 'platform-results', key: 'results' }, [
				h('div', { className: 'agent-console__queue-header' }, [h('div', null, [h('h2', null, 'Latest platform results'), h('p', { className: 'platform-console__meta' }, 'See the summary first, then drill into tool-level evidence. Use the filter controls when you want only hotspots or only healthy signals.')]), lastRun.runId ? h('span', { className: 'platform-console__badge platform-console__badge--ok' }, `Run #${lastRun.runId}`) : h('span', { className: 'platform-console__badge' }, 'Awaiting first run')]),
				h('div', { className: 'agent-console__actions' }, [h('button', { className: 'agent-console__example', type: 'button', onClick: () => setToolFilter('all') }, 'All tool cards'), h('button', { className: 'agent-console__example', type: 'button', onClick: () => setToolFilter('attention') }, 'Attention only'), h('button', { className: 'agent-console__example', type: 'button', onClick: () => setToolFilter('healthy') }, 'Healthy only')]),
				lastRun.answer
					? h('div', { className: 'platform-console__result-grid' }, [
						h('article', { className: 'platform-console__summary' }, [h('span', { className: 'platform-console__badge platform-console__badge--ok' }, 'Executive summary'), h('p', null, lastRun.answer)]),
						h('article', { className: 'platform-console__summary' }, [h('span', { className: 'platform-console__badge' }, 'At-a-glance'), h('ul', null, summaryCards.map((card) => h('li', { key: card.label }, [h('strong', null, `${card.label}: `), String(card.value)])))]),
						h('article', { className: 'platform-console__summary' }, [h('span', { className: 'platform-console__badge' }, 'Next actions'), h('ul', null, recommendations.map((item, index) => h('li', { key: `${index}-${item}` }, item)))]),
						h('article', { className: 'platform-console__summary' }, [h('span', { className: 'platform-console__badge' }, 'Blast radius / runbook correlation'), h('ul', null, [
							...(impactMap.length ? impactMap.slice(0, 3).map((item) => `${item.domain}: ${item.count} impacted check(s)`) : ['No impacted domains derived yet.']),
							...(runbookCorrelations.length ? runbookCorrelations.slice(0, 3).map((item) => `${item.title}: ${item.count} correlated signal(s)`) : ['No runbook correlation derived yet.'])
						].map((item, index) => h('li', { key: `correlation-${index}-${item}` }, item)))])
					])
					: h('div', { className: 'platform-console__empty' }, 'Run a platform review to populate the latest summary, readiness score, and evidence trace.'),
				filteredToolCards.length ? h('div', { className: 'platform-console__grid' }, filteredToolCards.map((card) => h('article', { className: 'platform-console__tool-card', key: card.tool }, [h('div', { className: 'agent-console__queue-header' }, [h('div', null, [h('h3', null, card.label), h('p', { className: 'platform-console__meta' }, `Tool: ${card.tool}`)]), card.error ? h('span', { className: 'platform-console__badge platform-console__badge--warn' }, 'Needs attention') : h('span', { className: 'platform-console__badge platform-console__badge--ok' }, 'Evidence captured')]), card.error ? h('p', null, card.error) : null, card.counts.length ? h('ul', null, card.counts.map((entry) => h('li', { key: `${card.tool}-${entry.label}` }, `${entry.label}: ${entry.value}`))) : h('p', { className: 'platform-console__meta' }, 'No count-style metrics were extracted from this tool response.'), ...card.rowGroups.map((group) => h('details', { key: `${card.tool}-${group.key}` }, [h('summary', null, `${group.key.replace(/_/g, ' ')} sample rows`), h('pre', null, JSON.stringify(group.rows, null, 2))]))]))) : h('div', { className: 'platform-console__empty' }, toolCards.length ? 'No tool cards match the current filter.' : 'No tool trace yet. Run the review to populate evidence cards.')
			]),

			h('section', { className: 'agent-console__panel', id: 'platform-sweep', key: 'sweep' }, [
				h('div', { className: 'agent-console__queue-header' }, [h('div', null, [h('h2', null, 'Multi-cluster sweep lane'), h('p', { className: 'platform-console__meta' }, 'Reuse the currently selected platform checks across multiple cluster scopes. This is the estate-wide variant of the local review flow.')]), h('span', { className: 'platform-console__pill' }, `${selectedSweepTools.length} sweep tools`)]),
				renderStatus(sweepStatus),
				h('div', { className: 'platform-console__grid' }, [
					h('label', { className: 'agent-console__label' }, ['Cluster scopes (CSV)', h('input', { className: 'agent-console__input', value: sweepRegions, onChange: (event) => setSweepRegions(event.target.value), placeholder: 'aro-prod,rosa-stage,baremetal-dr,ibmz-prod' })]),
					h('label', { className: 'agent-console__label' }, ['Execution contexts / role ARNs (one per line, optional)', h('textarea', { className: 'agent-console__textarea', rows: 3, value: sweepRoles, onChange: (event) => setSweepRoles(event.target.value), placeholder: 'Leave blank to use the current execution context.' })])
				]),
				h('div', { className: 'agent-console__actions' }, [h('button', { className: 'agent-console__button', type: 'button', onClick: runSweep }, 'Run platform sweep'), h('a', { href: 'posture-radar.html', className: 'agent-console__example' }, 'Open full posture radar')]),
				selectedFeatures.length > maxSweepTools ? h('p', { className: 'platform-console__meta' }, `The backend sweep endpoint accepts up to ${maxSweepTools} tools per request, so this lane uses the first ${maxSweepTools} selected platform checks.`) : null,
				sweepPayload.results?.length ? h('div', { className: 'platform-console__grid' }, sweepPayload.results.map(renderSweepCard)) : h('div', { className: 'platform-console__empty' }, 'Run a multi-cluster sweep to compare the selected platform signals across the estate.')
			]),

			h('section', { className: 'agent-console__panel', id: 'platform-exports', key: 'exports' }, [
				h('div', { className: 'agent-console__queue-header' }, [h('div', null, [h('h2', null, 'Export platform handoff pack'), h('p', { className: 'platform-console__meta' }, 'Create a quick handoff for change review, DR rehearsal, or migration planning without retyping the summary.')]), h('span', { className: 'platform-console__pill' }, 'CSV + PPT + PDF + Word')]),
				h('div', { className: 'platform-console__exports' }, [
					h('article', { className: 'platform-console__card' }, [h('h3', null, 'Export formats'), h('div', { className: 'agent-console__actions' }, [h('button', { className: 'agent-console__button', type: 'button', onClick: () => exportHandler('csv') }, 'Export CSV'), h('button', { className: 'agent-console__button', type: 'button', onClick: () => exportHandler('ppt') }, 'Export PPT'), h('button', { className: 'agent-console__button', type: 'button', onClick: () => exportHandler('pdf') }, 'Export PDF'), h('button', { className: 'agent-console__button', type: 'button', onClick: () => exportHandler('word') }, 'Export Word')])]),
					h('article', { className: 'platform-console__summary' }, [h('h3', null, 'Pack preview'), h('pre', null, markdownPack)])
				])
			]),

			h('section', { className: 'agent-console__panel', id: 'platform-trace', key: 'trace' }, [
				h('div', { className: 'agent-console__queue-header' }, [h('div', null, [h('h2', null, 'Evidence trace'), h('p', { className: 'platform-console__meta' }, 'The raw step list stays visible so platform teams can verify which evidence sources were actually inspected. In streaming mode, this table fills in as each tool returns.')]), h('span', { className: 'platform-console__pill' }, `${lastRun.steps.length} steps`)]),
				lastRun.steps.length ? h('div', { className: 'platform-console__trace' }, [h('table', { className: 'platform-console__step-table' }, [h('thead', null, h('tr', null, [h('th', null, 'Step'), h('th', null, 'Tool'), h('th', null, 'Status'), h('th', null, 'Highlights')])), h('tbody', null, lastRun.steps.map((step, index) => { const payload = deriveToolPayload(step); const counts = summarizeCounts(payload).map((entry) => `${entry.label}: ${entry.value}`).join('; '); return h('tr', { key: `${deriveToolName(step) || 'model'}-${index}` }, [h('td', null, String(index + 1)), h('td', null, deriveToolName(step) || 'model-step'), h('td', null, step.error || step.tool_error ? 'Error' : 'Completed'), h('td', null, counts || (typeof payload === 'string' ? payload.slice(0, 140) : 'Model reasoning or non-count payload'))]); }))])]) : h('div', { className: 'platform-console__empty' }, 'No step trace yet. The first platform review will show each evidence hop here.')
			])
		]);
	}

	const reactRoot = window.ReactDOM.createRoot(root);
	reactRoot.render(h(PlatformConsoleApp));
})();
