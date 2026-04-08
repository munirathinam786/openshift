# IPI — openshift-virtualization.tfvars

Variable definitions for OpenShift Virtualization (KubeVirt / CNV) deployment on workload clusters.

!!! info "File Locations"
    - DC Primary: `ipi-method/openshiftbaremetal/openshift-virtualization.tfvars`
    - DR Secondary: `ipi-method/openshiftbaremetal-dr/openshift-virtualization.tfvars`

!!! tip "Used with Pipeline"
    Consumed by the [OpenShift Virtualization Pipeline](../../../pipeline/terraform-cnv-pipeline.md) via `-var-file=openshift-virtualization.tfvars`.

## Key Variables

| Variable | Type | Description |
|----------|------|-------------|
| `enable_openshift_virtualization` | bool | Master toggle for CNV deployment |
| `cnv_channel` | string | Operator subscription channel |
| `cnv_cpu_model` | string | Default CPU model for VMs |
| `cnv_default_network_interface` | string | Default VM network binding |
| `cnv_live_migration_*` | various | Live migration bandwidth, parallelism, auto-converge, post-copy |
| `cnv_default_storage_class` | string | StorageClass for VM disks |
| `cnv_pci_passthrough_devices` | list | PCI device IDs for GPU/NIC passthrough |
| `cnv_mediated_devices` | list | vGPU mediated device types |
| `cnv_vm_templates` | list | Custom VM template definitions |
| `cnv_boot_images` | list | Custom boot image import definitions |
| `cnv_rbac_namespaces` | list | Namespaces for VM admin RBAC roles |

## Source — DC Primary

```hcl
--8<-- "ipi-method/openshiftbaremetal/openshift-virtualization.tfvars"
```
