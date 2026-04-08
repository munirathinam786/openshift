# Author: Sathishkumar Munirathinam

# =============================================================================
# Module: MIG Manager — NVIDIA Multi-Instance GPU partitioning
# =============================================================================

variable "kubeconfig" { type = string }
variable "bastion_host" { type = string }
variable "bastion_user" { type = string }
variable "bastion_ssh_key" { type = string }
variable "mig_strategy" {
  description = "MIG strategy (single or mixed)"
  type        = string
  default     = "mixed"
}
variable "mig_profiles" {
  description = "MIG profile configurations per node label"
  type = list(object({
    node_label  = string
    gpu_index   = number
    mig_profile = string
  }))
  default = [
    {
      node_label  = "nvidia.com/gpu.product=NVIDIA-A100-SXM4-80GB"
      gpu_index   = 0
      mig_profile = "3g.40gb"
    }
  ]
}

resource "null_resource" "mig_manager_config" {
  connection {
    type        = "ssh"
    host        = var.bastion_host
    user        = var.bastion_user
    private_key = file(var.bastion_ssh_key)
  }

  provisioner "remote-exec" {
    inline = [
      "export KUBECONFIG=${var.kubeconfig}",

      # Update GPU Operator ClusterPolicy for MIG
      "oc patch clusterpolicy gpu-cluster-policy --type merge -p '{",
      "  \"spec\": {",
      "    \"mig\": {",
      "      \"strategy\": \"${var.mig_strategy}\"",
      "    },",
      "    \"migManager\": {",
      "      \"enabled\": true",
      "    }",
      "  }",
      "}'",

      # Create MIG config ConfigMap
      "cat <<'EOF' | oc apply -f -",
      "apiVersion: v1",
      "kind: ConfigMap",
      "metadata:",
      "  name: mig-parted-config",
      "  namespace: nvidia-gpu-operator",
      "data:",
      "  config.yaml: |",
      "    version: v1",
      "    mig-configs:",
      "      all-balanced:",
      "        - devices: [0]",
      "          mig-enabled: true",
      "          mig-devices:",
      "            3g.40gb: 2",
      "      all-1g:",
      "        - devices: [0]",
      "          mig-enabled: true",
      "          mig-devices:",
      "            1g.10gb: 7",
      "      all-2g:",
      "        - devices: [0]",
      "          mig-enabled: true",
      "          mig-devices:",
      "            2g.20gb: 3",
      "      all-3g:",
      "        - devices: [0]",
      "          mig-enabled: true",
      "          mig-devices:",
      "            3g.40gb: 2",
      "      all-7g:",
      "        - devices: [0]",
      "          mig-enabled: true",
      "          mig-devices:",
      "            7g.80gb: 1",
      "EOF",

      # Label GPU nodes to apply default MIG config
      "for node in $(oc get nodes -l nvidia.com/gpu.present=true -o name); do",
      "  oc label $node nvidia.com/mig.config=all-balanced --overwrite 2>/dev/null || true",
      "done",

      "echo 'MIG Manager configured with strategy: ${var.mig_strategy}'",
    ]
  }
}
