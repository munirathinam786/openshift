# Author: Sathishkumar Munirathinam

# =============================================================================
# Module: OCP Baremetal Install
# Generates install-config.yaml, runs openshift-baremetal-install on bastion
# =============================================================================

variable "cluster_name" { type = string }
variable "base_domain" { type = string }
variable "ocp_version" { type = string }
variable "machine_network_cidr" { type = string }
variable "cluster_network_cidr" { type = string }
variable "cluster_network_host_prefix" { type = number }
variable "service_network_cidr" { type = string }
variable "api_vip" { type = string }
variable "ingress_vip" { type = string }
variable "dns_servers" { type = list(string) }
variable "ntp_servers" { type = list(string) }
variable "gateway" { type = string }
variable "pull_secret_file" { type = string }
variable "ssh_public_key_file" { type = string }
variable "bastion_host" { type = string }
variable "bastion_user" { type = string }
variable "bastion_ssh_key" { type = string }
variable "bootstrap_os_image_url" { type = string }
variable "mirror_registry" { type = string }
variable "additional_trust_bundle_file" { type = string }
variable "master_nodes" {
  type = list(object({
    name             = string
    bmc_address      = string
    bmc_username     = string
    bmc_password     = string
    boot_mac_address = string
    boot_mode        = string
    root_disk_min_gb = number
    ip               = string
    bond_interfaces  = list(string)
  }))
}
variable "worker_nodes" {
  type = list(object({
    name             = string
    bmc_address      = string
    bmc_username     = string
    bmc_password     = string
    boot_mac_address = string
    boot_mode        = string
    root_disk_min_gb = number
    ip               = string
    bond_interfaces  = list(string)
    gpu_worker       = bool
    odf_worker       = bool
  }))
}

locals {
  install_dir    = "/home/${var.bastion_user}/ocp-install"
  kubeconfig     = "${local.install_dir}/auth/kubeconfig"
  cluster_domain = "${var.cluster_name}.${var.base_domain}"
}

# --- Generate install-config.yaml from template ---
resource "local_file" "install_config" {
  filename = "${path.module}/generated/install-config.yaml"
  content = templatefile("${path.module}/templates/install-config.yaml.tftpl", {
    cluster_name                = var.cluster_name
    base_domain                 = var.base_domain
    machine_network_cidr        = var.machine_network_cidr
    cluster_network_cidr        = var.cluster_network_cidr
    cluster_network_host_prefix = var.cluster_network_host_prefix
    service_network_cidr        = var.service_network_cidr
    api_vip                     = var.api_vip
    ingress_vip                 = var.ingress_vip
    bootstrap_os_image_url      = var.bootstrap_os_image_url
    master_nodes                = var.master_nodes
    worker_nodes                = var.worker_nodes
    dns_servers                 = var.dns_servers
    gateway                     = var.gateway
    pull_secret                 = file(var.pull_secret_file)
    ssh_public_key              = file(var.ssh_public_key_file)
    mirror_registry             = var.mirror_registry
    additional_trust_bundle     = var.additional_trust_bundle_file != "" ? file(var.additional_trust_bundle_file) : ""
  })
}

# --- Copy install-config to bastion and run installer ---
resource "null_resource" "ocp_install" {
  triggers = {
    install_config_hash = sha256(local_file.install_config.content)
  }

  connection {
    type        = "ssh"
    host        = var.bastion_host
    user        = var.bastion_user
    private_key = file(var.bastion_ssh_key)
  }

  # Create install directory
  provisioner "remote-exec" {
    inline = [
      "mkdir -p ${local.install_dir}",
    ]
  }

  # Upload install-config.yaml
  provisioner "file" {
    source      = local_file.install_config.filename
    destination = "${local.install_dir}/install-config.yaml"
  }

  # Run the baremetal installer
  provisioner "remote-exec" {
    inline = [
      "cd ${local.install_dir}",
      "cp install-config.yaml install-config.yaml.bak",
      "openshift-baremetal-install --dir=${local.install_dir} --log-level=info create cluster",
    ]
  }

  depends_on = [local_file.install_config]
}

# --- Download kubeconfig from bastion ---
resource "null_resource" "fetch_kubeconfig" {
  triggers = {
    install = null_resource.ocp_install.id
  }

  provisioner "local-exec" {
    command = "scp -o StrictHostKeyChecking=no -i ${var.bastion_ssh_key} ${var.bastion_user}@${var.bastion_host}:${local.kubeconfig} ${path.module}/generated/kubeconfig"
  }

  depends_on = [null_resource.ocp_install]
}

output "kubeconfig_path" {
  value = "${path.module}/generated/kubeconfig"
}

output "install_config_path" {
  value = local_file.install_config.filename
}
