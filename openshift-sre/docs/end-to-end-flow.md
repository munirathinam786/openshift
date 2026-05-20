# End-to-End Code Flow

This page maps the complete repository flow from operator input to cluster data collection, persistence, dashboard drilldown, and CSV export.

## End-to-end diagram

```text
┌──────────────────────────────┐
│ Operator                     │
│ - browser UI                 │
│ - CLI prompt                 │
└──────────────┬───────────────┘
               │
               ▼
┌──────────────────────────────┐
│ Entry points                 │
│ - ui/src/app-shell.jsx       │
│ - docs/console.html          │
│ - src/openshift_sre_agent/cli.py   │
│ - src/openshift_sre_agent/api.py   │
└──────────────┬───────────────┘
               │ POST /chat
               ▼
┌──────────────────────────────┐
│ OpenShiftSreAgent                  │
│ src/openshift_sre_agent/agent.py   │
│ - prompt assembly            │
│ - reasoning loop             │
│ - tool call orchestration    │
└──────────────┬───────────────┘
               │
     ┌─────────┴─────────┐
     │                   │
     ▼                   ▼
┌───────────────┐   ┌─────────────────────┐
│ model_client  │   │ tools.py            │
│ Ollama chat   │   │ kubernetes / oc CLI     │
└──────┬────────┘   └─────────┬───────────┘
       │                      │
       └────────────┬─────────┘
                    ▼
          ┌──────────────────────┐
          │ persistence.py       │
          │ - agent_runs         │
          │ - agent_steps        │
          │ - metric_snapshots   │
          └──────────┬───────────┘
                     │
          ┌──────────┴────────────────────────────────┐
          │ History APIs                               │
          │ - GET /history/overview                    │
          │ - GET /history/runs/{run_id}               │
          │ - GET /history/tools/{tool_name}           │
          │ - GET /history/metrics/{metric_key}        │
          └──────────┬────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ docs/history.html + app-shell.js + history-dashboard.js    │
│ - filters, comparisons, charts                             │
│ - this week vs last week storytelling                      │
│ - percentile latency bands                                 │
│ - executive exception rollups                              │
│ - click run -> in-page run trace                           │
│ - click metric -> in-page metric collection drilldown      │
│ - export dashboard CSV / PNG / weekly ops review           │
│ - export selected metric CSV                               │
└──────────┬──────────────────────────────────────────────────┘
           │
           ▼
┌─────────────────────────────────────────────────────────────┐
│ docs/tool-drilldown.html + app-shell.js + tool-drilldown.js│
│ - per-tool invocation history                              │
│ - tool metric trends                                       │
│ - links back to history dashboard                          │
└─────────────────────────────────────────────────────────────┘
```

## File alignment by stage

### 1. Runtime configuration

- `src/openshift_sre_agent/config.py`
  - Loads `.env`
  - Defines runtime defaults for Ollama, cluster scope, DB, and step limits
- `.env` / `.env.example`
  - Runtime knobs for local and container execution

### 2. Operator entry points

- `src/openshift_sre_agent/cli.py`
  - `ask` for direct terminal use
  - `serve` for API mode on port `8000`
- `src/openshift_sre_agent/api.py`
  - FastAPI entrypoint
  - Mounts the generated docs site at `/guide`
  - Exposes `/chat` plus all history endpoints
- `ui/src/app-shell.jsx`
  - React-authored top-level operator shell for the custom documentation pages
- `docs/console.html`
  - Browser GUI for interactive runs

### 3. Agent reasoning layer

- `src/openshift_sre_agent/prompts.py`
  - System instructions and structured envelope contract
- `src/openshift_sre_agent/model_client.py`
  - Ollama request wrapper
- `src/openshift_sre_agent/agent.py`
  - Main reasoning loop
  - Tool selection, retry handling, final answer production
- `src/openshift_sre_agent/safety.py`
  - Read-only safety checks for CLI-style calls

### 4. Cluster collection layer

- `src/openshift_sre_agent/tools.py`
  - cluster data collection helpers across FinOps, security, platform, network, and data services
  - Returns structured result payloads that the agent can reason over

### 5. Persistence and aggregation layer

