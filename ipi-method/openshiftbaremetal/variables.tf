# Author: Sathishkumar Munirathinam

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
  default     = "580.126.20"
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
# Ceph Migration Variables
# =============================================================================
variable "enable_ceph_migration" {
  description = "Enable Ceph storage migration between clusters/datacenters"
  type        = bool
  default     = false
}
variable "ceph_migration_source_cluster_name" {
  description = "Name of the source cluster (migrating FROM)"
  type        = string
  default     = ""
}
variable "ceph_migration_source_cluster_kubeconfig" {
  description = "Kubeconfig path for the source cluster on the bastion"
  type        = string
  default     = ""
}
variable "ceph_migration_destination_cluster_name" {
  description = "Name of the destination cluster (migrating TO)"
  type        = string
  default     = ""
}
variable "ceph_migration_destination_cluster_kubeconfig" {
  description = "Kubeconfig path for the destination cluster on the bastion"
  type        = string
  default     = ""
}
variable "ceph_migration_mode" {
  description = "Replication mode: async (snapshot-based) or sync (real-time)"
  type        = string
  default     = "async"
}
variable "ceph_migration_replication_schedule" {
  description = "Cron schedule for async replication"
  type        = string
  default     = "*/5 * * * *"
}
variable "ceph_migration_pool_name" {
  description = "Ceph block pool name to migrate"
  type        = string
  default     = "ocs-storagecluster-cephblockpool"
}
variable "ceph_migration_cephfs_pool_name" {
  description = "CephFS data pool name to migrate (empty to skip)"
  type        = string
  default     = ""
}
variable "ceph_migration_storage_class" {
  description = "StorageClass for migrated PVCs on the destination"
  type        = string
  default     = "ocs-storagecluster-ceph-rbd"
}
variable "ceph_migration_namespaces" {
  description = "Namespaces whose PVCs should be migrated"
  type = list(object({
    name           = string
    pvc_selector   = optional(map(string), {})
    exclude_pvcs   = optional(list(string), [])
  }))
  default = []
}
variable "ceph_migration_action" {
  description = "Migration action: prepare, migrate, validate, or cleanup"
  type        = string
  default     = "prepare"
}
variable "ceph_migration_s3_endpoint" {
  description = "S3 endpoint for migration metadata"
  type        = string
  default     = ""
}
variable "ceph_migration_s3_bucket" {
  description = "S3 bucket for migration metadata"
  type        = string
  default     = "ceph-migration-metadata"
}
variable "ceph_migration_s3_access_key" {
  description = "S3 access key for migration metadata"
  type        = string
  sensitive   = true
  default     = ""
}
variable "ceph_migration_s3_secret_key" {
  description = "S3 secret key for migration metadata"
  type        = string
  sensitive   = true
  default     = ""
}
variable "ceph_migration_rbd_mirror_count" {
  description = "Number of rbd-mirror daemon instances"
  type        = number
  default     = 1
}
variable "ceph_migration_verify_data_integrity" {
  description = "Verify data integrity after migration"
  type        = bool
  default     = true
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

# --- OpenShift Virtualization (KubeVirt / CNV) ---
variable "enable_openshift_virtualization" {
  description = "Enable OpenShift Virtualization (KubeVirt / CNV)"
  type        = bool
  default     = false
}

variable "cnv_channel" {
  description = "OLM subscription channel for OpenShift Virtualization"
  type        = string
  default     = "stable"
}

variable "cnv_install_plan_approval" {
  description = "Install plan approval strategy (Automatic or Manual)"
  type        = string
  default     = "Automatic"
}

variable "cnv_feature_gates" {
  description = "HyperConverged feature gates to enable"
  type        = list(string)
  default     = ["withHostPassthroughCPU", "enableCommonBootImageImport"]
}

variable "cnv_default_network_interface" {
  description = "Default network interface for VMs (masquerade, bridge, sr-iov)"
  type        = string
  default     = "masquerade"
}

variable "cnv_permitted_host_devices_pci" {
  description = "PCI host devices to passthrough (GPU, NIC)"
  type = list(object({
    pci_vendor_selector        = string
    resource_name              = string
    external_resource_provider = optional(bool, false)
  }))
  default = []
}

variable "cnv_permitted_host_devices_usb" {
  description = "USB host devices to passthrough"
  type = list(object({
    resource_name = string
    selectors = list(object({
      vendor  = string
      product = string
    }))
  }))
  default = []
}

variable "cnv_live_migration_bandwidth_per_migration" {
  description = "Bandwidth limit per live migration"
  type        = string
  default     = "64Mi"
}

variable "cnv_live_migration_completion_timeout" {
  description = "Completion timeout per GiB for live migration (seconds)"
  type        = number
  default     = 800
}

variable "cnv_live_migration_parallel_migrations_per_cluster" {
  description = "Max parallel live migrations per cluster"
  type        = number
  default     = 5
}

variable "cnv_live_migration_parallel_outbound_per_node" {
  description = "Max parallel outbound migrations per node"
  type        = number
  default     = 2
}

variable "cnv_live_migration_progress_timeout" {
  description = "Progress timeout for live migration (seconds)"
  type        = number
  default     = 150
}

variable "cnv_live_migration_allow_auto_converge" {
  description = "Allow QEMU auto-converge during live migration"
  type        = bool
  default     = true
}

variable "cnv_live_migration_allow_post_copy" {
  description = "Allow post-copy live migration"
  type        = bool
  default     = false
}

variable "cnv_live_migration_network" {
  description = "Dedicated network for live migration (NAD name or empty)"
  type        = string
  default     = ""
}

variable "cnv_cpu_model" {
  description = "Default CPU model for VMs (host-passthrough, host-model, Skylake-Server)"
  type        = string
  default     = "host-model"
}

variable "cnv_default_storage_class" {
  description = "Default StorageClass for VM disks"
  type        = string
  default     = "ocs-storagecluster-ceph-rbd-virtualization"
}

variable "cnv_scratch_space_storage_class" {
  description = "StorageClass for CDI scratch/temp space"
  type        = string
  default     = ""
}

variable "cnv_cdi_upload_proxy_url" {
  description = "CDI upload proxy URL (auto-detected if empty)"
  type        = string
  default     = ""
}

variable "cnv_enable_bridge_binding" {
  description = "Enable Linux bridge binding plugin for VMs"
  type        = bool
  default     = true
}

variable "cnv_ovs_annotations" {
  description = "Additional OVS annotations"
  type        = map(string)
  default     = {}
}

variable "cnv_node_selector" {
  description = "Node selector for KubeVirt components"
  type        = map(string)
  default     = {}
}

variable "cnv_infra_node_selector" {
  description = "Node selector for infra components (virt-controller, virt-api)"
  type        = map(string)
  default     = {}
}

variable "cnv_workload_node_selector" {
  description = "Node selector for workload placement (virt-launcher pods)"
  type        = map(string)
  default     = {}
}

variable "cnv_common_boot_image_import" {
  description = "Enable auto-import of common OS boot images"
  type        = bool
  default     = true
}

variable "cnv_custom_boot_images" {
  description = "Custom boot images to import as DataSources"
  type = list(object({
    name          = string
    namespace     = string
    registry_url  = string
    storage_class = optional(string, "")
    size          = optional(string, "30Gi")
  }))
  default = []
}

variable "cnv_custom_vm_templates" {
  description = "Custom VM template definitions"
  type = list(object({
    name        = string
    namespace   = string
    os_type     = string
    cpu_cores   = number
    memory      = string
    disk_size   = string
    description = optional(string, "")
  }))
  default = []
}

variable "cnv_admin_groups" {
  description = "Groups to grant kubevirt-admin ClusterRole"
  type        = list(string)
  default     = []
}

variable "cnv_enable_monitoring_alerts" {
  description = "Enable PrometheusRule alerts for OpenShift Virtualization"
  type        = bool
  default     = true
}

variable "cnv_mediated_devices" {
  description = "Mediated device types for vGPU passthrough"
  type = list(object({
    resource_name = string
    mdev_types    = list(string)
    node_selector = optional(map(string), {})
  }))
  default = []
}

# --- VM Migration (MTV — Migration Toolkit for Virtualization) ---
variable "enable_vm_migration" {
  description = "Enable VM Migration (MTV operator)"
  type        = bool
  default     = false
}

variable "mtv_channel" {
  description = "OLM subscription channel for MTV"
  type        = string
  default     = "release-v2.7"
}

variable "mtv_install_plan_approval" {
  description = "Install plan approval strategy for MTV"
  type        = string
  default     = "Automatic"
}

variable "source_provider_type" {
  description = "Source virtualization provider (vsphere, ovirt, openstack)"
  type        = string
  default     = "vsphere"
}

variable "source_provider_name" {
  description = "Name for the source provider resource"
  type        = string
  default     = "vmware-source"
}

variable "source_provider_url" {
  description = "API URL of the source provider (e.g. https://vcenter.example.com/sdk)"
  type        = string
  default     = ""
}

variable "source_provider_username" {
  description = "Username for the source provider"
  type        = string
  default     = ""
}

variable "source_provider_password" {
  description = "Password for the source provider"
  type        = string
  default     = ""
  sensitive   = true
}

variable "source_provider_thumbprint" {
  description = "SSL thumbprint of the source provider"
  type        = string
  default     = ""
}

variable "source_provider_ca_cert" {
  description = "CA certificate path for the source provider"
  type        = string
  default     = ""
}

variable "source_provider_insecure_skip_verify" {
  description = "Skip TLS verification for source provider"
  type        = bool
  default     = false
}

variable "destination_provider_name" {
  description = "Name for the destination (OpenShift) provider"
  type        = string
  default     = "host"
}

variable "network_map_name" {
  description = "Name for the network mapping"
  type        = string
  default     = "vm-network-map"
}

variable "network_mappings" {
  description = "Map source networks to destination networks"
  type = list(object({
    source_network      = string
    destination_network = string
    destination_type    = optional(string, "pod")
  }))
  default = []
}

variable "storage_map_name" {
  description = "Name for the storage mapping"
  type        = string
  default     = "vm-storage-map"
}

variable "storage_mappings" {
  description = "Map source datastores to destination storage classes"
  type = list(object({
    source_datastore         = string
    destination_storage_class = string
    volume_mode              = optional(string, "Filesystem")
  }))
  default = []
}

variable "migration_plan_name" {
  description = "Name for the migration plan"
  type        = string
  default     = "vm-migration-plan"
}

variable "migration_plan_namespace" {
  description = "Namespace for the migration plan and migrated VMs"
  type        = string
  default     = "openshift-mtv"
}

variable "migration_vms" {
  description = "List of VMs to migrate"
  type = list(object({
    name      = string
    id        = optional(string, "")
    namespace = optional(string, "")
  }))
  default = []
}

variable "migration_type" {
  description = "Migration type: cold (shutdown first) or warm (live, vSphere only)"
  type        = string
  default     = "cold"
}

variable "migration_start_immediately" {
  description = "Start migration immediately after plan creation"
  type        = bool
  default     = false
}

variable "migration_cutover_datetime" {
  description = "Scheduled cutover time for warm migration (ISO 8601)"
  type        = string
  default     = ""
}

variable "migration_preserve_static_ips" {
  description = "Preserve static IPs from source VMs"
  type        = bool
  default     = true
}

variable "migration_preserve_mac_addresses" {
  description = "Preserve MAC addresses from source VMs"
  type        = bool
  default     = false
}

variable "migration_hooks" {
  description = "Ansible playbook hooks for pre/post migration"
  type = list(object({
    name      = string
    namespace = string
    playbook  = string
    image     = optional(string, "quay.io/konveyor/hook-runner:latest")
  }))
  default = []
}

variable "migration_transfer_network" {
  description = "Dedicated network for disk transfer (NAD name or empty)"
  type        = string
  default     = ""
}

variable "migration_max_concurrent_vms" {
  description = "Maximum number of VMs to migrate simultaneously"
  type        = number
  default     = 10
}

variable "migration_max_concurrent_disks_per_vm" {
  description = "Maximum concurrent disk transfers per VM"
  type        = number
  default     = 2
}

# =============================================================================
# MTC (Migration Toolkit for Containers)
# =============================================================================

variable "enable_mtc" {
  description = "Enable MTC (Migration Toolkit for Containers) deployment"
  type        = bool
  default     = false
}

variable "mtc_channel" {
  description = "MTC operator subscription channel"
  type        = string
  default     = "release-v1.10"
}

variable "mtc_install_plan_approval" {
  description = "MTC operator install plan approval (Automatic or Manual)"
  type        = string
  default     = "Automatic"
}

variable "mtc_source_cluster_name" {
  description = "Logical name for the source cluster"
  type        = string
  default     = "source-cluster"
}

variable "mtc_source_cluster_url" {
  description = "API URL of the source cluster"
  type        = string
  default     = ""
}

variable "mtc_source_cluster_sa_token" {
  description = "Service account token for the source cluster"
  type        = string
  default     = ""
  sensitive   = true
}

variable "mtc_source_cluster_insecure" {
  description = "Skip TLS verification for source cluster API"
  type        = bool
  default     = false
}

variable "mtc_source_cluster_ca_bundle" {
  description = "CA bundle for the source cluster API (path on bastion)"
  type        = string
  default     = ""
}

variable "mtc_source_cluster_registry" {
  description = "Internal registry URL on source cluster"
  type        = string
  default     = ""
}

variable "mtc_source_cluster_exposed_route" {
  description = "Exposed migration controller route on source cluster"
  type        = string
  default     = ""
}

variable "mtc_destination_cluster_name" {
  description = "Logical name for the destination cluster"
  type        = string
  default     = "host"
}

variable "mtc_destination_cluster_url" {
  description = "API URL of the destination cluster (empty = local host)"
  type        = string
  default     = ""
}

variable "mtc_destination_cluster_sa_token" {
  description = "SA token for destination cluster"
  type        = string
  default     = ""
  sensitive   = true
}

variable "mtc_replication_repository_name" {
  description = "Name for the replication repository"
  type        = string
  default     = "migration-repo"
}

variable "mtc_replication_repository_type" {
  description = "Type of replication repository (s3, gcs, azure)"
  type        = string
  default     = "s3"
}

variable "mtc_replication_repository_url" {
  description = "S3-compatible endpoint URL"
  type        = string
  default     = ""
}

variable "mtc_replication_repository_bucket" {
  description = "S3 bucket name"
  type        = string
  default     = "mtc-migration-data"
}

variable "mtc_replication_repository_region" {
  description = "S3 region"
  type        = string
  default     = "us-east-1"
}

variable "mtc_replication_repository_access_key" {
  description = "S3 access key"
  type        = string
  default     = ""
  sensitive   = true
}

variable "mtc_replication_repository_secret_key" {
  description = "S3 secret key"
  type        = string
  default     = ""
  sensitive   = true
}

variable "mtc_replication_repository_insecure" {
  description = "Use HTTP instead of HTTPS for replication repository"
  type        = bool
  default     = false
}

variable "mtc_replication_repository_ca_bundle" {
  description = "CA bundle for the replication repository endpoint"
  type        = string
  default     = ""
}

variable "mtc_migration_plan_name" {
  description = "Name of the migration plan"
  type        = string
  default     = "mtc-migration-plan"
}

variable "mtc_migration_plan_namespaces" {
  description = "List of namespaces to migrate"
  type = list(object({
    source_namespace      = string
    destination_namespace = optional(string, "")
    annotations           = optional(map(string), {})
  }))
  default = []
}

variable "mtc_migration_type" {
  description = "Migration type: stage, final, or rollback"
  type        = string
  default     = "final"
}

variable "mtc_pv_copy_method" {
  description = "PV copy method: filesystem (Restic) or snapshot (CSI)"
  type        = string
  default     = "filesystem"
}

variable "mtc_pv_verify" {
  description = "Verify data integrity of copied PVs"
  type        = bool
  default     = true
}

variable "mtc_pv_storage_class_mapping" {
  description = "Map source PV storage classes to destination"
  type = list(object({
    source_storage_class      = string
    destination_storage_class = string
  }))
  default = []
}

variable "mtc_pv_access_mode_mapping" {
  description = "Map source PV access modes to destination"
  type = list(object({
    source_access_mode      = string
    destination_access_mode = string
  }))
  default = []
}

variable "mtc_enable_direct_volume_migration" {
  description = "Enable Direct Volume Migration (DVM)"
  type        = bool
  default     = true
}

variable "mtc_enable_direct_image_migration" {
  description = "Enable Direct Image Migration (DIM)"
  type        = bool
  default     = true
}

variable "mtc_quiesce_pods" {
  description = "Quiesce source pods during final migration"
  type        = bool
  default     = true
}

variable "mtc_keep_annotations" {
  description = "Preserve annotations on migrated resources"
  type        = bool
  default     = true
}

variable "mtc_preserve_node_ports" {
  description = "Preserve NodePort values in migrated Services"
  type        = bool
  default     = false
}

variable "mtc_migration_hooks" {
  description = "Pre/post migration hooks"
  type = list(object({
    name            = string
    namespace       = string
    phase           = string
    playbook_path   = optional(string, "")
    custom_image    = optional(string, "")
    service_account = optional(string, "migration-controller")
  }))
  default = []
}

variable "mtc_excluded_resources" {
  description = "Kubernetes resource types to exclude from migration"
  type        = list(string)
  default     = []
}

variable "mtc_label_selector" {
  description = "Label selector to filter resources within migrated namespaces"
  type        = string
  default     = ""
}
