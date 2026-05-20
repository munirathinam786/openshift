# Function and module reference

This page is a practical source-level reference for the important modules and functions in `src/openshift_sre_agent/`.

It focuses on:

- public entry points
- important internal helpers
- the runtime and data flow between modules

## Package and entry points

| Module | Symbol | Purpose |
| --- | --- | --- |
| `__init__.py` | `OpenShiftSreAgent` | Re-exports the main agent class for package consumers |
| `__main__.py` | `app()` | Lets `python -m openshift_sre_agent` behave like the CLI entry point |
| `cli.py` | `ask(...)` | Runs one prompt locally and optionally prints the reasoning steps |
| `cli.py` | `serve(...)` | Starts the FastAPI server with Uvicorn |

## Configuration and model client

| Module | Symbol | Purpose |
| --- | --- | --- |
| `config.py` | `Settings.load()` | Builds runtime settings from `.env` and environment variables |
| `config.py` | `Settings.with_overrides(...)` | Applies request-scoped runtime overrides without mutating the base settings |
| `config.py` | `normalize_llm_provider(...)` / `get_llm_provider_defaults(...)` | Normalizes provider IDs and resolves provider metadata/defaults |
| `model_client.py` | `ModelClient.chat(...)` | Sends the agent conversation to the configured provider and returns the assistant text |
| `prompts.py` | `SYSTEM_PROMPT` | Defines the JSON-envelope contract and the OpenShift-SRE operating rules |

### Notes

- `Settings.with_overrides(...)` clears `kube_context_name` when explicit credentials are passed, avoiding mixed-auth ambiguity.
- `ModelClient.chat(...)` selects the provider from `Settings.llm_provider` and supports Ollama, OpenAI, Azure OpenAI, Anthropic, Gemini, and OpenRouter.
- `OllamaClient` remains as a compatibility alias to `ModelClient` so older imports keep working.

## Safety helpers

| Module | Symbol | Purpose |
| --- | --- | --- |
| `safety.py` | `ensure_no_shell_operators(...)` | Rejects shell chaining, redirection, pipes, and multiline commands |
| `safety.py` | `parse_oc_cli_command(...)` | Parses and validates the `oc <verb> <resource>` structure |
| `safety.py` | `oc_cli_verb(...)` | Extracts the operation token from an oc CLI command |
| `safety.py` | `ensure_read_only_oc_cli(...)` | Allows only `describe`, `get`, `head`, and `list` oc CLI verbs |

## Agent reasoning loop

| Module | Symbol | Purpose |
| --- | --- | --- |
| `agent.py` | `OpenShiftSreAgent.ask(...)` | Main reasoning loop: prompt model, call tools, recover from failures, finalize answer |
| `agent.py` | `OpenShiftSreAgent._system_prompt()` | Injects the live tool manifest into the system prompt |
| `agent.py` | `OpenShiftSreAgent._required_tools_for_prompt(...)` | Derives required tools from prompt content for service-coverage enforcement |
| `agent.py` | `OpenShiftSreAgent._prompt_allows_cli(...)` | Allows CLI fallback only when the operator explicitly asks for it |
| `agent.py` | `OpenShiftSreAgent._missing_required_tools(...)` | Checks whether explicitly requested services were actually inspected |
| `agent.py` | `OpenShiftSreAgent._auto_invoke_missing_required_tool(...)` | Auto-runs the next missing required tool when the model stalls or finalizes too early |
| `agent.py` | `OpenShiftSreAgent._build_auto_recovery_prompt(...)` | Builds the follow-up user turn that resumes the model from auto-recovered evidence |
| `agent.py` | `OpenShiftSreAgent._build_step_limit_answer(...)` | Produces a useful fallback answer when the step budget is exhausted |
| `agent.py` | `OpenShiftSreAgent._parse_envelope(...)` | Parses and validates model JSON output |
| `agent.py` | `OpenShiftSreAgent._normalize_payload(...)` | Accepts alternate model envelope shapes such as `answer`, `response`, or `tool` |
| `agent.py` | `OpenShiftSreAgent._normalize_tool_call(...)` | Normalizes tool-call aliases and stringified payloads |
| `agent.py` | `OpenShiftSreAgent._decode_json_payload(...)` | Recovers JSON from chatty or fenced model responses |
| `agent.py` | `OpenShiftSreAgent._augment_final_answer(...)` | Appends auth/service-state summaries to the final answer |
| `agent.py` | `OpenShiftSreAgent._build_follow_up_section(...)` | Builds the generic approval-based continuation block for incomplete or actionable runs |
| `agent.py` | `OpenShiftSreAgent._collect_follow_up_actions(...)` | Derives next-step actions from missing tools, cluster errors, and recommendation-bearing results |
| `agent.py` | `OpenShiftSreAgent._summarize_tool_result(...)` | Produces operator-readable service-state summaries from tool outputs |
| `agent.py` | `OpenShiftSreAgent._classify_error_message(...)` | Distinguishes auth, access-denied, not-enabled, and unsupported service errors |

