variable "assets_dir" {
  type = string
}

variable "zvm_host" {
  type = string
}

variable "zvm_user" {
  type = string
}

variable "zvm_ssh_private_key_file" {
  type = string
}

variable "zvm_ssh_port" {
  type = number
}

variable "zvm_guest_script_path" {
  type = string
}

variable "auto_provision" {
  type = bool
}

variable "nodes" {
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
  guest_inventory_lines = concat(
    ["name,role,zvm_userid,cpu,memory_mb,disk_gb,ip,mac,network"],
    [
      for node in var.nodes : join(",", [
        node.name,
        node.role,
        coalesce(node.zvm_userid, upper(replace(node.name, "-", ""))),
        tostring(node.cpu),
        tostring(node.memory_mb),
        tostring(node.disk_gb),
        node.ipv4,
        node.mac_address,
        node.zvm_network,
      ])
    ]
  )

  provision_script = <<-EOT
    #!/usr/bin/env bash
    set -euo pipefail

    inventory_file="${var.assets_dir}/zvm-guests.csv"

    if [[ ! -f "$inventory_file" ]]; then
      echo "Inventory file not found: $inventory_file" >&2
      exit 1
    fi

    tail -n +2 "$inventory_file" | while IFS=, read -r name role userid cpu memory_mb disk_gb ip mac network; do
      echo "Provisioning $name ($role) on ${var.zvm_host} using USERID $userid"
      ssh -i "${var.zvm_ssh_private_key_file}" -p "${var.zvm_ssh_port}" -o StrictHostKeyChecking=no "${var.zvm_user}@${var.zvm_host}" \
        "sudo ${var.zvm_guest_script_path} --userid $userid --hostname $name --cpu $cpu --memory-mb $memory_mb --disk-gb $disk_gb --network $network --ip $ip --mac $mac"
    done
  EOT
}

resource "local_file" "guest_inventory" {
  filename = "${var.assets_dir}/zvm-guests.csv"
  content  = join("\n", local.guest_inventory_lines)
}

resource "local_file" "provision_script" {
  filename = "${var.assets_dir}/provision-zvm-guests.sh"
  content  = local.provision_script
}

resource "null_resource" "provision_guests" {
  triggers = {
    inventory_sha = sha256(local_file.guest_inventory.content)
    script_sha    = sha256(local_file.provision_script.content)
  }

  provisioner "local-exec" {
    command = var.auto_provision ? "chmod +x '${local_file.provision_script.filename}' && '${local_file.provision_script.filename}'" : "echo 'z/VM guest manifest written to ${local_file.guest_inventory.filename}; provisioning skipped by configuration.'"
  }
}

output "guest_inventory_file" {
  value = local_file.guest_inventory.filename
}

output "provision_script_file" {
  value = local_file.provision_script.filename
}
