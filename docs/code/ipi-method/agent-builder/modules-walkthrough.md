# Modules Deep Dive — All 14 Modules Explained

!!! info "File Location"
    `ipi-method/agent-builder/modules/` — 14 subdirectories, each with a single `main.tf`

This page provides a **line-by-line breakdown** of every module. Each module follows the same pattern but deploys different Kubernetes resources. By understanding one module thoroughly, you can understand all 14.

---

## The Universal Module Pattern

Every module in this project follows this structure:

```hcl
# 1. Declare variables (inline — no separate variables.tf)
variable "bastion_host" { type = string }
variable "namespace" { type = string }
# ...more variables...

# 2. Create a Secret (if passwords/keys are needed)
resource "null_resource" "service_secret" {
  connection { ... }
  provisioner "remote-exec" {
    inline = ["oc create secret generic ... --dry-run=client -o yaml | oc apply -f -"]
  }
}

# 3. Create the main resources (Deployment, Service, Route, PVC, ConfigMap)
resource "null_resource" "service" {
  connection { ... }
  provisioner "remote-exec" {
    inline = ["cat <<'EOF' | oc apply -f -", "apiVersion: ...", "EOF"]
  }
  depends_on = [null_resource.service_secret]
}

# 4. Export outputs
output "service_name" { value = "agent-builder-service" }
output "port" { value = 8000 }
```

### Why Inline Variables?

Each module declares its variables directly in `main.tf` instead of a separate `variables.tf`. This is valid Terraform — the file name doesn't matter. Using a single file per module keeps things simple when the module is small.

### The Connection Block

Every `null_resource` includes:

```hcl
connection {
  type        = "ssh"
  host        = var.bastion_host
  user        = var.bastion_user
  private_key = file(var.bastion_ssh_key)
}
```

| Field | Purpose |
|---|---|
| `type = "ssh"` | Use SSH protocol (not WinRM or other) |
| `host` | The bastion host IP/hostname |
| `user` | SSH username |
| `private_key = file(var.bastion_ssh_key)` | `file()` reads the SSH key file from disk and passes its contents |

### The `--dry-run=client -o yaml | oc apply` Pattern

```bash
oc create secret generic name -n namespace \
  --from-literal=KEY='value' \
  --dry-run=client -o yaml | oc apply -f -
```

This is an **idempotent pattern**:

1. `oc create secret ... --dry-run=client -o yaml` — **generates** the YAML without applying it
2. `| oc apply -f -` — **applies** the YAML (creates or updates)

If the secret already exists, `oc apply` updates it instead of failing with "already exists".

### The Heredoc Pattern

```bash
cat <<'EOF' | oc apply -f -
apiVersion: v1
kind: Deployment
...
EOF
```

- `<<'EOF'` starts a **heredoc** (here-document) — all text until the closing `EOF` is treated as a single string
- The **single quotes** around `'EOF'` prevent shell variable expansion inside the heredoc
- `| oc apply -f -` pipes the YAML to `oc apply`, which reads from stdin (`-f -`)

!!! warning "Why single quotes on `'EOF'`?"
    Without quotes (`<<EOF`), the shell would try to expand `${}` variables. With quotes (`<<'EOF'`), the shell passes the text verbatim. However, Terraform's `${var.name}` interpolation **still works** because Terraform processes the string before the shell sees it.

---

## Module 1: Namespace

**Purpose:** Creates the Kubernetes namespace where all Agent Builder services will run.

### Variables

```hcl
variable "bastion_host" { type = string }
variable "bastion_user" { type = string }
variable "bastion_ssh_key" { type = string }
variable "kubeconfig" { type = string }
variable "namespace" { type = string }
```

These 5 "connection" variables appear in every module. They enable SSH access to the bastion host.

### Resource

```hcl
resource "null_resource" "namespace" {
  provisioner "remote-exec" {
    inline = [
      "export KUBECONFIG=${var.kubeconfig}",

      "cat <<'EOF' | oc apply -f -",
      "apiVersion: v1",
      "kind: Namespace",
      "metadata:",
      "  name: ${var.namespace}",
      "  labels:",
      "    app.kubernetes.io/part-of: agent-builder",
      "    app.kubernetes.io/managed-by: terraform",
      "  annotations:",
      "    openshift.io/description: \"Kyndryl Agent Builder Factory Platform\"",
      "EOF",
    ]
  }
}
```

