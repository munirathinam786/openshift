# Azure DevOps Pipeline — UPI Deployment

The UPI ADO pipeline provides **phased deployment** for the UPI installation method, with support for multiple boot methods and manual approval gates.

!!! info "UPI Pipeline"
    This pipeline is specific to the **UPI** installation method.
    For the IPI multi-cluster pipeline, see: [ADO Pipeline (IPI)](terraform-ado-pipeline.md)

## Pipeline Parameters

![UPI Pipeline Parameters](../diagrams/pipeline/07-upi-pipeline-parameters.svg){: .drawio-diagram }

???+ note "Draw.io Source: UPI Pipeline Parameters"
    [:material-download: Download .drawio file](../diagrams/pipeline/07-upi-pipeline-parameters.drawio){ .md-button } — Open in [draw.io](https://app.diagrams.net) for interactive editing.

### Boot Methods

| Method | Description | Automation Level |
|--------|-------------|-----------------|
| `pxe` | Automated PXE boot via DHCP+TFTP from bastion | Fully automated |
| `iso` | RHCOS ISO with embedded ignition URL | Semi-automated (mount ISO) |
| `manual` | Operator boots nodes outside Terraform | Manual with pipeline gates |

### Deployment Phases

![UPI Phase Selection](../diagrams/pipeline/08-upi-phase-selection.svg){: .drawio-diagram }

???+ note "Draw.io Source: UPI Phase Selection"
    [:material-download: Download .drawio file](../diagrams/pipeline/08-upi-phase-selection.drawio){ .md-button } — Open in [draw.io](https://app.diagrams.net) for interactive editing.

| Phase | Deploys | Use Case |
|-------|---------|----------|
| `prerequisites` | DNS + HAProxy + Quay Mirror | Infrastructure setup before install |
| `ignition` | install-config + ignition configs | Generate boot configs |
| `bootstrap` | Bootstrap + control plane nodes | Initial cluster bootstrap |
| `compute` | Worker nodes + CSR approval | Add compute capacity |
| `day2-operators` | GPU, ODF, AI, monitoring | Post-install operators |
| `full` | All phases sequentially | Complete end-to-end deployment |

## Stage Execution Order

![UPI Pipeline Stage Execution](../diagrams/pipeline/09-upi-pipeline-stages.svg){: .drawio-diagram }

???+ note "Draw.io Source: UPI Pipeline Stage Execution"
    [:material-download: Download .drawio file](../diagrams/pipeline/09-upi-pipeline-stages.drawio){ .md-button } — Open in [draw.io](https://app.diagrams.net) for interactive editing.

## Manual Boot Gate

When `bootMethod = manual`, the Bootstrap stage includes a **ManualValidation** task:

![Upi Boot Gate](../diagrams/pipeline/26-upi-boot-gate.svg){: .drawio-diagram }

???+ note "Draw.io Source: Upi Boot Gate"
    [:material-download: Download .drawio file](../diagrams/pipeline/26-upi-boot-gate.drawio){ .md-button } — Open in [draw.io](https://app.diagrams.net) for interactive editing.

## Secrets (ADO Variable Group)

The pipeline expects these secrets in the `ocp-baremetal-upi-secrets` variable group:

| Secret | Used By |
|--------|---------|
| `quay-admin-password` | Quay mirror registry |
| `ngc-api-key` | NVIDIA GPU Operator |
| `odf-dr-s3-access-key` | ODF DR replication |
| `odf-dr-s3-secret-key` | ODF DR replication |

## Source Code

See the full pipeline YAML in the Terraform Code section:
[azure-pipelines-upi.yml](../code/upi-method/azure-pipelines-upi.md)
