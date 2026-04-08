# =============================================================================
# OpenShift Baremetal + OpenShift AI — Variable Definitions
# Update all values below to match your environment.
# =============================================================================

# ---- Cluster ----
cluster_name = "ocp-ai"
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

# ---- Bootstrap OS Image ----
bootstrap_os_image_url = "http://10.142.41.10:8080/rhcos-qemu.x86_64.qcow2.gz?sha256=REPLACE_WITH_SHA256"

# ---- Local Quay Mirror Registry (Disconnected Install) ----
# Set enable_quay_mirror = true to use a dedicated local Quay server.
# oc-mirror will mirror OCP release images + all required operators into Quay.
# The RHCOS boot image will be staged on the bastion HTTP server.
enable_quay_mirror  = true
quay_host           = "10.142.41.15"                     # IP or FQDN of your local Quay server
quay_port           = 8443                               # Quay HTTPS port
quay_admin_user     = "quayadmin"                        # Quay admin username
quay_admin_password = "REPLACE_QUAY_PASSWORD"            # Quay admin password
quay_organization   = "ocp4"                             # Quay org to store mirrored content
quay_ca_cert_file   = "/home/kni/quay-certs/quay-ca.pem" # Quay server CA certificate
ocp_channel         = "stable-4.15"                      # OCP release channel for oc-mirror

# Operators to mirror (defaults cover all required operators; override to add/remove)
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

# Legacy overrides (auto-set by enable_quay_mirror; leave empty)
mirror_registry              = ""
additional_trust_bundle_file = ""

# ---- Master Nodes (3 required) ----
master_nodes = [
  {
    name             = "master-0"
    bmc_address      = "idrac-virtualmedia://10.142.41.100/redfish/v1/Systems/System.Embedded.1"
    bmc_username     = "admin"
    bmc_password     = "REPLACE_PASSWORD"
    boot_mac_address = "aa:bb:cc:dd:ee:01"
    boot_mode        = "UEFI"
    root_disk_min_gb = 890
    ip               = "10.142.41.101"
    bond_interfaces  = ["ens1f0", "ens1f1"]
  },
  {
    name             = "master-1"
    bmc_address      = "idrac-virtualmedia://10.142.41.102/redfish/v1/Systems/System.Embedded.1"
    bmc_username     = "admin"
    bmc_password     = "REPLACE_PASSWORD"
    boot_mac_address = "aa:bb:cc:dd:ee:02"
    boot_mode        = "UEFI"
    root_disk_min_gb = 890
    ip               = "10.142.41.103"
    bond_interfaces  = ["ens1f0", "ens1f1"]
  },
  {
    name             = "master-2"
    bmc_address      = "idrac-virtualmedia://10.142.41.104/redfish/v1/Systems/System.Embedded.1"
    bmc_username     = "admin"
    bmc_password     = "REPLACE_PASSWORD"
    boot_mac_address = "aa:bb:cc:dd:ee:03"
    boot_mode        = "UEFI"
    root_disk_min_gb = 890
    ip               = "10.142.41.105"
    bond_interfaces  = ["ens1f0", "ens1f1"]
  },
]