| Line | Kubernetes Concept | Explanation |
|---|---|---|
| `export KUBECONFIG=...` | - | Sets the kubeconfig for `oc` commands in this session |
| `apiVersion: v1` | API version | Namespaces use the core `v1` API |
| `kind: Namespace` | Resource type | Creates a Kubernetes Namespace |
| `name: ${var.namespace}` | Resource name | Set to `"agent-builder"` |
| `app.kubernetes.io/part-of` | Standard label | Groups all resources as part of `agent-builder` |
| `app.kubernetes.io/managed-by` | Standard label | Indicates Terraform manages this resource |
| `openshift.io/description` | OpenShift annotation | Shows description in the OpenShift console |

### Output

```hcl
output "namespace" {
  value = var.namespace
}
```

Passes the namespace name back to the root module (not used directly but available).

---

## Module 2: PostgreSQL

**Purpose:** Deploys a PostgreSQL 15 StatefulSet with init scripts to create 4 databases.

### Step 1: Create Credentials Secret

```hcl
resource "null_resource" "postgresql_secret" {
  provisioner "remote-exec" {
    inline = [
      "export KUBECONFIG=${var.kubeconfig}",
      "oc create secret generic agent-builder-postgresql-credentials -n ${var.namespace} \\",
      "  --from-literal=POSTGRES_USER=agentbuilder \\",
      "  --from-literal=POSTGRES_PASSWORD='${var.postgres_password}' \\",
      "  --from-literal=POSTGRES_DB=agentbuilder \\",
      "  --dry-run=client -o yaml | oc apply -f -",
    ]
  }
}
```

Creates a Kubernetes Secret with 3 keys:

| Key | Value | Used By |
|---|---|---|
| `POSTGRES_USER` | `agentbuilder` | PostgreSQL container reads this to create the default user |
| `POSTGRES_PASSWORD` | *(from variable)* | Password for the `agentbuilder` user |
| `POSTGRES_DB` | `agentbuilder` | Default database name |

### Step 2: Init SQL ConfigMap

```hcl
resource "null_resource" "postgresql_init_script" {
  provisioner "remote-exec" {
    inline = [
      "cat <<'CMEOF' | oc apply -f -",
      "apiVersion: v1",
      "kind: ConfigMap",
      "metadata:",
      "  name: agent-builder-postgresql-init",
      "  namespace: ${var.namespace}",
      "data:",
      "  init.sql: |",
      "    CREATE DATABASE temporal_db;",
      "    CREATE DATABASE temporal_visibility_db;",
      "    CREATE DATABASE litellm_db;",
      "    CREATE DATABASE agent_registry_db;",
      "    GRANT ALL PRIVILEGES ON DATABASE temporal_db TO agentbuilder;",
      "    GRANT ALL PRIVILEGES ON DATABASE temporal_visibility_db TO agentbuilder;",
      "    GRANT ALL PRIVILEGES ON DATABASE litellm_db TO agentbuilder;",
      "    GRANT ALL PRIVILEGES ON DATABASE agent_registry_db TO agentbuilder;",
      "CMEOF",
    ]
  }
  depends_on = [null_resource.postgresql_secret]
}
```

This ConfigMap stores SQL that runs when PostgreSQL first starts. It creates 4 databases:

| Database | Used By |
|---|---|
| `temporal_db` | Temporal workflow engine (execution history) |
| `temporal_visibility_db` | Temporal workflow search/listing |
| `litellm_db` | LiteLLM usage tracking and model configs |
| `agent_registry_db` | Agent Registry metadata |

### Step 3: StatefulSet + PVC + Service

The main resource creates three Kubernetes objects in a single `oc apply`:

**PersistentVolumeClaim:**

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: agent-builder-postgresql-data
spec:
  accessModes:
    - ReadWriteOnce
  storageClassName: ocs-storagecluster-ceph-rbd
  resources:
    requests:
      storage: 50Gi
