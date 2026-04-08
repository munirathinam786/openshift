# Author: Sathishkumar Munirathinam

# =============================================================================
# Module: Gatekeeper — OPA Policy Enforcement
# =============================================================================

variable "kubeconfig" { type = string }
variable "bastion_host" { type = string }
variable "bastion_user" { type = string }
variable "bastion_ssh_key" { type = string }
variable "gatekeeper_replicas" {
  description = "Number of Gatekeeper audit/webhook replicas"
  type        = number
  default     = 3
}
variable "gatekeeper_violation_action" {
  description = "Default enforcement action (deny, dryrun, warn)"
  type        = string
  default     = "warn"
}
variable "enable_default_constraints" {
  description = "Deploy default constraint templates (container limits, image allowlist, etc.)"
  type        = bool
  default     = true
}
variable "allowed_registries" {
  description = "List of allowed container image registries"
  type        = list(string)
  default     = ["registry.redhat.io", "quay.io", "registry.access.redhat.com"]
}

resource "null_resource" "gatekeeper_operator" {
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
      "  name: openshift-gatekeeper-system",
      "EOF",

      "cat <<'EOF' | oc apply -f -",
      "apiVersion: operators.coreos.com/v1",
      "kind: OperatorGroup",
      "metadata:",
      "  name: gatekeeper-operator",
      "  namespace: openshift-gatekeeper-system",
      "spec:",
      "  targetNamespaces:",
      "    - openshift-gatekeeper-system",
      "EOF",

      "cat <<'EOF' | oc apply -f -",
      "apiVersion: operators.coreos.com/v1alpha1",
      "kind: Subscription",
      "metadata:",
      "  name: gatekeeper-operator-product",
      "  namespace: openshift-gatekeeper-system",
      "spec:",
      "  channel: stable",
      "  installPlanApproval: Automatic",
      "  name: gatekeeper-operator-product",
      "  source: redhat-operators",
      "  sourceNamespace: openshift-marketplace",
      "EOF",

      "echo 'Waiting for Gatekeeper Operator...'",
      "for i in $(seq 1 60); do",
      "  oc get csv -n openshift-gatekeeper-system 2>/dev/null | grep gatekeeper | grep -q Succeeded && break",
      "  sleep 10",
      "done",

      # Create Gatekeeper instance
      "cat <<'EOF' | oc apply -f -",
      "apiVersion: operator.gatekeeper.sh/v1alpha1",
      "kind: Gatekeeper",
      "metadata:",
      "  name: gatekeeper",
      "spec:",
      "  audit:",
      "    replicas: ${var.gatekeeper_replicas}",
      "    auditInterval: 60",
      "  validatingWebhook: Enabled",
      "  mutatingWebhook: Disabled",
      "  webhook:",
      "    replicas: ${var.gatekeeper_replicas}",
      "    failurePolicy: Ignore",
      "EOF",

      "sleep 30",
      "echo 'Gatekeeper Operator installed'",
    ]
  }
}

# --- Default Constraint Templates ---
resource "null_resource" "default_constraints" {
  count = var.enable_default_constraints ? 1 : 0

  connection {
    type        = "ssh"
    host        = var.bastion_host
    user        = var.bastion_user
    private_key = file(var.bastion_ssh_key)
  }

  provisioner "remote-exec" {
    inline = [
      "export KUBECONFIG=${var.kubeconfig}",

      # Container resource limits required
      "cat <<'EOF' | oc apply -f -",
      "apiVersion: templates.gatekeeper.sh/v1",
      "kind: ConstraintTemplate",
      "metadata:",
      "  name: k8srequiredresources",
      "spec:",
      "  crd:",
      "    spec:",
      "      names:",
      "        kind: K8sRequiredResources",
      "  targets:",
      "    - target: admission.k8s.gatekeeper.sh",
      "      rego: |",
      "        package k8srequiredresources",
      "        violation[{\"msg\": msg}] {",
      "          container := input.review.object.spec.containers[_]",
      "          not container.resources.limits",
      "          msg := sprintf(\"Container %v has no resource limits\", [container.name])",
      "        }",
      "EOF",

      # Allowed registries
      "cat <<'EOF' | oc apply -f -",
      "apiVersion: templates.gatekeeper.sh/v1",
      "kind: ConstraintTemplate",
      "metadata:",
      "  name: k8sallowedregistries",
      "spec:",
      "  crd:",
      "    spec:",
      "      names:",
      "        kind: K8sAllowedRegistries",
      "      validation:",
      "        openAPIV3Schema:",
      "          type: object",
      "          properties:",
      "            registries:",
      "              type: array",
      "              items:",
      "                type: string",
      "  targets:",
      "    - target: admission.k8s.gatekeeper.sh",
      "      rego: |",
      "        package k8sallowedregistries",
      "        violation[{\"msg\": msg}] {",
      "          container := input.review.object.spec.containers[_]",
      "          not startswith(container.image, input.parameters.registries[_])",
      "          msg := sprintf(\"Container %v uses image %v from disallowed registry\", [container.name, container.image])",
      "        }",
      "EOF",

      # Apply constraints with configured action
      "sleep 10",

      "cat <<EOF | oc apply -f -",
      "apiVersion: constraints.gatekeeper.sh/v1beta1",
      "kind: K8sRequiredResources",
      "metadata:",
      "  name: require-resource-limits",
      "spec:",
      "  enforcementAction: ${var.gatekeeper_violation_action}",
      "  match:",
      "    kinds:",
      "      - apiGroups: ['']",
      "        kinds: ['Pod']",
      "    excludedNamespaces:",
      "      - openshift-*",
      "      - kube-*",
      "EOF",

      "cat <<EOF | oc apply -f -",
      "apiVersion: constraints.gatekeeper.sh/v1beta1",
      "kind: K8sAllowedRegistries",
      "metadata:",
      "  name: allowed-registries",
      "spec:",
      "  enforcementAction: ${var.gatekeeper_violation_action}",
      "  match:",
      "    kinds:",
      "      - apiGroups: ['']",
      "        kinds: ['Pod']",
      "    excludedNamespaces:",
      "      - openshift-*",
      "      - kube-*",
      "  parameters:",
      "    registries:",
      join("\n", [for r in var.allowed_registries : "      - ${r}"]),
      "EOF",

      "echo 'Default constraint templates and constraints deployed'",
    ]
  }

  depends_on = [null_resource.gatekeeper_operator]
}
