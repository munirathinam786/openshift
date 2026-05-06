# =============================================================================
# DR Secondary — Variable Definitions
# Update all values to match your DR site environment.
# =============================================================================

# ---- Cluster ----
cluster_name = "ocp-ai-dr"
base_domain  = "dr.example.com"
ocp_version  = "4.20"

# ---- Networking (use non-overlapping CIDRs if Submariner globalnet is off) ----
machine_network_cidr        = "10.143.41.0/24"
cluster_network_cidr        = "10.132.0.0/14"
cluster_network_host_prefix = 23
service_network_cidr        = "172.31.0.0/16"
api_vip                     = "10.143.41.30"
ingress_vip                 = "10.143.41.31"
gateway                     = "10.143.41.1"
dns_servers                 = ["10.143.41.2", "10.143.41.3"]
ntp_servers                 = ["pool.ntp.org"]

# ---- Pull Secret & SSH ----
pull_secret_file    = "/home/kni/pull-secret.json"
ssh_public_key_file = "~/.ssh/id_ed25519.pub"

# ---- Bastion / Provisioner Node (DR site) ----
bastion_host                 = "10.143.41.10"
bastion_user                 = "kni"
bastion_ssh_private_key_file = "~/.ssh/id_ed25519"

# ---- Bootstrap ----
bootstrap_os_image_url = "http://10.143.41.10:8080/rhcos-qemu.x86_64.qcow2.gz?sha256=REPLACE_WITH_SHA256"

# ---- Local Quay Mirror (DR site) ----
enable_quay_mirror  = true
quay_host           = "10.143.41.15"
quay_port           = 8443
quay_admin_user     = "quayadmin"
quay_admin_password = "REPLACE_QUAY_PASSWORD"
quay_organization   = "ocp4"
quay_ca_cert_file   = "/home/kni/quay-certs/quay-ca.pem"
ocp_channel         = "stable-4.20"

mirror_operators = [
  {
    catalog = "registry.redhat.io/redhat/redhat-operator-index:v4.20"
    packages = [
      { name = "nfd", channel = "stable" },
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
      { name = "submariner", channel = "stable-0.20" },
      { name = "redhat-oadp-operator", channel = "stable-1.6" },
      { name = "odr-cluster-operator", channel = "stable-4.20" },
      { name = "openshift-gitops-operator", channel = "latest" },
    ]
  },
  {
    catalog = "registry.redhat.io/redhat/certified-operator-index:v4.20"
    packages = [
      { name = "gpu-operator-certified", channel = "v26.3" },
    ]
  },
]

mirror_registry              = ""
additional_trust_bundle_file = ""

# ---- Master Nodes (3 required) ----
master_nodes = [
  {
    name = "master-0"
    bmc_address      = "idrac-virtualmedia://10.143.41.100/redfish/v1/Systems/System.Embedded.1"
    bmc_username     = "admin"
    bmc_password     = "REPLACE_PASSWORD"
    boot_mac_address = "aa:bb:cc:dd:ff:01"
    boot_mode        = "UEFI"
    root_disk_min_gb = 890
    ip               = "10.143.41.101"
    bond_interfaces  = ["ens1f0", "ens1f1"]
  },
  {
    name = "master-1"
    bmc_address      = "idrac-virtualmedia://10.143.41.102/redfish/v1/Systems/System.Embedded.1"
    bmc_username     = "admin"
    bmc_password     = "REPLACE_PASSWORD"
    boot_mac_address = "aa:bb:cc:dd:ff:02"
    boot_mode        = "UEFI"
    root_disk_min_gb = 890
    ip               = "10.143.41.103"
    bond_interfaces  = ["ens1f0", "ens1f1"]
  },
  {
    name = "master-2"
    bmc_address      = "idrac-virtualmedia://10.143.41.104/redfish/v1/Systems/System.Embedded.1"
    bmc_username     = "admin"
    bmc_password     = "REPLACE_PASSWORD"
    boot_mac_address = "aa:bb:cc:dd:ff:03"
    boot_mode        = "UEFI"
    root_disk_min_gb = 890
    ip               = "10.143.41.105"
    bond_interfaces  = ["ens1f0", "ens1f1"]
  },
]

