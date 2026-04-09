# Author: Sathishkumar Munirathinam
# Module: Agent Builder API — FastAPI backend for agent management

variable "bastion_host" { type = string }
variable "bastion_user" { type = string }
variable "bastion_ssh_key" { type = string }
variable "kubeconfig" { type = string }
variable "namespace" { type = string }
variable "container_image" { type = string }
variable "litellm_proxy_base" { type = string }
variable "litellm_master_key" { type = string; sensitive = true }
variable "mongodb_uri" { type = string; sensitive = true }
variable "temporal_host" { type = string }
variable "github_token" { type = string; sensitive = true; default = "" }
variable "api_host" { type = string }
variable "oidc_authority" { type = string; default = "" }
variable "oidc_client_id" { type = string; default = "" }

resource "null_resource" "api_secret" {
  connection {
    type        = "ssh"
    host        = var.bastion_host
    user        = var.bastion_user
    private_key = file(var.bastion_ssh_key)
  }

  provisioner "remote-exec" {
    inline = [
      "export KUBECONFIG=${var.kubeconfig}",

      "oc create secret generic agent-builder-api-env -n ${var.namespace} \\",
      "  --from-literal=LITELLM_MASTER_KEY='${var.litellm_master_key}' \\",
      "  --from-literal=MONGODB_URI='${var.mongodb_uri}' \\",
      "  --from-literal=GITHUB_TOKEN='${var.github_token}' \\",
      "  --dry-run=client -o yaml | oc apply -f -",
    ]
  }
}

resource "null_resource" "api" {
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
      "  name: agent-builder-api",
      "  namespace: ${var.namespace}",
      "  labels:",
      "    app.kubernetes.io/name: agent-builder-api",
      "    app.kubernetes.io/part-of: agent-builder",
      "spec:",
      "  replicas: 2",
      "  selector:",
      "    matchLabels:",
      "      app.kubernetes.io/name: agent-builder-api",
      "  template:",
      "    metadata:",
      "      labels:",
      "        app.kubernetes.io/name: agent-builder-api",
      "        app.kubernetes.io/part-of: agent-builder",
      "    spec:",
      "      containers:",
      "        - name: api",
      "          image: ${var.container_image}",
      "          ports:",
      "            - containerPort: 8000",
      "              name: http",
      "          env:",
      "            - name: LITELLM_PROXY_BASE",
      "              value: ${var.litellm_proxy_base}",
      "            - name: TEMPORAL_HOST",
      "              value: ${var.temporal_host}",
      "            - name: TEMPORAL_NAMESPACE",
      "              value: agent-builder",
      "            - name: TEMPORAL_TASK_QUEUE",
      "              value: workflow-builder-queue",
      "            - name: TEMPORAL_TLS_ENABLED",
      "              value: 'false'",
      "            - name: MONGODB_DATABASE",
      "              value: workflowagent",
      "            - name: OIDC_AUTHORITY",
      "              value: ${var.oidc_authority}",
      "            - name: OIDC_CLIENT_ID",
      "              value: ${var.oidc_client_id}",
      "            - name: K8S_NAMESPACE",
      "              value: ${var.namespace}",
      "          envFrom:",
      "            - secretRef:",
      "                name: agent-builder-api-env",
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
      "      serviceAccountName: agent-builder-api",
      "---",
      "apiVersion: v1",
      "kind: ServiceAccount",
      "metadata:",
      "  name: agent-builder-api",
      "  namespace: ${var.namespace}",
      "  labels:",
      "    app.kubernetes.io/name: agent-builder-api",
      "    app.kubernetes.io/part-of: agent-builder",
      "---",
      "apiVersion: rbac.authorization.k8s.io/v1",
      "kind: Role",
      "metadata:",
      "  name: agent-builder-api-deployer",
      "  namespace: ${var.namespace}",
      "rules:",
      "  - apiGroups: ['', 'apps', 'route.openshift.io']",
      "    resources: ['deployments', 'services', 'pods', 'pods/log', 'routes', 'configmaps', 'secrets']",
      "    verbs: ['get', 'list', 'watch', 'create', 'update', 'patch', 'delete']",
      "---",
      "apiVersion: rbac.authorization.k8s.io/v1",
      "kind: RoleBinding",
      "metadata:",
      "  name: agent-builder-api-deployer",
      "  namespace: ${var.namespace}",
      "roleRef:",
      "  apiGroup: rbac.authorization.k8s.io",
      "  kind: Role",
      "  name: agent-builder-api-deployer",
      "subjects:",
      "  - kind: ServiceAccount",
      "    name: agent-builder-api",
      "    namespace: ${var.namespace}",
      "---",
      "apiVersion: v1",
      "kind: Service",
      "metadata:",
      "  name: agent-builder-api",
      "  namespace: ${var.namespace}",
      "  labels:",
      "    app.kubernetes.io/name: agent-builder-api",
      "    app.kubernetes.io/part-of: agent-builder",
      "spec:",
      "  ports:",
      "    - port: 8000",
      "      targetPort: 8000",
      "      name: http",
      "  selector:",
      "    app.kubernetes.io/name: agent-builder-api",
      "  type: ClusterIP",
      "---",
      "apiVersion: route.openshift.io/v1",
      "kind: Route",
      "metadata:",
      "  name: agent-builder-api",
      "  namespace: ${var.namespace}",
      "  labels:",
      "    app.kubernetes.io/name: agent-builder-api",
      "    app.kubernetes.io/part-of: agent-builder",
      "spec:",
      "  host: ${var.api_host}",
      "  to:",
      "    kind: Service",
      "    name: agent-builder-api",
      "  port:",
      "    targetPort: http",
      "  tls:",
      "    termination: edge",
      "    insecureEdgeTerminationPolicy: Redirect",
      "EOF",

      "echo 'Waiting for Agent Builder API to be ready...'",
      "for i in $(seq 1 60); do",
      "  oc get pod -n ${var.namespace} -l app.kubernetes.io/name=agent-builder-api 2>/dev/null | grep -q Running && break",
      "  sleep 10",
      "done",
      "echo 'Agent Builder API deployment complete'",
    ]
  }

  depends_on = [null_resource.api_secret]
}

output "service_name" {
  value = "agent-builder-api"
}

output "port" {
  value = 8000
}
