# =============================================================================
# VM Migration (MTV — Migration Toolkit for Virtualization) — DR Secondary
# Apply separately: terraform apply -var-file=terraform.tfvars -var-file=vm-migration.tfvars
# =============================================================================

# =============================================================================
# Feature Toggle
# =============================================================================
enable_vm_migration = true

# =============================================================================
# MTV Operator
# =============================================================================
mtv_channel               = "release-v2.7"
mtv_install_plan_approval = "Automatic"

# =============================================================================
# Source Provider — VMware vSphere
# =============================================================================
source_provider_type     = "vsphere"
source_provider_name     = "vmware-dr-datacenter"
source_provider_url      = "https://vcenter-dr.example.com/sdk"
source_provider_username = "administrator@vsphere.local"
source_provider_password = "REPLACE_VCENTER_PASSWORD"
source_provider_thumbprint          = "AA:BB:CC:DD:EE:FF:00:11:22:33:44:55:66:77:88:99:AA:BB:CC:DD"
source_provider_ca_cert             = ""
source_provider_insecure_skip_verify = false

# VDDK image (required for vSphere) — pre-built and pushed to internal registry
# source_provider_vddk_init_image = "registry.example.com/vddk:v8.0.2"

# =============================================================================
# Destination Provider — OpenShift Cluster
# =============================================================================
destination_provider_name = "host"

# =============================================================================
# Alternative Source Provider Examples
# =============================================================================
# --- Red Hat Virtualization (RHV / oVirt) ---
# source_provider_type     = "ovirt"
# source_provider_name     = "rhv-dr-datacenter"
# source_provider_url      = "https://rhvm-dr.example.com/ovirt-engine/api"
# source_provider_username = "admin@internal"
# source_provider_password = "REPLACE_RHV_PASSWORD"
# source_provider_ca_cert  = "/home/kni/certs/rhvm-ca.pem"
#
# --- OpenStack ---
# source_provider_type     = "openstack"
# source_provider_name     = "openstack-dr"
# source_provider_url      = "https://keystone-dr.example.com:5000/v3"
# source_provider_username = "admin"
# source_provider_password = "REPLACE_OPENSTACK_PASSWORD"
# source_provider_ca_cert  = "/home/kni/certs/openstack-ca.pem"

# =============================================================================
# Network Mapping
# =============================================================================
network_map_name = "vmware-network-map"
network_mappings = [
  {
    source_network      = "VM Network"
    destination_network = "pod"
    destination_type    = "pod"
  },
]

# =============================================================================
# Storage Mapping
# =============================================================================
storage_map_name = "vmware-storage-map"
storage_mappings = [
  {
    source_datastore         = "datastore1"
    destination_storage_class = "ocs-storagecluster-ceph-rbd-virtualization"
    volume_mode              = "Filesystem"
  },
]

# =============================================================================
# Migration Plan
# =============================================================================
migration_plan_name      = "vmware-to-ocp-dr"
migration_plan_namespace = "openshift-mtv"

# =============================================================================
# VMs to Migrate
# =============================================================================
migration_vms = []

# =============================================================================
# Migration Options
# =============================================================================
migration_type                    = "cold"
migration_start_immediately       = false
migration_cutover_datetime        = ""
migration_preserve_static_ips     = true
migration_preserve_mac_addresses  = false

# =============================================================================
# Performance Tuning
# =============================================================================
migration_max_concurrent_vms          = 10
migration_max_concurrent_disks_per_vm = 2
migration_transfer_network            = ""

# =============================================================================
# Pre/Post Migration Hooks
# =============================================================================
migration_hooks = []
