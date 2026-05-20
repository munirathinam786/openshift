# Runtime, Docs, UI Build, and Tests

This page documents the remaining source files that make the project runnable, testable, and pleasant to operate from the browser.

Together with [`code-core.md`](code-core.md) and [`code-services.md`](code-services.md), this page completes the code walkthrough for the authored repository source.

## What lives in this layer

This part of the repository is responsible for four things:

- packaging and dependency management
- container and local stack execution
- documentation-site and browser UI delivery
- validation, rebuild, and regression testing

The main source files in this layer are:

- `pyproject.toml`
- `package.json`
- `ui/build.mjs`
- `ui/src/app-shell.jsx`
- `compose.yaml`
- `Containerfile`
- `mkdocs.yml`
- `scripts/podman-compose.sh`
- `scripts/podman-dev-refresh.sh`
- `docs/*.html`
- `docs/assets/javascripts/*.js`
- `docs/assets/stylesheets/agent-console.css`
- `tests/*.py`

Generated output such as `site/` is intentionally not treated as authored source, but it is produced directly from the files documented here.

## Packaging and Python entrypoints

### `pyproject.toml`

This file is the Python source of truth for packaging and test configuration.

It defines:

- the project name and metadata
- the Python version floor (`>=3.10`)
- runtime dependencies such as `fastapi`, `kubernetes`, `sqlalchemy`, `httpx`, and `typer`
- optional development dependencies used for tests and docs
- the console entrypoint `openshift-sre-agent`
- pytest configuration so tests run against `src/`

In practice, this is what makes both of these workflows possible:

- local development with `pip install -e .[dev]`
- container installation from the same source tree

### `src/openshift_sre_agent/__main__.py` and `src/openshift_sre_agent/cli.py`

These files are covered in the core docs, but from a runtime point of view they are the main execution boundary.

- `__main__.py` enables `python -m openshift_sre_agent`
- `cli.py` provides `ask` and `serve`

That means the same codebase supports:

- direct terminal prompting
- a FastAPI service on port `8000`
- containerized execution

## Frontend build pipeline

### Why there is a tiny frontend toolchain

The repository uses FastAPI and MkDocs for the main application experience, so a full SPA rewrite would have been architectural overkill.

Instead, the browser UX is upgraded with a very small React layer that only powers the shared shell for the custom operator pages.

This keeps the app:

- lightweight
- easy to rebuild inside the docs workflow
- compatible with the existing FastAPI + MkDocs architecture

### `package.json`

This file exists only for the documentation UI layer.

It adds:

- `react`
- `react-dom`
- `esbuild`

The key script is the UI bundle step that compiles the authored shell source into a plain browser asset that the docs pages can load.

### `ui/build.mjs`

This is the bridge between authored React code and generated browser code.

Its responsibilities are simple and deliberate:

- bundle `ui/src/app-shell.jsx`
- emit `docs/assets/javascripts/app-shell.js`
- use a production-friendly build suitable for the static docs site

That split matters because the repository keeps the readable source in `ui/src/`, while the docs site consumes the generated browser asset.

### `ui/src/app-shell.jsx`

This is the authored React component for the shared operator shell.

It provides:

- consistent cross-page navigation
- a hero block with page metadata supplied from inline JSON
- status badges, highlight cards, and quick links
- page accent theming through `data-shell-page`
- a graceful warning when the docs are opened directly from `file://` instead of the running app
- persistent workspace controls for theme, density, and motion preferences
- a live workspace capsule that shows mode, date/time, and current shell preferences
- section-jump navigation and clickable operator-shortcut chips powered by per-page metadata
- expandable feature-group decks that explain the capabilities of each custom page
- cursor-driven 3D tilt and glow effects for shell panels when motion is enabled

This shell is reused by the custom operator pages:

- `docs/console.html`
- `docs/finops-console.html`
- `docs/history.html`
- `docs/troubleshooting.html`
- `docs/llm-utilization.html`
- `docs/tool-drilldown.html`

## Docs site and operator pages

### `mkdocs.yml`

This is the docs navigation and site configuration file.

It wires together:

- the main Markdown pages
- the custom HTML operator pages
- the Material theme
- the Markdown extensions used across the documentation

