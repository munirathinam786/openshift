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

The UI build now runs a docs JavaScript syntax guard before bundling so render-breaking errors in pages like `docs/assets/javascripts/platform-console.js` fail fast instead of quietly shipping an empty console shell.

## Documentation site

The MkDocs site under `docs/` is kept as a first-class operator surface.

The OpenShift SRE retains the same major feature lanes:

- `Architect Workspace`
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

The new `Architect Workspace` adds an OpenShift-native design lane rather than a straight port of the AWS architect feature. It includes:

- a platform-pattern catalog for OpenShift fleet, GitOps, disconnected, security, CNV, DR, and migration designs
- portfolio-derived OpenShift patterns grounded in Red Hat Architecture Center material, including external authentication, SAP clean core on ROSA, cloud sovereignty, cloud-native application delivery, telco 5G, event-driven automation, Model as a Service, AI self-service, and virtualization partner patterns
- live cluster-state grounding through the existing OpenShift toolkit
- a shared architecture pack plus separate `HLD`, `LLD`, and assessment document packs generated from the same design run
- a senior-architect skill set for preparing a shared architecture pack plus distinct `HLD` and `LLD` outputs with explicit background, objectives, AS-IS, TO-BE, topology, component, network, security, DR, migration, validation, and appendix structure
- enterprise document scaling rules that target review-ready `HLD` depth and implementation-grade `LLD` depth rather than short markdown summaries
- pgvector-backed knowledge retrieval for internal standards, prior designs, and external references
- research-link ingestion for Red Hat documentation or internal architecture sources
- draw.io, SVG, and PNG artifact generation from inside the container runtime
- enterprise-style multi-page composition that now includes dedicated hub / spoke cluster blocks, DMZ / firewall / bastion lanes, ACM / ACS / Quay / ODF placement bands, and rack / node / VLAN infrastructure topology views inspired by senior Red Hat architecture packs
- pattern-specific diagram shaping so the generated draw.io output carries source-specific lanes such as external-auth deployment paths and bootstrap access, cloud-native source-to-registry-to-promotion flows, telco supplementary 5G services, and event-driven automation task/result feedback chains

That means the architecture lane can build design packs from prompts alone, from live cluster state, or from a hybrid of prompt + live evidence + trained knowledge.

The `Platform Console` now also follows the same landing-shell visual language as the main `Agent Console`, with a platform-specific indigo accent and a runway-style launcher section that stays aligned with the shared operator shell patterns.

Its `Selected platform checks` catalog now exposes the broader OpenShift inspection surface as well, including cluster identity, project inventory, node pressure, pod and event risk, SCC and network-policy posture, resource quotas, image streams, build signals, and deeper core lifecycle signals such as cluster proxy, DNS operator, feature gate, scheduler, machine health check, and autoscaling posture alongside the existing lifecycle, ACM, ACS, OADP, DR, and CNV checks.

The page now also includes:

- saved platform-review templates backed by the investigations API
- watchlist creation and manual watchlist execution from the same workspace
- run-to-run comparison and readiness scoring inside the platform lane
- a fast non-LLM advisory pack lane backed by `/platform/advisory` for pre-change review packs
- a multi-cluster sweep lane powered by the platform sweep API
- optional streaming review execution for live evidence visibility
- a searchable feature selector that now covers cluster networking, ingress controllers, cluster proxy, DNS operator settings, feature gates, scheduler posture, machine health checks, cluster autoscaling, HPAs, PDBs, CronJobs, volume snapshots, RBAC bindings, service accounts, limit ranges, BuildConfigs, DeploymentConfigs, Knative services, VM snapshots, and Migration Toolkit resources

The `Security and governance` lane in the Platform Console now exposes the full platform-facing governance surface already available in the backend, including OAuth/LDAP posture, SCCs, RBAC bindings, service accounts, limit ranges, network policies, resource quotas, ACM fleet governance, and ACS rollout coverage.

This enterprise pass also expands the console and toolkit with a few high-value control-plane checks that are easy to miss until they hurt:

- aggregated `APIService` availability and extension registration drift
- `CertificateSigningRequest` approval / denial backlog for node and certificate operations
- mutating and validating admission webhook posture, including fail-open behavior and missing CA bundle wiring

This follow-on pass adds another high-value enterprise lane focused on control-plane observability and extension safety:

- monitoring and alert posture across Prometheus, Alertmanager, and `PrometheusRule` coverage
- control-plane certificate expiry and trust-bundle review across key OpenShift namespaces
- operator dependency / extension readiness scoring that combines cluster operators, subscriptions, CSVs, webhook posture, and aggregated APIs
- a batched `/platform/advisory` endpoint for fast, non-LLM operator review packs

## Rebuild workflow

To rebuild the UI bundle, regenerate the site, and refresh the Podman stack:

- `bash ./scripts/podman-dev-refresh.sh`

If you only want to validate the authored docs controllers before a push, run:

- `npm run validate:docs-js`

For container-first Python validation of the recent hardening work, run the focused suite from a Podman container with the repo bind-mounted:

- `podman run --rm -v "$PWD":/app -w /app localhost/openshift-sre-agent-local:dev sh -lc "python -m pip install '.[dev]' >/tmp/pytest-dev-install.log && python -m pytest tests/test_config_validation.py tests/test_api.py tests/test_persistence.py --no-cov -q"`

The API runtime now also exposes a richer operational health contract:

- `GET /healthz` for lightweight liveness
- `GET /readyz` for readiness across LLM and optional persistence dependencies
- `GET /healthz/full` for subsystem-level detail including provider, database, and docs-site status

The architect workspace adds these design-oriented API groups as well:

- `GET /architect/templates`
- `POST /architect/openshift-state`
- `POST /architect/clarify`
- `POST /architect/assessment`
- `POST /architect/diagram`
- `GET /architect/knowledge`
- `POST /architect/knowledge/train-link`
- `POST /architect/knowledge/train-files`
- `POST /architect/knowledge/search`
- `POST /architect/knowledge/clear`

The browser entrypoint for the architect workspace is also reachable through multiple redirect aliases so the page works consistently when this app is served standalone or nested under a higher-level Terraform IaC site path:

- `/architect.html`
- `/openshift-sre/architect.html`
- `/terraform-iac/openshift-sre/architect.html`

That keeps the generated `site/` output aligned with the documented source under `docs/` and refreshes the app image in one pass.
