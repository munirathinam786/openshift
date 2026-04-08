# Author: Sathishkumar Munirathinam

# =============================================================================
# UPI — Ignition HTTP Server
# Serves ignition files via HTTP for RHCOS node boot
# =============================================================================

variable "install_dir" { type = string }
variable "bastion_host" { type = string }
variable "bastion_user" { type = string }
variable "bastion_ssh_key" { type = string }
variable "http_port" {
  type    = number
  default = 8080
}

resource "null_resource" "ignition_server" {
  provisioner "remote-exec" {
    inline = [
      # Copy ignition files to HTTP-accessible directory
      "sudo mkdir -p /var/www/html/ignition",
      "sudo cp ${var.install_dir}/*.ign /var/www/html/ignition/",
      "sudo chmod 644 /var/www/html/ignition/*.ign",

      # Start simple HTTP server if not using existing httpd
      <<-EOT
      if ! systemctl is-active httpd >/dev/null 2>&1; then
        cd /var/www/html/ignition
        nohup python3 -m http.server ${var.http_port} --bind 0.0.0.0 > /dev/null 2>&1 &
        echo "Started HTTP server on port ${var.http_port}"
      else
        echo "Apache httpd already running — ignition files served"
      fi
      EOT
      ,

      "echo 'Ignition files available at http://${var.bastion_host}:${var.http_port}/'",
    ]

    connection {
      type        = "ssh"
      host        = var.bastion_host
      user        = var.bastion_user
      private_key = file(var.bastion_ssh_key)
    }
  }
}

output "ignition_url" {
  value = "http://${var.bastion_host}:${var.http_port}"
}
