# Author: Sathishkumar Munirathinam

# =============================================================================
# UPI — Bootstrap Cleanup
# Removes bootstrap node from load balancer and powers it off
# =============================================================================

variable "bootstrap_ip" { type = string }
variable "bastion_host" { type = string }
variable "bastion_user" { type = string }
variable "bastion_ssh_key" { type = string }
variable "boot_method" {
  type    = string
  default = "pxe"
}

resource "null_resource" "bootstrap_cleanup" {
  provisioner "remote-exec" {
    inline = [
      "echo 'Cleaning up bootstrap node at ${var.bootstrap_ip}...'",

      # Remove bootstrap from HAProxy configuration
      <<-EOT
      if [ -f /etc/haproxy/haproxy.cfg ]; then
        sudo sed -i '/bootstrap/d' /etc/haproxy/haproxy.cfg
        sudo systemctl reload haproxy || true
        echo "Removed bootstrap from HAProxy"
      fi
      EOT
      ,

      # Remove PXE config for bootstrap
      <<-EOT
      %{if var.boot_method == "pxe" ~}
      sudo rm -f /var/lib/tftpboot/pxelinux.cfg/01-* 2>/dev/null || true
      echo "Removed PXE boot config for bootstrap"
      %{endif~}
      EOT
      ,

      # Power off bootstrap node (via SSH)
      "ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10 core@${var.bootstrap_ip} 'sudo shutdown -h now' 2>/dev/null || echo 'Bootstrap node powered off or unreachable.'",
    ]

    connection {
      type        = "ssh"
      host        = var.bastion_host
      user        = var.bastion_user
      private_key = file(var.bastion_ssh_key)
    }
  }
}

output "cleanup_complete" {
  value = true
}
