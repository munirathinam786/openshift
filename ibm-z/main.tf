locals {
  cluster_domain = "${var.cluster_name}.${var.base_domain}"
  assets_dir     = "${path.module}/generated/${var.cluster_name}"

  control_plane_nodes = [
    for node in var.control_plane_nodes : merge(node, { role = "master" })
  ]

  compute_nodes = [
    for node in var.compute_nodes : merge(node, { role = "worker" })
  ]

  all_nodes = concat(local.control_plane_nodes, local.compute_nodes)
}

module "install_config" {
  source = "./modules/install-config"

  assets_dir                   = local.assets_dir
  cluster_name                 = var.cluster_name
  base_domain                  = var.base_domain
  architecture                 = var.architecture
  control_plane_replicas       = length(local.control_plane_nodes)
  compute_replicas             = length(local.compute_nodes)
  machine_network_cidr         = var.machine_network_cidr
  cluster_network_cidr         = var.cluster_network_cidr
  cluster_network_host_prefix  = var.cluster_network_host_prefix
  service_network_cidr         = var.service_network_cidr
  network_type                 = var.network_type
  publish_strategy             = var.publish_strategy
  pull_secret_file             = var.pull_secret_file
  ssh_public_key_file          = var.ssh_public_key_file
  additional_trust_bundle_file = var.additional_trust_bundle_file
  image_digest_sources         = var.image_digest_sources
}

module "agent_config" {
  source = "./modules/agent-config"

  assets_dir          = local.assets_dir
  cluster_name        = var.cluster_name
  base_domain         = var.base_domain
  rendezvous_ip       = var.rendezvous_ip
  dns_servers         = var.dns_servers
  ntp_servers         = var.ntp_servers
  gateway             = var.gateway
  control_plane_nodes = local.control_plane_nodes
  compute_nodes       = local.compute_nodes
}

module "zvm_guests" {
  source = "./modules/zvm-guests"
  count  = var.enable_zvm_guest_provisioning ? 1 : 0

  assets_dir               = local.assets_dir
  zvm_host                 = var.zvm_host
  zvm_user                 = var.zvm_user
  zvm_ssh_private_key_file = var.zvm_ssh_private_key_file
  zvm_ssh_port             = var.zvm_ssh_port
  zvm_guest_script_path    = var.zvm_guest_script_path
  auto_provision           = var.enable_zvm_guest_provisioning
  nodes                    = local.all_nodes
}

module "cluster_install" {
  source = "./modules/cluster-install"

  assets_dir                   = local.assets_dir
  cluster_name                 = var.cluster_name
  bastion_host                 = var.bastion_host
  bastion_user                 = var.bastion_user
  bastion_ssh_private_key_file = var.bastion_ssh_private_key_file
  openshift_install_binary     = var.openshift_install_binary
  remote_assets_dir            = "${var.remote_assets_dir}/${var.cluster_name}"
  auto_approve_install         = var.auto_approve_install

  depends_on = [
    module.install_config,
    module.agent_config,
    module.zvm_guests,
  ]
}
