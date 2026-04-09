# Author: Sathishkumar Munirathinam
# Module: Agent Deployment Service — Deploys agents to Kubernetes

variable "bastion_host" { type = string }
variable "bastion_user" { type = string }
variable "bastion_ssh_key" { type = string }
variable "kubeconfig" { type = string }
variable "namespace" { type = string }
variable "container_image" { type = string }
variable "temporal_host" { type = string }
variable "mongodb_uri" { type = string; sensitive = true }
variable "deploy_svc_host" { type = string }

resource "null_resource" "deploy_svc_secret" {
  connection {
    type        = "ssh"
    host        = var.bastion_host
    user        = var.bastion_user
    private_key = file(var.bastion_ssh_key)
  }

  provisioner "remote-exec" {
    inline = [
      "export KUBECONFIG=${var.kubeconfig}",

      "oc create secret generic agent-builder-deploy-svc-env -n ${var.namespace} \\",
      "  --from-literal=MONGODB_URI='${var.mongodb_uri}' \\",
      "  --dry-run=client -o yaml | oc apply -f -",
    ]
  }
}

resource "null_resource" "deploy_svc" {
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
      "kind: ServiceAccount",
      "metadata:",
      "  name: agent-deployment-service",
      "  namespace: ${var.namespace}",
      "  labels:",
      "    app.kubernetes.io/name: agent-deployment-service",
      "    app.kubernetes.io/part-of: agent-builder",
      "---",
      "apiVersion: rbac.authorization.k8s.io/v1",
      "kind: ClusterRole",
      "metadata:",
      "  name: agent-deployment-service",
      "rules:",
      "  - apiGroups: ['', 'apps', 'route.openshift.io', 'image.openshift.io', 'build.openshift.io']",
      "    resources: ['namespaces', 'deployments', 'services', 'pods', 'pods/log', 'routes', 'configmaps', 'secrets', 'imagestreams', 'buildconfigs', 'builds']",
      "    verbs: ['get', 'list', 'watch', 'create', 'update', 'patch', 'delete']",
      "---",
      "apiVersion: rbac.authorization.k8s.io/v1",
      "kind: ClusterRoleBinding",
      "metadata:",
      "  name: agent-deployment-service",
      "roleRef:",
      "  apiGroup: rbac.authorization.k8s.io",
      "  kind: ClusterRole",
      "  name: agent-deployment-service",
      "subjects:",
      "  - kind: ServiceAccount",
      "    name: agent-deployment-service",
      "    namespace: ${var.namespace}",
      "---",
      "apiVersion: apps/v1",
      "kind: Deployment",
      "metadata:",
      "  name: agent-builder-deploy-svc",
      "  namespace: ${var.namespace}",
      "  labels:",
      "    app.kubernetes.io/name: agent-deployment-service",
      "    app.kubernetes.io/part-of: agent-builder",
      "spec:",
      "  replicas: 1",
      "  selector:",
      "    matchLabels:",
      "      app.kubernetes.io/name: agent-deployment-service",
      "  template:",
      "    metadata:",
      "      labels:",
      "        app.kubernetes.io/name: agent-deployment-service",
      "        app.kubernetes.io/part-of: agent-builder",
      "    spec:",
      "      serviceAccountName: agent-deployment-service",
      "      containers:",
      "        - name: deploy-svc",
      "          image: ${var.container_image}",
      "          ports:",
      "            - containerPort: 8001",
      "              name: http",
      "          env:",
      "            - name: TEMPORAL_HOST",
      "              value: ${var.temporal_host}",
      "            - name: TEMPORAL_NAMESPACE",
      "              value: agent-builder",
      "            - name: K8S_NAMESPACE",
      "              value: ${var.namespace}",
      "            - name: MONGODB_DATABASE",
      "              value: agent_deployments",
      "          envFrom:",
      "            - secretRef:",
      "                name: agent-builder-deploy-svc-env",
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
      "              port: 8001",
      "            initialDelaySeconds: 20",
      "            periodSeconds: 10",
      "          readinessProbe:",
      "            httpGet:",
      "              path: /health",
      "              port: 8001",
      "            initialDelaySeconds: 10",
      "            periodSeconds: 5",
      "---",
      "apiVersion: v1",
      "kind: Service",
      "metadata:",
      "  name: agent-builder-deploy-svc",
      "  namespace: ${var.namespace}",
      "  labels:",
      "    app.kubernetes.io/name: agent-deployment-service",
      "    app.kubernetes.io/part-of: agent-builder",
      "spec:",
      "  ports:",
      "    - port: 8001",
      "      targetPort: 8001",
      "      name: http",
      "  selector:",
      "    app.kubernetes.io/name: agent-deployment-service",
      "  type: ClusterIP",
      "---",
      "apiVersion: route.openshift.io/v1",
      "kind: Route",
      "metadata:",
      "  name: agent-builder-deploy-svc",
      "  namespace: ${var.namespace}",
      "  labels:",
      "    app.kubernetes.io/name: agent-deployment-service",
      "    app.kubernetes.io/part-of: agent-builder",
      "spec:",
      "  host: ${var.deploy_svc_host}",
      "  to:",
      "    kind: Service",
      "    name: agent-builder-deploy-svc",
      "  port:",
      "    targetPort: http",
      "  tls:",
      "    termination: edge",
      "    insecureEdgeTerminationPolicy: Redirect",
      "EOF",

      "echo 'Agent Deployment Service deployment complete'",
    ]
  }

  depends_on = [null_resource.deploy_svc_secret]
}

output "service_name" {
  value = "agent-builder-deploy-svc"
}

output "port" {
  value = 8001
}
