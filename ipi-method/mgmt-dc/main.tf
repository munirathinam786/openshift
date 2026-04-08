# =============================================================================
# Management Cluster — DC (ACM Hub + ACS Central + Quay Enterprise)
# =============================================================================

locals {
  cluster_domain            = "${var.cluster_name}.${var.base_domain}"
  kubeconfig                = module.ocp_baremetal.kubeconfig_path
  effective_mirror_registry = var.enable_quay_mirror ? "${var.quay_host}:${var.quay_port}/${var.quay_organization}" : var.mirror_registry
  effective_trust_bundle    = var.enable_quay_mirror ? var.quay_ca_cert_file : var.additional_trust_bundle_file
}

# --- DNS Records ---
module "dns" {
  source = "../openshiftbaremetal/modules/dns"

  cluster_name    = var.cluster_name
  base_domain     = var.base_domain
  api_vip         = var.api_vip
  ingress_vip     = var.ingress_vip
  master_nodes    = var.master_nodes
  worker_nodes    = var.worker_nodes
  bastion_host    = var.bastion_host
  bastion_user    = var.bastion_user
  bastion_ssh_key = var.bastion_ssh_private_key_file
  dns_servers     = var.dns_servers
}

# --- HAProxy Load Balancer ---
module "haproxy" {
  source = "../openshiftbaremetal/modules/haproxy"
  count  = length(var.haproxy_hosts) > 0 ? 1 : 0

  cluster_name  = var.cluster_name
  base_domain   = var.base_domain
  api_vip       = var.api_vip
  ingress_vip   = var.ingress_vip
  master_nodes  = var.master_nodes
  worker_nodes  = var.worker_nodes
  haproxy_hosts = var.haproxy_hosts
}

# --- Local Quay Mirror (Disconnected Install) ---
module "quay_mirror" {
  source = "../openshiftbaremetal/modules/quay-mirror"
  count  = var.enable_quay_mirror ? 1 : 0

  bastion_host        = var.bastion_host
  bastion_user        = var.bastion_user
  bastion_ssh_key     = var.bastion_ssh_private_key_file
  quay_host           = var.quay_host
  quay_port           = var.quay_port
  quay_admin_user     = var.quay_admin_user
  quay_admin_password = var.quay_admin_password
  quay_ca_cert_file   = var.quay_ca_cert_file
  quay_organization   = var.quay_organization
  ocp_version         = var.ocp_version
  ocp_channel         = var.ocp_channel
  pull_secret_file    = var.pull_secret_file
  mirror_operators    = var.mirror_operators
}

# --- OCP Baremetal Install ---
module "ocp_baremetal" {
  source = "../openshiftbaremetal/modules/ocp-baremetal"

  cluster_name                 = var.cluster_name
  base_domain                  = var.base_domain
  ocp_version                  = var.ocp_version
  machine_network_cidr         = var.machine_network_cidr
  cluster_network_cidr         = var.cluster_network_cidr
  cluster_network_host_prefix  = var.cluster_network_host_prefix
  service_network_cidr         = var.service_network_cidr
  api_vip                      = var.api_vip
  ingress_vip                  = var.ingress_vip
  dns_servers                  = var.dns_servers
  ntp_servers                  = var.ntp_servers
  gateway                      = var.gateway
  pull_secret_file             = var.pull_secret_file
  ssh_public_key_file          = var.ssh_public_key_file
  bastion_host                 = var.bastion_host
  bastion_user                 = var.bastion_user
  bastion_ssh_key              = var.bastion_ssh_private_key_file
  bootstrap_os_image_url       = var.bootstrap_os_image_url
  master_nodes                 = var.master_nodes
  worker_nodes                 = var.worker_nodes
  mirror_registry              = local.effective_mirror_registry
  additional_trust_bundle_file = local.effective_trust_bundle

  depends_on = [module.dns, module.quay_mirror]
}

# --- OpenShift Data Foundation (for ACM Observability + Quay storage) ---
module "odf_operator" {
  source = "../openshiftbaremetal/modules/odf-operator"
  count  = var.enable_odf ? 1 : 0

  kubeconfig       = local.kubeconfig
  bastion_host     = var.bastion_host
  bastion_user     = var.bastion_user
  bastion_ssh_key  = var.bastion_ssh_private_key_file
  odf_channel      = var.odf_channel
  storage_capacity = var.odf_storage_capacity
  odf_worker_nodes = [for w in var.worker_nodes : w if w.odf_worker]

