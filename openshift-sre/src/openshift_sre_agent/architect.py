from __future__ import annotations

import base64
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from html import escape
from io import BytesIO
import json
from pathlib import Path
import re
import shutil
import subprocess
from tempfile import TemporaryDirectory
from typing import Any
import xml.etree.ElementTree as ET

try:
    import cairosvg
except ImportError:  # pragma: no cover
    cairosvg = None


GROUP_ORDER = [
    "context",
    "fleet",
    "control-plane",
    "network",
    "security",
    "delivery",
    "workload",
    "data",
    "operations",
]
GROUP_LABELS = {
    "context": "Context",
    "fleet": "Fleet / management",
    "control-plane": "Control plane",
    "network": "Networking / ingress",
    "security": "Security / governance",
    "delivery": "Delivery / GitOps",
    "workload": "Applications / platform services",
    "data": "Storage / protection",
    "operations": "Observability / operations",
}
GROUP_STYLES = {
    "context": {"fill": "#E0F2FE", "stroke": "#0284C7"},
    "fleet": {"fill": "#EDE9FE", "stroke": "#7C3AED"},
    "control-plane": {"fill": "#DBEAFE", "stroke": "#2563EB"},
    "network": {"fill": "#CCFBF1", "stroke": "#0F766E"},
    "security": {"fill": "#FEE2E2", "stroke": "#DC2626"},
    "delivery": {"fill": "#FEF3C7", "stroke": "#D97706"},
    "workload": {"fill": "#DCFCE7", "stroke": "#16A34A"},
    "data": {"fill": "#FCE7F3", "stroke": "#DB2777"},
    "operations": {"fill": "#E2E8F0", "stroke": "#475569"},
}
ARCHITECT_ASSESSMENT_SCOPES = [
    {"id": "architecture-readiness", "label": "Architecture readiness", "description": "Balanced OpenShift architecture review across topology, security, operations, and resilience."},
    {"id": "security-governance", "label": "Security and governance", "description": "Review identity, policy, guardrails, and segmentation coverage."},
    {"id": "reliability-dr", "label": "Reliability and DR", "description": "Review failure domains, backup posture, and failover readiness."},
    {"id": "platform-operations", "label": "Platform operations", "description": "Review day-2 operations, observability, GitOps, and lifecycle posture."},
]
ARCHITECT_DIAGRAM_TEMPLATES = [
    {
        "id": "custom",
        "label": "Custom OpenShift architecture",
        "category": "General",
        "description": "Start with a prompt-led OpenShift design and let the workspace infer the right platform building blocks.",
        "prompt": "Design a production-grade OpenShift architecture with explicit cluster boundaries, ingress, platform services, security controls, observability, backup, and day-2 operating detail.",
        "mode": "prompt-only",
        "skills": ["OpenShift", "Kubernetes", "HLD", "LLD"],
        "default_nodes": [
            {"node_id": "business_context", "label": "Business / platform context", "group": "context", "detail": "Drivers, constraints, tenancy, and compliance posture."},
            {"node_id": "ocp_cluster", "label": "OpenShift clusters", "group": "control-plane", "detail": "Cluster API, operators, machine pools, and core platform services."},
            {"node_id": "ingress", "label": "Ingress / routes", "group": "network", "detail": "External access via IngressController, Routes, DNS, and load balancing."},
            {"node_id": "apps", "label": "Applications and workloads", "group": "workload", "detail": "Platform and business workloads running on projects / namespaces."},
            {"node_id": "ops", "label": "Observability and operations", "group": "operations", "detail": "Monitoring, logging, alerting, and runbook execution."},
        ],
        "default_edges": [
            {"source": "business_context", "target": "ocp_cluster", "label": "requirements"},
            {"source": "ingress", "target": "ocp_cluster", "label": "traffic entry"},
            {"source": "ocp_cluster", "target": "apps", "label": "workload runtime"},
            {"source": "ocp_cluster", "target": "ops", "label": "telemetry"},
        ],
    },
    {
        "id": "multicluster-fleet",
        "label": "ACM multicluster fleet",
        "category": "Platform",
        "description": "Hub-and-spoke fleet with ACM governance, policy, and lifecycle orchestration.",
        "prompt": "Create a multicluster OpenShift fleet architecture with ACM hub, managed clusters, governance, policy, GitOps, DR coordination, and platform operations.",
        "mode": "hybrid",
        "skills": ["ACM", "Fleet", "Governance", "DR"],
        "default_nodes": [
            {"node_id": "hub", "label": "ACM hub cluster", "group": "fleet", "detail": "Fleet management, governance, placement, and policy orchestration."},
            {"node_id": "managed_clusters", "label": "Managed clusters", "group": "control-plane", "detail": "ROSA, ARO, baremetal, and edge clusters under fleet governance."},
            {"node_id": "fleet_gitops", "label": "Fleet GitOps", "group": "delivery", "detail": "GitOps promotion, cluster config, and application deployment flows."},
            {"node_id": "fleet_security", "label": "Fleet security and policy", "group": "security", "detail": "ACM governance policy, identity, segmentation, and compliance evidence."},
            {"node_id": "fleet_ops", "label": "Fleet observability", "group": "operations", "detail": "Central monitoring, logging, health, and posture review."},
        ],
        "default_edges": [
            {"source": "hub", "target": "managed_clusters", "label": "governance / lifecycle"},
            {"source": "fleet_gitops", "target": "managed_clusters", "label": "config / app delivery"},
            {"source": "fleet_security", "target": "managed_clusters", "label": "policy enforcement"},
            {"source": "managed_clusters", "target": "fleet_ops", "label": "telemetry"},
        ],
    },
    {
        "id": "airgapped-disconnected",
        "label": "Disconnected / air-gapped platform",
        "category": "Platform",
        "description": "Air-gapped or restricted OpenShift with mirrored registries, controlled ingress, and offline operations.",
        "prompt": "Create a disconnected OpenShift architecture with mirrored registries, image supply chain controls, bastion or jump-host paths, offline content sync, observability, and supportable day-2 operations.",
        "mode": "prompt-only",
        "skills": ["Air-gapped", "Disconnected", "Registry", "Operations"],
        "default_nodes": [
            {"node_id": "mirror_registry", "label": "Mirror registry and content cache", "group": "delivery", "detail": "Mirrored release payloads, operator catalogs, and application images."},
            {"node_id": "offline_clusters", "label": "Disconnected clusters", "group": "control-plane", "detail": "OpenShift clusters with no direct internet dependency."},
            {"node_id": "offline_network", "label": "Controlled ingress and egress", "group": "network", "detail": "Proxy, firewall, bastion, and change-controlled external exchange points."},
            {"node_id": "offline_security", "label": "Supply chain and access controls", "group": "security", "detail": "Registry trust, identity, admission policy, and audit controls."},
            {"node_id": "offline_ops", "label": "Offline operations and support", "group": "operations", "detail": "Logging, backup, evidence collection, and break-glass procedures."},
        ],
        "default_edges": [
            {"source": "mirror_registry", "target": "offline_clusters", "label": "release / image sync"},
            {"source": "offline_network", "target": "mirror_registry", "label": "controlled transfer"},
            {"source": "offline_security", "target": "offline_clusters", "label": "policy / trust"},
            {"source": "offline_clusters", "target": "offline_ops", "label": "operations evidence"},
        ],
    },
    {
        "id": "gitops-delivery",
        "label": "GitOps and platform delivery",
        "category": "Delivery",
        "description": "GitOps, Tekton, image streams, and promotion lanes for OpenShift platform teams.",
        "prompt": "Create an OpenShift delivery architecture with GitOps, Tekton, image management, promotion controls, rollback, and operational feedback.",
        "mode": "hybrid",
        "skills": ["GitOps", "Tekton", "Delivery", "Rollback"],
        "default_nodes": [
            {"node_id": "source_control", "label": "Source and environment repos", "group": "context", "detail": "Application, platform, and environment configuration repositories."},
            {"node_id": "tekton", "label": "Tekton pipelines", "group": "delivery", "detail": "Build, test, sign, and promote application artifacts."},
            {"node_id": "argocd", "label": "OpenShift GitOps / Argo CD", "group": "delivery", "detail": "Declarative sync, drift control, and promotion between environments."},
            {"node_id": "delivery_clusters", "label": "Target clusters / namespaces", "group": "workload", "detail": "Application environments receiving promoted manifests and images."},
            {"node_id": "delivery_ops", "label": "Delivery observability", "group": "operations", "detail": "Pipeline health, deployment traceability, and rollback visibility."},
        ],
        "default_edges": [
            {"source": "source_control", "target": "tekton", "label": "commit / pipeline trigger"},
            {"source": "tekton", "target": "argocd", "label": "signed artifact / manifest"},
            {"source": "argocd", "target": "delivery_clusters", "label": "sync / rollout"},
            {"source": "delivery_clusters", "target": "delivery_ops", "label": "release telemetry"},
        ],
    },
    {
        "id": "security-governance",
        "label": "Security and governance",
        "category": "Security",
        "description": "Identity, SCC, RBAC, network policy, ACS, and governance coverage for OpenShift estates.",
        "prompt": "Create an OpenShift security architecture with OAuth or LDAP identity, SCC, RBAC, network policy, ACS, ACM governance, admission policy, audit, and evidence handling.",
        "mode": "hybrid",
        "skills": ["Security", "Governance", "RBAC", "ACS"],
        "default_nodes": [
            {"node_id": "identity", "label": "Identity and access", "group": "security", "detail": "OAuth, LDAP, SSO, service accounts, and RBAC posture."},
            {"node_id": "policy_controls", "label": "Admission and policy controls", "group": "security", "detail": "SCC, admission webhooks, policy engines, quota, and limit ranges."},
            {"node_id": "runtime_security", "label": "Runtime and compliance", "group": "security", "detail": "ACS, audit, findings, and evidence collection."},
            {"node_id": "governed_clusters", "label": "Governed clusters and namespaces", "group": "control-plane", "detail": "Cluster and namespace scope under security and governance controls."},
            {"node_id": "security_ops", "label": "Security operations", "group": "operations", "detail": "Alert routing, evidence, and remediation workflow."},
        ],
        "default_edges": [
            {"source": "identity", "target": "governed_clusters", "label": "access control"},
            {"source": "policy_controls", "target": "governed_clusters", "label": "admission / guardrails"},
            {"source": "runtime_security", "target": "security_ops", "label": "findings / evidence"},
            {"source": "governed_clusters", "target": "security_ops", "label": "audit / telemetry"},
        ],
    },
    {
        "id": "observability-logging",
        "label": "Observability and logging",
        "category": "Operations",
        "description": "Monitoring, logging, alert routing, and SRE operating model for OpenShift.",
        "prompt": "Create an OpenShift observability architecture with monitoring, Alertmanager, logging, traces or event pipelines, runbooks, and ownership boundaries.",
        "mode": "hybrid",
        "skills": ["Monitoring", "Logging", "Alerting", "SRE"],
        "default_nodes": [
            {"node_id": "signals", "label": "Metrics, logs, events", "group": "operations", "detail": "Application, node, platform, and security telemetry."},
            {"node_id": "monitoring", "label": "Prometheus / Alertmanager", "group": "operations", "detail": "Monitoring stack, alert rules, and escalation channels."},
            {"node_id": "logging", "label": "Cluster logging", "group": "operations", "detail": "Log collection, retention, forwarding, and search."},
            {"node_id": "runbooks", "label": "Runbooks and SRE workflow", "group": "operations", "detail": "Response procedures, handoff, and operational ownership."},
            {"node_id": "observed_clusters", "label": "Observed clusters and workloads", "group": "control-plane", "detail": "Sources of platform and application telemetry."},
        ],
        "default_edges": [
            {"source": "observed_clusters", "target": "signals", "label": "emit telemetry"},
            {"source": "signals", "target": "monitoring", "label": "metrics / alerts"},
            {"source": "signals", "target": "logging", "label": "logs / events"},
            {"source": "monitoring", "target": "runbooks", "label": "incident handoff"},
        ],
    },
    {
        "id": "virtualization-cnv",
        "label": "OpenShift Virtualization / CNV",
        "category": "Virtualization",
        "description": "KubeVirt, HyperConverged, VM workloads, snapshots, and migration flows.",
        "prompt": "Create an OpenShift Virtualization architecture with CNV control plane, VM workloads, snapshot protection, storage, network, and migration safety.",
        "mode": "hybrid",
        "skills": ["CNV", "KubeVirt", "VMs", "Snapshots"],
        "default_nodes": [
            {"node_id": "cnv_control", "label": "CNV control plane", "group": "control-plane", "detail": "KubeVirt, HyperConverged, and virtualization operators."},
            {"node_id": "vm_workloads", "label": "Virtual machine workloads", "group": "workload", "detail": "VMs, DataVolumes, live migration, and app services."},
            {"node_id": "vm_storage", "label": "VM storage and protection", "group": "data", "detail": "Persistent storage, snapshots, restore, and image sources."},
            {"node_id": "vm_network", "label": "VM networking and exposure", "group": "network", "detail": "Ingress, service networking, and east-west traffic."},
            {"node_id": "vm_ops", "label": "Virtualization operations", "group": "operations", "detail": "Capacity, migration monitoring, and platform health."},
        ],
        "default_edges": [
            {"source": "cnv_control", "target": "vm_workloads", "label": "virtualization runtime"},
            {"source": "vm_workloads", "target": "vm_storage", "label": "disks / snapshots"},
            {"source": "vm_network", "target": "vm_workloads", "label": "connectivity"},
            {"source": "vm_workloads", "target": "vm_ops", "label": "health / migration"},
        ],
    },
    {
        "id": "backup-dr",
        "label": "Backup and disaster recovery",
        "category": "Resilience",
        "description": "OADP, snapshots, ACM DR, replication, and recovery operations.",
        "prompt": "Create an OpenShift DR architecture with OADP, snapshots, replication, ACM or ODF DR controls, failover sequencing, and recovery operations.",
        "mode": "hybrid",
        "skills": ["OADP", "DR", "Backup", "Recovery"],
        "default_nodes": [
            {"node_id": "primary_site", "label": "Primary clusters / workloads", "group": "control-plane", "detail": "Primary production runtime and services."},
            {"node_id": "backup_plane", "label": "Backup and restore plane", "group": "data", "detail": "OADP, Velero, snapshots, backup storage, and restore workflow."},
            {"node_id": "dr_plane", "label": "Failover and replication controls", "group": "fleet", "detail": "DR policies, placement, replication, and failover orchestration."},
            {"node_id": "recovery_site", "label": "Recovery clusters / target site", "group": "control-plane", "detail": "Standby or recovery runtime with workload restore or relocation targets."},
            {"node_id": "dr_ops", "label": "Recovery operations", "group": "operations", "detail": "Runbooks, exercises, evidence, and failback decisions."},
        ],
        "default_edges": [
            {"source": "primary_site", "target": "backup_plane", "label": "backup / snapshot"},
            {"source": "primary_site", "target": "dr_plane", "label": "replication"},
            {"source": "dr_plane", "target": "recovery_site", "label": "failover / relocate"},
            {"source": "recovery_site", "target": "dr_ops", "label": "validation"},
        ],
    },
    {
        "id": "migration-factory",
        "label": "Migration and modernization factory",
        "category": "Migration",
        "description": "Wave-based migration into OpenShift with MTC, CNV, GitOps, and platform prerequisites.",
        "prompt": "Create an OpenShift migration architecture with discovery, readiness, MTC or workload migration, storage, networking, GitOps onboarding, and rollback-safe wave execution.",
        "mode": "hybrid",
        "skills": ["Migration", "MTC", "Waves", "Modernization"],
        "default_nodes": [
            {"node_id": "source_estate", "label": "Source estate", "group": "context", "detail": "Legacy platforms, VMs, namespaces, apps, and dependencies."},
            {"node_id": "factory", "label": "Migration factory", "group": "delivery", "detail": "Wave planning, readiness checks, migration tooling, and change gates."},
            {"node_id": "target_clusters", "label": "Target OpenShift clusters", "group": "control-plane", "detail": "Landing platform with clusters, namespaces, and platform services."},
            {"node_id": "migration_data", "label": "Data and storage migration", "group": "data", "detail": "Volumes, snapshots, replication, and data-cutover controls."},
            {"node_id": "migration_ops", "label": "Cutover and hypercare", "group": "operations", "detail": "Validation, rollback criteria, and support handoff."},
        ],
        "default_edges": [
            {"source": "source_estate", "target": "factory", "label": "inventory / wave plan"},
            {"source": "factory", "target": "target_clusters", "label": "migration execution"},
            {"source": "migration_data", "target": "target_clusters", "label": "state transfer"},
            {"source": "target_clusters", "target": "migration_ops", "label": "validation / hypercare"},
        ],
    },
]
TEMPLATE_LOOKUP = {item["id"]: item for item in ARCHITECT_DIAGRAM_TEMPLATES}
PATTERN_RULES = [
    ("airgapped-disconnected", ["airgap", "air-gap", "disconnected", "mirror registry", "offline"]),
    ("multicluster-fleet", ["multicluster", "fleet", "acm", "managed cluster", "hub"]),
    ("gitops-delivery", ["gitops", "argocd", "argo cd", "tekton", "pipeline", "cicd", "ci/cd"]),
    ("security-governance", ["acs", "security", "rbac", "scc", "network policy", "governance", "oauth", "ldap"]),
    ("observability-logging", ["observability", "monitoring", "logging", "alertmanager", "prometheus", "runbook"]),
    ("virtualization-cnv", ["virtualization", "cnv", "kubevirt", "virtual machine", "vm snapshot"]),
    ("backup-dr", ["disaster recovery", "failover", "oadp", "backup", "restore", "replication", "dr"]),
    ("migration-factory", ["migration", "mtc", "move", "modernization", "wave", "cutover"]),
]
OPENSHIFT_STATE_FEATURES = [
    ("identity", "get_cluster_identity"),
    ("infrastructure", "list_cluster_infrastructure"),
    ("projects", "list_projects"),
    ("cluster_version", "list_cluster_version"),
    ("cluster_operators", "list_cluster_operators"),
    ("network", "list_cluster_network_config"),
    ("ingress", "list_ingress_controllers"),
    ("nodes", "list_nodes"),
    ("pods", "list_pods"),
    ("storage", "list_persistent_storage"),
    ("subscriptions", "list_operator_subscriptions"),
    ("gitops", "list_gitops_argocds"),
    ("logging", "list_cluster_logging"),
    ("oadp", "list_oadp_resources"),
    ("acm", "list_acm_managed_clusters"),
    ("virtualization", "list_virtualization_resources"),
    ("disaster_recovery", "list_disaster_recovery_resources"),
]