The important architectural detail is that the custom operator pages live alongside the narrative docs, so operators can move between explanation and execution without switching applications.

### Custom docs pages

The custom HTML pages are not generic marketing pages; each one is a live operator surface.

#### `docs/console.html`

This is the browser console for `POST /chat`.

It includes:

- runtime override inputs for Ollama and cluster settings
- prompt templates for common investigations
- runtime-depth shortcuts for ECS service health and EKS nodegroup/add-on readiness checks
- deeper investigation shortcuts for operator health, route exposure, and OpenShift-native workload readiness
- final answer rendering
- reasoning trace rendering
- approval-oriented follow-up choices when the backend offers them
- FinOps and troubleshooting workflow surfaces
- shell-driven section navigation for the run surface, response hub, history snapshot, and trace lane
- richer feature metadata so the page explains what the run section and response section can do before the operator starts

#### `docs/history.html`

This page is the operational analytics workspace for persisted history.

It now includes:

- executive-style section dividers for scanning large dashboards
- KPI story cards above the numeric summary cards
- benchmark board surfaces for board-level comparisons
- operator-storytelling panels for this-week-vs-last-week comparisons, percentile latency bands, and exception rollups
- adjustable SLA controls for success rate and average duration
- export preset controls for standard, board review, and appendix-style snapshots
- a one-click weekly ops review export action that produces a board-friendly HTML packet
- refined chart cards for duration, tool usage, status, model, and region analysis
- richer empty and unavailable states for static preview
- metric and run drilldown panels
- CSV and PNG export actions
- shell-integrated section links for controls, overview, pattern analysis, metric intelligence, and trace drilldown
- feature-group summaries for the executive layer and traceability layer of the dashboard

#### `docs/troubleshooting.html`

This page is the guided incident-response surface.

The recent UX work made it more resilient by fixing overlapping layouts and turning the symptom/evidence/investigation areas into responsive cards that wrap correctly.

It now also exposes explicit shell metadata for:

- scenario setup
- evidence planning
- response review
- trace inspection

That makes the troubleshooting page behave more like an incident workbench than a single long form.

#### `docs/llm-utilization.html`

This page visualizes live model utilization data from `/ollama/utilization` and explains what can and cannot be observed from inside a local containerized setup.

It now documents its own runtime-health sections through the shared shell so operators can jump straight to the snapshot, loaded-model, process-visibility, or host-command areas.

#### `docs/tool-drilldown.html`

This page focuses on one tool at a time and is intended for follow-up analysis after using the historical dashboard.

It is the “what exactly is this tool doing over time?” view.

The shell metadata now makes the filter wall, summary lane, latest metric table, trend lane, and invocation list first-class navigable sections.

#### `docs/finops-console.html`

This page is the dedicated FinOps workspace.

It combines:

- operation launchers for optimization, chargeback, commitment, governance, and reporting flows
- workflow summaries derived from FinOps tool calls
- approval-queue-driven safe execution planning
- a report/export lane that enables PowerPoint and PDF export after a report is generated

#### `docs/security-console.html`

This page is the dedicated audit and cloud-security workspace.

It now combines:

- audit-profile launchers for SOX, CIS, PCI DSS, SOC 2, ISO 27001, NIST CSF, IAM hygiene, and resilience/governance review flows
- FinOps-style **Connection & credentials** controls so operators can choose the Ollama endpoint and model, plus request-scoped cluster scope/profile/credential overrides
- a dedicated security review launcher that turns the selected controls into a `/chat` request with runtime overrides
- a presentation/export lane for CSV, PowerPoint, PDF, and Word-compatible handoff packs
- clickable export buttons even before a review has been run, so the UI can explain the prerequisite instead of rendering the controls inert

The security page deliberately reuses the FinOps report-deck structure so the export surface looks and behaves the same across operator workspaces.

## Browser-side scripts

### `docs/assets/javascripts/app-shell.js`

This is the generated bundle produced from `ui/src/app-shell.jsx`.

It is not hand-edited. The authored source remains the React file.

### `docs/assets/javascripts/agent-console.js`

This script powers the browser console.

Its key responsibilities are:

- submit prompts to `/chat`
- pass request-scoped runtime overrides
- render final answers and reasoning steps
- improve operator guidance when APIs are unavailable during static preview
- support the approval-driven continuation workflow in the UI
- persist prompt history locally for faster re-use
- save and restore per-page drafts for prompt-heavy workflows
- render local session insight cards so operators can see how many runs they have made in the current browser session
- add answer-tooling actions such as copy/export of the latest response and trace payload
- render troubleshooting progress status so checklist completion and scenario framing stay visible beside the investigation flow

### `docs/assets/javascripts/history-dashboard.js`

This is the main browser controller for the historical dashboard.

It handles:

- filter state and auto-refresh
- client-side SLA state for success and duration targets
- export layout state for board-ready snapshot presets
- `/history/overview` loading
- `/history/runs/{run_id}` drilldown
- `/history/metrics/{metric_key}` drilldown
- dashboard CSV export
- selected metric CSV export
- dashboard PNG export
- weekly ops review HTML export
- executive summary storytelling cards
- benchmark ribbons and board brief generation from real overview payloads
- time-window comparison rendering for this week versus last week
- percentile latency band rendering from persisted duration data
- executive exception rollup rendering from backend-derived signals
- variance indicators across comparisons and latest metric deltas
- SLA target overlays on duration sparkline rendering
- richer sparkline rendering with area fills and focus points
- more polished empty-state and preview-state messaging

This file is the center of the “executive dashboard vibes” pass because it turns raw API payloads into structured operator visuals.

### `docs/assets/javascripts/finops-console.js`

This script implements the FinOps React workspace.

It handles:

- operation selection across the full FinOps catalog
- prompt generation and submission to `/chat`
- workflow construction from FinOps tool results
- action-card rendering and approval queue management
- a report-highlight lane for executive/report-style responses
- client-side `.pptx` generation so generated reports can be exported as PowerPoint decks directly from the tool
- client-side `.pdf` generation so the same report narrative can be downloaded as a lightweight executive brief

### `docs/assets/javascripts/security-console.js`

This script implements the Security Console React workspace.

It handles:

- audit profile selection and prompt generation for security/compliance review runs
- FinOps-style connection and credentials controls for Ollama URL, model selection, cluster scope/profile, temporary credentials, and SSL verification
- dynamic model discovery through `/ollama/models`
- `/chat` submission with request-scoped runtime overrides so the security workflow can target a different model or cluster credential context without restarting the stack
- summary cards, findings cards, evidence trace rendering, and export status handling
- client-side CSV, PowerPoint, PDF, and Word-compatible export generation for security handoff packs
- export-button interaction that stays clickable and shows guidance when no completed review is available yet

In practical terms, the security console now constructs a request body shaped like this:

```json
{
  "prompt": "Perform an platform security review using the selected audit profile...",
  "runtime": {
    "cluster_scope": "local-cluster",
    "local_model_name": "gpt-oss:20b",
    "ollama_base_url": "http://host.containers.internal:11434",
    "kube_context_name": "default",
    "openshift_api_url_field": "AKIA...",
    "openshift_token_field": "***",
    "openshift_namespace_field": "***",
    "verify_ssl": true,
    "agent_max_steps": 20
  },
  "tags": ["security-console", "sox"]
}
```

That is the core implementation detail behind the new UI: the page is not just collecting fields, it is passing them directly into the backend runtime override model exposed by `src/openshift_sre_agent/api.py`.

### `docs/assets/javascripts/llm-utilization.js`

This script renders live model utilization and the operator notes around it.

### `docs/assets/javascripts/tool-drilldown.js`

This script renders per-tool trend and invocation detail views.

### `docs/assets/stylesheets/agent-console.css`

This stylesheet is the shared design system for every custom operator page.

It now covers:

- the React shell frame and navigation
- per-page accent themes
- console forms and action pills
- troubleshooting cards and workflow layouts
- history dashboard summary cards and trend cards
- time-window storytelling cards, percentile-band components, and executive exception cards
- benchmark cards, variance pills, and board-brief layouts
- section dividers for executive scanning
- empty-state surfaces with subtle motion
- data-viz styling such as sparkline fills, SLA target overlays, benchmark ribbons, and comparison meters
- dark-mode variants for all major surfaces
- a 3D shell layer with glowing orbs, perspective tilt, glassy workspace capsules, and feature decks
- persistent density and motion-mode styling hooks through `data-density` and `data-motion`
- prompt toolbar, session rail, and troubleshooting progress components shared by the live console pages

