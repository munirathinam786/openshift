from __future__ import annotations

import hashlib
import json
import logging
import shlex
import subprocess
import time as _time
from dataclasses import dataclass
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
        self._batch: client.BatchV1Api | None = None
        self._networking: client.NetworkingV1Api | None = None
        self._storage: client.StorageV1Api | None = None
        self._custom: client.CustomObjectsApi | None = None
        self.tools: dict[str, ToolSpec] = {
            "get_cluster_identity": ToolSpec(
                "get_cluster_identity",
                "Return the active OpenShift cluster identity, API endpoint, and default project context.",
                {},
                self.get_cluster_identity,
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
            "list_security_context_constraints": ToolSpec(
                "list_security_context_constraints",
                "List security context constraints and summarize privilege and host access posture.",
                {},
                self.list_security_context_constraints,
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
        self._batch = client.BatchV1Api()
        self._networking = client.NetworkingV1Api()
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

    def get_cluster_identity(self) -> dict[str, Any]:
        self._ensure_clients()
        configuration = client.Configuration.get_default_copy()
        return {
            "cluster": self._settings.openshift_cluster,
            "api_url": configuration.host,
            "kube_context": self._current_context_name,
            "default_project": self._settings.openshift_namespace,
            "project_sweep_scope": self._selected_projects(),
            "verify_ssl": self._settings.openshift_verify_ssl,
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