  depends_on = [module.ocp_baremetal]
}

# --- MetalLB Operator (optional) ---
module "metallb_operator" {
  source = "../openshiftbaremetal/modules/metallb-operator"
  count  = var.enable_metallb ? 1 : 0

  kubeconfig                = local.kubeconfig
  bastion_host              = var.bastion_host
  bastion_user              = var.bastion_user
  bastion_ssh_key           = var.bastion_ssh_private_key_file
  metallb_address_pools     = var.metallb_address_pools
  metallb_l2_advertisements = var.metallb_l2_advertisements

  depends_on = [module.ocp_baremetal]
}

# --- Red Hat Advanced Cluster Management (ACM Hub) ---
module "acm" {
  source = "../openshiftbaremetal/modules/acm"
  count  = var.enable_acm ? 1 : 0

  kubeconfig           = local.kubeconfig
  bastion_host         = var.bastion_host
  bastion_user         = var.bastion_user
  bastion_ssh_key      = var.bastion_ssh_private_key_file
  acm_channel          = var.acm_channel
  acm_instance_name    = var.acm_instance_name
  enable_observability = var.acm_enable_observability
  s3_bucket            = var.acm_s3_bucket
  s3_endpoint          = var.acm_s3_endpoint
  s3_access_key        = var.acm_s3_access_key
  s3_secret_key        = var.acm_s3_secret_key

  depends_on = [module.ocp_baremetal, module.odf_operator]
}

# --- Red Hat Advanced Cluster Security (ACS Central) ---
module "acs" {
  source = "../openshiftbaremetal/modules/acs"
  count  = var.enable_acs ? 1 : 0

  kubeconfig                 = local.kubeconfig
  bastion_host               = var.bastion_host
  bastion_user               = var.bastion_user
  bastion_ssh_key            = var.bastion_ssh_private_key_file
  acs_channel                = var.acs_channel
  acs_central_admin_password = var.acs_central_admin_password
  acs_central_storage_size   = var.acs_central_storage_size
  deploy_central             = true
  deploy_secured_cluster     = true
  cluster_name               = var.cluster_name
  central_endpoint           = ""

  depends_on = [module.ocp_baremetal, module.odf_operator]
}

# --- Red Hat Quay Enterprise Registry ---
module "quay_enterprise" {
  source = "../openshiftbaremetal/modules/quay-enterprise"
  count  = var.enable_quay_enterprise ? 1 : 0

  kubeconfig         = local.kubeconfig
  bastion_host       = var.bastion_host
  bastion_user       = var.bastion_user
  bastion_ssh_key    = var.bastion_ssh_private_key_file
  quay_channel       = var.quay_enterprise_channel
  quay_instance_name = var.quay_enterprise_instance_name
  quay_storage_size  = var.quay_enterprise_storage_size
  quay_components    = var.quay_enterprise_components
  quay_superuser     = var.quay_enterprise_superuser

  depends_on = [module.ocp_baremetal, module.odf_operator]
}

# --- Quay Mirror Replication (Local Quay → Quay Enterprise) ---
module "quay_mirror_replicate" {
  source = "../openshiftbaremetal/modules/quay-mirror-replicate"
  count  = var.enable_quay_enterprise && var.enable_quay_mirror_replicate ? 1 : 0

  kubeconfig              = local.kubeconfig
  bastion_host            = var.bastion_host
  bastion_user            = var.bastion_user
  bastion_ssh_key         = var.bastion_ssh_private_key_file
  source_quay_host        = var.quay_host
  source_quay_port        = var.quay_port
  source_quay_user        = var.quay_admin_user
  source_quay_password    = var.quay_admin_password
  source_quay_organization = var.quay_organization
  dest_quay_route         = var.quay_enterprise_route
  dest_quay_user          = var.quay_enterprise_superuser
  dest_quay_password      = var.quay_enterprise_password
  dest_quay_organization  = var.quay_enterprise_mirror_org
  ocp_version             = var.ocp_version
  mirror_operators        = var.mirror_operators

  depends_on = [module.quay_enterprise, module.quay_mirror]
}

