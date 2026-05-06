# IBM Z Pipeline

The file `ibm-z/azure-pipelines-ibm-z.yml` adds an Azure DevOps workflow tailored for the IBM Z Terraform blueprint.

## Purpose

The pipeline is intentionally simpler than the x86 IPI/UPI flows because IBM Z deployments typically separate responsibilities this way:

- Terraform renders cluster assets
- platform automation provisions z/VM guests or operations teams prepare LPARs
- the helper node runs the OpenShift installer

## Workflow overview

![IBM Z Deployment Flow](../diagrams/ibm-z/02-ibm-z-deployment-flow.svg){: .drawio-diagram }

???+ note "Draw.io Source: IBM Z Deployment Flow"
    [:material-download: Download .drawio file](../diagrams/ibm-z/02-ibm-z-deployment-flow.drawio){ .md-button } — Open in [draw.io](https://app.diagrams.net) for interactive editing.

## Pipeline stages

| Stage | What it does |
|---|---|
| **Validate** | Runs `terraform init`, `terraform fmt -check`, and `terraform validate` |
| **Render_Assets** | Executes Terraform with `terraform.tfvars` and renders IBM Z install assets |
| **Summary** | Prints operator guidance for next steps |

## Parameters

| Parameter | Type | Purpose |
|---|---|---|
| `terraformAction` | string | `plan`, `apply`, or `destroy` |
| `autoProvisionZvm` | boolean | Enables the optional `zvm-guests` module execution |
| `waitForInstall` | boolean | Tells Terraform to wait for install completion on the bastion host |

## Recommended usage pattern

1. Run the pipeline with `terraformAction=plan` and verify all IBM Z variables.
2. Run `apply` with `autoProvisionZvm=true` only if your site automation is connected and approved.
3. Keep `waitForInstall=false` for change-controlled environments where install observation happens interactively.
4. Use `waitForInstall=true` for lower-touch lab or pre-production environments.

## Operational notes

- The pipeline watches `ibm-z/**`, `docs/ibm-z/**`, and `docs/diagrams/ibm-z/**`.
- The generated YAML assets land under `ibm-z/generated/` during Terraform execution.
- The bastion host remains the trusted boundary for the OpenShift installer and mirrored payload access.
