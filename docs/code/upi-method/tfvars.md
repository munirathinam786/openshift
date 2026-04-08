# UPI Method — terraform.tfvars

Environment-specific values for the UPI baremetal deployment (`upi-method/`).

!!! warning "Edit Before Deploying"
    Replace all `REPLACE_*` placeholders with your actual values before running Terraform.

## UPI-Specific Settings

```hcl
# ---- UPI Install Directory ----
install_dir = "/home/kni/ocp-install"

# ---- RHCOS Images (UPI — manual boot) ----
rhcos_iso_url    = "http://10.142.41.10:8080/rhcos-4.15.0-x86_64-live.x86_64.iso"
rhcos_rootfs_url = "http://10.142.41.10:8080/rhcos-4.15.0-x86_64-live-rootfs.x86_64.img"
install_disk     = "/dev/sda"

# ---- Boot Method ----
boot_method = "pxe"

# ---- Ignition HTTP Server ----
ignition_http_port = 8080

# ---- Bootstrap Node (ephemeral) ----
bootstrap_ip  = "10.142.41.20"
bootstrap_mac = "aa:bb:cc:dd:ee:00"
```

## Full Source

```hcl
# =============================================================================
# OpenShift Baremetal UPI + OpenShift AI — Variable Definitions
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

# ---- RHCOS Images ----
rhcos_iso_url    = "http://10.142.41.10:8080/rhcos-4.15.0-x86_64-live.x86_64.iso"
rhcos_rootfs_url = "http://10.142.41.10:8080/rhcos-4.15.0-x86_64-live-rootfs.x86_64.img"
install_disk     = "/dev/sda"
boot_method      = "pxe"
ignition_http_port = 8080

# ---- Bootstrap Node ----
bootstrap_ip  = "10.142.41.20"
bootstrap_mac = "aa:bb:cc:dd:ee:00"

# ---- Master Nodes (no BMC) ----
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

# ---- Worker Nodes (no BMC) ----
worker_nodes = [
  {
    name            = "worker-gpu-0"
    ip              = "10.142.41.111"
    mac_address     = "aa:bb:cc:dd:ee:10"
    gpu_worker      = true
    odf_worker      = false
  },
  {
    name            = "worker-gpu-1"
    ip              = "10.142.41.113"
    mac_address     = "aa:bb:cc:dd:ee:11"
    gpu_worker      = true
    odf_worker      = false
  },
  {
    name            = "worker-odf-0"
    ip              = "10.142.41.121"
    mac_address     = "aa:bb:cc:dd:ee:20"
    gpu_worker      = false
    odf_worker      = true
  },
  {
    name            = "worker-odf-1"
    ip              = "10.142.41.123"
    mac_address     = "aa:bb:cc:dd:ee:21"
    gpu_worker      = false
    odf_worker      = true
  },
  {
    name            = "worker-odf-2"
    ip              = "10.142.41.125"
    mac_address     = "aa:bb:cc:dd:ee:22"
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

# ... (GPU, ODF, OpenShift AI, Submariner settings same as IPI)

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
