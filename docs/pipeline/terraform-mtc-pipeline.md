# MTC (Migration Toolkit for Containers) Pipeline

Dedicated Azure DevOps pipeline for migrating **containerized workloads** (namespaces, PVs, Deployments, Services) between OpenShift clusters using the **Migration Toolkit for Containers (MTC)**.

!!! info "Pipeline Locations"
    - IPI: `ipi-method/azure-pipelines-mtc.yml`
    - UPI: `upi-method/azure-pipelines-mtc.yml`

!!! abstract "MTC vs MTV"
    | Toolkit | What it migrates | Source → Destination |
    |---------|-----------------|---------------------|
    | **MTV** (Migration Toolkit for Virtualization) | Virtual Machines | VMware/RHV/OpenStack → OpenShift Virtualization |
    | **MTC** (Migration Toolkit for Containers) | Containerized Workloads | OpenShift/Kubernetes → OpenShift |

## Overview

MTC automates the full lifecycle of workload migration between OpenShift clusters:

1. **MTC Operator** — Subscribes to `mtc-operator` from OperatorHub; creates `MigrationController` CR with Velero and Restic.
2. **Source Cluster Registration** — Registers the remote source cluster via `MigCluster` CR using a service account token.
3. **Replication Repository** — Configures S3-compatible storage (`MigStorage`) for intermediate data transfer.
4. **Migration Plan** — Defines namespaces to migrate, PV handling, network mappings via `MigPlan`.
5. **Migration Execution** — Triggers `MigMigration` (stage, final, or rollback).

## Pipeline Parameters

| Parameter | Type | Default | Values | Description |
|-----------|------|---------|--------|-------------|
| `deploymentScope` | string | `dc-only` | `dc-only`, `dr-only` | Target cluster |
| `mtcSourceClusterName` | string | `source-ocp-cluster` | — | Source cluster name |
| `mtcSourceClusterUrl` | string | — | — | Source cluster API URL |
| `mtcSourceClusterInsecure` | boolean | `false` | — | Skip TLS for source cluster |
| `mtcMigrationType` | string | `final` | `stage`, `final`, `rollback` | Migration type |
| `mtcPvCopyMethod` | string | `filesystem` | `filesystem`, `snapshot` | PV copy method |
| `mtcPvVerify` | boolean | `true` | — | Verify PV data integrity |
| `mtcDirectVolumeMigration` | boolean | `true` | — | Enable Direct Volume Migration |
| `mtcDirectImageMigration` | boolean | `true` | — | Enable Direct Image Migration |
| `mtcQuiescePods` | boolean | `true` | — | Quiesce source pods during final |
| `mtcKeepAnnotations` | boolean | `true` | — | Preserve annotations |
| `mtcPreserveNodePorts` | boolean | `false` | — | Preserve NodePort values |
| `terraformAction` | string | `plan` | `plan`, `apply`, `destroy` | Terraform action |
| `variableGroup` | string | `ocp-mtc-secrets` | — | ADO Variable Group |

## Migration Types

### Stage Migration
- Copies data **without** quiescing pods or cutting over
- Repeatable — use for incremental data pre-seeding before final cutover
- Source workloads remain running

### Final Migration
- Full migration with **quiesce** (scale-down) + cutover
- Source pods are scaled to 0, final data sync, then workloads start on destination
- Minimal downtime window

### Rollback
- Reverts a completed final migration
- Restores source cluster to pre-migration state

## Workflow

![MTC Container Migration Pipeline](../diagrams/pipeline/12-mtc-pipeline.svg){: .drawio-diagram }

???+ note "Draw.io Source: MTC Container Migration Pipeline"
    [:material-download: Download .drawio file](../diagrams/pipeline/12-mtc-pipeline.drawio){ .md-button } — Open in [draw.io](https://app.diagrams.net) for interactive editing.

## Direct Migration Modes

### Direct Volume Migration (DVM)
- Transfers PV data **directly** between clusters over Stunnel
- Bypasses the replication repository for PV data — much faster
- Requires network connectivity between source and destination cluster worker nodes

### Direct Image Migration (DIM)
- Transfers container images **directly** between internal registries
- Bypasses the replication repository for images
- Requires exposed registry routes on both clusters

## Prerequisites

!!! warning "Before running this pipeline"
    1. **MTC installed on source cluster** — The source cluster must also have the MTC operator installed with `MigrationController`
    2. **Service account token** — Generate on source cluster: `oc sa get-token migration-controller -n openshift-migration`
    3. **S3 storage** — Replication repository (MinIO, ODF MCG, AWS S3) must be accessible from both clusters
    4. **Network connectivity** — Destination must reach source API (port 6443) and worker nodes (for DVM)
    5. **Matching namespaces** — Target namespaces should not exist on destination (or be empty for re-migration)

## Required ADO Variable Group Secrets

| Secret | Description |
|--------|-------------|
| `mtc-source-cluster-sa-token` | Service account token for the source cluster |
| `mtc-s3-access-key` | S3 access key for replication repository |
| `mtc-s3-secret-key` | S3 secret key for replication repository |

## Terraform Var Files

| File | Purpose |
|------|---------|
| `terraform.tfvars` | Base cluster configuration |
| `mtc.tfvars` | MTC-specific settings (source/dest clusters, S3 repo, namespaces, PV mapping, migration options) |

## Usage

```bash
# Plan — preview MTC resources for DC Primary
# Parameters: deploymentScope=dc-only, terraformAction=plan

# Stage migration — pre-seed data without cutover
# Parameters: deploymentScope=dc-only, terraformAction=apply, mtcMigrationType=stage

# Final migration — full cutover
# Parameters: deploymentScope=dc-only, terraformAction=apply, mtcMigrationType=final

# Rollback — revert final migration
# Parameters: deploymentScope=dc-only, terraformAction=apply, mtcMigrationType=rollback

# Destroy — clean up MTC resources (does NOT delete migrated workloads)
# Parameters: deploymentScope=dc-only, terraformAction=destroy
```
