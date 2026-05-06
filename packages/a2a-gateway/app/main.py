from __future__ import annotations

import os
from datetime import UTC, datetime
from typing import Any

import httpx
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="A2A Gateway", version="1.0.0")
REGISTRY_URL = os.getenv("AGENT_REGISTRY_URL", "http://agent-builder-registry:8002")


class AgentMessage(BaseModel):
    sender: str
    recipient: str
    payload: dict[str, Any]


@app.get("/health")
def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "service": "a2a-gateway",
        "registry_url": REGISTRY_URL,
        "timestamp": datetime.now(UTC).isoformat(),
    }


@app.get("/discover")
async def discover() -> dict[str, Any]:
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            response = await client.get(f"{REGISTRY_URL}/agents")
            response.raise_for_status()
            items = response.json()
    except Exception:
        items = [{"name": "fallback-agent", "description": "Registry unavailable fallback"}]
    return {"agents": items, "count": len(items)}


@app.post("/message")
def route_message(message: AgentMessage) -> dict[str, Any]:
    return {
        "status": "accepted",
        "routed_to": message.recipient,
        "sender": message.sender,
        "payload": message.payload,
    }