@dataclass(slots=True)
class DiagramNode:
    node_id: str
    label: str
    group: str
    detail: str = ""


@dataclass(slots=True)
class DiagramEdge:
    source: str
    target: str
    label: str = ""


@dataclass(slots=True)
class PromptNormalization:
    pattern_id: str
    pattern_label: str
    normalized_prompt: str
    reasoning_summary: str
    confidence: str


@dataclass(slots=True)
class ClarificationQuestion:
    question_id: str
    title: str
    question: str
    rationale: str = ""
    placeholder: str = ""


def get_architect_diagram_templates() -> list[dict[str, Any]]:
    return ARCHITECT_DIAGRAM_TEMPLATES


def get_architect_assessment_scopes() -> list[dict[str, str]]:
    return ARCHITECT_ASSESSMENT_SCOPES


def _slugify(value: str, fallback: str = "node") -> str:
    normalized = re.sub(r"[^a-z0-9]+", "_", str(value or "").strip().lower()).strip("_")
    return normalized or fallback


def _pattern_label(pattern_id: str) -> str:
    return str(TEMPLATE_LOOKUP.get(pattern_id, TEMPLATE_LOOKUP["custom"])["label"])


def _normalize_pattern_id(pattern_id: str | None) -> str:
    candidate = str(pattern_id or "custom").strip()
    return candidate if candidate in TEMPLATE_LOOKUP else "custom"


