# FinOps queue API and UI flow

This page explains how the FinOps workflow moves from a generated recommendation in the browser to a persisted planning record in the database.

## What this workflow is for

The FinOps module is intentionally more than a prompt template.

It now supports:

- opportunity categories for `compute`, `storage`, `commitment`, and `idle`
- estimated savings and cost-impact tables
- recommended action cards with evidence, risk, confidence, and execution notes
- a backend-persisted approval queue for future safe execution planning
- explicit stage transitions for change control

The queue is still **planning-only**. No AWS mutation is executed by the current UI or backend.

## End-to-end flow

1. the operator runs a FinOps-oriented prompt from `docs/console.html`
2. `POST /chat` runs the agent and returns tool traces
3. `docs/assets/javascripts/agent-console.js` builds a workflow from the returned tool results
4. the UI renders category summaries, savings tables, and action cards
5. when the operator queues an action, the browser calls `POST /finops/queue`
6. `src/aws_sre_agent/api.py` validates the request and forwards it to `HistoryStore.create_finops_queue_item(...)`
7. `src/aws_sre_agent/persistence.py` stores the item in `FinopsQueueRecord`
8. subsequent stage changes call `PATCH /finops/queue/{item_id}`
9. the queue can be reloaded at any time with `GET /finops/queue`

## Browser responsibilities

The browser-side queue logic lives in `docs/assets/javascripts/agent-console.js`.

Key responsibilities:

- fetch the persisted queue from `/finops/queue`
- create queue items from FinOps opportunities
- update queue stages
- delete queue items
- render stage counts and per-item action buttons
- keep queue rendering separate from the agent's main `/chat` response flow

The UI does not store queue state in browser-local storage anymore. Refreshing the page re-reads the backend state.

## Backend responsibilities

### `src/aws_sre_agent/api.py`

Owns the HTTP contract:

- request models for create/update operations
- HTTP status code mapping
- persistence availability checks
- translating Python exceptions into FastAPI responses

### `src/aws_sre_agent/persistence.py`

Owns the durable storage contract:

- SQLAlchemy model `FinopsQueueRecord`
- supported stage list in `HistoryStore.FINOPS_QUEUE_STAGES`
- queue create/list/update/delete methods
- serialization of queue rows back into API payloads

## Queue stages

The stage model is intentionally operational rather than execution-oriented.

| Stage | Meaning |
| --- | --- |
| `planned` | identified and queued, but not yet approved |
| `approved` | approved for future controlled execution planning |
| `precheck_passed` | validation and prerequisite checks are complete |
| `ready_for_change_window` | prepared and waiting for the approved change window |
| `executed` | the planned change was executed by some future controlled process |
| `rolled_back` | execution was reverted |
| `deferred` | intentionally postponed |

## Auto-approve behavior

If the operator enables **Auto approve queued FinOps actions** in the UI:

- the browser still calls `POST /finops/queue`
- the request sets `auto_approve: true`
- the backend stores the item directly in the `approved` stage

This is a planning convenience only. It does **not** imply direct AWS execution.

## Persistence model

The current table stores:

- queue identity: `id`, `run_id`, `opportunity_key`, `title`
- classification: `category`, `risk`, `confidence`
- economics: `estimated_monthly_savings`, `unit`
- operator guidance: `action`, `basis`, `evidence`, `execution_plan`
- execution-planning metadata: `execution_stage`, `auto_approved`, `execution_mode`
- timestamps: `created_at`, `updated_at`

This is enough to support:

- queue replay after refresh
- dashboard-style summaries by stage
- linking recommendations back to the originating run
- future extensions for controlled execution workflows

## Example lifecycle

A typical commitment-optimization item might move like this:

1. `planned` — detected from Savings Plans coverage gaps
2. `approved` — finance/platform owner approves the idea
3. `precheck_passed` — baseline usage and rollback conditions verified
4. `ready_for_change_window` — waiting for the selected purchase or rollout window
5. `executed` — the commitment action is completed by a future controlled workflow

If the item is no longer appropriate, it may instead move to:

- `deferred`
- `rolled_back`

## Safety boundary

The current implementation stops at planning and documentation.

That means:

- the browser never sends direct AWS mutation requests
- `allow_mutating_actions` is still effectively reserved for future expansion
- the queue documents what should happen later, not what is happening automatically now

This keeps the FinOps UX useful without accidentally turning the console into an unsafe control plane.

## Related pages

- [`API reference`](api-reference.md)
- [`Architecture`](architecture.md)
- [`Runtime, Docs, and Tests`](code-runtime.md)
- [`FinOps & Optimization`](playbook-finops.md)
