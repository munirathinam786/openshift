# Author: Sathishkumar Munirathinam

# =============================================================================
# Outputs — UPI DR Secondary
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
  value = "${var.install_dir}/auth/kubeconfig"
}

output "install_dir" {
  value = var.install_dir
}

output "install_method" {
  value = "UPI (User Provisioned Infrastructure)"
}

output "boot_method" {
  value = var.boot_method
}

output "submariner_status" {
  description = "Submariner agent connectivity status"
  value = var.enable_submariner ? {
    enabled          = true
    role             = "agent"
    broker_api_url   = var.submariner_broker_api_url
    cable_driver     = var.submariner_cable_driver
    gateway_count    = var.submariner_gateway_count
    globalnet        = var.submariner_globalnet_enabled
  } : {
    enabled          = false
    role             = "none"
    broker_api_url   = ""
    cable_driver     = ""
    gateway_count    = 0
    globalnet        = false
  }
}

output "odf_dr_status" {
  description = "ODF disaster recovery replication status"
  value = var.enable_odf_dr ? {
    enabled              = true
    mode                 = var.odf_dr_mode
    peer_cluster         = var.odf_dr_peer_cluster_name
    replication_schedule = var.odf_dr_replication_schedule
    s3_bucket            = var.odf_dr_s3_bucket
  } : {
    enabled              = false
    mode                 = ""
    peer_cluster         = ""
    replication_schedule = ""
    s3_bucket            = ""
  }
}