def _detect_pattern(prompt: str, openshift_state: dict[str, Any] | None = None) -> str:
    prompt_lower = f" {(prompt or '').lower()} "
    for pattern_id, tokens in PATTERN_RULES:
        if any(token in prompt_lower for token in tokens):
            return pattern_id
    counts = (openshift_state or {}).get("resource_counts") or {}
    if int(counts.get("managed_clusters", 0) or 0) > 1:
        return "multicluster-fleet"
    if int(counts.get("virtual_machines", 0) or 0) > 0:
        return "virtualization-cnv"
    if int(counts.get("backup_locations", 0) or 0) > 0 or int(counts.get("dr_policies", 0) or 0) > 0:
        return "backup-dr"
    if int(counts.get("argocd_instances", 0) or 0) > 0 or int(counts.get("tekton_configs", 0) or 0) > 0:
        return "gitops-delivery"
    return "custom"


def _normalize_prompt(pattern_id: str, prompt: str) -> PromptNormalization:
    template = TEMPLATE_LOOKUP[_normalize_pattern_id(pattern_id)]
    normalized_prompt = f"{template['prompt']} Preserve the operator's original OpenShift goals and constraints: {prompt.strip()}".strip()
    confidence = "high" if pattern_id != "custom" else "medium"
    reasoning_summary = (
        f"Detected the {template['label']} pattern from the prompt and/or live OpenShift signals."
        if pattern_id != "custom"
        else "Using the custom OpenShift architecture pattern because the prompt does not strongly match a named template."
    )
    return PromptNormalization(
        pattern_id=pattern_id,
        pattern_label=str(template["label"]),
        normalized_prompt=normalized_prompt,
        reasoning_summary=reasoning_summary,
        confidence=confidence,
    )


