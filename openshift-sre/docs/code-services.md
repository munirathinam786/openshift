# Service & API Files

This page covers the platform service toolkit, HTTP API, and CLI entry points.

It now also covers the historical persistence layer that stores prompt runs and extracted metrics for the browser dashboard.

## `src/openshift_sre_agent/persistence.py`

This module turns ephemeral tool output into a historical telemetry store.

The main responsibilities are:

- define relational tables for runs, steps, and metric snapshots
- initialize the SQLAlchemy engine against a MySQL-compatible database such as MariaDB
- flatten tool payloads into trend-friendly numeric series
- provide a compact overview payload for the browser dashboard
- derive duration percentile bands from persisted run latency
- build this-week-vs-last-week comparison summaries from real stored runs
- produce executive exception rollups that summarize failures, latency spread, and hotspot cohorts

The extractor intentionally stores:

- generic `count` metrics
- severity and compliance bucket counts
- money fields such as `total_unblended_cost`, `forecast_total`, and `estimated_total_monthly_savings`
- per-row numeric metrics for service cost, tag cost, recommendations, and other structured result sets

The persistence layer now also stores FinOps queue items and their execution-planning state, which lets the browser queue survive refreshes and container restarts.

### HTTP entry-point sketch for `src/openshift_sre_agent/api.py`

This module is the FastAPI entry point.

### Main responsibilities

- build the shared `FastAPI` app instance
- mount the generated MkDocs site under `/guide`
- define request/response models for `/chat` and the FinOps queue endpoints
- parse dashboard query filters
- translate persistence and validation errors into HTTP status codes

### Important endpoint groups

- health and root routing: `/`, `/health`
- main agent execution: `/chat`
- historical analytics: `/history/overview`, `/history/runs/{run_id}`, `/history/tools/{tool_name}`, `/history/metrics/{metric_key}`
- persisted FinOps workflow: `/finops/queue`, `/finops/queue/{item_id}`

The historical overview payload now includes:

- selected-window latency percentiles (`p50`, `p90`, `p95`, `p99`)
- a built-in `this_week_vs_last_week` comparison block
- an executive exception rollup for story-first operator reviews

For concrete request and response examples, see [`API reference`](api-reference.md).

## `src/openshift_sre_agent/tools.py`

This is the largest file in the project because it contains the actual OpenShift and fleet inspection capabilities. Each tool is explicitly registered, discoverable by the model through the tool manifest, and executed through guarded Kubernetes clients or the restricted `oc` CLI fallback.

The live toolkit is now aligned to the repository's OpenShift estate rather than the older AWS-era inventory. In addition to core OpenShift cluster, workload, network, storage, Machine API, OLM, SCC, and quota inspection, the toolkit also surfaces:

- cluster identity, active context, project inventory, node-pressure conditions, and recent event posture for first-pass operational triage
- cluster infrastructure and platform-pattern detection for estates such as `ROSA`, `ARO`, and `IBM Z`
- ACM fleet objects such as `MultiClusterHub`, `ManagedCluster`, and governance `Policy`
- ACS objects such as `CentralService` and `SecuredCluster`
- OpenShift Virtualization / CNV objects such as `KubeVirt`, `HyperConverged`, `VirtualMachine`, `DataVolume`, and live migration resources
- ACM / ODF disaster-recovery objects such as `DRPolicy`, `DRPlacementControl`, and `VolumeReplication`
- OpenShift supply-chain and day-2 delivery objects such as `ImageStream`, `Build`, `Argo CD`, `Tekton`, `ClusterLogging`, and `OADP`
- guarded read-only `oc` support for edge-case diagnostics that are not worth hardcoding as dedicated tools

That means the SRE runtime can now reason about a single cluster, a managed multi-cluster fleet, or a platform-pattern comparison lane without pretending everything is just one generic OpenShift cluster.

### Toolkit architecture

The key moving parts are:

- `ToolSpec` for the manifest entries sent to the model
- `OpenShiftSreToolkit.tool_manifest()` to expose available tools and argument shapes
- `OpenShiftSreToolkit.invoke(...)` to dispatch a named tool call
- guarded Kubernetes API helpers and custom-resource discovery helpers
- the read-only `run_read_only_oc_cli(...)` escape hatch for safe diagnostics

### Service groupings in the live toolkit

- cluster identity and platform pattern: cluster identity, cluster infrastructure, cluster version, cluster operators
- project and node triage: projects, nodes, node pressure, pods, and recent warning events
- fleet governance: ACM MultiClusterHub, ManagedCluster, and Policy resources
- security and compliance: ACS CentralService, ACS SecuredCluster, SCCs, network policies, resource quotas
- workload and application posture: projects, pods, workload rollout health, services, routes, ingresses, events
- storage and supply chain: persistent storage, storage classes, image streams, builds
- platform lifecycle: machine config pools, machine sets, operator subscriptions, ClusterServiceVersions
- platform resiliency and migration: OADP backup posture, OpenShift Virtualization / CNV resources, and ACM / ODF disaster-recovery resources
- operator-safe diagnostics: guarded read-only `oc` CLI execution

The `Platform Console` now exposes much more of that live toolkit directly through its grouped `Selected platform checks` catalog, so the browser workspace can compose reviews from the same OpenShift inspection surface documented here instead of relying on a smaller hand-picked subset.

For a source-level inventory of the individual tool functions, see [`Function Reference`](function-reference.md).

````python
class OpenShiftSreToolkit:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self.tools: dict[str, ToolSpec] = {
            "get_cluster_identity": ToolSpec(...),
            "list_cluster_infrastructure": ToolSpec(...),
            "list_cluster_version": ToolSpec(...),
            "list_cluster_operators": ToolSpec(...),
            "list_nodes": ToolSpec(...),
            "list_workload_health": ToolSpec(...),
            "list_routes": ToolSpec(...),
            "list_persistent_storage": ToolSpec(...),
            "list_machine_sets": ToolSpec(...),
            "list_operator_subscriptions": ToolSpec(...),
            "list_acm_multicluster_hubs": ToolSpec(...),
            "list_acm_managed_clusters": ToolSpec(...),
            "list_acm_policies": ToolSpec(...),
            "list_acs_central_services": ToolSpec(...),
            "list_acs_secured_clusters": ToolSpec(...),
            "list_virtualization_resources": ToolSpec(...),
            "list_disaster_recovery_resources": ToolSpec(...),
            "run_read_only_oc_cli": ToolSpec(...),
        }

    def tool_manifest(self) -> list[dict[str, Any]]:
        return [
            {
                "name": tool.name,
                "description": tool.description,
                "arguments": tool.arguments,
            }
            for tool in self.tools.values()
        ]

    def invoke(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        tool = self.tools.get(name)
        if tool is None:
            raise KeyError(f"Unknown tool: {name}")
        return tool.handler(**arguments)
````

## `src/openshift_sre_agent/api.py`

This file exposes the agent over HTTP, mounts the generated MkDocs site, and lets callers provide per-request runtime overrides.

It now also persists completed runs into the historical store and serves `GET /history/overview` so the dashboard can render stored summaries, trend charts, and recent runs.

````python
from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .agent import OpenShiftSreAgent
from .config import Settings


def _resolve_site_dir() -> Path | None:
    candidates = [
        Path.cwd() / "site",
        Path(__file__).resolve().parents[2] / "site",
        Path(__file__).resolve().parents[1] / "site",
    ]
    for candidate in candidates:
        if candidate.exists() and candidate.is_dir():
            return candidate
    return None


SITE_DIR = _resolve_site_dir()

app = FastAPI(
    title="OpenShift SRE Local Agent",
    version="0.1.0",
    description="Local-model OpenShift SRE assistant with guarded OpenShift operational tools.",
)

if SITE_DIR is not None:
    app.mount("/guide", StaticFiles(directory=SITE_DIR, html=True), name="guide")

BASE_SETTINGS = Settings.load()


class RuntimeConfig(BaseModel):
    ollama_base_url: str | None = Field(default=None, description="Optional Ollama base URL override.")
    local_model_name: str | None = Field(default=None, description="Optional local model name override.")
    cluster_scope: str | None = Field(default=None, description="Optional cluster scope override.")
    kube_context_name: str | None = Field(default=None, description="Optional kube context override.")
    openshift_api_url_field: str | None = Field(default=None, description="Optional OpenShift API URL.")
    openshift_token_field: str | None = Field(default=None, description="Optional OpenShift token.")
    openshift_namespace_field: str | None = Field(default=None, description="Optional OpenShift namespace.")
    tls_ca_bundle: str | None = Field(default=None, description="Optional CA bundle path override.")
    verify_ssl: bool | None = Field(default=None, description="Optional TLS verification override.")
    agent_max_steps: int | None = Field(default=None, ge=1, le=20, description="Optional reasoning step limit.")


class ChatRequest(BaseModel):
    prompt: str = Field(min_length=5, description="Natural language SRE question or task.")
    runtime: RuntimeConfig | None = None


class ChatResponse(BaseModel):
    answer: str
    steps: list[dict]


@app.api_route("/", methods=["GET", "HEAD"], include_in_schema=False, response_model=None)
def root():
    if SITE_DIR is not None:
        return RedirectResponse(url="/guide/")
    return {
        "name": "OpenShift SRE Local Agent",
        "status": "ok",
        "endpoints": {
            "health": "/health",
            "chat": "/chat",
            "openapi_docs": "/docs",
        },
    }


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    try:
        runtime = request.runtime or RuntimeConfig()
        agent = OpenShiftSreAgent(
            BASE_SETTINGS.with_overrides(
                ollama_base_url=runtime.ollama_base_url,
                local_model_name=runtime.local_model_name,
                cluster_scope=runtime.cluster_scope,
                kube_context_name=runtime.kube_context_name,
                openshift_api_url_field=runtime.openshift_api_url_field,
                openshift_token_field=runtime.openshift_token_field,
                openshift_namespace_field=runtime.openshift_namespace_field,
                tls_ca_bundle=runtime.tls_ca_bundle,
                verify_ssl=runtime.verify_ssl,
                agent_max_steps=runtime.agent_max_steps,
            )
        )
        result = agent.ask(request.prompt)
    except Exception as error:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(error)) from error
    return ChatResponse(answer=result.answer, steps=result.steps)
