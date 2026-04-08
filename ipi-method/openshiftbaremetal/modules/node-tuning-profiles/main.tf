# =============================================================================
# Module: Node Tuning Profiles — Performance tuning via Tuned/MachineConfig
# =============================================================================

variable "kubeconfig" { type = string }
variable "bastion_host" { type = string }
variable "bastion_user" { type = string }
variable "bastion_ssh_key" { type = string }
variable "enable_hugepages" {
  description = "Enable 1Gi hugepages on worker nodes"
  type        = bool
  default     = false
}
variable "hugepages_count" {
  description = "Number of 1Gi hugepages to allocate"
  type        = number
  default     = 16
}
variable "enable_realtime_kernel" {
  description = "Enable RT kernel on specific nodes"
  type        = bool
  default     = false
}
variable "realtime_node_selector" {
  description = "Label selector for RT kernel nodes"
  type        = map(string)
  default     = { "node-role.kubernetes.io/worker-rt" = "" }
}
variable "sysctl_tuning" {
  description = "Custom sysctl parameters"
  type        = map(string)
  default = {
    "vm.max_map_count"              = "262144"
    "net.core.somaxconn"            = "32768"
    "net.ipv4.tcp_max_syn_backlog"  = "16384"
  }
}

resource "null_resource" "performance_tuned_profile" {
  connection {
    type        = "ssh"
    host        = var.bastion_host
    user        = var.bastion_user
    private_key = file(var.bastion_ssh_key)
  }

  provisioner "remote-exec" {
    inline = [
      "export KUBECONFIG=${var.kubeconfig}",

      # Create Tuned profile for GPU/HPC workloads
      "cat <<'EOF' | oc apply -f -",
      "apiVersion: tuned.openshift.io/v1",
      "kind: Tuned",
      "metadata:",
      "  name: openshift-gpu-hpc",
      "  namespace: openshift-cluster-node-tuning-operator",
      "spec:",
      "  profile:",
      "    - name: openshift-gpu-hpc",
      "      data: |",
      "        [main]",
      "        summary=Optimized profile for GPU/HPC workloads",
      "        include=openshift-node",
      "        [sysctl]",
      join("\n", [for k, v in var.sysctl_tuning : "        ${k}=${v}"]),
      var.enable_hugepages ? "        [vm]" : "",
      var.enable_hugepages ? "        transparent_hugepages=never" : "",
      var.enable_hugepages ? "        [sysctl]" : "",
      var.enable_hugepages ? "        vm.nr_hugepages=${var.hugepages_count}" : "",
      "  recommend:",
      "    - profile: openshift-gpu-hpc",
      "      priority: 20",
      "      match:",
      "        - label: node-role.kubernetes.io/worker",
      "EOF",

      "echo 'Performance Tuned profile applied'",
    ]
  }
}

# --- RT Kernel MachineConfigPool ---
resource "null_resource" "realtime_kernel" {
  count = var.enable_realtime_kernel ? 1 : 0

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
      "apiVersion: machineconfiguration.openshift.io/v1",
      "kind: MachineConfigPool",
      "metadata:",
      "  name: worker-rt",
      "spec:",
      "  machineConfigSelector:",
      "    matchExpressions:",
      "      - key: machineconfiguration.openshift.io/role",
      "        operator: In",
      "        values: [worker, worker-rt]",
      "  nodeSelector:",
      "    matchLabels:",
      "      node-role.kubernetes.io/worker-rt: ''",
      "EOF",

      # Enable RT kernel via PerformanceProfile (requires Performance Addon Operator)
      "cat <<'EOF' | oc apply -f -",
      "apiVersion: performance.openshift.io/v2",
      "kind: PerformanceProfile",
      "metadata:",
      "  name: rt-performance",
      "spec:",
      "  realTimeKernel:",
      "    enabled: true",
      "  nodeSelector:",
      "    node-role.kubernetes.io/worker-rt: ''",
      "  cpu:",
      "    isolated: 2-63",
      "    reserved: 0-1",
      "  numa:",
      "    topologyPolicy: single-numa-node",
      "EOF",

      "echo 'RT kernel PerformanceProfile applied for worker-rt nodes'",
    ]
  }
}