```

| Field | Value | Explanation |
|---|---|---|
| `accessModes: ReadWriteOnce` | `RWO` | Only one node can mount this volume at a time (fine for single-replica databases) |
| `storageClassName` | From variable | `ocs-storagecluster-ceph-rbd` = Ceph block storage via ODF |
| `storage: 50Gi` | From variable | 50 GiB of persistent storage |

**StatefulSet (key fields):**

```yaml
apiVersion: apps/v1
kind: StatefulSet
spec:
  serviceName: agent-builder-postgresql
  replicas: 1
  template:
    spec:
      securityContext:
        fsGroup: 26
      containers:
        - name: postgresql
          image: registry.redhat.io/rhel9/postgresql-16:latest
          ports:
            - containerPort: 5432
          envFrom:
            - secretRef:
                name: agent-builder-postgresql-credentials
          resources:
            requests:
              cpu: 500m
              memory: 1Gi
            limits:
              cpu: '2'
              memory: 4Gi
```

| Field | Explanation |
|---|---|
| `kind: StatefulSet` | Used instead of `Deployment` for databases — provides stable network identity and ordered scaling |
| `serviceName` | Must match the Service name for DNS to work |
| `replicas: 1` | Single instance (not HA — use PostgreSQL operator for production HA) |
| `fsGroup: 26` | Linux group ID for PostgreSQL. Ensures the mounted volume has correct permissions |
| `image: registry.redhat.io/rhel9/postgresql-16:latest` | Red Hat's certified PostgreSQL 15 image |
| `envFrom.secretRef` | Injects all keys from the Secret as environment variables |
| `resources.requests` | **Minimum** CPU/memory guaranteed to this pod |
| `resources.limits` | **Maximum** CPU/memory this pod can use |

**Health Probes:**

```yaml
livenessProbe:
  exec:
    command: ["pg_isready", "-U", "agentbuilder"]
  initialDelaySeconds: 30
  periodSeconds: 10
readinessProbe:
  exec:
    command: ["pg_isready", "-U", "agentbuilder"]
  initialDelaySeconds: 5
  periodSeconds: 10
```

| Probe | Purpose |
|---|---|
| `livenessProbe` | Kubernetes restarts the pod if this fails. Uses `pg_isready` to check if PostgreSQL accepts connections |
| `readinessProbe` | Kubernetes removes the pod from the Service if this fails. Same check but starts sooner |

**Service:**

```yaml
apiVersion: v1
kind: Service
spec:
  ports:
    - port: 5432
      targetPort: 5432
  selector:
    app.kubernetes.io/name: postgresql
  type: ClusterIP
```

| Field | Explanation |
|---|---|
| `type: ClusterIP` | Internal-only service (not exposed outside the cluster) |
| `selector` | Routes traffic to pods with label `app.kubernetes.io/name: postgresql` |
| DNS name | `agent-builder-postgresql.agent-builder.svc.cluster.local` |

**Wait Loop:**

```bash
for i in $(seq 1 60); do
  oc get pod -n ${var.namespace} -l app.kubernetes.io/name=postgresql 2>/dev/null | grep -q Running && break
  sleep 10
done
```

Waits up to 10 minutes (60 × 10 seconds) for the PostgreSQL pod to reach `Running` state. This ensures dependent modules don't start before the database is ready.

---

## Module 3: MongoDB

**Purpose:** Deploys MongoDB 6 for agent metadata storage.

Follows the same pattern as PostgreSQL:

1. **Secret** with `MONGO_INITDB_ROOT_USERNAME=root` and password
2. **StatefulSet** using `registry.redhat.io/rhel9/mongodb-7:latest`
3. **Service** on port 27017
4. **Health check** using `mongosh --eval 'db.runCommand({ping:1}).ok'`

Key differences from PostgreSQL:

| Aspect | PostgreSQL | MongoDB |
|---|---|---|
| Image | `rhel9/postgresql-16` | `rhel9/mongodb-7` |
| Port | 5432 | 27017 |
| `fsGroup` | 26 (postgres) | 184 (mongodb) |
| Health check | `pg_isready -U agentbuilder` | `mongosh --eval 'db.runCommand({ping:1}).ok'` |
| Init scripts | SQL ConfigMap | None (databases auto-created) |

---

## Module 4: Redis

**Purpose:** Deploys Redis 7 as a caching layer for LiteLLM.

Key differences from database modules:

```yaml
command:
  - redis-server
  - --requirepass
  - $(REDIS_PASSWORD)
  - --maxmemory
  - 2gb
  - --maxmemory-policy
  - allkeys-lru
  - --appendonly
  - 'yes'
