# =============================================================================
# Module: Machine Config Pools — Custom worker pools with labels
# =============================================================================

variable "kubeconfig" { type = string }
variable "bastion_host" { type = string }
variable "bastion_user" { type = string }
variable "bastion_ssh_key" { type = string }
variable "machine_config_pools" {
  description = "Custom MachineConfigPools to create"
  type = list(object({
    name            = string
    node_selector   = map(string)
    max_unavailable = string
    paused          = bool
  }))
  default = [
    {
      name            = "worker-gpu"
      node_selector   = { "node-role.kubernetes.io/worker-gpu" = "" }
      max_unavailable = "1"
      paused          = false
    },
    {
      name            = "worker-infra"
      node_selector   = { "node-role.kubernetes.io/infra" = "" }
      max_unavailable = "1"
      paused          = false
    }
  ]
}

resource "null_resource" "machine_config_pool" {
  count = length(var.machine_config_pools)

  connection {
    type        = "ssh"
    host        = var.bastion_host
    user        = var.bastion_user
    private_key = file(var.bastion_ssh_key)
  }

  provisioner "remote-exec" {
    inline = [
      "export KUBECONFIG=${var.kubeconfig}",

      "cat <<EOF | oc apply -f -",
      "apiVersion: machineconfiguration.openshift.io/v1",
      "kind: MachineConfigPool",
      "metadata:",
      "  name: ${var.machine_config_pools[count.index].name}",
      "spec:",
      "  paused: ${var.machine_config_pools[count.index].paused}",
      "  maxUnavailable: ${var.machine_config_pools[count.index].max_unavailable}",
      "  machineConfigSelector:",
      "    matchExpressions:",
      "      - key: machineconfiguration.openshift.io/role",
      "        operator: In",
      "        values:",
      "          - worker",
      "          - ${var.machine_config_pools[count.index].name}",
      "  nodeSelector:",
      "    matchLabels:",
      join("\n", [for k, v in var.machine_config_pools[count.index].node_selector : "      ${k}: '${v}'"]),
      "EOF",

      "echo 'MachineConfigPool ${var.machine_config_pools[count.index].name} created'",
    ]
  }
}
