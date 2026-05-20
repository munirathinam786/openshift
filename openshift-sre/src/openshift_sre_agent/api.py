from __future__ import annotations

import asyncio
import json
import logging
import os
import signal
import shutil
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
import subprocess
from time import perf_counter
from typing import Any, AsyncGenerator
from urllib.parse import urlparse

import httpx
from fastapi import FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.responses import PlainTextResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from starlette.responses import StreamingResponse

from .agent import OpenShiftSreAgent
from .config import LLM_PROVIDER_METADATA, Settings, get_llm_provider_defaults, normalize_llm_provider
from .logging_config import setup_logging
from .middleware import (
    MAX_PROMPT_LENGTH,
    AuthMiddleware,
    RateLimitMiddleware,
    RequestTracingMiddleware,
    SecurityHeadersMiddleware,
    add_cors,
    detect_prompt_injection,
)
from .model_client import CircuitOpen, ModelClient, OllamaClient
from .persistence import HistoryStore
from .tools import OpenShiftSreToolkit

logger = logging.getLogger(__name__)
STACK_CONTAINER_NAMES = {"openshift-sre-agent", "openshift-sre-agent-db"}
AGENT_HELPERS = OpenShiftSreAgent


def _resolve_site_dir() -> Path | None:
    """Return the generated MkDocs ``site/`` directory if one is available."""

    candidates = [
        Path.cwd() / "site",
        Path(__file__).resolve().parents[2] / "site",
        Path(__file__).resolve().parents[1] / "site",
    ]
    for candidate in candidates:
        if candidate.exists() and candidate.is_dir():
            return candidate
    return None


def _resolve_legacy_site_dir() -> Path | None:
    """Return the parent Terraform-IaC generated site directory when available."""

    configured = os.environ.get("LEGACY_SITE_DIR")
    candidates = [
        Path(configured).expanduser() if configured else None,
        Path("/app/legacy-site"),
        Path.cwd() / "legacy-site",
        Path(__file__).resolve().parents[3] / "site",
        Path.cwd().parent / "site",
    ]
    for candidate in candidates:
        if candidate is not None and candidate.exists() and candidate.is_dir():
            return candidate
    return None


SITE_DIR = _resolve_site_dir()
LEGACY_SITE_DIR = _resolve_legacy_site_dir()

# --- Graceful shutdown lifespan — v0.3.0 ---
_shutting_down = False


@asynccontextmanager
async def lifespan(application: FastAPI):
    """Manage startup retention enforcement and graceful-shutdown state."""

    global _shutting_down
    logger.info("OpenShift SRE Agent starting up — v0.3.0")
    # Enforce data retention on startup
    if BASE_SETTINGS.data_retention_days > 0 and HISTORY_STORE.enabled:
        purged = HISTORY_STORE.enforce_retention(BASE_SETTINGS.data_retention_days)
        if purged:
            logger.info("Data retention: purged %d runs older than %d days", purged, BASE_SETTINGS.data_retention_days)
    yield
    _shutting_down = True
    logger.info("OpenShift SRE Agent shutting down gracefully")


app = FastAPI(
    title="OpenShift SRE Local Agent",
    version="0.3.0",
    description="Local-model OpenShift SRE assistant with guarded read-only platform tools.",
    lifespan=lifespan,
)

# --- Middleware stack (order matters: outermost runs first) ---
add_cors(app)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RateLimitMiddleware, capacity=60, refill_rate=1.0)
app.add_middleware(RequestTracingMiddleware)

if SITE_DIR is not None:
    app.mount("/guide", StaticFiles(directory=SITE_DIR, html=True), name="guide")

BASE_SETTINGS = Settings.load()
setup_logging(BASE_SETTINGS.log_level)
HISTORY_STORE = HistoryStore(BASE_SETTINGS)

# Auth middleware (only active when API_KEY is set)
if BASE_SETTINGS.auth_enabled and BASE_SETTINGS.api_key:
    app.add_middleware(AuthMiddleware, api_key=BASE_SETTINGS.api_key)
    logger.info("API key authentication enabled")

# --- WebSocket connection manager for live updates ---
_ws_clients: set[WebSocket] = set()


async def _broadcast_ws(event: dict) -> None:
    """Send *event* to all connected WebSocket clients."""
    dead: set[WebSocket] = set()
    payload = json.dumps(event, default=str)
    for ws in _ws_clients:
        try:
            await ws.send_text(payload)
        except Exception:  # noqa: BLE001
            dead.add(ws)
    _ws_clients.difference_update(dead)


