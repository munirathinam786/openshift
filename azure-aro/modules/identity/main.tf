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