def _safe_invoke(toolkit: Any, tool_name: str) -> dict[str, Any]:
    try:
        if hasattr(toolkit, "tools") and tool_name not in getattr(toolkit, "tools", {}):
            return {"error": f"Tool not available: {tool_name}"}
        if hasattr(toolkit, "invoke"):
            return toolkit.invoke(tool_name, {})
        handler = getattr(toolkit, tool_name)
        return handler()
    except Exception as error:  # noqa: BLE001
        return {"error": str(error)}


def _first_row(payload: dict[str, Any], keys: list[str]) -> dict[str, Any]:
    for key in keys:
        rows = payload.get(key)
        if isinstance(rows, list) and rows:
            first = rows[0]
            if isinstance(first, dict):
                return first
    return {}


def _extract_resource_counts(collected: dict[str, Any]) -> dict[str, int]:
    counts = {
        "projects": int(collected.get("projects", {}).get("count", 0) or 0),
        "degraded_operators": int(collected.get("cluster_operators", {}).get("degraded_count", 0) or 0),
        "ingress_controllers": int(collected.get("ingress", {}).get("count", 0) or 0),
        "nodes": int(collected.get("nodes", {}).get("count", 0) or 0),
        "risky_pods": int(collected.get("pods", {}).get("risky_pod_count", 0) or 0),
        "persistent_volume_claims": int(collected.get("storage", {}).get("pvc_count", 0) or 0),
        "pending_pvcs": int(collected.get("storage", {}).get("pending_pvc_count", 0) or 0),
        "managed_clusters": int(collected.get("acm", {}).get("count", 0) or 0),
        "argocd_instances": int(collected.get("gitops", {}).get("count", 0) or 0),
        "backup_locations": int(collected.get("oadp", {}).get("backup_storage_location_count", 0) or 0),
        "dr_policies": int(collected.get("disaster_recovery", {}).get("dr_policy_count", 0) or 0),
        "virtual_machines": int(collected.get("virtualization", {}).get("virtual_machine_count", 0) or 0),
    }
    return counts


def collect_architecture_state(toolkit: Any) -> dict[str, Any]:
    collected: dict[str, Any] = {}
    for state_key, tool_name in OPENSHIFT_STATE_FEATURES:
        collected[state_key] = _safe_invoke(toolkit, tool_name)

    identity = collected.get("identity") or {}
    infrastructure = _first_row(collected.get("infrastructure") or {}, ["cluster_infrastructure"])
    version = _first_row(collected.get("cluster_version") or {}, ["cluster_versions"])
    resource_counts = _extract_resource_counts(collected)

    summaries = []
    if infrastructure.get("platform_pattern"):
        summaries.append(f"Platform pattern: {infrastructure['platform_pattern']}")
    if version.get("version"):
        summaries.append(f"Cluster version: {version['version']}")
    if resource_counts.get("managed_clusters"):
        summaries.append(f"Managed clusters: {resource_counts['managed_clusters']}")
    if resource_counts.get("degraded_operators"):
        summaries.append(f"Degraded operators: {resource_counts['degraded_operators']}")
    if resource_counts.get("argocd_instances"):
        summaries.append(f"GitOps instances: {resource_counts['argocd_instances']}")
    if resource_counts.get("backup_locations") or resource_counts.get("dr_policies"):
        summaries.append(
            f"DR signals: backups={resource_counts.get('backup_locations', 0)} / policies={resource_counts.get('dr_policies', 0)}"
        )

    return {
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "cluster": identity.get("cluster_name") or identity.get("cluster") or "openshift-cluster",
        "cluster_context": identity.get("kube_context") or identity.get("current_context"),
        "platform_pattern": infrastructure.get("platform_pattern") or infrastructure.get("platform_type") or "OpenShift platform",
        "resource_counts": resource_counts,
        "summary": "; ".join(summaries) if summaries else "Live OpenShift topology was collected for the architect workspace.",
        "raw": collected,
    }


def suggest_architecture_clarifications(*, prompt: str, openshift_state: dict[str, Any] | None) -> dict[str, Any]:
    pattern_id = _detect_pattern(prompt, openshift_state)
    planning = _normalize_prompt(pattern_id, prompt)
    prompt_lower = (prompt or "").lower()
    questions: list[ClarificationQuestion] = []

    if pattern_id == "airgapped-disconnected":
        if not any(token in prompt_lower for token in ["registry", "quay", "mirror"]):
            questions.append(
                ClarificationQuestion(
                    question_id="mirror_registry",
                    title="Registry and content mirroring",
                    question="Which mirrored registry, operator catalog, and release-content sources should the disconnected design use?",
                    rationale="Disconnected OpenShift designs are far more useful when they reflect the actual mirror and content-sync path instead of a generic placeholder.",
                    placeholder="Example: Quay mirror in the management zone, weekly release sync, mirrored certified operators only.",
                )
            )
        if not any(token in prompt_lower for token in ["proxy", "bastion", "jump", "transfer"]):
            questions.append(
                ClarificationQuestion(
                    question_id="airgap_transfer",
                    title="Controlled transfer path",
                    question="What controlled transfer or break-glass path should I show for moving content, patches, and support bundles into or out of the air-gapped environment?",
                    rationale="Supportability and governance live or die on the controlled transfer path in disconnected estates.",
                    placeholder="Example: bastion in staging zone plus removable-media approval flow and offline bundle scan.",
                )
            )
    if pattern_id in {"multicluster-fleet", "backup-dr", "migration-factory"} and not any(token in prompt_lower for token in ["hub", "spoke", "primary", "secondary", "prod", "dr", "fleet"]):
        questions.append(
            ClarificationQuestion(
                question_id="cluster_roles",
                title="Cluster roles and environments",
                question="What cluster roles or environment labels should I use for the main clusters in this design?",
                rationale="Cluster role names help the HLD and LLD explain who does what across primary, DR, hub, edge, and workload clusters.",
                placeholder="Example: acm-hub, prod-east, prod-west, dr-west, edge-factory, sandbox.",
            )
        )
    if not any(token in prompt_lower for token in ["ingress", "route", "dns", "load balancer"]):
        questions.append(
            ClarificationQuestion(
                question_id="ingress_model",
                title="Ingress and exposure model",
                question="What ingress pattern should I show for this OpenShift design: internal-only, internet-facing, API-only, private WAN, or mixed?",
                rationale="Ingress assumptions affect the topology, trust boundaries, and the document narrative immediately.",
                placeholder="Example: internet-facing apps through F5 + DNS, platform APIs private only, east-west traffic via service mesh.",
            )
        )
    if not any(token in prompt_lower for token in ["storage", "snapshot", "backup", "restore"]):
        questions.append(
            ClarificationQuestion(
                question_id="storage_protection",
                title="Storage and protection",
                question="What storage, snapshot, or backup expectations should I include in the architecture?",
                rationale="HLD and LLD packages are much stronger when storage and restore posture are explicit instead of implied.",
                placeholder="Example: ODF for app data, CSI snapshots, OADP to S3-compatible storage, quarterly restore test.",
            )
        )
    if not any(token in prompt_lower for token in ["rto", "rpo", "failover", "recovery", "restore"]):
        questions.append(
            ClarificationQuestion(
                question_id="recovery_targets",
                title="Recovery targets",
                question="Should the design include explicit RTO/RPO, failover, or recovery-state expectations?",
                rationale="Recovery objectives change the architecture and the review language for both HLD and LLD outputs.",
                placeholder="Example: RTO 4h, RPO 30m, warm standby cluster, relocate stateful apps only after storage sync health is green.",
            )
        )

    return {
        "needs_clarification": bool(questions),
        "planning": asdict(planning),
        "summary": (
            "This prompt can already produce an OpenShift architecture pack. Answer the questions below if you want a more implementation-ready HLD or LLD."
            if questions
            else "The current prompt already has enough detail for the OpenShift architect workspace to proceed."
        ),
        "questions": [asdict(question) for question in questions[:4]],
    }


