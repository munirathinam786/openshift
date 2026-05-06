# Author: Sathishkumar Munirathinam
# Module: Temporal — Server + Web UI for workflow orchestration

variable "bastion_host" { type = string }
variable "bastion_user" { type = string }
variable "bastion_ssh_key" { type = string }
variable "kubeconfig" { type = string }
variable "namespace" { type = string }
variable "postgres_host" { type = string }
variable "postgres_password" { type = string; sensitive = true }
variable "temporal_ui_host" { type = string }

resource "null_resource" "temporal_secret" {
  connection {
    type        = "ssh"
    host        = var.bastion_host
    user        = var.bastion_user
    private_key = file(var.bastion_ssh_key)
  }

  provisioner "remote-exec" {
    inline = [
      "export KUBECONFIG=${var.kubeconfig}",

      "oc create secret generic agent-builder-temporal-credentials -n ${var.namespace} \\",
      "  --from-literal=POSTGRES_PASSWORD='${var.postgres_password}' \\",
      "  --from-literal=POSTGRES_USER=agentbuilder \\",
      "  --dry-run=client -o yaml | oc apply -f -",
    ]
  }
}

resource "null_resource" "temporal_config" {
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
      "  name: agent-builder-temporal-config",
      "  namespace: ${var.namespace}",
      "data:",
      "  TEMPORAL_ADDRESS: 0.0.0.0:7233",
      "  DB: postgresql",
      "  DB_PORT: '5432'",
      "  POSTGRES_SEEDS: ${var.postgres_host}",
      "  DBNAME: temporal_db",
      "  VISIBILITY_DBNAME: temporal_visibility_db",
      "  TEMPORAL_BROADCAST_ADDRESS: 0.0.0.0",
      "  NUM_HISTORY_SHARDS: '512'",
      "  SKIP_DEFAULT_NAMESPACE_CREATION: 'false'",
      "  DEFAULT_NAMESPACE: agent-builder",
      "  SKIP_SCHEMA_SETUP: 'false'",
      "  TEMPORAL_CLI_ADDRESS: agent-builder-temporal:7233",
      "EOF",
    ]
  }

  depends_on = [null_resource.temporal_secret]
}

resource "null_resource" "temporal_server" {
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
      "  name: agent-builder-temporal",
      "  namespace: ${var.namespace}",
      "  labels:",
      "    app.kubernetes.io/name: temporal",
      "    app.kubernetes.io/component: server",
      "    app.kubernetes.io/part-of: agent-builder",
      "spec:",
      "  replicas: 1",
      "  selector:",
      "    matchLabels:",
      "      app.kubernetes.io/name: temporal",
      "      app.kubernetes.io/component: server",
      "  template:",
      "    metadata:",
      "      labels:",
      "        app.kubernetes.io/name: temporal",
      "        app.kubernetes.io/component: server",
      "        app.kubernetes.io/part-of: agent-builder",
      "    spec:",
      "      containers:",
      "        - name: temporal",
      "          image: temporalio/auto-setup:1.30.4",
      "          ports:",
      "            - containerPort: 7233",
      "              name: frontend",
      "            - containerPort: 6831",
      "              name: jaeger",
      "            - containerPort: 9090",
      "              name: metrics",
      "          envFrom:",
      "            - configMapRef:",
      "                name: agent-builder-temporal-config",
      "          env:",
      "            - name: POSTGRES_PWD",
      "              valueFrom:",
      "                secretKeyRef:",
      "                  name: agent-builder-temporal-credentials",
      "                  key: POSTGRES_PASSWORD",
      "            - name: POSTGRES_USER",
      "              valueFrom:",
      "                secretKeyRef:",
      "                  name: agent-builder-temporal-credentials",
      "                  key: POSTGRES_USER",
      "          resources:",
      "            requests:",
      "              cpu: 500m",
      "              memory: 1Gi",
      "            limits:",
      "              cpu: '2'",
      "              memory: 4Gi",
      "          livenessProbe:",
      "            tcpSocket:",
      "              port: 7233",
      "            initialDelaySeconds: 60",
      "            periodSeconds: 10",
      "          readinessProbe:",
      "            tcpSocket:",
      "              port: 7233",
      "            initialDelaySeconds: 30",
      "            periodSeconds: 10",
      "---",
      "apiVersion: v1",
      "kind: Service",
      "metadata:",
      "  name: agent-builder-temporal",
      "  namespace: ${var.namespace}",
      "  labels:",
      "    app.kubernetes.io/name: temporal",
      "    app.kubernetes.io/component: server",
      "    app.kubernetes.io/part-of: agent-builder",
      "spec:",
      "  ports:",
      "    - port: 7233",
      "      targetPort: 7233",
      "      name: frontend",
      "    - port: 9090",
      "      targetPort: 9090",
      "      name: metrics",
      "  selector:",
      "    app.kubernetes.io/name: temporal",
      "    app.kubernetes.io/component: server",
      "  type: ClusterIP",
      "EOF",

      "echo 'Waiting for Temporal Server to be ready...'",
      "for i in $(seq 1 90); do",
      "  oc get pod -n ${var.namespace} -l app.kubernetes.io/name=temporal,app.kubernetes.io/component=server 2>/dev/null | grep -q Running && break",
      "  sleep 10",
      "done",
      "echo 'Temporal Server deployment complete'",
    ]
  }

  depends_on = [null_resource.temporal_config]
}

