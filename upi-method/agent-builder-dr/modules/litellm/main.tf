# Author: Sathishkumar Munirathinam
# Module: LiteLLM — Multi-model LLM proxy with local LLM support

variable "bastion_host" { type = string }
variable "bastion_user" { type = string }
variable "bastion_ssh_key" { type = string }
variable "kubeconfig" { type = string }
variable "namespace" { type = string }
variable "litellm_master_key" { type = string; sensitive = true }
variable "postgres_host" { type = string }
variable "postgres_password" { type = string; sensitive = true }
variable "redis_host" { type = string }
variable "redis_password" { type = string; sensitive = true }
variable "anthropic_api_key" { type = string; sensitive = true; default = "" }
variable "azure_openai_endpoint" { type = string; default = "" }
variable "azure_openai_key" { type = string; sensitive = true; default = "" }
variable "openai_api_key" { type = string; sensitive = true; default = "" }
variable "litellm_host" { type = string }
variable "enable_ollama" { type = bool; default = false }
variable "ollama_host" { type = string; default = "" }
variable "ollama_model" { type = string; default = "llama3" }
variable "enable_local_llm_laptop" { type = bool; default = false }
variable "local_llm_laptop_url" { type = string; default = "" }

resource "null_resource" "litellm_secret" {
  connection {
    type        = "ssh"
    host        = var.bastion_host
    user        = var.bastion_user
    private_key = file(var.bastion_ssh_key)
  }

  provisioner "remote-exec" {
    inline = [
      "export KUBECONFIG=${var.kubeconfig}",

      "oc create secret generic agent-builder-litellm-credentials -n ${var.namespace} \\",
      "  --from-literal=LITELLM_MASTER_KEY='${var.litellm_master_key}' \\",
      "  --from-literal=DATABASE_URL='postgresql://agentbuilder:${var.postgres_password}@${var.postgres_host}:5432/litellm_db' \\",
      "  --from-literal=REDIS_PASSWORD='${var.redis_password}' \\",
      "  --from-literal=ANTHROPIC_API_KEY='${var.anthropic_api_key}' \\",
      "  --from-literal=AZURE_OPENAI_KEY='${var.azure_openai_key}' \\",
      "  --from-literal=OPENAI_API_KEY='${var.openai_api_key}' \\",
      "  --dry-run=client -o yaml | oc apply -f -",
    ]
  }
}

resource "null_resource" "litellm_config" {
  connection {
    type        = "ssh"
    host        = var.bastion_host
    user        = var.bastion_user
    private_key = file(var.bastion_ssh_key)
  }

  provisioner "remote-exec" {
    inline = [
      "export KUBECONFIG=${var.kubeconfig}",

      "cat <<'CMEOF' | oc apply -f -",
      "apiVersion: v1",
      "kind: ConfigMap",
      "metadata:",
      "  name: agent-builder-litellm-config",
      "  namespace: ${var.namespace}",
      "data:",
      "  litellm_config.yaml: |",
      "    model_list:",
      "      # ---- Cloud LLM Providers ----",
      "      - model_name: claude-3-haiku",
      "        litellm_params:",
      "          model: anthropic/claude-3-haiku-20240307",
      "          api_key: os.environ/ANTHROPIC_API_KEY",
      "      - model_name: gpt-4o",
      "        litellm_params:",
      "          model: azure/gpt-4o",
      "          api_base: ${var.azure_openai_endpoint}",
      "          api_key: os.environ/AZURE_OPENAI_KEY",
      "          api_version: '2025-01-01-preview'",
      "      - model_name: openai-gpt-4o",
      "        litellm_params:",
      "          model: openai/gpt-4o",
      "          api_key: os.environ/OPENAI_API_KEY",
      "%{if var.enable_ollama~}",
      "      # ---- In-Cluster Ollama (Local LLM) ----",
      "      - model_name: ${var.ollama_model}",
      "        litellm_params:",
      "          model: ollama/${var.ollama_model}",
      "          api_base: http://${var.ollama_host}:11434",
      "      - model_name: ${var.ollama_model}-chat",
      "        litellm_params:",
      "          model: ollama_chat/${var.ollama_model}",
      "          api_base: http://${var.ollama_host}:11434",
      "%{endif~}",
      "%{if var.enable_local_llm_laptop~}",
      "      # ---- Laptop Ollama (External Local LLM) ----",
      "      - model_name: laptop-llama3",
      "        litellm_params:",
      "          model: ollama/llama3",
      "          api_base: ${var.local_llm_laptop_url}",
      "      - model_name: laptop-llama3-chat",
      "        litellm_params:",
      "          model: ollama_chat/llama3",
      "          api_base: ${var.local_llm_laptop_url}",
      "      - model_name: laptop-codellama",
      "        litellm_params:",
      "          model: ollama/codellama",
      "          api_base: ${var.local_llm_laptop_url}",
      "      - model_name: laptop-mistral",
      "        litellm_params:",
      "          model: ollama/mistral",
      "          api_base: ${var.local_llm_laptop_url}",
      "%{endif~}",
      "    ",
      "    litellm_settings:",
      "      drop_params: true",
      "      cache: true",
      "      cache_params:",
      "        type: redis",
      "        host: ${var.redis_host}",
      "        port: 6379",
      "        password: os.environ/REDIS_PASSWORD",
      "        ttl: 1800",
      "      store_model_in_db: true",
      "      store_prompts_in_spend_logs: true",
      "    ",
      "    general_settings:",
      "      master_key: os.environ/LITELLM_MASTER_KEY",
      "      database_url: os.environ/DATABASE_URL",
      "CMEOF",
    ]
  }

  depends_on = [null_resource.litellm_secret]
}

