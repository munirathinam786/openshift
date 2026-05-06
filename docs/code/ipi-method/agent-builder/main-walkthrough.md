# main.tf — Line-by-Line Walkthrough

!!! info "File Location"
    `ipi-method/agent-builder/main.tf`

This is the **root orchestration file** — the "brain" of the deployment. It does NOT deploy anything directly. Instead, it:

1. Computes local values from variables
2. Calls 14 child modules in the correct dependency order
3. Passes the right variables to each module

---

## Architecture: What main.tf Orchestrates

![Agent Builder Module Dependency Architecture](../../../diagrams/code/13-agent-builder-module-deps.svg)

[:material-download: Download draw.io source](../../../diagrams/code/13-agent-builder-module-deps.drawio){ .md-button .md-button--primary }

---

## Section 1: Header Comments (Lines 1–16)

```hcl linenums="1"
# Author: Sathishkumar Munirathinam
# Agent Builder Factory — Deployment on OpenShift Baremetal
# Deploys the complete Kyndryl Agent Builder platform including:
#   - PostgreSQL (Temporal + LiteLLM backend)
#   - MongoDB (Agent metadata)
#   - Redis (Caching layer)
#   - Temporal Server + Web UI (Workflow orchestration)
#   - Temporal Workers (Activity execution)
#   - LiteLLM Proxy (Multi-model LLM gateway)
#   - Ollama (Local LLM — Llama3)
#   - Agent Builder API (FastAPI backend)
#   - Agent Builder UI (React frontend)
#   - Tool Catalog (MCP Tools Discovery)
#   - Agent Deployment Service
#   - Agent Registry
#   - A2A Gateway (Agent-to-Agent communication)
```

These comments serve as a **manifest** — listing every service this file deploys. A reader can immediately understand the scope.

---

## Section 2: Locals Block (Lines 22–27)

```hcl linenums="22"
locals {
  kubeconfig   = "/home/${var.bastion_user}/ocp/${var.cluster_name}/auth/kubeconfig"
  ab_namespace = var.agent_builder_namespace
  registry     = var.container_registry
  domain       = "${var.agent_builder_subdomain}.apps.${var.cluster_name}.${var.base_domain}"
}
```

### What `locals` does

The `locals` block defines **computed values** that are reused across multiple module calls. This avoids repeating the same string interpolation many times.

### Line-by-line:

#### `kubeconfig` (Line 23)

```hcl
kubeconfig = "/home/${var.bastion_user}/ocp/${var.cluster_name}/auth/kubeconfig"
```

| Part | Evaluates To (with example values) |
|---|---|
| `${var.bastion_user}` | `kni` |
| `${var.cluster_name}` | `ocp-ai` |
| **Full result** | `/home/kni/ocp/ocp-ai/auth/kubeconfig` |

!!! info "What is kubeconfig?"
    The kubeconfig file contains credentials to connect to the OpenShift API server. It is created by the OpenShift installer on the bastion host. Every `oc` command needs this file via `export KUBECONFIG=...`.

#### `ab_namespace` (Line 24)

```hcl
ab_namespace = var.agent_builder_namespace
```

Simple alias — saves typing `var.agent_builder_namespace` in every module call. Evaluates to `"agent-builder"`.

#### `registry` (Line 25)

```hcl
registry = var.container_registry
```

Evaluates to `"quay-host:8443/agent-builder"`. Used to construct container image references.

#### `domain` (Line 26)

```hcl
domain = "${var.agent_builder_subdomain}.apps.${var.cluster_name}.${var.base_domain}"
```

| Part | Value |
|---|---|
| `${var.agent_builder_subdomain}` | `agent-builder` |
| `${var.cluster_name}` | `ocp-ai` |
| `${var.base_domain}` | `example.com` |
| **Full result** | `agent-builder.apps.ocp-ai.example.com` |

This domain is the base for all service routes:

- `ui.agent-builder.apps.ocp-ai.example.com` — UI
- `api.agent-builder.apps.ocp-ai.example.com` — API
- `litellm.agent-builder.apps.ocp-ai.example.com` — LiteLLM

---

## Section 3: Module Calls (Lines 33–340)

Each module call follows this pattern:

```hcl
module "module_name" {
  source = "./modules/folder-name"    # Path to the module

  # Variables passed to the module
  variable1 = var.some_variable
  variable2 = local.some_local

  # Execution order control
  depends_on = [module.prerequisite]
}
```

### Module 1: Namespace (Lines 33–42)