```

| Redis Config | Value | Explanation |
|---|---|---|
| `--requirepass` | From Secret | Password authentication |
| `--maxmemory 2gb` | 2 GiB | Maximum memory for cache data |
| `--maxmemory-policy allkeys-lru` | LRU eviction | When memory is full, remove Least Recently Used keys |
| `--appendonly yes` | AOF persistence | Write every operation to disk for durability |

---

## Module 5: Temporal

**Purpose:** Deploys the Temporal workflow engine (server + Web UI).

This is the most complex module — it creates **4 resources**:

### Resource 1: Credentials Secret

Stores PostgreSQL credentials for Temporal.

### Resource 2: ConfigMap

```yaml
data:
  TEMPORAL_ADDRESS: 0.0.0.0:7233
  DB: postgresql
  POSTGRES_SEEDS: <postgresql-service-dns>
  DBNAME: temporal_db
  VISIBILITY_DBNAME: temporal_visibility_db
  NUM_HISTORY_SHARDS: '512'
  DEFAULT_NAMESPACE: agent-builder
  SKIP_SCHEMA_SETUP: 'false'
```

| Config | Value | Explanation |
|---|---|---|
| `DB: postgresql` | Database backend | Temporal supports PostgreSQL, MySQL, Cassandra |
| `POSTGRES_SEEDS` | PostgreSQL DNS | How Temporal finds the database |
| `NUM_HISTORY_SHARDS: 512` | Shard count | Determines parallelism. 512 is recommended for production |
| `SKIP_SCHEMA_SETUP: false` | Auto-setup | Temporal auto-creates its database schema on first start |

### Resource 3: Temporal Server Deployment

Uses the official `temporalio/auto-setup:1.30.4` image which handles database migration automatically.

**Ports exposed:**

| Port | Name | Protocol |
|---|---|---|
| 7233 | `frontend` | gRPC — main Temporal API |
| 6831 | `jaeger` | Distributed tracing (optional) |
| 9090 | `metrics` | Prometheus metrics |

### Resource 4: Temporal UI Deployment + Route

Uses `temporalio/ui:2.49.1` — a web dashboard for viewing workflows.

```yaml
env:
  - name: TEMPORAL_ADDRESS
    value: agent-builder-temporal:7233
  - name: TEMPORAL_CORS_ORIGINS
    value: https://temporal.agent-builder.apps.ocp-ai.example.com
```

The UI connects to the Temporal server via internal DNS and has CORS configured for the external route URL.

---

## Module 6: Ollama

**Purpose:** Deploys a local LLM (Llama3) for air-gapped inference.

### Model Auto-Pull Script

```yaml
data:
  pull-model.sh: |
    #!/bin/bash
    set -e
    # Wait for Ollama server to start
    for i in $(seq 1 120); do
      curl -s http://localhost:11434/api/tags > /dev/null 2>&1 && break
      sleep 5
    done
    # Pull the model
    curl -s http://localhost:11434/api/pull -d '{"name": "llama3"}'
