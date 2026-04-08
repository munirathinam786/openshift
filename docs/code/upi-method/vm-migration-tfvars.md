# UPI — vm-migration.tfvars

Variable definitions for VM Migration using the Migration Toolkit for Virtualization (MTV / Forklift) on the UPI DC Primary cluster.

!!! info "File Location"
    `upi-method/openshiftbaremetal/vm-migration.tfvars`

!!! tip "Used with Pipeline"
    Consumed by the [VM Migration Pipeline](../../pipeline/terraform-vm-migration-pipeline.md) via `-var-file=vm-migration.tfvars`.

## Key Variables

| Variable | Type | Description |
|----------|------|-------------|
| `enable_vm_migration` | bool | Master toggle for MTV deployment |
| `source_provider_type` | string | Source platform (`vsphere`, `ovirt`, `openstack`) |
| `source_provider_url` | string | Source platform endpoint URL |
| `migration_network_mappings` | list | Source → destination network mappings |
| `migration_storage_mappings` | list | Source → destination storage mappings |
| `migration_plan_name` | string | Name of the migration plan |
| `migration_plan_vms` | list | VMs to include in the migration plan |
| `migration_type` | string | `cold` or `warm` |
| `migration_max_concurrent_vms` | number | Max concurrent VM migrations |
| `migration_ansible_hooks` | list | Pre/post-migration Ansible playbooks |

## Source — UPI DC Primary

```hcl
--8<-- "upi-method/openshiftbaremetal/vm-migration.tfvars"
```
