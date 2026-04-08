# =============================================================================
# Module: Cost Management — Red Hat Cost Management for OpenShift
# =============================================================================

variable "kubeconfig" { type = string }
variable "bastion_host" { type = string }
variable "bastion_user" { type = string }
variable "bastion_ssh_key" { type = string }
variable "cost_management_channel" {
  description = "OLM channel for Cost Management Metrics Operator"
  type        = string
  default     = "stable"
}
variable "cost_management_source_name" {
  description = "Source name for cost management reporting"
  type        = string
  default     = "openshift-cluster"
}
variable "cost_management_upload_cycle" {
  description = "Upload cycle in minutes"
  type        = number
  default     = 360
}

resource "null_resource" "cost_management_operator" {
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
      "  name: costmanagement-metrics-operator",
      "EOF",

      "cat <<'EOF' | oc apply -f -",
      "apiVersion: operators.coreos.com/v1",
      "kind: OperatorGroup",
      "metadata:",
      "  name: costmanagement-metrics-operator",
      "  namespace: costmanagement-metrics-operator",
      "spec:",
      "  targetNamespaces:",
      "    - costmanagement-metrics-operator",
      "EOF",

      "cat <<'EOF' | oc apply -f -",
      "apiVersion: operators.coreos.com/v1alpha1",
      "kind: Subscription",
      "metadata:",
      "  name: costmanagement-metrics-operator",
      "  namespace: costmanagement-metrics-operator",
      "spec:",
      "  channel: ${var.cost_management_channel}",
      "  installPlanApproval: Automatic",
      "  name: costmanagement-metrics-operator",
      "  source: redhat-operators",
      "  sourceNamespace: openshift-marketplace",
      "EOF",

      "echo 'Waiting for Cost Management Operator...'",
      "for i in $(seq 1 60); do",
      "  oc get csv -n costmanagement-metrics-operator 2>/dev/null | grep costmanagement | grep -q Succeeded && break",
      "  sleep 10",
      "done",

      # Create CostManagementMetricsConfig
      "cat <<EOF | oc apply -f -",
      "apiVersion: costmanagement-metrics-cfg.openshift.io/v1beta1",
      "kind: CostManagementMetricsConfig",
      "metadata:",
      "  name: costmanagementmetricscfg",
      "  namespace: costmanagement-metrics-operator",
      "spec:",
      "  authentication:",
      "    type: token",
      "  packaging:",
      "    max_reports_to_store: 30",
      "    max_size_MB: 100",
      "  source:",
      "    name: ${var.cost_management_source_name}",
      "    create_source: true",
      "  upload:",
      "    upload_cycle: ${var.cost_management_upload_cycle}",
      "    upload_toggle: true",
      "EOF",

      "echo 'Cost Management Metrics Operator deployed'",
    ]
  }
}
