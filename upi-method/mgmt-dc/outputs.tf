# Author: Sathishkumar Munirathinam

# =============================================================================
# Outputs — Management Cluster DC (UPI)
# =============================================================================

output "cluster_name" {
  value = var.cluster_name
}

output "cluster_domain" {
  value = local.cluster_domain
}

output "api_url" {
  value = "https://api.${local.cluster_domain}:6443"
}

output "console_url" {
  value = "https://console-openshift-console.apps.${local.cluster_domain}"
}

output "install_method" {
  value = "UPI"
}

output "boot_method" {
  value = var.boot_method
}

output "install_dir" {
  value = var.install_dir
}

output "acm_console_url" {
  value = var.enable_acm ? "https://multicloud-console.apps.${local.cluster_domain}" : ""
}

output "acs_central_url" {
  value = var.enable_acs ? "https://central-stackrox.apps.${local.cluster_domain}" : ""
}

output "quay_enterprise_url" {
  value = var.enable_quay_enterprise ? "https://${var.quay_enterprise_instance_name}-quay-enterprise.apps.${local.cluster_domain}" : ""
}

output "kubeconfig_path" {
  value = local.kubeconfig
}