# --- etcd Backup CronJob ---
module "etcd_backup" {
  source = "../openshiftbaremetal/modules/etcd-backup"
  count  = var.enable_etcd_backup ? 1 : 0

  kubeconfig      = local.kubeconfig
  bastion_host    = var.bastion_host
  bastion_user    = var.bastion_user
  bastion_ssh_key = var.bastion_ssh_private_key_file
  backup_schedule = var.etcd_backup_schedule

  depends_on = [module.ocp_baremetal]
}

# --- Cluster Logging (ClusterLogging + ClusterLogForwarder with S3) ---
module "cluster_logging" {
  source = "../openshiftbaremetal/modules/cluster-logging"
  count  = var.enable_cluster_logging ? 1 : 0

  kubeconfig      = local.kubeconfig
  bastion_host    = var.bastion_host
  bastion_user    = var.bastion_user
  bastion_ssh_key = var.bastion_ssh_private_key_file

  logging_channel           = var.logging_channel
  log_store_type            = var.log_store_type
  log_retention_application = var.log_retention_application
  log_retention_infra       = var.log_retention_infra
  log_retention_audit       = var.log_retention_audit
  elasticsearch_node_count  = var.elasticsearch_node_count
  log_storage_class         = var.log_storage_class
  log_storage_size          = var.log_storage_size
  elasticsearch_memory      = var.elasticsearch_memory

  enable_log_forwarding_s3 = var.enable_log_forwarding_s3
  log_s3_endpoint          = var.log_s3_endpoint
  log_s3_bucket            = var.log_s3_bucket
  log_s3_region            = var.log_s3_region
  log_s3_access_key        = var.log_s3_access_key
  log_s3_secret_key        = var.log_s3_secret_key

  depends_on = [module.ocp_baremetal]
}

# --- OADP — Backup & Restore (Velero + S3 BSL) ---
module "oadp" {
  source = "../openshiftbaremetal/modules/oadp"
  count  = var.enable_oadp ? 1 : 0

  kubeconfig      = local.kubeconfig
  bastion_host    = var.bastion_host
  bastion_user    = var.bastion_user
  bastion_ssh_key = var.bastion_ssh_private_key_file

  oadp_channel              = var.oadp_channel
  oadp_dpa_name             = var.oadp_dpa_name
  oadp_s3_endpoint          = var.oadp_s3_endpoint
  oadp_s3_bucket            = var.oadp_s3_bucket
  oadp_s3_prefix            = var.oadp_s3_prefix
  oadp_s3_region            = var.oadp_s3_region
  oadp_s3_access_key        = var.oadp_s3_access_key
  oadp_s3_secret_key        = var.oadp_s3_secret_key
  oadp_s3_insecure_skip_tls = var.oadp_s3_insecure_skip_tls

  enable_backup_schedule      = var.enable_backup_schedule
  backup_schedule_name        = var.backup_schedule_name
  backup_schedule_cron        = var.backup_schedule_cron
  backup_included_namespaces  = var.backup_included_namespaces
  backup_ttl                  = var.backup_ttl
  backup_volumes_fs           = var.backup_volumes_fs
  backup_csi_snapshot_timeout = var.backup_csi_snapshot_timeout

  depends_on = [module.ocp_baremetal]
}

# --- LDAP / OAuth Identity Provider ---
module "ldap_oauth" {
  source = "../openshiftbaremetal/modules/ldap-oauth"
  count  = var.enable_ldap ? 1 : 0

  kubeconfig      = local.kubeconfig
  bastion_host    = var.bastion_host
  bastion_user    = var.bastion_user
  bastion_ssh_key = var.bastion_ssh_private_key_file

  ldap_provider_name           = var.ldap_provider_name
  ldap_url                     = var.ldap_url
  ldap_bind_dn                 = var.ldap_bind_dn
  ldap_bind_password           = var.ldap_bind_password
  ldap_ca_cert_file            = var.ldap_ca_cert_file
  ldap_insecure                = var.ldap_insecure
  ldap_attr_id                 = var.ldap_attr_id
  ldap_attr_email              = var.ldap_attr_email
  ldap_attr_name               = var.ldap_attr_name
  ldap_attr_preferred_username = var.ldap_attr_preferred_username

