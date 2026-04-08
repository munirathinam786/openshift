# Author: Sathishkumar Munirathinam

# =============================================================================
# UPI — Bootstrap Node Provisioning
# Boots the bootstrap node with RHCOS and ignition config
# =============================================================================

variable "bootstrap_ip" { type = string }
variable "bootstrap_mac" { type = string }
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

resource "null_resource" "bootstrap" {
  provisioner "remote-exec" {
    inline = [
      <<-EOT
      echo "=== Provisioning bootstrap node ==="
      echo "IP: ${var.bootstrap_ip}"
      echo "MAC: ${var.bootstrap_mac}"
      echo "Boot method: ${var.boot_method}"
      echo "Ignition URL: ${var.ignition_url}"
      echo "RHCOS ISO: ${var.rhcos_iso_url}"
      echo "Install disk: ${var.install_disk}"

      %{if var.boot_method == "pxe" ~}
      # PXE boot: configure DHCP/TFTP for bootstrap
      echo "Configuring PXE boot for bootstrap node..."
      sudo tee /var/lib/tftpboot/pxelinux.cfg/01-$(echo ${var.bootstrap_mac} | tr ':' '-' | tr '[:upper:]' '[:lower:]') <<'PXEOF'
      DEFAULT bootstrap
      LABEL bootstrap
        KERNEL rhcos/kernel
        APPEND initrd=rhcos/initramfs.img coreos.inst.install_dev=${var.install_disk} coreos.inst.ignition_url=${var.ignition_url} coreos.live.rootfs_url=${var.rhcos_rootfs_url} ip=dhcp
      PXEOF
      %{endif~}

      %{if var.boot_method == "iso" ~}
      echo "ISO boot method selected — ensure bootstrap is booted from RHCOS ISO with ignition URL"
      %{endif~}
      EOT
      ,

      # Wait for bootstrap node to be reachable
      "echo 'Waiting for bootstrap node to come online...'",
      "for i in $(seq 1 120); do ssh -o StrictHostKeyChecking=no -o ConnectTimeout=5 core@${var.bootstrap_ip} 'hostname' >/dev/null 2>&1 && echo 'Bootstrap node is online.' && break || sleep 15; done",
    ]

    connection {
      type        = "ssh"
      host        = var.bastion_host
      user        = var.bastion_user
      private_key = file(var.bastion_ssh_key)
    }
  }
}

output "bootstrap_ip" {
  value = var.bootstrap_ip
}
