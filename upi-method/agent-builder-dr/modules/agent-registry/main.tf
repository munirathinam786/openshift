# Author: Sathishkumar Munirathinam
# Module: Agent Registry — Agent metadata management

variable "bastion_host" { type = string }
variable "bastion_user" { type = string }
variable "bastion_ssh_key" { type = string }
variable "kubeconfig" { type = string }
variable "namespace" { type = string }
variable "container_image" { type = string }
variable "mongodb_uri" { type = string; sensitive = true }
variable "postgres_host" { type = string }
variable "postgres_password" { type = string; sensitive = true }
variable "registry_host" { type = string }

resource "null_resource" "registry_secret" {
  connection {
    type        = "ssh"
    host        = var.bastion_host
    user        = var.bastion_user
    private_key = file(var.bastion_ssh_key)
  }

  provisioner "remote-exec" {
    inline = [
      "export KUBECONFIG=${var.kubeconfig}",

      "oc create secret generic agent-builder-registry-env -n ${var.namespace} \\",
      "  --from-literal=MONGODB_URI='${var.mongodb_uri}' \\",
      "  --from-literal=DATABASE_URL='postgresql://agentbuilder:${var.postgres_password}@${var.postgres_host}:5432/agent_registry_db' \\",
      "  --dry-run=client -o yaml | oc apply -f -",
    ]
  }
}

resource "null_resource" "registry" {
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
      "  name: agent-builder-registry",
      "  namespace: ${var.namespace}",
      "  labels:",
      "    app.kubernetes.io/name: agent-registry",
      "    app.kubernetes.io/part-of: agent-builder",
      "spec:",
      "  replicas: 1",
      "  selector:",
      "    matchLabels:",
      "      app.kubernetes.io/name: agent-registry",
      "  template:",
      "    metadata:",
      "      labels:",
      "        app.kubernetes.io/name: agent-registry",
      "        app.kubernetes.io/part-of: agent-builder",
      "    spec:",
      "      containers:",
      "        - name: registry",
      "          image: ${var.container_image}",
      "          ports:",
      "            - containerPort: 8002",
      "              name: http",
      "          env:",
      "            - name: PORT",
      "              value: '8002'",
      "            - name: NODE_ENV",
      "              value: production",
      "            - name: LOG_LEVEL",
      "              value: info",
      "          envFrom:",
      "            - secretRef:",
      "                name: agent-builder-registry-env",
      "          resources:",
      "            requests:",
      "              cpu: 250m",
      "              memory: 512Mi",
      "            limits:",
      "              cpu: '1'",
      "              memory: 2Gi",
      "          livenessProbe:",
      "            httpGet:",
      "              path: /health",
      "              port: 8002",
      "            initialDelaySeconds: 20",
      "            periodSeconds: 10",
      "          readinessProbe:",
      "            httpGet:",
      "              path: /health",
      "              port: 8002",
      "            initialDelaySeconds: 10",
      "            periodSeconds: 5",
      "---",
      "apiVersion: v1",
      "kind: Service",
      "metadata:",
      "  name: agent-builder-registry",
      "  namespace: ${var.namespace}",
      "  labels:",
      "    app.kubernetes.io/name: agent-registry",
      "    app.kubernetes.io/part-of: agent-builder",
      "spec:",
      "  ports:",
      "    - port: 8002",
      "      targetPort: 8002",
      "      name: http",
      "  selector:",
      "    app.kubernetes.io/name: agent-registry",
      "  type: ClusterIP",
      "---",
      "apiVersion: route.openshift.io/v1",
      "kind: Route",
      "metadata:",
      "  name: agent-builder-registry",
      "  namespace: ${var.namespace}",
      "  labels:",
      "    app.kubernetes.io/name: agent-registry",
      "    app.kubernetes.io/part-of: agent-builder",
      "spec:",
      "  host: ${var.registry_host}",
      "  to:",
      "    kind: Service",
      "    name: agent-builder-registry",
      "  port:",
      "    targetPort: http",
      "  tls:",
      "    termination: edge",
      "    insecureEdgeTerminationPolicy: Redirect",
      "EOF",

      "echo 'Agent Registry deployment complete'",
    ]
  }

  depends_on = [null_resource.registry_secret]
}

output "service_name" {
  value = "agent-builder-registry"
}

output "port" {
  value = 8002
}
