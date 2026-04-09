# Author: Sathishkumar Munirathinam
# Module: Temporal Workers — Scalable workflow activity executors

variable "bastion_host" { type = string }
variable "bastion_user" { type = string }
variable "bastion_ssh_key" { type = string }
variable "kubeconfig" { type = string }
variable "namespace" { type = string }
variable "container_image" { type = string }
variable "temporal_host" { type = string }
variable "mongodb_uri" { type = string; sensitive = true }
variable "replicas" { type = number; default = 2 }

resource "null_resource" "temporal_workers_secret" {
  connection {
    type        = "ssh"
    host        = var.bastion_host
    user        = var.bastion_user
    private_key = file(var.bastion_ssh_key)
  }

  provisioner "remote-exec" {
    inline = [
      "export KUBECONFIG=${var.kubeconfig}",

      "oc create secret generic agent-builder-temporal-workers-env -n ${var.namespace} \\",
      "  --from-literal=MONGODB_URI='${var.mongodb_uri}' \\",
      "  --dry-run=client -o yaml | oc apply -f -",
    ]
  }
}

resource "null_resource" "temporal_workers" {
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
      "  name: agent-builder-temporal-workers",
      "  namespace: ${var.namespace}",
      "  labels:",
      "    app.kubernetes.io/name: temporal-workers",
      "    app.kubernetes.io/part-of: agent-builder",
      "spec:",
      "  replicas: ${var.replicas}",
      "  selector:",
      "    matchLabels:",
      "      app.kubernetes.io/name: temporal-workers",
      "  template:",
      "    metadata:",
      "      labels:",
      "        app.kubernetes.io/name: temporal-workers",
      "        app.kubernetes.io/part-of: agent-builder",
      "    spec:",
      "      containers:",
      "        - name: temporal-workers",
      "          image: ${var.container_image}",
      "          ports:",
      "            - containerPort: 8000",
      "              name: health",
      "          env:",
      "            - name: TEMPORAL_HOST",
      "              value: ${var.temporal_host}",
      "            - name: TEMPORAL_NAMESPACE",
      "              value: agent-builder",
      "            - name: TEMPORAL_TASK_QUEUE",
      "              value: workflow-builder-queue",
      "            - name: TEMPORAL_TLS_ENABLED",
      "              value: 'false'",
      "            - name: MONGODB_DATABASE",
      "              value: workflow_builder",
      "            - name: LOG_LEVEL",
      "              value: INFO",
      "            - name: MAX_CONCURRENT_WORKFLOW_TASKS",
      "              value: '100'",
      "            - name: MAX_CONCURRENT_ACTIVITIES",
      "              value: '100'",
      "          envFrom:",
      "            - secretRef:",
      "                name: agent-builder-temporal-workers-env",
      "          resources:",
      "            requests:",
      "              cpu: 500m",
      "              memory: 1Gi",
      "            limits:",
      "              cpu: '2'",
      "              memory: 4Gi",
      "          livenessProbe:",
      "            httpGet:",
      "              path: /health",
      "              port: 8000",
      "            initialDelaySeconds: 30",
      "            periodSeconds: 15",
      "          readinessProbe:",
      "            httpGet:",
      "              path: /health",
      "              port: 8000",
      "            initialDelaySeconds: 15",
      "            periodSeconds: 10",
      "---",
      "apiVersion: v1",
      "kind: Service",
      "metadata:",
      "  name: agent-builder-temporal-workers",
      "  namespace: ${var.namespace}",
      "  labels:",
      "    app.kubernetes.io/name: temporal-workers",
      "    app.kubernetes.io/part-of: agent-builder",
      "spec:",
      "  ports:",
      "    - port: 8000",
      "      targetPort: 8000",
      "      name: health",
      "  selector:",
      "    app.kubernetes.io/name: temporal-workers",
      "  type: ClusterIP",
      "EOF",

      "echo 'Temporal Workers deployment complete (${var.replicas} replicas)'",
    ]
  }

  depends_on = [null_resource.temporal_workers_secret]
}

output "service_name" {
  value = "agent-builder-temporal-workers"
}