  enable_ldap_group_sync     = var.enable_ldap_group_sync
  ldap_user_base_dn          = var.ldap_user_base_dn
  ldap_group_base_dn         = var.ldap_group_base_dn
  ldap_group_filter          = var.ldap_group_filter
  ldap_group_membership_attr = var.ldap_group_membership_attr
  ldap_group_sync_schedule   = var.ldap_group_sync_schedule

  ldap_group_role_bindings = var.ldap_group_role_bindings
  disable_kubeadmin        = var.disable_kubeadmin

  depends_on = [module.oadp]
}

# --- OpenShift GitOps (Argo CD) ---
module "openshift_gitops" {
  source = "../openshiftbaremetal/modules/openshift-gitops"
  count  = var.enable_openshift_gitops ? 1 : 0

  kubeconfig      = local.kubeconfig
  bastion_host    = var.bastion_host
  bastion_user    = var.bastion_user
  bastion_ssh_key = var.bastion_ssh_private_key_file

  gitops_channel               = var.gitops_channel
  argocd_ha_enabled            = var.argocd_ha_enabled
  argocd_server_autoscale      = var.argocd_server_autoscale
  argocd_server_cpu_request    = var.argocd_server_cpu_request
  argocd_server_memory_request = var.argocd_server_memory_request
  argocd_server_cpu_limit      = var.argocd_server_cpu_limit
  argocd_server_memory_limit   = var.argocd_server_memory_limit
  argocd_controller_cpu_request    = var.argocd_controller_cpu_request
  argocd_controller_memory_request = var.argocd_controller_memory_request
  argocd_controller_cpu_limit      = var.argocd_controller_cpu_limit
  argocd_controller_memory_limit   = var.argocd_controller_memory_limit
  argocd_cluster_admin         = var.argocd_cluster_admin
  argocd_rbac_default_policy   = var.argocd_rbac_default_policy
  argocd_rbac_policy           = var.argocd_rbac_policy
  argocd_managed_namespaces    = var.argocd_managed_namespaces
  argocd_repo_url              = var.argocd_repo_url
  argocd_repo_token            = var.argocd_repo_token
  argocd_repo_insecure         = var.argocd_repo_insecure

  depends_on = [module.ldap_oauth]
}

# --- OpenShift Pipelines (Tekton) ---
module "openshift_pipelines" {
  source = "../openshiftbaremetal/modules/openshift-pipelines"
  count  = var.enable_openshift_pipelines ? 1 : 0

  kubeconfig      = local.kubeconfig
  bastion_host    = var.bastion_host
  bastion_user    = var.bastion_user
  bastion_ssh_key = var.bastion_ssh_private_key_file

  pipelines_channel              = var.pipelines_channel
  tekton_profile                 = var.tekton_profile
  tekton_api_fields              = var.tekton_api_fields
  enable_cluster_tasks           = var.enable_tekton_cluster_tasks
  enable_pipeline_templates      = var.enable_pipeline_templates
  enable_community_cluster_tasks = var.enable_community_cluster_tasks
  enable_pipelines_as_code       = var.enable_pipelines_as_code
  pipeline_default_timeout       = var.pipeline_default_timeout
  pipeline_default_sa            = var.pipeline_default_sa
  pipeline_namespaces            = var.pipeline_namespaces
  enable_pipeline_resource_limits    = var.enable_pipeline_resource_limits
  pipeline_container_cpu_request     = var.pipeline_container_cpu_request
  pipeline_container_memory_request  = var.pipeline_container_memory_request
  pipeline_container_cpu_limit       = var.pipeline_container_cpu_limit
  pipeline_container_memory_limit    = var.pipeline_container_memory_limit
  pac_webhook_secret             = var.pac_webhook_secret
  pac_webhook_shared_secret      = var.pac_webhook_shared_secret

  depends_on = [module.openshift_gitops]
}

# --- ACM Cluster Import (Import workload clusters into ACM Hub) ---
module "acm_cluster_import" {
  source = "../openshiftbaremetal/modules/acm-cluster-import"
  count  = var.enable_acm_cluster_import ? 1 : 0

  kubeconfig      = local.kubeconfig
  bastion_host    = var.bastion_host
  bastion_user    = var.bastion_user
  bastion_ssh_key = var.bastion_ssh_private_key_file

  managed_clusters = var.acm_managed_clusters
  cluster_set_name = var.enable_acm_cluster_set ? var.acm_cluster_set_name : ""
  auto_import_retry = var.acm_auto_import_retry

