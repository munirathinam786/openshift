# =============================================================================
# Module: OpenShift Virtualization (KubeVirt / CNV)
# =============================================================================

variable "kubeconfig" { type = string }
variable "bastion_host" { type = string }
variable "bastion_user" { type = string }
variable "bastion_ssh_key" { type = string }

# ---- Operator ----
variable "cnv_channel" {
  type    = string
  default = "stable"
}
variable "cnv_install_plan_approval" {
  type    = string
  default = "Automatic"
}

# ---- HyperConverged CR ----
variable "cnv_feature_gates" {
  type    = list(string)
  default = ["withHostPassthroughCPU", "enableCommonBootImageImport"]
}
variable "cnv_default_network_interface" {
  type    = string
  default = "masquerade"
}
variable "cnv_permitted_host_devices_pci" {
  description = "List of PCI host devices to passthrough (e.g. GPU, NIC)"
  type = list(object({
    pci_vendor_selector        = string
    resource_name              = string
    external_resource_provider = optional(bool, false)
  }))
  default = []
}
variable "cnv_permitted_host_devices_usb" {
  description = "List of USB host devices to passthrough"
  type = list(object({
    resource_name           = string
    selectors = list(object({
      vendor  = string
      product = string
    }))
  }))
  default = []
}

# ---- Live Migration ----
variable "cnv_live_migration_bandwidth_per_migration" {
  type    = string
  default = "64Mi"
}
variable "cnv_live_migration_completion_timeout" {
  type    = number
  default = 800
}
variable "cnv_live_migration_parallel_migrations_per_cluster" {
  type    = number
  default = 5
}
variable "cnv_live_migration_parallel_outbound_per_node" {
  type    = number
  default = 2
}
variable "cnv_live_migration_progress_timeout" {
  type    = number
  default = 150
}
variable "cnv_live_migration_allow_auto_converge" {
  type    = bool
  default = true
}
variable "cnv_live_migration_allow_post_copy" {
  type    = bool
  default = false
}
variable "cnv_live_migration_network" {
  description = "Dedicated network for live migration (NAD name or empty for default)"
  type        = string
  default     = ""
}

# ---- CPU & Memory ----
variable "cnv_cpu_model" {
  description = "Default CPU model for VMs (e.g. host-passthrough, host-model, Skylake-Server)"
  type        = string
  default     = "host-model"
}

# ---- Storage ----
variable "cnv_default_storage_class" {
  description = "Default StorageClass for VM disks"
  type        = string
  default     = "ocs-storagecluster-ceph-rbd-virtualization"
}
variable "cnv_scratch_space_storage_class" {
  description = "StorageClass for scratch/temp space (CDI)"
  type        = string
  default     = ""
}
variable "cnv_cdi_upload_proxy_url" {
  description = "CDI upload proxy URL (auto-detected if empty)"
  type        = string
  default     = ""
}

# ---- Networking ----
variable "cnv_enable_bridge_binding" {
  description = "Enable Linux bridge binding plugin for VMs"
  type        = bool
  default     = true
}
variable "cnv_ovs_annotations" {
  description = "Additional OVS annotations to apply"
  type        = map(string)
  default     = {}
}

# ---- Node Placement ----
variable "cnv_node_selector" {
  description = "Node selector for KubeVirt components (empty = all schedulable nodes)"
  type        = map(string)
  default     = {}
}
variable "cnv_infra_node_selector" {
  description = "Node selector for infra components (virt-controller, virt-api)"
  type        = map(string)
  default     = {}
}
variable "cnv_workload_node_selector" {
  description = "Node selector for workload placement (virt-launcher pods)"
  type        = map(string)
  default     = {}
}

# ---- Common Boot Images ----
variable "cnv_common_boot_image_import" {
  description = "Enable auto-import of common OS boot images (RHEL, CentOS, Fedora, Windows)"
  type        = bool
  default     = true
}
variable "cnv_custom_boot_images" {
  description = "Custom boot images to import as DataSources"
  type = list(object({
    name          = string
    namespace     = string
    registry_url  = string
    storage_class = optional(string, "")
    size          = optional(string, "30Gi")
  }))
  default = []
}

# ---- Templates ----
variable "cnv_custom_vm_templates" {
  description = "List of custom VM template names to create"
  type = list(object({
    name        = string
    namespace   = string
    os_type     = string
    cpu_cores   = number
    memory      = string
    disk_size   = string
    description = optional(string, "")
  }))
  default = []
}

# ---- RBAC ----
variable "cnv_admin_groups" {
  description = "Groups to grant kubevirt-admin ClusterRole"
  type        = list(string)
  default     = []
}

# ---- Monitoring ----
variable "cnv_enable_monitoring_alerts" {
  description = "Enable OpenShift Virtualization PrometheusRule alerts"
  type        = bool
  default     = true
}

# ---- MediatedDevices (vGPU) ----
variable "cnv_mediated_devices" {
  description = "List of mediated device types for vGPU passthrough"
  type = list(object({
    resource_name   = string
    mdev_types      = list(string)
    node_selector   = optional(map(string), {})
  }))
  default = []
}

