# OpenShift Virtualization Pipeline

Dedicated Azure DevOps pipeline for deploying **OpenShift Virtualization** (KubeVirt / CNV) to workload clusters (DC Primary & DR Secondary).

!!! info "Pipeline Locations"
    - IPI: `ipi-method/azure-pipelines-cnv.yml`
    - UPI: `upi-method/azure-pipelines-cnv.yml`

!!! tip "Workload Clusters Only"
    This pipeline targets only the **non-management** workload clusters. OpenShift Virtualization is deployed on baremetal worker nodes with hardware-assisted virtualization (KVM).

## Overview

OpenShift Virtualization (CNV — Container-Native Virtualization) enables running traditional virtual machines alongside containers on the same OpenShift cluster. The pipeline automates:

1. **Operator Installation** — Subscribes to the `kubevirt-hyperconverged` operator from OperatorHub on the `stable` channel.
2. **HyperConverged CR** — Creates the `HyperConverged` custom resource in the `openshift-cnv` namespace with configurable CPU model, live-migration settings, networking, and storage defaults.
3. **Node Labeling** — Labels worker nodes with `node-role.kubernetes.io/virtualization=""` to identify CNV-capable nodes.
4. **Live Migration Config** — Configures bandwidth limits, parallelism, auto-converge, and post-copy settings.
5. **Networking** — Configures default VM network interface (masquerade, bridge, or SR-IOV), optional Linux bridge binding plugin.
6. **Storage** — Sets the default `StorageClass` for VM disks; optionally auto-imports common OS boot images.
7. **Monitoring** — Deploys `PrometheusRule` alerts for CNV health metrics (pending migrations, error rates, node CPU/memory).

## Pipeline Parameters

| Parameter | Type | Default | Values | Description |
|-----------|------|---------|--------|-------------|
| `deploymentScope` | string | `dc-only` | `dc-only`, `dr-only`, `dc-and-dr` | Target cluster(s) |
| `cnvChannel` | string | `stable` | — | Operator subscription channel |
| `cnvCpuModel` | string | `host-model` | `host-passthrough`, `host-model`, `Skylake-Server`, `Cascadelake-Server`, `Icelake-Server`, `Sapphire-Rapids` | Default CPU model for VMs |
| `cnvDefaultNetworkInterface` | string | `masquerade` | `masquerade`, `bridge`, `sr-iov` | Default VM network binding |
| `cnvEnableBridgeBinding` | boolean | `true` | — | Enable Linux bridge binding plugin |
| `cnvLiveMigrationBandwidth` | string | `64Mi` | — | Per-migration bandwidth limit |
| `cnvLiveMigrationParallelPerCluster` | number | `5` | — | Max parallel migrations per cluster |
| `cnvLiveMigrationParallelOutbound` | number | `2` | — | Max parallel outbound per node |
| `cnvLiveMigrationAutoConverge` | boolean | `true` | — | Allow auto-converge during live migration |
| `cnvLiveMigrationPostCopy` | boolean | `false` | — | Allow post-copy live migration |
| `cnvDefaultStorageClass` | string | `ocs-storagecluster-ceph-rbd-virtualization` | — | Default StorageClass for VM disks |
| `cnvCommonBootImageImport` | boolean | `true` | — | Auto-import common OS boot images |
| `cnvEnableMonitoringAlerts` | boolean | `true` | — | Deploy PrometheusRule alerts |
| `terraformAction` | string | `plan` | `plan`, `apply`, `destroy` | Terraform action to execute |
| `variableGroup` | string | `ocp-virtualization-secrets` | — | ADO Variable Group for secrets |

## Pipeline Stages

![OpenShift Virtualization (CNV) Pipeline](../diagrams/pipeline/10-cnv-pipeline.svg){: .drawio-diagram }

???+ note "Draw.io Source: OpenShift Virtualization (CNV) Pipeline"
    [:material-download: Download .drawio file](../diagrams/pipeline/10-cnv-pipeline.drawio){ .md-button } — Open in [draw.io](https://app.diagrams.net) for interactive editing.

### Stage 1 — DC Primary OpenShift Virtualization

- **Condition**: `deploymentScope = dc-only` or `dc-and-dr`
- Runs in `openshiftbaremetal/` directory
- Uses `-var-file=terraform.tfvars -var-file=openshift-virtualization.tfvars`
- Overrides all CNV parameters from pipeline inputs

### Stage 2 — DR Secondary OpenShift Virtualization

- **Condition**: `deploymentScope = dr-only` or `dc-and-dr`
- Runs in `openshiftbaremetal-dr/` directory
- Depends on Stage 1 when `dc-and-dr` is selected

### Stage 3 — Summary

- Prints deployment configuration summary

## Workflow

![Cnv Deploy Workflow](../diagrams/pipeline/24-cnv-deploy-workflow.svg){: .drawio-diagram }

???+ note "Draw.io Source: Cnv Deploy Workflow"
    [:material-download: Download .drawio file](../diagrams/pipeline/24-cnv-deploy-workflow.drawio){ .md-button } — Open in [draw.io](https://app.diagrams.net) for interactive editing.

## Prerequisites

!!! warning "Before running this pipeline"
    1. **Cluster deployed** — Target workload cluster must be fully operational
    2. **OCS/ODF storage** — OpenShift Data Foundation must be deployed with `ocs-storagecluster-ceph-rbd-virtualization` StorageClass
    3. **Hardware virtualization** — Worker nodes must support hardware-assisted virtualization (Intel VT-x / AMD-V)
    4. **SSH access** — Pipeline agent must reach the bastion host via SSH
    5. **OperatorHub** — The `kubevirt-hyperconverged` operator must be available in the cluster's OperatorHub

## Terraform Var Files

| File | Purpose |
|------|---------|
| `terraform.tfvars` | Base cluster configuration (SSH, bastion, cluster name) |
| `openshift-virtualization.tfvars` | CNV-specific settings (CPU model, live migration, networking, storage, boot images, monitoring) |

## Usage

```bash
# Plan only — DC Primary
# Parameters: deploymentScope=dc-only, terraformAction=plan

# Apply to both clusters
# Parameters: deploymentScope=dc-and-dr, terraformAction=apply

# Destroy CNV from DR only
# Parameters: deploymentScope=dr-only, terraformAction=destroy
```
