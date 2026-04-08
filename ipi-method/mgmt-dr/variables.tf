# =============================================================================
# Management Cluster DR — Variables
# =============================================================================

# ---- Cluster Basics ----
variable "cluster_name" {
  type = string
}
variable "base_domain" {
  type = string
}
variable "ocp_version" {
  type    = string
  default = "4.15"
}

# ---- Networking ----
variable "machine_network_cidr" {
  type = string
}
variable "cluster_network_cidr" {
  type    = string
  default = "10.140.0.0/14"
}
variable "cluster_network_host_prefix" {
  type    = number
  default = 23
}
variable "service_network_cidr" {
  type    = string
  default = "172.29.0.0/16"
}
variable "api_vip" {
  type = string
}
variable "ingress_vip" {
  type = string
}
variable "dns_servers" {
  type = list(string)
}
variable "ntp_servers" {
  type    = list(string)
  default = ["pool.ntp.org"]
}
variable "gateway" {
  type = string
}

# ---- Pull Secret & SSH ----
variable "pull_secret_file" {
  type = string
}
variable "ssh_public_key_file" {
  type    = string
  default = "~/.ssh/id_ed25519.pub"
}

# ---- Bastion ----
variable "bastion_host" {
  type = string
}
variable "bastion_user" {
  type    = string
  default = "kni"
}
variable "bastion_ssh_private_key_file" {
  type    = string
  default = "~/.ssh/id_ed25519"
}

# ---- Bootstrap ----
variable "bootstrap_os_image_url" {
  type = string
}

# ---- Nodes ----
variable "master_nodes" {
  type = list(object({
    name             = string
    bmc_address      = string
    bmc_username     = string
    bmc_password     = string
    boot_mac_address = string
    boot_mode        = optional(string, "UEFI")
    root_disk_min_gb = optional(number, 890)
    ip               = string
    bond_interfaces  = optional(list(string), ["ens1f0", "ens1f1"])
  }))
}
variable "worker_nodes" {
  type = list(object({
    name             = string
    bmc_address      = string
    bmc_username     = string
    bmc_password     = string
    boot_mac_address = string
    boot_mode        = optional(string, "UEFI")
    root_disk_min_gb = optional(number, 890)
    ip               = string
    bond_interfaces  = optional(list(string), ["ens1f0", "ens1f1"])
    gpu_worker       = optional(bool, false)
    odf_worker       = optional(bool, false)
  }))
}
variable "haproxy_hosts" {
  type = list(object({
    host    = string
    user    = string
    ssh_key = string
  }))
  default = []
}

# ---- Local Quay Mirror ----
variable "enable_quay_mirror" {
  type    = bool
  default = false
}
variable "quay_host" {
  type    = string
  default = ""
}
variable "quay_port" {
  type    = number
  default = 8443
}
variable "quay_admin_user" {
  type    = string
  default = "quayadmin"
}
variable "quay_admin_password" {
  type      = string
  sensitive = true
  default   = ""
}
variable "quay_organization" {
  type    = string
  default = "ocp4"
}
variable "quay_ca_cert_file" {
  type    = string
  default = ""
}
variable "ocp_channel" {
  type    = string
  default = "stable-4.15"
}
variable "mirror_operators" {
  type = list(object({
    catalog = string
    packages = list(object({
      name    = string
      channel = string
    }))
  }))
  default = []
}
variable "mirror_registry" {
  type    = string
  default = ""
}
variable "additional_trust_bundle_file" {
  type    = string
  default = ""
}

# ---- MetalLB ----
variable "enable_metallb" {
  type    = bool
  default = false
}
variable "metallb_address_pools" {
  type = list(object({
    name        = string
    addresses   = list(string)
    auto_assign = optional(bool, true)
  }))
  default = []
}
variable "metallb_l2_advertisements" {
  type = list(object({
    name       = string
    pool_names = list(string)
  }))
  default = []
}

# ---- ODF ----
variable "enable_odf" {
  type    = bool
  default = true
}
variable "odf_storage_capacity" {
  type    = string
  default = "2Ti"
}
variable "odf_channel" {
  type    = string
  default = "stable-4.16"
}