This file is where the visual consistency of the operator experience is enforced.

### `docs/assets/stylesheets/finops-console.css`

This stylesheet adds FinOps-specific presentation on top of the shared operator design system.

It now covers:

- the FinOps workspace hero and stat capsules
- enhanced launcher/result panel styling
- the executive report export lane
- report summary cards and export guidance surfaces
- FinOps-specific responsive and dark-mode polish

It now also provides the shared settings-panel styling used by both FinOps and Security, including the model-picker row that pairs the model dropdown with the refresh action.

### `docs/assets/stylesheets/security-console.css`

This stylesheet is intentionally small.

Its job is to keep only the security-page-specific layout hooks, while relying on `finops-console.css` for the heavy visual treatment.

That means it now owns:

- the security launcher grid layout
- the multi-select sizing for platform security controls
- responsive layout behavior for the security review form
- small hero overrides that let the Security Console keep the same FinOps visual language with security-specific copy and content density

## Container and local stack files

### `Containerfile`

This image packages the app plus the generated site.

At build time it:

- copies the Python source
- copies the generated `site/` folder
- installs the package from `pyproject.toml`

At runtime it launches:

- `python -m openshift_sre_agent.cli serve --host 0.0.0.0 --port 8000`

That keeps the image simple: one service, one port, one bundled docs site.

### `compose.yaml`

This file defines the local multi-container stack.

The important services are:

- `app` for FastAPI + MkDocs delivery
- `db` for MariaDB-backed persistence

This is what enables the live historical dashboard instead of a purely ephemeral prompt experience.

### `scripts/podman-compose.sh`

This helper script normalizes Podman Compose invocation across environments.

Its purpose is to spare contributors from caring whether the host machine exposes `podman compose` or `podman-compose`.

### `scripts/podman-dev-refresh.sh`

This is the main rebuild path used in the project.

It is the preferred workflow because it keeps the full system aligned:

- rebuild frontend assets
- rebuild the MkDocs site
- refresh the Podman image and stack

In other words, it validates the operator UX in the same shape that the container will serve.

## Tests and validation

### `tests/test_agent.py`

Validates the reasoning loop, JSON envelope recovery, tool invocation behavior, and approval-oriented recovery logic.

### `tests/test_persistence.py`

Validates the persistence layer, metric extraction, and dashboard aggregation behavior.

This is especially important because the dashboard depends on shaped historical payloads rather than raw database rows.

### `tests/test_safety.py`

Validates the read-only oc CLI safety boundary.

These tests ensure the CLI fallback does not quietly turn into an unrestricted shell executor.

## Generated output and source-of-truth rules

The repository intentionally separates authored source from generated output.

### Authored source of truth

- `src/`
- `ui/src/`
- `docs/`
- `tests/`
- runtime/build config files in the repo root

### Generated artifacts

- `docs/assets/javascripts/app-shell.js` from `ui/src/app-shell.jsx`
- `site/` from MkDocs and the docs asset pipeline

This matters when making changes:

- edit the authored source first
- rebuild the generated assets
- validate the result through the Podman workflow

## Practical extension points

If you want to extend the runtime layer, these are the highest-leverage places:

- add new docs shell behaviors in `ui/src/app-shell.jsx`
- add new dashboard visuals in `docs/assets/javascripts/history-dashboard.js`
- add FinOps workflow or report-export behavior in `docs/assets/javascripts/finops-console.js`
- expand shared visual language in `docs/assets/stylesheets/agent-console.css`
- refine FinOps-specific visuals in `docs/assets/stylesheets/finops-console.css`
- add productivity helpers and workflow affordances in `docs/assets/javascripts/agent-console.js`
- add or modify container orchestration behavior in `compose.yaml` and `scripts/podman-dev-refresh.sh`
- add regression coverage in `tests/`

## Related pages

- [`code-core.md`](code-core.md)
- [`code-services.md`](code-services.md)
- [`end-to-end-flow.md`](end-to-end-flow.md)
- [`architecture.md`](architecture.md)