def _unique_nodes(nodes: list[DiagramNode]) -> list[DiagramNode]:
    seen: set[str] = set()
    unique: list[DiagramNode] = []
    for node in nodes:
        if node.node_id in seen:
            continue
        seen.add(node.node_id)
        unique.append(node)
    return unique


def _edge_key(edge: DiagramEdge) -> tuple[str, str, str]:
    return edge.source, edge.target, edge.label


def _unique_edges(edges: list[DiagramEdge]) -> list[DiagramEdge]:
    seen: set[tuple[str, str, str]] = set()
    unique: list[DiagramEdge] = []
    for edge in edges:
        key = _edge_key(edge)
        if key in seen:
            continue
        seen.add(key)
        unique.append(edge)
    return unique


def _live_state_nodes(openshift_state: dict[str, Any] | None) -> tuple[list[DiagramNode], list[DiagramEdge], list[str]]:
    if not openshift_state:
        return [], [], []
    raw = openshift_state.get("raw") or {}
    counts = openshift_state.get("resource_counts") or {}
    nodes: list[DiagramNode] = []
    edges: list[DiagramEdge] = []
    summaries: list[str] = []

    infra = _first_row(raw.get("infrastructure") or {}, ["cluster_infrastructure"])
    if infra:
        nodes.append(DiagramNode("live_platform", infra.get("platform_pattern") or "Platform pattern", "context", f"Live platform pattern: {infra.get('platform_pattern') or infra.get('platform_type') or 'OpenShift'}"))
        summaries.append(f"Live platform pattern: {infra.get('platform_pattern') or infra.get('platform_type') or 'OpenShift'}")

    if int(counts.get("managed_clusters", 0) or 0) > 0:
        nodes.append(DiagramNode("live_fleet", "Managed cluster fleet", "fleet", f"{counts.get('managed_clusters', 0)} managed cluster(s) discovered."))
        edges.append(DiagramEdge("live_platform", "live_fleet", "fleet posture"))
        summaries.append(f"Managed clusters discovered: {counts.get('managed_clusters', 0)}")

    if int(counts.get("ingress_controllers", 0) or 0) > 0:
        nodes.append(DiagramNode("live_ingress", "Ingress controllers", "network", f"{counts.get('ingress_controllers', 0)} ingress controller(s) discovered."))
        summaries.append(f"Ingress controllers: {counts.get('ingress_controllers', 0)}")

    if int(counts.get("degraded_operators", 0) or 0) > 0:
        nodes.append(DiagramNode("live_operators", "Operator risk", "control-plane", f"{counts.get('degraded_operators', 0)} degraded operator(s) need review."))
        summaries.append(f"Degraded operators: {counts.get('degraded_operators', 0)}")

    if int(counts.get("argocd_instances", 0) or 0) > 0:
        nodes.append(DiagramNode("live_gitops", "GitOps instances", "delivery", f"{counts.get('argocd_instances', 0)} Argo CD instance(s) discovered."))
        summaries.append(f"GitOps instances: {counts.get('argocd_instances', 0)}")

    if int(counts.get("persistent_volume_claims", 0) or 0) > 0:
        nodes.append(DiagramNode("live_storage", "Persistent storage", "data", f"PVCs: {counts.get('persistent_volume_claims', 0)}; pending: {counts.get('pending_pvcs', 0)}."))
        summaries.append(f"PVCs: {counts.get('persistent_volume_claims', 0)}")

    if int(counts.get("backup_locations", 0) or 0) > 0 or int(counts.get("dr_policies", 0) or 0) > 0:
        nodes.append(DiagramNode("live_dr", "Backup and DR posture", "operations", f"Backup locations: {counts.get('backup_locations', 0)}; DR policies: {counts.get('dr_policies', 0)}."))
        summaries.append(f"Backup / DR posture: backups={counts.get('backup_locations', 0)}, policies={counts.get('dr_policies', 0)}")

    if int(counts.get("virtual_machines", 0) or 0) > 0:
        nodes.append(DiagramNode("live_vm", "Virtual machine estate", "workload", f"{counts.get('virtual_machines', 0)} virtual machine(s) discovered."))
        summaries.append(f"Virtual machines: {counts.get('virtual_machines', 0)}")

    for candidate in ["live_fleet", "live_ingress", "live_operators", "live_gitops", "live_storage", "live_dr", "live_vm"]:
        if any(node.node_id == candidate for node in nodes):
            edges.append(DiagramEdge("live_platform", candidate, "live posture"))

    return nodes, edges, summaries


def _keyword_nodes(prompt: str) -> tuple[list[DiagramNode], list[DiagramEdge]]:
    prompt_lower = (prompt or "").lower()
    mappings = [
        ("acm", DiagramNode("keyword_acm", "ACM governance", "fleet", "Fleet governance, placement, and policy orchestration."), DiagramEdge("keyword_acm", "fleet_ops", "fleet governance")),
        ("acs", DiagramNode("keyword_acs", "ACS", "security", "Runtime security, policy, and findings management."), DiagramEdge("keyword_acs", "security_ops", "security findings")),
        ("gitops", DiagramNode("keyword_gitops", "GitOps", "delivery", "Declarative delivery, sync, and drift control."), DiagramEdge("keyword_gitops", "delivery_clusters", "delivery flow")),
        ("tekton", DiagramNode("keyword_tekton", "Tekton", "delivery", "Pipeline execution and promotion controls."), DiagramEdge("keyword_tekton", "delivery_clusters", "pipeline delivery")),
        ("logging", DiagramNode("keyword_logging", "Cluster logging", "operations", "Collector, retention, forwarding, and search."), DiagramEdge("keyword_logging", "runbooks", "incident evidence")),
        ("oadp", DiagramNode("keyword_oadp", "OADP / Velero", "data", "Backup orchestration and restore flows."), DiagramEdge("keyword_oadp", "dr_ops", "recovery evidence")),
        ("virtualization", DiagramNode("keyword_virtualization", "KubeVirt / CNV", "workload", "Virtual machine runtime and migration safety."), DiagramEdge("keyword_virtualization", "vm_ops", "virtualization telemetry")),
    ]
    nodes: list[DiagramNode] = []
    edges: list[DiagramEdge] = []
    for token, node, edge in mappings:
        if token in prompt_lower:
            nodes.append(node)
            edges.append(edge)
    return nodes, edges


