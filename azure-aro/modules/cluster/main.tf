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