### Why these helpers matter

The live agent is deliberately more defensive than a minimal tool-calling loop. It can:

- recover from invalid JSON
- recover from empty turns
- auto-run the next missing required check after repeated unproductive turns or a premature final answer
- normalize non-standard model envelopes
- stop the model from finalizing before all explicitly named services are checked
- block unprompted CLI detours during structured workflows such as FinOps
- turn incomplete investigations and actionable findings into approval-gated continuation options without breaking the read-only safety model

That recovery logic is shared by every page that uses `POST /chat`, so it protects Security, FinOps, Agent Console, and Troubleshooting workflows without requiring page-specific code paths.

## API layer

| Module | Symbol | Purpose |
| --- | --- | --- |
| `api.py` | `_resolve_site_dir()` | Finds the generated MkDocs `site/` directory for static mounting |
| `api.py` | `_parse_csv_query(...)` | Normalizes comma-separated filter query parameters |
| `api.py` | `_runtime_settings(...)` | Applies request-scoped provider, cluster, and agent overrides to the base settings |
| `api.py` | `_get_llm_provider_catalog()` | Produces the provider metadata payload consumed by the UI |
| `api.py` | `_get_container_observability()` / `_get_runtime_observability_snapshot()` | Collects stack container metrics and pairs them with database telemetry for the main console |
| `api.py` | `root()` | Redirects to `/guide/` when docs are present |
| `api.py` | `health()` | Liveness endpoint |
| `api.py` | `llm_providers()` | Returns the provider catalog for the UI and automation clients |
| `api.py` | `runtime_observability()` | Returns the main console runtime telemetry payload |
| `api.py` | `history_overview(...)` | Aggregated historical dashboard payload |
| `api.py` | `history_run_detail(...)` | Full run detail endpoint |
| `api.py` | `history_tool_detail(...)` | Tool drilldown endpoint |
| `api.py` | `history_metric_detail(...)` | Metric drilldown endpoint |
| `api.py` | `chat(...)` | Main agent execution endpoint |
| `api.py` | `finops_queue()` | Lists persisted FinOps queue state |
| `api.py` | `create_finops_queue_item(...)` | Creates a persisted FinOps queue item |
| `api.py` | `update_finops_queue_item(...)` | Changes a queue item stage |
| `api.py` | `delete_finops_queue_item(...)` | Removes a queue item |

### Pydantic request/response models

Important API models include:

- `RuntimeConfig`
- `ChatRequest`
- `ChatResponse`
- `FinopsQueueCreateRequest`
- `FinopsQueueStageUpdateRequest`

## Persistence and analytics

| Module | Symbol | Purpose |
| --- | --- | --- |
| `persistence.py` | `HistoryStore.record_chat(...)` | Stores a run, its steps, and extracted metrics |
| `persistence.py` | `HistoryStore.get_overview(...)` | Produces the historical dashboard summary payload |
| `persistence.py` | `HistoryStore.get_database_observability()` | Returns database size, runtime stats, table inventory, and schema metadata for the console |
| `persistence.py` | `HistoryStore.get_run_detail(...)` | Returns a single run with steps and metrics |
| `persistence.py` | `HistoryStore.get_tool_detail(...)` | Returns tool-specific usage and metric series |
| `persistence.py` | `HistoryStore.get_metric_detail(...)` | Returns metric-specific drilldown payloads |
| `persistence.py` | `HistoryStore.list_finops_queue()` | Lists the persisted queue and stage counts |
| `persistence.py` | `HistoryStore.create_finops_queue_item(...)` | Creates queue items and applies auto-approve behavior |
| `persistence.py` | `HistoryStore.update_finops_queue_item_stage(...)` | Enforces supported FinOps stage transitions |
| `persistence.py` | `HistoryStore.delete_finops_queue_item(...)` | Deletes queue rows |
| `persistence.py` | `HistoryStore.extract_metrics(...)` | Extracts trend-friendly metrics from tool results |
| `persistence.py` | `HistoryStore._extract_from_payload(...)` | Walks top-level tool payloads |
| `persistence.py` | `HistoryStore._extract_from_mapping(...)` | Converts simple mappings and money objects into metrics |
| `persistence.py` | `HistoryStore._extract_from_rows(...)` | Converts row-based results into dimensioned metrics |
| `persistence.py` | `HistoryStore._serialize_finops_queue_item(...)` | Converts queue records into API-safe dictionaries |

### ORM models

Important SQLAlchemy models:

- `AgentRunRecord`
- `AgentStepRecord`
- `MetricSnapshotRecord`
- `FinopsQueueRecord`

### Database observability notes

