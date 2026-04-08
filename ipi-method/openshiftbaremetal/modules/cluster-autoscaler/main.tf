# =============================================================================
# Module: Cluster Autoscaler + Machine Autoscaler
# =============================================================================

variable "kubeconfig" { type = string }
variable "bastion_host" { type = string }
variable "bastion_user" { type = string }
variable "bastion_ssh_key" { type = string }
variable "max_nodes" { type = number }
variable "max_gpus" { type = number }

resource "null_resource" "cluster_autoscaler" {
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
      "apiVersion: autoscaling.openshift.io/v1",
      "kind: ClusterAutoscaler",
      "metadata:",
      "  name: default",
      "spec:",
      "  podPriorityThreshold: -10",
      "  resourceLimits:",
      "    maxNodesTotal: ${var.max_nodes}",
      "    cores:",
      "      min: 8",
      "      max: 128",
      "    memory:",
      "      min: 4",
      "      max: 256",
      "    gpus:",
      "      - type: nvidia.com/gpu",
      "        min: 0",
      "        max: ${var.max_gpus}",
      "  scaleDown:",
      "    enabled: true",
      "    delayAfterAdd: 10m",
      "    delayAfterDelete: 5m",
      "    delayAfterFailure: 30s",
      "    unneededTime: 5m",
      "    utilizationThreshold: '0.4'",
      "EOF",

      "echo 'ClusterAutoscaler created'",
    ]
  }
}
