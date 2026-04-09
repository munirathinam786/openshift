# Author: Sathishkumar Munirathinam
# Module: Agent Builder UI — React frontend

variable "bastion_host" { type = string }
variable "bastion_user" { type = string }
variable "bastion_ssh_key" { type = string }
variable "kubeconfig" { type = string }
variable "namespace" { type = string }
variable "container_image" { type = string }
variable "api_base_url" { type = string }
variable "ui_host" { type = string }
variable "oidc_authority" { type = string; default = "" }
variable "oidc_client_id" { type = string; default = "" }
variable "oidc_redirect_uri" { type = string; default = "" }

resource "null_resource" "ui" {
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
      "kind: ConfigMap",
      "metadata:",
      "  name: agent-builder-ui-config",
      "  namespace: ${var.namespace}",
      "data:",
      "  VITE_API_BASE_URL: ${var.api_base_url}",
      "  VITE_OIDC_AUTHORITY: ${var.oidc_authority}",
      "  VITE_OIDC_CLIENT_ID: ${var.oidc_client_id}",
      "  VITE_OIDC_REDIRECT_URI: ${var.oidc_redirect_uri}",
      "  VITE_OIDC_SCOPE: openid profile email",
      "  VITE_APP_NAME: Kyndryl Agent Builder",
      "  VITE_ENABLE_LOGGING: 'true'",
      "  VITE_MAX_AGENTS: '10'",
      "  VITE_POLLING_INTERVAL: '1000'",
      "  VITE_API_TIMEOUT: '30000'",
      "---",
      "apiVersion: apps/v1",
      "kind: Deployment",
      "metadata:",
      "  name: agent-builder-ui",
      "  namespace: ${var.namespace}",
      "  labels:",
      "    app.kubernetes.io/name: agent-builder-ui",
      "    app.kubernetes.io/part-of: agent-builder",
      "spec:",
      "  replicas: 2",
      "  selector:",
      "    matchLabels:",
      "      app.kubernetes.io/name: agent-builder-ui",
      "  template:",
      "    metadata:",
      "      labels:",
      "        app.kubernetes.io/name: agent-builder-ui",
      "        app.kubernetes.io/part-of: agent-builder",
      "    spec:",
      "      containers:",
      "        - name: ui",
      "          image: ${var.container_image}",
      "          ports:",
      "            - containerPort: 3000",
      "              name: http",
      "          envFrom:",
      "            - configMapRef:",
      "                name: agent-builder-ui-config",
      "          env:",
      "            - name: NODE_ENV",
      "              value: production",
      "            - name: NODE_OPTIONS",
      "              value: --max-old-space-size=4096",
      "          resources:",
      "            requests:",
      "              cpu: 250m",
      "              memory: 512Mi",
      "            limits:",
      "              cpu: '1'",
      "              memory: 2Gi",
      "          livenessProbe:",
      "            httpGet:",
      "              path: /",
      "              port: 3000",
      "            initialDelaySeconds: 15",
      "            periodSeconds: 10",
      "          readinessProbe:",
      "            httpGet:",
      "              path: /",
      "              port: 3000",
      "            initialDelaySeconds: 10",
      "            periodSeconds: 5",
      "---",
      "apiVersion: v1",
      "kind: Service",
      "metadata:",
      "  name: agent-builder-ui",
      "  namespace: ${var.namespace}",
      "  labels:",
      "    app.kubernetes.io/name: agent-builder-ui",
      "    app.kubernetes.io/part-of: agent-builder",
      "spec:",
      "  ports:",
      "    - port: 3000",
      "      targetPort: 3000",
      "      name: http",
      "  selector:",
      "    app.kubernetes.io/name: agent-builder-ui",
      "  type: ClusterIP",
      "---",
      "apiVersion: route.openshift.io/v1",
      "kind: Route",
      "metadata:",
      "  name: agent-builder-ui",
      "  namespace: ${var.namespace}",
      "  labels:",
      "    app.kubernetes.io/name: agent-builder-ui",
      "    app.kubernetes.io/part-of: agent-builder",
      "spec:",
      "  host: ${var.ui_host}",
      "  to:",
      "    kind: Service",
      "    name: agent-builder-ui",
      "  port:",
      "    targetPort: http",
      "  tls:",
      "    termination: edge",
      "    insecureEdgeTerminationPolicy: Redirect",
      "EOF",

      "echo 'Agent Builder UI deployment complete'",
    ]
  }
}

output "service_name" {
  value = "agent-builder-ui"
}

output "port" {
  value = 3000
}
