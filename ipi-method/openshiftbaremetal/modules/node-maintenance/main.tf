# =============================================================================
# Module: Node Maintenance — Controlled node drain/cordon automation
# =============================================================================

variable "kubeconfig" { type = string }
variable "bastion_host" { type = string }
variable "bastion_user" { type = string }
variable "bastion_ssh_key" { type = string }
variable "node_maintenance_channel" {
  description = "OLM channel for Node Maintenance Operator"
  type        = string
  default     = "stable"
}

resource "null_resource" "node_maintenance_operator" {
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
      "  name: openshift-node-maintenance-operator",
      "EOF",

      "cat <<'EOF' | oc apply -f -",
      "apiVersion: operators.coreos.com/v1",
      "kind: OperatorGroup",
      "metadata:",
      "  name: node-maintenance-operator",
      "  namespace: openshift-node-maintenance-operator",
      "spec: {}",
      "EOF",

      "cat <<'EOF' | oc apply -f -",
      "apiVersion: operators.coreos.com/v1alpha1",
      "kind: Subscription",
      "metadata:",
      "  name: node-maintenance-operator",
      "  namespace: openshift-node-maintenance-operator",
      "spec:",
      "  channel: ${var.node_maintenance_channel}",
      "  installPlanApproval: Automatic",
      "  name: node-maintenance-operator",
      "  source: redhat-operators",
      "  sourceNamespace: openshift-marketplace",
      "EOF",

      "echo 'Waiting for Node Maintenance Operator CSV...'",
      "for i in $(seq 1 60); do",
      "  oc get csv -n openshift-node-maintenance-operator 2>/dev/null | grep node-maintenance | grep -q Succeeded && break",
      "  sleep 10",
      "done",

      "echo 'Node Maintenance Operator installed'",
    ]
  }
}
