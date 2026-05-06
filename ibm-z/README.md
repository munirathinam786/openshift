# IBM Z Terraform Blueprint

This folder contains an IBM Z / LinuxONE focused Terraform blueprint for deploying Red Hat OpenShift on `s390x` using an agent-based workflow.

## What is included

- `versions.tf` — provider and Terraform constraints
- `variables.tf` — IBM Z, network, bastion, and node inventory inputs
- `main.tf` — root orchestration for install-config, agent-config, z/VM guest provisioning, and cluster install hand-off
- `outputs.tf` — generated asset locations and console/API endpoints
- `terraform.tfvars` — starter values for an IBM Z deployment
- `azure-pipelines-ibm-z.yml` — Azure DevOps pipeline for the IBM Z workflow
- `modules/` — focused submodules for configuration rendering and install orchestration

## Deployment model

The implementation assumes:

1. OpenShift is installed with the **agent-based installer**.
2. Control plane and worker nodes are `s390x` systems running either as **z/VM guests** or **LPARs**.
3. A bastion host has access to the OpenShift installer, pull secret, mirrored release payload, and SSH connectivity to IBM Z management endpoints.
4. Disconnected environments use a mirrored registry via `imageDigestSources`.

## Notes

- This blueprint intentionally avoids x86-specific features such as GPU operators, BMC-driven IPI flows, and bare-metal Redfish provisioning.
- Optional z/VM guest provisioning is implemented as a Terraform-assisted shell hand-off so teams can plug in their site-specific automation.
- Local repository documentation preview is standardized on Podman; from the repo root use `podman compose up -d --build`.
