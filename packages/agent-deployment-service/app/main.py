from __future__ import annotations

import os
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from fastapi import FastAPI
from pydantic import BaseModel, Field

app = FastAPI(title="Agent Deployment Service", version="1.0.0")

DEPLOYMENTS: dict[str, dict[str, Any]] = {}


class DeploymentRequest(BaseModel):
    agent_name: str
    image: str
    replicas: int = 1
    environment: dict[str, str] = Field(default_factory=dict)


@app.get("/health")
def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "service": "agent-deployment-service",
        "temporal_host": os.getenv("TEMPORAL_HOST", "temporal:7233"),
        "namespace": os.getenv("K8S_NAMESPACE", "agent-builder"),
        "timestamp": datetime.now(UTC).isoformat(),
    }


@app.get("/deployments")
def list_deployments() -> list[dict[str, Any]]:
    return list(DEPLOYMENTS.values())


@app.post("/deployments")
def create_deployment(request: DeploymentRequest) -> dict[str, Any]:
    deployment_id = f"deploy-{uuid4()}"
    deployment = {
        "id": deployment_id,
        "status": "accepted",
        "created_at": datetime.now(UTC).isoformat(),
        **request.model_dump(),
    }
    DEPLOYMENTS[deployment_id] = deployment
    return deployment