```hcl linenums="33"
module "namespace" {
  source = "./modules/namespace"

  bastion_host    = var.bastion_host
  bastion_user    = var.bastion_user
  bastion_ssh_key = var.bastion_ssh_private_key_file
  kubeconfig      = local.kubeconfig
  namespace       = local.ab_namespace
}
```

| Line | What It Does |
|---|---|
| `source = "./modules/namespace"` | Tells Terraform to load code from the `modules/namespace/` directory |
| `bastion_host = var.bastion_host` | Passes the bastion IP from root variables to the module |
| `bastion_user = var.bastion_user` | Passes SSH user |
| `bastion_ssh_key = var.bastion_ssh_private_key_file` | Passes SSH key path |
| `kubeconfig = local.kubeconfig` | Passes the computed kubeconfig path |
| `namespace = local.ab_namespace` | Passes the namespace name (`"agent-builder"`) |

!!! tip "No `depends_on`"
    The namespace module has no dependencies — it's the **first thing deployed**. All other modules depend on it.

**What happens inside this module:** SSHs into bastion → runs `oc apply` to create the Kubernetes Namespace.

---

### Module 2: PostgreSQL (Lines 48–62)

```hcl linenums="48"
module "postgresql" {
  source = "./modules/postgresql"

  bastion_host    = var.bastion_host
  bastion_user    = var.bastion_user
  bastion_ssh_key = var.bastion_ssh_private_key_file
  kubeconfig      = local.kubeconfig
  namespace       = local.ab_namespace

  postgres_password       = var.postgres_password
  postgres_storage_size   = var.postgres_storage_size
  postgres_storage_class  = var.storage_class

  depends_on = [module.namespace]
}
```

| Line | What It Does |
|---|---|
| `postgres_password = var.postgres_password` | Passes the sensitive password to the module |
| `postgres_storage_class = var.storage_class` | Note: root variable is `storage_class` but module variable is `postgres_storage_class` — mapping happens here |
| `depends_on = [module.namespace]` | PostgreSQL cannot deploy until the namespace exists |

**What happens inside:** Creates a Secret (credentials) → ConfigMap (init SQL) → StatefulSet + PVC → Service. The init SQL creates 4 databases: `temporal_db`, `temporal_visibility_db`, `litellm_db`, `agent_registry_db`.

---

### Module 3: MongoDB (Lines 68–82)

```hcl linenums="68"
module "mongodb" {
  source = "./modules/mongodb"

  bastion_host    = var.bastion_host
  bastion_user    = var.bastion_user
  bastion_ssh_key = var.bastion_ssh_private_key_file
  kubeconfig      = local.kubeconfig
  namespace       = local.ab_namespace

  mongodb_root_password  = var.mongodb_root_password
  mongodb_storage_size   = var.mongodb_storage_size
  mongodb_storage_class  = var.storage_class

  depends_on = [module.namespace]
}
```

Same pattern as PostgreSQL. Deploys a MongoDB StatefulSet for storing agent metadata and conversation history.

---

### Module 4: Redis (Lines 88–102)

```hcl linenums="88"
module "redis" {
  source = "./modules/redis"

  bastion_host    = var.bastion_host
  bastion_user    = var.bastion_user
  bastion_ssh_key = var.bastion_ssh_private_key_file
  kubeconfig      = local.kubeconfig
  namespace       = local.ab_namespace

  redis_password      = var.redis_password
  redis_storage_size  = var.redis_storage_size
  redis_storage_class = var.storage_class

  depends_on = [module.namespace]
}
```

Deploys Redis for LiteLLM response caching. Configured with `maxmemory 2gb` and LRU eviction policy.

---

### Module 5: Temporal Server (Lines 108–121)

```hcl linenums="108"
module "temporal" {
  source = "./modules/temporal"

  bastion_host    = var.bastion_host
  bastion_user    = var.bastion_user
  bastion_ssh_key = var.bastion_ssh_private_key_file
  kubeconfig      = local.kubeconfig
  namespace       = local.ab_namespace

  postgres_host     = "agent-builder-postgresql.${local.ab_namespace}.svc.cluster.local"
  postgres_password = var.postgres_password
  temporal_ui_host  = "temporal.${local.domain}"

  depends_on = [module.postgresql]
}
```

**Key detail — Kubernetes DNS (Line 118):**

```hcl
postgres_host = "agent-builder-postgresql.${local.ab_namespace}.svc.cluster.local"
# Result: "agent-builder-postgresql.agent-builder.svc.cluster.local"
```

