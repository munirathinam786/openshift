# DR Secondary — outputs.tf

Outputs exposed after deploying the DR Secondary cluster. Includes additional
`submariner_status` and `odf_dr_status` outputs.

## Source Code

```hcl
# =============================================================================
# Outputs — DR Secondary
# =============================================================================

output "cluster_name" {
  value = var.cluster_name
}

output "cluster_domain" {
  value = "${var.cluster_name}.${var.base_domain}"
}

output "api_url" {
  value = "https://api.${var.cluster_name}.${var.base_domain}:6443"
}

output "console_url" {
  value = "https://console-openshift-console.apps.${var.cluster_name}.${var.base_domain}"
}

output "openshift_ai_dashboard_url" {
  value = var.enable_openshift_ai ? "https://rhods-dashboard-redhat-ods-applications.apps.${var.cluster_name}.${var.base_domain}" : ""
}

output "kubeconfig_path" {
  value = module.ocp_baremetal.kubeconfig_path
}

output "install_config_path" {
  value = module.ocp_baremetal.install_config_path
}

output "submariner_status" {
  value = var.enable_submariner ? "agent-connected" : "disabled"
}

output "odf_dr_status" {
  value = var.enable_odf_dr ? "replication-${var.odf_dr_mode}" : "disabled"
}
```
