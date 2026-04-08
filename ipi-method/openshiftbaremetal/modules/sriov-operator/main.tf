# =============================================================================
# Module: SR-IOV Network Operator
# Enables high-performance networking via Single Root I/O Virtualization
# =============================================================================

variable "kubeconfig" { type = string }
variable "bastion_host" { type = string }
variable "bastion_user" { type = string }
variable "bastion_ssh_key" { type = string }
variable "sriov_node_selector" {
  description = "Node label selector for SR-IOV capable nodes"
  type        = map(string)
  default     = { "node-role.kubernetes.io/worker" = "" }
}
variable "sriov_network_devices" {
  description = "List of SR-IOV network device configurations"
  type = list(object({
    name          = string
    pf_names      = list(string)
    num_vfs       = number
    resource_name = string
    device_type   = optional(string, "netdevice")
    root_devices  = optional(list(string), [])
  }))
  default = []
}
variable "sriov_networks" {
  description = "List of SR-IOV network attachment definitions"
  type = list(object({
    name             = string
    resource_name    = string
    target_namespace = string
    vlan             = optional(number, 0)
    ipam             = optional(string, "{}")
  }))
  default = []
}

# --- Install SR-IOV Network Operator ---
resource "null_resource" "sriov_operator" {
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
      "  name: openshift-sriov-network-operator",
      "  annotations:",
      "    workload.openshift.io/allowed: management",
      "EOF",

      # Create OperatorGroup
      "cat <<'EOF' | oc apply -f -",
      "apiVersion: operators.coreos.com/v1",
      "kind: OperatorGroup",
      "metadata:",
      "  name: sriov-network-operators",
      "  namespace: openshift-sriov-network-operator",
      "spec:",
      "  targetNamespaces:",
      "    - openshift-sriov-network-operator",
      "EOF",

      # Create Subscription
      "cat <<'EOF' | oc apply -f -",
      "apiVersion: operators.coreos.com/v1alpha1",
      "kind: Subscription",
      "metadata:",
      "  name: sriov-network-operator-subscription",
      "  namespace: openshift-sriov-network-operator",
      "spec:",
      "  channel: stable",
      "  installPlanApproval: Automatic",
      "  name: sriov-network-operator",
      "  source: redhat-operators",
      "  sourceNamespace: openshift-marketplace",
      "EOF",

      # Wait for operator to be ready
      "echo 'Waiting for SR-IOV Network Operator to install...'",
      "for i in $(seq 1 60); do",
      "  oc get csv -n openshift-sriov-network-operator 2>/dev/null | grep sriov | grep -q Succeeded && break",
      "  sleep 10",
      "done",

      # Verify SriovOperatorConfig exists
      "echo 'Verifying SriovOperatorConfig...'",
      "oc get sriovoperatorconfig default -n openshift-sriov-network-operator -o yaml 2>/dev/null || echo 'SriovOperatorConfig will be created by the operator'",

      "echo 'SR-IOV Network Operator installed'",
    ]
  }
}

# --- Create SriovNetworkNodePolicy for each device config ---
resource "null_resource" "sriov_node_policies" {
  for_each = { for idx, dev in var.sriov_network_devices : dev.name => dev }

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
      "apiVersion: sriovnetwork.openshift.io/v1",
      "kind: SriovNetworkNodePolicy",
      "metadata:",
      "  name: ${each.value.name}",
      "  namespace: openshift-sriov-network-operator",
      "spec:",
      "  resourceName: ${each.value.resource_name}",
      "  nodeSelector:",
      "    node-role.kubernetes.io/worker: ''",
      "  numVfs: ${each.value.num_vfs}",
      "  nicSelector:",
      "    pfNames:",
      join("\n", [for pf in each.value.pf_names : "      - ${pf}"]),
      "  deviceType: ${each.value.device_type}",
      "EOF",

      "echo 'SriovNetworkNodePolicy ${each.value.name} applied'",
    ]
  }

  depends_on = [null_resource.sriov_operator]
}

# --- Create SriovNetwork attachment definitions ---
resource "null_resource" "sriov_networks" {
  for_each = { for idx, net in var.sriov_networks : net.name => net }

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
      "apiVersion: sriovnetwork.openshift.io/v1",
      "kind: SriovNetwork",
      "metadata:",
      "  name: ${each.value.name}",
      "  namespace: openshift-sriov-network-operator",
      "spec:",
      "  resourceName: ${each.value.resource_name}",
      "  networkNamespace: ${each.value.target_namespace}",
      "  vlan: ${each.value.vlan}",
      "  ipam: '${each.value.ipam}'",
      "EOF",

      "echo 'SriovNetwork ${each.value.name} applied'",
    ]
  }

  depends_on = [null_resource.sriov_node_policies]
}
