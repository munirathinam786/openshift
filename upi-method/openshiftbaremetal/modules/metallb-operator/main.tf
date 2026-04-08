# =============================================================================
# Module: MetalLB Operator
# Layer 2 / BGP load balancer for bare metal clusters
# =============================================================================

variable "kubeconfig" { type = string }
variable "bastion_host" { type = string }
variable "bastion_user" { type = string }
variable "bastion_ssh_key" { type = string }
variable "metallb_address_pools" {
  description = "List of IPAddressPool definitions for MetalLB"
  type = list(object({
    name        = string
    addresses   = list(string)
    auto_assign = optional(bool, true)
  }))
  default = []
}
variable "metallb_l2_advertisements" {
  description = "List of L2Advertisement definitions"
  type = list(object({
    name       = string
    pool_names = list(string)
  }))
  default = []
}

# --- Install MetalLB Operator ---
resource "null_resource" "metallb_operator" {
  connection {
    type        = "ssh"
    host        = var.bastion_host
    user        = var.bastion_user
    private_key = file(var.bastion_ssh_key)
  }

  provisioner "remote-exec" {
    inline = [
      "export KUBECONFIG=${var.kubeconfig}",

      # Create namespace
      "cat <<'EOF' | oc apply -f -",
      "apiVersion: v1",
      "kind: Namespace",
      "metadata:",
      "  name: metallb-system",
      "  labels:",
      "    openshift.io/cluster-monitoring: 'true'",
      "EOF",

      # Create OperatorGroup
      "cat <<'EOF' | oc apply -f -",
      "apiVersion: operators.coreos.com/v1",
      "kind: OperatorGroup",
      "metadata:",
      "  name: metallb-operator",
      "  namespace: metallb-system",
      "spec:",
      "  targetNamespaces:",
      "    - metallb-system",
      "EOF",

      # Create Subscription
      "cat <<'EOF' | oc apply -f -",
      "apiVersion: operators.coreos.com/v1alpha1",
      "kind: Subscription",
      "metadata:",
      "  name: metallb-operator-sub",
      "  namespace: metallb-system",
      "spec:",
      "  channel: stable",
      "  installPlanApproval: Automatic",
      "  name: metallb-operator",
      "  source: redhat-operators",
      "  sourceNamespace: openshift-marketplace",
      "EOF",

      # Wait for operator
      "echo 'Waiting for MetalLB operator to install...'",
      "for i in $(seq 1 60); do",
      "  oc get csv -n metallb-system 2>/dev/null | grep metallb | grep -q Succeeded && break",
      "  sleep 10",
      "done",

      # Create MetalLB instance
      "cat <<'EOF' | oc apply -f -",
      "apiVersion: metallb.io/v1beta1",
      "kind: MetalLB",
      "metadata:",
      "  name: metallb",
      "  namespace: metallb-system",
      "spec: {}",
      "EOF",

      # Wait for MetalLB pods
      "echo 'Waiting for MetalLB pods...'",
      "for i in $(seq 1 60); do",
      "  READY=$(oc get pods -n metallb-system --no-headers 2>/dev/null | grep -c Running)",
      "  [ \"$READY\" -ge 1 ] && echo 'MetalLB pods running' && break",
      "  sleep 10",
      "done",

      "echo 'MetalLB Operator installed'",
    ]
  }
}

# --- Create IPAddressPools ---
resource "null_resource" "metallb_address_pools" {
  for_each = { for pool in var.metallb_address_pools : pool.name => pool }

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
      "apiVersion: metallb.io/v1beta1",
      "kind: IPAddressPool",
      "metadata:",
      "  name: ${each.value.name}",
      "  namespace: metallb-system",
      "spec:",
      "  addresses:",
      join("\n", [for addr in each.value.addresses : "    - ${addr}"]),
      "  autoAssign: ${each.value.auto_assign}",
      "EOF",

      "echo 'IPAddressPool ${each.value.name} created'",
    ]
  }

  depends_on = [null_resource.metallb_operator]
}

# --- Create L2Advertisements ---
resource "null_resource" "metallb_l2_advertisements" {
  for_each = { for adv in var.metallb_l2_advertisements : adv.name => adv }

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
      "apiVersion: metallb.io/v1beta1",
      "kind: L2Advertisement",
      "metadata:",
      "  name: ${each.value.name}",
      "  namespace: metallb-system",
      "spec:",
      "  ipAddressPools:",
      join("\n", [for p in each.value.pool_names : "    - ${p}"]),
      "EOF",

      "echo 'L2Advertisement ${each.value.name} created'",
    ]
  }

  depends_on = [null_resource.metallb_address_pools]
}
