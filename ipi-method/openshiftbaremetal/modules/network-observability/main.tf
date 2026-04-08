# Author: Sathishkumar Munirathinam

# =============================================================================
# Module: Network Observability — eBPF-based flow collection
# =============================================================================

variable "kubeconfig" { type = string }
variable "bastion_host" { type = string }
variable "bastion_user" { type = string }
variable "bastion_ssh_key" { type = string }
variable "netobserv_sampling" {
  description = "eBPF flow sampling rate (1 = every packet, 50 = every 50th)"
  type        = number
  default     = 50
}
variable "netobserv_loki_enable" {
  description = "Enable Loki as the flow store"
  type        = bool
  default     = true
}
variable "netobserv_loki_url" {
  description = "Loki ingester URL"
  type        = string
  default     = "https://loki-gateway-http.netobserv.svc:8080/api/logs/v1/network"
}

resource "null_resource" "network_observability_operator" {
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
      "kind: Namespace",
      "metadata:",
      "  name: netobserv",
      "EOF",

      "cat <<'EOF' | oc apply -f -",
      "apiVersion: operators.coreos.com/v1",
      "kind: OperatorGroup",
      "metadata:",
      "  name: netobserv",
      "  namespace: netobserv",
      "spec: {}",
      "EOF",

      "cat <<'EOF' | oc apply -f -",
      "apiVersion: operators.coreos.com/v1alpha1",
      "kind: Subscription",
      "metadata:",
      "  name: netobserv-operator",
      "  namespace: netobserv",
      "spec:",
      "  channel: stable",
      "  installPlanApproval: Automatic",
      "  name: netobserv-operator",
      "  source: redhat-operators",
      "  sourceNamespace: openshift-marketplace",
      "EOF",

      "echo 'Waiting for Network Observability Operator...'",
      "for i in $(seq 1 60); do",
      "  oc get csv -n netobserv 2>/dev/null | grep netobserv | grep -q Succeeded && break",
      "  sleep 10",
      "done",

      # Install Loki Operator (dependency)
      "cat <<'EOF' | oc apply -f -",
      "apiVersion: operators.coreos.com/v1alpha1",
      "kind: Subscription",
      "metadata:",
      "  name: loki-operator",
      "  namespace: openshift-operators-redhat",
      "spec:",
      "  channel: stable-6.1",
      "  installPlanApproval: Automatic",
      "  name: loki-operator",
      "  source: redhat-operators",
      "  sourceNamespace: openshift-marketplace",
      "EOF",

      "sleep 30",

      # Create FlowCollector
      "cat <<EOF | oc apply -f -",
      "apiVersion: flows.netobserv.io/v1beta2",
      "kind: FlowCollector",
      "metadata:",
      "  name: cluster",
      "spec:",
      "  namespace: netobserv",
      "  deploymentModel: Direct",
      "  agent:",
      "    type: eBPF",
      "    ebpf:",
      "      sampling: ${var.netobserv_sampling}",
      "      privileged: true",
      "  processor:",
      "    logTypes: Flows",
      "  loki:",
      "    enable: ${var.netobserv_loki_enable}",
      "    url: ${var.netobserv_loki_url}",
      "    mode: LokiStack",
      "  consolePlugin:",
      "    register: true",
      "    portNaming:",
      "      enable: true",
      "EOF",

      "echo 'Network Observability FlowCollector deployed'",
    ]
  }
}
