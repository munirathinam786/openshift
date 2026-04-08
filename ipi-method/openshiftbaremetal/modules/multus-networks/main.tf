# Author: Sathishkumar Munirathinam

# =============================================================================
# Module: Multus Networks — Secondary CNI for GPU/DPDK workloads
# =============================================================================

variable "kubeconfig" { type = string }
variable "bastion_host" { type = string }
variable "bastion_user" { type = string }
variable "bastion_ssh_key" { type = string }
variable "multus_networks" {
  description = "List of additional network attachment definitions"
  type = list(object({
    name             = string
    namespace        = string
    type             = string
    master           = optional(string, "")
    mode             = optional(string, "bridge")
    vlan             = optional(number, 0)
    ipam_type        = optional(string, "whereabouts")
    ipam_range       = optional(string, "")
    ipam_gateway     = optional(string, "")
  }))
  default = []
}

resource "null_resource" "multus_networks" {
  count = length(var.multus_networks)

  connection {
    type        = "ssh"
    host        = var.bastion_host
    user        = var.bastion_user
    private_key = file(var.bastion_ssh_key)
  }

  provisioner "remote-exec" {
    inline = [
      "export KUBECONFIG=${var.kubeconfig}",

      "oc create namespace ${var.multus_networks[count.index].namespace} --dry-run=client -o yaml | oc apply -f -",

      "cat <<'EOF' | oc apply -f -",
      "apiVersion: k8s.cni.cncf.io/v1",
      "kind: NetworkAttachmentDefinition",
      "metadata:",
      "  name: ${var.multus_networks[count.index].name}",
      "  namespace: ${var.multus_networks[count.index].namespace}",
      "spec:",
      "  config: '{",
      "    \"cniVersion\": \"0.3.1\",",
      "    \"type\": \"${var.multus_networks[count.index].type}\",",
      var.multus_networks[count.index].master != "" ? "    \"master\": \"${var.multus_networks[count.index].master}\"," : "",
      var.multus_networks[count.index].vlan > 0 ? "    \"vlan\": ${var.multus_networks[count.index].vlan}," : "",
      "    \"mode\": \"${var.multus_networks[count.index].mode}\",",
      "    \"ipam\": {",
      "      \"type\": \"${var.multus_networks[count.index].ipam_type}\"",
      var.multus_networks[count.index].ipam_range != "" ? "      ,\"range\": \"${var.multus_networks[count.index].ipam_range}\"" : "",
      var.multus_networks[count.index].ipam_gateway != "" ? "      ,\"gateway\": \"${var.multus_networks[count.index].ipam_gateway}\"" : "",
      "    }",
      "  }'",
      "EOF",

      "echo 'NetworkAttachmentDefinition ${var.multus_networks[count.index].name} created'",
    ]
  }
}
