# =============================================================================
# Outputs — Management Cluster DC
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
  value = module.ocp_baremetal.kubeconfig_path
}
