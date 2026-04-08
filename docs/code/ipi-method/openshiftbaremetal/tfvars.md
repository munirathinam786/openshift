# DC Primary — terraform.tfvars

Example variable values for the DC Primary workload cluster. Update all `REPLACE_*` placeholders
with your environment-specific values before deployment.

!!! warning "Sensitive Values"
    Replace all `REPLACE_*` placeholders with actual credentials. Never commit real secrets to version control.
    Use ADO Variable Groups or environment variables for sensitive values.

## Source Code

```hcl
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

# ---- HAProxy Load Balancers (optional) ----
haproxy_hosts = []

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
# Enable when deploying DC+DR with storage replication

# ---- LDAP / OAuth Identity Provider ----
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

enable_ldap_group_sync     = true
ldap_user_base_dn          = "OU=Users,DC=example,DC=com"
ldap_group_base_dn         = "OU=OpenShift,OU=Groups,DC=example,DC=com"
ldap_group_filter          = "(objectClass=group)"
ldap_group_membership_attr = "member"
ldap_group_sync_schedule   = "*/30 * * * *"

ldap_group_role_bindings = [
  { group_name = "ocp-cluster-admins",  cluster_role = "cluster-admin" },
  { group_name = "ocp-developers",      cluster_role = "edit" },
  { group_name = "ocp-viewers",         cluster_role = "view" },
]

disable_kubeadmin = false
```