  depends_on = [module.acm]
}

# --- ACM DR Applications (DRPolicy + Failover/Failback) ---
module "acm_dr_apps" {
  source = "../openshiftbaremetal/modules/acm-dr-applications"
  count  = var.enable_acm_dr_apps ? 1 : 0

  kubeconfig      = local.kubeconfig
  bastion_host    = var.bastion_host
  bastion_user    = var.bastion_user
  bastion_ssh_key = var.bastion_ssh_private_key_file

  dr_policy_name       = var.dr_policy_name
  dr_clusters          = var.dr_clusters
  scheduling_interval  = var.dr_scheduling_interval
  dr_mode              = var.dr_mode
  dr_applications      = var.dr_applications
  dr_action            = var.dr_action
  create_placement_rules = var.dr_create_placement_rules
  channel_namespace    = var.dr_channel_namespace
  channel_git_url      = var.dr_channel_git_url
  channel_git_branch   = var.dr_channel_git_branch
  channel_git_token    = var.dr_channel_git_token

  depends_on = [module.acm_cluster_import]
}


# ============================================================================
# Day 2 — New Modules
# ============================================================================

# --- Security & Compliance ---
module "compliance_operator" {
  source       = "../openshiftbaremetal/modules/compliance-operator"
  count        = var.enable_compliance_operator ? 1 : 0
  kubeconfig   = local.kubeconfig
  bastion_host = var.bastion_host
  bastion_user = var.bastion_user
  bastion_ssh_key = var.bastion_ssh_private_key_file
}

module "file_integrity_operator" {
  source       = "../openshiftbaremetal/modules/file-integrity-operator"
  count        = var.enable_file_integrity_operator ? 1 : 0
  kubeconfig   = local.kubeconfig
  bastion_host = var.bastion_host
  bastion_user = var.bastion_user
  bastion_ssh_key = var.bastion_ssh_private_key_file
}

module "cert_manager" {
  source       = "../openshiftbaremetal/modules/cert-manager"
  count        = var.enable_cert_manager ? 1 : 0
  kubeconfig   = local.kubeconfig
  bastion_host = var.bastion_host
  bastion_user = var.bastion_user
  bastion_ssh_key = var.bastion_ssh_private_key_file
}

module "gatekeeper" {
  source       = "../openshiftbaremetal/modules/gatekeeper"
  count        = var.enable_gatekeeper ? 1 : 0
  kubeconfig   = local.kubeconfig
  bastion_host = var.bastion_host
  bastion_user = var.bastion_user
  bastion_ssh_key = var.bastion_ssh_private_key_file
}

module "network_policies" {
  source       = "../openshiftbaremetal/modules/network-policies"
  count        = var.enable_network_policies ? 1 : 0
  kubeconfig   = local.kubeconfig
  bastion_host = var.bastion_host
  bastion_user = var.bastion_user
  bastion_ssh_key = var.bastion_ssh_private_key_file
}

# --- Networking ---
module "nmstate_operator" {
  source       = "../openshiftbaremetal/modules/nmstate-operator"
  count        = var.enable_nmstate_operator ? 1 : 0
  kubeconfig   = local.kubeconfig
  bastion_host = var.bastion_host
  bastion_user = var.bastion_user
  bastion_ssh_key = var.bastion_ssh_private_key_file
}

module "external_dns" {
  source       = "../openshiftbaremetal/modules/external-dns"
  count        = var.enable_external_dns ? 1 : 0
  kubeconfig   = local.kubeconfig
  bastion_host = var.bastion_host
  bastion_user = var.bastion_user
  bastion_ssh_key = var.bastion_ssh_private_key_file
}

module "ingress_controller" {
  source       = "../openshiftbaremetal/modules/ingress-controller"
  count        = var.enable_ingress_controller ? 1 : 0
  kubeconfig   = local.kubeconfig
  bastion_host = var.bastion_host
  bastion_user = var.bastion_user
  bastion_ssh_key = var.bastion_ssh_private_key_file
}

module "multus_networks" {
  source       = "../openshiftbaremetal/modules/multus-networks"
  count        = var.enable_multus_networks ? 1 : 0
  kubeconfig   = local.kubeconfig
  bastion_host = var.bastion_host
  bastion_user = var.bastion_user
  bastion_ssh_key = var.bastion_ssh_private_key_file
}

