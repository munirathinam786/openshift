# =============================================================================
# Module: Custom Grafana Dashboards
# Deploys cluster capacity, namespace usage, GPU utilization dashboards
# =============================================================================

variable "kubeconfig" { type = string }
variable "bastion_host" { type = string }
variable "bastion_user" { type = string }
variable "bastion_ssh_key" { type = string }
variable "enable_gpu_dashboard" {
  description = "Deploy NVIDIA GPU utilization dashboard"
  type        = bool
  default     = false
}
variable "grafana_namespace" {
  description = "Namespace for custom Grafana instance"
  type        = string
  default     = "grafana-custom"
}

resource "null_resource" "grafana_operator" {
  connection {
    type        = "ssh"
    host        = var.bastion_host
    user        = var.bastion_user
    private_key = file(var.bastion_ssh_key)
  }

  provisioner "remote-exec" {
    inline = [
      "export KUBECONFIG=${var.kubeconfig}",

      "oc create namespace ${var.grafana_namespace} --dry-run=client -o yaml | oc apply -f -",

      # Deploy community Grafana Operator
      "cat <<'EOF' | oc apply -f -",
      "apiVersion: operators.coreos.com/v1",
      "kind: OperatorGroup",
      "metadata:",
      "  name: grafana-operator",
      "  namespace: ${var.grafana_namespace}",
      "spec:",
      "  targetNamespaces:",
      "    - ${var.grafana_namespace}",
      "EOF",

      "cat <<'EOF' | oc apply -f -",
      "apiVersion: operators.coreos.com/v1alpha1",
      "kind: Subscription",
      "metadata:",
      "  name: grafana-operator",
      "  namespace: ${var.grafana_namespace}",
      "spec:",
      "  channel: v5",
      "  installPlanApproval: Automatic",
      "  name: grafana-operator",
      "  source: community-operators",
      "  sourceNamespace: openshift-marketplace",
      "EOF",

      "echo 'Waiting for Grafana Operator...'",
      "for i in $(seq 1 60); do",
      "  oc get csv -n ${var.grafana_namespace} 2>/dev/null | grep grafana | grep -q Succeeded && break",
      "  sleep 10",
      "done",

      # Create Grafana instance
      "cat <<'EOF' | oc apply -f -",
      "apiVersion: grafana.integreatly.org/v1beta1",
      "kind: Grafana",
      "metadata:",
      "  name: grafana",
      "  namespace: ${var.grafana_namespace}",
      "spec:",
      "  route:",
      "    spec:",
      "      tls:",
      "        termination: edge",
      "  config:",
      "    auth:",
      "      disable_login_form: 'false'",
      "    security:",
      "      admin_user: admin",
      "      admin_password: admin",
      "EOF",

      "sleep 30",

      # Create datasource pointing to Thanos Querier
      "BEARER_TOKEN=$(oc sa get-token grafana-sa -n ${var.grafana_namespace} 2>/dev/null || echo '')",

      "cat <<'EOF' | oc apply -f -",
      "apiVersion: grafana.integreatly.org/v1beta1",
      "kind: GrafanaDatasource",
      "metadata:",
      "  name: prometheus",
      "  namespace: ${var.grafana_namespace}",
      "spec:",
      "  instanceSelector:",
      "    matchLabels:",
      "      dashboards: grafana",
      "  datasource:",
      "    name: Prometheus",
      "    type: prometheus",
      "    access: proxy",
      "    url: https://thanos-querier.openshift-monitoring.svc.cluster.local:9091",
      "    isDefault: true",
      "    jsonData:",
      "      httpHeaderName1: Authorization",
      "      timeInterval: 5s",
      "      tlsSkipVerify: true",
      "    secureJsonData:",
      "      httpHeaderValue1: 'Bearer $${BEARER_TOKEN}'",
      "EOF",

      "echo 'Grafana instance and datasource created'",
    ]
  }
}