`HistoryStore.get_database_observability()` is intentionally database-aware:

- for `sqlite`, it reports file-level size, page statistics, table counts, row counts, and schema details
- for MySQL/MariaDB-compatible engines, it also reads `information_schema.tables` to surface per-table data size, index size, free space, and runtime counters such as connected threads when available
- the main Agent Console uses this metadata for the new runtime/database observability panel instead of querying table contents directly

## Toolkit infrastructure

| Module | Symbol | Purpose |
| --- | --- | --- |
| `tools.py` | `ToolSpec` | Declares the tool name, description, arguments, and handler |
| `tools.py` | `AwsSessionFactory.create()` | Builds a kubernetes session using the configured region/profile/credentials |
| `tools.py` | `OpenShiftSreToolkit.tool_manifest()` | Returns the tool schema sent to the model |
| `tools.py` | `OpenShiftSreToolkit.invoke(...)` | Resolves and executes one tool call |
| `tools.py` | `OpenShiftSreToolkit._client(...)` | Creates a kubernetes client with shared retry and TLS settings |
| `tools.py` | `_cost_time_period(...)`, `_normalize_granularity(...)`, `_money_value(...)`, `_money_dict(...)` | Shared helpers for FinOps tools |
| `model_client.py` | `_chat_ollama(...)`, `_chat_openai_compatible(...)`, `_chat_azure_openai(...)`, `_chat_anthropic(...)`, `_chat_gemini(...)` | Provider-specific request/response adapters with normalized token tracking |

## Toolkit functions by domain

### Compute and platform inventory

- `list_ec2_instances`
- `list_autoscaling_groups`
- `list_ebs_volumes`
- `list_rds_instances`
- `list_cloudformation_stacks`
- `list_ecs_clusters`
- `list_eks_clusters`
- `list_lambda_functions`
- `list_emr_clusters`
- `list_ecr_repositories`

### Networking and edge

- `list_vpc_inventory`
- `list_subnets`
- `list_transit_gateways`
- `list_load_balancers`
- `list_target_groups`
- `list_api_gateways`
- `list_cloudfront_distributions`
- `list_route53_zones`
- `list_waf_web_acls`
- `list_network_firewalls`
- `list_firewall_manager_policies`

### Observability and operations

- `get_cloudwatch_metric`
- `query_logs_insights`
- `list_alarms`
- `list_ssm_managed_instances`
- `list_ssm_parameters`
- `list_secrets_manager_secrets`
- `list_eventbridge_buses`
- `list_eventbridge_rules`
- `list_step_functions`

### FinOps and cost analysis

- `list_cost_and_usage_summary`
- `list_cost_by_service`
- `list_cost_by_tag`
- `get_cost_forecast`
- `list_savings_plans_coverage`
- `list_rightsizing_recommendations`

### Data and analytics

- `list_s3_buckets`
- `list_glue_catalog`
- `list_athena_workgroups`
- `list_redshift_clusters`
- `list_redshift_serverless`
- `list_dynamodb_tables`
- `list_kinesis_streams`
- `list_opensearch_domains`
- `list_elasticache_clusters`
- `list_sqs_queues`
- `list_sns_topics`

### Security, governance, and backup

- `list_cloudtrail_trails`
- `list_cloudtrail_event_selectors`
- `list_config_rules`
- `list_config_compliance_summary`
- `list_guardduty_detectors`
- `list_guardduty_findings`
- `list_detective_graphs`
- `list_inspector_findings`
- `list_macie_posture`
- `list_access_analyzers`
- `list_kms_keys`
- `list_securityhub_findings`
- `list_securityhub_standards`
- `list_backup_vaults`
- `list_backup_recovery_points`
- `list_backup_plan_vault_mappings`
- `list_organization_accounts`
- `list_organization_structure`
- `list_organization_account_mappings`
- `list_controltower_controls`

### Guarded CLI fallback

- `run_read_only_oc_cli`

This method is intentionally special:

- it is only allowed when the operator explicitly asks for an oc CLI command
- it is filtered through `ensure_read_only_oc_cli(...)`
- the agent discourages model detours into it when a named SDK-backed tool is more appropriate

## Tests that define expected behavior

The most useful executable references live in:

- `tests/test_agent.py`
- `tests/test_persistence.py`

They document expected behavior for:

- malformed JSON recovery
- model-envelope alias normalization
- required-tool enforcement
- FinOps step-budget expansion
- CLI detour blocking
- metric extraction
- dashboard filtering
- persisted FinOps queue lifecycle
- multi-provider provider catalog exposure
- hosted-provider request shape normalization and token accounting

## Related pages

- [`Core Python Files`](code-core.md)
- [`Service & API Files`](code-services.md)
- [`API reference`](api-reference.md)
- [`FinOps queue API and UI flow`](finops-queue-flow.md)