def _build_nodes_and_edges(prompt: str, openshift_state: dict[str, Any] | None) -> tuple[PromptNormalization, list[DiagramNode], list[DiagramEdge], list[str]]:
    pattern_id = _detect_pattern(prompt, openshift_state)
    planning = _normalize_prompt(pattern_id, prompt)
    template = TEMPLATE_LOOKUP[pattern_id]
    nodes = [DiagramNode(**item) for item in template.get("default_nodes", [])]
    edges = [DiagramEdge(**item) for item in template.get("default_edges", [])]
    live_nodes, live_edges, live_summaries = _live_state_nodes(openshift_state)
    keyword_nodes, keyword_edges = _keyword_nodes(prompt)
    nodes.extend(live_nodes)
    nodes.extend(keyword_nodes)
    edges.extend(live_edges)
    edges.extend(keyword_edges)
    return planning, _unique_nodes(nodes), _unique_edges(edges), live_summaries


def _layout_nodes(nodes: list[DiagramNode]) -> tuple[dict[str, dict[str, float]], dict[str, dict[str, float]], float, float]:
    grouped: dict[str, list[DiagramNode]] = {group: [] for group in GROUP_ORDER}
    for node in nodes:
        grouped.setdefault(node.group, []).append(node)
    group_boxes: dict[str, dict[str, float]] = {}
    positions: dict[str, dict[str, float]] = {}
    x = 60.0
    column_width = 250.0
    group_gap = 36.0
    node_width = 210.0
    node_height = 74.0
    vertical_gap = 18.0
    max_bottom = 120.0

    for group in GROUP_ORDER:
        group_nodes = grouped.get(group) or []
        if not group_nodes:
            continue
        y = 110.0
        for node in group_nodes:
            positions[node.node_id] = {"x": x + 20.0, "y": y, "width": node_width, "height": node_height}
            y += node_height + vertical_gap
        group_boxes[group] = {
            "x": x,
            "y": 60.0,
            "width": column_width,
            "height": max(180.0, y - 60.0),
        }
        max_bottom = max(max_bottom, group_boxes[group]["y"] + group_boxes[group]["height"])
        x += column_width + group_gap

    total_width = max(1280.0, x)
    total_height = max(720.0, max_bottom + 60.0)
    return positions, group_boxes, total_width, total_height


def _wrap_text(value: str, max_chars: int = 26) -> list[str]:
    words = str(value or "").split()
    if not words:
        return [""]
    lines: list[str] = []
    current = words[0]
    for word in words[1:]:
        candidate = f"{current} {word}"
        if len(candidate) <= max_chars:
            current = candidate
            continue
        lines.append(current)
        current = word
    lines.append(current)
    return lines[:4]


def _render_svg(title: str, summary: str, nodes: list[DiagramNode], edges: list[DiagramEdge], positions: dict[str, dict[str, float]], group_boxes: dict[str, dict[str, float]], total_width: float, total_height: float) -> str:
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{int(total_width)}" height="{int(total_height)}" viewBox="0 0 {int(total_width)} {int(total_height)}">',
        '<rect width="100%" height="100%" fill="#F8FAFC"/>',
        f'<text x="48" y="36" font-size="24" font-weight="700" fill="#0F172A">{escape(title)}</text>',
        f'<text x="48" y="56" font-size="12" fill="#475569">{escape(summary)}</text>',
    ]
    for group, box in group_boxes.items():
        style = GROUP_STYLES[group]
        parts.append(
            f'<rect x="{box["x"]}" y="{box["y"]}" width="{box["width"]}" height="{box["height"]}" rx="18" fill="{style["fill"]}" fill-opacity="0.55" stroke="{style["stroke"]}" stroke-width="2"/>'
        )
        parts.append(
            f'<text x="{box["x"] + 16}" y="{box["y"] + 26}" font-size="14" font-weight="700" fill="#0F172A">{escape(GROUP_LABELS.get(group, group.title()))}</text>'
        )

    for edge in edges:
        source = positions.get(edge.source)
        target = positions.get(edge.target)
        if not source or not target:
            continue
        sx = source["x"] + source["width"]
        sy = source["y"] + (source["height"] / 2)
        tx = target["x"]
        ty = target["y"] + (target["height"] / 2)
        mx = (sx + tx) / 2
        parts.append(f'<path d="M {sx} {sy} C {mx} {sy}, {mx} {ty}, {tx} {ty}" fill="none" stroke="#64748B" stroke-width="2"/>')
        if edge.label:
            lx = mx
            ly = ((sy + ty) / 2) - 6
            parts.append(f'<text x="{lx}" y="{ly}" font-size="11" text-anchor="middle" fill="#334155">{escape(edge.label)}</text>')

    for node in nodes:
        position = positions[node.node_id]
        style = GROUP_STYLES.get(node.group, {"fill": "#FFFFFF", "stroke": "#94A3B8"})
        parts.append(
            f'<rect x="{position["x"]}" y="{position["y"]}" width="{position["width"]}" height="{position["height"]}" rx="14" fill="#FFFFFF" stroke="{style["stroke"]}" stroke-width="2"/>'
        )
        title_lines = _wrap_text(node.label, 24)
        for index, line in enumerate(title_lines):
            parts.append(
                f'<text x="{position["x"] + 12}" y="{position["y"] + 24 + (index * 15)}" font-size="13" font-weight="700" fill="#0F172A">{escape(line)}</text>'
            )
        detail_lines = _wrap_text(node.detail, 30)
        for index, line in enumerate(detail_lines[:2]):
            parts.append(
                f'<text x="{position["x"] + 12}" y="{position["y"] + 52 + (index * 13)}" font-size="11" fill="#475569">{escape(line)}</text>'
            )
    parts.append('</svg>')
    return ''.join(parts)


def _drawio_text(value: str) -> str:
    return escape(value).replace("\n", "&#xa;")


