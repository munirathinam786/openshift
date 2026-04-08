# Author: Sathishkumar Munirathinam

# =============================================================================
# Module: DevSpaces — Red Hat OpenShift Dev Spaces (Eclipse Che)
# =============================================================================

variable "kubeconfig" { type = string }
variable "bastion_host" { type = string }
variable "bastion_user" { type = string }
variable "bastion_ssh_key" { type = string }
variable "devspaces_channel" {
  description = "OLM channel for Dev Spaces"
  type        = string
  default     = "stable"
}
variable "devspaces_storage_class" {
  description = "StorageClass for Dev Spaces PVCs"
  type        = string
  default     = "ocs-storagecluster-ceph-rbd"
}
variable "devspaces_storage_size" {
  description = "PVC size per workspace"
  type        = string
  default     = "10Gi"
}
variable "devspaces_max_workspaces_per_user" {
  description = "Max concurrent workspaces per user"
  type        = number
  default     = 3
}

resource "null_resource" "devspaces_operator" {
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
      "  name: openshift-devspaces",
      "EOF",

      "cat <<'EOF' | oc apply -f -",
      "apiVersion: operators.coreos.com/v1",
      "kind: OperatorGroup",
      "metadata:",
      "  name: devspaces",
      "  namespace: openshift-devspaces",
      "spec: {}",
      "EOF",

      "cat <<'EOF' | oc apply -f -",
      "apiVersion: operators.coreos.com/v1alpha1",
      "kind: Subscription",
      "metadata:",
      "  name: devspaces",
      "  namespace: openshift-devspaces",
      "spec:",
      "  channel: ${var.devspaces_channel}",
      "  installPlanApproval: Automatic",
      "  name: devspaces",
      "  source: redhat-operators",
      "  sourceNamespace: openshift-marketplace",
      "EOF",

      "echo 'Waiting for DevSpaces Operator...'",
      "for i in $(seq 1 60); do",
      "  oc get csv -n openshift-devspaces 2>/dev/null | grep devspaces | grep -q Succeeded && break",
      "  sleep 10",
      "done",

      # Create CheCluster
      "cat <<EOF | oc apply -f -",
      "apiVersion: org.eclipse.che/v2",
      "kind: CheCluster",
      "metadata:",
      "  name: devspaces",
      "  namespace: openshift-devspaces",
      "spec:",
      "  components:",
      "    cheServer:",
      "      debug: false",
      "    dashboard: {}",
      "    devfileRegistry: {}",
      "    pluginRegistry: {}",
      "  devEnvironments:",
      "    maxNumberOfWorkspacesPerUser: ${var.devspaces_max_workspaces_per_user}",
      "    storage:",
      "      pvcStrategy: per-user",
      "      perUserStrategyPvcConfig:",
      "        storageClass: ${var.devspaces_storage_class}",
      "        claimSize: ${var.devspaces_storage_size}",
      "    defaultNamespace:",
      "      autoProvision: true",
      "    secondsOfInactivityBeforeIdling: 1800",
      "    secondsOfRunBeforeIdling: -1",
      "  networking:",
      "    auth:",
      "      gateway:",
      "        configLabels:",
      "          app: che",
      "          component: che-gateway-config",
      "EOF",

      "echo 'OpenShift Dev Spaces deployed'",
    ]
  }
}
