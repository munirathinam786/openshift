# azure-pipelines-ceph-migration.yml (Ceph Migration — UPI)

Azure DevOps pipeline for Ceph/ODF storage migration between clusters or datacenters (UPI method).
See the [Ceph Migration Pipeline Documentation](../../pipeline/terraform-ceph-migration-pipeline.md) for full details.

!!! info "Location"
    `upi-method/azure-pipelines-ceph-migration.yml`

## Pipeline Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `deploymentScope` | string | `dc-only` | Source cluster (`dc-only` or `dr-only`) |
| `migrationAction` | string | `prepare` | Action: `prepare`, `migrate`, `validate`, `cleanup` |
| `migrationMode` | string | `async` | Replication mode: `async` or `sync` |
| `replicationSchedule` | string | `*/5 * * * *` | Async snapshot interval |
| `poolName` | string | `ocs-storagecluster-cephblockpool` | Ceph block pool |
| `verifyDataIntegrity` | boolean | `true` | Verify data after migration |
| `terraformAction` | string | `plan` | Terraform action |
| `variableGroup` | string | `ocp-ceph-migration-secrets` | ADO Variable Group |

## Stages

1. **Ceph Migration DC/DR** — Execute migration action on selected cluster
2. **Summary** — Print deployment summary
