# DC Primary — variables.tf

Variable definitions for the DC Primary workload cluster. Covers cluster basics, networking, nodes,
GPU, MetalLB, SR-IOV, ODF, OpenShift AI, Submariner broker, and ODF DR.

## Source Code

```hcl
# =============================================================================
# OpenShift Baremetal + OpenShift AI — Terraform Variables
# =============================================================================

# ---- Cluster Basics ----
variable "cluster_name" {
  description = "OpenShift cluster name"
  type        = string
}

variable "base_domain" {
  description = "Base DNS domain (e.g. example.com)"
  type        = string
}

variable "ocp_version" {
  description = "OpenShift version to deploy"
  type        = string
  default     = "4.20"
}

# ---- Networking ----
variable "machine_network_cidr" {
  description = "Machine network CIDR (e.g. 10.142.41.0/24)"
  type        = string
}

variable "cluster_network_cidr" {
  description = "Cluster (pod) network CIDR"
  type        = string
  default     = "10.128.0.0/14"
}

variable "cluster_network_host_prefix" {
  description = "Host prefix for cluster network"
  type        = number
  default     = 23
}

variable "service_network_cidr" {
  description = "Service network CIDR"
  type        = string
  default     = "172.30.0.0/16"
}

variable "api_vip" {
  description = "Virtual IP for the Kubernetes API"
  type        = string
}

variable "ingress_vip" {
  description = "Virtual IP for OpenShift Ingress"
  type        = string
}

variable "dns_servers" {
  description = "List of DNS server IPs"
  type        = list(string)
}

variable "ntp_servers" {
  description = "NTP server addresses"
  type        = list(string)
  default     = ["pool.ntp.org"]
}

variable "gateway" {
  description = "Default gateway IP"
  type        = string
}

# ---- Pull Secret ----
variable "pull_secret_file" {
  description = "Path to the pull-secret.json from console.redhat.com"
  type        = string
}

# ---- SSH ----
variable "ssh_public_key_file" {
  description = "Path to the SSH public key for core user access"
  type        = string
  default     = "~/.ssh/id_ed25519.pub"
}

# ---- Bastion / Provisioner ----
variable "bastion_host" {
  description = "IP or hostname of the bastion/provisioner node"
  type        = string
}

variable "bastion_user" {
  description = "SSH user on bastion (e.g. kni)"
  type        = string
  default     = "kni"
}

variable "bastion_ssh_private_key_file" {
  description = "Path to the SSH private key for bastion access"
  type        = string
  default     = "~/.ssh/id_ed25519"
}

# ---- Bootstrap OS Image ----
variable "bootstrap_os_image_url" {
  description = "HTTP URL to the RHCOS qemu image on the provisioner node"
  type        = string
}

# ---- Master Nodes ----
variable "master_nodes" {
  description = "List of master/control-plane node definitions"
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

# ---- Worker Nodes ----
variable "worker_nodes" {
  description = "List of worker (compute) node definitions"
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

# ---- HAProxy / Load Balancer ----
variable "haproxy_hosts" {
  description = "List of HAProxy LB hosts"
  type = list(object({
    host    = string
    user    = string
    ssh_key = string
  }))
  default = []
}

# ---- Local Quay Mirror Registry (Disconnected) ----
variable "enable_quay_mirror" {
  description = "Enable local Quay mirror registry for disconnected install"
  type        = bool
  default     = false
}

variable "quay_host" {
  description = "IP or FQDN of the local Quay mirror registry server"
  type        = string
  default     = ""
}

variable "quay_port" {
  description = "Port of the local Quay mirror registry"
  type        = number
  default     = 8443
}

variable "quay_admin_user" {
  description = "Admin username for the local Quay registry"
  type        = string
  default     = "quayadmin"
}

variable "quay_admin_password" {
  description = "Admin password for the local Quay registry"
  type        = string
  sensitive   = true
  default     = ""
}

variable "quay_organization" {
  description = "Quay organization/namespace to store mirrored images"
  type        = string
  default     = "ocp4"
}

variable "quay_ca_cert_file" {
  description = "Path to the Quay server CA certificate PEM file"
  type        = string
  default     = ""
}

variable "ocp_channel" {
  description = "OCP update channel for oc-mirror (e.g. stable-4.20)"
  type        = string
  default     = "stable-4.20"
}

variable "mirror_operators" {
  description = "Operators to mirror into local Quay via oc-mirror"
  type = list(object({
    catalog = string
    packages = list(object({
      name    = string
      channel = string
    }))
  }))
  default = [
    {
      catalog = "registry.redhat.io/redhat/redhat-operator-index:v4.20"
      packages = [
        { name = "nfd", channel = "stable" },
        { name = "gpu-operator-certified", channel = "v26.3" },
        { name = "odf-operator", channel = "stable-4.20" },
        { name = "kubernetes-nmstate-operator", channel = "stable" },
        { name = "metallb-operator", channel = "stable" },
        { name = "sriov-network-operator", channel = "stable" },
        { name = "serverless-operator", channel = "stable" },
        { name = "servicemeshoperator", channel = "stable" },
        { name = "kiali-ossm", channel = "stable" },
        { name = "openshift-pipelines-operator-rh", channel = "latest" },
        { name = "rhods-operator", channel = "stable" },
        { name = "cluster-logging", channel = "stable" },
        { name = "elasticsearch-operator", channel = "stable" },
      ]
    },
    {
      catalog = "registry.redhat.io/redhat/certified-operator-index:v4.20"
      packages = [
        { name = "gpu-operator-certified", channel = "v26.3" },
      ]
    },
  ]
}

variable "mirror_registry" {
  description = "Mirror registry URL for disconnected installs (auto-set when enable_quay_mirror=true)"
  type        = string
  default     = ""
}

variable "additional_trust_bundle_file" {
  description = "Path to CA bundle PEM for mirror registry (auto-set when enable_quay_mirror=true)"
  type        = string
  default     = ""
}

# ---- GPU ----
variable "ngc_api_key" {
  description = "NVIDIA NGC API key for pulling vGPU images and NIM models"
  type        = string
  sensitive   = true
  default     = ""
}

variable "nls_token_file" {
  description = "Path to NVIDIA NLS client license token file"
  type        = string
  default     = ""
}

variable "vgpu_driver_version" {
  description = "NVIDIA vGPU guest driver version"
  type        = string
  default     = "560.35.03"
}

variable "vgpu_driver_image" {
  description = "NVIDIA vGPU driver container image name"
  type        = string
  default     = "vgpu-guest-driver-5"
}

variable "gpu_rdma_enabled" {
  description = "Enable GPUDirect RDMA in ClusterPolicy"
  type        = bool
  default     = false
}

# ---- MetalLB ----
variable "enable_metallb" {
  description = "Deploy MetalLB Operator for bare metal load balancing (optional)"
  type        = bool
  default     = false
}

variable "metallb_address_pools" {
  description = "MetalLB IPAddressPool definitions (IP ranges for LoadBalancer services)"
  type = list(object({
    name        = string
    addresses   = list(string)
    auto_assign = optional(bool, true)
  }))
  default = []
}

variable "metallb_l2_advertisements" {
  description = "MetalLB L2Advertisement definitions"
  type = list(object({
    name       = string
    pool_names = list(string)
  }))
  default = []
}

# ---- SR-IOV ----
variable "enable_sriov" {
  description = "Deploy SR-IOV Network Operator for high-performance networking"
  type        = bool
  default     = false
}

variable "sriov_network_devices" {
  description = "SR-IOV network device policies (PF names, VF counts, resource names)"
  type = list(object({
    name          = string
    pf_names      = list(string)
    num_vfs       = number
    resource_name = string
    device_type   = optional(string, "netdevice")
    root_devices  = optional(list(string), [])
  }))
  default = []
}

variable "sriov_networks" {
  description = "SR-IOV network attachment definitions"
  type = list(object({
    name             = string
    resource_name    = string
    target_namespace = string
    vlan             = optional(number, 0)
    ipam             = optional(string, "{}")
  }))
  default = []
}

# ---- Cluster-Wide Entitlement ----
variable "entitlement_pem_file" {
  description = "Path to the Red Hat entitlement PEM certificate file"
  type        = string
  default     = ""
}

# ---- ODF ----
variable "enable_odf" {
  description = "Deploy OpenShift Data Foundation"
  type        = bool
  default     = true
}

variable "odf_storage_capacity" {
  description = "ODF storage capacity (e.g. 2Ti)"
  type        = string
  default     = "2Ti"
}

variable "odf_channel" {
  description = "ODF operator channel"
  type        = string
  default     = "stable-4.20"
}

# ---- OpenShift AI ----
variable "enable_openshift_ai" {
  description = "Deploy Red Hat OpenShift AI"
  type        = bool
  default     = true
}

variable "oai_components" {
  description = "OpenShift AI DataScienceCluster components management state"
  type = object({
    dashboard            = optional(string, "Managed")
    workbenches          = optional(string, "Managed")
    datasciencepipelines = optional(string, "Managed")
    modelmeshserving     = optional(string, "Managed")
    kserve               = optional(string, "Managed")
    codeflare            = optional(string, "Managed")
    ray                  = optional(string, "Managed")
    trustyai             = optional(string, "Managed")
  })
  default = {}
}

variable "enable_nim" {
  description = "Enable NVIDIA NIM model serving integration"
  type        = bool
  default     = false
}

# ---- Service Mesh & Serverless ----
variable "enable_servicemesh" {
  description = "Deploy OpenShift Service Mesh (required for KServe)"
  type        = bool
  default     = true
}

variable "enable_serverless" {
  description = "Deploy OpenShift Serverless (required for KServe)"
  type        = bool
  default     = true
}

# ---- GPU Monitoring ----
variable "enable_gpu_monitoring" {
  description = "Deploy NVIDIA DCGM Exporter dashboard"
  type        = bool
  default     = true
}

# ---- Autoscaler ----
variable "enable_cluster_autoscaler" {
  description = "Deploy Cluster Autoscaler"
  type        = bool
  default     = false
}

variable "autoscaler_max_nodes" {
  description = "Maximum total nodes for cluster autoscaler"
  type        = number
  default     = 24
}

variable "autoscaler_max_gpus" {
  description = "Maximum GPUs for cluster autoscaler"
  type        = number
  default     = 16
}

# ---- etcd Backup ----
variable "enable_etcd_backup" {
  description = "Deploy etcd backup CronJob"
  type        = bool
  default     = true
}

variable "etcd_backup_schedule" {
  description = "Cron schedule for etcd backups"
  type        = string
  default     = "56 23 * * *"
}

# ---- Submariner (Broker — DC Primary) ----
variable "enable_submariner" {
  description = "Enable Submariner broker for DC↔DR connectivity"
  type        = bool
  default     = false
}
variable "submariner_cable_driver" {
  description = "Submariner tunnel driver: libreswan, wireguard, or vxlan"
  type        = string
  default     = "libreswan"
}
variable "submariner_gateway_count" {
  type    = number
  default = 1
}
variable "submariner_globalnet_enabled" {
  description = "Enable Globalnet for overlapping CIDRs"
  type        = bool
  default     = false
}
variable "submariner_gateway_node_labels" {
  type    = map(string)
  default = { "submariner.io/gateway" = "true" }
}

# ---- ODF DR Replication (DC side) ----
variable "enable_odf_dr" {
  description = "Enable ODF disaster recovery replication"
  type        = bool
  default     = false
}
variable "odf_dr_mode" {
  description = "DR mode: regional-dr (async) or metro-dr (sync)"
  type        = string
  default     = "regional-dr"
}
variable "odf_dr_replication_schedule" {
  description = "Cron schedule for async mirroring"
  type        = string
  default     = "*/5 * * * *"
}
variable "odf_dr_peer_cluster_name" {
  description = "Name of the DR cluster for mirroring"
  type        = string
  default     = ""
}
variable "odf_dr_s3_endpoint" {
  type    = string
  default = ""
}
variable "odf_dr_s3_bucket" {
  type    = string
  default = "odf-dr-metadata"
}
variable "odf_dr_s3_access_key" {
  type      = string
  sensitive = true
  default   = ""
}
variable "odf_dr_s3_secret_key" {
  type      = string
  sensitive = true
  default   = ""
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
  default     = "stable-6.2"
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
  default     = "stable-1.6"
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
```