def _build_drawio_xml(title: str, nodes: list[DiagramNode], edges: list[DiagramEdge], positions: dict[str, dict[str, float]], group_boxes: dict[str, dict[str, float]], total_width: float, total_height: float) -> str:
    mxfile = ET.Element("mxfile", host="app.diagrams.net", modified=datetime.now(timezone.utc).isoformat(), agent="openshift-sre-architect", version="24.7.17")
    diagram = ET.SubElement(mxfile, "diagram", id="openshift-architect", name=title)
    graph_model = ET.SubElement(diagram, "mxGraphModel", dx="1200", dy="700", grid="1", gridSize="10", guides="1", tooltips="1", connect="1", arrows="1", fold="1", page="1", pageScale="1", pageWidth=str(int(total_width)), pageHeight=str(int(total_height)), math="0", shadow="0")
    root = ET.SubElement(graph_model, "root")
    ET.SubElement(root, "mxCell", id="0")
    ET.SubElement(root, "mxCell", id="1", parent="0")

    cell_counter = 2
    group_ids: dict[str, str] = {}
    node_ids: dict[str, str] = {}

    for group, box in group_boxes.items():
        style = GROUP_STYLES[group]
        group_id = str(cell_counter)
        cell_counter += 1
        group_ids[group] = group_id
        group_cell = ET.SubElement(root, "mxCell", id=group_id, value=_drawio_text(GROUP_LABELS.get(group, group.title())), style=f"rounded=1;whiteSpace=wrap;html=1;fillColor={style['fill']};strokeColor={style['stroke']};fontStyle=1;fontSize=14;align=left;verticalAlign=top;spacingTop=8;spacingLeft=12;", vertex="1", parent="1")
        ET.SubElement(group_cell, "mxGeometry", x=str(box["x"]), y=str(box["y"]), width=str(box["width"]), height=str(box["height"]), as_="geometry")

    for node in nodes:
        position = positions[node.node_id]
        cell_id = str(cell_counter)
        cell_counter += 1
        node_ids[node.node_id] = cell_id
        style = GROUP_STYLES.get(node.group, {"stroke": "#94A3B8"})
        value = _drawio_text(f"{node.label}\n{node.detail}")
        node_cell = ET.SubElement(root, "mxCell", id=cell_id, value=value, style=f"rounded=1;whiteSpace=wrap;html=1;fillColor=#ffffff;strokeColor={style['stroke']};fontSize=12;fontStyle=1;spacing=8;", vertex="1", parent="1")
        ET.SubElement(node_cell, "mxGeometry", x=str(position["x"]), y=str(position["y"]), width=str(position["width"]), height=str(position["height"]), as_="geometry")

    for edge in edges:
        source_id = node_ids.get(edge.source)
        target_id = node_ids.get(edge.target)
        if not source_id or not target_id:
            continue
        edge_id = str(cell_counter)
        cell_counter += 1
        edge_cell = ET.SubElement(root, "mxCell", id=edge_id, value=_drawio_text(edge.label), style="edgeStyle=orthogonalEdgeStyle;rounded=0;orthogonalLoop=1;jettySize=auto;html=1;strokeColor=#64748B;fontSize=11;endArrow=block;endFill=1;", edge="1", parent="1", source=source_id, target=target_id)
        ET.SubElement(edge_cell, "mxGeometry", relative="1", as_="geometry")

    return ET.tostring(mxfile, encoding="unicode")


def _export_with_drawio(drawio_xml: str, extension: str) -> bytes | None:
    binary = shutil.which("drawio") or shutil.which("draw.io")
    if not binary:
        return None
    with TemporaryDirectory() as tmp_dir:
        input_path = Path(tmp_dir) / "diagram.drawio"
        output_path = Path(tmp_dir) / f"diagram.{extension}"
        input_path.write_text(drawio_xml, encoding="utf-8")
        command = [binary, "--export", "--format", extension, "--output", str(output_path), str(input_path)]
        if shutil.which("xvfb-run"):
            command = ["xvfb-run", "-a", *command]
        try:
            subprocess.run(command, check=True, capture_output=True, text=True)
        except Exception:  # noqa: BLE001
            return None
        if output_path.exists():
            return output_path.read_bytes()
    return None


def _png_from_svg(svg_markup: str) -> bytes | None:
    if cairosvg is None:
        return None
    try:
        return cairosvg.svg2png(bytestring=svg_markup.encode("utf-8"))
    except Exception:  # noqa: BLE001
        return None


def _assessment_dimensions(nodes: list[DiagramNode], prompt: str, openshift_state: dict[str, Any] | None) -> list[dict[str, Any]]:
    labels = " ".join([node.label.lower() + " " + node.detail.lower() for node in nodes]) + " " + (prompt or "").lower()
    counts = (openshift_state or {}).get("resource_counts") or {}

    def has_any(tokens: list[str]) -> bool:
        return any(token in labels for token in tokens)

    dimensions = [
        {
            "id": "security-governance",
            "label": "Security and governance",
            "assessment": "Security posture is explicit and reviewable." if has_any(["security", "rbac", "scc", "policy", "acs", "oauth", "network policy"]) else "Security posture needs clearer identity, policy, and segmentation detail.",
            "actions": [
                "Document identity providers, privileged access paths, and namespace or fleet governance boundaries.",
                "Make SCC, RBAC, admission policy, and runtime security ownership explicit in the design pack.",
            ],
        },
        {
            "id": "reliability-dr",
            "label": "Reliability and DR",
            "assessment": "Reliability posture includes backup and recovery signals." if has_any(["backup", "restore", "dr", "failover", "snapshot", "replication"]) or int(counts.get("dr_policies", 0) or 0) > 0 else "Reliability posture needs clearer failure-domain, backup, and failover detail.",
            "actions": [
                "Add RTO/RPO, recovery sequencing, backup ownership, and restore-evidence expectations.",
                "Show which clusters, namespaces, or workloads participate in failover or recovery operations.",
            ],
        },
        {
            "id": "platform-operations",
            "label": "Platform operations",
            "assessment": "Operational coverage includes observability and delivery flows." if has_any(["observability", "monitoring", "logging", "gitops", "tekton", "runbook"]) else "Operational coverage needs clearer telemetry, runbook, and day-2 ownership detail.",
            "actions": [
                "Describe monitoring, alert routing, logging, and runbook ownership clearly.",
                "Show GitOps, delivery, and rollback behavior if the architecture includes managed rollout lanes.",
            ],
        },
        {
            "id": "architecture-readiness",
            "label": "Architecture readiness",
            "assessment": "The architecture covers the main OpenShift platform domains." if len(nodes) >= 6 else "The architecture needs more domain coverage before it is ready for formal handoff.",
            "actions": [
                "Expand the pack with explicit environment roles, boundaries, and integration points.",
                "Capture architectural decisions, consequences, and open questions before sign-off.",
            ],
        },
    ]
    return dimensions