# ---- ACM (Standby) ----
variable "enable_acm" {
  type    = bool
  default = true
}
variable "acm_channel" {
  type    = string
  default = "release-2.11"
}
variable "acm_instance_name" {
  type    = string
  default = "multiclusterhub"
}
variable "acm_enable_observability" {
  type    = bool
  default = false
}
variable "acm_s3_bucket" {
  type    = string
  default = ""
}
variable "acm_s3_endpoint" {
  type    = string
  default = ""
}
variable "acm_s3_access_key" {
  type      = string
  sensitive = true
  default   = ""
}
variable "acm_s3_secret_key" {
  type      = string
  sensitive = true
  default   = ""
}

# ---- ACS (SecuredCluster only — Central is in mgmt-dc) ----
variable "enable_acs" {
  type    = bool
  default = true
}
variable "acs_channel" {
  type    = string
  default = "stable"
}
variable "acs_central_storage_size" {
  type    = string
  default = "100Gi"
}
variable "acs_central_endpoint" {
  description = "ACS Central endpoint from mgmt-dc (host:port)"
  type        = string
  default     = ""
}

# ---- Quay Enterprise ----
variable "enable_quay_enterprise" {
  type    = bool
  default = true
}
variable "quay_enterprise_channel" {
  type    = string
  default = "stable-3.12"
}
variable "quay_enterprise_instance_name" {
  type    = string
  default = "central-quay"
}
variable "quay_enterprise_storage_size" {
  type    = string
  default = "100Gi"
}
variable "quay_enterprise_components" {
  type = object({
    clair          = optional(string, "managed")
    clairpostgres  = optional(string, "managed")
    objectstorage  = optional(string, "managed")
    postgres       = optional(string, "managed")
    redis          = optional(string, "managed")
    horizontalpodautoscaler = optional(string, "managed")
    mirror         = optional(string, "managed")
    monitoring     = optional(string, "managed")
    route          = optional(string, "managed")
    tls            = optional(string, "managed")
  })
  default = {}
}
variable "quay_enterprise_superuser" {
  type    = string
  default = "quayadmin"
}

# ---- etcd Backup ----
variable "enable_etcd_backup" {
  type    = bool
  default = true
}
variable "etcd_backup_schedule" {
  type    = string
  default = "56 23 * * *"
}

# =============================================================================
# Cluster Logging Variables
# =============================================================================
variable "enable_cluster_logging" {
  description = "Enable dedicated Cluster Logging (ClusterLogging + ClusterLogForwarder)"
  type        = bool
  default     = true
}
variable "logging_channel" {
  description = "OLM subscription channel for Cluster Logging operator"
  type        = string
  default     = "stable-5.9"
}
variable "log_store_type" {
  description = "Log store backend: elasticsearch or lokistack"
  type        = string
  default     = "elasticsearch"
}
variable "log_retention_application" {
  description = "Application log retention period"
  type        = string
  default     = "7d"
}
variable "log_retention_infra" {
  description = "Infrastructure log retention period"
  type        = string
  default     = "7d"
}
variable "log_retention_audit" {
  description = "Audit log retention period"
  type        = string
  default     = "7d"
}
variable "elasticsearch_node_count" {
  description = "Number of Elasticsearch nodes"
  type        = number
  default     = 3
}
variable "log_storage_class" {
  description = "StorageClass for logging PVCs (use ODF: ocs-storagecluster-ceph-rbd)"
  type        = string
  default     = "ocs-storagecluster-ceph-rbd"
}
variable "log_storage_size" {
  description = "PVC size per Elasticsearch node"
  type        = string
  default     = "200Gi"
}
variable "elasticsearch_memory" {
  description = "Memory request per Elasticsearch node"
  type        = string
  default     = "8Gi"
}

