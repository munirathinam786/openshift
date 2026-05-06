variable "assets_dir" {
  type = string
}

variable "cluster_name" {
  type = string
}

variable "base_domain" {
  type = string
}

variable "rendezvous_ip" {
  type = string
}

variable "dns_servers" {
  type = list(string)
}

variable "ntp_servers" {
  type = list(string)
}

variable "gateway" {
  type = string
}

variable "control_plane_nodes" {
  type = list(object({
    name           = string
    role           = string
    ipv4           = string
    mac_address    = string
    interface_name = string
    prefix_length  = number
    install_device = string
    cpu            = number
    memory_mb      = number
    disk_gb        = number
    zvm_userid     = string
    zvm_network    = string
  }))
}

variable "compute_nodes" {
  type = list(object({
    name           = string
    role           = string
    ipv4           = string
    mac_address    = string
    interface_name = string
    prefix_length  = number
    install_device = string
    cpu            = number
    memory_mb      = number
    disk_gb        = number
    zvm_userid     = string
    zvm_network    = string
  }))
}

locals {
  all_nodes = concat(var.control_plane_nodes, var.compute_nodes)

  agent_config = {
    apiVersion           = "v1alpha1"
    kind                 = "AgentConfig"
    rendezvousIP         = var.rendezvous_ip
    additionalNTPSources = var.ntp_servers
    hosts = [
      for node in local.all_nodes : {
        hostname       = node.name
        role           = node.role
        bootMACAddress = node.mac_address
        rootDeviceHints = {
          deviceName = node.install_device
        }
        interfaces = [
          {
            name       = node.interface_name
            macAddress = node.mac_address
          }
        ]
        networkConfig = {
          interfaces = [
            {
              name          = node.interface_name
              type          = "ethernet"
              state         = "up"
              "mac-address" = node.mac_address
              ipv4 = {
                enabled = true
                dhcp    = false
                address = [
                  {
                    ip              = node.ipv4
                    "prefix-length" = node.prefix_length
                  }
                ]
              }
            }
          ]
          "dns-resolver" = {
            config = {
              server = var.dns_servers
            }
          }
          routes = {
            config = [
              {
                destination          = "0.0.0.0/0"
                "next-hop-address"   = var.gateway
                "next-hop-interface" = node.interface_name
              }
            ]
          }
        }
      }
    ]
  }
}

resource "local_file" "agent_config" {
  filename = "${var.assets_dir}/agent-config.yaml"
  content  = yamlencode(local.agent_config)
}

output "agent_config_file" {
  value = local_file.agent_config.filename
}
