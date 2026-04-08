# =============================================================================
# OpenShift Baremetal UPI + OpenShift AI — Variable Definitions
# Update all values below to match your environment.
# =============================================================================

# ---- Cluster ----
cluster_name = "ocp-ai-upi"
base_domain  = "example.com"
ocp_version  = "4.15"

# ---- Networking ----
machine_network_cidr        = "10.142.41.0/24"
cluster_network_cidr        = "10.128.0.0/14"
cluster_network_host_prefix = 23
service_network_cidr        = "172.30.0.0/16"
api_vip                     = "10.142.41.30"
ingress_vip                 = "10.142.41.31"
gateway                     = "10.142.41.1"
dns_servers                 = ["10.142.41.2", "10.142.41.3"]
ntp_servers                 = ["pool.ntp.org"]

# ---- Pull Secret & SSH ----
pull_secret_file    = "/home/kni/pull-secret.json"
ssh_public_key_file = "~/.ssh/id_ed25519.pub"

# ---- Bastion / Provisioner Node ----
bastion_host                 = "10.142.41.10"
bastion_user                 = "kni"
bastion_ssh_private_key_file = "~/.ssh/id_ed25519"

# ---- UPI Install Directory ----
install_dir = "/home/kni/ocp-install"

# ---- RHCOS Images (UPI — manual boot) ----
rhcos_iso_url    = "http://10.142.41.10:8080/rhcos-4.15.0-x86_64-live.x86_64.iso"
rhcos_rootfs_url = "http://10.142.41.10:8080/rhcos-4.15.0-x86_64-live-rootfs.x86_64.img"
install_disk     = "/dev/sda"

# ---- Boot Method ----
# Options: pxe, iso, manual
# "manual" = operator boots nodes manually with ignition URLs
boot_method = "pxe"

# ---- Ignition HTTP Server (bastion serves ignition configs) ----
ignition_http_port = 8080

# ---- Bootstrap Node (ephemeral — removed after install) ----
bootstrap_ip  = "10.142.41.20"
bootstrap_mac = "aa:bb:cc:dd:ee:00"

# ---- Local Quay Mirror Registry (Disconnected Install) ----
enable_quay_mirror  = true
quay_host           = "10.142.41.15"
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
      { name = "nfd", channel = "stable" },
      { name = "odf-operator", channel = "stable-4.16" },
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
      { name = "submariner", channel = "stable-0.18" },
      { name = "redhat-oadp-operator", channel = "stable-1.4" },
      { name = "odr-cluster-operator", channel = "stable-4.16" },
      { name = "openshift-gitops-operator", channel = "latest" },
    ]
  },
  {
    catalog = "registry.redhat.io/redhat/certified-operator-index:v4.15"
    packages = [
      { name = "gpu-operator-certified", channel = "v24.6" },
    ]
  },
]

mirror_registry              = ""
additional_trust_bundle_file = ""

# ---- Master Nodes (3 required — no BMC in UPI) ----
master_nodes = [
  {
    name            = "master-0"
    ip              = "10.142.41.101"
    mac_address     = "aa:bb:cc:dd:ee:01"
    boot_mode       = "UEFI"
    bond_interfaces = ["ens1f0", "ens1f1"]
  },
  {
    name            = "master-1"
    ip              = "10.142.41.103"
    mac_address     = "aa:bb:cc:dd:ee:02"
    boot_mode       = "UEFI"
    bond_interfaces = ["ens1f0", "ens1f1"]
  },
  {
    name            = "master-2"
    ip              = "10.142.41.105"
    mac_address     = "aa:bb:cc:dd:ee:03"
    boot_mode       = "UEFI"
    bond_interfaces = ["ens1f0", "ens1f1"]
  },
]