# --- S3 Log Forwarding (ODF RGW / NooBaa / MinIO) ---
variable "enable_log_forwarding_s3" {
  description = "Enable forwarding logs to S3-compatible endpoint (ODF-based)"
  type        = bool
  default     = false
}
variable "log_s3_endpoint" {
  description = "S3 endpoint URL for log forwarding (e.g., ODF RGW: https://s3-openshift-storage.apps.<cluster>)"
  type        = string
  default     = ""
}
variable "log_s3_bucket" {
  description = "S3 bucket name for log storage"
  type        = string
  default     = "openshift-logs"
}
variable "log_s3_region" {
  description = "S3 region (use us-east-1 for ODF RGW)"
  type        = string
  default     = "us-east-1"
}
variable "log_s3_access_key" {
  description = "S3 access key for log forwarding"
  type        = string
  sensitive   = true
  default     = ""
}
variable "log_s3_secret_key" {
  description = "S3 secret key for log forwarding"
  type        = string
  sensitive   = true
  default     = ""
}

# =============================================================================
# OADP — Backup & Restore Variables
# =============================================================================
variable "enable_oadp" {
  description = "Enable OADP (OpenShift API for Data Protection) for backup and restore"
  type        = bool
  default     = true
}
variable "oadp_channel" {
  description = "OLM subscription channel for OADP operator"
  type        = string
  default     = "stable-1.4"
}
variable "oadp_dpa_name" {
  description = "DataProtectionApplication CR name"
  type        = string
  default     = "velero-dpa"
}

# --- OADP S3 Backup Storage Location (ODF-based) ---
variable "oadp_s3_endpoint" {
  description = "S3 endpoint URL for OADP backups (e.g., ODF RGW: https://s3-openshift-storage.apps.<cluster>)"
  type        = string
  default     = ""
}
variable "oadp_s3_bucket" {
  description = "S3 bucket name for OADP backups"
  type        = string
  default     = "openshift-backups"
}
variable "oadp_s3_prefix" {
  description = "S3 key prefix (folder) for backup data"
  type        = string
  default     = "velero"
}
variable "oadp_s3_region" {
  description = "S3 region (use us-east-1 for ODF RGW)"
  type        = string
  default     = "us-east-1"
}
variable "oadp_s3_access_key" {
  description = "S3 access key for OADP backups"
  type        = string
  sensitive   = true
  default     = ""
}
variable "oadp_s3_secret_key" {
  description = "S3 secret key for OADP backups"
  type        = string
  sensitive   = true
  default     = ""
}
variable "oadp_s3_insecure_skip_tls" {
  description = "Skip TLS verification for S3 endpoint"
  type        = string
  default     = "false"
}

# --- OADP Backup Schedule ---
variable "enable_backup_schedule" {
  description = "Create a default backup schedule"
  type        = bool
  default     = true
}
variable "backup_schedule_name" {
  description = "Name for the default backup schedule"
  type        = string
  default     = "daily-backup"
}
variable "backup_schedule_cron" {
  description = "Cron expression for backup schedule"
  type        = string
  default     = "0 2 * * *"
}
variable "backup_included_namespaces" {
  description = "Namespaces to include in scheduled backups"
  type        = list(string)
  default     = ["*"]
}
variable "backup_ttl" {
  description = "Backup retention TTL"
  type        = string
  default     = "720h0m0s"
}
variable "backup_volumes_fs" {
  description = "Use filesystem backup for volumes"
  type        = bool
  default     = false
}
variable "backup_csi_snapshot_timeout" {
  description = "Timeout for CSI volume snapshots"
  type        = string
  default     = "10m0s"
}

# =============================================================================
# LDAP / OAuth Identity Provider
# =============================================================================

