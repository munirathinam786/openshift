# =============================================================================
# Module: NMState Operator — Declarative Node Network Configuration
# =============================================================================

variable "kubeconfig" { type = string }
variable "bastion_host" { type = string }
variable "bastion_user" { type = string }
variable "bastion_ssh_key" { type = string }
variable "nmstate_node_network_policies" {
  description = "List of NodeNetworkConfigurationPolicy definitions"
  type = list(object({
    name            = string
    node_selector   = map(string)
    desired_state   = string
  }))
  default = []
}

resource "null_resource" "nmstate_operator" {
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
      "  name: openshift-nmstate",
      "  labels:",
      "    openshift.io/cluster-monitoring: 'true'",
      "EOF",

      "cat <<'EOF' | oc apply -f -",
      "apiVersion: operators.coreos.com/v1",
      "kind: OperatorGroup",
      "metadata:",
      "  name: openshift-nmstate",
      "  namespace: openshift-nmstate",
      "spec:",
      "  targetNamespaces:",
      "    - openshift-nmstate",
      "EOF",

      "cat <<'EOF' | oc apply -f -",
      "apiVersion: operators.coreos.com/v1alpha1",
      "kind: Subscription",
      "metadata:",
      "  name: kubernetes-nmstate-operator",
      "  namespace: openshift-nmstate",
      "spec:",
      "  channel: stable",
      "  installPlanApproval: Automatic",
      "  name: kubernetes-nmstate-operator",
      "  source: redhat-operators",
      "  sourceNamespace: openshift-marketplace",
      "EOF",

      "echo 'Waiting for NMState Operator...'",
      "for i in $(seq 1 60); do",
      "  oc get csv -n openshift-nmstate 2>/dev/null | grep nmstate | grep -q Succeeded && break",
      "  sleep 10",
      "done",

      # Create NMState instance
      "cat <<'EOF' | oc apply -f -",
      "apiVersion: nmstate.io/v1",
      "kind: NMState",
      "metadata:",
      "  name: nmstate",
      "spec: {}",
      "EOF",

      "sleep 30",
      "echo 'NMState Operator installed'",
    ]
  }
}

# --- Apply NodeNetworkConfigurationPolicies ---
resource "null_resource" "nmstate_policies" {
  count = length(var.nmstate_node_network_policies)

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
      "apiVersion: nmstate.io/v1",
      "kind: NodeNetworkConfigurationPolicy",
      "metadata:",
      "  name: ${var.nmstate_node_network_policies[count.index].name}",
      "spec:",
      "  nodeSelector:",
      join("\n", [for k, v in var.nmstate_node_network_policies[count.index].node_selector : "    ${k}: '${v}'"]),
      "  desiredState:",
      "    ${indent(4, var.nmstate_node_network_policies[count.index].desired_state)}",
      "EOF",

      "echo 'NodeNetworkConfigurationPolicy ${var.nmstate_node_network_policies[count.index].name} applied'",
    ]
  }

  depends_on = [null_resource.nmstate_operator]
}
