# Operations Guide

## Local prerequisites

- Python `3.10+`
- either Ollama running locally **or** credentials for a hosted provider such as OpenAI, Azure OpenAI, Anthropic, Gemini, or OpenRouter
- an installed local model, for example `gpt-oss:20b`, when you want local inference
- access to an OpenShift cluster through `~/.kube/config` or an explicit API URL and bearer token
- Podman installed for the default container workflow

## LLM provider setup

The operator pages and backend runtime support both local Ollama and hosted providers.

You can configure providers in two ways:

1. set process-wide defaults in `.env`
2. choose a provider per request from the page-level settings panels

For hosted providers, the core runtime fields are:

- `LLM_PROVIDER`
- `LLM_MODEL_NAME`
- `LLM_BASE_URL`
- `LLM_API_KEY`
- `LLM_API_VERSION`
- `LLM_ORGANIZATION`

The browser pages automatically switch the settings form between Ollama-only fields and hosted-provider auth fields based on the selected provider.

For a full provider-by-provider reference, see [`LLM Providers`](llm-providers.md).

## Example operator prompts

- `Investigate cluster operator health and summarize degraded components.`
- `List warning events in openshift-monitoring and tell me which ones look most urgent.`
- `Inspect pending pods and restart-heavy workloads in my default projects.`
- `Run a read-only oc command to get clusterversion.`
- `Review routes, ingresses, and services for exposure or TLS gaps.`
- `Inspect machine config pools, machine sets, and operator subscriptions for platform drift.`
- `Summarize SCC, network policy, and quota posture for the selected projects.`
- `Inspect PVC and PV status and identify storage bottlenecks.`
- `Review builds and image streams for delivery-path failures.`
- `Calculate an upgrade preflight score for the next OpenShift change window and explain any hold / no-go blockers.`
- `Assess SLO and error-budget posture using alerts, events, workload health, and exposure signals.`
- `Map operator upgrade blast radius across auth, ingress, storage, and workload surfaces.`
- `Correlate current alerts and warning events to the most relevant OpenShift runbook and next owner handoff.`

## Guided troubleshooting workflows

The docs console includes a troubleshooting workflow dropdown in the **Technical troubleshooting** module.
Each selection loads a scenario-specific investigation prompt and previews the evidence sources to inspect before you run the agent.

Coverage is intentionally broad across common OpenShift failure domains, including:

- cluster operator degradation and upgrade readiness
- node pressure, node readiness, and machine config drift
- deployment, statefulset, daemonset, and job rollout failures
- route, ingress, and service exposure problems
- PVC, PV, storage class, and quota-related scheduling failures
- SCC, network policy, and project isolation posture
- OLM subscription, CSV, build, and image stream drift

Example guided workflow detail:

- **Cluster operator degradation** checks cluster version, cluster operators, machine config pools, and related warning events
- **Pending or crashlooping workloads** checks workload health, pods, quotas, storage, and node pressure
- **Route or ingress exposure issues** checks services, routes, ingresses, and recent events

For planned SRE review work, the Platform Console adds dedicated lanes for:

- upgrade preflight scoring before a change window
- SLO / error-budget posture review before accepting more change
- operator upgrade blast-radius mapping for dependency-heavy estates
- alert-to-runbook correlation when noisy signals need a clear owner and playbook destination

This does not attempt to enumerate every OpenShift problem permutation, but it does provide a large guided catalog across the main platform, workload, storage, network, and security troubleshooting paths.

## LLM utilization page

The docs site includes a dedicated [`LLM Utilization`](llm-utilization.html) page.

It is designed to answer questions like:

- which Ollama model is loaded right now?
- how much VRAM is the loaded model using?
- what context window is active?
- is the runtime running in Podman or on the host?
- are host-level process metrics available from the current runtime?

The page reads the live `GET /ollama/utilization` endpoint and is also linked from the Historical Dashboard.

## Safety model

This project intentionally starts with a conservative posture.

- SDK tools are read-oriented and diagnostic
- CLI commands must be read-only `oc` commands
- shell chaining, redirection, and other dangerous operators are blocked
- mutating actions are not enabled by default

## Container model

The included `Containerfile` packages the API so it can run consistently in Podman.
It now also bakes the Red Hat Architecture Center draw.io offline libraries into the image at `/app/redhat-drawio`, sourced from `docs/assets/redhat-drawio/` in the repo.
The service listens on port `8000`.

The default container entrypoints in this repo are:

- `bash ./scripts/podman-compose.sh ...`
- `bash ./scripts/podman-dev-refresh.sh`

On macOS, the container should use `http://host.containers.internal:11434` to reach Ollama running on the host.
The architect knowledge-training flow now retries the equivalent host aliases (`host.containers.internal`, `host.docker.internal`, and `localhost` where appropriate) and uses a short connection timeout so an unreachable alias fails fast instead of hanging the embeddings request.
If you want cluster and CLI access inside the container, mount `~/.kube` read-only into `/root/.kube`.
If the container cannot validate your enterprise or self-signed cluster trust chain, use `OPENSHIFT_VERIFY_SSL=false` temporarily or provide a trusted kubeconfig and CA chain.
If you want to import the official Red Hat draw.io libraries offline from inside the container, use the vendored `.mxlibrary` files in `/app/redhat-drawio` or the built-docs copies under `/guide/assets/redhat-drawio/`.
The Architect Workspace now also preloads those vendored Red Hat libraries automatically inside the embedded diagrams.net editor, so the offline bundle is available by default without a manual import step.

## Historical metrics database

The local stack supports a small MySQL-compatible database in its own container.

- `compose.yaml` starts `MariaDB 11.4`
- the database uses the named volume `openshift-sre-agent-mysql-data`
- the app stores prompt runs, reasoning steps, and extracted metrics into that database
- the browser dashboard reads historical summaries and trend series from `GET /history/overview`

Suggested Podman workflow:

1. `bash ./scripts/podman-dev-refresh.sh`
2. open `http://127.0.0.1:8000/`
3. run a few prompts that produce counts, warning summaries, or posture metrics
4. review the historical dashboard section after each run

## Suggested future enhancements

- add direct Prometheus, Alertmanager, or Loki integrations
- add configurable approval workflows for mutating actions
- add role-based tool policies per environment
- add traces and evaluations for prompt/tool quality

## Playbook index

- [`Audit & Security`](playbook-audit-security.md)
- [`Advanced Security & Governance`](playbook-advanced-security-governance.md)
- [`Capacity & Optimization`](playbook-finops.md)
- [`Platform & Automation`](playbook-platform-automation.md)
- [`Storage & Governance`](playbook-storage-governance.md)
