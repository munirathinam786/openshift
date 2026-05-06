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
