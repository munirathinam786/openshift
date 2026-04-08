# VM Migration Pipeline

Dedicated Azure DevOps pipeline for migrating virtual machines from **VMware vSphere**, **Red Hat Virtualization (RHV/oVirt)**, or **OpenStack** to OpenShift Virtualization using the **Migration Toolkit for Virtualization (MTV / Forklift)**.

!!! info "Pipeline Locations"
    - IPI: `ipi-method/azure-pipelines-vm-migration.yml`
    - UPI: `upi-method/azure-pipelines-vm-migration.yml`

!!! warning "Requires OpenShift Virtualization"
    OpenShift Virtualization (CNV) must be deployed on the target cluster **before** running this pipeline. Use the [OpenShift Virtualization Pipeline](terraform-cnv-pipeline.md) first.

## Overview

The VM Migration pipeline automates the full lifecycle of the **Migration Toolkit for Virtualization (MTV)**:

1. **MTV Operator** — Subscribes to the `mtv-operator` from OperatorHub and creates the `ForkliftController` CR.
2. **Source Provider** — Registers the source virtualization platform (vSphere, RHV, or OpenStack) with credentials and endpoint URL.
3. **Destination Provider** — Registers the target OpenShift cluster as the destination.
4. **Network Mapping** — Maps source VM networks to OpenShift network attachment definitions (NADs) or pod network.
5. **Storage Mapping** — Maps source datastores/storage domains to OpenShift StorageClasses.
6. **Migration Plan** — Defines which VMs to migrate, migration type (cold/warm), and migration options.
7. **Migration Execution** — Triggers the migration plan with configurable concurrency and optional cutover scheduling.

## Pipeline Parameters

| Parameter | Type | Default | Values | Description |
|-----------|------|---------|--------|-------------|
| `deploymentScope` | string | `dc-only` | `dc-only`, `dr-only` | Target cluster (one at a time) |
| `sourceProviderType` | string | `vsphere` | `vsphere`, `ovirt`, `openstack` | Source virtualization platform |
| `sourceProviderName` | string | `vmware-datacenter` | — | Logical name for the source provider |
| `sourceProviderUrl` | string | — | — | Source platform URL (e.g. `https://vcenter.example.com/sdk`) |
| `migrationType` | string | `cold` | `cold`, `warm` | Cold = powered off; Warm = incremental + cutover |
| `migrationStartImmediately` | boolean | `false` | — | Start migration as soon as plan is created |
| `migrationCutoverDatetime` | string | — | — | Warm migration cutover time (ISO 8601) |
| `preserveStaticIPs` | boolean | `true` | — | Preserve source VM static IP addresses |
| `preserveMACAddresses` | boolean | `false` | — | Preserve source VM MAC addresses |
| `maxConcurrentVMs` | number | `10` | — | Max VMs migrating concurrently |
| `maxConcurrentDisksPerVM` | number | `2` | — | Max disk transfers per VM |
| `terraformAction` | string | `plan` | `plan`, `apply`, `destroy` | Terraform action to execute |
| `variableGroup` | string | `ocp-vm-migration-secrets` | — | ADO Variable Group for secrets |

## Pipeline Stages

![VM Migration (MTV) Pipeline](../diagrams/pipeline/11-vm-migration-pipeline.svg){: .drawio-diagram }

???+ note "Draw.io Source: VM Migration (MTV) Pipeline"
    [:material-download: Download .drawio file](../diagrams/pipeline/11-vm-migration-pipeline.drawio){ .md-button } — Open in [draw.io](https://app.diagrams.net) for interactive editing.

!!! note "One Cluster at a Time"
    Unlike the CNV pipeline, VM migration targets **one cluster at a time** (`dc-only` or `dr-only`). This is intentional — migration plans are cluster-specific with different VM lists and network/storage mappings.

### Stage 1 — VM Migration

- Runs in `openshiftbaremetal/` (DC) or `openshiftbaremetal-dr/` (DR)
- Uses `-var-file=terraform.tfvars -var-file=vm-migration.tfvars`
- Injects source provider credentials from ADO Variable Group as environment variables

### Stage 2 — Summary

- Prints migration configuration summary

## Workflow

![Vm Migration Workflow](../diagrams/pipeline/25-vm-migration-workflow.svg){: .drawio-diagram }

???+ note "Draw.io Source: Vm Migration Workflow"
    [:material-download: Download .drawio file](../diagrams/pipeline/25-vm-migration-workflow.drawio){ .md-button } — Open in [draw.io](https://app.diagrams.net) for interactive editing.

## Migration Types

### Cold Migration

- VMs are **powered off** before migration
- Single snapshot → full disk transfer → VM created on OpenShift
- **Pros**: Simpler, no data consistency concerns
- **Cons**: Downtime required for the entire transfer duration

### Warm Migration

- VMs remain **running** during migration
- Incremental snapshots are transferred periodically
- At **cutover time**, the VM is powered off, final delta is transferred, and the VM starts on OpenShift
- **Pros**: Minimal downtime (only final cutover)
- **Cons**: Requires more network bandwidth, longer overall process

## Prerequisites

!!! warning "Before running this pipeline"
    1. **OpenShift Virtualization deployed** — CNV must be installed on the target cluster
    2. **Source platform accessible** — Network path from OpenShift worker nodes to source platform (vCenter, RHV Manager, OpenStack API)
    3. **VDDK image** (vSphere only) — VMware Virtual Disk Development Kit image must be available in the cluster's internal registry
    4. **Source credentials** — Username/password for the source platform stored in ADO Variable Group
    5. **Network mappings** — Source VM networks must be mapped to OpenShift NADs or pod network
    6. **Storage mappings** — Source datastores must be mapped to available StorageClasses

## Required ADO Variable Group Secrets

| Secret | Description |
|--------|-------------|
| `source-provider-username` | Username for the source virtualization platform |
| `source-provider-password` | Password for the source virtualization platform |
| `source-provider-thumbprint` | TLS certificate thumbprint (vSphere) or CA cert |

## Terraform Var Files

| File | Purpose |
|------|---------|
| `terraform.tfvars` | Base cluster configuration (SSH, bastion, cluster name) |
| `vm-migration.tfvars` | Migration-specific settings (source provider, VM list, network/storage mappings, migration options) |

## Usage

```bash
# Plan — preview migration resources for DC Primary
# Parameters: deploymentScope=dc-only, terraformAction=plan

# Apply — execute cold migration for DC Primary
# Parameters: deploymentScope=dc-only, terraformAction=apply,
#             migrationType=cold, migrationStartImmediately=true

# Apply — schedule warm migration cutover for DR
# Parameters: deploymentScope=dr-only, terraformAction=apply,
#             migrationType=warm, migrationCutoverDatetime=2026-04-10T02:00:00Z

# Destroy — clean up migration resources (does NOT delete migrated VMs)
# Parameters: deploymentScope=dc-only, terraformAction=destroy
```
