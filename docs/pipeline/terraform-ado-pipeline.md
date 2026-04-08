# Azure DevOps Pipeline — Multi-Cluster Deployment

The ADO pipeline provides **selective deployment** of any combination of the four cluster environments with optional Submariner networking and ODF DR replication.

!!! info "Multi-Cluster Architecture"
    See also:
    [Multi-Cluster Overview](../architecture/terraform-multi-cluster-overview.md) |
    [DC Primary](../clusters/terraform-ocp-baremetal.md) |
    [DR Secondary](../clusters/terraform-dr-secondary.md) |
    [Management DC](../clusters/terraform-mgmt-dc.md) |
    [Management DR](../clusters/terraform-mgmt-dr.md)

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