# ---- Worker Nodes (GPU + ODF) ----
worker_nodes = [
  {
    name             = "worker-gpu-0"
    bmc_address      = "idrac-virtualmedia://10.142.41.110/redfish/v1/Systems/System.Embedded.1"
    bmc_username     = "admin"
    bmc_password     = "REPLACE_PASSWORD"
    boot_mac_address = "aa:bb:cc:dd:ee:10"
    boot_mode        = "UEFI"
    root_disk_min_gb = 890
    ip               = "10.142.41.111"
    bond_interfaces  = ["ens1f0", "ens1f1"]
    gpu_worker       = true
    odf_worker       = false
  },
  {
    name             = "worker-gpu-1"
    bmc_address      = "idrac-virtualmedia://10.142.41.112/redfish/v1/Systems/System.Embedded.1"
    bmc_username     = "admin"
    bmc_password     = "REPLACE_PASSWORD"
    boot_mac_address = "aa:bb:cc:dd:ee:11"
    boot_mode        = "UEFI"
    root_disk_min_gb = 890
    ip               = "10.142.41.113"
    bond_interfaces  = ["ens1f0", "ens1f1"]
    gpu_worker       = true
    odf_worker       = false
  },
  {
    name             = "worker-odf-0"
    bmc_address      = "idrac-virtualmedia://10.142.41.120/redfish/v1/Systems/System.Embedded.1"
    bmc_username     = "admin"
    bmc_password     = "REPLACE_PASSWORD"
    boot_mac_address = "aa:bb:cc:dd:ee:20"
    boot_mode        = "UEFI"
    root_disk_min_gb = 890
    ip               = "10.142.41.121"
    bond_interfaces  = ["ens1f0", "ens1f1"]
    gpu_worker       = false
    odf_worker       = true
  },
  {
    name             = "worker-odf-1"
    bmc_address      = "idrac-virtualmedia://10.142.41.122/redfish/v1/Systems/System.Embedded.1"
    bmc_username     = "admin"
    bmc_password     = "REPLACE_PASSWORD"
    boot_mac_address = "aa:bb:cc:dd:ee:21"
    boot_mode        = "UEFI"
    root_disk_min_gb = 890
    ip               = "10.142.41.123"
    bond_interfaces  = ["ens1f0", "ens1f1"]
    gpu_worker       = false
    odf_worker       = true
  },
  {
    name             = "worker-odf-2"
    bmc_address      = "idrac-virtualmedia://10.142.41.124/redfish/v1/Systems/System.Embedded.1"
    bmc_username     = "admin"
    bmc_password     = "REPLACE_PASSWORD"
    boot_mac_address = "aa:bb:cc:dd:ee:22"
    boot_mode        = "UEFI"
    root_disk_min_gb = 890
    ip               = "10.142.41.125"
    bond_interfaces  = ["ens1f0", "ens1f1"]
    gpu_worker       = false
    odf_worker       = true
  },
]

# ---- HAProxy Load Balancers (optional — leave empty if using F5/external LB) ----
haproxy_hosts = [
  # {
  #   host    = "10.142.41.5"
  #   user    = "root"
  #   ssh_key = "~/.ssh/id_ed25519"
  # },
  # {
  #   host    = "10.142.41.6"
  #   user    = "root"
  #   ssh_key = "~/.ssh/id_ed25519"
  # },
]

# ---- MetalLB Operator (optional) ----
# Enable for bare metal LoadBalancer service support (Layer 2 or BGP)
enable_metallb = false

# IP address pools for LoadBalancer services
metallb_address_pools = [
  # {
  #   name      = "default-pool"
  #   addresses = ["10.142.41.200-10.142.41.250"]
  #   auto_assign = true
  # },
]

# L2 advertisements — announce pools via ARP/NDP
metallb_l2_advertisements = [
  # {
  #   name       = "default-l2"
  #   pool_names = ["default-pool"]
  # },
]

# ---- SR-IOV Network Operator (optional) ----
# Enable for high-performance networking (GPUDirect RDMA, data plane acceleration)
enable_sriov = false

# SR-IOV device policies — configure per your NIC hardware
# Uncomment and update pf_names to match your physical function interface names
sriov_network_devices = [
  # {
  #   name          = "gpu-sriov-policy"
  #   pf_names      = ["ens2f0", "ens2f1"]    # Physical Function NIC names
  #   num_vfs       = 8                         # Number of Virtual Functions
  #   resource_name = "gpusriovnic"             # Resource name for pod requests
  #   device_type   = "netdevice"               # netdevice or vfio-pci
  # },
]

# SR-IOV network attachment definitions
sriov_networks = [
  # {
  #   name             = "gpu-sriov-network"
  #   resource_name    = "gpusriovnic"
  #   target_namespace = "default"
  #   vlan             = 100
  #   ipam             = "{\"type\": \"dhcp\"}"
  # },
]

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

# ---- Service Mesh & Serverless (required for KServe model serving) ----
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
# Enable when deploying DC+DR with cross-cluster networking
enable_submariner              = false
submariner_cable_driver        = "libreswan"
submariner_gateway_count       = 1
submariner_globalnet_enabled   = false
submariner_gateway_node_labels = { "submariner.io/gateway" = "true" }

# ---- ODF DR Replication (DC side) ----
# Enable when deploying DC+DR with storage replication
enable_odf_dr               = false
odf_dr_mode                 = "regional-dr"    # regional-dr (async) or metro-dr (sync)
odf_dr_replication_schedule = "*/5 * * * *"
odf_dr_peer_cluster_name    = "ocp-ai-dr"      # DR Secondary cluster name
odf_dr_s3_endpoint          = ""
odf_dr_s3_bucket            = "odf-dr-metadata"
odf_dr_s3_access_key        = "REPLACE_S3_ACCESS_KEY"
odf_dr_s3_secret_key        = "REPLACE_S3_SECRET_KEY"
