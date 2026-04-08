# Author: Sathishkumar Munirathinam

# =============================================================================
# Module: File Integrity Operator — AIDE-based file monitoring
# =============================================================================

variable "kubeconfig" { type = string }
variable "bastion_host" { type = string }
variable "bastion_user" { type = string }
variable "bastion_ssh_key" { type = string }
variable "file_integrity_node_selector" {
  description = "Node selector for file integrity monitoring"
  type        = map(string)
  default     = {}
}
variable "file_integrity_grace_period" {
  description = "Grace period in seconds before first scan"
  type        = number
  default     = 900
}

resource "null_resource" "file_integrity_operator" {
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
      "  name: openshift-file-integrity",
      "  labels:",
      "    openshift.io/cluster-monitoring: 'true'",
      "EOF",

      "cat <<'EOF' | oc apply -f -",
      "apiVersion: operators.coreos.com/v1",
      "kind: OperatorGroup",
      "metadata:",
      "  name: file-integrity-operator",
      "  namespace: openshift-file-integrity",
      "spec:",
      "  targetNamespaces:",
      "    - openshift-file-integrity",
      "EOF",

      "cat <<'EOF' | oc apply -f -",
      "apiVersion: operators.coreos.com/v1alpha1",
      "kind: Subscription",
      "metadata:",
      "  name: file-integrity-operator",
      "  namespace: openshift-file-integrity",
      "spec:",
      "  channel: stable",
      "  installPlanApproval: Automatic",
      "  name: file-integrity-operator",
      "  source: redhat-operators",
      "  sourceNamespace: openshift-marketplace",
      "EOF",

      "echo 'Waiting for File Integrity Operator...'",
      "for i in $(seq 1 60); do",
      "  oc get csv -n openshift-file-integrity 2>/dev/null | grep file-integrity | grep -q Succeeded && break",
      "  sleep 10",
      "done",

      # Create FileIntegrity instances for worker and master nodes
      "cat <<'EOF' | oc apply -f -",
      "apiVersion: fileintegrity.openshift.io/v1alpha1",
      "kind: FileIntegrity",
      "metadata:",
      "  name: worker-fileintegrity",
      "  namespace: openshift-file-integrity",
      "spec:",
      "  nodeSelector:",
      "    node-role.kubernetes.io/worker: ''",
      "  config:",
      "    gracePeriod: ${var.file_integrity_grace_period}",
      "EOF",

      "cat <<'EOF' | oc apply -f -",
      "apiVersion: fileintegrity.openshift.io/v1alpha1",
      "kind: FileIntegrity",
      "metadata:",
      "  name: master-fileintegrity",
      "  namespace: openshift-file-integrity",
      "spec:",
      "  nodeSelector:",
      "    node-role.kubernetes.io/master: ''",
      "  config:",
      "    gracePeriod: ${var.file_integrity_grace_period}",
      "EOF",

      "echo 'File Integrity Operator installed with AIDE monitoring on all nodes'",
    ]
  }
}
