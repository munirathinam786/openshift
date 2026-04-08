# UPI — Azure DevOps Pipeline — azure-pipelines-acm-import.yml

Pipeline for importing UPI workload clusters into ACM Hub as ManagedClusters.
Supports selective import scope, ManagedClusterSet creation, and post-import validation.

!!! info "Pipeline Location"
    Source file: `upi-method/azure-pipelines-acm-import.yml`

!!! tip "High-Level Documentation"
    See [ACM Cluster Import Pipeline](../../pipeline/terraform-acm-import-pipeline.md) for workflow details, prerequisites, and usage guide.

## Pipeline Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `importScope` | string | `all-workload` | Clusters to import (`dc-primary-only`, `dr-secondary-only`, `all-workload`) |
| `acmHub` | string | `mgmt-dc` | ACM Hub cluster target |
| `enableClusterImport` | boolean | `true` | Enable ManagedCluster + KlusterletAddonConfig |
| `enableClusterSet` | boolean | `true` | Create ManagedClusterSet |
| `terraformAction` | string | `plan` | `plan`, `apply`, or `destroy` |
| `variableGroup` | string | `ocp-baremetal-acm-secrets` | ADO Variable Group |

## Source Code

```yaml
--8<-- "upi-method/azure-pipelines-acm-import.yml"
```