- `src/openshift_sre_agent/persistence.py`
  - Stores runs in `agent_runs`
  - Stores reasoning/tool steps in `agent_steps`
  - Extracts numeric metrics into `metric_snapshots`
  - Aggregates dashboard views for overview, run detail, tool detail, and metric detail

### 6. Dashboard rendering layer

- `docs/history.html`
  - Main historical dashboard shell
- `docs/assets/javascripts/app-shell.js`
  - Generated React bundle shared by the custom operator pages
- `docs/assets/javascripts/history-dashboard.js`
  - Fetches live history APIs
  - Renders executive summary cards, benchmark boards, charts, metric trends, run details, metric collection details, and CSV/PNG exports
  - Adds richer preview states, filled sparklines, variance indicators, SLA overlays, comparison meters, week-over-week storytelling, percentile bands, and exception rollups for faster scanning
- `docs/tool-drilldown.html`
  - Per-tool detail page
- `docs/assets/javascripts/tool-drilldown.js`
  - Tool-centric invocation history and trend rendering
- `docs/assets/stylesheets/agent-console.css`
  - Shared styles for the React shell, console, history dashboard, troubleshooting flows, tool drilldown, dark mode, detail panels, and executive section dividers

## Sequence: prompt to persisted dashboard data

```text
1. Operator opens a custom docs page and the shared React shell renders the page-level navigation, hero framing, and page accent theme.
2. Operator submits a prompt from the browser or CLI.
3. `api.py` or `cli.py` creates runtime settings.
4. `agent.py` sends the structured request to Ollama.
5. The model either asks for a tool or returns a final answer.
6. `tools.py` collects cluster data.
7. `agent.py` loops until a final answer is produced.
8. `persistence.py` stores:
   - prompt and final answer
   - step-by-step tool activity
   - extracted numeric metrics
9. The dashboard calls `/history/overview` and renders the high-level view, executive story cards, and comparison surfaces.
10. Clicking a run calls `/history/runs/{run_id}` for the full trace.
11. Clicking a tool opens the tool drilldown page backed by `/history/tools/{tool_name}`.
12. Clicking a metric calls `/history/metrics/{metric_key}` to show the detailed source collection.
13. The selected metric collection can be exported as CSV from the dashboard.

## Sequence: executive dashboard rendering

```text
1. `history.html` defines the dashboard structure and section dividers.
2. `app-shell.js` renders the shared navigation and hero frame.
3. `history-dashboard.js` loads `/history/overview`.
4. Summary data is transformed into:
  - KPI story cards
  - summary cards
  - benchmark ribbons
  - board brief commentary
  - time-window comparison cards
  - percentile latency bands
  - executive exception callouts
  - comparison meters
  - variance pills
  - trend sparklines
  - SLA target overlays
  - empty or preview state cards when live APIs are unavailable
5. `agent-console.css` applies the shared enterprise styling, subtle motion, and dark-mode variants.
```

## Sequence: metric drilldown and CSV export

```text
history.html
  └─ latest metric row or trend card click
       └─ history-dashboard.js
            └─ GET /history/metrics/{metric_key}
                 └─ api.py
                      └─ persistence.py.get_metric_detail(...)
                           ├─ read matching metric_snapshots rows
                           ├─ join matching agent_runs rows
                           └─ join source agent_steps payloads
            └─ render summary + sparkline + source collection payloads
            └─ export selected metric as CSV
```

## Diagram: file relationship map

```text
config.py ───────┐
                 ├── api.py ──> agent.py ──> model_client.py
.env(.example) ──┘        │          │
                          │          └──> tools.py ──> OpenShift APIs
                          │
ui/src/app-shell.jsx ──> ui/build.mjs ──> docs/assets/javascripts/app-shell.js
                          │
                          └──> persistence.py ──> MariaDB / SQLite
                                   │
                                   ├──> history.html + app-shell.js + history-dashboard.js
                                   └──> tool-drilldown.html + app-shell.js + tool-drilldown.js
```

## Where to extend next

- Add pagination for very large metric collections
- Add server-side CSV generation for bulk exports
- Add drillthrough from tool detail to a preselected run detail
- Add richer collection visualizations for nested list payloads
