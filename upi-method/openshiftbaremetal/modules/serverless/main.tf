# Author: Sathishkumar Munirathinam

# =============================================================================
# Module: OpenShift Serverless (Knative)
# =============================================================================

variable "kubeconfig" { type = string }
variable "bastion_host" { type = string }
variable "bastion_user" { type = string }
variable "bastion_ssh_key" { type = string }

resource "null_resource" "serverless" {
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
      "  name: openshift-serverless",
      "EOF",

      # Create OperatorGroup
      "cat <<'EOF' | oc apply -f -",
      "apiVersion: operators.coreos.com/v1",
      "kind: OperatorGroup",
      "metadata:",
      "  name: serverless-operators",
      "  namespace: openshift-serverless",
      "spec: {}",
      "EOF",

      # Create Subscription
      "cat <<'EOF' | oc apply -f -",
      "apiVersion: operators.coreos.com/v1alpha1",
      "kind: Subscription",
      "metadata:",
      "  name: serverless-operator",
      "  namespace: openshift-serverless",
      "spec:",
      "  channel: stable",
      "  installPlanApproval: Automatic",
      "  name: serverless-operator",
      "  source: redhat-operators",
      "  sourceNamespace: openshift-marketplace",
      "EOF",

      # Wait for operator
      "echo 'Waiting for Serverless operator...'",
      "for i in $(seq 1 60); do",
      "  oc get csv -n openshift-serverless 2>/dev/null | grep serverless | grep -q Succeeded && break",
      "  sleep 10",
      "done",

      # Create KnativeServing
      "cat <<'EOF' | oc apply -f -",
      "apiVersion: v1",
      "kind: Namespace",
      "metadata:",
      "  name: knative-serving",
      "EOF",

      "cat <<'EOF' | oc apply -f -",
      "apiVersion: operator.knative.dev/v1beta1",
      "kind: KnativeServing",
      "metadata:",
      "  name: knative-serving",
      "  namespace: knative-serving",
      "spec: {}",
      "EOF",

      # Wait for KnativeServing
      "echo 'Waiting for KnativeServing...'",
      "for i in $(seq 1 60); do",
      "  READY=$(oc get knativeserving knative-serving -n knative-serving -o jsonpath='{.status.conditions[?(@.type==\"Ready\")].status}' 2>/dev/null)",
      "  [ \"$READY\" = \"True\" ] && echo 'KnativeServing is ready' && break",
      "  sleep 10",
      "done",
    ]
  }
}
