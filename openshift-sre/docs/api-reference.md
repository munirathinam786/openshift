# API reference

This page documents the live HTTP surface exposed by `src/openshift_sre_agent/api.py`.

The FastAPI application serves two roles:

- expose the agent and historical APIs under `/`
- mount the generated MkDocs site under `/guide`

## API surface summary

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/` | Redirects to `/guide/` when the site is present, otherwise returns a small service summary payload |
| `GET` | `/health` | Liveness check |
| `GET` | `/llm/providers` | Provider catalog used by the browser consoles to render provider choices and auth fields |
| `GET` | `/ollama/utilization` | Live Ollama model/utilization snapshot for the LLM Utilization page and dashboard summary |
| `GET` | `/runtime/observability` | Container and database telemetry used by the main Agent Console observability panel |
| `GET` | `/builder/catalog` | Discover local OpenShift pipeline, template, and variable YAML inventory for OpenShift Builder |
| `POST` | `/builder/design/plan` | Recommend matching catalog pipelines for the current OpenShift Architect design snapshot and prompt |
| `POST` | `/builder/ado/auth` | Validate Azure DevOps organization/project/repository settings and return YAML-backed pipeline inventory using an operator-supplied PAT |
| `POST` | `/builder/ado/pipelines` | Fetch Azure DevOps pipeline definitions and YAML content as OpenShift Builder catalog entries |
| `POST` | `/builder/implement` | Package selected catalog pipelines, generate missing YAML when confirmed, and optionally push to Azure DevOps |
| `POST` | `/chat` | Run a prompt through the agent with optional per-request runtime overrides |
| `POST` | `/security/audit` | Run a batched security audit for Security Console profiles such as SOX and HIPAA |
| `GET` | `/history/overview` | Summary payload for the historical dashboard |
| `GET` | `/history/runs/{run_id}` | Full run detail including steps and extracted metrics |
| `GET` | `/history/compare` | Compare two runs and highlight answer, tag, step, and metric drift |
| `GET` | `/history/tools/{tool_name}` | Tool-specific drilldown view |
| `GET` | `/history/metrics/{metric_key}` | Metric-specific drilldown with source payloads |
| `GET` | `/investigations` | List saved investigations |
| `POST` | `/investigations` | Create a saved investigation |
| `PATCH` | `/investigations/{investigation_id}` | Update a saved investigation |
| `DELETE` | `/investigations/{investigation_id}` | Delete a saved investigation |
| `GET` | `/watchlists` | List saved watchlists |
| `POST` | `/watchlists` | Create a watchlist |
| `PATCH` | `/watchlists/{watchlist_id}` | Update a watchlist |
| `DELETE` | `/watchlists/{watchlist_id}` | Delete a watchlist |
| `POST` | `/watchlists/{watchlist_id}/run` | Run a saved investigation across the watchlist scope |
| `POST` | `/platform/sweep` | Execute selected tools across regions and optional role assumptions |
| `GET` | `/finops/queue` | List persisted FinOps approval-queue items and stage counts |
| `POST` | `/finops/queue` | Create a queue item for future safe execution planning |
| `PATCH` | `/finops/queue/{item_id}` | Move a queue item to another planning stage |
| `DELETE` | `/finops/queue/{item_id}` | Remove a queue item |
| `GET` | `/healthz` | Liveness check with version |
| `GET` | `/readyz` | Readiness check — verifies the configured LLM provider and persistence layer |
| `GET` | `/history/export` | Export run history as CSV |
| `POST` | `/history/runs/{id}/tags` | Add tags to a run |
| `DELETE` | `/history/runs/{id}` | Delete a run |
| `POST` | `/chat/batch` | Run multiple prompts in one request |
| `GET` | `/prompts/templates` | List available prompt templates |
| `GET` | `/metrics` | Prometheus-compatible metrics |
| `POST` | `/admin/retention` | Enforce data retention policy |

## OpenShift Builder API

The OpenShift Builder workspace uses the `/builder/*` API group to turn Architect output into delivery-ready OpenShift pipeline assets:

- `GET /builder/catalog` scans configured source roots for Azure Pipeline YAML, templates, and variable files across IPI, UPI, ACM, DR, migration, virtualization, ARO, ROSA, IBM Z, and SRE folders.
- `POST /builder/ado/auth` validates Azure DevOps organization, project, repository, branch, target directory, and PAT values without storing the PAT, then returns a `catalog` payload containing YAML-backed Azure Pipelines when Azure DevOps exposes a YAML path for the pipeline definition.
- `POST /builder/ado/pipelines` performs only the Azure DevOps pipeline discovery step and returns the same catalog shape used by `/builder/catalog`.
- `POST /builder/design/plan` compares the latest OpenShift Architect design snapshot and operator prompt with the discovered catalog and returns recommended pipeline IDs plus missing requirements. When ADO context is supplied, the server merges local catalog entries with the ADO pipeline catalog so selected ADO pipeline IDs can be planned.
- `POST /builder/implement` packages selected catalog YAML, optionally generates missing implementation files after confirmation, and can push the resulting payload to Azure DevOps. Generated YAML is plan-first and uses placeholders for service connections, state backends, and credentials.

Non-secret defaults are read from `OPENSHIFT_BUILDER_SOURCE_PATHS`, `OPENSHIFT_BUILDER_ADO_ORG_URL`, `OPENSHIFT_BUILDER_ADO_PROJECT`, `OPENSHIFT_BUILDER_ADO_REPO`, `OPENSHIFT_BUILDER_ADO_BRANCH`, and `OPENSHIFT_BUILDER_ADO_TARGET_DIRECTORY` when present.

## `POST /chat`

### Chat purpose

Runs a single operator prompt through `OpenShiftSreAgent`, stores the run through `HistoryStore`, and returns both the final answer and the reasoning/tool trace.

### Request body

```json
{
  "prompt": "Run a FinOps drilldown with cost and usage summary, cost by service, cost by tag for Environment, cost forecast, Savings Plans coverage, and rightsizing recommendations.",
  "runtime": {
    "llm_provider": "openai",
    "llm_model_name": "gpt-4.1-mini",
    "llm_base_url": "https://api.openai.com/v1",
    "llm_api_key": "sk-...",
    "llm_organization": "optional-org-id",
    "ollama_base_url": "http://host.containers.internal:11434",
    "local_model_name": "gpt-oss:20b",
    "cluster_scope": "local-cluster",
    "kube_context_name": "default",
    "agent_max_steps": 12,
    "verify_ssl": true
  }
}
```

### Response body

```json
{
  "answer": "FinOps drilldown completed.\n\nObserved service states:\n- Cost And Usage Summary: estimated 100.00 USD across the last 30 day(s).\n\nWhat I can do next:\n- Translate the collected FinOps signals into a prioritized cost-optimization plan with risk, approval, and rollback guidance.\n\nApproval options:\n- Reply with `Approve fix plan` and I will turn the current findings into a service-by-service remediation plan with validation and rollback guidance.\n- Reply with `Approve supported execution plan` and I will prepare approval-gated execution guidance for supported workflows while keeping direct cluster mutations disabled.",
  "run_id": 42,
  "steps": [
    {
      "step": 1,
      "thought": "Need the high-level spend baseline first",
      "tool_call": {
        "name": "list_cost_and_usage_summary",
        "arguments": {}
      },
      "final_answer": "",
      "tool_result": {
        "days": 30,
        "total_unblended_cost": {
          "amount": 100,
          "unit": "USD"
        }
      }
    }
  ]
}
```

### Answer behavior

The `answer` field is not just the model's raw final text. The backend may augment it with operator-friendly sections such as:

- **Observed service states** — a normalized summary of tool results and service posture
- **What I can do next** — generic recovery or remediation actions derived from missing checks, cluster errors, and collected findings
- **Approval options** — explicit phrases the operator can send next, such as `Approve follow-up` or `Approve fix plan`

This makes incomplete or blocked runs actionable instead of ending with a bare step-limit failure.

For prompts that explicitly require certain cluster checks, the backend can also recover before step exhaustion. If the model returns repeated invalid or empty turns, or tries to finalize before all required checks are complete, the agent may automatically invoke the next missing required tool and continue the run from that evidence.

Those recovery steps are included in the `steps` trace and are marked with `"auto_recovery": true` so the UI can show that the backend intervened to keep the investigation moving.

In the browser console, those approval options are now rendered as radio-button choices. Selecting one prepares the next contextual follow-up prompt automatically, so the operator does not need to type the approval phrase manually.

Because this behavior lives behind `POST /chat`, it applies across all chat-backed pages, including the Agent Console, Troubleshooting workflows, and FinOps Console.

## `POST /security/audit`

Runs a batched control review for the **Security Console** without waiting for the model to decide on each tool one-by-one.

This endpoint is designed for larger audit presets such as **SOX** and **HIPAA**, where the UI already knows which platform security controls to inspect and can ask the backend to execute them directly.

### Security-audit request body

```json
{
  "profile_key": "hipaa",
  "profile_label": "HIPAA safeguard and evidence readiness",
  "focus_label": "Executive summary + priority findings",
  "selected_features": [
    "list_cloudtrail_trails",
    "list_securityhub_standards",
    "list_securityhub_findings",
    "list_kms_keys"
  ],
  "operator_notes": "Validate logging, encryption, and findings coverage.",
  "runtime": {
    "cluster_scope": "local-cluster",
    "llm_provider": "ollama",
    "local_model_name": "gpt-oss:20b"
  },
  "tags": ["security-console", "hipaa"]
}
```

### Security-audit behavior

- validates each requested feature against the live toolkit
- runs the selected cluster inspection tools directly in sequence
- captures per-tool success or error details in the returned `steps`
- stores the audit run through `HistoryStore` like other operator workflows
- returns the same `ChatResponse` shape used by `/chat`, so the browser console can reuse its result rendering

### Why it exists

The standard `/chat` endpoint is still the right choice for open-ended investigations. The dedicated security-audit endpoint exists to keep compliance presets fast and predictable when the operator already chose the exact control set to review.

### Runtime overrides

The `runtime` object is optional. When present, it is applied with `Settings.with_overrides(...)`.

Important behavior:

- `llm_provider` switches the request between local Ollama and hosted providers such as OpenAI, Azure OpenAI, Anthropic, Gemini, and OpenRouter
- `llm_model_name`, `llm_base_url`, `llm_api_key`, `llm_api_version`, and `llm_organization` are provider-specific hosted-model overrides
- explicit tokens clear the configured kube context for that request
- the Ollama base URL is normalized to remove a trailing slash
- the override affects only the current request and does not mutate `.env`
- `cluster_scopes` can provide a comma-separated sweep scope that the watchlist and platform sweep workflows reuse
- `reserved_role_arn`, `reserved_role_external_id`, and `agent_session_name` allow cross-cluster sweeps without changing the base process configuration
- `tls_ca_bundle` and `verify_ssl` let operators deal with private trust chains and enterprise proxy certificates on a per-request basis

### External-provider example runtime

```json
{
  "prompt": "Summarize the highest-risk Security Hub findings and next steps.",
  "runtime": {
    "llm_provider": "azure-openai",
    "llm_model_name": "gpt-4.1-mini",
    "llm_base_url": "https://your-resource-name.openai.azure.com",
    "llm_api_key": "azure-api-key",
    "llm_api_version": "2024-06-01",
    "cluster_scope": "local-cluster",
    "agent_max_steps": 12
  }
}
```

## `GET /llm/providers`

Returns the provider catalog used by the browser pages to populate provider dropdowns, suggested models, and credential fields.

### Provider-catalog response fields

- the configured default provider
- the configured effective model name
- the configured effective base URL
- a list of provider metadata entries with:
  - label
  - category (`local` or `external`)
  - suggested models
  - default base URL
  - optional default API version
  - credential field descriptors used by the UI

### Runtime observability example response

```json
{
  "configured_provider": "ollama",
  "configured_model_name": "gpt-oss:20b",
  "configured_base_url": "http://localhost:11434",
  "providers": [
    {
      "id": "openai",
      "label": "OpenAI",
      "category": "external",
      "default_base_url": "https://api.openai.com/v1",
      "default_model": "gpt-4.1-mini",
      "credential_fields": [
        {"key": "llm_api_key", "label": "API key", "required": true}
      ]
    }
  ]
}
```

## `GET /history/overview`

### Purpose

Provides the aggregated payload used by `docs/assets/javascripts/history-dashboard.js` and the historical cards on the console page.

### Compare query parameters

| Parameter | Meaning |
| --- | --- |
| `time_range` | One of `24h`, `7d`, `30d`, `90d`, `all` |
| `model_names` / `model_name` | Filter to one or more model names |
| `cluster_scopes` / `cluster_scope` | Filter to one or more cluster scopes |
| `tool_names` | Filter to runs that used one or more tools |
| `run_limit` | Maximum number of recent runs returned |
| `point_limit` | Maximum points per metric series |
| `series_limit` | Maximum metric series returned |

### History overview example response fragment

```json
{
  "enabled": true,
  "summary": {
    "total_runs": 5,
    "failed_runs": 1,
    "metrics_recorded": 54,
    "average_duration_ms": 812.4,
    "last_run_at": "2026-05-14T16:22:13+00:00"
  },
  "tool_usage": [
    {
      "tool_name": "list_cost_by_service",
      "label": "Cost By Service",
      "count": 3
    }
  ],
  "recent_runs": [
    {
      "run_id": 42,
      "status": "completed",
      "model_name": "gpt-oss:20b",
      "cluster_scope": "local-cluster"
    }
  ]
}
```

## `GET /history/runs/{run_id}`

Returns the full stored record for one run:

- prompt and final answer
- each reasoning step
- tool arguments
- tool results and tool errors
- extracted metrics

Use this for operator drilldown and debugging model/tool behavior after a run.

## `GET /history/compare`

Compares two persisted runs and returns a normalized diff payload intended for the Drift Diff workspace.

### Query parameters

| Parameter | Meaning |
| --- | --- |
| `left_run_id` | Baseline run ID |
| `right_run_id` | Comparison run ID |

### Behavior

The response is persistence-backed and returns `404` when either run is missing. The payload is designed to highlight:

- answer changes
- tag differences
- step-level tool drift
- metric additions, removals, and value changes

## `GET /investigations`

Lists all saved investigations. These are reusable prompt definitions that can carry default regions, tags, and preferred tools.

## `POST /investigations`

Creates a saved investigation.

### Investigation create example request

```json
{
  "name": "Weekly platform posture",
  "prompt": "Inspect caller identity, network posture, S3 posture, IAM role posture, and Lambda posture.",
  "description": "Repeatable baseline review for production shared services.",
  "category": "platform",
  "default_regions": ["local-cluster", "us-west-2"],
  "default_tags": ["weekly-review", "platform"],
  "default_tools": ["get_caller_identity", "list_network_posture", "list_s3_posture"]
}
```

### Investigation update and delete behavior

- `PATCH /investigations/{investigation_id}` updates any supplied fields
- `DELETE /investigations/{investigation_id}` removes the saved investigation
- persistence-backed workflows return `503` when historical storage is disabled

## `GET /watchlists`

Returns all watchlists along with linked saved-investigation data when available.

## `POST /watchlists`

Creates a watchlist that references an investigation and optionally narrows regions, role ARNs, tags, and schedule hints.

### Watchlist create example request

```json
{
  "name": "Prod posture watch",
  "investigation_id": 7,
  "notes": "Run before the weekly ops review.",
  "schedule_hint": "weekly",
  "regions": ["local-cluster", "eu-west-1"],
  "role_arns": ["cluster:role/readonly-sre"],
  "tags": ["prod", "watchlist"],
  "enabled": true
}
```

### Watchlist update and delete behavior

- `PATCH /watchlists/{watchlist_id}` updates the stored scope or metadata
- `DELETE /watchlists/{watchlist_id}` removes the watchlist

## `POST /watchlists/{watchlist_id}/run`

Expands the linked saved investigation across the watchlist scope.

The backend resolves the effective scope in this order:

1. request-level runtime override
2. watchlist regions / role ARNs
3. investigation defaults
4. base settings from `.env`

Each region/role combination runs the saved prompt through `OpenShiftSreAgent`, then the response list is returned together with the updated watchlist metadata.

## `POST /platform/sweep`

Executes a list of tool names directly via `OpenShiftSreToolkit` across the requested regions and optional role ARNs.

### FinOps queue stage update example request

```json
{
  "tool_names": ["get_caller_identity", "list_network_posture", "list_s3_posture"],
  "regions": ["local-cluster", "us-west-2"],
  "role_arns": ["cluster:role/readonly-sre"],
  "runtime": {
    "verify_ssl": true,
    "agent_session_name": "weekly-platform-sweep"
  }
}
```

### Sweep behavior

- the endpoint validates every requested tool name before execution
- caller identity is included for each region/role result block
- tool failures are captured per tool instead of aborting the whole sweep
- unsupported tool names return `400`

## `GET /history/tools/{tool_name}`

Returns a tool-specific view containing:

- invocation counts
- run counts
- failure counts
- recent invocations
- metric series derived from that tool

Typical example:

- `/history/tools/get_cost_forecast`
- `/history/tools/list_securityhub_findings`

## `GET /history/metrics/{metric_key}`

Returns a metric-specific drilldown with:

- metric summary values
- recent matching records
- the original tool arguments/result that produced each metric sample
- chart-friendly points in chronological order

Typical example:

- `/history/metrics/list_savings_plans_coverage.average_coverage_percentage`

## `GET /ollama/utilization`

### Ollama utilization purpose

Provides the live payload used by `docs/llm-utilization.html` and the live LLM summary panel on `docs/history.html` for the **local Ollama runtime**.

### What it returns

- configured `OLLAMA_BASE_URL`
- configured local model name
- currently loaded model list from Ollama's `/api/ps`
- parameter size and quantization details
- VRAM footprint and context length
- whether the API could reach Ollama
- whether the current runtime can inspect local Ollama processes
- documented host-side commands for direct laptop inspection

### Container behavior

When the API is running inside Podman and Ollama is running on the host, host-level macOS process CPU/RAM is intentionally reported as unavailable from the container runtime. In that case the endpoint still returns the live Ollama API snapshot and a note explaining that host-side commands should be run directly on the laptop.

When the active provider is not `ollama`, this endpoint is still available for local-runtime visibility, but hosted-provider readiness is primarily surfaced through `GET /readyz` and `GET /llm/providers`.

### Ollama utilization example response fragment

```json
{
  "checked_at": "2026-05-15T15:42:12.345678+00:00",
  "ollama_base_url": "http://host.containers.internal:11434",
  "configured_model_name": "gpt-oss:20b",
  "api_reachable": true,
  "active_model_count": 1,
  "loaded_models": [
    {
      "name": "gpt-oss:20b",
      "parameter_size": "20.9B",
      "quantization_level": "MXFP4",
      "size_vram_gib": 14.66,
      "context_length": 8192
    }
  ],
  "host_process_metrics": {
    "available": false,
    "scope": "container",
    "note": "The API is running inside Podman, so host-level macOS Ollama process CPU/RAM is not directly visible here."
  }
}
```

## `GET /runtime/observability`

Returns the live runtime payload used by the **Agent Console** to show:

- the containers used by the local stack
- container image and size information when the local container CLI exposes it
- CPU and memory usage for each visible container
- GPU visibility notes when the runtime can or cannot expose accelerator telemetry
- database utilization, schema inventory, and table-level details in dropdown form

### Runtime observability behavior

- prefers live `podman` or `docker` CLI telemetry when the API process can reach the local container runtime
- falls back to safe in-container app memory telemetry plus stack metadata when the container CLI is not reachable from inside the app container
- always returns database utilization from `HistoryStore.get_database_observability()` when the persistence layer is enabled
- intentionally keeps database table details to metadata such as row counts, sizes, indexes, primary keys, and columns rather than returning table contents

### Example response fragment

```json
{
  "checked_at": "2026-05-19T12:34:56.000000+00:00",
  "containers": {
    "runtime": "podman",
    "source": "container-cli",
    "containers": [
      {
        "name": "openshift-sre-agent",
        "image": "localhost/openshift-sre-agent-local:dev",
        "status": "Up 2 minutes",
        "size": "145MB (virtual 1.2GB)",
        "cpu_percent": 3.5,
        "memory_percent": 6.25,
        "memory_usage": "128MiB / 2GiB",
        "gpu_usage": null
      }
    ]
  },
  "database": {
    "enabled": true,
    "dialect": "mysql",
    "database_name": "openshift_sre_agent",
    "utilization": {
      "table_count": 6,
      "database_size_bytes": 1048576,
      "tracked_run_count": 42
    },
    "tables": [
      {
        "table_name": "agent_runs",
        "row_count": 42,
        "size_bytes": 32768,
        "primary_key": ["id"]
      }
    ]
  }
}
```

## `GET /finops/queue`

Returns the persisted approval queue used by the console's FinOps workflow.

### Example response

```json
{
  "enabled": true,
  "stage_counts": {
    "approved": 1
  },
  "items": [
    {
      "id": 1,
      "run_id": 42,
      "opportunity_key": "commitment-savings-plans-gap",
      "title": "Close Savings Plans coverage gap (72.5%)",
      "category": "commitment",
      "estimated_monthly_savings": 88.75,
      "unit": "USD",
      "execution_stage": "approved",
      "risk": "medium",
      "confidence": "high",
      "action": "Review steady-state baseline and align commitment coverage.",
      "basis": "Observed uncovered on-demand spend",
      "evidence": "Average coverage below target.",
      "execution_plan": "Validate baseline, obtain approval, schedule change window, and prepare rollback accounting.",
      "auto_approved": true,
      "execution_mode": "future-safe-execution-plan-only",
      "created_at": "2026-05-14T16:54:47+00:00",
      "updated_at": "2026-05-14T16:54:47+00:00"
    }
  ]
}
```

## `POST /finops/queue`

Creates a queue item. The backend converts `auto_approve: true` into an initial stage of `approved`; otherwise the item starts at `planned`.

### FinOps queue create example request

```json
{
  "opportunity_key": "compute-rightsize-demo",
  "title": "Rightsize demo workload",
  "category": "compute",
  "estimated_monthly_savings": 42.5,
  "unit": "USD",
  "risk": "medium",
  "confidence": "high",
  "action": "Review and rightsize the workload.",
  "basis": "Direct rightsizing recommendation",
  "evidence": "Projected savings from observed utilization.",
  "execution_plan": "Validate, approve, schedule, and rollback if needed.",
  "run_id": 42,
  "auto_approve": true,
  "execution_mode": "future-safe-execution-plan-only"
}
```

## `PATCH /finops/queue/{item_id}`

Moves a queue item to another stage.

### Example request

```json
{
  "execution_stage": "ready_for_change_window"
}
```

Supported stages are:

- `planned`
- `approved`
- `precheck_passed`
- `ready_for_change_window`
- `executed`
- `rolled_back`
- `deferred`

## `DELETE /finops/queue/{item_id}`

Deletes the stored queue item and returns:

```json
{
  "deleted": true
}
```

## v0.3.0 endpoints

### `POST /chat/batch`

Run multiple prompts in a single request. Returns an array of chat responses.

```json
{ "prompts": ["List EC2 instances", "Show CloudWatch alarms"] }
```

### `GET /prompts/templates`

Returns all available prompt templates (persona names and their system prompt text).

### `GET /history/export`

Download all run history as a CSV file.

### `POST /history/runs/{id}/tags`

Tag a run with metadata labels.

```json
{ "tags": ["incident-123", "prod"] }
```

### `DELETE /history/runs/{id}`

Permanently delete a run and its steps.

### `GET /metrics`

Prometheus-compatible metrics including request counts, duration histograms, and token usage totals.

### `POST /admin/retention`

Enforce data retention by deleting runs older than the configured retention period.

```json
{ "days": 90 }
```

### Authentication

When `API_KEY` is set, all endpoints except `/healthz`, `/readyz`, and `/guide/*` require a `Bearer` token in the `Authorization` header.

### Prompt injection detection

The `/chat` endpoint scans incoming prompts against six pattern categories (instruction override, role hijacking, system prompt extraction, developer mode, encoding bypass, delimiter injection). Blocked requests return `400`.

## Error behavior

The API intentionally maps common failure modes to operator-friendly HTTP responses:

- `400` for invalid FinOps stage transitions
- `400` for watchlists missing a linked saved investigation or unsupported sweep tools
- `404` for missing run, tool, metric, or queue item records
- `404` for missing saved investigations, watchlists, or compared run IDs
- `500` for agent execution failures during `/chat`
- `503` when persistence-backed features are requested but the historical store is disabled or unavailable

## Site mounting behavior

If the generated `site/` directory exists, `api.py` mounts it as static content under `/guide`. The root path then redirects to `/guide/`, which is why the container can serve both the operator documentation and the live console from the same process.
