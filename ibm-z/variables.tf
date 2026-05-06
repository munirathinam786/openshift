variable "cluster_name" {
  description = "Short cluster name used in DNS and install assets."
  type        = string
}

variable "base_domain" {
  description = "Base DNS domain for the OpenShift cluster."
  type        = string
}

variable "openshift_version" {
  description = "OpenShift version used for documentation and tagging."
  type        = string
  default     = "4.20"
}

variable "release_image" {
  description = "Mirrored OpenShift release image for the s390x payload."
  type        = string
}

variable "architecture" {
  description = "Target CPU architecture. IBM Z uses s390x."
  type        = string
  default     = "s390x"
}

variable "pull_secret_file" {
  description = "Path to the pull secret file available to Terraform."
  type        = string
}

variable "ssh_public_key_file" {
  description = "Path to the SSH public key injected into cluster nodes."
  type        = string
}

variable "additional_trust_bundle_file" {
  description = "Optional CA bundle for disconnected registry trust."
  type        = string
  default     = ""
}

variable "machine_network_cidr" {
  description = "Machine network CIDR used by the IBM Z nodes."
  type        = string
}

variable "cluster_network_cidr" {
  description = "Pod network CIDR."
  type        = string
}

variable "cluster_network_host_prefix" {
  description = "Pod network host prefix."
  type        = number
  default     = 23
}

variable "service_network_cidr" {
  description = "Service network CIDR."
  type        = string
}

variable "network_type" {
  description = "OpenShift network plugin."
  type        = string
  default     = "OVNKubernetes"
}

variable "publish_strategy" {
  description = "OpenShift publish strategy."
  type        = string
  default     = "External"
}

variable "dns_servers" {
  description = "DNS servers reachable by IBM Z nodes."
  type        = list(string)
}

variable "ntp_servers" {
  description = "NTP servers reachable by IBM Z nodes."
  type        = list(string)
  default     = []
}

variable "gateway" {
  description = "Default gateway for static node configuration."
  type        = string
}

variable "rendezvous_ip" {
  description = "Rendezvous IP used by the agent-based installer."
  type        = string
}

variable "image_digest_sources" {
  description = "Optional mirrored registry sources for disconnected installations."
  type = list(object({
    source  = string
    mirrors = list(string)
  }))
  default = []
}

variable "bastion_host" {
  description = "Bastion or helper host that runs openshift-install."
  type        = string
}

variable "bastion_user" {
  description = "SSH user for the bastion host."
  type        = string
}

variable "bastion_ssh_private_key_file" {
  description = "Path to the SSH private key used for bastion access."
  type        = string
}

variable "openshift_install_binary" {
  description = "Absolute path to openshift-install on the bastion host."
  type        = string
  default     = "/usr/local/bin/openshift-install"
}

variable "remote_assets_dir" {
  description = "Remote directory on the bastion host that stores cluster assets."
  type        = string
  default     = "/var/tmp/ocp-ibmz"
}

variable "enable_zvm_guest_provisioning" {
  description = "If true, Terraform generates and optionally runs z/VM guest provisioning commands."
  type        = bool
  default     = false
}

variable "auto_approve_install" {
  description = "If true, Terraform waits for install completion on the bastion host."
  type        = bool
  default     = false
}

variable "zvm_host" {
  description = "Optional z/VM management host."
  type        = string
  default     = ""
}

variable "zvm_user" {
  description = "SSH user for the z/VM management host."
  type        = string
  default     = ""
}

variable "zvm_ssh_private_key_file" {
  description = "SSH private key used for the z/VM management host."
  type        = string
  default     = ""
}

variable "zvm_ssh_port" {
  description = "SSH port for the z/VM management host."
  type        = number
  default     = 22
}

variable "zvm_guest_script_path" {
  description = "Site-specific automation wrapper used to create or update z/VM guests."
  type        = string
  default     = "/opt/ibmz/provision-guest.sh"
}

variable "control_plane_nodes" {
  description = "IBM Z control plane nodes."
  type = list(object({
    name           = string
    ipv4           = string
    mac_address    = string
    interface_name = optional(string, "enc600")
    prefix_length  = optional(number, 24)
    install_device = optional(string, "/dev/dasda")
    cpu            = optional(number, 8)
    memory_mb      = optional(number, 32768)
    disk_gb        = optional(number, 250)
    zvm_userid     = optional(string, null)
    zvm_network    = optional(string, "VSW1")
  }))
}

variable "compute_nodes" {
  description = "IBM Z worker nodes."
  type = list(object({
    name           = string
    ipv4           = string
    mac_address    = string
    interface_name = optional(string, "enc600")
    prefix_length  = optional(number, 24)
    install_device = optional(string, "/dev/dasda")
    cpu            = optional(number, 8)
    memory_mb      = optional(number, 32768)
    disk_gb        = optional(number, 500)
    zvm_userid     = optional(string, null)
    zvm_network    = optional(string, "VSW1")
  }))
}
