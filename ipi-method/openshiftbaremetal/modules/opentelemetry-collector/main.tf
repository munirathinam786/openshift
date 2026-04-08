# Author: Sathishkumar Munirathinam

# =============================================================================
# Module: OpenTelemetry Collector — Distributed Tracing
# =============================================================================

variable "kubeconfig" { type = string }
variable "bastion_host" { type = string }
variable "bastion_user" { type = string }
variable "bastion_ssh_key" { type = string }
variable "otel_collector_mode" {
  description = "Collector deployment mode (deployment, daemonset, sidecar)"
  type        = string
  default     = "deployment"
}
variable "tempo_endpoint" {
  description = "Tempo/Jaeger endpoint for trace export"
  type        = string
  default     = "tempo-simplest-distributor.openshift-tempo:4317"
}

resource "null_resource" "otel_operator" {
  connection {
    type        = "ssh"
    host        = var.bastion_host
    user        = var.bastion_user
    private_key = file(var.bastion_ssh_key)
  }

  provisioner "remote-exec" {
    inline = [
      "export KUBECONFIG=${var.kubeconfig}",

      # Install Red Hat build of OpenTelemetry
      "cat <<'EOF' | oc apply -f -",
      "apiVersion: operators.coreos.com/v1alpha1",
      "kind: Subscription",
      "metadata:",
      "  name: opentelemetry-product",
      "  namespace: openshift-opentelemetry-operator",
      "spec:",
      "  channel: stable",
      "  installPlanApproval: Automatic",
      "  name: opentelemetry-product",
      "  source: redhat-operators",
      "  sourceNamespace: openshift-marketplace",
      "EOF",

      # Install Tempo Operator
      "cat <<'EOF' | oc apply -f -",
      "apiVersion: operators.coreos.com/v1alpha1",
      "kind: Subscription",
      "metadata:",
      "  name: tempo-product",
      "  namespace: openshift-tempo-operator",
      "spec:",
      "  channel: stable",
      "  installPlanApproval: Automatic",
      "  name: tempo-product",
      "  source: redhat-operators",
      "  sourceNamespace: openshift-marketplace",
      "EOF",

      "echo 'Waiting for OpenTelemetry Operator...'",
      "for i in $(seq 1 60); do",
      "  oc get csv -n openshift-opentelemetry-operator 2>/dev/null | grep opentelemetry | grep -q Succeeded && break",
      "  sleep 10",
      "done",

      "sleep 30",

      # Create TempoStack
      "cat <<'EOF' | oc apply -f -",
      "apiVersion: v1",
      "kind: Namespace",
      "metadata:",
      "  name: openshift-tempo",
      "EOF",

      "cat <<'EOF' | oc apply -f -",
      "apiVersion: tempo.grafana.com/v1alpha1",
      "kind: TempoStack",
      "metadata:",
      "  name: simplest",
      "  namespace: openshift-tempo",
      "spec:",
      "  storage:",
      "    secret:",
      "      name: tempo-storage-secret",
      "      type: s3",
      "  storageSize: 10Gi",
      "  resources:",
      "    total:",
      "      limits:",
      "        memory: 2Gi",
      "  template:",
      "    queryFrontend:",
      "      jaegerQuery:",
      "        enabled: true",
      "        ingress:",
      "          type: route",
      "EOF",

      # Create OpenTelemetryCollector
      "cat <<EOF | oc apply -f -",
      "apiVersion: opentelemetry.io/v1beta1",
      "kind: OpenTelemetryCollector",
      "metadata:",
      "  name: otel-collector",
      "  namespace: openshift-opentelemetry-operator",
      "spec:",
      "  mode: ${var.otel_collector_mode}",
      "  config:",
      "    receivers:",
      "      otlp:",
      "        protocols:",
      "          grpc:",
      "            endpoint: 0.0.0.0:4317",
      "          http:",
      "            endpoint: 0.0.0.0:4318",
      "    processors:",
      "      batch:",
      "        timeout: 5s",
      "        send_batch_size: 10000",
      "      memory_limiter:",
      "        check_interval: 5s",
      "        limit_mib: 1024",
      "    exporters:",
      "      otlp:",
      "        endpoint: ${var.tempo_endpoint}",
      "        tls:",
      "          insecure: true",
      "    service:",
      "      pipelines:",
      "        traces:",
      "          receivers: [otlp]",
      "          processors: [memory_limiter, batch]",
      "          exporters: [otlp]",
      "EOF",

      "echo 'OpenTelemetry Collector and Tempo deployed'",
    ]
  }
}
