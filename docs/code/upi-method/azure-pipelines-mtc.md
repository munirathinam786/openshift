# UPI — Azure DevOps Pipeline — azure-pipelines-mtc.yml

Pipeline for migrating containerized workloads between OpenShift clusters using
the Migration Toolkit for Containers (MTC / Crane) on UPI clusters.

!!! info "Pipeline Location"
    Source file: `upi-method/azure-pipelines-mtc.yml`

!!! tip "High-Level Documentation"
    See [MTC Pipeline](../../pipeline/terraform-mtc-pipeline.md) for workflow details, prerequisites, and usage guide.

## Pipeline Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `deploymentScope` | string | `dc-only` | Target cluster (`dc-only`, `dr-only`) |
| `mtcSourceClusterName` | string | `source-ocp-cluster` | Source cluster name |
| `mtcSourceClusterUrl` | string | — | Source cluster API URL |
| `mtcSourceClusterInsecure` | boolean | `false` | Skip TLS for source |
| `mtcMigrationType` | string | `final` | `stage`, `final`, `rollback` |
| `mtcPvCopyMethod` | string | `filesystem` | `filesystem` or `snapshot` |
| `mtcPvVerify` | boolean | `true` | Verify PV data integrity |
| `mtcDirectVolumeMigration` | boolean | `true` | Enable DVM |
| `mtcDirectImageMigration` | boolean | `true` | Enable DIM |
| `mtcQuiescePods` | boolean | `true` | Quiesce source pods |
| `mtcKeepAnnotations` | boolean | `true` | Preserve annotations |
| `mtcPreserveNodePorts` | boolean | `false` | Preserve NodePort values |
| `terraformAction` | string | `plan` | `plan`, `apply`, or `destroy` |
| `variableGroup` | string | `ocp-mtc-secrets` | ADO Variable Group |

## Required Secrets (ADO Variable Group)

| Secret | Description |
|--------|-------------|
| `mtc-source-cluster-sa-token` | Source cluster SA token |
| `mtc-s3-access-key` | S3 access key |
| `mtc-s3-secret-key` | S3 secret key |

## Terraform Var Files

- `terraform.tfvars` — Base cluster configuration
- `mtc.tfvars` — MTC settings (source/dest clusters, S3 repo, namespaces, PV mappings)

## Source Code

```yaml
--8<-- "upi-method/azure-pipelines-mtc.yml"
```
