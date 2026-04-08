# =============================================================================
# VM Migration (MTV — Migration Toolkit for Virtualization) — DC Primary
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
# Provider type: vsphere, ovirt, openstack
source_provider_type = "vsphere"
source_provider_name = "vmware-datacenter"

# vCenter connection details
source_provider_url      = "https://vcenter.example.com/sdk"
source_provider_username = "administrator@vsphere.local"
source_provider_password = "REPLACE_VCENTER_PASSWORD"             # Override via ADO Variable Group

# vCenter SSL thumbprint (run: openssl s_client -connect vcenter.example.com:443 < /dev/null 2>/dev/null | openssl x509 -fingerprint -sha1 -noout)
source_provider_thumbprint = "AA:BB:CC:DD:EE:FF:00:11:22:33:44:55:66:77:88:99:AA:BB:CC:DD"

# CA certificate for vCenter (path on bastion, leave empty to use thumbprint)
source_provider_ca_cert = ""

# Skip TLS verification (NOT recommended for production)
source_provider_insecure_skip_verify = false

# VDDK image (VMware Virtual Disk Development Kit) — required for vSphere migrations
# Must be built and pushed to the cluster's internal registry beforehand.
# See: https://docs.redhat.com/en/documentation/migration_toolkit_for_virtualization/
# source_provider_vddk_init_image = "registry.example.com/vddk:v8.0.2"

# =============================================================================
# Destination Provider — OpenShift Cluster
# =============================================================================
# "host" uses the local OpenShift cluster as destination
destination_provider_name = "host"

# =============================================================================
# Alternative Source Provider Examples
# =============================================================================
# --- Red Hat Virtualization (RHV / oVirt) ---
# source_provider_type     = "ovirt"
# source_provider_name     = "rhv-datacenter"
# source_provider_url      = "https://rhvm.example.com/ovirt-engine/api"
# source_provider_username = "admin@internal"
# source_provider_password = "REPLACE_RHV_PASSWORD"
# source_provider_ca_cert  = "/home/kni/certs/rhvm-ca.pem"
# source_provider_thumbprint = ""   # Not needed for RHV; use ca_cert instead
#
# --- OpenStack ---
# source_provider_type     = "openstack"
# source_provider_name     = "openstack-cloud"
# source_provider_url      = "https://keystone.example.com:5000/v3"
# source_provider_username = "admin"
# source_provider_password = "REPLACE_OPENSTACK_PASSWORD"
# source_provider_ca_cert  = "/home/kni/certs/openstack-ca.pem"

# =============================================================================
# Network Mapping
# =============================================================================
# Map source VM networks to OpenShift destination networks
network_map_name = "vmware-network-map"
network_mappings = [
  {
    source_network      = "VM Network"         # VMware port group name
    destination_network = "pod"                # "pod" for default pod network
    destination_type    = "pod"                # "pod" or "multus" (for NAD)
  },
  # {
  #   source_network      = "VLAN100-Production"
  #   destination_network = "production-bridge"  # NAD name if destination_type = "multus"
  #   destination_type    = "multus"
  # },
]

# =============================================================================
# Storage Mapping
# =============================================================================
# Map source VM datastores to OpenShift storage classes
storage_map_name = "vmware-storage-map"
storage_mappings = [
  {
    source_datastore         = "datastore1"                                  # VMware datastore name
    destination_storage_class = "ocs-storagecluster-ceph-rbd-virtualization"  # ODF storage class
    volume_mode              = "Filesystem"                                  # Filesystem or Block
  },
  # {
  #   source_datastore         = "SAN-LUN-Production"
  #   destination_storage_class = "ocs-storagecluster-ceph-rbd-virtualization"
  #   volume_mode              = "Block"
  # },
]

# =============================================================================
# Migration Plan
# =============================================================================
migration_plan_name      = "vmware-to-ocp-dc"
migration_plan_namespace = "openshift-mtv"

# =============================================================================
# VMs to Migrate
# =============================================================================
# Specify VMs by name (and optionally by vSphere MoRef ID)
migration_vms = [
  # {
  #   name      = "web-server-01"
  #   id        = ""                           # vSphere MoRef ID (optional, name is sufficient)
  #   namespace = "production"                 # Target namespace on OpenShift
  # },
  # {
  #   name      = "db-server-01"
  #   id        = ""
  #   namespace = "databases"
  # },
  # {
  #   name      = "app-server-01"
  #   id        = ""
  #   namespace = "applications"
  # },
]

# =============================================================================
# Migration Options
# =============================================================================
# Type: "cold" (shutdown VM, full copy) or "warm" (incremental with CBT, vSphere only)
migration_type = "cold"

# Start migration immediately after plan creation
migration_start_immediately = false

# Scheduled cutover time for warm migration (ISO 8601 format)
# Only used when migration_type = "warm"
migration_cutover_datetime = ""

# Preserve source VM static IPs in the migrated VM
migration_preserve_static_ips = true

# Preserve source VM MAC addresses
migration_preserve_mac_addresses = false

# =============================================================================
# Performance Tuning
# =============================================================================
# Maximum concurrent VM migrations
migration_max_concurrent_vms = 10

# Maximum concurrent disk transfers per VM
migration_max_concurrent_disks_per_vm = 2

# Dedicated network for disk transfer (NAD name or "" for default)
migration_transfer_network = ""

# =============================================================================
# Pre/Post Migration Hooks (Ansible Playbooks)
# =============================================================================
# Run Ansible playbooks before or after VM migration
migration_hooks = [
  # {
  #   name      = "pre-migration-cleanup"
  #   namespace = "openshift-mtv"
  #   playbook  = "/home/kni/playbooks/pre-migration.yml"
  #   image     = "quay.io/konveyor/hook-runner:latest"
  # },
  # {
  #   name      = "post-migration-config"
  #   namespace = "openshift-mtv"
  #   playbook  = "/home/kni/playbooks/post-migration.yml"
  #   image     = "quay.io/konveyor/hook-runner:latest"
  # },
]
