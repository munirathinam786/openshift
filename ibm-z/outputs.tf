output "cluster_domain" {
  description = "Fully qualified OpenShift cluster domain."
  value       = local.cluster_domain
}

output "generated_assets_dir" {
  description = "Local directory containing generated install assets."
  value       = local.assets_dir
}

output "install_config_file" {
  description = "Path to the generated install-config.yaml file."
  value       = module.install_config.install_config_file
}

output "agent_config_file" {
  description = "Path to the generated agent-config.yaml file."
  value       = module.agent_config.agent_config_file
}

output "zvm_guest_manifest_file" {
  description = "Optional z/VM guest manifest generated for site automation."
  value       = try(module.zvm_guests[0].guest_inventory_file, null)
}

output "remote_assets_dir" {
  description = "Remote bastion directory used by openshift-install."
  value       = module.cluster_install.remote_assets_dir
}

output "api_url" {
  description = "Expected Kubernetes API endpoint."
  value       = "https://api.${local.cluster_domain}:6443"
}

output "console_url" {
  description = "Expected OpenShift web console endpoint."
  value       = "https://console-openshift-console.apps.${local.cluster_domain}"
}