def _document_sections(document_type: str, title: str, planning: PromptNormalization, nodes: list[DiagramNode], edges: list[DiagramEdge], prompt: str, openshift_state: dict[str, Any] | None, knowledge_context: dict[str, Any] | None, assessment_scope_id: str = "architecture-readiness") -> dict[str, Any]:
    counts = (openshift_state or {}).get("resource_counts") or {}
    grouped: dict[str, list[DiagramNode]] = {}
    for node in nodes:
        grouped.setdefault(node.group, []).append(node)
    flow_lines = [f"{edge.source} -> {edge.target}{f' ({edge.label})' if edge.label else ''}" for edge in edges]
    knowledge_items = list((knowledge_context or {}).get("items") or [])

    assumptions = [
        planning.reasoning_summary,
        f"Prompt preserved: {prompt.strip() or 'Prompt-free architecture generation based on live OpenShift state.'}",
        f"Live OpenShift state included: {'yes' if openshift_state else 'no'}.",
        f"RAG grounding used: {'yes' if knowledge_items else 'no'}.",
    ]

    decision_rows = [
        {
            "title": "Architecture pattern",
            "decision": f"Use the {planning.pattern_label} pattern as the primary OpenShift reference design.",
            "rationale": "The detected platform pattern aligns the HLD and LLD narrative with a consistent topology, ownership model, and operating story.",
            "consequences": "The final pack can explain platform, security, networking, data, and operations from one coherent reference model.",
        },
        {
            "title": "Boundary-first design",
            "decision": "Describe the platform through explicit cluster, namespace, ingress, security, and operational boundaries.",
            "rationale": "OpenShift handoff quality improves when control-plane, workload, and governance boundaries are explicit instead of implied.",
            "consequences": "Operators and engineering teams can map architecture review findings directly to platform owners and implementation workstreams.",
        },
    ]

    state_views = [
        {
            "title": "Steady-state",
            "summary": "Normal operating posture with control plane, workloads, network entry, and operational visibility in service.",
            "bullets": [
                "Clusters and namespaces operate with the planned ingress, delivery, and governance controls in place.",
                "Monitoring, logging, and operator health provide the baseline operational feedback loop.",
            ],
        },
        {
            "title": "Change and deployment state",
            "summary": "How new releases, platform changes, or cluster lifecycle actions move through the environment.",
            "bullets": [
                "Delivery and GitOps lanes should show how changes are promoted, validated, and rolled back.",
                "Cluster lifecycle and operator dependencies should be reviewed together before major maintenance windows.",
            ],
        },
        {
            "title": "Failure and recovery state",
            "summary": "How the platform behaves during degradation, backup, failover, restore, or incident response.",
            "bullets": [
                "Document degraded operator, workload, network, and storage signals and the first responder workflow.",
                "Capture backup, restore, failover, and validation expectations where the design includes resilience controls.",
            ],
        },
    ]

    dimensions = _assessment_dimensions(nodes, prompt, openshift_state)
    selected_dimensions = dimensions if assessment_scope_id == "architecture-readiness" else [item for item in dimensions if item["id"] == assessment_scope_id]

    sections = [
        {
            "title": "Executive summary",
            "body": [
                f"This {document_type.upper()} pack describes the {title} design using the {planning.pattern_label} OpenShift architecture pattern.",
                f"Live state highlights: degraded operators={counts.get('degraded_operators', 0)}, managed clusters={counts.get('managed_clusters', 0)}, PVCs={counts.get('persistent_volume_claims', 0)}, DR policies={counts.get('dr_policies', 0)}.",
            ],
        },
        {
            "title": "Assumptions and constraints",
            "body": assumptions,
        },
        {
            "title": "Domain decomposition",
            "body": [
                f"{GROUP_LABELS.get(group, group.title())}: " + "; ".join(f"{node.label} — {node.detail}" for node in group_nodes)
                for group, group_nodes in grouped.items()
            ],
        },
        {
            "title": "Flow summary",
            "body": flow_lines or ["The architecture uses implicit relationships derived from the selected pattern."],
        },
        {
            "title": "Architectural decisions",
            "body": [f"{row['title']}: {row['decision']} Rationale: {row['rationale']} Consequence: {row['consequences']}" for row in decision_rows],
        },
        {
            "title": "System-state views",
            "body": [f"{view['title']}: {view['summary']} {' '.join(view['bullets'])}" for view in state_views],
        },
    ]

    if knowledge_items:
        sections.append(
            {
                "title": "Grounding references",
                "body": [
                    f"{item.get('title', 'Knowledge source')} ({item.get('source_type', 'knowledge')}) — {item.get('excerpt', '')}"
                    for item in knowledge_items[:6]
                ],
            }
        )

    if document_type == "assessment":
        sections.append(
            {
                "title": "Assessment findings",
                "body": [f"{item['label']}: {item['assessment']} Actions: {'; '.join(item['actions'])}" for item in selected_dimensions],
            }
        )
    elif document_type == "lld":
        sections.append(
            {
                "title": "Implementation detail",
                "body": [
                    f"Component: {node.label}. Detail: {node.detail}. Recommended owner: {GROUP_LABELS.get(node.group, node.group.title())}."
                    for node in nodes
                ],
            }
        )

    return {
        "document_type": document_type,
        "title": f"{title} — {document_type.upper()}",
        "summary": sections[0]["body"][0],
        "sections": sections,
        "assumptions": assumptions,
        "decision_rows": decision_rows,
        "state_views": state_views,
        "assessment_dimensions": selected_dimensions,
    }


def generate_architecture_diagram(*, prompt: str, openshift_state: dict[str, Any] | None, model_client: Any | None = None, reference_diagrams: list[dict[str, Any]] | None = None, knowledge_context: dict[str, Any] | None = None, require_model: bool = False, assessment_scope_id: str = "architecture-readiness") -> dict[str, Any]:
    if require_model and model_client is not None and hasattr(model_client, "probe"):
        probe = model_client.probe()
        if getattr(probe, "ok", True) is False:
            raise RuntimeError(getattr(probe, "detail", "The selected model is unavailable for this architect run."))

    planning, nodes, edges, live_summaries = _build_nodes_and_edges(prompt, openshift_state)
    positions, group_boxes, total_width, total_height = _layout_nodes(nodes)
    title = f"{planning.pattern_label} architecture"
    summary = live_summaries[0] if live_summaries else planning.reasoning_summary
    drawio_xml = _build_drawio_xml(title, nodes, edges, positions, group_boxes, total_width, total_height)
    svg_preview = _render_svg(title, summary, nodes, edges, positions, group_boxes, total_width, total_height)
    svg_bytes = _export_with_drawio(drawio_xml, "svg")
    png_bytes = _export_with_drawio(drawio_xml, "png")
    if png_bytes is None:
        png_bytes = _png_from_svg(svg_preview)

    documents = {
        "hld": _document_sections("hld", title, planning, nodes, edges, prompt, openshift_state, knowledge_context, assessment_scope_id=assessment_scope_id),
        "lld": _document_sections("lld", title, planning, nodes, edges, prompt, openshift_state, knowledge_context, assessment_scope_id=assessment_scope_id),
        "assessment": _document_sections("assessment", title, planning, nodes, edges, prompt, openshift_state, knowledge_context, assessment_scope_id=assessment_scope_id),
    }
    score = min(100, 58 + (len(nodes) * 3) + (6 if openshift_state else 0) + (4 if knowledge_context and knowledge_context.get("used") else 0))
    quality_scorecard = {
        "overall_score": score,
        "max_score": 100,
        "quality_band": "Solid" if score >= 75 else ("Developing" if score >= 60 else "Needs work"),
        "summary": "OpenShift architecture quality review based on domain coverage, live evidence, and design clarity.",
        "top_gaps": [
            item["question"]
            for item in suggest_architecture_clarifications(prompt=prompt, openshift_state=openshift_state).get("questions", [])[:4]
        ],
    }

    return {
        "planning": asdict(planning),
        "diagram": {
            "title": title,
            "summary": documents["hld"]["summary"],
            "nodes": [asdict(node) for node in nodes],
            "edges": [asdict(edge) for edge in edges],
        },
        "knowledge": knowledge_context or {"enabled": False, "used": False, "items": []},
        "reference_diagrams_used": len(reference_diagrams or []),
        "documents": documents,
        "rendering": {
            "quality_scorecard": quality_scorecard,
            "diagram_pages": [
                {
                    "page_number": 1,
                    "page_name": "Holistic OpenShift architecture",
                    "title": title,
                    "summary": documents["hld"]["summary"],
                    "included_groups": [group for group in GROUP_ORDER if group in group_boxes],
                    "node_count": len(nodes),
                    "edge_count": len(edges),
                }
            ],
        },
        "artifacts": {
            "drawio_xml": drawio_xml,
            "svg_preview": svg_preview,
            "svg": svg_bytes.decode("utf-8", errors="ignore") if svg_bytes else svg_preview,
            "png_base64": base64.b64encode(png_bytes).decode("ascii") if png_bytes else None,
            "filenames": {
                "drawio": f"{_slugify(title)}.drawio",
                "svg": f"{_slugify(title)}.svg",
                "png": f"{_slugify(title)}.png",
            },
        },
    }