module "network_observability" {
  source       = "../openshiftbaremetal/modules/network-observability"
  count        = var.enable_network_observability ? 1 : 0
  kubeconfig   = local.kubeconfig
  bastion_host = var.bastion_host
  bastion_user = var.bastion_user
  bastion_ssh_key = var.bastion_ssh_private_key_file
}

# --- Monitoring & Observability ---
module "alertmanager_config" {
  source       = "../openshiftbaremetal/modules/alertmanager-config"
  count        = var.enable_alertmanager_config ? 1 : 0
  kubeconfig   = local.kubeconfig
  bastion_host = var.bastion_host
  bastion_user = var.bastion_user
  bastion_ssh_key = var.bastion_ssh_private_key_file
}

module "custom_grafana_dashboards" {
  source       = "../openshiftbaremetal/modules/custom-grafana-dashboards"
  count        = var.enable_custom_grafana ? 1 : 0
  kubeconfig   = local.kubeconfig
  bastion_host = var.bastion_host
  bastion_user = var.bastion_user
  bastion_ssh_key = var.bastion_ssh_private_key_file
}

module "opentelemetry_collector" {
  source       = "../openshiftbaremetal/modules/opentelemetry-collector"
  count        = var.enable_opentelemetry ? 1 : 0
  kubeconfig   = local.kubeconfig
  bastion_host = var.bastion_host
  bastion_user = var.bastion_user
  bastion_ssh_key = var.bastion_ssh_private_key_file
}

module "loki_logging" {
  source       = "../openshiftbaremetal/modules/loki-logging"
  count        = var.enable_loki_logging ? 1 : 0
  kubeconfig   = local.kubeconfig
  bastion_host = var.bastion_host
  bastion_user = var.bastion_user
  bastion_ssh_key = var.bastion_ssh_private_key_file
}

module "thanos_ruler" {
  source       = "../openshiftbaremetal/modules/thanos-ruler"
  count        = var.enable_thanos_ruler ? 1 : 0
  kubeconfig   = local.kubeconfig
  bastion_host = var.bastion_host
  bastion_user = var.bastion_user
  bastion_ssh_key = var.bastion_ssh_private_key_file
  thanos_s3_endpoint   = ""
  thanos_s3_access_key = ""
  thanos_s3_secret_key = ""
}

# --- Cluster Operations ---
module "node_tuning_profiles" {
  source       = "../openshiftbaremetal/modules/node-tuning-profiles"
  count        = var.enable_node_tuning ? 1 : 0
  kubeconfig   = local.kubeconfig
  bastion_host = var.bastion_host
  bastion_user = var.bastion_user
  bastion_ssh_key = var.bastion_ssh_private_key_file
}

module "image_registry" {
  source       = "../openshiftbaremetal/modules/image-registry"
  count        = var.enable_image_registry ? 1 : 0
  kubeconfig   = local.kubeconfig
  bastion_host = var.bastion_host
  bastion_user = var.bastion_user
  bastion_ssh_key = var.bastion_ssh_private_key_file
}

module "custom_catalogsource" {
  source       = "../openshiftbaremetal/modules/custom-catalogsource"
  count        = var.enable_custom_catalogsource ? 1 : 0
  kubeconfig   = local.kubeconfig
  bastion_host = var.bastion_host
  bastion_user = var.bastion_user
  bastion_ssh_key = var.bastion_ssh_private_key_file
}

module "machine_config_pools" {
  source       = "../openshiftbaremetal/modules/machine-config-pools"
  count        = var.enable_machine_config_pools ? 1 : 0
  kubeconfig   = local.kubeconfig
  bastion_host = var.bastion_host
  bastion_user = var.bastion_user
  bastion_ssh_key = var.bastion_ssh_private_key_file
}

module "node_maintenance" {
  source       = "../openshiftbaremetal/modules/node-maintenance"
  count        = var.enable_node_maintenance ? 1 : 0
  kubeconfig   = local.kubeconfig
  bastion_host = var.bastion_host
  bastion_user = var.bastion_user
  bastion_ssh_key = var.bastion_ssh_private_key_file
}

