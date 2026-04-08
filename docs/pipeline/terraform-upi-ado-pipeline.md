# Azure DevOps Pipeline — UPI Deployment

The UPI ADO pipeline provides **phased deployment** for the UPI installation method, with support for multiple boot methods and manual approval gates.

!!! info "UPI Pipeline"
    This pipeline is specific to the **UPI** installation method.
    For the IPI multi-cluster pipeline, see: [ADO Pipeline (IPI)](terraform-ado-pipeline.md)

## ADO Prerequisites

Before creating and running the UPI pipelines, ensure the following are configured in Azure DevOps:

### 1. Self-Hosted Agent Pool

All UPI pipelines use a **self-hosted Linux agent pool** named **`self-hosted-linux`**.

| Requirement | Details |
|---|---|
| Pool Name | `self-hosted-linux` |
| OS | Linux (RHEL 8+/9+ or Ubuntu 20.04+) |
| Network Access | Must reach bastion hosts (SSH), DHCP/TFTP servers (PXE boot), and cluster API endpoints (port 6443) |
| Terraform | Installed automatically by pipeline via `TerraformInstaller@1` task |
| Tools | `oc`, `kubectl`, `jq`, `ssh`, `openshift-install` must be available on the agent |

### 2. Terraform Extension (Marketplace)

Install the **Terraform** extension from the Azure DevOps Marketplace:

| Extension | Publisher | Task Used |
|---|---|---|
| [Terraform](https://marketplace.visualstudio.com/items?itemName=ms-devlabs.custom-terraform-tasks) | Microsoft DevLabs | `TerraformInstaller@1` |

### 3. ADO Variable Groups

See the complete list of variable groups and secret variables in the [IPI Pipeline — ADO Prerequisites](terraform-ado-pipeline.md#ado-prerequisites) section. The UPI pipelines use the same variable groups (with `ocp-baremetal-upi-secrets` and `ocp-upi-day2-secrets` as UPI-specific groups).

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
