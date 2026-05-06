# Azure Red Hat OpenShift (ARO) Terraform Code Reference

<!-- markdownlint-disable MD024 -->

This page explains the Terraform implementation under the repository's `azure-aro/` folder and includes the full source for the top-level Terraform files, the sample `terraform.tfvars`, the Azure DevOps pipeline, and each module entry point.

## Module relationship

![Azure Red Hat OpenShift Terraform Modules](../diagrams/azure-aro/03-azure-aro-terraform-modules.svg){: .drawio-diagram }

???+ note "Draw.io Source: Azure Red Hat OpenShift Terraform Modules"
    [:material-download: Download .drawio file](../diagrams/azure-aro/03-azure-aro-terraform-modules.drawio){ .md-button } — Open in [draw.io](https://app.diagrams.net) for interactive editing.

## Root module structure

```text
azure-aro/
├── main.tf
├── variables.tf
├── outputs.tf
├── versions.tf
├── terraform.tfvars
├── azure-pipelines-aro.yml
└── modules/
    ├── networking/
    ├── identity/
    ├── cluster/
    └── cluster-assets/
```

## `main.tf` orchestration

The root module composes the ARO workflow in four parts:

- `networking` — creates the resource group, VNet, and the two required subnets
- `identity` — creates or reuses a Microsoft Entra service principal and assigns Azure RBAC roles
- `cluster` — provisions the managed ARO cluster resource
- `cluster-assets` — renders preflight, kubeconfig, DNS, delete, and summary files

### Full source

```hcl
provider "azurerm" {
  features {}
}

data "azurerm_client_config" "current" {}

locals {
  assets_dir                = "${path.module}/generated/${var.cluster_name}"
  effective_vnet_name       = trimspace(var.vnet_name) != "" ? var.vnet_name : "${var.cluster_name}-vnet"
  effective_managed_rg_name = trimspace(var.managed_resource_group_name) != "" ? var.managed_resource_group_name : "${var.cluster_name}-managed-rg"
  pull_secret_value         = trimspace(coalesce(var.pull_secret, "")) != "" ? var.pull_secret : (trimspace(var.pull_secret_file) != "" ? file(var.pull_secret_file) : null)
  common_tags               = merge(var.additional_tags, { Name = var.cluster_name, cluster = var.cluster_name, platform = "aro" })
}

resource "null_resource" "assets_dir" {
  triggers = {
    assets_dir = local.assets_dir
  }

  provisioner "local-exec" {
    command = "mkdir -p '${local.assets_dir}'"
  }
}

module "networking" {
  source = "./modules/networking"

  cluster_name              = var.cluster_name
  location                  = var.location
  resource_group_name       = var.resource_group_name
  vnet_name                 = local.effective_vnet_name
  vnet_cidr                 = var.vnet_cidr
  control_plane_subnet_name = var.control_plane_subnet_name
  worker_subnet_name        = var.worker_subnet_name
  control_plane_subnet_cidr = var.control_plane_subnet_cidr
  worker_subnet_cidr        = var.worker_subnet_cidr
  additional_tags           = local.common_tags
}

module "identity" {
  source = "./modules/identity"

  cluster_name                             = var.cluster_name
  resource_group_id                        = module.networking.resource_group_id
  vnet_id                                  = module.networking.vnet_id
  subscription_id                          = data.azurerm_client_config.current.subscription_id
  create_service_principal                 = var.create_service_principal
  existing_service_principal_client_id     = var.existing_service_principal_client_id
  existing_service_principal_client_secret = var.existing_service_principal_client_secret
}

module "cluster" {
  source = "./modules/cluster"

  cluster_name                                 = var.cluster_name
  location                                     = var.location
  resource_group_name                          = module.networking.resource_group_name
  managed_resource_group_name                  = local.effective_managed_rg_name
  cluster_domain                               = var.cluster_domain
  openshift_version                            = var.openshift_version
  pull_secret                                  = local.pull_secret_value
  control_plane_subnet_id                      = module.networking.control_plane_subnet_id
  worker_subnet_id                             = module.networking.worker_subnet_id
  pod_cidr                                     = var.pod_cidr
  service_cidr                                 = var.service_cidr
  api_visibility                               = var.api_visibility
  ingress_visibility                           = var.ingress_visibility
  outbound_type                                = var.outbound_type
  preconfigured_network_security_group_enabled = var.preconfigured_network_security_group_enabled
  fips_enabled                                 = var.fips_enabled
  master_vm_size                               = var.master_vm_size
  master_encryption_at_host_enabled            = var.master_encryption_at_host_enabled
  worker_vm_size                               = var.worker_vm_size
  worker_disk_size_gb                          = var.worker_disk_size_gb
  worker_node_count                            = var.worker_node_count
  worker_encryption_at_host_enabled            = var.worker_encryption_at_host_enabled
  service_principal_client_id                  = module.identity.service_principal_client_id
  service_principal_client_secret              = module.identity.service_principal_client_secret
  tags                                         = local.common_tags

  depends_on = [module.identity]
}

module "cluster_assets" {
  source = "./modules/cluster-assets"

  assets_dir                  = local.assets_dir
  cluster_name                = var.cluster_name
  location                    = var.location
  resource_group_name         = module.networking.resource_group_name
  managed_resource_group_name = local.effective_managed_rg_name
  cluster_domain              = var.cluster_domain
  console_url                 = module.cluster.console_url
  api_server_url              = module.cluster.api_server_url
  api_server_ip               = module.cluster.api_server_ip
  ingress_ip                  = module.cluster.ingress_ip
  dns_zone_name               = var.dns_zone_name
  dns_resource_group_name     = var.dns_resource_group_name
  azure_cli_binary            = var.azure_cli_binary
  oc_binary                   = var.oc_binary
  kubeconfig_path             = var.kubeconfig_path
  auto_fetch_admin_kubeconfig = var.auto_fetch_admin_kubeconfig

  depends_on = [null_resource.assets_dir, module.cluster]
}
```

## `variables.tf`

The ARO variables model Azure-specific concerns such as networking, visibility, cluster sizing, service principal strategy, pull secret input, and DNS helper configuration.

### Full source

```hcl
variable "cluster_name" {
  description = "Short ARO cluster name."
  type        = string
  default     = "aro-prod"

  validation {
    condition     = can(regex("^[a-z0-9-]{3,30}$", var.cluster_name))
    error_message = "cluster_name must be 3-30 characters and contain only lowercase letters, numbers, and hyphens."
  }
}

variable "location" {
  description = "Azure region for the ARO deployment."
  type        = string
  default     = "eastus"
}

variable "resource_group_name" {
  description = "Azure resource group that hosts the ARO cluster resource and network foundation."
  type        = string
  default     = "aro-prod-rg"
}

variable "managed_resource_group_name" {
  description = "Optional managed resource group name created by ARO for cluster-managed Azure resources."
  type        = string
  default     = ""
}

variable "vnet_name" {
  description = "Optional virtual network name. Defaults to <cluster_name>-vnet when empty."
  type        = string
  default     = ""
}

variable "control_plane_subnet_name" {
  description = "Subnet name used by the ARO control plane."
  type        = string
  default     = "control-plane-subnet"
}

variable "worker_subnet_name" {
  description = "Subnet name used by ARO worker nodes."
  type        = string
  default     = "worker-subnet"
}

variable "vnet_cidr" {
  description = "CIDR block for the ARO virtual network."
  type        = string
  default     = "10.90.0.0/22"
}

variable "control_plane_subnet_cidr" {
  description = "CIDR block for the control-plane subnet. Must be /27 or larger."
  type        = string
  default     = "10.90.0.0/23"

  validation {
    condition     = can(cidrhost(var.control_plane_subnet_cidr, 0)) && tonumber(split("/", var.control_plane_subnet_cidr)[1]) <= 27
    error_message = "control_plane_subnet_cidr must be a valid CIDR with a prefix length of /27 or larger."
  }
}

variable "worker_subnet_cidr" {
  description = "CIDR block for the worker subnet. Must be /27 or larger."
  type        = string
  default     = "10.90.2.0/23"

  validation {
    condition     = can(cidrhost(var.worker_subnet_cidr, 0)) && tonumber(split("/", var.worker_subnet_cidr)[1]) <= 27
    error_message = "worker_subnet_cidr must be a valid CIDR with a prefix length of /27 or larger."
  }
}

variable "cluster_domain" {
  description = "Custom domain for the ARO cluster, for example aro.example.com."
  type        = string
  default     = "aro.example.com"

  validation {
    condition     = can(regex("^[a-z0-9.-]+$", var.cluster_domain))
    error_message = "cluster_domain must contain only lowercase letters, numbers, dots, and hyphens."
  }
}

variable "openshift_version" {
  description = "Desired OpenShift version for ARO. Use az aro get-versions --location <region> to confirm availability."
  type        = string
  default     = "4.17.27"
}

variable "pod_cidr" {
  description = "Pod network CIDR used by OpenShift SDN / OVN."
  type        = string
  default     = "10.128.0.0/14"

  validation {
    condition     = can(cidrhost(var.pod_cidr, 0))
    error_message = "pod_cidr must be a valid CIDR block."
  }
}

variable "service_cidr" {
  description = "Service network CIDR used by OpenShift."
  type        = string
  default     = "172.30.0.0/16"

  validation {
    condition     = can(cidrhost(var.service_cidr, 0))
    error_message = "service_cidr must be a valid CIDR block."
  }
}

variable "master_vm_size" {
  description = "VM size used by ARO control-plane nodes."
  type        = string
  default     = "Standard_D8s_v5"
}

variable "worker_vm_size" {
  description = "VM size used by ARO worker nodes."
  type        = string
  default     = "Standard_D4s_v5"
}

variable "worker_disk_size_gb" {
  description = "OS disk size in GB for worker nodes."
  type        = number
  default     = 128
}

variable "worker_node_count" {
  description = "Initial worker node count created with the ARO cluster."
  type        = number
  default     = 3

  validation {
    condition     = var.worker_node_count >= 3 && var.worker_node_count <= 50
    error_message = "worker_node_count must be between 3 and 50 for initial ARO creation."
  }
}

variable "api_visibility" {
  description = "API server visibility. Supported values are Public or Private."
  type        = string
  default     = "Public"

  validation {
    condition     = contains(["Public", "Private"], var.api_visibility)
    error_message = "api_visibility must be either Public or Private."
  }
}

variable "ingress_visibility" {
  description = "Ingress visibility. Supported values are Public or Private."
  type        = string
  default     = "Public"

  validation {
    condition     = contains(["Public", "Private"], var.ingress_visibility)
    error_message = "ingress_visibility must be either Public or Private."
  }
}

variable "outbound_type" {
  description = "ARO outbound routing method. Supported values are LoadBalancer or UserDefinedRouting."
  type        = string
  default     = "LoadBalancer"

  validation {
    condition     = contains(["LoadBalancer", "UserDefinedRouting"], var.outbound_type)
    error_message = "outbound_type must be either LoadBalancer or UserDefinedRouting."
  }
}

variable "preconfigured_network_security_group_enabled" {
  description = "Whether preconfigured NSGs are used on the ARO subnets."
  type        = bool
  default     = false
}

variable "fips_enabled" {
  description = "Whether FIPS validated cryptographic modules are enabled for the cluster."
  type        = bool
  default     = false
}

variable "master_encryption_at_host_enabled" {
  description = "Whether host-based encryption is enabled for control-plane VMs."
  type        = bool
  default     = false
}

variable "worker_encryption_at_host_enabled" {
  description = "Whether host-based encryption is enabled for worker VMs."
  type        = bool
  default     = false
}

variable "pull_secret" {
  description = "Optional Red Hat pull secret content. Prefer secure variables rather than inline values."
  type        = string
  default     = null
  nullable    = true
  sensitive   = true
}

variable "pull_secret_file" {
  description = "Optional path to a local Red Hat pull secret file used when pull_secret is not set."
  type        = string
  default     = ""
}

variable "create_service_principal" {
  description = "If true, Terraform creates a dedicated Microsoft Entra application and service principal for ARO."
  type        = bool
  default     = true
}

variable "existing_service_principal_client_id" {
  description = "Existing service principal client ID used when create_service_principal is false."
  type        = string
  default     = ""

  validation {
    condition     = var.create_service_principal || trimspace(var.existing_service_principal_client_id) != ""
    error_message = "existing_service_principal_client_id must be set when create_service_principal is false."
  }
}

variable "existing_service_principal_client_secret" {
  description = "Existing service principal client secret used when create_service_principal is false."
  type        = string
  default     = ""
  sensitive   = true

  validation {
    condition     = var.create_service_principal || trimspace(var.existing_service_principal_client_secret) != ""
    error_message = "existing_service_principal_client_secret must be set when create_service_principal is false."
  }
}

variable "dns_zone_name" {
  description = "Optional Azure DNS zone name for helper script generation."
  type        = string
  default     = ""
}

variable "dns_resource_group_name" {
  description = "Optional Azure resource group that contains the Azure DNS zone."
  type        = string
  default     = ""
}

variable "azure_cli_binary" {
  description = "Path or command name for the Azure CLI."
  type        = string
  default     = "az"
}

variable "oc_binary" {
  description = "Path or command name for the OpenShift oc CLI."
  type        = string
  default     = "oc"
}

variable "kubeconfig_path" {
  description = "Optional path for the generated admin kubeconfig file. Defaults to the generated assets folder."
  type        = string
  default     = ""
}

variable "auto_fetch_admin_kubeconfig" {
  description = "If true, run the generated preflight and admin kubeconfig helper scripts after cluster creation."
  type        = bool
  default     = false
}

variable "additional_tags" {
  description = "Additional tags applied to Azure resources created by this blueprint."
  type        = map(string)
  default     = {}
}
```

## `outputs.tf`

The outputs expose the Azure resource IDs, cluster connection details, and helper script paths produced by the deployment.

### Full source

```hcl
output "generated_assets_dir" {
  description = "Directory containing the rendered ARO helper scripts and inventories."
  value       = local.assets_dir
}

output "resource_group_name" {
  description = "Azure resource group that hosts the ARO deployment."
  value       = module.networking.resource_group_name
}

output "vnet_id" {
  description = "Azure virtual network ID used by the ARO cluster."
  value       = module.networking.vnet_id
}

output "control_plane_subnet_id" {
  description = "Subnet ID used by ARO control-plane nodes."
  value       = module.networking.control_plane_subnet_id
}

output "worker_subnet_id" {
  description = "Subnet ID used by ARO worker nodes."
  value       = module.networking.worker_subnet_id
}

output "service_principal_client_id" {
  description = "Service principal client ID used by the ARO cluster."
  value       = module.identity.service_principal_client_id
}

output "cluster_id" {
  description = "Resource ID of the Azure Red Hat OpenShift cluster."
  value       = module.cluster.cluster_id
}

output "console_url" {
  description = "ARO web console URL."
  value       = module.cluster.console_url
}

output "api_server_url" {
  description = "ARO API server URL."
  value       = module.cluster.api_server_url
}

output "api_server_ip" {
  description = "ARO API server IP address."
  value       = module.cluster.api_server_ip
}

output "ingress_ip" {
  description = "ARO ingress IP address."
  value       = module.cluster.ingress_ip
}

output "preflight_script" {
  description = "Script that validates Azure CLI prerequisites and provider registration state."
  value       = module.cluster_assets.preflight_script_file
}

output "admin_kubeconfig_script" {
  description = "Script that fetches the admin kubeconfig for the ARO cluster."
  value       = module.cluster_assets.kubeconfig_script_file
}

output "dns_helper_script" {
  description = "Optional helper script for Azure DNS A records once the cluster endpoints are known."
  value       = module.cluster_assets.dns_script_file
}
```

## `versions.tf`

Provider and Terraform version constraints for the ARO blueprint.

### Full source

```hcl
terraform {
  required_version = ">= 1.9.0"

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 4.71"
    }
    azuread = {
      source  = "hashicorp/azuread"
      version = "~> 3.5"
    }
    local = {
      source  = "hashicorp/local"
      version = "~> 2.5"
    }
    null = {
      source  = "hashicorp/null"
      version = "~> 3.2"
    }
    time = {
      source  = "hashicorp/time"
      version = "~> 0.12"
    }
  }
}
```

## `terraform.tfvars`

Sample input values for the ARO deployment, including cluster size, network CIDRs, and the default service principal strategy.

### Full source

```hcl
cluster_name                = "aro-prod"
location                    = "eastus"
resource_group_name         = "aro-prod-rg"
managed_resource_group_name = "aro-prod-managed-rg"
cluster_domain              = "aro.example.com"
openshift_version           = "4.17.27"

vnet_cidr                 = "10.90.0.0/22"
control_plane_subnet_cidr = "10.90.0.0/23"
worker_subnet_cidr        = "10.90.2.0/23"

pod_cidr     = "10.128.0.0/14"
service_cidr = "172.30.0.0/16"

master_vm_size      = "Standard_D8s_v5"
worker_vm_size      = "Standard_D4s_v5"
worker_disk_size_gb = 128
worker_node_count   = 3

api_visibility     = "Public"
ingress_visibility = "Public"
outbound_type      = "LoadBalancer"

create_service_principal = true

# Prefer providing the pull secret through a secure variable or protected file path.
# pull_secret_file = "/secure/path/pull-secret.txt"

# Optional Azure DNS helper configuration.
# dns_zone_name           = "example.com"
# dns_resource_group_name = "shared-dns-rg"

additional_tags = {
  environment = "production"
  workload    = "aro"
}
```

## `azure-pipelines-aro.yml`

Azure DevOps pipeline for validating the ARO Terraform, provisioning the Azure foundation and ARO cluster, and optionally fetching the admin kubeconfig.

### Full source

```yaml
# =============================================================================
# Azure DevOps Pipeline — Azure Red Hat OpenShift (ARO)
# Validates Terraform, provisions the Azure network and ARO cluster, and
# optionally fetches the admin kubeconfig after cluster creation.
# =============================================================================

trigger:
  branches:
    include:
      - develop
  paths:
    include:
      - azure-aro/**
      - docs/azure-aro/**
      - docs/diagrams/azure-aro/**

parameters:
  - name: terraformAction
    displayName: Terraform Action
    type: string
    default: plan
    values:
      - plan
      - apply
      - destroy

  - name: fetchAdminKubeconfig
    displayName: Fetch admin kubeconfig after create
    type: boolean
    default: false

variables:
  - name: TF_IN_AUTOMATION
    value: "true"
  - name: TF_INPUT
    value: "false"
  - name: WORKING_DIR
    value: "azure-aro"

stages:
  - stage: Validate
    displayName: Validate ARO Terraform
    jobs:
      - job: FmtValidate
        pool:
          name: self-hosted-linux
        steps:
          - checkout: self
          - task: TerraformInstaller@1
            inputs:
              terraformVersion: latest
          - script: |
              cd $(WORKING_DIR)
              terraform init -input=false
              terraform fmt -check -recursive
              terraform validate
            displayName: terraform init / fmt / validate
            env:
              ARM_CLIENT_ID: $(azure-client-id)
              ARM_CLIENT_SECRET: $(azure-client-secret)
              ARM_SUBSCRIPTION_ID: $(azure-subscription-id)
              ARM_TENANT_ID: $(azure-tenant-id)
              AZURE_CLIENT_ID: $(azure-client-id)
              AZURE_CLIENT_SECRET: $(azure-client-secret)
              AZURE_SUBSCRIPTION_ID: $(azure-subscription-id)
              AZURE_TENANT_ID: $(azure-tenant-id)

  - stage: Provision
    displayName: Provision Azure foundation and ARO
    dependsOn: Validate
    jobs:
      - job: TerraformApply
        pool:
          name: self-hosted-linux
        steps:
          - checkout: self
          - task: TerraformInstaller@1
            inputs:
              terraformVersion: latest
          - script: |
              cd $(WORKING_DIR)
              terraform init -input=false
              terraform ${{ parameters.terraformAction }} \
                -var-file=terraform.tfvars \
                -var auto_fetch_admin_kubeconfig=${{ lower(parameters.fetchAdminKubeconfig) }} \
                -input=false \
                $(if [ "${{ parameters.terraformAction }}" != "plan" ]; then echo "-auto-approve"; fi)
            displayName: terraform plan/apply/destroy
            env:
              ARM_CLIENT_ID: $(azure-client-id)
              ARM_CLIENT_SECRET: $(azure-client-secret)
              ARM_SUBSCRIPTION_ID: $(azure-subscription-id)
              ARM_TENANT_ID: $(azure-tenant-id)
              AZURE_CLIENT_ID: $(azure-client-id)
              AZURE_CLIENT_SECRET: $(azure-client-secret)
              AZURE_SUBSCRIPTION_ID: $(azure-subscription-id)
              AZURE_TENANT_ID: $(azure-tenant-id)
              TF_VAR_pull_secret: $(aro-pull-secret)

  - stage: Summary
    displayName: ARO summary
    dependsOn: Provision
    condition: always()
    jobs:
      - job: OutputSummary
        pool:
          name: self-hosted-linux
        steps:
          - checkout: none
          - script: |
              echo "ARO Terraform workflow completed."
              echo "Review azure-aro/generated for the preflight, kubeconfig, DNS, and delete helper assets."
              echo "If fetchAdminKubeconfig=false, run the generated helper scripts manually once az login and oc are available."
            displayName: Print summary
```

## `modules/networking`

This module creates the Azure primitives ARO depends on: the resource group, virtual network, required control-plane and worker subnets, and Azure service endpoints for Storage and Container Registry.

### Full source

```hcl
variable "cluster_name" {
  type = string
}

variable "location" {
  type = string
}

variable "resource_group_name" {
  type = string
}

variable "vnet_name" {
  type = string
}

variable "vnet_cidr" {
  type = string
}

variable "control_plane_subnet_name" {
  type = string
}

variable "worker_subnet_name" {
  type = string
}

variable "control_plane_subnet_cidr" {
  type = string
}

variable "worker_subnet_cidr" {
  type = string
}

variable "additional_tags" {
  type = map(string)
}

locals {
  common_tags = merge(var.additional_tags, { module = "networking" })
}

resource "azurerm_resource_group" "this" {
  name     = var.resource_group_name
  location = var.location

  tags = local.common_tags
}

resource "azurerm_virtual_network" "this" {
  name                = var.vnet_name
  location            = azurerm_resource_group.this.location
  resource_group_name = azurerm_resource_group.this.name
  address_space       = [var.vnet_cidr]

  tags = merge(local.common_tags, {
    Name = var.vnet_name
  })
}

resource "azurerm_subnet" "control_plane" {
  name                 = var.control_plane_subnet_name
  resource_group_name  = azurerm_resource_group.this.name
  virtual_network_name = azurerm_virtual_network.this.name
  address_prefixes     = [var.control_plane_subnet_cidr]
  service_endpoints    = ["Microsoft.Storage", "Microsoft.ContainerRegistry"]
}

resource "azurerm_subnet" "worker" {
  name                 = var.worker_subnet_name
  resource_group_name  = azurerm_resource_group.this.name
  virtual_network_name = azurerm_virtual_network.this.name
  address_prefixes     = [var.worker_subnet_cidr]
  service_endpoints    = ["Microsoft.Storage", "Microsoft.ContainerRegistry"]
}

output "resource_group_id" {
  value = azurerm_resource_group.this.id
}

output "resource_group_name" {
  value = azurerm_resource_group.this.name
}

output "vnet_id" {
  value = azurerm_virtual_network.this.id
}

output "vnet_name" {
  value = azurerm_virtual_network.this.name
}

output "control_plane_subnet_id" {
  value = azurerm_subnet.control_plane.id
}

output "worker_subnet_id" {
  value = azurerm_subnet.worker.id
}
```

## `modules/identity`

This module handles the identity boundary ARO needs by creating or reusing a Microsoft Entra service principal and assigning the required Contributor, Network Contributor, and Reader roles.

### Full source

```hcl
variable "cluster_name" {
  type = string
}

variable "resource_group_id" {
  type = string
}

variable "vnet_id" {
  type = string
}

variable "subscription_id" {
  type = string
}

variable "create_service_principal" {
  type = bool
}

variable "existing_service_principal_client_id" {
  type = string
}

variable "existing_service_principal_client_secret" {
  type      = string
  sensitive = true
}

data "azuread_service_principal" "redhatopenshift" {
  client_id = "f1dd0a37-89c6-4e07-bcd1-ffd3d43d8875"
}

resource "time_rotating" "service_principal_secret" {
  count = var.create_service_principal ? 1 : 0

  rotation_days = 730
}

resource "azuread_application" "this" {
  count = var.create_service_principal ? 1 : 0

  display_name = "${var.cluster_name}-aro"
}

resource "azuread_service_principal" "this" {
  count = var.create_service_principal ? 1 : 0

  client_id = azuread_application.this[0].client_id
}

resource "azuread_service_principal_password" "this" {
  count = var.create_service_principal ? 1 : 0

  service_principal_id = azuread_service_principal.this[0].object_id
  end_date             = time_rotating.service_principal_secret[0].rotation_rfc3339
}

data "azuread_service_principal" "existing" {
  count = var.create_service_principal ? 0 : 1

  client_id = var.existing_service_principal_client_id
}

locals {
  service_principal_client_id = var.create_service_principal ? azuread_application.this[0].client_id : data.azuread_service_principal.existing[0].client_id
  service_principal_object_id = var.create_service_principal ? azuread_service_principal.this[0].object_id : data.azuread_service_principal.existing[0].object_id
  service_principal_secret    = var.create_service_principal ? azuread_service_principal_password.this[0].value : var.existing_service_principal_client_secret
}

resource "azurerm_role_assignment" "cluster_rg_contributor" {
  scope                = var.resource_group_id
  role_definition_name = "Contributor"
  principal_id         = local.service_principal_object_id

  skip_service_principal_aad_check = true
}

resource "azurerm_role_assignment" "cluster_vnet_network_contributor" {
  scope                = var.vnet_id
  role_definition_name = "Network Contributor"
  principal_id         = local.service_principal_object_id

  skip_service_principal_aad_check = true
}

resource "azurerm_role_assignment" "aro_rp_vnet_network_contributor" {
  scope                = var.vnet_id
  role_definition_name = "Network Contributor"
  principal_id         = data.azuread_service_principal.redhatopenshift.object_id
}

resource "azurerm_role_assignment" "aro_rp_subscription_reader" {
  scope                = "/subscriptions/${var.subscription_id}"
  role_definition_name = "Reader"
  principal_id         = data.azuread_service_principal.redhatopenshift.object_id
}

output "service_principal_client_id" {
  value = local.service_principal_client_id
}

output "service_principal_object_id" {
  value = local.service_principal_object_id
}

output "service_principal_client_secret" {
  value     = local.service_principal_secret
  sensitive = true
}
```

## `modules/cluster`

This module wraps `azurerm_redhat_openshift_cluster` and captures the main ARO settings such as version, cluster domain, networking, VM profiles, visibility, FIPS, and host-based encryption toggles.

### Full source

```hcl
variable "cluster_name" {
  type = string
}

variable "location" {
  type = string
}

variable "resource_group_name" {
  type = string
}

variable "managed_resource_group_name" {
  type = string
}

variable "cluster_domain" {
  type = string
}

variable "openshift_version" {
  type = string
}

variable "pull_secret" {
  type      = string
  default   = null
  nullable  = true
  sensitive = true
}

variable "control_plane_subnet_id" {
  type = string
}

variable "worker_subnet_id" {
  type = string
}

variable "pod_cidr" {
  type = string
}

variable "service_cidr" {
  type = string
}

variable "api_visibility" {
  type = string
}

variable "ingress_visibility" {
  type = string
}

variable "outbound_type" {
  type = string
}

variable "preconfigured_network_security_group_enabled" {
  type = bool
}

variable "fips_enabled" {
  type = bool
}

variable "master_vm_size" {
  type = string
}

variable "master_encryption_at_host_enabled" {
  type = bool
}

variable "worker_vm_size" {
  type = string
}

variable "worker_disk_size_gb" {
  type = number
}

variable "worker_node_count" {
  type = number
}

variable "worker_encryption_at_host_enabled" {
  type = bool
}

variable "service_principal_client_id" {
  type = string
}

variable "service_principal_client_secret" {
  type      = string
  sensitive = true
}

variable "tags" {
  type = map(string)
}

locals {
  cluster_profile = {
    domain                      = var.cluster_domain
    version                     = var.openshift_version
    managed_resource_group_name = var.managed_resource_group_name
    fips_enabled                = var.fips_enabled
  }
}

resource "azurerm_redhat_openshift_cluster" "this" {
  name                = var.cluster_name
  location            = var.location
  resource_group_name = var.resource_group_name
  tags                = var.tags

  cluster_profile {
    domain                      = local.cluster_profile.domain
    version                     = local.cluster_profile.version
    managed_resource_group_name = local.cluster_profile.managed_resource_group_name
    pull_secret                 = var.pull_secret
    fips_enabled                = local.cluster_profile.fips_enabled
  }

  network_profile {
    pod_cidr                                     = var.pod_cidr
    service_cidr                                 = var.service_cidr
    outbound_type                                = var.outbound_type
    preconfigured_network_security_group_enabled = var.preconfigured_network_security_group_enabled
  }

  main_profile {
    vm_size                    = var.master_vm_size
    subnet_id                  = var.control_plane_subnet_id
    encryption_at_host_enabled = var.master_encryption_at_host_enabled
  }

  api_server_profile {
    visibility = var.api_visibility
  }

  ingress_profile {
    visibility = var.ingress_visibility
  }

  worker_profile {
    vm_size                    = var.worker_vm_size
    subnet_id                  = var.worker_subnet_id
    disk_size_gb               = var.worker_disk_size_gb
    node_count                 = var.worker_node_count
    encryption_at_host_enabled = var.worker_encryption_at_host_enabled
  }

  service_principal {
    client_id     = var.service_principal_client_id
    client_secret = var.service_principal_client_secret
  }

  timeouts {
    create = "120m"
    read   = "10m"
    update = "120m"
    delete = "120m"
  }
}

output "cluster_id" {
  value = azurerm_redhat_openshift_cluster.this.id
}

output "console_url" {
  value = azurerm_redhat_openshift_cluster.this.console_url
}

output "api_server_url" {
  value = azurerm_redhat_openshift_cluster.this.api_server_profile[0].url
}

output "api_server_ip" {
  value = azurerm_redhat_openshift_cluster.this.api_server_profile[0].ip_address
}

output "ingress_ip" {
  value = azurerm_redhat_openshift_cluster.this.ingress_profile[0].ip_address
}
```

## `modules/cluster-assets`

This module renders the operational hand-off files under `azure-aro/generated/<cluster>/`, including preflight, kubeconfig, DNS, delete, and environment summary assets.

### Full source

```hcl
variable "assets_dir" {
  type = string
}

variable "cluster_name" {
  type = string
}

variable "location" {
  type = string
}

variable "resource_group_name" {
  type = string
}

variable "managed_resource_group_name" {
  type = string
}

variable "cluster_domain" {
  type = string
}

variable "console_url" {
  type = string
}

variable "api_server_url" {
  type = string
}

variable "api_server_ip" {
  type = string
}

variable "ingress_ip" {
  type = string
}

variable "dns_zone_name" {
  type = string
}

variable "dns_resource_group_name" {
  type = string
}

variable "azure_cli_binary" {
  type = string
}

variable "oc_binary" {
  type = string
}

variable "kubeconfig_path" {
  type = string
}

variable "auto_fetch_admin_kubeconfig" {
  type = bool
}

locals {
  effective_kubeconfig_path = trimspace(var.kubeconfig_path) != "" ? var.kubeconfig_path : "${var.assets_dir}/kubeconfig"
  dns_enabled               = trimspace(var.dns_zone_name) != "" && trimspace(var.dns_resource_group_name) != ""

  preflight_script = <<-EOT
    #!/usr/bin/env bash
    set -euo pipefail

    for bin in "${var.azure_cli_binary}" "${var.oc_binary}"; do
      command -v "$${bin}" >/dev/null 2>&1 || {
        echo "Required binary not found: $${bin}" >&2
        exit 1
      }
    done

    ${var.azure_cli_binary} account show >/dev/null

    echo "Checking Azure resource provider registration state..."
    ${var.azure_cli_binary} provider show --namespace Microsoft.RedHatOpenShift --query registrationState -o tsv
    ${var.azure_cli_binary} provider show --namespace Microsoft.Compute --query registrationState -o tsv
    ${var.azure_cli_binary} provider show --namespace Microsoft.Storage --query registrationState -o tsv
    ${var.azure_cli_binary} provider show --namespace Microsoft.Authorization --query registrationState -o tsv

    echo "Available ARO versions in ${var.location}:"
    ${var.azure_cli_binary} aro get-versions --location "${var.location}" -o table || true
  EOT

  kubeconfig_script = <<-EOT
    #!/usr/bin/env bash
    set -euo pipefail

    mkdir -p "$(dirname "${local.effective_kubeconfig_path}")"

    ${var.azure_cli_binary} aro get-admin-kubeconfig \
      --resource-group "${var.resource_group_name}" \
      --name "${var.cluster_name}" \
      --file "${local.effective_kubeconfig_path}"

    echo "Kubeconfig written to ${local.effective_kubeconfig_path}"
    echo "Console URL: ${var.console_url}"
    echo "API server : ${var.api_server_url}"
  EOT

  dns_script = <<-EOT
    #!/usr/bin/env bash
    set -euo pipefail

    if [[ -z "${var.dns_zone_name}" || -z "${var.dns_resource_group_name}" ]]; then
      echo "dns_zone_name or dns_resource_group_name is empty; Azure DNS changes are not configured for this cluster."
      exit 0
    fi

    ${var.azure_cli_binary} network dns record-set a create \
      --resource-group "${var.dns_resource_group_name}" \
      --zone-name "${var.dns_zone_name}" \
      --name "api.${var.cluster_domain}" >/dev/null 2>&1 || true

    ${var.azure_cli_binary} network dns record-set a add-record \
      --resource-group "${var.dns_resource_group_name}" \
      --zone-name "${var.dns_zone_name}" \
      --record-set-name "api.${var.cluster_domain}" \
      --ipv4-address "${var.api_server_ip}"

    ${var.azure_cli_binary} network dns record-set a create \
      --resource-group "${var.dns_resource_group_name}" \
      --zone-name "${var.dns_zone_name}" \
      --name "*.apps.${var.cluster_domain}" >/dev/null 2>&1 || true

    ${var.azure_cli_binary} network dns record-set a add-record \
      --resource-group "${var.dns_resource_group_name}" \
      --zone-name "${var.dns_zone_name}" \
      --record-set-name "*.apps.${var.cluster_domain}" \
      --ipv4-address "${var.ingress_ip}"
  EOT

  delete_cluster_script = <<-EOT
    #!/usr/bin/env bash
    set -euo pipefail

    ${var.azure_cli_binary} aro delete \
      --resource-group "${var.resource_group_name}" \
      --name "${var.cluster_name}" \
      --yes
  EOT

  environment_summary = <<-EOT
    # ARO environment summary — ${var.cluster_name}

    - Azure location: `${var.location}`
    - Resource group: `${var.resource_group_name}`
    - Managed resource group: `${var.managed_resource_group_name}`
    - Cluster domain: `${var.cluster_domain}`
    - Console URL: `${var.console_url}`
    - API server URL: `${var.api_server_url}`
    - API server IP: `${var.api_server_ip}`
    - Ingress IP: `${var.ingress_ip}`
    - Azure DNS zone: `${var.dns_zone_name}`
    - Azure DNS resource group: `${var.dns_resource_group_name}`
    - Admin kubeconfig path: `${local.effective_kubeconfig_path}`
  EOT
}

resource "local_file" "preflight" {
  filename = "${var.assets_dir}/aro-preflight-checks.sh"
  content  = local.preflight_script
}

resource "local_file" "kubeconfig" {
  filename = "${var.assets_dir}/get-admin-kubeconfig.sh"
  content  = local.kubeconfig_script
}

resource "local_file" "dns" {
  filename = "${var.assets_dir}/configure-azure-dns-records.sh"
  content  = local.dns_script
}

resource "local_file" "delete_cluster" {
  filename = "${var.assets_dir}/delete-aro-cluster.sh"
  content  = local.delete_cluster_script
}

resource "local_file" "environment_summary" {
  filename = "${var.assets_dir}/aro-environment.md"
  content  = local.environment_summary
}

resource "null_resource" "fetch_admin_kubeconfig" {
  triggers = {
    preflight  = sha256(local.preflight_script)
    kubeconfig = sha256(local.kubeconfig_script)
  }

  provisioner "local-exec" {
    command = var.auto_fetch_admin_kubeconfig ? "chmod +x '${local_file.preflight.filename}' '${local_file.kubeconfig.filename}' && '${local_file.preflight.filename}' && '${local_file.kubeconfig.filename}'" : "echo 'ARO helper assets rendered to ${var.assets_dir}; execution skipped by configuration.'"
  }
}

output "preflight_script_file" {
  value = local_file.preflight.filename
}

output "kubeconfig_script_file" {
  value = local_file.kubeconfig.filename
}

output "dns_script_file" {
  value = local_file.dns.filename
}
```
