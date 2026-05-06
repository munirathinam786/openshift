# Agent Builder Factory — Application Packages

This page documents the **top-level `packages/` source tree** used by the Agent Builder Day 1 pipelines when `buildImages=true`.

These packages were added so the repository contains **actual runnable application code**, not only Terraform manifests and pipeline YAML. In other words: the platform can now explain itself *and* build itself.

## Why this folder exists

The Terraform modules under `ipi-method/agent-builder/` and `upi-method/agent-builder/` deploy services such as:

- `agent-builder-api`
- `agent-builder-ui`
- `agent-builder-temporal-workers`
- `tool-catalog`
- `agent-deployment-service`
- `agent-registry`
- `a2a-gateway`

The Day 1 Azure DevOps pipelines reference those services as container images. The top-level `packages/` directory now provides the build context for those images so local pipeline builds are reproducible and self-contained.

## Directory layout

```text
packages/
├── README.md
├── agent-builder-api/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── app/main.py
├── agent-builder-ui/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── app/
│       ├── main.py
│       └── templates/index.html
├── agent-builder-temporal-workers/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── app/main.py
├── tool-catalog/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── app/main.py
├── agent-deployment-service/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── app/main.py
├── agent-registry/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── app/main.py
└── a2a-gateway/
    ├── Dockerfile
    ├── requirements.txt
    └── app/main.py
```

## Package responsibilities

| Package | Port | Role | Health endpoint |
|---|---:|---|---|
| `agent-builder-api` | 8000 | Agent, tool, and workflow API | `/health` |
| `agent-builder-ui` | 3000 | Web UI and runtime config surface | `/` |
| `agent-builder-temporal-workers` | 8000 | Worker heartbeat and queue insight | `/health` |
| `tool-catalog` | 8090 | MCP-style tool discovery catalog | `/tools-server/health` |
| `agent-deployment-service` | 8001 | Deployment orchestration API | `/health` |
| `agent-registry` | 8002 | Agent metadata registry | `/health` |
| `a2a-gateway` | 8003 | Agent-to-agent discovery and routing | `/health` |

## Example: `agent-builder-api`

The API service is a FastAPI application that exposes health, agent registration, tool listing, and workflow submission endpoints.

```python
app = FastAPI(title="Agent Builder API", version="1.0.0")

@app.get("/health")
def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "service": "agent-builder-api",
        "timestamp": datetime.now(UTC).isoformat(),
        "settings": SETTINGS,
        "registered_agents": len(AGENTS),
    }

@app.get("/agents")
def list_agents() -> list[AgentDefinition]:
    return list(AGENTS.values())

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
```

### Why it matters

- Matches the Terraform module expectation for port `8000`
- Exposes a reliable `/health` probe for OpenShift readiness/liveness checks
- Demonstrates how the platform wires Temporal and LiteLLM-related settings into the service runtime

## Example: `agent-builder-ui`

The UI package is intentionally lightweight. It serves an HTML front end and exposes runtime configuration from environment variables such as `VITE_API_BASE_URL` and OIDC settings.

```python
app = FastAPI(title="Agent Builder UI", version="1.0.0")
templates = Jinja2Templates(directory="/app/app/templates")

def ui_config() -> dict[str, str]:
    return {
        "apiBaseUrl": os.getenv("VITE_API_BASE_URL", "http://localhost:8000"),
        "appName": os.getenv("VITE_APP_NAME", "Kyndryl Agent Builder"),
        "oidcAuthority": os.getenv("VITE_OIDC_AUTHORITY", ""),
        "oidcClientId": os.getenv("VITE_OIDC_CLIENT_ID", ""),
        "oidcRedirectUri": os.getenv("VITE_OIDC_REDIRECT_URI", ""),
    }

@app.get("/config")
def config() -> JSONResponse:
    return JSONResponse(ui_config())
```

### Why it matters

- Keeps the repo self-contained for image builds
- Uses the same runtime environment variables that the Terraform-deployed service expects
- Provides a simple but real UI artifact instead of a placeholder container

## Example: `tool-catalog`

The Tool Catalog exposes MCP-style tool metadata so the wider Agent Builder platform can discover what capabilities are available.

```python
TOOLS: list[dict[str, Any]] = [
    {"id": "search", "name": "Workspace Search", "category": "discovery", "protocol": "mcp"},
    {"id": "terraform", "name": "Terraform Runner", "category": "infrastructure", "protocol": "mcp"},
    {"id": "kubernetes", "name": "Kubernetes Actions", "category": "platform", "protocol": "mcp"},
    {"id": "git", "name": "Git Workflow", "category": "source-control", "protocol": "mcp"},
]

@app.get("/tools-server/tools")
def list_tools() -> dict[str, Any]:
    return {"items": TOOLS, "count": len(TOOLS)}
```

### Why it matters

- Aligns with the Terraform route and service expectations for port `8090`
- Gives the deployed platform a concrete tool-discovery endpoint
- Makes local and pipeline builds deterministic

## Pipeline integration

When `buildImages=true`, the IPI and UPI Day 1 pipelines:

1. Verify that every required subdirectory exists in `packages/`
2. Build each image with `podman build`
3. Push the images to the configured registry
4. Continue Terraform deployment using the selected `imageTag`

When `buildImages=false`, the build stage is skipped and the deployment assumes the referenced images are already present in the registry.

## Validation performed

The `packages/` tree has been verified by:

- compiling all Python modules successfully
- building all seven service images successfully with Podman

That means these packages are not documentation-only artifacts; they are runnable build inputs for the deployment pipelines.

## Related pages

- [Agent Builder Deployment Guide](terraform-agent-builder.md)
- [Agent Builder Pipeline (Day 1)](../pipeline/terraform-agent-builder-pipeline.md)
- [IPI Day 1 Pipeline Code Reference](../code/ipi-method/agent-builder/azure-pipelines-agent-builder.md)
- [UPI Day 1 Pipeline Code Reference](../code/upi-method/agent-builder/azure-pipelines-agent-builder.md)