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
