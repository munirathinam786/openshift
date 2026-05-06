# Management DR — terraform.tfvars

Example variable values for the Management DR cluster. Deploys ACM Standby, ACS SecuredCluster
(pointing to Central in mgmt-dc), and Quay Enterprise on the DR management network (`10.143.42.0/24`).

!!! warning "Sensitive Values"
    Replace all `REPLACE_*` placeholders with actual credentials.

## Source Code

```hcl
# =============================================================================
# Management Cluster DR — Variable Definitions
# ACM Standby + ACS SecuredCluster + Quay Enterprise
# =============================================================================

# ---- Cluster ----
cluster_name = "mgmt-dr"
base_domain  = "dr.example.com"
ocp_version  = "4.20"

# ---- Networking ----
machine_network_cidr        = "10.143.42.0/24"
cluster_network_cidr        = "10.140.0.0/14"
cluster_network_host_prefix = 23
service_network_cidr        = "172.29.0.0/16"
api_vip                     = "10.143.42.30"
ingress_vip                 = "10.143.42.31"
gateway                     = "10.143.42.1"
dns_servers                 = ["10.143.42.2", "10.143.42.3"]
ntp_servers                 = ["pool.ntp.org"]

# ---- Pull Secret & SSH ----
pull_secret_file    = "/home/kni/pull-secret.json"
ssh_public_key_file = "~/.ssh/id_ed25519.pub"

# ---- Bastion ----
bastion_host                 = "10.143.42.10"
bastion_user                 = "kni"
bastion_ssh_private_key_file = "~/.ssh/id_ed25519"

# ---- Bootstrap ----
bootstrap_os_image_url = "http://10.143.42.10:8080/rhcos-qemu.x86_64.qcow2.gz?sha256=REPLACE_WITH_SHA256"

# ---- Local Quay Mirror (Disconnected) ----
enable_quay_mirror  = true
quay_host           = "10.143.42.15"
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
      { name = "advanced-cluster-management", channel = "release-2.11" },
      { name = "rhacs-operator", channel = "stable" },
      { name = "quay-operator", channel = "stable-3.12" },
      { name = "odf-operator", channel = "stable-4.20" },
      { name = "metallb-operator", channel = "stable" },
      { name = "cluster-logging", channel = "stable" },
      { name = "elasticsearch-operator", channel = "stable" },
      { name = "redhat-oadp-operator", channel = "stable-1.6" },
      { name = "submariner", channel = "stable-0.20" },
      { name = "odr-hub-operator", channel = "stable-4.20" },
    ]
  },
]

mirror_registry              = ""
additional_trust_bundle_file = ""

# ---- Master Nodes ----
master_nodes = [
  {
    name = "master-0"
    bmc_address      = "idrac-virtualmedia://10.143.42.100/redfish/v1/Systems/System.Embedded.1"
    bmc_username     = "admin"
    bmc_password     = "REPLACE_PASSWORD"
    boot_mac_address = "aa:bb:cc:ff:01:01"
    boot_mode        = "UEFI"
    root_disk_min_gb = 890
    ip               = "10.143.42.101"
    bond_interfaces  = ["ens1f0", "ens1f1"]
  },
  {
    name = "master-1"
    bmc_address      = "idrac-virtualmedia://10.143.42.102/redfish/v1/Systems/System.Embedded.1"
    bmc_username     = "admin"
    bmc_password     = "REPLACE_PASSWORD"
    boot_mac_address = "aa:bb:cc:ff:01:02"
    boot_mode        = "UEFI"
    root_disk_min_gb = 890
    ip               = "10.143.42.103"
    bond_interfaces  = ["ens1f0", "ens1f1"]
  },
  {
    name = "master-2"
    bmc_address      = "idrac-virtualmedia://10.143.42.104/redfish/v1/Systems/System.Embedded.1"
    bmc_username     = "admin"
    bmc_password     = "REPLACE_PASSWORD"
    boot_mac_address = "aa:bb:cc:ff:01:03"
    boot_mode        = "UEFI"
    root_disk_min_gb = 890
    ip               = "10.143.42.105"
    bond_interfaces  = ["ens1f0", "ens1f1"]
  },
]

# ---- Worker Nodes ----
worker_nodes = [
  {
    name = "worker-odf-0"
    bmc_address      = "idrac-virtualmedia://10.143.42.120/redfish/v1/Systems/System.Embedded.1"
    bmc_username     = "admin"
    bmc_password     = "REPLACE_PASSWORD"
    boot_mac_address = "aa:bb:cc:ff:02:01"
    boot_mode        = "UEFI"
    root_disk_min_gb = 890
    ip               = "10.143.42.121"
    bond_interfaces  = ["ens1f0", "ens1f1"]
    gpu_worker       = false
    odf_worker       = true
  },
  {
    name = "worker-odf-1"
    bmc_address      = "idrac-virtualmedia://10.143.42.122/redfish/v1/Systems/System.Embedded.1"
    bmc_username     = "admin"
    bmc_password     = "REPLACE_PASSWORD"
    boot_mac_address = "aa:bb:cc:ff:02:02"
    boot_mode        = "UEFI"
    root_disk_min_gb = 890
    ip               = "10.143.42.123"
    bond_interfaces  = ["ens1f0", "ens1f1"]
    gpu_worker       = false
    odf_worker       = true
  },
  {
    name = "worker-odf-2"
    bmc_address      = "idrac-virtualmedia://10.143.42.124/redfish/v1/Systems/System.Embedded.1"
    bmc_username     = "admin"
    bmc_password     = "REPLACE_PASSWORD"
    boot_mac_address = "aa:bb:cc:ff:02:03"
    boot_mode        = "UEFI"
    root_disk_min_gb = 890
    ip               = "10.143.42.125"
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

# ---- ODF ----
enable_odf           = true
odf_storage_capacity = "2Ti"
odf_channel          = "stable-4.20"

# ---- ACM (Standby — can be promoted to hub during DR failover) ----
enable_acm               = true
acm_channel              = "release-2.11"
acm_instance_name        = "multiclusterhub"
acm_enable_observability = false
acm_s3_bucket            = ""
acm_s3_endpoint          = ""
acm_s3_access_key        = ""
acm_s3_secret_key        = ""

# ---- ACS (SecuredCluster only — Central is in mgmt-dc) ----
enable_acs               = true
acs_channel              = "stable"
acs_central_storage_size = "100Gi"
acs_central_endpoint     = "central-stackrox.apps.mgmt-dc.example.com:443"

# ---- Quay Enterprise Registry ----
enable_quay_enterprise            = true
quay_enterprise_channel           = "stable-3.12"
quay_enterprise_instance_name     = "central-quay"
quay_enterprise_storage_size      = "100Gi"
quay_enterprise_superuser         = "quayadmin"
quay_enterprise_components = {
  clair          = "managed"
  clairpostgres  = "managed"
  objectstorage  = "managed"
  postgres       = "managed"
  redis          = "managed"
  horizontalpodautoscaler = "managed"
  mirror         = "managed"
  monitoring     = "managed"
  route          = "managed"
  tls            = "managed"
}

# ---- etcd Backup ----
enable_etcd_backup   = true
etcd_backup_schedule = "56 23 * * *"

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

## ACM Additional Variable Files

!!! info "Separate Var Files"
    ACM Cluster Import and DR Applications use **dedicated tfvars files** passed as additional `-var-file` arguments:
    
    - `acm-import.tfvars` — [ACM Import Config](acm-import-tfvars.md)
    - `acm-dr.tfvars` — [ACM DR Config](acm-dr-tfvars.md)