# ---- Worker Nodes (GPU + ODF — no BMC in UPI) ----
worker_nodes = [
  {
    name            = "worker-gpu-0"
    ip              = "10.142.41.111"
    mac_address     = "aa:bb:cc:dd:ee:10"
    boot_mode       = "UEFI"
    bond_interfaces = ["ens1f0", "ens1f1"]
    gpu_worker      = true
    odf_worker      = false
  },
  {
    name            = "worker-gpu-1"
    ip              = "10.142.41.113"
    mac_address     = "aa:bb:cc:dd:ee:11"
    boot_mode       = "UEFI"
    bond_interfaces = ["ens1f0", "ens1f1"]
    gpu_worker      = true
    odf_worker      = false
  },
  {
    name            = "worker-odf-0"
    ip              = "10.142.41.121"
    mac_address     = "aa:bb:cc:dd:ee:20"
    boot_mode       = "UEFI"
    bond_interfaces = ["ens1f0", "ens1f1"]
    gpu_worker      = false
    odf_worker      = true
  },
  {
    name            = "worker-odf-1"
    ip              = "10.142.41.123"
    mac_address     = "aa:bb:cc:dd:ee:21"
    boot_mode       = "UEFI"
    bond_interfaces = ["ens1f0", "ens1f1"]
    gpu_worker      = false
    odf_worker      = true
  },
  {
    name            = "worker-odf-2"
    ip              = "10.142.41.125"
    mac_address     = "aa:bb:cc:dd:ee:22"
    boot_mode       = "UEFI"
    bond_interfaces = ["ens1f0", "ens1f1"]
    gpu_worker      = false
    odf_worker      = true
  },
]

# ---- HAProxy Load Balancers (required for UPI) ----
haproxy_hosts = [
  {
    host    = "10.142.41.5"
    user    = "root"
    ssh_key = "~/.ssh/id_ed25519"
  },
]

# ---- MetalLB Operator (optional) ----
enable_metallb            = false
metallb_address_pools     = []
metallb_l2_advertisements = []

# ---- SR-IOV Network Operator (optional) ----
enable_sriov          = false
sriov_network_devices = []
sriov_networks        = []

# ---- GPU / NVIDIA ----
ngc_api_key         = "REPLACE_NGC_API_KEY"
nls_token_file      = "/path/to/client_configuration_token.tok"
vgpu_driver_version = "550.90.07"
vgpu_driver_image   = "vgpu-guest-driver-5"
gpu_rdma_enabled    = false

# ---- Cluster-Wide Entitlement ----
entitlement_pem_file = "/path/to/entitlement.pem"

# ---- ODF Storage ----
enable_odf           = true
odf_storage_capacity = "2Ti"
odf_channel          = "stable-4.16"

# ---- OpenShift AI ----
enable_openshift_ai = true
oai_components = {
  dashboard            = "Managed"
  workbenches          = "Managed"
  datasciencepipelines = "Managed"
  modelmeshserving     = "Managed"
  kserve               = "Managed"
  codeflare            = "Managed"
  ray                  = "Managed"
  trustyai             = "Managed"
}
enable_nim = false

# ---- Service Mesh & Serverless ----
enable_servicemesh = true
enable_serverless  = true

# ---- GPU Monitoring ----
enable_gpu_monitoring = true

# ---- Cluster Autoscaler ----
enable_cluster_autoscaler = false
autoscaler_max_nodes      = 24
autoscaler_max_gpus       = 16

# ---- etcd Backup ----
enable_etcd_backup   = true
etcd_backup_schedule = "56 23 * * *"

# ---- Submariner (DC Primary as Broker) ----
enable_submariner              = false
submariner_cable_driver        = "libreswan"
submariner_gateway_count       = 1
submariner_globalnet_enabled   = false
submariner_gateway_node_labels = { "submariner.io/gateway" = "true" }

# ---- ODF DR Replication (DC side) ----
enable_odf_dr               = false
odf_dr_mode                 = "regional-dr"
odf_dr_replication_schedule = "*/5 * * * *"
odf_dr_peer_cluster_name    = "ocp-ai-dr"
odf_dr_s3_endpoint          = ""
odf_dr_s3_bucket            = "odf-dr-metadata"
odf_dr_s3_access_key        = "REPLACE_S3_ACCESS_KEY"
odf_dr_s3_secret_key        = "REPLACE_S3_SECRET_KEY"
