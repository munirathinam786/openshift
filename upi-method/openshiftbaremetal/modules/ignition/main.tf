# Author: Sathishkumar Munirathinam

# =============================================================================
# UPI — Ignition Config Generation
# Runs openshift-install to create manifests and ignition configs
# =============================================================================

variable "install_dir" { type = string }
variable "ocp_version" { type = string }
variable "bastion_host" { type = string }
variable "bastion_user" { type = string }
variable "bastion_ssh_key" { type = string }

resource "null_resource" "create_ignition" {
  provisioner "remote-exec" {
    inline = [
      "cd ${var.install_dir}",

      # Generate manifests
      "openshift-install create manifests --dir=${var.install_dir}",

      # Set masters unschedulable for UPI
      "sed -i 's/mastersSchedulable: true/mastersSchedulable: false/' ${var.install_dir}/manifests/cluster-scheduler-02-config.yml || true",

      # Generate ignition configs
      "openshift-install create ignition-configs --dir=${var.install_dir}",

      "echo 'Ignition configs generated successfully'",
      "ls -la ${var.install_dir}/*.ign",
    ]

    connection {
      type        = "ssh"
      host        = var.bastion_host
      user        = var.bastion_user
      private_key = file(var.bastion_ssh_key)
    }
  }
}

output "ignition_dir" {
  value = var.install_dir
}
