from __future__ import annotations

import base64
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from html import escape
from io import BytesIO
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
from tempfile import TemporaryDirectory
import time
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
GROUP_ICON_LABELS = {
    "context": "CTX",
    "fleet": "ACM",
    "control-plane": "OCP",
    "network": "NET",
    "security": "SEC",
    "delivery": "GIT",
    "workload": "APP",
    "data": "DATA",
    "operations": "OPS",
}
GROUP_NODE_SHAPES = {
    "context": "shape=cloud;",
    "fleet": "shape=hexagon;perimeter=hexagonPerimeter2;",
    "control-plane": "rounded=1;",
    "network": "shape=parallelogram;perimeter=parallelogramPerimeter;",
    "security": "shape=hexagon;perimeter=hexagonPerimeter2;",
    "delivery": "shape=step;perimeter=stepPerimeter;",
    "workload": "rounded=1;",
    "data": "shape=cylinder3;boundedLbl=1;backgroundOutline=1;size=15;",
    "operations": "shape=note;",
}
KUBERNETES_POD_ICON_STYLE = (
    "sketch=0;html=1;dashed=0;whitespace=wrap;fillColor=#2875E2;strokeColor=#ffffff;"
    "points=[[0.005,0.63,0],[0.1,0.2,0],[0.9,0.2,0],[0.5,0,0],[0.995,0.63,0],[0.72,0.99,0],[0.5,1,0],[0.28,0.99,0]];"
    "verticalLabelPosition=bottom;align=center;verticalAlign=top;shape=mxgraph.kubernetes.icon;prIcon=pod"
)
DOCUMENT_PAGE_TARGETS = {
    "hld": 50,
    "lld": 100,
    "assessment": 24,
}
REFERENCE_ARCHITECTURE_BASELINE = [
    {
        "title": "OpenShift Container Platform architecture",
        "version": "4.20+",
        "url": "https://docs.redhat.com/en/documentation/openshift_container_platform/4.20/html/architecture",
        "focus": "Platform and application architecture, cluster boundaries, and supported topology language.",
    },
    {
        "title": "OpenShift networking overview",
        "version": "4.20+",
        "url": "https://docs.redhat.com/en/documentation/openshift_container_platform/4.20/html/networking_overview",
        "focus": "Networking model, service exposure, and cluster networking assumptions.",
    },
    {
        "title": "OpenShift ingress and load balancing",
        "version": "4.20+",
        "url": "https://docs.redhat.com/en/documentation/openshift_container_platform/4.20/html/ingress_and_load_balancing",
        "focus": "Routes, ingress, external exposure, and load-balancing patterns.",
    },
    {
        "title": "OpenShift security and compliance",
        "version": "4.20+",
        "url": "https://docs.redhat.com/en/documentation/openshift_container_platform/4.20/html/security_and_compliance",
        "focus": "Certificates, encryption, cluster hardening, and security controls.",
    },
    {
        "title": "OpenShift storage",
        "version": "4.20+",
        "url": "https://docs.redhat.com/en/documentation/openshift_container_platform/4.20/html/storage",
        "focus": "Persistent storage planning, back ends, and dynamic provisioning.",
    },
    {
        "title": "OpenShift backup and restore",
        "version": "4.20+",
        "url": "https://docs.redhat.com/en/documentation/openshift_container_platform/4.20/html/backup_and_restore",
        "focus": "Backup, restore, and disaster recovery decision points.",
    },
    {
        "title": "OpenShift monitoring stack",
        "version": "4.20+",
        "url": "https://docs.redhat.com/en/documentation/openshift_container_platform/4.20/html/monitoring",
        "focus": "Core and user workload monitoring, alerts, and troubleshooting.",
    },
    {
        "title": "ACM governance",
        "version": "2.14+",
        "url": "https://docs.redhat.com/en/documentation/red_hat_advanced_cluster_management_for_kubernetes/2.14/html/governance",
        "focus": "Policy-driven fleet governance, compliance, and security hardening across clusters.",
    },
    {
        "title": "ACM business continuity",
        "version": "2.14+",
        "url": "https://docs.redhat.com/en/documentation/red_hat_advanced_cluster_management_for_kubernetes/2.14/html/business_continuity",
        "focus": "Multicluster backup, VolSync, recovery, and business continuity patterns.",
    },
    {
        "title": "OpenShift GitOps declarative cluster configuration",
        "version": "1.18+",
        "url": "https://docs.redhat.com/en/documentation/red_hat_openshift_gitops/1.18/html/declarative_cluster_configuration",
        "focus": "Declarative cluster config, recursive sync, and application synchronization patterns.",
    },
    {
        "title": "OpenShift GitOps multitenancy",
        "version": "1.18+",
        "url": "https://docs.redhat.com/en/documentation/red_hat_openshift_gitops/1.18/html/multitenancy",
        "focus": "Argo CD tenancy boundaries, instance scoping, and multitenant GitOps choices.",
    },
]
REPO_ARCHITECTURAL_PRIORITIES = [
    "Model OpenShift 4.20+ estates with explicit management, workload, DC, and DR cluster roles rather than generic Kubernetes boxes.",
    "Prefer supported Red Hat operators and platform-native capabilities such as ACM, GitOps, ODF, OADP, OpenShift Virtualization, OpenShift AI, logging, monitoring, and operator-driven lifecycle management.",
    "Treat disconnected and air-gapped operations as first-class concerns: mirrored registries, controlled transfer paths, trust bundles, bastions, and supportable day-2 procedures.",
    "Capture ingress, DNS, certificates, load balancing, firewall ports, and east-west connectivity as architecture content, not implementation afterthoughts.",
    "Explain business continuity with backup, restore, replication, failover, relocate, and failback workflows across multicluster estates using ACM and related platform services when relevant.",
    "Reflect the repository's deployment patterns across bare metal IPI and UPI, ROSA, ARO, IBM Z, multicluster management, DR, and migration use cases.",
    "Generate editable draw.io output with multiple architecture views so the shared architecture pack and the separate HLD and LLD exports mirror enterprise review expectations.",
]
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
        "id": "onprem-baremetal",
        "label": "On-prem bare-metal OpenShift",
        "category": "On-prem",
        "description": "Holistic on-prem OpenShift for rack, VLAN, firewall, bonded-NIC, console, and ODF review packs that should feel close to enterprise ocp.drawio-style diagrams.",
        "prompt": "Create an on-prem bare-metal OpenShift architecture that mirrors an enterprise rack-and-network review drawing: paired edge firewalls, separate management VLAN and user VLAN switch fabrics, console or BMC access, bonded NIC uplinks using Bond0 over ETH0 and ETH1, rack-aligned control-plane and worker nodes, ODF / Rook-Ceph data paths, and explicit shared services for ACM, ACS, GitOps, Quay, observability, backup, and disaster recovery.",
        "mode": "hybrid",
        "skills": ["On-prem", "Bare metal", "VLAN", "ODF", "Rack topology", "HLD", "LLD"],
        "default_nodes": [
            {"node_id": "dc_context", "label": "On-prem data center and enterprise edge", "group": "context", "detail": "Upstream WAN, enterprise security zones, DNS, and route ownership around the OpenShift estate."},
            {"node_id": "edge_firewalls", "label": "Paired edge firewalls", "group": "security", "detail": "DMZ and trust-boundary controls between upstream access and the OpenShift management and user VLAN fabrics."},
            {"node_id": "management_vlan", "label": "Management VLAN switch fabric", "group": "network", "detail": "Management network for API, provisioning, BMC or console access, operator administration, and day-2 control traffic."},
            {"node_id": "user_vlan", "label": "User VLAN switch fabric", "group": "network", "detail": "Application, ingress, east-west, and consumer-facing traffic network for workloads and platform routes."},
            {"node_id": "console_ports", "label": "Console port and BMC access", "group": "security", "detail": "Console or BMC network for bootstrap, control-plane, and worker recovery access plus change-controlled break-glass paths."},
            {"node_id": "control_plane_rack", "label": "Control-plane rack", "group": "control-plane", "detail": "Bootstrap and control-plane nodes on bare metal with Bond0 uplinks over ETH0 and ETH1 plus management attachments."},
            {"node_id": "worker_rack", "label": "Worker rack", "group": "workload", "detail": "Bare-metal worker nodes with bonded uplinks, user VLAN exposure, and workload scale-out lanes."},
            {"node_id": "platform_services_rack", "label": "Shared platform services rack", "group": "delivery", "detail": "ACM, ACS, GitOps, Quay, registry mirroring, and supporting operator-run shared services."},
            {"node_id": "odf_rook", "label": "ODF / Rook-Ceph data path", "group": "data", "detail": "NVMe-backed ODF with MON, MGR, MDS, and OSD service lanes plus snapshot and backup integration."},
            {"node_id": "ops_lane", "label": "Observability, backup, and DR lane", "group": "operations", "detail": "Monitoring, logging, alerting, OADP, DR orchestration, and validation runbooks for steady state and recovery."},
        ],
        "default_edges": [
            {"source": "dc_context", "target": "edge_firewalls", "label": "enterprise ingress / egress"},
            {"source": "edge_firewalls", "target": "management_vlan", "label": "protected management path"},
            {"source": "edge_firewalls", "target": "user_vlan", "label": "protected user path"},
            {"source": "management_vlan", "target": "console_ports", "label": "console / BMC"},
            {"source": "management_vlan", "target": "control_plane_rack", "label": "API / provisioning"},
            {"source": "user_vlan", "target": "worker_rack", "label": "apps / ingress"},
            {"source": "control_plane_rack", "target": "worker_rack", "label": "cluster control"},
            {"source": "platform_services_rack", "target": "control_plane_rack", "label": "governance / GitOps / registry"},
            {"source": "worker_rack", "target": "odf_rook", "label": "ODF data path"},
            {"source": "control_plane_rack", "target": "ops_lane", "label": "telemetry / backup / DR"},
            {"source": "worker_rack", "target": "ops_lane", "label": "logs / alerts / restore"},
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
    ("onprem-baremetal", ["on-prem", "on prem", "bare metal", "baremetal", "management vlan", "user vlan", "bond0", "eth0", "eth1", "console port", "bmc", "idrac", "rook", "ceph", "rack"]),
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
    version_baseline: str
    architect_profile: str
    source_highlights: list[str]


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


def _reference_highlights(limit: int = 6) -> list[str]:
    return [
        f"{item['title']} ({item['version']}) — {item['focus']}"
        for item in REFERENCE_ARCHITECTURE_BASELINE[:limit]
    ]


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
    senior_architect_brief = (
        "Act as a senior Red Hat OpenShift architect using official OpenShift Container Platform 4.20 and later guidance, "
        "plus ACM 2.14+ and OpenShift GitOps 1.18+ practices where relevant. Favor supported OpenShift-native capabilities, "
        "explicit cluster and tenancy boundaries, clear ingress and DNS design, certificate and trust-chain ownership, "
        "operator lifecycle clarity, observability, backup and restore posture, and business continuity planning."
    )
    repository_context = " ".join(REPO_ARCHITECTURAL_PRIORITIES[:5])
    output_expectations = (
        "Produce a multi-page shared draw.io architecture pack with at least holistic, topology, security-and-operations, and "
        "delivery-and-resilience views. Expand the separate HLD and LLD documents using enterprise document rhythm: background, objectives, AS-IS, TO-BE, "
        "solution design views, components, sizing, network requirements, firewall ports, certificates, DNS, load balancing, DR/BCP, "
        "migration, assumptions, decisions, and annexures."
    )
    if pattern_id == "onprem-baremetal":
        output_expectations += (
            " The holistic page must read like an on-prem architecture review board drawing with paired firewalls, user and management VLAN switch fabrics, "
            "console or BMC access, Bond0 and ETH uplinks, rack-aligned control-plane and worker nodes, and explicit ODF / Rook-Ceph storage lanes."
        )
    normalized_prompt = (
        f"{senior_architect_brief} {template['prompt']} {repository_context} {output_expectations} "
        f"Preserve the operator's original OpenShift goals and constraints: {prompt.strip()}"
    ).strip()
    confidence = "high" if pattern_id != "custom" else "medium"
    reasoning_summary = (
        f"Detected the {template['label']} pattern from the prompt and/or live OpenShift signals, then normalized it against a senior Red Hat OpenShift 4.20+ reference baseline."
        if pattern_id != "custom"
        else "Using the custom OpenShift architecture pattern because the prompt does not strongly match a named template, while still applying the Red Hat OpenShift 4.20+ reference baseline."
    )
    return PromptNormalization(
        pattern_id=pattern_id,
        pattern_label=str(template["label"]),
        normalized_prompt=normalized_prompt,
        reasoning_summary=reasoning_summary,
        confidence=confidence,
        version_baseline="OpenShift Container Platform 4.20 and later; ACM 2.14 and later; OpenShift GitOps 1.18 and later.",
        architect_profile="Senior Red Hat OpenShift architect",
        source_highlights=_reference_highlights(),
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
    if pattern_id == "onprem-baremetal":
        if not any(token in prompt_lower for token in ["management vlan", "user vlan", "network", "switch"]):
            questions.append(
                ClarificationQuestion(
                    question_id="onprem_vlan_design",
                    title="VLAN and switch fabrics",
                    question="What management VLAN, user VLAN, and switch-fabric assumptions should the on-prem OpenShift design show?",
                    rationale="The holistic on-prem drawing becomes far more useful when VLAN separation and switch ownership are explicit instead of implied.",
                    placeholder="Example: dual management VLAN switches for API/BMC, dual user VLAN switches for ingress and app traffic, bonded uplinks on all nodes.",
                )
            )
        if not any(token in prompt_lower for token in ["odf", "rook", "ceph", "storage"]):
            questions.append(
                ClarificationQuestion(
                    question_id="onprem_storage_design",
                    title="ODF and storage lane",
                    question="Should the on-prem design show ODF / Rook-Ceph, external storage, or another storage topology for persistent workloads?",
                    rationale="On-prem OpenShift diagrams usually need explicit storage topology and recovery paths, especially when ODF is part of the reference design.",
                    placeholder="Example: ODF internal mode on worker nodes with NVMe OSDs, CSI snapshots, and OADP backups to S3-compatible storage.",
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
                rationale="Cluster role names help the separate HLD and LLD explain who does what across primary, DR, hub, edge, and workload clusters.",
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
                rationale="The separate HLD and LLD outputs are much stronger when storage and restore posture are explicit instead of implied.",
                placeholder="Example: ODF for app data, CSI snapshots, OADP to S3-compatible storage, quarterly restore test.",
            )
        )
    if not any(token in prompt_lower for token in ["rto", "rpo", "failover", "recovery", "restore"]):
        questions.append(
            ClarificationQuestion(
                question_id="recovery_targets",
                title="Recovery targets",
                question="Should the design include explicit RTO/RPO, failover, or recovery-state expectations?",
                rationale="Recovery objectives change the architecture and the review language for both the HLD and LLD outputs.",
                placeholder="Example: RTO 4h, RPO 30m, warm standby cluster, relocate stateful apps only after storage sync health is green.",
            )
        )

    return {
        "needs_clarification": bool(questions),
        "planning": asdict(planning),
        "summary": (
            "This prompt can already produce the shared OpenShift architecture pack. Answer the questions below if you want more implementation-ready HLD or LLD outputs."
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


def _zone(
    *,
    title: str,
    x: float,
    y: float,
    width: float,
    height: float,
    fill: str,
    stroke: str,
    subtitle: str = "",
    notes: list[str] | None = None,
    dashed: bool = False,
    radius: float = 18.0,
) -> dict[str, Any]:
    return {
        "title": title,
        "subtitle": subtitle,
        "notes": list(notes or []),
        "x": x,
        "y": y,
        "width": width,
        "height": height,
        "fill": fill,
        "stroke": stroke,
        "dashed": dashed,
        "radius": radius,
    }


def _layout_nodes_in_rect(
    nodes: list[DiagramNode],
    *,
    x: float,
    y: float,
    width: float,
    height: float,
    columns: int = 1,
    node_width: float = 210.0,
    node_height: float = 82.0,
) -> dict[str, dict[str, float]]:
    positions: dict[str, dict[str, float]] = {}
    if not nodes:
        return positions
    columns = max(1, columns)
    horizontal_gap = max(16.0, (width - 32.0 - (columns * node_width)) / max(columns - 1, 1)) if columns > 1 else 0.0
    vertical_gap = 18.0
    current_x = x + 16.0
    current_y = y + 42.0
    column = 0
    for node in nodes:
        if current_y + node_height > y + height - 12.0 and column < columns - 1:
            column += 1
            current_x = x + 16.0 + (column * (node_width + horizontal_gap))
            current_y = y + 42.0
        positions[node.node_id] = {
            "x": current_x,
            "y": current_y,
            "width": node_width,
            "height": node_height,
        }
        current_y += node_height + vertical_gap
    return positions


def _node_matches(node: DiagramNode, *tokens: str) -> bool:
    haystack = f"{node.label} {node.detail}".lower()
    return any(token in haystack for token in tokens)


def _ordered_subset(nodes: list[DiagramNode], predicate: Any) -> tuple[list[DiagramNode], list[DiagramNode]]:
    selected: list[DiagramNode] = []
    remaining: list[DiagramNode] = []
    for node in nodes:
        if predicate(node):
            selected.append(node)
        else:
            remaining.append(node)
    return selected, remaining


def _layout_hub_spoke_page(nodes: list[DiagramNode]) -> tuple[dict[str, dict[str, float]], list[dict[str, Any]], float, float]:
    total_width = 1560.0
    total_height = 980.0
    zones = [
        _zone(title="Business context and external dependencies", subtitle="Drivers, ingress entry points, registry exchange, and upstream dependencies", x=60, y=70, width=1440, height=140, fill="#EFF6FF", stroke="#2563EB"),
        _zone(title="Hub / management cluster block", subtitle="ACM, governance, policy, and shared control services", x=60, y=240, width=320, height=580, fill="#FEF2F2", stroke="#DC2626"),
        _zone(title="Spoke / workload cluster blocks", subtitle="Managed OpenShift clusters, primary and DR roles, and site topology", x=410, y=240, width=650, height=580, fill="#F8FAFC", stroke="#475569", dashed=True),
        _zone(title="Shared platform services", subtitle="GitOps, observability, security, storage, and day-2 shared services", x=1090, y=240, width=410, height=580, fill="#F5F3FF", stroke="#7C3AED"),
    ]

    remaining = list(nodes)
    context_nodes, remaining = _ordered_subset(remaining, lambda node: node.group == "context" or _node_matches(node, "ingress", "route", "dns", "mirror", "registry", "internet"))
    hub_nodes, remaining = _ordered_subset(remaining, lambda node: node.group == "fleet" or _node_matches(node, "acm", "hub", "governance", "policy"))
    spoke_nodes, remaining = _ordered_subset(remaining, lambda node: node.group == "control-plane" or _node_matches(node, "cluster", "primary", "recovery", "managed", "workload cluster", "dr"))
    shared_nodes = remaining

    positions: dict[str, dict[str, float]] = {}
    positions.update(_layout_nodes_in_rect(context_nodes or nodes[:2], x=60, y=70, width=1440, height=140, columns=max(1, min(4, len(context_nodes or nodes[:2]))), node_width=220.0, node_height=74.0))
    positions.update(_layout_nodes_in_rect(hub_nodes or nodes[:2], x=60, y=240, width=320, height=580, columns=1, node_width=260.0, node_height=88.0))
    positions.update(_layout_nodes_in_rect(spoke_nodes or nodes[:3], x=410, y=240, width=650, height=580, columns=2, node_width=270.0, node_height=88.0))
    positions.update(_layout_nodes_in_rect(shared_nodes or nodes[:3], x=1090, y=240, width=410, height=580, columns=1, node_width=300.0, node_height=82.0))
    return positions, zones, total_width, total_height


def _layout_security_lanes_page(nodes: list[DiagramNode]) -> tuple[dict[str, dict[str, float]], list[dict[str, Any]], float, float]:
    total_width = 1600.0
    total_height = 1040.0
    zones = [
        _zone(title="Internet / upstream services", subtitle="External users, public DNS, upstream registries, and provider dependencies", x=60, y=86, width=1480, height=118, fill="#FFF7ED", stroke="#EA580C"),
        _zone(title="DMZ and edge ingress lane", subtitle="Public routes, load balancing, ingress controllers, and controlled exposure", x=60, y=230, width=1480, height=156, fill="#F8FAFC", stroke="#475569", dashed=True),
        _zone(title="Firewall, bastion, and access lane", subtitle="Segmentation, bastion/jump access, identity, and trust-boundary controls", x=60, y=412, width=1480, height=176, fill="#FEF2F2", stroke="#DC2626"),
        _zone(title="Cluster core and service plane", subtitle="Control plane, application, storage, and platform runtime inside the protected zone", x=60, y=614, width=1480, height=196, fill="#F0FDF4", stroke="#16A34A"),
        _zone(title="Security operations and evidence", subtitle="Monitoring, logging, alerts, policy evidence, and incident response handoff", x=60, y=836, width=1480, height=126, fill="#EEF2FF", stroke="#4338CA"),
    ]

    remaining = list(nodes)
    upstream_nodes, remaining = _ordered_subset(remaining, lambda node: node.group == "context" or _node_matches(node, "internet", "mirror", "registry", "source", "repo", "external"))
    dmz_nodes, remaining = _ordered_subset(remaining, lambda node: node.group == "network" or _node_matches(node, "ingress", "route", "dns", "load balancer", "api"))
    access_nodes, remaining = _ordered_subset(remaining, lambda node: node.group == "security" or _node_matches(node, "firewall", "bastion", "proxy", "identity", "oauth", "ldap", "policy", "acs"))
    core_nodes, remaining = _ordered_subset(remaining, lambda node: node.group in {"fleet", "control-plane", "workload", "data"})
    ops_nodes = remaining

    positions: dict[str, dict[str, float]] = {}
    positions.update(_layout_nodes_in_rect(upstream_nodes or nodes[:3], x=60, y=86, width=1480, height=118, columns=max(1, min(5, len(upstream_nodes or nodes[:3]))), node_width=228.0, node_height=64.0))
    positions.update(_layout_nodes_in_rect(dmz_nodes or nodes[:3], x=60, y=230, width=1480, height=156, columns=max(1, min(5, len(dmz_nodes or nodes[:3]))), node_width=220.0, node_height=70.0))
    positions.update(_layout_nodes_in_rect(access_nodes or nodes[:4], x=60, y=412, width=1480, height=176, columns=max(1, min(5, len(access_nodes or nodes[:4]))), node_width=228.0, node_height=74.0))
    positions.update(_layout_nodes_in_rect(core_nodes or nodes[:5], x=60, y=614, width=1480, height=196, columns=max(1, min(5, len(core_nodes or nodes[:5]))), node_width=228.0, node_height=76.0))
    positions.update(_layout_nodes_in_rect(ops_nodes or nodes[:3], x=60, y=836, width=1480, height=126, columns=max(1, min(5, len(ops_nodes or nodes[:3]))), node_width=228.0, node_height=64.0))
    return positions, zones, total_width, total_height


def _layout_service_bands_page(nodes: list[DiagramNode]) -> tuple[dict[str, dict[str, float]], list[dict[str, Any]], float, float]:
    total_width = 1560.0
    total_height = 980.0
    zones = [
        _zone(title="ACM / ACS / Quay placement band", subtitle="Hub services, governance plane, security stack, and mirrored registry placement", x=60, y=70, width=690, height=220, fill="#FEF2F2", stroke="#DC2626"),
        _zone(title="GitOps / delivery placement band", subtitle="Argo CD, Tekton, pipelines, image promotion, and rollout controls", x=800, y=70, width=700, height=220, fill="#FFF7ED", stroke="#D97706"),
        _zone(title="ODF / OADP / data protection band", subtitle="Storage services, snapshots, backup targets, and recovery controls", x=60, y=330, width=690, height=240, fill="#F5F3FF", stroke="#7C3AED"),
        _zone(title="Observability / operations band", subtitle="Monitoring, logging, alerts, runbooks, and support visibility", x=800, y=330, width=700, height=240, fill="#EEF2FF", stroke="#4338CA"),
        _zone(title="Cluster service placement block", subtitle="Core OpenShift services, cluster operators, and shared platform runtime placement", x=60, y=610, width=1440, height=280, fill="#F0FDF4", stroke="#16A34A"),
    ]

    remaining = list(nodes)
    acm_nodes, remaining = _ordered_subset(remaining, lambda node: _node_matches(node, "acm", "acs", "quay", "hub", "governance"))
    delivery_nodes, remaining = _ordered_subset(remaining, lambda node: node.group == "delivery" or _node_matches(node, "gitops", "argocd", "tekton", "pipeline", "promotion"))
    data_nodes, remaining = _ordered_subset(remaining, lambda node: node.group == "data" or _node_matches(node, "odf", "oadp", "backup", "restore", "ceph", "snapshot", "storage"))
    ops_nodes, remaining = _ordered_subset(remaining, lambda node: node.group == "operations" or _node_matches(node, "observability", "monitoring", "logging", "alert", "runbook"))
    cluster_nodes = remaining

    positions: dict[str, dict[str, float]] = {}
    positions.update(_layout_nodes_in_rect(acm_nodes or nodes[:3], x=60, y=70, width=690, height=220, columns=max(1, min(2, len(acm_nodes or nodes[:3]))), node_width=300.0, node_height=84.0))
    positions.update(_layout_nodes_in_rect(delivery_nodes or nodes[:3], x=800, y=70, width=700, height=220, columns=max(1, min(2, len(delivery_nodes or nodes[:3]))), node_width=310.0, node_height=84.0))
    positions.update(_layout_nodes_in_rect(data_nodes or nodes[:3], x=60, y=330, width=690, height=240, columns=max(1, min(2, len(data_nodes or nodes[:3]))), node_width=300.0, node_height=84.0))
    positions.update(_layout_nodes_in_rect(ops_nodes or nodes[:3], x=800, y=330, width=700, height=240, columns=max(1, min(2, len(ops_nodes or nodes[:3]))), node_width=310.0, node_height=84.0))
    positions.update(_layout_nodes_in_rect(cluster_nodes or nodes[:4], x=60, y=610, width=1440, height=280, columns=max(1, min(4, len(cluster_nodes or nodes[:4]))), node_width=250.0, node_height=84.0))
    return positions, zones, total_width, total_height


def _layout_infra_topology_page(nodes: list[DiagramNode]) -> tuple[dict[str, dict[str, float]], list[dict[str, Any]], float, float]:
    total_width = 1700.0
    total_height = 1120.0
    zones = [
        _zone(title="User VLAN", subtitle="Application and east-west network presentation", x=60, y=86, width=1580, height=102, fill="#EFF6FF", stroke="#0284C7"),
        _zone(title="Management VLAN", subtitle="API, provisioning, bastion, node management, and service administration", x=60, y=214, width=1580, height=102, fill="#ECFDF5", stroke="#16A34A"),
        _zone(title="Rack and node topology", subtitle="Cluster and site blocks arranged like rack-aligned node lanes", x=60, y=342, width=1580, height=454, fill="#F8FAFC", stroke="#475569", dashed=True),
        _zone(title="Platform services and infrastructure", subtitle="ODF, Quay, GitOps, monitoring, ACS, and supporting infra services", x=60, y=822, width=1580, height=236, fill="#F5F3FF", stroke="#7C3AED"),
        _zone(title="Rack A", subtitle="Hub / infra", x=94, y=400, width=334, height=330, fill="#FFFFFF", stroke="#94A3B8", dashed=True, radius=14.0),
        _zone(title="Rack B", subtitle="Primary cluster", x=472, y=400, width=334, height=330, fill="#FFFFFF", stroke="#94A3B8", dashed=True, radius=14.0),
        _zone(title="Rack C", subtitle="Recovery cluster", x=850, y=400, width=334, height=330, fill="#FFFFFF", stroke="#94A3B8", dashed=True, radius=14.0),
        _zone(title="Rack D", subtitle="Shared services", x=1228, y=400, width=334, height=330, fill="#FFFFFF", stroke="#94A3B8", dashed=True, radius=14.0),
    ]

    remaining = list(nodes)
    user_vlan_nodes, remaining = _ordered_subset(remaining, lambda node: node.group == "network" or _node_matches(node, "ingress", "route", "dns", "load balancer", "user vlan"))
    mgmt_nodes, remaining = _ordered_subset(remaining, lambda node: _node_matches(node, "bastion", "api", "management", "proxy", "firewall", "console", "hub") or node.group == "context")
    rack_a_nodes, remaining = _ordered_subset(remaining, lambda node: _node_matches(node, "acm", "hub", "fleet", "quay"))
    rack_b_nodes, remaining = _ordered_subset(remaining, lambda node: _node_matches(node, "primary", "prod", "cluster") or node.group == "control-plane")
    rack_c_nodes, remaining = _ordered_subset(remaining, lambda node: _node_matches(node, "recovery", "dr", "backup", "oadp") or node.group == "data")
    rack_d_nodes = remaining

    positions: dict[str, dict[str, float]] = {}
    positions.update(_layout_nodes_in_rect(user_vlan_nodes or nodes[:4], x=60, y=86, width=1580, height=102, columns=max(1, min(6, len(user_vlan_nodes or nodes[:4]))), node_width=214.0, node_height=60.0))
    positions.update(_layout_nodes_in_rect(mgmt_nodes or nodes[:4], x=60, y=214, width=1580, height=102, columns=max(1, min(6, len(mgmt_nodes or nodes[:4]))), node_width=214.0, node_height=60.0))
    positions.update(_layout_nodes_in_rect(rack_a_nodes or nodes[:3], x=94, y=422, width=334, height=250, columns=2, node_width=138.0, node_height=64.0))
    positions.update(_layout_nodes_in_rect(rack_b_nodes or nodes[:3], x=472, y=422, width=334, height=250, columns=2, node_width=138.0, node_height=64.0))
    positions.update(_layout_nodes_in_rect(rack_c_nodes or nodes[:3], x=850, y=422, width=334, height=250, columns=2, node_width=138.0, node_height=64.0))
    positions.update(_layout_nodes_in_rect(rack_d_nodes or nodes[:4], x=1228, y=422, width=334, height=250, columns=2, node_width=138.0, node_height=64.0))
    all_service_nodes = rack_a_nodes + rack_b_nodes + rack_c_nodes + rack_d_nodes
    positions.update(_layout_nodes_in_rect(all_service_nodes[:10] or nodes[:5], x=60, y=822, width=1580, height=236, columns=max(1, min(5, len(all_service_nodes[:10] or nodes[:5]))), node_width=250.0, node_height=76.0))
    return positions, zones, total_width, total_height


def _layout_onprem_holistic_page(nodes: list[DiagramNode]) -> tuple[dict[str, dict[str, float]], list[dict[str, Any]], float, float]:
    total_width = 1720.0
    total_height = 1140.0
    zones = [
        _zone(title="Enterprise edge and upstream dependencies", subtitle="Users, WAN, enterprise DNS, load-balancing, and upstream service ownership around the on-prem OpenShift estate", x=60, y=78, width=1600, height=118, fill="#FFF7ED", stroke="#EA580C"),
        _zone(title="DMZ and firewall presentation lane", subtitle="Paired firewall, proxy, bastion, and trust-boundary controls before traffic enters the cluster fabrics", x=60, y=218, width=1600, height=136, fill="#FEF2F2", stroke="#DC2626"),
        _zone(title="Management VLAN", subtitle="API, provisioning, console or BMC, operator administration, and day-2 management connectivity", x=60, y=376, width=1600, height=96, fill="#ECFDF5", stroke="#16A34A"),
        _zone(title="User VLAN", subtitle="Ingress, application exposure, service access, and east-west workload presentation across the user network", x=60, y=494, width=1600, height=96, fill="#EFF6FF", stroke="#0284C7"),
        _zone(title="Rack and node topology", subtitle="Rack-aligned bare-metal platform showing control-plane, worker, and shared-service blocks like an enterprise data-center review drawing", x=60, y=614, width=1600, height=336, fill="#F8FAFC", stroke="#475569", dashed=True),
        _zone(title="Platform services and ODF data path", subtitle="Shared services, ODF / Rook-Ceph lanes, observability, backup, and DR orchestration supporting the on-prem cluster", x=60, y=972, width=1600, height=118, fill="#F5F3FF", stroke="#7C3AED"),
        _zone(title="Rack A", subtitle="Edge and management", x=94, y=670, width=350, height=236, fill="#FFFFFF", stroke="#94A3B8", dashed=True, radius=14.0),
        _zone(title="Rack B", subtitle="Control plane", x=486, y=670, width=350, height=236, fill="#FFFFFF", stroke="#94A3B8", dashed=True, radius=14.0),
        _zone(title="Rack C", subtitle="Workers and workloads", x=878, y=670, width=350, height=236, fill="#FFFFFF", stroke="#94A3B8", dashed=True, radius=14.0),
        _zone(title="Rack D", subtitle="Shared services and storage", x=1270, y=670, width=350, height=236, fill="#FFFFFF", stroke="#94A3B8", dashed=True, radius=14.0),
    ]

    remaining = list(nodes)
    upstream_nodes, remaining = _ordered_subset(remaining, lambda node: node.group == "context" or _node_matches(node, "enterprise", "wan", "dns", "upstream", "edge", "user"))
    dmz_nodes, remaining = _ordered_subset(remaining, lambda node: node.group == "security" or _node_matches(node, "firewall", "dmz", "bastion", "proxy", "console", "bmc"))
    management_nodes, remaining = _ordered_subset(remaining, lambda node: _node_matches(node, "management vlan", "api", "provisioning", "console", "bond0", "eth0", "eth1", "bmc"))
    user_nodes, remaining = _ordered_subset(remaining, lambda node: _node_matches(node, "user vlan", "ingress", "route", "application", "workload", "worker"))
    rack_a_nodes, remaining = _ordered_subset(remaining, lambda node: _node_matches(node, "firewall", "console", "management", "acm", "hub", "quay"))
    rack_b_nodes, remaining = _ordered_subset(remaining, lambda node: node.group == "control-plane" or _node_matches(node, "control-plane", "master", "bootstrap", "api"))
    rack_c_nodes, remaining = _ordered_subset(remaining, lambda node: node.group == "workload" or _node_matches(node, "worker", "workload", "ingress"))
    rack_d_nodes, remaining = _ordered_subset(remaining, lambda node: node.group in {"delivery", "data", "operations"} or _node_matches(node, "odf", "rook", "ceph", "backup", "dr", "gitops", "observability"))
    service_nodes = remaining

    positions: dict[str, dict[str, float]] = {}
    positions.update(_layout_nodes_in_rect(upstream_nodes or nodes[:3], x=60, y=78, width=1600, height=118, columns=max(1, min(5, len(upstream_nodes or nodes[:3]))), node_width=260.0, node_height=66.0))
    positions.update(_layout_nodes_in_rect(dmz_nodes or nodes[:4], x=60, y=218, width=1600, height=136, columns=max(1, min(5, len(dmz_nodes or nodes[:4]))), node_width=250.0, node_height=74.0))
    positions.update(_layout_nodes_in_rect(management_nodes or nodes[:4], x=60, y=376, width=1600, height=96, columns=max(1, min(6, len(management_nodes or nodes[:4]))), node_width=230.0, node_height=60.0))
    positions.update(_layout_nodes_in_rect(user_nodes or nodes[:4], x=60, y=494, width=1600, height=96, columns=max(1, min(6, len(user_nodes or nodes[:4]))), node_width=230.0, node_height=60.0))
    positions.update(_layout_nodes_in_rect(rack_a_nodes or nodes[:3], x=94, y=700, width=350, height=172, columns=2, node_width=148.0, node_height=66.0))
    positions.update(_layout_nodes_in_rect(rack_b_nodes or nodes[:3], x=486, y=700, width=350, height=172, columns=2, node_width=148.0, node_height=66.0))
    positions.update(_layout_nodes_in_rect(rack_c_nodes or nodes[:3], x=878, y=700, width=350, height=172, columns=2, node_width=148.0, node_height=66.0))
    positions.update(_layout_nodes_in_rect(rack_d_nodes or nodes[:4], x=1270, y=700, width=350, height=172, columns=2, node_width=148.0, node_height=66.0))
    combined_service_nodes = (rack_d_nodes + service_nodes)[:10] or nodes[:5]
    positions.update(_layout_nodes_in_rect(combined_service_nodes, x=60, y=972, width=1600, height=118, columns=max(1, min(5, len(combined_service_nodes))), node_width=250.0, node_height=66.0))
    return positions, zones, total_width, total_height


def _layout_explanation_page(nodes: list[DiagramNode]) -> tuple[dict[str, dict[str, float]], list[dict[str, Any]], float, float]:
    total_width = 1560.0
    total_height = 1180.0
    grouped: dict[str, list[DiagramNode]] = {group: [] for group in GROUP_ORDER}
    for node in nodes:
        grouped.setdefault(node.group, []).append(node)

    def node_notes(groups: list[str], *, prefix: str, limit: int = 4) -> list[str]:
        selected: list[str] = []
        for group in groups:
            for node in grouped.get(group, [])[:limit]:
                selected.append(f"{prefix}{node.label}: {node.detail}")
                if len(selected) >= limit:
                    return selected
        return selected

    zones = [
        _zone(
            title="Architecture explanation and design narrative",
            subtitle="Why this architecture exists, what it optimizes for, and how the review pack should be read by platform, network, security, and operations teams.",
            notes=[
                "Page 1 gives the holistic executive picture; the remaining pages decompose the same design into component, perimeter, placement, infrastructure, and recovery lenses.",
                "The pack is intentionally structured like an enterprise Red Hat review document rather than a single generic Kubernetes sheet.",
                "Cluster boundaries, ingress controls, storage posture, observability, and DR semantics are treated as first-class architecture content.",
            ],
            x=60,
            y=70,
            width=1440,
            height=180,
            fill="#EFF6FF",
            stroke="#2563EB",
        ),
        _zone(
            title="Primary platform component view",
            subtitle="The component pages should explain cluster roles, shared services, and operator ownership before implementation begins.",
            notes=node_notes(["fleet", "control-plane", "workload"], prefix="• ", limit=4),
            x=60,
            y=280,
            width=690,
            height=220,
            fill="#F8FAFC",
            stroke="#475569",
        ),
        _zone(
            title="Network, security, and perimeter explanation",
            subtitle="Separate the access story from the component story so DMZ, bastion, firewall, DNS, and ingress decisions remain reviewable.",
            notes=node_notes(["network", "security"], prefix="• ", limit=4),
            x=810,
            y=280,
            width=690,
            height=220,
            fill="#FEF2F2",
            stroke="#DC2626",
        ),
        _zone(
            title="Operations, delivery, and resilience explanation",
            subtitle="Show how the platform is delivered, observed, protected, and recovered—not just how it is installed.",
            notes=node_notes(["delivery", "operations", "data"], prefix="• ", limit=4),
            x=60,
            y=530,
            width=690,
            height=220,
            fill="#F5F3FF",
            stroke="#7C3AED",
        ),
        _zone(
            title="Version baseline and architecture guardrails",
            subtitle="The shared architecture pack plus the separate HLD and LLD outputs should stay grounded on supported Red Hat constructs and explicit enterprise operating assumptions.",
            notes=[
                "• OpenShift Container Platform 4.20 and later.",
                "• ACM 2.14+ and OpenShift GitOps 1.18+ where the design requires them.",
                "• Prefer supported operators and OpenShift-native services over bespoke platform components.",
                "• Document DNS, certificates, ports, load balancing, backup, and DR expectations explicitly.",
            ],
            x=810,
            y=530,
            width=690,
            height=220,
            fill="#ECFDF5",
            stroke="#16A34A",
        ),
        _zone(
            title="Anchor component map",
            subtitle="Representative components referenced by the narrative page so the explanation stays tied to the actual architecture pack.",
            x=60,
            y=790,
            width=1440,
            height=320,
            fill="#FFFFFF",
            stroke="#94A3B8",
            dashed=True,
        ),
    ]

    positions = _layout_nodes_in_rect(
        nodes,
        x=60,
        y=790,
        width=1440,
        height=320,
        columns=max(1, min(4, len(nodes) or 1)),
        node_width=300.0,
        node_height=82.0,
    )
    return positions, zones, total_width, total_height


def _layout_page(
    *,
    layout_mode: str,
    nodes: list[DiagramNode],
) -> tuple[dict[str, dict[str, float]], dict[str, dict[str, float]], list[dict[str, Any]], float, float]:
    if layout_mode == "onprem-holistic":
        positions, zones, total_width, total_height = _layout_onprem_holistic_page(nodes)
        return positions, {}, zones, total_width, total_height
    if layout_mode == "hub-spoke":
        positions, zones, total_width, total_height = _layout_hub_spoke_page(nodes)
        return positions, {}, zones, total_width, total_height
    if layout_mode == "security-lanes":
        positions, zones, total_width, total_height = _layout_security_lanes_page(nodes)
        return positions, {}, zones, total_width, total_height
    if layout_mode == "service-bands":
        positions, zones, total_width, total_height = _layout_service_bands_page(nodes)
        return positions, {}, zones, total_width, total_height
    if layout_mode == "infra-topology":
        positions, zones, total_width, total_height = _layout_infra_topology_page(nodes)
        return positions, {}, zones, total_width, total_height
    if layout_mode == "explanation":
        positions, zones, total_width, total_height = _layout_explanation_page(nodes)
        return positions, {}, zones, total_width, total_height
    positions, group_boxes, total_width, total_height = _layout_nodes(nodes)
    return positions, group_boxes, [], total_width, total_height


def _filter_edges_for_nodes(edges: list[DiagramEdge], allowed_ids: set[str]) -> list[DiagramEdge]:
    return [edge for edge in edges if edge.source in allowed_ids and edge.target in allowed_ids]


def _diagram_page_specs(
    *,
    title: str,
    planning: PromptNormalization,
    nodes: list[DiagramNode],
    edges: list[DiagramEdge],
    openshift_state: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    counts = (openshift_state or {}).get("resource_counts") or {}
    is_onprem_baremetal = planning.pattern_id == "onprem-baremetal"
    summaries = {
        "holistic": (
            "Holistic on-prem OpenShift view with enterprise edge, paired firewalls, management and user VLAN switch fabrics, bonded bare-metal racks, and explicit ODF / Rook-Ceph service lanes."
            if is_onprem_baremetal
            else planning.reasoning_summary
        ),
        "topology": (
            f"Site and topology view covering managed clusters={counts.get('managed_clusters', 0)}, ingress controllers={counts.get('ingress_controllers', 0)}, "
            f"and workload/data placement assumptions."
        ),
        "security": "Security, governance, delivery, and observability responsibilities grouped for architecture review and control ownership.",
        "recovery": (
            f"Lifecycle, resilience, and recovery view covering backups={counts.get('backup_locations', 0)}, "
            f"DR policies={counts.get('dr_policies', 0)}, and delivery/migration sequencing."
        ),
    }
    page_definitions = [
        {
            "page_name": "Holistic OpenShift architecture",
            "title": title,
            "summary": summaries["holistic"],
            "groups": GROUP_ORDER,
            "layout_mode": "onprem-holistic" if is_onprem_baremetal else "grouped",
        },
        {
            "page_name": "Architecture explanation and design narrative",
            "title": f"{planning.pattern_label} — architecture explanation",
            "summary": "A narrative page that explains how to read the architecture pack before diving into the deeper component and infrastructure views.",
            "groups": GROUP_ORDER,
            "layout_mode": "explanation",
        },
        {
            "page_name": "Component architecture and cluster topology",
            "title": f"{planning.pattern_label} — component and cluster view",
            "summary": "Dedicated hub / spoke cluster blocks with shared platform services, closely aligned to enterprise OpenShift fleet presentation patterns.",
            "groups": ["context", "fleet", "control-plane", "delivery", "operations", "workload", "data", "network"],
            "layout_mode": "hub-spoke",
        },
        {
            "page_name": "DMZ, firewall, and bastion lanes",
            "title": f"{planning.pattern_label} — perimeter and access lanes",
            "summary": "DMZ, firewall, bastion, and protected-cluster lanes laid out like a Red Hat-ready security review page.",
            "groups": ["context", "network", "security", "fleet", "control-plane", "workload", "data", "operations", "delivery"],
            "layout_mode": "security-lanes",
        },
        {
            "page_name": "ACM, ACS, Quay, ODF, and GitOps placement bands",
            "title": f"{planning.pattern_label} — platform service placement",
            "summary": "ACM / ACS / Quay / ODF / GitOps service placement bands for platform architecture review and operator ownership mapping.",
            "groups": ["fleet", "security", "delivery", "data", "operations", "control-plane", "workload"],
            "layout_mode": "service-bands",
        },
        {
            "page_name": "Rack, node, VLAN, and infrastructure topology",
            "title": f"{planning.pattern_label} — VLAN and rack topology",
            "summary": summaries["topology"],
            "groups": ["context", "network", "fleet", "control-plane", "workload", "data", "delivery", "operations"],
            "layout_mode": "infra-topology",
        },
        {
            "page_name": "Delivery, resilience, and recovery",
            "title": f"{planning.pattern_label} — delivery and resilience",
            "summary": summaries["recovery"],
            "groups": ["fleet", "control-plane", "delivery", "workload", "data", "operations"],
            "layout_mode": "grouped",
        },
    ]

    pages: list[dict[str, Any]] = []
    for index, definition in enumerate(page_definitions, start=1):
        page_nodes = [node for node in nodes if node.group in definition["groups"]] or nodes
        allowed_ids = {node.node_id for node in page_nodes}
        page_edges = _filter_edges_for_nodes(edges, allowed_ids) or edges
        positions, group_boxes, zones, total_width, total_height = _layout_page(layout_mode=str(definition.get("layout_mode", "grouped")), nodes=page_nodes)
        pages.append(
            {
                "page_number": index,
                "page_id": f"architect-page-{index}",
                "page_name": definition["page_name"],
                "title": definition["title"],
                "summary": definition["summary"],
                "layout_mode": definition.get("layout_mode", "grouped"),
                "nodes": page_nodes,
                "edges": page_edges,
                "positions": positions,
                "group_boxes": group_boxes,
                "zones": zones,
                "total_width": total_width,
                "total_height": total_height,
                "included_groups": [group for group in definition["groups"] if any(node.group == group for node in page_nodes)],
            }
        )
    return pages


def _section(title: str, body: list[str]) -> dict[str, Any]:
    cleaned = [str(item).strip() for item in body if str(item or "").strip()]
    return {"title": title, "body": cleaned}


def _estimate_document_pages(sections: list[dict[str, Any]], document_type: str) -> int:
    word_count = 0
    for section in sections:
        word_count += 120
        for line in section.get("body", []):
            word_count += len(str(line).split()) + 12
    words_per_page = {
        "hld": 180,
        "lld": 160,
        "assessment": 220,
    }.get(document_type, 180)
    return max(1, round(word_count / words_per_page))


def _reference_sections() -> list[dict[str, Any]]:
    return [
        _section(
            "Reference baseline and standards",
            [
                f"{item['title']} [{item['version']}] — {item['focus']} Source: {item['url']}"
                for item in REFERENCE_ARCHITECTURE_BASELINE
            ]
            + [
                "These references are treated as the default architecture baseline for OpenShift 4.20+ designs unless the operator brief explicitly requires a narrower or more opinionated standard.",
                "Where the repository already contains stronger environment-specific guidance, the pack should reconcile official Red Hat patterns with those local deployment realities instead of replacing them.",
            ],
        )
    ]


def _repo_alignment_sections() -> list[dict[str, Any]]:
    return [
        _section(
            "Repository-aligned architecture guardrails",
            REPO_ARCHITECTURAL_PRIORITIES,
        )
    ]


def _foundational_outline_sections(
    *,
    document_type: str,
    title: str,
    planning: PromptNormalization,
    nodes: list[DiagramNode],
    edges: list[DiagramEdge],
    prompt: str,
    openshift_state: dict[str, Any] | None,
    knowledge_context: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    counts = (openshift_state or {}).get("resource_counts") or {}
    grouped: dict[str, list[DiagramNode]] = {}
    for node in nodes:
        grouped.setdefault(node.group, []).append(node)
    knowledge_items = list((knowledge_context or {}).get("items") or [])
    flow_lines = [f"{edge.source} -> {edge.target}{f' ({edge.label})' if edge.label else ''}" for edge in edges]

    sections = [
        _section(
            "Background",
            [
                f"This {document_type.upper()} describes {title} using the {planning.pattern_label} pattern and a senior Red Hat OpenShift 4.20+ architecture baseline.",
                "The document assumes enterprise review expectations: supported services, clear ownership boundaries, explicit operational controls, and architecture language aligned to Red Hat platform constructs.",
                f"Operator brief preserved for design intent: {prompt.strip() or 'Prompt-free generation based on live OpenShift platform state and trained architecture knowledge.'}",
            ],
        ),
        _section(
            "Objective",
            [
                "Define an implementation-aligned OpenShift reference architecture that supports platform, security, networking, operations, recovery, and delivery review in a single structured package.",
                "Provide enough detail for architecture boards, operations teams, and delivery teams to understand why the design exists, what it depends on, and how it will be operated safely.",
                "Preserve Red Hat supported-pattern language for OpenShift 4.20 and later while aligning the output with the repository's multi-cluster, air-gapped, ACM, GitOps, DR, and migration capabilities.",
            ],
        ),
        _section(
            "AS-IS environment and constraints",
            [
                f"Live OpenShift state included: {'yes' if openshift_state else 'no'}.",
                f"Observed platform indicators: managed clusters={counts.get('managed_clusters', 0)}, degraded operators={counts.get('degraded_operators', 0)}, ingress controllers={counts.get('ingress_controllers', 0)}, PVCs={counts.get('persistent_volume_claims', 0)}, DR policies={counts.get('dr_policies', 0)}, Argo CD instances={counts.get('argocd_instances', 0)}.",
                "AS-IS review should identify topology already in place, unsupported dependencies, control-plane risks, unsupported ingress assumptions, and any mismatch between business continuity expectations and the current platform posture.",
                "When live state is unavailable, the AS-IS baseline should be treated as hypothesis-driven and must be validated before build approval or cutover planning.",
            ],
        ),
        _section(
            "TO-BE target state",
            [
                f"The TO-BE state uses the {planning.pattern_label} pattern to create a supported, OpenShift-native end state with explicit cluster, security, networking, delivery, data, and operations domains.",
                "Target-state language should favor supported Red Hat operators, OpenShift-native primitives, and explicit lifecycle ownership instead of bespoke or opaque infrastructure assumptions.",
                "The TO-BE design should be reviewable as an enterprise architecture pack, meaning that every major boundary has a purpose, dependency chain, control objective, and operational support model.",
            ],
        ),
        _section(
            "Solution design view",
            [
                "The diagram pack is intentionally multi-page so architecture stakeholders can review the same design from multiple lenses without overloading a single sheet.",
                "Required design views include holistic architecture, site and topology, security and operations, and delivery and resilience. Additional views may be added when the prompt introduces migration, virtualization, edge, or AI specialization.",
                f"Relationship summary: {'; '.join(flow_lines[:12]) if flow_lines else 'Architecture relationships are inferred from the selected OpenShift pattern and live platform posture.'}",
            ],
        ),
        _section(
            "Solution components",
            [
                f"{GROUP_LABELS.get(group, group.title())}: {'; '.join(f'{node.label} — {node.detail}' for node in group_nodes)}"
                for group, group_nodes in grouped.items()
            ],
        ),
        _section(
            "Sizing and capacity provisioning",
            [
                "Capacity planning should distinguish control-plane stability, infrastructure workloads, user workloads, storage growth, and observability retention expectations instead of using one undifferentiated node pool narrative.",
                "Where the design includes AI, CNV, ODF, or multicluster management, capacity assumptions must identify which features drive CPU, memory, storage, and network consumption and how they scale over time.",
                "Sizing decisions should also call out maintenance windows, disruption budgets, spare capacity, and recovery-time headroom so the target estate remains supportable during node failure, upgrades, and DR events.",
            ],
        ),
        _section(
            "Network requirements",
            [
                "Document cluster networks, service networks, ingress or egress boundaries, DNS dependencies, east-west paths, and any cross-site or cross-cluster networking assumptions required for ACM, DR, or GitOps.",
                "Treat ingress exposure, private API reachability, proxy paths, service discovery, and firewall policy as part of the target design rather than operational follow-up work.",
                "If the design spans sites, clouds, or air-gapped segments, define the controlled transfer path, route ownership, and failure-domain implications explicitly.",
            ],
        ),
        _section(
            "Ports to be opened",
            [
                "Firewall guidance must identify API, machine-config, ingress, storage, backup, DR, GitOps, monitoring, and any platform-operator ports that cross trust boundaries.",
                "Port decisions should align to Red Hat supported service exposure models and the repository's own documented ACM, DR, ODF, Submariner, registry, and platform-service communication patterns.",
                "The final implementation handoff should map every cross-boundary port to a named use case, source and destination context, security owner, and test method.",
            ],
        ),
        _section(
            "Certificates and trust",
            [
                "Certificate ownership, renewal paths, trust-bundle propagation, ingress certificates, internal service trust, and mirrored-registry trust must be explicit for OpenShift 4.20+ production designs.",
                "Security posture should describe which components terminate TLS, which certificates are platform-managed, which are externally managed, and what evidence proves the trust chain remains valid after change.",
                "Disconnected and hybrid designs must also explain offline CA distribution, mirror registry trust, and support-bundle validation paths.",
            ],
        ),
        _section(
            "DNS and load balancing",
            [
                "DNS design should include API, wildcard application routes, internal service-discovery dependencies, and any global or site-aware load-balancing behavior required by the target topology.",
                "Load-balancing language should specify ownership for VIPs, DNS records, health checks, and cutover or failover behavior during maintenance and incident conditions.",
                "Where external appliances or cloud-native load balancers are used, the design should state why they are needed and how they align with supported OpenShift ingress and route patterns.",
            ],
        ),
        _section(
            "Security, governance, and compliance posture",
            [
                "Security architecture should cover identity and access, namespace or tenancy boundaries, SCC or admission policy posture, ACS or runtime security integration, certificate handling, and audit evidence paths.",
                "Fleet or multicluster estates should treat ACM governance as a control plane for policy, placement, and compliance evidence rather than as a generic management box.",
                "Compliance intent should be traceable from control objective to enforcement method to evidence collection and operational ownership.",
            ],
        ),
        _section(
            "Observability and operations",
            [
                "Operations coverage must explain monitoring, user workload monitoring, alert routing, logging, support handoff, and runbook use for both steady-state and degraded-state operations.",
                "Architecture readiness improves when dashboards, alerts, log retention, and troubleshooting entry points are designed alongside the platform rather than retrofitted later.",
                "Day-2 language should include patching, upgrades, certificate rotation, backup validation, and platform health review routines.",
            ],
        ),
        _section(
            "Disaster recovery and business continuity approach",
            [
                "Business continuity should differentiate backup and restore, replication, relocate, failover, and failback semantics so stakeholders can distinguish recovery tooling from orchestration intent.",
                "Where ACM, VolSync, ODF, OADP, or related controls are present, the pack should describe cluster roles, metadata paths, replication boundaries, and validation evidence after recovery events.",
                "RTO, RPO, warm-standby or active-active assumptions, and application protection scoping should be named directly to avoid ambiguous DR promises.",
            ],
        ),
        _section(
            "Migration and implementation approach",
            [
                "Migration language should use waves, readiness gates, rollback safety, and hypercare ownership when the platform is modernizing from legacy clusters, VMs, or partially managed estates.",
                "Implementation sequencing should identify day-0 prerequisites, day-1 install activities, and day-2 operator enablement with explicit ownership and dependency handoffs.",
                "If the design is greenfield, this section still needs to describe implementation order, acceptance criteria, and how architecture decisions will be validated before production sign-off.",
            ],
        ),
        _section(
            "Architectural decisions",
            [
                f"Decision 1: Use the {planning.pattern_label} pattern as the design spine so stakeholders review one coherent OpenShift story instead of disconnected diagrams and notes.",
                "Decision 2: Prefer supported Red Hat platform capabilities and operators over bespoke services unless the brief states a justified exception with lifecycle ownership.",
                "Decision 3: Make cluster boundaries, ingress, DNS, certificates, backup, observability, and security evidence first-class architecture content rather than implementation footnotes.",
            ],
        ),
        _section(
            "Assumptions and considerations",
            [
                planning.reasoning_summary,
                planning.version_baseline,
                "The resulting pack should be reviewed against site-specific standards, subscription choices, external integration dependencies, and supportability constraints before build approval.",
                "Any operator-specific or cloud-specific deviations from supported Red Hat patterns should be recorded explicitly with owner, rationale, and rollback implications.",
            ],
        ),
    ]

    if knowledge_items:
        sections.append(
            _section(
                "Grounding references and trained knowledge",
                [
                    f"{item.get('title', 'Knowledge source')} ({item.get('source_type', 'knowledge')}) — {item.get('excerpt', '')}"
                    for item in knowledge_items[:10]
                ],
            )
        )

    return sections


def _booster_sections(
    *,
    document_type: str,
    grouped: dict[str, list[DiagramNode]],
    nodes: list[DiagramNode],
    edges: list[DiagramEdge],
    iteration: int,
) -> list[dict[str, Any]]:
    group_summaries = [
        f"{GROUP_LABELS.get(group, group.title())}: {'; '.join(node.label for node in group_nodes)}"
        for group, group_nodes in grouped.items()
        if group_nodes
    ]
    component_names = ", ".join(node.label for node in nodes[:14]) or "core OpenShift platform services"
    interface_names = "; ".join(f"{edge.source}->{edge.target}" for edge in edges[:14]) or "pattern-derived relationships"
    return [
        _section(
            f"Implementation wave and rollout plan {iteration}",
            [
                f"Wave objective {iteration}: transform the target architecture into a reviewable, sequence-safe execution plan covering {component_names}.",
                "Pre-wave conditions: validate infrastructure readiness, DNS and certificate dependencies, networking paths, mirrored content availability, access delegation, and change approvals.",
                "Wave execution should stage platform foundations first, shared services next, workload onboarding after control validation, and resilience controls only after the steady-state path is proven.",
                "Each wave should define explicit entry criteria, non-negotiable health checks, rollback boundaries, and service-owner approvals before the next stage begins.",
                f"Domain emphasis for this wave: {' | '.join(group_summaries[:8])}.",
                "Where multi-cluster coordination exists, promotion between clusters or sites must be synchronized with GitOps, policy, and DR validation rather than treated as independent workstreams.",
                "Wave completion evidence must include health status, alert posture, certificate state, ingress validation, backup coverage, and stakeholder sign-off records.",
            ],
        ),
        _section(
            f"Operations, SRE, and support model {iteration}",
            [
                "Operational design must specify which team owns platform health, which team owns workload onboarding, and which team holds authority during incident, change, and recovery events.",
                "Routine operating procedures should include monitoring review, alert tuning, logging validation, backup success review, certificate lifecycle checks, patch planning, and subscription or entitlement validation.",
                "Supportability depends on traceable dashboards, actionable alerts, evidence-friendly logs, and first-response runbooks for the highest-risk domains in the estate.",
                f"Primary interaction map for support reviews: {interface_names}.",
                "For air-gapped, regulated, or multicluster environments, support runbooks should also define controlled transfer, evidence handling, and escalation boundaries between site, platform, security, and vendor support teams.",
                "SRE operating language should distinguish transient degradation from true platform risk, and should document when to fail over, when to relocate, and when to restore from backup instead.",
                "After every major change or recovery test, the support model must capture lessons learned, updated thresholds, and the exact evidence used to prove service restoration.",
            ],
        ),
        _section(
            f"Security and compliance evidence pack {iteration}",
            [
                "Security evidence should align identity, privilege, certificates, network segmentation, policy enforcement, runtime findings, and audit event generation to named control objectives.",
                "Governance evidence for multicluster estates should identify which policies are inherited, which are cluster-specific, how waivers are approved, and how drift is detected and remediated.",
                "Compliance conversations are strongest when the pack explains not only what control exists, but where it is enforced, who reviews it, and what artifact proves continued compliance.",
                f"This evidence round focuses on the following domains: {' | '.join(group_summaries[:8])}.",
                "For delivery lanes, the evidence pack should include GitOps tenancy, promotion gates, secret handling, signed or validated content paths, and rollback authorization boundaries.",
                "For resilience lanes, the evidence pack should include backup immutability or protection assumptions, restore validation, DR exercises, and post-event attestation requirements.",
                "Risk acceptance items, open gaps, and temporary exceptions must be visible in the architecture pack so downstream implementation teams do not inherit hidden assumptions.",
            ],
        ),
    ] + (
        [
            _section(
                f"Low-level deployment matrix {iteration}",
                [
                    f"Low-level deployment matrix {iteration} maps component placement, namespace boundaries, operator dependencies, ingress exposure, secrets, certificates, and supporting infrastructure for {component_names}.",
                    "Each component row should capture environment scope, cluster scope, namespace or project placement, required operators, storage dependencies, network policy assumptions, and monitoring hooks.",
                    "The matrix should also track deployment order, rollback dependency, configuration source of truth, and whether the component is managed by GitOps, imperative automation, or operator reconciliation.",
                    "Integration dependencies should explicitly record DNS names, routes, service accounts, certificates, firewall paths, storage classes, and recovery responsibilities.",
                    "The implementation team should be able to walk this matrix during build, upgrade, and recovery without needing to reinterpret the HLD narrative.",
                    "Every matrix entry should end with validation evidence, expected healthy signal, and an escalation pointer for support operations.",
                ],
            ),
            _section(
                f"Validation, rollback, and change control {iteration}",
                [
                    "Rollback design must identify the last-known-good state, protected data boundary, authorization path, and the exact signals that tell the team rollback is safer than continuing the change.",
                    "Validation should cover happy path, degraded path, restart path, certificate path, backup state, monitoring signal, and application reachability across every major architecture boundary.",
                    "Change control artifacts should reference maintenance window prerequisites, stakeholder approvals, health checks before and after change, and post-change evidence retention requirements.",
                    f"This validation round reviews {len(nodes)} components and {len(edges)} primary relationships in the architecture pack.",
                    "Where GitOps or multicluster promotion exists, change control should validate sync health, drift reconciliation, policy compliance, and impact on dependent clusters or recovery targets.",
                    "Where recovery services exist, the rollback conversation must explicitly distinguish restore, failover, relocate, and failback so actions remain deterministic during incident response.",
                ],
            ),
        ]
        if document_type == "lld"
        else []
    )


def _domain_lines(group: str, group_nodes: list[DiagramNode], document_type: str) -> list[str]:
    domain_title = GROUP_LABELS.get(group, group.title())
    lines = [
        f"{domain_title} scope: this domain contains {len(group_nodes)} primary component(s) and establishes the responsibility boundary for the {document_type.upper()} pack.",
        f"Architecture intent: keep the {domain_title.lower()} lane explicit so ownership, sequencing, and support boundaries are reviewable by platform, security, network, and application teams.",
    ]
    for node in group_nodes:
        lines.extend(
            [
                f"Component: {node.label}. Purpose: {node.detail}",
                f"Design expectation for {node.label}: define placement, dependencies, scaling boundaries, security controls, and operational ownership before implementation sign-off.",
                f"Operational note for {node.label}: capture health indicators, failure symptoms, and the first-response workflow for this component within the target operating model.",
            ]
        )
        if document_type == "lld":
            lines.extend(
                [
                    f"Implementation detail for {node.label}: record namespace or cluster placement, resource assumptions, required operators, DNS or ingress needs, and lifecycle dependencies.",
                    f"Validation detail for {node.label}: include deployment checks, rollback conditions, security verification, and observability signals that indicate readiness or degradation.",
                ]
            )
    return lines


def _component_appendix_sections(nodes: list[DiagramNode], document_type: str) -> list[dict[str, Any]]:
    sections: list[dict[str, Any]] = []
    for node in nodes:
        sections.append(
            _section(
                f"Component specification — {node.label}",
                [
                    f"Role: {node.label} operates in the {GROUP_LABELS.get(node.group, node.group.title())} domain.",
                    f"Purpose: {node.detail}",
                    "Placement and topology: document the exact site, cluster, namespace, or host placement expected for this component and identify any anti-affinity or failure-domain expectations.",
                    "Dependencies: identify upstream identity, DNS, registry, storage, logging, monitoring, certificate, and network controls that must be in place before this component is activated.",
                    "Security controls: define access control, secrets handling, certificate ownership, segmentation expectations, audit requirements, and hardening responsibilities.",
                    "Performance and scaling: define expected throughput, concurrency, storage, CPU, memory, and horizontal or vertical growth guardrails.",
                    "Operations and support: capture routine maintenance, upgrade sequencing, backup expectations, health checks, SLO ownership, and evidence capture requirements.",
                    "Failure handling: describe degraded mode, restart or failover behavior, rollback approach, and the escalation path when this component becomes unavailable.",
                    "Observability: list the metrics, events, logs, alerts, and dashboards that will prove this component is healthy and supportable.",
                    "Implementation checkpoints: include prerequisite validation, configuration completion criteria, and production readiness checks for stakeholder sign-off.",
                ]
                + (
                    [
                        "Low-level implementation notes: include deployment order, resource manifests or operator CRs, namespace conventions, integration endpoints, and any site-specific overrides.",
                        "Day-2 change model: describe patching, certificate renewal, capacity review, routine runbook execution, and validation after change windows.",
                    ]
                    if document_type == "lld"
                    else []
                ),
            )
        )
        if document_type == "lld":
            sections.append(
                _section(
                    f"Verification and rollback — {node.label}",
                    [
                        f"Pre-deployment checks for {node.label}: confirm infrastructure readiness, DNS and certificate prerequisites, firewall paths, storage preparation, and access delegation.",
                        f"Deployment verification for {node.label}: verify the control objective, happy path, degraded path, monitoring signal, and support handoff evidence.",
                        f"Security verification for {node.label}: validate least privilege, segmentation, secret handling, compliance evidence, and audit event generation.",
                        f"Rollback checkpoints for {node.label}: define the last-known-good state, data protection measure, rollback trigger, stakeholder approvals, and service validation after recovery.",
                        f"Operational readiness for {node.label}: confirm dashboards, alerts, ownership matrix, runbook links, and spare capacity assumptions for steady state and incident scenarios.",
                    ],
                )
            )
    return sections


def _interface_appendix_sections(edges: list[DiagramEdge], document_type: str) -> list[dict[str, Any]]:
    sections: list[dict[str, Any]] = []
    for index, edge in enumerate(edges, start=1):
        sections.append(
            _section(
                f"Interface and dependency matrix {index}",
                [
                    f"Flow: {edge.source} -> {edge.target}{f' ({edge.label})' if edge.label else ''}.",
                    "Purpose of the interface: explain what is exchanged across this boundary, why the dependency exists, and who owns each side of the relationship.",
                    "Connectivity and policy: identify DNS, VIP, route, load-balancing, proxy, firewall, certificate, network-policy, or service-mesh assumptions for this dependency.",
                    "Security expectation: describe authentication, authorization, encryption, trust anchors, and audit requirements associated with this interface.",
                    "Failure behavior: define timeout, retry, fallback, backlog, or failover behavior if the relationship degrades or becomes unavailable.",
                ]
                + (
                    [
                        "Low-level mapping: record endpoint names, namespace or cluster source and destination, expected port exposure, secret usage, and deployment sequencing dependencies.",
                        "Validation steps: test normal operation, degraded operation, recovery, and rollback across this interface before production sign-off.",
                    ]
                    if document_type == "lld"
                    else []
                ),
            )
        )
    return sections


def _padding_sections(
    *,
    document_type: str,
    grouped: dict[str, list[DiagramNode]],
    nodes: list[DiagramNode],
    edges: list[DiagramEdge],
) -> list[dict[str, Any]]:
    sections: list[dict[str, Any]] = []
    for group in GROUP_ORDER:
        group_nodes = grouped.get(group) or []
        if not group_nodes:
            continue
        sections.append(
            _section(
                f"Appendix — {GROUP_LABELS.get(group, group.title())} implementation checklist",
                [
                    f"Checklist objective: turn the {GROUP_LABELS.get(group, group.title()).lower()} domain into an executable workstream with explicit prerequisites, validations, and ownership boundaries.",
                    "Prerequisites: infrastructure readiness, network reachability, DNS, time sync, certificates, access delegation, observability hooks, and approved change records.",
                    "Configuration checkpoints: cluster or namespace placement, operator availability, quota or policy alignment, secrets preparation, storage availability, and ingress exposure rules.",
                    "Security checkpoints: identity, privilege, audit, segmentation, certificate trust, secret rotation, and evidence retention expectations must be captured before go-live.",
                    "Operational checkpoints: dashboards, alerts, runbooks, backup coverage, maintenance windows, and handoff readiness are validated before production use.",
                    f"Components in this checklist: {'; '.join(node.label for node in group_nodes)}.",
                ]
                + (
                    [
                        "Detailed execution notes: record manifest locations, operator CRs, parameter sources, rollback criteria, and validation scripts or commands used by the delivery team.",
                        "Post-change validation: record smoke tests, platform health checks, security evidence collection, and stakeholder sign-off requirements for the domain.",
                    ]
                    if document_type == "lld"
                    else []
                ),
            )
        )
    sections.extend(_component_appendix_sections(nodes, document_type))
    sections.extend(_interface_appendix_sections(edges, document_type))
    return sections


def _node_icon_profile(node: DiagramNode) -> dict[str, str | float]:
    text = f"{node.label} {node.detail}".lower()
    if any(token in text for token in ["bond0", "eth0", "eth1", "console port", "bmc", "idrac", "ilo"]):
        return {
            "kind": "nic",
            "accent": "#005F4B",
            "drawio_style": "sketch=0;pointerEvents=1;shadow=0;dashed=0;html=1;strokeColor=none;fillColor=#005F4B;labelPosition=center;verticalLabelPosition=bottom;verticalAlign=top;align=center;outlineConnect=0;shape=mxgraph.veeam2.network_card;",
            "drawio_value": "",
            "width": 28.0,
            "height": 20.0,
        }
    if any(token in text for token in ["acm", "hub cluster", "fleet", "managed cluster", "multicluster"]):
        return {
            "kind": "acm",
            "accent": "#FF3333",
            "drawio_style": "rounded=1;whiteSpace=wrap;html=1;fillColor=#FF3333;strokeColor=#FFFFFF;fontStyle=1;fontColor=#ffffff;align=center;verticalAlign=middle;arcSize=20;",
            "drawio_value": "ACM",
            "width": 34.0,
            "height": 20.0,
        }
    if any(token in text for token in ["firewall", "policy", "rbac", "scc", "acs", "oauth", "ldap", "security", "governance", "segmentation"]):
        return {
            "kind": "firewall",
            "accent": "#DA4026",
            "drawio_style": "sketch=0;pointerEvents=1;shadow=0;dashed=0;html=1;strokeColor=none;labelPosition=center;verticalLabelPosition=bottom;verticalAlign=top;outlineConnect=0;align=center;shape=mxgraph.office.concepts.firewall;fillColor=#DA4026;",
            "drawio_value": "",
            "width": 28.0,
            "height": 24.0,
        }
    if any(token in text for token in ["switch", "ingress", "route", "dns", "load balancer", "network", "submariner"]):
        return {
            "kind": "switch",
            "accent": "#6881B3",
            "drawio_style": "fontColor=#0066CC;verticalAlign=top;verticalLabelPosition=bottom;labelPosition=center;align=center;html=1;outlineConnect=0;fillColor=#CCCCCC;strokeColor=#6881B3;gradientColor=none;gradientDirection=north;strokeWidth=2;shape=mxgraph.networks.switch;",
            "drawio_value": "",
            "width": 34.0,
            "height": 16.0,
        }
    if any(token in text for token in ["virtual machine", "kubevirt", "cnv", "hyperconverged", "vm workload"]):
        return {
            "kind": "vm",
            "accent": "#4495D1",
            "drawio_style": "shadow=0;dashed=0;html=1;strokeColor=none;fillColor=#4495D1;labelPosition=center;verticalLabelPosition=bottom;verticalAlign=top;align=center;outlineConnect=0;shape=mxgraph.veeam.2d.virtual_machine;",
            "drawio_value": "",
            "width": 26.0,
            "height": 26.0,
        }
    if any(token in text for token in ["storage", "odf", "oadp", "snapshot", "backup", "restore", "disk", "volume", "ceph", "rook", "persistent"]):
        return {
            "kind": "disk",
            "accent": "#7C3AED",
            "drawio_style": "image;aspect=fixed;html=1;points=[];align=center;fontSize=12;image=img/lib/azure2/other/Disk_Pool.svg;",
            "drawio_value": "",
            "width": 28.0,
            "height": 26.0,
        }
    if any(token in text for token in ["bare metal", "server", "worker", "master node", "control plane node", "bootstrap"]):
        return {
            "kind": "server",
            "accent": "#005F4B",
            "drawio_style": "image;aspect=fixed;perimeter=ellipsePerimeter;html=1;align=center;fontSize=12;verticalAlign=top;fontColor=#364149;shadow=0;dashed=0;image=img/lib/cumulus/server_bare_metal.svg;",
            "drawio_value": "",
            "width": 30.0,
            "height": 22.0,
        }
    if any(token in text for token in ["gitops", "tekton", "quay", "application", "workload", "monitoring", "logging", "runbook", "observability", "pod"]):
        return {
            "kind": "pod",
            "accent": "#2875E2",
            "drawio_style": KUBERNETES_POD_ICON_STYLE,
            "drawio_value": "",
            "width": 28.0,
            "height": 18.0,
        }
    if node.group == "control-plane":
        return {
            "kind": "openshift",
            "accent": "#EE0000",
            "drawio_style": "image;sketch=0;aspect=fixed;html=1;points=[];align=center;fontSize=12;image=img/lib/mscae/OpenShift.svg;",
            "drawio_value": "",
            "width": 26.0,
            "height": 26.0,
        }
    if node.group == "data":
        return {
            "kind": "disk",
            "accent": "#7C3AED",
            "drawio_style": "image;aspect=fixed;html=1;points=[];align=center;fontSize=12;image=img/lib/azure2/other/Disk_Pool.svg;",
            "drawio_value": "",
            "width": 28.0,
            "height": 26.0,
        }
    if node.group in {"delivery", "workload", "operations"}:
        return {
            "kind": "pod",
            "accent": "#2875E2",
            "drawio_style": KUBERNETES_POD_ICON_STYLE,
            "drawio_value": "",
            "width": 28.0,
            "height": 18.0,
        }
    return {
        "kind": "generic",
        "accent": str(GROUP_STYLES.get(node.group, {"stroke": "#475569"})["stroke"]),
        "drawio_style": "ellipse;whiteSpace=wrap;html=1;fillColor=#ffffff;strokeColor=#475569;strokeWidth=2;",
        "drawio_value": "",
        "width": 22.0,
        "height": 22.0,
    }


def _svg_icon_markup(kind: str, accent: str, x: float, y: float) -> str:
    if kind == "openshift":
        return (
            f'<circle cx="{x + 13}" cy="{y + 13}" r="10" fill="none" stroke="{accent}" stroke-width="3"/>'
            f'<circle cx="{x + 13}" cy="{y + 13}" r="4.5" fill="none" stroke="{accent}" stroke-width="2"/>'
        )
    if kind == "acm":
        return (
            f'<rect x="{x}" y="{y + 4}" width="28" height="18" rx="6" fill="{accent}" stroke="#FFFFFF" stroke-width="1.5"/>'
            f'<text x="{x + 14}" y="{y + 17}" font-size="9" font-weight="700" text-anchor="middle" fill="#FFFFFF">ACM</text>'
        )
    if kind == "switch":
        ports = ''.join(f'<circle cx="{x + 7 + (offset * 5)}" cy="{y + 16}" r="1.2" fill="#FFFFFF"/>' for offset in range(4))
        return (
            f'<rect x="{x}" y="{y + 8}" width="30" height="12" rx="3" fill="#D1D5DB" stroke="{accent}" stroke-width="2"/>'
            f'{ports}'
        )
    if kind == "firewall":
        bricks = []
        for row in range(2):
            for column in range(3):
                brick_x = x + 2 + (column * 8) + (4 if row else 0)
                brick_y = y + 4 + (row * 8)
                bricks.append(f'<rect x="{brick_x}" y="{brick_y}" width="7" height="6" rx="1" fill="{accent}"/>')
        return ''.join(bricks)
    if kind == "vm":
        return (
            f'<rect x="{x + 2}" y="{y + 3}" width="24" height="16" rx="2" fill="#E0F2FE" stroke="{accent}" stroke-width="2"/>'
            f'<rect x="{x + 10}" y="{y + 20}" width="8" height="2.5" rx="1" fill="{accent}"/>'
        )
    if kind == "disk":
        return (
            f'<ellipse cx="{x + 14}" cy="{y + 8}" rx="10" ry="4" fill="#F5F3FF" stroke="{accent}" stroke-width="2"/>'
            f'<rect x="{x + 4}" y="{y + 8}" width="20" height="11" fill="#F5F3FF" stroke="{accent}" stroke-width="2"/>'
            f'<ellipse cx="{x + 14}" cy="{y + 19}" rx="10" ry="4" fill="#F5F3FF" stroke="{accent}" stroke-width="2"/>'
        )
    if kind == "nic":
        return (
            f'<rect x="{x + 2}" y="{y + 6}" width="24" height="14" rx="2" fill="#ECFDF5" stroke="{accent}" stroke-width="2"/>'
            f'<rect x="{x + 7}" y="{y + 3}" width="14" height="4" rx="1" fill="{accent}"/>'
            f'<circle cx="{x + 9}" cy="{y + 13}" r="1.5" fill="{accent}"/>'
            f'<circle cx="{x + 14}" cy="{y + 13}" r="1.5" fill="{accent}"/>'
            f'<circle cx="{x + 19}" cy="{y + 13}" r="1.5" fill="{accent}"/>'
        )
    if kind == "server":
        bays = ''.join(f'<rect x="{x + 6}" y="{y + 6 + (slot * 5)}" width="16" height="2.5" rx="1" fill="#FFFFFF"/>' for slot in range(3))
        return (
            f'<rect x="{x + 2}" y="{y + 2}" width="24" height="22" rx="3" fill="#ECFDF5" stroke="{accent}" stroke-width="2"/>'
            f'{bays}'
        )
    if kind == "pod":
        return (
            f'<path d="M {x + 14} {y + 1} L {x + 25} {y + 7} L {x + 22} {y + 19} L {x + 14} {y + 25} L {x + 6} {y + 19} L {x + 3} {y + 7} Z" fill="#DBEAFE" stroke="{accent}" stroke-width="2"/>'
            f'<circle cx="{x + 14}" cy="{y + 13}" r="3" fill="{accent}"/>'
        )
    return f'<circle cx="{x + 14}" cy="{y + 14}" r="9" fill="#FFFFFF" stroke="{accent}" stroke-width="2"/>'


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


def _render_svg(
    title: str,
    summary: str,
    nodes: list[DiagramNode],
    edges: list[DiagramEdge],
    positions: dict[str, dict[str, float]],
    group_boxes: dict[str, dict[str, float]],
    zones: list[dict[str, Any]],
    total_width: float,
    total_height: float,
) -> str:
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{int(total_width)}" height="{int(total_height)}" viewBox="0 0 {int(total_width)} {int(total_height)}">',
        '<rect width="100%" height="100%" fill="#F8FAFC"/>',
        f'<text x="48" y="36" font-size="24" font-weight="700" fill="#0F172A">{escape(title)}</text>',
        f'<text x="48" y="56" font-size="12" fill="#475569">{escape(summary)}</text>',
    ]
    for zone in zones:
        dashed = ' stroke-dasharray="10 8"' if zone.get("dashed") else ""
        parts.append(
            f'<rect x="{zone["x"]}" y="{zone["y"]}" width="{zone["width"]}" height="{zone["height"]}" rx="{zone.get("radius", 18)}" fill="{zone["fill"]}" fill-opacity="0.55" stroke="{zone["stroke"]}" stroke-width="2"{dashed}/>'
        )
        parts.append(
            f'<text x="{zone["x"] + 14}" y="{zone["y"] + 24}" font-size="14" font-weight="700" fill="#0F172A">{escape(zone["title"])}</text>'
        )
        next_y = zone["y"] + 42
        if zone.get("subtitle"):
            for line in _wrap_text(str(zone["subtitle"]), 88):
                parts.append(
                    f'<text x="{zone["x"] + 14}" y="{next_y}" font-size="11" fill="#475569">{escape(line)}</text>'
                )
                next_y += 14
        for note in zone.get("notes", []):
            for line in _wrap_text(str(note), 86):
                parts.append(
                    f'<text x="{zone["x"] + 18}" y="{next_y}" font-size="10.5" fill="#334155">{escape(line)}</text>'
                )
                next_y += 13
            next_y += 2
    for group, box in group_boxes.items():
        style = GROUP_STYLES[group]
        parts.append(
            f'<rect x="{box["x"]}" y="{box["y"]}" width="{box["width"]}" height="{box["height"]}" rx="18" fill="{style["fill"]}" fill-opacity="0.55" stroke="{style["stroke"]}" stroke-width="2"/>'
        )
        parts.append(
            f'<rect x="{box["x"] + 16}" y="{box["y"] + 10}" width="42" height="18" rx="9" fill="{style["stroke"]}"/>'
        )
        parts.append(
            f'<text x="{box["x"] + 37}" y="{box["y"] + 23}" font-size="10" font-weight="700" text-anchor="middle" fill="#FFFFFF">{escape(GROUP_ICON_LABELS.get(group, group[:3].upper()))}</text>'
        )
        parts.append(
            f'<text x="{box["x"] + 66}" y="{box["y"] + 24}" font-size="14" font-weight="700" fill="#0F172A">{escape(GROUP_LABELS.get(group, group.title()))}</text>'
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
        icon_profile = _node_icon_profile(node)
        parts.append(
            f'<rect x="{position["x"]}" y="{position["y"]}" width="{position["width"]}" height="{position["height"]}" rx="14" fill="#FFFFFF" stroke="{style["stroke"]}" stroke-width="2"/>'
        )
        parts.append(_svg_icon_markup(str(icon_profile["kind"]), str(icon_profile["accent"]), position["x"] + 10, position["y"] + 8))
        title_lines = _wrap_text(node.label, 24)
        for index, line in enumerate(title_lines):
            parts.append(
                f'<text x="{position["x"] + 50}" y="{position["y"] + 24 + (index * 15)}" font-size="13" font-weight="700" fill="#0F172A">{escape(line)}</text>'
            )
        detail_lines = _wrap_text(node.detail, 30)
        for index, line in enumerate(detail_lines[:2]):
            parts.append(
                f'<text x="{position["x"] + 50}" y="{position["y"] + 52 + (index * 13)}" font-size="11" fill="#475569">{escape(line)}</text>'
            )
    legend_y = total_height - 36
    legend_x = 48
    present_groups = [group for group in GROUP_ORDER if group in group_boxes] or [group for group in GROUP_ORDER if any(node.group == group for node in nodes)]
    for group in present_groups:
        style = GROUP_STYLES[group]
        parts.append(f'<rect x="{legend_x}" y="{legend_y}" width="14" height="14" rx="4" fill="{style["fill"]}" stroke="{style["stroke"]}" stroke-width="1.5"/>')
        parts.append(f'<text x="{legend_x + 22}" y="{legend_y + 11}" font-size="11" fill="#334155">{escape(GROUP_LABELS.get(group, group.title()))}</text>')
        legend_x += 148
    parts.append('</svg>')
    return ''.join(parts)


def _drawio_text(value: str) -> str:
    return escape(value).replace("\n", "&#xa;")


def _append_drawio_page_frame(root: ET.Element, *, page: dict[str, Any], cell_counter: int, page_total: int) -> int:
    frame_id = str(cell_counter)
    cell_counter += 1
    frame_cell = ET.SubElement(
        root,
        "mxCell",
        id=frame_id,
        value="",
        style="rounded=1;whiteSpace=wrap;html=1;fillColor=#FFFFFF;strokeColor=#CBD5E1;strokeWidth=2;arcSize=18;",
        vertex="1",
        parent="1",
    )
    ET.SubElement(frame_cell, "mxGeometry", x="18", y="18", width=str(max(400, int(page["total_width"]) - 36)), height=str(max(260, int(page["total_height"]) - 36)), **{"as": "geometry"})

    header_id = str(cell_counter)
    cell_counter += 1
    header_cell = ET.SubElement(
        root,
        "mxCell",
        id=header_id,
        value="",
        style="rounded=1;whiteSpace=wrap;html=1;fillColor=#111827;strokeColor=#111827;strokeWidth=1;arcSize=12;",
        vertex="1",
        parent="1",
    )
    ET.SubElement(header_cell, "mxGeometry", x="28", y="22", width=str(max(360, int(page["total_width"]) - 56)), height="54", **{"as": "geometry"})

    brand_id = str(cell_counter)
    cell_counter += 1
    brand_value = _drawio_text("OPENSHIFT 4.20+\nArchitecture review pack")
    brand_cell = ET.SubElement(
        root,
        "mxCell",
        id=brand_id,
        value=brand_value,
        style="text;html=1;strokeColor=none;fillColor=none;align=left;verticalAlign=middle;fontSize=10;fontColor=#E2E8F0;fontStyle=1;",
        vertex="1",
        parent="1",
    )
    ET.SubElement(brand_cell, "mxGeometry", x="46", y="29", width="200", height="34", **{"as": "geometry"})

    meta_id = str(cell_counter)
    cell_counter += 1
    meta_value = _drawio_text(
        f"Page {page['page_number']} / {page_total}\n{page['page_name']}\nSenior Red Hat OpenShift architect"
    )
    meta_cell = ET.SubElement(
        root,
        "mxCell",
        id=meta_id,
        value=meta_value,
        style="rounded=1;whiteSpace=wrap;html=1;fillColor=#FFFFFF;strokeColor=#111827;strokeWidth=1.5;fontSize=10;fontStyle=1;align=left;verticalAlign=middle;spacing=8;",
        vertex="1",
        parent="1",
    )
    ET.SubElement(meta_cell, "mxGeometry", x=str(max(280, int(page["total_width"]) - 326)), y="28", width="270", height="42", **{"as": "geometry"})
    return cell_counter


def _append_drawio_security_overlays(root: ET.Element, *, page: dict[str, Any], cell_counter: int) -> int:
    zone_lookup = {str(zone.get("title", "")): zone for zone in page.get("zones", [])}
    dmz_zone = zone_lookup.get("DMZ and edge ingress lane")
    access_zone = zone_lookup.get("Firewall, bastion, and access lane")
    core_zone = zone_lookup.get("Cluster core and service plane")
    if dmz_zone:
        dmz_id = str(cell_counter)
        cell_counter += 1
        dmz_cell = ET.SubElement(root, "mxCell", id=dmz_id, value=_drawio_text("DMZ"), style="rounded=1;whiteSpace=wrap;html=1;fillColor=#FFF7ED;strokeColor=#EA580C;strokeWidth=2;fontStyle=1;fontSize=16;align=center;verticalAlign=middle;", vertex="1", parent="1")
        ET.SubElement(dmz_cell, "mxGeometry", x=str(dmz_zone["x"] + 18), y=str(dmz_zone["y"] + 16), width="88", height="34", **{"as": "geometry"})
    if access_zone:
        for offset in range(3):
            firewall_id = str(cell_counter)
            cell_counter += 1
            firewall_cell = ET.SubElement(root, "mxCell", id=firewall_id, value="", style="sketch=0;pointerEvents=1;shadow=0;dashed=0;html=1;strokeColor=none;labelPosition=center;verticalLabelPosition=bottom;verticalAlign=top;outlineConnect=0;align=center;shape=mxgraph.office.concepts.firewall;fillColor=#DA4026;", vertex="1", parent="1")
            ET.SubElement(firewall_cell, "mxGeometry", x=str(access_zone["x"] + 210 + (offset * 310)), y=str(access_zone["y"] + 18), width="38", height="34", **{"as": "geometry"})
        trust_id = str(cell_counter)
        cell_counter += 1
        trust_cell = ET.SubElement(root, "mxCell", id=trust_id, value=_drawio_text("Trust boundary\nFirewall / bastion / identity controls"), style="rounded=1;whiteSpace=wrap;html=1;fillColor=#FFFFFF;strokeColor=#DC2626;strokeWidth=2;fontSize=11;fontStyle=1;align=center;verticalAlign=middle;", vertex="1", parent="1")
        ET.SubElement(trust_cell, "mxGeometry", x=str(access_zone["x"] + access_zone["width"] - 270), y=str(access_zone["y"] + 16), width="228", height="52", **{"as": "geometry"})
    if core_zone:
        protected_id = str(cell_counter)
        cell_counter += 1
        protected_cell = ET.SubElement(root, "mxCell", id=protected_id, value=_drawio_text("Protected cluster core"), style="rounded=1;whiteSpace=wrap;html=1;fillColor=#DCFCE7;strokeColor=#16A34A;strokeWidth=2;fontSize=14;fontStyle=1;align=center;verticalAlign=middle;", vertex="1", parent="1")
        ET.SubElement(protected_cell, "mxGeometry", x=str(core_zone["x"] + 18), y=str(core_zone["y"] + 16), width="196", height="32", **{"as": "geometry"})
    return cell_counter


def _append_drawio_rack_overlays(root: ET.Element, *, page: dict[str, Any], cell_counter: int) -> int:
    rack_zones = [zone for zone in page.get("zones", []) if str(zone.get("title", "")).startswith("Rack ")]
    for rack_zone in rack_zones:
        shell_id = str(cell_counter)
        cell_counter += 1
        shell_cell = ET.SubElement(root, "mxCell", id=shell_id, value="", style="rounded=0;whiteSpace=wrap;html=1;fillColor=#FFFFFF;strokeColor=#111827;strokeWidth=1.6;", vertex="1", parent="1")
        ET.SubElement(shell_cell, "mxGeometry", x=str(rack_zone["x"] + 22), y=str(rack_zone["y"] + 38), width=str(rack_zone["width"] - 44), height=str(rack_zone["height"] - 86), **{"as": "geometry"})

        stripe_specs = [
            ("VM", "#4A90E2", 78),
            ("vSAN", "#16A34A", 54),
            ("Hypervisor", "#166534", 34),
            ("Bare metal", "#334155", 22),
        ]
        current_y = rack_zone["y"] + rack_zone["height"] - 22
        for label, fill, height in reversed(stripe_specs):
            current_y -= height
            stripe_id = str(cell_counter)
            cell_counter += 1
            stripe_cell = ET.SubElement(root, "mxCell", id=stripe_id, value=_drawio_text(label), style=f"rounded=0;whiteSpace=wrap;html=1;fillColor={fill};strokeColor={fill};fontColor=#FFFFFF;fontSize=11;fontStyle=1;align=center;verticalAlign=middle;", vertex="1", parent="1")
            ET.SubElement(stripe_cell, "mxGeometry", x=str(rack_zone["x"] + 22), y=str(current_y), width=str(rack_zone["width"] - 44), height=str(height), **{"as": "geometry"})

        for slot in range(3):
            server_id = str(cell_counter)
            cell_counter += 1
            server_cell = ET.SubElement(root, "mxCell", id=server_id, value="", style="image;aspect=fixed;perimeter=ellipsePerimeter;html=1;align=center;fontSize=12;verticalAlign=top;fontColor=#364149;shadow=0;dashed=0;image=img/lib/cumulus/server_bare_metal.svg;", vertex="1", parent="1")
            ET.SubElement(server_cell, "mxGeometry", x=str(rack_zone["x"] + 36 + (slot * ((rack_zone["width"] - 120) / 2))), y=str(rack_zone["y"] + rack_zone["height"] - 44), width="78", height="18", **{"as": "geometry"})

    vlan_zones = [zone for zone in page.get("zones", []) if str(zone.get("title", "")).endswith("VLAN")]
    for vlan_zone in vlan_zones:
        switch_fill = "#0284C7" if "User" in str(vlan_zone.get("title", "")) else "#16A34A"
        switch_label = "User VLAN switch fabric" if "User" in str(vlan_zone.get("title", "")) else "Management VLAN switch fabric"
        switch_id = str(cell_counter)
        cell_counter += 1
        switch_cell = ET.SubElement(root, "mxCell", id=switch_id, value="", style="fontColor=#0066CC;verticalAlign=top;verticalLabelPosition=bottom;labelPosition=center;align=center;html=1;outlineConnect=0;fillColor=#CCCCCC;strokeColor=#6881B3;gradientColor=none;gradientDirection=north;strokeWidth=2;shape=mxgraph.networks.switch;", vertex="1", parent="1")
        ET.SubElement(switch_cell, "mxGeometry", x=str(vlan_zone["x"] + 22), y=str(vlan_zone["y"] + 18), width="160", height="24", **{"as": "geometry"})
        switch_text_id = str(cell_counter)
        cell_counter += 1
        switch_text = ET.SubElement(root, "mxCell", id=switch_text_id, value=_drawio_text(switch_label), style=f"text;html=1;strokeColor=none;fillColor=none;align=left;verticalAlign=middle;fontSize=11;fontStyle=1;fontColor={switch_fill};", vertex="1", parent="1")
        ET.SubElement(switch_text, "mxGeometry", x=str(vlan_zone["x"] + 196), y=str(vlan_zone["y"] + 17), width="220", height="22", **{"as": "geometry"})
    return cell_counter


def _append_drawio_legend(root: ET.Element, *, page: dict[str, Any], cell_counter: int) -> int:
    legend_width = 256
    legend_height = 150 if page.get("layout_mode") == "infra-topology" else 132
    legend_x = max(48, int(page["total_width"]) - legend_width - 34)
    legend_y = max(86, int(page["total_height"]) - legend_height - 32)

    legend_box_id = str(cell_counter)
    cell_counter += 1
    legend_box = ET.SubElement(root, "mxCell", id=legend_box_id, value="", style="rounded=1;whiteSpace=wrap;html=1;fillColor=#FFFFFF;strokeColor=#111827;strokeWidth=1.6;arcSize=16;", vertex="1", parent="1")
    ET.SubElement(legend_box, "mxGeometry", x=str(legend_x), y=str(legend_y), width=str(legend_width), height=str(legend_height), **{"as": "geometry"})

    legend_title_id = str(cell_counter)
    cell_counter += 1
    legend_title = ET.SubElement(root, "mxCell", id=legend_title_id, value=_drawio_text("Legend"), style="text;html=1;strokeColor=none;fillColor=none;align=center;verticalAlign=middle;fontSize=13;fontStyle=1;", vertex="1", parent="1")
    ET.SubElement(legend_title, "mxGeometry", x=str(legend_x + 88), y=str(legend_y + 8), width="80", height="20", **{"as": "geometry"})

    rows: list[tuple[str, str, str]] = [("swatch", "#2563EB", "OpenShift domain grouping")]
    if page.get("layout_mode") == "infra-topology":
        rows.extend([
            ("line-magenta", "#FF33FF", "User VLAN path"),
            ("line-green", "#16A34A", "Management VLAN / protected path"),
            ("firewall", "#DA4026", "Firewall / DMZ control"),
            ("pill", "#111827", "Rack / cluster review frame"),
        ])
    else:
        rows.extend([
            ("firewall", "#DA4026", "Firewall / bastion boundary"),
            ("line-green", "#16A34A", "Protected cluster plane"),
            ("pill", "#111827", "Page frame and review block"),
        ])

    current_y = legend_y + 34
    for marker, color, label in rows[:5]:
        if marker == "swatch":
            marker_id = str(cell_counter)
            cell_counter += 1
            marker_cell = ET.SubElement(root, "mxCell", id=marker_id, value="", style=f"rounded=1;whiteSpace=wrap;html=1;fillColor=#DBEAFE;strokeColor={color};strokeWidth=2;", vertex="1", parent="1")
            ET.SubElement(marker_cell, "mxGeometry", x=str(legend_x + 16), y=str(current_y), width="24", height="14", **{"as": "geometry"})
        elif marker.startswith("line"):
            marker_id = str(cell_counter)
            cell_counter += 1
            marker_cell = ET.SubElement(root, "mxCell", id=marker_id, value="", style=f"shape=line;strokeColor={color};strokeWidth=3;", vertex="1", parent="1")
            ET.SubElement(marker_cell, "mxGeometry", x=str(legend_x + 14), y=str(current_y + 7), width="28", height="1", **{"as": "geometry"})
        elif marker == "firewall":
            marker_id = str(cell_counter)
            cell_counter += 1
            marker_cell = ET.SubElement(root, "mxCell", id=marker_id, value="", style="sketch=0;pointerEvents=1;shadow=0;dashed=0;html=1;strokeColor=none;labelPosition=center;verticalLabelPosition=bottom;verticalAlign=top;outlineConnect=0;align=center;shape=mxgraph.office.concepts.firewall;fillColor=#DA4026;", vertex="1", parent="1")
            ET.SubElement(marker_cell, "mxGeometry", x=str(legend_x + 15), y=str(current_y - 2), width="24", height="22", **{"as": "geometry"})
        else:
            marker_id = str(cell_counter)
            cell_counter += 1
            marker_cell = ET.SubElement(root, "mxCell", id=marker_id, value="", style=f"rounded=1;whiteSpace=wrap;html=1;fillColor={color};strokeColor={color};arcSize=18;", vertex="1", parent="1")
            ET.SubElement(marker_cell, "mxGeometry", x=str(legend_x + 15), y=str(current_y), width="26", height="12", **{"as": "geometry"})

        label_id = str(cell_counter)
        cell_counter += 1
        label_cell = ET.SubElement(root, "mxCell", id=label_id, value=_drawio_text(label), style="text;html=1;strokeColor=none;fillColor=none;align=left;verticalAlign=middle;fontSize=11;", vertex="1", parent="1")
        ET.SubElement(label_cell, "mxGeometry", x=str(legend_x + 52), y=str(current_y - 2), width=str(legend_width - 66), height="20", **{"as": "geometry"})
        current_y += 24
    return cell_counter


def _build_drawio_xml(title: str, diagram_pages: list[dict[str, Any]]) -> str:
    mxfile = ET.Element("mxfile", host="app.diagrams.net", modified=datetime.now(timezone.utc).isoformat(), agent="openshift-sre-architect", version="24.7.17")
    page_total = len(diagram_pages)
    for page in diagram_pages:
        diagram = ET.SubElement(mxfile, "diagram", id=str(page["page_id"]), name=str(page["page_name"] or title))
        graph_model = ET.SubElement(
            diagram,
            "mxGraphModel",
            dx="1200",
            dy="700",
            grid="1",
            gridSize="10",
            guides="1",
            tooltips="1",
            connect="1",
            arrows="1",
            fold="1",
            page="1",
            pageScale="1",
            pageWidth=str(int(page["total_width"])),
            pageHeight=str(int(page["total_height"])),
            math="0",
            shadow="0",
        )
        root = ET.SubElement(graph_model, "root")
        ET.SubElement(root, "mxCell", id="0")
        ET.SubElement(root, "mxCell", id="1", parent="0")

        cell_counter = 2
        cell_counter = _append_drawio_page_frame(root, page=page, cell_counter=cell_counter, page_total=page_total)
        title_cell = ET.SubElement(root, "mxCell", id=str(cell_counter), value=_drawio_text(page["title"]), style="text;html=1;strokeColor=none;fillColor=none;align=left;verticalAlign=middle;fontSize=20;fontStyle=1;", vertex="1", parent="1")
        ET.SubElement(title_cell, "mxGeometry", x="46", y="30", width=str(max(520, int(page["total_width"]) - 420)), height="26", **{"as": "geometry"})
        cell_counter += 1
        summary_cell = ET.SubElement(root, "mxCell", id=str(cell_counter), value=_drawio_text(page["summary"]), style="text;html=1;strokeColor=none;fillColor=none;align=left;verticalAlign=middle;fontSize=11;fontColor=#475569;", vertex="1", parent="1")
        ET.SubElement(summary_cell, "mxGeometry", x="46", y="56", width=str(max(520, int(page["total_width"]) - 420)), height="18", **{"as": "geometry"})
        cell_counter += 1

        for zone in page.get("zones", []):
            zone_lines = [zone["title"]]
            if zone.get("subtitle"):
                zone_lines.append(str(zone["subtitle"]))
            zone_lines.extend(str(item) for item in zone.get("notes", []))
            zone_value = "\n".join(zone_lines)
            zone_cell = ET.SubElement(
                root,
                "mxCell",
                id=str(cell_counter),
                value=_drawio_text(zone_value),
                style=(
                    f"rounded=1;whiteSpace=wrap;html=1;fillColor={zone['fill']};fillOpacity=55;strokeColor={zone['stroke']};"
                    f"strokeWidth=2;fontStyle=1;fontSize=13;align=left;verticalAlign=top;spacingTop=8;spacingLeft=12;"
                    + ("dashed=1;dashPattern=12 12;" if zone.get("dashed") else "")
                ),
                vertex="1",
                parent="1",
            )
            ET.SubElement(
                zone_cell,
                "mxGeometry",
                x=str(zone["x"]),
                y=str(zone["y"]),
                width=str(zone["width"]),
                height=str(zone["height"]),
                **{"as": "geometry"},
            )
            cell_counter += 1

        if page.get("layout_mode") == "security-lanes":
            cell_counter = _append_drawio_security_overlays(root, page=page, cell_counter=cell_counter)
        if page.get("layout_mode") in {"infra-topology", "onprem-holistic"}:
            cell_counter = _append_drawio_rack_overlays(root, page=page, cell_counter=cell_counter)

        node_ids: dict[str, str] = {}
        for group, box in page["group_boxes"].items():
            style = GROUP_STYLES[group]
            group_id = str(cell_counter)
            cell_counter += 1
            group_value = _drawio_text(f"{GROUP_ICON_LABELS.get(group, group[:3].upper())} • {GROUP_LABELS.get(group, group.title())}")
            group_cell = ET.SubElement(root, "mxCell", id=group_id, value=group_value, style=f"rounded=1;whiteSpace=wrap;html=1;fillColor={style['fill']};strokeColor={style['stroke']};fontStyle=1;fontSize=14;align=left;verticalAlign=top;spacingTop=8;spacingLeft=12;", vertex="1", parent="1")
            ET.SubElement(group_cell, "mxGeometry", x=str(box["x"]), y=str(box["y"]), width=str(box["width"]), height=str(box["height"]), **{"as": "geometry"})

        for node in page["nodes"]:
            position = page["positions"][node.node_id]
            cell_id = str(cell_counter)
            cell_counter += 1
            node_ids[node.node_id] = cell_id
            style = GROUP_STYLES.get(node.group, {"stroke": "#94A3B8"})
            shape = GROUP_NODE_SHAPES.get(node.group, "rounded=1;")
            icon_profile = _node_icon_profile(node)
            value = _drawio_text(f"{node.label}\n{node.detail}")
            node_cell = ET.SubElement(root, "mxCell", id=cell_id, value=value, style=f"{shape}whiteSpace=wrap;html=1;fillColor=#ffffff;strokeColor={style['stroke']};fontSize=12;fontStyle=1;spacing=8;spacingLeft=48;", vertex="1", parent="1")
            ET.SubElement(node_cell, "mxGeometry", x=str(position["x"]), y=str(position["y"]), width=str(position["width"]), height=str(position["height"]), **{"as": "geometry"})
            icon_id = str(cell_counter)
            cell_counter += 1
            icon_cell = ET.SubElement(
                root,
                "mxCell",
                id=icon_id,
                value=_drawio_text(str(icon_profile["drawio_value"])),
                style=str(icon_profile["drawio_style"]),
                vertex="1",
                parent="1",
            )
            ET.SubElement(
                icon_cell,
                "mxGeometry",
                x=str(position["x"] + 10),
                y=str(position["y"] + 10),
                width=str(icon_profile["width"]),
                height=str(icon_profile["height"]),
                **{"as": "geometry"},
            )
            badge_id = str(cell_counter)
            cell_counter += 1
            badge_cell = ET.SubElement(
                root,
                "mxCell",
                id=badge_id,
                value=_drawio_text(GROUP_ICON_LABELS.get(node.group, node.group[:3].upper())),
                style=f"rounded=1;whiteSpace=wrap;html=1;fillColor={style['stroke']};strokeColor={style['stroke']};fontColor=#FFFFFF;fontStyle=1;fontSize=9;align=center;verticalAlign=middle;arcSize=12;",
                vertex="1",
                parent="1",
            )
            ET.SubElement(
                badge_cell,
                "mxGeometry",
                x=str(position["x"] + position["width"] - 50),
                y=str(position["y"] + 8),
                width="38",
                height="16",
                **{"as": "geometry"},
            )

        for edge in page["edges"]:
            source_id = node_ids.get(edge.source)
            target_id = node_ids.get(edge.target)
            if not source_id or not target_id:
                continue
            edge_id = str(cell_counter)
            cell_counter += 1
            edge_cell = ET.SubElement(root, "mxCell", id=edge_id, value=_drawio_text(edge.label), style="edgeStyle=orthogonalEdgeStyle;rounded=0;orthogonalLoop=1;jettySize=auto;html=1;strokeColor=#64748B;fontSize=11;endArrow=block;endFill=1;", edge="1", parent="1", source=source_id, target=target_id)
            ET.SubElement(edge_cell, "mxGeometry", relative="1", **{"as": "geometry"})

        if page.get("layout_mode") in {"security-lanes", "infra-topology", "service-bands", "onprem-holistic"}:
            cell_counter = _append_drawio_legend(root, page=page, cell_counter=cell_counter)

    return ET.tostring(mxfile, encoding="unicode")


def _export_with_drawio(drawio_xml: str, extension: str, *, page_index: int | None = None) -> bytes | None:
    binary = (
        shutil.which("drawio")
        or shutil.which("draw.io")
        or next(
            (
                candidate
                for candidate in ("/usr/bin/drawio", "/opt/drawio/drawio")
                if Path(candidate).exists()
            ),
            None,
        )
    )
    if not binary:
        return None
    with TemporaryDirectory() as tmp_dir:
        input_path = Path(tmp_dir) / "diagram.drawio"
        output_path = Path(tmp_dir) / f"diagram.{extension}"
        input_path.write_text(drawio_xml, encoding="utf-8")
        command = [binary]
        if hasattr(os, "geteuid") and os.geteuid() == 0:
            command.append("--no-sandbox")
        command.extend(["--export", "--format", extension, "--output", str(output_path), str(input_path)])
        if page_index is not None:
            command.extend(["--page-index", str(page_index)])
        env = os.environ.copy()
        xvfb_process: subprocess.Popen[str] | None = None
        display_reader: int | None = None
        display_writer: int | None = None
        if shutil.which("xvfb-run") and shutil.which("xauth"):
            command = ["xvfb-run", "-a", *command]
        try:
            if not env.get("DISPLAY") and shutil.which("Xvfb") and not (shutil.which("xvfb-run") and shutil.which("xauth")):
                display_reader, display_writer = os.pipe()
                xvfb_process = subprocess.Popen(
                    ["Xvfb", "-displayfd", str(display_writer), "-screen", "0", "1920x1080x24"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    text=True,
                    pass_fds=(display_writer,),
                )
                os.close(display_writer)
                display_writer = None
                display_number = os.read(display_reader, 32).decode("utf-8", errors="ignore").strip()
                os.close(display_reader)
                display_reader = None
                if not display_number:
                    xvfb_process.terminate()
                    xvfb_process.wait(timeout=5)
                    return None
                env["DISPLAY"] = f":{display_number}"
                time.sleep(0.4)
            subprocess.run(command, check=True, capture_output=True, text=True, env=env)
        except Exception:  # noqa: BLE001
            return None
        finally:
            if display_writer is not None:
                os.close(display_writer)
            if display_reader is not None:
                os.close(display_reader)
            if xvfb_process is not None:
                xvfb_process.terminate()
                try:
                    xvfb_process.wait(timeout=5)
                except Exception:  # noqa: BLE001
                    xvfb_process.kill()
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


def _extract_exact_reference_diagram(reference_diagrams: list[dict[str, Any]] | None) -> dict[str, Any] | None:
    for item in reference_diagrams or []:
        if not isinstance(item, dict):
            continue
        if not (item.get("use_as_canonical") or item.get("preserve_exact") or str(item.get("mode") or "").lower() == "exact"):
            continue
        for key in ("drawio_xml", "xml", "content", "text"):
            content = item.get(key)
            if isinstance(content, str) and "<mxfile" in content:
                return {
                    "name": item.get("filename") or item.get("name") or "reference.drawio",
                    "drawio_xml": content,
                }
    return None


def _reference_preview_svg(page_name: str, source_name: str) -> str:
    safe_page_name = escape(page_name or "Reference diagram")
    safe_source_name = escape(source_name or "reference.drawio")
    return (
        "<svg xmlns=\"http://www.w3.org/2000/svg\" width=\"1600\" height=\"900\" viewBox=\"0 0 1600 900\">"
        "<rect width=\"1600\" height=\"900\" fill=\"#f8fafc\" />"
        "<rect x=\"84\" y=\"84\" width=\"1432\" height=\"732\" rx=\"24\" fill=\"#ffffff\" stroke=\"#0f172a\" stroke-width=\"4\" />"
        f"<text x=\"120\" y=\"180\" fill=\"#0f172a\" font-family=\"Arial, Helvetica, sans-serif\" font-size=\"36\" font-weight=\"700\">{safe_page_name}</text>"
        f"<text x=\"120\" y=\"236\" fill=\"#334155\" font-family=\"Arial, Helvetica, sans-serif\" font-size=\"24\">Exact reference diagram preserved from {safe_source_name}.</text>"
        "<text x=\"120\" y=\"304\" fill=\"#64748b\" font-family=\"Arial, Helvetica, sans-serif\" font-size=\"22\">Preview export is unavailable in this runtime, but the draw.io XML artifact remains unchanged.</text>"
        "</svg>"
    )


def _reference_diagram_pages(drawio_xml: str, source_name: str) -> list[dict[str, Any]]:
    try:
        root = ET.fromstring(drawio_xml)
        diagrams = root.findall("diagram")
    except ET.ParseError:
        diagrams = []

    pages = [
        {
            "page_number": index + 1,
            "page_name": diagram.attrib.get("name") or f"Reference page {index + 1}",
            "layout_mode": "reference-exact",
            "title": diagram.attrib.get("name") or f"Reference page {index + 1}",
            "summary": f"Exact reference diagram preserved from {source_name}.",
            "included_groups": ["reference"],
            "node_count": 0,
            "edge_count": 0,
        }
        for index, diagram in enumerate(diagrams)
    ]
    return pages or [
        {
            "page_number": 1,
            "page_name": Path(source_name or "reference.drawio").stem or "Reference page 1",
            "layout_mode": "reference-exact",
            "title": Path(source_name or "reference.drawio").stem or "Reference page 1",
            "summary": f"Exact reference diagram preserved from {source_name}.",
            "included_groups": ["reference"],
            "node_count": 0,
            "edge_count": 0,
        }
    ]


def _build_reference_drawio_artifacts(drawio_xml: str, source_name: str) -> dict[str, Any]:
    pages = _reference_diagram_pages(drawio_xml, source_name)
    page_previews: list[dict[str, Any]] = []
    for index, page in enumerate(pages):
        drawio_page_svg = _export_with_drawio(drawio_xml, "svg", page_index=index)
        preview_svg = drawio_page_svg.decode("utf-8", errors="ignore") if drawio_page_svg else _reference_preview_svg(page["page_name"], source_name)
        page_png = _export_with_drawio(drawio_xml, "png", page_index=index)
        if page_png is None:
            page_png = _png_from_svg(preview_svg)
        page_previews.append(
            {
                "page_number": page["page_number"],
                "page_name": page["page_name"],
                "layout_mode": page["layout_mode"],
                "title": page["title"],
                "summary": page["summary"],
                "svg": preview_svg,
                "png_base64": base64.b64encode(page_png).decode("ascii") if page_png else None,
            }
        )

    svg_bytes = _export_with_drawio(drawio_xml, "svg", page_index=0)
    png_bytes = _export_with_drawio(drawio_xml, "png", page_index=0)
    svg_preview = page_previews[0]["svg"] if page_previews else _reference_preview_svg("Reference page 1", source_name)
    if png_bytes is None:
        png_bytes = _png_from_svg(svg_preview)

    filename = Path(source_name or "reference.drawio").name or "reference.drawio"
    stem = Path(filename).stem or "reference-diagram"
    return {
        "pages": pages,
        "svg_preview": svg_preview,
        "svg": svg_bytes.decode("utf-8", errors="ignore") if svg_bytes else svg_preview,
        "png_base64": base64.b64encode(png_bytes).decode("ascii") if png_bytes else None,
        "page_previews": page_previews,
        "preview_page_name": pages[0]["page_name"],
        "filenames": {
            "drawio": filename,
            "svg": f"{_slugify(stem)}.svg",
            "png": f"{_slugify(stem)}.png",
        },
    }


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
    grouped: dict[str, list[DiagramNode]] = {}
    for node in nodes:
        grouped.setdefault(node.group, []).append(node)
    assumptions = [
        planning.reasoning_summary,
        f"Prompt preserved: {prompt.strip() or 'Prompt-free architecture generation based on live OpenShift state.'}",
        f"Live OpenShift state included: {'yes' if openshift_state else 'no'}.",
        f"RAG grounding used: {'yes' if (knowledge_context or {}).get('items') else 'no'}.",
        planning.version_baseline,
    ]
    decision_rows = [
        {
            "title": "Architecture pattern",
            "decision": f"Use the {planning.pattern_label} pattern as the primary OpenShift reference design.",
            "rationale": "The detected platform pattern aligns the shared architecture pack plus the HLD and LLD narratives with a consistent topology, ownership model, and operating story.",
            "consequences": "The final pack can explain platform, security, networking, data, and operations from one coherent reference model.",
        },
        {
            "title": "Boundary-first design",
            "decision": "Describe the platform through explicit cluster, namespace, ingress, security, and operational boundaries.",
            "rationale": "OpenShift handoff quality improves when control-plane, workload, and governance boundaries are explicit instead of implied.",
            "consequences": "Operators and engineering teams can map architecture review findings directly to platform owners and implementation workstreams.",
        },
        {
            "title": "Reference baseline",
            "decision": "Ground the pack on Red Hat OpenShift 4.20+ documentation and the repository's own multicluster and DR patterns.",
            "rationale": "This keeps the output aligned to supported platform language while preserving local deployment realities and enterprise handoff expectations.",
            "consequences": "Reviewers receive a senior-architect narrative instead of a generic Kubernetes diagram and a thin implementation note set.",
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
    sections = _foundational_outline_sections(
        document_type=document_type,
        title=title,
        planning=planning,
        nodes=nodes,
        edges=edges,
        prompt=prompt,
        openshift_state=openshift_state,
        knowledge_context=knowledge_context,
    )
    sections.extend(_reference_sections())
    sections.extend(_repo_alignment_sections())
    for group in GROUP_ORDER:
        group_nodes = grouped.get(group) or []
        if group_nodes:
            sections.append(_section(f"Domain design — {GROUP_LABELS.get(group, group.title())}", _domain_lines(group, group_nodes, document_type)))

    if document_type == "assessment":
        sections.append(_section("Assessment findings", [f"{item['label']}: {item['assessment']} Actions: {'; '.join(item['actions'])}" for item in selected_dimensions]))
    else:
        sections.extend(_padding_sections(document_type=document_type, grouped=grouped, nodes=nodes, edges=edges))

    target_pages = DOCUMENT_PAGE_TARGETS.get(document_type, 24)
    estimated_pages = _estimate_document_pages(sections, document_type)
    iteration = 1
    while document_type in {"hld", "lld"} and estimated_pages < target_pages and iteration <= 24:
        sections.extend(_booster_sections(document_type=document_type, grouped=grouped, nodes=nodes, edges=edges, iteration=iteration))
        estimated_pages = _estimate_document_pages(sections, document_type)
        iteration += 1

    if document_type == "assessment" and estimated_pages < target_pages:
        sections.extend(_booster_sections(document_type="hld", grouped=grouped, nodes=nodes, edges=edges, iteration=1)[:2])
        estimated_pages = _estimate_document_pages(sections, document_type)

    return {
        "document_type": document_type,
        "title": f"{title} — {document_type.upper()}",
        "summary": sections[0]["body"][0],
        "sections": sections,
        "assumptions": assumptions,
        "decision_rows": decision_rows,
        "state_views": state_views,
        "assessment_dimensions": selected_dimensions,
        "target_page_count": target_pages,
        "estimated_page_count": estimated_pages,
        "page_target_met": estimated_pages >= target_pages,
        "architect_profile": planning.architect_profile,
        "version_baseline": planning.version_baseline,
    }


def generate_architecture_diagram(*, prompt: str, openshift_state: dict[str, Any] | None, model_client: Any | None = None, reference_diagrams: list[dict[str, Any]] | None = None, knowledge_context: dict[str, Any] | None = None, require_model: bool = False, assessment_scope_id: str = "architecture-readiness") -> dict[str, Any]:
    if require_model and model_client is not None and hasattr(model_client, "probe"):
        probe = model_client.probe()
        if getattr(probe, "ok", True) is False:
            raise RuntimeError(getattr(probe, "detail", "The selected model is unavailable for this architect run."))

    planning, nodes, edges, live_summaries = _build_nodes_and_edges(prompt, openshift_state)
    title = f"{planning.pattern_label} architecture"
    summary = live_summaries[0] if live_summaries else planning.reasoning_summary
    exact_reference = _extract_exact_reference_diagram(reference_diagrams)
    if exact_reference:
        drawio_xml = exact_reference["drawio_xml"]
        reference_artifacts = _build_reference_drawio_artifacts(drawio_xml, exact_reference["name"])
        rendering_pages = reference_artifacts["pages"]
        first_page = rendering_pages[0]
        svg_preview = reference_artifacts["svg_preview"]
        page_previews = reference_artifacts["page_previews"]
    else:
        diagram_pages = _diagram_page_specs(
            title=title,
            planning=planning,
            nodes=nodes,
            edges=edges,
            openshift_state=openshift_state,
        )
        first_page = diagram_pages[0]
        drawio_xml = _build_drawio_xml(title, diagram_pages)
        fallback_page_previews = [
            {
                "page_number": page["page_number"],
                "page_name": page["page_name"],
                "layout_mode": page["layout_mode"],
                "title": page["title"],
                "summary": page["summary"],
                "svg": _render_svg(
                    page["title"],
                    page["summary"],
                    page["nodes"],
                    page["edges"],
                    page["positions"],
                    page["group_boxes"],
                    page.get("zones", []),
                    page["total_width"],
                    page["total_height"],
                ),
            }
            for page in diagram_pages
        ]
        page_previews = []
        for index, page in enumerate(diagram_pages):
            drawio_page_svg = _export_with_drawio(drawio_xml, "svg", page_index=index)
            preview_svg = drawio_page_svg.decode("utf-8", errors="ignore") if drawio_page_svg else fallback_page_previews[index]["svg"]
            page_png = _export_with_drawio(drawio_xml, "png", page_index=index)
            if page_png is None:
                page_png = _png_from_svg(preview_svg)
            page_previews.append(
                {
                    "page_number": page["page_number"],
                    "page_name": page["page_name"],
                    "layout_mode": page["layout_mode"],
                    "title": page["title"],
                    "summary": page["summary"],
                    "svg": preview_svg,
                    "png_base64": base64.b64encode(page_png).decode("ascii") if page_png else None,
                }
            )
        svg_preview = page_previews[0]["svg"] if page_previews else fallback_page_previews[0]["svg"]
        rendering_pages = [
            {
                "page_number": page["page_number"],
                "page_name": page["page_name"],
                "layout_mode": page["layout_mode"],
                "title": page["title"],
                "summary": page["summary"],
                "included_groups": page["included_groups"],
                "node_count": len(page["nodes"]),
                "edge_count": len(page["edges"]),
            }
            for page in diagram_pages
        ]

    svg_bytes = _export_with_drawio(drawio_xml, "svg", page_index=0)
    png_bytes = _export_with_drawio(drawio_xml, "png", page_index=0)
    if png_bytes is None:
        png_bytes = _png_from_svg(svg_preview)

    documents = {
        "hld": _document_sections("hld", title, planning, nodes, edges, prompt, openshift_state, knowledge_context, assessment_scope_id=assessment_scope_id),
        "lld": _document_sections("lld", title, planning, nodes, edges, prompt, openshift_state, knowledge_context, assessment_scope_id=assessment_scope_id),
        "assessment": _document_sections("assessment", title, planning, nodes, edges, prompt, openshift_state, knowledge_context, assessment_scope_id=assessment_scope_id),
    }
    score = min(100, 60 + (len(nodes) * 3) + (len(rendering_pages) * 2) + (6 if openshift_state else 0) + (4 if knowledge_context and knowledge_context.get("used") else 0) + (8 if exact_reference else 0))
    quality_scorecard = {
        "overall_score": score,
        "max_score": 100,
        "quality_band": "Solid" if score >= 75 else ("Developing" if score >= 60 else "Needs work"),
        "summary": "OpenShift architecture quality review based on domain coverage, Red Hat 4.20+ reference alignment, live evidence, and document completeness.",
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
            "diagram_pages": rendering_pages,
        },
        "artifacts": {
            "drawio_xml": drawio_xml,
            "svg_preview": svg_preview,
            "svg": reference_artifacts["svg"] if exact_reference else (svg_bytes.decode("utf-8", errors="ignore") if svg_bytes else svg_preview),
            "png_base64": base64.b64encode(png_bytes).decode("ascii") if png_bytes else None,
            "preview_page_name": first_page["page_name"],
            "page_previews": page_previews,
            "filenames": reference_artifacts["filenames"] if exact_reference else {
                "drawio": f"{_slugify(title)}.drawio",
                "svg": f"{_slugify(title)}.svg",
                "png": f"{_slugify(title)}.png",
            },
        },
    }
