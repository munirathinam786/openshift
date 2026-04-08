# Azure DevOps Pipeline — Multi-Cluster Deployment

The ADO pipeline provides **selective deployment** of any combination of the four cluster environments with optional Submariner networking and ODF DR replication.

!!! info "Multi-Cluster Architecture"
    See also:
    [Multi-Cluster Overview](../architecture/terraform-multi-cluster-overview.md) |
    [DC Primary](../clusters/terraform-ocp-baremetal.md) |
    [DR Secondary](../clusters/terraform-dr-secondary.md) |
    [Management DC](../clusters/terraform-mgmt-dc.md) |
    [Management DR](../clusters/terraform-mgmt-dr.md)

## ADO Prerequisites

![ADO Prerequisites & Pipeline Execution Flow](../diagrams/pipeline/27-ado-prerequisites.svg){: .drawio-diagram }

???+ note "Draw.io Source: ADO Prerequisites & Pipeline Execution Flow"
    [:material-download: Download .drawio file](../diagrams/pipeline/27-ado-prerequisites.drawio){ .md-button } — Open in [draw.io](https://app.diagrams.net) for interactive editing.

Before creating and running any pipeline, the following must be configured in your Azure DevOps project:

### 1. Self-Hosted Agent Pool

All pipelines use a **self-hosted Linux agent pool** named **`self-hosted-linux`**.

| Requirement | Details |
|---|---|
| Pool Name | `self-hosted-linux` |
| OS | Linux (RHEL 8+/9+ or Ubuntu 20.04+) |
| Network Access | Must reach all bare-metal OpenShift cluster API endpoints (port 6443) and bastion hosts via SSH |
| Terraform | Installed automatically by pipeline via `TerraformInstaller@1` task |
| Tools | `oc`, `kubectl`, `jq`, `ssh` must be available on the agent |

!!! tip "Agent Setup"
    Go to **Project Settings → Agent Pools → Add Pool** → select **Self-hosted** → name it `self-hosted-linux`. Then install and register the Azure Pipelines agent on your Linux host.

### 2. Terraform Extension (Marketplace)

Install the **Terraform** extension from the Azure DevOps Marketplace:

| Extension | Publisher | Task Used |
|---|---|---|
| [Terraform](https://marketplace.visualstudio.com/items?itemName=ms-devlabs.custom-terraform-tasks) | Microsoft DevLabs | `TerraformInstaller@1` |

!!! warning "Required"
    Without this extension, all pipelines will fail at the **Install Terraform** step. Install it from **Organization Settings → Extensions → Browse Marketplace**.

### 3. ADO Variable Groups

Create the following Variable Groups under **Project Settings → Pipelines → Library → + Variable Group**. Mark all values as **secret** (lock icon).

| Variable Group | Used By Pipeline | Description |
|---|---|---|
| `ocp-baremetal-secrets` | IPI Multi-Cluster Deployment | Main deployment secrets (DC, DR, Mgmt) |
| `ocp-baremetal-upi-secrets` | UPI Deployment | UPI main deployment secrets |
| `ocp-baremetal-day2-secrets` | IPI Day 2 Operations | Day 2 operator secrets (LDAP, ArgoCD, OADP, etc.) |
| `ocp-upi-day2-secrets` | UPI Day 2 Operations | UPI Day 2 operator secrets |
| `ocp-baremetal-acm-secrets` | ACM Cluster Import | ACM import kubeconfig paths + secrets |
| `ocp-baremetal-acm-dr-secrets` | ACM DR Failover/Failback | DR policy + failover secrets |
| `ocp-virtualization-secrets` | OpenShift Virtualization (CNV) | CNV-specific secrets |
| `ocp-mtc-secrets` | MTC Migration | Migration Toolkit for Containers secrets |
| `ocp-vm-migration-secrets` | VM Migration | Source provider credentials for VM migration |

### 4. Secret Variables Reference

The following secrets must be populated across the variable groups above:

| Secret Variable | Variable Group(s) | Description |
|---|---|---|
| `quay-admin-password` | `ocp-baremetal-secrets`, `ocp-baremetal-upi-secrets` | Quay mirror registry admin password |
| `ngc-api-key` | `ocp-baremetal-secrets`, `ocp-baremetal-upi-secrets` | NVIDIA NGC API key for GPU operators |
| `submariner-broker-token` | `ocp-baremetal-secrets` | Submariner broker ServiceAccount token |
| `odf-dr-s3-access-key` | `ocp-baremetal-secrets`, `ocp-baremetal-upi-secrets` | S3 access key for ODF DR metadata |
| `odf-dr-s3-secret-key` | `ocp-baremetal-secrets`, `ocp-baremetal-upi-secrets` | S3 secret key for ODF DR metadata |
| `acs-central-admin-password` | `ocp-baremetal-secrets` | ACS Central initial admin password |
| `acm-s3-access-key` | `ocp-baremetal-secrets` | S3 access key for ACM Observability |
| `acm-s3-secret-key` | `ocp-baremetal-secrets` | S3 secret key for ACM Observability |
| `ldap-bind-password` | `ocp-baremetal-day2-secrets`, `ocp-upi-day2-secrets` | LDAP bind password for OAuth |
| `log-s3-access-key` | `ocp-baremetal-day2-secrets`, `ocp-upi-day2-secrets` | S3 access key for log forwarding |
| `log-s3-secret-key` | `ocp-baremetal-day2-secrets`, `ocp-upi-day2-secrets` | S3 secret key for log forwarding |
| `oadp-s3-access-key` | `ocp-baremetal-day2-secrets`, `ocp-upi-day2-secrets` | S3 access key for OADP backups |
| `oadp-s3-secret-key` | `ocp-baremetal-day2-secrets`, `ocp-upi-day2-secrets` | S3 secret key for OADP backups |
| `argocd-repo-token` | `ocp-baremetal-day2-secrets`, `ocp-upi-day2-secrets` | Git token for ArgoCD repo access |
| `pac-webhook-secret` | `ocp-baremetal-day2-secrets`, `ocp-upi-day2-secrets` | Pipelines-as-Code webhook secret |
| `pac-webhook-shared-secret` | `ocp-baremetal-day2-secrets`, `ocp-upi-day2-secrets` | Pipelines-as-Code shared secret |
| `channel-git-token` | `ocp-baremetal-acm-dr-secrets` | Git token for ACM application channels |
| `mtc-replication-repository-access-key` | `ocp-mtc-secrets` | S3 access key for MTC replication |
| `mtc-replication-repository-secret-key` | `ocp-mtc-secrets` | S3 secret key for MTC replication |
| `mtc-source-cluster-sa-token` | `ocp-mtc-secrets` | Source cluster SA token for MTC |
| `source-provider-username` | `ocp-vm-migration-secrets` | Source hypervisor username |
| `source-provider-password` | `ocp-vm-migration-secrets` | Source hypervisor password |
| `source-provider-thumbprint` | `ocp-vm-migration-secrets` | Source hypervisor SSL thumbprint |

## Pipeline Parameters

![IPI Pipeline Parameters](../diagrams/pipeline/02-ipi-pipeline-parameters.svg){: .drawio-diagram }

???+ note "Draw.io Source: IPI Pipeline Parameters"
    [:material-download: Download .drawio file](../diagrams/pipeline/02-ipi-pipeline-parameters.drawio){ .md-button } — Open in [draw.io](https://app.diagrams.net) for interactive editing.

### Deployment Scope Options

![IPI Pipeline Scope Selection](../diagrams/pipeline/16-ipi-pipeline-scope.svg){: .drawio-diagram }

???+ note "Draw.io Source: IPI Pipeline Scope Selection"
    [:material-download: Download .drawio file](../diagrams/pipeline/16-ipi-pipeline-scope.drawio){ .md-button } — Open in [draw.io](https://app.diagrams.net) for interactive editing.

| Scope | Deploys | Use Case |
|-------|---------|----------|
| `dc-only` | DC Primary | Initial DC setup or DC-only changes |
| `dr-only` | DR Secondary | DR site day-2 changes |
| `dc-and-dr` | DC → DR (sequential) | Full workload deployment |
| `mgmt-dc-only` | Mgmt DC | ACM/ACS/Quay changes on DC |
| `mgmt-dr-only` | Mgmt DR | DR management cluster changes |
| `mgmt-clusters` | Mgmt DC → Mgmt DR | Both management clusters |
| `all-dc` | DC Primary → Mgmt DC | All DC site clusters |
| `all-dr` | DR Secondary → Mgmt DR | All DR site clusters |
| `all` | DC → DR → Mgmt DC → Mgmt DR | Complete multi-cluster deployment |

## Stage Execution Order

![IPI Pipeline Stage Execution](../diagrams/pipeline/01-ipi-pipeline-stages.svg){: .drawio-diagram }

???+ note "Draw.io Source: IPI Pipeline Stage Execution"
    [:material-download: Download .drawio file](../diagrams/pipeline/01-ipi-pipeline-stages.drawio){ .md-button } — Open in [draw.io](https://app.diagrams.net) for interactive editing.

## How Each Stage Works

### Stage 1 — DC Primary

![Post-Deployment Topology](../diagrams/pipeline/03-post-deployment-topology.svg){: .drawio-diagram }

???+ note "Draw.io Source: Post-Deployment Topology"
    [:material-download: Download .drawio file](../diagrams/pipeline/03-post-deployment-topology.drawio){ .md-button } — Open in [draw.io](https://app.diagrams.net) for interactive editing.

- Runs in `openshiftbaremetal/`
- Injects **`enable_submariner=true`** via `-var` if Submariner is selected
- Secrets from ADO Variable Group: `quay-admin-password`, `ngc-api-key`

### Stage 2 — DR Secondary

![Pipeline Secrets Flow](../diagrams/pipeline/17-pipeline-secrets-flow.svg){: .drawio-diagram }

???+ note "Draw.io Source: Pipeline Secrets Flow"
    [:material-download: Download .drawio file](../diagrams/pipeline/17-pipeline-secrets-flow.drawio){ .md-button } — Open in [draw.io](https://app.diagrams.net) for interactive editing.

- Runs in `openshiftbaremetal-dr/`
- Depends on **Stage 1** (when scope is `dc-and-dr` or `all`)
- Injects Submariner agent + ODF DR settings
- Additional secrets: `submariner-broker-token`, `odf-dr-s3-access-key`, `odf-dr-s3-secret-key`

### Stage 3 — Management DC

- Runs in `mgmt-dc/`
- Deploys ACM Hub, ACS Central, Quay Enterprise
- Secrets: `acs-central-admin-password`, `acm-s3-access-key`, `acm-s3-secret-key`

### Stage 4 — Management DR

- Runs in `mgmt-dr/`
- Depends on **Stage 3** (when scope is `mgmt-clusters` or `all`)
- ACS connects to Central endpoint from Stage 3

## Post-Deployment Cluster Topology

After the pipeline completes, this is the resulting cluster connectivity:

![Ado Deploy Topology](../diagrams/pipeline/19-ado-deploy-topology.svg){: .drawio-diagram }

???+ note "Draw.io Source: Ado Deploy Topology"
    [:material-download: Download .drawio file](../diagrams/pipeline/19-ado-deploy-topology.drawio){ .md-button } — Open in [draw.io](https://app.diagrams.net) for interactive editing.

## ADO Variable Group

Create a Variable Group named **`ocp-baremetal-secrets`** in ADO with these secrets:

| Secret Name | Used By | Description |
|-------------|---------|-------------|
| `quay-admin-password` | DC, DR, Mgmt DC, Mgmt DR | Quay mirror admin password |
| `ngc-api-key` | DC, DR | NVIDIA NGC API key |
| `submariner-broker-token` | DR | Submariner broker SA token |
| `odf-dr-s3-access-key` | DR | S3 access key for ODF DR metadata |
| `odf-dr-s3-secret-key` | DR | S3 secret key for ODF DR metadata |
| `acs-central-admin-password` | Mgmt DC | ACS Central initial admin password |
| `acm-s3-access-key` | Mgmt DC, Mgmt DR | S3 access key for ACM Observability |
| `acm-s3-secret-key` | Mgmt DC, Mgmt DR | S3 secret key for ACM Observability |

## Example: Full Deployment Run

![Full Deployment Sequence](../diagrams/pipeline/20-full-deployment-sequence.svg){: .drawio-diagram }

???+ note "Draw.io Source: Full Deployment Sequence"
    [:material-download: Download .drawio file](../diagrams/pipeline/20-full-deployment-sequence.drawio){ .md-button } — Open in [draw.io](https://app.diagrams.net) for interactive editing.

### Steps in ADO UI

1. Navigate to **Pipelines → OpenShift Multi-Cluster Deployment**
2. Click **Run pipeline**
3. Set parameters:

    ![Pipeline Parameters](../images/ado-pipeline-params.png){: .skip-lightbox }

    | Parameter | Value |
    |-----------|-------|
    | Deployment Scope | `all` |
    | Enable Submariner | ✅ |
    | Enable ODF Replication | ✅ |
    | ODF DR Mode | `regional-dr` |
    | Terraform Action | `plan` |
    | Variable Group | `ocp-baremetal-secrets` |

4. Review the plan output in each stage
5. Re-run with **Terraform Action = `apply`** to execute

## Pipeline File

The pipeline definition is at the repository root:

```
azure-pipelines.yml
```

It triggers on changes to any of the four cluster folders:

```yaml
trigger:
  branches:
    include:
      - main
  paths:
    include:
      - openshiftbaremetal/**
      - openshiftbaremetal-dr/**
      - mgmt-dc/**
      - mgmt-dr/**
```
