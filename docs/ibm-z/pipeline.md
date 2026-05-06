# IBM Z Pipeline

The file `ibm-z/azure-pipelines-ibm-z.yml` adds an Azure DevOps workflow tailored for the IBM Z Terraform blueprint.

## Purpose

The pipeline is intentionally simpler than the x86 IPI/UPI flows because IBM Z deployments typically separate responsibilities this way:

- Terraform renders cluster assets
- platform automation provisions z/VM guests or operations teams prepare LPARs
- the helper node runs the OpenShift installer

This pipeline is not a placeholder. It runs real Terraform against `ibm-z/`, renders executable IBM Z handoff assets, and can optionally launch the remote installer when the bastion is ready.

## Workflow overview

![IBM Z Deployment Flow](../diagrams/ibm-z/02-ibm-z-deployment-flow.svg){: .drawio-diagram }

???+ note "Draw.io Source: IBM Z Deployment Flow"
    [:material-download: Download .drawio file](../diagrams/ibm-z/02-ibm-z-deployment-flow.drawio){ .md-button } — Open in [draw.io](https://app.diagrams.net) for interactive editing.

## Pipeline stages

| Stage | What it does |
| --- | --- |
| **Validate** | Runs `terraform init`, `terraform fmt -check`, and `terraform validate` |
| **Render_Assets** | Executes Terraform with `terraform.tfvars` and renders IBM Z install assets |
| **Summary** | Prints operator guidance for next steps |

## Parameters

| Parameter | Type | Purpose |
| --- | --- | --- |
| `terraformAction` | string | `plan`, `apply`, or `destroy` |
| `autoProvisionZvm` | boolean | Enables the optional `zvm-guests` module execution |
| `runRemoteInstall` | boolean | Launches the rendered bastion install wrapper |
| `waitForInstall` | boolean | Tells Terraform to wait for install completion on the bastion host |

## Recommended usage pattern

1. Run the pipeline with `terraformAction=plan` and verify all IBM Z variables.
2. Run `apply` with `autoProvisionZvm=true` only if your site automation is connected and approved.
3. Keep `runRemoteInstall=false` for change-controlled environments where Terraform should only render assets and the bastion launch script.
4. Use `runRemoteInstall=true` when the helper node is ready to start the installer remotely.
5. Keep `waitForInstall=false` when install observation should stay interactive, even if `runRemoteInstall=true`.

## Operational notes

- The pipeline watches `ibm-z/**`, `docs/ibm-z/**`, and `docs/diagrams/ibm-z/**`.
- The generated YAML assets land under `ibm-z/generated/` during Terraform execution.
- The bastion host remains the trusted boundary for the OpenShift installer and mirrored payload access.
- The rendered `launch-ibmz-install.sh` script is always available; remote execution is now an explicit opt-in instead of an implied side effect.
