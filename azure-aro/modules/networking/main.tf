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
