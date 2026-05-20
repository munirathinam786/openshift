from __future__ import annotations

import base64
import hashlib
import json
import logging
import re
import shlex
import ssl
import subprocess
import tempfile
import time as _time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable

from kubernetes import client, config
from kubernetes.client import ApiException
from kubernetes.config.config_exception import ConfigException

from .config import Settings

logger = logging.getLogger(__name__)

ToolHandler = Callable[..., dict[str, Any]]


@dataclass(slots=True)
class ToolSpec:
    name: str
    description: str
    arguments: dict[str, str]
    handler: ToolHandler


class _ToolResultCache:
    """In-memory TTL cache keyed on tool name plus normalized arguments."""

    def __init__(self, ttl_seconds: float = 60.0) -> None:
        self._ttl = ttl_seconds
        self._store: dict[str, tuple[float, dict[str, Any]]] = {}

    def _key(self, tool_name: str, arguments: dict[str, Any]) -> str:
        raw = json.dumps({"t": tool_name, "a": arguments}, sort_keys=True, default=str)
        return hashlib.sha256(raw.encode()).hexdigest()

    def get(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any] | None:
        key = self._key(tool_name, arguments)
        entry = self._store.get(key)
        if entry is None:
            return None
        ts, result = entry
        if _time.monotonic() - ts > self._ttl:
            del self._store[key]
            return None
        return result

    def put(self, tool_name: str, arguments: dict[str, Any], result: dict[str, Any]) -> None:
        self._store[self._key(tool_name, arguments)] = (_time.monotonic(), result)


_tool_cache = _ToolResultCache(ttl_seconds=60.0)