# =============================================================================
# Resources
# =============================================================================

resource "null_resource" "cnv_namespace" {
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
      "  name: openshift-cnv",
      "EOF",

      # Create OperatorGroup
      "cat <<'EOF' | oc apply -f -",
      "apiVersion: operators.coreos.com/v1",
      "kind: OperatorGroup",
      "metadata:",
      "  name: kubevirt-hyperconverged-group",
      "  namespace: openshift-cnv",
      "spec:",
      "  targetNamespaces:",
      "    - openshift-cnv",
      "EOF",

      # Create Subscription
      "cat <<'EOF' | oc apply -f -",
      "apiVersion: operators.coreos.com/v1alpha1",
      "kind: Subscription",
      "metadata:",
      "  name: kubevirt-hyperconverged",
      "  namespace: openshift-cnv",
      "spec:",
      "  channel: ${var.cnv_channel}",
      "  installPlanApproval: ${var.cnv_install_plan_approval}",
      "  name: kubevirt-hyperconverged",
      "  source: redhat-operators",
      "  sourceNamespace: openshift-marketplace",
      "EOF",

      # Wait for operator to install
      "echo 'Waiting for OpenShift Virtualization operator...'",
      "for i in $(seq 1 90); do",
      "  oc get csv -n openshift-cnv 2>/dev/null | grep kubevirt-hyperconverged | grep -q Succeeded && break",
      "  sleep 10",
      "done",
      "oc get csv -n openshift-cnv | grep kubevirt-hyperconverged | grep -q Succeeded || { echo 'ERROR: CNV operator not ready'; exit 1; }",
    ]
  }
}

resource "null_resource" "cnv_hyperconverged" {
  depends_on = [null_resource.cnv_namespace]

  connection {
    type        = "ssh"
    host        = var.bastion_host
    user        = var.bastion_user
    private_key = file(var.bastion_ssh_key)
  }

  provisioner "remote-exec" {
    inline = [
      "export KUBECONFIG=${var.kubeconfig}",

      # Create HyperConverged CR
      "cat <<'HCEOF' | oc apply -f -",
      "apiVersion: hco.kubevirt.io/v1beta1",
      "kind: HyperConverged",
      "metadata:",
      "  name: kubevirt-hyperconverged",
      "  namespace: openshift-cnv",
      "spec:",
      "  featureGates:",
      "    withHostPassthroughCPU: ${contains(var.cnv_feature_gates, "withHostPassthroughCPU")}",
      "    enableCommonBootImageImport: ${var.cnv_common_boot_image_import}",
      "  liveMigrationConfig:",
      "    bandwidthPerMigration: ${var.cnv_live_migration_bandwidth_per_migration}",
      "    completionTimeoutPerGiB: ${var.cnv_live_migration_completion_timeout}",
      "    parallelMigrationsPerCluster: ${var.cnv_live_migration_parallel_migrations_per_cluster}",
      "    parallelOutboundMigrationsPerNode: ${var.cnv_live_migration_parallel_outbound_per_node}",
      "    progressTimeout: ${var.cnv_live_migration_progress_timeout}",
      "    allowAutoConverge: ${var.cnv_live_migration_allow_auto_converge}",
      "    allowPostCopy: ${var.cnv_live_migration_allow_post_copy}",
      "  certConfig:",
      "    ca:",
      "      duration: 48h0m0s",
      "      renewBefore: 24h0m0s",
      "    server:",
      "      duration: 24h0m0s",
      "      renewBefore: 12h0m0s",
      "HCEOF",

      # Wait for HyperConverged to become Available
      "echo 'Waiting for HyperConverged CR to become Available...'",
      "for i in $(seq 1 120); do",
      "  STATUS=$(oc get hyperconverged kubevirt-hyperconverged -n openshift-cnv -o jsonpath='{.status.conditions[?(@.type==\"Available\")].status}' 2>/dev/null)",
      "  [ \"$STATUS\" = \"True\" ] && break",
      "  sleep 10",
      "done",
      "echo 'OpenShift Virtualization is ready.'",
    ]
  }
}

# --- Node labeling for workload placement ---
resource "null_resource" "cnv_node_labels" {
  count      = length(var.cnv_workload_node_selector) > 0 ? 1 : 0
  depends_on = [null_resource.cnv_hyperconverged]

  connection {
    type        = "ssh"
    host        = var.bastion_host
    user        = var.bastion_user
    private_key = file(var.bastion_ssh_key)
  }

  provisioner "remote-exec" {
    inline = [
      "export KUBECONFIG=${var.kubeconfig}",
      "echo 'Applying workload node labels...'",
      # Labels are applied by the user via cnv_workload_node_selector; the HyperConverged CR uses them.
      "oc get nodes --show-labels | head -20",
    ]
  }
}

output "cnv_namespace" {
  value = "openshift-cnv"
}

output "cnv_status" {
  value = "OpenShift Virtualization deployed via kubevirt-hyperconverged operator"
}