```

This script is stored in a ConfigMap and runs as a `postStart` lifecycle hook. It waits for Ollama to be ready, then downloads the model.

### GPU Patching

```hcl
resource "null_resource" "ollama_gpu_patch" {
  count = var.ollama_gpu_enabled ? 1 : 0

  provisioner "remote-exec" {
    inline = [
      "oc patch deployment agent-builder-ollama -n ${var.namespace} --type=json -p='[",
      "  {\"op\": \"add\", \"path\": \"/spec/.../nvidia.com~1gpu\", \"value\": \"${var.ollama_gpu_limit}\"}",
      "]'",
    ]
  }
  depends_on = [null_resource.ollama]
}
```

If GPUs are enabled, a **separate resource** patches the Deployment to add NVIDIA GPU resource requests and tolerations. The `~1` in the JSON path is the escaped `/` (JSON Pointer spec).

---

## Module 7: LiteLLM

**Purpose:** Multi-model LLM proxy that abstracts cloud and local LLM providers.

### Dynamic Config Generation

The most interesting part is the **conditional config** using Terraform's `%{if}` directive:

```hcl
"%{if var.enable_ollama~}",
"      - model_name: ${var.ollama_model}",
"        litellm_params:",
"          model: ollama/${var.ollama_model}",
"          api_base: http://${var.ollama_host}:11434",
"%{endif~}",
```

| Syntax | Meaning |
|---|---|
| `%{if var.enable_ollama~}` | If `enable_ollama` is true, include the following lines |
| `%{endif~}` | End of conditional block |
| `~` (tilde) | Strip whitespace before/after the directive |

This generates different LiteLLM configs based on which LLM providers are enabled.

### Model Routing Table

The generated `litellm_config.yaml` ConfigMap contains:

| Model Name | Provider | When Available |
|---|---|---|
| `claude-3-haiku` | Anthropic | When `anthropic_api_key` is set |
| `gpt-4o` | Azure OpenAI | When `azure_openai_endpoint` is set |
| `openai-gpt-4o` | OpenAI | When `openai_api_key` is set |
| `llama3` | In-cluster Ollama | When `enable_ollama = true` |
| `laptop-llama3` | Laptop Ollama | When `enable_local_llm_laptop = true` |
| `laptop-codellama` | Laptop Ollama | When `enable_local_llm_laptop = true` |
| `laptop-mistral` | Laptop Ollama | When `enable_local_llm_laptop = true` |

---

## Module 8: Temporal Workers

**Purpose:** Scalable workflow activity executors that process tasks from Temporal queues.

Key configuration:

```yaml
env:
  - name: TEMPORAL_TASK_QUEUE
    value: workflow-builder-queue
  - name: MAX_CONCURRENT_WORKFLOW_TASKS
    value: '100'
  - name: MAX_CONCURRENT_ACTIVITIES
    value: '100'
```

Workers poll the `workflow-builder-queue` task queue in Temporal and execute workflow activities (API calls, agent executions, etc.).

---

## Module 9: Agent Builder API

**Purpose:** FastAPI backend that manages agents, workflows, and LLM interactions.

### RBAC Configuration

This module creates **ServiceAccount + Role + RoleBinding** for the API to deploy agents:

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: agent-builder-api-deployer
rules:
  - apiGroups: ['', 'apps', 'route.openshift.io']
    resources: ['deployments', 'services', 'pods', 'pods/log', 'routes', 'configmaps', 'secrets']
    verbs: ['get', 'list', 'watch', 'create', 'update', 'patch', 'delete']
```

| RBAC Object | Purpose |
|---|---|
| `ServiceAccount` | Identity for the API pod |
| `Role` | Permission set — what resources the API can manage |
| `RoleBinding` | Links the ServiceAccount to the Role |

The API can create/delete Deployments, Services, and Routes — this is how it deploys user-created agents.

---

## Module 10: Agent Builder UI

**Purpose:** React frontend for the Agent Builder platform.

### Environment Configuration via ConfigMap

```yaml
data:
  VITE_API_BASE_URL: https://api.agent-builder.apps.ocp-ai.example.com
  VITE_OIDC_AUTHORITY: ""
  VITE_OIDC_CLIENT_ID: ""
  VITE_APP_NAME: Kyndryl Agent Builder
  VITE_POLLING_INTERVAL: '1000'
  VITE_API_TIMEOUT: '30000'
```

`VITE_` prefix is the standard for Vite.js (React build tool) environment variables. These are injected into the container at runtime via `envFrom.configMapRef`.

---

## Module 11: Tool Catalog

**Purpose:** MCP (Model Context Protocol) tools discovery server.

Simplest application module — no secrets needed, no database connections. Just a Deployment + Service + Route on port 8090.

---

## Module 12: Agent Deployment Service

**Purpose:** Deploys user-created agents to Kubernetes namespaces.

### ClusterRole (not Role)

Unlike the API module which uses a namespace-scoped `Role`, this module uses a **ClusterRole**:

```yaml
kind: ClusterRole
rules:
  - apiGroups: ['', 'apps', 'route.openshift.io', 'image.openshift.io', 'build.openshift.io']
    resources: ['namespaces', 'deployments', 'services', 'pods', 'routes', 'imagestreams', 'buildconfigs']
    verbs: ['get', 'list', 'watch', 'create', 'update', 'patch', 'delete']
```

| Role vs ClusterRole | Scope |
|---|---|
| `Role` | Permissions within a single namespace |
| `ClusterRole` | Permissions across **all namespaces** |

The Deployment Service needs ClusterRole because it deploys agents into **different namespaces** (not just `agent-builder`).

---

## Module 13: Agent Registry

**Purpose:** Metadata management for registered agents.

Uses **both** PostgreSQL and MongoDB:

- PostgreSQL: Structured agent metadata (names, versions, capabilities)
- MongoDB: Document-based storage (agent configs, conversation logs)

---

## Module 14: A2A Gateway

**Purpose:** Agent-to-Agent communication using the Google A2A Protocol.

```yaml
env:
  - name: AGENT_REGISTRY_URL
    value: http://agent-builder-registry:8002
```

The A2A Gateway queries the Agent Registry to discover available agents and route inter-agent messages.

---

## How to Write a New Module From Scratch

1. **Create a directory:** `modules/my-service/main.tf`

2. **Declare variables:**
    ```hcl
    variable "bastion_host" { type = string }
    variable "bastion_user" { type = string }
    variable "bastion_ssh_key" { type = string }
    variable "kubeconfig" { type = string }
    variable "namespace" { type = string }
    # Add service-specific variables
    ```

3. **Create a Secret** (if the service needs passwords):
    ```hcl
    resource "null_resource" "my_service_secret" {
      connection { ... }
      provisioner "remote-exec" {
        inline = ["oc create secret generic ... --dry-run=client -o yaml | oc apply -f -"]
      }
    }
    ```

4. **Create the Deployment + Service** (+ Route if external access is needed):
    ```hcl
    resource "null_resource" "my_service" {
      connection { ... }
      provisioner "remote-exec" {
        inline = ["cat <<'EOF' | oc apply -f -", "apiVersion: apps/v1...", "EOF"]
      }
      depends_on = [null_resource.my_service_secret]
    }
    ```

5. **Add outputs:**
    ```hcl
    output "service_name" { value = "my-service" }
    output "port" { value = 8080 }
    ```

6. **Call from root `main.tf`:**
    ```hcl
    module "my_service" {
      source = "./modules/my-service"
      bastion_host = var.bastion_host
      # ...
      depends_on = [module.namespace]
    }
    ```

---

## Summary: All 14 Modules at a Glance

| # | Module | K8s Resources Created | Port | Has Secret | Has Route |
|---|---|---|---|---|---|
| 1 | namespace | Namespace | — | No | No |
| 2 | postgresql | Secret, ConfigMap, PVC, StatefulSet, Service | 5432 | Yes | No |
| 3 | mongodb | Secret, PVC, StatefulSet, Service | 27017 | Yes | No |
| 4 | redis | Secret, ConfigMap, PVC, StatefulSet, Service | 6379 | Yes | No |
| 5 | temporal | Secret, ConfigMap, 2× Deployment, 2× Service, Route | 7233, 8080 | Yes | Yes (UI) |
| 6 | ollama | ConfigMap, PVC, Deployment, Service (+GPU patch) | 11434 | No | No |
| 7 | litellm | Secret, ConfigMap, Deployment, Service, Route (+ExternalName) | 4000 | Yes | Yes |
| 8 | temporal-workers | Secret, Deployment, Service | 8000 | Yes | No |
| 9 | agent-builder-api | Secret, SA, Role, RoleBinding, Deployment, Service, Route | 8000 | Yes | Yes |
| 10 | agent-builder-ui | ConfigMap, Deployment, Service, Route | 3000 | No | Yes |
| 11 | tool-catalog | Deployment, Service, Route | 8090 | No | Yes |
| 12 | agent-deployment-service | Secret, SA, ClusterRole, ClusterRoleBinding, Deployment, Service, Route | 8001 | Yes | Yes |
| 13 | agent-registry | Secret, Deployment, Service, Route | 8002 | Yes | Yes |
| 14 | a2a-gateway | Deployment, Service, Route | 8003 | No | Yes |