variable "enable_ldap" {
  description = "Enable LDAP identity provider configuration"
  type        = bool
  default     = false
}
variable "ldap_provider_name" {
  description = "Display name for the LDAP identity provider in OpenShift"
  type        = string
  default     = "LDAP"
}
variable "ldap_url" {
  description = "LDAP URL — ldaps://host:636/baseDN?attr?scope?filter"
  type        = string
  default     = ""
}
variable "ldap_bind_dn" {
  description = "LDAP bind DN (service account for queries)"
  type        = string
  default     = ""
}
variable "ldap_bind_password" {
  description = "LDAP bind password (sensitive — use ADO Variable Group)"
  type        = string
  default     = ""
  sensitive   = true
}
variable "ldap_ca_cert_file" {
  description = "Path to LDAP CA certificate on bastion (empty = use system CAs)"
  type        = string
  default     = ""
}
variable "ldap_insecure" {
  description = "Allow insecure LDAP (only when no CA cert is provided)"
  type        = string
  default     = "false"
}
variable "ldap_attr_id" {
  description = "LDAP attribute for unique identity"
  type        = string
  default     = "dn"
}
variable "ldap_attr_email" {
  description = "LDAP attribute for email"
  type        = string
  default     = "mail"
}
variable "ldap_attr_name" {
  description = "LDAP attribute for display name"
  type        = string
  default     = "cn"
}
variable "ldap_attr_preferred_username" {
  description = "LDAP attribute for login username"
  type        = string
  default     = "sAMAccountName"
}
variable "enable_ldap_group_sync" {
  description = "Deploy CronJob for automatic LDAP group synchronisation"
  type        = bool
  default     = true
}
variable "ldap_user_base_dn" {
  description = "Base DN for LDAP user searches"
  type        = string
  default     = ""
}
variable "ldap_group_base_dn" {
  description = "Base DN for LDAP group searches"
  type        = string
  default     = ""
}
variable "ldap_group_filter" {
  description = "LDAP filter for group queries"
  type        = string
  default     = "(objectClass=group)"
}
variable "ldap_group_membership_attr" {
  description = "LDAP attribute listing group members"
  type        = string
  default     = "member"
}
variable "ldap_group_sync_schedule" {
  description = "Cron schedule for LDAP group sync"
  type        = string
  default     = "*/30 * * * *"
}
variable "ldap_group_role_bindings" {
  description = "Map LDAP groups to OpenShift ClusterRoles"
  type = list(object({
    group_name   = string
    cluster_role = string
  }))
  default = []
}
variable "disable_kubeadmin" {
  description = "Remove kubeadmin secret after LDAP is configured (irreversible)"
  type        = bool
  default     = false
}

# =============================================================================
# OpenShift GitOps (Argo CD) — Day 2
# =============================================================================
variable "enable_openshift_gitops" {
  description = "Deploy OpenShift GitOps (Argo CD) operator and instance"
  type        = bool
  default     = false
}

variable "gitops_channel" {
  description = "OpenShift GitOps operator subscription channel"
  type        = string
  default     = "latest"
}

variable "argocd_ha_enabled" {
  description = "Enable HA for ArgoCD components"
  type        = bool
  default     = false
}

variable "argocd_server_autoscale" {
  description = "Enable autoscaling for ArgoCD server"
  type        = bool
  default     = false
}

variable "argocd_server_cpu_request" {
  description = "CPU request for ArgoCD server"
  type        = string
  default     = "250m"
}

variable "argocd_server_memory_request" {
  description = "Memory request for ArgoCD server"
  type        = string
  default     = "256Mi"
}

variable "argocd_server_cpu_limit" {
  description = "CPU limit for ArgoCD server"
  type        = string
  default     = "500m"
}

variable "argocd_server_memory_limit" {
  description = "Memory limit for ArgoCD server"
  type        = string
  default     = "512Mi"
}

variable "argocd_controller_cpu_request" {
  description = "CPU request for ArgoCD application controller"
  type        = string
  default     = "500m"
}

variable "argocd_controller_memory_request" {
  description = "Memory request for ArgoCD application controller"
  type        = string
  default     = "512Mi"
}

variable "argocd_controller_cpu_limit" {
  description = "CPU limit for ArgoCD application controller"
  type        = string
  default     = "2"
}

variable "argocd_controller_memory_limit" {
  description = "Memory limit for ArgoCD application controller"
  type        = string
  default     = "2Gi"
}

variable "argocd_cluster_admin" {
  description = "Grant cluster-admin to ArgoCD application-controller SA"
  type        = bool
  default     = true
}

