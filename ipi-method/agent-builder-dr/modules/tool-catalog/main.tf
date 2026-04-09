# Author: Sathishkumar Munirathinam
# Module: Tool Catalog — MCP Tools Discovery Server

variable "bastion_host" { type = string }
variable "bastion_user" { type = string }
variable "bastion_ssh_key" { type = string }
variable "kubeconfig" { type = string }
variable "namespace" { type = string }
variable "container_image" { type = string }
variable "tool_catalog_host" { type = string }

resource "null_resource" "tool_catalog" {
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
      "  name: agent-builder-tool-catalog",
      "  namespace: ${var.namespace}",
      "  labels:",
      "    app.kubernetes.io/name: tool-catalog",
      "    app.kubernetes.io/part-of: agent-builder",
      "spec:",
      "  replicas: 1",
      "  selector:",
      "    matchLabels:",
      "      app.kubernetes.io/name: tool-catalog",
      "  template:",
      "    metadata:",
      "      labels:",
      "        app.kubernetes.io/name: tool-catalog",
      "        app.kubernetes.io/part-of: agent-builder",
      "    spec:",
      "      containers:",
      "        - name: tool-catalog",
      "          image: ${var.container_image}",
      "          ports:",
      "            - containerPort: 8090",
      "              name: http",
      "          env:",
      "            - name: PORT",
      "              value: '8090'",
      "            - name: LOG_LEVEL",
      "              value: INFO",
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
      "              path: /tools-server/health",
      "              port: 8090",
      "            initialDelaySeconds: 20",
      "            periodSeconds: 10",
      "          readinessProbe:",
      "            httpGet:",
      "              path: /tools-server/health",
      "              port: 8090",
      "            initialDelaySeconds: 10",
      "            periodSeconds: 5",
      "---",
      "apiVersion: v1",
      "kind: Service",
      "metadata:",
      "  name: agent-builder-tool-catalog",
      "  namespace: ${var.namespace}",
      "  labels:",
      "    app.kubernetes.io/name: tool-catalog",
      "    app.kubernetes.io/part-of: agent-builder",
      "spec:",
      "  ports:",
      "    - port: 8090",
      "      targetPort: 8090",
      "      name: http",
      "  selector:",
      "    app.kubernetes.io/name: tool-catalog",
      "  type: ClusterIP",
      "---",
      "apiVersion: route.openshift.io/v1",
      "kind: Route",
      "metadata:",
      "  name: agent-builder-tool-catalog",
      "  namespace: ${var.namespace}",
      "  labels:",
      "    app.kubernetes.io/name: tool-catalog",
      "    app.kubernetes.io/part-of: agent-builder",
      "spec:",
      "  host: ${var.tool_catalog_host}",
      "  to:",
      "    kind: Service",
      "    name: agent-builder-tool-catalog",
      "  port:",
      "    targetPort: http",
      "  tls:",
      "    termination: edge",
      "    insecureEdgeTerminationPolicy: Redirect",
      "EOF",

      "echo 'Tool Catalog deployment complete'",
    ]
  }
}

output "service_name" {
  value = "agent-builder-tool-catalog"
}

output "port" {
  value = 8090
}
