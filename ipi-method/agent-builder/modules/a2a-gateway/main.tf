# Author: Sathishkumar Munirathinam
# Module: A2A Gateway — Agent-to-Agent communication (Google A2A Protocol)

variable "bastion_host" { type = string }
variable "bastion_user" { type = string }
variable "bastion_ssh_key" { type = string }
variable "kubeconfig" { type = string }
variable "namespace" { type = string }
variable "container_image" { type = string }
variable "a2a_host" { type = string }

resource "null_resource" "a2a_gateway" {
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
      "  name: agent-builder-a2a-gateway",
      "  namespace: ${var.namespace}",
      "  labels:",
      "    app.kubernetes.io/name: a2a-gateway",
      "    app.kubernetes.io/part-of: agent-builder",
      "spec:",
      "  replicas: 1",
      "  selector:",
      "    matchLabels:",
      "      app.kubernetes.io/name: a2a-gateway",
      "  template:",
      "    metadata:",
      "      labels:",
      "        app.kubernetes.io/name: a2a-gateway",
      "        app.kubernetes.io/part-of: agent-builder",
      "    spec:",
      "      containers:",
      "        - name: a2a-gateway",
      "          image: ${var.container_image}",
      "          ports:",
      "            - containerPort: 8003",
      "              name: http",
      "          env:",
      "            - name: PORT",
      "              value: '8003'",
      "            - name: LOG_LEVEL",
      "              value: INFO",
      "            - name: AGENT_REGISTRY_URL",
      "              value: http://agent-builder-registry:8002",
      "            - name: KUBERNETES_NAMESPACE",
      "              value: ${var.namespace}",
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
      "              port: 8003",
      "            initialDelaySeconds: 15",
      "            periodSeconds: 10",
      "          readinessProbe:",
      "            httpGet:",
      "              path: /health",
      "              port: 8003",
      "            initialDelaySeconds: 10",
      "            periodSeconds: 5",
      "---",
      "apiVersion: v1",
      "kind: Service",
      "metadata:",
      "  name: agent-builder-a2a-gateway",
      "  namespace: ${var.namespace}",
      "  labels:",
      "    app.kubernetes.io/name: a2a-gateway",
      "    app.kubernetes.io/part-of: agent-builder",
      "spec:",
      "  ports:",
      "    - port: 8003",
      "      targetPort: 8003",
      "      name: http",
      "  selector:",
      "    app.kubernetes.io/name: a2a-gateway",
      "  type: ClusterIP",
      "---",
      "apiVersion: route.openshift.io/v1",
      "kind: Route",
      "metadata:",
      "  name: agent-builder-a2a-gateway",
      "  namespace: ${var.namespace}",
      "  labels:",
      "    app.kubernetes.io/name: a2a-gateway",
      "    app.kubernetes.io/part-of: agent-builder",
      "spec:",
      "  host: ${var.a2a_host}",
      "  to:",
      "    kind: Service",
      "    name: agent-builder-a2a-gateway",
      "  port:",
      "    targetPort: http",
      "  tls:",
      "    termination: edge",
      "    insecureEdgeTerminationPolicy: Redirect",
      "EOF",

      "echo 'A2A Gateway deployment complete'",
    ]
  }
}

output "service_name" {
  value = "agent-builder-a2a-gateway"
}

output "port" {
  value = 8003
}