This is a **Kubernetes internal DNS name**. The format is: `<service-name>.<namespace>.svc.cluster.local`

| Part | Value | Meaning |
|---|---|---|
| `agent-builder-postgresql` | Service name | Matches the Service created by the PostgreSQL module |
| `agent-builder` | Namespace | The namespace where PostgreSQL runs |
| `svc.cluster.local` | Standard suffix | Kubernetes DNS suffix for services |

!!! info "Why not use an IP address?"
    Pod IPs change when pods restart. The Kubernetes DNS name always resolves to the current pod. This is why every module creates a `Service` resource — it provides a stable DNS endpoint.

**Route construction (Line 119):**

```hcl
temporal_ui_host = "temporal.${local.domain}"
# Result: "temporal.agent-builder.apps.ocp-ai.example.com"
```

---

### Module 6: Ollama — Conditional (Lines 127–143)

```hcl linenums="127"
module "ollama" {
  source = "./modules/ollama"
  count  = var.enable_ollama ? 1 : 0

  bastion_host    = var.bastion_host
  bastion_user    = var.bastion_user
  bastion_ssh_key = var.bastion_ssh_private_key_file
  kubeconfig      = local.kubeconfig
  namespace       = local.ab_namespace

  ollama_model          = var.ollama_model
  ollama_storage_size   = var.ollama_storage_size
  ollama_storage_class  = var.storage_class
  ollama_gpu_enabled    = var.ollama_gpu_enabled
  ollama_gpu_limit      = var.ollama_gpu_limit
  ollama_memory_limit   = var.ollama_memory_limit
  ollama_cpu_limit      = var.ollama_cpu_limit

  depends_on = [module.namespace]
}
```

**The `count` meta-argument (Line 129):**

```hcl
count = var.enable_ollama ? 1 : 0
```

This is a **ternary expression**: `condition ? value_if_true : value_if_false`

- If `enable_ollama = true` → `count = 1` → module is created (1 instance)
- If `enable_ollama = false` → `count = 0` → module is **skipped entirely**

This is Terraform's way of implementing **conditional deployment**.

---

### Module 7: LiteLLM Proxy (Lines 149–173)

```hcl linenums="149"
module "litellm" {
  source = "./modules/litellm"

  bastion_host    = var.bastion_host
  bastion_user    = var.bastion_user
  bastion_ssh_key = var.bastion_ssh_private_key_file
  kubeconfig      = local.kubeconfig
  namespace       = local.ab_namespace

  litellm_master_key       = var.litellm_master_key
  postgres_host            = "agent-builder-postgresql.${local.ab_namespace}.svc.cluster.local"
  postgres_password        = var.postgres_password
  redis_host               = "agent-builder-redis.${local.ab_namespace}.svc.cluster.local"
  redis_password            = var.redis_password
  anthropic_api_key        = var.anthropic_api_key
  azure_openai_endpoint    = var.azure_openai_endpoint
  azure_openai_key         = var.azure_openai_key
  openai_api_key           = var.openai_api_key
  litellm_host             = "litellm.${local.domain}"

  enable_ollama            = var.enable_ollama
  ollama_host              = var.enable_ollama ? "agent-builder-ollama.${local.ab_namespace}.svc.cluster.local" : ""
  ollama_model             = var.ollama_model

  enable_local_llm_laptop  = var.enable_local_llm_laptop
  local_llm_laptop_url     = var.local_llm_laptop_url

  depends_on = [module.postgresql, module.redis]
}
```

**Conditional variable (Line 170):**

```hcl
ollama_host = var.enable_ollama ? "agent-builder-ollama.${local.ab_namespace}.svc.cluster.local" : ""
```

If Ollama is disabled, pass an empty string instead of a DNS name. The LiteLLM config uses `%{if var.enable_ollama}` directives to conditionally include Ollama model entries.

**Multiple dependencies (Line 176):**

```hcl
depends_on = [module.postgresql, module.redis]
```

LiteLLM needs both PostgreSQL (for storing usage data) and Redis (for caching). Terraform waits for **both** to complete before deploying LiteLLM.

---

### Module 8: Temporal Workers (Lines 182–196)

