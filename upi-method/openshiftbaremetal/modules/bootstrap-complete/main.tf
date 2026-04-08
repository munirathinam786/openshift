# =============================================================================
# UPI — Bootstrap Complete (wait for bootstrap to finish)
# Waits for openshift-install bootstrap-complete and CSR approval
# =============================================================================

variable "install_dir" { type = string }
variable "ocp_version" { type = string }
variable "bastion_host" { type = string }
variable "bastion_user" { type = string }
variable "bastion_ssh_key" { type = string }

resource "null_resource" "bootstrap_complete" {
  provisioner "remote-exec" {
    inline = [
      "export KUBECONFIG=${var.install_dir}/auth/kubeconfig",

      # Approve any pending CSRs (bootstrap phase)
      <<-EOT
      echo "Auto-approving pending CSRs..."
      for i in $(seq 1 30); do
        oc get csr -o go-template='{{range .items}}{{if not .status}}{{.metadata.name}}{{"\n"}}{{end}}{{end}}' 2>/dev/null | xargs -r oc adm certificate approve 2>/dev/null || true
        sleep 30
      done &
      CSR_PID=$!
      EOT
      ,

      # Wait for bootstrap to complete
      "openshift-install wait-for bootstrap-complete --dir=${var.install_dir} --log-level=info 2>&1 | tail -20",

      "echo 'Bootstrap complete.'",
    ]

    connection {
      type        = "ssh"
      host        = var.bastion_host
      user        = var.bastion_user
      private_key = file(var.bastion_ssh_key)
    }
  }
}

output "bootstrap_complete" {
  value = true
}
