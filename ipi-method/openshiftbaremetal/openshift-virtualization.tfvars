# =============================================================================
# OpenShift Virtualization (KubeVirt / CNV) — DC Primary
# Apply separately: terraform apply -var-file=terraform.tfvars -var-file=openshift-virtualization.tfvars
# =============================================================================

# =============================================================================
# Feature Toggle
# =============================================================================
enable_openshift_virtualization = true

# =============================================================================
# Operator Configuration
# =============================================================================
cnv_channel               = "stable"
cnv_install_plan_approval = "Automatic"

# =============================================================================
# HyperConverged — Feature Gates
# =============================================================================
cnv_feature_gates = [
  "withHostPassthroughCPU",
  "enableCommonBootImageImport",
]

# =============================================================================
# Live Migration Settings
# =============================================================================
cnv_live_migration_bandwidth_per_migration       = "64Mi"
cnv_live_migration_completion_timeout             = 800
cnv_live_migration_parallel_migrations_per_cluster = 5
cnv_live_migration_parallel_outbound_per_node     = 2
cnv_live_migration_progress_timeout               = 150
cnv_live_migration_allow_auto_converge            = true
cnv_live_migration_allow_post_copy                = false

# Dedicated live migration network (set to a NAD name for dedicated migration traffic, or "" for default)
cnv_live_migration_network = ""

# =============================================================================
# CPU Model
# =============================================================================
# Options: host-passthrough (best perf), host-model (safe live migration), or specific model (e.g. Skylake-Server)
cnv_cpu_model = "host-model"

# =============================================================================
# Default Network Interface Binding
# =============================================================================
# Options: masquerade (default, NAT-based), bridge (L2), or sr-iov
cnv_default_network_interface = "masquerade"

# Enable Linux bridge binding plugin for VMs
cnv_enable_bridge_binding = true

# Additional OVS annotations (optional)
cnv_ovs_annotations = {}

# =============================================================================
# Storage
# =============================================================================
# Default StorageClass for VM disks (use ODF virtualization-optimized class)
cnv_default_storage_class       = "ocs-storagecluster-ceph-rbd-virtualization"

# StorageClass for CDI scratch/temp space (leave empty to use default)
cnv_scratch_space_storage_class = ""

# CDI upload proxy URL (auto-detected if empty)
cnv_cdi_upload_proxy_url = ""

# =============================================================================
# Node Placement
# =============================================================================
# Node selector for KubeVirt infrastructure components (empty = all schedulable nodes)
cnv_node_selector = {}

# Node selector for infra components (virt-controller, virt-api)
cnv_infra_node_selector = {}

# Node selector for workload placement (virt-launcher pods run VMs here)
# Example: { "node-role.kubernetes.io/virtualization" = "" }
cnv_workload_node_selector = {}

# =============================================================================
# Common Boot Images
# =============================================================================
# Auto-import golden images for RHEL, CentOS, Fedora, Windows
cnv_common_boot_image_import = true

# Custom boot images to import as DataSources
cnv_custom_boot_images = [
  # {
  #   name          = "rhel9-custom"
  #   namespace     = "openshift-virtualization-os-images"
  #   registry_url  = "docker://registry.example.com/rhel9:latest"
  #   storage_class = "ocs-storagecluster-ceph-rbd-virtualization"
  #   size          = "30Gi"
  # },
]

# =============================================================================
# PCI Device Passthrough (GPU, NIC)
# =============================================================================
# Passthrough physical PCI devices to VMs (e.g. NVIDIA GPUs for VM workloads)
cnv_permitted_host_devices_pci = [
  # {
  #   pci_vendor_selector        = "10DE:2204"       # NVIDIA A100
  #   resource_name              = "nvidia.com/A100"
  #   external_resource_provider = false
  # },
  # {
  #   pci_vendor_selector        = "10DE:2684"       # NVIDIA H100
  #   resource_name              = "nvidia.com/H100"
  #   external_resource_provider = false
  # },
]

# USB device passthrough
cnv_permitted_host_devices_usb = []

# =============================================================================
# Mediated Devices (vGPU)
# =============================================================================
# Configure vGPU profiles for GPU sharing across VMs
cnv_mediated_devices = [
  # {
  #   resource_name = "nvidia.com/GRID_A100-20C"
  #   mdev_types    = ["nvidia-710"]
  #   node_selector = { "nvidia.com/gpu.present" = "true" }
  # },
]

# =============================================================================
# Custom VM Templates
# =============================================================================
cnv_custom_vm_templates = [
  # {
  #   name        = "rhel9-large"
  #   namespace   = "openshift"
  #   os_type     = "rhel9"
  #   cpu_cores   = 8
  #   memory      = "32Gi"
  #   disk_size   = "100Gi"
  #   description = "RHEL 9 large template with 8 vCPU and 32Gi RAM"
  # },
  # {
  #   name        = "win2022-standard"
  #   namespace   = "openshift"
  #   os_type     = "win2k22"
  #   cpu_cores   = 4
  #   memory      = "16Gi"
  #   disk_size   = "80Gi"
  #   description = "Windows Server 2022 standard template"
  # },
]

# =============================================================================
# RBAC — Admin Groups
# =============================================================================
# Groups to grant kubevirt-admin ClusterRole
cnv_admin_groups = [
  # "cnv-admins",
  # "platform-team",
]

# =============================================================================
# Monitoring
# =============================================================================
# Enable PrometheusRule alerts for OpenShift Virtualization
cnv_enable_monitoring_alerts = true
