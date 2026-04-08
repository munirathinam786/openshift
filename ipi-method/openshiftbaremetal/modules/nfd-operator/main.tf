# =============================================================================
# Module: Node Feature Discovery (NFD) Operator
# =============================================================================

variable "kubeconfig" { type = string }
variable "bastion_host" { type = string }
variable "bastion_user" { type = string }
variable "bastion_ssh_key" { type = string }

resource "null_resource" "nfd_operator" {
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
      "  name: openshift-nfd",
      "EOF",

      # Create OperatorGroup
      "cat <<'EOF' | oc apply -f -",
      "apiVersion: operators.coreos.com/v1",
      "kind: OperatorGroup",
      "metadata:",
      "  name: openshift-nfd",
      "  namespace: openshift-nfd",
      "spec:",
      "  targetNamespaces:",
      "    - openshift-nfd",
      "EOF",

      # Create Subscription
      "cat <<'EOF' | oc apply -f -",
      "apiVersion: operators.coreos.com/v1alpha1",
      "kind: Subscription",
      "metadata:",
      "  name: nfd",
      "  namespace: openshift-nfd",
      "spec:",
      "  channel: stable",
      "  installPlanApproval: Automatic",
      "  name: nfd",
      "  source: redhat-operators",
      "  sourceNamespace: openshift-marketplace",
      "EOF",

      # Wait for operator to be ready
      "echo 'Waiting for NFD operator to be ready...'",
      "for i in $(seq 1 60); do",
      "  oc get csv -n openshift-nfd 2>/dev/null | grep -q Succeeded && break",
      "  sleep 10",
      "done",

      # Create NodeFeatureDiscovery CR
      "cat <<'EOF' | oc apply -f -",
      "apiVersion: nfd.openshift.io/v1",
      "kind: NodeFeatureDiscovery",
      "metadata:",
      "  name: nfd-instance",
      "  namespace: openshift-nfd",
      "spec:",
      "  operand:",
      "    image: registry.redhat.io/openshift4/ose-node-feature-discovery:latest",
      "    servicePort: 12000",
      "  workerConfig:",
      "    configData: |",
      "      sources:",
      "        pci:",
      "          deviceClassWhitelist:",
      "            - \"0300\"",
      "            - \"0302\"",
      "          deviceLabelFields:",
      "            - vendor",
      "EOF",

      # Verify NFD labels on GPU nodes
      "sleep 30",
      "echo '--- NFD GPU detection ---'",
      "oc describe node | egrep 'Roles|pci' | grep -v master || echo 'No GPU PCI labels detected yet (may take a few minutes)'",
    ]
  }
}
