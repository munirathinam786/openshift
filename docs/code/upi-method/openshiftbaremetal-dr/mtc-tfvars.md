# UPI DR — mtc.tfvars

Variable definitions for MTC (Migration Toolkit for Containers) — migrating containerized workloads between OpenShift clusters via the UPI DR Secondary cluster.

!!! info "File Location"
    `upi-method/openshiftbaremetal-dr/mtc.tfvars`

!!! tip "Used with Pipeline"
    Consumed by the [MTC Pipeline](../../../pipeline/terraform-mtc-pipeline.md) via `-var-file=mtc.tfvars`.

## Key Variables

| Variable | Type | Description |
|----------|------|-------------|
| `enable_mtc` | bool | Master toggle for MTC deployment |
| `mtc_source_cluster_name` | string | Logical name for the source cluster |
| `mtc_source_cluster_url` | string | API URL of the source cluster |
| `mtc_source_cluster_sa_token` | string | Service account token for source cluster |
| `mtc_destination_cluster_name` | string | Destination cluster name (`host` = local) |
| `mtc_replication_repository_*` | various | S3 storage for migration data |
| `mtc_migration_plan_namespaces` | list | Namespaces to migrate with optional remapping |
| `mtc_migration_type` | string | `stage`, `final`, or `rollback` |
| `mtc_pv_copy_method` | string | `filesystem` (Restic) or `snapshot` (CSI) |
| `mtc_pv_storage_class_mapping` | list | Source → destination StorageClass mapping |
| `mtc_enable_direct_volume_migration` | bool | Enable DVM for faster PV transfer |
| `mtc_enable_direct_image_migration` | bool | Enable DIM for direct registry transfer |
| `mtc_migration_hooks` | list | Pre/post migration Ansible hooks |

## Source — UPI DR Secondary

```hcl
--8<-- "upi-method/openshiftbaremetal-dr/mtc.tfvars"
```
