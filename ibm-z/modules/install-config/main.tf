variable "assets_dir" {
  type = string
}

variable "cluster_name" {
  type = string
}

variable "base_domain" {
  type = string
}

variable "architecture" {
  type = string
}

variable "control_plane_replicas" {
  type = number
}

variable "compute_replicas" {
  type = number
}

variable "machine_network_cidr" {
  type = string
}

variable "cluster_network_cidr" {
  type = string
}

variable "cluster_network_host_prefix" {
  type = number
}

variable "service_network_cidr" {
  type = string
}

variable "network_type" {
  type = string
}

variable "publish_strategy" {
  type = string
}

variable "pull_secret_file" {
  type = string
}

variable "ssh_public_key_file" {
  type = string
}

variable "additional_trust_bundle_file" {
  type = string
}

variable "image_digest_sources" {
  type = list(object({
    source  = string
    mirrors = list(string)
  }))
}

locals {
  install_config = merge(
    {
      apiVersion = "v1"
      baseDomain = var.base_domain
      metadata = {
        name = var.cluster_name
      }
      controlPlane = {
        name           = "master"
        replicas       = var.control_plane_replicas
        architecture   = var.architecture
        hyperthreading = "Enabled"
      }
      compute = [
        {
          name           = "worker"
          replicas       = var.compute_replicas
          architecture   = var.architecture
          hyperthreading = "Enabled"
        }
      ]
      networking = {
        networkType = var.network_type
        machineNetwork = [
          {
            cidr = var.machine_network_cidr
          }
        ]
        clusterNetwork = [
          {
            cidr       = var.cluster_network_cidr
            hostPrefix = var.cluster_network_host_prefix
          }
        ]
        serviceNetwork = [var.service_network_cidr]
      }
      platform = {
        none = {}
      }
      publish    = var.publish_strategy
      pullSecret = trimspace(file(var.pull_secret_file))
      sshKey     = trimspace(file(var.ssh_public_key_file))
    },
    length(trimspace(var.additional_trust_bundle_file)) > 0 ? {
      additionalTrustBundle = file(var.additional_trust_bundle_file)
    } : {},
    length(var.image_digest_sources) > 0 ? {
      imageDigestSources = var.image_digest_sources
    } : {}
  )
}

resource "local_file" "install_config" {
  filename = "${var.assets_dir}/install-config.yaml"
  content  = yamlencode(local.install_config)
}

output "install_config_file" {
  value = local_file.install_config.filename
}