resource "null_resource" "temporal_ui" {
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
      "  name: agent-builder-temporal-ui",
      "  namespace: ${var.namespace}",
      "  labels:",
      "    app.kubernetes.io/name: temporal",
      "    app.kubernetes.io/component: ui",
      "    app.kubernetes.io/part-of: agent-builder",
      "spec:",
      "  replicas: 1",
      "  selector:",
      "    matchLabels:",
      "      app.kubernetes.io/name: temporal",
      "      app.kubernetes.io/component: ui",
      "  template:",
      "    metadata:",
      "      labels:",
      "        app.kubernetes.io/name: temporal",
      "        app.kubernetes.io/component: ui",
      "        app.kubernetes.io/part-of: agent-builder",
      "    spec:",
      "      containers:",
      "        - name: temporal-ui",
      "          image: temporalio/ui:2.49.1",
      "          ports:",
      "            - containerPort: 8080",
      "              name: http",
      "          env:",
      "            - name: TEMPORAL_ADDRESS",
      "              value: agent-builder-temporal:7233",
      "            - name: TEMPORAL_CORS_ORIGINS",
      "              value: https://${var.temporal_ui_host}",
      "          resources:",
      "            requests:",
      "              cpu: 100m",
      "              memory: 128Mi",
      "            limits:",
      "              cpu: 500m",
      "              memory: 512Mi",
      "          livenessProbe:",
      "            httpGet:",
      "              path: /",
      "              port: 8080",
      "            initialDelaySeconds: 15",
      "            periodSeconds: 10",
      "---",
      "apiVersion: v1",
      "kind: Service",
      "metadata:",
      "  name: agent-builder-temporal-ui",
      "  namespace: ${var.namespace}",
      "  labels:",
      "    app.kubernetes.io/name: temporal",
      "    app.kubernetes.io/component: ui",
      "    app.kubernetes.io/part-of: agent-builder",
      "spec:",
      "  ports:",
      "    - port: 8080",
      "      targetPort: 8080",
      "      name: http",
      "  selector:",
      "    app.kubernetes.io/name: temporal",
      "    app.kubernetes.io/component: ui",
      "  type: ClusterIP",
      "---",
      "apiVersion: route.openshift.io/v1",
      "kind: Route",
      "metadata:",
      "  name: agent-builder-temporal-ui",
      "  namespace: ${var.namespace}",
      "  labels:",
      "    app.kubernetes.io/name: temporal",
      "    app.kubernetes.io/component: ui",
      "    app.kubernetes.io/part-of: agent-builder",
      "spec:",
      "  host: ${var.temporal_ui_host}",
      "  to:",
      "    kind: Service",
      "    name: agent-builder-temporal-ui",
      "  port:",
      "    targetPort: http",
      "  tls:",
      "    termination: edge",
      "    insecureEdgeTerminationPolicy: Redirect",
      "EOF",

      "echo 'Temporal UI deployment complete'",
    ]
  }

  depends_on = [null_resource.temporal_server]
}

output "service_name" {
  value = "agent-builder-temporal"
}

output "frontend_port" {
  value = 7233
}

output "ui_port" {
  value = 8080
}
