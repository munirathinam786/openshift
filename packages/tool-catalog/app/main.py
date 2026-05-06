from __future__ import annotations

import os
from datetime import UTC, datetime
from typing import Any

from fastapi import FastAPI, HTTPException

app = FastAPI(title="Tool Catalog", version="1.0.0")

TOOLS: list[dict[str, Any]] = [
    {"id": "search", "name": "Workspace Search", "category": "discovery", "protocol": "mcp"},
    {"id": "terraform", "name": "Terraform Runner", "category": "infrastructure", "protocol": "mcp"},
    {"id": "kubernetes", "name": "Kubernetes Actions", "category": "platform", "protocol": "mcp"},
    {"id": "git", "name": "Git Workflow", "category": "source-control", "protocol": "mcp"},
]


@app.get("/tools-server/health")
def health() -> dict[str, str]:
    return {
        "status": "ok",
        "service": "tool-catalog",
        "namespace": os.getenv("KUBERNETES_NAMESPACE", "agent-builder"),
        "timestamp": datetime.now(UTC).isoformat(),
    }


@app.get("/tools-server/tools")
def list_tools() -> dict[str, Any]:
    return {"items": TOOLS, "count": len(TOOLS)}


@app.get("/tools-server/tools/{tool_id}")
def get_tool(tool_id: str) -> dict[str, Any]:
    for tool in TOOLS:
        if tool["id"] == tool_id:
            return tool
    raise HTTPException(status_code=404, detail="Tool not found")