variable "argocd_rbac_default_policy" {
  description = "Default RBAC policy for ArgoCD"
  type        = string
  default     = "role:readonly"
}

variable "argocd_rbac_policy" {
  description = "ArgoCD RBAC policy CSV (multi-line)"
  type        = string
  default     = <<-EOT
    g, system:cluster-admins, role:admin
    g, ocp-cluster-admins, role:admin
  EOT
}

variable "argocd_managed_namespaces" {
  description = "List of namespaces managed by ArgoCD"
  type        = list(string)
  default     = []
}

variable "argocd_repo_url" {
  description = "Git repository URL for ArgoCD"
  type        = string
  default     = ""
}

variable "argocd_repo_token" {
  description = "Git PAT / token for ArgoCD repo authentication"
  type        = string
  default     = ""
  sensitive   = true
}

variable "argocd_repo_insecure" {
  description = "Skip TLS verification for the Git repository"
  type        = bool
  default     = false
}

# =============================================================================
# OpenShift Pipelines (Tekton) — Day 2
# =============================================================================
variable "enable_openshift_pipelines" {
  description = "Deploy OpenShift Pipelines (Tekton) operator and configuration"
  type        = bool
  default     = false
}

variable "pipelines_channel" {
  description = "OpenShift Pipelines operator subscription channel"
  type        = string
  default     = "latest"
}

variable "tekton_profile" {
  description = "TektonConfig profile (all, basic, lite)"
  type        = string
  default     = "all"
}

variable "tekton_api_fields" {
  description = "Tekton API fields stability level (stable, beta, alpha)"
  type        = string
  default     = "stable"
}

variable "enable_tekton_cluster_tasks" {
  description = "Install default ClusterTasks"
  type        = bool
  default     = true
}

variable "enable_pipeline_templates" {
  description = "Install pipeline templates"
  type        = bool
  default     = true
}

variable "enable_community_cluster_tasks" {
  description = "Install community ClusterTasks"
  type        = bool
  default     = false
}

variable "enable_pipelines_as_code" {
  description = "Enable Pipelines-as-Code (webhook integration)"
  type        = bool
  default     = true
}

variable "pipeline_default_timeout" {
  description = "Default pipeline run timeout in minutes"
  type        = string
  default     = "60"
}

variable "pipeline_default_sa" {
  description = "Default service account for pipeline runs"
  type        = string
  default     = "pipeline"
}

variable "pipeline_namespaces" {
  description = "List of namespaces for Tekton pipeline workloads"
  type        = list(string)
  default     = []
}

variable "enable_pipeline_resource_limits" {
  description = "Apply LimitRange to the openshift-pipelines namespace"
  type        = bool
  default     = false
}

variable "pipeline_container_cpu_request" {
  description = "Default CPU request for pipeline containers"
  type        = string
  default     = "100m"
}

variable "pipeline_container_memory_request" {
  description = "Default memory request for pipeline containers"
  type        = string
  default     = "256Mi"
}

variable "pipeline_container_cpu_limit" {
  description = "Default CPU limit for pipeline containers"
  type        = string
  default     = "500m"
}

variable "pipeline_container_memory_limit" {
  description = "Default memory limit for pipeline containers"
  type        = string
  default     = "1Gi"
}

variable "pac_webhook_secret" {
  description = "Git provider PAT for Pipelines-as-Code"
  type        = string
  default     = ""
  sensitive   = true
}

variable "pac_webhook_shared_secret" {
  description = "Shared webhook secret for Pipelines-as-Code"
  type        = string
  default     = ""
  sensitive   = true
}

# =============================================================================
# ACM Cluster Import Variables
# =============================================================================

variable "enable_acm_cluster_import" {
  description = "Enable importing workload clusters into ACM Hub"
  type        = bool
  default     = false
}