# ---- Worker Nodes ----
worker_nodes = [
  {
    name = "worker-gpu-0"
    bmc_address      = "idrac-virtualmedia://10.143.41.110/redfish/v1/Systems/System.Embedded.1"
    bmc_username     = "admin"
    bmc_password     = "REPLACE_PASSWORD"
    boot_mac_address = "aa:bb:cc:dd:ff:10"
    boot_mode        = "UEFI"
    root_disk_min_gb = 890
    ip               = "10.143.41.111"
    bond_interfaces  = ["ens1f0", "ens1f1"]
    gpu_worker       = true
    odf_worker       = false
  },
  {
    name = "worker-gpu-1"
    bmc_address      = "idrac-virtualmedia://10.143.41.112/redfish/v1/Systems/System.Embedded.1"
    bmc_username     = "admin"
    bmc_password     = "REPLACE_PASSWORD"
    boot_mac_address = "aa:bb:cc:dd:ff:11"
    boot_mode        = "UEFI"
    root_disk_min_gb = 890
    ip               = "10.143.41.113"
    bond_interfaces  = ["ens1f0", "ens1f1"]
    gpu_worker       = true
    odf_worker       = false
  },
  {
    name = "worker-odf-0"
    bmc_address      = "idrac-virtualmedia://10.143.41.120/redfish/v1/Systems/System.Embedded.1"
    bmc_username     = "admin"
    bmc_password     = "REPLACE_PASSWORD"
    boot_mac_address = "aa:bb:cc:dd:ff:20"
    boot_mode        = "UEFI"
    root_disk_min_gb = 890
    ip               = "10.143.41.121"
    bond_interfaces  = ["ens1f0", "ens1f1"]
    gpu_worker       = false
    odf_worker       = true
  },
  {
    name = "worker-odf-1"
    bmc_address      = "idrac-virtualmedia://10.143.41.122/redfish/v1/Systems/System.Embedded.1"
    bmc_username     = "admin"
    bmc_password     = "REPLACE_PASSWORD"
    boot_mac_address = "aa:bb:cc:dd:ff:21"
    boot_mode        = "UEFI"
    root_disk_min_gb = 890
    ip               = "10.143.41.123"
    bond_interfaces  = ["ens1f0", "ens1f1"]
    gpu_worker       = false
    odf_worker       = true
  },
  {
    name = "worker-odf-2"
    bmc_address      = "idrac-virtualmedia://10.143.41.124/redfish/v1/Systems/System.Embedded.1"
    bmc_username     = "admin"
    bmc_password     = "REPLACE_PASSWORD"
    boot_mac_address = "aa:bb:cc:dd:ff:22"
    boot_mode        = "UEFI"
    root_disk_min_gb = 890
    ip               = "10.143.41.125"
    bond_interfaces  = ["ens1f0", "ens1f1"]
    gpu_worker       = false
    odf_worker       = true
  },
]

haproxy_hosts = []

# ---- MetalLB (optional) ----
enable_metallb        = false
metallb_address_pools = []
metallb_l2_advertisements = []

# ---- SR-IOV (optional) ----
enable_sriov          = false
sriov_network_devices = []
sriov_networks        = []

# ---- GPU ----
ngc_api_key          = "REPLACE_NGC_API_KEY"
nls_token_file       = "/path/to/client_configuration_token.tok"
vgpu_driver_version  = "580.126.20"
vgpu_driver_image    = "vgpu-guest-driver-5"
gpu_rdma_enabled     = false
entitlement_pem_file = "/path/to/entitlement.pem"

# ---- ODF Storage ----
enable_odf           = true
odf_storage_capacity = "2Ti"
odf_channel          = "stable-4.20"

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

# ---- Autoscaler ----
enable_cluster_autoscaler = false
autoscaler_max_nodes      = 24
autoscaler_max_gpus       = 16

# ---- etcd Backup ----
enable_etcd_backup   = true
etcd_backup_schedule = "56 23 * * *"

# ---- Submariner (connects DR back to DC Primary as agent) ----
enable_submariner              = false
submariner_broker_api_url      = "https://api.ocp-ai.example.com:6443"
submariner_broker_token        = "REPLACE_BROKER_TOKEN"
submariner_broker_ca           = ""
submariner_cable_driver        = "libreswan"
submariner_gateway_count       = 1
submariner_globalnet_enabled   = false
submariner_gateway_node_labels = { "submariner.io/gateway" = "true" }

# ---- ODF DR Replication (DC ↔ DR async/sync mirroring) ----
enable_odf_dr              = false
odf_dr_mode                = "regional-dr"    # regional-dr (async) or metro-dr (sync)
odf_dr_replication_schedule = "*/5 * * * *"
odf_dr_peer_cluster_name   = "ocp-ai"         # DC Primary cluster name
odf_dr_s3_endpoint         = ""
odf_dr_s3_bucket           = "odf-dr-metadata"
odf_dr_s3_access_key       = "REPLACE_S3_ACCESS_KEY"
odf_dr_s3_secret_key       = "REPLACE_S3_SECRET_KEY"
