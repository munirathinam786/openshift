# =============================================================================
# Submariner — Multi-Cluster Networking (DC ↔ DR)
# =============================================================================

variable "kubeconfig" {
  type = string
}

variable "bastion_host" {
  type = string
}

variable "bastion_user" {
  type = string
}

variable "bastion_ssh_key" {
  type = string
}

variable "cluster_role" {
  description = "Cluster role: broker or agent"
  type        = string
  validation {
    condition     = contains(["broker", "agent"], var.cluster_role)
    error_message = "cluster_role must be 'broker' or 'agent'."
  }
}

variable "broker_api_url" {
  description = "API URL of the broker cluster (required for agent role)"
  type        = string
  default     = ""
}

variable "broker_token" {
  description = "Service account token for broker cluster (required for agent role)"
  type        = string
  default     = ""
  sensitive   = true
}

variable "broker_ca" {
  description = "CA certificate of the broker cluster (required for agent role)"
  type        = string
  default     = ""
}

variable "cable_driver" {
  description = "Tunnel driver: libreswan, wireguard, or vxlan"
  type        = string
  default     = "libreswan"
}

variable "gateway_count" {
  description = "Number of gateway nodes"
  type        = number
  default     = 1
}

variable "cluster_cidr" {
  description = "Pod CIDR of this cluster"
  type        = string
}

variable "service_cidr" {
  description = "Service CIDR of this cluster"
  type        = string
}

variable "cluster_id" {
  description = "Unique cluster identifier for Submariner"
  type        = string
}

variable "globalnet_enabled" {
  description = "Enable Globalnet for overlapping CIDRs"
  type        = bool
  default     = false
}

variable "gateway_node_labels" {
  description = "Node selector labels for gateway nodes"
  type        = map(string)
  default     = { "submariner.io/gateway" = "true" }
}

# --- Label gateway nodes ---
resource "null_resource" "label_gateway_nodes" {
  provisioner "remote-exec" {
    inline = [
      "export KUBECONFIG=${var.kubeconfig}",
      "for key in ${join(" ", [for k, v in var.gateway_node_labels : "${k}=${v}"])}; do",
      "  oc label nodes -l node-role.kubernetes.io/worker \"$key\" --overwrite || true",
      "done",
    ]
    connection {
      type        = "ssh"
      host        = var.bastion_host
      user        = var.bastion_user
      private_key = file(var.bastion_ssh_key)
    }
  }
}

# --- Install Submariner Operator ---
resource "null_resource" "submariner_operator" {
  provisioner "remote-exec" {
    inline = [
      "export KUBECONFIG=${var.kubeconfig}",
      <<-EOT
      cat <<'EOF' | oc apply -f -
      apiVersion: v1
      kind: Namespace
      metadata:
        name: submariner-operator
        labels:
          openshift.io/cluster-monitoring: "true"
      EOF
      EOT
      ,
      <<-EOT
      cat <<'EOF' | oc apply -f -
      apiVersion: operators.coreos.com/v1
      kind: OperatorGroup
      metadata:
        name: submariner-operator-group
        namespace: submariner-operator
      spec:
        targetNamespaces:
          - submariner-operator
      EOF
      EOT
      ,
      <<-EOT
      cat <<'EOF' | oc apply -f -
      apiVersion: operators.coreos.com/v1alpha1
      kind: Subscription
      metadata:
        name: submariner
        namespace: submariner-operator
      spec:
        channel: stable-0.18
        installPlanApproval: Automatic
        name: submariner
        source: redhat-operators
        sourceNamespace: openshift-marketplace
      EOF
      EOT
      ,
      "echo 'Waiting for Submariner Operator CSV...'",
      "for i in $(seq 1 60); do oc get csv -n submariner-operator 2>/dev/null | grep -q Succeeded && break || sleep 10; done",
    ]
    connection {
      type        = "ssh"
      host        = var.bastion_host
      user        = var.bastion_user
      private_key = file(var.bastion_ssh_key)
    }
  }

  depends_on = [null_resource.label_gateway_nodes]
}

# --- Deploy Broker (DC Primary only) ---
resource "null_resource" "submariner_broker" {
  count = var.cluster_role == "broker" ? 1 : 0

  provisioner "remote-exec" {
    inline = [
      "export KUBECONFIG=${var.kubeconfig}",
      <<-EOT
      cat <<'EOF' | oc apply -f -
      apiVersion: submariner.io/v1alpha1
      kind: Broker
      metadata:
        name: submariner-broker
        namespace: submariner-operator
      spec:
        globalnetEnabled: ${var.globalnet_enabled}
      EOF
      EOT
      ,
      "echo 'Waiting for Broker to be ready...'",
      "sleep 30",
    ]
    connection {
      type        = "ssh"
      host        = var.bastion_host
      user        = var.bastion_user
      private_key = file(var.bastion_ssh_key)
    }
  }

  depends_on = [null_resource.submariner_operator]
}

# --- Deploy Submariner CR (both broker and agent clusters) ---
resource "null_resource" "submariner_cr" {
  provisioner "remote-exec" {
    inline = [
      "export KUBECONFIG=${var.kubeconfig}",
      <<-EOT
      cat <<'EOF' | oc apply -f -
      apiVersion: submariner.io/v1alpha1
      kind: Submariner
      metadata:
        name: submariner
        namespace: submariner-operator
      spec:
        broker: k8s
        brokerK8sApiServer: "${var.cluster_role == "broker" ? "" : var.broker_api_url}"
        brokerK8sApiServerToken: "${var.cluster_role == "broker" ? "" : var.broker_token}"
        brokerK8sCA: "${var.cluster_role == "broker" ? "" : var.broker_ca}"
        cableDriver: "${var.cable_driver}"
        ceIPSecDebug: false
        clusterCIDR: "${var.cluster_cidr}"
        clusterID: "${var.cluster_id}"
        debug: false
        globalCIDR: ""
        namespace: submariner-operator
        natEnabled: false
        serviceCIDR: "${var.service_cidr}"
        serviceDiscoveryEnabled: true
      EOF
      EOT
      ,
      "echo 'Waiting for Submariner gateway to be ready...'",
      "for i in $(seq 1 60); do oc get gateways.submariner.io -n submariner-operator 2>/dev/null | grep -q connected && break || sleep 10; done",
      "oc get gateways.submariner.io -n submariner-operator 2>/dev/null || true",
    ]
    connection {
      type        = "ssh"
      host        = var.bastion_host
      user        = var.bastion_user
      private_key = file(var.bastion_ssh_key)
    }
  }

  depends_on = [null_resource.submariner_operator, null_resource.submariner_broker]
}

output "submariner_namespace" {
  value = "submariner-operator"
}

output "cluster_role" {
  value = var.cluster_role
}