module "cost_management" {
  source       = "../openshiftbaremetal/modules/cost-management"
  count        = var.enable_cost_management ? 1 : 0
  kubeconfig   = local.kubeconfig
  bastion_host = var.bastion_host
  bastion_user = var.bastion_user
  bastion_ssh_key = var.bastion_ssh_private_key_file
}

# --- Developer Experience ---
module "devspaces" {
  source       = "../openshiftbaremetal/modules/devspaces"
  count        = var.enable_devspaces ? 1 : 0
  kubeconfig   = local.kubeconfig
  bastion_host = var.bastion_host
  bastion_user = var.bastion_user
  bastion_ssh_key = var.bastion_ssh_private_key_file
}

module "web_terminal" {
  source       = "../openshiftbaremetal/modules/web-terminal"
  count        = var.enable_web_terminal ? 1 : 0
  kubeconfig   = local.kubeconfig
  bastion_host = var.bastion_host
  bastion_user = var.bastion_user
  bastion_ssh_key = var.bastion_ssh_private_key_file
}

module "image_streams" {
  source       = "../openshiftbaremetal/modules/image-streams"
  count        = var.enable_image_streams ? 1 : 0
  kubeconfig   = local.kubeconfig
  bastion_host = var.bastion_host
  bastion_user = var.bastion_user
  bastion_ssh_key = var.bastion_ssh_private_key_file
}

# --- AI/ML ---
module "kuberay_operator" {
  source       = "../openshiftbaremetal/modules/kuberay-operator"
  count        = var.enable_kuberay ? 1 : 0
  kubeconfig   = local.kubeconfig
  bastion_host = var.bastion_host
  bastion_user = var.bastion_user
  bastion_ssh_key = var.bastion_ssh_private_key_file
}

module "training_operator" {
  source       = "../openshiftbaremetal/modules/training-operator"
  count        = var.enable_training_operator ? 1 : 0
  kubeconfig   = local.kubeconfig
  bastion_host = var.bastion_host
  bastion_user = var.bastion_user
  bastion_ssh_key = var.bastion_ssh_private_key_file
}

module "model_registry" {
  source       = "../openshiftbaremetal/modules/model-registry"
  count        = var.enable_model_registry ? 1 : 0
  kubeconfig   = local.kubeconfig
  bastion_host = var.bastion_host
  bastion_user = var.bastion_user
  bastion_ssh_key = var.bastion_ssh_private_key_file
}

module "nvidia_nim" {
  source       = "../openshiftbaremetal/modules/nvidia-nim"
  count        = var.enable_nvidia_nim ? 1 : 0
  kubeconfig   = local.kubeconfig
  bastion_host = var.bastion_host
  bastion_user = var.bastion_user
  bastion_ssh_key = var.bastion_ssh_private_key_file
  ngc_api_key  = ""
}

module "mig_manager" {
  source       = "../openshiftbaremetal/modules/mig-manager"
  count        = var.enable_mig_manager ? 1 : 0
  kubeconfig   = local.kubeconfig
  bastion_host = var.bastion_host
  bastion_user = var.bastion_user
  bastion_ssh_key = var.bastion_ssh_private_key_file
}

# --- Multi-Cluster / DR ---
module "global_load_balancer" {
  source       = "../openshiftbaremetal/modules/global-load-balancer"
  count        = var.enable_global_load_balancer ? 1 : 0
  kubeconfig   = local.kubeconfig
  bastion_host = var.bastion_host
  bastion_user = var.bastion_user
  bastion_ssh_key = var.bastion_ssh_private_key_file
  gslb_domain              = ""
  gslb_primary_ingress_ip  = ""
  gslb_secondary_ingress_ip = ""
}

module "velero_schedule" {
  source       = "../openshiftbaremetal/modules/velero-schedule"
  count        = var.enable_velero_schedule ? 1 : 0
  kubeconfig   = local.kubeconfig
  bastion_host = var.bastion_host
  bastion_user = var.bastion_user
  bastion_ssh_key = var.bastion_ssh_private_key_file
}

module "dr_runbook_automation" {
  source       = "../openshiftbaremetal/modules/dr-runbook-automation"
  count        = var.enable_dr_runbook ? 1 : 0
  kubeconfig   = local.kubeconfig
  bastion_host = var.bastion_host
  bastion_user = var.bastion_user
  bastion_ssh_key = var.bastion_ssh_private_key_file
  dr_primary_api   = ""
  dr_secondary_api = ""
}
