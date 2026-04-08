# =============================================================================
# Module: Web Terminal — Browser-based terminal access
# =============================================================================

variable "kubeconfig" { type = string }
variable "bastion_host" { type = string }
variable "bastion_user" { type = string }
variable "bastion_ssh_key" { type = string }
variable "web_terminal_channel" {
  description = "OLM channel for Web Terminal Operator"
  type        = string
  default     = "fast"
}
variable "web_terminal_timeout" {
  description = "Idle timeout for web terminal sessions in minutes"
  type        = number
  default     = 15
}

resource "null_resource" "web_terminal_operator" {
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
      "apiVersion: operators.coreos.com/v1alpha1",
      "kind: Subscription",
      "metadata:",
      "  name: web-terminal",
      "  namespace: openshift-operators",
      "spec:",
      "  channel: ${var.web_terminal_channel}",
      "  installPlanApproval: Automatic",
      "  name: web-terminal",
      "  source: redhat-operators",
      "  sourceNamespace: openshift-marketplace",
      "EOF",

      "echo 'Waiting for Web Terminal Operator...'",
      "for i in $(seq 1 60); do",
      "  oc get csv -n openshift-operators 2>/dev/null | grep web-terminal | grep -q Succeeded && break",
      "  sleep 10",
      "done",

      # Configure idle timeout
      "cat <<'EOF' | oc apply -f -",
      "apiVersion: workspace.devfile.io/v1alpha1",
      "kind: DevWorkspaceOperatorConfig",
      "metadata:",
      "  name: devworkspace-operator-config",
      "  namespace: openshift-operators",
      "spec:",
      "  workspace:",
      "    idleTimeout: ${var.web_terminal_timeout}m",
      "EOF",

      "echo 'Web Terminal Operator installed (idle timeout: ${var.web_terminal_timeout}m)'",
    ]
  }
}
