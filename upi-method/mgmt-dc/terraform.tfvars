# =============================================================================
# Management Cluster DC (UPI) — Variable Definitions
# ACM Hub + ACS Central + Quay Enterprise
# =============================================================================

# ---- Cluster ----
cluster_name = "mgmt-dc-upi"
base_domain  = "example.com"
ocp_version  = "4.15"

# ---- UPI Install ----
install_dir      = "/home/kni/upi-install"
rhcos_iso_url    = "https://mirror.openshift.com/pub/openshift-v4/x86_64/dependencies/rhcos/4.15/latest/rhcos-live.x86_64.iso"
rhcos_rootfs_url = "https://mirror.openshift.com/pub/openshift-v4/x86_64/dependencies/rhcos/4.15/latest/rhcos-live-rootfs.x86_64.img"
install_disk     = "/dev/sda"
boot_method      = "pxe"
ignition_http_port = 8080
bootstrap_ip     = "10.142.42.20"
bootstrap_mac    = "aa:bb:cc:ee:01:00"

# ---- Networking ----
machine_network_cidr        = "10.142.42.0/24"
cluster_network_cidr        = "10.136.0.0/14"
cluster_network_host_prefix = 23
service_network_cidr        = "172.28.0.0/16"
api_vip                     = "10.142.42.30"
ingress_vip                 = "10.142.42.31"
gateway                     = "10.142.42.1"
dns_servers                 = ["10.142.42.2", "10.142.42.3"]
ntp_servers                 = ["pool.ntp.org"]

# ---- Pull Secret & SSH ----
pull_secret_file    = "/home/kni/pull-secret.json"
ssh_public_key_file = "~/.ssh/id_ed25519.pub"

# ---- Bastion ----
bastion_host                 = "10.142.42.10"
bastion_user                 = "kni"
bastion_ssh_private_key_file = "~/.ssh/id_ed25519"

# ---- Bootstrap OS Image ----
bootstrap_os_image_url = "http://10.142.42.10:8080/rhcos-qemu.x86_64.qcow2.gz?sha256=REPLACE_WITH_SHA256"

# ---- Local Quay Mirror (Disconnected) ----
enable_quay_mirror  = true
quay_host           = "10.142.42.15"
quay_port           = 8443
quay_admin_user     = "quayadmin"
quay_admin_password = "REPLACE_QUAY_PASSWORD"
quay_organization   = "ocp4"
quay_ca_cert_file   = "/home/kni/quay-certs/quay-ca.pem"
ocp_channel         = "stable-4.15"

mirror_operators = [
  {
    catalog = "registry.redhat.io/redhat/redhat-operator-index:v4.15"
    packages = [
      { name = "advanced-cluster-management", channel = "release-2.11" },
      { name = "rhacs-operator", channel = "stable" },
      { name = "quay-operator", channel = "stable-3.12" },
      { name = "odf-operator", channel = "stable-4.16" },
      { name = "metallb-operator", channel = "stable" },
      { name = "cluster-logging", channel = "stable" },
      { name = "elasticsearch-operator", channel = "stable" },
      { name = "redhat-oadp-operator", channel = "stable-1.4" },
      { name = "submariner", channel = "stable-0.18" },
      { name = "openshift-gitops-operator", channel = "latest" },
      { name = "openshift-pipelines-operator-rh", channel = "latest" },
      { name = "odr-hub-operator", channel = "stable-4.16" },
    ]
  },
]

mirror_registry              = ""
additional_trust_bundle_file = ""

