# IPI DC Primary — ceph-migration.tfvars

Configuration for Ceph/ODF storage migration from DC Primary to another cluster using RBD mirroring.
Used with the [Ceph Migration Pipeline](../../../pipeline/terraform-ceph-migration-pipeline.md).

!!! info "Usage"
    ```bash
    terraform apply -var-file=terraform.tfvars -var-file=ceph-migration.tfvars
    ```

!!! warning "Migration Action"
    Set `ceph_migration_action = "prepare"` for initial setup. Change to `migrate`, `validate`, or `cleanup` only when executing subsequent stages.

## Variable Reference

| Variable | Type | Value | Description |
|----------|------|-------|-------------|
| `enable_ceph_migration` | bool | `true` | Enable the Ceph migration module |
| `ceph_migration_source_cluster_name` | string | `dc-primary` | Source cluster name |
| `ceph_migration_source_cluster_kubeconfig` | string | `/opt/ocp/dc-primary/auth/kubeconfig` | Source kubeconfig path |
| `ceph_migration_destination_cluster_name` | string | `dr-secondary` | Destination cluster name |
| `ceph_migration_destination_cluster_kubeconfig` | string | `/opt/ocp/dr-secondary/auth/kubeconfig` | Destination kubeconfig path |
| `ceph_migration_mode` | string | `async` | Replication mode |
| `ceph_migration_replication_schedule` | string | `*/5 * * * *` | Async replication schedule |
| `ceph_migration_pool_name` | string | `ocs-storagecluster-cephblockpool` | Ceph block pool |
| `ceph_migration_storage_class` | string | `ocs-storagecluster-ceph-rbd` | Destination StorageClass |
| `ceph_migration_action` | string | `prepare` | Migration action |
| `ceph_migration_namespaces` | list(object) | See below | Namespaces to migrate |

## Namespaces

| Namespace | PVC Selector | Exclude PVCs |
|-----------|-------------|--------------|
| `ai-platform` | `app=ai-platform` | — |

## Source Code

```hcl
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
ceph_migration_action = "prepare"

# ---- Namespaces to Migrate ----
ceph_migration_namespaces = [
  {
    name         = "ai-platform"
    pvc_selector = { app = "ai-platform" }
    exclude_pvcs = []
  },
]

# ---- S3 Configuration ----
ceph_migration_s3_endpoint = ""
ceph_migration_s3_bucket   = "ceph-migration-metadata"

# ---- Advanced ----
ceph_migration_rbd_mirror_count    = 1
ceph_migration_verify_data_integrity = true
```
