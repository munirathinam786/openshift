# =============================================================================
# Module: OpenShift Service Mesh (Istio) + Kiali
# =============================================================================

variable "kubeconfig" { type = string }
variable "bastion_host" { type = string }
variable "bastion_user" { type = string }
variable "bastion_ssh_key" { type = string }

resource "null_resource" "servicemesh" {
  connection {
    type        = "ssh"
    host        = var.bastion_host
    user        = var.bastion_user
    private_key = file(var.bastion_ssh_key)
  }

  provisioner "remote-exec" {
    inline = [
      "export KUBECONFIG=${var.kubeconfig}",

      # --- Kiali Operator ---
      "cat <<'EOF' | oc apply -f -",
      "apiVersion: operators.coreos.com/v1alpha1",
      "kind: Subscription",
      "metadata:",
      "  name: kiali-ossm",
      "  namespace: openshift-operators",
      "spec:",
      "  channel: stable",
      "  installPlanApproval: Automatic",
      "  name: kiali-ossm",
      "  source: redhat-operators",
      "  sourceNamespace: openshift-marketplace",
      "EOF",

      # --- Service Mesh Operator ---
      "cat <<'EOF' | oc apply -f -",
      "apiVersion: operators.coreos.com/v1alpha1",
      "kind: Subscription",
      "metadata:",
      "  name: servicemeshoperator",
      "  namespace: openshift-operators",
      "spec:",
      "  channel: stable",
      "  installPlanApproval: Automatic",
      "  name: servicemeshoperator",
      "  source: redhat-operators",
      "  sourceNamespace: openshift-marketplace",
      "EOF",

      # Wait for operators
      "echo 'Waiting for Service Mesh operators...'",
      "for i in $(seq 1 60); do",
      "  KIALI=$(oc get csv -n openshift-operators 2>/dev/null | grep kiali | grep -c Succeeded)",
      "  MESH=$(oc get csv -n openshift-operators 2>/dev/null | grep servicemesh | grep -c Succeeded)",
      "  [ \"$KIALI\" -ge 1 ] && [ \"$MESH\" -ge 1 ] && echo 'Service Mesh operators ready' && break",
      "  sleep 10",
      "done",
    ]
  }
}