resource "null_resource" "litellm" {
  connection {
    type        = "ssh"
    host        = var.bastion_host
    user        = var.bastion_user
    private_key = file(var.bastion_ssh_key)
  }

  provisioner "remote-exec" {
    inline = [
      "export KUBECONFIG=${var.kubeconfig}",

      "cat <<'EOF' | oc apply -f -",
      "apiVersion: apps/v1",
      "kind: Deployment",
      "metadata:",
      "  name: agent-builder-litellm",
      "  namespace: ${var.namespace}",
      "  labels:",
      "    app.kubernetes.io/name: litellm",
      "    app.kubernetes.io/part-of: agent-builder",
      "spec:",
      "  replicas: 1",
      "  selector:",
      "    matchLabels:",
      "      app.kubernetes.io/name: litellm",
      "  template:",
      "    metadata:",
      "      labels:",
      "        app.kubernetes.io/name: litellm",
      "        app.kubernetes.io/part-of: agent-builder",
      "    spec:",
      "      containers:",
      "        - name: litellm",
      "          image: ghcr.io/berriai/litellm:v1.83.10-stable",
      "          args:",
      "            - --config",
      "            - /etc/litellm/litellm_config.yaml",
      "            - --port",
      "            - '4000'",
      "          ports:",
      "            - containerPort: 4000",
      "              name: http",
      "          envFrom:",
      "            - secretRef:",
      "                name: agent-builder-litellm-credentials",
      "          resources:",
      "            requests:",
      "              cpu: 500m",
      "              memory: 1Gi",
      "            limits:",
      "              cpu: '2'",
      "              memory: 4Gi",
      "          volumeMounts:",
      "            - name: config",
      "              mountPath: /etc/litellm",
      "          livenessProbe:",
      "            httpGet:",
      "              path: /health/liveliness",
      "              port: 4000",
      "            initialDelaySeconds: 30",
      "            periodSeconds: 15",
      "          readinessProbe:",
      "            httpGet:",
      "              path: /health/readiness",
      "              port: 4000",
      "            initialDelaySeconds: 15",
      "            periodSeconds: 10",
      "      volumes:",
      "        - name: config",
      "          configMap:",
      "            name: agent-builder-litellm-config",
      "---",
      "apiVersion: v1",
      "kind: Service",
      "metadata:",
      "  name: agent-builder-litellm",
      "  namespace: ${var.namespace}",
      "  labels:",
      "    app.kubernetes.io/name: litellm",
      "    app.kubernetes.io/part-of: agent-builder",
      "spec:",
      "  ports:",
      "    - port: 4000",
      "      targetPort: 4000",
      "      name: http",
      "  selector:",
      "    app.kubernetes.io/name: litellm",
      "  type: ClusterIP",
      "---",
      "apiVersion: route.openshift.io/v1",
      "kind: Route",
      "metadata:",
      "  name: agent-builder-litellm",
      "  namespace: ${var.namespace}",
      "  labels:",
      "    app.kubernetes.io/name: litellm",
      "    app.kubernetes.io/part-of: agent-builder",
      "spec:",
      "  host: ${var.litellm_host}",
      "  to:",
      "    kind: Service",
      "    name: agent-builder-litellm",
      "  port:",
      "    targetPort: http",
      "  tls:",
      "    termination: edge",
      "    insecureEdgeTerminationPolicy: Redirect",
      "EOF",

      "echo 'Waiting for LiteLLM to be ready...'",
      "for i in $(seq 1 60); do",
      "  oc get pod -n ${var.namespace} -l app.kubernetes.io/name=litellm 2>/dev/null | grep -q Running && break",
      "  sleep 10",
      "done",
      "echo 'LiteLLM deployment complete'",
    ]
  }

  depends_on = [null_resource.litellm_config]
}

# ExternalName service for laptop Ollama (when enabled)
resource "null_resource" "laptop_ollama_endpoint" {
  count = var.enable_local_llm_laptop ? 1 : 0

  connection {
    type        = "ssh"
    host        = var.bastion_host
    user        = var.bastion_user
    private_key = file(var.bastion_ssh_key)
  }

  provisioner "remote-exec" {
    inline = [
      "export KUBECONFIG=${var.kubeconfig}",

      "cat <<'EOF' | oc apply -f -",
      "apiVersion: v1",
      "kind: Service",
      "metadata:",
      "  name: agent-builder-laptop-ollama",
      "  namespace: ${var.namespace}",
      "  labels:",
      "    app.kubernetes.io/name: laptop-ollama",
      "    app.kubernetes.io/part-of: agent-builder",
      "  annotations:",
      "    description: External endpoint for Ollama running on laptop",
      "spec:",
      "  type: ExternalName",
      "  externalName: ${replace(replace(var.local_llm_laptop_url, "http://", ""), ":11434", "")}",
      "EOF",

      "echo 'Laptop Ollama external service configured'",
    ]
  }

  depends_on = [null_resource.litellm]
}

output "service_name" {
  value = "agent-builder-litellm"
}

output "port" {
  value = 4000
}