````

## `src/openshift_sre_agent/cli.py`

The CLI offers a one-shot terminal mode and the HTTP server mode used by the container.

````python
from __future__ import annotations

import json

import typer
from rich.console import Console
from rich.panel import Panel

from .agent import OpenShiftSreAgent
from .config import Settings

app = typer.Typer(help="OpenShift SRE local-model agent")
console = Console()


@app.command()
def ask(prompt: str, show_steps: bool = typer.Option(True, help="Show the reasoning/tool trace.")) -> None:
    """Ask the agent to investigate an OpenShift SRE question."""
    agent = OpenShiftSreAgent(Settings.load())
    result = agent.ask(prompt)
    console.print(Panel.fit(result.answer, title="OpenShift SRE Agent"))
    if show_steps:
        console.print_json(json.dumps(result.steps, default=str))


@app.command()
def serve(host: str = "0.0.0.0", port: int = 8000) -> None:
    """Run the HTTP API that can be containerized or called from other tools."""
    import uvicorn

    uvicorn.run("openshift_sre_agent.api:app", host=host, port=port, reload=False)


if __name__ == "__main__":
    app()
````

## `src/openshift_sre_agent/__main__.py`

This file makes `python -m openshift_sre_agent` work by delegating directly to the Typer app.

````python
from .cli import app

app()
````

## `src/openshift_sre_agent/__init__.py`

This is the package export file. It keeps the top-level import clean so callers can import `OpenShiftSreAgent` directly from `openshift_sre_agent` instead of reaching into module internals.

````python
"""OpenShift SRE local-model agent."""

from .agent import OpenShiftSreAgent

__all__ = ["OpenShiftSreAgent"]
````
