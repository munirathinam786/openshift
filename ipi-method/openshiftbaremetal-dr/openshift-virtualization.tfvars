# =============================================================================
# OpenShift Virtualization (KubeVirt / CNV) — DR Secondary
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
cnv_live_migration_network                        = ""

# =============================================================================
# CPU Model
# =============================================================================
cnv_cpu_model = "host-model"

# =============================================================================
# Default Network Interface Binding
# =============================================================================
cnv_default_network_interface = "masquerade"
cnv_enable_bridge_binding     = true
cnv_ovs_annotations           = {}

# =============================================================================
# Storage
# =============================================================================
cnv_default_storage_class       = "ocs-storagecluster-ceph-rbd-virtualization"
cnv_scratch_space_storage_class = ""
cnv_cdi_upload_proxy_url        = ""

# =============================================================================
# Node Placement
# =============================================================================
cnv_node_selector          = {}
cnv_infra_node_selector    = {}
cnv_workload_node_selector = {}

# =============================================================================
# Common Boot Images
# =============================================================================
cnv_common_boot_image_import = true
cnv_custom_boot_images       = []

# =============================================================================
# PCI Device Passthrough (GPU, NIC)
# =============================================================================
cnv_permitted_host_devices_pci = []
cnv_permitted_host_devices_usb = []

# =============================================================================
# Mediated Devices (vGPU)
# =============================================================================
cnv_mediated_devices = []

# =============================================================================
# Custom VM Templates
# =============================================================================
cnv_custom_vm_templates = []

# =============================================================================
# RBAC — Admin Groups
# =============================================================================
cnv_admin_groups = []

# =============================================================================
# Monitoring
# =============================================================================
cnv_enable_monitoring_alerts = true
