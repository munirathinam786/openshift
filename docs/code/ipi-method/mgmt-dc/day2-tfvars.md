# day2-terraform.tfvars — IPI Management DC

Day 2 post-install configuration for the **IPI Management DC** cluster. Applied separately from Day 1:

```bash
terraform apply -var-file=terraform.tfvars -var-file=day2-terraform.tfvars
```

## Day 2 Operations

| Feature | Variable | Default |
|---|---|---|
| Cluster Logging | `enable_cluster_logging` | `true` |
| OADP Backup | `enable_oadp` | `true` |
| LDAP/OAuth | `enable_ldap` | `true` |
| OpenShift GitOps | `enable_openshift_gitops` | `true` |
| OpenShift Pipelines | `enable_openshift_pipelines` | `true` |

## Source Code

```hcl
# =============================================================================
# Day 2 Operations — Post-Install Configuration
# Apply separately: terraform apply -var-file=day2-terraform.tfvars
# =============================================================================

# =============================================================================
# Cluster Logging
# =============================================================================
enable_cluster_logging    = true
logging_channel           = "stable-5.9"
log_store_type            = "elasticsearch"
log_retention_application = "7d"
log_retention_infra       = "7d"
log_retention_audit       = "7d"
elasticsearch_node_count  = 3
log_storage_class         = "ocs-storagecluster-ceph-rbd"
log_storage_size          = "200Gi"
elasticsearch_memory      = "8Gi"

# S3 Log Forwarding (ODF-based — update endpoint per cluster)
enable_log_forwarding_s3  = true
log_s3_endpoint           = "https://s3-openshift-storage.apps.<cluster_domain>"   # ODF RGW endpoint
log_s3_bucket             = "openshift-logs"
log_s3_region             = "us-east-1"
log_s3_access_key         = ""   # Provide via ADO Variable Group or env var
log_s3_secret_key         = ""   # Provide via ADO Variable Group or env var

# =============================================================================
# OADP — Backup & Restore
# =============================================================================
enable_oadp               = true
oadp_channel              = "stable-1.4"
oadp_dpa_name             = "velero-dpa"

# OADP S3 Backup Storage Location (ODF-based — update endpoint per cluster)
oadp_s3_endpoint          = "https://s3-openshift-storage.apps.<cluster_domain>"   # ODF RGW endpoint
oadp_s3_bucket            = "openshift-backups"
oadp_s3_prefix            = "velero"
oadp_s3_region            = "us-east-1"
oadp_s3_access_key        = ""   # Provide via ADO Variable Group or env var
oadp_s3_secret_key        = ""   # Provide via ADO Variable Group or env var
oadp_s3_insecure_skip_tls = "false"

# OADP Backup Schedule
enable_backup_schedule     = true
backup_schedule_name       = "daily-backup"
backup_schedule_cron       = "0 2 * * *"
backup_included_namespaces = ["*"]
backup_ttl                 = "720h0m0s"
backup_volumes_fs          = false
backup_csi_snapshot_timeout = "10m0s"

# =============================================================================
# LDAP / OAuth Identity Provider
# =============================================================================
enable_ldap                  = true
ldap_provider_name           = "Corporate-LDAP"
ldap_url                     = "ldaps://ldap.example.com:636/dc=example,dc=com?sAMAccountName?sub?(objectClass=person)"
ldap_bind_dn                 = "CN=svc-openshift,OU=ServiceAccounts,DC=example,DC=com"
ldap_bind_password           = "REPLACE_LDAP_BIND_PASSWORD"
ldap_ca_cert_file            = "/home/kni/ldap-certs/ldap-ca.pem"
ldap_insecure                = "false"
ldap_attr_id                 = "dn"
ldap_attr_email              = "mail"
ldap_attr_name               = "cn"
ldap_attr_preferred_username = "sAMAccountName"

# ---- LDAP Group Sync ----
enable_ldap_group_sync     = true
ldap_user_base_dn          = "OU=Users,DC=example,DC=com"
ldap_group_base_dn         = "OU=OpenShift,OU=Groups,DC=example,DC=com"
ldap_group_filter          = "(objectClass=group)"
ldap_group_membership_attr = "member"
ldap_group_sync_schedule   = "*/30 * * * *"

# ---- RBAC — LDAP Group to ClusterRole Mappings ----
ldap_group_role_bindings = [
  { group_name = "ocp-cluster-admins",  cluster_role = "cluster-admin" },
  { group_name = "ocp-developers",      cluster_role = "edit" },
  { group_name = "ocp-viewers",         cluster_role = "view" },
]

disable_kubeadmin = false

# =============================================================================
# OpenShift GitOps (Argo CD)
# =============================================================================
enable_openshift_gitops       = true
gitops_channel                = "latest"
argocd_ha_enabled             = false
argocd_server_autoscale       = false
argocd_server_cpu_request     = "250m"
argocd_server_memory_request  = "256Mi"
argocd_server_cpu_limit       = "500m"
argocd_server_memory_limit    = "512Mi"
argocd_controller_cpu_request     = "500m"
argocd_controller_memory_request  = "512Mi"
argocd_controller_cpu_limit       = "2"
argocd_controller_memory_limit    = "2Gi"
argocd_cluster_admin          = true
argocd_rbac_default_policy    = "role:readonly"
argocd_rbac_policy            = "g, system:cluster-admins, role:admin\ng, ocp-cluster-admins, role:admin"
argocd_managed_namespaces     = []
argocd_repo_url               = ""         # Set to your GitOps repo URL
argocd_repo_token             = ""         # Provide via ADO Variable Group or env var
argocd_repo_insecure          = false

# =============================================================================
# OpenShift Pipelines (Tekton)
# =============================================================================
enable_openshift_pipelines         = true
pipelines_channel                  = "latest"
tekton_profile                     = "all"
tekton_api_fields                  = "stable"
enable_tekton_cluster_tasks        = true
enable_pipeline_templates          = true
enable_community_cluster_tasks     = false
enable_pipelines_as_code           = true
pipeline_default_timeout           = "60"
pipeline_default_sa                = "pipeline"
pipeline_namespaces                = []
enable_pipeline_resource_limits    = false
pipeline_container_cpu_request     = "100m"
pipeline_container_memory_request  = "256Mi"
pipeline_container_cpu_limit       = "500m"
pipeline_container_memory_limit    = "1Gi"
pac_webhook_secret                 = ""    # Provide via ADO Variable Group or env var
pac_webhook_shared_secret          = ""    # Provide via ADO Variable Group or env var

# ============================================================================
# Day 2 — New Module Defaults (all disabled by default, enable via pipeline)
# ============================================================================

# Security & Compliance
enable_compliance_operator      = false
enable_file_integrity_operator  = false
enable_cert_manager             = false
enable_gatekeeper               = false
enable_network_policies         = false

# Networking
enable_nmstate_operator         = false
enable_external_dns             = false
enable_ingress_controller       = false
enable_multus_networks          = false
enable_network_observability    = false

# Monitoring & Observability
enable_alertmanager_config      = false
enable_custom_grafana           = false
enable_opentelemetry            = false
enable_loki_logging             = false
enable_thanos_ruler             = false

# Cluster Operations
enable_node_tuning              = false
enable_image_registry           = false
enable_custom_catalogsource     = false
enable_machine_config_pools     = false
enable_node_maintenance         = false
enable_cost_management          = false

# Developer Experience
enable_devspaces                = false
enable_web_terminal             = false
enable_image_streams            = false

# AI/ML
enable_kuberay                  = false
enable_training_operator        = false
enable_model_registry           = false
enable_nvidia_nim               = false
enable_mig_manager              = false

# Multi-Cluster / DR
enable_global_load_balancer     = false
enable_velero_schedule          = false
enable_dr_runbook               = false

# ============================================================================
# Day 2 — New Module Defaults (all disabled by default, enable via pipeline)
# ============================================================================

# Security & Compliance
enable_compliance_operator      = false
enable_file_integrity_operator  = false
enable_cert_manager             = false
enable_gatekeeper               = false
enable_network_policies         = false

# Networking
enable_nmstate_operator         = false
enable_external_dns             = false
enable_ingress_controller       = false
enable_multus_networks          = false
enable_network_observability    = false

# Monitoring & Observability
enable_alertmanager_config      = false
enable_custom_grafana           = false
enable_opentelemetry            = false
enable_loki_logging             = false
enable_thanos_ruler             = false

# Cluster Operations
enable_node_tuning              = false
enable_image_registry           = false
enable_custom_catalogsource     = false
enable_machine_config_pools     = false
enable_node_maintenance         = false
enable_cost_management          = false

# Developer Experience
enable_devspaces                = false
enable_web_terminal             = false
enable_image_streams            = false

# AI/ML
enable_kuberay                  = false
enable_training_operator        = false
enable_model_registry           = false
enable_nvidia_nim               = false
enable_mig_manager              = false

# Multi-Cluster / DR
enable_global_load_balancer     = false
enable_velero_schedule          = false
enable_dr_runbook               = false

# =============================================================================
# Quay Mirror Replication (Local Quay → Quay Enterprise)
# =============================================================================
enable_quay_mirror_replicate = false
quay_enterprise_route        = ""
quay_enterprise_password     = ""
quay_enterprise_mirror_org   = "ocp4-mirror"

# =============================================================================
# Quay Mirror Replication (Local Quay → Quay Enterprise)
# =============================================================================
enable_quay_mirror_replicate = false
quay_enterprise_route        = ""
quay_enterprise_password     = ""
quay_enterprise_mirror_org   = "ocp4-mirror"
```
