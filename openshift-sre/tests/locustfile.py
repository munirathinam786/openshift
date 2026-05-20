"""Locust load test for the OpenShift SRE Local Agent API.

Run with:
    locust -f tests/locustfile.py --host http://127.0.0.1:8000 --headless -u 10 -r 2 -t 60s
"""
from __future__ import annotations

from locust import HttpUser, between, task


class SreAgentUser(HttpUser):
    wait_time = between(1, 3)

    @task(5)
    def health(self) -> None:
        self.client.get("/health")

    @task(3)
    def healthz(self) -> None:
        self.client.get("/healthz")

    @task(2)
    def readyz(self) -> None:
        self.client.get("/readyz")

    @task(3)
    def history_overview(self) -> None:
        self.client.get("/history/overview?time_range=7d&run_limit=10")

    @task(1)
    def ollama_utilization(self) -> None:
        self.client.get("/ollama/utilization")

    @task(1)
    def chat_prompt(self) -> None:
        self.client.post(
            "/chat",
            json={"prompt": "Summarize degraded cluster operators and failing workloads in openshift-monitoring"},
            timeout=120,
        )