```hcl linenums="182"
module "temporal_workers" {
  source = "./modules/temporal-workers"

  bastion_host    = var.bastion_host
  bastion_user    = var.bastion_user
  bastion_ssh_key = var.bastion_ssh_private_key_file
  kubeconfig      = local.kubeconfig
  namespace       = local.ab_namespace

  container_image  = "${local.registry}/agent-builder-temporal-workers:${var.image_tag}"
  temporal_host    = "agent-builder-temporal.${local.ab_namespace}.svc.cluster.local:7233"
  mongodb_uri      = "mongodb://root:${var.mongodb_root_password}@agent-builder-mongodb.${local.ab_namespace}.svc.cluster.local:27017"
  replicas         = var.temporal_workers_replicas

  depends_on = [module.temporal, module.mongodb]
}
```

**Container image construction (Line 191):**

```hcl
container_image = "${local.registry}/agent-builder-temporal-workers:${var.image_tag}"
# Result: "quay-host:8443/agent-builder/agent-builder-temporal-workers:latest"
```

This is how the container registry, image name, and tag are combined.

**MongoDB URI construction (Line 193):**

```hcl
mongodb_uri = "mongodb://root:${var.mongodb_root_password}@agent-builder-mongodb.${local.ab_namespace}.svc.cluster.local:27017"
```

Standard MongoDB connection string format: `mongodb://user:password@host:port`

---

### Modules 9–14: Application Services

The remaining modules follow the same pattern. Here's a summary of key details:

#### Agent Builder API (Lines 204–220)

```hcl
module "agent_builder_api" {
  source = "./modules/agent-builder-api"
  # ...
  container_image    = "${local.registry}/agent-builder-api:${var.image_tag}"
  litellm_proxy_base = "http://agent-builder-litellm.${local.ab_namespace}.svc.cluster.local:4000"
  api_host           = "api.${local.domain}"
  depends_on         = [module.temporal, module.litellm, module.mongodb]
}
```

Depends on **three modules** because the API needs all three services to function.

#### Agent Builder UI (Lines 237–249)

```hcl
module "agent_builder_ui" {
  source = "./modules/agent-builder-ui"
  # ...
  api_base_url      = "https://api.${local.domain}"
  ui_host           = "ui.${local.domain}"
  oidc_redirect_uri = "https://ui.${local.domain}"
  depends_on        = [module.agent_builder_api]
}
```

The UI only depends on the API — it's the last service in the main chain.

#### Tool Catalog (Lines 260–270)

```hcl
module "tool_catalog" {
  source = "./modules/tool-catalog"
  # ...
  depends_on = [module.namespace]
}
```

Independent — only needs the namespace. Can deploy in parallel with databases.

#### Agent Deployment Service (Lines 280–293)

```hcl
module "agent_deployment_service" {
  source = "./modules/agent-deployment-service"
  # ...
  depends_on = [module.temporal, module.mongodb]
}
```

#### Agent Registry (Lines 303–317)

```hcl
module "agent_registry" {
  source = "./modules/agent-registry"
  # ...
  depends_on = [module.postgresql, module.mongodb]
}
```

Needs both PostgreSQL (for structured data) and MongoDB (for document data).

#### A2A Gateway (Lines 327–340)

```hcl
module "a2a_gateway" {
  source = "./modules/a2a-gateway"
  # ...
  depends_on = [module.agent_registry]
}
```

The A2A Gateway talks to the Agent Registry to discover agents for inter-agent communication.

---

## Deployment Order Summary

Based on `depends_on` chains, Terraform deploys in this order:

| Phase | Module(s) | Why This Order |
|---|---|---|
| 1 | `namespace` | Must exist before anything else |
| 2 | `postgresql`, `mongodb`, `redis`, `ollama`, `tool_catalog` | All depend only on namespace — **deployed in parallel** |
| 3 | `temporal` | Needs PostgreSQL |
| 4 | `litellm` | Needs PostgreSQL + Redis |
| 5 | `temporal_workers`, `agent_deployment_service`, `agent_registry` | Need Temporal and/or databases |
| 6 | `agent_builder_api` | Needs Temporal + LiteLLM + MongoDB |
| 7 | `agent_builder_ui`, `a2a_gateway` | UI needs API; A2A needs Registry |

---

## How to Write `main.tf` From Scratch

1. **Define `locals`** for values used across multiple modules
2. **Create the namespace module first** — everything depends on it
3. **Add database modules** with `depends_on = [module.namespace]`
4. **Add application modules** in dependency order
5. **For each module, ask:** "What services does this need to already be running?"
6. **List those dependencies** in `depends_on = [module.dep1, module.dep2]`
7. **Construct Kubernetes DNS names** as `<service>.<namespace>.svc.cluster.local`
8. **Construct container images** as `${local.registry}/<image-name>:${var.image_tag}`
9. **Construct route hostnames** as `<prefix>.${local.domain}`
