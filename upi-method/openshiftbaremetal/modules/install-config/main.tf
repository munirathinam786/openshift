# Author: Sathishkumar Munirathinam

# =============================================================================
# UPI — Install Config Generation (platform: none)
# Generates install-config.yaml for UPI bare metal deployment
# =============================================================================

variable "cluster_name" { type = string }
variable "base_domain" { type = string }
variable "ocp_version" { type = string }
variable "machine_network_cidr" { type = string }
variable "cluster_network_cidr" { type = string }
variable "cluster_network_host_prefix" { type = number }
variable "service_network_cidr" { type = string }
variable "dns_servers" { type = list(string) }
variable "pull_secret_file" { type = string }
variable "ssh_public_key_file" { type = string }
variable "install_dir" { type = string }
variable "bastion_host" { type = string }
variable "bastion_user" { type = string }
variable "bastion_ssh_key" { type = string }
variable "mirror_registry" {
  type    = string
  default = ""
}
variable "additional_trust_bundle_file" {
  type    = string
  default = ""
}
variable "master_replicas" {
  type    = number
  default = 3
}
variable "worker_replicas" {
  type    = number
  default = 3
}

resource "null_resource" "install_config" {
  provisioner "remote-exec" {
    inline = [
      "mkdir -p ${var.install_dir}",

      # Read pull secret and SSH key
      "PULL_SECRET=$(cat ${var.pull_secret_file})",
      "SSH_KEY=$(cat ${var.ssh_public_key_file})",

      # Generate install-config.yaml for UPI (platform: none)
      <<-EOT
      cat > ${var.install_dir}/install-config.yaml <<EOCFG
      apiVersion: v1
      metadata:
        name: ${var.cluster_name}
      baseDomain: ${var.base_domain}
      compute:
        - architecture: amd64
          hyperthreading: Enabled
          name: worker
          replicas: 0
      controlPlane:
        architecture: amd64
        hyperthreading: Enabled
        name: master
        replicas: ${var.master_replicas}
      networking:
        clusterNetwork:
          - cidr: ${var.cluster_network_cidr}
            hostPrefix: ${var.cluster_network_host_prefix}
        machineNetwork:
          - cidr: ${var.machine_network_cidr}
        networkType: OVNKubernetes
        serviceNetwork:
          - ${var.service_network_cidr}
      platform:
        none: {}
      pullSecret: '$PULL_SECRET'
      sshKey: '$SSH_KEY'
      EOCFG
      EOT
      ,

      # Backup the install-config.yaml
      "cp ${var.install_dir}/install-config.yaml ${var.install_dir}/install-config.yaml.bak",
    ]

    connection {
      type        = "ssh"
      host        = var.bastion_host
      user        = var.bastion_user
      private_key = file(var.bastion_ssh_key)
    }
  }
}

output "install_dir" {
  value = var.install_dir
}
