# Core Python Files

This page explains the smaller runtime modules and the main reasoning loop in the current codebase.

For endpoint-level details, see [`API reference`](api-reference.md).
For a symbol-by-symbol index, see [`Function Reference`](function-reference.md).

## `src/openshift_sre_agent/__init__.py`

This package file is intentionally tiny. It re-exports `OpenShiftSreAgent` so external callers can import the main agent class from the package root.

## `src/openshift_sre_agent/__main__.py`

This file makes the package runnable with:

- `python -m openshift_sre_agent`

It simply delegates to the Typer CLI app defined in `cli.py`.

## `src/openshift_sre_agent/cli.py`

The CLI exposes two operator-facing commands:

- `ask` — run one prompt locally and optionally print the full reasoning/tool trace
- `serve` — start the HTTP server on port `8000`

The CLI is intentionally thin. It does not reimplement agent logic; it just constructs `OpenShiftSreAgent` or starts Uvicorn with `openshift_sre_agent.api:app`.

## `src/openshift_sre_agent/config.py`

This module centralizes runtime configuration.

### What it does

- loads `.env` from the repository root
- reads standard environment variables such as `OLLAMA_BASE_URL`, `OPENSHIFT_CLUSTER`, and `LOCAL_MODEL_NAME`
- builds database connection settings for the historical store
- supports request-scoped overrides without changing the base process configuration

### Important behavior

- if `DATABASE_ENABLED=true` and no explicit `DATABASE_URL` is provided, the module constructs one from `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, and `DB_PASSWORD`
- if a request supplies explicit OpenShift token, `with_overrides(...)` clears `kube_context_name` to avoid mixed-auth ambiguity
- the Ollama base URL is normalized to remove a trailing slash

## `src/openshift_sre_agent/model_client.py`

This module is the Ollama adapter.

### Primary responsibility

- receives the conversation built by `OpenShiftSreAgent`
- posts it to `POST {OLLAMA_BASE_URL}/api/chat`
- returns the final assistant message text

### Why it stays small

Keeping this class small isolates local-model transport behavior from reasoning logic. If the transport changes later, the agent loop does not have to.

## `src/openshift_sre_agent/prompts.py`

This module defines `SYSTEM_PROMPT`, which is the core behavior contract for the local model.

### Key instructions in the prompt

- use tools for live cluster information
- stay read-only and cautious
- never invent cluster state
- distinguish auth failures, access-denied results, unsubscribed services, and empty-but-healthy outputs
- return a strict JSON envelope with `thought`, `tool_call`, and `final_answer`

The prompt is intentionally paired with runtime validation in `agent.py`, so the system does not trust the model blindly.

## `src/openshift_sre_agent/safety.py`

This module defines the CLI fallback safety rails.

### What it blocks

- shell chaining such as `;`, `&&`, and `||`
- pipes and redirection
- command substitution with backticks
- multi-line commands
- non-read-only oc CLI verbs

### Main helpers

- `ensure_no_shell_operators(...)`
- `parse_oc_cli_command(...)`
- `oc_cli_verb(...)`
- `ensure_read_only_oc_cli(...)`

This is what keeps `run_read_only_oc_cli` from becoming an unbounded shell executor.

## `src/openshift_sre_agent/agent.py`

This is the core reasoning loop.

### Main responsibilities

- assemble the system prompt and live tool manifest
- send the conversation to the local model
- parse and validate the JSON envelope returned by the model
- invoke tools through `OpenShiftSreToolkit`
- recover from malformed or incomplete model turns
- stop only after a valid final answer is produced or the step budget is exhausted

### Current hardening behavior

The live implementation is more defensive than a minimal loop. It now supports:

- recovery from malformed JSON and empty model turns
- automatic recovery by invoking the next missing required tool after repeated unproductive turns
- normalization of alternate model envelope shapes such as `reasoning`, `answer`, `tool`, and stringified tool arguments
- dynamic step-budget expansion for large workflows such as FinOps drilldowns
- enforcement that explicitly requested services must actually be checked before finalizing
- blocking unprompted `run_read_only_oc_cli` detours during structured workflows
- final-answer augmentation with service-state and auth summaries
- approval-gated follow-up guidance when the run is incomplete, blocked by service posture/auth issues, or returns actionable recommendations

### Important runtime helpers

- `_required_tools_for_prompt(...)` maps prompt patterns to required tools
- `_auto_invoke_missing_required_tool(...)` runs the next missing required check when the model stalls or finalizes too early
- `_build_auto_recovery_prompt(...)` feeds the recovery tool output back into the next model turn with explicit continuation instructions
- `_parse_envelope(...)` and `_decode_json_payload(...)` recover valid JSON from imperfect model output
- `_normalize_payload(...)` and `_normalize_tool_call(...)` adapt model-specific aliases into the expected schema
- `_augment_final_answer(...)` appends operator-friendly summaries based on collected tool outputs
- `_build_follow_up_section(...)` adds a reusable “what I can do next” block with approval options such as `Approve follow-up` and `Approve fix plan`
- `_collect_follow_up_actions(...)` derives generic next-step guidance from missing tools, service errors, and actionable results
- `_classify_error_message(...)` distinguishes auth problems from unsubscribed or unsupported services

### Why this matters

This extra logic is what prevents common local-model failure modes from breaking the operator workflow:

- invalid JSON
- premature finalization
- repeated empty or otherwise unproductive turns while required checks are still missing
- incorrect tool aliases
- drifting into CLI fallback when richer SDK tools exist
- exhausting the step budget without a helpful summary

### Cross-page impact

This protection is intentionally implemented in `OpenShiftSreAgent.ask(...)`, not in a single browser page.

That means the same recovery logic now protects every workflow that sends prompts to `POST /chat`, including:

- the main Agent Console
- the Troubleshooting Console workflows hosted through the Agent Console UI
- the FinOps Console
- the Security Console

If one of those pages asks for a multi-service review and the model stalls before completing all explicitly requested checks, the backend can now keep the investigation moving by auto-running the next missing required tool instead of burning the rest of the step budget.

### New approval-based recovery behavior

When the model cannot finish cleanly, the agent no longer stops at a dead-end error paragraph.

For required-service investigations there is now an earlier recovery path as well: after repeated invalid or empty turns—or immediately after a premature final answer—the backend can auto-run the next missing required tool, mark that step with `auto_recovery`, and then prompt the model to continue from the recovered evidence.

Instead, the answer is augmented with:

- a short explanation of what can be done next to resolve the gap
- approval-oriented continuation choices such as:
  - `Approve follow-up`
  - `Approve fix plan`
  - `Approve supported execution plan`
- an explicit note that direct cluster mutations remain disabled under the current read-only safety posture

That behavior is generic: it works for incomplete required-service coverage, credentials or permission failures, not-enabled service posture, and actionable recommendation workflows such as FinOps rightsizing.

In the browser UI, those approval choices are no longer just plain text instructions. The console parses them into selectable radio actions and prepares a contextual follow-up prompt for the next run.

## Related pages

- [`Service & API Files`](code-services.md)
- [`API reference`](api-reference.md)
- [`Function Reference`](function-reference.md)
