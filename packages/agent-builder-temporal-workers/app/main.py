from __future__ import annotations

import asyncio
import os
from datetime import UTC, datetime
from typing import Any

from fastapi import FastAPI

app = FastAPI(title="Agent Builder Temporal Workers", version="1.0.0")

STATE: dict[str, Any] = {
    "last_heartbeat": None,
    "started_at": datetime.now(UTC).isoformat(),
}

SETTINGS = {
    "temporal_host": os.getenv("TEMPORAL_HOST", "temporal:7233"),
    "temporal_namespace": os.getenv("TEMPORAL_NAMESPACE", "agent-builder"),
    "temporal_task_queue": os.getenv("TEMPORAL_TASK_QUEUE", "workflow-builder-queue"),
    "mongodb_database": os.getenv("MONGODB_DATABASE", "workflow_builder"),
    "max_concurrent_workflow_tasks": os.getenv("MAX_CONCURRENT_WORKFLOW_TASKS", "100"),
    "max_concurrent_activities": os.getenv("MAX_CONCURRENT_ACTIVITIES", "100"),
}


async def heartbeat_loop() -> None:
    while True:
        STATE["last_heartbeat"] = datetime.now(UTC).isoformat()
        await asyncio.sleep(5)


@app.on_event("startup")
async def startup() -> None:
    asyncio.create_task(heartbeat_loop())


@app.get("/health")
def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "service": "agent-builder-temporal-workers",
        "state": STATE,
        "settings": SETTINGS,
    }


@app.get("/queues")
def queues() -> dict[str, Any]:
    return {
        "default_queue": SETTINGS["temporal_task_queue"],
        "available_workers": 1,
        "mode": "lightweight-simulated-worker",
    }