def _schedule_ws_broadcast(event: dict) -> None:
    """Dispatch websocket notifications from both async and sync request contexts."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop is not None and loop.is_running():
        loop.create_task(_broadcast_ws(event))
        return

    asyncio.run(_broadcast_ws(event))


class RuntimeConfig(BaseModel):
    llm_provider: str | None = Field(default=None, description="Optional LLM provider override.")
    llm_model_name: str | None = Field(default=None, description="Optional external/provider model name override.")
    llm_base_url: str | None = Field(default=None, description="Optional external/provider base URL override.")
    llm_api_key: str | None = Field(default=None, description="Optional external/provider API key.")
    llm_api_version: str | None = Field(default=None, description="Optional external/provider API version.")
    llm_organization: str | None = Field(default=None, description="Optional organization or tenant hint for supported providers.")
    ollama_base_url: str | None = Field(default=None, description="Optional Ollama base URL override.")
    local_model_name: str | None = Field(default=None, description="Optional local model name override.")
    openshift_cluster: str | None = Field(default=None, description="Optional OpenShift cluster name override.")
    openshift_namespace: str | None = Field(default=None, description="Optional default namespace or project override.")
    openshift_projects: str | None = Field(default=None, description="Optional CSV list of projects for sweeps.")
    openshift_api_url: str | None = Field(default=None, description="Optional Kubernetes API endpoint override.")
    openshift_token: str | None = Field(default=None, description="Optional bearer token override.")
    kubeconfig_path: str | None = Field(default=None, description="Optional kubeconfig path override.")
    kube_context: str | None = Field(default=None, description="Optional kube context override.")
    oc_cli_path: str | None = Field(default=None, description="Optional oc CLI path override.")
    openshift_verify_ssl: bool | None = Field(default=None, description="Optional cluster SSL verification override.")
    cluster_scope: str | None = Field(default=None, description="Backward-compatible alias for cluster name.")
    cluster_scopes: str | None = Field(default=None, description="Backward-compatible alias for project sweep scope.")
    kube_context_name: str | None = Field(default=None, description="Backward-compatible alias for kube context.")
    openshift_api_url_field: str | None = Field(default=None, description="Backward-compatible alias for API endpoint.")
    openshift_token_field: str | None = Field(default=None, description="Backward-compatible alias for bearer token.")
    openshift_namespace_field: str | None = Field(default=None, description="Backward-compatible alias for namespace.")
    reserved_role_arn: str | None = Field(default=None, description="Retained for compatibility; unused for OpenShift runtime.")
    reserved_role_external_id: str | None = Field(default=None, description="Retained for compatibility; unused for OpenShift runtime.")
    agent_session_name: str | None = Field(default=None, description="Retained for compatibility with historical API clients.")
    tls_ca_bundle: str | None = Field(default=None, description="Retained for compatibility; prefer kubeconfig trust settings.")
    verify_ssl: bool | None = Field(default=None, description="Backward-compatible alias for cluster SSL verification override.")
    agent_max_steps: int | None = Field(default=None, ge=1, le=20, description="Optional reasoning step limit.")


class ChatRequest(BaseModel):
    prompt: str = Field(min_length=5, max_length=MAX_PROMPT_LENGTH, description="Natural language SRE question or task.")
    runtime: RuntimeConfig | None = None
    conversation_id: str | None = Field(default=None, max_length=64, description="Optional conversation ID for multi-turn memory.")
    tags: list[str] | None = Field(default=None, max_length=10, description="Optional labels for this run.")


class ChatResponse(BaseModel):
    answer: str
    steps: list[dict]
    run_id: int | None = None
    confidence: float | None = None
    token_usage: dict[str, int] | None = None
    tags: list[str] | None = None


class SecurityAuditRequest(BaseModel):
    profile_key: str = Field(default="sox", max_length=64)
    profile_label: str = Field(min_length=1, max_length=255)
    focus_label: str = Field(min_length=1, max_length=255)
    selected_features: list[str] = Field(min_length=1, max_length=20)
    operator_notes: str = Field(default="", max_length=4000)
    runtime: RuntimeConfig | None = None
    tags: list[str] | None = Field(default=None, max_length=10)


class FinopsQueueCreateRequest(BaseModel):
    opportunity_key: str = Field(min_length=1, max_length=255)
    title: str = Field(min_length=1, max_length=255)
    category: str = Field(min_length=1, max_length=64)
    estimated_monthly_savings: float = Field(default=0.0)
    unit: str = Field(default="USD", max_length=32)
    risk: str = Field(default="unknown", max_length=32)
    confidence: str = Field(default="unknown", max_length=32)
    action: str = Field(default="")
    basis: str = Field(default="")
    evidence: str = Field(default="")
    execution_plan: str = Field(default="")
    run_id: int | None = None
    auto_approve: bool = False
    execution_mode: str = Field(default="future-safe-execution-plan-only", max_length=128)


class FinopsQueueStageUpdateRequest(BaseModel):
    execution_stage: str = Field(min_length=1, max_length=64)


class SavedInvestigationCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    prompt: str = Field(min_length=5, max_length=MAX_PROMPT_LENGTH)
    description: str = Field(default="")
    category: str = Field(default="general", max_length=64)
    default_regions: list[str] | None = None
    default_tags: list[str] | None = None
    default_tools: list[str] | None = None


class SavedInvestigationUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    prompt: str | None = Field(default=None, min_length=5, max_length=MAX_PROMPT_LENGTH)
    description: str | None = None
    category: str | None = Field(default=None, max_length=64)
    default_regions: list[str] | None = None
    default_tags: list[str] | None = None
    default_tools: list[str] | None = None


class WatchlistCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    investigation_id: int | None = None
    notes: str = Field(default="")
    schedule_hint: str = Field(default="manual", max_length=128)
    regions: list[str] | None = None
    role_arns: list[str | None] | None = None
    tags: list[str] | None = None
    enabled: bool = True


class WatchlistUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    investigation_id: int | None = None
    notes: str | None = None
    schedule_hint: str | None = Field(default=None, max_length=128)
    regions: list[str] | None = None
    role_arns: list[str | None] | None = None
    tags: list[str] | None = None
    enabled: bool | None = None


class WatchlistRunRequest(BaseModel):
    runtime: RuntimeConfig | None = None


class PlatformSweepRequest(BaseModel):
    tool_names: list[str] = Field(min_length=1, max_length=12)
    regions: list[str] | None = None
    role_arns: list[str | None] | None = None
    runtime: RuntimeConfig | None = None


def _parse_csv_query(value: str | None) -> list[str] | None:
    if value is None:
        return None
    items = [item.strip() for item in value.split(",") if item.strip()]
    return items or None


def _runtime_settings(runtime: RuntimeConfig | None) -> Settings:
    """Combine base settings with request-scoped provider and OpenShift overrides."""

    resolved_runtime = runtime or RuntimeConfig()
    return BASE_SETTINGS.with_overrides(
        llm_provider=normalize_llm_provider(resolved_runtime.llm_provider),
        llm_model_name=resolved_runtime.llm_model_name,
        llm_base_url=resolved_runtime.llm_base_url,
        llm_api_key=resolved_runtime.llm_api_key,
        llm_api_version=resolved_runtime.llm_api_version,
        llm_organization=resolved_runtime.llm_organization,
        ollama_base_url=resolved_runtime.ollama_base_url,
        local_model_name=resolved_runtime.local_model_name,
        openshift_cluster=resolved_runtime.openshift_cluster,
        openshift_namespace=resolved_runtime.openshift_namespace,
        openshift_projects=resolved_runtime.openshift_projects,
        openshift_api_url=resolved_runtime.openshift_api_url,
        openshift_token=resolved_runtime.openshift_token,
        kubeconfig_path=resolved_runtime.kubeconfig_path,
        kube_context=resolved_runtime.kube_context,
        oc_cli_path=resolved_runtime.oc_cli_path,
        openshift_verify_ssl=resolved_runtime.openshift_verify_ssl,
        cluster_scope=resolved_runtime.cluster_scope,
        cluster_scopes=resolved_runtime.cluster_scopes,
        kube_context_name=resolved_runtime.kube_context_name,
        openshift_api_url_field=resolved_runtime.openshift_api_url_field,
        openshift_token_field=resolved_runtime.openshift_token_field,
        openshift_namespace_field=resolved_runtime.openshift_namespace_field,
        reserved_role_arn=resolved_runtime.reserved_role_arn,
        reserved_role_external_id=resolved_runtime.reserved_role_external_id,
        agent_session_name=resolved_runtime.agent_session_name,
        tls_ca_bundle=resolved_runtime.tls_ca_bundle,
        verify_ssl=resolved_runtime.verify_ssl,
        agent_max_steps=resolved_runtime.agent_max_steps,
    )


def _execute_agent_prompt(
    *,
    prompt: str,
    runtime: RuntimeConfig | None,
    conversation_id: str | None = None,
    tags: list[str] | None = None,
) -> tuple[ChatResponse, Settings, int]:
    """Execute one prompt, persist the run, and return the API response tuple."""

    settings = _runtime_settings(runtime)
    started_at = perf_counter()
    try:
        agent = OpenShiftSreAgent(settings)
        if tags:
            agent.set_tags(tags)
        if conversation_id:
            agent.set_conversation_context(HISTORY_STORE.get_conversation_turns(conversation_id, limit=5))
        result = agent.ask(prompt)
    except Exception as error:  # noqa: BLE001
        status_code, detail = _map_agent_error_to_http(error, settings)
        HISTORY_STORE.record_chat(
            prompt=prompt,
            answer="",
            steps=[],
            model_name=settings.effective_model_name,
            cluster_scope=settings.cluster_scope,
            duration_ms=int((perf_counter() - started_at) * 1000),
            status="failed",
            error_message=detail,
        )
        raise HTTPException(status_code=status_code, detail=detail) from error

    duration_ms = int((perf_counter() - started_at) * 1000)
    run_id = HISTORY_STORE.record_chat(
        prompt=prompt,
        answer=result.answer,
        steps=result.steps,
        model_name=settings.effective_model_name,
        cluster_scope=settings.cluster_scope,
        duration_ms=duration_ms,
        conversation_id=conversation_id,
        token_usage=result.token_usage,
        tags=result.tags,
    )
    _schedule_ws_broadcast(
        {
            "type": "run_completed",
            "run_id": run_id,
            "status": "completed",
            "duration_ms": duration_ms,
            "model_name": settings.effective_model_name,
            "provider_name": settings.llm_provider,
            "prompt_excerpt": prompt[:120],
            "confidence": result.confidence,
        }
    )
    return (
        ChatResponse(
            answer=result.answer,
            steps=result.steps,
            run_id=run_id,
            confidence=result.confidence,
            token_usage=result.token_usage,
            tags=result.tags,
        ),
        settings,
        duration_ms,
    )


def _safe_int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _build_security_audit_prompt(
    *,
    profile_label: str,
    focus_label: str,
    region: str,
    selected_features: list[str],
    operator_notes: str,
) -> str:
    feature_labels = [AGENT_HELPERS._humanize_tool_name(tool_name) for tool_name in selected_features]
    prompt_parts = [
        f'Perform a batched OpenShift security audit using the profile "{profile_label}".',
        f"Primary region: {region}.",
        f"Review focus: {focus_label}.",
        f"Selected OpenShift security features: {', '.join(feature_labels)}.",
        "Return an executive summary, control coverage, missing APIs or permissions, and prioritized next steps.",
    ]
    if operator_notes.strip():
        prompt_parts.append(f"Operator notes: {operator_notes.strip()}")
    return " ".join(prompt_parts)


def _count_security_audit_signals(steps: list[dict[str, Any]]) -> dict[str, int]:
    summary = {
        "reviewed_controls": 0,
        "blocking_errors": 0,
        "disabled_controls": 0,
        "finding_count": 0,
        "compliance_gaps": 0,
        "identity_or_encryption_gaps": 0,
        "data_protection_gaps": 0,
    }

    for step in steps:
        result = step.get("tool_result") or {}
        error_message = result.get("error") or step.get("tool_error")
        if error_message:
            summary["blocking_errors"] += 1
            if AGENT_HELPERS._error_classification(str(error_message)) == "not_enabled":
                summary["disabled_controls"] += 1
            continue

        summary["reviewed_controls"] += 1
        tool_name = (step.get("tool_call") or {}).get("name") or ""
        summary["finding_count"] += _safe_int(result.get("count") if tool_name in AGENT_HELPERS._FINDINGS_TOOL_NAMES else 0)

        compliance_counts = result.get("compliance_type_counts") or {}
        if isinstance(compliance_counts, dict):
            summary["compliance_gaps"] += sum(
                _safe_int(value)
                for key, value in compliance_counts.items()
                if str(key).upper() not in {"COMPLIANT", "PASSED", "OK"}
            )

        summary["identity_or_encryption_gaps"] += _safe_int(result.get("stale_role_count"))
        summary["identity_or_encryption_gaps"] += _safe_int(result.get("public_or_unencrypted_count"))
        summary["data_protection_gaps"] += _safe_int(result.get("public_or_unencrypted_count"))
        summary["data_protection_gaps"] += _safe_int(result.get("at_risk_instance_count"))
        summary["data_protection_gaps"] += _safe_int(result.get("at_risk_cluster_count"))

    return summary


def _build_security_audit_answer(
    *,
    profile_label: str,
    focus_label: str,
    region: str,
    operator_notes: str,
    steps: list[dict[str, Any]],
) -> str:
    counters = _count_security_audit_signals(steps)
    total_controls = len(steps)
    summary_parts = [
        f"{profile_label} security audit completed for {region}.",
        (
            f"Reviewed {counters['reviewed_controls']} of {total_controls} requested control area(s), "
            f"with {counters['blocking_errors']} blocking error(s) and {counters['disabled_controls']} disabled or unsubscribed control(s)."
        ),
        f"Audit focus: {focus_label}.",
    ]

    if counters["finding_count"] > 0:
        summary_parts.append(f"Sampled security findings captured: {counters['finding_count']}.")
    if counters["compliance_gaps"] > 0:
        summary_parts.append(f"Compliance exceptions detected in sampled Config outputs: {counters['compliance_gaps']}.")
    if counters["identity_or_encryption_gaps"] > 0:
        summary_parts.append(
            f"Identity, encryption, or exposure gaps detected across the sampled controls: {counters['identity_or_encryption_gaps']}."
        )
    if counters["reviewed_controls"] == 0:
        summary_parts.append("No control checks completed successfully, so the results should be treated as incomplete.")
    if operator_notes.strip():
        summary_parts.append(f"Operator context noted: {operator_notes.strip()}")

    return AGENT_HELPERS._augment_final_answer(" ".join(summary_parts), steps, missing_tools=[])


def _run_batched_security_audit(request: SecurityAuditRequest) -> tuple[ChatResponse, Settings, int]:
    settings = _runtime_settings(request.runtime)
    toolkit = OpenShiftSreToolkit(settings)
    selected_features: list[str] = []
    invalid_features: list[str] = []
    for tool_name in request.selected_features:
        normalized = str(tool_name or "").strip()
        if not normalized:
            continue
        if normalized in toolkit.tools:
            if normalized not in selected_features:
                selected_features.append(normalized)
        else:
            invalid_features.append(normalized)

    if invalid_features:
        raise HTTPException(status_code=400, detail=f"Unsupported security audit tools requested: {', '.join(invalid_features)}")
    if not selected_features:
        raise HTTPException(status_code=400, detail="At least one supported security audit feature is required.")

    prompt = _build_security_audit_prompt(
        profile_label=request.profile_label,
        focus_label=request.focus_label,
        region=settings.cluster_scope,
        selected_features=selected_features,
        operator_notes=request.operator_notes,
    )

    started_at = perf_counter()
    steps: list[dict[str, Any]] = []
    for index, tool_name in enumerate(selected_features, start=1):
        step_record: dict[str, Any] = {
            "step": index,
            "thought": f"Run {AGENT_HELPERS._humanize_tool_name(tool_name)} for the batched security audit.",
            "tool_call": {"name": tool_name, "arguments": {}},
            "final_answer": "",
            "batched_security_audit": True,
        }
        try:
            step_record["tool_result"] = toolkit.invoke(tool_name, {})
        except Exception as error:  # noqa: BLE001
            step_record["tool_error"] = str(error)
            step_record["tool_result"] = {"error": str(error)}
        steps.append(step_record)

    answer = _build_security_audit_answer(
        profile_label=request.profile_label,
        focus_label=request.focus_label,
        region=settings.cluster_scope,
        operator_notes=request.operator_notes,
        steps=steps,
    )
    duration_ms = int((perf_counter() - started_at) * 1000)
    audit_tags = list(dict.fromkeys([*(request.tags or []), "security-audit", request.profile_key]))
    confidence = AGENT_HELPERS._compute_confidence(steps)
    run_id = HISTORY_STORE.record_chat(
        prompt=prompt,
        answer=answer,
        steps=steps,
        model_name=settings.effective_model_name,
        cluster_scope=settings.cluster_scope,
        duration_ms=duration_ms,
        token_usage={"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
        tags=audit_tags,
    )
    if run_id is not None:
        _schedule_ws_broadcast(
            {
                "type": "run_completed",
                "run_id": run_id,
                "status": "completed",
                "duration_ms": duration_ms,
                "model_name": settings.effective_model_name,
                "provider_name": settings.llm_provider,
                "prompt_excerpt": prompt[:120],
                "confidence": confidence,
            }
        )

    return (
        ChatResponse(
            answer=answer,
            steps=steps,
            run_id=run_id,
            confidence=confidence,
            token_usage={"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
            tags=audit_tags,
        ),
        settings,
        duration_ms,
    )


def _map_agent_error_to_http(error: Exception, settings: Settings) -> tuple[int, str]:
    """Map agent/model/provider failures to operator-friendly HTTP responses."""

    provider_label = settings.llm_provider

    if isinstance(error, CircuitOpen):
        return 503, f"{provider_label} provider is temporarily unavailable after repeated failures. Please retry shortly."

    if isinstance(error, httpx.HTTPStatusError):
        response = error.response
        request = error.request
        upstream_text = ""
        try:
            upstream_text = (response.text or "").strip()
        except Exception:  # noqa: BLE001
            upstream_text = ""
        if len(upstream_text) > 600:
            upstream_text = f"{upstream_text[:600].rstrip()}…"
        detail = (
            f"{provider_label} provider request failed with upstream status {response.status_code} "
            f"for {request.url}."
        )
        if upstream_text:
            detail = f"{detail} Response body: {upstream_text}"
        return 502, detail

    if isinstance(error, httpx.HTTPError):
        return 502, f"{provider_label} provider request failed: {error}"

    message = str(error).strip() or error.__class__.__name__
    if message.startswith("LLM provider ") and "requires an API key" in message:
        return 400, message
    if message.startswith("Unsupported LLM provider:"):
        return 400, message

    return 500, message


def _running_in_container() -> bool:
    return Path("/.dockerenv").exists() or Path("/run/.containerenv").exists()


def _format_bytes_label(value: int | float | None) -> str | None:
    if value is None:
        return None
    numeric = float(value)
    units = ["B", "KiB", "MiB", "GiB", "TiB"]
    index = 0
    while numeric >= 1024 and index < len(units) - 1:
        numeric /= 1024
        index += 1
    return f"{numeric:.2f} {units[index]}"


def _parse_percent_value(value: str | None) -> float | None:
    if value is None:
        return None
    cleaned = str(value).strip().replace("%", "")
    try:
        return round(float(cleaned), 2)
    except ValueError:
        return None


def _parse_json_stream(stdout: str) -> list[dict]:
    raw = stdout.strip()
    if not raw:
        return []
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        parsed = None
    if isinstance(parsed, list):
        return [item for item in parsed if isinstance(item, dict)]
    if isinstance(parsed, dict):
        return [parsed]

    rows: list[dict] = []
    for line in raw.splitlines():
        text = line.strip()
        if not text:
            continue
        try:
            payload = json.loads(text)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            rows.append(payload)
    return rows


def _read_cgroup_int(path: str) -> int | None:
    try:
        raw = Path(path).read_text().strip()
    except OSError:
        return None
    if raw in {"", "max"}:
        return None
    try:
        return int(raw)
    except ValueError:
        return None


def _build_container_stub(name: str, *, image: str | None = None, note: str | None = None, include_memory: bool = False) -> dict:
    memory_usage_bytes = _read_cgroup_int("/sys/fs/cgroup/memory.current") if include_memory else None
    memory_limit_bytes = _read_cgroup_int("/sys/fs/cgroup/memory.max") if include_memory else None
    memory_percent = None
    if memory_usage_bytes is not None and memory_limit_bytes not in (None, 0):
        memory_percent = round((memory_usage_bytes / memory_limit_bytes) * 100, 2)
    return {
        "name": name,
        "image": image,
        "status": "running" if include_memory else "unknown",
        "state": "running" if include_memory else "unknown",
        "size": None,
        "cpu_percent": None,
        "memory_percent": memory_percent,
        "memory_usage": _format_bytes_label(memory_usage_bytes),
        "memory_limit": _format_bytes_label(memory_limit_bytes),
        "memory_usage_bytes": memory_usage_bytes,
        "memory_limit_bytes": memory_limit_bytes,
        "gpu_usage": None,
        "gpu_note": "GPU metrics are unavailable unless the local container runtime exposes them.",
        "source": "fallback",
        "note": note,
    }


def _container_cli_name() -> str | None:
    return shutil.which("podman") or shutil.which("docker")


def _get_container_observability() -> dict:
    cli = _container_cli_name()
    runtime_name = Path(cli).name if cli else None
    note = None
    containers: list[dict] = []

    if cli:
        try:
            ps_output = subprocess.run(
                [cli, "ps", "-a", "--size", "--format", "{{json .}}"],
                check=True,
                capture_output=True,
                text=True,
            )
            stats_output = subprocess.run(
                [cli, "stats", "--all", "--no-stream", "--format", "{{json .}}"],
                check=True,
                capture_output=True,
                text=True,
            )
            ps_rows = _parse_json_stream(ps_output.stdout)
            stats_rows = _parse_json_stream(stats_output.stdout)
            stats_by_name = {
                row.get("Name") or row.get("Names") or row.get("Container") or row.get("ContainerName"): row
                for row in stats_rows
                if isinstance(row, dict)
            }
            for row in ps_rows:
                name = row.get("Names") or row.get("Name") or row.get("Container") or row.get("ContainerName")
                if not name or (STACK_CONTAINER_NAMES and name not in STACK_CONTAINER_NAMES and not name.startswith("openshift-sre-agent")):
                    continue
                stats = stats_by_name.get(name, {})
                containers.append(
                    {
                        "name": name,
                        "image": row.get("Image") or row.get("ImageID"),
                        "status": row.get("Status") or row.get("State"),
                        "state": row.get("State") or row.get("Status"),
                        "size": row.get("Size") or row.get("LocalVolumes"),
                        "cpu_percent": _parse_percent_value(stats.get("CPU") or stats.get("CPUPerc") or stats.get("AVGCPU")),
                        "memory_percent": _parse_percent_value(stats.get("MemPerc") or stats.get("MEM %")),
                        "memory_usage": stats.get("MemUsage") or stats.get("MemUsage / Limit"),
                        "memory_limit": None,
                        "memory_usage_bytes": None,
                        "memory_limit_bytes": None,
                        "gpu_usage": stats.get("GPU") or stats.get("GPUUsage") or None,
                        "gpu_note": "GPU metrics are only shown when exposed by the container runtime.",
                        "source": "container-cli",
                        "note": None,
                    }
                )
        except (subprocess.CalledProcessError, FileNotFoundError) as error:
            note = f"{runtime_name} metrics are unavailable from this process: {error}"

    if not containers:
        fallback_note = note or (
            "Container-runtime statistics are not directly reachable from the app process, so the page is showing safe fallback data."
        )
        if _running_in_container():
            containers.append(
                _build_container_stub(
                    os.environ.get("HOSTNAME") or "openshift-sre-agent",
                    image="localhost/openshift-sre-agent-local:dev",
                    note="This is the current application container. CPU usage requires Podman or Docker CLI visibility from the host.",
                    include_memory=True,
                )
            )
        containers.append(
            _build_container_stub(
                "openshift-sre-agent-db",
                image="docker.io/library/mariadb:11.4",
                note="Database-specific utilization is reported in the database section below.",
            )
        )
        note = fallback_note

    return {
        "runtime": runtime_name or "unavailable",
        "source": "container-cli" if cli and any(item.get("source") == "container-cli" for item in containers) else "fallback",
        "note": note,
        "containers": containers,
    }


def _get_runtime_observability_snapshot() -> dict:
    return {
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "containers": _get_container_observability(),
        "database": HISTORY_STORE.get_database_observability(),
    }


def _format_gib(value: int | float | None) -> float | None:
    if value is None:
        return None
    return round(float(value) / (1024 ** 3), 2)


def _parse_process_snapshot(stdout: str) -> list[dict]:
    processes: list[dict] = []
    for raw_line in stdout.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        parts = line.split(None, 7)
        if len(parts) < 8:
            continue
        pid, ppid, cpu_percent, mem_percent, rss_kb, vsz_kb, elapsed, command = parts
        lowered = command.lower()
        if not any(token in lowered for token in ("ollama", "llama", "runner")):
            continue
        try:
            processes.append(
                {
                    "pid": int(pid),
                    "ppid": int(ppid),
                    "cpu_percent": float(cpu_percent),
                    "mem_percent": float(mem_percent),
                    "rss_mb": round(int(rss_kb) / 1024, 1),
                    "vsz_mb": round(int(vsz_kb) / 1024, 1),
                    "elapsed": elapsed,
                    "command": command,
                }
            )
        except ValueError:
            continue
    return processes


def _inspect_local_ollama_processes(settings: Settings) -> dict:
    parsed = urlparse(settings.ollama_base_url)
    host = (parsed.hostname or "").lower()
    running_in_container = _running_in_container()

    if running_in_container and host in {"host.containers.internal", "localhost", "127.0.0.1"}:
        return {
            "available": False,
            "scope": "container",
            "note": (
                "The API is running inside Podman, so host-level macOS Ollama process CPU/RAM is not directly visible here. "
                "Use the documented laptop commands on the LLM Utilization page for host process metrics."
            ),
            "processes": [],
        }

    try:
        result = subprocess.run(
            [
                "ps",
                "-axo",
                "pid,ppid,%cpu,%mem,rss,vsz,etime,command",
            ],
            check=True,
            capture_output=True,
            text=True,
        )
    except (FileNotFoundError, subprocess.CalledProcessError) as error:
        return {
            "available": False,
            "scope": "local",
            "note": f"Local process inspection failed: {error}",
            "processes": [],
        }

    processes = _parse_process_snapshot(result.stdout)
    return {
        "available": bool(processes),
        "scope": "local",
        "note": "Process metrics are sampled from the same runtime that serves this API.",
        "processes": processes,
    }


def _get_ollama_utilization_snapshot(settings: Settings) -> dict:
    snapshot: dict = {
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "ollama_base_url": settings.ollama_base_url,
        "configured_model_name": settings.local_model_name,
        "running_in_container": _running_in_container(),
        "api_reachable": False,
        "api_error": None,
        "active_model_count": 0,
        "loaded_models": [],
        "host_process_metrics": _inspect_local_ollama_processes(settings),
        "recommended_host_commands": [
            "ollama ps",
            "curl -s http://127.0.0.1:11434/api/ps",
            "lsof -nP -iTCP:11434 -sTCP:LISTEN",
            "ps -axo pid,ppid,%cpu,%mem,rss,vsz,etime,command | egrep 'ollama|llama|runner' | egrep -v 'egrep'",
            "top -l 1 -pid <OLLAMA_SERVE_PID> -pid <OLLAMA_RUNNER_PID> -stats pid,command,cpu,mem,rprvt,vsize,state,time",
        ],
    }

    try:
        with httpx.Client(timeout=5.0) as client:
            response = client.get(f"{settings.ollama_base_url}/api/ps")
            response.raise_for_status()
            payload = response.json()
    except Exception as error:  # noqa: BLE001
        snapshot["api_error"] = str(error)
        return snapshot

    models = []
    for model in payload.get("models", []):
        details = model.get("details") or {}
        size_bytes = model.get("size")
        size_vram_bytes = model.get("size_vram")
        models.append(
            {
                "name": model.get("name") or model.get("model"),
                "model": model.get("model") or model.get("name"),
                "digest": model.get("digest"),
                "size_bytes": size_bytes,
                "size_gib": _format_gib(size_bytes),
                "size_vram_bytes": size_vram_bytes,
                "size_vram_gib": _format_gib(size_vram_bytes),
                "context_length": model.get("context_length"),
                "expires_at": model.get("expires_at"),
                "family": details.get("family"),
                "families": details.get("families") or [],
                "format": details.get("format"),
                "parameter_size": details.get("parameter_size"),
                "quantization_level": details.get("quantization_level"),
                "processor_hint": "GPU/VRAM" if size_vram_bytes else "CPU / unknown",
            }
        )

    snapshot["api_reachable"] = True
    snapshot["loaded_models"] = models
    snapshot["active_model_count"] = len(models)
    return snapshot


def _get_ollama_models_catalog(settings: Settings) -> dict:
    snapshot: dict = {
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "ollama_base_url": settings.ollama_base_url,
        "configured_model_name": settings.local_model_name,
        "api_reachable": False,
        "api_error": None,
        "model_count": 0,
        "models": [],
    }

    loaded_models: dict[str, dict] = {}
    try:
        with httpx.Client(timeout=5.0) as client:
            response = client.get(f"{settings.ollama_base_url}/api/ps")
            response.raise_for_status()
            for model in response.json().get("models", []):
                name = model.get("name") or model.get("model")
                if name:
                    loaded_models[name] = model
    except Exception:  # noqa: BLE001
        loaded_models = {}

    try:
        with httpx.Client(timeout=5.0) as client:
            response = client.get(f"{settings.ollama_base_url}/api/tags")
            response.raise_for_status()
            payload = response.json()
    except Exception as error:  # noqa: BLE001
        snapshot["api_error"] = str(error)
        return snapshot

    models = []
    for model in payload.get("models", []):
        details = model.get("details") or {}
        name = model.get("name") or model.get("model")
        if not name:
            continue
        loaded_model = loaded_models.get(name, {})
        models.append(
            {
                "name": name,
                "model": model.get("model") or name,
                "modified_at": model.get("modified_at"),
                "size_bytes": model.get("size"),
                "size_gib": _format_gib(model.get("size")),
                "family": details.get("family"),
                "parameter_size": details.get("parameter_size"),
                "quantization_level": details.get("quantization_level"),
                "loaded": bool(loaded_model),
                "loaded_context_length": loaded_model.get("context_length"),
                "loaded_size_vram_gib": _format_gib(loaded_model.get("size_vram")),
            }
        )

    models.sort(
        key=lambda model: (
            0 if model["name"] == settings.local_model_name else 1,
            0 if model["loaded"] else 1,
            model["name"],
        )
    )
    snapshot["api_reachable"] = True
    snapshot["models"] = models
    snapshot["model_count"] = len(models)
    return snapshot


def _get_llm_provider_catalog() -> dict:
    """Return the provider catalog payload consumed by the browser settings panels."""

    providers = []
    for provider_id, metadata in LLM_PROVIDER_METADATA.items():
        defaults = get_llm_provider_defaults(provider_id)
        providers.append(
            {
                "id": provider_id,
                "label": metadata.get("label", provider_id),
                "category": metadata.get("category", "external"),
                "description": metadata.get("description", ""),
                "default_base_url": defaults.get("default_base_url"),
                "default_model": defaults.get("default_model"),
                "default_api_version": defaults.get("default_api_version"),
                "supports_catalog_refresh": bool(metadata.get("supports_catalog_refresh")),
                "suggested_models": list(metadata.get("suggested_models") or []),
                "credential_fields": list(metadata.get("credential_fields") or []),
            }
        )
    providers.sort(key=lambda item: (0 if item["id"] == "ollama" else 1, item["label"]))
    return {
        "configured_provider": BASE_SETTINGS.llm_provider,
        "configured_model_name": BASE_SETTINGS.effective_model_name,
        "configured_base_url": BASE_SETTINGS.effective_llm_base_url,
        "providers": providers,
    }


def _llm_health_snapshot(settings: Settings) -> dict[str, Any]:
    client = ModelClient(settings)
    base_payload: dict[str, Any] = {
        "provider": settings.llm_provider,
        "model": settings.effective_model_name,
        "base_url": settings.effective_llm_base_url,
        "api_key_configured": bool(settings.llm_api_key) if settings.llm_provider != "ollama" else None,
    }

    if settings.llm_provider != "ollama":
        configured = client.ping()
        return {
            **base_payload,
            "status": "ok" if configured else "error",
            "ready": configured,
            "mode": "configuration",
            "detail": None if configured else "Hosted provider configuration is incomplete.",
        }

    reachable = client.ping()
    detail: str | None = None
    loaded_model_count = 0
    configured_model_loaded = False
    if reachable:
        try:
            with httpx.Client(timeout=5.0) as http_client:
                response = http_client.get(f"{settings.ollama_base_url}/api/ps")
                response.raise_for_status()
                models = response.json().get("models", [])
                loaded_names = {model.get("name") or model.get("model") for model in models}
                loaded_model_count = len(models)
                configured_model_loaded = settings.local_model_name in loaded_names
        except Exception as error:  # noqa: BLE001
            detail = f"Ollama model inventory could not be inspected: {error}"
    else:
        detail = "Ollama API is unreachable or misconfigured."

    return {
        **base_payload,
        "status": "ok" if reachable else "error",
        "ready": reachable,
        "mode": "connectivity",
        "detail": detail,
        "loaded_model_count": loaded_model_count,
        "configured_model_loaded": configured_model_loaded if reachable else False,
    }


def _database_health_snapshot(settings: Settings) -> dict[str, Any]:
    if not settings.database_enabled:
        return {
            "status": "disabled",
            "ready": True,
            "configured": False,
            "detail": "Historical storage is disabled by configuration.",
        }
    if HISTORY_STORE.enabled:
        return {
            "status": "ok",
            "ready": True,
            "configured": True,
            "detail": None,
            "database_url_present": bool(settings.database_url),
        }
    return {
        "status": "error",
        "ready": False,
        "configured": True,
        "detail": HISTORY_STORE.error or "Historical storage failed to initialize.",
        "database_url_present": bool(settings.database_url),
    }


def _site_health_snapshot() -> dict[str, Any]:
    return {
        "status": "ok" if SITE_DIR is not None else "warning",
        "ready": True,
        "generated_docs_available": SITE_DIR is not None,
        "legacy_docs_available": LEGACY_SITE_DIR is not None,
        "site_dir": str(SITE_DIR) if SITE_DIR is not None else None,
    }


def _build_health_snapshot(settings: Settings) -> dict[str, Any]:
    llm = _llm_health_snapshot(settings)
    database = _database_health_snapshot(settings)
    site = _site_health_snapshot()
    ready = bool(llm["ready"] and database["ready"])
    return {
        "status": "ready" if ready else "degraded",
        "ready": ready,
        "version": "v0.3.0",
        "runtime": {
            "llm_provider": settings.llm_provider,
            "effective_model_name": settings.effective_model_name,
            "cluster_scope": settings.cluster_scope,
            "prompt_template": settings.prompt_template,
            "auth_enabled": settings.auth_enabled,
            "prometheus_enabled": settings.enable_prometheus,
        },
        "checks": {
            "llm": llm,
            "database": database,
            "site": site,
        },
    }


def _redirect_site_page(target: str) -> RedirectResponse:
    """Redirect a friendly HTML alias to the generated guide site."""

    if SITE_DIR is not None:
        return RedirectResponse(url=target)
    raise HTTPException(status_code=404, detail="Documentation site is not available")


@app.api_route("/", methods=["GET", "HEAD"], include_in_schema=False, response_model=None)
def root():
    if LEGACY_SITE_DIR is not None:
        return RedirectResponse(url="/index.html")
    if SITE_DIR is not None:
        return RedirectResponse(url="/guide/")
    return {
        "name": "OpenShift SRE Local Agent",
        "status": "ok",
        "endpoints": {
            "health": "/health",
            "chat": "/chat",
            "history_overview": "/history/overview",
            "openapi_docs": "/docs",
        },
    }


@app.api_route("/console.html", methods=["GET", "HEAD"], include_in_schema=False, response_model=None)
@app.api_route("/docs/console.html", methods=["GET", "HEAD"], include_in_schema=False, response_model=None)
def console_page():
    return _redirect_site_page("/guide/console.html")


@app.api_route("/security-console.html", methods=["GET", "HEAD"], include_in_schema=False, response_model=None)
@app.api_route("/security-console/", methods=["GET", "HEAD"], include_in_schema=False, response_model=None)
@app.api_route("/docs/security-console.html", methods=["GET", "HEAD"], include_in_schema=False, response_model=None)
def security_console_page():
    return _redirect_site_page("/guide/security-console.html")


@app.api_route("/troubleshooting.html", methods=["GET", "HEAD"], include_in_schema=False, response_model=None)
@app.api_route("/docs/troubleshooting.html", methods=["GET", "HEAD"], include_in_schema=False, response_model=None)
def troubleshooting_page():
    return _redirect_site_page("/guide/troubleshooting.html")


@app.api_route("/llm-utilization.html", methods=["GET", "HEAD"], include_in_schema=False, response_model=None)
@app.api_route("/docs/llm-utilization.html", methods=["GET", "HEAD"], include_in_schema=False, response_model=None)
def llm_utilization_page():
    return _redirect_site_page("/guide/llm-utilization.html")


@app.api_route("/history.html", methods=["GET", "HEAD"], include_in_schema=False, response_model=None)
@app.api_route("/docs/history.html", methods=["GET", "HEAD"], include_in_schema=False, response_model=None)
def history_page():
    return _redirect_site_page("/guide/history.html")


@app.api_route("/docs-home", methods=["GET", "HEAD"], include_in_schema=False, response_model=None)
@app.api_route("/docs-home/", methods=["GET", "HEAD"], include_in_schema=False, response_model=None)
def docs_home_page():
    if LEGACY_SITE_DIR is not None:
        return RedirectResponse(url="/docs-home/index.html")
    raise HTTPException(status_code=404, detail="Legacy documentation site is not available")


@app.api_route("/tool-drilldown.html", methods=["GET", "HEAD"], include_in_schema=False, response_model=None)
@app.api_route("/docs/tool-drilldown.html", methods=["GET", "HEAD"], include_in_schema=False, response_model=None)
def tool_drilldown_page():
    return _redirect_site_page("/guide/tool-drilldown.html")


@app.api_route("/finops-console.html", methods=["GET", "HEAD"], include_in_schema=False, response_model=None)
@app.api_route("/finops-console/", methods=["GET", "HEAD"], include_in_schema=False, response_model=None)
@app.api_route("/docs/finops-console.html", methods=["GET", "HEAD"], include_in_schema=False, response_model=None)
def finops_console_page():
    return _redirect_site_page("/guide/finops-console.html")


@app.api_route("/platform-console.html", methods=["GET", "HEAD"], include_in_schema=False, response_model=None)
@app.api_route("/platform-console/", methods=["GET", "HEAD"], include_in_schema=False, response_model=None)
@app.api_route("/docs/platform-console.html", methods=["GET", "HEAD"], include_in_schema=False, response_model=None)
def platform_console_page():
    return _redirect_site_page("/guide/platform-console.html")


@app.api_route("/posture-radar.html", methods=["GET", "HEAD"], include_in_schema=False, response_model=None)
@app.api_route("/docs/posture-radar.html", methods=["GET", "HEAD"], include_in_schema=False, response_model=None)
def posture_radar_page():
    return _redirect_site_page("/guide/posture-radar.html")


@app.api_route("/watchlists.html", methods=["GET", "HEAD"], include_in_schema=False, response_model=None)
@app.api_route("/docs/watchlists.html", methods=["GET", "HEAD"], include_in_schema=False, response_model=None)
def watchlists_page():
    return _redirect_site_page("/guide/watchlists.html")


@app.api_route("/drift-diff.html", methods=["GET", "HEAD"], include_in_schema=False, response_model=None)
@app.api_route("/docs/drift-diff.html", methods=["GET", "HEAD"], include_in_schema=False, response_model=None)
def drift_diff_page():
    return _redirect_site_page("/guide/drift-diff.html")


@app.get("/health")
def health() -> dict[str, str]:
    """Return a lightweight versioned health payload for basic probes."""

    return {"status": "ok", "version": "v0.3.0"}


@app.get("/healthz")
def healthz() -> dict[str, str]:
    """Liveness probe — always returns ok if the process is running."""
    return {"status": "ok", "version": "v0.3.0"}


@app.get("/healthz/full")
def full_healthz() -> dict[str, Any]:
    """Detailed subsystem health payload for operators and dashboards."""

    return _build_health_snapshot(BASE_SETTINGS)


@app.get("/readyz")
def readyz() -> dict:
    """Readiness probe — validates the configured LLM path and optional persistence layer."""

    snapshot = _build_health_snapshot(BASE_SETTINGS)
    if not snapshot["ready"]:
        raise HTTPException(status_code=503, detail=snapshot)
    return snapshot


@app.post("/settings/refresh")
def refresh_settings() -> dict[str, str]:
    """Reload settings from environment variables without a restart (secrets rotation)."""
    global BASE_SETTINGS, HISTORY_STORE
    try:
        BASE_SETTINGS = Settings.load()
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    HISTORY_STORE = HistoryStore(BASE_SETTINGS)
    logger.info("Settings refreshed from environment")
    return {"status": "refreshed"}


@app.websocket("/ws/events")
async def ws_events(websocket: WebSocket) -> None:
    """WebSocket endpoint for live run-completion events."""
    await websocket.accept()
    _ws_clients.add(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        _ws_clients.discard(websocket)


@app.get("/ollama/utilization")
def ollama_utilization() -> dict:
    """Return local Ollama utilization and host-visibility details."""

    return _get_ollama_utilization_snapshot(BASE_SETTINGS)


@app.get("/ollama/models")
def ollama_models(ollama_base_url: str | None = Query(default=None)) -> dict:
    """Return the local Ollama model catalog for UI dropdown refresh actions."""

    settings = BASE_SETTINGS.with_overrides(ollama_base_url=ollama_base_url)
    return _get_ollama_models_catalog(settings)


@app.get("/llm/providers")
def llm_providers() -> dict:
    """Return the configured provider catalog including UI credential metadata."""

    return _get_llm_provider_catalog()


@app.get("/runtime/observability")
def runtime_observability() -> dict:
    """Return container and database telemetry used by the main console observability panel."""

    return _get_runtime_observability_snapshot()


@app.get("/history/overview")
def history_overview(
    time_range: str = Query(default="all", pattern="^(24h|7d|30d|90d|all)$"),
    model_names: str | None = Query(default=None),
    model_name: str | None = Query(default=None, max_length=255),
    cluster_scopes: str | None = Query(default=None),
    cluster_scope: str | None = Query(default=None, max_length=64),
    tool_names: str | None = Query(default=None),
    run_limit: int = Query(default=100, ge=1, le=500),
    run_offset: int = Query(default=0, ge=0, description="Pagination offset for recent_runs."),
    point_limit: int = Query(default=24, ge=1, le=120),
    series_limit: int = Query(default=12, ge=1, le=50),
) -> dict:
    parsed_model_names = _parse_csv_query(model_names) or _parse_csv_query(model_name)
    parsed_regions = _parse_csv_query(cluster_scopes) or _parse_csv_query(cluster_scope)
    parsed_tool_names = _parse_csv_query(tool_names)
    return HISTORY_STORE.get_overview(
        time_range=time_range,
        model_names=parsed_model_names,
        cluster_scopes=parsed_regions,
        tool_names=parsed_tool_names,
        run_limit=run_limit,
        point_limit=point_limit,
        series_limit=series_limit,
    )


@app.get("/history/runs/{run_id}")
def history_run_detail(run_id: int) -> dict:
    detail = HISTORY_STORE.get_run_detail(run_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="Run not found")
    return detail


@app.get("/history/tools/{tool_name}")
def history_tool_detail(
    tool_name: str,
    time_range: str = Query(default="all", pattern="^(24h|7d|30d|90d|all)$"),
    model_names: str | None = Query(default=None),
    model_name: str | None = Query(default=None, max_length=255),
    cluster_scopes: str | None = Query(default=None),
    cluster_scope: str | None = Query(default=None, max_length=64),
    run_limit: int = Query(default=25, ge=1, le=100),
    point_limit: int = Query(default=24, ge=1, le=120),
) -> dict:
    detail = HISTORY_STORE.get_tool_detail(
        tool_name,
        time_range=time_range,
        model_names=_parse_csv_query(model_names) or _parse_csv_query(model_name),
        cluster_scopes=_parse_csv_query(cluster_scopes) or _parse_csv_query(cluster_scope),
        run_limit=run_limit,
        point_limit=point_limit,
    )
    if detail is None:
        raise HTTPException(status_code=404, detail="Tool history not found")
    return detail


@app.get("/history/metrics/{metric_key:path}")
def history_metric_detail(
    metric_key: str,
    time_range: str = Query(default="all", pattern="^(24h|7d|30d|90d|all)$"),
    model_names: str | None = Query(default=None),
    model_name: str | None = Query(default=None, max_length=255),
    cluster_scopes: str | None = Query(default=None),
    cluster_scope: str | None = Query(default=None, max_length=64),
    record_limit: int = Query(default=40, ge=1, le=200),
) -> dict:
    detail = HISTORY_STORE.get_metric_detail(
        metric_key,
        time_range=time_range,
        model_names=_parse_csv_query(model_names) or _parse_csv_query(model_name),
        cluster_scopes=_parse_csv_query(cluster_scopes) or _parse_csv_query(cluster_scope),
        record_limit=record_limit,
    )
    if detail is None:
        raise HTTPException(status_code=404, detail="Metric history not found")
    return detail


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    """Run one prompt through the agent with optional runtime overrides."""

    if _shutting_down:
        raise HTTPException(status_code=503, detail="Server is shutting down.")
    if detect_prompt_injection(request.prompt):
        raise HTTPException(status_code=400, detail="Prompt rejected: potential injection detected.")
    response, _, _ = _execute_agent_prompt(
        prompt=request.prompt,
        runtime=request.runtime,
        conversation_id=request.conversation_id,
        tags=request.tags,
    )
    return response


@app.post("/security/audit", response_model=ChatResponse)
def security_audit(request: SecurityAuditRequest) -> ChatResponse:
    """Run a batched security audit for selected controls without a slow multi-turn agent loop."""

    if _shutting_down:
        raise HTTPException(status_code=503, detail="Server is shutting down.")

    response, _, _ = _run_batched_security_audit(request)
    return response


@app.post("/chat/stream")
def chat_stream(request: ChatRequest) -> StreamingResponse:
    """SSE endpoint that streams each reasoning step as it completes."""
    settings = _runtime_settings(request.runtime)

    async def _generate() -> AsyncGenerator[str, None]:
        started_at = perf_counter()
        try:
            agent = OpenShiftSreAgent(settings)
            if request.conversation_id:
                agent.set_conversation_context(
                    HISTORY_STORE.get_conversation_turns(request.conversation_id, limit=5)
                )
            result = agent.ask(request.prompt)
            for i, step in enumerate(result.steps):
                yield f"data: {json.dumps({'type': 'step', 'index': i, 'step': step}, default=str)}\n\n"
            duration_ms = int((perf_counter() - started_at) * 1000)
            run_id = HISTORY_STORE.record_chat(
                prompt=request.prompt,
                answer=result.answer,
                steps=result.steps,
                model_name=settings.effective_model_name,
                cluster_scope=settings.cluster_scope,
                duration_ms=duration_ms,
                conversation_id=request.conversation_id,
            )
            yield f"data: {json.dumps({'type': 'done', 'answer': result.answer, 'run_id': run_id, 'confidence': result.confidence, 'duration_ms': duration_ms}, default=str)}\n\n"
        except Exception as error:  # noqa: BLE001
            yield f"data: {json.dumps({'type': 'error', 'detail': str(error)}, default=str)}\n\n"

    return StreamingResponse(_generate(), media_type="text/event-stream")


@app.get("/finops/queue")
def finops_queue() -> dict:
    return HISTORY_STORE.list_finops_queue()


@app.post("/finops/queue")
def create_finops_queue_item(request: FinopsQueueCreateRequest) -> dict:
    if not HISTORY_STORE.enabled:
        raise HTTPException(status_code=503, detail=HISTORY_STORE.error or "Historical storage is not configured.")
    try:
        item = HISTORY_STORE.create_finops_queue_item(**request.model_dump())
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    if item is None:
        raise HTTPException(status_code=503, detail=HISTORY_STORE.error or "Historical storage is not configured.")
    return item


@app.patch("/finops/queue/{item_id}")
def update_finops_queue_item(item_id: int, request: FinopsQueueStageUpdateRequest) -> dict:
    if not HISTORY_STORE.enabled:
        raise HTTPException(status_code=503, detail=HISTORY_STORE.error or "Historical storage is not configured.")
    try:
        item = HISTORY_STORE.update_finops_queue_item_stage(item_id, request.execution_stage)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    if item is None:
        raise HTTPException(status_code=404, detail="FinOps queue item not found")
    return item


@app.delete("/finops/queue/{item_id}")
def delete_finops_queue_item(item_id: int) -> dict[str, bool]:
    if not HISTORY_STORE.enabled:
        raise HTTPException(status_code=503, detail=HISTORY_STORE.error or "Historical storage is not configured.")
    deleted = HISTORY_STORE.delete_finops_queue_item(item_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="FinOps queue item not found")
    return {"deleted": True}


# ---------------------------------------------------------------------------
# v0.3.0 new endpoints
# ---------------------------------------------------------------------------


@app.get("/history/export")
def history_export(
    time_range: str = Query(default="all", pattern="^(24h|7d|30d|90d|all)$"),
    limit: int = Query(default=500, ge=1, le=5000),
) -> PlainTextResponse:
    """Export run history as CSV for offline analysis."""
    csv_data = HISTORY_STORE.export_runs_csv(time_range=time_range, limit=limit)
    return PlainTextResponse(
        csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=agent-history.csv"},
    )


class TagRequest(BaseModel):
    tags: list[str] = Field(min_length=1, max_length=10)


@app.post("/history/runs/{run_id}/tags")
def tag_run(run_id: int, request: TagRequest) -> dict:
    """Add tags to a historical run."""
    if not HISTORY_STORE.enabled:
        raise HTTPException(status_code=503, detail=HISTORY_STORE.error or "Historical storage is not configured.")
    result = HISTORY_STORE.tag_run(run_id, request.tags)
    if result is None:
        raise HTTPException(status_code=404, detail="Run not found")
    return result


@app.delete("/history/runs/{run_id}")
def delete_run(run_id: int) -> dict[str, bool]:
    """Delete a historical run and its associated steps/metrics."""
    if not HISTORY_STORE.enabled:
        raise HTTPException(status_code=503, detail=HISTORY_STORE.error or "Historical storage is not configured.")
    deleted = HISTORY_STORE.delete_run(run_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Run not found")
    return {"deleted": True}


@app.get("/history/compare")
def history_compare(left_run_id: int = Query(ge=1), right_run_id: int = Query(ge=1)) -> dict:
    detail = HISTORY_STORE.compare_runs(left_run_id, right_run_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="One or both runs were not found")
    return detail


@app.get("/investigations")
def list_saved_investigations() -> dict:
    return HISTORY_STORE.list_saved_investigations()


@app.post("/investigations")
def create_saved_investigation(request: SavedInvestigationCreateRequest) -> dict:
    if not HISTORY_STORE.enabled:
        raise HTTPException(status_code=503, detail=HISTORY_STORE.error or "Historical storage is not configured.")
    created = HISTORY_STORE.create_saved_investigation(**request.model_dump())
    if created is None:
        raise HTTPException(status_code=503, detail=HISTORY_STORE.error or "Historical storage is not configured.")
    return created


@app.patch("/investigations/{investigation_id}")
def update_saved_investigation(investigation_id: int, request: SavedInvestigationUpdateRequest) -> dict:
    if not HISTORY_STORE.enabled:
        raise HTTPException(status_code=503, detail=HISTORY_STORE.error or "Historical storage is not configured.")
    updated = HISTORY_STORE.update_saved_investigation(investigation_id, **request.model_dump(exclude_unset=True))
    if updated is None:
        raise HTTPException(status_code=404, detail="Saved investigation not found")
    return updated


@app.delete("/investigations/{investigation_id}")
def delete_saved_investigation(investigation_id: int) -> dict[str, bool]:
    if not HISTORY_STORE.enabled:
        raise HTTPException(status_code=503, detail=HISTORY_STORE.error or "Historical storage is not configured.")
    deleted = HISTORY_STORE.delete_saved_investigation(investigation_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Saved investigation not found")
    return {"deleted": True}


@app.get("/watchlists")
def list_watchlists() -> dict:
    return HISTORY_STORE.list_watchlists()


@app.post("/watchlists")
def create_watchlist(request: WatchlistCreateRequest) -> dict:
    if not HISTORY_STORE.enabled:
        raise HTTPException(status_code=503, detail=HISTORY_STORE.error or "Historical storage is not configured.")
    try:
        created = HISTORY_STORE.create_watchlist(**request.model_dump())
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    if created is None:
        raise HTTPException(status_code=503, detail=HISTORY_STORE.error or "Historical storage is not configured.")
    return created


@app.patch("/watchlists/{watchlist_id}")
def update_watchlist(watchlist_id: int, request: WatchlistUpdateRequest) -> dict:
    if not HISTORY_STORE.enabled:
        raise HTTPException(status_code=503, detail=HISTORY_STORE.error or "Historical storage is not configured.")
    try:
        updated = HISTORY_STORE.update_watchlist(watchlist_id, **request.model_dump(exclude_unset=True))
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    if updated is None:
        raise HTTPException(status_code=404, detail="Watchlist not found")
    return updated


@app.delete("/watchlists/{watchlist_id}")
def delete_watchlist(watchlist_id: int) -> dict[str, bool]:
    if not HISTORY_STORE.enabled:
        raise HTTPException(status_code=503, detail=HISTORY_STORE.error or "Historical storage is not configured.")
    deleted = HISTORY_STORE.delete_watchlist(watchlist_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Watchlist not found")
    return {"deleted": True}


@app.post("/watchlists/{watchlist_id}/run")
def run_watchlist(watchlist_id: int, request: WatchlistRunRequest) -> dict:
    if not HISTORY_STORE.enabled:
        raise HTTPException(status_code=503, detail=HISTORY_STORE.error or "Historical storage is not configured.")
    watchlist = HISTORY_STORE.get_watchlist(watchlist_id)
    if watchlist is None:
        raise HTTPException(status_code=404, detail="Watchlist not found")
    investigation = watchlist.get("investigation")
    if not investigation:
        raise HTTPException(status_code=400, detail="Watchlist is missing a saved investigation")

    base_runtime = request.runtime or RuntimeConfig()
    regions = watchlist.get("regions") or investigation.get("default_regions") or _parse_csv_query(BASE_SETTINGS.cluster_scopes) or [BASE_SETTINGS.cluster_scope]
    role_arns = watchlist.get("role_arns") or [base_runtime.reserved_role_arn or BASE_SETTINGS.reserved_role_arn or None]
    tags = list(dict.fromkeys((watchlist.get("tags") or []) + (investigation.get("default_tags") or [])))
    results = []
    for region in regions:
        for role_arn in role_arns:
            runtime = base_runtime.model_copy(update={"cluster_scope": region, "reserved_role_arn": role_arn})
            response, _, _ = _execute_agent_prompt(prompt=investigation.get("prompt", ""), runtime=runtime, tags=tags)
            results.append(
                {
                    "region": region,
                    "role_arn": role_arn,
                    "run_id": response.run_id,
                    "answer": response.answer,
                    "confidence": response.confidence,
                    "tags": response.tags,
                }
            )
    last_run_id = results[-1]["run_id"] if results else None
    updated_watchlist = HISTORY_STORE.touch_watchlist_run(watchlist_id, last_run_id)
    return {"watchlist": updated_watchlist, "results": results, "count": len(results)}


@app.post("/platform/sweep")
def platform_sweep(request: PlatformSweepRequest) -> dict:
    settings = _runtime_settings(request.runtime)
    regions = request.regions or _parse_csv_query(settings.cluster_scopes) or [settings.cluster_scope]
    role_arns = request.role_arns or [settings.reserved_role_arn or None]

    results = []
    for region in regions:
        for role_arn in role_arns:
            scoped_settings = settings.with_overrides(cluster_scope=region, reserved_role_arn=role_arn)
            toolkit = OpenShiftSreToolkit(scoped_settings)
            invalid_tools = [tool_name for tool_name in request.tool_names if tool_name not in toolkit.tools]
            if invalid_tools:
                raise HTTPException(status_code=400, detail=f"Unsupported tools requested: {', '.join(invalid_tools)}")
            caller_identity = toolkit.get_caller_identity()
            tool_results: dict[str, dict] = {}
            for tool_name in request.tool_names:
                try:
                    tool_results[tool_name] = toolkit.invoke(tool_name, {})
                except Exception as error:  # noqa: BLE001
                    tool_results[tool_name] = {"error": str(error)}
            results.append(
                {
                    "region": region,
                    "role_arn": role_arn,
                    "caller_identity": caller_identity,
                    "tool_results": tool_results,
                }
            )
    return {"count": len(results), "results": results}


class BatchChatRequest(BaseModel):
    prompts: list[str] = Field(min_length=1, max_length=10, description="List of prompts to run sequentially.")
    runtime: RuntimeConfig | None = None
    conversation_id: str | None = None
    tags: list[str] | None = None


@app.post("/chat/batch")
def chat_batch(request: BatchChatRequest) -> dict:
    """Run multiple prompts sequentially and return all results."""
    results = []
    for prompt in request.prompts:
        if detect_prompt_injection(prompt):
            results.append({"prompt": prompt[:120], "error": "Prompt rejected: potential injection detected."})
            continue
        sub_request = ChatRequest(
            prompt=prompt,
            runtime=request.runtime,
            conversation_id=request.conversation_id,
            tags=request.tags,
        )
        try:
            response = chat(sub_request)
            results.append({
                "prompt": prompt[:120],
                "answer": response.answer,
                "run_id": response.run_id,
                "confidence": response.confidence,
                "token_usage": response.token_usage,
            })
        except HTTPException as exc:
            results.append({"prompt": prompt[:120], "error": exc.detail})
    return {"results": results, "count": len(results)}


@app.get("/prompts/templates")
def list_prompt_templates() -> dict:
    """List available prompt templates."""
    from .prompts import PROMPT_TEMPLATES
    return {
        "templates": list(PROMPT_TEMPLATES.keys()),
        "template_details": [
            {"name": name, "excerpt": template[:200].strip()}
            for name, template in PROMPT_TEMPLATES.items()
        ],
        "current": BASE_SETTINGS.prompt_template,
    }


@app.get("/metrics")
def prometheus_metrics() -> PlainTextResponse:
    """Prometheus-compatible /metrics endpoint with key counters and gauges."""
    lines: list[str] = []
    if HISTORY_STORE.enabled:
        overview = HISTORY_STORE.get_overview(time_range="24h", run_limit=1, point_limit=1, series_limit=1)
        summary = overview.get("summary", {})
        lines.append(f'# HELP agent_runs_total Total agent runs in the last 24h')
        lines.append(f'# TYPE agent_runs_total gauge')
        lines.append(f'agent_runs_total {summary.get("total_runs", 0)}')
        lines.append(f'# HELP agent_runs_failed Failed agent runs in the last 24h')
        lines.append(f'# TYPE agent_runs_failed gauge')
        lines.append(f'agent_runs_failed {summary.get("failed_runs", 0)}')
        avg_dur = summary.get("average_duration_ms")
        lines.append(f'# HELP agent_avg_duration_ms Average run duration in ms')
        lines.append(f'# TYPE agent_avg_duration_ms gauge')
        lines.append(f'agent_avg_duration_ms {avg_dur if avg_dur is not None else 0}')
    else:
        lines.append('# HELP agent_database_enabled Whether history storage is active')
        lines.append('# TYPE agent_database_enabled gauge')
        lines.append('agent_database_enabled 0')
    lines.append(f'# HELP agent_info Agent version info')
    lines.append(f'# TYPE agent_info gauge')
    lines.append(f'agent_info{{version="0.3.0"}} 1')
    return PlainTextResponse("\n".join(lines) + "\n", media_type="text/plain; version=0.0.4; charset=utf-8")


@app.post("/admin/retention")
def enforce_retention(days: int = Query(default=None, ge=1, le=3650)) -> dict:
    """Manually trigger data retention enforcement."""
    retention_days = days or BASE_SETTINGS.data_retention_days
    purged = HISTORY_STORE.enforce_retention(retention_days)
    return {"purged_runs": purged, "retention_days": retention_days}


if LEGACY_SITE_DIR is not None:
    app.mount("/docs-home", StaticFiles(directory=LEGACY_SITE_DIR, html=True), name="legacy-docs-home")
    app.mount("/", StaticFiles(directory=LEGACY_SITE_DIR, html=True), name="legacy-site")
