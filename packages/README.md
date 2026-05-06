# Agent Builder application packages

This directory contains the missing buildable application sources referenced by the Agent Builder Azure DevOps pipelines.

Included packages:

- `agent-builder-api` — workflow and agent management API
- `agent-builder-ui` — web UI for the platform
- `agent-builder-temporal-workers` — worker service with health and queue status
- `tool-catalog` — MCP-style tool discovery catalog
- `agent-deployment-service` — deployment orchestration API
- `agent-registry` — agent metadata registry service
- `a2a-gateway` — agent-to-agent gateway facade

These packages are intentionally lightweight but functional so the repository is self-contained for image builds and deployment pipelines.