variable "acm_managed_clusters" {
  description = "List of clusters to import into ACM hub"
  type = list(object({
    name               = string
    api_url            = string
    kubeconfig_path    = string
    cluster_labels     = map(string)
    klusterlet_addons  = optional(object({
      application_manager = optional(bool, true)
      policy_controller   = optional(bool, true)
      search_collector    = optional(bool, true)
      cert_policy         = optional(bool, true)
      iam_policy          = optional(bool, true)
    }), {})
  }))
  default = []
}

variable "acm_cluster_set_name" {
  description = "Name of the ManagedClusterSet for grouping imported clusters"
  type        = string
  default     = ""
}

variable "acm_auto_import_retry" {
  description = "Number of retries for auto-import"
  type        = number
  default     = 2
}

variable "enable_acm_cluster_set" {
  description = "Enable creating ManagedClusterSet"
  type        = bool
  default     = false
}

variable "acm_import_scope" {
  description = "Scope of clusters to import (used by pipeline)"
  type        = string
  default     = "all-workload"
}

# =============================================================================
# ACM DR Application Variables
# =============================================================================

variable "enable_acm_dr_apps" {
  description = "Enable ACM DR application configuration (DRPolicy + DRPlacementControl)"
  type        = bool
  default     = false
}

variable "dr_policy_name" {
  description = "Name of the DRPolicy CR"
  type        = string
  default     = "dr-policy"
}

variable "dr_clusters" {
  description = "List of cluster names in the DR pair"
  type        = list(string)
  default     = []
}

variable "dr_scheduling_interval" {
  description = "Replication scheduling interval (e.g. 5m for async, 0m for sync)"
  type        = string
  default     = "5m"
}

variable "dr_mode" {
  description = "DR mode: regional-dr (async) or metro-dr (sync)"
  type        = string
  default     = "regional-dr"
}

variable "dr_applications" {
  description = "List of applications to protect with DR failover/failback"
  type = list(object({
    name                 = string
    namespace            = string
    placement_name       = string
    preferred_cluster    = string
    failover_cluster     = string
    pvc_selector         = optional(map(string), {})
    kubeobject_protection = optional(bool, false)
    s3_profile_name      = optional(string, "s3-profile")
  }))
  default = []
}

variable "dr_action" {
  description = "DR action to perform: none, failover, failback, or relocate"
  type        = string
  default     = "none"
}

variable "dr_create_placement_rules" {
  description = "Create PlacementRule and Subscription resources for each application"
  type        = bool
  default     = true
}

variable "dr_channel_namespace" {
  description = "Namespace for the ACM application Channel"
  type        = string
  default     = "acm-app-channel"
}

variable "dr_channel_git_url" {
  description = "Git URL for the ACM application Channel"
  type        = string
  default     = ""
}

variable "dr_channel_git_branch" {
  description = "Git branch for the ACM application Channel"
  type        = string
  default     = "main"
}

variable "dr_channel_git_token" {
  description = "Git access token for private ACM application Channel"
  type        = string
  default     = ""
  sensitive   = true
}

# ============================================================================
# Day 2 — New Module Enable Variables
# ============================================================================

# --- Security & Compliance ---
variable "enable_compliance_operator" {
  description = "Enable Compliance Operator (OpenSCAP profiles)"
  type        = bool
  default     = false
}

variable "enable_file_integrity_operator" {
  description = "Enable File Integrity Operator (AIDE)"
  type        = bool
  default     = false
}

variable "enable_cert_manager" {
  description = "Enable cert-manager for TLS certificate lifecycle"
  type        = bool
  default     = false
}

variable "enable_gatekeeper" {
  description = "Enable OPA Gatekeeper policy enforcement"
  type        = bool
  default     = false
}

variable "enable_network_policies" {
  description = "Enable default-deny network policies"
  type        = bool
  default     = false
}

# --- Networking ---
variable "enable_nmstate_operator" {
  description = "Enable NMState Operator for node network configuration"
  type        = bool
  default     = false
}

variable "enable_external_dns" {
  description = "Enable ExternalDNS for automatic DNS records"
  type        = bool
  default     = false
}

variable "enable_ingress_controller" {
  description = "Enable custom Ingress Controller configuration"
  type        = bool
  default     = false
}

