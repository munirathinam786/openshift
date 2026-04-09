# Author: Sathishkumar Munirathinam

# =============================================================================
# Ceph Migration — Variable Values (DC Primary)
# Migrates Ceph/ODF storage data between clusters or datacenters
# using RBD mirroring and snapshot-based replication.
# =============================================================================

# ---- Enable Ceph Migration ----
enable_ceph_migration = true

# ---- Source Cluster ----
ceph_migration_source_cluster_name       = "dc-primary"
ceph_migration_source_cluster_kubeconfig = "/opt/ocp/dc-primary/auth/kubeconfig"

# ---- Destination Cluster ----
ceph_migration_destination_cluster_name       = "dr-secondary"
ceph_migration_destination_cluster_kubeconfig = "/opt/ocp/dr-secondary/auth/kubeconfig"

# ---- Migration Configuration ----
ceph_migration_mode                = "async"
ceph_migration_replication_schedule = "*/5 * * * *"
ceph_migration_pool_name           = "ocs-storagecluster-cephblockpool"
ceph_migration_cephfs_pool_name    = ""
ceph_migration_storage_class       = "ocs-storagecluster-ceph-rbd"

# ---- Migration Action ----
# Values: prepare, migrate, validate, cleanup
#   prepare  — Setup mirroring between source and destination
#   migrate  — Promote destination and demote source (cutover)
#   validate — Check replication and data status
#   cleanup  — Remove mirroring configuration from source
ceph_migration_action = "prepare"

# ---- Namespaces to Migrate ----
ceph_migration_namespaces = [
  {
    name         = "agent-builder"
    pvc_selector = { app = "agent-builder" }
    exclude_pvcs = []
  },
  # Uncomment to add more namespaces:
  # {
  #   name         = "production-db"
  #   pvc_selector = { tier = "database" }
  #   exclude_pvcs = ["temp-pvc"]
  # },
]

# ---- S3 Configuration ----
ceph_migration_s3_endpoint = ""
ceph_migration_s3_bucket   = "ceph-migration-metadata"

# ---- Advanced ----
ceph_migration_rbd_mirror_count    = 1
ceph_migration_verify_data_integrity = true
