from __future__ import annotations

import os
from datetime import UTC, datetime
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

app = FastAPI(title="Agent Registry", version="1.0.0")


class RegisteredAgent(BaseModel):
    name: str
    description: str
    version: str = "0.1.0"
    tags: list[str] = Field(default_factory=list)


REGISTRY: dict[str, RegisteredAgent] = {
    "research-assistant": RegisteredAgent(
        name="research-assistant",
        description="Summarizes repositories and docs.",
        tags=["analysis", "docs"],
    ),
    "deployment-agent": RegisteredAgent(
        name="deployment-agent",
        description="Builds deployment plans and manifests.",
        tags=["terraform", "kubernetes"],
    ),
}


@app.get("/health")
def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "service": "agent-registry",
        "database_url_present": bool(os.getenv("DATABASE_URL")),
        "mongodb_uri_present": bool(os.getenv("MONGODB_URI")),
        "registered_agents": len(REGISTRY),
        "timestamp": datetime.now(UTC).isoformat(),
    }


@app.get("/agents")
def list_agents() -> list[RegisteredAgent]:
    return list(REGISTRY.values())


@app.get("/agents/{name}")
def get_agent(name: str) -> RegisteredAgent:
    if name not in REGISTRY:
        raise HTTPException(status_code=404, detail="Agent not found")
    return REGISTRY[name]


@app.post("/agents")
def register_agent(agent: RegisteredAgent) -> RegisteredAgent:
    REGISTRY[agent.name] = agent
    return agent
