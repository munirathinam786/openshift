# ACM Cluster Import Pipeline

Dedicated Azure DevOps pipeline for importing workload clusters (DC Primary, DR Secondary) into the **ACM Hub** as ManagedClusters and grouping them into a ManagedClusterSet.

!!! info "Pipeline Location"
    Source file: `ipi-method/azure-pipelines-acm-import.yml`

!!! tip "Runs on ACM Hub"
    This pipeline always targets the **management cluster** running the ACM Hub (`mgmt-dc` or `mgmt-dr`). It uses `acm-import.tfvars` alongside `terraform.tfvars`.

## Overview

ACM Cluster Import performs three key actions:

1. **ManagedCluster** — Creates a `ManagedCluster` CR on the ACM Hub for each workload cluster, which triggers the Klusterlet agent deployment on the target cluster.
2. **KlusterletAddonConfig** — Configures add-ons (Application Manager, Policy Controller, Search Collector, Cert Policy, IAM Policy) for each imported cluster.
3. **ManagedClusterSet** — Groups imported clusters into a logical set (e.g. `ocp-workload-clusters`) for placement and policy scoping.

## Pipeline Parameters

| Parameter | Type | Default | Values | Description |
|-----------|------|---------|--------|-------------|
| `importScope` | string | `all-workload` | `dc-primary-only`, `dr-secondary-only`, `all-workload` | Which clusters to import |
| `acmHub` | string | `mgmt-dc` | `mgmt-dc`, `mgmt-dr` | ACM Hub cluster to target |
| `enableClusterImport` | boolean | `true` | — | Create ManagedCluster + KlusterletAddonConfig |
| `enableClusterSet` | boolean | `true` | — | Create ManagedClusterSet for grouping |
| `terraformAction` | string | `plan` | `plan`, `apply`, `destroy` | Terraform action to execute |
| `variableGroup` | string | `ocp-baremetal-acm-secrets` | — | ADO Variable Group containing secrets |

## Pipeline Stages

![ACM Cluster Import Pipeline](../diagrams/pipeline/04-acm-import-pipeline.svg){: .drawio-diagram }

???+ note "Draw.io Source: ACM Cluster Import Pipeline"
    [:material-download: Download .drawio file](../diagrams/pipeline/04-acm-import-pipeline.drawio){ .md-button } — Open in [draw.io](https://app.diagrams.net) for interactive editing.

### Stage 1 — ACM Cluster Import

- Runs `terraform init` then `terraform plan/apply/destroy` on the selected ACM Hub directory
- Passes `-var-file=terraform.tfvars -var-file=acm-import.tfvars` plus feature toggle overrides from pipeline parameters
- Environment variables inject kubeconfig paths for DC and DR clusters

### Stage 2 — Validate Import

- Only runs when `terraformAction = apply`
- Checks `ManagedCluster` availability status via `oc get managedclusters`
- Verifies `ManagedClusterSet` and `KlusterletAddonConfig` were created
- Warns if any cluster is not in `Available` state

## Prerequisites

!!! warning "Before running this pipeline"
    1. **ACM Hub deployed** — The management cluster must have ACM Hub installed (`enable_acm = true`)
    2. **Workload clusters running** — DC Primary and/or DR Secondary must be deployed and accessible
    3. **Network connectivity** — ACM Hub must be able to reach the workload cluster API servers on port 6443
    4. **Kubeconfig paths** — Valid kubeconfig files for each workload cluster must be available on the pipeline agent

## Workflow

![Acm Import Workflow](../diagrams/pipeline/21-acm-import-workflow.svg){: .drawio-diagram }

???+ note "Draw.io Source: Acm Import Workflow"
    [:material-download: Download .drawio file](../diagrams/pipeline/21-acm-import-workflow.drawio){ .md-button } — Open in [draw.io](https://app.diagrams.net) for interactive editing.

## Required ADO Variable Group Secrets

| Secret | Description |
|--------|-------------|
| `dc-primary-kubeconfig-path` | Path to DC Primary kubeconfig on the pipeline agent |
| `dr-secondary-kubeconfig-path` | Path to DR Secondary kubeconfig on the pipeline agent |

## Usage

```bash
# Manual run — plan only (preview)
# Set importScope = all-workload, terraformAction = plan

# Apply — import both clusters
# Set importScope = all-workload, terraformAction = apply

# Import DC only
# Set importScope = dc-primary-only, terraformAction = apply

# Destroy — remove imported clusters from ACM
# Set importScope = all-workload, terraformAction = destroy
```

!!! note "Terraform State"
    The ACM import state is stored in the same Terraform state as the management cluster (`mgmt-dc/` or `mgmt-dr/`). The `acm_cluster_import` module is conditionally enabled via `enable_acm_cluster_import`.
