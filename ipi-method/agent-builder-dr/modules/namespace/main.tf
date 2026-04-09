# Author: Sathishkumar Munirathinam
# Module: Namespace — Creates the agent-builder namespace with labels

variable "bastion_host" { type = string }
variable "bastion_user" { type = string }
variable "bastion_ssh_key" { type = string }
variable "kubeconfig" { type = string }
variable "namespace" { type = string }

resource "null_resource" "namespace" {
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
      "  name: ${var.namespace}",
      "  labels:",
      "    app.kubernetes.io/part-of: agent-builder",
      "    app.kubernetes.io/managed-by: terraform",
      "  annotations:",
      "    openshift.io/description: \"Kyndryl Agent Builder Factory Platform\"",
      "EOF",

      "echo 'Namespace ${var.namespace} created successfully'",
    ]
  }
}

output "namespace" {
  value = var.namespace
}
