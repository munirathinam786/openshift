# UPI — Azure DevOps Pipeline — azure-pipelines-acm-dr.yml

Pipeline for configuring DRPolicy, DRPlacementControl, and executing failover/failback actions via ACM and OpenShift DR for UPI clusters.

!!! info "Pipeline Location"
    Source file: `upi-method/azure-pipelines-acm-dr.yml`

!!! tip "High-Level Documentation"
    See [ACM DR Failover/Failback Pipeline](../../pipeline/terraform-acm-dr-pipeline.md) for workflow details, prerequisites, and usage guide.

## Pipeline Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `drAction` | string | `none` | DR action (`none`, `failover`, `failback`, `relocate`) |
| `acmHub` | string | `mgmt-dc` | ACM Hub cluster (DR control plane) |
| `configureDRPolicy` | boolean | `true` | Configure DRPolicy + DRPlacementControl |
| `executeDRAction` | boolean | `false` | Execute the failover/failback action |
| `applicationScope` | string | `all` | Applications to protect/failover |
| `terraformAction` | string | `plan` | `plan`, `apply`, or `destroy` |
| `variableGroup` | string | `ocp-baremetal-acm-dr-secrets` | ADO Variable Group |

## Source Code

```yaml
--8<-- "upi-method/azure-pipelines-acm-dr.yml"
```