# ---- Master Nodes (UPI — no BMC) ----
master_nodes = [
  {
    name             = "master-0"
    boot_mac_address = "aa:bb:cc:ee:01:01"
    boot_mode        = "UEFI"
    root_disk_min_gb = 890
    ip               = "10.142.42.101"
    bond_interfaces  = ["ens1f0", "ens1f1"]
  },
  {
    name             = "master-1"
    boot_mac_address = "aa:bb:cc:ee:01:02"
    boot_mode        = "UEFI"
    root_disk_min_gb = 890
    ip               = "10.142.42.103"
    bond_interfaces  = ["ens1f0", "ens1f1"]
  },
  {
    name             = "master-2"
    boot_mac_address = "aa:bb:cc:ee:01:03"
    boot_mode        = "UEFI"
    root_disk_min_gb = 890
    ip               = "10.142.42.105"
    bond_interfaces  = ["ens1f0", "ens1f1"]
  },
]

# ---- Worker Nodes (UPI — no BMC) ----
worker_nodes = [
  {
    name             = "worker-odf-0"
    boot_mac_address = "aa:bb:cc:ee:02:01"
    boot_mode        = "UEFI"
    root_disk_min_gb = 890
    ip               = "10.142.42.121"
    bond_interfaces  = ["ens1f0", "ens1f1"]
    gpu_worker       = false
    odf_worker       = true
  },
  {
    name             = "worker-odf-1"
    boot_mac_address = "aa:bb:cc:ee:02:02"
    boot_mode        = "UEFI"
    root_disk_min_gb = 890
    ip               = "10.142.42.123"
    bond_interfaces  = ["ens1f0", "ens1f1"]
    gpu_worker       = false
    odf_worker       = true
  },
  {
    name             = "worker-odf-2"
    boot_mac_address = "aa:bb:cc:ee:02:03"
    boot_mode        = "UEFI"
    root_disk_min_gb = 890
    ip               = "10.142.42.125"
    bond_interfaces  = ["ens1f0", "ens1f1"]
    gpu_worker       = false
    odf_worker       = true
  },
]

# ---- HAProxy (required for UPI) ----
haproxy_hosts = [
  {
    host    = "10.142.42.10"
    user    = "kni"
    ssh_key = "~/.ssh/id_ed25519"
  },
]

# ---- MetalLB ----
enable_metallb        = true
metallb_address_pools = [
  {
    name        = "mgmt-dc-pool"
    addresses   = ["10.142.42.200-10.142.42.220"]
    auto_assign = true
  }
]
metallb_l2_advertisements = [
  {
    name       = "mgmt-dc-l2"
    pool_names = ["mgmt-dc-pool"]
  }
]

# ---- ODF ----
enable_odf           = true
odf_storage_capacity = "2Ti"
odf_channel          = "stable-4.16"

# ---- ACM (Hub) ----
enable_acm               = true
acm_channel              = "release-2.11"
acm_instance_name        = "multiclusterhub"
acm_enable_observability = true
acm_s3_bucket            = "acm-observability"
acm_s3_endpoint          = "https://s3.example.com"
acm_s3_access_key        = "REPLACE_S3_ACCESS_KEY"
acm_s3_secret_key        = "REPLACE_S3_SECRET_KEY"

# ---- ACS (Central + SecuredCluster) ----
enable_acs                 = true
acs_channel                = "stable"
acs_central_admin_password = "REPLACE_ACS_ADMIN_PASSWORD"
acs_central_storage_size   = "100Gi"

# ---- Quay Enterprise Registry ----
enable_quay_enterprise            = true
quay_enterprise_channel           = "stable-3.12"
quay_enterprise_instance_name     = "central-quay"
quay_enterprise_storage_size      = "100Gi"
quay_enterprise_superuser         = "quayadmin"
quay_enterprise_components = {
  clair                   = "managed"
  clairpostgres           = "managed"
  objectstorage           = "managed"
  postgres                = "managed"
  redis                   = "managed"
  horizontalpodautoscaler = "managed"
  mirror                  = "managed"
  monitoring              = "managed"
  route                   = "managed"
  tls                     = "managed"
}

# ---- etcd Backup ----
enable_etcd_backup   = true
etcd_backup_schedule = "56 23 * * *"
