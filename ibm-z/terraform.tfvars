cluster_name        = "ocp-z-prod"
base_domain         = "example.ibmz.lab"
openshift_version   = "4.20"
release_image       = "mirror.ibmz.lab:8443/openshift/release-images:4.20.0-s390x"
architecture        = "s390x"
pull_secret_file    = "/secure/pull-secret.json"
ssh_public_key_file = "/secure/id_ed25519.pub"

additional_trust_bundle_file = "/secure/mirror-ca.crt"

machine_network_cidr        = "10.154.10.0/24"
cluster_network_cidr        = "10.160.0.0/14"
cluster_network_host_prefix = 23
service_network_cidr        = "172.31.0.0/16"
network_type                = "OVNKubernetes"
publish_strategy            = "External"

dns_servers = ["10.154.10.10", "10.154.10.11"]
ntp_servers = ["10.154.10.20"]
gateway     = "10.154.10.1"

rendezvous_ip = "10.154.10.21"

image_digest_sources = [
  {
    source  = "quay.io/openshift-release-dev/ocp-release"
    mirrors = ["mirror.ibmz.lab:8443/openshift/release-images"]
  },
  {
    source  = "quay.io/openshift-release-dev/ocp-v4.0-art-dev"
    mirrors = ["mirror.ibmz.lab:8443/openshift/release-artifacts"]
  }
]

bastion_host                 = "helper.ibmz.lab"
bastion_user                 = "kni"
bastion_ssh_private_key_file = "/secure/id_ed25519"
openshift_install_binary     = "/usr/local/bin/openshift-install"
remote_assets_dir            = "/var/tmp/ocp-ibmz"
auto_launch_install          = false
auto_approve_install         = false

enable_zvm_guest_provisioning = true
zvm_host                      = "zvm-mgmt.ibmz.lab"
zvm_user                      = "automation"
zvm_ssh_private_key_file      = "/secure/id_ed25519"
zvm_guest_script_path         = "/opt/ibmz/provision-guest.sh"

control_plane_nodes = [
  {
    name        = "ocp-z-master-0"
    ipv4        = "10.154.10.21"
    mac_address = "02:00:00:00:10:21"
    zvm_userid  = "OCPZM01"
    zvm_network = "VSW1"
  },
  {
    name        = "ocp-z-master-1"
    ipv4        = "10.154.10.22"
    mac_address = "02:00:00:00:10:22"
    zvm_userid  = "OCPZM02"
    zvm_network = "VSW1"
  },
  {
    name        = "ocp-z-master-2"
    ipv4        = "10.154.10.23"
    mac_address = "02:00:00:00:10:23"
    zvm_userid  = "OCPZM03"
    zvm_network = "VSW1"
  }
]

compute_nodes = [
  {
    name        = "ocp-z-worker-0"
    ipv4        = "10.154.10.31"
    mac_address = "02:00:00:00:10:31"
    zvm_userid  = "OCPZW01"
    zvm_network = "VSW1"
    disk_gb     = 750
  },
  {
    name        = "ocp-z-worker-1"
    ipv4        = "10.154.10.32"
    mac_address = "02:00:00:00:10:32"
    zvm_userid  = "OCPZW02"
    zvm_network = "VSW1"
    disk_gb     = 750
  }
]