variable "enable_multus_networks" {
  description = "Enable Multus secondary network definitions"
  type        = bool
  default     = false
}

variable "enable_network_observability" {
  description = "Enable Network Observability (eBPF flow collection)"
  type        = bool
  default     = false
}

# --- Monitoring & Observability ---
variable "enable_alertmanager_config" {
  description = "Enable custom Alertmanager routing (Slack/PagerDuty/Email)"
  type        = bool
  default     = false
}

variable "enable_custom_grafana" {
  description = "Enable custom Grafana dashboards"
  type        = bool
  default     = false
}

variable "enable_opentelemetry" {
  description = "Enable OpenTelemetry Collector and Tempo"
  type        = bool
  default     = false
}

variable "enable_loki_logging" {
  description = "Enable LokiStack-based log aggregation"
  type        = bool
  default     = false
}

variable "enable_thanos_ruler" {
  description = "Enable Thanos long-term metrics storage"
  type        = bool
  default     = false
}

# --- Cluster Operations ---
variable "enable_node_tuning" {
  description = "Enable custom node tuning profiles"
  type        = bool
  default     = false
}

variable "enable_image_registry" {
  description = "Enable internal image registry configuration"
  type        = bool
  default     = false
}

variable "enable_custom_catalogsource" {
  description = "Enable custom CatalogSource for private operators"
  type        = bool
  default     = false
}

variable "enable_machine_config_pools" {
  description = "Enable custom MachineConfigPools"
  type        = bool
  default     = false
}

variable "enable_node_maintenance" {
  description = "Enable Node Maintenance Operator"
  type        = bool
  default     = false
}

variable "enable_cost_management" {
  description = "Enable Cost Management Metrics Operator"
  type        = bool
  default     = false
}

# --- Developer Experience ---
variable "enable_devspaces" {
  description = "Enable OpenShift Dev Spaces (Eclipse Che)"
  type        = bool
  default     = false
}

variable "enable_web_terminal" {
  description = "Enable Web Terminal Operator"
  type        = bool
  default     = false
}

variable "enable_image_streams" {
  description = "Enable custom image streams"
  type        = bool
  default     = false
}

# --- AI/ML ---
variable "enable_kuberay" {
  description = "Enable KubeRay Operator for Ray clusters"
  type        = bool
  default     = false
}

variable "enable_training_operator" {
  description = "Enable Kubeflow Training Operator"
  type        = bool
  default     = false
}

variable "enable_model_registry" {
  description = "Enable ML Model Registry"
  type        = bool
  default     = false
}

variable "enable_nvidia_nim" {
  description = "Enable NVIDIA NIM inference microservices"
  type        = bool
  default     = false
}

variable "enable_mig_manager" {
  description = "Enable NVIDIA MIG Manager"
  type        = bool
  default     = false
}

# --- Multi-Cluster / DR ---
variable "enable_global_load_balancer" {
  description = "Enable Global Load Balancer (cross-cluster GSLB)"
  type        = bool
  default     = false
}

variable "enable_velero_schedule" {
  description = "Enable Velero backup schedules"
  type        = bool
  default     = false
}

variable "enable_dr_runbook" {
  description = "Enable DR Runbook Automation"
  type        = bool
  default     = false
}

# =============================================================================
# Quay Mirror Replication (Local Quay → Quay Enterprise)
# =============================================================================
variable "enable_quay_mirror_replicate" {
  description = "Enable replication from internet-facing local Quay to on-cluster Quay Enterprise"
  type        = bool
  default     = false
}

variable "quay_enterprise_route" {
  description = "Quay Enterprise route URL (auto-discovered if empty)"
  type        = string
  default     = ""
}

variable "quay_enterprise_password" {
  description = "Quay Enterprise admin password for replication target"
  type        = string
  sensitive   = true
  default     = ""
}

variable "quay_enterprise_mirror_org" {
  description = "Organization in Quay Enterprise for mirrored content"
  type        = string
  default     = "ocp4-mirror"
}
