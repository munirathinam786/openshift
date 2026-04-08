# IPI — Azure DevOps Pipeline — azure-pipelines-vm-migration.yml

Pipeline for migrating VMs from VMware vSphere, RHV, or OpenStack to OpenShift Virtualization
using the Migration Toolkit for Virtualization (MTV / Forklift).

!!! info "Pipeline Location"
    Source file: `ipi-method/azure-pipelines-vm-migration.yml`

!!! tip "High-Level Documentation"
    See [VM Migration Pipeline](../../../pipeline/terraform-vm-migration-pipeline.md) for workflow details, prerequisites, and usage guide.

## Pipeline Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `deploymentScope` | string | `dc-only` | Target cluster (`dc-only`, `dr-only`) |
| `sourceProviderType` | string | `vsphere` | Source platform (`vsphere`, `ovirt`, `openstack`) |
| `sourceProviderName` | string | `vmware-datacenter` | Logical name for source provider |
| `sourceProviderUrl` | string | — | Source platform endpoint URL |
| `migrationType` | string | `cold` | Migration type (`cold`, `warm`) |
| `migrationStartImmediately` | boolean | `false` | Auto-start migration |
| `migrationCutoverDatetime` | string | — | Warm migration cutover (ISO 8601) |
| `preserveStaticIPs` | boolean | `true` | Preserve source VM static IPs |
| `preserveMACAddresses` | boolean | `false` | Preserve source VM MACs |
| `maxConcurrentVMs` | number | `10` | Max concurrent VM migrations |
| `maxConcurrentDisksPerVM` | number | `2` | Max disk transfers per VM |
| `terraformAction` | string | `plan` | `plan`, `apply`, or `destroy` |
| `variableGroup` | string | `ocp-vm-migration-secrets` | ADO Variable Group |

## Required Secrets (ADO Variable Group)

| Secret | Description |
|--------|-------------|
| `source-provider-username` | Source platform username |
| `source-provider-password` | Source platform password |
| `source-provider-thumbprint` | TLS thumbprint (vSphere) or CA cert |

## Terraform Var Files

- `terraform.tfvars` — Base cluster configuration
- `vm-migration.tfvars` — Migration-specific settings (source provider, VM list, network/storage mappings)

## Source Code

```yaml
--8<-- "ipi-method/azure-pipelines-vm-migration.yml"
```
