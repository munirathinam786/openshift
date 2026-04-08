# =============================================================================
# UPI — Compute (Worker) Node Provisioning
# Boots worker nodes with RHCOS and approves CSRs
# =============================================================================

variable "worker_nodes" {
  type = list(object({
    name             = string
    ip               = string
    mac_address      = optional(string, "")
    boot_mac_address = optional(string, "")
    boot_mode        = optional(string, "UEFI")
    bond_interfaces  = optional(list(string), ["ens1f0", "ens1f1"])
    root_disk_min_gb = optional(number, 890)
    gpu_worker       = optional(bool, false)
    odf_worker       = optional(bool, false)
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
  worker_mac = [
    for w in var.worker_nodes :
    coalesce(w.mac_address, w.boot_mac_address)
  ]
}

resource "null_resource" "compute_nodes" {
  count = length(var.worker_nodes)

  provisioner "remote-exec" {
    inline = [
      <<-EOT
      echo "=== Provisioning worker node: ${var.worker_nodes[count.index].name} ==="
      echo "IP: ${var.worker_nodes[count.index].ip}"
      echo "MAC: ${local.worker_mac[count.index]}"

      %{if var.boot_method == "pxe" ~}
      MAC_LOWER=$(echo ${local.worker_mac[count.index]} | tr ':' '-' | tr '[:upper:]' '[:lower:]')
      sudo tee /var/lib/tftpboot/pxelinux.cfg/01-$MAC_LOWER <<'PXEOF'
      DEFAULT worker
      LABEL worker
        KERNEL rhcos/kernel
        APPEND initrd=rhcos/initramfs.img coreos.inst.install_dev=${var.install_disk} coreos.inst.ignition_url=${var.ignition_url} coreos.live.rootfs_url=${var.rhcos_rootfs_url} ip=dhcp
      PXEOF
      %{endif~}
      EOT
      ,

      # Wait for worker node to be reachable
      "echo 'Waiting for worker ${var.worker_nodes[count.index].name} to come online...'",
      "for i in $(seq 1 120); do ssh -o StrictHostKeyChecking=no -o ConnectTimeout=5 core@${var.worker_nodes[count.index].ip} 'hostname' >/dev/null 2>&1 && echo 'Worker node online.' && break || sleep 15; done",
    ]

    connection {
      type        = "ssh"
      host        = var.bastion_host
      user        = var.bastion_user
      private_key = file(var.bastion_ssh_key)
    }
  }
}

output "worker_ips" {
  value = [for w in var.worker_nodes : w.ip]
}