class OpenShiftSreToolkit:
    """OpenShift / Kubernetes inspection toolkit behind the existing agent contract."""

    _READ_ONLY_OC_VERBS = {"get", "describe", "logs", "whoami", "api-resources", "api-versions", "version", "explain", "adm"}
    _DENIED_OC_TOKENS = {
        "apply",
        "create",
        "delete",
        "patch",
        "replace",
        "edit",
        "annotate",
        "label",
        "scale",
        "set",
        "rollout",
        "restart",
        "cordon",
        "uncordon",
        "drain",
        "taint",
        "exec",
        "debug",
        "port-forward",
        "cp",
        "rsync",
    }

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._configured = False
        self._current_context_name: str | None = settings.kube_context
        self._core: client.CoreV1Api | None = None
        self._apps: client.AppsV1Api | None = None
        self._autoscaling: client.AutoscalingV2Api | None = None
        self._apiregistration: client.ApiregistrationV1Api | None = None
        self._admissionregistration: client.AdmissionregistrationV1Api | None = None
        self._batch: client.BatchV1Api | None = None
        self._certificates: client.CertificatesV1Api | None = None
        self._networking: client.NetworkingV1Api | None = None
        self._policy: client.PolicyV1Api | None = None
        self._rbac: client.RbacAuthorizationV1Api | None = None
        self._storage: client.StorageV1Api | None = None
        self._custom: client.CustomObjectsApi | None = None
        self.tools: dict[str, ToolSpec] = {
            "get_cluster_identity": ToolSpec(
                "get_cluster_identity",
                "Return the active OpenShift cluster identity, API endpoint, and default project context.",
                {},
                self.get_cluster_identity,
            ),
            "list_cluster_infrastructure": ToolSpec(
                "list_cluster_infrastructure",
                "Inspect the cluster infrastructure resource to identify the platform type, topology, and likely platform pattern such as ARO, ROSA, or IBM Z.",
                {},
                self.list_cluster_infrastructure,
            ),
            "list_projects": ToolSpec(
                "list_projects",
                "List OpenShift projects / namespaces and summarize phase, labels, and age.",
                {},
                self.list_projects,
            ),
            "list_cluster_version": ToolSpec(
                "list_cluster_version",
                "Inspect cluster version, upgrade channel, and high-level version conditions.",
                {},
                self.list_cluster_version,
            ),
            "list_cluster_operators": ToolSpec(
                "list_cluster_operators",
                "Inspect cluster operators and summarize available, progressing, and degraded posture.",
                {},
                self.list_cluster_operators,
            ),
            "list_cluster_network_config": ToolSpec(
                "list_cluster_network_config",
                "Inspect cluster network configuration to summarize network type, cluster/service CIDRs, external exposure ranges, and topology-related network settings.",
                {},
                self.list_cluster_network_config,
            ),
            "list_ingress_controllers": ToolSpec(
                "list_ingress_controllers",
                "Inspect OpenShift ingress controllers to summarize domain, publishing strategy, replica posture, and availability across the estate.",
                {},
                self.list_ingress_controllers,
            ),
            "list_cluster_proxy_config": ToolSpec(
                "list_cluster_proxy_config",
                "Inspect the cluster proxy configuration to summarize HTTP/HTTPS proxy posture, no-proxy coverage, trusted CA wiring, and readiness endpoints.",
                {},
                self.list_cluster_proxy_config,
            ),
            "list_cluster_dns_config": ToolSpec(
                "list_cluster_dns_config",
                "Inspect the OpenShift DNS operator configuration to summarize resolver posture, node placement, log level, and zone wiring.",
                {},
                self.list_cluster_dns_config,
            ),
            "list_feature_gate_config": ToolSpec(
                "list_feature_gate_config",
                "Inspect cluster feature gate configuration to summarize the active feature set and any custom no-upgrade features enabled for lifecycle planning.",
                {},
                self.list_feature_gate_config,
            ),
            "list_scheduler_config": ToolSpec(
                "list_scheduler_config",
                "Inspect cluster scheduler configuration to summarize profile count, default node selector, and master schedulability posture.",
                {},
                self.list_scheduler_config,
            ),
            "list_nodes": ToolSpec(
                "list_nodes",
                "List cluster nodes with roles, readiness, taints, and kubelet versions.",
                {},
                self.list_nodes,
            ),
            "list_node_pressure": ToolSpec(
                "list_node_pressure",
                "Summarize node readiness and pressure conditions such as memory, disk, and PID pressure.",
                {},
                self.list_node_pressure,
            ),
            "list_pods": ToolSpec(
                "list_pods",
                "List pods across the selected project scope and summarize restart or pending risk.",
                {"project": "Optional namespace / project name to scope the query."},
                self.list_pods,
            ),
            "list_workload_health": ToolSpec(
                "list_workload_health",
                "Summarize deployment, statefulset, daemonset, and job rollout health across the selected projects.",
                {"project": "Optional namespace / project name to scope the query."},
                self.list_workload_health,
            ),
            "list_services": ToolSpec(
                "list_services",
                "List services and summarize type, selectors, and endpoint exposure posture.",
                {"project": "Optional namespace / project name to scope the query."},
                self.list_services,
            ),
            "list_routes": ToolSpec(
                "list_routes",
                "List OpenShift routes and summarize host, TLS, wildcard, and admitted posture.",
                {"project": "Optional namespace / project name to scope the query."},
                self.list_routes,
            ),
            "list_ingresses": ToolSpec(
                "list_ingresses",
                "List ingresses across the selected projects and summarize host, class, and TLS posture.",
                {"project": "Optional namespace / project name to scope the query."},
                self.list_ingresses,
            ),
            "list_events": ToolSpec(
                "list_events",
                "List recent warning and normal events to accelerate cluster or workload troubleshooting.",
                {"project": "Optional namespace / project name to scope the query."},
                self.list_events,
            ),
            "list_persistent_storage": ToolSpec(
                "list_persistent_storage",
                "List PVs and PVCs and summarize bind state, capacity, access mode, and storage class posture.",
                {"project": "Optional namespace / project name to scope the query."},
                self.list_persistent_storage,
            ),
            "list_horizontal_pod_autoscalers": ToolSpec(
                "list_horizontal_pod_autoscalers",
                "List horizontal pod autoscalers and summarize target workloads, min/max ranges, and scaling readiness posture.",
                {"project": "Optional namespace / project name to scope the query."},
                self.list_horizontal_pod_autoscalers,
            ),
            "list_pod_disruption_budgets": ToolSpec(
                "list_pod_disruption_budgets",
                "List pod disruption budgets and summarize allowed disruptions plus workloads that may block safe maintenance or upgrades.",
                {"project": "Optional namespace / project name to scope the query."},
                self.list_pod_disruption_budgets,
            ),
            "list_cronjobs": ToolSpec(
                "list_cronjobs",
                "List cron jobs and summarize schedule, suspend posture, and last/next execution coverage.",
                {"project": "Optional namespace / project name to scope the query."},
                self.list_cronjobs,
            ),
            "list_volume_snapshots": ToolSpec(
                "list_volume_snapshots",
                "List volume snapshots and volume snapshot classes to summarize protection coverage, readiness, and snapshot policy posture.",
                {"project": "Optional namespace / project name to scope the query."},
                self.list_volume_snapshots,
            ),
            "list_storage_classes": ToolSpec(
                "list_storage_classes",
                "List storage classes and summarize provisioner, expansion support, and default-class posture.",
                {},
                self.list_storage_classes,
            ),
            "list_machine_config_pools": ToolSpec(
                "list_machine_config_pools",
                "Inspect machine config pools for update, degraded, and machine-count posture.",
                {},
                self.list_machine_config_pools,
            ),
            "list_machine_sets": ToolSpec(
                "list_machine_sets",
                "Inspect machine sets in the machine API namespace and summarize replica drift or readiness gaps.",
                {},
                self.list_machine_sets,
            ),
            "list_machine_health_checks": ToolSpec(
                "list_machine_health_checks",
                "Inspect machine health checks to summarize remediation posture, selector coverage, and max-unhealthy guardrails for machine lifecycle safety.",
                {},
                self.list_machine_health_checks,
            ),
            "list_cluster_autoscaling": ToolSpec(
                "list_cluster_autoscaling",
                "Inspect cluster autoscaler and machine autoscaler resources to summarize fleet capacity guardrails, scale-down posture, and node-pool scaling ranges.",
                {},
                self.list_cluster_autoscaling,
            ),
            "list_operator_subscriptions": ToolSpec(
                "list_operator_subscriptions",
                "List Operator Lifecycle Manager subscriptions and summarize channel, source, and state posture.",
                {},
                self.list_operator_subscriptions,
            ),
            "list_cluster_service_versions": ToolSpec(
                "list_cluster_service_versions",
                "List ClusterServiceVersions and summarize phase, operator version, and namespace posture.",
                {},
                self.list_cluster_service_versions,
            ),
            "list_monitoring_alert_posture": ToolSpec(
                "list_monitoring_alert_posture",
                "Inspect monitoring stack resources to summarize Prometheus, Alertmanager, and alert-rule posture across cluster and user-workload monitoring namespaces.",
                {},
                self.list_monitoring_alert_posture,
            ),
            "list_control_plane_certificates": ToolSpec(
                "list_control_plane_certificates",
                "Inspect control-plane certificate and trust-bundle resources to summarize expiration risk, trust wiring, and expiring CA or serving-certificate posture.",
                {},
                self.list_control_plane_certificates,
            ),
            "list_api_service_health": ToolSpec(
                "list_api_service_health",
                "Inspect aggregated APIService registrations to summarize availability, backing services, TLS skip-verify posture, and extension health risks.",
                {},
                self.list_api_service_health,
            ),
            "list_certificatesigning_requests": ToolSpec(
                "list_certificatesigning_requests",
                "Inspect certificate signing requests to summarize pending node joins, denied requests, signer usage, and certificate issuance posture.",
                {},
                self.list_certificatesigning_requests,
            ),
            "list_acm_multicluster_hubs": ToolSpec(
                "list_acm_multicluster_hubs",
                "Inspect ACM MultiClusterHub resources to summarize hub availability, lifecycle phase, and placement namespace coverage.",
                {},
                self.list_acm_multicluster_hubs,
            ),
            "list_acm_managed_clusters": ToolSpec(
                "list_acm_managed_clusters",
                "Inspect ACM ManagedCluster resources to summarize fleet join state, availability, and cluster distribution across platform patterns.",
                {},
                self.list_acm_managed_clusters,
            ),
            "list_acm_policies": ToolSpec(
                "list_acm_policies",
                "Inspect ACM governance policies and summarize remediation posture, disabled policies, and compliance state where reported.",
                {},
                self.list_acm_policies,
            ),
            "list_acs_central_services": ToolSpec(
                "list_acs_central_services",
                "Inspect Red Hat Advanced Cluster Security central services to summarize install phase, availability, and namespace placement.",
                {},
                self.list_acs_central_services,
            ),
            "list_acs_secured_clusters": ToolSpec(
                "list_acs_secured_clusters",
                "Inspect Red Hat Advanced Cluster Security secured clusters to summarize sensor deployment, cluster presence, and protection coverage.",
                {},
                self.list_acs_secured_clusters,
            ),
            "list_security_context_constraints": ToolSpec(
                "list_security_context_constraints",
                "List security context constraints and summarize privilege and host access posture.",
                {},
                self.list_security_context_constraints,
            ),
            "list_admission_webhook_configurations": ToolSpec(
                "list_admission_webhook_configurations",
                "Inspect mutating and validating webhook configurations to summarize failure policy, service backing, CA bundle posture, and admission-governance risk.",
                {},
                self.list_admission_webhook_configurations,
            ),
            "list_operator_extension_readiness": ToolSpec(
                "list_operator_extension_readiness",
                "Combine operator, extension API, CSV, and webhook signals into a readiness score for platform extensions and operator-dependent control-plane services.",
                {},
                self.list_operator_extension_readiness,
            ),
            "list_rbac_bindings": ToolSpec(
                "list_rbac_bindings",
                "List role bindings and cluster role bindings to surface privileged subjects, cluster-admin assignments, and namespace access posture.",
                {"project": "Optional namespace / project name to scope the query."},
                self.list_rbac_bindings,
            ),
            "list_service_accounts": ToolSpec(
                "list_service_accounts",
                "List service accounts and summarize token mounting posture, secret counts, and image-pull dependency signals.",
                {"project": "Optional namespace / project name to scope the query."},
                self.list_service_accounts,
            ),
            "list_limit_ranges": ToolSpec(
                "list_limit_ranges",
                "List limit ranges across the selected projects to show governance guardrails around default requests, limits, and max ratios.",
                {"project": "Optional namespace / project name to scope the query."},
                self.list_limit_ranges,
            ),
            "list_network_policies": ToolSpec(
                "list_network_policies",
                "List network policies across the selected projects and summarize ingress and egress isolation coverage.",
                {"project": "Optional namespace / project name to scope the query."},
                self.list_network_policies,
            ),
            "list_resource_quotas": ToolSpec(
                "list_resource_quotas",
                "List resource quotas and cluster resource quotas to highlight quota pressure or missing guardrails.",
                {"project": "Optional namespace / project name to scope the query."},
                self.list_resource_quotas,
            ),
            "list_image_streams": ToolSpec(
                "list_image_streams",
                "List OpenShift image streams and summarize tag count, lookup policy, and project distribution.",
                {"project": "Optional namespace / project name to scope the query."},
                self.list_image_streams,
            ),
            "list_builds": ToolSpec(
                "list_builds",
                "List recent builds and build configs to surface delivery-pipeline failures or drift.",
                {"project": "Optional namespace / project name to scope the query."},
                self.list_builds,
            ),
            "list_build_configs": ToolSpec(
                "list_build_configs",
                "List build configs to summarize source strategy, trigger coverage, and output destinations across delivery namespaces.",
                {"project": "Optional namespace / project name to scope the query."},
                self.list_build_configs,
            ),
            "list_deployment_configs": ToolSpec(
                "list_deployment_configs",
                "List OpenShift deployment configs to summarize replica posture, strategy, and rollout trigger coverage.",
                {"project": "Optional namespace / project name to scope the query."},
                self.list_deployment_configs,
            ),
            "list_gitops_argocds": ToolSpec(
                "list_gitops_argocds",
                "Inspect OpenShift GitOps / Argo CD instances to summarize install posture, HA settings, namespaces, and server exposure.",
                {},
                self.list_gitops_argocds,
            ),
            "list_knative_services": ToolSpec(
                "list_knative_services",
                "Inspect Knative services to summarize readiness, latest revisions, and serverless delivery posture when OpenShift Serverless is installed.",
                {"project": "Optional namespace / project name to scope the query."},
                self.list_knative_services,
            ),
            "list_gitops_applications": ToolSpec(
                "list_gitops_applications",
                "Inspect Argo CD applications to summarize sync, health, project, and destination posture across managed namespaces.",
                {},
                self.list_gitops_applications,
            ),
            "list_tekton_configs": ToolSpec(
                "list_tekton_configs",
                "Inspect OpenShift Pipelines / Tekton configuration resources to summarize profile, API stability, and pipelines-as-code posture.",
                {},
                self.list_tekton_configs,
            ),
            "list_tekton_pipeline_runs": ToolSpec(
                "list_tekton_pipeline_runs",
                "Inspect Tekton pipeline runs to summarize recent CI/CD execution health, namespace distribution, and failure posture.",
                {"project": "Optional namespace / project name to scope the query."},
                self.list_tekton_pipeline_runs,
            ),
            "list_cluster_logging": ToolSpec(
                "list_cluster_logging",
                "Inspect OpenShift Logging resources to summarize ClusterLogging and ClusterLogForwarder posture, retention, and forwarding configuration.",
                {},
                self.list_cluster_logging,
            ),
            "list_oadp_resources": ToolSpec(
                "list_oadp_resources",
                "Inspect OADP and Velero resources to summarize backup applications, storage locations, and schedule posture.",
                {},
                self.list_oadp_resources,
            ),
            "list_virtualization_resources": ToolSpec(
                "list_virtualization_resources",
                "Inspect OpenShift Virtualization / CNV resources to summarize KubeVirt control-plane health, HyperConverged posture, virtual machines, DataVolumes, and live migration activity.",
                {"project": "Optional namespace / project name to scope VM, DataVolume, and migration queries."},
                self.list_virtualization_resources,
            ),
            "list_virtual_machine_snapshots": ToolSpec(
                "list_virtual_machine_snapshots",
                "Inspect KubeVirt virtual machine snapshots to summarize snapshot readiness, source VMs, and restore posture.",
                {"project": "Optional namespace / project name to scope VM snapshot queries."},
                self.list_virtual_machine_snapshots,
            ),
            "list_migration_toolkit_resources": ToolSpec(
                "list_migration_toolkit_resources",
                "Inspect Migration Toolkit for Containers resources to summarize migration clusters, storage, plans, and recent migration execution posture.",
                {"project": "Optional namespace / project name to scope migration toolkit queries."},
                self.list_migration_toolkit_resources,
            ),
            "list_disaster_recovery_resources": ToolSpec(
                "list_disaster_recovery_resources",
                "Inspect ACM and ODF disaster-recovery resources to summarize DR policies, DR placement controls, and volume replication posture.",
                {"project": "Optional namespace / project name to scope DR placement and replication queries."},
                self.list_disaster_recovery_resources,
            ),
            "list_oauth_configuration": ToolSpec(
                "list_oauth_configuration",
                "Inspect OpenShift OAuth configuration to summarize identity providers, LDAP posture, and cluster-admin access expectations.",
                {},
                self.list_oauth_configuration,
            ),
            "run_read_only_oc_cli": ToolSpec(
                "run_read_only_oc_cli",
                "Run a carefully validated read-only oc CLI command for edge-case diagnostics.",
                {"command": "Full oc command starting with oc."},
                self.run_read_only_oc_cli,
            ),
        }

    def tool_manifest(self, names: list[str] | tuple[str, ...] | None = None) -> list[dict[str, Any]]:
        selected_names = None if names is None else set(names)
        return [
            {"name": tool.name, "description": tool.description, "arguments": tool.arguments}
            for tool in self.tools.values()
            if selected_names is None or tool.name in selected_names
        ]

    def invoke(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        tool = self.tools.get(name)
        if tool is None:
            raise KeyError(f"Unknown tool: {name}")
        cached = _tool_cache.get(name, arguments)
        if cached is not None:
            return cached
        result = tool.handler(**arguments)
        _tool_cache.put(name, arguments, result)
        return result

    def _ensure_clients(self) -> None:
        if self._configured:
            return
        try:
            if self._settings.openshift_api_url and self._settings.openshift_token:
                configuration = client.Configuration()
                configuration.host = self._settings.openshift_api_url.rstrip("/")
                configuration.verify_ssl = self._settings.openshift_verify_ssl
                configuration.api_key = {"authorization": f"Bearer {self._settings.openshift_token}"}
                client.Configuration.set_default(configuration)
                self._current_context_name = self._settings.openshift_cluster
            else:
                load_kwargs: dict[str, Any] = {}
                if self._settings.kubeconfig_path:
                    load_kwargs["config_file"] = self._settings.kubeconfig_path
                if self._settings.kube_context:
                    load_kwargs["context"] = self._settings.kube_context
                    self._current_context_name = self._settings.kube_context
                else:
                    try:
                        _, active_context = config.list_kube_config_contexts(**load_kwargs)
                        if active_context:
                            self._current_context_name = active_context.get("name")
                    except Exception:
                        pass
                config.load_kube_config(**load_kwargs)
        except (ConfigException, FileNotFoundError):
            config.load_incluster_config()
            self._current_context_name = self._current_context_name or "in-cluster"

        self._core = client.CoreV1Api()
        self._apps = client.AppsV1Api()
        self._autoscaling = client.AutoscalingV2Api()
        self._apiregistration = client.ApiregistrationV1Api()
        self._admissionregistration = client.AdmissionregistrationV1Api()
        self._batch = client.BatchV1Api()
        self._certificates = client.CertificatesV1Api()
        self._networking = client.NetworkingV1Api()
        self._policy = client.PolicyV1Api()
        self._rbac = client.RbacAuthorizationV1Api()
        self._storage = client.StorageV1Api()
        self._custom = client.CustomObjectsApi()
        self._configured = True

    @staticmethod
    def _parse_csv(value: str | None) -> list[str]:
        return [item.strip() for item in (value or "").split(",") if item.strip()]

    def _selected_projects(self, project: str | None = None) -> list[str]:
        if project and project.strip():
            return [project.strip()]
        projects = self._parse_csv(self._settings.openshift_projects)
        if projects:
            return projects
        if self._settings.openshift_namespace:
            return [self._settings.openshift_namespace]
        return ["default"]

    def _all_projects(self) -> list[str]:
        self._ensure_clients()
        assert self._core is not None
        try:
            return [self._metadata_name(item) for item in self._core.list_namespace().items if self._metadata_name(item)]
        except ApiException:
            return self._selected_projects()

    @staticmethod
    def _namespace_candidates(*groups: list[str]) -> list[str]:
        ordered: list[str] = []
        for group in groups:
            for item in group:
                if item and item not in ordered:
                    ordered.append(item)
        return ordered

    @staticmethod
    def _metadata_name(item: Any) -> str | None:
        metadata = getattr(item, "metadata", None)
        return getattr(metadata, "name", None) if metadata else None

    @staticmethod
    def _labels(item: Any) -> dict[str, str]:
        metadata = getattr(item, "metadata", None)
        return getattr(metadata, "labels", None) or {} if metadata else {}

    @staticmethod
    def _creation_timestamp(item: Any) -> str | None:
        metadata = getattr(item, "metadata", None)
        value = getattr(metadata, "creation_timestamp", None) if metadata else None
        return value.isoformat() if value else None

    @staticmethod
    def _condition_status(conditions: list[Any] | None, condition_type: str) -> str | None:
        for condition in conditions or []:
            if getattr(condition, "type", None) == condition_type:
                return getattr(condition, "status", None)
        return None

    @staticmethod
    def _resource_value(usage: dict[str, Any] | None, key: str) -> str | None:
        return usage.get(key) if usage else None

    @staticmethod
    def _extract_pem_certificates(raw_text: str | None) -> list[str]:
        if not raw_text:
            return []
        return re.findall(r"-----BEGIN CERTIFICATE-----.*?-----END CERTIFICATE-----", raw_text, flags=re.DOTALL)

    @staticmethod
    def _x509_name_common_name(items: Any) -> str | None:
        for entry in items or []:
            for key, value in entry:
                if key == "commonName":
                    return value
        return None

    @classmethod
    def _decode_pem_certificate(cls, pem_text: str) -> dict[str, Any] | None:
        try:
            with tempfile.NamedTemporaryFile("w", suffix=".pem", delete=True) as handle:
                handle.write(pem_text)
                handle.flush()
                decoded = ssl._ssl._test_decode_cert(handle.name)  # type: ignore[attr-defined]
        except Exception:  # noqa: BLE001
            return None

        not_after = decoded.get("notAfter")
        expires_at: str | None = None
        days_until_expiry: int | None = None
        expired = False
        if isinstance(not_after, str):
            try:
                expiry_ts = ssl.cert_time_to_seconds(not_after)
                expiry_dt = datetime.fromtimestamp(expiry_ts, tz=timezone.utc)
                expires_at = expiry_dt.isoformat()
                days_until_expiry = int((expiry_dt - datetime.now(timezone.utc)).total_seconds() // 86400)
                expired = expiry_dt <= datetime.now(timezone.utc)
            except Exception:  # noqa: BLE001
                expires_at = None
                days_until_expiry = None
                expired = False

        return {
            "subject_common_name": cls._x509_name_common_name(decoded.get("subject")),
            "issuer_common_name": cls._x509_name_common_name(decoded.get("issuer")),
            "serial_number": decoded.get("serialNumber"),
            "not_before": decoded.get("notBefore"),
            "not_after": not_after,
            "expires_at": expires_at,
            "days_until_expiry": days_until_expiry,
            "expired": expired,
        }

    @staticmethod
    def _control_plane_namespaces() -> list[str]:
        return [
            "openshift-config",
            "openshift-config-managed",
            "openshift-ingress",
            "openshift-kube-apiserver",
            "openshift-kube-controller-manager",
            "openshift-apiserver",
            "openshift-authentication",
            "openshift-monitoring",
            "openshift-service-ca",
        ]

    def _list_custom(self, *, group: str, version: str, plural: str, namespace: str | None = None) -> list[dict[str, Any]]:
        self._ensure_clients()
        assert self._custom is not None
        try:
            if namespace:
                payload = self._custom.list_namespaced_custom_object(group, version, namespace, plural)
            else:
                payload = self._custom.list_cluster_custom_object(group, version, plural)
        except ApiException as error:
            if error.status in {403, 404}:
                return []
            raise
        return list(payload.get("items") or [])

    def _list_custom_any_version(
        self,
        *,
        group: str,
        versions: list[str] | tuple[str, ...],
        plural: str,
        namespace: str | None = None,
    ) -> list[dict[str, Any]]:
        for version in versions:
            items = self._list_custom(group=group, version=version, plural=plural, namespace=namespace)
            if items:
                return items
        return []

    def _list_custom_from_namespaces(
        self,
        *,
        group: str,
        versions: list[str] | tuple[str, ...],
        plural: str,
        namespaces: list[str],
    ) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for namespace in self._namespace_candidates(namespaces):
            rows.extend(self._list_custom_any_version(group=group, versions=versions, plural=plural, namespace=namespace))
        return rows

    @staticmethod
    def _extract_condition_map(conditions: list[dict[str, Any]] | None) -> dict[str, str | None]:
        mapping: dict[str, str | None] = {}
        for condition in conditions or []:
            condition_type = condition.get("type")
            if condition_type:
                mapping[str(condition_type)] = condition.get("status")
        return mapping

    @staticmethod
    def _guess_platform_pattern(platform_type: str | None, cluster_name: str | None, infrastructure_name: str | None, architectures: list[str]) -> str:
        joined_name = " ".join(filter(None, [cluster_name, infrastructure_name])).lower()
        architecture_set = {architecture.lower() for architecture in architectures}
        if "s390x" in architecture_set or "ibmz" in joined_name or "ibm-z" in joined_name:
            return "IBM Z"
        if (platform_type or "").lower() == "aws":
            return "ROSA" if "rosa" in joined_name else "OpenShift on AWS"
        if (platform_type or "").lower() == "azure":
            return "ARO" if "aro" in joined_name else "OpenShift on Azure"
        if "rosa" in joined_name:
            return "ROSA"
        if "aro" in joined_name:
            return "ARO"
        return platform_type or "OpenShift platform"

    def get_cluster_identity(self) -> dict[str, Any]:
        self._ensure_clients()
        configuration = client.Configuration.get_default_copy()
        infrastructure = self.list_cluster_infrastructure()
        infrastructure_row = (infrastructure.get("cluster_infrastructure") or [None])[0] or {}
        return {
            "cluster": self._settings.openshift_cluster,
            "cluster_name": self._settings.openshift_cluster,
            "api_url": configuration.host,
            "kube_context": self._current_context_name,
            "current_context": self._current_context_name,
            "default_project": self._settings.openshift_namespace,
            "project_sweep_scope": self._selected_projects(),
            "verify_ssl": self._settings.openshift_verify_ssl,
            "platform_type": infrastructure_row.get("platform_type"),
            "platform_pattern": infrastructure_row.get("platform_pattern"),
            "infrastructure_name": infrastructure_row.get("infrastructure_name"),
            "node_architectures": infrastructure_row.get("node_architectures") or [],
        }

    def list_cluster_infrastructure(self) -> dict[str, Any]:
        items = self._list_custom(group="config.openshift.io", version="v1", plural="infrastructures")
        item = next((entry for entry in items if (entry.get("metadata") or {}).get("name") == "cluster"), None)
        if item is None:
            return {"count": 0, "cluster_infrastructure": []}

        status = item.get("status") or {}
        platform_status = status.get("platformStatus") or {}
        platform_type = status.get("platform") or platform_status.get("type") or (item.get("spec") or {}).get("platformSpec", {}).get("type")
        node_rows = self.list_nodes().get("nodes") or []
        node_architectures = sorted({
            str(label_value)
            for node in node_rows
            for label_key, label_value in ((node.get("labels") or {}) if isinstance(node.get("labels"), dict) else {}).items()
            if label_key in {"kubernetes.io/arch", "beta.kubernetes.io/arch"}
        })
        if not node_architectures:
            self._ensure_clients()
            assert self._core is not None
            try:
                live_nodes = self._core.list_node().items
                node_architectures = sorted({
                    (self._labels(node).get("kubernetes.io/arch") or self._labels(node).get("beta.kubernetes.io/arch") or "")
                    for node in live_nodes
                } - {""})
            except ApiException:
                node_architectures = []

        infrastructure_name = status.get("infrastructureName") or (item.get("metadata") or {}).get("name")
        cluster_name = self._settings.openshift_cluster or infrastructure_name
        return {
            "count": 1,
            "cluster_infrastructure": [
                {
                    "cluster_name": cluster_name,
                    "infrastructure_name": infrastructure_name,
                    "platform_type": platform_type,
                    "platform_pattern": self._guess_platform_pattern(platform_type, cluster_name, infrastructure_name, node_architectures),
                    "api_server_url": status.get("apiServerURL"),
                    "api_server_internal_url": status.get("apiServerInternalURL"),
                    "base_domain": status.get("apiServerURL", "").split("api.")[-1] if status.get("apiServerURL") and "api." in status.get("apiServerURL") else status.get("etcdDiscoveryDomain"),
                    "infrastructure_topology": status.get("infrastructureTopology"),
                    "control_plane_topology": status.get("controlPlaneTopology"),
                    "node_architectures": node_architectures,
                    "platform_status": platform_status,
                }
            ],
        }

    def list_projects(self) -> dict[str, Any]:
        self._ensure_clients()
        assert self._core is not None
        rows = [
            {
                "project": self._metadata_name(item),
                "phase": getattr(getattr(item, "status", None), "phase", None),
                "labels": self._labels(item),
                "created_at": self._creation_timestamp(item),
            }
            for item in self._core.list_namespace().items
        ]
        return {"count": len(rows), "projects": rows}

    def list_cluster_version(self) -> dict[str, Any]:
        items = self._list_custom(group="config.openshift.io", version="v1", plural="clusterversions")
        item = next((entry for entry in items if (entry.get("metadata") or {}).get("name") == "version"), None)
        if item is None:
            return {"count": 0, "cluster_versions": []}
        status = item.get("status") or {}
        desired = status.get("desired") or {}
        conditions = [
            {
                "type": condition.get("type"),
                "status": condition.get("status"),
                "reason": condition.get("reason"),
                "message": condition.get("message"),
            }
            for condition in status.get("conditions") or []
        ]
        return {
            "count": 1,
            "cluster_versions": [
                {
                    "cluster": self._settings.openshift_cluster,
                    "version": desired.get("version"),
                    "channel": (item.get("spec") or {}).get("channel"),
                    "image": desired.get("image"),
                    "available": next((c.get("status") for c in conditions if c.get("type") == "Available"), None),
                    "progressing": next((c.get("status") for c in conditions if c.get("type") == "Progressing"), None),
                    "failing": next((c.get("status") for c in conditions if c.get("type") == "Failing"), None),
                    "conditions": conditions,
                }
            ],
        }

    def list_cluster_operators(self) -> dict[str, Any]:
        items = self._list_custom(group="config.openshift.io", version="v1", plural="clusteroperators")
        rows = []
        degraded_count = 0
        progressing_count = 0
        for item in items:
            conditions = item.get("status", {}).get("conditions") or []
            available = next((c.get("status") for c in conditions if c.get("type") == "Available"), None)
            progressing = next((c.get("status") for c in conditions if c.get("type") == "Progressing"), None)
            degraded = next((c.get("status") for c in conditions if c.get("type") == "Degraded"), None)
            if degraded == "True":
                degraded_count += 1
            if progressing == "True":
                progressing_count += 1
            rows.append(
                {
                    "name": (item.get("metadata") or {}).get("name"),
                    "available": available,
                    "progressing": progressing,
                    "degraded": degraded,
                    "version": next((v.get("version") for v in item.get("status", {}).get("versions") or [] if v.get("name") == "operator"), None),
                    "message": next((c.get("message") for c in conditions if c.get("type") in {"Degraded", "Progressing"} and c.get("message")), None),
                }
            )
        return {"count": len(rows), "degraded_count": degraded_count, "progressing_count": progressing_count, "cluster_operators": rows}

    def list_cluster_network_config(self) -> dict[str, Any]:
        items = self._list_custom(group="config.openshift.io", version="v1", plural="networks")
        item = next((entry for entry in items if (entry.get("metadata") or {}).get("name") == "cluster"), None)
        if item is None:
            return {"count": 0, "cluster_networks": []}
        spec = item.get("spec") or {}
        status = item.get("status") or {}
        cluster_network = spec.get("clusterNetwork") or []
        service_network = spec.get("serviceNetwork") or []
        return {
            "count": 1,
            "cluster_networks": [
                {
                    "cluster_network_cidr_count": len(cluster_network),
                    "service_network_cidr_count": len(service_network),
                    "network_type": status.get("networkType") or spec.get("networkType"),
                    "cluster_network_cidrs": cluster_network,
                    "service_network_cidrs": service_network,
                    "external_ip": spec.get("externalIP") or {},
                    "load_balancer": spec.get("loadBalancer") or {},
                    "ingress": spec.get("ingress") or {},
                    "status": status,
                }
            ],
        }

    def list_ingress_controllers(self) -> dict[str, Any]:
        rows = []
        available_count = 0
        unavailable_count = 0
        for item in self._list_custom(group="operator.openshift.io", version="v1", plural="ingresscontrollers", namespace="openshift-ingress-operator"):
            metadata = item.get("metadata") or {}
            spec = item.get("spec") or {}
            status = item.get("status") or {}
            conditions = self._extract_condition_map(status.get("conditions"))
            available = conditions.get("Available")
            replicas = status.get("availableReplicas")
            desired = spec.get("replicas")
            if available == "True":
                available_count += 1
            if desired is not None and replicas is not None and replicas < desired:
                unavailable_count += 1
            rows.append(
                {
                    "namespace": metadata.get("namespace"),
                    "ingress_controller_name": metadata.get("name"),
                    "domain": spec.get("domain"),
                    "endpoint_publishing_strategy": ((spec.get("endpointPublishingStrategy") or {}).get("type")),
                    "route_selector": spec.get("routeSelector") or {},
                    "namespace_selector": spec.get("namespaceSelector") or {},
                    "desired_replicas": desired,
                    "available_replicas": replicas,
                    "available": available,
                    "degraded": conditions.get("Degraded"),
                }
            )
        return {"count": len(rows), "available_count": available_count, "unavailable_count": unavailable_count, "ingress_controllers": rows}

    def list_cluster_proxy_config(self) -> dict[str, Any]:
        items = self._list_custom(group="config.openshift.io", version="v1", plural="proxies")
        item = next((entry for entry in items if (entry.get("metadata") or {}).get("name") == "cluster"), None)
        if item is None:
            return {"count": 0, "cluster_proxies": []}
        spec = item.get("spec") or {}
        status = item.get("status") or {}
        no_proxy = spec.get("noProxy") or status.get("noProxy") or ""
        return {
            "count": 1,
            "cluster_proxies": [
                {
                    "http_proxy_configured": bool(spec.get("httpProxy") or status.get("httpProxy")),
                    "https_proxy_configured": bool(spec.get("httpsProxy") or status.get("httpsProxy")),
                    "readiness_endpoint_count": len(spec.get("readinessEndpoints") or []),
                    "no_proxy_entry_count": len([entry for entry in str(no_proxy).split(",") if entry.strip()]),
                    "trusted_ca_name": ((spec.get("trustedCA") or {}).get("name")),
                    "readiness_endpoints": spec.get("readinessEndpoints") or [],
                    "status": status,
                }
            ],
        }

    def list_cluster_dns_config(self) -> dict[str, Any]:
        items = self._list_custom(group="operator.openshift.io", version="v1", plural="dnses")
        item = next((entry for entry in items if (entry.get("metadata") or {}).get("name") == "default"), None) or (items[0] if items else None)
        if item is None:
            return {"count": 0, "dns_configurations": []}
        metadata = item.get("metadata") or {}
        spec = item.get("spec") or {}
        status = item.get("status") or {}
        return {
            "count": 1,
            "dns_configurations": [
                {
                    "dns_name": metadata.get("name"),
                    "namespace": metadata.get("namespace"),
                    "base_domain": spec.get("baseDomain") or status.get("clusterDomain"),
                    "log_level": spec.get("logLevel"),
                    "upstream_resolver_count": len(spec.get("upstreamResolvers") or []),
                    "upstream_resolvers": spec.get("upstreamResolvers") or [],
                    "server_count": len(spec.get("servers") or []),
                    "node_placement_configured": bool(spec.get("nodePlacement")),
                    "public_zone": spec.get("publicZone") or status.get("publicZone"),
                    "private_zone": spec.get("privateZone") or status.get("privateZone"),
                }
            ],
        }

    def list_feature_gate_config(self) -> dict[str, Any]:
        items = self._list_custom(group="config.openshift.io", version="v1", plural="featuregates")
        item = next((entry for entry in items if (entry.get("metadata") or {}).get("name") == "cluster"), None)
        if item is None:
            return {"count": 0, "feature_gates": []}
        spec = item.get("spec") or {}
        custom = spec.get("customNoUpgrade") or {}
        enabled = custom.get("enabled") or []
        disabled = custom.get("disabled") or []
        return {
            "count": 1,
            "feature_gates": [
                {
                    "feature_set": spec.get("featureSet"),
                    "enabled_custom_feature_count": len(enabled),
                    "disabled_custom_feature_count": len(disabled),
                    "enabled_custom_features": enabled,
                    "disabled_custom_features": disabled,
                }
            ],
        }

    def list_scheduler_config(self) -> dict[str, Any]:
        items = self._list_custom(group="config.openshift.io", version="v1", plural="schedulers")
        item = next((entry for entry in items if (entry.get("metadata") or {}).get("name") == "cluster"), None)
        if item is None:
            return {"count": 0, "scheduler_configurations": []}
        spec = item.get("spec") or {}
        policy = spec.get("policy") or {}
        profiles = spec.get("profiles") or []
        return {
            "count": 1,
            "scheduler_configurations": [
                {
                    "policy_name": policy.get("name") if isinstance(policy, dict) else policy,
                    "profile_count": len(profiles),
                    "profiles": profiles,
                    "default_node_selector": spec.get("defaultNodeSelector"),
                    "masters_schedulable": spec.get("mastersSchedulable"),
                }
            ],
        }

    def list_nodes(self) -> dict[str, Any]:
        self._ensure_clients()
        assert self._core is not None
        rows = []
        not_ready_count = 0
        for node in self._core.list_node().items:
            conditions = getattr(getattr(node, "status", None), "conditions", None)
            ready = self._condition_status(conditions, "Ready")
            if ready != "True":
                not_ready_count += 1
            labels = self._labels(node)
            roles = sorted(label.split("node-role.kubernetes.io/", 1)[1] for label in labels if label.startswith("node-role.kubernetes.io/"))
            node_info = getattr(getattr(node, "status", None), "node_info", None)
            rows.append(
                {
                    "node_name": self._metadata_name(node),
                    "roles": roles,
                    "labels": labels,
                    "ready": ready,
                    "unschedulable": getattr(getattr(node, "spec", None), "unschedulable", False),
                    "kubelet_version": getattr(node_info, "kubelet_version", None),
                    "taint_count": len(getattr(getattr(node, "spec", None), "taints", None) or []),
                    "created_at": self._creation_timestamp(node),
                }
            )
        return {"count": len(rows), "not_ready_count": not_ready_count, "nodes": rows}

    def list_node_pressure(self) -> dict[str, Any]:
        self._ensure_clients()
        assert self._core is not None
        rows = []
        pressure_counts = {"memory": 0, "disk": 0, "pid": 0, "not_ready": 0}
        for node in self._core.list_node().items:
            conditions = getattr(getattr(node, "status", None), "conditions", None) or []
            memory_pressure = self._condition_status(conditions, "MemoryPressure")
            disk_pressure = self._condition_status(conditions, "DiskPressure")
            pid_pressure = self._condition_status(conditions, "PIDPressure")
            ready = self._condition_status(conditions, "Ready")
            if memory_pressure == "True":
                pressure_counts["memory"] += 1
            if disk_pressure == "True":
                pressure_counts["disk"] += 1
            if pid_pressure == "True":
                pressure_counts["pid"] += 1
            if ready != "True":
                pressure_counts["not_ready"] += 1
            rows.append(
                {
                    "node_name": self._metadata_name(node),
                    "ready": ready,
                    "memory_pressure": memory_pressure,
                    "disk_pressure": disk_pressure,
                    "pid_pressure": pid_pressure,
                }
            )
        return {"count": len(rows), "pressure_counts": pressure_counts, "nodes": rows}

    def list_pods(self, project: str | None = None) -> dict[str, Any]:
        self._ensure_clients()
        assert self._core is not None
        rows = []
        risky_pod_count = 0
        for namespace in self._selected_projects(project):
            for pod in self._core.list_namespaced_pod(namespace).items:
                phase = getattr(getattr(pod, "status", None), "phase", None)
                restart_count = sum(getattr(container, "restart_count", 0) for container in getattr(getattr(pod, "status", None), "container_statuses", None) or [])
                if phase in {"Pending", "Failed", "Unknown"} or restart_count > 3:
                    risky_pod_count += 1
                rows.append(
                    {
                        "project": namespace,
                        "pod_name": self._metadata_name(pod),
                        "phase": phase,
                        "node_name": getattr(getattr(pod, "spec", None), "node_name", None),
                        "restart_count": restart_count,
                        "host_ip": getattr(getattr(pod, "status", None), "host_ip", None),
                        "pod_ip": getattr(getattr(pod, "status", None), "pod_ip", None),
                    }
                )
        return {"count": len(rows), "risky_pod_count": risky_pod_count, "pods": rows}

    def list_workload_health(self, project: str | None = None) -> dict[str, Any]:
        self._ensure_clients()
        assert self._apps is not None
        assert self._batch is not None
        rows = []
        degraded_count = 0
        for namespace in self._selected_projects(project):
            for deployment in self._apps.list_namespaced_deployment(namespace).items:
                desired = getattr(getattr(deployment, "spec", None), "replicas", 0) or 0
                available = getattr(getattr(deployment, "status", None), "available_replicas", 0) or 0
                ready = getattr(getattr(deployment, "status", None), "ready_replicas", 0) or 0
                unavailable = max(desired - available, 0)
                if unavailable > 0:
                    degraded_count += 1
                rows.append({"project": namespace, "kind": "Deployment", "name": self._metadata_name(deployment), "desired": desired, "available": available, "ready": ready, "unavailable": unavailable})
            for statefulset in self._apps.list_namespaced_stateful_set(namespace).items:
                desired = getattr(getattr(statefulset, "spec", None), "replicas", 0) or 0
                ready = getattr(getattr(statefulset, "status", None), "ready_replicas", 0) or 0
                if ready < desired:
                    degraded_count += 1
                rows.append({"project": namespace, "kind": "StatefulSet", "name": self._metadata_name(statefulset), "desired": desired, "available": ready, "ready": ready, "unavailable": max(desired - ready, 0)})
            for daemonset in self._apps.list_namespaced_daemon_set(namespace).items:
                desired = getattr(getattr(daemonset, "status", None), "desired_number_scheduled", 0) or 0
                ready = getattr(getattr(daemonset, "status", None), "number_ready", 0) or 0
                if ready < desired:
                    degraded_count += 1
                rows.append({"project": namespace, "kind": "DaemonSet", "name": self._metadata_name(daemonset), "desired": desired, "available": ready, "ready": ready, "unavailable": max(desired - ready, 0)})
            for job in self._batch.list_namespaced_job(namespace).items:
                succeeded = getattr(getattr(job, "status", None), "succeeded", 0) or 0
                failed = getattr(getattr(job, "status", None), "failed", 0) or 0
                if failed > 0:
                    degraded_count += 1
                rows.append({"project": namespace, "kind": "Job", "name": self._metadata_name(job), "desired": getattr(getattr(job, "spec", None), "completions", None), "available": succeeded, "ready": succeeded, "unavailable": failed})
        return {"count": len(rows), "degraded_count": degraded_count, "workloads": rows}

    def list_services(self, project: str | None = None) -> dict[str, Any]:
        self._ensure_clients()
        assert self._core is not None
        rows = []
        for namespace in self._selected_projects(project):
            for svc in self._core.list_namespaced_service(namespace).items:
                rows.append(
                    {
                        "project": namespace,
                        "service_name": self._metadata_name(svc),
                        "type": getattr(getattr(svc, "spec", None), "type", None),
                        "cluster_ip": getattr(getattr(svc, "spec", None), "cluster_ip", None),
                        "port_count": len(getattr(getattr(svc, "spec", None), "ports", None) or []),
                        "selector": getattr(getattr(svc, "spec", None), "selector", None) or {},
                    }
                )
        return {"count": len(rows), "services": rows}

    def list_routes(self, project: str | None = None) -> dict[str, Any]:
        rows = []
        insecure_count = 0
        for namespace in self._selected_projects(project):
            for item in self._list_custom(group="route.openshift.io", version="v1", plural="routes", namespace=namespace):
                tls = item.get("spec", {}).get("tls") or {}
                admitted = any(condition.get("type") == "Admitted" and condition.get("status") == "True" for ingress in item.get("status", {}).get("ingress") or [] for condition in ingress.get("conditions") or [])
                if not tls:
                    insecure_count += 1
                rows.append(
                    {
                        "project": namespace,
                        "route_name": (item.get("metadata") or {}).get("name"),
                        "host": item.get("spec", {}).get("host"),
                        "path": item.get("spec", {}).get("path"),
                        "tls_termination": tls.get("termination"),
                        "wildcard_policy": item.get("spec", {}).get("wildcardPolicy"),
                        "admitted": admitted,
                    }
                )
        return {"count": len(rows), "insecure_count": insecure_count, "routes": rows}

    def list_ingresses(self, project: str | None = None) -> dict[str, Any]:
        self._ensure_clients()
        assert self._networking is not None
        rows = []
        for namespace in self._selected_projects(project):
            for ingress in self._networking.list_namespaced_ingress(namespace).items:
                rows.append(
                    {
                        "project": namespace,
                        "ingress_name": self._metadata_name(ingress),
                        "class_name": getattr(getattr(ingress, "spec", None), "ingress_class_name", None),
                        "host_count": len(getattr(getattr(ingress, "spec", None), "rules", None) or []),
                        "tls_count": len(getattr(getattr(ingress, "spec", None), "tls", None) or []),
                    }
                )
        return {"count": len(rows), "ingresses": rows}

    def list_events(self, project: str | None = None) -> dict[str, Any]:
        self._ensure_clients()
        assert self._core is not None
        rows = []
        warning_count = 0
        for namespace in self._selected_projects(project):
            for event in self._core.list_namespaced_event(namespace).items[:100]:
                event_type = getattr(event, "type", None)
                if event_type == "Warning":
                    warning_count += 1
                rows.append(
                    {
                        "project": namespace,
                        "reason": getattr(event, "reason", None),
                        "type": event_type,
                        "object": getattr(getattr(event, "involved_object", None), "name", None),
                        "kind": getattr(getattr(event, "involved_object", None), "kind", None),
                        "message": getattr(event, "message", None),
                        "count": getattr(event, "count", None),
                        "last_timestamp": getattr(event, "last_timestamp", None).isoformat() if getattr(event, "last_timestamp", None) else None,
                    }
                )
        return {"count": len(rows), "warning_count": warning_count, "events": rows}

    def list_persistent_storage(self, project: str | None = None) -> dict[str, Any]:
        self._ensure_clients()
        assert self._core is not None
        pvs = []
        pvcs = []
        pending_pvc_count = 0
        for pv in self._core.list_persistent_volume().items:
            pvs.append(
                {
                    "pv_name": self._metadata_name(pv),
                    "phase": getattr(getattr(pv, "status", None), "phase", None),
                    "capacity": self._resource_value(getattr(getattr(pv, "spec", None), "capacity", None), "storage"),
                    "access_modes": getattr(getattr(pv, "spec", None), "access_modes", None) or [],
                    "storage_class": getattr(getattr(pv, "spec", None), "storage_class_name", None),
                    "claim_ref": getattr(getattr(getattr(pv, "spec", None), "claim_ref", None), "name", None),
                }
            )
        for namespace in self._selected_projects(project):
            for pvc in self._core.list_namespaced_persistent_volume_claim(namespace).items:
                phase = getattr(getattr(pvc, "status", None), "phase", None)
                resources = getattr(getattr(pvc, "spec", None), "resources", None)
                if phase != "Bound":
                    pending_pvc_count += 1
                pvcs.append(
                    {
                        "project": namespace,
                        "pvc_name": self._metadata_name(pvc),
                        "phase": phase,
                        "requested_storage": self._resource_value(getattr(resources, "requests", None), "storage"),
                        "access_modes": getattr(getattr(pvc, "spec", None), "access_modes", None) or [],
                        "storage_class": getattr(getattr(pvc, "spec", None), "storage_class_name", None),
                        "volume_name": getattr(getattr(pvc, "spec", None), "volume_name", None),
                    }
                )
        return {"pv_count": len(pvs), "pvc_count": len(pvcs), "pending_pvc_count": pending_pvc_count, "persistent_volumes": pvs, "persistent_volume_claims": pvcs}

    def list_horizontal_pod_autoscalers(self, project: str | None = None) -> dict[str, Any]:
        self._ensure_clients()
        assert self._autoscaling is not None
        rows = []
        constrained_count = 0
        for namespace in self._selected_projects(project):
            for autoscaler in self._autoscaling.list_namespaced_horizontal_pod_autoscaler(namespace).items:
                spec = getattr(autoscaler, "spec", None)
                status = getattr(autoscaler, "status", None)
                current = getattr(status, "current_replicas", None)
                maximum = getattr(spec, "max_replicas", None)
                if current is not None and maximum is not None and current >= maximum:
                    constrained_count += 1
                rows.append(
                    {
                        "project": namespace,
                        "horizontal_pod_autoscaler_name": self._metadata_name(autoscaler),
                        "target_kind": getattr(getattr(spec, "scale_target_ref", None), "kind", None),
                        "target_name": getattr(getattr(spec, "scale_target_ref", None), "name", None),
                        "min_replicas": getattr(spec, "min_replicas", None),
                        "max_replicas": maximum,
                        "current_replicas": current,
                        "desired_replicas": getattr(status, "desired_replicas", None),
                        "condition_count": len(getattr(status, "conditions", None) or []),
                    }
                )
        return {"count": len(rows), "constrained_count": constrained_count, "horizontal_pod_autoscalers": rows}

    def list_pod_disruption_budgets(self, project: str | None = None) -> dict[str, Any]:
        self._ensure_clients()
        assert self._policy is not None
        rows = []
        blocking_count = 0
        for namespace in self._selected_projects(project):
            for pdb in self._policy.list_namespaced_pod_disruption_budget(namespace).items:
                status = getattr(pdb, "status", None)
                disruptions = getattr(status, "disruptions_allowed", None)
                if disruptions == 0:
                    blocking_count += 1
                rows.append(
                    {
                        "project": namespace,
                        "pod_disruption_budget_name": self._metadata_name(pdb),
                        "min_available": getattr(getattr(pdb, "spec", None), "min_available", None),
                        "max_unavailable": getattr(getattr(pdb, "spec", None), "max_unavailable", None),
                        "current_healthy": getattr(status, "current_healthy", None),
                        "desired_healthy": getattr(status, "desired_healthy", None),
                        "expected_pods": getattr(status, "expected_pods", None),
                        "disruptions_allowed": disruptions,
                    }
                )
        return {"count": len(rows), "blocking_count": blocking_count, "pod_disruption_budgets": rows}

    def list_cronjobs(self, project: str | None = None) -> dict[str, Any]:
        self._ensure_clients()
        assert self._batch is not None
        rows = []
        suspended_count = 0
        for namespace in self._selected_projects(project):
            for cronjob in self._batch.list_namespaced_cron_job(namespace).items:
                spec = getattr(cronjob, "spec", None)
                status = getattr(cronjob, "status", None)
                suspended = bool(getattr(spec, "suspend", False))
                if suspended:
                    suspended_count += 1
                rows.append(
                    {
                        "project": namespace,
                        "cronjob_name": self._metadata_name(cronjob),
                        "schedule": getattr(spec, "schedule", None),
                        "suspend": suspended,
                        "concurrency_policy": getattr(spec, "concurrency_policy", None),
                        "last_schedule_time": getattr(status, "last_schedule_time", None).isoformat() if getattr(status, "last_schedule_time", None) else None,
                        "active_job_count": len(getattr(status, "active", None) or []),
                    }
                )
        return {"count": len(rows), "suspended_count": suspended_count, "cronjobs": rows}

    def list_volume_snapshots(self, project: str | None = None) -> dict[str, Any]:
        snapshot_rows = []
        ready_count = 0
        namespaces = self._selected_projects(project)
        for namespace in namespaces:
            for item in self._list_custom_any_version(
                group="snapshot.storage.k8s.io",
                versions=("v1", "v1beta1"),
                plural="volumesnapshots",
                namespace=namespace,
            ):
                metadata = item.get("metadata") or {}
                spec = item.get("spec") or {}
                status = item.get("status") or {}
                if status.get("readyToUse") is True:
                    ready_count += 1
                snapshot_rows.append(
                    {
                        "project": namespace,
                        "volume_snapshot_name": metadata.get("name"),
                        "source_pvc": ((spec.get("source") or {}).get("persistentVolumeClaimName")),
                        "volume_snapshot_class_name": spec.get("volumeSnapshotClassName"),
                        "ready_to_use": status.get("readyToUse"),
                        "restore_size": status.get("restoreSize"),
                    }
                )
        snapshot_class_rows = [
            {
                "volume_snapshot_class_name": (item.get("metadata") or {}).get("name"),
                "driver": (item.get("driver")),
                "deletion_policy": item.get("deletionPolicy"),
                "is_default": ((item.get("metadata") or {}).get("annotations") or {}).get("snapshot.storage.kubernetes.io/is-default-class") == "true",
            }
            for item in self._list_custom_any_version(
                group="snapshot.storage.k8s.io",
                versions=("v1", "v1beta1"),
                plural="volumesnapshotclasses",
            )
        ]
        return {
            "volume_snapshot_count": len(snapshot_rows),
            "ready_volume_snapshot_count": ready_count,
            "volume_snapshot_class_count": len(snapshot_class_rows),
            "volume_snapshots": snapshot_rows,
            "volume_snapshot_classes": snapshot_class_rows,
        }

    def list_storage_classes(self) -> dict[str, Any]:
        self._ensure_clients()
        assert self._storage is not None
        rows = []
        default_count = 0
        for storage_class in self._storage.list_storage_class().items:
            labels = self._labels(storage_class)
            is_default = labels.get("storageclass.kubernetes.io/is-default-class") == "true" or labels.get("storageclass.beta.kubernetes.io/is-default-class") == "true"
            if is_default:
                default_count += 1
            rows.append(
                {
                    "storage_class_name": self._metadata_name(storage_class),
                    "provisioner": getattr(storage_class, "provisioner", None),
                    "allow_volume_expansion": getattr(storage_class, "allow_volume_expansion", None),
                    "reclaim_policy": getattr(storage_class, "reclaim_policy", None),
                    "volume_binding_mode": getattr(storage_class, "volume_binding_mode", None),
                    "is_default": is_default,
                }
            )
        return {"count": len(rows), "default_count": default_count, "storage_classes": rows}

    def list_machine_config_pools(self) -> dict[str, Any]:
        rows = []
        degraded_count = 0
        for item in self._list_custom(group="machineconfiguration.openshift.io", version="v1", plural="machineconfigpools"):
            conditions = item.get("status", {}).get("conditions") or []
            degraded = next((condition.get("status") for condition in conditions if condition.get("type") == "Degraded"), None)
            updating = next((condition.get("status") for condition in conditions if condition.get("type") == "Updating"), None)
            if degraded == "True":
                degraded_count += 1
            rows.append(
                {
                    "name": (item.get("metadata") or {}).get("name"),
                    "machine_count": item.get("status", {}).get("machineCount"),
                    "ready_machine_count": item.get("status", {}).get("readyMachineCount"),
                    "updated_machine_count": item.get("status", {}).get("updatedMachineCount"),
                    "degraded": degraded,
                    "updating": updating,
                }
            )
        return {"count": len(rows), "degraded_count": degraded_count, "machine_config_pools": rows}

    def list_machine_sets(self) -> dict[str, Any]:
        namespace = "openshift-machine-api"
        rows = []
        for item in self._list_custom(group="machine.openshift.io", version="v1beta1", plural="machinesets", namespace=namespace):
            desired = item.get("spec", {}).get("replicas") or 0
            ready = item.get("status", {}).get("readyReplicas") or 0
            rows.append(
                {
                    "project": namespace,
                    "machine_set_name": (item.get("metadata") or {}).get("name"),
                    "desired_replicas": desired,
                    "ready_replicas": ready,
                    "available_replicas": item.get("status", {}).get("availableReplicas") or 0,
                    "unavailable_replicas": max(desired - ready, 0),
                }
            )
        return {"count": len(rows), "machine_sets": rows}

    def list_machine_health_checks(self) -> dict[str, Any]:
        namespace = "openshift-machine-api"
        rows = []
        remediation_enabled_count = 0
        for item in self._list_custom_any_version(
            group="machine.openshift.io",
            versions=("v1beta1", "v1"),
            plural="machinehealthchecks",
            namespace=namespace,
        ):
            metadata = item.get("metadata") or {}
            spec = item.get("spec") or {}
            status = item.get("status") or {}
            remediation = spec.get("remediationTemplate") or {}
            if remediation:
                remediation_enabled_count += 1
            rows.append(
                {
                    "namespace": namespace,
                    "machine_health_check_name": metadata.get("name"),
                    "selector": spec.get("selector") or {},
                    "max_unhealthy": spec.get("maxUnhealthy"),
                    "node_startup_timeout": spec.get("nodeStartupTimeout"),
                    "unhealthy_condition_count": len(spec.get("unhealthyConditions") or []),
                    "current_healthy": status.get("currentHealthy"),
                    "expected_machines": status.get("expectedMachines"),
                    "remediations_allowed": status.get("remediationsAllowed"),
                    "remediation_template": remediation,
                }
            )
        return {
            "count": len(rows),
            "remediation_enabled_count": remediation_enabled_count,
            "machine_health_checks": rows,
        }

    def list_cluster_autoscaling(self) -> dict[str, Any]:
        cluster_autoscaler_rows = []
        machine_autoscaler_rows = []
        machine_autoscaler_enabled_count = 0
        for item in self._list_custom_any_version(
            group="autoscaling.openshift.io",
            versions=("v1", "v1beta1"),
            plural="clusterautoscalers",
        ):
            metadata = item.get("metadata") or {}
            spec = item.get("spec") or {}
            cluster_autoscaler_rows.append(
                {
                    "cluster_autoscaler_name": metadata.get("name"),
                    "pod_priority_threshold": spec.get("podPriorityThreshold"),
                    "max_node_provision_time": spec.get("maxNodeProvisionTime"),
                    "balance_similar_node_groups": spec.get("balanceSimilarNodeGroups"),
                    "scale_down_enabled": ((spec.get("scaleDown") or {}).get("enabled")),
                    "scale_down_delay_after_add": ((spec.get("scaleDown") or {}).get("delayAfterAdd")),
                    "scale_down_unneeded_time": ((spec.get("scaleDown") or {}).get("unneededTime")),
                    "resource_limits": spec.get("resourceLimits") or {},
                }
            )
        for item in self._list_custom_any_version(
            group="autoscaling.openshift.io",
            versions=("v1beta1", "v1"),
            plural="machineautoscalers",
            namespace="openshift-machine-api",
        ):
            metadata = item.get("metadata") or {}
            spec = item.get("spec") or {}
            min_replicas = spec.get("minReplicas")
            max_replicas = spec.get("maxReplicas")
            if min_replicas is not None or max_replicas is not None:
                machine_autoscaler_enabled_count += 1
            rows_target = spec.get("scaleTargetRef") or {}
            machine_autoscaler_rows.append(
                {
                    "namespace": "openshift-machine-api",
                    "machine_autoscaler_name": metadata.get("name"),
                    "target_kind": rows_target.get("kind"),
                    "target_name": rows_target.get("name"),
                    "min_replicas": min_replicas,
                    "max_replicas": max_replicas,
                }
            )
        return {
            "cluster_autoscaler_count": len(cluster_autoscaler_rows),
            "machine_autoscaler_count": len(machine_autoscaler_rows),
            "machine_autoscaler_enabled_count": machine_autoscaler_enabled_count,
            "cluster_autoscalers": cluster_autoscaler_rows,
            "machine_autoscalers": machine_autoscaler_rows,
        }

    def list_operator_subscriptions(self) -> dict[str, Any]:
        rows = []
        unhealthy_count = 0
        for namespace in ["openshift-operators", "openshift-operators-redhat"]:
            for item in self._list_custom(group="operators.coreos.com", version="v1alpha1", plural="subscriptions", namespace=namespace):
                state = (item.get("status") or {}).get("state")
                if state not in {None, "AtLatestKnown", "UpgradePending"}:
                    unhealthy_count += 1
                rows.append(
                    {
                        "project": namespace,
                        "subscription_name": (item.get("metadata") or {}).get("name"),
                        "channel": item.get("spec", {}).get("channel"),
                        "source": item.get("spec", {}).get("source"),
                        "package": item.get("spec", {}).get("name"),
                        "state": state,
                        "installed_csv": (item.get("status") or {}).get("installedCSV"),
                    }
                )
        return {"count": len(rows), "unhealthy_count": unhealthy_count, "subscriptions": rows}

    def list_cluster_service_versions(self) -> dict[str, Any]:
        rows = []
        failed_count = 0
        for namespace in ["openshift-operators", "openshift-operators-redhat"]:
            for item in self._list_custom(group="operators.coreos.com", version="v1alpha1", plural="clusterserviceversions", namespace=namespace):
                phase = (item.get("status") or {}).get("phase")
                if phase not in {None, "Succeeded", "Replacing"}:
                    failed_count += 1
                rows.append(
                    {
                        "project": namespace,
                        "csv_name": (item.get("metadata") or {}).get("name"),
                        "phase": phase,
                        "version": (item.get("spec") or {}).get("version"),
                        "display_name": (item.get("spec") or {}).get("displayName"),
                    }
                )
        return {"count": len(rows), "failed_count": failed_count, "cluster_service_versions": rows}

    def list_monitoring_alert_posture(self) -> dict[str, Any]:
        namespaces = self._namespace_candidates(["openshift-monitoring", "openshift-user-workload-monitoring"], self._all_projects())
        alertmanager_rows = []
        prometheus_rows = []
        rule_rows = []
        unavailable_alertmanager_count = 0
        unavailable_prometheus_count = 0
        alert_rule_count = 0
        critical_alert_rule_count = 0
        warning_alert_rule_count = 0

        for item in self._list_custom_from_namespaces(
            group="monitoring.coreos.com",
            versions=("v1",),
            plural="alertmanagers",
            namespaces=namespaces,
        ):
            metadata = item.get("metadata") or {}
            spec = item.get("spec") or {}
            status = item.get("status") or {}
            available = status.get("availableReplicas") or 0
            desired = spec.get("replicas") or 0
            if desired and available < desired:
                unavailable_alertmanager_count += 1
            alertmanager_rows.append(
                {
                    "namespace": metadata.get("namespace"),
                    "alertmanager_name": metadata.get("name"),
                    "desired_replicas": desired,
                    "available_replicas": available,
                    "paused": spec.get("paused"),
                    "external_url": spec.get("externalUrl"),
                }
            )

        for item in self._list_custom_from_namespaces(
            group="monitoring.coreos.com",
            versions=("v1",),
            plural="prometheuses",
            namespaces=namespaces,
        ):
            metadata = item.get("metadata") or {}
            spec = item.get("spec") or {}
            status = item.get("status") or {}
            available = status.get("availableReplicas") or 0
            desired = spec.get("replicas") or 0
            if desired and available < desired:
                unavailable_prometheus_count += 1
            prometheus_rows.append(
                {
                    "namespace": metadata.get("namespace"),
                    "prometheus_name": metadata.get("name"),
                    "desired_replicas": desired,
                    "available_replicas": available,
                    "paused": spec.get("paused"),
                    "rule_namespace_selector": spec.get("ruleNamespaceSelector") or {},
                }
            )

        for item in self._list_custom_from_namespaces(
            group="monitoring.coreos.com",
            versions=("v1",),
            plural="prometheusrules",
            namespaces=namespaces,
        ):
            metadata = item.get("metadata") or {}
            spec = item.get("spec") or {}
            groups = spec.get("groups") or []
            rule_count = 0
            critical_count = 0
            warning_count = 0
            for group in groups:
                for rule in group.get("rules") or []:
                    if not rule.get("alert"):
                        continue
                    rule_count += 1
                    severity = str(((rule.get("labels") or {}).get("severity")) or "").lower()
                    if severity == "critical":
                        critical_count += 1
                    elif severity == "warning":
                        warning_count += 1
            alert_rule_count += rule_count
            critical_alert_rule_count += critical_count
            warning_alert_rule_count += warning_count
            rule_rows.append(
                {
                    "namespace": metadata.get("namespace"),
                    "prometheus_rule_name": metadata.get("name"),
                    "group_count": len(groups),
                    "alert_rule_count": rule_count,
                    "critical_alert_rule_count": critical_count,
                    "warning_alert_rule_count": warning_count,
                }
            )

        return {
            "alertmanager_count": len(alertmanager_rows),
            "unavailable_alertmanager_count": unavailable_alertmanager_count,
            "prometheus_count": len(prometheus_rows),
            "unavailable_prometheus_count": unavailable_prometheus_count,
            "prometheus_rule_count": len(rule_rows),
            "alert_rule_count": alert_rule_count,
            "critical_alert_rule_count": critical_alert_rule_count,
            "warning_alert_rule_count": warning_alert_rule_count,
            "alertmanagers": alertmanager_rows,
            "prometheuses": prometheus_rows,
            "prometheus_rules": rule_rows,
        }

    def list_control_plane_certificates(self) -> dict[str, Any]:
        self._ensure_clients()
        assert self._core is not None
        rows = []
        expired_count = 0
        expiring_within_30d_count = 0
        trust_bundle_count = 0
        namespaces = self._namespace_candidates(self._control_plane_namespaces(), self._selected_projects())
        candidate_keys = {"tls.crt", "ca.crt", "service-ca.crt", "ca-bundle.crt", "trusted-ca-bundle"}

        def _record(namespace: str, kind: str, resource_name: str, key: str, raw_value: str) -> None:
            nonlocal expired_count, expiring_within_30d_count, trust_bundle_count
            certs = self._extract_pem_certificates(raw_value)
            if not certs:
                return
            decoded = self._decode_pem_certificate(certs[0])
            if decoded is None:
                return
            trust_bundle = (
                "ca" in key.lower()
                or "bundle" in key.lower()
                or "trusted-ca" in resource_name.lower()
                or resource_name.lower().endswith("-ca")
            )
            if trust_bundle:
                trust_bundle_count += 1
            days_until_expiry = decoded.get("days_until_expiry")
            expired = bool(decoded.get("expired"))
            if expired:
                expired_count += 1
            elif isinstance(days_until_expiry, int) and days_until_expiry <= 30:
                expiring_within_30d_count += 1
            rows.append(
                {
                    "namespace": namespace,
                    "resource_kind": kind,
                    "resource_name": resource_name,
                    "data_key": key,
                    "certificate_count": len(certs),
                    "trust_bundle": trust_bundle,
                    **decoded,
                }
            )

        for namespace in namespaces:
            try:
                for secret in self._core.list_namespaced_secret(namespace).items:
                    for key, value in (getattr(secret, "data", None) or {}).items():
                        if key in candidate_keys or key.endswith(".crt") or key.endswith(".pem"):
                            try:
                                decoded_text = base64.b64decode(value).decode("utf-8", errors="ignore")
                            except Exception:  # noqa: BLE001
                                continue
                            _record(namespace, "Secret", self._metadata_name(secret) or "unknown", key, decoded_text)
            except ApiException as error:
                if error.status not in {403, 404}:
                    raise

            try:
                for config_map in self._core.list_namespaced_config_map(namespace).items:
                    for key, value in (getattr(config_map, "data", None) or {}).items():
                        if key in candidate_keys or key.endswith(".crt") or key.endswith(".pem") or "bundle" in key.lower():
                            _record(namespace, "ConfigMap", self._metadata_name(config_map) or "unknown", key, value)
            except ApiException as error:
                if error.status not in {403, 404}:
                    raise

        rows.sort(key=lambda item: (item.get("days_until_expiry") is None, item.get("days_until_expiry") if item.get("days_until_expiry") is not None else 10**9, item.get("namespace") or "", item.get("resource_name") or ""))
        return {
            "count": len(rows),
            "expired_count": expired_count,
            "expiring_within_30d_count": expiring_within_30d_count,
            "trust_bundle_count": trust_bundle_count,
            "control_plane_certificates": rows,
        }

    def list_api_service_health(self) -> dict[str, Any]:
        self._ensure_clients()
        assert self._apiregistration is not None
        rows = []
        unavailable_count = 0
        local_count = 0
        insecure_skip_tls_count = 0
        try:
            items = self._apiregistration.list_api_service().items
        except ApiException as error:
            if error.status in {403, 404}:
                return {"count": 0, "unavailable_count": 0, "local_count": 0, "insecure_skip_tls_count": 0, "api_services": []}
            raise
        for api_service in items:
            metadata = getattr(api_service, "metadata", None)
            spec = getattr(api_service, "spec", None)
            status = getattr(api_service, "status", None)
            service_ref = getattr(spec, "service", None)
            available = self._condition_status(getattr(status, "conditions", None), "Available")
            if available != "True":
                unavailable_count += 1
            if service_ref is None:
                local_count += 1
            if getattr(spec, "insecure_skip_tls_verify", False):
                insecure_skip_tls_count += 1
            rows.append(
                {
                    "api_service_name": getattr(metadata, "name", None),
                    "group": getattr(spec, "group", None),
                    "version": getattr(spec, "version", None),
                    "group_priority_minimum": getattr(spec, "group_priority_minimum", None),
                    "version_priority": getattr(spec, "version_priority", None),
                    "service_namespace": getattr(service_ref, "namespace", None) if service_ref else None,
                    "service_name": getattr(service_ref, "name", None) if service_ref else None,
                    "local": service_ref is None,
                    "insecure_skip_tls_verify": bool(getattr(spec, "insecure_skip_tls_verify", False)),
                    "ca_bundle_configured": bool(getattr(spec, "ca_bundle", None)),
                    "available": available,
                    "reason": next((getattr(condition, "reason", None) for condition in getattr(status, "conditions", None) or [] if getattr(condition, "type", None) == "Available"), None),
                    "message": next((getattr(condition, "message", None) for condition in getattr(status, "conditions", None) or [] if getattr(condition, "type", None) == "Available"), None),
                }
            )
        return {
            "count": len(rows),
            "unavailable_count": unavailable_count,
            "local_count": local_count,
            "insecure_skip_tls_count": insecure_skip_tls_count,
            "api_services": rows,
        }

    def list_certificatesigning_requests(self) -> dict[str, Any]:
        self._ensure_clients()
        assert self._certificates is not None
        rows = []
        approved_count = 0
        denied_count = 0
        pending_count = 0
        issued_count = 0
        try:
            items = self._certificates.list_certificate_signing_request().items
        except ApiException as error:
            if error.status in {403, 404}:
                return {
                    "count": 0,
                    "approved_count": 0,
                    "denied_count": 0,
                    "pending_count": 0,
                    "issued_count": 0,
                    "certificate_signing_requests": [],
                }
            raise
        for request in items:
            metadata = getattr(request, "metadata", None)
            spec = getattr(request, "spec", None)
            status = getattr(request, "status", None)
            condition_types = {getattr(condition, "type", None) for condition in getattr(status, "conditions", None) or []}
            approved = "Approved" in condition_types
            denied = "Denied" in condition_types
            issued = bool(getattr(status, "certificate", None))
            if approved:
                approved_count += 1
            if denied:
                denied_count += 1
            if issued:
                issued_count += 1
            if not approved and not denied:
                pending_count += 1
            rows.append(
                {
                    "csr_name": getattr(metadata, "name", None),
                    "signer_name": getattr(spec, "signer_name", None),
                    "username": getattr(spec, "username", None),
                    "group_count": len(getattr(spec, "groups", None) or []),
                    "expiration_seconds": getattr(spec, "expiration_seconds", None),
                    "approved": approved,
                    "denied": denied,
                    "pending": not approved and not denied,
                    "certificate_issued": issued,
                    "created_at": self._creation_timestamp(request),
                }
            )
        return {
            "count": len(rows),
            "approved_count": approved_count,
            "denied_count": denied_count,
            "pending_count": pending_count,
            "issued_count": issued_count,
            "certificate_signing_requests": rows,
        }

    def list_acm_multicluster_hubs(self) -> dict[str, Any]:
        namespaces = self._namespace_candidates(
            ["open-cluster-management", "open-cluster-management-hub"],
            self._selected_projects(),
        )
        rows = []
        available_count = 0
        for item in self._list_custom_from_namespaces(
            group="operator.open-cluster-management.io",
            versions=("v1",),
            plural="multiclusterhubs",
            namespaces=namespaces,
        ):
            metadata = item.get("metadata") or {}
            status = item.get("status") or {}
            conditions = self._extract_condition_map(status.get("conditions"))
            available = conditions.get("Available")
            if available == "True":
                available_count += 1
            rows.append(
                {
                    "namespace": metadata.get("namespace"),
                    "hub_name": metadata.get("name"),
                    "phase": status.get("phase"),
                    "current_version": status.get("currentVersion"),
                    "desired_version": status.get("desiredVersion"),
                    "available": available,
                    "updating": conditions.get("Updating"),
                    "components": status.get("components") or [],
                }
            )
        return {"count": len(rows), "available_count": available_count, "multicluster_hubs": rows}

    def list_acm_managed_clusters(self) -> dict[str, Any]:
        rows = []
        available_count = 0
        joined_count = 0
        platform_patterns: dict[str, int] = {}
        for item in self._list_custom_any_version(
            group="cluster.open-cluster-management.io",
            versions=("v1", "v1beta1"),
            plural="managedclusters",
        ):
            metadata = item.get("metadata") or {}
            status = item.get("status") or {}
            conditions = self._extract_condition_map(status.get("conditions"))
            labels = metadata.get("labels") or {}
            vendor = labels.get("vendor") or labels.get("cloud") or labels.get("cluster.open-cluster-management.io/clusterset")
            cluster_name = metadata.get("name")
            platform_pattern = self._guess_platform_pattern(vendor, cluster_name, cluster_name, [])
            platform_patterns[platform_pattern] = platform_patterns.get(platform_pattern, 0) + 1
            if conditions.get("ManagedClusterConditionAvailable") == "True" or conditions.get("Available") == "True":
                available_count += 1
            if conditions.get("ManagedClusterJoined") == "True" or conditions.get("Joined") == "True":
                joined_count += 1
            rows.append(
                {
                    "cluster_name": cluster_name,
                    "labels": labels,
                    "hub_accepted": conditions.get("HubAcceptedManagedCluster") or conditions.get("HubAccepted"),
                    "joined": conditions.get("ManagedClusterJoined") or conditions.get("Joined"),
                    "available": conditions.get("ManagedClusterConditionAvailable") or conditions.get("Available"),
                    "cluster_sets": sorted({value for key, value in labels.items() if "clusterset" in key.lower()}),
                    "version": (status.get("version") or {}).get("kubernetes"),
                    "platform_pattern": platform_pattern,
                }
            )
        return {
            "count": len(rows),
            "available_count": available_count,
            "joined_count": joined_count,
            "platform_pattern_counts": platform_patterns,
            "managed_clusters": rows,
        }

    def list_acm_policies(self) -> dict[str, Any]:
        rows = []
        disabled_count = 0
        compliance_type_counts: dict[str, int] = {}
        for item in self._list_custom_from_namespaces(
            group="policy.open-cluster-management.io",
            versions=("v1",),
            plural="policies",
            namespaces=self._all_projects(),
        ):
            metadata = item.get("metadata") or {}
            spec = item.get("spec") or {}
            status = item.get("status") or {}
            disabled = bool(spec.get("disabled"))
            compliance = status.get("complianceState") or status.get("compliant") or "Unknown"
            compliance_type_counts[compliance] = compliance_type_counts.get(compliance, 0) + 1
            if disabled:
                disabled_count += 1
            rows.append(
                {
                    "namespace": metadata.get("namespace"),
                    "policy_name": metadata.get("name"),
                    "remediation_action": spec.get("remediationAction"),
                    "disabled": disabled,
                    "compliance_state": compliance,
                    "policy_templates": len(spec.get("policy-templates") or []),
                }
            )
        return {
            "count": len(rows),
            "disabled_count": disabled_count,
            "compliance_type_counts": compliance_type_counts,
            "policies": rows,
        }

    def list_acs_central_services(self) -> dict[str, Any]:
        rows = []
        available_count = 0
        for item in self._list_custom_from_namespaces(
            group="platform.stackrox.io",
            versions=("v1alpha1",),
            plural="centralservices",
            namespaces=self._namespace_candidates(
                ["stackrox", "rhacs-operator", "redhat-acs-operator"],
                self._all_projects(),
            ),
        ):
            metadata = item.get("metadata") or {}
            status = item.get("status") or {}
            conditions = self._extract_condition_map(status.get("conditions"))
            available = conditions.get("Available")
            if available == "True":
                available_count += 1
            rows.append(
                {
                    "namespace": metadata.get("namespace"),
                    "central_name": metadata.get("name"),
                    "phase": status.get("phase"),
                    "version": status.get("version"),
                    "available": available,
                    "progressing": conditions.get("Progressing"),
                    "degraded": conditions.get("Degraded"),
                }
            )
        return {"count": len(rows), "available_count": available_count, "central_services": rows}

    def list_acs_secured_clusters(self) -> dict[str, Any]:
        rows = []
        available_count = 0
        for item in self._list_custom_from_namespaces(
            group="platform.stackrox.io",
            versions=("v1alpha1",),
            plural="securedclusters",
            namespaces=self._namespace_candidates(
                ["stackrox", "rhacs-operator", "redhat-acs-operator"],
                self._all_projects(),
            ),
        ):
            metadata = item.get("metadata") or {}
            status = item.get("status") or {}
            conditions = self._extract_condition_map(status.get("conditions"))
            available = conditions.get("Available")
            if available == "True":
                available_count += 1
            rows.append(
                {
                    "namespace": metadata.get("namespace"),
                    "secured_cluster_name": metadata.get("name"),
                    "cluster_name": (item.get("spec") or {}).get("clusterName") or metadata.get("name"),
                    "available": available,
                    "progressing": conditions.get("Progressing"),
                    "degraded": conditions.get("Degraded"),
                    "central_endpoint": ((item.get("spec") or {}).get("centralApiEndpoint") or (item.get("spec") or {}).get("central", {})).get("endpoint") if isinstance((item.get("spec") or {}).get("central"), dict) else (item.get("spec") or {}).get("centralApiEndpoint"),
                }
            )
        return {"count": len(rows), "available_count": available_count, "secured_clusters": rows}

    def list_security_context_constraints(self) -> dict[str, Any]:
        rows = []
        privileged_count = 0
        for item in self._list_custom(group="security.openshift.io", version="v1", plural="securitycontextconstraints"):
            allow_privileged = bool(item.get("allowPrivilegedContainer"))
            if allow_privileged:
                privileged_count += 1
            rows.append(
                {
                    "name": (item.get("metadata") or {}).get("name"),
                    "priority": item.get("priority"),
                    "allow_privileged_container": allow_privileged,
                    "allow_host_dir_volume_plugin": item.get("allowHostDirVolumePlugin"),
                    "allow_host_network": item.get("allowHostNetwork"),
                    "allow_host_pid": item.get("allowHostPID"),
                    "allow_host_ports": item.get("allowHostPorts"),
                }
            )
        return {"count": len(rows), "privileged_count": privileged_count, "security_context_constraints": rows}

    def list_admission_webhook_configurations(self) -> dict[str, Any]:
        self._ensure_clients()
        assert self._admissionregistration is not None
        rows = []
        fail_open_webhook_count = 0
        missing_ca_bundle_webhook_count = 0
        service_backed_webhook_count = 0

        def _collect(configuration_kind: str, items: list[Any]) -> None:
            nonlocal fail_open_webhook_count, missing_ca_bundle_webhook_count, service_backed_webhook_count
            for configuration in items:
                metadata = getattr(configuration, "metadata", None)
                webhooks = list(getattr(configuration, "webhooks", None) or [])
                config_fail_open = 0
                config_missing_ca = 0
                config_service_backed = 0
                for webhook in webhooks:
                    client_config = getattr(webhook, "client_config", None)
                    service_ref = getattr(client_config, "service", None) if client_config else None
                    failure_policy = getattr(webhook, "failure_policy", None) or "Fail"
                    ca_bundle = getattr(client_config, "ca_bundle", None) if client_config else None
                    if failure_policy == "Ignore":
                        fail_open_webhook_count += 1
                        config_fail_open += 1
                    if service_ref is not None:
                        service_backed_webhook_count += 1
                        config_service_backed += 1
                    if service_ref is not None and not ca_bundle:
                        missing_ca_bundle_webhook_count += 1
                        config_missing_ca += 1
                rows.append(
                    {
                        "configuration_kind": configuration_kind,
                        "configuration_name": getattr(metadata, "name", None),
                        "webhook_count": len(webhooks),
                        "fail_open_webhook_count": config_fail_open,
                        "missing_ca_bundle_webhook_count": config_missing_ca,
                        "service_backed_webhook_count": config_service_backed,
                        "webhook_names": [getattr(webhook, "name", None) for webhook in webhooks],
                    }
                )

        try:
            _collect("MutatingWebhookConfiguration", self._admissionregistration.list_mutating_webhook_configuration().items)
            _collect("ValidatingWebhookConfiguration", self._admissionregistration.list_validating_webhook_configuration().items)
        except ApiException as error:
            if error.status in {403, 404}:
                return {
                    "count": 0,
                    "webhook_count": 0,
                    "fail_open_webhook_count": 0,
                    "missing_ca_bundle_webhook_count": 0,
                    "service_backed_webhook_count": 0,
                    "admission_webhook_configurations": [],
                }
            raise

        return {
            "count": len(rows),
            "webhook_count": sum(row["webhook_count"] for row in rows),
            "fail_open_webhook_count": fail_open_webhook_count,
            "missing_ca_bundle_webhook_count": missing_ca_bundle_webhook_count,
            "service_backed_webhook_count": service_backed_webhook_count,
            "admission_webhook_configurations": rows,
        }

    def list_operator_extension_readiness(self) -> dict[str, Any]:
        operators = self.list_cluster_operators()
        subscriptions = self.list_operator_subscriptions()
        csvs = self.list_cluster_service_versions()
        api_services = self.list_api_service_health()
        webhooks = self.list_admission_webhook_configurations()

        degraded_operator_count = operators.get("degraded_count") or 0
        unhealthy_subscription_count = subscriptions.get("unhealthy_count") or 0
        failed_csv_count = csvs.get("failed_count") or 0
        unavailable_api_service_count = api_services.get("unavailable_count") or 0
        fail_open_webhook_count = webhooks.get("fail_open_webhook_count") or 0
        missing_ca_bundle_webhook_count = webhooks.get("missing_ca_bundle_webhook_count") or 0

        penalties = (
            (int(degraded_operator_count) * 9)
            + (int(unhealthy_subscription_count) * 5)
            + (int(failed_csv_count) * 4)
            + (int(unavailable_api_service_count) * 10)
            + (int(fail_open_webhook_count) * 2)
            + (int(missing_ca_bundle_webhook_count) * 3)
        )
        readiness_score = max(0, min(100, 100 - penalties))

        hotspots: list[str] = []
        if degraded_operator_count:
            hotspots.append(f"{degraded_operator_count} degraded cluster operator(s)")
        if unavailable_api_service_count:
            hotspots.append(f"{unavailable_api_service_count} unavailable aggregated APIService registration(s)")
        if unhealthy_subscription_count:
            hotspots.append(f"{unhealthy_subscription_count} unhealthy operator subscription(s)")
        if failed_csv_count:
            hotspots.append(f"{failed_csv_count} ClusterServiceVersion(s) outside a healthy phase")
        if missing_ca_bundle_webhook_count:
            hotspots.append(f"{missing_ca_bundle_webhook_count} webhook(s) missing a CA bundle")
        if fail_open_webhook_count:
            hotspots.append(f"{fail_open_webhook_count} fail-open admission webhook(s)")

        return {
            "count": 1,
            "readiness_score": readiness_score,
            "degraded_operator_count": degraded_operator_count,
            "unhealthy_subscription_count": unhealthy_subscription_count,
            "failed_csv_count": failed_csv_count,
            "unavailable_api_service_count": unavailable_api_service_count,
            "fail_open_webhook_count": fail_open_webhook_count,
            "missing_ca_bundle_webhook_count": missing_ca_bundle_webhook_count,
            "hotspot_count": len(hotspots),
            "hotspots": hotspots,
            "operator_extension_readiness": [
                {
                    "readiness_score": readiness_score,
                    "degraded_operator_count": degraded_operator_count,
                    "unhealthy_subscription_count": unhealthy_subscription_count,
                    "failed_csv_count": failed_csv_count,
                    "unavailable_api_service_count": unavailable_api_service_count,
                    "fail_open_webhook_count": fail_open_webhook_count,
                    "missing_ca_bundle_webhook_count": missing_ca_bundle_webhook_count,
                    "hotspots": hotspots,
                }
            ],
        }

    def list_rbac_bindings(self, project: str | None = None) -> dict[str, Any]:
        self._ensure_clients()
        assert self._rbac is not None
        cluster_rows = []
        cluster_admin_count = 0
        for binding in self._rbac.list_cluster_role_binding().items:
            role_ref = getattr(binding, "role_ref", None)
            role_name = getattr(role_ref, "name", None)
            if role_name == "cluster-admin":
                cluster_admin_count += 1
            cluster_rows.append(
                {
                    "cluster_role_binding_name": self._metadata_name(binding),
                    "role_ref_kind": getattr(role_ref, "kind", None),
                    "role_ref_name": role_name,
                    "subject_count": len(getattr(binding, "subjects", None) or []),
                }
            )
        namespace_rows = []
        elevated_namespace_binding_count = 0
        for namespace in self._selected_projects(project):
            for binding in self._rbac.list_namespaced_role_binding(namespace).items:
                role_ref = getattr(binding, "role_ref", None)
                role_name = getattr(role_ref, "name", None)
                if role_name in {"admin", "cluster-admin", "edit"}:
                    elevated_namespace_binding_count += 1
                namespace_rows.append(
                    {
                        "project": namespace,
                        "role_binding_name": self._metadata_name(binding),
                        "role_ref_kind": getattr(role_ref, "kind", None),
                        "role_ref_name": role_name,
                        "subject_count": len(getattr(binding, "subjects", None) or []),
                    }
                )
        return {
            "cluster_role_binding_count": len(cluster_rows),
            "namespace_role_binding_count": len(namespace_rows),
            "cluster_admin_binding_count": cluster_admin_count,
            "elevated_namespace_binding_count": elevated_namespace_binding_count,
            "cluster_role_bindings": cluster_rows,
            "role_bindings": namespace_rows,
        }

    def list_service_accounts(self, project: str | None = None) -> dict[str, Any]:
        self._ensure_clients()
        assert self._core is not None
        rows = []
        token_mount_count = 0
        for namespace in self._selected_projects(project):
            for service_account in self._core.list_namespaced_service_account(namespace).items:
                automount = getattr(service_account, "automount_service_account_token", None)
                if automount is True:
                    token_mount_count += 1
                rows.append(
                    {
                        "project": namespace,
                        "service_account_name": self._metadata_name(service_account),
                        "automount_service_account_token": automount,
                        "secret_count": len(getattr(service_account, "secrets", None) or []),
                        "image_pull_secret_count": len(getattr(service_account, "image_pull_secrets", None) or []),
                    }
                )
        return {"count": len(rows), "automount_token_enabled_count": token_mount_count, "service_accounts": rows}

    def list_limit_ranges(self, project: str | None = None) -> dict[str, Any]:
        self._ensure_clients()
        assert self._core is not None
        rows = []
        for namespace in self._selected_projects(project):
            for limit_range in self._core.list_namespaced_limit_range(namespace).items:
                limits = []
                for item in getattr(limit_range, "spec", None).limits or []:
                    limits.append(
                        {
                            "type": getattr(item, "type", None),
                            "default": getattr(item, "default", None) or {},
                            "default_request": getattr(item, "default_request", None) or {},
                            "max": getattr(item, "max", None) or {},
                            "min": getattr(item, "min", None) or {},
                        }
                    )
                rows.append(
                    {
                        "project": namespace,
                        "limit_range_name": self._metadata_name(limit_range),
                        "limit_item_count": len(limits),
                        "limits": limits,
                    }
                )
        return {"count": len(rows), "limit_ranges": rows}

    def list_network_policies(self, project: str | None = None) -> dict[str, Any]:
        self._ensure_clients()
        assert self._networking is not None
        rows = []
        for namespace in self._selected_projects(project):
            for policy in self._networking.list_namespaced_network_policy(namespace).items:
                spec = getattr(policy, "spec", None)
                rows.append(
                    {
                        "project": namespace,
                        "policy_name": self._metadata_name(policy),
                        "policy_types": getattr(spec, "policy_types", None) or [],
                        "ingress_rule_count": len(getattr(spec, "ingress", None) or []),
                        "egress_rule_count": len(getattr(spec, "egress", None) or []),
                    }
                )
        return {"count": len(rows), "network_policies": rows}

    def list_resource_quotas(self, project: str | None = None) -> dict[str, Any]:
        self._ensure_clients()
        assert self._core is not None
        quotas = []
        for namespace in self._selected_projects(project):
            for quota in self._core.list_namespaced_resource_quota(namespace).items:
                hard = getattr(getattr(quota, "status", None), "hard", None) or {}
                used = getattr(getattr(quota, "status", None), "used", None) or {}
                quotas.append(
                    {
                        "project": namespace,
                        "resource_quota_name": self._metadata_name(quota),
                        "hard_pods": hard.get("pods"),
                        "used_pods": used.get("pods"),
                        "hard_cpu": hard.get("limits.cpu") or hard.get("requests.cpu"),
                        "used_cpu": used.get("limits.cpu") or used.get("requests.cpu"),
                        "hard_memory": hard.get("limits.memory") or hard.get("requests.memory"),
                        "used_memory": used.get("limits.memory") or used.get("requests.memory"),
                    }
                )
        cluster_quotas = [
            {"cluster_resource_quota_name": (item.get("metadata") or {}).get("name"), "selector": (item.get("spec") or {}).get("selector") or {}}
            for item in self._list_custom(group="quota.openshift.io", version="v1", plural="clusterresourcequotas")
        ]
        return {"quota_count": len(quotas), "cluster_quota_count": len(cluster_quotas), "resource_quotas": quotas, "cluster_resource_quotas": cluster_quotas}

    def list_image_streams(self, project: str | None = None) -> dict[str, Any]:
        rows = []
        for namespace in self._selected_projects(project):
            for item in self._list_custom(group="image.openshift.io", version="v1", plural="imagestreams", namespace=namespace):
                rows.append(
                    {
                        "project": namespace,
                        "image_stream_name": (item.get("metadata") or {}).get("name"),
                        "public_docker_image_repository": (item.get("status") or {}).get("publicDockerImageRepository"),
                        "tag_count": len((item.get("status") or {}).get("tags") or []),
                        "lookup_policy_local": ((item.get("spec") or {}).get("lookupPolicy") or {}).get("local"),
                    }
                )
        return {"count": len(rows), "image_streams": rows}

    def list_builds(self, project: str | None = None) -> dict[str, Any]:
        rows = []
        failed_count = 0
        for namespace in self._selected_projects(project):
            for item in self._list_custom(group="build.openshift.io", version="v1", plural="builds", namespace=namespace):
                phase = (item.get("status") or {}).get("phase")
                if phase in {"Failed", "Error", "Cancelled"}:
                    failed_count += 1
                rows.append(
                    {
                        "project": namespace,
                        "build_name": (item.get("metadata") or {}).get("name"),
                        "phase": phase,
                        "start_timestamp": (item.get("status") or {}).get("startTimestamp"),
                        "completion_timestamp": (item.get("status") or {}).get("completionTimestamp"),
                        "git_uri": ((item.get("spec") or {}).get("source") or {}).get("git", {}).get("uri"),
                    }
                )
        return {"count": len(rows), "failed_count": failed_count, "builds": rows}

    def list_build_configs(self, project: str | None = None) -> dict[str, Any]:
        rows = []
        trigger_count = 0
        for namespace in self._selected_projects(project):
            for item in self._list_custom(group="build.openshift.io", version="v1", plural="buildconfigs", namespace=namespace):
                spec = item.get("spec") or {}
                triggers = spec.get("triggers") or []
                trigger_count += len(triggers)
                rows.append(
                    {
                        "project": namespace,
                        "build_config_name": (item.get("metadata") or {}).get("name"),
                        "source_type": ((spec.get("source") or {}).get("type")),
                        "strategy_type": next((key for key in (spec.get("strategy") or {}) if key.endswith("Strategy")), None),
                        "output_to_kind": ((spec.get("output") or {}).get("to") or {}).get("kind"),
                        "output_to_name": ((spec.get("output") or {}).get("to") or {}).get("name"),
                        "trigger_count": len(triggers),
                    }
                )
        return {"count": len(rows), "trigger_count": trigger_count, "build_configs": rows}

    def list_deployment_configs(self, project: str | None = None) -> dict[str, Any]:
        rows = []
        degraded_count = 0
        for namespace in self._selected_projects(project):
            for item in self._list_custom(group="apps.openshift.io", version="v1", plural="deploymentconfigs", namespace=namespace):
                spec = item.get("spec") or {}
                status = item.get("status") or {}
                desired = spec.get("replicas") or 0
                available = status.get("availableReplicas") or 0
                if available < desired:
                    degraded_count += 1
                rows.append(
                    {
                        "project": namespace,
                        "deployment_config_name": (item.get("metadata") or {}).get("name"),
                        "strategy_type": ((spec.get("strategy") or {}).get("type")),
                        "desired_replicas": desired,
                        "available_replicas": available,
                        "ready_replicas": status.get("readyReplicas") or 0,
                        "latest_version": status.get("latestVersion"),
                        "trigger_count": len(spec.get("triggers") or []),
                    }
                )
        return {"count": len(rows), "degraded_count": degraded_count, "deployment_configs": rows}

    def list_knative_services(self, project: str | None = None) -> dict[str, Any]:
        rows = []
        not_ready_count = 0
        namespaces = self._selected_projects(project)
        if not project:
            namespaces = self._namespace_candidates(namespaces, self._all_projects())
        for namespace in namespaces:
            for item in self._list_custom_any_version(
                group="serving.knative.dev",
                versions=("v1", "v1beta1"),
                plural="services",
                namespace=namespace,
            ):
                metadata = item.get("metadata") or {}
                spec = item.get("spec") or {}
                status = item.get("status") or {}
                conditions = self._extract_condition_map(status.get("conditions"))
                ready = conditions.get("Ready")
                if ready not in {None, "True"}:
                    not_ready_count += 1
                rows.append(
                    {
                        "project": namespace,
                        "knative_service_name": metadata.get("name"),
                        "url": status.get("url"),
                        "latest_created_revision_name": status.get("latestCreatedRevisionName"),
                        "latest_ready_revision_name": status.get("latestReadyRevisionName"),
                        "container_count": len(((spec.get("template") or {}).get("spec") or {}).get("containers") or []),
                        "ready": ready,
                    }
                )
        return {"count": len(rows), "not_ready_count": not_ready_count, "knative_services": rows}

    def list_gitops_argocds(self) -> dict[str, Any]:
        rows = []
        available_count = 0
        namespaces = self._namespace_candidates(
            ["openshift-gitops", "openshift-gitops-operator"],
            self._all_projects(),
        )
        for item in self._list_custom_from_namespaces(
            group="argoproj.io",
            versions=("v1beta1", "v1alpha1"),
            plural="argocds",
            namespaces=namespaces,
        ):
            metadata = item.get("metadata") or {}
            spec = item.get("spec") or {}
            status = item.get("status") or {}
            conditions = self._extract_condition_map(status.get("conditions"))
            available = conditions.get("Available") or conditions.get("Reconciled")
            if available == "True":
                available_count += 1
            managed_namespaces = spec.get("sourceNamespaces") or spec.get("applicationSet", {}).get("sourceNamespaces") or []
            rows.append(
                {
                    "namespace": metadata.get("namespace"),
                    "argocd_name": metadata.get("name"),
                    "server_route_enabled": ((spec.get("server") or {}).get("route") or {}).get("enabled"),
                    "server_autoscale_enabled": ((spec.get("server") or {}).get("autoscale") or {}).get("enabled"),
                    "ha_enabled": spec.get("ha", {}).get("enabled") if isinstance(spec.get("ha"), dict) else spec.get("ha"),
                    "controller_processors": ((spec.get("controller") or {}).get("processors") or {}).get("operation") if isinstance((spec.get("controller") or {}).get("processors"), dict) else None,
                    "application_instance_label_key": spec.get("applicationInstanceLabelKey"),
                    "managed_namespace_count": len(managed_namespaces),
                    "managed_namespaces": managed_namespaces,
                    "available": available,
                    "phase": status.get("phase"),
                }
            )
        return {"count": len(rows), "available_count": available_count, "gitops_argocds": rows}

    def list_gitops_applications(self) -> dict[str, Any]:
        rows = []
        unhealthy_count = 0
        for item in self._list_custom_from_namespaces(
            group="argoproj.io",
            versions=("v1alpha1",),
            plural="applications",
            namespaces=self._namespace_candidates(["openshift-gitops"], self._all_projects()),
        ):
            metadata = item.get("metadata") or {}
            spec = item.get("spec") or {}
            status = item.get("status") or {}
            sync_status = ((status.get("sync") or {}).get("status"))
            health_status = ((status.get("health") or {}).get("status"))
            if sync_status not in {None, "Synced"} or health_status not in {None, "Healthy"}:
                unhealthy_count += 1
            destination = spec.get("destination") or {}
            rows.append(
                {
                    "namespace": metadata.get("namespace"),
                    "application_name": metadata.get("name"),
                    "project": spec.get("project"),
                    "destination_namespace": destination.get("namespace"),
                    "destination_server": destination.get("server"),
                    "repo_url": (spec.get("source") or {}).get("repoURL"),
                    "path": (spec.get("source") or {}).get("path"),
                    "target_revision": (spec.get("source") or {}).get("targetRevision"),
                    "sync_status": sync_status,
                    "health_status": health_status,
                }
            )
        return {"count": len(rows), "unhealthy_count": unhealthy_count, "gitops_applications": rows}

    def list_tekton_configs(self) -> dict[str, Any]:
        config_rows = []
        pipeline_as_code_rows = []
        namespaces = self._namespace_candidates(["openshift-pipelines", "openshift-operators"], self._all_projects())
        for item in self._list_custom_any_version(
            group="operator.tekton.dev",
            versions=("v1alpha1", "v1beta1", "v1"),
            plural="tektonconfigs",
        ):
            metadata = item.get("metadata") or {}
            spec = item.get("spec") or {}
            status = item.get("status") or {}
            conditions = self._extract_condition_map(status.get("conditions"))
            config_rows.append(
                {
                    "tekton_config_name": metadata.get("name"),
                    "profile": spec.get("profile"),
                    "target_namespace": spec.get("targetNamespace"),
                    "pipeline_enable_api_fields": ((spec.get("pipeline") or {}).get("enable-api-fields")) or ((spec.get("pipeline") or {}).get("enableApiFields")),
                    "pipeline_as_code_enabled": ((spec.get("pipeline") or {}).get("enable-pipelines-as-code")) or ((spec.get("pipeline") or {}).get("enablePipelinesAsCode")),
                    "pruner_enabled": ((spec.get("pruner") or {}).get("disabled")) is False if spec.get("pruner") is not None else None,
                    "ready": conditions.get("Ready") or conditions.get("Succeeded"),
                    "version": status.get("version"),
                }
            )
        for item in self._list_custom_from_namespaces(
            group="operator.tekton.dev",
            versions=("v1alpha1",),
            plural="tektonpipelines",
            namespaces=namespaces,
        ):
            metadata = item.get("metadata") or {}
            status = item.get("status") or {}
            conditions = self._extract_condition_map(status.get("conditions"))
            pipeline_as_code_rows.append(
                {
                    "namespace": metadata.get("namespace"),
                    "tekton_pipeline_name": metadata.get("name"),
                    "ready": conditions.get("Ready") or conditions.get("Succeeded"),
                    "version": status.get("version"),
                }
            )
        return {
            "config_count": len(config_rows),
            "pipeline_install_count": len(pipeline_as_code_rows),
            "tekton_configs": config_rows,
            "tekton_pipelines": pipeline_as_code_rows,
        }

    def list_tekton_pipeline_runs(self, project: str | None = None) -> dict[str, Any]:
        rows = []
        failed_count = 0
        namespaces = self._selected_projects(project)
        if not project:
            namespaces = self._namespace_candidates(namespaces, ["openshift-pipelines"])
        for namespace in namespaces:
            for item in self._list_custom_any_version(
                group="tekton.dev",
                versions=("v1", "v1beta1"),
                plural="pipelineruns",
                namespace=namespace,
            ):
                metadata = item.get("metadata") or {}
                spec = item.get("spec") or {}
                status = item.get("status") or {}
                conditions = status.get("conditions") or []
                succeeded_condition = next((condition for condition in conditions if condition.get("type") == "Succeeded"), {})
                succeeded = succeeded_condition.get("status")
                if succeeded == "False":
                    failed_count += 1
                rows.append(
                    {
                        "project": namespace,
                        "pipeline_run_name": metadata.get("name"),
                        "pipeline_name": ((spec.get("pipelineRef") or {}).get("name")) or ((status.get("pipelineSpec") or {}).get("metadata") or {}).get("name"),
                        "service_account": spec.get("taskRunTemplate", {}).get("serviceAccountName") or spec.get("serviceAccountName"),
                        "status": succeeded,
                        "reason": succeeded_condition.get("reason"),
                        "start_time": status.get("startTime"),
                        "completion_time": status.get("completionTime"),
                    }
                )
        return {"count": len(rows), "failed_count": failed_count, "tekton_pipeline_runs": rows}

    def list_cluster_logging(self) -> dict[str, Any]:
        cluster_logging_rows = []
        log_forwarder_rows = []
        unavailable_count = 0
        namespaces = self._namespace_candidates(["openshift-logging"], self._all_projects())
        for item in self._list_custom_from_namespaces(
            group="logging.openshift.io",
            versions=("v1",),
            plural="clusterloggings",
            namespaces=namespaces,
        ):
            metadata = item.get("metadata") or {}
            spec = item.get("spec") or {}
            status = item.get("status") or {}
            conditions = self._extract_condition_map(status.get("conditions"))
            ready = conditions.get("Ready") or conditions.get("Available")
            if ready not in {None, "True"}:
                unavailable_count += 1
            cluster_logging_rows.append(
                {
                    "namespace": metadata.get("namespace"),
                    "cluster_logging_name": metadata.get("name"),
                    "management_state": spec.get("managementState"),
                    "log_store_type": ((spec.get("logStore") or {}).get("type")),
                    "visualization_type": ((spec.get("visualization") or {}).get("type")),
                    "collection_type": ((spec.get("collection") or {}).get("type")),
                    "ready": ready,
                }
            )
        for item in self._list_custom_from_namespaces(
            group="logging.openshift.io",
            versions=("v1",),
            plural="clusterlogforwarders",
            namespaces=namespaces,
        ):
            metadata = item.get("metadata") or {}
            spec = item.get("spec") or {}
            status = item.get("status") or {}
            outputs = spec.get("outputs") or []
            log_forwarder_rows.append(
                {
                    "namespace": metadata.get("namespace"),
                    "cluster_log_forwarder_name": metadata.get("name"),
                    "input_count": len(spec.get("inputs") or []),
                    "pipeline_count": len(spec.get("pipelines") or []),
                    "output_types": sorted({output.get("type") for output in outputs if output.get("type")}),
                    "ready": self._extract_condition_map(status.get("conditions")).get("Ready"),
                }
            )
        return {
            "cluster_logging_count": len(cluster_logging_rows),
            "cluster_log_forwarder_count": len(log_forwarder_rows),
            "unavailable_count": unavailable_count,
            "cluster_loggings": cluster_logging_rows,
            "cluster_log_forwarders": log_forwarder_rows,
        }

    def list_oadp_resources(self) -> dict[str, Any]:
        application_rows = []
        backup_location_rows = []
        schedule_rows = []
        namespaces = self._namespace_candidates(["openshift-adp", "oadp-operator"], self._all_projects())
        for item in self._list_custom_from_namespaces(
            group="oadp.openshift.io",
            versions=("v1alpha1",),
            plural="dataprotectionapplications",
            namespaces=namespaces,
        ):
            metadata = item.get("metadata") or {}
            spec = item.get("spec") or {}
            status = item.get("status") or {}
            conditions = self._extract_condition_map(status.get("conditions"))
            application_rows.append(
                {
                    "namespace": metadata.get("namespace"),
                    "data_protection_application_name": metadata.get("name"),
                    "backup_image": ((spec.get("backupLocations") or [{}])[0] or {}).get("velero") if isinstance(spec.get("backupLocations"), list) else None,
                    "snapshot_location_count": len(spec.get("snapshotLocations") or []),
                    "backup_location_count": len(spec.get("backupLocations") or []),
                    "reconciled": conditions.get("Reconciled") or conditions.get("Ready"),
                }
            )
        for namespace in namespaces:
            for item in self._list_custom_any_version(
                group="velero.io",
                versions=("v1",),
                plural="backupstoragelocations",
                namespace=namespace,
            ):
                metadata = item.get("metadata") or {}
                spec = item.get("spec") or {}
                backup_location_rows.append(
                    {
                        "namespace": metadata.get("namespace"),
                        "backup_storage_location_name": metadata.get("name"),
                        "provider": spec.get("provider"),
                        "bucket": (spec.get("objectStorage") or {}).get("bucket"),
                        "default": spec.get("default"),
                        "access_mode": spec.get("accessMode"),
                    }
                )
            for item in self._list_custom_any_version(
                group="velero.io",
                versions=("v1",),
                plural="schedules",
                namespace=namespace,
            ):
                metadata = item.get("metadata") or {}
                spec = item.get("spec") or {}
                schedule_rows.append(
                    {
                        "namespace": metadata.get("namespace"),
                        "schedule_name": metadata.get("name"),
                        "schedule": spec.get("schedule"),
                        "paused": spec.get("paused"),
                        "ttl": ((spec.get("template") or {}).get("ttl")),
                    }
                )
        return {
            "application_count": len(application_rows),
            "backup_storage_location_count": len(backup_location_rows),
            "schedule_count": len(schedule_rows),
            "data_protection_applications": application_rows,
            "backup_storage_locations": backup_location_rows,
            "backup_schedules": schedule_rows,
        }

    def list_virtualization_resources(self, project: str | None = None) -> dict[str, Any]:
        control_plane_namespaces = self._namespace_candidates(["openshift-cnv", "openshift-cnv-operator"], self._all_projects())
        workload_namespaces = self._selected_projects(project)
        if not project:
            workload_namespaces = self._namespace_candidates(
                workload_namespaces,
                ["openshift-cnv", "openshift-virtualization-os-images"],
            )

        kubevirt_rows = []
        kubevirt_available_count = 0
        for item in self._list_custom_from_namespaces(
            group="kubevirt.io",
            versions=("v1", "v1alpha3"),
            plural="kubevirts",
            namespaces=control_plane_namespaces,
        ):
            metadata = item.get("metadata") or {}
            status = item.get("status") or {}
            conditions = self._extract_condition_map(status.get("conditions"))
            available = conditions.get("Available") or conditions.get("Progressing")
            if conditions.get("Available") == "True":
                kubevirt_available_count += 1
            kubevirt_rows.append(
                {
                    "namespace": metadata.get("namespace"),
                    "kubevirt_name": metadata.get("name"),
                    "phase": status.get("phase"),
                    "observed_version": status.get("observedKubeVirtVersion") or status.get("observedDeploymentConfigVersion"),
                    "target_version": status.get("targetKubeVirtVersion") or status.get("targetDeploymentConfigVersion"),
                    "available": available,
                    "conditions": conditions,
                }
            )

        hyperconverged_rows = []
        hyperconverged_available_count = 0
        for item in self._list_custom_from_namespaces(
            group="hco.kubevirt.io",
            versions=("v1beta1", "v1alpha1"),
            plural="hyperconvergeds",
            namespaces=control_plane_namespaces,
        ):
            metadata = item.get("metadata") or {}
            status = item.get("status") or {}
            conditions = self._extract_condition_map(status.get("conditions"))
            available = conditions.get("Available") or conditions.get("ReconcileCompleted")
            if conditions.get("Available") == "True" or conditions.get("ReconcileCompleted") == "True":
                hyperconverged_available_count += 1
            hyperconverged_rows.append(
                {
                    "namespace": metadata.get("namespace"),
                    "hyperconverged_name": metadata.get("name"),
                    "version": status.get("versions", {}).get("operator") if isinstance(status.get("versions"), dict) else None,
                    "available": available,
                    "conditions": conditions,
                    "live_migration_config": ((item.get("spec") or {}).get("liveMigrationConfig")) or {},
                }
            )

        vm_rows = []
        running_vm_count = 0
        for namespace in workload_namespaces:
            for item in self._list_custom_any_version(
                group="kubevirt.io",
                versions=("v1", "v1alpha3"),
                plural="virtualmachines",
                namespace=namespace,
            ):
                metadata = item.get("metadata") or {}
                spec = item.get("spec") or {}
                status = item.get("status") or {}
                printable_status = status.get("printableStatus") or status.get("status")
                if printable_status == "Running":
                    running_vm_count += 1
                vm_rows.append(
                    {
                        "project": namespace,
                        "virtual_machine_name": metadata.get("name"),
                        "run_strategy": spec.get("runStrategy"),
                        "running": spec.get("running"),
                        "printable_status": printable_status,
                        "ready": status.get("ready"),
                    }
                )

        datavolume_rows = []
        failed_datavolume_count = 0
        for namespace in workload_namespaces:
            for item in self._list_custom_any_version(
                group="cdi.kubevirt.io",
                versions=("v1beta1", "v1alpha1"),
                plural="datavolumes",
                namespace=namespace,
            ):
                metadata = item.get("metadata") or {}
                status = item.get("status") or {}
                phase = status.get("phase")
                if phase in {"Failed", "Unknown"}:
                    failed_datavolume_count += 1
                datavolume_rows.append(
                    {
                        "project": namespace,
                        "data_volume_name": metadata.get("name"),
                        "phase": phase,
                        "progress": status.get("progress"),
                        "storage": ((item.get("spec") or {}).get("storage") or {}).get("resources", {}).get("requests", {}).get("storage"),
                    }
                )

        migration_rows = []
        failed_migration_count = 0
        for namespace in workload_namespaces:
            for item in self._list_custom_any_version(
                group="kubevirt.io",
                versions=("v1", "v1alpha3"),
                plural="virtualmachineinstancemigrations",
                namespace=namespace,
            ):
                metadata = item.get("metadata") or {}
                status = item.get("status") or {}
                phase = status.get("phase")
                if phase in {"Failed", "Unknown"}:
                    failed_migration_count += 1
                migration_rows.append(
                    {
                        "project": namespace,
                        "migration_name": metadata.get("name"),
                        "phase": phase,
                        "vm_instance_name": ((item.get("spec") or {}).get("vmiName")),
                        "creation_timestamp": metadata.get("creationTimestamp"),
                    }
                )

        return {
            "kubevirt_count": len(kubevirt_rows),
            "kubevirt_available_count": kubevirt_available_count,
            "hyperconverged_count": len(hyperconverged_rows),
            "hyperconverged_available_count": hyperconverged_available_count,
            "virtual_machine_count": len(vm_rows),
            "running_virtual_machine_count": running_vm_count,
            "data_volume_count": len(datavolume_rows),
            "failed_data_volume_count": failed_datavolume_count,
            "migration_count": len(migration_rows),
            "failed_migration_count": failed_migration_count,
            "kubevirts": kubevirt_rows,
            "hyperconvergeds": hyperconverged_rows,
            "virtual_machines": vm_rows,
            "data_volumes": datavolume_rows,
            "live_migrations": migration_rows,
        }

    def list_virtual_machine_snapshots(self, project: str | None = None) -> dict[str, Any]:
        rows = []
        ready_count = 0
        namespaces = self._selected_projects(project)
        if not project:
            namespaces = self._namespace_candidates(namespaces, ["openshift-cnv"])
        for namespace in namespaces:
            for item in self._list_custom_any_version(
                group="snapshot.kubevirt.io",
                versions=("v1beta1", "v1alpha1"),
                plural="virtualmachinesnapshots",
                namespace=namespace,
            ):
                metadata = item.get("metadata") or {}
                spec = item.get("spec") or {}
                status = item.get("status") or {}
                if status.get("readyToUse") is True:
                    ready_count += 1
                rows.append(
                    {
                        "project": namespace,
                        "virtual_machine_snapshot_name": metadata.get("name"),
                        "source_virtual_machine_name": ((spec.get("source") or {}).get("name")),
                        "ready_to_use": status.get("readyToUse"),
                        "creation_time": status.get("creationTime"),
                        "error": status.get("error") or {},
                    }
                )
        return {"count": len(rows), "ready_count": ready_count, "virtual_machine_snapshots": rows}

    def list_migration_toolkit_resources(self, project: str | None = None) -> dict[str, Any]:
        namespaces = self._namespace_candidates(
            self._selected_projects(project),
            ["openshift-migration"],
        )
        migcluster_rows = []
        migstorage_rows = []
        migplan_rows = []
        migration_rows = []
        active_migration_count = 0
        for namespace in namespaces:
            for item in self._list_custom_any_version(
                group="migration.openshift.io",
                versions=("v1alpha1",),
                plural="migclusters",
                namespace=namespace,
            ):
                migcluster_rows.append(
                    {
                        "project": namespace,
                        "mig_cluster_name": (item.get("metadata") or {}).get("name"),
                        "is_host_cluster": (item.get("spec") or {}).get("isHostCluster"),
                        "ready": ((item.get("status") or {}).get("conditions") or []),
                    }
                )
            for item in self._list_custom_any_version(
                group="migration.openshift.io",
                versions=("v1alpha1",),
                plural="migstorages",
                namespace=namespace,
            ):
                backup_storage_config = (item.get("spec") or {}).get("backupStorageConfig") or {}
                migstorage_rows.append(
                    {
                        "project": namespace,
                        "mig_storage_name": (item.get("metadata") or {}).get("name"),
                        "backup_storage_provider": backup_storage_config.get("provider") or backup_storage_config.get("awsBucketName") or backup_storage_config.get("gcpBucket") or backup_storage_config.get("azureResourceGroup"),
                    }
                )
            for item in self._list_custom_any_version(
                group="migration.openshift.io",
                versions=("v1alpha1",),
                plural="migplans",
                namespace=namespace,
            ):
                migplan_rows.append(
                    {
                        "project": namespace,
                        "mig_plan_name": (item.get("metadata") or {}).get("name"),
                        "source_cluster": ((item.get("spec") or {}).get("srcMigClusterRef") or {}).get("name"),
                        "destination_cluster": ((item.get("spec") or {}).get("destMigClusterRef") or {}).get("name"),
                        "migration_stage_count": len(((item.get("spec") or {}).get("stages") or [])),
                        "include_pvs": ((item.get("spec") or {}).get("indirectImageMigration")),
                    }
                )
            for item in self._list_custom_any_version(
                group="migration.openshift.io",
                versions=("v1alpha1",),
                plural="migmigrations",
                namespace=namespace,
            ):
                status = item.get("status") or {}
                phase = status.get("phase") or status.get("conditions")
                if isinstance(phase, str) and phase.lower() in {"running", "executing", "started"}:
                    active_migration_count += 1
                migration_rows.append(
                    {
                        "project": namespace,
                        "mig_migration_name": (item.get("metadata") or {}).get("name"),
                        "mig_plan_name": ((item.get("spec") or {}).get("migPlanRef") or {}).get("name"),
                        "phase": phase,
                        "stage": status.get("stage"),
                    }
                )
        return {
            "mig_cluster_count": len(migcluster_rows),
            "mig_storage_count": len(migstorage_rows),
            "mig_plan_count": len(migplan_rows),
            "mig_migration_count": len(migration_rows),
            "active_migration_count": active_migration_count,
            "mig_clusters": migcluster_rows,
            "mig_storages": migstorage_rows,
            "mig_plans": migplan_rows,
            "mig_migrations": migration_rows,
        }

    def list_disaster_recovery_resources(self, project: str | None = None) -> dict[str, Any]:
        base_namespaces = self._namespace_candidates(
            self._selected_projects(project),
            ["openshift-dr-system", "open-cluster-management-backup", "openshift-adp"],
        )
        cluster_namespaces = self._namespace_candidates(base_namespaces, self._all_projects())

        dr_policy_rows = []
        for item in self._list_custom_from_namespaces(
            group="ramendr.openshift.io",
            versions=("v1alpha1", "v1alpha2"),
            plural="drpolicies",
            namespaces=cluster_namespaces,
        ):
            metadata = item.get("metadata") or {}
            spec = item.get("spec") or {}
            dr_policy_rows.append(
                {
                    "namespace": metadata.get("namespace"),
                    "dr_policy_name": metadata.get("name"),
                    "scheduling_interval": spec.get("schedulingInterval"),
                    "dr_cluster_count": len(spec.get("drClusters") or []),
                    "dr_clusters": spec.get("drClusters") or [],
                }
            )

        drpc_rows = []
        failover_count = 0
        for item in self._list_custom_from_namespaces(
            group="ramendr.openshift.io",
            versions=("v1alpha1", "v1alpha2"),
            plural="drplacementcontrols",
            namespaces=cluster_namespaces,
        ):
            metadata = item.get("metadata") or {}
            spec = item.get("spec") or {}
            status = item.get("status") or {}
            action = spec.get("action") or status.get("action")
            if action in {"Failover", "Relocate"}:
                failover_count += 1
            drpc_rows.append(
                {
                    "namespace": metadata.get("namespace"),
                    "dr_placement_control_name": metadata.get("name"),
                    "preferred_cluster": spec.get("preferredCluster"),
                    "dr_policy_ref": spec.get("drPolicyRef", {}).get("name") if isinstance(spec.get("drPolicyRef"), dict) else spec.get("drPolicyRef"),
                    "action": action,
                    "phase": status.get("phase"),
                    "conditions": self._extract_condition_map(status.get("conditions")),
                }
            )

        volume_replication_class_rows = []
        for item in self._list_custom_any_version(
            group="replication.storage.openshift.io",
            versions=("v1alpha1", "v1beta1"),
            plural="volumereplicationclasses",
        ):
            metadata = item.get("metadata") or {}
            spec = item.get("spec") or {}
            volume_replication_class_rows.append(
                {
                    "volume_replication_class_name": metadata.get("name"),
                    "provisioner": spec.get("provisioner"),
                    "parameters": spec.get("parameters") or {},
                }
            )

        volume_replication_rows = []
        degraded_replication_count = 0
        for namespace in cluster_namespaces:
            for item in self._list_custom_any_version(
                group="replication.storage.openshift.io",
                versions=("v1alpha1", "v1beta1"),
                plural="volumereplications",
                namespace=namespace,
            ):
                metadata = item.get("metadata") or {}
                spec = item.get("spec") or {}
                status = item.get("status") or {}
                state = status.get("state") or status.get("lastSyncTime")
                if isinstance(state, str) and state.lower() in {"failed", "error"}:
                    degraded_replication_count += 1
                volume_replication_rows.append(
                    {
                        "namespace": metadata.get("namespace"),
                        "volume_replication_name": metadata.get("name"),
                        "data_source": spec.get("dataSource", {}).get("name") if isinstance(spec.get("dataSource"), dict) else None,
                        "replication_state": spec.get("replicationState"),
                        "status_state": status.get("state"),
                        "last_sync_time": status.get("lastSyncTime"),
                    }
                )

        return {
            "dr_policy_count": len(dr_policy_rows),
            "dr_placement_control_count": len(drpc_rows),
            "active_failover_action_count": failover_count,
            "volume_replication_class_count": len(volume_replication_class_rows),
            "volume_replication_count": len(volume_replication_rows),
            "degraded_replication_count": degraded_replication_count,
            "dr_policies": dr_policy_rows,
            "dr_placement_controls": drpc_rows,
            "volume_replication_classes": volume_replication_class_rows,
            "volume_replications": volume_replication_rows,
        }

    def list_oauth_configuration(self) -> dict[str, Any]:
        items = self._list_custom(group="config.openshift.io", version="v1", plural="oauths")
        item = next((entry for entry in items if (entry.get("metadata") or {}).get("name") == "cluster"), None)
        if item is None:
            return {"count": 0, "oauth_configurations": []}
        spec = item.get("spec") or {}
        identity_providers = spec.get("identityProviders") or []
        ldap_count = 0
        rows = []
        for provider in identity_providers:
            provider_type = provider.get("type")
            if provider_type == "LDAP":
                ldap_count += 1
            rows.append(
                {
                    "name": provider.get("name"),
                    "type": provider_type,
                    "mapping_method": provider.get("mappingMethod"),
                    "ldap_url": ((provider.get("ldap") or {}).get("url")) if provider_type == "LDAP" else None,
                    "challenge": provider.get("challenge"),
                    "login": provider.get("login"),
                }
            )
        return {
            "count": 1,
            "ldap_provider_count": ldap_count,
            "oauth_configurations": [
                {
                    "identity_provider_count": len(rows),
                    "templates_configured": list((spec.get("templates") or {}).keys()) if isinstance(spec.get("templates"), dict) else [],
                    "token_config": spec.get("tokenConfig") or {},
                    "identity_providers": rows,
                }
            ],
        }

    def run_read_only_oc_cli(self, command: str) -> dict[str, Any]:
        if not command or not command.strip():
            raise ValueError("The oc command cannot be empty.")
        parts = shlex.split(command)
        if not parts or parts[0] != "oc":
            raise ValueError("Only oc commands are allowed, and they must begin with 'oc'.")
        lowered = {part.lower() for part in parts[1:]}
        if lowered & self._DENIED_OC_TOKENS:
            raise ValueError("The requested oc command is not read-only and has been blocked.")
        verb = parts[1].lower() if len(parts) > 1 else ""
        if verb not in self._READ_ONLY_OC_VERBS:
            raise ValueError("Only read-only oc verbs such as get, describe, logs, whoami, and version are allowed.")
        if verb == "adm" and any(token in lowered for token in {"upgrade", "drain", "cordon", "uncordon", "taint"}):
            raise ValueError("Mutating oc adm subcommands are blocked.")

        completed = subprocess.run(
            [self._settings.oc_cli_path, *parts[1:]],
            check=True,
            capture_output=True,
            text=True,
        )
        return {
            "command": command,
            "stdout": completed.stdout.strip(),
            "stderr": completed.stderr.strip(),
            "return_code": completed.returncode,
        }
