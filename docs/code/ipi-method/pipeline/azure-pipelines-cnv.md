# IPI — Azure DevOps Pipeline — azure-pipelines-cnv.yml

Pipeline for deploying OpenShift Virtualization (KubeVirt / CNV) to workload clusters.
Supports DC Primary, DR Secondary, or both clusters simultaneously.

!!! info "Pipeline Location"
    Source file: `ipi-method/azure-pipelines-cnv.yml`

!!! tip "High-Level Documentation"
    See [OpenShift Virtualization Pipeline](../../../pipeline/terraform-cnv-pipeline.md) for workflow details, prerequisites, and usage guide.

## Pipeline Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `deploymentScope` | string | `dc-only` | Target clusters (`dc-only`, `dr-only`, `dc-and-dr`) |
| `cnvChannel` | string | `stable` | Operator subscription channel |
| `cnvCpuModel` | string | `host-model` | Default CPU model for VMs |
| `cnvDefaultNetworkInterface` | string | `masquerade` | Default VM network binding |
| `cnvEnableBridgeBinding` | boolean | `true` | Enable Linux bridge binding plugin |
| `cnvLiveMigrationBandwidth` | string | `64Mi` | Per-migration bandwidth limit |
| `cnvLiveMigrationParallelPerCluster` | number | `5` | Max parallel migrations per cluster |
| `cnvLiveMigrationParallelOutbound` | number | `2` | Max parallel outbound per node |
| `cnvLiveMigrationAutoConverge` | boolean | `true` | Allow auto-converge |
| `cnvLiveMigrationPostCopy` | boolean | `false` | Allow post-copy |
| `cnvDefaultStorageClass` | string | `ocs-storagecluster-ceph-rbd-virtualization` | Default StorageClass for VM disks |
| `cnvCommonBootImageImport` | boolean | `true` | Auto-import OS boot images |
| `cnvEnableMonitoringAlerts` | boolean | `true` | Deploy PrometheusRule alerts |
| `terraformAction` | string | `plan` | `plan`, `apply`, or `destroy` |
| `variableGroup` | string | `ocp-virtualization-secrets` | ADO Variable Group |

## Terraform Var Files

- `terraform.tfvars` — Base cluster configuration
- `openshift-virtualization.tfvars` — CNV-specific settings

## Source Code

```yaml
--8<-- "ipi-method/azure-pipelines-cnv.yml"
```
