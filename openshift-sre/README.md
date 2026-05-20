# OpenShift SRE Local Agent

`OpenShift SRE Local Agent` is a Python-based AI agent that can connect to either a **local Ollama model** or a **hosted external LLM provider** and perform **guarded Red Hat OpenShift operational investigations**.

It keeps the same product shape as the initial proof-of-concept:

- a CLI for direct operator use
- an HTTP API that runs on port `8000`
- a MkDocs site with interactive consoles
- persistence backed by MariaDB or SQLite-compatible SQLAlchemy wiring
- historical analytics, watchlists, drift review, and export flows
- Podman-first local rebuild scripts

## What this OpenShift variant investigates

The OpenShift toolkit focuses on read-only cluster and workload investigations such as:

- cluster identity, version, upgrade state, and health conditions
- cluster operators and degraded/progressing availability posture
- projects, quotas, and namespace-level hygiene
- nodes, node pressure signals, readiness, and scheduling impact
- pods, workload health, deployments, statefulsets, daemonsets, jobs, and crash loops
- routes, services, ingresses, and edge exposure checks
- persistent storage posture across PVs, PVCs, and storage classes
- machine config pools and machine sets for platform drift checks
- operator subscriptions and ClusterServiceVersions for lifecycle and upgrade diagnostics
- security context constraints and network policies for security posture investigations
- image streams, build pipelines, and recent events for delivery-path troubleshooting
- carefully validated **read-only** `oc` CLI execution for edge cases when the CLI is available

## Why this design still works

The same separation of concerns is preserved:

- `model_client.py` handles Ollama and hosted providers
- `agent.py` runs the reasoning loop and selects the right tools
- `tools.py` exposes guarded OpenShift and Kubernetes inspection tools
- `persistence.py` stores prompts, runs, steps, watchlists, queue state, and extracted metrics
- `api.py` exposes the runtime over FastAPI
- `cli.py` provides terminal workflows for local operators

## Quick start

1. Install Python dependencies.
2. Either make sure Ollama is running locally **or** configure a hosted provider API key and endpoint.
3. Make sure OpenShift credentials are available through either `~/.kube/config` or explicit API/token settings.
4. Start the API on port `8000`.

### Podman-first local workflow

This repository keeps **Podman as the default container workflow**.

- use `bash ./scripts/podman-compose.sh ...` as the stable compose entrypoint
- use `bash ./scripts/podman-dev-refresh.sh` to rebuild the docs and refresh the local stack
- use the generated MkDocs site and live API at `http://127.0.0.1:8000/`

For container runs on macOS with Podman, `http://host.containers.internal:11434` is the normal Ollama base URL from inside the container.

The compose stack now mounts `~/.kube` read-only so the container can reuse your local OpenShift access context.

## Environment variables

See `.env.example` for the complete list.

The most important OpenShift-specific settings are:

- `OPENSHIFT_CLUSTER`: label stored with historical runs and used as the default cluster scope
- `OPENSHIFT_NAMESPACE`: default project/namespace for workload-oriented investigations
- `OPENSHIFT_PROJECTS`: optional comma-separated default project sweep list
- `OPENSHIFT_API_URL`: optional direct API endpoint override
- `OPENSHIFT_TOKEN`: optional bearer token override
- `KUBECONFIG_PATH`: optional kubeconfig path override
- `KUBECONFIG_CONTEXT`: optional kubeconfig context override
- `OPENSHIFT_VERIFY_SSL`: whether API TLS validation stays enabled
- `DATABASE_ENABLED`, `DATABASE_URL`, `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`: persistence settings for historical dashboards

## Container runtime

The project includes a `Containerfile` and is intended to run with Podman.

For multi-container local development, `compose.yaml` provides:

- a `MariaDB` container for run history and metric storage
- a named persistent volume for the database
- default app wiring so dashboards can render history from `/history/overview`
- a kubeconfig mount so the OpenShift runtime can reuse local credentials

Start the local stack with:

- `bash ./scripts/podman-compose.sh -f compose.yaml up -d --build`

For the normal rebuild-and-refresh flow, run:

- `bash ./scripts/podman-dev-refresh.sh`

## Documentation site

The MkDocs site under `docs/` is kept as a first-class operator surface.

The OpenShift SRE retains the same major feature lanes:

- `Agent Console`
- `Platform Console`
- `Troubleshooting`
- `Security Console`
- `FinOps Console`
- `Posture Radar`
- `Watchlists`
- `Drift Diff`
- `Historical Dashboard`
- `Tool Drilldown`
- `LLM Utilization`

Those pages continue to use the live FastAPI endpoints and the shared React operator shell, while the backend logic now targets OpenShift and Kubernetes operational posture.

The `Platform Console` now also follows the same landing-shell visual language as the main `Agent Console`, with a platform-specific indigo accent and a runway-style launcher section that stays aligned with the shared operator shell patterns.

## Rebuild workflow

To rebuild the UI bundle, regenerate the site, and refresh the Podman stack:

- `bash ./scripts/podman-dev-refresh.sh`

That keeps the generated `site/` output aligned with the documented source under `docs/` and refreshes the app image in one pass.
