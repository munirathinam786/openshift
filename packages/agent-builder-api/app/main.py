from __future__ import annotations

import os
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from fastapi import FastAPI
from pydantic import BaseModel, Field


class AgentDefinition(BaseModel):
    name: str
    description: str
    model: str = "gpt-4.1"
    tools: list[str] = Field(default_factory=list)


class WorkflowRequest(BaseModel):
    name: str
    goal: str
    agent: str
    context: dict[str, Any] = Field(default_factory=dict)


app = FastAPI(title="Agent Builder API", version="1.0.0")

SETTINGS = {
    "litellm_proxy_base": os.getenv("LITELLM_PROXY_BASE", "http://litellm:4000"),
    "temporal_host": os.getenv("TEMPORAL_HOST", "temporal:7233"),
    "temporal_namespace": os.getenv("TEMPORAL_NAMESPACE", "agent-builder"),
    "temporal_task_queue": os.getenv("TEMPORAL_TASK_QUEUE", "workflow-builder-queue"),
    "mongodb_database": os.getenv("MONGODB_DATABASE", "workflowagent"),
    "oidc_authority": os.getenv("OIDC_AUTHORITY", ""),
    "oidc_client_id": os.getenv("OIDC_CLIENT_ID", ""),
    "k8s_namespace": os.getenv("K8S_NAMESPACE", "agent-builder"),
}

AGENTS: dict[str, AgentDefinition] = {
    "research-assistant": AgentDefinition(
        name="research-assistant",
        description="Summarizes technical docs and repo context.",
        model="gpt-4.1",
        tools=["search", "summarize", "fetch"],
    ),
    "deployment-agent": AgentDefinition(
        name="deployment-agent",
        description="Creates deployment plans and environment manifests.",
        model="gpt-4.1-mini",
        tools=["terraform", "kubernetes", "git"],
    ),
}


@app.get("/health")
def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "service": "agent-builder-api",
        "timestamp": datetime.now(UTC).isoformat(),
        "settings": SETTINGS,
        "registered_agents": len(AGENTS),
    }


@app.get("/")
def root() -> dict[str, Any]:
    return {
        "message": "Agent Builder API is running",
        "docs": "/docs",
        "health": "/health",
    }


@app.get("/agents")
def list_agents() -> list[AgentDefinition]:
    return list(AGENTS.values())


@app.post("/agents")
def create_agent(agent: AgentDefinition) -> dict[str, Any]:
    AGENTS[agent.name] = agent
    return {"status": "created", "agent": agent}


@app.get("/tools")
def list_tools() -> list[dict[str, str]]:
    return [
        {"name": "search", "category": "discovery"},
        {"name": "fetch", "category": "integration"},
        {"name": "terraform", "category": "infrastructure"},
        {"name": "kubernetes", "category": "platform"},
    ]


@app.post("/workflows")
def submit_workflow(request: WorkflowRequest) -> dict[str, Any]:
    workflow_id = f"wf-{uuid4()}"
    return {
        "workflow_id": workflow_id,
        "status": "queued",
        "request": request,
        "temporal": {
            "host": SETTINGS["temporal_host"],
            "namespace": SETTINGS["temporal_namespace"],
            "task_queue": SETTINGS["temporal_task_queue"],
        },
    }
