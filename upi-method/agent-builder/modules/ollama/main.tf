# Author: Sathishkumar Munirathinam
# Module: Ollama — Local LLM (Llama3) on OpenShift
# Deploys Ollama with model auto-pull for air-gapped or GPU-enabled inference

variable "bastion_host" { type = string }
variable "bastion_user" { type = string }
variable "bastion_ssh_key" { type = string }
variable "kubeconfig" { type = string }
variable "namespace" { type = string }
variable "ollama_model" { type = string; default = "llama3" }
variable "ollama_storage_size" { type = string; default = "100Gi" }
variable "ollama_storage_class" { type = string }
variable "ollama_gpu_enabled" { type = bool; default = false }
variable "ollama_gpu_limit" { type = number; default = 1 }
variable "ollama_memory_limit" { type = string; default = "16Gi" }
variable "ollama_cpu_limit" { type = string; default = "8" }

locals {
  gpu_resources = var.ollama_gpu_enabled ? "            nvidia.com/gpu: '${var.ollama_gpu_limit}'" : ""
  gpu_limits    = var.ollama_gpu_enabled ? "            nvidia.com/gpu: '${var.ollama_gpu_limit}'" : ""
}

resource "null_resource" "ollama" {
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
      "kind: PersistentVolumeClaim",
      "metadata:",
      "  name: agent-builder-ollama-models",
      "  namespace: ${var.namespace}",
      "spec:",
      "  accessModes:",
      "    - ReadWriteOnce",
      "  storageClassName: ${var.ollama_storage_class}",
      "  resources:",
      "    requests:",
      "      storage: ${var.ollama_storage_size}",
      "---",
      "apiVersion: v1",
      "kind: ConfigMap",
      "metadata:",
      "  name: agent-builder-ollama-init",
      "  namespace: ${var.namespace}",
      "data:",
      "  pull-model.sh: |",
      "    #!/bin/bash",
      "    set -e",
      "    echo 'Waiting for Ollama server to start...'",
      "    for i in $(seq 1 120); do",
      "      curl -s http://localhost:11434/api/tags > /dev/null 2>&1 && break",
      "      sleep 5",
      "    done",
      "    echo 'Pulling model: ${var.ollama_model}'",
      "    curl -s http://localhost:11434/api/pull -d '{\"name\": \"${var.ollama_model}\"}' | while read line; do",
      "      echo \"$$line\"",
      "    done",
      "    echo 'Model ${var.ollama_model} ready'",
      "---",
      "apiVersion: apps/v1",
      "kind: Deployment",
      "metadata:",
      "  name: agent-builder-ollama",
      "  namespace: ${var.namespace}",
      "  labels:",
      "    app.kubernetes.io/name: ollama",
      "    app.kubernetes.io/part-of: agent-builder",
      "spec:",
      "  replicas: 1",
      "  selector:",
      "    matchLabels:",
      "      app.kubernetes.io/name: ollama",
      "  strategy:",
      "    type: Recreate",
      "  template:",
      "    metadata:",
      "      labels:",
      "        app.kubernetes.io/name: ollama",
      "        app.kubernetes.io/part-of: agent-builder",
      "    spec:",
      "      containers:",
      "        - name: ollama",
      "          image: docker.io/ollama/ollama:latest",
      "          ports:",
      "            - containerPort: 11434",
      "              name: http",
      "          env:",
      "            - name: OLLAMA_HOST",
      "              value: 0.0.0.0:11434",
      "            - name: OLLAMA_MODELS",
      "              value: /root/.ollama/models",
      "            - name: OLLAMA_KEEP_ALIVE",
      "              value: 24h",
      "          resources:",
      "            requests:",
      "              cpu: '4'",
      "              memory: 8Gi",
      "            limits:",
      "              cpu: '${var.ollama_cpu_limit}'",
      "              memory: ${var.ollama_memory_limit}",
      "          volumeMounts:",
      "            - name: models",
      "              mountPath: /root/.ollama",
      "            - name: init-scripts",
      "              mountPath: /scripts",
      "          lifecycle:",
      "            postStart:",
      "              exec:",
      "                command:",
      "                  - /bin/bash",
      "                  - /scripts/pull-model.sh",
      "          livenessProbe:",
      "            httpGet:",
      "              path: /api/tags",
      "              port: 11434",
      "            initialDelaySeconds: 60",
      "            periodSeconds: 30",
      "            timeoutSeconds: 10",
      "          readinessProbe:",
      "            httpGet:",
      "              path: /api/tags",
      "              port: 11434",
      "            initialDelaySeconds: 30",
      "            periodSeconds: 10",
      "      volumes:",
      "        - name: models",
      "          persistentVolumeClaim:",
      "            claimName: agent-builder-ollama-models",
      "        - name: init-scripts",
      "          configMap:",
      "            name: agent-builder-ollama-init",
      "            defaultMode: 0755",
      "---",
      "apiVersion: v1",
      "kind: Service",
      "metadata:",
      "  name: agent-builder-ollama",
      "  namespace: ${var.namespace}",
      "  labels:",
      "    app.kubernetes.io/name: ollama",
      "    app.kubernetes.io/part-of: agent-builder",
      "spec:",
      "  ports:",
      "    - port: 11434",
      "      targetPort: 11434",
      "      name: http",
      "  selector:",
      "    app.kubernetes.io/name: ollama",
      "  type: ClusterIP",
      "EOF",

      "echo 'Ollama deployment initiated — model pull will happen in background'",
    ]
  }
}

# If GPU is enabled, patch the deployment to add GPU resources
resource "null_resource" "ollama_gpu_patch" {
  count = var.ollama_gpu_enabled ? 1 : 0

  connection {
    type        = "ssh"
    host        = var.bastion_host
    user        = var.bastion_user
    private_key = file(var.bastion_ssh_key)
  }

  provisioner "remote-exec" {
    inline = [
      "export KUBECONFIG=${var.kubeconfig}",

      "oc patch deployment agent-builder-ollama -n ${var.namespace} --type=json -p='[",
      "  {\"op\": \"add\", \"path\": \"/spec/template/spec/containers/0/resources/limits/nvidia.com~1gpu\", \"value\": \"${var.ollama_gpu_limit}\"},",
      "  {\"op\": \"add\", \"path\": \"/spec/template/spec/containers/0/resources/requests/nvidia.com~1gpu\", \"value\": \"${var.ollama_gpu_limit}\"}",
      "]'",

      # Add tolerations for GPU nodes
      "oc patch deployment agent-builder-ollama -n ${var.namespace} --type=json -p='[",
      "  {\"op\": \"add\", \"path\": \"/spec/template/spec/tolerations\", \"value\": [{\"key\": \"nvidia.com/gpu\", \"operator\": \"Exists\", \"effect\": \"NoSchedule\"}]}",
      "]'",

      "echo 'GPU resources patched for Ollama'",
    ]
  }

  depends_on = [null_resource.ollama]
}

output "service_name" {
  value = "agent-builder-ollama"
}

output "port" {
  value = 11434
}
