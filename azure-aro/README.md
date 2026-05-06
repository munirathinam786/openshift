# Azure Red Hat OpenShift (ARO) Terraform Blueprint

This folder contains a Terraform-driven blueprint for deploying **Azure Red Hat OpenShift (ARO)** with the Azure network foundation, required Microsoft Entra service principal and role assignments, the managed ARO cluster resource, and post-deployment helper assets.

## What is included

- `versions.tf` — Terraform and provider constraints for AzureRM, AzureAD, local files, and helper execution
- `variables.tf` — ARO, Azure networking, visibility, DNS, and automation inputs
- `terraform.tfvars` — starter values for a production-style ARO deployment
- `main.tf` — root orchestration across networking, identity, cluster provisioning, and generated helper assets
- `outputs.tf` — cluster IDs, console and API details, subnet IDs, and generated asset references
- `azure-pipelines-aro.yml` — Azure DevOps workflow for validation and optional execution of post-create helper assets
- `modules/networking` — resource group, virtual network, and control-plane / worker subnet creation
- `modules/identity` — Microsoft Entra application, service principal, and RBAC assignments for ARO
- `modules/cluster` — `azurerm_redhat_openshift_cluster` resource and related outputs
- `modules/cluster-assets` — generated preflight, kubeconfig, DNS, and delete helper assets

## Deployment model

The implementation assumes:

1. Terraform owns the **resource group**, **virtual network**, and the two empty subnets required by ARO.
2. Terraform creates a **dedicated Microsoft Entra application and service principal** by default, then grants it the Contributor and Network Contributor permissions required by ARO.
3. Terraform also assigns **Network Contributor** on the VNet to the Azure Red Hat OpenShift resource provider service principal.
4. A command runner host or pipeline agent has `az` and `oc` available when executing the generated helper scripts.
5. Optional Azure DNS helper assets are rendered when you provide a DNS zone name and resource group.

## Notes

- ARO requires the Azure resource providers `Microsoft.RedHatOpenShift`, `Microsoft.Compute`, `Microsoft.Storage`, and `Microsoft.Authorization` to be registered in the target subscription.
- ARO requires at least **44 vCPUs** of quota during installation and two empty subnets sized at **/27 or larger**.
- The default Terraform path creates the cluster directly with the AzureRM provider rather than shelling out to the Azure CLI for cluster provisioning.
- If you provide a pull secret, keep it out of Git and inject it through secure variables or a protected local file.