# --- Cluster Capacity Dashboard ---
resource "null_resource" "cluster_capacity_dashboard" {
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
      "apiVersion: grafana.integreatly.org/v1beta1",
      "kind: GrafanaDashboard",
      "metadata:",
      "  name: cluster-capacity",
      "  namespace: ${var.grafana_namespace}",
      "spec:",
      "  instanceSelector:",
      "    matchLabels:",
      "      dashboards: grafana",
      "  json: |",
      "    {",
      "      \"title\": \"Cluster Capacity Overview\",",
      "      \"uid\": \"cluster-capacity\",",
      "      \"panels\": [",
      "        {\"title\": \"CPU Utilization\", \"type\": \"gauge\", \"targets\": [{\"expr\": \"1 - avg(rate(node_cpu_seconds_total{mode='idle'}[5m]))\"}]},",
      "        {\"title\": \"Memory Utilization\", \"type\": \"gauge\", \"targets\": [{\"expr\": \"1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)\"}]},",
      "        {\"title\": \"Pod Count\", \"type\": \"stat\", \"targets\": [{\"expr\": \"count(kube_pod_info)\"}]},",
      "        {\"title\": \"Node Count\", \"type\": \"stat\", \"targets\": [{\"expr\": \"count(kube_node_info)\"}]}",
      "      ]",
      "    }",
      "EOF",

      "echo 'Cluster Capacity dashboard deployed'",
    ]
  }

  depends_on = [null_resource.grafana_operator]
}

# --- Namespace Usage Dashboard ---
resource "null_resource" "namespace_usage_dashboard" {
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
      "apiVersion: grafana.integreatly.org/v1beta1",
      "kind: GrafanaDashboard",
      "metadata:",
      "  name: namespace-usage",
      "  namespace: ${var.grafana_namespace}",
      "spec:",
      "  instanceSelector:",
      "    matchLabels:",
      "      dashboards: grafana",
      "  json: |",
      "    {",
      "      \"title\": \"Namespace Resource Usage\",",
      "      \"uid\": \"namespace-usage\",",
      "      \"templating\": {\"list\": [{\"name\": \"namespace\", \"type\": \"query\", \"query\": \"label_values(kube_namespace_labels, namespace)\"}]},",
      "      \"panels\": [",
      "        {\"title\": \"CPU Usage by Namespace\", \"type\": \"timeseries\", \"targets\": [{\"expr\": \"sum(rate(container_cpu_usage_seconds_total{namespace='$namespace'}[5m])) by (pod)\"}]},",
      "        {\"title\": \"Memory Usage by Namespace\", \"type\": \"timeseries\", \"targets\": [{\"expr\": \"sum(container_memory_working_set_bytes{namespace='$namespace'}) by (pod)\"}]}",
      "      ]",
      "    }",
      "EOF",

      "echo 'Namespace Usage dashboard deployed'",
    ]
  }

  depends_on = [null_resource.grafana_operator]
}

# --- GPU Utilization Dashboard ---
resource "null_resource" "gpu_dashboard" {
  count = var.enable_gpu_dashboard ? 1 : 0

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
      "apiVersion: grafana.integreatly.org/v1beta1",
      "kind: GrafanaDashboard",
      "metadata:",
      "  name: gpu-utilization",
      "  namespace: ${var.grafana_namespace}",
      "spec:",
      "  instanceSelector:",
      "    matchLabels:",
      "      dashboards: grafana",
      "  json: |",
      "    {",
      "      \"title\": \"NVIDIA GPU Utilization\",",
      "      \"uid\": \"gpu-utilization\",",
      "      \"panels\": [",
      "        {\"title\": \"GPU Utilization (%)\", \"type\": \"timeseries\", \"targets\": [{\"expr\": \"DCGM_FI_DEV_GPU_UTIL\"}]},",
      "        {\"title\": \"GPU Memory Used (MiB)\", \"type\": \"timeseries\", \"targets\": [{\"expr\": \"DCGM_FI_DEV_FB_USED\"}]},",
      "        {\"title\": \"GPU Temperature (°C)\", \"type\": \"timeseries\", \"targets\": [{\"expr\": \"DCGM_FI_DEV_GPU_TEMP\"}]},",
      "        {\"title\": \"GPU Power Usage (W)\", \"type\": \"timeseries\", \"targets\": [{\"expr\": \"DCGM_FI_DEV_POWER_USAGE\"}]}",
      "      ]",
      "    }",
      "EOF",

      "echo 'GPU Utilization dashboard deployed'",
    ]
  }

  depends_on = [null_resource.grafana_operator]
}
