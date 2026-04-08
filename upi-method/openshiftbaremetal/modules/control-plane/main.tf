# =============================================================================
# UPI — Control Plane Node Provisioning
# Boots master/control-plane nodes with RHCOS and ignition config
# =============================================================================

variable "master_nodes" {
  type = list(object({
    name             = string
    ip               = string
    mac_address      = optional(string, "")
    boot_mac_address = optional(string, "")
    boot_mode        = optional(string, "UEFI")
    bond_interfaces  = optional(list(string), ["ens1f0", "ens1f1"])
    root_disk_min_gb = optional(number, 890)
  }))
}
variable "rhcos_iso_url" { type = string }
variable "rhcos_rootfs_url" { type = string }
variable "ignition_url" { type = string }
variable "install_disk" {
  type    = string
  default = "/dev/sda"
}
variable "bastion_host" { type = string }
variable "bastion_user" { type = string }
variable "bastion_ssh_key" { type = string }
variable "boot_method" {
  type    = string
  default = "pxe"
}

locals {
  master_mac = [
    for m in var.master_nodes :
    coalesce(m.mac_address, m.boot_mac_address)
  ]
}

resource "null_resource" "control_plane" {
  count = length(var.master_nodes)

  provisioner "remote-exec" {
    inline = [
      <<-EOT
      echo "=== Provisioning control plane node: ${var.master_nodes[count.index].name} ==="
      echo "IP: ${var.master_nodes[count.index].ip}"
      echo "MAC: ${local.master_mac[count.index]}"

      %{if var.boot_method == "pxe" ~}
      MAC_LOWER=$(echo ${local.master_mac[count.index]} | tr ':' '-' | tr '[:upper:]' '[:lower:]')
      sudo tee /var/lib/tftpboot/pxelinux.cfg/01-$MAC_LOWER <<'PXEOF'
      DEFAULT master
      LABEL master
        KERNEL rhcos/kernel
        APPEND initrd=rhcos/initramfs.img coreos.inst.install_dev=${var.install_disk} coreos.inst.ignition_url=${var.ignition_url} coreos.live.rootfs_url=${var.rhcos_rootfs_url} ip=dhcp
      PXEOF
      %{endif~}
      EOT
      ,

      # Wait for control plane node to be reachable
      "echo 'Waiting for master ${var.master_nodes[count.index].name} to come online...'",
      "for i in $(seq 1 120); do ssh -o StrictHostKeyChecking=no -o ConnectTimeout=5 core@${var.master_nodes[count.index].ip} 'hostname' >/dev/null 2>&1 && echo 'Master node online.' && break || sleep 15; done",
    ]

    connection {
      type        = "ssh"
      host        = var.bastion_host
      user        = var.bastion_user
      private_key = file(var.bastion_ssh_key)
    }
  }
}

output "master_ips" {
  value = [for m in var.master_nodes : m.ip]
}
